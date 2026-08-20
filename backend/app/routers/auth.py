from fastapi import APIRouter, Depends, HTTPException

from app.core.deps import get_current_employee
from app.core.security import create_access_token
from app.models.auth import ChangePasswordRequest, LoginRequest
from app.services import employee_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
def login(payload: LoginRequest):
    employee = employee_service.authenticate(payload.email, payload.password)
    if employee is None:
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")
    token = create_access_token(employee["email"])
    return {
        "access_token": token,
        "token_type": "bearer",
        "must_change_password": employee.get("must_change_password", False),
        "employee": employee_service.serialize_employee_summary(employee),
    }


@router.post("/change-password")
def change_password(payload: ChangePasswordRequest, employee=Depends(get_current_employee)):
    ok = employee_service.change_password(employee, payload.current_password, payload.new_password)
    if not ok:
        raise HTTPException(status_code=401, detail="Mot de passe actuel incorrect")
    return {"status": "ok"}
