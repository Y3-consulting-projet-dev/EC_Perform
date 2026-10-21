# Grades autorisés à créer l'équipe d'une mission, affecter/évaluer les cycles, et créer des
# missions. Le grade Assistant est en lecture seule sur ces actions (il voit tout le reste).
MANAGEMENT_GRADES = {
    "senior",
    "assistant manager",
    "manager",
    "senior manager",
    "associé",
    "associe",
}


def is_management_grade(employee) -> bool:
    grade = (employee.get("grade") or "").strip().lower()
    return grade in MANAGEMENT_GRADES


# Revue multi-niveaux (Phase 5) : ordre de la chaîne de validation et rang hiérarchique de
# chaque grade. Un grade peut agir sur son niveau et sur les niveaux inférieurs (un Manager
# peut faire la revue Senior en l'absence de Senior), jamais au-dessus.
REVIEW_LEVELS = ["senior", "manager", "associe"]
REVIEW_LEVEL_LABELS = {"senior": "Senior", "manager": "Manager", "associe": "Associé"}
REVIEW_LEVEL_RANKS = {"senior": 1, "manager": 2, "associe": 3}
GRADE_REVIEW_RANKS = {
    "senior": 1,
    "assistant manager": 1,
    "manager": 2,
    "senior manager": 2,
    "associé": 3,
    "associe": 3,
}


def review_rank(employee) -> int:
    grade = (employee.get("grade") or "").strip().lower()
    return GRADE_REVIEW_RANKS.get(grade, 0)


def can_review(employee, niveau: str) -> bool:
    return review_rank(employee) >= REVIEW_LEVEL_RANKS[niveau]
