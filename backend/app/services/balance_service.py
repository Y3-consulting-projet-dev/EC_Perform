import logging
import os
import re

from fastapi import HTTPException

from app.services.balance_engine import (
    compute_coherence,
    compute_intangibilite,
    compute_vraisemblance,
    parse_balance_file,
)
from app.services.document_service import UPLOADS_DIR
from app.services.mission_service import default_documents, get_mission_or_404

logger = logging.getLogger(__name__)


def _detect_annee(*texts):
    for text in texts:
        match = re.search(r"(19|20)\d{2}", text or "")
        if match:
            return int(match.group(0))
    return None


def balance_candidates(mission):
    documents = mission.get("documents") or default_documents()
    candidates = []
    for category in documents.get("categories", []):
        for document in category.get("documents", []):
            if not document.get("fileUrl"):
                continue
            description = document.get("description", "")
            file_name = document.get("fileName", "")
            if not (re.search(r"balance", description, re.I) or re.search(r"balance", file_name, re.I)):
                continue
            candidates.append(
                {
                    "documentId": document["id"],
                    "description": description,
                    "fileName": file_name,
                    "fileUrl": document["fileUrl"],
                    "annee": _detect_annee(description, file_name),
                }
            )
    candidates.sort(key=lambda c: (c["annee"] is None, -(c["annee"] or 0)))
    return candidates


def _find_mission_document(mission, document_id):
    documents = mission.get("documents") or default_documents()
    for category in documents.get("categories", []):
        for document in category.get("documents", []):
            if document.get("id") == document_id:
                return document
    return None


def _document_file_path(mission_id, document):
    stored_name = document["fileUrl"].rsplit("/", 1)[-1]
    return os.path.join(UPLOADS_DIR, mission_id, stored_name)


def parse_balance_document(mission_id, mission, document_id, label):
    document = _find_mission_document(mission, document_id)
    if document is None or not document.get("fileUrl"):
        raise HTTPException(status_code=404, detail=f"Balance {label} introuvable")
    try:
        return parse_balance_file(_document_file_path(mission_id, document)), document
    except Exception:
        logger.exception("Échec de lecture de la balance %s (document_id=%s)", label, document_id)
        raise HTTPException(status_code=400, detail=f"Impossible de lire le fichier de la balance {label}")


def get_mission_balances(mission_id: str):
    _, mission = get_mission_or_404(mission_id)
    return {"balances": balance_candidates(mission)}


def get_controle_intangibilite(mission_id: str, document_id_n: str | None, document_id_n_moins1: str | None):
    _, mission = get_mission_or_404(mission_id)
    candidates = balance_candidates(mission)

    if not document_id_n or not document_id_n_moins1:
        if len(candidates) < 2:
            raise HTTPException(status_code=404, detail="Balances N et N-1 introuvables pour cette mission")
        document_id_n = document_id_n or candidates[0]["documentId"]
        document_id_n_moins1 = document_id_n_moins1 or candidates[1]["documentId"]

    comptes_n, document_n = parse_balance_document(mission_id, mission, document_id_n, "N")
    comptes_n_moins1, document_n_moins1 = parse_balance_document(mission_id, mission, document_id_n_moins1, "N-1")

    resultat = compute_intangibilite(comptes_n, comptes_n_moins1)
    annee_n = _detect_annee(document_n.get("description", ""), document_n.get("fileName", ""))
    annee_n_moins1 = _detect_annee(document_n_moins1.get("description", ""), document_n_moins1.get("fileName", ""))
    resultat["periodeN"] = str(annee_n) if annee_n else document_n.get("description", "")
    resultat["periodeNMoins1"] = str(annee_n_moins1) if annee_n_moins1 else document_n_moins1.get("description", "")
    resultat["documentIdN"] = document_id_n
    resultat["documentIdNMoins1"] = document_id_n_moins1
    return resultat


def get_controle_coherence(mission_id: str, document_id: str | None):
    _, mission = get_mission_or_404(mission_id)
    candidates = balance_candidates(mission)

    if not document_id:
        if not candidates:
            raise HTTPException(status_code=404, detail="Aucune balance trouvée pour cette mission")
        document_id = candidates[0]["documentId"]

    comptes, document = parse_balance_document(mission_id, mission, document_id, "sélectionnée")
    resultat = compute_coherence(comptes)
    resultat["vraisemblance"] = compute_vraisemblance(comptes)
    annee = _detect_annee(document.get("description", ""), document.get("fileName", ""))
    resultat["annee"] = str(annee) if annee else document.get("description", "")
    resultat["documentId"] = document_id
    return resultat
