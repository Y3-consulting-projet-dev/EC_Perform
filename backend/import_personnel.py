import csv
from pathlib import Path

from app.db.session import db

CSV_PATH = Path(__file__).parent / "data" / "registre_personnel.csv"

collection = db.employees
collection.create_index("email", unique=True)

inserted = 0
updated = 0

with CSV_PATH.open(encoding="utf-8-sig") as f:
    reader = csv.DictReader(f, delimiter=";")
    for row in reader:
        email = row["Mail"].strip().lower()
        doc = {
            "nom": row["NOM"].strip(),
            "prenoms": row["PRENOMS"].strip(),
            "grade": row["GRADE"].strip(),
            "departement": row["DEPARTEMENT"].strip(),
            "email": email,
        }
        result = collection.update_one({"email": email}, {"$set": doc}, upsert=True)
        if result.upserted_id is not None:
            inserted += 1
        elif result.modified_count:
            updated += 1

print(f"{inserted} employé(s) inséré(s), {updated} mis à jour, total en base: {collection.count_documents({})}")
