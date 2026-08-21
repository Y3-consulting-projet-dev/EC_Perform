import mimetypes
import os
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.db.session import db
from app.services.mission_service import (
    DOCUMENT_STATUTS_TRAITES,
    default_documents,
    get_mission_or_404,
    next_phase_if_collecte_complete,
)

UPLOADS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "uploads"))
os.makedirs(UPLOADS_DIR, exist_ok=True)

INLINE_MIME_TYPES = {"application/pdf"}


def serialize_documents(mission_doc):
    documents = mission_doc.get("documents") or default_documents()
    categories = documents.get("categories", [])
    total = sum(len(c.get("documents", [])) for c in categories)
    # "recus" compte aussi les documents marqués "Non applicable" : ils sont traités au
    # même titre qu'un document reçu et ne doivent pas bloquer indéfiniment la checklist.
    recus = sum(
        1 for c in categories for d in c.get("documents", []) if d.get("statut") in DOCUMENT_STATUTS_TRAITES
    )
    return {
        "recus": recus,
        "total": total,
        "categories": categories,
        "phase": mission_doc.get("phase", ""),
    }


def get_upload_response(mission_id: str, stored_name: str) -> FileResponse:
    file_path = os.path.abspath(os.path.join(UPLOADS_DIR, mission_id, stored_name))
    if not file_path.startswith(UPLOADS_DIR + os.sep) or not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="Fichier introuvable")

    original_name = stored_name.split("_", 1)[1] if "_" in stored_name else stored_name
    mime_type, _ = mimetypes.guess_type(original_name)
    is_inline = mime_type in INLINE_MIME_TYPES or (mime_type or "").startswith("image/")

    return FileResponse(
        file_path,
        media_type=mime_type or "application/octet-stream",
        filename=original_name,
        content_disposition_type="inline" if is_inline else "attachment",
    )


def get_mission_documents(mission_id: str):
    object_id, mission = get_mission_or_404(mission_id)

    if "documents" not in mission:
        db.missions.update_one({"_id": object_id}, {"$set": {"documents": default_documents()}})
        mission = db.missions.find_one({"_id": object_id})

    return serialize_documents(mission)


def add_mission_document(
    mission_id: str,
    categorie: str,
    description: str,
    version: str,
    date_demande: str,
    statut: str,
    fichier: UploadFile | None,
):
    object_id, mission = get_mission_or_404(mission_id)

    categorie = categorie.strip()
    description = description.strip()
    if not categorie or not description:
        raise HTTPException(status_code=400, detail="Catégorie et description requises")

    documents = mission.get("documents") or default_documents()
    category = next((c for c in documents["categories"] if c["title"] == categorie), None)
    if category is None:
        category = {"title": categorie, "documents": []}
        documents["categories"].append(category)

    file_name = None
    file_url = None
    if fichier is not None and fichier.filename:
        mission_dir = os.path.join(UPLOADS_DIR, mission_id)
        os.makedirs(mission_dir, exist_ok=True)
        safe_name = os.path.basename(fichier.filename)
        stored_name = f"{uuid.uuid4().hex}_{safe_name}"
        with open(os.path.join(mission_dir, stored_name), "wb") as f:
            f.write(fichier.file.read())
        file_name = safe_name
        file_url = f"/uploads/{mission_id}/{stored_name}"

    document = {
        "id": uuid.uuid4().hex,
        "description": description,
        "version": version.strip() or "Electronique",
        "dateDemande": date_demande.strip() or "-",
        "dateReception": datetime.now(timezone.utc).strftime("%Y-%m-%d") if statut == "Reçu" else "-",
        "statut": statut,
        "fileName": file_name,
        "fileUrl": file_url,
    }
    category["documents"].append(document)

    update_fields = {"documents": documents}
    next_phase = next_phase_if_collecte_complete(mission.get("phase", ""), documents)
    if next_phase:
        update_fields["phase"] = next_phase

    db.missions.update_one({"_id": object_id}, {"$set": update_fields})
    updated = db.missions.find_one({"_id": object_id})
    return serialize_documents(updated)


def update_mission_document(mission_id: str, document_id: str, statut: str):
    object_id, mission = get_mission_or_404(mission_id)

    documents = mission.get("documents") or default_documents()
    target = None
    for category in documents["categories"]:
        for d in category["documents"]:
            if d["id"] == document_id:
                target = d
                break
        if target:
            break
    if target is None:
        raise HTTPException(status_code=404, detail="Document introuvable")

    target["statut"] = statut
    if statut == "Reçu":
        target["dateReception"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    update_fields = {"documents": documents}
    next_phase = next_phase_if_collecte_complete(mission.get("phase", ""), documents)
    if next_phase:
        update_fields["phase"] = next_phase

    db.missions.update_one({"_id": object_id}, {"$set": update_fields})
    updated = db.missions.find_one({"_id": object_id})
    return serialize_documents(updated)
