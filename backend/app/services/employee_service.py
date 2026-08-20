from app.core.security import hash_password, verify_password
from app.db.session import db


def serialize_employee_summary(doc):
    return {
        "nom": doc.get("nom", ""),
        "prenoms": doc.get("prenoms", ""),
        "grade": doc.get("grade", ""),
        "departement": doc.get("departement", ""),
        "email": doc.get("email", ""),
    }


def authenticate(email: str, password: str):
    employee = db.employees.find_one({"email": email.strip().lower()})
    if employee is None or not verify_password(password, employee["password_hash"]):
        return None
    return employee


def change_password(employee, current_password: str, new_password: str) -> bool:
    if not verify_password(current_password, employee["password_hash"]):
        return False
    db.employees.update_one(
        {"_id": employee["_id"]},
        {"$set": {"password_hash": hash_password(new_password), "must_change_password": False}},
    )
    return True


def update_profile(employee, nom: str, prenoms: str):
    db.employees.update_one(
        {"_id": employee["_id"]},
        {"$set": {"nom": nom.strip(), "prenoms": prenoms.strip()}},
    )
    return db.employees.find_one({"_id": employee["_id"]})


def list_employees():
    employees = db.employees.find().sort("nom", 1)
    return [
        {
            "id": str(e["_id"]),
            "nom": e.get("nom", ""),
            "prenoms": e.get("prenoms", ""),
            "grade": e.get("grade", ""),
            "departement": e.get("departement", ""),
        }
        for e in employees
    ]
