"""Phase 6 – rapport final : génération (mission de démonstration SAVEDO SA, données fictives),
versions, ONLYOFFICE (config, callback, co-édition), régénération, émission, saisie, restitution."""

import io

import jwt
import pytest
from pptx import Presentation
from pptx.oxml.ns import qn

from app.db.session import db
from app.services import balance_service, onlyoffice_service
from app.services.balance_engine import format_montant
from app.services.rapport import builders, formules
from app.services.rapport.assembleur import MODELE
from scripts.demo_savedo import creer_mission_demo, solde_cloture_2025

OO_SECRET = "secret-onlyoffice-test"

# Décomposition du nombre de slides attendu pour la mission de démonstration :
#   couverture                                                     1
#   1. Contexte : sommaire, séparateur, contexte, présentation,
#      évènements significatifs, réunion de restitution           6
#   2. Contrôle interne : sommaire, séparateur, introduction,
#      fiches A et E (Gouvernance ; K exclu explicitement)          5
#   3. Cycles : sommaire, séparateur, intangibilité                 3
#      A synthèse + constats                                        2
#      B synthèse, point « Créances douteuses », constats           3
#      C synthèse, constats, écritures proposées                    3
#      D extrait de balance                                         1
#      E synthèse, constats, écritures non regroupées               3
#      F synthèse, point « Cadrage », écritures non regroupées      3
#      G, I, L extrait de balance                                   3
#      H extrait + point « Variation »                              2
#      J extrait + point « Compte d'attente » (grand livre)         2
#      K extrait + constats                                         2
#      M (aucune donnée) : omis                                     0
#   4. Régularisation : sommaire, séparateur, récapitulatif         3
#   fin                                                             1
NB_SLIDES_DEMO = 43


@pytest.fixture
def oo_env(monkeypatch):
    monkeypatch.setenv("ONLYOFFICE_JWT_SECRET", OO_SECRET)
    monkeypatch.setenv("ONLYOFFICE_PUBLIC_URL", "http://localhost:8080")
    monkeypatch.setenv("ONLYOFFICE_INTERNAL_URL", "http://onlyoffice")
    monkeypatch.setenv("BACKEND_URL_FOR_ONLYOFFICE", "http://host.docker.internal:8000")


@pytest.fixture
def demo(api, employees, tmp_path, monkeypatch, oo_env):
    monkeypatch.setattr(balance_service, "UPLOADS_DIR", str(tmp_path))
    ids = creer_mission_demo(db, str(tmp_path), [employees["assistant"]["id"], employees["manager"]["id"]])
    return ids


def _demo_non_cloturee(employees, tmp_path, monkeypatch):
    monkeypatch.setattr(balance_service, "UPLOADS_DIR", str(tmp_path))
    return creer_mission_demo(db, str(tmp_path), [employees["manager"]["id"]], non_clotures=("B", "C"))


def _generer(api, employees, mission_id, qui="manager", force=False):
    return api.post(f"/missions/{mission_id}/rapport/generer", params={"force": force} if force else None,
                    headers=employees[qui]["headers"])


def _pptx(api, employees, mission_id, numero):
    r = api.get(f"/missions/{mission_id}/rapport/versions/{numero}/fichier", headers=employees["manager"]["headers"])
    assert r.status_code == 200
    return Presentation(io.BytesIO(r.content))


def _textes(prs):
    out = []
    for slide in prs.slides:
        for shape in slide.shapes:
            if shape.has_text_frame:
                out.append(shape.text_frame.text)
            if getattr(shape, "has_table", False) and shape.has_table:
                out.extend(c.text for row in shape.table.rows for c in row.cells)
    return "\n".join(out)


def _rapport_id(mission_id):
    return str(db.rapports.find_one({"missionId": mission_id})["_id"])


def _callback(api, mission_id, corps, secret=OO_SECRET, jeton_api=None):
    rid = _rapport_id(mission_id)
    jeton_api = jeton_api or onlyoffice_service.url_callback(rid).split("jeton=")[1]
    return api.post(f"/onlyoffice/callback/{rid}", params={"jeton": jeton_api},
                    json={**corps, "token": jwt.encode(corps, secret, algorithm="HS256")})


# --- Génération -------------------------------------------------------------------------------


def test_generation_rapport_complet(api, employees, demo):
    r = _generer(api, employees, demo["missionId"])
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["statut"] == "genere"
    assert data["generation"]["avertissements"] == []
    assert data["generation"]["brouillon"] is False
    assert data["versions"][0]["origine"] == "generation" and data["versions"][0]["numero"] == 1

    prs = _pptx(api, employees, demo["missionId"], 1)
    assert len(prs.slides) == NB_SLIDES_DEMO == data["generation"]["nbSlides"]

    # Aucun espace réservé vide, aucune invite « Cliquez pour… », dispositions du modèle uniquement.
    for numero, slide in enumerate(prs.slides, start=1):
        assert slide.slide_layout.name.startswith("EC "), numero
        for ph in slide.placeholders:
            if ph.element.tag == qn("p:sp"):
                assert ph.has_text_frame and ph.text_frame.text.strip(), f"slide {numero} : espace réservé vide {ph.name}"
    texte = _textes(prs)
    assert "Cliquez" not in texte and "Click to" not in texte
    assert "#FORMULE" not in texte

    # Montants attendus (FCFA, format « 1 234 567 »).
    attendus = [
        "4 900 000",  # écriture de dépréciation (cycle B)
        "10 240 000",  # total du récapitulatif des écritures proposées
        "1 250 000",  # écart d'intangibilité du compte clients
        "250 000",  # écart de mars, calculé par la formule du papier de travail
        "52 750 000",  # total du livre de paie (=SUM(B1:B3))
        "2 520 000",  # total de l'extrait du grand livre saisi
        "FCFA 50 000 000",  # capital (fiche signalétique)
    ]
    attendus.append(format_montant(solde_cloture_2025("521100")))  # solde 2025 de la banque SGCI (cycle A)
    for montant in attendus:
        assert montant in texte, montant
    assert "SAVEDO SA" in texte and "Exercice 2025" in texte and "Avril 2026" in texte
    # Commentaires de la restitution repris dans la fiche de contrôle interne.
    assert "Un inventaire mensuel sera mis en place" in texte
    assert "PROJET" not in texte


def test_brouillon_si_cycles_non_clotures(api, employees, tmp_path, monkeypatch, oo_env):
    ids = _demo_non_cloturee(employees, tmp_path, monkeypatch)
    r = _generer(api, employees, ids["missionId"])
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["generation"]["brouillon"] is True
    assert [c["code"] for c in data["cyclesNonClotures"]] == ["B", "C"]
    assert "B, C" in data["generation"]["avertissements"][0]
    assert "PROJET – document provisoire" in _textes(_pptx(api, employees, ids["missionId"], 1))

    r = api.post(f"/missions/{ids['missionId']}/rapport/emettre", headers=employees["associe"]["headers"])
    assert r.status_code == 409
    assert "B (Ventes et clients)" in r.json()["detail"]


def test_generation_reservee_encadrement_affecte(api, employees, demo):
    assert _generer(api, employees, demo["missionId"], "assistant").status_code == 403  # grade
    assert _generer(api, employees, demo["missionId"], "senior").status_code == 403  # non affecté


def test_tableau_long_pagine(api):
    prs = Presentation(MODELE)
    tableau = {
        "colonnes": [{"titre": "Compte", "poids": 1}, {"titre": "Libellé", "poids": 3},
                     {"titre": "Solde", "poids": 1, "align": "r"}],
        "lignes": [{"cellules": [f"4011{i:03d}", f"Fournisseur {i}", "1 000"]} for i in range(120)],
        "pied": [{"cellules": ["Total", "", "120 000"], "style": "total"}],
    }
    slides = builders.tableau_seul(prs, "C – Achats et fournisseurs", "Balance auxiliaire", tableau)
    assert len(slides) > 1
    lignes_vues = 0
    for i, slide in enumerate(slides, start=1):
        table = next(s for s in slide.shapes if getattr(s, "has_table", False) and s.has_table).table
        assert table.cell(0, 0).text == "Compte"  # en-tête répété
        corps = [r.cells[0].text for r in list(table.rows)[1:]]
        assert ("Total" in corps) == (i == len(slides))  # total uniquement en dernière page
        lignes_vues += len([c for c in corps if c != "Total"])
        assert f"({i}/{len(slides)})" in slide.placeholders[13].text_frame.text
    assert lignes_vues == 120


def test_formules_papier_de_travail():
    data = [[10, 20, "=A1+B1"], ["=SUM(A1:B1)", "=IF(C1>25,\"haut\",\"bas\")", "=ROUND(C1/3,1)"], ["=FOO(1)", "", ""]]
    valeurs, erreurs = formules.valeurs_feuille(data)
    assert valeurs[0][2] == 30
    assert valeurs[1][0] == 30 and valeurs[1][1] == "haut" and valeurs[1][2] == 10.0
    assert valeurs[2][0] == "#FORMULE" and erreurs == 1


# --- ONLYOFFICE -------------------------------------------------------------------------------


def test_config_editeur_mode_et_jwt(api, employees, demo):
    mid = demo["missionId"]
    assert api.get(f"/missions/{mid}/rapport/editeur", headers=employees["assistant"]["headers"]).status_code == 400
    _generer(api, employees, mid)
    rid = _rapport_id(mid)

    r = api.get(f"/missions/{mid}/rapport/editeur", headers=employees["assistant"]["headers"])
    assert r.status_code == 200
    data = r.json()
    config = data["config"]
    assert data["mode"] == "edit" and config["editorConfig"]["mode"] == "edit"
    assert config["document"]["key"] == f"{rid}-v1"
    assert config["editorConfig"]["user"]["id"] == employees["assistant"]["id"]
    assert config["editorConfig"]["callbackUrl"].startswith(f"http://host.docker.internal:8000/onlyoffice/callback/{rid}")
    signe = jwt.decode(config["token"], OO_SECRET, algorithms=["HS256"])
    assert signe["document"]["key"] == config["document"]["key"]

    # Non affecté à la mission : la mission ne s'ouvre pas.
    r = api.get(f"/missions/{mid}/rapport/editeur", headers=employees["senior"]["headers"])
    assert r.status_code == 403

    # Le Document Server télécharge le fichier avec le jeton de l'URL.
    url = config["document"]["url"].replace("http://host.docker.internal:8000", "")
    assert api.get(url).status_code == 200
    assert api.get(url.replace("jeton=", "jeton=x")).status_code == 403


def test_callback_jwt_invalide_refuse(api, employees, demo):
    mid = demo["missionId"]
    _generer(api, employees, mid)
    corps = {"key": f"{_rapport_id(mid)}-v1", "status": 2, "url": "http://localhost:8080/cache/f.pptx", "users": []}
    assert _callback(api, mid, corps, secret="mauvais-secret").status_code == 403
    assert _callback(api, mid, corps, jeton_api="faux").status_code == 403
    rid = _rapport_id(mid)
    jeton = onlyoffice_service.url_callback(rid).split("jeton=")[1]
    assert api.post(f"/onlyoffice/callback/{rid}", params={"jeton": jeton}, json=corps).status_code == 403  # sans JWT
    assert len(db.rapports.find_one({"missionId": mid})["versions"]) == 1


def test_cycle_edition_regeneration_emission(api, employees, demo, monkeypatch):
    mid = demo["missionId"]
    _generer(api, employees, mid)
    rid = _rapport_id(mid)

    # Deux éditeurs reçoivent la même clé (co-édition).
    k1 = api.get(f"/missions/{mid}/rapport/editeur", headers=employees["assistant"]["headers"]).json()["config"]["document"]["key"]
    k2 = api.get(f"/missions/{mid}/rapport/editeur", headers=employees["manager"]["headers"]).json()["config"]["document"]["key"]
    assert k1 == k2 == f"{rid}-v1"

    # Le Document Server confirme la session : la régénération est bloquée pendant l'édition.
    assert _callback(api, mid, {"key": k1, "status": 1, "users": [employees["assistant"]["id"]]}).json() == {"error": 0}
    r = _generer(api, employees, mid, force=True)
    assert r.status_code == 409 and r.json()["detail"]["code"] == "edition_en_cours"

    # Enregistrement forcé (statut 6), puis fermeture avec modifications (statut 2).
    modifie = Presentation(io.BytesIO(api.get(f"/missions/{mid}/rapport/versions/1/fichier",
                                              headers=employees["manager"]["headers"]).content))
    modifie.slides[0].shapes.title.text_frame.text = "Révision des comptes — version annotée"
    buffer = io.BytesIO()
    modifie.save(buffer)
    telecharges = []

    def faux_telechargement(url):
        telecharges.append(onlyoffice_service._url_autorisee(url))
        return buffer.getvalue()

    monkeypatch.setattr(onlyoffice_service, "telecharger_depuis_document_server", faux_telechargement)
    u = [employees["assistant"]["id"]]
    assert _callback(api, mid, {"key": k1, "status": 6, "url": "http://localhost:8080/cache/a.pptx", "users": u}).json() == {"error": 0}
    assert _callback(api, mid, {"key": k1, "status": 6, "url": "http://localhost:8080/cache/a.pptx", "users": u}).json() == {"error": 0}
    assert _callback(api, mid, {"key": k1, "status": 2, "url": "http://localhost:8080/cache/b.pptx", "users": u}).json() == {"error": 0}
    assert telecharges[0] == "http://onlyoffice/cache/a.pptx"  # origine publique réécrite vers l'interne
    # URL hors Document Server : refusée.
    assert _callback(api, mid, {"key": k1, "status": 2, "url": "http://evil.example/x.pptx", "users": u}).json() == {"error": 1}

    rapport = api.get(f"/missions/{mid}/rapport", headers=employees["manager"]["headers"]).json()
    assert rapport["statut"] == "en_finition" and rapport["modificationsOnlyoffice"] is True
    assert [v["origine"] for v in rapport["versions"]] == ["edition_onlyoffice", "edition_onlyoffice", "generation"]
    assert rapport["versions"][0]["auteur"]["id"] == employees["assistant"]["id"]
    assert rapport["sessionEdition"] is None
    assert "version annotée" in _textes(_pptx(api, employees, mid, 3))

    # Nouvelle session : clé de la dernière version (jamais celle d'un contenu déjà modifié).
    k3 = api.get(f"/missions/{mid}/rapport/editeur", headers=employees["assistant"]["headers"]).json()["config"]["document"]["key"]
    assert k3 == f"{rid}-v3"
    assert _callback(api, mid, {"key": k3, "status": 4, "users": []}).json() == {"error": 0}

    # Régénération : bloquée sans confirmation, autorisée avec force.
    r = _generer(api, employees, mid)
    assert r.status_code == 409 and r.json()["detail"]["code"] == "modifications_onlyoffice"
    r = _generer(api, employees, mid, force=True)
    assert r.status_code == 200 and r.json()["versions"][0]["numero"] == 4 and r.json()["statut"] == "genere"

    # Émission : réservée à l'Associé ; export PDF via le Document Server (simulé).
    assert api.post(f"/missions/{mid}/rapport/emettre", headers=employees["manager"]["headers"]).status_code == 403
    monkeypatch.setattr(onlyoffice_service, "convertir_pdf", lambda rapport, version: b"%PDF-1.7 rapport")
    r = api.post(f"/missions/{mid}/rapport/emettre", headers=employees["associe"]["headers"])
    assert r.status_code == 200, r.text
    emis = r.json()
    assert emis["statut"] == "emis" and emis["pdf"] is True
    assert emis["versions"][0]["origine"] == "emission" and emis["versions"][0]["baseeSur"] == 4
    assert emis["emission"]["version"] == 5
    assert api.get(f"/missions/{mid}/rapport/pdf", headers=employees["assistant"]["headers"]).content.startswith(b"%PDF")

    # Après émission : lecture seule pour tous, plus de régénération, ni de saisie, ni de callback.
    cfg = api.get(f"/missions/{mid}/rapport/editeur", headers=employees["assistant"]["headers"]).json()
    assert cfg["mode"] == "view" and cfg["version"] == 5
    assert _generer(api, employees, mid, force=True).status_code == 409
    assert api.post(f"/missions/{mid}/rapport/emettre", headers=employees["associe"]["headers"]).status_code == 409
    saisie = api.get(f"/missions/{mid}/rapport/saisie", headers=employees["manager"]["headers"]).json()
    assert saisie["modifiable"] is False
    assert api.put(f"/missions/{mid}/rapport/saisie", json={"saisie": saisie["saisie"], "version": saisie["version"]},
                   headers=employees["manager"]["headers"]).status_code == 409
    _callback(api, mid, {"key": cfg["config"]["document"]["key"], "status": 2, "url": "http://localhost:8080/cache/c.pptx", "users": []})
    assert len(db.rapports.find_one({"missionId": mid})["versions"]) == 5


def test_emission_pdf_en_echec_ne_bloque_pas(api, employees, demo, monkeypatch):
    mid = demo["missionId"]
    _generer(api, employees, mid)

    def echec(rapport, version):
        raise RuntimeError("Document Server injoignable")

    monkeypatch.setattr(onlyoffice_service, "convertir_pdf", echec)
    r = api.post(f"/missions/{mid}/rapport/emettre", headers=employees["associe"]["headers"])
    assert r.status_code == 200 and r.json()["statut"] == "emis"
    assert r.json()["pdf"] is False and "injoignable" in r.json()["pdfErreur"]
    monkeypatch.setattr(onlyoffice_service, "convertir_pdf", lambda rapport, version: b"%PDF-1.7")
    r = api.post(f"/missions/{mid}/rapport/pdf", headers=employees["manager"]["headers"])
    assert r.json()["pdf"] is True and r.json()["pdfErreur"] is None


# --- Saisie & restitution ---------------------------------------------------------------------


def test_saisie_ecritures_et_verrou(api, employees, demo):
    mid = demo["missionId"]
    h = employees["assistant"]["headers"]
    s = api.get(f"/missions/{mid}/rapport/saisie", headers=h).json()
    assert s["modifiable"] is True
    assert {c["cycleCode"] for c in s["referentiels"]["constats"]} == {"A", "B", "C", "E", "K"}

    saisie = s["saisie"]
    aj_e = demo["ajustements"]["E"]
    saisie["ecritures"].append({"cycleCode": "E", "libelle": "Moitié d'écriture", "ajustementIds": aj_e[:1]})
    r = api.put(f"/missions/{mid}/rapport/saisie", json={"saisie": saisie, "version": s["version"]}, headers=h)
    assert r.status_code == 400 and "pas équilibrée" in r.json()["detail"]

    saisie["ecritures"][-1]["ajustementIds"] = aj_e
    saisie["points"]["E"] = [{"titre": "Dotations", "texte": "Recalcul des dotations.", "blocs": [{"type": "balance", "prefixes": ["28"]}]}]
    r = api.put(f"/missions/{mid}/rapport/saisie", json={"saisie": saisie, "version": s["version"]}, headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["saisie"]["points"]["E"][0]["id"]
    # Version périmée : conflit.
    assert api.put(f"/missions/{mid}/rapport/saisie", json={"saisie": saisie, "version": s["version"]}, headers=h).status_code == 409
    # Non affecté : refusé.
    assert api.put(f"/missions/{mid}/rapport/saisie", json={"saisie": saisie, "version": s["version"] + 1},
                   headers=employees["senior"]["headers"]).status_code == 403


def test_restitution_client(api, employees, demo):
    mid = demo["missionId"]
    h = employees["assistant"]["headers"]
    r = api.get(f"/missions/{mid}/restitution", headers=h).json()
    assert r["modifiable"] is True and len(r["constats"]) == 5
    constat_k = demo["constats"]["K"][0]
    payload = {
        "reunion": {"date": "2026-04-12", "lieu": "Visioconférence", "participantsCabinet": [employees["manager"]["id"]],
                    "participantsClient": [{"nom": "Marie YAO", "fonction": "DAF"}, {"nom": "", "fonction": ""}]},
        "commentaires": {constat_k: {"commentaireClient": "Accord.", "reponseManagement": "Piste d'audit activée en mai."}},
        "version": r["version"],
    }
    r = api.put(f"/missions/{mid}/restitution", json=payload, headers=h)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["reunion"]["participantsCabinet"] == [{"id": employees["manager"]["id"], "nom": "Manager MANAGER"}]
    assert data["reunion"]["participantsClient"] == [{"nom": "Marie YAO", "fonction": "DAF"}]
    assert list(data["commentaires"]) == [constat_k]
    assert api.put(f"/missions/{mid}/restitution", json=payload, headers=h).status_code == 409  # version périmée
    payload["version"] = data["version"]
    assert api.put(f"/missions/{mid}/restitution", json=payload, headers=employees["senior"]["headers"]).status_code == 403

    _generer(api, employees, mid)
    texte = _textes(_pptx(api, employees, mid, 1))
    assert "Réunion de restitution du 12/04/2026 — Visioconférence" in texte
    assert "Piste d'audit activée en mai." in texte and "Manager MANAGER" in texte
