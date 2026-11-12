"""Intégration ONLYOFFICE Docs (Document Server auto-hébergé) pour le rapport final.

Flux :
- le navigateur demande la config de l'éditeur (signée en JWT avec ONLYOFFICE_JWT_SECRET) ;
- le Document Server télécharge le fichier via /onlyoffice/fichier/... (jeton court signé par
  l'API, propre à une version) ;
- pendant et après l'édition, le Document Server appelle /onlyoffice/callback/... : le JWT du
  Document Server est vérifié ; statuts 2 (document fermé, modifié) et 6 (enregistrement forcé) :
  le fichier modifié est téléchargé et enregistré comme nouvelle version.

Clé de document : unique par version (`{rapportId}-v{n}`). Tant qu'une session d'édition est
ouverte, tous les éditeurs reçoivent la même clé (co-édition) ; une fois la session fermée, la clé
suivante porte sur la dernière version, jamais sur un contenu déjà modifié.

Variables d'environnement (voir backend/.env.example) : ONLYOFFICE_JWT_SECRET,
ONLYOFFICE_PUBLIC_URL, ONLYOFFICE_INTERNAL_URL, BACKEND_URL_FOR_ONLYOFFICE, ONLYOFFICE_JWT_HEADER.
"""

import logging
import os
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit, urlunsplit

import httpx
import jwt
from bson import ObjectId
from fastapi import HTTPException

from app.core.security import JWT_SECRET_KEY
from app.db.session import db
from app.services import rapport_service as rs
from app.services.mission_service import get_mission_or_404
from app.services.revision_service import auteur, now_iso

logger = logging.getLogger(__name__)

JETON_FICHIER_DUREE = timedelta(hours=24)
JETON_CALLBACK_DUREE = timedelta(days=7)
TIMEOUT = httpx.Timeout(60.0, connect=10.0)


def config_env():
    publique = os.getenv("ONLYOFFICE_PUBLIC_URL", "http://localhost:8080").rstrip("/")
    return {
        "secret": os.getenv("ONLYOFFICE_JWT_SECRET", ""),
        "public": publique,
        "interne": (os.getenv("ONLYOFFICE_INTERNAL_URL") or publique).rstrip("/"),
        "backend": os.getenv("BACKEND_URL_FOR_ONLYOFFICE", "http://host.docker.internal:8000").rstrip("/"),
        "entete": os.getenv("ONLYOFFICE_JWT_HEADER", "Authorization"),
    }


def _secret():
    secret = config_env()["secret"]
    if not secret:
        raise HTTPException(status_code=503, detail="ONLYOFFICE n'est pas configuré (ONLYOFFICE_JWT_SECRET manquant).")
    return secret


# --- Jetons de l'API (fichier, callback) ------------------------------------------------------


def _jeton(usage, rapport_id, duree, **extra):
    payload = {"usage": usage, "rapport": str(rapport_id), "exp": datetime.now(timezone.utc) + duree, **extra}
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm="HS256")


def verifier_jeton(jeton, usage, rapport_id):
    try:
        payload = jwt.decode(jeton, JWT_SECRET_KEY, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(status_code=403, detail="Jeton invalide ou expiré")
    if payload.get("usage") != usage or payload.get("rapport") != str(rapport_id):
        raise HTTPException(status_code=403, detail="Jeton invalide")
    return payload


def url_fichier(rapport_id, numero):
    jeton = _jeton("oo-fichier", rapport_id, JETON_FICHIER_DUREE, numero=numero)
    return f"{config_env()['backend']}/onlyoffice/fichier/{rapport_id}/{numero}?jeton={jeton}"


def url_callback(rapport_id):
    jeton = _jeton("oo-callback", rapport_id, JETON_CALLBACK_DUREE)
    return f"{config_env()['backend']}/onlyoffice/callback/{rapport_id}?jeton={jeton}"


# --- Config de l'éditeur ----------------------------------------------------------------------


def _cle(rapport_id, numero):
    return f"{rapport_id}-v{numero}"


def config_editeur(mission_id, employee):
    _, mission = get_mission_or_404(mission_id)
    rapport = rs.get_rapport_doc(mission_id)
    derniere = rs.derniere_version(rapport)
    if derniere is None:
        raise HTTPException(status_code=400, detail="Générez le rapport avant de l'ouvrir dans l'éditeur.")
    secret = _secret()
    edition = rs.droits(employee, mission, rapport)["editer"]
    rid = str(rapport["_id"])

    if edition:
        session = rs.session_reutilisable(rapport)
        if session is None:
            session = {"cle": _cle(rid, derniere["numero"]), "version": derniere["numero"], "ouverteLe": now_iso(),
                       "majLe": now_iso(), "confirmee": False, "utilisateurs": []}
            db.rapports.update_one({"_id": rapport["_id"]}, {"$set": {"session": session}})
        cle, numero = session["cle"], session["version"]
    else:
        cle, numero = _cle(rid, derniere["numero"]), derniere["numero"]

    nom = f"{employee.get('prenoms', '')} {employee.get('nom', '')}".strip()
    config = {
        "documentType": "slide",
        "document": {
            "fileType": "pptx",
            "key": cle,
            "title": rs.nom_fichier(mission, numero),
            "url": url_fichier(rid, numero),
            "permissions": {"edit": edition, "download": True, "print": True, "comment": edition, "review": False},
        },
        "editorConfig": {
            "mode": "edit" if edition else "view",
            "lang": "fr",
            "region": "fr-FR",
            "callbackUrl": url_callback(rid),
            "user": {"id": str(employee["_id"]), "name": nom or employee.get("email", ""),
                     "group": employee.get("grade", "")},
            "customization": {"forcesave": True, "autosave": True, "compactHeader": False, "uiTheme": "theme-light"},
            "coEditing": {"mode": "fast", "change": False},
        },
    }
    config["token"] = jwt.encode(config, secret, algorithm="HS256")
    return {
        "config": config,
        "documentServerUrl": config_env()["public"],
        "mode": config["editorConfig"]["mode"],
        "version": numero,
    }


def fichier(rapport_id, numero, jeton):
    verifier_jeton(jeton, "oo-fichier", rapport_id)
    payload = jwt.decode(jeton, JWT_SECRET_KEY, algorithms=["HS256"])
    if payload.get("numero") != numero:
        raise HTTPException(status_code=403, detail="Jeton invalide")
    rapport = rs.get_rapport_by_id(rapport_id)
    version = rs.version_numero(rapport, numero)
    return rs.reponse_fichier(rs.lire_fichier(version["fileId"]), f"rapport_v{numero}.pptx")


# --- Callback ---------------------------------------------------------------------------------


def _payload_document_server(corps, entetes):
    """Vérifie le JWT du Document Server (dans le corps, ou dans l'en-tête configuré) et renvoie le
    contenu signé, seul digne de confiance."""
    secret = _secret()
    jeton = corps.get("token")
    dans_entete = False
    if not jeton:
        valeur = entetes.get(config_env()["entete"].lower()) or ""
        jeton = valeur[7:] if valeur.lower().startswith("bearer ") else ""
        dans_entete = True
    if not jeton:
        raise HTTPException(status_code=403, detail="JWT ONLYOFFICE manquant")
    try:
        payload = jwt.decode(jeton, secret, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(status_code=403, detail="JWT ONLYOFFICE invalide")
    return payload.get("payload", payload) if dans_entete else payload


def _url_autorisee(url):
    """N'accepte que les URL du Document Server ; réécrit l'origine publique vers l'origine
    interne (le backend joint le Document Server par son adresse interne). Évite que le callback
    fasse télécharger au backend une URL arbitraire."""
    env = config_env()
    cible = urlsplit(url)
    for origine in (env["interne"], env["public"]):
        o = urlsplit(origine)
        if (cible.scheme, cible.netloc) == (o.scheme, o.netloc):
            i = urlsplit(env["interne"])
            return urlunsplit((i.scheme, i.netloc, cible.path, cible.query, ""))
    raise HTTPException(status_code=400, detail="URL de fichier non autorisée")


def telecharger_depuis_document_server(url):
    reponse = httpx.get(_url_autorisee(url), timeout=TIMEOUT)
    reponse.raise_for_status()
    return reponse.content


def _auteur_callback(utilisateurs):
    for uid in utilisateurs or []:
        if ObjectId.is_valid(uid):
            employee = db.employees.find_one({"_id": ObjectId(uid)})
            if employee:
                return auteur(employee)
    return {"id": None, "nom": "Éditeur ONLYOFFICE", "grade": ""}


def callback(rapport_id, jeton, corps, entetes):
    verifier_jeton(jeton, "oo-callback", rapport_id)
    payload = _payload_document_server(corps, entetes)
    rapport = rs.get_rapport_by_id(rapport_id)
    statut = payload.get("status")
    session = rapport.get("session") or {}
    cle = payload.get("key")
    meme_session = bool(session) and session.get("cle") == cle

    if statut == 1:  # document en cours d'édition (connexion / déconnexion d'un utilisateur)
        if meme_session:
            noms = []
            for uid in payload.get("users") or []:
                a = _auteur_callback([uid])
                noms.append({"id": a["id"], "name": a["nom"]})
            db.rapports.update_one(
                {"_id": rapport["_id"]},
                {"$set": {"session.confirmee": True, "session.majLe": now_iso(), "session.utilisateurs": noms}},
            )
        return {"error": 0}

    if statut in (2, 6):
        url = payload.get("url")
        if not url:
            return {"error": 1}
        if rapport.get("statut") == "emis":
            logger.warning("Callback ONLYOFFICE ignoré : rapport %s émis", rapport_id)
            return {"error": 0}
        if any(v.get("sourceUrl") == url for v in rapport.get("versions") or []):
            return {"error": 0}  # callback rejoué par le Document Server
        try:
            contenu = telecharger_depuis_document_server(url)
        except (httpx.HTTPError, HTTPException):
            logger.exception("Téléchargement du fichier ONLYOFFICE impossible (%s)", rapport_id)
            return {"error": 1}
        auteur_v = _auteur_callback(payload.get("users") or [a.get("userid") for a in payload.get("actions") or []])
        rs.ajouter_version(
            rapport["_id"], contenu, "edition_onlyoffice", auteur_v,
            {"sourceUrl": url, "cleSession": cle, "enregistrementForce": statut == 6},
            statut="en_finition", base=session.get("version"),
        )
        if statut == 2 and meme_session:
            db.rapports.update_one({"_id": rapport["_id"]}, {"$set": {"session": None}})
        elif meme_session:
            db.rapports.update_one({"_id": rapport["_id"]}, {"$set": {"session.majLe": now_iso()}})
        return {"error": 0}

    if statut == 4:  # fermé sans modification
        if meme_session:
            db.rapports.update_one({"_id": rapport["_id"]}, {"$set": {"session": None}})
        return {"error": 0}

    if statut in (3, 7):
        logger.error("ONLYOFFICE signale une erreur d'enregistrement (statut %s, rapport %s)", statut, rapport_id)
    return {"error": 0}


# --- Conversion PDF ---------------------------------------------------------------------------


def convertir_pdf(rapport, version):
    """Conversion PPTX -> PDF par l'API de conversion du Document Server (synchrone)."""
    env = config_env()
    secret = _secret()
    rid = str(rapport["_id"])
    demande = {
        "async": False,
        "filetype": "pptx",
        "outputtype": "pdf",
        "key": f"{_cle(rid, version['numero'])}-pdf",
        "title": f"rapport_v{version['numero']}.pptx",
        "url": url_fichier(rid, version["numero"]),
    }
    jeton = jwt.encode(demande, secret, algorithm="HS256")
    reponse = httpx.post(
        f"{env['interne']}/ConvertService.ashx",
        json={**demande, "token": jeton},
        headers={"Accept": "application/json", env["entete"]: f"Bearer {jeton}"},
        timeout=httpx.Timeout(180.0, connect=10.0),
    )
    reponse.raise_for_status()
    resultat = reponse.json()
    if resultat.get("error"):
        raise RuntimeError(f"code d'erreur ONLYOFFICE {resultat['error']}")
    if not resultat.get("endConvert") or not resultat.get("fileUrl"):
        raise RuntimeError("conversion inachevée")
    return telecharger_depuis_document_server(resultat["fileUrl"])
