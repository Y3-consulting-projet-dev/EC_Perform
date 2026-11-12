from pydantic import BaseModel


class MissionCreateRequest(BaseModel):
    clientId: str
    exercice: str
    phase: str = "1/7 · Ouverture et collecte"
    statut: str = "En cours"
    rapport: str | None = None
    dateDebut: str
    echeance: str
    # Plusieurs managers / seniors peuvent intervenir sur une mission (noms complets).
    managers: list[str] = []
    seniors: list[str] = []
    # Ancien format (un seul nom), encore accepté.
    manager: str = ""
    senior: str = ""


class MissionCloseRequest(BaseModel):
    dateFin: str | None = None


class FicheSignaletiqueUpdate(BaseModel):
    valeurs: dict[str, str]
