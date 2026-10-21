import io
import os
import re
import zipfile
from xml.sax.saxutils import escape

from bson import ObjectId
from fastapi import HTTPException, UploadFile
from fastapi.responses import Response

from app.db.session import db
from app.services.document_service import store_upload
from app.services.mission_service import get_mission_or_404
from app.services.revision_service import auteur, now_iso

# Rubriques de la fiche signalétique de l'entité, dans l'ordre du modèle du cabinet.
# multiligne : saisie sur plusieurs lignes (une ligne = un élément, ex. un associé par ligne).
CHAMPS = [
    {"key": "denomination", "label": "Dénomination sociale"},
    {"key": "sigle", "label": "Sigle"},
    {"key": "formeJuridique", "label": "Forme juridique"},
    {"key": "capitalSocial", "label": "Capital social"},
    {"key": "evenementJuridique", "label": "Évènement juridique", "multiligne": True},
    {"key": "gerant", "label": "Gérant"},
    {"key": "associes", "label": "Associés", "multiligne": True},
    {"key": "anneeCreation", "label": "Année de création"},
    {"key": "objet", "label": "Objet", "multiligne": True},
    {"key": "ville", "label": "Ville"},
    {"key": "notaireConstitution", "label": "Notaire ayant effectué la constitution"},
    {"key": "adressePostale", "label": "Adresse postale"},
    {"key": "email", "label": "E-mail"},
    {"key": "secteurActivite", "label": "Secteur d'activité"},
    {"key": "descriptionActivite", "label": "Description de l'activité", "multiligne": True},
    {"key": "adresseGeographique", "label": "Adresse géographique", "multiligne": True},
    {"key": "telephone", "label": "Téléphone"},
    {"key": "numeroCC", "label": "N° CC"},
    {"key": "rccm", "label": "N° RCCM"},
    {"key": "centreImposition", "label": "Centre d'imposition"},
    {"key": "systemePresentation", "label": "Système de présentation des états annuels"},
    {"key": "effectif", "label": "Effectif"},
    {"key": "masseSalariale", "label": "Masse salariale annuelle"},
    {"key": "chiffreAffairesHT", "label": "Chiffre d'affaires annuel HT"},
    {"key": "sourcesChiffreAffaires", "label": "Sources du chiffre d'affaires", "multiligne": True},
    {"key": "infosAssocieUnique", "label": "Informations sur l'associé unique", "multiligne": True},
    {"key": "autresInformations", "label": "Autres informations", "multiligne": True},
]
CHAMPS_KEYS = {c["key"] for c in CHAMPS}

# Pré-remplissage depuis la fiche client tant que la fiche n'a jamais été enregistrée.
CHAMPS_CLIENT = {
    "denomination": "raisonSociale",
    "formeJuridique": "formeJuridique",
    "ville": "ville",
    "adresseGeographique": "adresse",
    "email": "email",
    "telephone": "telephone",
    "numeroCC": "compteContribuable",
    "rccm": "rccm",
    "secteurActivite": "secteurActivite",
}

EXTENSIONS_IMPORT = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".png", ".jpg", ".jpeg"}


def _verifier_modifiable(mission):
    if mission.get("statut") == "Terminée":
        raise HTTPException(status_code=409, detail="Mission clôturée : la fiche signalétique n'est plus modifiable.")


def _valeurs_client(mission):
    try:
        client = db.clients.find_one({"_id": ObjectId(mission.get("clientId"))})
    except Exception:
        client = None
    if not client:
        return {}
    return {key: str(client.get(champ_client) or "") for key, champ_client in CHAMPS_CLIENT.items()}


def _serialize(mission):
    fiche = mission.get("ficheSignaletique") or {}
    renseignee = bool(fiche.get("valeurs"))
    valeurs = fiche.get("valeurs") if renseignee else _valeurs_client(mission)
    return {
        "champs": CHAMPS,
        "valeurs": {c["key"]: (valeurs or {}).get(c["key"], "") for c in CHAMPS},
        "renseignee": renseignee,
        "fichier": fiche.get("fichier"),
        "updatedAt": fiche.get("updatedAt"),
        "updatedBy": fiche.get("updatedBy"),
        "modifiable": mission.get("statut") != "Terminée",
    }


def get_fiche(mission_id: str):
    _, mission = get_mission_or_404(mission_id)
    return _serialize(mission)


def update_fiche(mission_id: str, valeurs: dict, employee):
    object_id, mission = get_mission_or_404(mission_id)
    _verifier_modifiable(mission)

    propres = {key: (valeurs.get(key) or "").strip() for key in CHAMPS_KEYS}
    if not any(propres.values()):
        raise HTTPException(status_code=400, detail="Renseignez au moins une rubrique de la fiche.")

    db.missions.update_one(
        {"_id": object_id},
        {
            "$set": {
                "ficheSignaletique.valeurs": propres,
                "ficheSignaletique.updatedAt": now_iso(),
                "ficheSignaletique.updatedBy": auteur(employee),
            }
        },
    )
    return _serialize(db.missions.find_one({"_id": object_id}))


def importer_fichier(mission_id: str, fichier: UploadFile, employee):
    object_id, mission = get_mission_or_404(mission_id)
    _verifier_modifiable(mission)

    if not fichier.filename or os.path.splitext(fichier.filename)[1].lower() not in EXTENSIONS_IMPORT:
        raise HTTPException(status_code=400, detail="Formats acceptés : PDF, Word, Excel, PNG, JPG.")
    file_name, file_url = store_upload(mission_id, fichier.filename, fichier.file.read())

    db.missions.update_one(
        {"_id": object_id},
        {
            "$set": {
                "ficheSignaletique.fichier": {
                    "fileName": file_name,
                    "fileUrl": file_url,
                    "importeLe": now_iso(),
                    "importePar": auteur(employee),
                },
            }
        },
    )
    return _serialize(db.missions.find_one({"_id": object_id}))


# --- Export Word (.docx) -----------------------------------------------------------------
# Document minimal écrit à la main (pas de dépendance python-docx) : un tableau à deux
# colonnes reprenant la mise en forme du modèle (bandeau violet, libellés en gras).

_W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'

_CONTENT_TYPES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/word/document.xml" '
    'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
    "</Types>"
)

_RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" '
    'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
    'Target="word/document.xml"/>'
    "</Relationships>"
)


def _paragraphe(texte, gras=False, centre=False):
    ppr = '<w:pPr><w:spacing w:before="20" w:after="20"/>' + ('<w:jc w:val="center"/>' if centre else "") + "</w:pPr>"
    rpr = '<w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/>' + ("<w:b/>" if gras else "") + '<w:sz w:val="20"/></w:rPr>'
    return f'<w:p>{ppr}<w:r>{rpr}<w:t xml:space="preserve">{escape(texte)}</w:t></w:r></w:p>'


def _cellule(contenu, largeur, fond=None, fusion=None):
    tcpr = f'<w:tcW w:w="{largeur}" w:type="dxa"/>'
    if fusion:
        tcpr += f'<w:gridSpan w:val="{fusion}"/>'
    if fond:
        tcpr += f'<w:shd w:val="clear" w:color="auto" w:fill="{fond}"/>'
    return f"<w:tc><w:tcPr>{tcpr}</w:tcPr>{contenu}</w:tc>"


def _construire_docx(valeurs):
    sigle = valeurs.get("sigle") or valeurs.get("denomination") or ""
    titre = f"INFORMATIONS GENERALES {sigle}".strip()
    lignes = [
        "<w:tr>" + _cellule(_paragraphe(titre, gras=True, centre=True), 9000, fond="7030A0", fusion=2) + "</w:tr>"
    ]
    for champ in CHAMPS:
        valeur = valeurs.get(champ["key"]) or ""
        elements = [l.strip() for l in valeur.splitlines() if l.strip()] or [""]
        if champ["key"] == "associes" and len(elements) > 1:
            elements = [f"- {e}" for e in elements]
        lignes.append(
            "<w:tr>"
            + _cellule(_paragraphe(champ["label"], gras=True), 4000)
            + _cellule("".join(_paragraphe(e) for e in elements), 5000)
            + "</w:tr>"
        )

    bordure = '<w:{0} w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
    bordures = "".join(bordure.format(b) for b in ("top", "left", "bottom", "right", "insideH", "insideV"))
    tableau = (
        f'<w:tbl><w:tblPr><w:tblW w:w="9000" w:type="dxa"/><w:jc w:val="center"/>'
        f"<w:tblBorders>{bordures}</w:tblBorders></w:tblPr>"
        f'<w:tblGrid><w:gridCol w:w="4000"/><w:gridCol w:w="5000"/></w:tblGrid>'
        f"{''.join(lignes)}</w:tbl>"
    )
    document = (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document {_W}><w:body>'
        f'{tableau}<w:p/><w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
        f'<w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134" w:header="708" w:footer="708" w:gutter="0"/>'
        f"</w:sectPr></w:body></w:document>"
    )

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _CONTENT_TYPES)
        archive.writestr("_rels/.rels", _RELS)
        archive.writestr("word/document.xml", document)
    return buffer.getvalue()


def exporter_docx(mission_id: str):
    _, mission = get_mission_or_404(mission_id)
    valeurs = _serialize(mission)["valeurs"]
    nom = re.sub(r"[^\w\-]+", "_", valeurs.get("sigle") or valeurs.get("denomination") or "entite", flags=re.ASCII).strip("_")
    return Response(
        content=_construire_docx(valeurs),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="Fiche_signaletique_{nom or "entite"}.docx"'},
    )
