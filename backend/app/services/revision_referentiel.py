# Référentiel de la Phase 4 (révision par cycle) et de la Phase 5 (revue multi-niveaux) :
# étapes, assertions d'audit et grilles de revue par niveau. Pas de dépendance FastAPI/Mongo.

from app.core.permissions import REVIEW_LEVELS

ETAPES = ["4a", "4b", "4c", "4d", "4e", "4f"]
ETAPE_LABELS = {
    "4a": "Prise de connaissance",
    "4b": "Lead du cycle",
    "4c": "Justification du solde",
    "4d": "Contrôles détaillés",
    "4e": "Constats / Risques",
    "4f": "Conclusion du cycle",
}

STATUTS_REVUE = {niveau: f"revue_{niveau}" for niveau in REVIEW_LEVELS}
STATUT_CLOTURE = "cloture"

# Au-delà de ce nombre de retours sur un même point, il est signalé « À traiter en séance de travail ».
SEUIL_ALERTE_ROUNDS = 3

ASSERTIONS = [
    ("existence", "Existence"),
    ("exhaustivite", "Exhaustivité"),
    ("evaluation", "Évaluation"),
    ("droitsObligations", "Droits et obligations"),
    ("presentation", "Présentation"),
]

CHECKLISTS = {
    "senior": [
        ("justificationSoldes", "Justification des soldes"),
        ("referencementPieces", "Référencement des pièces"),
        ("coherenceCalculs", "Cohérence des calculs"),
        ("programmeRevision", "Respect du programme de révision"),
        ("anomaliesForme", "Traitement des anomalies identifiées sur la forme"),
        ("leadRenseigne", "Lead renseigné"),
        ("conclusionRedigee", "Conclusion rédigée"),
        ("referencesCroisees", "Références croisées correctes"),
        ("piecesJointes", "Pièces jointes présentes"),
    ],
    "manager": [
        ("zonesRisque", "Les zones à risque ont-elles été couvertes ?"),
        ("conclusionsCoherentes", "Les conclusions sont-elles cohérentes avec les travaux ?"),
        ("variationsExpliquees", "Les évolutions ont-elles été expliquées ?"),
        ("ecartsInvestigues", "Les écarts inhabituels ont-ils été investigués ?"),
        ("ajustementsJustifies", "Les écritures proposées sont-elles justifiées ?"),
        ("impactsFiscaux", "Les impacts fiscaux ont-ils été analysés ?"),
    ],
    "associe": [
        ("risquesMajeurs", "Risques majeurs identifiés"),
        ("desaccordsClient", "Points de désaccord avec le client"),
        ("ajustementsRefuses", "Ajustements refusés"),
        ("risquesFiscaux", "Risques fiscaux significatifs"),
        ("impactEtatsFinanciers", "Impact des anomalies sur les états financiers"),
        ("peutEmettre", "Peut-on émettre les états financiers sur ce point ?"),
    ],
}

OBJECTIFS_NIVEAU = {
    "senior": "S'assurer que les travaux du collaborateur sont complets, correctement documentés et "
    "cohérents avec le programme de travail. Le Senior ne refait pas le travail : il contrôle la forme "
    "et la traçabilité.",
    "manager": "Valider la pertinence des conclusions et apprécier les risques. Le Manager ne revérifie "
    "pas toutes les pièces : il challenge le raisonnement.",
    "associe": "Apprécier le risque global du dossier et valider la position du cabinet. L'Associé ne "
    "contrôle pas les détails d'exécution ; il se concentre sur les sujets à enjeux.",
}
