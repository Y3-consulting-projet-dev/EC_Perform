import os

# Base dédiée aux tests, vidée à chaque test : à définir avant tout import de l'application.
os.environ["MONGO_DB_NAME"] = "ec_perform_test"
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.db.session import client as mongo_client
from app.db.session import db
from app.main import app
from app.services import document_service

GRADES = {
    "assistant": "Assistant",
    "senior": "Senior",
    "manager": "Manager",
    "associe": "Associé",
}


@pytest.fixture
def api(tmp_path, monkeypatch):
    # Les fichiers déposés pendant les tests ne doivent pas polluer backend/uploads.
    monkeypatch.setattr(document_service, "UPLOADS_DIR", str(tmp_path))
    mongo_client.drop_database(db.name)
    with TestClient(app) as test_client:
        yield test_client
    mongo_client.drop_database(db.name)


@pytest.fixture
def employees(api):
    created = {}
    for key, grade in GRADES.items():
        email = f"{key}@test.ci"
        result = db.employees.insert_one(
            {"nom": key.upper(), "prenoms": key.capitalize(), "grade": grade, "email": email, "password_hash": "x"}
        )
        created[key] = {"id": str(result.inserted_id), "headers": {"Authorization": f"Bearer {create_access_token(email)}"}}
    return created


@pytest.fixture
def mission(employees):
    client_id = db.clients.insert_one({"raisonSociale": "SAVEDO SA"}).inserted_id
    result = db.missions.insert_one(
        {
            "clientId": str(client_id),
            "exercice": "2025",
            "phase": "3/7 · Organisation",
            "statut": "En cours",
            "senior": "Senior SENIOR",
            "manager": "Manager MANAGER",
            "cycleAssignments": {"C": {"risque": "Élevé", "assigneA": employees["assistant"]["id"], "delai": None}},
        }
    )
    return str(result.inserted_id)
