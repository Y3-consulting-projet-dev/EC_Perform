"""Collecte, en LECTURE SEULE, des données des phases 1 à 5 (et de la Phase 6 : saisie du rapport,
restitution client) nécessaires au rapport final.

C'est la seule couche du générateur qui accède à Mongo. Elle n'écrit jamais : en particulier, elle
lit `cycle_revisions` / `working_papers` directement au lieu d'appeler les fonctions des phases 4/5
qui créent le document au premier accès. Le résultat est un dict « RapportData » consommé par
l'assembleur, qui reste ainsi testable sans base.
"""

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException

from app.db.session import db
from app.services.balance_engine import compute_intangibilite
from app.services.balance_service import _detect_annee, balance_candidates, parse_balance_document
from app.services.client_service import serialize_client
from app.services.cycle_service import CYCLES, resoudre_cycle
from app.services.fiche_signaletique_service import _serialize as serialize_fiche
from app.services.rapport.formules import valeurs_feuille
from app.services.revision_referentiel import STATUT_CLOTURE

FAMILLES_CI_PAR_DEFAUT = {"Gouvernance", "Système d'information"}


def _client(mission):
    try:
        doc = db.clients.find_one({"_id": ObjectId(mission.get("clientId"))})
    except (InvalidId, TypeError):
        doc = None
    return serialize_client(doc) if doc else {}


def _balances(mission_id, mission, avertissements):
    """Comptes N et N-1 (parsés depuis les balances déposées en Phase 1), ou (None, None, {})."""
    candidates = balance_candidates(mission)
    if len(candidates) < 2:
        avertissements.append(
            "Balances N et N-1 introuvables : les extraits de balance et l'intangibilité ne sont pas générés."
        )
        return None, None, {}
    try:
        comptes_n, doc_n = parse_balance_document(mission_id, mission, candidates[0]["documentId"], "N")
        comptes_n1, doc_n1 = parse_balance_document(mission_id, mission, candidates[1]["documentId"], "N-1")
    except HTTPException as exc:
        avertissements.append(f"{exc.detail} : les extraits de balance ne sont pas générés.")
        return None, None, {}
    periodes = {
        "n": str(_detect_annee(doc_n.get("description", ""), doc_n.get("fileName", "")) or "N"),
        "nMoins1": str(_detect_annee(doc_n1.get("description", ""), doc_n1.get("fileName", "")) or "N-1"),
    }
    return comptes_n, comptes_n1, periodes


def _solde(compte, prefixe):
    return compte[f"debit{prefixe}"] - compte[f"credit{prefixe}"]


def _comptes_par_cycle(comptes_n, comptes_n1):
    """Pour chaque cycle : lignes {numero, libelle, soldeN, soldeNMoins1, ouverture, mvtDebit,
    mvtCredit} (union N / N-1, triées par numéro)."""
    par_cycle = {c["code"]: {} for c in CYCLES}
    for compte in comptes_n1 or []:
        cycle = resoudre_cycle(compte["numero"])
        if cycle:
            par_cycle[cycle["code"]][compte["numero"]] = {
                "numero": compte["numero"],
                "libelle": compte["libelle"],
                "soldeN": 0.0,
                "soldeNMoins1": _solde(compte, "Cloture"),
                "ouverture": 0.0,
                "mvtDebit": 0.0,
                "mvtCredit": 0.0,
                "presentN": False,
            }
    for compte in comptes_n or []:
        cycle = resoudre_cycle(compte["numero"])
        if not cycle:
            continue
        ligne = par_cycle[cycle["code"]].setdefault(
            compte["numero"], {"numero": compte["numero"], "soldeNMoins1": 0.0}
        )
        ligne.update(
            {
                "libelle": compte["libelle"],
                "soldeN": _solde(compte, "Cloture"),
                "ouverture": _solde(compte, "Ouverture"),
                "mvtDebit": compte["debitMouvement"],
                "mvtCredit": compte["creditMouvement"],
                "presentN": True,
            }
        )
    return {code: [lignes[n] for n in sorted(lignes)] for code, lignes in par_cycle.items()}


def _papiers(mission_id):
    """Feuilles des papiers de travail : {paperId: {cycleCode, etape, titre, feuilles: {nom: (colonnes,
    lignes de valeurs, nb cellules non évaluables)}}}. Mode lien : valeurs relues du classeur déposé ;
    mode intégré : formules évaluées."""
    out = {}
    for papier in db.working_papers.find({"missionId": mission_id}):
        if papier.get("mode") == "lien":
            feuilles = {
                f["nom"]: (f.get("colonnes") or [], f.get("data") or [], 0)
                for f in (papier.get("lien") or {}).get("feuilles") or []
            }
        else:
            feuilles = {}
            for f in papier.get("feuilles") or []:
                lignes, erreurs = valeurs_feuille(f.get("data") or [])
                feuilles[f["nom"]] = (f.get("colonnes") or [], lignes, erreurs)
        out[str(papier["_id"])] = {
            "cycleCode": papier.get("cycleCode"),
            "etape": papier.get("etape"),
            "titre": papier.get("titre", ""),
            "mode": papier.get("mode"),
            "feuilles": feuilles,
        }
    return out


def collecter(mission_id, mission, rapport):
    """Assemble toutes les données du rapport. `rapport` est le document de la collection
    `rapports` (saisie de la Phase 6)."""
    avertissements = []
    client = _client(mission)
    fiche = serialize_fiche(mission)["valeurs"]
    nom_client = (fiche.get("denomination") or "").strip() or client.get("raisonSociale") or "le client"

    comptes_n, comptes_n1, periodes = _balances(mission_id, mission, avertissements)
    intangibilite = None
    if comptes_n is not None:
        intangibilite = compute_intangibilite(comptes_n, comptes_n1)
        intangibilite.update({"periodeN": periodes["n"], "periodeNMoins1": periodes["nMoins1"]})
    comptes_cycles = _comptes_par_cycle(comptes_n, comptes_n1) if comptes_n is not None else {}

    saisie = (rapport or {}).get("saisie") or {}
    saisie_constats = saisie.get("constats") or {}
    restitution = db.restitutions.find_one({"missionId": mission_id}) or {}
    commentaires = restitution.get("commentaires") or {}

    revisions = {r["code"]: r for r in db.cycle_revisions.find({"missionId": mission_id})}
    cycles, ajustements_par_id, constats = [], {}, []
    for cycle in CYCLES:
        code = cycle["code"]
        rev = revisions.get(code) or {}
        conclusion = rev.get("conclusion") or {}
        justification = rev.get("justification") or {}
        ajustements = [{**a, "cycleCode": code} for a in conclusion.get("ajustements") or []]
        for a in ajustements:
            ajustements_par_id[a["id"]] = a
        constats_cycle = []
        for c in rev.get("constats") or []:
            s = saisie_constats.get(c.get("id")) or {}
            r = commentaires.get(c.get("id")) or {}
            retenir = s.get("retenirCI")
            constat = {
                **c,
                "cycleCode": code,
                "cycleLibelle": cycle["libelle"],
                "titre": (s.get("titre") or "").strip(),
                "risques": [x.strip() for x in s.get("risques") or [] if x and x.strip()],
                "retenirCI": c.get("famille") in FAMILLES_CI_PAR_DEFAUT if retenir is None else bool(retenir),
                "commentaireClient": (r.get("commentaireClient") or "").strip(),
                "reponseManagement": (r.get("reponseManagement") or "").strip(),
            }
            constats_cycle.append(constat)
            constats.append(constat)
        cycles.append(
            {
                "code": code,
                "libelle": cycle["libelle"],
                "statut": rev.get("statut") or "non_commence",
                "cloture": rev.get("statut") == STATUT_CLOTURE,
                "comptes": comptes_cycles.get(code, []),
                "commentairesComptes": (rev.get("lead") or {}).get("commentaires") or {},
                "synthese": (conclusion.get("synthese") or "").strip(),
                "commentaireJustification": ((justification.get("commentaire") or {}).get("texte") or "").strip(),
                "constats": constats_cycle,
                "ajustements": ajustements,
                "points": (saisie.get("points") or {}).get(code) or [],
            }
        )

    return {
        "missionId": mission_id,
        "exercice": mission.get("exercice", ""),
        "client": client,
        "nomClient": nom_client,
        "fiche": fiche,
        "saisie": saisie,
        "medias": (rapport or {}).get("medias") or {},
        "restitution": restitution,
        "intangibilite": intangibilite,
        "periodes": periodes,
        "cycles": cycles,
        "constats": constats,
        "ajustementsParId": ajustements_par_id,
        "ecritures": saisie.get("ecritures") or [],
        "papiers": _papiers(mission_id),
        "cyclesNonClotures": [c["code"] for c in cycles if not c["cloture"]],
        "avertissements": avertissements,
    }
