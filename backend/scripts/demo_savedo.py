"""Mission de démonstration SAVEDO SA (données FICTIVES) pour le rapport final.

Utilisée par tests/test_rapport.py, et en ligne de commande pour alimenter la base de dev
(essai manuel de la génération et de l'éditeur ONLYOFFICE) :

    python -m scripts.demo_savedo --email prenom.nom@y3ac.com [--non-clotures B,C]

L'employé désigné par --email est ajouté à l'équipe de la mission.
"""

import argparse
import os
import uuid

from bson import ObjectId
from openpyxl import Workbook

from app.services.cycle_service import CYCLES

# Comptes de la balance : numéro, libellé, solde de clôture N-1, mouvements débit N, crédit N.
# Solde positif = débiteur, négatif = créditeur. Ouverture N = clôture N-1 (sauf 411100, cf. ECART).
COMPTES = [
    ("101300", "Capital souscrit, appelé, versé", -50_000_000, 0, 0),
    ("111000", "Réserve légale", -10_000_000, 0, 0),
    ("121000", "Report à nouveau créditeur", -84_250_000, 0, 41_500_000),
    ("131000", "Résultat net : bénéfice", -41_500_000, 41_500_000, 0),
    ("162000", "Emprunts auprès des établissements de crédit", -120_000_000, 30_000_000, 0),
    ("196100", "Provision pour indemnités de fin de carrière", -18_400_000, 0, 2_600_000),
    ("213100", "Logiciels", 12_500_000, 3_200_000, 0),
    ("231000", "Bâtiments industriels", 310_000_000, 0, 0),
    ("244100", "Matériel de bureau", 24_800_000, 6_450_000, 0),
    ("245100", "Matériel automobile", 58_300_000, 21_000_000, 0),
    ("281300", "Amortissements des logiciels", -7_500_000, 0, 2_500_000),
    ("283100", "Amortissements des bâtiments", -93_000_000, 0, 15_500_000),
    ("284410", "Amortissements du matériel de bureau", -12_400_000, 0, 4_960_000),
    ("311000", "Marchandises", 46_750_000, 52_300_000, 46_750_000),
    ("401100", "Fournisseurs", -68_420_000, 512_300_000, 531_900_000),
    ("408100", "Fournisseurs, factures non parvenues", -4_150_000, 4_150_000, 3_870_000),
    ("409100", "Fournisseurs, avances versées", 2_300_000, 1_500_000, 2_300_000),
    ("411100", "Clients", 135_600_000, 1_245_000_000, 1_198_400_000),
    ("416100", "Créances douteuses", 9_800_000, 0, 0),
    ("419100", "Clients, avances reçues", -6_000_000, 6_000_000, 4_250_000),
    ("421000", "Personnel, avances et acomptes", 1_250_000, 3_600_000, 3_850_000),
    ("422000", "Personnel, rémunérations dues", -14_300_000, 178_900_000, 181_250_000),
    ("431100", "Caisse nationale de prévoyance sociale", -6_820_000, 41_200_000, 42_050_000),
    ("441000", "État, impôt sur les bénéfices", -9_600_000, 9_600_000, 11_840_000),
    ("443100", "TVA facturée sur ventes", -18_250_000, 214_300_000, 219_500_000),
    ("445200", "TVA récupérable sur achats", 7_480_000, 88_900_000, 87_100_000),
    ("447200", "Impôts sur traitements et salaires", -3_910_000, 25_700_000, 26_150_000),
    ("471800", "Comptes d'attente à régulariser", 1_870_000, 650_000, 0),
    ("521100", "Banque SGCI", 54_300_000, 1_312_000_000, 1_296_450_000),
    ("521200", "Banque NSIA", 18_760_000, 203_500_000, 211_900_000),
    ("571100", "Caisse siège", 640_000, 12_300_000, 12_115_000),
    ("601100", "Achats de marchandises", 0, 498_600_000, 0),
    ("603100", "Variation des stocks de marchandises", 0, 46_750_000, 52_300_000),
    ("605200", "Fournitures non stockables – électricité", 0, 18_450_000, 0),
    ("622300", "Locations de bâtiments", 0, 36_000_000, 0),
    ("624100", "Entretien et réparations", 0, 7_820_000, 0),
    ("641100", "Impôts fonciers", 0, 4_200_000, 0),
    ("661100", "Appointements, salaires et commissions", 0, 212_400_000, 0),
    ("664100", "Charges sociales", 0, 39_870_000, 0),
    ("671100", "Intérêts des emprunts", 0, 9_360_000, 0),
    ("681300", "Dotations aux amortissements", 0, 22_960_000, 0),
    ("701100", "Ventes de marchandises", 0, 0, 1_052_300_000),
    ("706100", "Services vendus", 0, 0, 132_700_000),
    ("891000", "Impôts sur le résultat", 0, 11_840_000, 0),
]
# Écart d'intangibilité volontaire : ouverture 2025 du compte clients ≠ clôture 2024.
ECART = {"411100": 1_250_000}

CONSTATS = {
    "A": [
        {"famille": "Gouvernance", "severite": "Élevé",
         "constat": "Aucun procès-verbal d'inventaire de caisse n'a été établi au 31/12/2025.",
         "recommandation": "Procéder à un inventaire physique de la caisse à chaque clôture, consigné dans un procès-verbal signé par deux personnes habilitées.",
         "titre": "Absence d'inventaire de caisse", "risques": ["Risque sur l'exactitude du solde de caisse", "Risque de détournement non détecté"],
         "client": "La direction prend acte du constat.", "reponse": "Un inventaire mensuel sera mis en place dès janvier 2026 sous la responsabilité du DAF."},
    ],
    "B": [
        {"famille": "Évaluation", "severite": "Moyen",
         "constat": "Les créances douteuses (compte 416100) n'ont fait l'objet d'aucune dépréciation alors qu'elles ont plus de deux ans d'ancienneté.",
         "recommandation": "Constituer une dépréciation des créances douteuses sur la base d'une revue individuelle des dossiers contentieux.",
         "client": "Les dossiers sont suivis par notre avocat.", "reponse": "Une revue contradictoire sera organisée avant l'arrêté des comptes."},
    ],
    "C": [
        {"famille": "Comptabilisation", "severite": "Faible",
         "constat": "Des factures d'électricité de décembre 2025 ont été enregistrées en compte d'attente.",
         "recommandation": "Reclasser les factures en charges de l'exercice.",
         "client": "", "reponse": "Accord sur le reclassement."},
    ],
    "E": [
        {"famille": "Gouvernance", "severite": "Moyen",
         "constat": "Le fichier des immobilisations n'est pas rapproché de la comptabilité et aucun inventaire physique n'a été réalisé.",
         "recommandation": "Réaliser un inventaire physique des immobilisations et rapprocher le fichier des immobilisations de la comptabilité.",
         "titre": "Absence d'inventaire des immobilisations", "risques": ["Exhaustivité des immobilisations"],
         "client": "", "reponse": "Inventaire prévu au premier trimestre 2026."},
    ],
    "K": [
        {"famille": "Système d'information", "severite": "Faible",
         "constat": "Le logiciel comptable autorise la modification d'écritures validées sans trace d'audit.",
         "recommandation": "Activer la piste d'audit du logiciel et restreindre les droits de modification.",
         "titre": "Piste d'audit du logiciel comptable", "risques": ["Fiabilité des données comptables"],
         "client": "", "reponse": ""},
    ],
}

# Ajustements (Phase 4, conclusion du cycle) : (cycle, compte, libellé, sens, montant).
AJUSTEMENTS = [
    ("B", "659100", "Dépréciation des créances douteuses", "Débit", 4_900_000),
    ("B", "491100", "Dépréciation des créances douteuses", "Crédit", 4_900_000),
    ("C", "605200", "Reclassement factures électricité décembre", "Débit", 650_000),
    ("C", "471800", "Reclassement factures électricité décembre", "Crédit", 650_000),
    ("F", "661100", "Régularisation congés payés 2025", "Débit", 3_450_000),
    ("F", "428200", "Régularisation congés payés 2025", "Crédit", 3_450_000),
    ("E", "681300", "Complément de dotation 2025", "Débit", 1_240_000),
    ("E", "284410", "Complément de dotation 2025", "Crédit", 1_240_000),
]

SYNTHESES = {
    "A": "Les soldes bancaires ont été rapprochés des relevés et des états de rapprochement au 31/12/2025 sans écart.\nLe solde de caisse n'est pas appuyé par un procès-verbal d'inventaire.",
    "B": "Le chiffre d'affaires a été rapproché du journal des ventes. Les créances douteuses doivent être dépréciées.",
    "C": "Les dettes fournisseurs ont été rapprochées de la balance auxiliaire sans écart significatif.",
    "E": "Les acquisitions de l'exercice sont justifiées par des factures. Un complément de dotation aux amortissements est proposé.",
    "F": "La masse salariale comptabilisée a été rapprochée du livre de paie mensuel.",
}


def ecrire_balance(chemin, annee):
    """Balance au format positionnel à 8 colonnes (cf. balance_engine.FALLBACK_COLUMN_INDEX)."""
    wb = Workbook()
    ws = wb.active
    ws.append(["Compte", "Intitulé", "Débit ouverture", "Crédit ouverture", "Débit mouvements", "Crédit mouvements",
               "Débit clôture", "Crédit clôture"])
    for numero, libelle, cloture_n1, mvt_d, mvt_c in COMPTES:
        if annee == 2024:
            ouverture, debit, credit = 0, max(cloture_n1, 0), max(-cloture_n1, 0)
            mvt_d, mvt_c = debit, credit
        else:
            ouverture = cloture_n1 + ECART.get(numero, 0)
        cloture = ouverture + mvt_d - mvt_c
        ws.append([numero, libelle, max(ouverture, 0), max(-ouverture, 0), mvt_d, mvt_c, max(cloture, 0), max(-cloture, 0)])
    wb.save(chemin)


def solde_cloture_2025(numero):
    for n, _, cloture_n1, mvt_d, mvt_c in COMPTES:
        if n == numero:
            return cloture_n1 + ECART.get(n, 0) + mvt_d - mvt_c
    raise KeyError(numero)


def _id():
    return uuid.uuid4().hex


def creer_mission_demo(db, uploads_dir, equipe_ids, non_clotures=(), avec_saisie=True):
    """Crée client, mission, balances, révisions (Phase 4/5), papier de travail, saisie Phase 6
    et restitution. Renvoie un dict d'ids utiles aux tests."""
    client_id = db.clients.insert_one({
        "raisonSociale": "SAVEDO SA", "secteurActivite": "Distribution", "formeJuridique": "SA",
        "rccm": "CI-ABJ-2009-B-1234", "ville": "Abidjan", "adresse": "Zone 4, Marcory, Abidjan",
    }).inserted_id
    mission_id = str(db.missions.insert_one({
        "clientId": str(client_id), "exercice": "2025", "phase": "6/7 · Restitution client", "statut": "En cours",
        "dateDebut": "2026-01-15", "echeance": "2026-04-30", "manager": "", "senior": "",
        "equipe": list(equipe_ids), "createdAt": None,
        "ficheSignaletique": {"valeurs": {
            "denomination": "SAVEDO SA", "sigle": "SAVEDO", "formeJuridique": "société anonyme avec conseil d'administration",
            "capitalSocial": "FCFA 50 000 000", "anneeCreation": "2009", "adresseGeographique": "à Abidjan, Zone 4, Marcory",
            "descriptionActivite": "Distribution de produits alimentaires et d'équipements ménagers.",
            "gerant": "M. Jean KOUASSI, Président Directeur Général", "rccm": "CI-ABJ-2009-B-1234", "effectif": "86",
            "associes": "SAVEDO Holding : 70 %\nM. Jean KOUASSI : 30 %",
        }},
    }).inserted_id)

    dossier = os.path.join(uploads_dir, mission_id)
    os.makedirs(dossier, exist_ok=True)
    documents = []
    for annee in (2025, 2024):
        nom = f"{uuid.uuid4().hex}_balance_{annee}.xlsx"
        ecrire_balance(os.path.join(dossier, nom), annee)
        documents.append({"id": _id(), "description": f"Balance générale {annee}", "version": "Electronique",
                          "dateDemande": "-", "dateReception": "2026-01-20", "statut": "Reçu",
                          "fileName": f"balance_{annee}.xlsx", "fileUrl": f"/uploads/{mission_id}/{nom}"})
    db.missions.update_one({"_id": ObjectId(mission_id)},
                           {"$set":{"documents": {"categories": [{"title": "DOCUMENT GENERAUX DE LA SOCIETE", "documents": documents}]}}})

    ids = {"missionId": mission_id, "constats": {}, "ajustements": {}}
    for cycle in CYCLES:
        code = cycle["code"]
        constats = []
        for c in CONSTATS.get(code, []):
            cid = _id()
            ids["constats"].setdefault(code, []).append(cid)
            constats.append({"id": cid, "famille": c["famille"], "constat": c["constat"], "severite": c["severite"],
                             "recommandation": c["recommandation"], "statut": "Noté"})
        ajustements = []
        for (cc, compte, libelle, sens, montant) in AJUSTEMENTS:
            if cc == code:
                aid = _id()
                ids["ajustements"].setdefault(code, []).append(aid)
                ajustements.append({"id": aid, "compte": compte, "libelle": libelle, "sens": sens, "montant": montant})
        db.cycle_revisions.insert_one({
            "missionId": mission_id, "code": code,
            "statut": "revue_senior" if code in non_clotures else "cloture",
            "priseConnaissance": {"processus": "", "risques": ["Exhaustivité", "Évaluation"], "referentiel": ""},
            "lead": {"commentaires": {"521100": "Rapproché du relevé bancaire"} if code == "A" else {}},
            "justification": {"assertions": {}, "pieces": [], "commentaire": {"texte": "", "par": None, "le": None}},
            "constats": constats,
            "conclusion": {"synthese": SYNTHESES.get(code, ""), "ajustements": ajustements, "decision": "justifie"},
            "version": 3, "updatedAt": "2026-03-01T10:00:00+00:00",
        })

    # Papier de travail intégré (cycle F) : cadrage mensuel avec formules Jspreadsheet.
    lignes = [[m, lp, cpt, f"=B{i}-C{i}"] for i, (m, lp, cpt) in enumerate(
        [("Janvier", 17_500_000, 17_500_000), ("Février", 17_600_000, 17_600_000), ("Mars", 17_650_000, 17_400_000)],
        start=1)]
    lignes.append(["Total", "=SUM(B1:B3)", "=SUM(C1:C3)", "=SUM(D1:D3)"])
    paper_id = db.working_papers.insert_one({
        "missionId": mission_id, "cycleCode": "F", "etape": "4d", "titre": "PT — Cadrage paie", "mode": "integre",
        "lien": {}, "feuilles": [{"nom": "Cadrage", "colonnes": ["Mois", "Livre de paie", "Comptabilité", "Écart"],
                                  "data": lignes}], "version": 1,
    }).inserted_id
    ids["paperId"] = str(paper_id)

    if avec_saisie:
        ecriture_b = {"id": _id(), "cycleCode": "B", "libelle": "Dépréciation des créances douteuses",
                      "ajustementIds": ids["ajustements"]["B"]}
        ecriture_c = {"id": _id(), "cycleCode": "C", "libelle": "Reclassement des factures d'électricité",
                      "ajustementIds": ids["ajustements"]["C"]}
        saisie_constats = {}
        for code, liste in CONSTATS.items():
            for c, cid in zip(liste, ids["constats"][code]):
                if c.get("titre") or c.get("risques"):
                    saisie_constats[cid] = {"titre": c.get("titre", ""), "risques": c.get("risques", []), "retenirCI": None}
        # Le constat du cycle A (famille Gouvernance) est retenu par défaut ; on retient aussi celui du cycle E
        # (Gouvernance, par défaut) et on exclut celui du cycle K (Système d'information) explicitement.
        saisie_constats[ids["constats"]["K"][0]]["retenirCI"] = False
        db.rapports.insert_one({
            "missionId": mission_id, "statut": None, "compteurVersion": 0, "versions": [], "saisieVersion": 1,
            "medias": {}, "session": None, "emission": None, "pdf": None,
            "saisie": {
                "dateRapport": "2026-04",
                "lettreMission": {"date": "15 janvier 2026", "prestations": "une mission de révision des comptes et d'établissement des états financiers"},
                "contexteComplement": "",
                "actionnariat": "",
                "evenements": [{"id": _id(), "titre": "Changement de logiciel comptable",
                                "texte": "SAVEDO SA a migré vers un nouveau logiciel comptable au 1er juillet 2025."}],
                "intangibiliteCommentaire": "L'écart porte sur le compte clients et doit être corrigé dans la balance d'ouverture.",
                "constats": saisie_constats,
                "points": {
                    "B": [{"id": _id(), "titre": "Créances douteuses",
                           "texte": "Les créances douteuses s'élèvent à FCFA 9 800 000 sans dépréciation. Nous proposons l'écriture ci-dessous.",
                           "blocs": [{"id": _id(), "type": "ecriture", "titre": "", "ecritureId": ecriture_b["id"]}]}],
                    "F": [{"id": _id(), "titre": "Cadrage de la masse salariale",
                           "texte": "Le cadrage mensuel entre le livre de paie et la comptabilité est présenté ci-dessous.",
                           "blocs": [{"id": _id(), "type": "papier", "titre": "Cadrage livre de paie / comptabilité",
                                      "paperId": str(paper_id), "feuille": "Cadrage"}]}],
                    "H": [{"id": _id(), "titre": "Variation des capitaux propres",
                           "texte": "Le résultat 2024 a été affecté en report à nouveau conformément au procès-verbal d'assemblée.",
                           "blocs": [{"id": _id(), "type": "variation", "titre": "", "prefixes": ["10", "11", "12", "13"]}]}],
                    "J": [{"id": _id(), "titre": "Compte d'attente 471800",
                           "texte": "Extrait du grand livre du compte d'attente :",
                           "blocs": [{"id": _id(), "type": "grand_livre", "titre": "", "grandLivre": {
                               "source": "saisie", "filtre": {"comptes": ["4718"], "du": "", "au": ""},
                               "lignes": [
                                   {"date": "15/12/2025", "journal": "BQ", "piece": "742", "compte": "471800",
                                    "compteTiers": "", "libelle": "Facture CIE décembre", "debit": 650_000, "credit": None},
                                   {"date": "31/12/2025", "journal": "OD", "piece": "801", "compte": "471800",
                                    "compteTiers": "", "libelle": "Solde à nouveau", "debit": 1_870_000, "credit": None},
                               ]}}]}],
                },
                "ecritures": [ecriture_b, ecriture_c],
            },
        })
        db.restitutions.insert_one({
            "missionId": mission_id, "version": 1,
            "reunion": {"date": "2026-04-10", "lieu": "Siège de SAVEDO SA",
                        "participantsCabinet": [{"id": None, "nom": "Awa DIALLO"}],
                        "participantsClient": [{"nom": "Jean KOUASSI", "fonction": "PDG"}, {"nom": "Marie YAO", "fonction": "DAF"}]},
            "commentaires": {
                cid: {"commentaireClient": c["client"], "reponseManagement": c["reponse"]}
                for code, liste in CONSTATS.items() for c, cid in zip(liste, ids["constats"][code])
                if c["client"] or c["reponse"]
            },
        })
    return ids


def main():
    from app.db.session import db
    from app.services.document_service import UPLOADS_DIR

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True, help="Employé ajouté à l'équipe de la mission de démonstration")
    parser.add_argument("--non-clotures", default="", help="Codes de cycles laissés en revue, ex. B,C")
    args = parser.parse_args()
    employee = db.employees.find_one({"email": args.email.strip().lower()})
    if employee is None:
        raise SystemExit(f"Employé introuvable : {args.email}")
    non_clotures = [c.strip().upper() for c in args.non_clotures.split(",") if c.strip()]
    ids = creer_mission_demo(db, UPLOADS_DIR, [str(employee["_id"])], non_clotures)
    print(f"Mission de démonstration SAVEDO SA créée : {ids['missionId']}")


if __name__ == "__main__":
    main()
