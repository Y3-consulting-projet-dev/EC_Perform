import io
import zipfile

from app.db.session import db


def _url(mission, suffix=""):
    return f"/missions/{mission}/fiche-signaletique{suffix}"


def test_fiche_pre_remplie_depuis_le_client(api, employees, mission):
    response = api.get(_url(mission), headers=employees["assistant"]["headers"])
    assert response.status_code == 200, response.text
    fiche = response.json()
    assert fiche["renseignee"] is False
    assert fiche["fichier"] is None
    assert fiche["valeurs"]["denomination"] == "SAVEDO SA"
    assert [c["key"] for c in fiche["champs"]][:2] == ["denomination", "sigle"]


def test_saisie_puis_export_docx(api, employees, mission):
    headers = employees["assistant"]["headers"]
    assert api.put(_url(mission), headers=headers, json={"valeurs": {}}).status_code == 400

    response = api.put(
        _url(mission),
        headers=headers,
        json={"valeurs": {"denomination": " Compagnie & Fils ", "sigle": "CFP", "associes": "KONE\nSANZ", "inconnu": "x"}},
    )
    assert response.status_code == 200, response.text
    fiche = response.json()
    assert fiche["renseignee"] is True
    assert fiche["valeurs"]["denomination"] == "Compagnie & Fils"
    assert "inconnu" not in fiche["valeurs"]
    assert fiche["updatedBy"]["nom"] == "Assistant ASSISTANT"

    export = api.get(_url(mission, "/export"), headers=headers)
    assert export.status_code == 200
    assert "Fiche_signaletique_CFP.docx" in export.headers["content-disposition"]
    with zipfile.ZipFile(io.BytesIO(export.content)) as archive:
        document = archive.read("word/document.xml").decode()
    assert "INFORMATIONS GENERALES CFP" in document
    assert "Compagnie &amp; Fils" in document
    assert "- KONE" in document and "- SANZ" in document


def test_import_fichier_et_mission_cloturee(api, employees, mission):
    headers = employees["assistant"]["headers"]
    refus = api.post(_url(mission, "/fichier"), headers=headers, files={"fichier": ("fiche.exe", b"x")})
    assert refus.status_code == 400

    response = api.post(_url(mission, "/fichier"), headers=headers, files={"fichier": ("fiche.pdf", b"%PDF")})
    assert response.status_code == 200, response.text
    assert response.json()["fichier"]["fileName"] == "fiche.pdf"

    db.missions.update_one({}, {"$set": {"statut": "Terminée"}})
    assert api.get(_url(mission), headers=headers).json()["modifiable"] is False
    assert api.put(_url(mission), headers=headers, json={"valeurs": {"sigle": "X"}}).status_code == 409
