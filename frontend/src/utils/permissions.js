// Grades autorisés à créer l'équipe d'une mission, affecter/évaluer les cycles, et créer des
// missions. Le grade Assistant est en lecture seule sur ces actions (il voit tout le reste).
// Doit rester cohérent avec MANAGEMENT_GRADES côté backend (app/core/permissions.py).
const MANAGEMENT_GRADES = ['senior', 'assistant manager', 'manager', 'senior manager', 'associé', 'associe']

export function canManage() {
  const employee = JSON.parse(localStorage.getItem('employee') ?? '{}')
  return MANAGEMENT_GRADES.includes((employee.grade ?? '').trim().toLowerCase())
}
