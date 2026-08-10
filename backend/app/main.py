from datetime import datetime, timedelta, timezone

from bson import ObjectId
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from app.auth import create_access_token, decode_access_token, hash_password, verify_password
from app.db import db

app = FastAPI(title="Ec-perform API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

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


@app.get("/clients")
def list_clients(employee=Depends(get_current_employee)):
    clients = [serialize_client(c) for c in db.clients.find()]
    clients.sort(key=lambda c: c["raisonSociale"].lower())
    return clients


@app.post("/clients", status_code=201)
def create_client(payload: ClientCreateRequest, employee=Depends(get_current_employee)):
    doc = payload.model_dump()
    doc["missionsEnCours"] = 0
    doc["missions"] = []
    result = db.clients.insert_one(doc)
    created = db.clients.find_one({"_id": result.inserted_id})
    return serialize_client(created)
