"""Builders : une fonction par type de slide. Pas d'accès Mongo.

Chaque builder ajoute une ou plusieurs slides à la présentation à partir de données déjà
préparées par l'assembleur, en paginant si nécessaire. Contrat :
- les slides utilisent les dispositions nommées du modèle (templates/rapport_template.pptx) ;
- tout espace réservé non rempli est SUPPRIMÉ de la slide (jamais laissé vide, jamais
  « Cliquez pour ajouter… ») : voir `_nettoyer`.

Un paragraphe est un dict : {"texte", "niveau": 0|1, "style": None|"intertitre"|"gras",
"label": préfixe en gras (facultatif), "couleur": RRGGBB (facultatif)}.
Un tableau est un dict : {"colonnes": [{"titre", "poids", "align": "l"|"r"|"c"}],
"lignes": [{"cellules": [...], "style": None|"groupe"|"total"}], "pied": [lignes de total]}.
"""

import io

from PIL import Image
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Cm, Emu, Pt

from app.services.rapport import pagination
from app.services.rapport.textes import PRIORITES

NAVY = "043D5D"
VERT = "6FAE3A"
GRIS = "333333"
BORDURE = "BFC9D1"
FOND_ALTERNE = "F2F6F9"
FOND_TOTAL = "E3F0D8"
FOND_GROUPE = "DCE6EE"
POLICE = "Work Sans"

L_COUVERTURE = "EC Couverture"
L_SEPARATEUR = "EC Séparateur"
L_SOMMAIRE = "EC Sommaire"
L_TEXTE = "EC Texte"
L_TABLEAU = "EC Tableau"
L_TEXTE_TABLEAU = "EC Texte + tableau"
L_CONSTAT = "EC Constat CI"
L_FIN = "EC Fin"

IDX_TITRE, IDX_CORPS, IDX_RUBRIQUE, IDX_TABLEAU = 0, 1, 13, 12

# Style de tableau « Aucun style, aucune grille » : la mise en forme est explicite (bordures,
# fonds), pour un rendu identique dans PowerPoint, ONLYOFFICE et LibreOffice.
STYLE_TABLEAU_NEUTRE = "{2D5ABB26-0587-4C30-8999-92F81FD0307C}"


def P(texte, **kw):
    return {"texte": texte, **kw}


def paragraphes_depuis_texte(texte, **kw):
    """Texte saisi -> un paragraphe par ligne non vide (contenu repris tel quel)."""
    return [P(l.strip(), **kw) for l in (texte or "").splitlines() if l.strip()]


# --- Outils ------------------------------------------------------------------------------------


def disposition(prs, nom):
    for layout in prs.slide_layouts:
        if layout.name == nom:
            return layout
    raise KeyError(f"Disposition « {nom} » absente du modèle")


def zone(prs, nom_layout, idx):
    """(largeur, hauteur) en cm de l'espace réservé `idx` d'une disposition."""
    for ph in disposition(prs, nom_layout).placeholders:
        if ph.placeholder_format.idx == idx:
            return Emu(ph.width).cm, Emu(ph.height).cm
    raise KeyError(f"Espace réservé {idx} absent de « {nom_layout} »")


def _slide(prs, nom_layout):
    return prs.slides.add_slide(disposition(prs, nom_layout))


def _ph(slide, idx):
    for ph in slide.placeholders:
        if ph.placeholder_format.idx == idx:
            return ph
    return None


def _nettoyer(slide):
    """Supprime les espaces réservés restés vides (texte, image ou tableau non insérés)."""
    for ph in list(slide.placeholders):
        el = ph.element
        if el.tag != qn("p:sp"):
            continue  # image ou tableau inséré : l'élément a été remplacé
        if not ph.has_text_frame or not ph.text_frame.text.strip():
            el.getparent().remove(el)


def _couleur(run, rrggbb):
    run.font.color.rgb = RGBColor.from_string(rrggbb)


def _ecrire(text_frame, paragraphes):
    for i, p in enumerate(paragraphes):
        para = text_frame.paragraphs[0] if i == 0 else text_frame.add_paragraph()
        para.level = p.get("niveau", 0)
        if p.get("label"):
            run = para.add_run()
            run.text = f"{p['label']} : "
            run.font.bold = True
            if p.get("couleur"):
                _couleur(run, p["couleur"])
        run = para.add_run()
        run.text = p["texte"]
        style = p.get("style")
        if style in ("intertitre", "gras"):
            run.font.bold = True
        if style == "intertitre":
            _couleur(run, NAVY)
        elif p.get("couleur") and not p.get("label"):
            _couleur(run, p["couleur"])


def _texte_ph(slide, idx, texte):
    ph = _ph(slide, idx)
    if ph is not None and texte:
        ph.text_frame.text = texte


def _numeroter(rubrique, i, n):
    return f"{rubrique} ({i}/{n})" if n > 1 else rubrique


# --- Tableaux ---------------------------------------------------------------------------------


def _bordures(cell, couleur=BORDURE):
    tcPr = cell._tc.get_or_add_tcPr()
    for bord in ("a:lnL", "a:lnR", "a:lnT", "a:lnB"):
        ln = tcPr.find(qn(bord))
        if ln is None:
            ln = tcPr.makeelement(qn(bord), {})
            tcPr.append(ln)
        ln.set("w", "6350")
        for enfant in list(ln):
            ln.remove(enfant)
        fill = ln.makeelement(qn("a:solidFill"), {})
        clr = fill.makeelement(qn("a:srgbClr"), {"val": couleur})
        fill.append(clr)
        ln.append(fill)


def _cellule(cell, valeur, align="l", gras=False, couleur=GRIS, fond=None):
    cell.margin_left = cell.margin_right = Cm(pagination.TABLE_MARGE_H_CM / 2)
    cell.margin_top = cell.margin_bottom = Cm(pagination.TABLE_MARGE_V_CM / 2)
    cell.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf = cell.text_frame
    tf.word_wrap = True
    lignes = ["" if valeur is None else str(valeur)]
    if "\n" in lignes[0]:
        lignes = lignes[0].split("\n")
    for i, texte in enumerate(lignes):
        para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        para.alignment = {"r": PP_ALIGN.RIGHT, "c": PP_ALIGN.CENTER}.get(align, PP_ALIGN.LEFT)
        # Taille aussi sur la marque de fin de paragraphe : sans elle, une cellule vide prend la
        # taille par défaut (18 pt) et la ligne s'agrandit au rendu.
        para._p.get_or_add_endParaRPr().set("sz", str(pagination.TABLE_PT * 100))
        if texte:
            run = para.add_run()
            run.text = texte
            run.font.size = Pt(pagination.TABLE_PT)
            run.font.name = POLICE
            run.font.bold = gras
            _couleur(run, couleur)
    _bordures(cell)
    if fond:
        cell.fill.solid()
        cell.fill.fore_color.rgb = RGBColor.from_string(fond)
    else:
        cell.fill.background()


def _tableau(slide, idx, tableau, lignes):
    """Insère une page de tableau dans l'espace réservé `idx` : en-tête + lignes (+ pied si
    `lignes` est la dernière page, signalé par la clé "_pied")."""
    ph = _ph(slide, idx)
    colonnes = tableau["colonnes"]
    toutes = [{"cellules": [c["titre"] for c in colonnes], "style": "entete"}] + lignes
    largeur_cm = Emu(ph.width).cm
    largeurs = pagination.largeurs_colonnes(colonnes, largeur_cm)
    gf = ph.insert_table(rows=len(toutes), cols=len(colonnes))
    table = gf.table
    tbl_pr = gf._element.graphic.graphicData.tbl.tblPr
    style = tbl_pr.find(qn("a:tableStyleId"))
    if style is None:
        style = tbl_pr.makeelement(qn("a:tableStyleId"), {})
        tbl_pr.append(style)
    style.text = STYLE_TABLEAU_NEUTRE
    table.first_row = True
    table.horz_banding = False
    for i, largeur in enumerate(largeurs):
        table.columns[i].width = Cm(largeur)
    hauteur = 0
    for r, ligne in enumerate(toutes):
        h = pagination.hauteur_ligne(ligne["cellules"], largeurs)
        table.rows[r].height = Cm(h)
        hauteur += h
        style_ligne = ligne.get("style")
        if style_ligne == "groupe":
            premiere = table.cell(r, 0)
            for c in range(1, len(colonnes)):
                # Cellules masquées par la fusion : même taille de police que le tableau.
                for para in table.cell(r, c).text_frame.paragraphs:
                    para._p.get_or_add_endParaRPr().set("sz", str(pagination.TABLE_PT * 100))
            if len(colonnes) > 1:
                premiere.merge(table.cell(r, len(colonnes) - 1))
            _cellule(premiere, ligne["cellules"][0], gras=True, couleur=NAVY, fond=FOND_GROUPE)
            continue
        for c, valeur in enumerate(ligne["cellules"]):
            align = colonnes[c].get("align", "l")
            if style_ligne == "entete":
                _cellule(table.cell(r, c), valeur, align="c" if align == "c" else align, gras=True,
                         couleur="FFFFFF", fond=NAVY)
            elif style_ligne == "total":
                _cellule(table.cell(r, c), valeur, align, gras=True, couleur=NAVY, fond=FOND_TOTAL)
            else:
                _cellule(table.cell(r, c), valeur, align, fond=FOND_ALTERNE if r % 2 == 0 else None)
    gf.width = Cm(largeur_cm)
    gf.height = Cm(hauteur)
    return gf


def pages_tableau(prs, tableau, layout, premiere_hauteur=None):
    largeur, hauteur = zone(prs, layout, IDX_TABLEAU)
    _, h_pleine = zone(prs, L_TABLEAU, IDX_TABLEAU)
    pages = pagination.paginer_tableau(tableau, largeur, [premiere_hauteur or hauteur, h_pleine])
    pages[-1] = pages[-1] + list(tableau.get("pied") or [])
    return pages


# --- Builders ---------------------------------------------------------------------------------


def couverture(prs, titre, exercice, client, date, mention=None, logo=None):
    slide = _slide(prs, L_COUVERTURE)
    _texte_ph(slide, IDX_TITRE, titre)
    _texte_ph(slide, 1, f"Exercice {exercice}" if exercice else "")
    _texte_ph(slide, IDX_RUBRIQUE, client)
    _texte_ph(slide, 10, date)
    _texte_ph(slide, 14, mention)
    if logo:
        _image_contenue(slide, _ph(slide, 11), logo)
    _nettoyer(slide)
    return slide


def _image_contenue(slide, ph, blob):
    """Insère une image dans la zone d'un espace réservé SANS la rogner (logo), puis retire
    l'espace réservé."""
    if ph is None:
        return
    with Image.open(io.BytesIO(blob)) as im:
        ratio = im.height / im.width
    left, top, w, h = ph.left, ph.top, ph.width, ph.height
    if w * ratio > h:
        w2, h2 = int(h / ratio), h
    else:
        w2, h2 = w, int(w * ratio)
    slide.shapes.add_picture(io.BytesIO(blob), left + (w - w2), top + (h - h2) // 2, w2, h2)
    ph.element.getparent().remove(ph.element)


def separateur(prs, numero, titre, photo=None):
    slide = _slide(prs, L_SEPARATEUR)
    _texte_ph(slide, 10, str(numero))
    _texte_ph(slide, IDX_TITRE, titre)
    ph = _ph(slide, 11)
    if photo and ph is not None:
        ph.insert_picture(io.BytesIO(photo))
    _nettoyer(slide)
    return slide


def sommaire(prs, parties, courante):
    """`parties` : [{"numero", "titre", "sous": [libellés]}] ; la partie `courante` est en vert."""
    slide = _slide(prs, L_SOMMAIRE)
    _texte_ph(slide, IDX_TITRE, "SOMMAIRE")
    paragraphes = []
    for partie in parties:
        actif = partie["numero"] == courante
        paragraphes.append(P(f"{partie['numero']}. {partie['titre']}", style="gras",
                             couleur=VERT if actif else NAVY))
        paragraphes.extend(P(s, niveau=1, couleur=None if actif else "7F8C96") for s in partie.get("sous") or [])
    ph = _ph(slide, IDX_CORPS)
    body_pr = ph.text_frame._txBody.find(qn("a:bodyPr"))
    if sum(len(p.get("sous") or []) + 1 for p in parties) > 14:
        body_pr.set("numCol", "2")
        body_pr.set("spcCol", str(Cm(1.2)))
    _ecrire(ph.text_frame, paragraphes)
    _nettoyer(slide)
    return slide


def texte(prs, titre, rubrique, paragraphes):
    """Slides de texte, paginées."""
    if not paragraphes:
        return []
    largeur, hauteur = zone(prs, L_TEXTE, IDX_CORPS)
    pages = pagination.paginer_texte(paragraphes, largeur, hauteur)
    slides = []
    for i, page in enumerate(pages, start=1):
        slide = _slide(prs, L_TEXTE)
        _texte_ph(slide, IDX_TITRE, titre)
        _texte_ph(slide, IDX_RUBRIQUE, _numeroter(rubrique, i, len(pages)))
        _ecrire(_ph(slide, IDX_CORPS).text_frame, page)
        _nettoyer(slide)
        slides.append(slide)
    return slides


def tableau_seul(prs, titre, rubrique, tableau):
    pages = pages_tableau(prs, tableau, L_TABLEAU)
    slides = []
    for i, lignes in enumerate(pages, start=1):
        slide = _slide(prs, L_TABLEAU)
        _texte_ph(slide, IDX_TITRE, titre)
        _texte_ph(slide, IDX_RUBRIQUE, _numeroter(rubrique, i, len(pages)))
        _tableau(slide, IDX_TABLEAU, tableau, lignes)
        _nettoyer(slide)
        slides.append(slide)
    return slides


def section(prs, titre, rubrique, paragraphes, tableaux):
    """Section complète : texte puis tableaux (chacun {"legende", "tableau"}), en enchaînant le
    texte et le premier tableau sur la même slide quand la fin du texte tient dans la zone haute
    de « EC Texte + tableau »."""
    slides = []
    tableaux = [t for t in tableaux if t["tableau"]["lignes"] or t["tableau"].get("pied")]
    largeur_t, hauteur_t = zone(prs, L_TEXTE, IDX_CORPS)
    largeur_c, hauteur_c = zone(prs, L_TEXTE_TABLEAU, IDX_CORPS)
    pages = pagination.paginer_texte(paragraphes, largeur_t, hauteur_t) if paragraphes else []
    combine = bool(tableaux and pages and pagination.hauteur_texte(pages[-1], largeur_c) <= hauteur_c)

    if combine:
        slides += texte(prs, titre, rubrique, [p for page in pages[:-1] for p in page]) if len(pages) > 1 else []
        premier = tableaux.pop(0)
        _, h_tab = zone(prs, L_TEXTE_TABLEAU, IDX_TABLEAU)
        pages_t = pages_tableau(prs, premier["tableau"], L_TEXTE_TABLEAU, h_tab)
        slide = _slide(prs, L_TEXTE_TABLEAU)
        _texte_ph(slide, IDX_TITRE, titre)
        suite = " (suite)" if len(pages) > 1 else ""
        _texte_ph(slide, IDX_RUBRIQUE, rubrique + suite)
        legende = [P(premier["legende"], style="intertitre")] if premier.get("legende") else []
        _ecrire(_ph(slide, IDX_CORPS).text_frame, pages[-1] + legende)
        _tableau(slide, IDX_TABLEAU, premier["tableau"], pages_t[0])
        _nettoyer(slide)
        slides.append(slide)
        for i, lignes in enumerate(pages_t[1:], start=2):
            slides.append(_page_tableau(prs, titre, _sous_rubrique(rubrique, premier, i, len(pages_t)),
                                        premier["tableau"], lignes))
    else:
        slides += texte(prs, titre, rubrique, paragraphes)

    for t in tableaux:
        pages_t = pages_tableau(prs, t["tableau"], L_TABLEAU)
        for i, lignes in enumerate(pages_t, start=1):
            slides.append(_page_tableau(prs, titre, _sous_rubrique(rubrique, t, i, len(pages_t)), t["tableau"], lignes))
    return slides


def _sous_rubrique(rubrique, t, i, n):
    base = f"{rubrique} — {t['legende']}" if t.get("legende") else rubrique
    return _numeroter(base, i, n)


def _page_tableau(prs, titre, rubrique, tableau, lignes):
    slide = _slide(prs, L_TABLEAU)
    _texte_ph(slide, IDX_TITRE, titre)
    _texte_ph(slide, IDX_RUBRIQUE, rubrique)
    _tableau(slide, IDX_TABLEAU, tableau, lignes)
    _nettoyer(slide)
    return slide


def ci_introduction(prs, titre, paragraphes):
    """Introduction du contrôle interne + légende des priorités (en bas de la slide)."""
    legende = [P("Légende :", style="intertitre")] + [
        P(description, label=libelle, couleur=couleur) for libelle, description, couleur in PRIORITES.values()
    ]
    return texte(prs, titre, "Introduction et légende", paragraphes + legende)


def _feu(slide, left, top, severite):
    """Feu de priorité : trois pastilles, celle du niveau de sévérité allumée."""
    largeur, hauteur = Cm(1.2), Cm(3.2)
    boite = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, largeur, hauteur)
    boite.fill.solid()
    boite.fill.fore_color.rgb = RGBColor.from_string("FFFFFF")
    boite.line.color.rgb = RGBColor.from_string("7F8C96")
    boite.name = "Feu de priorité"
    for i, niveau in enumerate(("Élevé", "Moyen", "Faible")):
        pastille = slide.shapes.add_shape(MSO_SHAPE.OVAL, left + Cm(0.2), top + Cm(0.2 + i * 1.0), Cm(0.8), Cm(0.8))
        pastille.line.color.rgb = RGBColor.from_string("7F8C96")
        pastille.fill.solid()
        couleur = PRIORITES[niveau][2] if niveau == severite else "FFFFFF"
        pastille.fill.fore_color.rgb = RGBColor.from_string(couleur)
    libelle = slide.shapes.add_textbox(left - Cm(0.6), top + hauteur + Cm(0.1), Cm(2.4), Cm(0.8))
    tf = libelle.text_frame
    tf.word_wrap = True
    para = tf.paragraphs[0]
    para.alignment = PP_ALIGN.CENTER
    run = para.add_run()
    run.text = PRIORITES[severite][0] if severite in PRIORITES else ""
    run.font.size = Pt(8)
    run.font.bold = True
    run.font.name = POLICE
    _couleur(run, NAVY)


def constat_ci(prs, titre, rubrique, constat, colonne_management):
    """Fiche constat du contrôle interne : tableau Constat / Risques / Recommandations /
    Commentaires du management, et feu de priorité. Une fiche trop longue pour une slide est
    présentée en texte, rubrique par rubrique (rien n'est tronqué)."""
    tableau = {
        "colonnes": [
            {"titre": "Constat / Observation", "poids": 3},
            {"titre": "Risques", "poids": 2.2},
            {"titre": "Recommandations Y3", "poids": 3},
            {"titre": colonne_management, "poids": 2.4},
        ],
        "lignes": [
            {
                "cellules": [
                    constat["constat"],
                    "\n".join(f"• {r}" for r in constat["risques"]),
                    constat.get("recommandation") or "",
                    constat.get("reponseManagement") or "",
                ]
            }
        ],
    }
    largeur, hauteur = zone(prs, L_CONSTAT, IDX_TABLEAU)
    largeurs = pagination.largeurs_colonnes(tableau["colonnes"], largeur)
    h = pagination.hauteur_ligne([c["titre"] for c in tableau["colonnes"]], largeurs) + pagination.hauteur_ligne(
        tableau["lignes"][0]["cellules"], largeurs
    )
    if h <= hauteur:
        slide = _slide(prs, L_CONSTAT)
        _texte_ph(slide, IDX_TITRE, titre)
        _texte_ph(slide, IDX_RUBRIQUE, rubrique)
        gf = _tableau(slide, IDX_TABLEAU, tableau, tableau["lignes"])
        _feu(slide, gf.left + gf.width + Cm(0.9), gf.top + Cm(0.2), constat.get("severite"))
        _nettoyer(slide)
        return [slide]

    paragraphes = [P("Constat / Observation", style="intertitre")] + paragraphes_depuis_texte(constat["constat"])
    if constat["risques"]:
        paragraphes += [P("Risques", style="intertitre")] + [P(r, niveau=1) for r in constat["risques"]]
    if constat.get("recommandation"):
        paragraphes += [P("Recommandations Y3", style="intertitre")] + paragraphes_depuis_texte(constat["recommandation"])
    if constat.get("reponseManagement"):
        paragraphes += [P(colonne_management, style="intertitre")] + paragraphes_depuis_texte(constat["reponseManagement"])
    if constat.get("severite") in PRIORITES:
        libelle, _, couleur = PRIORITES[constat["severite"]]
        paragraphes.append(P(libelle, style="gras", couleur=couleur))
    return texte(prs, titre, rubrique, paragraphes)


def fin(prs):
    slide = _slide(prs, L_FIN)
    _nettoyer(slide)
    return slide
