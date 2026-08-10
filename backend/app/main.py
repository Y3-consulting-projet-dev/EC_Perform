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


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    try:
        email = decode_access_token(credentials.credentials)
    except Exception:
        raise HTTPException(status_code=401, detail="Session invalide ou expirée")
    user = db.users.find_one({"email": email})
    if user is None:
        raise HTTPException(status_code=401, detail="Utilisateur introuvable")
    return user


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
    user = db.users.find_one({"email": payload.email.strip().lower()})
    if user is None or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")
    token = create_access_token(user["email"])
    return {
        "access_token": token,
        "token_type": "bearer",
        "must_change_password": user.get("must_change_password", False),
        "employee": {
            "nom": user["nom"],
            "prenoms": user["prenoms"],
            "grade": user["grade"],
            "departement": user["departement"],
            "email": user["email"],
        },
    }


@app.post("/auth/change-password")
def change_password(payload: ChangePasswordRequest, user=Depends(get_current_user)):
    if not verify_password(payload.current_password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Mot de passe actuel incorrect")
    db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {"password_hash": hash_password(payload.new_password), "must_change_password": False}},
    )
    return {"status": "ok"}


@app.patch("/users/me")
def update_profile(payload: UpdateProfileRequest, user=Depends(get_current_user)):
    db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {"nom": payload.nom.strip(), "prenoms": payload.prenoms.strip()}},
    )
    updated = db.users.find_one({"_id": user["_id"]})
    return {
        "nom": updated["nom"],
        "prenoms": updated["prenoms"],
        "grade": updated["grade"],
        "departement": updated["departement"],
        "email": updated["email"],
    }
