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
