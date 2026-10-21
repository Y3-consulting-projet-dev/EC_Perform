import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pymongo.errors import PyMongoError

from app.db.indexes import create_indexes
from app.db.session import db
from app.routers import (
    auth,
    balances,
    clients,
    cycles,
    documents,
    employees,
    missions,
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(employees.router)
app.include_router(clients.router)
app.include_router(missions.router)
app.include_router(documents.router)
app.include_router(balances.router)
app.include_router(cycles.router)
app.include_router(revision.router)
app.include_router(review.router)
app.include_router(working_papers.router)


@app.get("/health")
def health():
    server_info = db.client.server_info()
    return {"status": "ok", "database": db.name, "mongo_version": server_info["version"]}
