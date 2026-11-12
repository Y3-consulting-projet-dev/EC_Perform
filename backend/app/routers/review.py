from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.core.deps import get_current_employee
from app.models.revision import (
    ChecklistUpdate,
    Niveau,
    PointCreateRequest,
    PointStatutUpdate,
    RetourRequest,
)
from app.services import review_service

router = APIRouter(prefix="/missions/{mission_id}/cycles/{code}", tags=["revue"])


@router.patch("/revue/{niveau}/checklist")
def update_checklist(
    mission_id: str,
    code: str,
    niveau: Niveau,
    payload: ChecklistUpdate,
    employee=Depends(get_current_employee),
):
    return review_service.update_checklist(mission_id, code, niveau, payload.items, employee)


@router.post("/revue/{niveau}/valider")
def valider(mission_id: str, code: str, niveau: Niveau, employee=Depends(get_current_employee)):
    return review_service.valider(mission_id, code, niveau, employee)


@router.post("/revue/{niveau}/retour")
def retour(
    mission_id: str,
    code: str,
    niveau: Niveau,
    payload: RetourRequest,
    employee=Depends(get_current_employee),
):
    return review_service.retour(mission_id, code, niveau, payload.commentaire, employee)


@router.get("/points")
def list_points(mission_id: str, code: str, employee=Depends(get_current_employee)):
    return review_service.list_points(mission_id, code)


@router.post("/points", status_code=201)
def create_point(
    mission_id: str,
    code: str,
    payload: PointCreateRequest,
    employee=Depends(get_current_employee),
):
    return review_service.create_point(
        mission_id, code, payload.niveau, payload.corps, payload.cible.model_dump(), employee
    )


@router.post("/points/{point_id}/reponses", status_code=201)
def repondre(
    mission_id: str,
    code: str,
    point_id: str,
    texte: str = Form(""),
    ptRef: str = Form(""),
    fichiers: list[UploadFile] = File(default=[]),
    employee=Depends(get_current_employee),
):
    return review_service.repondre(mission_id, code, point_id, texte, ptRef, fichiers, employee)


@router.patch("/points/{point_id}")
def changer_statut_point(
    mission_id: str,
    code: str,
    point_id: str,
    payload: PointStatutUpdate,
    employee=Depends(get_current_employee),
):
    return review_service.changer_statut_point(mission_id, code, point_id, payload.statut, employee)
