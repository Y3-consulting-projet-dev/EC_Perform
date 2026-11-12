"""Rapport final (Phase 6 – Émission du rapport final) : document `rapports` (un par mission),
versions stockées dans GridFS, saisie complémentaire, génération, émission.

Statuts : genere (dernière version issue d'une génération) -> en_finition (au moins une version
enregistrée depuis ONLYOFFICE après la dernière génération) -> emis (version figée, lecture seule).
"""

import io
import logging
import os
import re
import uuid
from datetime import datetime, timedelta, timezone

import gridfs
from bson import ObjectId
from bson.errors import InvalidId
from PIL import Image
from fastapi import HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import ValidationError
from pymongo import ReturnDocument

from app.core.permissions import est_affecte, is_management_grade, peut_emettre_rapport
from app.db.session import db
from app.models.rapport import SaisieRapport
from app.services.cycle_service import CYCLES
from app.services.mission_service import get_mission_or_404
from app.services.rapport.assembleur import assembler
from app.services.rapport.donnees import collecter
from app.services.revision_service import auteur, now_iso

logger = logging.getLogger(__name__)

BUCKET = "rapport_fichiers"
MIME_PPTX = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
STATUTS = ("genere", "en_finition", "emis")
ORIGINES = ("generation", "edition_onlyoffice", "emission")
# Une session d'édition ONLYOFFICE confirmée (callback statut 1) sans nouvelle de plus de cette
# durée est considérée comme abandonnée (Document Server arrêté, etc.).
SESSION_EXPIRATION = timedelta(hours=12)
# Une config d'éditeur délivrée mais jamais confirmée par le Document Server reste réutilisable
# (même clé pour les collègues qui ouvrent en même temps) pendant ce délai.
SESSION_ATTENTE = timedelta(minutes=10)
MEDIAS = {"logo", "photo"}
EXTENSIONS_IMAGE = {".png", ".jpg", ".jpeg"}
MAX_MEDIA = 5 * 1024 * 1024


def fs():
    return gridfs.GridFSBucket(db, bucket_name=BUCKET)


def _maintenant():
    return datetime.now(timezone.utc)


def _date(valeur):
    try:
        return datetime.fromisoformat(valeur)
    except (TypeError, ValueError):
        return None


# --- Document rapport -------------------------------------------------------------------------


def _nouveau(mission_id):
    return {
        "missionId": mission_id,
        "statut": None,
        "compteurVersion": 0,
        "versions": [],
        "saisie": SaisieRapport().model_dump(),
        "saisieVersion": 0,
        "medias": {},
        "session": None,
        "emission": None,
        "pdf": None,
        "createdAt": now_iso(),
    }


def get_rapport_doc(mission_id):
    return db.rapports.find_one_and_update(
        {"missionId": mission_id},
        {"$setOnInsert": _nouveau(mission_id)},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )


def get_rapport_by_id(rapport_id):
    try:
        doc = db.rapports.find_one({"_id": ObjectId(rapport_id)})
    except (InvalidId, TypeError):
        doc = None
    if doc is None:
        raise HTTPException(status_code=404, detail="Rapport introuvable")
    return doc


def derniere_version(rapport):
    return rapport["versions"][-1] if rapport.get("versions") else None


def version_numero(rapport, numero):
    for v in rapport.get("versions") or []:
        if v["numero"] == numero:
            return v
    raise HTTPException(status_code=404, detail="Version introuvable")


def session_active(rapport, maintenant=None):
    """Session d'édition en cours (confirmée par le Document Server et récente)."""
    session = rapport.get("session")
    if not session or not session.get("confirmee"):
        return None
    maj = _date(session.get("majLe"))
    if maj is None or (maintenant or _maintenant()) - maj > SESSION_EXPIRATION:
        return None
    return session


def session_reutilisable(rapport, maintenant=None):
    """Session à rejoindre par un nouvel éditeur : active, ou délivrée il y a peu."""
    maintenant = maintenant or _maintenant()
    if session_active(rapport, maintenant):
        return rapport["session"]
    session = rapport.get("session")
    if session and not session.get("confirmee"):
        ouverte = _date(session.get("ouverteLe"))
        if ouverte and maintenant - ouverte <= SESSION_ATTENTE:
            return session
    return None


def a_des_modifications_onlyoffice(rapport):
    """Une version enregistrée depuis ONLYOFFICE existe après la dernière génération."""
    for v in reversed(rapport.get("versions") or []):
        if v["origine"] == "generation":
            return False
        if v["origine"] == "edition_onlyoffice":
            return True
    return False


# --- Fichiers (GridFS) ------------------------------------------------------------------------


def stocker_fichier(contenu, nom, metadata, content_type=MIME_PPTX):
    return fs().upload_from_stream(nom, io.BytesIO(contenu), metadata={**metadata, "contentType": content_type})


def lire_fichier(file_id):
    try:
        flux = fs().open_download_stream(ObjectId(file_id) if not isinstance(file_id, ObjectId) else file_id)
    except (gridfs.errors.NoFile, InvalidId):
        raise HTTPException(status_code=404, detail="Fichier introuvable")
    return flux.read()


def reponse_fichier(contenu, nom, media_type=MIME_PPTX, inline=False):
    disposition = "inline" if inline else "attachment"
    nom_ascii = re.sub(r"[^\w.\-]+", "_", nom, flags=re.ASCII)
    return StreamingResponse(
        io.BytesIO(contenu),
        media_type=media_type,
        headers={"Content-Disposition": f'{disposition}; filename="{nom_ascii}"'},
    )


def nom_fichier(mission, numero, extension="pptx"):
    client = db.clients.find_one({"_id": ObjectId(mission["clientId"])}) if ObjectId.is_valid(mission.get("clientId", "")) else None
    nom = (client or {}).get("raisonSociale") or (client or {}).get("company_name") or "mission"
    return f"Rapport_final_{nom}_{mission.get('exercice', '')}_v{numero}.{extension}"


def ajouter_version(rapport_id, contenu, origine, employe_auteur, metadata_extra=None, statut=None, base=None):
    """Enregistre un fichier comme nouvelle version (numéro attribué atomiquement)."""
    assert origine in ORIGINES
    doc = db.rapports.find_one_and_update(
        {"_id": rapport_id}, {"$inc": {"compteurVersion": 1}}, return_document=ReturnDocument.AFTER
    )
    numero = doc["compteurVersion"]
    file_id = stocker_fichier(contenu, f"rapport_v{numero}.pptx", {"rapportId": str(rapport_id), "numero": numero})
    version = {
        "numero": numero,
        "date": now_iso(),
        "auteur": employe_auteur,
        "origine": origine,
        "fileId": file_id,
        "taille": len(contenu),
        "baseeSur": base,
        **(metadata_extra or {}),
    }
    sets = {"statut": statut} if statut else {}
    db.rapports.update_one({"_id": rapport_id}, {"$push": {"versions": version}, **({"$set": sets} if sets else {})})
    return version


# --- Droits & sérialisation -------------------------------------------------------------------


def droits(employee, mission, rapport):
    emis = rapport.get("statut") == "emis"
    affecte = est_affecte(employee, mission)
    return {
        "editer": affecte and not emis,
        "generer": affecte and is_management_grade(employee) and not emis,
        "emettre": peut_emettre_rapport(employee) and not emis,
    }


def _cycles_non_clotures(mission_id):
    statuts = {r["code"]: r.get("statut") for r in db.cycle_revisions.find({"missionId": mission_id}, {"code": 1, "statut": 1})}
    return [{"code": c["code"], "libelle": c["libelle"]} for c in CYCLES if statuts.get(c["code"]) != "cloture"]


def _serialize_version(v):
    return {k: (str(val) if isinstance(val, ObjectId) else val) for k, val in v.items() if k != "fileId"} | {
        "fichier": True
    }


def serialize(rapport, mission, employee):
    session = session_active(rapport)
    return {
        "id": str(rapport["_id"]),
        "missionId": rapport["missionId"],
        "statut": rapport.get("statut"),
        "versions": [_serialize_version(v) for v in reversed(rapport.get("versions") or [])],
        "derniereVersion": (derniere_version(rapport) or {}).get("numero"),
        "modificationsOnlyoffice": a_des_modifications_onlyoffice(rapport),
        "sessionEdition": {"utilisateurs": session.get("utilisateurs") or [], "depuis": session.get("ouverteLe")}
        if session
        else None,
        "cyclesNonClotures": _cycles_non_clotures(rapport["missionId"]),
        "emission": rapport.get("emission"),
        "pdf": bool((rapport.get("pdf") or {}).get("fileId")),
        "pdfErreur": (rapport.get("pdf") or {}).get("erreur"),
        "medias": {k: {"nom": v.get("nom")} for k, v in (rapport.get("medias") or {}).items()},
        "derniereGeneration": rapport.get("derniereGeneration"),
        "droits": droits(employee, mission, rapport),
    }


def get_rapport(mission_id, employee):
    _, mission = get_mission_or_404(mission_id)
    return serialize(get_rapport_doc(mission_id), mission, employee)


# --- Génération -------------------------------------------------------------------------------


def _medias_blobs(rapport):
    blobs = {}
    for cle, media in (rapport.get("medias") or {}).items():
        try:
            blobs[cle] = lire_fichier(media["fileId"])
        except HTTPException:
            logger.warning("Média %s introuvable pour le rapport %s", cle, rapport["_id"])
    return blobs


def construire(mission_id, mission, rapport):
    """Génère le PPTX sans l'enregistrer : (octets, résumé)."""
    data = collecter(mission_id, mission, rapport)
    data["mediasBlobs"] = _medias_blobs(rapport)
    return assembler(data)


def generer(mission_id, employee, force=False):
    _, mission = get_mission_or_404(mission_id)
    rapport = get_rapport_doc(mission_id)
    d = droits(employee, mission, rapport)
    if rapport.get("statut") == "emis":
        raise HTTPException(status_code=409, detail="Le rapport final est émis : il ne peut plus être régénéré.")
    if not d["generer"]:
        raise HTTPException(
            status_code=403,
            detail="La génération est réservée aux grades senior et au-dessus affectés à la mission.",
        )
    session = session_active(rapport)
    if session:
        noms = ", ".join(u.get("name", "") for u in session.get("utilisateurs") or []) or "un collaborateur"
        raise HTTPException(
            status_code=409,
            detail={
                "code": "edition_en_cours",
                "message": f"Le rapport est ouvert dans l'éditeur ({noms}). Fermez l'éditeur pour que les "
                "modifications soient enregistrées avant de régénérer.",
            },
        )
    if a_des_modifications_onlyoffice(rapport) and not force:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "modifications_onlyoffice",
                "message": "Des modifications ont été faites dans l'éditeur depuis la dernière génération. "
                "Régénérer crée une nouvelle version à partir des données d'EC Perform : ces modifications "
                "n'y figureront pas (elles restent consultables dans les versions précédentes).",
            },
        )

    contenu, resume = construire(mission_id, mission, rapport)
    base = (derniere_version(rapport) or {}).get("numero")
    version = ajouter_version(
        rapport["_id"], contenu, "generation", auteur(employee),
        {"brouillon": resume["brouillon"], "nbSlides": resume["nbSlides"], "force": bool(force)},
        statut="genere", base=base,
    )
    db.rapports.update_one(
        {"_id": rapport["_id"]},
        {"$set": {"session": None, "derniereGeneration": {"le": version["date"], "par": version["auteur"],
                                                           "avertissements": resume["avertissements"],
                                                           "nbSlides": resume["nbSlides"]}}},
    )
    rapport = db.rapports.find_one({"_id": rapport["_id"]})
    return {**serialize(rapport, mission, employee), "generation": resume}


def telecharger(mission_id, numero, employee):
    _, mission = get_mission_or_404(mission_id)
    rapport = get_rapport_doc(mission_id)
    version = version_numero(rapport, numero)
    return reponse_fichier(lire_fichier(version["fileId"]), nom_fichier(mission, numero))


# --- Émission ---------------------------------------------------------------------------------


def emettre(mission_id, employee, convertir_pdf=None):
    """Fige la dernière version : nouvelle version « emission » (même fichier), statut emis.
    `convertir_pdf(rapport, version) -> octets` : export PDF (ONLYOFFICE) ; un échec n'empêche pas
    l'émission, il est signalé et peut être relancé."""
    _, mission = get_mission_or_404(mission_id)
    rapport = get_rapport_doc(mission_id)
    if rapport.get("statut") == "emis":
        raise HTTPException(status_code=409, detail="Le rapport final est déjà émis.")
    if not peut_emettre_rapport(employee):
        raise HTTPException(status_code=403, detail="L'émission du rapport final est réservée à l'Associé.")
    derniere = derniere_version(rapport)
    if derniere is None:
        raise HTTPException(status_code=400, detail="Aucune version du rapport : générez-le avant de l'émettre.")
    non_clotures = _cycles_non_clotures(mission_id)
    if non_clotures:
        raise HTTPException(
            status_code=409,
            detail="L'émission exige que tous les cycles soient clôturés. Cycles non clôturés : "
            + ", ".join(f"{c['code']} ({c['libelle']})" for c in non_clotures) + ".",
        )
    if session_active(rapport):
        raise HTTPException(
            status_code=409,
            detail="Le rapport est ouvert dans l'éditeur : fermez-le pour enregistrer les dernières modifications avant l'émission.",
        )

    par, le = auteur(employee), now_iso()
    numero = db.rapports.find_one_and_update(
        {"_id": rapport["_id"], "statut": {"$ne": "emis"}},
        {"$inc": {"compteurVersion": 1}},
        return_document=ReturnDocument.AFTER,
    )
    if numero is None:
        raise HTTPException(status_code=409, detail="Le rapport final est déjà émis.")
    numero = numero["compteurVersion"]
    version = {
        "numero": numero, "date": le, "auteur": par, "origine": "emission", "fileId": derniere["fileId"],
        "taille": derniere.get("taille"), "baseeSur": derniere["numero"],
    }
    db.rapports.update_one(
        {"_id": rapport["_id"]},
        {
            "$push": {"versions": version},
            "$set": {"statut": "emis", "session": None, "emission": {"le": le, "par": par, "version": numero}},
        },
    )
    rapport = db.rapports.find_one({"_id": rapport["_id"]})
    if convertir_pdf:
        exporter_pdf(rapport, mission, convertir_pdf)
        rapport = db.rapports.find_one({"_id": rapport["_id"]})
    return serialize(rapport, mission, employee)


def exporter_pdf(rapport, mission, convertir_pdf):
    version = derniere_version(rapport)
    try:
        contenu = convertir_pdf(rapport, version)
        file_id = stocker_fichier(contenu, f"rapport_v{version['numero']}.pdf",
                                  {"rapportId": str(rapport["_id"]), "numero": version["numero"]}, "application/pdf")
        pdf = {"fileId": file_id, "version": version["numero"], "le": now_iso(), "erreur": None}
    except Exception as exc:  # conversion indisponible : l'émission reste valable
        logger.exception("Export PDF du rapport %s impossible", rapport["_id"])
        pdf = {"fileId": None, "version": version["numero"], "le": now_iso(),
               "erreur": f"Export PDF impossible : {exc}"}
    db.rapports.update_one({"_id": rapport["_id"]}, {"$set": {"pdf": pdf}})


def relancer_pdf(mission_id, employee, convertir_pdf):
    _, mission = get_mission_or_404(mission_id)
    rapport = get_rapport_doc(mission_id)
    if rapport.get("statut") != "emis":
        raise HTTPException(status_code=409, detail="Le PDF est produit à l'émission du rapport.")
    if not est_affecte(employee, mission) and not peut_emettre_rapport(employee):
        raise HTTPException(status_code=403, detail="Action réservée aux collaborateurs affectés à la mission.")
    exporter_pdf(rapport, mission, convertir_pdf)
    return serialize(db.rapports.find_one({"_id": rapport["_id"]}), mission, employee)


def telecharger_pdf(mission_id, employee):
    _, mission = get_mission_or_404(mission_id)
    rapport = get_rapport_doc(mission_id)
    pdf = rapport.get("pdf") or {}
    if not pdf.get("fileId"):
        raise HTTPException(status_code=404, detail="Aucun PDF disponible")
    return reponse_fichier(lire_fichier(pdf["fileId"]), nom_fichier(mission, pdf["version"], "pdf"), "application/pdf")


# --- Saisie complémentaire --------------------------------------------------------------------


def _verifier_saisie_modifiable(employee, mission, rapport):
    if rapport.get("statut") == "emis":
        raise HTTPException(status_code=409, detail="Le rapport final est émis : la saisie n'est plus modifiable.")
    if not est_affecte(employee, mission):
        raise HTTPException(status_code=403, detail="Réservé aux collaborateurs affectés à la mission.")


def _contexte_saisie(mission_id):
    """Référentiels proposés dans l'écran de saisie : constats, ajustements et feuilles de PT."""
    constats, ajustements = [], []
    for rev in db.cycle_revisions.find({"missionId": mission_id}):
        for c in rev.get("constats") or []:
            constats.append({k: c.get(k) for k in ("id", "famille", "constat", "severite", "recommandation")}
                            | {"cycleCode": rev["code"]})
        for a in (rev.get("conclusion") or {}).get("ajustements") or []:
            ajustements.append({k: a.get(k) for k in ("id", "compte", "libelle", "sens", "montant")}
                               | {"cycleCode": rev["code"]})
        risques = (rev.get("priseConnaissance") or {}).get("risques") or []
        for c in constats:
            if c["cycleCode"] == rev["code"]:
                c["risquesCycle"] = risques
    ordre = {c["code"]: i for i, c in enumerate(CYCLES)}
    constats.sort(key=lambda c: ordre.get(c["cycleCode"], 99))
    ajustements.sort(key=lambda a: ordre.get(a["cycleCode"], 99))
    papiers = []
    for p in db.working_papers.find({"missionId": mission_id}):
        feuilles = (p.get("lien") or {}).get("feuilles") if p.get("mode") == "lien" else p.get("feuilles")
        papiers.append({"id": str(p["_id"]), "cycleCode": p.get("cycleCode"), "etape": p.get("etape"),
                        "titre": p.get("titre"), "feuilles": [f["nom"] for f in feuilles or []]})
    return {
        "cycles": [{"code": c["code"], "libelle": c["libelle"]} for c in CYCLES],
        "constats": constats,
        "ajustements": ajustements,
        "papiers": papiers,
    }


def get_saisie(mission_id, employee):
    _, mission = get_mission_or_404(mission_id)
    rapport = get_rapport_doc(mission_id)
    return {
        "saisie": rapport.get("saisie") or SaisieRapport().model_dump(),
        "version": rapport.get("saisieVersion", 0),
        "modifiable": rapport.get("statut") != "emis" and est_affecte(employee, mission),
        "referentiels": _contexte_saisie(mission_id),
    }


def _avec_ids(items):
    return [{**i, "id": i.get("id") or uuid.uuid4().hex} for i in items]


def _normaliser(saisie: SaisieRapport, mission_id):
    """Ids manquants, cycles valides, écritures équilibrées et sans doublon."""
    data = saisie.model_dump()
    codes = {c["code"] for c in CYCLES}
    data["evenements"] = _avec_ids(data["evenements"])
    points = {}
    for code, liste in data["points"].items():
        if code not in codes:
            raise HTTPException(status_code=400, detail=f"Cycle inconnu : {code}")
        points[code] = [{**p, "blocs": _avec_ids(p["blocs"])} for p in _avec_ids(liste)]
    data["points"] = points

    ajustements = {}
    for rev in db.cycle_revisions.find({"missionId": mission_id}, {"code": 1, "conclusion.ajustements": 1}):
        for a in (rev.get("conclusion") or {}).get("ajustements") or []:
            ajustements[a.get("id")] = {**a, "cycleCode": rev["code"]}
    deja = set()
    for e in data["ecritures"]:
        if e["cycleCode"] not in codes:
            raise HTTPException(status_code=400, detail=f"Cycle inconnu : {e['cycleCode']}")
        if not e["ajustementIds"]:
            raise HTTPException(status_code=400, detail=f"L'écriture « {e['libelle']} » ne contient aucune ligne.")
        debit = credit = 0.0
        for aid in e["ajustementIds"]:
            a = ajustements.get(aid)
            if a is None or a["cycleCode"] != e["cycleCode"]:
                raise HTTPException(status_code=400, detail=f"Ajustement introuvable dans le cycle {e['cycleCode']}.")
            if aid in deja:
                raise HTTPException(status_code=400, detail="Un ajustement ne peut appartenir qu'à une seule écriture.")
            deja.add(aid)
            if a.get("sens") == "Débit":
                debit += float(a.get("montant") or 0)
            else:
                credit += float(a.get("montant") or 0)
        if abs(debit - credit) >= 0.5:
            raise HTTPException(
                status_code=400,
                detail=f"L'écriture « {e['libelle'] or 'sans libellé'} » n'est pas équilibrée "
                f"(débit {debit:,.0f}, crédit {credit:,.0f}).".replace(",", " "),
            )
    data["ecritures"] = _avec_ids(data["ecritures"])
    return data


def update_saisie(mission_id, saisie_brute, version, employee):
    _, mission = get_mission_or_404(mission_id)
    rapport = get_rapport_doc(mission_id)
    _verifier_saisie_modifiable(employee, mission, rapport)
    try:
        saisie = SaisieRapport.model_validate(saisie_brute)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=[{"loc": e["loc"], "msg": e["msg"]} for e in exc.errors()])
    data = _normaliser(saisie, mission_id)
    updated = db.rapports.find_one_and_update(
        {"_id": rapport["_id"], "saisieVersion": version, "statut": {"$ne": "emis"}},
        {"$set": {"saisie": data, "saisieMajLe": now_iso(), "saisieMajPar": auteur(employee)},
         "$inc": {"saisieVersion": 1}},
        return_document=ReturnDocument.AFTER,
    )
    if updated is None:
        raise HTTPException(
            status_code=409,
            detail="La saisie a été modifiée entre-temps par un autre utilisateur. Rechargez pour récupérer la dernière version.",
        )
    return get_saisie(mission_id, employee)


def deposer_media(mission_id, cle, fichier: UploadFile, employee):
    if cle not in MEDIAS:
        raise HTTPException(status_code=404, detail="Média inconnu")
    _, mission = get_mission_or_404(mission_id)
    rapport = get_rapport_doc(mission_id)
    _verifier_saisie_modifiable(employee, mission, rapport)
    if not fichier.filename or os.path.splitext(fichier.filename)[1].lower() not in EXTENSIONS_IMAGE:
        raise HTTPException(status_code=400, detail="Formats acceptés : PNG, JPG.")
    contenu = fichier.file.read()
    if len(contenu) > MAX_MEDIA:
        raise HTTPException(status_code=400, detail="Image trop volumineuse (5 Mo maximum).")
    try:
        with Image.open(io.BytesIO(contenu)) as im:
            im.verify()
    except Exception:
        raise HTTPException(status_code=400, detail="Image illisible.")
    ancien = (rapport.get("medias") or {}).get(cle)
    file_id = stocker_fichier(contenu, fichier.filename, {"rapportId": str(rapport["_id"]), "media": cle},
                              fichier.content_type or "image/png")
    db.rapports.update_one({"_id": rapport["_id"]},
                           {"$set": {f"medias.{cle}": {"fileId": file_id, "nom": fichier.filename, "le": now_iso()}}})
    if ancien:
        try:
            fs().delete(ancien["fileId"])
        except gridfs.errors.NoFile:
            pass
    return get_rapport(mission_id, employee)


def supprimer_media(mission_id, cle, employee):
    _, mission = get_mission_or_404(mission_id)
    rapport = get_rapport_doc(mission_id)
    _verifier_saisie_modifiable(employee, mission, rapport)
    ancien = (rapport.get("medias") or {}).get(cle)
    if ancien:
        db.rapports.update_one({"_id": rapport["_id"]}, {"$unset": {f"medias.{cle}": ""}})
        try:
            fs().delete(ancien["fileId"])
        except gridfs.errors.NoFile:
            pass
    return get_rapport(mission_id, employee)


def lire_media(mission_id, cle):
    rapport = get_rapport_doc(mission_id)
    media = (rapport.get("medias") or {}).get(cle)
    if not media:
        raise HTTPException(status_code=404, detail="Média introuvable")
    contenu = lire_fichier(media["fileId"])
    media_type = "image/png" if media["nom"].lower().endswith(".png") else "image/jpeg"
    return reponse_fichier(contenu, media["nom"], media_type, inline=True)
