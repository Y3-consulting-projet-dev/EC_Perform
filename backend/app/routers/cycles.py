from fastapi import APIRouter, Depends

from app.core.deps import get_current_employee
from app.models.repartition import EquipeUpdateRequest, RepartitionUpdateRequest
from app.services import cycle_service, repartition_service

router = APIRouter(prefix="/missions/{mission_id}", tags=["cycles"])


@router.get("/cycles")
def get_mission_cycles(
    mission_id: str,
    documentIdN: str | None = None,
    documentIdNMoins1: str | None = None,
    employee=Depends(get_current_employee),
):
    return cycle_service.get_mission_cycles(mission_id, documentIdN, documentIdNMoins1)


@router.get("/cycles/{code}")
def get_mission_cycle_detail(
    mission_id: str,
    code: str,
    documentIdN: str | None = None,
    documentIdNMoins1: str | None = None,
    employee=Depends(get_current_employee),
):
    return cycle_service.get_mission_cycle_detail(mission_id, code, documentIdN, documentIdNMoins1)


@router.get("/repartition")
def get_repartition(mission_id: str, employee=Depends(get_current_employee)):
    return repartition_service.get_repartition(mission_id)


@router.patch("/repartition/{code}")
def update_repartition(
    mission_id: str,
    code: str,
    payload: RepartitionUpdateRequest,
    employee=Depends(get_current_employee),
):
    return repartition_service.update_repartition(
        mission_id, code, payload.risque, payload.assigneA, payload.delai, employee
    )


@router.get("/equipe")
def get_equipe(mission_id: str, employee=Depends(get_current_employee)):
    return repartition_service.get_equipe(mission_id)


@router.put("/equipe")
def set_equipe(mission_id: str, payload: EquipeUpdateRequest, employee=Depends(get_current_employee)):
    return repartition_service.set_equipe(mission_id, payload.employeeIds, employee)
