#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
X1000 PMU COURSES V68
COORDINATION CENTRALE - ARBITRAGE CONTROLE

- M1 a M5 independants.
- Validation des classements.
- Comparaison des propositions.
- Arbitrage par consensus.
- Aucune prediction sans donnees valides.
- Aucun pari automatique.
- Aucun FIGE automatique.
- Aucune ecriture dans les archives.
- Aucun commit, push ou deploiement.
"""

from collections import defaultdict
from datetime import datetime, timezone

from moteurs import MOTEURS

VERSION = "V68"
PROJET = "X1000 PMU COURSES"

NOMS_ATTENDUS = {
    "M1", "M2", "M3", "M4", "M5"
}

POINTS_POSITION = (5, 4, 3, 2, 1)


def numeros_actifs(course):
    """Extraire les numeros de partants actifs."""

    if not isinstance(course, dict):
        return set()

    partants = course.get("partants")

    if not isinstance(partants, list):
        return set()

    numeros = set()

    for partant in partants:
        if not isinstance(partant, dict):
            continue

        numero = partant.get("numero")

        if (
            isinstance(numero, int)
            and not isinstance(numero, bool)
            and numero > 0
            and partant.get("non_partant") is False
        ):
            numeros.add(numero)

    return numeros


def verifier_classement(resultat, course):
    """Valider un classement de cinq chevaux."""

    if not isinstance(resultat, dict):
        return False

    if resultat.get("statut") != "ANALYSE_VALIDEE":
        return False

    classement = resultat.get("classement")

    if not isinstance(classement, list):
        return False

    if len(classement) != 5:
        return False

    if any(
        not isinstance(numero, int)
        or isinstance(numero, bool)
        or numero <= 0
        for numero in classement
    ):
        return False

    if len(set(classement)) != 5:
        return False

    actifs = numeros_actifs(course)

    if len(actifs) < 5:
        return False

    return all(
        numero in actifs
        for numero in classement
    )


def arbitrer(valides):
    """
    Calculer un consensus positionnel.

    Le score est une agregation des
    classements transmis, et non une
    probabilite de victoire.

    Au moins deux moteurs independants
    doivent etre valides pour publier
    une proposition centrale.
    """

    if len(valides) < 2:
        return {
            "classement": [],
            "scores": {},
            "accords": {},
            "statut": "CONSENSUS_INSUFFISANT",
        }

    scores = defaultdict(int)
    accords = defaultdict(int)

    for resultat in valides:
        classement = resultat["classement"]

        for position, numero in enumerate(
            classement
        ):
            scores[numero] += (
                POINTS_POSITION[position]
            )
            accords[numero] += 1

    classement_central = sorted(
        scores,
        key=lambda numero: (
            -scores[numero],
            -accords[numero],
            numero,
        )
    )[:5]

    return {
        "classement": classement_central,
        "scores": dict(scores),
        "accords": dict(accords),
        "statut": "CONSENSUS_CALCULE",
    }


def coordonner(course):
    """
    Consulter les moteurs independants
    et arbitrer uniquement les analyses
    structurellement valides.

    Aucune persistance.
    """

    if not isinstance(course, dict):
        raise ValueError("Course invalide")

    details = []
    valides = []
    noms_vus = set()

    for moteur in MOTEURS:
        nom = getattr(moteur, "nom", None)

        if (
            not isinstance(nom, str)
            or nom not in NOMS_ATTENDUS
            or nom in noms_vus
        ):
            details.append({
                "moteur": str(nom),
                "statut": "IDENTITE_INVALIDE",
                "classement": [],
                "pari": None,
                "fige": False,
            })
            continue

        noms_vus.add(nom)

        try:
            resultat = moteur.analyser(course)

            if not isinstance(resultat, dict):
                details.append({
                    "moteur": nom,
                    "statut": "FORMAT_INVALIDE",
                    "classement": [],
                    "pari": None,
                    "fige": False,
                })
                continue

            # L'identite provient de l'objet
            # moteur, pas d'une declaration
            # arbitraire du resultat.
            if resultat.get("moteur") != nom:
                details.append({
                    "moteur": nom,
                    "statut": "IDENTITE_RESULTAT_INVALIDE",
                    "classement": [],
                    "pari": None,
                    "fige": False,
                })
                continue

            if verifier_classement(
                resultat, course
            ):
                valides.append({
                    "moteur": nom,
                    "classement": list(
                        resultat["classement"]
                    ),
                })

                details.append({
                    "moteur": nom,
                    "statut": "ANALYSE_VALIDEE",
                    "classement": list(
                        resultat["classement"]
                    ),
                    "analyse": resultat.get(
                        "analyse"
                    ),
                    "pari": resultat.get(
                        "pari"
                    ),
                    "fige": False,
                })

            else:
                details.append({
                    "moteur": nom,
                    "statut": "ANALYSE_NON_VALIDEE",
                    "classement": [],
                    "pari": None,
                    "fige": False,
                })

        except Exception as exc:
            details.append({
                "moteur": nom,
                "statut": "ERREUR_MOTEUR",
                "erreur_type": type(
                    exc
                ).__name__,
                "classement": [],
                "pari": None,
                "fige": False,
            })

    resultat_arbitrage = arbitrer(valides)

    classement = resultat_arbitrage[
        "classement"
    ]

    installation_complete = (
        noms_vus == NOMS_ATTENDUS
        and len(details) == 5
    )

    statut = (
        "PROPOSITION_CENTRALE"
        if classement and installation_complete
        else "EN_ATTENTE_ANALYSES"
    )

    return {
        "moteur": "X1000",
        "projet": PROJET,
        "version": VERSION,
        "course_id": course.get("id"),
        "statut": statut,
        "installation_complete":
            installation_complete,
        "moteurs_consultes": len(details),
        "moteurs_valides": len(valides),
        "classement": (
            classement
            if installation_complete
            else []
        ),
        "analyse": (
            "Consensus positionnel des "
            "classements valides"
            if statut == "PROPOSITION_CENTRALE"
            else None
        ),
        "scores": (
            resultat_arbitrage["scores"]
            if installation_complete
            else {}
        ),
        "accords": (
            resultat_arbitrage["accords"]
            if installation_complete
            else {}
        ),
        "pari": None,
        "fige": False,
        "details": details,
        "horodatage": datetime.now(
            timezone.utc
        ).isoformat(),
    }


if __name__ == "__main__":
    course_test = {
        "id": "TEST-ISOLE-V68",
        "hippodrome": "TEST",
        "partants": [
            {
                "numero": numero,
                "non_partant": False,
            }
            for numero in range(1, 7)
        ],
    }

    resultat = coordonner(course_test)

    assert (
        resultat["moteurs_consultes"] == 5
    )

    assert resultat["pari"] is None
    assert resultat["fige"] is False

    print(
        "Coordination X1000 V68 : "
        "controle termine"
    )
