from app.db.session import db

result = db.status.insert_one({"initialized": True})
print(f"Base '{db.name}' créée avec la collection 'status' (id={result.inserted_id})")
