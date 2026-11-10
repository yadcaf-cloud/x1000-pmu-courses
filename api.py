#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
X1000 PMU COURSES V74
API SECURISEE - AUDIT AVANT RENDER

Compatible :
- moteurs.py V68
- moteurs_v65.py V70
- coordination_x1000.py V68
- collecte_pmu.py V67
- validation_pmu.py V71
- integration_x1000.py V72

Aucune analyse reelle autorisee.
Aucune ecriture de fichier.
Aucun FIGE automatique.
Aucun commit, push ou deploiement.
"""

import logging
import os
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from moteurs import MOTEURS
from collecte_pmu import (
    collecter,
    CollecteErreur,
)
from validation_pmu import valider_course
from integration_x1000 import (
    examiner_course,
    analyser_course,
    ANALYSE_REELLE_AUTORISEE,
)

PROJET = "X1000 PMU COURSES"
VERSION = "V74"
PORT_LOCAL = 8765

logger = logging.getLogger(
    "x1000-pmu-courses"
)

app = FastAPI(
    title=PROJET,
    version="74.0",
    description=(
        "API de supervision et de "
        "validation securisee"
    ),
)

# Origines HTTPS autorisees.
ORIGINES = {
    "https://yadcaf-cloud.github.io"
}

for origine in os.getenv(
    "X1000_CORS_ORIGINS", ""
).split(","):
    origine = origine.strip().rstrip("/")

    if (
        origine.startswith("https://")
        and origine.count("/") == 2
        and "@" not in origine
        and "?" not in origine
        and "#" not in origine
    ):
        ORIGINES.add(origine)

app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(ORIGINES),
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=[
        "Accept",
        "Content-Type",
    ],
    allow_credentials=False,
)


def maintenant():
    return datetime.now(
        timezone.utc
    ).isoformat()


def etat_moteurs():
    """
    Etat structurel uniquement.
    Ne prouve pas une execution.
    """
    return {
        getattr(m, "nom", "INCONNU"):
        "EN_ATTENTE_VALIDATION"
        for m in MOTEURS
    }


def analyse_active():
    """
    L'activation par environnement
    ne suffit jamais a autoriser
    une analyse reelle.
    """
    return (
        ANALYSE_REELLE_AUTORISEE
        is True
        and os.getenv(
            "X1000_ANALYZE_ENABLED", "0"
        ).strip() == "1"
    )


def configuration_source():
    url = os.getenv(
        "X1000_SOURCE_URL", ""
    ).strip()

    hosts = os.getenv(
        "X1000_ALLOWED_HOSTS", ""
    ).strip()

    return {
        "source_configuree": bool(
            url and hosts
        ),
        "collecte_automatique": False,
    }


@app.get("/health")
def health():
    """
    Verification technique.
    Ne certifie pas les donnees PMU.
    """
    return {
        "status": "ok",
        "projet": PROJET,
        "version": VERSION,
        "analyse_active":
            analyse_active(),
    }


@app.get("/api/status")
def status():
    source = configuration_source()

    return {
        "projet": PROJET,
        "version": VERSION,
        "mode": "LECTURE_SEULE",
        "moteurs": etat_moteurs(),
        "production_port_preserve":
            PORT_LOCAL,
        "source_configuree":
            source["source_configuree"],
        "collecte_automatique": False,
        "analyse_active":
            analyse_active(),
        "validation_pmu":
            "STRUCTURELLE",
        "source_authentifiee": False,
        "fige_automatique": False,
        "horodatage": maintenant(),
    }


@app.get("/api/engines")
def engines():
    moteurs = etat_moteurs()

    return {
        "projet": PROJET,
        "version": VERSION,
        "moteurs": moteurs,
        "nombre_detecte":
            len(moteurs),
        "execution_validee": False,
        "analyse_reelle_autorisee":
            analyse_active(),
    }


@app.get("/api/courses")
def courses():
    """
    Collecte explicite a la requete.
    Aucune execution des moteurs.
    """
    try:
        resultat = collecter()

        if not isinstance(
            resultat, dict
        ):
            raise CollecteErreur(
                "Format de collecte invalide"
            )

        donnees = resultat.get(
            "courses", []
        )

        if not isinstance(
            donnees, list
        ):
            raise CollecteErreur(
                "Liste de courses invalide"
            )

        return {
            "courses": donnees,
            "statut": resultat.get(
                "statut",
                "NON_VERIFIE",
            ),
            "source": resultat.get(
                "source"
            ),
            "donnees_verifiees": False,
            "source_authentifiee": False,
            "horodatage": maintenant(),
        }

    except CollecteErreur as exc:
        logger.warning(
            "Erreur collecte : %s",
            getattr(
                exc,
                "code",
                "COLLECTE_ERREUR",
            ),
        )

        return {
            "courses": [],
            "statut": "ERREUR_COLLECTE",
            "code_erreur": getattr(
                exc,
                "code",
                "COLLECTE_ERREUR",
            ),
            "http_status": getattr(
                exc,
                "http_status",
                None,
            ),
            "source": None,
            "donnees_verifiees": False,
            "source_authentifiee": False,
            "horodatage": maintenant(),
        }

    except Exception:
        logger.exception(
            "Erreur interne de collecte"
        )

        raise HTTPException(
            status_code=503,
            detail="Collecte indisponible",
        )


@app.get("/api/selections")
def selections():
    """
    Aucune selection inventee.
    Source persistante non raccordee.
    """
    return {
        "selections": [],
        "statut": "SOURCE_NON_CONNECTEE",
        "donnees_verifiees": False,
    }


@app.get("/api/figes")
def figes():
    """
    Aucune modification ni
    generation de FIGE.
    """
    return {
        "figes": [],
        "statut": "ARCHIVES_NON_CONNECTEES",
        "donnees_verifiees": False,
    }


@app.get("/api/audits")
def audits():
    """
    Aucun audit officiel invente.
    """
    return {
        "audits": [],
        "statut": "AUDITS_NON_CONNECTES",
        "donnees_verifiees": False,
    }


class AnalyseRequete(BaseModel):
    course: dict = Field(
        description=(
            "Course fournie pour "
            "validation structurelle"
        )
    )


@app.get("/api/analyze")
def analyze_information():
    return {
        "projet": PROJET,
        "version": VERSION,
        "statut": "ANALYSE_DESACTIVEE",
        "methode": "POST",
        "analyse_active": False,
        "moteurs": etat_moteurs(),
        "fige_automatique": False,
    }


@app.post("/api/analyze")
def analyze(requete: AnalyseRequete):
    """
    Aucun client ne peut autoriser
    une analyse par simple booleen.

    Validation et diagnostic seulement.
    """

    if not analyse_active():
        raise HTTPException(
            status_code=503,
            detail={
                "statut": "ANALYSE_DESACTIVEE",
                "raison": (
                    "Authentification de "
                    "source non validee"
                ),
            },
        )

    # Protection supplementaire :
    # le validateur existant ne
    # certifie aucune provenance.
    course = dict(requete.course)
    course["donnees_verifiees"] = False

    rapport = valider_course(
        course,
        provenance=None,
    )

    if (
        rapport.get(
            "autorisation_analyse"
        ) is not True
        or rapport.get(
            "provenance_authentifiee"
        ) is not True
    ):
        raise HTTPException(
            status_code=422,
            detail={
                "statut":
                    "VALIDATION_INSUFFISANTE",
                "message": (
                    "Analyse refusee : "
                    "donnees non authentifiees"
                ),
            },
        )

    # Double verrou de securite.
    raise HTTPException(
        status_code=503,
        detail={
            "statut":
                "ANALYSE_REELLE_NON_AUTORISEE"
        },
    )


@app.post("/api/validate")
def validate(requete: AnalyseRequete):
    """
    Diagnostic structurel uniquement.

    Ne produit jamais de classement.
    Ne valide pas l'authenticite PMU.
    """
    try:
        course = dict(
            requete.course
        )

        course[
            "donnees_verifiees"
        ] = False

        examen = examiner_course(
            course,
            provenance=None,
        )

        return {
            "projet": PROJET,
            "version": VERSION,
            "statut":
                "DIAGNOSTIC_SEULEMENT",
            "validation": examen.get(
                "validation"
            ),
            "source_authentifiee":
                False,
            "analyse_autorisee": False,
            "classement": [],
            "pari": None,
            "fige": False,
            "horodatage": maintenant(),
        }

    except Exception:
        logger.exception(
            "Erreur de validation"
        )

        raise HTTPException(
            status_code=503,
            detail=(
                "Validation indisponible"
            ),
        )


@app.get("/api/diagnostic")
def diagnostic():
    """
    Etat de preparation technique.
    Aucun secret retourne.
    """
    return {
        "projet": PROJET,
        "version": VERSION,
        "mode": "AUDIT_AVANT_RENDER",
        "moteurs_detectes":
            len(MOTEURS),
        "moteurs_attendus": 5,
        "analyse_active":
            analyse_active(),
        "source_authentifiee": False,
        "archives_connectees": False,
        "render_deploye": False,
        "fige_automatique": False,
        "horodatage": maintenant(),
    }


if __name__ == "__main__":
    import uvicorn

    # Termux : port historique 8765.
    # Render : PORT fourni par Render.
    port = int(
        os.getenv(
            "PORT",
            str(PORT_LOCAL),
        )
    )

    host = (
        "0.0.0.0"
        if os.getenv("PORT")
        else "127.0.0.1"
    )

    uvicorn.run(
        app,
        host=host,
        port=port,
    )
