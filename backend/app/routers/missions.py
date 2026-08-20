from fastapi import APIRouter, Depends

from app.core.deps import get_current_employee
from app.models.mission import MissionCloseRequest, MissionCreateRequest
from app.services import mission_service

router = APIRouter(prefix="/missions", tags=["missions"])


@router.get("/stats")
def mission_stats(employee=Depends(get_current_employee)):
    return mission_service.get_stats()


@router.get("/phases")
def mission_phases(employee=Depends(get_current_employee)):
    return mission_service.get_phases()


@router.get("")
def list_missions(employee=Depends(get_current_employee)):
    return mission_service.list_missions()


@router.post("", status_code=201)
def create_mission(payload: MissionCreateRequest, employee=Depends(get_current_employee)):
    return mission_service.create_mission(payload.model_dump(), employee)


@router.patch("/{mission_id}/cloturer")
def close_mission(mission_id: str, payload: MissionCloseRequest, employee=Depends(get_current_employee)):
    return mission_service.close_mission(mission_id, payload.dateFin)
