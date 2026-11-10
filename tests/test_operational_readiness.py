"""X1000 PMU COURSES - Tests de preparation operationnelle.

Aucune collecte reseau directe.
Aucun pronostic invente.
Aucun FIGE, pari ou audit cree.
Aucune modification des archives.
Aucun deploiement Render.
"""

from fastapi.testclient import TestClient

from api import app
from moteurs import MOTEURS
from coordination_x1000 import coordonner


def course_isolee():
    return {
        "id": "TEST-ISOLATION",
        "hippodrome": "TEST",
        "donnees_verifiees": False,
        "partants": [
            {
                "numero": numero,
                "non_partant": False,
                "indicateurs": {},
            }
            for numero in range(1, 8)
        ],
    }


def test_cinq_moteurs_installes():
    noms = [m.nom for m in MOTEURS]

    assert len(noms) == 5
    assert set(noms) == {
        "M1", "M2", "M3", "M4", "M5"
    }

    for moteur in MOTEURS:
        assert callable(moteur.analyser)


def test_moteurs_sans_donnees_verifiees():
    course = course_isolee()

    for moteur in MOTEURS:
        resultat = moteur.analyser(course)

        assert resultat["classement"] == []
        assert resultat["pari"] is None
        assert resultat["fige"] is False
        assert resultat["statut"] != "ANALYSE_VALIDEE"


def test_coordination_centrale():
    resultat = coordonner(course_isolee())

    assert resultat["classement"] == []
    assert resultat["pari"] is None
    assert resultat["fige"] is False


def test_routes_api():
    routes = [
        "/health",
        "/api/status",
        "/api/engines",
        "/api/selections",
        "/api/figes",
        "/api/audits",
    ]

    with TestClient(app) as client:
        for route in routes:
            response = client.get(route)
            assert response.status_code == 200, route


def test_api_refuse_confiance_client():
    course = course_isolee()

    # Ce booleen fourni par un client
    # ne constitue pas une verification.
    course["donnees_verifiees"] = True

    with TestClient(app) as client:
        response = client.post(
            "/api/analyze",
            json={"course": course},
        )

        assert response.status_code in (422, 503)


def test_aucun_fige_automatique():
    with TestClient(app) as client:
        statut = client.get("/api/status").json()

        assert statut["fige_automatique"] is False


def test_analyse_reelle_encore_verrouillee():
    with TestClient(app) as client:
        statut = client.get("/api/status").json()

        assert statut["analyse_active"] is False
