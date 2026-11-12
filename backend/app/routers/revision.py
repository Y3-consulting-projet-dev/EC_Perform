from fastapi import APIRouter, Depends, File, UploadFile

from app.core.deps import get_current_employee
from app.models.revision import RevisionSectionUpdate
from app.services import revision_service

router = APIRouter(prefix="/missions/{mission_id}", tags=["revision"])


@router.get("/revisions")
def get_mission_revisions(mission_id: str, employee=Depends(get_current_employee)):
    return revision_service.get_mission_revisions(mission_id)


@router.get("/cycles/{code}/revision")
def get_revision(mission_id: str, code: str, employee=Depends(get_current_employee)):
    return revision_service.get_revision(mission_id, code, employee)


@router.patch("/cycles/{code}/revision")
def update_revision_section(
    mission_id: str,
    code: str,
    payload: RevisionSectionUpdate,
    employee=Depends(get_current_employee),
):
    return revision_service.update_section(
        mission_id, code, payload.section, payload.data, payload.version, employee
    )


@router.post("/cycles/{code}/revision/pieces", status_code=201)
def deposer_piece(
    mission_id: str,
    code: str,
    fichier: UploadFile = File(...),
    employee=Depends(get_current_employee),
):
    return revision_service.deposer_piece(mission_id, code, fichier, employee)


@router.post("/cycles/{code}/revision/soumettre")
def soumettre_revision(mission_id: str, code: str, employee=Depends(get_current_employee)):
    return revision_service.soumettre(mission_id, code, employee)
