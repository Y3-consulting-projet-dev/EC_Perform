from fastapi import APIRouter, Depends

from app.core.deps import get_current_employee
from app.models.client import ClientCreateRequest, ClientUpdateRequest
from app.services import client_service

router = APIRouter(prefix="/clients", tags=["clients"])


@router.get("/stats")
def client_stats(employee=Depends(get_current_employee)):
    return client_service.get_stats()


@router.get("")
def list_clients(employee=Depends(get_current_employee)):
    return client_service.list_clients()


@router.post("", status_code=201)
def create_client(payload: ClientCreateRequest, employee=Depends(get_current_employee)):
    return client_service.create_client(payload.model_dump())


@router.patch("/{client_id}")
def update_client(client_id: str, payload: ClientUpdateRequest, employee=Depends(get_current_employee)):
    return client_service.update_client(client_id, payload.model_dump())
