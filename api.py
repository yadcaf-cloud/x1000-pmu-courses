#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
X1000 PMU COURSES V69
API - RACCORDEMENT CENTRAL CONTROLE

Routes :
GET  /health
GET  /api/status
GET  /api/engines
GET  /api/courses
GET  /api/selections
GET  /api/figes
GET  /api/audits
GET  /api/analyze
POST /api/analyze

SECURITE :
- Lecture seule des fichiers existants.
- Analyse desactivee par defaut.
- Aucun FIGE automatique.
- Aucun pronostic archive automatiquement.
- Aucun commit, push ou deploiement.
- Port de production 8765 preserve.
"""

import os
import logging
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from moteurs import MOTEURS
from collecte_pmu import collecter, CollecteErreur
from coordination_x1000 import coordonner

PROJET = "X1000 PMU COURSES"
VERSION = "V69"
PORT_PRODUCTION = 8765

logger = logging.getLogger("x1000-pmu-courses")

app = FastAPI(
    title=PROJET,
    version="69.0",
)

origines = {
    "https://yadcaf-cloud.github.io"
}

origines.update(
    origine.strip().rstrip("/")
    for origine in os.getenv(
        "X1000_CORS_ORIGINS", ""
    ).split(",")
    if origine.strip()
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(origines),
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Accept", "Content-Type"],
)


def analyse_active():
    """
    Activation explicite uniquement
    apres validation des moteurs.
    """
    return (
        os.getenv(
            "X1000_ANALYZE_ENABLED", "0"
        ).strip() == "1"
    )


def etat_moteurs():
    """
    Presence des moteurs, sans
    supposer leur fonctionnement.
    """
    return {
        getattr(m, "nom", "INCONNU"):
            "EN_ATTENTE_VALIDATION"
        for m in MOTEURS
    }


def horodatage():
    return datetime.now(
        timezone.utc
    ).isoformat()


@app.get("/health")
def health():
    return {
        "status": "ok",
        "version": VERSION,
    }


@app.get("/api/status")
def status():
    return {
        "projet": PROJET,
        "version": VERSION,
        "mode": "LECTURE_SEULE",
        "moteurs": etat_moteurs(),
        "production_port_preserve":
            PORT_PRODUCTION,
        "source_configuree": bool(
            os.getenv(
                "X1000_SOURCE_URL", ""
            ).strip()
        ),
        "analyse_active":
            analyse_active(),
        "collecte_automatique": False,
        "fige_automatique": False,
        "horodatage": horodatage(),
    }


@app.get("/api/engines")
def engines():
    moteurs = etat_moteurs()

    return {
        "moteurs": moteurs,
        "nombre_detecte": len(moteurs),
        "execution_validee": False,
    }


@app.get("/api/courses")
def courses():
    try:
        resultat = collecter()

        if not isinstance(resultat, dict):
            raise CollecteErreur(
                "Format de collecte invalide"
            )

        donnees = resultat.get(
            "courses", []
        )

        if not isinstance(donnees, list):
            raise CollecteErreur(
                "Liste des courses invalide"
            )

        return {
            "courses": donnees,
            "statut": resultat.get(
                "statut", "NON_VERIFIE"
            ),
            "source": resultat.get(
                "source"
            ),
            "donnees_verifiees": False,
        }

    except CollecteErreur as exc:
        logger.warning(
            "Collecte indisponible: %s",
            getattr(
                exc, "code",
                "COLLECTE_ERREUR"
            )
        )

        return {
            "courses": [],
            "statut": "ERREUR_COLLECTE",
            "code_erreur": getattr(
                exc, "code",
                "COLLECTE_ERREUR"
            ),
            "http_status": getattr(
                exc, "http_status",
                None
            ),
            "source": None,
            "donnees_verifiees": False,
        }


@app.get("/api/selections")
def selections():
    return {
        "selections": [],
        "statut": "SOURCE_NON_CONNECTEE",
        "donnees_verifiees": False,
    }


@app.get("/api/figes")
def figes():
    return {
        "figes": [],
        "statut": "ARCHIVES_NON_CONNECTEES",
        "donnees_verifiees": False,
    }


@app.get("/api/audits")
def audits():
    return {
        "audits": [],
        "statut": "AUDITS_NON_CONNECTES",
        "donnees_verifiees": False,
    }


class AnalyseRequete(BaseModel):
    """
    Course fournie explicitement.

    Aucun chargement automatique
    de donnees PMU.
    """

    course: dict = Field(
        description="Course a analyser"
    )


@app.get("/api/analyze")
def analyze_information():
    return {
        "statut": (
            "ACTIVABLE"
            if analyse_active()
            else "DESACTIVEE"
        ),
        "methode": "POST",
        "analyse_active":
            analyse_active(),
        "moteurs": etat_moteurs(),
        "fige_automatique": False,
    }


@app.post("/api/analyze")
def analyze(requete: AnalyseRequete):
    """
    Analyse uniquement sur demande.

    Aucun resultat n'est archive.
    """

    if not analyse_active():
        raise HTTPException(
            status_code=503,
            detail={
                "statut": "ANALYSE_DESACTIVEE",
                "message": (
                    "Activation impossible avant "
                    "validation des moteurs."
                ),
            },
        )

    course = requete.course

    if not isinstance(course, dict):
        raise HTTPException(
            status_code=422,
            detail="Course invalide",
        )

    partants = course.get("partants")

    if (
        not isinstance(partants, list)
        or len(partants) < 5
    ):
        raise HTTPException(
            status_code=422,
            detail="Partants insuffisants",
        )

    # Les moteurs ne doivent etre
    # actives qu'apres audit de leurs
    # effets de bord.
    try:
        resultat = coordonner(course)

    except Exception:
        logger.exception(
            "Erreur de coordination X1000"
        )

        raise HTTPException(
            status_code=503,
            detail="Coordination indisponible",
        )

    return {
        "projet": PROJET,
        "version": VERSION,
        "mode": "ANALYSE_NON_PERSISTEE",
        "resultat": resultat,
        "archive": False,
        "fige_automatique": False,
        "horodatage": horodatage(),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=PORT_PRODUCTION,
    )
