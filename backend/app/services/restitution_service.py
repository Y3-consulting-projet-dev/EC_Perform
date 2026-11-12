"""Phase 6 – Restitution client : réunion de restitution (date, lieu, participants) et, pour chaque
constat de la Phase 4, le commentaire du client et la réponse du management. Un document
`restitutions` par mission ; le rapport final lit ces données (rapport/donnees.py)."""

from bson import ObjectId
from fastapi import HTTPException
from pydantic import ValidationError
from pymongo import ReturnDocument

from app.core.permissions import est_affecte
from app.db.session import db
from app.models.rapport import RestitutionUpdate
from app.services.cycle_service import CYCLES
from app.services.mission_service import get_mission_or_404, parse_date
from app.services.revision_service import auteur, now_iso


def _nouvelle(mission_id):
    return {
        "missionId": mission_id,
        "reunion": {"date": "", "lieu": "", "participantsCabinet": [], "participantsClient": []},
        "commentaires": {},
        "version": 0,
        "createdAt": now_iso(),
        "updatedAt": None,
        "updatedBy": None,
    }


def _doc(mission_id):
    return db.restitutions.find_one_and_update(
        {"missionId": mission_id},
        {"$setOnInsert": _nouvelle(mission_id)},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )


def _constats(mission_id):
    ordre = {c["code"]: i for i, c in enumerate(CYCLES)}
    libelles = {c["code"]: c["libelle"] for c in CYCLES}
    out = []
    for rev in sorted(db.cycle_revisions.find({"missionId": mission_id}, {"code": 1, "constats": 1}),
                      key=lambda r: ordre.get(r["code"], 99)):
        for c in rev.get("constats") or []:
            out.append({
                "id": c.get("id"), "cycleCode": rev["code"], "cycleLibelle": libelles.get(rev["code"], ""),
                "famille": c.get("famille"), "constat": c.get("constat"), "severite": c.get("severite"),
                "recommandation": c.get("recommandation"), "statut": c.get("statut"),
            })
    return out


def _modifiable(employee, mission):
    rapport = db.rapports.find_one({"missionId": str(mission["_id"])}, {"statut": 1}) or {}
    if rapport.get("statut") == "emis":
        return False, "Le rapport final est émis : la restitution n'est plus modifiable."
    if not est_affecte(employee, mission):
        return False, "Réservé aux collaborateurs affectés à la mission."
    return True, None


def _serialize(doc, mission, employee):
    modifiable, raison = _modifiable(employee, mission)
    return {
        "reunion": doc.get("reunion"),
        "commentaires": doc.get("commentaires") or {},
        "constats": _constats(doc["missionId"]),
        "version": doc["version"],
        "updatedAt": doc.get("updatedAt"),
        "updatedBy": doc.get("updatedBy"),
        "modifiable": modifiable,
        "raisonLectureSeule": raison,
    }


def get_restitution(mission_id, employee):
    _, mission = get_mission_or_404(mission_id)
    return _serialize(_doc(mission_id), mission, employee)


def update_restitution(mission_id, payload: dict, employee):
    _, mission = get_mission_or_404(mission_id)
    modifiable, raison = _modifiable(employee, mission)
    if not modifiable:
        raise HTTPException(status_code=409 if "émis" in raison else 403, detail=raison)
    try:
        data = RestitutionUpdate.model_validate(payload)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=[{"loc": e["loc"], "msg": e["msg"]} for e in exc.errors()])

    reunion = data.reunion
    if reunion.date and parse_date(reunion.date) is None:
        raise HTTPException(status_code=400, detail="Date de réunion invalide")
    participants = []
    for employee_id in dict.fromkeys(reunion.participantsCabinet):
        e = db.employees.find_one({"_id": ObjectId(employee_id)}) if ObjectId.is_valid(employee_id) else None
        if e is None:
            raise HTTPException(status_code=404, detail="Collaborateur introuvable")
        participants.append({"id": employee_id, "nom": f"{e.get('prenoms', '')} {e.get('nom', '')}".strip()})

    ids_constats = {c["id"] for c in _constats(mission_id)}
    commentaires = {}
    for constat_id, c in data.commentaires.items():
        if constat_id not in ids_constats:
            raise HTTPException(status_code=400, detail="Constat introuvable")
        client, reponse = c.commentaireClient.strip(), c.reponseManagement.strip()
        if client or reponse:
            commentaires[constat_id] = {"commentaireClient": client, "reponseManagement": reponse}

    doc = _doc(mission_id)
    par, le = auteur(employee), now_iso()
    updated = db.restitutions.find_one_and_update(
        {"_id": doc["_id"], "version": data.version},
        {
            "$set": {
                "reunion": {
                    "date": reunion.date,
                    "lieu": reunion.lieu.strip(),
                    "participantsCabinet": participants,
                    "participantsClient": [p.model_dump() for p in reunion.participantsClient if p.nom.strip()],
                },
                "commentaires": commentaires,
                "updatedAt": le,
                "updatedBy": par,
            },
            "$inc": {"version": 1},
        },
        return_document=ReturnDocument.AFTER,
    )
    if updated is None:
        raise HTTPException(
            status_code=409,
            detail="La restitution a été modifiée entre-temps par un autre utilisateur. Rechargez pour récupérer la dernière version.",
        )
    return _serialize(updated, mission, employee)
