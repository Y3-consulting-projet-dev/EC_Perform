import re

import openpyxl

TOLERANCE = 1.0

# Colonnes positionnelles d'une balance à 8 colonnes (pas d'en-tête exploitable) :
# A=compte, B=libellé, C=débit ouverture, D=crédit ouverture,
# E=débit mouvement, F=crédit mouvement, G=débit clôture, H=crédit clôture.
COLUMN_INDEX = {
    "numero": 0,
    "libelle": 1,
    "debitOuverture": 2,
    "creditOuverture": 3,
    "debitMouvement": 4,
    "creditMouvement": 5,
    "debitCloture": 6,
    "creditCloture": 7,
}


def _to_float(value):
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(" ", "").replace(",", ".")
    if not text:
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def _solde(debit, credit):
    return debit - credit


def format_montant(value):
    rounded = round(value)
    sign = "-" if rounded < 0 else ""
    digits = str(abs(rounded))
    groups = []
    while digits:
        groups.insert(0, digits[-3:])
        digits = digits[:-3]
    return sign + " ".join(groups)


def parse_balance_file(path):
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        sheet = workbook.worksheets[0]
        comptes = []
        for row_index, row in enumerate(sheet.iter_rows(values_only=True)):
            if row_index == 0:
                continue
            if not row or len(row) <= COLUMN_INDEX["numero"]:
                continue
            numero = row[COLUMN_INDEX["numero"]]
            if numero is None:
                continue
            numero = str(numero).strip()
            if not re.match(r"^\d+$", numero):
                continue
            comptes.append(
                {
                    "numero": numero,
                    "libelle": str(row[COLUMN_INDEX["libelle"]] or "").strip(),
                    "debitOuverture": _to_float(row[COLUMN_INDEX["debitOuverture"]] if len(row) > 2 else None),
                    "creditOuverture": _to_float(row[COLUMN_INDEX["creditOuverture"]] if len(row) > 3 else None),
                    "debitMouvement": _to_float(row[COLUMN_INDEX["debitMouvement"]] if len(row) > 4 else None),
                    "creditMouvement": _to_float(row[COLUMN_INDEX["creditMouvement"]] if len(row) > 5 else None),
                    "debitCloture": _to_float(row[COLUMN_INDEX["debitCloture"]] if len(row) > 6 else None),
                    "creditCloture": _to_float(row[COLUMN_INDEX["creditCloture"]] if len(row) > 7 else None),
                }
            )
        return comptes
    finally:
        workbook.close()


def _explication_intangibilite(statut, numero, solde_n, solde_n_moins1, ecart):
    if statut == "Nouveau":
        return (
            f"Le compte {numero} est présent dans l'exercice N avec un solde d'ouverture de "
            f"{format_montant(solde_n)}, mais n'existait pas dans l'exercice N-1. Cela peut indiquer une "
            f"création de compte, un reclassement ou une erreur de saisie."
        )
    if statut == "Disparu":
        return (
            f"Le compte {numero} était présent dans l'exercice N-1 avec un solde de clôture de "
            f"{format_montant(solde_n_moins1)}, mais n'existe plus dans l'exercice N. Cela peut indiquer une "
            f"clôture de compte, un reclassement ou une erreur de saisie."
        )
    if statut == "Écart":
        return (
            f"Le compte {numero} présente un écart de {format_montant(ecart)} entre le solde de clôture N-1 "
            f"({format_montant(solde_n_moins1)}) et le solde d'ouverture N ({format_montant(solde_n)}). Le "
            f"principe d'intangibilité du bilan d'ouverture impose que ces deux soldes soient strictement "
            f"identiques."
        )
    return (
        f"Le solde d'ouverture N ({format_montant(solde_n)}) correspond exactement au solde de clôture N-1 "
        f"({format_montant(solde_n_moins1)})."
    )


def compute_intangibilite(comptes_n, comptes_n_moins1):
    par_numero_n = {c["numero"]: c for c in comptes_n}
    par_numero_n_moins1 = {c["numero"]: c for c in comptes_n_moins1}
    tous_numeros = set(par_numero_n) | set(par_numero_n_moins1)

    lignes = []
    for numero in tous_numeros:
        compte_n = par_numero_n.get(numero)
        compte_n_moins1 = par_numero_n_moins1.get(numero)

        solde_n = _solde(compte_n["debitOuverture"], compte_n["creditOuverture"]) if compte_n else 0.0
        solde_n_moins1 = (
            _solde(compte_n_moins1["debitCloture"], compte_n_moins1["creditCloture"]) if compte_n_moins1 else 0.0
        )
        ecart = solde_n - solde_n_moins1

        if compte_n and not compte_n_moins1:
            statut = "Nouveau"
        elif compte_n_moins1 and not compte_n:
            statut = "Disparu"
        elif abs(ecart) < TOLERANCE:
            statut = "OK"
        else:
            statut = "Écart"

        libelle = (compte_n or compte_n_moins1)["libelle"]
        lignes.append(
            {
                "compte": numero,
                "libelle": libelle,
                "bilanOuvertureN": format_montant(solde_n) if compte_n else "N/A",
                "bilanClotureNMoins1": format_montant(solde_n_moins1) if compte_n_moins1 else "N/A",
                "ecart": format_montant(ecart),
                "statut": statut,
                "explication": _explication_intangibilite(statut, numero, solde_n, solde_n_moins1, ecart),
                "_sortKey": (0 if statut != "OK" else 1, -abs(ecart)),
            }
        )

    lignes.sort(key=lambda l: (l["_sortKey"], l["compte"]))
    for index, ligne in enumerate(lignes, start=1):
        ligne["n"] = index
        del ligne["_sortKey"]

    ecarts = sum(1 for l in lignes if l["statut"] != "OK")
    return {"totalComptes": len(lignes), "ecarts": ecarts, "comptes": lignes}


# Sens normal du solde par classe de compte, selon le plan comptable SYSCOHADA.
CLASSE_SENS_NORMAL = {
    "1": "CRÉDITEUR",
    "2": "DÉBITEUR",
    "3": "DÉBITEUR",
    "4": "Variable selon sous-classe",
    "5": "DÉBITEUR",
    "6": "DÉBITEUR",
    "7": "CRÉDITEUR",
}

CLASSE_NATURE = {
    "1": "Capital social, réserves, report à nouveau, subventions d'investissement, provisions "
    "réglementées, emprunts et dettes assimilées.",
    "2": "Immobilisations incorporelles, corporelles, financières, avances sur immobilisations, "
    "amortissements et dépréciations.",
    "3": "Stocks de marchandises, matières, en-cours de production, produits, dépréciations de stocks.",
    "4": "Fournisseurs, clients, personnel, organismes sociaux, État, groupe et associés, comptes "
    "débiteurs/créditeurs divers.",
    "5": "Banques, caisse, valeurs mobilières de placement, virements internes.",
    "6": "Achats, charges externes, impôts et taxes, charges de personnel, dotations, charges financières.",
    "7": "Ventes, production stockée/immobilisée, subventions d'exploitation, produits financiers.",
}

# Comptes qui doivent obligatoirement être soldés : (préfixe, libellé, gravité, motif).
COMPTES_A_SOLDER = [
    ("471", "Comptes transitoires ou d'attente", "Critique",
     "Tout solde indique des écritures en suspens non régularisées ; à analyser ligne par ligne."),
    ("58", "Virements internes", "Critique",
     "Tout solde indique une erreur de lettrage ou un virement non comptabilisé des deux côtés."),
    ("422", "Personnel - Rémunérations dues", "Moyenne",
     "Doit être soldé lors de la paie suivante ; un solde ancien peut indiquer une erreur de lettrage."),
    ("4387", "Organismes sociaux - Charges à payer", "Moyenne",
     "Doit être soldé lors de la déclaration sociale suivante."),
    ("44551", "TVA à décaisser", "Critique",
     "Doit être soldée lors du paiement de la TVA ; un solde ancien indique un risque fiscal."),
]


def _sens_attendu(numero):
    if not numero or not numero[0].isdigit():
        return "BOTH"
    classe = numero[0]
    if classe == "1":
        if numero.startswith(("105", "12", "109", "129", "1309")):
            return "BOTH"
        return "C"
    if classe == "2":
        return "C" if numero.startswith(("28", "29")) else "D"
    if classe == "3":
        return "C" if numero.startswith("39") else "D"
    if classe == "4":
        if numero.startswith("40"):
            return "BOTH" if numero.startswith("4091") else "C"
        if numero.startswith("41"):
            return "BOTH" if numero.startswith("4191") else "D"
        if numero.startswith(("42", "43", "49")):
            return "C"
        return "BOTH"
    if classe == "5":
        if numero.startswith(("519", "58")):
            return "BOTH"
        return "C" if numero.startswith("59") else "D"
    if classe == "6":
        return "D"
    if classe == "7":
        return "C"
    return "BOTH"


def _compte_a_solder(numero):
    for prefixe, libelle, gravite, motif in COMPTES_A_SOLDER:
        if numero.startswith(prefixe):
            return libelle, gravite, motif
    if numero and numero[0] in ("6", "7"):
        return (
            "Compte de gestion (classe 6/7)",
            "Moyenne",
            "Doit être soldé en fin d'exercice par virement au compte de résultat (12) ; aucun solde ne "
            "doit subsister à l'ouverture de l'exercice suivant.",
        )
    return None


def compute_vraisemblance(comptes):
    tableau_classes = {
        classe: {
            "classe": classe,
            "sensNormal": CLASSE_SENS_NORMAL[classe],
            "nature": CLASSE_NATURE[classe],
            "anomalies": [],
        }
        for classe in CLASSE_SENS_NORMAL
    }
    comptes_non_soldes = []
    anomalies_signe = 0

    for c in comptes:
        numero = c["numero"]
        classe = numero[0] if numero and numero[0].isdigit() else None
        solde = _solde(c["debitCloture"], c["creditCloture"])
        message = None

        if numero.startswith("53") and solde < -TOLERANCE:
            message = (
                f"Compte de caisse {numero} avec un solde créditeur de {format_montant(-solde)} FCFA : "
                "impossible physiquement, une caisse ne peut être créditrice. Erreur certaine à corriger."
            )
        elif classe == "3" and not numero.startswith("39") and solde < -TOLERANCE:
            message = (
                f"Compte de stock {numero} avec un solde créditeur de {format_montant(-solde)} FCFA : "
                "anomalie à investiguer (écritures d'inventaire, erreur de saisie ou de valorisation)."
            )
        else:
            sens = _sens_attendu(numero)
            if sens == "D" and solde < -TOLERANCE:
                message = (
                    f"Compte {numero} (classe {classe}) attendu débiteur mais présente un solde créditeur "
                    f"de {format_montant(-solde)} FCFA."
                )
            elif sens == "C" and solde > TOLERANCE:
                message = (
                    f"Compte {numero} (classe {classe}) attendu créditeur mais présente un solde débiteur "
                    f"de {format_montant(solde)} FCFA."
                )

        if message and classe in tableau_classes:
            anomalies_signe += 1
            tableau_classes[classe]["anomalies"].append(
                {"compte": numero, "libelle": c["libelle"], "solde": format_montant(solde), "message": message}
            )

        a_solder = _compte_a_solder(numero) if numero else None
        if a_solder and abs(solde) >= TOLERANCE:
            libelle, gravite, motif = a_solder
            comptes_non_soldes.append(
                {
                    "compte": numero,
                    "libelle": c["libelle"],
                    "solde": format_montant(solde),
                    "gravite": gravite,
                    "motif": f"{libelle} — {motif}",
                }
            )

    total = len(comptes)
    ok = anomalies_signe == 0 and not comptes_non_soldes

    if ok:
        explication = (
            f"Le système a vérifié le sens (débit/crédit) des soldes de {total} compte(s) selon les règles "
            "SYSCOHADA, ainsi que le solde des comptes devant être obligatoirement soldés. Aucune anomalie "
            "détectée."
        )
    else:
        explication = (
            f"Le système a vérifié le sens (débit/crédit) des soldes de {total} compte(s) selon les règles "
            f"SYSCOHADA. {anomalies_signe} compte(s) présentent un sens anormal et {len(comptes_non_soldes)} "
            "compte(s) devant être soldés portent encore un solde."
        )

    return {
        "statut": "OK" if ok else "Erreur",
        "comptesVerifies": total,
        "anomaliesSigne": anomalies_signe,
        "comptesNonSoldes": len(comptes_non_soldes),
        "explication": explication,
        "tableauClasses": list(tableau_classes.values()),
        "listeComptesNonSoldes": comptes_non_soldes,
    }


def compute_coherence(comptes):
    total_debits = sum(c["debitCloture"] for c in comptes)
    total_credits = sum(c["creditCloture"] for c in comptes)
    equilibre_ok = abs(total_debits - total_credits) < TOLERANCE

    if equilibre_ok:
        equilibre_explication = (
            f"Le système a vérifié que le total des débits ({format_montant(total_debits)} FCFA) est "
            f"strictement égal au total des crédits ({format_montant(total_credits)} FCFA) en additionnant "
            f"les colonnes 'Débit fin' et 'Crédit fin' de tous les comptes."
        )
    else:
        equilibre_explication = (
            f"Le système a constaté que le total des débits ({format_montant(total_debits)} FCFA) n'est PAS "
            f"égal au total des crédits ({format_montant(total_credits)} FCFA) — écart de "
            f"{format_montant(total_debits - total_credits)} FCFA en additionnant les colonnes 'Débit fin' et "
            f"'Crédit fin' de tous les comptes."
        )

    comptes_en_erreur = []
    for c in comptes:
        solde_ouverture = _solde(c["debitOuverture"], c["creditOuverture"])
        mouvements = _solde(c["debitMouvement"], c["creditMouvement"])
        cloture_attendue = solde_ouverture + mouvements
        cloture_balance = _solde(c["debitCloture"], c["creditCloture"])
        ecart = cloture_attendue - cloture_balance
        if abs(ecart) >= TOLERANCE:
            comptes_en_erreur.append(
                {
                    "compte": c["numero"],
                    "libelle": c["libelle"],
                    "soldeOuverture": format_montant(solde_ouverture),
                    "mouvements": format_montant(mouvements),
                    "soldeClotureAttendu": format_montant(cloture_attendue),
                    "soldeClotureBalance": format_montant(cloture_balance),
                    "ecart": format_montant(ecart),
                }
            )

    total = len(comptes)
    non_respectee = len(comptes_en_erreur)
    respectee = total - non_respectee

    if non_respectee > 0:
        formule_description = (
            f"Le système a vérifié la formule 'Solde de clôture = Solde d'ouverture + Mouvements de période' "
            f"pour {total} comptes. {respectee} comptes respectent la formule, mais {non_respectee} comptes "
            f"présentent des ERREURS. Les comptes en erreur sont listés ci-dessous avec les détails de "
            f"l'écart détecté."
        )
    else:
        formule_description = (
            f"Le système a vérifié la formule 'Solde de clôture = Solde d'ouverture + Mouvements de période' "
            f"pour {total} comptes. Les {total} comptes respectent la formule."
        )

    return {
        "equilibreOk": equilibre_ok,
        "erreurs": non_respectee,
        "equilibre": {
            "totalDebits": format_montant(total_debits),
            "totalCredits": format_montant(total_credits),
            "nombreComptes": total,
            "explication": equilibre_explication,
            "commentVerifier": (
                "Additionnez toutes les valeurs de la colonne 'Débit fin' de tous les comptes, puis "
                "additionnez toutes les valeurs de la colonne 'Crédit fin'. Les deux totaux doivent être "
                "identiques."
            ),
        },
        "formule": {
            "libelle": "Solde de clôture = Solde d'ouverture + Mouvements de période",
            "description": formule_description,
            "comptesVerifies": total,
            "formuleRespectee": respectee,
            "formuleNonRespectee": non_respectee,
            "comptesEnErreur": comptes_en_erreur,
        },
    }
