from bson import ObjectId
from bson.errors import InvalidId
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.permissions import peut_ouvrir_mission
from app.core.security import decode_access_token
from app.db.session import db

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


def require_mission_access(mission_id: str, employee=Depends(get_current_employee)):
    """Toute route /missions/{mission_id}/... : réservée aux collaborateurs de la mission."""
    try:
        object_id = ObjectId(mission_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Mission invalide")
    mission = db.missions.find_one({"_id": object_id})
    if mission is None:
        raise HTTPException(status_code=404, detail="Mission introuvable")
    if not peut_ouvrir_mission(employee, mission):
        raise HTTPException(status_code=403, detail="Vous n'êtes pas affecté à cette mission.")
    return employee
