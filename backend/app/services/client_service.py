from datetime import datetime, timedelta, timezone

from bson import ObjectId

from app.db.session import db
from app.services.mission_service import serialize_mission


def serialize_client(doc):
    # The `clients` collection mixes two schemas: records bulk-imported from the legacy
    # source (company_name/sector/legal_form/RCCM/address/responsable_*) and records
    # created via the app (raisonSociale/secteurActivite/...). Fall back across both.
    address = doc.get("adresse") or doc.get("address") or ""
    address = address.strip()

    ville = doc.get("ville") or ""
    if not ville and address:
        parts = [p.strip() for p in address.split(",") if p.strip()]
        ville = parts[-1] if parts else ""

    contact_principal = doc.get("contactPrincipal") or ""
    if not contact_principal:
        civility = (doc.get("civility") or "").strip()
        name = (doc.get("responsable_name") or "").strip()
        function = (doc.get("responsable_function") or "").strip()
        who = " ".join(p for p in [civility, name] if p)
        contact_principal = f"{who} - {function}" if who and function else who or function

    return {
        "id": str(doc["_id"]),
        "raisonSociale": doc.get("raisonSociale") or doc.get("company_name") or "",
        "secteurActivite": doc.get("secteurActivite") or doc.get("sector") or "",
        "formeJuridique": doc.get("formeJuridique") or doc.get("legal_form") or "",
        "rccm": doc.get("rccm") or doc.get("RCCM") or "",
        "compteContribuable": doc.get("compteContribuable", ""),
        "regimeFiscal": doc.get("regimeFiscal", ""),
        "adresse": address,
        "exerciceComptable": doc.get("exerciceComptable", ""),
        "ville": ville,
        "contactPrincipal": contact_principal,
        "email": doc.get("email", ""),
        "telephone": doc.get("telephone", ""),
        "missionsEnCours": doc.get("missionsEnCours", 0),
        "missions": doc.get("missions", []),
    }


def get_stats():
    total = db.clients.count_documents({})
    cutoff = datetime.now(timezone.utc) - timedelta(days=90)
    new_last_three_months = db.clients.count_documents({"_id": {"$gte": ObjectId.from_datetime(cutoff)}})
    return {"total": total, "newLastThreeMonths": new_last_three_months}


def list_clients():
    clients = [serialize_client(c) for c in db.clients.find()]
    clients.sort(key=lambda c: c["raisonSociale"].lower())

    missions_by_client = {}
    for m in db.missions.find():
        missions_by_client.setdefault(m["clientId"], []).append(serialize_mission(m))
    for c in clients:
        c["missions"] = missions_by_client.get(c["id"], [])
        c["missionsEnCours"] = sum(1 for m in c["missions"] if m["statut"] == "En cours")

    return clients


def create_client(payload_dict):
    doc = dict(payload_dict)
    doc["missionsEnCours"] = 0
    doc["missions"] = []
    result = db.clients.insert_one(doc)
    created = db.clients.find_one({"_id": result.inserted_id})
    return serialize_client(created)
