from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException

from app.db.session import db
from app.services.cycle_service import CYCLES
from app.services.mission_service import get_mission_or_404, parse_date

RISQUE_OPTIONS = ["Élevé", "Moyen", "Faible"]
DEFAULT_RISQUE = "Moyen"

CYCLE_CODES = {cycle["code"] for cycle in CYCLES}
CYCLE_LIBELLES = {cycle["code"]: cycle["libelle"] for cycle in CYCLES}

# Grades autorisés à créer l'équipe et à affecter/évaluer les cycles (risque, collaborateur
# assigné, délai). Les autres grades (ex. Assistant) sont en lecture seule sur cette page.
CYCLE_MANAGEMENT_GRADES = {
    "senior",
    "assistant manager",
    "manager",
    "senior manager",
    "associé",
    "associe",
}


def peut_gerer_repartition(employee):
    grade = (employee.get("grade") or "").strip().lower()
    return grade in CYCLE_MANAGEMENT_GRADES


def _verifier_droit_gestion(employee):
    if not peut_gerer_repartition(employee):
        raise HTTPException(
            status_code=403,
            detail="Seuls les grades senior et au-dessus peuvent créer l'équipe et affecter les cycles.",
        )


def _serialize_row(code, assignment):
    assignment = assignment or {}
    return {
        "code": code,
        "libelle": CYCLE_LIBELLES[code],
        "risque": assignment.get("risque") or DEFAULT_RISQUE,
        "assigneA": assignment.get("assigneA"),
        "delai": assignment.get("delai"),
    }


def get_repartition(mission_id: str):
    _, mission = get_mission_or_404(mission_id)
    assignments = mission.get("cycleAssignments") or {}
    return [_serialize_row(cycle["code"], assignments.get(cycle["code"])) for cycle in CYCLES]


def update_repartition(mission_id: str, code: str, risque: str, assigne_a: str | None, delai: str | None, employee):
    _verifier_droit_gestion(employee)

    if code not in CYCLE_CODES:
        raise HTTPException(status_code=404, detail="Cycle introuvable")
    if risque not in RISQUE_OPTIONS:
        raise HTTPException(status_code=400, detail="Risque invalide")
    if delai and parse_date(delai) is None:
        raise HTTPException(status_code=400, detail="Date d'échéance invalide")
    if assigne_a:
        try:
            employee_object_id = ObjectId(assigne_a)
        except InvalidId:
            raise HTTPException(status_code=400, detail="Collaborateur invalide")
        if db.employees.find_one({"_id": employee_object_id}) is None:
            raise HTTPException(status_code=404, detail="Collaborateur introuvable")

    object_id, mission = get_mission_or_404(mission_id)
    assignments = mission.get("cycleAssignments") or {}
    assignments[code] = {"risque": risque, "assigneA": assigne_a, "delai": delai}
    db.missions.update_one({"_id": object_id}, {"$set": {"cycleAssignments": assignments}})

    return _serialize_row(code, assignments[code])


def get_equipe(mission_id: str):
    _, mission = get_mission_or_404(mission_id)
    return {"equipe": mission.get("equipe") or []}


def set_equipe(mission_id: str, employee_ids, employee):
    _verifier_droit_gestion(employee)

    unique_ids = list(dict.fromkeys(employee_ids))
    object_ids = []
    for employee_id in unique_ids:
        try:
            object_ids.append(ObjectId(employee_id))
        except InvalidId:
            raise HTTPException(status_code=400, detail="Collaborateur invalide")

    found_count = db.employees.count_documents({"_id": {"$in": object_ids}})
    if found_count != len(unique_ids):
        raise HTTPException(status_code=404, detail="Un ou plusieurs collaborateurs sont introuvables")

    object_id, _ = get_mission_or_404(mission_id)
    db.missions.update_one({"_id": object_id}, {"$set": {"equipe": unique_ids}})
    return {"equipe": unique_ids}
