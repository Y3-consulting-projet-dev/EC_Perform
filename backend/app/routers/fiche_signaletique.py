from fastapi import APIRouter, Depends, File, UploadFile

from app.core.deps import get_current_employee
from app.models.mission import FicheSignaletiqueUpdate
from app.services import fiche_signaletique_service

router = APIRouter(prefix="/missions/{mission_id}/fiche-signaletique", tags=["fiche signalétique"])


@router.get("")
def get_fiche(mission_id: str, employee=Depends(get_current_employee)):
    return fiche_signaletique_service.get_fiche(mission_id)


@router.put("")
def update_fiche(mission_id: str, payload: FicheSignaletiqueUpdate, employee=Depends(get_current_employee)):
    return fiche_signaletique_service.update_fiche(mission_id, payload.valeurs, employee)


@router.post("/fichier")
def importer_fiche(mission_id: str, fichier: UploadFile = File(...), employee=Depends(get_current_employee)):
    return fiche_signaletique_service.importer_fichier(mission_id, fichier, employee)


@router.get("/export")
def exporter_fiche(mission_id: str, employee=Depends(get_current_employee)):
    return fiche_signaletique_service.exporter_docx(mission_id)
