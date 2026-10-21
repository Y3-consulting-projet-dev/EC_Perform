from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.core.deps import get_current_employee
from app.models.revision import PapierUpdateRequest
from app.services import working_paper_service

router = APIRouter(prefix="/missions/{mission_id}/cycles/{code}/papiers", tags=["papiers de travail"])


@router.get("/{etape}")
def get_papier(mission_id: str, code: str, etape: str, employee=Depends(get_current_employee)):
    return working_paper_service.get_papier(mission_id, code, etape)


@router.patch("/{etape}")
def update_papier(
    mission_id: str,
    code: str,
    etape: str,
    payload: PapierUpdateRequest,
    employee=Depends(get_current_employee),
):
    return working_paper_service.update_papier(mission_id, code, etape, payload, employee)


@router.get("/{etape}/versions")
def list_versions(mission_id: str, code: str, etape: str, employee=Depends(get_current_employee)):
    return working_paper_service.list_versions(mission_id, code, etape)


@router.post("/{etape}/export")
def exporter_papier(mission_id: str, code: str, etape: str, employee=Depends(get_current_employee)):
    return working_paper_service.exporter_papier(mission_id, code, etape)


@router.post("/{etape}/fichier")
def importer_fichier_lie(
    mission_id: str,
    code: str,
    etape: str,
    version: int = Form(...),
    fichier: UploadFile = File(...),
    employee=Depends(get_current_employee),
):
    return working_paper_service.importer_fichier_lie(mission_id, code, etape, version, fichier, employee)
