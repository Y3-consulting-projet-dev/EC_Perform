import json
import uuid
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException
from pydantic import ValidationError
from pymongo import ReturnDocument

from app.core.permissions import REVIEW_LEVEL_LABELS, REVIEW_LEVELS, can_review, is_management_grade
from app.db.session import db
from app.models.revision import ConclusionData, ConstatsData, JustificationData, LeadData, PriseConnaissanceData
from app.services.cycle_service import CYCLES
from app.services.document_service import store_upload
from app.services.mission_service import MISSION_STEP_LABELS, get_mission_or_404, mission_step
from app.services.revision_referentiel import (
    ASSERTIONS,
    CHECKLISTS,
    ETAPES,
    OBJECTIFS_NIVEAU,
    STATUT_CLOTURE,
    STATUTS_REVUE,
)

CYCLE_LIBELLES = {cycle["code"]: cycle["libelle"] for cycle in CYCLES}

# Section éditable -> (schéma de validation, étape à laquelle elle appartient).
SECTIONS = {
    "priseConnaissance": (PriseConnaissanceData, "4a"),
    "lead": (LeadData, "4b"),
    "justification": (JustificationData, "4c"),
    "constats": (ConstatsData, "4e"),
    "conclusion": (ConclusionData, "4f"),
}


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def auteur(employee):
    return {
        "id": str(employee["_id"]),
        "nom": f"{employee.get('prenoms', '')} {employee.get('nom', '')}".strip(),
        "grade": employee.get("grade", ""),
    }


def _employee_by_id(employee_id):
    if not employee_id:
        return None
    try:
        employee = db.employees.find_one({"_id": ObjectId(employee_id)})
    except InvalidId:
        return None
    return auteur(employee) if employee else None


def verifier_code(code: str):
    if code not in CYCLE_LIBELLES:
        raise HTTPException(status_code=404, detail="Cycle introuvable")


def _default_revision():
    return {
        "statut": "4a",
        "retourDe": None,
        "priseConnaissance": {"processus": "", "risques": [], "referentiel": ""},
        "lead": {"commentaires": {}},
        "justification": {"assertions": {}, "pieces": [], "commentaire": {"texte": "", "par": None, "le": None}},
        "constats": [],
        "conclusion": {"synthese": "", "ajustements": [], "decision": None},
        "checklists": {niveau: {} for niveau in REVIEW_LEVELS},
        "validations": {"collaborateur": None, **{niveau: None for niveau in REVIEW_LEVELS}},
        "historique": [],
        "version": 0,
        "createdAt": now_iso(),
        "updatedAt": None,
        "updatedBy": None,
    }


def get_revision_doc(mission_id: str, code: str):
    """Retourne le document de révision du cycle, en le créant au premier accès."""
    verifier_code(code)
    return db.cycle_revisions.find_one_and_update(
        {"missionId": mission_id, "code": code},
        {"$setOnInsert": _default_revision()},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )


def est_verrouille(doc) -> bool:
    return doc["statut"] not in ETAPES


def peut_reviser(employee, mission, code) -> bool:
    """Le collaborateur affecté au cycle (Phase 3) ou un grade d'encadrement. Si personne n'est
    affecté, tout membre du cabinet peut travailler sur le cycle."""
    assignment = (mission.get("cycleAssignments") or {}).get(code) or {}
    assigne = assignment.get("assigneA")
    return is_management_grade(employee) or not assigne or assigne == str(employee["_id"])


def verifier_edition(doc, mission, employee):
    if est_verrouille(doc):
        raise HTTPException(
            status_code=409,
            detail="Le cycle est soumis en revue : les travaux sont en lecture seule.",
        )
    if not peut_reviser(employee, mission, doc["code"]):
        raise HTTPException(status_code=403, detail="Ce cycle est affecté à un autre collaborateur.")


def _niveau_actif(statut):
    return next((niveau for niveau, s in STATUTS_REVUE.items() if s == statut), None)


def _chaine(doc, mission, collaborateur):
    """Composant « chaîne de validation » : Collaborateur -> Senior -> Manager -> Associé."""
    statut = doc["statut"]
    validations = doc.get("validations") or {}
    retour_de = doc.get("retourDe")
    soumission = validations.get("collaborateur")

    if statut in ETAPES:
        etat = "retour" if retour_de else "en_cours"
    else:
        etat = "fait"
    chaine = [
        {
            "niveau": "collaborateur",
            "label": "Collaborateur",
            "etat": etat,
            "par": (soumission or {}).get("par", {}).get("nom") or (collaborateur or {}).get("nom"),
            "le": (soumission or {}).get("le"),
            "modifieApresValidation": False,
        }
    ]

    attendus = {"senior": mission.get("senior") or None, "manager": mission.get("manager") or None, "associe": None}
    for niveau in REVIEW_LEVELS:
        validation = validations.get(niveau)
        if statut == STATUTS_REVUE[niveau]:
            etat = "en_cours"
        elif validation or statut == STATUT_CLOTURE:
            etat = "fait"
        elif retour_de == niveau and statut in ETAPES:
            etat = "retour"
        else:
            etat = "en_attente"
        chaine.append(
            {
                "niveau": niveau,
                "label": REVIEW_LEVEL_LABELS[niveau],
                "etat": etat,
                "par": validation["par"]["nom"] if validation else attendus[niveau],
                "le": validation["le"] if validation else None,
                "modifieApresValidation": bool(validation and validation.get("modifieApresValidation")),
            }
        )
    return chaine


def _serialize_checklists(doc):
    stored = doc.get("checklists") or {}
    return {
        niveau: {
            "objectif": OBJECTIFS_NIVEAU[niveau],
            "items": [
                {
                    "cle": cle,
                    "libelle": libelle,
                    "coche": (stored.get(niveau) or {}).get(cle, {}).get("coche", False),
                    "par": (stored.get(niveau) or {}).get(cle, {}).get("par"),
                    "le": (stored.get(niveau) or {}).get(cle, {}).get("le"),
                }
                for cle, libelle in items
            ],
        }
        for niveau, items in CHECKLISTS.items()
    }


def _compteurs_points(mission_id, code):
    ouverts = {niveau: 0 for niveau in REVIEW_LEVELS}
    alertes = 0
    for point in db.review_points.find({"missionId": mission_id, "cycleCode": code}, {"niveau": 1, "statut": 1, "alerte": 1}):
        if point["statut"] == "ouvert":
            ouverts[point["niveau"]] += 1
            if point.get("alerte"):
                alertes += 1
    return ouverts, alertes


def _droits(doc, mission, employee):
    """Ce que l'utilisateur courant peut faire sur ce cycle, pour piloter l'interface."""
    reviseur = peut_reviser(employee, mission, doc["code"])
    return {
        "editer": reviseur and not est_verrouille(doc),
        "repondre": reviseur and doc["statut"] != STATUT_CLOTURE,
        "revue": {niveau: can_review(employee, niveau) for niveau in REVIEW_LEVELS},
    }


def serialize_revision(doc, mission, employee):
    assignment = (mission.get("cycleAssignments") or {}).get(doc["code"]) or {}
    collaborateur = _employee_by_id(assignment.get("assigneA"))
    justification = doc.get("justification") or {}
    assertions = justification.get("assertions") or {}
    points_ouverts, alertes = _compteurs_points(doc["missionId"], doc["code"])

    return {
        "missionId": doc["missionId"],
        "code": doc["code"],
        "libelle": CYCLE_LIBELLES[doc["code"]],
        "statut": doc["statut"],
        "verrouille": est_verrouille(doc),
        "niveauActif": _niveau_actif(doc["statut"]),
        "retourDe": doc.get("retourDe"),
        "collaborateur": collaborateur,
        "priseConnaissance": doc.get("priseConnaissance"),
        "lead": doc.get("lead"),
        "justification": {
            "assertions": [
                {
                    "cle": cle,
                    "libelle": libelle,
                    "coche": assertions.get(cle, {}).get("coche", False),
                    "par": assertions.get(cle, {}).get("par"),
                    "le": assertions.get(cle, {}).get("le"),
                }
                for cle, libelle in ASSERTIONS
            ],
            "pieces": justification.get("pieces") or [],
            "commentaire": justification.get("commentaire") or {"texte": "", "par": None, "le": None},
        },
        "constats": doc.get("constats") or [],
        "conclusion": doc.get("conclusion"),
        "checklists": _serialize_checklists(doc),
        "chaine": _chaine(doc, mission, collaborateur),
        "pointsOuverts": points_ouverts,
        "alertes": alertes,
        "historique": doc.get("historique") or [],
        "droits": _droits(doc, mission, employee),
        "version": doc["version"],
        "updatedAt": doc.get("updatedAt"),
        "updatedBy": doc.get("updatedBy"),
    }


def sync_mission_phase(mission_id: str):
    """Fait avancer la phase de la mission selon l'état des cycles (jamais de retour arrière) :
    4/7 dès qu'un cycle est en révision, 5/7 quand tous sont soumis, 6/7 quand tous sont clôturés."""
    object_id, mission = get_mission_or_404(mission_id)
    statuts = [r["statut"] for r in db.cycle_revisions.find({"missionId": mission_id}, {"statut": 1})]
    step = mission_step(mission)
    target = step
    if statuts and step < 4:
        target = 4
    if len(statuts) == len(CYCLE_LIBELLES):
        if all(s not in ETAPES for s in statuts):
            target = max(target, 5)
        if all(s == STATUT_CLOTURE for s in statuts):
            target = max(target, 6)
    if target != step:
        db.missions.update_one(
            {"_id": object_id},
            {"$set": {"phase": f"{target}/7 · {MISSION_STEP_LABELS[target - 1]}"}},
        )


def get_mission_revisions(mission_id: str):
    _, mission = get_mission_or_404(mission_id)
    docs = {
        d["code"]: d
        for d in db.cycle_revisions.find(
            {"missionId": mission_id}, {"code": 1, "statut": 1, "retourDe": 1, "updatedAt": 1}
        )
    }
    result = []
    for cycle in CYCLES:
        code = cycle["code"]
        doc = docs.get(code)
        # Un cycle seulement consulté (document créé à l'ouverture, jamais modifié) n'est pas commencé.
        if doc and doc.get("updatedAt") is None:
            doc = None
        points_ouverts, alertes = _compteurs_points(mission_id, code)
        result.append(
            {
                "code": code,
                "libelle": cycle["libelle"],
                "statut": doc["statut"] if doc else "non_commence",
                "verrouille": bool(doc) and est_verrouille(doc),
                "niveauActif": _niveau_actif(doc["statut"]) if doc else None,
                "retourDe": doc.get("retourDe") if doc else None,
                "pointsOuverts": sum(points_ouverts.values()),
                "alertes": alertes,
                "assigneA": ((mission.get("cycleAssignments") or {}).get(code) or {}).get("assigneA"),
            }
        )
    return result


def get_revision(mission_id: str, code: str, employee):
    _, mission = get_mission_or_404(mission_id)
    return serialize_revision(get_revision_doc(mission_id, code), mission, employee)


def _avec_ids(items):
    return [{**item, "id": item.get("id") or uuid.uuid4().hex} for item in items]


def _appliquer_section(section, parsed, doc, par, le):
    if section == "priseConnaissance":
        risques = list(dict.fromkeys(r.strip() for r in parsed.risques if r.strip()))
        return {"priseConnaissance": {**parsed.model_dump(), "risques": risques}}

    if section == "lead":
        return {"lead.commentaires": {k: v for k, v in parsed.commentaires.items() if v.strip()}}

    if section == "justification":
        precedent = doc.get("justification") or {}
        anciennes = precedent.get("assertions") or {}
        assertions = {}
        for cle, _ in ASSERTIONS:
            ancienne = anciennes.get(cle) or {"coche": False, "par": None, "le": None}
            coche = parsed.assertions.get(cle, ancienne["coche"])
            assertions[cle] = ancienne if coche == ancienne["coche"] else {"coche": coche, "par": par, "le": le}

        ancien_commentaire = precedent.get("commentaire") or {"texte": "", "par": None, "le": None}
        commentaire = ancien_commentaire
        if parsed.commentaire != ancien_commentaire["texte"]:
            commentaire = {"texte": parsed.commentaire, "par": par, "le": le}

        return {
            "justification": {
                "assertions": assertions,
                "pieces": _avec_ids([p.model_dump() for p in parsed.pieces]),
                "commentaire": commentaire,
            }
        }

    if section == "constats":
        return {"constats": _avec_ids([c.model_dump() for c in parsed.constats])}

    if section == "conclusion":
        return {
            "conclusion": {
                "synthese": parsed.synthese,
                "ajustements": _avec_ids([a.model_dump() for a in parsed.ajustements]),
                "decision": parsed.decision,
            }
        }

    raise HTTPException(status_code=400, detail="Section inconnue")


def update_section(mission_id: str, code: str, section: str, data: dict, version: int, employee):
    _, mission = get_mission_or_404(mission_id)
    doc = get_revision_doc(mission_id, code)
    verifier_edition(doc, mission, employee)

    model, etape = SECTIONS[section]
    try:
        parsed = model.model_validate(data)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=json.loads(exc.json()))

    par, le = auteur(employee), now_iso()
    fields = _appliquer_section(section, parsed, doc, par, le)

    # Le statut suit l'étape la plus avancée atteinte, sauf « Compléter la justification »
    # qui ramène explicitement le cycle en 4c.
    statut = max(doc["statut"], etape, key=ETAPES.index)
    if section == "conclusion" and parsed.decision == "completer":
        statut = "4c"

    updated = db.cycle_revisions.find_one_and_update(
        {"_id": doc["_id"], "version": version, "statut": {"$in": ETAPES}},
        {"$set": {**fields, "statut": statut, "updatedAt": le, "updatedBy": par}, "$inc": {"version": 1}},
        return_document=ReturnDocument.AFTER,
    )
    if updated is None:
        raise HTTPException(
            status_code=409,
            detail="Le cycle a été modifié entre-temps par un autre utilisateur. Rechargez pour récupérer la dernière version.",
        )
    sync_mission_phase(mission_id)
    return serialize_revision(updated, mission, employee)


def deposer_piece(mission_id: str, code: str, fichier, employee):
    """Dépose le fichier d'une pièce probante (4c). La pièce elle-même est enregistrée avec la
    section justification ; ce dépôt ne fait que stocker le fichier."""
    _, mission = get_mission_or_404(mission_id)
    doc = get_revision_doc(mission_id, code)
    verifier_edition(doc, mission, employee)
    if not fichier.filename:
        raise HTTPException(status_code=400, detail="Fichier requis")
    file_name, file_url = store_upload(mission_id, fichier.filename, fichier.file.read())
    return {"fileName": file_name, "fileUrl": file_url}


def soumettre(mission_id: str, code: str, employee):
    _, mission = get_mission_or_404(mission_id)
    doc = get_revision_doc(mission_id, code)
    verifier_edition(doc, mission, employee)

    conclusion = doc.get("conclusion") or {}
    if conclusion.get("decision") != "justifie":
        raise HTTPException(status_code=400, detail="La décision « Cycle justifié » est requise avant la soumission.")
    if not (conclusion.get("synthese") or "").strip():
        raise HTTPException(status_code=400, detail="La synthèse du cycle doit être rédigée avant la soumission.")

    # Après un retour, le cycle revient directement au niveau qui l'a renvoyé ; les validations
    # des niveaux inférieurs restent acquises mais sont signalées comme antérieures à la modification.
    niveau = doc.get("retourDe") or "senior"
    par, le = auteur(employee), now_iso()
    sets = {
        "statut": STATUTS_REVUE[niveau],
        "retourDe": None,
        "validations.collaborateur": {"par": par, "le": le},
        "updatedAt": le,
        "updatedBy": par,
    }
    if doc.get("retourDe"):
        for inferieur in REVIEW_LEVELS[: REVIEW_LEVELS.index(niveau)]:
            if (doc.get("validations") or {}).get(inferieur):
                sets[f"validations.{inferieur}.modifieApresValidation"] = True

    updated = db.cycle_revisions.find_one_and_update(
        {"_id": doc["_id"], "statut": {"$in": ETAPES}},
        {
            "$set": sets,
            "$inc": {"version": 1},
            "$push": {"historique": {"action": "soumission", "niveau": niveau, "par": par, "le": le}},
        },
        return_document=ReturnDocument.AFTER,
    )
    if updated is None:
        raise HTTPException(status_code=409, detail="Le cycle a déjà été soumis.")
    sync_mission_phase(mission_id)
    return serialize_revision(updated, mission, employee)
