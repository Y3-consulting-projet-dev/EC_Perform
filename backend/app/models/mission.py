from pydantic import BaseModel


class MissionCreateRequest(BaseModel):
    clientId: str
    exercice: str
    phase: str = "1/7 · Ouverture et collecte"
    statut: str = "En cours"
    rapport: str | None = None
    dateDebut: str
    echeance: str
    manager: str = ""
    senior: str = ""


class MissionCloseRequest(BaseModel):
    dateFin: str | None = None
