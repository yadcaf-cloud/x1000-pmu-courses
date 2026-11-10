#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
X1000 PMU COURSES V67
MOTEURS M1 A M5 - COMPATIBILITE CONTROLEE

Objectifs :
- Conserver les moteurs existants V65.
- Verifier les cinq identites M1 a M5.
- Verifier les interfaces d'analyse.
- Preserver les contrats existants.
- Ne produire aucun pronostic artificiel.
- Ne modifier aucun FIGE ni archive.
- Ne realiser aucune collecte reseau.
- Aucun commit, push ou deploiement.
"""

import json
from datetime import datetime, timezone

from moteurs_v65 import (
    ROLES,
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
VERSION = "V67"
PORT_PRODUCTION = 8765

NOMS_ATTENDUS = (
    "M1",
    "M2",
    "M3",
    "M4",
    "M5",
)


def verifier_installation():
    """
    Diagnostic structurel sans execution
    des analyses et sans ecriture.
    """

    noms = [
        getattr(m, "nom", None)
        for m in MOTEURS
    ]

    cinq_moteurs = (
        len(MOTEURS) == 5
    )

    noms_valides = (
        tuple(noms) == NOMS_ATTENDUS
    )

    moteurs_uniques = (
        len(set(noms)) == 5
        if all(
            isinstance(n, str)
            for n in noms
        )
        else False
    )

    interfaces = {}

    for moteur in MOTEURS:
        nom = getattr(
            moteur,
            "nom",
            None
        )

        if not isinstance(nom, str):
            continue

        interfaces[nom] = {
            "role": ROLES.get(nom),
            "methode_analyser": callable(
                getattr(
                    moteur,
                    "analyser",
                    None
                )
            ),
            "statut": "NON_EXECUTE",
        }

    interfaces_valides = (
        len(interfaces) == 5
        and all(
            item["methode_analyser"]
            for item in interfaces.values()
        )
        and callable(verifier_course)
        and callable(analyser_tous)
    )

    installation_valide = all((
        cinq_moteurs,
        noms_valides,
        moteurs_uniques,
        interfaces_valides,
    ))

    return {
        "projet": PROJET,
        "version": VERSION,
        "mode": "DIAGNOSTIC_LECTURE_SEULE",
        "moteurs_installes": len(MOTEURS),
        "moteurs_uniques": moteurs_uniques,
        "noms": noms,
        "ordre_valide": noms_valides,
        "interfaces": interfaces,
        "interfaces_valides": interfaces_valides,
        "installation_valide": installation_valide,
        "algorithmes_valides": False,
        "execution_validee": False,
        "pronostics_generes": False,
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
    """
    Alias de diagnostic sans analyse.
    """
    return verifier_installation()


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
            "ERREUR : interfaces M1-M5 invalides"
        )

    print(
        "X1000 PMU COURSES V67 : "
        "interfaces M1-M5 conformes"
    )
