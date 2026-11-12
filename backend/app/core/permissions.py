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


# Rapport final (Phase 6). L'émission fige le rapport : réservée à l'Associé (rang 3), selon la
# recommandation retenue le 09/11/2026 (rôle à confirmer par le cabinet : modifier ce rang suffit).
RANG_EMISSION_RAPPORT = 3


def peut_emettre_rapport(employee) -> bool:
    return review_rank(employee) >= RANG_EMISSION_RAPPORT


def intervenants(mission, role: str) -> list[str]:
    """Noms des managers (role="manager") ou seniors (role="senior") désignés sur la mission.
    Listes `managers` / `seniors` ; les missions plus anciennes n'ont qu'un champ texte `manager` / `senior`."""
    noms = mission.get(f"{role}s")
    if not isinstance(noms, list):
        noms = [mission.get(role) or ""]
    return [n.strip() for n in noms if isinstance(n, str) and n.strip()]


def est_affecte(employee, mission) -> bool:
    """Collaborateur affecté à la mission : membre de l'équipe (Phase 3), affecté à un cycle, ou
    désigné comme senior / manager de la mission (noms : comparaison sur le nom complet)."""
    employee_id = str(employee["_id"])
    if employee_id in (mission.get("equipe") or []):
        return True
    if any((a or {}).get("assigneA") == employee_id for a in (mission.get("cycleAssignments") or {}).values()):
        return True
    nom = f"{employee.get('prenoms', '')} {employee.get('nom', '')}".strip().lower()
    designes = {n.lower() for role in ("senior", "manager") for n in intervenants(mission, role)}
    return bool(nom) and nom in designes


def peut_ouvrir_mission(employee, mission) -> bool:
    """Accès à l'espace de travail d'une mission : collaborateur affecté (équipe, cycle, senior /
    manager), créateur de la mission, ou Associé (signe les rapports de toutes les missions).
    Les autres voient la mission dans les listes sans pouvoir l'ouvrir."""
    if est_affecte(employee, mission):
        return True
    if (mission.get("createdBy") or {}).get("id") == str(employee["_id"]):
        return True
    return review_rank(employee) >= RANG_EMISSION_RAPPORT
