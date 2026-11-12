"""Orchestrateur : assemble le rapport complet à partir des données collectées (donnees.py).

Plan du rapport (un chapitre par cycle, décision du 09/11/2026) :
  Couverture
  pour chaque partie présente : Sommaire (partie courante en vert), Séparateur, contenu
    1. Contexte et objectifs de la mission (contexte, présentation de l'entité, évènements
       significatifs, réunion de restitution)
    2. Appréciation du dispositif de contrôle interne (si des constats sont retenus)
    3. Travaux de révision par cycle (intangibilité, puis un chapitre par cycle A–M non vide)
    4. Travaux de régularisation (si des ajustements existent) : écritures regroupées
  Fin

Aucun texte n'est inventé : chaque élément provient des données de la mission, de la saisie de
la Phase 6 ou des paragraphes types du cabinet (textes.py) ; une section sans donnée est omise.
"""

import io
import os
from datetime import datetime, timezone

from pptx import Presentation

from app.services.balance_engine import format_montant
from app.services.rapport import builders as b
from app.services.rapport import textes
from app.services.rapport.builders import P, paragraphes_depuis_texte
from app.services.rapport.formules import nombre

MODELE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "templates", "rapport_template.pptx"))
TITRE_RAPPORT = "Révision des comptes"
COLONNES_GRAND_LIVRE = ["Date", "Journal", "N° pièce", "Compte", "Compte tiers", "Libellé", "Débit", "Crédit"]


# --- Formats ----------------------------------------------------------------------------------


def montant(v):
    return format_montant(v) if v is not None and abs(v) >= 0.5 else "-"


def _cellule_valeur(v):
    if v is None:
        return ""
    if isinstance(v, bool):
        return "Vrai" if v else "Faux"
    if isinstance(v, (int, float)):
        if float(v).is_integer() or abs(v) >= 1000:
            return format_montant(v)
        return f"{v:.2f}".replace(".", ",")
    return str(v)


def _date_rapport(saisie, maintenant):
    valeur = (saisie.get("dateRapport") or "").strip()
    try:
        annee, mois = (int(x) for x in valeur.split("-")[:2])
        return f"{textes.MOIS[mois - 1]} {annee}"
    except (ValueError, IndexError):
        return f"{textes.MOIS[maintenant.month - 1]} {maintenant.year}"


def _colonne(titre, poids=1, align="l"):
    return {"titre": titre, "poids": poids, "align": align}


def _filtrer(comptes, prefixes):
    prefixes = [p.strip() for p in prefixes or [] if p and p.strip()]
    return [c for c in comptes if not prefixes or any(c["numero"].startswith(p) for p in prefixes)]


# --- Tableaux métier --------------------------------------------------------------------------


def tableau_balance(cycle, periodes, prefixes=None):
    comptes = [
        c for c in _filtrer(cycle["comptes"], prefixes)
        if abs(c["soldeN"]) >= 0.5 or abs(c["soldeNMoins1"]) >= 0.5
    ]
    commentaires = cycle.get("commentairesComptes") or {}
    avec_commentaire = any(commentaires.get(c["numero"]) for c in comptes)
    colonnes = [
        _colonne("Compte", 1.3), _colonne("Intitulé", 3.6),
        _colonne(f"Solde {periodes.get('nMoins1', 'N-1')}", 1.7, "r"),
        _colonne(f"Solde {periodes.get('n', 'N')}", 1.7, "r"), _colonne("Variation", 1.6, "r"),
    ]
    if avec_commentaire:
        colonnes.append(_colonne("Commentaire", 3.6))
    lignes = []
    for c in comptes:
        cellules = [c["numero"], c["libelle"], montant(c["soldeNMoins1"]), montant(c["soldeN"]),
                    montant(c["soldeN"] - c["soldeNMoins1"])]
        if avec_commentaire:
            cellules.append(commentaires.get(c["numero"], ""))
        lignes.append({"cellules": cellules})
    total_n1 = sum(c["soldeNMoins1"] for c in comptes)
    total_n = sum(c["soldeN"] for c in comptes)
    pied = ["Total", "", montant(total_n1), montant(total_n), montant(total_n - total_n1)]
    if avec_commentaire:
        pied.append("")
    return {"colonnes": colonnes, "lignes": lignes, "pied": [{"cellules": pied, "style": "total"}] if lignes else []}


def tableau_variation(cycle, periodes, prefixes=None):
    comptes = [
        c for c in _filtrer(cycle["comptes"], prefixes)
        if c.get("presentN") and any(abs(c[k]) >= 0.5 for k in ("ouverture", "mvtDebit", "mvtCredit", "soldeN"))
    ]
    n = periodes.get("n", "N")
    colonnes = [
        _colonne("Compte", 1.3), _colonne("Intitulé", 3.4), _colonne(f"Solde d'ouverture {n}", 1.8, "r"),
        _colonne("Mouvements débit", 1.7, "r"), _colonne("Mouvements crédit", 1.7, "r"),
        _colonne(f"Solde de clôture {n}", 1.8, "r"),
    ]
    lignes = [
        {"cellules": [c["numero"], c["libelle"], montant(c["ouverture"]), montant(c["mvtDebit"]),
                      montant(c["mvtCredit"]), montant(c["soldeN"])]}
        for c in comptes
    ]
    tot = {k: sum(c[k] for c in comptes) for k in ("ouverture", "mvtDebit", "mvtCredit", "soldeN")}
    pied = [{"cellules": ["Total", "", montant(tot["ouverture"]), montant(tot["mvtDebit"]),
                          montant(tot["mvtCredit"]), montant(tot["soldeN"])], "style": "total"}]
    return {"colonnes": colonnes, "lignes": lignes, "pied": pied if lignes else []}


def _lignes_ajustements(ajustements):
    lignes, debit, credit = [], 0.0, 0.0
    for a in ajustements:
        est_debit = a.get("sens") == "Débit"
        m = float(a.get("montant") or 0)
        debit += m if est_debit else 0
        credit += 0 if est_debit else m
        lignes.append({"cellules": [a.get("compte", ""), a.get("libelle", ""), montant(m) if est_debit else "",
                                    "" if est_debit else montant(m)]})
    return lignes, debit, credit


COLONNES_ECRITURE = [_colonne("Compte", 1.2), _colonne("Libellé", 4.0), _colonne("Débit", 1.5, "r"),
                     _colonne("Crédit", 1.5, "r")]


def tableau_ajustements(ajustements):
    lignes, debit, credit = _lignes_ajustements(ajustements)
    pied = [{"cellules": ["Total", "", montant(debit), montant(credit)], "style": "total"}]
    return {"colonnes": COLONNES_ECRITURE, "lignes": lignes, "pied": pied if lignes else []}


def tableau_libre(colonnes, lignes):
    largeur = max([len(colonnes)] + [len(l) for l in lignes]) if (colonnes or lignes) else 0
    colonnes = list(colonnes) + [""] * (largeur - len(colonnes))
    lignes = [list(l) + [""] * (largeur - len(l)) for l in lignes]
    cols = []
    for i, titre in enumerate(colonnes):
        valeurs = [l[i] for l in lignes if str(l[i]).strip()]
        numerique = bool(valeurs) and all(nombre(v) is not None for v in valeurs)
        cols.append(_colonne(str(titre), 1, "r" if numerique else "l"))
    return {"colonnes": cols, "lignes": [{"cellules": [str(v) for v in l]} for l in lignes], "pied": []}


def tableau_grand_livre(grand_livre):
    lignes, debit, credit = [], 0.0, 0.0
    for l in grand_livre.get("lignes") or []:
        d, c = l.get("debit"), l.get("credit")
        debit += d or 0
        credit += c or 0
        lignes.append({"cellules": [l.get("date", ""), l.get("journal", ""), l.get("piece", ""), l.get("compte", ""),
                                    l.get("compteTiers", ""), l.get("libelle", ""),
                                    montant(d) if d else "", montant(c) if c else ""]})
    poids = [1.1, 0.8, 0.9, 1.1, 1.1, 3.0, 1.3, 1.3]
    colonnes = [_colonne(t, p, "r" if t in ("Débit", "Crédit") else "l") for t, p in zip(COLONNES_GRAND_LIVRE, poids)]
    pied = [{"cellules": ["Total", "", "", "", "", "", montant(debit), montant(credit)], "style": "total"}]
    return {"colonnes": colonnes, "lignes": lignes, "pied": pied if lignes else []}


def tableau_papier(feuille):
    colonnes, valeurs, _ = feuille
    lignes = [[_cellule_valeur(v) for v in l] for l in valeurs]
    while lignes and not any(str(v).strip() for v in lignes[-1]):
        lignes.pop()
    largeur = max([len(l) for l in lignes] + [0])
    utiles = [i for i in range(largeur) if any(i < len(l) and str(l[i]).strip() for l in lignes)]
    titres = [colonnes[i] if i < len(colonnes) else "" for i in utiles]
    return tableau_libre(titres, [[l[i] if i < len(l) else "" for i in utiles] for l in lignes])


def tableau_constats(constats, nom_client):
    avec_client = any(c["commentaireClient"] for c in constats)
    avec_mgmt = any(c["reponseManagement"] for c in constats)
    colonnes = [_colonne("Constat", 3), _colonne("Sévérité", 0.9, "c"), _colonne("Recommandation", 3)]
    if avec_client:
        colonnes.append(_colonne(f"Commentaire de {nom_client}", 2.2))
    if avec_mgmt:
        colonnes.append(_colonne("Réponse du management", 2.2))
    lignes = []
    for c in constats:
        cellules = [c.get("constat", ""), c.get("severite", ""), c.get("recommandation", "")]
        if avec_client:
            cellules.append(c["commentaireClient"])
        if avec_mgmt:
            cellules.append(c["reponseManagement"])
        lignes.append({"cellules": cellules})
    return {"colonnes": colonnes, "lignes": lignes, "pied": []}


# --- Écritures regroupées ---------------------------------------------------------------------


def _ecritures(data, avertissements):
    """Écritures saisies (groupes d'ajustements) résolues, et ajustements non regroupés par cycle."""
    par_id = data["ajustementsParId"]
    regroupes, ecritures = set(), []
    for e in data["ecritures"]:
        ajustements = [par_id[i] for i in e.get("ajustementIds") or [] if i in par_id]
        manquants = len(e.get("ajustementIds") or []) - len(ajustements)
        libelle = e.get("libelle") or "Écriture"
        if manquants:
            avertissements.append(f"Écriture « {libelle} » : {manquants} ajustement(s) supprimé(s) en Phase 4 ignoré(s).")
        if not ajustements:
            continue
        _, debit, credit = _lignes_ajustements(ajustements)
        if abs(debit - credit) >= 0.5:
            avertissements.append(
                f"Écriture « {libelle} » déséquilibrée (débit {montant(debit)}, crédit {montant(credit)})."
            )
        regroupes.update(a["id"] for a in ajustements)
        ecritures.append({**e, "libelle": libelle, "ajustements": ajustements})
    non_regroupes = {}
    for a in par_id.values():
        if a["id"] not in regroupes:
            non_regroupes.setdefault(a["cycleCode"], []).append(a)
    return ecritures, non_regroupes


# --- Blocs des points saisis ------------------------------------------------------------------


def _bloc(bloc, cycle, data, ecritures_par_id, avertissements):
    type_ = bloc.get("type")
    legende = (bloc.get("titre") or "").strip()
    periodes = data["periodes"]
    if type_ == "balance":
        if not cycle["comptes"]:
            avertissements.append(f"Cycle {cycle['code']} : extrait de balance demandé mais balances absentes.")
            return None
        return {"legende": legende or "Extrait de la balance", "tableau": tableau_balance(cycle, periodes, bloc.get("prefixes"))}
    if type_ == "variation":
        if not cycle["comptes"]:
            avertissements.append(f"Cycle {cycle['code']} : tableau de variation demandé mais balances absentes.")
            return None
        return {"legende": legende or "Variation des comptes", "tableau": tableau_variation(cycle, periodes, bloc.get("prefixes"))}
    if type_ == "tableau":
        return {"legende": legende, "tableau": tableau_libre(bloc.get("colonnes") or [], bloc.get("lignes") or [])}
    if type_ == "grand_livre":
        return {"legende": legende or "Extrait du grand livre", "tableau": tableau_grand_livre(bloc.get("grandLivre") or {})}
    if type_ == "papier":
        papier = data["papiers"].get(bloc.get("paperId") or "")
        feuille = (papier or {}).get("feuilles", {}).get(bloc.get("feuille") or "")
        if feuille is None:
            avertissements.append(f"Cycle {cycle['code']} : feuille de papier de travail introuvable (« {bloc.get('feuille')} »).")
            return None
        if feuille[2]:
            avertissements.append(
                f"Cycle {cycle['code']} : {feuille[2]} formule(s) non évaluable(s) dans « {bloc.get('feuille')} » "
                "(affichées #FORMULE, à compléter dans l'éditeur)."
            )
        return {"legende": legende or bloc.get("feuille"), "tableau": tableau_papier(feuille)}
    if type_ == "ecriture":
        ecriture = ecritures_par_id.get(bloc.get("ecritureId") or "")
        if ecriture is None:
            avertissements.append(f"Cycle {cycle['code']} : écriture référencée introuvable.")
            return None
        return {"legende": legende or ecriture["libelle"], "tableau": tableau_ajustements(ecriture["ajustements"])}
    return None


# --- Parties ----------------------------------------------------------------------------------


def _partie_contexte(data):
    saisie = data["saisie"]
    client = data["nomClient"]
    lettre = saisie.get("lettreMission") or {}
    contexte = [P(t) for t in textes.contexte_paragraphes(
        client, data["exercice"], (lettre.get("date") or "").strip(), (lettre.get("prestations") or "").strip()
    )] + paragraphes_depuis_texte(saisie.get("contexteComplement"))

    presentation = [P(t) for t in textes.presentation_paragraphes(data["fiche"])]
    actionnariat = paragraphes_depuis_texte(saisie.get("actionnariat"), niveau=1) or paragraphes_depuis_texte(
        data["fiche"].get("associes"), niveau=1
    )
    if actionnariat:
        presentation += [P("Actionnariat", style="intertitre")] + actionnariat

    evenements = []
    for e in saisie.get("evenements") or []:
        if (e.get("titre") or "").strip() or (e.get("texte") or "").strip():
            if (e.get("titre") or "").strip():
                evenements.append(P(e["titre"].strip(), style="intertitre"))
            evenements += paragraphes_depuis_texte(e.get("texte"))

    reunion = (data["restitution"] or {}).get("reunion") or {}
    restitution = []
    if reunion.get("date"):
        restitution.append(P(f"Réunion de restitution du {_date_fr(reunion['date'])}"
                             + (f" — {reunion['lieu'].strip()}" if (reunion.get("lieu") or "").strip() else ""),
                             style="intertitre"))
        cabinet = [p["nom"] for p in reunion.get("participantsCabinet") or [] if (p.get("nom") or "").strip()]
        client_p = [f"{p['nom']}" + (f", {p['fonction']}" if p.get("fonction") else "")
                    for p in reunion.get("participantsClient") or [] if (p.get("nom") or "").strip()]
        if cabinet:
            restitution += [P(f"Pour {textes.CABINET} :", style="gras")] + [P(n, niveau=1) for n in cabinet]
        if client_p:
            restitution += [P(f"Pour {client} :", style="gras")] + [P(n, niveau=1) for n in client_p]

    sections = [("Contexte et objectifs", contexte), ("Présentation de l'entité", presentation),
                ("Évènements significatifs", evenements), ("Réunion de restitution", restitution)]
    sections = [(r, p) for r, p in sections if p]
    titre = textes.PARTIES["contexte"]

    def rendre(prs):
        for rubrique, paragraphes in sections:
            b.texte(prs, titre, rubrique, paragraphes)

    return {"titre": titre, "sous": [r for r, _ in sections], "rendre": rendre}


def _partie_controle_interne(data):
    retenus = [c for c in data["constats"] if c["retenirCI"]]
    if not retenus:
        return None
    titre = textes.PARTIES["controle_interne"]

    def libelle(c):
        return f"{c['cycleLibelle']} : {c['titre'] or c.get('famille', '')}"

    intro = [P(t[0], niveau=t[1]) if isinstance(t, tuple) else P(t) for t in textes.CI_INTRODUCTION]
    intro += [P("Les principaux points relevés au cours de notre intervention portent sur les processus suivants :")]
    intro += [P(libelle(c), niveau=1) for c in retenus]
    colonne = f"Commentaires du management de {data['nomClient']}"

    def rendre(prs):
        b.ci_introduction(prs, titre, intro)
        for c in retenus:
            b.constat_ci(prs, titre, libelle(c), c, colonne)

    return {"titre": titre, "sous": ["Introduction et légende"] + sorted({c["cycleLibelle"] for c in retenus}),
            "rendre": rendre}


def _cycle_non_vide(cycle):
    soldes = any(abs(c["soldeN"]) >= 0.5 or abs(c["soldeNMoins1"]) >= 0.5 for c in cycle["comptes"])
    return soldes or cycle["synthese"] or cycle["commentaireJustification"] or cycle["constats"] \
        or cycle["ajustements"] or cycle["points"]


def _partie_cycles(data, ecritures, non_regroupes, avertissements):
    cycles = [c for c in data["cycles"] if _cycle_non_vide(c)]
    intangibilite = data["intangibilite"]
    if not cycles and not intangibilite:
        return None
    titre_partie = textes.PARTIES["cycles"]
    ecritures_par_id = {e["id"]: e for e in ecritures if e.get("id")}

    def rendre_intangibilite(prs):
        lignes = [l for l in intangibilite["comptes"] if l["statut"] != "OK"]
        paragraphes = [P(textes.INTANGIBILITE_DEFINITION), P(textes.intangibilite_constat(
            len(lignes), intangibilite["periodeNMoins1"], intangibilite["periodeN"]))]
        paragraphes += paragraphes_depuis_texte(data["saisie"].get("intangibiliteCommentaire"))
        tableau = {
            "colonnes": [_colonne("Compte", 1.2), _colonne("Intitulé", 3.2),
                         _colonne(f"Clôture {intangibilite['periodeNMoins1']}", 1.6, "r"),
                         _colonne(f"Ouverture {intangibilite['periodeN']}", 1.6, "r"),
                         _colonne("Écart", 1.4, "r"), _colonne("Statut", 1.0, "c")],
            "lignes": [{"cellules": [l["compte"], l["libelle"], l["bilanClotureNMoins1"], l["bilanOuvertureN"],
                                     l["ecart"], l["statut"]]} for l in lignes],
            "pied": [],
        }
        b.section(prs, "Intangibilité du bilan", "Rapprochement clôture N-1 / ouverture N", paragraphes,
                  [{"legende": "Comptes présentant un écart", "tableau": tableau}] if lignes else [])

    def rendre_cycle(prs, cycle):
        titre = f"{cycle['code']} – {cycle['libelle']}"
        synthese = paragraphes_depuis_texte(cycle["synthese"])
        if cycle["commentaireJustification"]:
            synthese += [P("Justification du solde", style="intertitre")] + paragraphes_depuis_texte(
                cycle["commentaireJustification"])
        tableaux = []
        if cycle["comptes"]:
            t = tableau_balance(cycle, data["periodes"])
            if t["lignes"]:
                tableaux.append({"legende": "Extrait de la balance", "tableau": t})
        if synthese or tableaux:
            b.section(prs, titre, "Synthèse du cycle", synthese, tableaux)

        utilisees = set()
        for point in cycle["points"]:
            blocs = []
            for bloc in point.get("blocs") or []:
                if bloc.get("type") == "ecriture":
                    utilisees.add(bloc.get("ecritureId"))
                rendu = _bloc(bloc, cycle, data, ecritures_par_id, avertissements)
                if rendu:
                    blocs.append(rendu)
            b.section(prs, titre, point.get("titre") or "Point", paragraphes_depuis_texte(point.get("texte")), blocs)

        if cycle["constats"]:
            b.tableau_seul(prs, titre, "Constats et recommandations", tableau_constats(cycle["constats"], data["nomClient"]))

        restantes = [
            {"legende": e["libelle"], "tableau": tableau_ajustements(e["ajustements"])}
            for e in ecritures if e.get("cycleCode") == cycle["code"] and e.get("id") not in utilisees
        ]
        if non_regroupes.get(cycle["code"]):
            restantes.append({"legende": "Ajustements non regroupés",
                              "tableau": tableau_ajustements(non_regroupes[cycle["code"]])})
        if restantes:
            b.section(prs, titre, "Écritures proposées", [], restantes)

    def rendre(prs):
        if intangibilite:
            rendre_intangibilite(prs)
        for cycle in cycles:
            rendre_cycle(prs, cycle)

    sous = (["Intangibilité du bilan"] if intangibilite else []) + [f"{c['code']} – {c['libelle']}" for c in cycles]
    return {"titre": titre_partie, "sous": sous, "rendre": rendre}


def _partie_regularisation(data, ecritures, non_regroupes):
    if not data["ajustementsParId"]:
        return None
    titre = textes.PARTIES["regularisation"]
    lignes, debit, credit = [], 0.0, 0.0
    for cycle in data["cycles"]:
        groupes = [(e["libelle"], e["ajustements"]) for e in ecritures if e.get("cycleCode") == cycle["code"]]
        if non_regroupes.get(cycle["code"]):
            groupes.append(("Ajustements non regroupés", non_regroupes[cycle["code"]]))
        for libelle, ajustements in groupes:
            l, d, c = _lignes_ajustements(ajustements)
            lignes.append({"cellules": [f"{cycle['code']} – {cycle['libelle']} · {libelle}", "", "", ""], "style": "groupe"})
            lignes += l
            debit, credit = debit + d, credit + c
    tableau = {"colonnes": COLONNES_ECRITURE, "lignes": lignes,
               "pied": [{"cellules": ["Total", "", montant(debit), montant(credit)], "style": "total"}]}

    def rendre(prs):
        b.tableau_seul(prs, titre, "Récapitulatif des écritures proposées", tableau)

    return {"titre": titre, "sous": ["Récapitulatif des écritures proposées"], "rendre": rendre}


def _date_fr(valeur):
    try:
        return datetime.strptime(valeur[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        return valeur


# --- Orchestration ----------------------------------------------------------------------------


def assembler(data, modele=MODELE, maintenant=None):
    """Construit le PPTX. Renvoie (octets, résumé)."""
    maintenant = maintenant or datetime.now(timezone.utc)
    avertissements = list(data["avertissements"])
    ecritures, non_regroupes = _ecritures(data, avertissements)

    parties = [
        _partie_contexte(data),
        _partie_controle_interne(data),
        _partie_cycles(data, ecritures, non_regroupes, avertissements),
        _partie_regularisation(data, ecritures, non_regroupes),
    ]
    parties = [p for p in parties if p]
    for numero, partie in enumerate(parties, start=1):
        partie["numero"] = numero

    projet = bool(data["cyclesNonClotures"])
    if projet:
        avertissements.insert(0, "Rapport généré en brouillon : cycles non clôturés — "
                              + ", ".join(data["cyclesNonClotures"]) + ".")
    medias = data.get("mediasBlobs") or {}

    prs = Presentation(modele)
    b.couverture(prs, TITRE_RAPPORT, data["exercice"], data["nomClient"], _date_rapport(data["saisie"], maintenant),
                 "PROJET – document provisoire" if projet else None, medias.get("logo"))
    for partie in parties:
        b.sommaire(prs, parties, partie["numero"])
        b.separateur(prs, partie["numero"], partie["titre"], medias.get("photo"))
        partie["rendre"](prs)
    b.fin(prs)

    buffer = io.BytesIO()
    prs.save(buffer)
    resume = {
        "nbSlides": len(prs.slides),
        "parties": [p["titre"] for p in parties],
        "brouillon": projet,
        "cyclesNonClotures": data["cyclesNonClotures"],
        "avertissements": avertissements,
    }
    return buffer.getvalue(), resume
