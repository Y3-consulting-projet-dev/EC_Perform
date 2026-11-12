from fastapi import APIRouter, Depends, File, UploadFile

from app.core.deps import get_current_employee
from app.models.rapport import SaisieUpdate
from app.services import onlyoffice_service, rapport_service, restitution_service

router = APIRouter(prefix="/missions/{mission_id}", tags=["rapport final"])


# --- Rapport final ----------------------------------------------------------------------------


@router.get("/rapport")
def get_rapport(mission_id: str, employee=Depends(get_current_employee)):
    return rapport_service.get_rapport(mission_id, employee)


@router.post("/rapport/generer")
def generer(mission_id: str, force: bool = False, employee=Depends(get_current_employee)):
    return rapport_service.generer(mission_id, employee, force)


@router.get("/rapport/versions/{numero}/fichier")
def telecharger(mission_id: str, numero: int, employee=Depends(get_current_employee)):
    return rapport_service.telecharger(mission_id, numero, employee)


@router.get("/rapport/editeur")
def config_editeur(mission_id: str, employee=Depends(get_current_employee)):
    return onlyoffice_service.config_editeur(mission_id, employee)


@router.post("/rapport/emettre")
def emettre(mission_id: str, employee=Depends(get_current_employee)):
    return rapport_service.emettre(mission_id, employee, onlyoffice_service.convertir_pdf)


@router.post("/rapport/pdf")
def relancer_pdf(mission_id: str, employee=Depends(get_current_employee)):
    return rapport_service.relancer_pdf(mission_id, employee, onlyoffice_service.convertir_pdf)


@router.get("/rapport/pdf")
def telecharger_pdf(mission_id: str, employee=Depends(get_current_employee)):
    return rapport_service.telecharger_pdf(mission_id, employee)


@router.get("/rapport/saisie")
def get_saisie(mission_id: str, employee=Depends(get_current_employee)):
    return rapport_service.get_saisie(mission_id, employee)


@router.put("/rapport/saisie")
def update_saisie(mission_id: str, payload: SaisieUpdate, employee=Depends(get_current_employee)):
    return rapport_service.update_saisie(mission_id, payload.saisie.model_dump(), payload.version, employee)


@router.post("/rapport/medias/{cle}")
def deposer_media(mission_id: str, cle: str, fichier: UploadFile = File(...), employee=Depends(get_current_employee)):
    return rapport_service.deposer_media(mission_id, cle, fichier, employee)


@router.delete("/rapport/medias/{cle}")
def supprimer_media(mission_id: str, cle: str, employee=Depends(get_current_employee)):
    return rapport_service.supprimer_media(mission_id, cle, employee)


@router.get("/rapport/medias/{cle}")
def lire_media(mission_id: str, cle: str, employee=Depends(get_current_employee)):
    return rapport_service.lire_media(mission_id, cle)


# --- Restitution client -----------------------------------------------------------------------


@router.get("/restitution")
def get_restitution(mission_id: str, employee=Depends(get_current_employee)):
    return restitution_service.get_restitution(mission_id, employee)


@router.put("/restitution")
def update_restitution(mission_id: str, payload: dict, employee=Depends(get_current_employee)):
    return restitution_service.update_restitution(mission_id, payload, employee)
