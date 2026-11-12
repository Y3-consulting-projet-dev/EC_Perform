from fastapi import APIRouter, Depends

from app.core.deps import get_current_employee
from app.services import balance_service

router = APIRouter(prefix="/missions/{mission_id}", tags=["balances"])


@router.get("/balances")
def get_mission_balances(mission_id: str, employee=Depends(get_current_employee)):
    return balance_service.get_mission_balances(mission_id)


@router.get("/controles/intangibilite")
def get_controle_intangibilite(
    mission_id: str,
    documentIdN: str | None = None,
    documentIdNMoins1: str | None = None,
    employee=Depends(get_current_employee),
):
    return balance_service.get_controle_intangibilite(mission_id, documentIdN, documentIdNMoins1)


@router.get("/controles/coherence")
def get_controle_coherence(
    mission_id: str,
    documentId: str | None = None,
    employee=Depends(get_current_employee),
):
    return balance_service.get_controle_coherence(mission_id, documentId)
