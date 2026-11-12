"""Construit backend/templates/rapport_template.pptx : le modèle PowerPoint du rapport final.

Usage (depuis backend/, venv actif) :  python -m scripts.construire_modele

Le modèle est construit uniquement à partir des visuels Y3 de templates/assets/ (aucun contenu
client, aucun élément d'un modèle tiers). Il contient un masque unique et une disposition nommée
par type de slide. Les builders (app/services/rapport/builders.py) s'appuient sur les NOMS des
dispositions et sur les idx des espaces réservés : on peut retoucher le visuel dans PowerPoint
(couleurs, polices, positions, fonds) à condition de conserver ces noms et ces idx.
"""

import os
import re

from PIL import Image
from pptx import Presentation
from pptx.opc.constants import CONTENT_TYPE as CT
from pptx.opc.constants import RELATIONSHIP_TYPE as RT
from pptx.opc.packuri import PackURI
from pptx.oxml import parse_xml
from pptx.parts.slide import SlideLayoutPart

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TEMPLATES_DIR = os.path.join(BACKEND_DIR, "templates")
ASSETS_DIR = os.path.join(TEMPLATES_DIR, "assets")
SORTIE = os.path.join(TEMPLATES_DIR, "rapport_template.pptx")

CM = 360000
LARGEUR, HAUTEUR = 12192000, 6858000  # 16:9, 33,867 × 19,05 cm

NAVY = "043D5D"
VERT = "6FAE3A"
GRIS = "333333"
POLICE_TITRE = "Rajdhani"
POLICE_TEXTE = "Work Sans"

NS = (
    'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
    'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"'
)

# Dispositions : nom -> idx des espaces réservés (contrat avec les builders).
DISPOSITIONS = [
    "EC Couverture",
    "EC Séparateur",
    "EC Sommaire",
    "EC Texte",
    "EC Tableau",
    "EC Texte + tableau",
    "EC Constat CI",
    "EC Fin",
]


def _cm(v):
    return int(round(v * CM))


def _xfrm(x, y, w, h):
    return f'<a:xfrm><a:off x="{_cm(x)}" y="{_cm(y)}"/><a:ext cx="{_cm(w)}" cy="{_cm(h)}"/></a:xfrm>'


def _rpr(taille, gras=False, couleur=GRIS, police=POLICE_TEXTE, balise="a:defRPr"):
    b = ' b="1"' if gras else ' b="0"'
    return (
        f'<{balise} lang="fr-FR" sz="{int(taille * 100)}"{b}>'
        f'<a:solidFill><a:srgbClr val="{couleur}"/></a:solidFill>'
        f'<a:latin typeface="{police}"/><a:cs typeface="{police}"/></{balise}>'
    )


class Formes:
    """Accumule les formes d'une disposition, avec des id uniques."""

    def __init__(self):
        self.xml = []
        self.next_id = 2

    def _id(self):
        self.next_id += 1
        return self.next_id

    def espace(self, nom, type_, idx, x, y, w, h, invite, taille=12, gras=False, couleur=GRIS,
               police=POLICE_TEXTE, ancre="t", aligne="l", autofit=True, majuscules=False, fond=None):
        ph = f'<p:ph type="{type_}"/>' if type_ == "title" else f'<p:ph type="{type_}" idx="{idx}"/>'
        cap = ' cap="all"' if majuscules else ""
        remplissage = (
            f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:solidFill><a:srgbClr val="{fond}"/></a:solidFill>'
            if fond
            else ""
        )
        corps = ""
        if type_ not in ("pic", "tbl"):
            fit = "<a:normAutofit/>" if autofit else "<a:noAutofit/>"
            lvl1 = (
                f'<a:lvl1pPr marL="0" indent="0" algn="{aligne}"><a:lnSpc><a:spcPct val="100000"/></a:lnSpc>'
                f'<a:spcBef><a:spcPts val="0"/></a:spcBef><a:spcAft><a:spcPts val="600"/></a:spcAft><a:buNone/>'
                + _rpr(taille, gras, couleur, police).replace("<a:defRPr", f"<a:defRPr{cap}", 1)
                + "</a:lvl1pPr>"
            )
            lvl2 = (
                f'<a:lvl2pPr marL="{_cm(0.6)}" indent="-{_cm(0.4)}" algn="l"><a:spcAft><a:spcPts val="300"/></a:spcAft>'
                f'<a:buClr><a:srgbClr val="{VERT}"/></a:buClr><a:buFont typeface="Arial"/><a:buChar char="•"/>'
                + _rpr(taille, False, couleur, police) + "</a:lvl2pPr>"
            )
            corps = (
                f'<p:txBody><a:bodyPr wrap="square" lIns="0" tIns="0" rIns="0" bIns="0" anchor="{ancre}">{fit}</a:bodyPr>'
                f"<a:lstStyle>{lvl1}{lvl2}</a:lstStyle>"
                f'<a:p><a:r><a:rPr lang="fr-FR"/><a:t>{invite}</a:t></a:r></a:p></p:txBody>'
            )
        elif type_ == "pic":
            corps = (
                '<p:txBody><a:bodyPr/><a:lstStyle/>'
                f'<a:p><a:r><a:rPr lang="fr-FR"/><a:t>{invite}</a:t></a:r></a:p></p:txBody>'
            )
        self.xml.append(
            f'<p:sp><p:nvSpPr><p:cNvPr id="{self._id()}" name="{nom}"/>'
            f'<p:cNvSpPr><a:spLocks noGrp="1"/></p:cNvSpPr><p:nvPr>{ph}</p:nvPr></p:nvSpPr>'
            f"<p:spPr>{_xfrm(x, y, w, h)}{remplissage}</p:spPr>{corps}</p:sp>"
        )

    def texte(self, nom, x, y, w, h, paragraphes, taille=12, gras=False, couleur=GRIS, police=POLICE_TEXTE,
              aligne="l", ancre="t", fond=None):
        ps = "".join(
            f'<a:p><a:pPr algn="{aligne}"/><a:r>{_rpr(t, g, c, police, "a:rPr")}<a:t>{texte}</a:t></a:r></a:p>'
            for texte, t, g, c in (
                (p if isinstance(p, tuple) else (p, taille, gras, couleur)) for p in paragraphes
            )
        )
        remplissage = f'<a:solidFill><a:srgbClr val="{fond}"/></a:solidFill>' if fond else "<a:noFill/>"
        self.xml.append(
            f'<p:sp><p:nvSpPr><p:cNvPr id="{self._id()}" name="{nom}"/><p:cNvSpPr txBox="1"/>'
            f'<p:nvPr userDrawn="1"/></p:nvSpPr><p:spPr>{_xfrm(x, y, w, h)}'
            f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>{remplissage}</p:spPr>'
            f'<p:txBody><a:bodyPr wrap="square" lIns="{_cm(0.15)}" tIns="0" rIns="{_cm(0.15)}" bIns="0" anchor="{ancre}">'
            f"<a:noAutofit/></a:bodyPr><a:lstStyle/>{ps}</p:txBody></p:sp>"
        )

    def numero_slide(self):
        self.xml.append(
            f'<p:sp><p:nvSpPr><p:cNvPr id="{self._id()}" name="Numéro de slide"/><p:cNvSpPr txBox="1"/>'
            f'<p:nvPr userDrawn="1"/></p:nvSpPr><p:spPr>{_xfrm(29.6, 17.75, 2.6, 0.9)}'
            '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/></p:spPr>'
            '<p:txBody><a:bodyPr wrap="square" lIns="0" tIns="0" rIns="0" bIns="0" anchor="ctr"><a:noAutofit/></a:bodyPr>'
            '<a:lstStyle/><a:p><a:pPr algn="r"/>'
            '<a:fld id="{B6F15528-21DE-4FAA-801E-634DDDAF4B2B}" type="slidenum">'
            + _rpr(11, True, "FFFFFF", POLICE_TEXTE, "a:rPr")
            + "<a:t>‹N°›</a:t></a:fld></a:p></p:txBody></p:sp>"
        )

    def image(self, nom, rid, x, y, w, h):
        self.xml.append(
            f'<p:pic><p:nvPicPr><p:cNvPr id="{self._id()}" name="{nom}"/>'
            '<p:cNvPicPr><a:picLocks noChangeAspect="1"/></p:cNvPicPr><p:nvPr userDrawn="1"/></p:nvPicPr>'
            f'<p:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></p:blipFill>'
            f'<p:spPr>{_xfrm(x, y, w, h)}<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr></p:pic>'
        )


def _ratio(nom_image):
    with Image.open(os.path.join(ASSETS_DIR, nom_image)) as im:
        return im.height / im.width


def _xml_disposition(nom, formes, fond_rid):
    fond = (
        f'<p:bg><p:bgPr><a:blipFill dpi="0" rotWithShape="1"><a:blip r:embed="{fond_rid}"/><a:srcRect/>'
        "<a:stretch><a:fillRect/></a:stretch></a:blipFill><a:effectLst/></p:bgPr></p:bg>"
        if fond_rid
        else ""
    )
    return (
        f'<p:sldLayout {NS} preserve="1" userDrawn="1"><p:cSld name="{nom}">{fond}<p:spTree>'
        '<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
        '<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/>'
        '<a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>'
        + "".join(formes.xml)
        + "</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sldLayout>"
    )


def _entete_contenu(f, largeur_titre=30.8):
    f.espace("Titre", "title", 0, 1.5, 0.6, largeur_titre, 1.3, "Titre", taille=24, gras=True,
             couleur=VERT, police=POLICE_TITRE, ancre="b", autofit=False)
    f.espace("Rubrique", "body", 13, 1.5, 1.9, 30.8, 0.9, "Rubrique", taille=13, gras=True,
             couleur=NAVY, autofit=False)


def _formes(nom, img):
    """Formes de chaque disposition. `img(nom_fichier)` renvoie le rId d'un visuel de assets/."""
    f = Formes()
    if nom == "EC Couverture":
        f.espace("Titre", "title", 0, 2.8, 5.6, 21.0, 2.0, "Révision des comptes", taille=36, gras=True,
                 couleur=NAVY, police=POLICE_TITRE, ancre="b", autofit=False)
        f.espace("Exercice", "body", 1, 2.8, 7.6, 21.0, 1.6, "Exercice", taille=30, gras=True,
                 couleur=NAVY, police=POLICE_TITRE, autofit=False)
        f.espace("Client", "body", 13, 2.8, 9.3, 21.0, 1.0, "Client", taille=16, gras=True, couleur=GRIS, autofit=False)
        f.espace("Date", "body", 10, 2.8, 10.6, 8.0, 1.2, "Date", taille=18, gras=True, couleur="FFFFFF",
                 ancre="ctr", autofit=False, fond=VERT)
        f.espace("Mention", "body", 14, 2.8, 13.6, 14.0, 0.9, "Mention", taille=14, gras=True, couleur="C00000",
                 autofit=False)
        f.espace("Logo client", "pic", 11, 22.4, 0.6, 10.0, 4.6, "Logo du client")
        f.texte("Confidentiel", 2.8, 12.3, 6.0, 0.9, ["Confidentiel"], taille=14, gras=True, couleur="C00000")
        f.image("Logo Y3", img("logo_y3.png"), 2.87, 15.19, 2.37, 2.37 * _ratio("logo_y3.png"))
        f.image("Logo Y3 blanc", img("logo_y3_blanc.png"), 28.8, 14.04, 5.08, 5.08 * _ratio("logo_y3_blanc.png"))
        return f, "fond_couverture.png"

    if nom == "EC Séparateur":
        f.espace("Numéro", "body", 10, 2.8, 3.4, 1.6, 1.6, "1", taille=24, gras=True, couleur="FFFFFF",
                 police=POLICE_TITRE, ancre="ctr", aligne="ctr", autofit=False, fond=VERT)
        f.espace("Titre", "title", 0, 2.8, 5.6, 15.5, 4.0, "Titre de partie", taille=32, gras=True,
                 couleur="FFFFFF", police=POLICE_TITRE, ancre="t", autofit=False, majuscules=True)
        f.espace("Image", "pic", 11, 19.6, 1.6, 12.6, 14.4, "Image")
        return f, "fond_sombre.png"

    if nom == "EC Sommaire":
        f.espace("Titre", "title", 0, 1.5, 0.6, 30.8, 1.3, "SOMMAIRE", taille=24, gras=True, couleur=NAVY,
                 police=POLICE_TITRE, ancre="b", autofit=False)
        f.espace("Chapitres", "body", 1, 2.0, 2.8, 29.8, 14.0, "Chapitres", taille=13)
        f.numero_slide()
        return f, "fond_contenu.png"

    _entete_contenu(f, 27.6 if nom == "EC Constat CI" else 30.8)
    if nom == "EC Texte":
        f.espace("Texte", "body", 1, 1.5, 3.0, 30.8, 13.8, "Texte", taille=12)
    elif nom == "EC Tableau":
        f.espace("Tableau", "tbl", 12, 1.5, 3.0, 30.8, 13.8, "Tableau")
    elif nom == "EC Texte + tableau":
        f.espace("Texte", "body", 1, 1.5, 3.0, 30.8, 4.4, "Texte", taille=12)
        f.espace("Tableau", "tbl", 12, 1.5, 7.6, 30.8, 9.2, "Tableau")
    elif nom == "EC Constat CI":
        f.espace("Tableau", "tbl", 12, 1.5, 3.0, 27.6, 13.8, "Tableau")
    elif nom == "EC Fin":
        f = Formes()
        f.texte("Adresse - titre", 2.4, 12.6, 18.0, 1.2, ["Adresse géographique"], taille=22, gras=True,
                couleur=VERT, police=POLICE_TITRE)
        f.texte(
            "Adresse", 2.4, 13.9, 18.0, 3.0,
            [
                "Riviera Golf Mafit - Immeuble TIGA 3ème étage - Appartement 103",
                "Abidjan - Côte d'Ivoire",
                "+225 27 22 23 05 26",
                "www.y3ac.com",
            ],
            taille=11, couleur="FFFFFF",
        )
        f.image("Logo Y3", img("logo_y3_blanc.png"), 2.4, 1.2, 3.4, 3.4 * _ratio("logo_y3_blanc.png"))
        f.image("Visuel", img("visuel_fin.png"), 23.11, 8.43, 10.76, 10.76 * _ratio("visuel_fin.png"))
        return f, "fond_sombre.png"
    f.numero_slide()
    return f, "fond_contenu.png"


def _theme(master):
    """Polices et couleurs du thème : Rajdhani (titres), Work Sans (texte), navy / vert Y3."""
    theme_part = master.part.part_related_by(RT.THEME)
    xml = theme_part.blob.decode("utf-8")
    xml = re.sub(r'(<a:majorFont>\s*<a:latin typeface=")[^"]*', r"\g<1>" + POLICE_TITRE, xml)
    xml = re.sub(r'(<a:minorFont>\s*<a:latin typeface=")[^"]*', r"\g<1>" + POLICE_TEXTE, xml)
    for balise, couleur in (("dk2", NAVY), ("accent1", NAVY), ("accent2", VERT)):
        xml = re.sub(rf"(<a:{balise}>)\s*<a:(srgbClr|sysClr)[^/]*/>", rf'\g<1><a:srgbClr val="{couleur}"/>', xml)
    xml = re.sub(r'<a:theme ([^>]*)name="[^"]*"', r'<a:theme \1name="Y3 Audit et Conseils"', xml, count=1)
    theme_part._blob = xml.encode("utf-8")


def construire():
    prs = Presentation()
    prs.slide_width, prs.slide_height = LARGEUR, HAUTEUR
    master = prs.slide_masters[0]
    _theme(master)

    # Retire les 11 dispositions par défaut de python-pptx.
    id_lst = master._element.get_or_add_sldLayoutIdLst()
    for sld_layout_id in list(id_lst):
        master.part.drop_rel(sld_layout_id.rId)
        id_lst.remove(sld_layout_id)

    package = master.part.package
    for numero, nom in enumerate(DISPOSITIONS, start=1):
        part = SlideLayoutPart(
            PackURI(f"/ppt/slideLayouts/slideLayout{numero}.xml"),
            CT.PML_SLIDE_LAYOUT,
            package,
            parse_xml(_xml_disposition(nom, Formes(), None)),
        )
        part.relate_to(master.part, RT.SLIDE_MASTER)
        # Rattachée au masque AVANT l'ajout des images : le paquet ne nomme correctement les
        # médias (image1.png, image2.png…) que s'il voit les parties déjà atteignables.
        rid = master.part.relate_to(part, RT.SLIDE_LAYOUT)
        rids = {}

        def img(nom_fichier, part=part, rids=rids):
            if nom_fichier not in rids:
                _, rid = part.get_or_add_image_part(os.path.join(ASSETS_DIR, nom_fichier))
                rids[nom_fichier] = rid
            return rids[nom_fichier]

        formes, fond = _formes(nom, img)
        part._element = parse_xml(_xml_disposition(nom, formes, img(fond)))
        id_lst._add_sldLayoutId(id=2147483648 + numero, rId=rid)

    props = prs.core_properties
    props.title = "Rapport final – modèle"
    props.author = props.last_modified_by = "Y3 Audit & Conseils"
    props.comments = props.subject = props.keywords = props.category = ""
    prs.save(SORTIE)
    return SORTIE


if __name__ == "__main__":
    chemin = construire()
    verif = Presentation(chemin)
    print(chemin)
    for layout in verif.slide_layouts:
        print(f"  {layout.name}: {[ph.placeholder_format.idx for ph in layout.placeholders]}")
