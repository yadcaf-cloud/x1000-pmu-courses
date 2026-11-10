"""X1000 PMU COURSES V66 — API lecture seule."""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from moteurs import MOTEURS
from collecte_pmu import collecter, CollecteErreur

app = FastAPI(
    title="X1000 PMU COURSES",
    version="66.0"
)

origines = [
    x.strip()
    for x in os.getenv(
        "X1000_CORS_ORIGINS", ""
    ).split(",")
    if x.strip()
]

if origines:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origines,
        allow_methods=["GET"],
        allow_headers=["Accept"],
    )


@app.get("/api/status")
def status():
    return {
        "projet": "X1000 PMU COURSES",
        "version": "V66",
        "mode": "LECTURE_SEULE",
        "moteurs": {
            m.nom: "EN_ATTENTE_VALIDATION"
            for m in MOTEURS
        },
        "production_port_preserve": 8765,
        "source_configuree": bool(
            os.getenv("X1000_SOURCE_URL", "").strip()
        ),
        "collecte_automatique": False,
        "fige_automatique": False,
    }


@app.get("/api/courses")
def courses():
    try:
        resultat = collecter()

        return {
            "courses": resultat["courses"],
            "statut": resultat["statut"],
            "source": resultat["source"],
            "donnees_verifiees": False,
        }

    except CollecteErreur:
        return {
            "courses": [],
            "statut": "ERREUR_COLLECTE",
            "source": None,
            "donnees_verifiees": False,
        }


@app.get("/api/selections")
def selections():
    return {
        "selections": [],
        "statut": "AUCUNE_SELECTION_PUBLIEE",
    }


@app.get("/api/figes")
def figes():
    return {
        "figes": [],
        "statut": "ARCHIVES_NON_CONNECTEES",
    }


@app.get("/api/audits")
def audits():
    return {
        "audits": [],
        "statut": "AUDITS_NON_CONNECTES",
    }
