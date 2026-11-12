"""Routes appelées par le Document Server ONLYOFFICE (serveur à serveur, sans jeton bearer
utilisateur) : authentifiées par un jeton signé par l'API dans l'URL, et — pour le callback —
par le JWT du Document Server."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from app.services import onlyoffice_service

router = APIRouter(prefix="/onlyoffice", tags=["onlyoffice"])


@router.get("/fichier/{rapport_id}/{numero}")
def fichier(rapport_id: str, numero: int, jeton: str):
    return onlyoffice_service.fichier(rapport_id, numero, jeton)


@router.post("/callback/{rapport_id}")
async def callback(rapport_id: str, jeton: str, request: Request):
    try:
        corps = await request.json()
    except ValueError:
        return JSONResponse({"error": 1}, status_code=400)
    # Traitement synchrone (pymongo, httpx) hors de la boucle d'événements.
    resultat = await run_in_threadpool(onlyoffice_service.callback, rapport_id, jeton, corps, dict(request.headers))
    return resultat
