import re
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException

from app.db.session import db

DEFAULT_DOCUMENT_CATEGORIES = [
    "DOCUMENT GENERAUX DE LA SOCIETE",
    "OPERATIONS DE TRESORERIE",
    "ACHATS ET VENTES/PRESTATIONS",
    "GESTION DE LA PAIE",
    "CADRE FISCALE ET SOCIALE",
]

DOCUMENT_STATUTS_TRAITES = ("Reçu", "Non applicable")

MISSION_STEP_LABELS = [
    "Ouverture et collecte",
    "Contrôle",
    "Organisation",
    "Revue par cycle",
    "Revue multi-niveaux",
    "Restitution client",
    "Archivage",
]


def default_documents():
    return {"categories": [{"title": title, "documents": []} for title in DEFAULT_DOCUMENT_CATEGORIES]}


def parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def mission_step(doc):
    match = re.match(r"\s*(\d+)\s*/\s*7", doc.get("phase", ""))
    if match:
        step = int(match.group(1))
        if 1 <= step <= 7:
            return step
    return 1


def next_phase_if_collecte_complete(current_phase, documents):
    """Advance from phase 1 (Ouverture et collecte) to phase 2 (Contrôle) once every
    requested document has been received or marked non applicable. Returns the new phase
    string, or None if the mission isn't currently on phase 1 or the checklist isn't 100%
    complete."""
    if mission_step({"phase": current_phase}) != 1:
        return None
    categories = documents.get("categories", [])
    total = sum(len(c.get("documents", [])) for c in categories)
    traites = sum(
        1 for c in categories for d in c.get("documents", []) if d.get("statut") in DOCUMENT_STATUTS_TRAITES
    )
    if total > 0 and traites == total:
        return f"2/7 · {MISSION_STEP_LABELS[1]}"
    return None


def serialize_mission(doc):
    created_at = doc.get("createdAt")
    return {
        "id": str(doc["_id"]),
        "clientId": doc["clientId"],
        "exercice": doc.get("exercice", ""),
        "phase": doc.get("phase", ""),
        "phaseStep": mission_step(doc),
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


def get_mission_or_404(mission_id):
    try:
        object_id = ObjectId(mission_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Mission invalide")
    mission = db.missions.find_one({"_id": object_id})
    if mission is None:
        raise HTTPException(status_code=404, detail="Mission introuvable")
    return object_id, mission


def get_stats():
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
        date_fin = parse_date(m.get("dateFinReelle"))
        if date_fin and date_fin.year == now.year:
            terminees_cette_annee.append(m)

    total_terminees = len(terminees_cette_annee)
    dans_les_delais = sum(
        1
        for m in terminees_cette_annee
        if (echeance := parse_date(m.get("echeance")))
        and (date_fin := parse_date(m.get("dateFinReelle")))
        and date_fin <= echeance
    )
    pourcentage_dans_les_delais = round(dans_les_delais / total_terminees * 100) if total_terminees else None

    return {
        "enCours": en_cours,
        "deltaVsLastMonth": this_month - last_month,
        "terminees": total_terminees,
        "annee": now.year,
        "pourcentageDansLesDelais": pourcentage_dans_les_delais,
    }


def list_missions():
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

        date_debut = parse_date(m.get("dateDebut"))
        echeance = parse_date(m.get("echeance"))

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
                "phaseStep": mission_step(m),
            }
        )

    missions.sort(key=lambda x: x["client"].lower())
    return missions


def get_phases():
    counts = [0] * 7
    for m in db.missions.find():
        counts[mission_step(m) - 1] += 1
    return [{"value": counts[i], "label": MISSION_STEP_LABELS[i]} for i in range(7)]


def create_mission(payload_dict, employee):
    try:
        client_object_id = ObjectId(payload_dict["clientId"])
    except InvalidId:
        raise HTTPException(status_code=400, detail="Client invalide")
    if db.clients.find_one({"_id": client_object_id}) is None:
        raise HTTPException(status_code=404, detail="Client introuvable")

    doc = dict(payload_dict)
    doc["createdBy"] = {
        "id": str(employee["_id"]),
        "nom": employee["nom"],
        "prenoms": employee["prenoms"],
    }
    doc["createdAt"] = datetime.now(timezone.utc)
    doc["documents"] = default_documents()
    result = db.missions.insert_one(doc)
    created = db.missions.find_one({"_id": result.inserted_id})
    return serialize_mission(created)


def close_mission(mission_id, date_fin):
    object_id, mission = get_mission_or_404(mission_id)

    date_fin = date_fin or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if parse_date(date_fin) is None:
        raise HTTPException(status_code=400, detail="Date de fin invalide")

    db.missions.update_one(
        {"_id": object_id},
        {"$set": {"statut": "Terminée", "dateFinReelle": date_fin}},
    )
    updated = db.missions.find_one({"_id": object_id})
    return serialize_mission(updated)
