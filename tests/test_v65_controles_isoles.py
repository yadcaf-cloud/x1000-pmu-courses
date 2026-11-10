"""Tests V65 sans collecte ni ecriture."""
from fastapi.testclient import TestClient

from api import app
from moteurs import MOTEURS
from coordination_x1000 import coordonner
from collecte_pmu import collecter

client = TestClient(app)

def test_cinq_moteurs():
    assert len(MOTEURS) == 5
    assert len({m.nom for m in MOTEURS}) == 5

def test_pas_de_pronostic_invente():
    course = {
        "id": "TEST-ISOLE",
        "hippodrome": "TEST",
        "partants": [{"numero": 1}]
    }
    resultat = coordonner(course)
    assert resultat["classement"] == []
    assert resultat["pari"] is None
    assert resultat["fige"] is False

def test_routes():
    for route in (
        "/api/status",
        "/api/courses",
        "/api/selections",
        "/api/figes",
        "/api/audits"
    ):
        response = client.get(route)
        assert response.status_code == 200

def test_aucune_collecte_par_defaut(monkeypatch):
    monkeypatch.delenv(
        "X1000_SOURCE_URL", raising=False
    )
    assert collecter()["courses"] == []
