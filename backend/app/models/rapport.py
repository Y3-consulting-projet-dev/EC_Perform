from typing import Literal

from pydantic import BaseModel, Field, field_validator

# --- Phase 6 : saisie complémentaire du rapport final ---------------------------------------
# Tout ce que le rapport contient sans source dans les phases 1 à 5. Les éléments rattachés à
# des objets existants le sont par leur id (constat, ajustement, papier de travail) : les
# modèles des phases 1 à 5 ne sont pas modifiés.


class LettreMission(BaseModel):
    date: str = ""
    prestations: str = ""


class Evenement(BaseModel):
    id: str | None = None
    titre: str = ""
    texte: str = ""


class ConstatSaisie(BaseModel):
    """Compléments d'un constat de la Phase 4 (indexé par son id dans `saisie.constats`)."""

    titre: str = ""
    risques: list[str] = Field(default_factory=list)
    # None : choix par défaut (familles Gouvernance et Système d'information retenues).
    retenirCI: bool | None = None


class LigneGrandLivre(BaseModel):
    date: str = ""
    journal: str = ""
    piece: str = ""
    compte: str = ""
    compteTiers: str = ""
    libelle: str = ""
    debit: float | None = None
    credit: float | None = None


class FiltreGrandLivre(BaseModel):
    comptes: list[str] = Field(default_factory=list)  # préfixes de comptes
    du: str = ""
    au: str = ""


class GrandLivre(BaseModel):
    """Extrait du grand livre. V1 : lignes saisies ou collées depuis Excel (source « saisie »).
    Prévu pour un import ultérieur du grand livre (source « import ») : les lignes seront alors
    extraites du grand livre importé selon `filtre`, avec la même structure de ligne."""

    source: Literal["saisie", "import"] = "saisie"
    filtre: FiltreGrandLivre = Field(default_factory=FiltreGrandLivre)
    lignes: list[LigneGrandLivre] = Field(default_factory=list)


class Bloc(BaseModel):
    id: str | None = None
    type: Literal["balance", "variation", "tableau", "grand_livre", "papier", "ecriture"]
    titre: str = ""
    prefixes: list[str] = Field(default_factory=list)  # balance / variation (vide = tout le cycle)
    colonnes: list[str] = Field(default_factory=list)  # tableau
    lignes: list[list[str]] = Field(default_factory=list)  # tableau
    grandLivre: GrandLivre | None = None  # grand_livre
    paperId: str | None = None  # papier
    feuille: str | None = None  # papier
    ecritureId: str | None = None  # ecriture


class Point(BaseModel):
    id: str | None = None
    titre: str
    texte: str = ""
    blocs: list[Bloc] = Field(default_factory=list)

    @field_validator("titre")
    @classmethod
    def titre_requis(cls, v):
        if not v.strip():
            raise ValueError("Le titre du point est requis")
        return v.strip()


class Ecriture(BaseModel):
    """Écriture proposée : regroupement d'ajustements (lignes) de la Phase 4, équilibré."""

    id: str | None = None
    cycleCode: str
    libelle: str = ""
    ajustementIds: list[str] = Field(default_factory=list)


class SaisieRapport(BaseModel):
    dateRapport: str = ""  # AAAA-MM ; vide = mois de génération
    lettreMission: LettreMission = Field(default_factory=LettreMission)
    contexteComplement: str = ""
    actionnariat: str = ""
    evenements: list[Evenement] = Field(default_factory=list)
    intangibiliteCommentaire: str = ""
    constats: dict[str, ConstatSaisie] = Field(default_factory=dict)
    points: dict[str, list[Point]] = Field(default_factory=dict)  # par code cycle
    ecritures: list[Ecriture] = Field(default_factory=list)


class SaisieUpdate(BaseModel):
    saisie: SaisieRapport
    version: int


# --- Phase 6 : restitution client -----------------------------------------------------------


class ParticipantClient(BaseModel):
    nom: str = ""
    fonction: str = ""


class Reunion(BaseModel):
    date: str = ""  # AAAA-MM-JJ
    lieu: str = ""
    participantsCabinet: list[str] = Field(default_factory=list)  # ids d'employés
    participantsClient: list[ParticipantClient] = Field(default_factory=list)


class CommentaireConstat(BaseModel):
    commentaireClient: str = ""
    reponseManagement: str = ""


class RestitutionUpdate(BaseModel):
    reunion: Reunion
    commentaires: dict[str, CommentaireConstat] = Field(default_factory=dict)  # par id de constat
    version: int
