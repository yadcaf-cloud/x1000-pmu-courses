"""X1000 PMU COURSES V67 — API contrôlée, lecture seule.

Aucun pronostic inventé.
Aucun FIGÉ automatique.
Aucune modification des archives.
Port de production 8765 préservé.
"""

import os
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from moteurs import MOTEURS
from collecte_pmu import collecter, CollecteErreur

VERSION = "V67"
PORT_PRODUCTION = 8765

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("x1000-pmu-courses")

app = FastAPI(
    title="X1000 PMU COURSES",
    version="67.0",
    description="API de consultation et diagnostic contrôlé",
)

# Origine GitHub Pages autorisée.
# D'autres origines peuvent être ajoutées par variable
# d'environnement, sans utiliser de joker.
origines = {
    "https://yadcaf-cloud.github.io"
}

origines.update(
    x.strip().rstrip("/")
    for x in os.getenv(
        "X1000_CORS_ORIGINS", ""
    ).split(",")
    if x.strip()
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(origines),
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Accept"],
)


def moteurs_disponibles():
    resultat = {}

    for moteur in MOTEURS:
        nom = getattr(moteur, "nom", None)

        if not isinstance(nom, str) or not nom:
            continue

        resultat[nom] = "EN_ATTENTE_VALIDATION"

    return resultat


@app.get("/health")
def health():
    return {
        "status": "ok",
        "version": VERSION,
    }


@app.get("/api/status")
def status():
    return {
        "projet": "X1000 PMU COURSES",
        "version": VERSION,
        "mode": "LECTURE_SEULE",
        "moteurs": moteurs_disponibles(),
        "production_port_preserve": PORT_PRODUCTION,
        "source_configuree": bool(
            os.getenv("X1000_SOURCE_URL", "").strip()
        ),
        "collecte_automatique": False,
        "fige_automatique": False,
        "archives_modifiees": False,
    }


@app.get("/api/engines")
def engines():
    return {
        "moteurs": moteurs_disponibles(),
        "nombre_detecte": len(moteurs_disponibles()),
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

        donnees = resultat.get("courses", [])

        if not isinstance(donnees, list):
            raise CollecteErreur(
                "Liste des courses invalide"
            )

        return {
            "courses": donnees,
            "statut": resultat.get(
                "statut", "NON_VERIFIE"
            ),
            "source": resultat.get("source"),
            "donnees_verifiees": False,
        }

    except CollecteErreur as exc:
        logger.warning(
            "Collecte PMU indisponible: %s",
            type(exc).__name__,
        )

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
    course_id: str = Field(
        min_length=1,
        max_length=128,
    )


@app.post("/api/analyze")
def analyze(requete: AnalyseRequete):
    # Aucun appel aux moteurs tant que leur contrat
    # réel et les garanties de lecture seule
    # ne sont pas vérifiés.
    raise HTTPException(
        status_code=503,
        detail={
            "statut": "ANALYSE_NON_CONNECTEE",
            "course_id": requete.course_id,
            "moteurs": moteurs_disponibles(),
            "pronostic_genere": False,
            "fige": False,
            "message": (
                "Contrat du noyau central à valider "
                "avant activation de l'analyse."
            ),
        },
    )


@app.get("/api/analyze")
def analyze_information():
    return {
        "statut": "ANALYSE_NON_CONNECTEE",
        "methode_prevue": "POST",
        "execution_validee": False,
        "pronostic_genere": False,
        "fige": False,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=PORT_PRODUCTION,
    )
