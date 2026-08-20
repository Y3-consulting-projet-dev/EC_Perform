from fastapi import HTTPException

from app.services.balance_engine import TOLERANCE, format_montant
from app.services.balance_service import balance_candidates, parse_balance_document
from app.services.mission_service import get_mission_or_404

# Table de correspondance Cycles de révision comptable <-> Comptes SYSCOHADA.
#
# - classes : classes entières couvertes (ex. "3" = toute la classe 3)
# - prefixes : préfixes de compte (2 ou 3 chiffres) inclus dans le cycle
# - subPrefixes : sous-comptes (souvent du compte transversal 44) rattachés à ce cycle ;
#   vérifiés en priorité, avant toute résolution par classe/préfixe
# - excludePrefixes : préfixes à exclure explicitement (déjà couverts par un subPrefixe
#   d'un autre cycle)
#
# L'ORDRE de la liste fait partie de la règle de résolution : un compte est affecté au
# premier cycle qui le revendique (ex. 66xxxx est réclamé par F avant que K, plus large,
# ne l'absorbe via la classe 6 ; 70xxxx par B avant K via la classe 7 ; 68xxxx par E avant
# K via la classe 6 ; 64xxxx et 89xxxx par G avant K via les classes 6 et 8).
CYCLES = [
    {
        "code": "A",
        "libelle": "Trésorerie et financement",
        "classes": ["5"],
        "prefixes": ["50", "52", "53", "56", "57", "58", "59"],
        "subPrefixes": {},
        "excludePrefixes": [],
    },
    {
        "code": "B",
        "libelle": "Ventes et clients",
        "classes": [],
        "prefixes": ["41", "70", "391", "491"],
        "subPrefixes": {"4432": "TVA facturée", "4434": "TVA collectée"},
        "excludePrefixes": [],
    },
    {
        "code": "C",
        "libelle": "Achats et fournisseurs",
        "classes": [],
        "prefixes": ["40", "60", "401", "408"],
        "subPrefixes": {"4452": "TVA déductible"},
        "excludePrefixes": [],
    },
    {
        "code": "D",
        "libelle": "Stocks",
        "classes": ["3"],
        "prefixes": ["31", "32", "33", "34", "35", "36", "37", "38", "39"],
        "subPrefixes": {},
        "excludePrefixes": [],
    },
    {
        "code": "E",
        "libelle": "Immobilisations",
        "classes": ["2"],
        "prefixes": ["20", "21", "22", "23", "24", "25", "26", "27", "28", "29", "68"],
        "subPrefixes": {},
        "excludePrefixes": [],
    },
    {
        "code": "F",
        "libelle": "Personnel et charges sociales",
        "classes": [],
        "prefixes": ["42", "43", "66"],
        "subPrefixes": {},
        "excludePrefixes": [],
    },
    {
        "code": "G",
        "libelle": "Fiscalité",
        "classes": [],
        "prefixes": ["44", "64", "89"],
        "subPrefixes": {},
        "excludePrefixes": ["4432", "4434", "4452"],
    },
    {
        "code": "H",
        "libelle": "Capitaux propres",
        "classes": [],
        "prefixes": ["10", "11", "12", "13", "14", "15"],
        "subPrefixes": {},
        "excludePrefixes": [],
    },
    {
        "code": "I",
        "libelle": "Emprunts et dettes financières",
        "classes": [],
        "prefixes": ["16", "17", "19"],
        "subPrefixes": {},
        "excludePrefixes": [],
    },
    {
        "code": "J",
        "libelle": "Autres actifs et passifs",
        "classes": [],
        "prefixes": ["18", "45", "46", "47", "48"],
        "subPrefixes": {},
        "excludePrefixes": [],
    },
    {
        "code": "K",
        "libelle": "Produits et charges",
        "classes": ["6", "7", "8"],
        "prefixes": [],
        "subPrefixes": {},
        "excludePrefixes": [],
    },
    {
        "code": "L",
        "libelle": "États financiers",
        "classes": [],
        "prefixes": [],
        "subPrefixes": {},
        "excludePrefixes": [],
    },
]


def resoudre_cycle(numero_compte):
    """Retourne le cycle (dict) auquel appartient un numéro de compte, ou None."""
    compte = str(numero_compte)

    # Sous-comptes spécifiques d'abord (cas du compte transversal 44 : TVA).
    for cycle in CYCLES:
        if any(compte.startswith(p) for p in cycle["subPrefixes"]):
            return cycle

    # Puis classes entières et préfixes, en respectant les exclusions.
    for cycle in CYCLES:
        if any(compte.startswith(p) for p in cycle["excludePrefixes"]):
            continue
        if compte[:1] in cycle["classes"]:
            return cycle
        if any(compte.startswith(p) for p in cycle["prefixes"]):
            return cycle

    return None


def _plage_label(cycle):
    classes = cycle["classes"]
    if len(classes) > 1:
        class_labels = [f"Classes {', '.join(classes)}"]
    elif classes:
        class_labels = [f"Classe {classes[0]}"]
    else:
        class_labels = []

    extra_prefixes = [p for p in cycle["prefixes"] if p[:1] not in classes]
    parts = class_labels + extra_prefixes + list(cycle["subPrefixes"])
    label = ", ".join(parts) if parts else "—"

    if cycle["excludePrefixes"]:
        label += f" (hors {', '.join(cycle['excludePrefixes'])})"
    return label


def _solde_cloture(compte):
    return compte["debitCloture"] - compte["creditCloture"]


def _grouper_par_cycle(comptes):
    par_cycle = {cycle["code"]: [] for cycle in CYCLES}
    for compte in comptes:
        cycle = resoudre_cycle(compte["numero"])
        if cycle:
            par_cycle[cycle["code"]].append(compte)
    return par_cycle


def _variation(solde_n, solde_n_moins1):
    ecart = solde_n - solde_n_moins1
    if abs(ecart) < TOLERANCE:
        sens = "stable"
    elif ecart > 0:
        sens = "hausse"
    else:
        sens = "baisse"
    # On divise par la valeur absolue du solde N-1 : le solde de base peut être négatif
    # (comptes créditeurs comme les ventes), et diviser par un nombre négatif inverserait
    # le signe du pourcentage indépendamment du sens hausse/baisse déjà déterminé ci-dessus.
    pct = round(ecart / abs(solde_n_moins1) * 100, 1) if abs(solde_n_moins1) >= TOLERANCE else None
    return ecart, pct, sens


def compute_cycles(comptes_n, comptes_n_moins1):
    comptes_n_par_cycle = _grouper_par_cycle(comptes_n)
    comptes_n_moins1_par_cycle = _grouper_par_cycle(comptes_n_moins1)

    cycles = []
    for cycle in CYCLES:
        comptes_cycle_n = comptes_n_par_cycle[cycle["code"]]
        comptes_cycle_n_moins1 = comptes_n_moins1_par_cycle[cycle["code"]]
        solde_n = sum(_solde_cloture(c) for c in comptes_cycle_n)
        solde_n_moins1 = sum(_solde_cloture(c) for c in comptes_cycle_n_moins1)
        ecart, pct, sens = _variation(solde_n, solde_n_moins1)
        cycles.append(
            {
                "code": cycle["code"],
                "libelle": cycle["libelle"],
                "plage": _plage_label(cycle),
                "nbComptes": len(comptes_cycle_n),
                "soldeN": format_montant(solde_n),
                "soldeNMoins1": format_montant(solde_n_moins1),
                "ecart": format_montant(ecart),
                "variationPct": pct,
                "sens": sens,
            }
        )
    return cycles


def _resolve_balances(mission_id, mission, document_id_n, document_id_n_moins1):
    candidates = balance_candidates(mission)

    if not document_id_n or not document_id_n_moins1:
        if len(candidates) < 2:
            raise HTTPException(status_code=404, detail="Balances N et N-1 introuvables pour cette mission")
        document_id_n = document_id_n or candidates[0]["documentId"]
        document_id_n_moins1 = document_id_n_moins1 or candidates[1]["documentId"]

    comptes_n, _ = parse_balance_document(mission_id, mission, document_id_n, "N")
    comptes_n_moins1, _ = parse_balance_document(mission_id, mission, document_id_n_moins1, "N-1")
    return comptes_n, comptes_n_moins1, document_id_n, document_id_n_moins1


def get_mission_cycles(mission_id: str, document_id_n: str | None, document_id_n_moins1: str | None):
    _, mission = get_mission_or_404(mission_id)
    comptes_n, comptes_n_moins1, document_id_n, document_id_n_moins1 = _resolve_balances(
        mission_id, mission, document_id_n, document_id_n_moins1
    )

    return {
        "cycles": compute_cycles(comptes_n, comptes_n_moins1),
        "documentIdN": document_id_n,
        "documentIdNMoins1": document_id_n_moins1,
    }


def get_mission_cycle_detail(mission_id: str, code: str, document_id_n: str | None, document_id_n_moins1: str | None):
    if code not in {cycle["code"] for cycle in CYCLES}:
        raise HTTPException(status_code=404, detail="Cycle introuvable")

    _, mission = get_mission_or_404(mission_id)
    comptes_n, comptes_n_moins1, document_id_n, document_id_n_moins1 = _resolve_balances(
        mission_id, mission, document_id_n, document_id_n_moins1
    )

    comptes_n_cycle = {c["numero"]: c for c in _grouper_par_cycle(comptes_n)[code]}
    comptes_n_moins1_cycle = {c["numero"]: c for c in _grouper_par_cycle(comptes_n_moins1)[code]}

    comptes = []
    for numero in sorted(set(comptes_n_cycle) | set(comptes_n_moins1_cycle)):
        compte_n = comptes_n_cycle.get(numero)
        compte_n_moins1 = comptes_n_moins1_cycle.get(numero)
        comptes.append(
            {
                "numero": numero,
                "libelle": (compte_n or compte_n_moins1)["libelle"],
                "soldeN": _solde_cloture(compte_n) if compte_n else 0.0,
                "soldeNMoins1": _solde_cloture(compte_n_moins1) if compte_n_moins1 else 0.0,
            }
        )

    return {
        "code": code,
        "comptes": comptes,
        "documentIdN": document_id_n,
        "documentIdNMoins1": document_id_n_moins1,
    }
