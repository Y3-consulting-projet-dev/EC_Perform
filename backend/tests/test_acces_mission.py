from app.core.security import create_access_token
from app.db.session import db


def _headers_non_affecte():
    db.employees.insert_one({"nom": "X", "prenoms": "Y", "grade": "Manager", "email": "x@test.ci", "password_hash": "x"})
    return {"Authorization": f"Bearer {create_access_token('x@test.ci')}"}


def test_liste_indique_si_la_mission_peut_etre_ouverte(api, employees, mission):
    autre = _headers_non_affecte()
    assert [m["peutOuvrir"] for m in api.get("/missions", headers=autre).json()] == [False]
    # Affecté à un cycle, senior / manager désignés, Associé : accès.
    for key in ("assistant", "senior", "manager", "associe"):
        assert api.get("/missions", headers=employees[key]["headers"]).json()[0]["peutOuvrir"] is True
    clients = api.get("/clients", headers=autre).json()
    assert clients[0]["missions"][0]["peutOuvrir"] is False


def test_routes_de_la_mission_refusees_au_non_affecte(api, employees, mission):
    autre = _headers_non_affecte()
    for path in ("/documents", "/fiche-signaletique", "/balances", "/cycles", "/repartition", "/revisions", "/rapport"):
        assert api.get(f"/missions/{mission}{path}", headers=autre).status_code == 403, path
    assert api.patch(f"/missions/{mission}/cloturer", json={}, headers=autre).status_code == 403
    assert api.get(f"/missions/{mission}/documents", headers=employees["assistant"]["headers"]).status_code == 200


def test_plusieurs_managers_et_seniors(api, employees):
    db.employees.insert_one({"nom": "DEUX", "prenoms": "Manager", "grade": "Manager", "email": "m2@test.ci", "password_hash": "x"})
    m2 = {"Authorization": f"Bearer {create_access_token('m2@test.ci')}"}
    client_id = str(db.clients.insert_one({"raisonSociale": "ACME"}).inserted_id)
    payload = {
        "clientId": client_id, "exercice": "2026", "dateDebut": "2026-01-01", "echeance": "2026-03-31",
        "managers": ["Manager MANAGER", "Manager DEUX", "Manager DEUX"], "seniors": ["Senior SENIOR"],
    }
    created = api.post("/missions", json=payload, headers=employees["senior"]["headers"]).json()
    assert created["managers"] == ["Manager MANAGER", "Manager DEUX"] and created["seniors"] == ["Senior SENIOR"]
    mission = api.get("/missions", headers=m2).json()[0]
    assert mission["peutOuvrir"] is True
    assert [r["nom"] for r in mission["managers"]] == ["Manager MANAGER", "Manager DEUX"]
    assert api.get(f"/missions/{created['id']}/documents", headers=m2).status_code == 200


def test_le_createur_et_l_equipe_ont_acces(api, employees, mission):
    autre = _headers_non_affecte()
    employe = db.employees.find_one({"email": "x@test.ci"})
    db.missions.update_one({}, {"$set": {"createdBy": {"id": str(employe["_id"])}}})
    assert api.get(f"/missions/{mission}/documents", headers=autre).status_code == 200
    db.missions.update_one({}, {"$unset": {"createdBy": ""}, "$set": {"equipe": [str(employe["_id"])]}})
    assert api.get(f"/missions/{mission}/documents", headers=autre).status_code == 200
