import uuid

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException, UploadFile
from pymongo import ReturnDocument

from app.core.permissions import REVIEW_LEVEL_LABELS, REVIEW_LEVELS, can_review
from app.db.session import db
from app.services.document_service import store_upload
from app.services.mission_service import get_mission_or_404
from app.services.revision_referentiel import (
    CHECKLISTS,
    ETAPES,
    SEUIL_ALERTE_ROUNDS,
    STATUT_CLOTURE,
    STATUTS_REVUE,
)
from app.services.revision_service import (
    auteur,
    get_revision_doc,
    now_iso,
    peut_reviser,
    serialize_revision,
    sync_mission_phase,
    verifier_code,
)


def _verifier_droit(employee, niveau):
    if not can_review(employee, niveau):
        raise HTTPException(
            status_code=403,
            detail=f"Votre grade ne permet pas d'intervenir au niveau {REVIEW_LEVEL_LABELS[niveau]}.",
        )


def _verifier_niveau_actif(doc, niveau):
    if doc["statut"] != STATUTS_REVUE[niveau]:
        raise HTTPException(
            status_code=409,
            detail=f"Le cycle n'est pas en revue {REVIEW_LEVEL_LABELS[niveau]}.",
        )


def _points_ouverts(mission_id, code, niveau):
    return list(db.review_points.find({"missionId": mission_id, "cycleCode": code, "niveau": niveau, "statut": "ouvert"}))


def update_checklist(mission_id: str, code: str, niveau: str, items: dict, employee):
    _, mission = get_mission_or_404(mission_id)
    doc = get_revision_doc(mission_id, code)
    _verifier_droit(employee, niveau)
    _verifier_niveau_actif(doc, niveau)

    cles = {cle for cle, _ in CHECKLISTS[niveau]}
    actuels = (doc.get("checklists") or {}).get(niveau) or {}
    par, le = auteur(employee), now_iso()
    sets = {}
    for cle, coche in items.items():
        if cle not in cles:
            raise HTTPException(status_code=400, detail=f"Point de contrôle inconnu : {cle}")
        if (actuels.get(cle) or {}).get("coche", False) != coche:
            sets[f"checklists.{niveau}.{cle}"] = {"coche": coche, "par": par, "le": le}

    if sets:
        doc = db.cycle_revisions.find_one_and_update(
            {"_id": doc["_id"], "statut": STATUTS_REVUE[niveau]},
            {"$set": sets, "$inc": {"version": 1}},
            return_document=ReturnDocument.AFTER,
        )
        if doc is None:
            raise HTTPException(status_code=409, detail="Le statut du cycle a changé entre-temps. Rechargez la page.")
    return serialize_revision(doc, mission, employee)


def valider(mission_id: str, code: str, niveau: str, employee):
    _, mission = get_mission_or_404(mission_id)
    doc = get_revision_doc(mission_id, code)
    _verifier_droit(employee, niveau)
    _verifier_niveau_actif(doc, niveau)

    ouverts = _points_ouverts(mission_id, code, niveau)
    if ouverts:
        refs = ", ".join(p["ref"] for p in ouverts)
        raise HTTPException(
            status_code=409,
            detail=f"Validation bloquée : {len(ouverts)} point(s) de revue encore ouvert(s) ({refs}).",
        )
    checklist = (doc.get("checklists") or {}).get(niveau) or {}
    if not all((checklist.get(cle) or {}).get("coche") for cle, _ in CHECKLISTS[niveau]):
        raise HTTPException(
            status_code=409,
            detail=f"La grille de revue {REVIEW_LEVEL_LABELS[niveau]} doit être entièrement cochée avant validation.",
        )

    index = REVIEW_LEVELS.index(niveau)
    suivant = REVIEW_LEVELS[index + 1] if index + 1 < len(REVIEW_LEVELS) else None
    par, le = auteur(employee), now_iso()
    updated = db.cycle_revisions.find_one_and_update(
        {"_id": doc["_id"], "statut": STATUTS_REVUE[niveau]},
        {
            "$set": {
                "statut": STATUTS_REVUE[suivant] if suivant else STATUT_CLOTURE,
                f"validations.{niveau}": {"par": par, "le": le, "modifieApresValidation": False},
                "updatedAt": le,
                "updatedBy": par,
            },
            "$inc": {"version": 1},
            "$push": {"historique": {"action": "validation", "niveau": niveau, "par": par, "le": le}},
        },
        return_document=ReturnDocument.AFTER,
    )
    if updated is None:
        raise HTTPException(status_code=409, detail="Le statut du cycle a changé entre-temps. Rechargez la page.")
    sync_mission_phase(mission_id)
    return serialize_revision(updated, mission, employee)


def retour(mission_id: str, code: str, niveau: str, commentaire: str, employee):
    """Renvoie uniquement ce cycle au collaborateur, à l'étape la plus en amont visée par les
    points ouverts du niveau. Chaque point renvoyé voit son compteur de rounds incrémenté."""
    _, mission = get_mission_or_404(mission_id)
    doc = get_revision_doc(mission_id, code)
    _verifier_droit(employee, niveau)
    _verifier_niveau_actif(doc, niveau)

    ouverts = _points_ouverts(mission_id, code, niveau)
    if not ouverts:
        raise HTTPException(
            status_code=400,
            detail="Ajoutez au moins un point de revue ouvert avant de renvoyer le cycle au collaborateur.",
        )

    etape_cible = min((p["cible"]["etape"] for p in ouverts), key=ETAPES.index)
    par, le = auteur(employee), now_iso()
    updated = db.cycle_revisions.find_one_and_update(
        {"_id": doc["_id"], "statut": STATUTS_REVUE[niveau]},
        {
            "$set": {
                "statut": etape_cible,
                "retourDe": niveau,
                f"validations.{niveau}": None,
                "updatedAt": le,
                "updatedBy": par,
            },
            "$inc": {"version": 1},
            "$push": {
                "historique": {
                    "action": "retour",
                    "niveau": niveau,
                    "par": par,
                    "le": le,
                    "commentaire": commentaire.strip(),
                    "points": [p["ref"] for p in ouverts],
                }
            },
        },
        return_document=ReturnDocument.AFTER,
    )
    if updated is None:
        raise HTTPException(status_code=409, detail="Le statut du cycle a changé entre-temps. Rechargez la page.")

    ids = [p["_id"] for p in ouverts]
    db.review_points.update_many({"_id": {"$in": ids}}, {"$inc": {"roundCount": 1}})
    db.review_points.update_many(
        {"_id": {"$in": ids}, "roundCount": {"$gt": SEUIL_ALERTE_ROUNDS}},
        {"$set": {"alerte": True}},
    )
    return serialize_revision(updated, mission, employee)


# --- Points de revue ---------------------------------------------------------------------


def serialize_point(point):
    return {
        "id": str(point["_id"]),
        "ref": point["ref"],
        "cycleCode": point["cycleCode"],
        "niveau": point["niveau"],
        "niveauLabel": REVIEW_LEVEL_LABELS[point["niveau"]],
        "auteur": point["auteur"],
        "corps": point["corps"],
        "cible": point["cible"],
        "statut": point["statut"],
        "roundCount": point.get("roundCount", 0),
        "alerte": point.get("alerte", False),
        "reponses": point.get("reponses") or [],
        "createdAt": point.get("createdAt"),
        "clearedAt": point.get("clearedAt"),
        "clearedBy": point.get("clearedBy"),
    }


def _get_point_or_404(mission_id, code, point_id):
    try:
        object_id = ObjectId(point_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Point de revue invalide")
    point = db.review_points.find_one({"_id": object_id, "missionId": mission_id, "cycleCode": code})
    if point is None:
        raise HTTPException(status_code=404, detail="Point de revue introuvable")
    return point


def list_points(mission_id: str, code: str):
    verifier_code(code)
    get_mission_or_404(mission_id)
    points = db.review_points.find({"missionId": mission_id, "cycleCode": code}).sort("createdAt", 1)
    return [serialize_point(p) for p in points]


def create_point(mission_id: str, code: str, niveau: str, corps: str, cible: dict, employee):
    get_mission_or_404(mission_id)
    doc = get_revision_doc(mission_id, code)
    _verifier_droit(employee, niveau)
    _verifier_niveau_actif(doc, niveau)
    if not corps.strip():
        raise HTTPException(status_code=400, detail="Le texte du point de revue est requis.")

    compteur = db.counters.find_one_and_update(
        {"_id": f"review_points:{mission_id}:{code}"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    point = {
        "ref": f"{code}-{compteur['seq']}",
        "missionId": mission_id,
        "cycleCode": code,
        "niveau": niveau,
        "auteur": auteur(employee),
        "corps": corps.strip(),
        "cible": cible,
        "statut": "ouvert",
        "roundCount": 0,
        "alerte": False,
        "reponses": [],
        "createdAt": now_iso(),
        "clearedAt": None,
        "clearedBy": None,
    }
    result = db.review_points.insert_one(point)
    point["_id"] = result.inserted_id
    return serialize_point(point)


def repondre(
    mission_id: str,
    code: str,
    point_id: str,
    texte: str,
    pt_ref: str,
    fichiers: list[UploadFile],
    employee,
):
    _, mission = get_mission_or_404(mission_id)
    doc = get_revision_doc(mission_id, code)
    if not peut_reviser(employee, mission, code):
        raise HTTPException(status_code=403, detail="Ce cycle est affecté à un autre collaborateur.")
    if doc["statut"] == STATUT_CLOTURE:
        raise HTTPException(status_code=409, detail="Le cycle est clôturé.")

    point = _get_point_or_404(mission_id, code, point_id)
    if point["statut"] != "ouvert":
        raise HTTPException(status_code=409, detail="Ce point de revue est déjà clôturé.")

    fichiers = [f for f in fichiers if f.filename]
    if not texte.strip() and not fichiers:
        raise HTTPException(status_code=400, detail="Rédigez une réponse ou joignez une pièce.")

    pieces = []
    for fichier in fichiers:
        file_name, file_url = store_upload(mission_id, fichier.filename, fichier.file.read())
        pieces.append({"fileName": file_name, "fileUrl": file_url})

    reponse = {
        "id": uuid.uuid4().hex,
        "texte": texte.strip(),
        "ptRef": pt_ref.strip() or None,
        "pieces": pieces,
        "auteur": auteur(employee),
        "le": now_iso(),
    }
    updated = db.review_points.find_one_and_update(
        {"_id": point["_id"]},
        {"$push": {"reponses": reponse}},
        return_document=ReturnDocument.AFTER,
    )
    return serialize_point(updated)


def changer_statut_point(mission_id: str, code: str, point_id: str, statut: str, employee):
    get_mission_or_404(mission_id)
    doc = get_revision_doc(mission_id, code)
    point = _get_point_or_404(mission_id, code, point_id)
    niveau = point["niveau"]
    _verifier_droit(employee, niveau)
    # Seul le niveau émetteur clôture ses points, une fois le cycle revenu à son niveau.
    if doc["statut"] != STATUTS_REVUE[niveau]:
        raise HTTPException(
            status_code=409,
            detail=f"Le cycle doit être en revue {REVIEW_LEVEL_LABELS[niveau]} pour changer le statut de ce point.",
        )

    if statut == "cleared":
        sets = {"statut": "cleared", "clearedAt": now_iso(), "clearedBy": auteur(employee)}
    else:
        sets = {"statut": "ouvert", "clearedAt": None, "clearedBy": None}
    updated = db.review_points.find_one_and_update(
        {"_id": point["_id"]},
        {"$set": sets},
        return_document=ReturnDocument.AFTER,
    )
    return serialize_point(updated)
