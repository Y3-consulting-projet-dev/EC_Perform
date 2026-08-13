import mimetypes
import os
import re
import uuid
from datetime import datetime, timedelta, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from app.auth import create_access_token, decode_access_token, hash_password, verify_password
from app.balance import compute_coherence, compute_intangibilite, parse_balance_file
from app.db import db

app = FastAPI(title="Ec-perform API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOADS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "uploads"))
os.makedirs(UPLOADS_DIR, exist_ok=True)

INLINE_MIME_TYPES = {"application/pdf"}

bearer_scheme = HTTPBearer()


def get_current_employee(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    try:
        email = decode_access_token(credentials.credentials)
    except Exception:
        raise HTTPException(status_code=401, detail="Session invalide ou expirée")
    employee = db.employees.find_one({"email": email})
    if employee is None:
        raise HTTPException(status_code=401, detail="Utilisateur introuvable")
    return employee


class LoginRequest(BaseModel):
    email: str
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class UpdateProfileRequest(BaseModel):
    nom: str
    prenoms: str


class ClientCreateRequest(BaseModel):
    raisonSociale: str
    secteurActivite: str
    formeJuridique: str = ""
    rccm: str
    compteContribuable: str = ""
    regimeFiscal: str = ""
    adresse: str = ""
    exerciceComptable: str = ""
    ville: str
    contactPrincipal: str = ""
    email: str = ""
    telephone: str = ""


class MissionCreateRequest(BaseModel):
    clientId: str
    exercice: str
    phase: str = "1/7 · Ouverture et collecte"
    statut: str = "En cours"
    rapport: str | None = None
    dateDebut: str
    echeance: str
    manager: str = ""
    senior: str = ""


class MissionCloseRequest(BaseModel):
    dateFin: str | None = None


class DocumentStatusUpdate(BaseModel):
    statut: str


DEFAULT_DOCUMENT_CATEGORIES = [
    "DOCUMENT GENERAUX DE LA SOCIETE",
    "OPERATIONS DE TRESORERIE",
    "ACHATS ET VENTES/PRESTATIONS",
    "GESTION DE LA PAIE",
    "CADRE FISCALE ET SOCIALE",
]


def _default_documents():
    return {"categories": [{"title": title, "documents": []} for title in DEFAULT_DOCUMENT_CATEGORIES]}


def serialize_documents(mission_doc):
    documents = mission_doc.get("documents") or _default_documents()
    categories = documents.get("categories", [])
    total = sum(len(c.get("documents", [])) for c in categories)
    recus = sum(1 for c in categories for d in c.get("documents", []) if d.get("statut") == "Reçu")
    return {
        "recus": recus,
        "total": total,
        "categories": categories,
        "phase": mission_doc.get("phase", ""),
    }


def serialize_mission(doc):
    created_at = doc.get("createdAt")
    return {
        "id": str(doc["_id"]),
        "clientId": doc["clientId"],
        "exercice": doc.get("exercice", ""),
        "phase": doc.get("phase", ""),
        "phaseStep": _mission_step(doc),
        "statut": doc.get("statut", ""),
        "rapport": doc.get("rapport"),
        "dateDebut": doc.get("dateDebut", ""),
        "echeance": doc.get("echeance", ""),
        "dateFinReelle": doc.get("dateFinReelle"),
        "manager": doc.get("manager", ""),
        "senior": doc.get("senior", ""),
        "createdBy": doc.get("createdBy", {}),
        "createdAt": created_at.isoformat() if created_at else None,
    }


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def serialize_client(doc):
    # The `clients` collection mixes two schemas: records bulk-imported from the legacy
    # source (company_name/sector/legal_form/RCCM/address/responsable_*) and records
    # created via the app (raisonSociale/secteurActivite/...). Fall back across both.
    address = doc.get("adresse") or doc.get("address") or ""
    address = address.strip()

    ville = doc.get("ville") or ""
    if not ville and address:
        parts = [p.strip() for p in address.split(",") if p.strip()]
        ville = parts[-1] if parts else ""

    contact_principal = doc.get("contactPrincipal") or ""
    if not contact_principal:
        civility = (doc.get("civility") or "").strip()
        name = (doc.get("responsable_name") or "").strip()
        function = (doc.get("responsable_function") or "").strip()
        who = " ".join(p for p in [civility, name] if p)
        contact_principal = f"{who} — {function}" if who and function else who or function

    return {
        "id": str(doc["_id"]),
        "raisonSociale": doc.get("raisonSociale") or doc.get("company_name") or "",
        "secteurActivite": doc.get("secteurActivite") or doc.get("sector") or "",
        "formeJuridique": doc.get("formeJuridique") or doc.get("legal_form") or "",
        "rccm": doc.get("rccm") or doc.get("RCCM") or "",
        "compteContribuable": doc.get("compteContribuable", ""),
        "regimeFiscal": doc.get("regimeFiscal", ""),
        "adresse": address,
        "exerciceComptable": doc.get("exerciceComptable", ""),
        "ville": ville,
        "contactPrincipal": contact_principal,
        "email": doc.get("email", ""),
        "telephone": doc.get("telephone", ""),
        "missionsEnCours": doc.get("missionsEnCours", 0),
        "missions": doc.get("missions", []),
    }


@app.get("/health")
def health():
    server_info = db.client.server_info()
    return {"status": "ok", "database": db.name, "mongo_version": server_info["version"]}


@app.post("/auth/login")
def login(payload: LoginRequest):
    employee = db.employees.find_one({"email": payload.email.strip().lower()})
    if employee is None or not verify_password(payload.password, employee["password_hash"]):
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")
    token = create_access_token(employee["email"])
    return {
        "access_token": token,
        "token_type": "bearer",
        "must_change_password": employee.get("must_change_password", False),
        "employee": {
            "nom": employee["nom"],
            "prenoms": employee["prenoms"],
            "grade": employee["grade"],
            "departement": employee["departement"],
            "email": employee["email"],
        },
    }


@app.post("/auth/change-password")
def change_password(payload: ChangePasswordRequest, employee=Depends(get_current_employee)):
    if not verify_password(payload.current_password, employee["password_hash"]):
        raise HTTPException(status_code=401, detail="Mot de passe actuel incorrect")
    db.employees.update_one(
        {"_id": employee["_id"]},
        {"$set": {"password_hash": hash_password(payload.new_password), "must_change_password": False}},
    )
    return {"status": "ok"}


@app.patch("/employees/me")
def update_profile(payload: UpdateProfileRequest, employee=Depends(get_current_employee)):
    db.employees.update_one(
        {"_id": employee["_id"]},
        {"$set": {"nom": payload.nom.strip(), "prenoms": payload.prenoms.strip()}},
    )
    updated = db.employees.find_one({"_id": employee["_id"]})
    return {
        "nom": updated["nom"],
        "prenoms": updated["prenoms"],
        "grade": updated["grade"],
        "departement": updated["departement"],
        "email": updated["email"],
    }


@app.get("/employees")
def list_employees(employee=Depends(get_current_employee)):
    employees = db.employees.find().sort("nom", 1)
    return [
        {
            "id": str(e["_id"]),
            "nom": e.get("nom", ""),
            "prenoms": e.get("prenoms", ""),
            "grade": e.get("grade", ""),
            "departement": e.get("departement", ""),
        }
        for e in employees
    ]


@app.get("/clients/stats")
def client_stats(employee=Depends(get_current_employee)):
    total = db.clients.count_documents({})
    cutoff = datetime.now(timezone.utc) - timedelta(days=90)
    new_last_three_months = db.clients.count_documents({"_id": {"$gte": ObjectId.from_datetime(cutoff)}})
    return {"total": total, "newLastThreeMonths": new_last_three_months}


@app.get("/missions/stats")
def mission_stats(employee=Depends(get_current_employee)):
    en_cours = db.missions.count_documents({"statut": "En cours"})

    now = datetime.now(timezone.utc)
    start_this_month = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    if now.month == 1:
        start_last_month = datetime(now.year - 1, 12, 1, tzinfo=timezone.utc)
    else:
        start_last_month = datetime(now.year, now.month - 1, 1, tzinfo=timezone.utc)

    this_month = db.missions.count_documents({"createdAt": {"$gte": start_this_month}})
    last_month = db.missions.count_documents({"createdAt": {"$gte": start_last_month, "$lt": start_this_month}})

    terminees_cette_annee = []
    for m in db.missions.find({"statut": "Terminée"}):
        date_fin = _parse_date(m.get("dateFinReelle"))
        if date_fin and date_fin.year == now.year:
            terminees_cette_annee.append(m)

    total_terminees = len(terminees_cette_annee)
    dans_les_delais = sum(
        1
        for m in terminees_cette_annee
        if (echeance := _parse_date(m.get("echeance"))) and (date_fin := _parse_date(m.get("dateFinReelle"))) and date_fin <= echeance
    )
    pourcentage_dans_les_delais = round(dans_les_delais / total_terminees * 100) if total_terminees else None

    return {
        "enCours": en_cours,
        "deltaVsLastMonth": this_month - last_month,
        "terminees": total_terminees,
        "annee": now.year,
        "pourcentageDansLesDelais": pourcentage_dans_les_delais,
    }


@app.get("/missions")
def list_missions(employee=Depends(get_current_employee)):
    clients_by_id = {str(c["_id"]): c for c in db.clients.find()}
    managers_by_name = {}
    for e in db.employees.find():
        full_name = f"{e.get('prenoms', '')} {e.get('nom', '')}".strip()
        managers_by_name[full_name] = e

    today = datetime.now(timezone.utc).date()
    missions = []
    for m in db.missions.find():
        client = clients_by_id.get(m.get("clientId"))
        client_name = ""
        if client:
            client_name = client.get("raisonSociale") or client.get("company_name") or ""

        manager = managers_by_name.get(m.get("manager", ""))
        manager_grade = manager.get("grade", "") if manager else ""

        date_debut = _parse_date(m.get("dateDebut"))
        echeance = _parse_date(m.get("echeance"))

        duree_semaines = None
        if date_debut and echeance:
            duree_semaines = max(0, round((echeance - date_debut).days / 7))

        if m.get("statut") == "Terminée":
            statut = "Terminée"
        elif date_debut and today < date_debut:
            statut = "Pas encore commencée"
        else:
            statut = "En cours"

        progression = 0
        if statut == "Terminée":
            progression = 100
        elif date_debut and echeance and echeance > date_debut:
            total_days = (echeance - date_debut).days
            elapsed_days = (today - date_debut).days
            progression = round(max(0, min(100, elapsed_days / total_days * 100)))

        missions.append(
            {
                "id": str(m["_id"]),
                "client": client_name,
                "exercice": m.get("exercice", ""),
                "dateDebut": m.get("dateDebut", ""),
                "echeance": m.get("echeance", ""),
                "dureeSemaines": duree_semaines,
                "manager": m.get("manager", ""),
                "managerGrade": manager_grade,
                "statut": statut,
                "progression": progression,
                "phase": m.get("phase", ""),
                "phaseStep": _mission_step(m),
            }
        )

    missions.sort(key=lambda x: x["client"].lower())
    return missions


MISSION_STEP_LABELS = [
    "Ouverture et collecte",
    "Contrôle",
    "Organisation",
    "Revue par cycle",
    "Revue multi-niveaux",
    "Restitution client",
    "Archivage",
]


def _mission_step(doc):
    match = re.match(r"\s*(\d+)\s*/\s*7", doc.get("phase", ""))
    if match:
        step = int(match.group(1))
        if 1 <= step <= 7:
            return step
    return 1


def _next_phase_if_collecte_complete(current_phase, documents):
    """Advance from phase 1 (Ouverture et collecte) to phase 2 (Contrôle) once every
    requested document has been received. Returns the new phase string, or None if
    the mission isn't currently on phase 1 or the checklist isn't 100% complete."""
    if _mission_step({"phase": current_phase}) != 1:
        return None
    categories = documents.get("categories", [])
    total = sum(len(c.get("documents", [])) for c in categories)
    recus = sum(1 for c in categories for d in c.get("documents", []) if d.get("statut") == "Reçu")
    if total > 0 and recus == total:
        return f"2/7 · {MISSION_STEP_LABELS[1]}"
    return None


@app.get("/missions/phases")
def mission_phases(employee=Depends(get_current_employee)):
    counts = [0] * 7
    for m in db.missions.find():
        counts[_mission_step(m) - 1] += 1
    return [{"value": counts[i], "label": MISSION_STEP_LABELS[i]} for i in range(7)]


@app.get("/clients")
def list_clients(employee=Depends(get_current_employee)):
    clients = [serialize_client(c) for c in db.clients.find()]
    clients.sort(key=lambda c: c["raisonSociale"].lower())

    missions_by_client = {}
    for m in db.missions.find():
        missions_by_client.setdefault(m["clientId"], []).append(serialize_mission(m))
    for c in clients:
        c["missions"] = missions_by_client.get(c["id"], [])
        c["missionsEnCours"] = sum(1 for m in c["missions"] if m["statut"] == "En cours")

    return clients


@app.post("/clients", status_code=201)
def create_client(payload: ClientCreateRequest, employee=Depends(get_current_employee)):
    doc = payload.model_dump()
    doc["missionsEnCours"] = 0
    doc["missions"] = []
    result = db.clients.insert_one(doc)
    created = db.clients.find_one({"_id": result.inserted_id})
    return serialize_client(created)


@app.post("/missions", status_code=201)
def create_mission(payload: MissionCreateRequest, employee=Depends(get_current_employee)):
    try:
        client_object_id = ObjectId(payload.clientId)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Client invalide")
    if db.clients.find_one({"_id": client_object_id}) is None:
        raise HTTPException(status_code=404, detail="Client introuvable")

    doc = payload.model_dump()
    doc["createdBy"] = {
        "id": str(employee["_id"]),
        "nom": employee["nom"],
        "prenoms": employee["prenoms"],
    }
    doc["createdAt"] = datetime.now(timezone.utc)
    doc["documents"] = _default_documents()
    result = db.missions.insert_one(doc)
    created = db.missions.find_one({"_id": result.inserted_id})
    return serialize_mission(created)


@app.patch("/missions/{mission_id}/cloturer")
def close_mission(mission_id: str, payload: MissionCloseRequest, employee=Depends(get_current_employee)):
    try:
        mission_object_id = ObjectId(mission_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Mission invalide")
    if db.missions.find_one({"_id": mission_object_id}) is None:
        raise HTTPException(status_code=404, detail="Mission introuvable")

    date_fin = payload.dateFin or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if _parse_date(date_fin) is None:
        raise HTTPException(status_code=400, detail="Date de fin invalide")

    db.missions.update_one(
        {"_id": mission_object_id},
        {"$set": {"statut": "Terminée", "dateFinReelle": date_fin}},
    )
    updated = db.missions.find_one({"_id": mission_object_id})
    return serialize_mission(updated)


def _get_mission_or_404(mission_id):
    try:
        object_id = ObjectId(mission_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Mission invalide")
    mission = db.missions.find_one({"_id": object_id})
    if mission is None:
        raise HTTPException(status_code=404, detail="Mission introuvable")
    return object_id, mission


@app.get("/uploads/{mission_id}/{stored_name}")
def serve_upload(mission_id: str, stored_name: str):
    file_path = os.path.abspath(os.path.join(UPLOADS_DIR, mission_id, stored_name))
    if not file_path.startswith(UPLOADS_DIR + os.sep) or not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="Fichier introuvable")

    original_name = stored_name.split("_", 1)[1] if "_" in stored_name else stored_name
    mime_type, _ = mimetypes.guess_type(original_name)
    is_inline = mime_type in INLINE_MIME_TYPES or (mime_type or "").startswith("image/")

    return FileResponse(
        file_path,
        media_type=mime_type or "application/octet-stream",
        filename=original_name,
        content_disposition_type="inline" if is_inline else "attachment",
    )


@app.get("/missions/{mission_id}/documents")
def get_mission_documents(mission_id: str, employee=Depends(get_current_employee)):
    object_id, mission = _get_mission_or_404(mission_id)

    if "documents" not in mission:
        db.missions.update_one({"_id": object_id}, {"$set": {"documents": _default_documents()}})
        mission = db.missions.find_one({"_id": object_id})

    return serialize_documents(mission)


@app.post("/missions/{mission_id}/documents", status_code=201)
def add_mission_document(
    mission_id: str,
    categorie: str = Form(...),
    description: str = Form(...),
    version: str = Form("Electronique"),
    dateDemande: str = Form(""),
    statut: str = Form("En attente de livraison"),
    fichier: UploadFile | None = File(None),
    employee=Depends(get_current_employee),
):
    object_id, mission = _get_mission_or_404(mission_id)

    categorie = categorie.strip()
    description = description.strip()
    if not categorie or not description:
        raise HTTPException(status_code=400, detail="Catégorie et description requises")

    documents = mission.get("documents") or _default_documents()
    category = next((c for c in documents["categories"] if c["title"] == categorie), None)
    if category is None:
        category = {"title": categorie, "documents": []}
        documents["categories"].append(category)

    file_name = None
    file_url = None
    if fichier is not None and fichier.filename:
        mission_dir = os.path.join(UPLOADS_DIR, mission_id)
        os.makedirs(mission_dir, exist_ok=True)
        safe_name = os.path.basename(fichier.filename)
        stored_name = f"{uuid.uuid4().hex}_{safe_name}"
        with open(os.path.join(mission_dir, stored_name), "wb") as f:
            f.write(fichier.file.read())
        file_name = safe_name
        file_url = f"/uploads/{mission_id}/{stored_name}"

    document = {
        "id": uuid.uuid4().hex,
        "description": description,
        "version": version.strip() or "Electronique",
        "dateDemande": dateDemande.strip() or "—",
        "dateReception": datetime.now(timezone.utc).strftime("%Y-%m-%d") if statut == "Reçu" else "—",
        "statut": statut,
        "fileName": file_name,
        "fileUrl": file_url,
    }
    category["documents"].append(document)

    update_fields = {"documents": documents}
    next_phase = _next_phase_if_collecte_complete(mission.get("phase", ""), documents)
    if next_phase:
        update_fields["phase"] = next_phase

    db.missions.update_one({"_id": object_id}, {"$set": update_fields})
    updated = db.missions.find_one({"_id": object_id})
    return serialize_documents(updated)


@app.patch("/missions/{mission_id}/documents/{document_id}")
def update_mission_document(
    mission_id: str,
    document_id: str,
    payload: DocumentStatusUpdate,
    employee=Depends(get_current_employee),
):
    object_id, mission = _get_mission_or_404(mission_id)

    documents = mission.get("documents") or _default_documents()
    target = None
    for category in documents["categories"]:
        for d in category["documents"]:
            if d["id"] == document_id:
                target = d
                break
        if target:
            break
    if target is None:
        raise HTTPException(status_code=404, detail="Document introuvable")

    target["statut"] = payload.statut
    if payload.statut == "Reçu":
        target["dateReception"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    update_fields = {"documents": documents}
    next_phase = _next_phase_if_collecte_complete(mission.get("phase", ""), documents)
    if next_phase:
        update_fields["phase"] = next_phase

    db.missions.update_one({"_id": object_id}, {"$set": update_fields})
    updated = db.missions.find_one({"_id": object_id})
    return serialize_documents(updated)


def _detect_annee(*texts):
    for text in texts:
        match = re.search(r"(19|20)\d{2}", text or "")
        if match:
            return int(match.group(0))
    return None


def _balance_candidates(mission):
    documents = mission.get("documents") or _default_documents()
    candidates = []
    for category in documents.get("categories", []):
        for document in category.get("documents", []):
            if not document.get("fileUrl"):
                continue
            description = document.get("description", "")
            file_name = document.get("fileName", "")
            if not (re.search(r"balance", description, re.I) or re.search(r"balance", file_name, re.I)):
                continue
            candidates.append(
                {
                    "documentId": document["id"],
                    "description": description,
                    "fileName": file_name,
                    "fileUrl": document["fileUrl"],
                    "annee": _detect_annee(description, file_name),
                }
            )
    candidates.sort(key=lambda c: (c["annee"] is None, -(c["annee"] or 0)))
    return candidates


def _find_mission_document(mission, document_id):
    documents = mission.get("documents") or _default_documents()
    for category in documents.get("categories", []):
        for document in category.get("documents", []):
            if document.get("id") == document_id:
                return document
    return None


def _document_file_path(mission_id, document):
    stored_name = document["fileUrl"].rsplit("/", 1)[-1]
    return os.path.join(UPLOADS_DIR, mission_id, stored_name)


def _parse_balance_document(mission_id, mission, document_id, label):
    document = _find_mission_document(mission, document_id)
    if document is None or not document.get("fileUrl"):
        raise HTTPException(status_code=404, detail=f"Balance {label} introuvable")
    try:
        return parse_balance_file(_document_file_path(mission_id, document)), document
    except Exception:
        raise HTTPException(status_code=400, detail=f"Impossible de lire le fichier de la balance {label}")


@app.get("/missions/{mission_id}/balances")
def get_mission_balances(mission_id: str, employee=Depends(get_current_employee)):
    _, mission = _get_mission_or_404(mission_id)
    return {"balances": _balance_candidates(mission)}


@app.get("/missions/{mission_id}/controles/intangibilite")
def get_controle_intangibilite(
    mission_id: str,
    documentIdN: str | None = None,
    documentIdNMoins1: str | None = None,
    employee=Depends(get_current_employee),
):
    _, mission = _get_mission_or_404(mission_id)
    candidates = _balance_candidates(mission)

    if not documentIdN or not documentIdNMoins1:
        if len(candidates) < 2:
            raise HTTPException(status_code=404, detail="Balances N et N-1 introuvables pour cette mission")
        documentIdN = documentIdN or candidates[0]["documentId"]
        documentIdNMoins1 = documentIdNMoins1 or candidates[1]["documentId"]

    comptes_n, document_n = _parse_balance_document(mission_id, mission, documentIdN, "N")
    comptes_n_moins1, document_n_moins1 = _parse_balance_document(mission_id, mission, documentIdNMoins1, "N-1")

    resultat = compute_intangibilite(comptes_n, comptes_n_moins1)
    annee_n = _detect_annee(document_n.get("description", ""), document_n.get("fileName", ""))
    annee_n_moins1 = _detect_annee(document_n_moins1.get("description", ""), document_n_moins1.get("fileName", ""))
    resultat["periodeN"] = str(annee_n) if annee_n else document_n.get("description", "")
    resultat["periodeNMoins1"] = str(annee_n_moins1) if annee_n_moins1 else document_n_moins1.get("description", "")
    resultat["documentIdN"] = documentIdN
    resultat["documentIdNMoins1"] = documentIdNMoins1
    return resultat


@app.get("/missions/{mission_id}/controles/coherence")
def get_controle_coherence(
    mission_id: str,
    documentId: str | None = None,
    employee=Depends(get_current_employee),
):
    _, mission = _get_mission_or_404(mission_id)
    candidates = _balance_candidates(mission)

    if not documentId:
        if not candidates:
            raise HTTPException(status_code=404, detail="Aucune balance trouvée pour cette mission")
        documentId = candidates[0]["documentId"]

    comptes, document = _parse_balance_document(mission_id, mission, documentId, "sélectionnée")
    resultat = compute_coherence(comptes)
    annee = _detect_annee(document.get("description", ""), document.get("fileName", ""))
    resultat["annee"] = str(annee) if annee else document.get("description", "")
    resultat["documentId"] = documentId
    return resultat
