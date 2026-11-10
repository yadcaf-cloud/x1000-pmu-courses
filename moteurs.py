#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
X1000 PMU COURSES V68
MOTEURS M1 A M5 - ROLES ET CONTROLE

- Cinq moteurs independants.
- Roles hippiques explicitement definis.
- Conservation des moteurs V65.
- Verification des interfaces existantes.
- Aucun pronostic invente.
- Aucun pari ou FIGE automatique.
- Aucune collecte reseau.
- Aucune modification des archives.
- Aucun commit, push ou deploiement.
"""

import json
from datetime import datetime, timezone

from moteurs_v65 import (
    ROLES as ROLES_V65,
    Moteur,
    M1,
    M2,
    M3,
    M4,
    M5,
    MOTEURS,
    verifier_course,
    analyser_tous,
)

PROJET = "X1000 PMU COURSES"
VERSION = "V68"
PORT_PRODUCTION = 8765

NOMS_ATTENDUS = (
    "M1", "M2", "M3", "M4", "M5"
)

# Missions officielles des moteurs.
# Ces descriptions ne remplacent pas
# les algorithmes existants.

MISSIONS = {
    "M1": {
        "nom": "Statistiques et performances",
        "axes": [
            "Performances historiques",
            "Classements et chronometres",
            "Regularite",
            "Distance et parcours",
            "Niveau des oppositions",
        ],
    },
    "M2": {
        "nom": "Strategie et deroulement",
        "axes": [
            "Rythme probable",
            "Chevaux de tete",
            "Attentistes",
            "Placement et tactique",
            "Scenarios de course",
        ],
    },
    "M3": {
        "nom": "Profils et aptitudes",
        "axes": [
            "Aptitude du cheval",
            "Terrain et distance",
            "Jockey ou driver",
            "Entraineur",
            "Corde et parcours",
        ],
    },
    "M4": {
        "nom": "Forme et informations recentes",
        "axes": [
            "Forme actuelle",
            "Dernieres performances",
            "Ferrure et equipement",
            "Non-partants",
            "Conditions recentes verifiees",
        ],
    },
    "M5": {
        "nom": "Contre-analyse et outsiders",
        "axes": [
            "Faux favoris potentiels",
            "Chevaux sous-estimes",
            "Outsiders credibles",
            "Incoherences des cotes",
            "Valeur sportive cachee",
        ],
    },
}

# ROLES conserve la compatibilite
# avec les imports du projet.
ROLES = {
    nom: mission["nom"]
    for nom, mission in MISSIONS.items()
}


def verifier_installation():
    """
    Controle structurel uniquement.

    Aucun moteur n'est execute.
    Aucune donnee n'est modifiee.
    """

    try:
        moteurs = list(MOTEURS)
    except TypeError:
        moteurs = []

    noms = [
        getattr(m, "nom", None)
        for m in moteurs
    ]

    noms_valides = (
        len(noms) == 5
        and all(
            isinstance(n, str)
            for n in noms
        )
    )

    uniques = (
        len(set(noms)) == 5
        if noms_valides
        else False
    )

    identites_valides = (
        noms_valides
        and uniques
        and set(noms) == set(NOMS_ATTENDUS)
    )

    interfaces = {}

    for moteur in moteurs:
        nom = getattr(moteur, "nom", None)

        if not isinstance(nom, str):
            continue

        mission = MISSIONS.get(nom, {})

        interfaces[nom] = {
            "mission": mission.get("nom"),
            "axes": mission.get("axes", []),
            "role_v65": (
                ROLES_V65.get(nom)
                if isinstance(ROLES_V65, dict)
                else None
            ),
            "methode_analyser": callable(
                getattr(moteur, "analyser", None)
            ),
            "statut": "NON_EXECUTE",
        }

    contrats_valides = (
        callable(verifier_course)
        and callable(analyser_tous)
        and all(
            callable(
                getattr(m, "analyser", None)
            )
            for m in moteurs
        )
    )

    installation_valide = (
        identites_valides
        and contrats_valides
        and len(interfaces) == 5
    )

    return {
        "projet": PROJET,
        "version": VERSION,
        "mode": "LECTURE_SEULE",
        "moteurs_detectes": len(moteurs),
        "identites_valides": identites_valides,
        "moteurs_uniques": uniques,
        "interfaces_valides": contrats_valides,
        "installation_valide": installation_valide,
        "interfaces": interfaces,
        "algorithmes_valides": False,
        "execution_validee": False,
        "classements_generes": False,
        "paris_generes": False,
        "figes_modifies": False,
        "archives_modifiees": False,
        "port_production_preserve":
            PORT_PRODUCTION,
        "horodatage": datetime.now(
            timezone.utc
        ).isoformat(),
    }


def diagnostic_moteurs():
    return verifier_installation()


def missions_moteurs():
    """
    Retourner les missions declarees.

    Aucun calcul hippique.
    """
    return {
        nom: {
            "nom": mission["nom"],
            "axes": list(mission["axes"]),
        }
        for nom, mission in MISSIONS.items()
    }


if __name__ == "__main__":
    rapport = verifier_installation()

    print(
        json.dumps(
            rapport,
            ensure_ascii=False,
            indent=2
        )
    )

    if not rapport["installation_valide"]:
        raise SystemExit(
            "ERREUR : installation M1-M5 "
            "ou interfaces non conformes"
        )

    print(
        "X1000 PMU COURSES V68 : "
        "interfaces M1-M5 conformes"
    )
