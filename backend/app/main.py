import logging
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pymongo.errors import PyMongoError

from app.core.deps import require_mission_access
from app.db.indexes import create_indexes
from app.db.session import db
from app.routers import (
    auth,
    balances,
    clients,
    cycles,
    documents,
    employees,
    fiche_signaletique,
    missions,
    onlyoffice,
    rapports,
    review,
    revision,
    working_papers,
)


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Mongo indisponible au démarrage : l'API démarre quand même (comme avant l'ajout des index),
    # /health signale le problème et les index seront créés au prochain démarrage.
    try:
        create_indexes()
    except PyMongoError as exc:
        logger.warning("Index Mongo non créés (base injoignable) : %s", exc)
    yield


app = FastAPI(title="Ec-perform API", lifespan=lifespan)

# Origines autorisées : CORS_ORIGIN_REGEX (.env) ; par défaut le frontend sur le port 5173 (dev)
# ou 4173 (preview), servi en localhost ou depuis une adresse de réseau privé (accès depuis une
# autre machine du réseau local). L'authentification passe par un bearer token, pas de cookie.
CORS_ORIGIN_REGEX = os.getenv(
    "CORS_ORIGIN_REGEX",
    r"^http://(localhost|127\.0\.0\.1|10(\.\d{1,3}){3}|192\.168(\.\d{1,3}){2}"
    r"|172\.(1[6-9]|2\d|3[01])(\.\d{1,3}){2}|[A-Za-z0-9-]+(\.local)?):(5173|4173)$",
)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=CORS_ORIGIN_REGEX,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(employees.router)
app.include_router(clients.router)
app.include_router(missions.router)
app.include_router(documents.router)
app.include_router(onlyoffice.router)

# Routes d'une mission (/missions/{mission_id}/...) : réservées aux collaborateurs de la mission.
for mission_router in (
    fiche_signaletique.router,
    balances.router,
    cycles.router,
    revision.router,
    review.router,
    working_papers.router,
    rapports.router,
):
    app.include_router(mission_router, dependencies=[Depends(require_mission_access)])


@app.get("/health")
def health():
    server_info = db.client.server_info()
    return {"status": "ok", "database": db.name, "mongo_version": server_info["version"]}
