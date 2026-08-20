from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.core.deps import get_current_employee
from app.models.document import DocumentStatusUpdate
from app.services import document_service

router = APIRouter(tags=["documents"])


@router.get("/uploads/{mission_id}/{stored_name}")
def serve_upload(mission_id: str, stored_name: str):
    return document_service.get_upload_response(mission_id, stored_name)


@router.get("/missions/{mission_id}/documents")
def get_mission_documents(mission_id: str, employee=Depends(get_current_employee)):
    return document_service.get_mission_documents(mission_id)


@router.post("/missions/{mission_id}/documents", status_code=201)
def add_mission_document(
    mission_id: str,
    categorie: str = Form(...),
    description: str = Form(...),
    version: str = Form("Electronique"),
    dateDemande: str = Form(""),
    statut: str = Form("En attente de livraison"),
    fichier: UploadFile | None = File(None),
    employee=Depends(get_current_employee),
):
    return document_service.add_mission_document(
        mission_id, categorie, description, version, dateDemande, statut, fichier
    )


@router.patch("/missions/{mission_id}/documents/{document_id}")
def update_mission_document(
    mission_id: str,
    document_id: str,
    payload: DocumentStatusUpdate,
    employee=Depends(get_current_employee),
):
    return document_service.update_mission_document(mission_id, document_id, payload.statut)
