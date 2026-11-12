"""Textes du rapport : paragraphes types du cabinet (statiques) et phrases-gabarits.

Règle : une phrase-gabarit n'est produite que si TOUTES les valeurs qu'elle insère sont
renseignées. Les valeurs sont insérées telles que saisies (aucune reformulation) ; une donnée
absente fait disparaître la phrase, jamais remplacée par un texte inventé.
"""

CABINET = "Y³ Audit et Conseils"

PARTIES = {
    "contexte": "Contexte et objectifs de la mission",
    "controle_interne": "Appréciation du dispositif de contrôle interne",
    "cycles": "Travaux de révision par cycle",
    "regularisation": "Travaux de régularisation",
}

MOIS = [
    "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
    "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre",
]

# --- Contexte et objectifs (paragraphes types du cabinet) ---------------------------------

def contexte_paragraphes(client, exercice, lettre_date, prestations):
    paragraphes = []
    if lettre_date and prestations:
        paragraphes.append(
            f"Conformément aux termes de notre lettre de mission du {lettre_date}, {CABINET} fournit à "
            f"{client} {prestations} au titre de l'exercice {exercice}."
        )
    elif lettre_date:
        paragraphes.append(
            f"Conformément aux termes de notre lettre de mission du {lettre_date}, {CABINET} intervient auprès de "
            f"{client} au titre de l'exercice {exercice}."
        )
    paragraphes.extend(
        [
            f"Ces travaux sont exécutés à partir des informations et documents que {client} met à notre disposition, "
            "dans le respect des lois et réglementations en vigueur, notamment des dispositions du référentiel "
            "comptable SYSCOHADA, du Code Général des Impôts, du Code du travail, de la Convention Collective "
            "Interprofessionnelle et du Code de prévoyance sociale.",
            f"Ce document a été établi uniquement à des fins de discussion avec la direction de {client} dans le cadre "
            "de la finalisation de la revue des comptes en vue de l'élaboration des états financiers. Il ne peut en "
            "aucun cas être modifié ou diffusé sans notre approbation. Il ne constitue pas un rapport d'audit formel "
            "exprimant une opinion sur les comptes et n'a pas vocation à être communiqué à des tiers.",
            "Nos diligences ont été réalisées conformément aux dispositions du Système comptable OHADA et de l'Acte "
            "uniforme relatif au droit comptable et à l'information financière de l'OHADA applicables pour "
            "l'établissement des états financiers.",
        ]
    )
    return paragraphes


def presentation_paragraphes(valeurs):
    """Présentation de l'entité à partir de la fiche signalétique (Phase 1)."""
    v = {k: (valeurs.get(k) or "").strip() for k in valeurs}
    nom = v.get("denomination", "")
    out = []
    if nom and v.get("formeJuridique"):
        phrase = f"{nom} est une {v['formeJuridique']}"
        if v.get("capitalSocial"):
            phrase += f" au capital de {v['capitalSocial']}"
        if v.get("anneeCreation"):
            phrase += f", créée en {v['anneeCreation']}"
        if v.get("adresseGeographique"):
            phrase += f", dont le siège social est situé {_premiere_ligne(v['adresseGeographique'])}"
        out.append(phrase + ".")
    activite = v.get("descriptionActivite") or v.get("objet")
    if activite:
        out.append(f"Activité : {_une_ligne(activite)}")
    if v.get("secteurActivite"):
        out.append(f"Secteur d'activité : {v['secteurActivite']}")
    if v.get("gerant"):
        out.append(f"Représentant légal : {v['gerant']}")
    for cle, libelle in (("rccm", "N° RCCM"), ("numeroCC", "N° CC"), ("effectif", "Effectif")):
        if v.get(cle):
            out.append(f"{libelle} : {v[cle]}")
    return out


def _premiere_ligne(texte):
    return texte.strip().splitlines()[0].strip()


def _une_ligne(texte):
    return " ".join(l.strip() for l in texte.splitlines() if l.strip())


# --- Contrôle interne -----------------------------------------------------------------------

CI_INTRODUCTION = [
    "Le contrôle interne est un dispositif mis en œuvre par les organes décisionnels, les dirigeants et le "
    "personnel d'une organisation, destiné à fournir une assurance raisonnable quant à la réalisation "
    "d'objectifs entrant dans les catégories suivantes :",
    ("Réalisation et optimisation des opérations ;", 1),
    ("Fiabilité des informations financières ;", 1),
    ("Conformité aux lois et à la réglementation en vigueur.", 1),
    "La mise en place et le suivi d'un système de contrôle interne efficace relève de la responsabilité du "
    "management de l'organisation et requiert une supervision continue afin de déterminer l'efficacité des "
    "différents contrôles opérationnels prévus.",
]

PRIORITES = {
    "Élevé": ("Priorité forte", "Les mesures préconisées devraient être suivies rapidement car elles couvrent "
              "des insuffisances significatives.", "C00000"),
    "Moyen": ("Priorité moyenne", "Les améliorations devraient être prises en compte à moyen terme.", "F2A900"),
    "Faible": ("Priorité faible", "Les recommandations correspondent aux meilleures pratiques et peuvent être "
               "mises en œuvre à plus long terme.", "6FAE3A"),
}

# --- Intangibilité --------------------------------------------------------------------------

INTANGIBILITE_DEFINITION = (
    "Le principe d'intangibilité du bilan d'ouverture impose que le bilan d'ouverture de l'exercice "
    "corresponde au bilan de clôture de l'exercice précédent."
)


def intangibilite_constat(nb_ecarts, periode_n_moins1, periode_n):
    if nb_ecarts == 0:
        return (
            f"Le rapprochement entre la balance de clôture {periode_n_moins1} et la balance d'ouverture "
            f"{periode_n} ne fait ressortir aucun écart : le principe d'intangibilité est respecté."
        )
    pluriel = "s présentent" if nb_ecarts > 1 else " présente"
    return (
        f"Le rapprochement entre la balance de clôture {periode_n_moins1} et la balance d'ouverture "
        f"{periode_n} fait ressortir {nb_ecarts} compte{pluriel} un écart, détaillé ci-dessous."
    )
