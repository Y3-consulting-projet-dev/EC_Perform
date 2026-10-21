from typing import Literal

from pydantic import BaseModel, Field

Etape = Literal["4a", "4b", "4c", "4d", "4e", "4f"]
Niveau = Literal["senior", "manager", "associe"]
Section = Literal["priseConnaissance", "lead", "justification", "constats", "conclusion"]


# --- Phase 4 : sections du cycle -------------------------------------------------------


class PriseConnaissanceData(BaseModel):
    processus: str = ""
    risques: list[str] = Field(default_factory=list)
    referentiel: str = ""


class LeadData(BaseModel):
    # Commentaire par numéro de compte, dans le tableau de rapprochement.
    commentaires: dict[str, str] = Field(default_factory=dict)


class PieceProbante(BaseModel):
    id: str | None = None
    libelle: str
    source: str = ""
    statut: Literal["Reçue", "En attente", "Manquante"] = "En attente"
    fileName: str | None = None
    fileUrl: str | None = None
    # Papier de travail exporté et rattaché comme pièce (ex. "4d").
    ptEtape: str | None = None


class JustificationData(BaseModel):
    # Clé d'assertion -> cochée ou non. L'horodatage est posé côté serveur.
    assertions: dict[str, bool] = Field(default_factory=dict)
    pieces: list[PieceProbante] = Field(default_factory=list)
    commentaire: str = ""


class Constat(BaseModel):
    id: str | None = None
    famille: Literal["Comptabilisation", "Évaluation", "Présentation", "Gouvernance", "Système d'information"]
    constat: str
    severite: Literal["Faible", "Moyen", "Élevé"] = "Moyen"
    recommandation: str = ""
    statut: Literal["Ouvert", "Noté", "Clôturé"] = "Ouvert"


class ConstatsData(BaseModel):
    constats: list[Constat] = Field(default_factory=list)


class Ajustement(BaseModel):
    id: str | None = None
    compte: str
    libelle: str = ""
    sens: Literal["Débit", "Crédit"]
    montant: float


class ConclusionData(BaseModel):
    synthese: str = ""
    ajustements: list[Ajustement] = Field(default_factory=list)
    decision: Literal["justifie", "completer"] | None = None


class RevisionSectionUpdate(BaseModel):
    section: Section
    data: dict
    version: int


# --- Phase 5 : revue multi-niveaux -------------------------------------------------------


class ChecklistUpdate(BaseModel):
    items: dict[str, bool]


class RetourRequest(BaseModel):
    commentaire: str = ""


class CiblePoint(BaseModel):
    etape: Etape
    ptEtape: str | None = None
    onglet: str | None = None
    cellule: str | None = None


class PointCreateRequest(BaseModel):
    niveau: Niveau
    corps: str
    cible: CiblePoint


class PointStatutUpdate(BaseModel):
    statut: Literal["ouvert", "cleared"]


# --- Papiers de travail ------------------------------------------------------------------


class Feuille(BaseModel):
    nom: str
    colonnes: list[str] = Field(default_factory=list)
    data: list[list[str | float | int | None]] = Field(default_factory=list)


class LienExcel(BaseModel):
    provider: Literal["onedrive", "sharepoint", "google", "autre"] = "onedrive"
    webUrl: str = ""
    chemin: str = ""


class PapierUpdateRequest(BaseModel):
    version: int
    titre: str | None = None
    mode: Literal["lien", "integre"] | None = None
    lien: LienExcel | None = None
    feuilles: list[Feuille] | None = None
