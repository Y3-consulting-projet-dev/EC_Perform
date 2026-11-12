"""Découpage des textes et des tableaux trop longs pour une slide. Pas de dépendance pptx/Mongo.

Les hauteurs sont des ESTIMATIONS (pas de moteur de rendu) : volontairement prudentes, pour qu'un
contenu ne déborde pas. Les zones de texte du modèle ont en plus l'ajustement automatique activé,
ce qui absorbe un léger dépassement lors de l'édition dans ONLYOFFICE.
"""

import math

PT_CM = 2.54 / 72

# Texte courant (corps 12 pt, Work Sans).
TEXTE_PT = 12
TEXTE_CHAR_CM = 0.25
TEXTE_INTERLIGNE = 1.2
TEXTE_ESPACE_APRES_CM = 6 * PT_CM

# Tableaux (9 pt).
TABLE_PT = 9
TABLE_CHAR_CM = 0.19
TABLE_MARGE_V_CM = 0.16
TABLE_MARGE_H_CM = 0.2
TABLE_LIGNE_MIN_CM = 0.5


def lignes_texte(texte, largeur_cm, char_cm=TEXTE_CHAR_CM):
    """Nombre de lignes occupées par un paragraphe dans une largeur donnée."""
    par_ligne = max(1, int(largeur_cm / char_cm))
    return sum(max(1, math.ceil(len(morceau) / par_ligne)) for morceau in (texte or "").split("\n"))


def hauteur_paragraphe(paragraphe, largeur_cm):
    texte, niveau = paragraphe["texte"], paragraphe.get("niveau", 0)
    retrait = 0.6 if niveau else 0
    n = lignes_texte(texte, largeur_cm - retrait)
    return n * TEXTE_PT * TEXTE_INTERLIGNE * PT_CM + TEXTE_ESPACE_APRES_CM


def paginer_texte(paragraphes, largeur_cm, hauteur_cm):
    """Répartit des paragraphes sur des pages. Un paragraphe plus haut qu'une page est découpé
    en phrases ; un intertitre n'est jamais laissé seul en bas de page."""
    pages, page, h = [], [], 0.0
    for p in _decouper_longs(paragraphes, largeur_cm, hauteur_cm):
        hp = hauteur_paragraphe(p, largeur_cm)
        if page and h + hp > hauteur_cm:
            reporte = [page.pop()] if page and page[-1].get("style") == "intertitre" else []
            if page:
                pages.append(page)
            page, h = reporte, sum(hauteur_paragraphe(x, largeur_cm) for x in reporte)
        page.append(p)
        h += hp
    if page:
        pages.append(page)
    return pages


def hauteur_texte(paragraphes, largeur_cm):
    return sum(hauteur_paragraphe(p, largeur_cm) for p in paragraphes)


def _decouper_longs(paragraphes, largeur_cm, hauteur_cm):
    for p in paragraphes:
        if hauteur_paragraphe(p, largeur_cm) <= hauteur_cm:
            yield p
            continue
        morceau = ""
        for phrase in _phrases(p["texte"]):
            essai = f"{morceau} {phrase}".strip()
            if morceau and hauteur_paragraphe({**p, "texte": essai}, largeur_cm) > hauteur_cm:
                yield {**p, "texte": morceau}
                morceau = phrase
            else:
                morceau = essai
        if morceau:
            yield {**p, "texte": morceau}


def _phrases(texte):
    out, courant = [], ""
    for mot in texte.split(" "):
        courant = f"{courant} {mot}".strip()
        if mot.endswith((".", ";", ":", "!", "?")):
            out.append(courant)
            courant = ""
    if courant:
        out.append(courant)
    # Garde-fou : une « phrase » sans ponctuation plus longue qu'une page est coupée par mots.
    final = []
    for phrase in out:
        mots = phrase.split(" ")
        while len(mots) > 400:
            final.append(" ".join(mots[:400]))
            mots = mots[400:]
        final.append(" ".join(mots))
    return final


def largeurs_colonnes(colonnes, largeur_cm):
    poids = [c.get("poids", 1) for c in colonnes]
    total = sum(poids) or 1
    return [largeur_cm * p / total for p in poids]


def hauteur_ligne(cellules, largeurs_cm):
    lignes = 1
    for valeur, largeur in zip(cellules, largeurs_cm):
        texte = "" if valeur is None else str(valeur)
        lignes = max(lignes, lignes_texte(texte, max(0.5, largeur - TABLE_MARGE_H_CM), TABLE_CHAR_CM))
    return max(TABLE_LIGNE_MIN_CM, lignes * TABLE_PT * 1.2 * PT_CM + TABLE_MARGE_V_CM)


def paginer_tableau(tableau, largeur_cm, hauteurs_cm):
    """Découpe les lignes d'un tableau en pages. `hauteurs_cm` : hauteur disponible pour la 1re
    page, puis pour les suivantes. L'en-tête est répété sur chaque page ; les lignes de `pied`
    (totaux) ne figurent que sur la dernière. Renvoie une liste de listes de lignes."""
    largeurs = largeurs_colonnes(tableau["colonnes"], largeur_cm)
    entete = hauteur_ligne([c["titre"] for c in tableau["colonnes"]], largeurs)
    pied = sum(hauteur_ligne(l["cellules"], largeurs) for l in tableau.get("pied") or [])
    pages, page, h = [], [], entete
    disponible = hauteurs_cm[0]
    lignes = tableau["lignes"]
    for i, ligne in enumerate(lignes):
        hl = hauteur_ligne(ligne["cellules"], largeurs)
        derniere = i == len(lignes) - 1
        besoin = hl + (pied if derniere else 0)
        if page and h + besoin > disponible:
            # Un intertitre de groupe n'est jamais laissé seul en bas de page.
            reporte = [page.pop()] if page[-1].get("style") == "groupe" else []
            if page:
                pages.append(page)
            page = reporte
            h = entete + sum(hauteur_ligne(l["cellules"], largeurs) for l in reporte)
            disponible = hauteurs_cm[-1]
        page.append(ligne)
        h += hl
    if page or not pages:
        pages.append(page)
    if tableau.get("pied") and h + pied > disponible and pages[-1]:
        pages.append([])
    return pages
