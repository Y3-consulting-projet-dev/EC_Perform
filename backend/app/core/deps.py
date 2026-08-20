from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

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
