from fastapi import APIRouter, Depends

from app.core.deps import get_current_employee
from app.models.employee import UpdateProfileRequest
from app.services import employee_service

router = APIRouter(tags=["employees"])


@router.patch("/employees/me")
def update_profile(payload: UpdateProfileRequest, employee=Depends(get_current_employee)):
    updated = employee_service.update_profile(employee, payload.nom, payload.prenoms)
    return employee_service.serialize_employee_summary(updated)


@router.get("/employees")
def list_employees(employee=Depends(get_current_employee)):
    return employee_service.list_employees()
