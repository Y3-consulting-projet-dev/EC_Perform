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
