from app.auth import hash_password
from app.db import db

DEFAULT_PASSWORD = "Ycube@c2026"

password_hash = hash_password(DEFAULT_PASSWORD)

result = db.users.update_many(
    {},
    {"$set": {"password_hash": password_hash, "must_change_password": False}},
)

print(f"Mot de passe commun appliqué à {result.modified_count} employé(s).")
