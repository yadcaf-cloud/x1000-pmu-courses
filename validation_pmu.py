#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
X1000 PMU COURSES V71
VALIDATION DES DONNEES PMU - LECTURE SEULE

Missions :
- Verifier identite et parametres de course.
- Verifier partants et non-partants.
- Verifier provenance et fraicheur.
- Controler les indicateurs M1 a M5.
- Refuser les donnees non fiables.
- Ne jamais faire confiance a un booleen
  donnees_verifiees transmis par un client.
- Ne jamais fabriquer de notes ou pronostics.

Aucun reseau, fichier, FIGE, pari,
commit, push ou deploiement.

IMPORTANT :
Le controle structurel ne certifie pas
l'authenticite d'une source PMU.
La confiance exige un adaptateur de
collecte authentifie et audite.
"""

import copy
import ipaddress
import json
import math
import re

from datetime import datetime, timezone
from urllib.parse import urlsplit

VERSION = "V71"
PROJET = "X1000 PMU COURSES"

MAX_PARTANTS = 40
MAX_AGE_MINUTES = 10

ROLES = {
    "M1": "Statistiques et performances",
    "M2": "Rythme et strategie",
    "M3": "Profils et aptitudes",
    "M4": "Forme recente",
    "M5": "Contre-analyse et outsiders",
}

CRITERES = {
    "M1": (
        "performance",
        "regularite",
        "distance",
        "chrono",
        "opposition",
    ),
    "M2": (
        "rythme",
        "placement",
        "tactique",
        "scenario",
    ),
    "M3": (
        "aptitude_terrain",
        "aptitude_parcours",
        "jockey",
        "entraineur",
        "aptitude_distance",
    ),
    "M4": (
        "forme_recente",
        "condition",
        "ferrure",
        "informations_recentes",
    ),
    "M5": (
        "valeur_cachee",
        "potentiel_outsider",
        "contre_favori",
        "rapport_valeur_cote",
    ),
}

ID_PATTERN = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$"
)

HOST_PATTERN = re.compile(
    r"^[a-z0-9-]+(?:\.[a-z0-9-]+)+$"
)


class ValidationErreur(Exception):
    """Erreur de validation controlee."""
    pass


def horodatage():
    return datetime.now(
        timezone.utc
    ).isoformat()


def date_utc(valeur):
    """
    Exiger une date ISO 8601 avec
    fuseau horaire explicite.
    """

    if not isinstance(valeur, str):
        raise ValidationErreur(
            "Horodatage absent"
        )

    try:
        dt = datetime.fromisoformat(
            valeur.replace("Z", "+00:00")
        )
    except ValueError as exc:
        raise ValidationErreur(
            "Horodatage invalide"
        ) from exc

    if dt.tzinfo is None:
        raise ValidationErreur(
            "Fuseau horaire absent"
        )

    if dt.utcoffset() is None:
        raise ValidationErreur(
            "Fuseau horaire invalide"
        )

    return dt.astimezone(timezone.utc)


def verifier_provenance(
    provenance,
    maintenant=None,
    age_max_minutes=MAX_AGE_MINUTES,
):
    """
    Controle de coherence uniquement.

    Ne constitue PAS une preuve
    cryptographique d'authenticite.
    """

    erreurs = []

    if not isinstance(provenance, dict):
        return {
            "valide": False,
            "erreurs": [
                "Provenance absente"
            ],
        }

    source = provenance.get("source")
    collecte_a = provenance.get(
        "collecte_a"
    )

    if not isinstance(source, str):
        erreurs.append(
            "Source absente"
        )
    else:
        try:
            parsed = urlsplit(source)
            host = parsed.hostname
            port = parsed.port

            if (
                parsed.scheme != "https"
                or not host
                or port not in (None, 443)
                or parsed.username is not None
                or parsed.password is not None
                or parsed.fragment
                or not HOST_PATTERN.fullmatch(
                    host
                )
            ):
                erreurs.append(
                    "Source HTTPS invalide"
                )

            if host:
                try:
                    ipaddress.ip_address(host)
                except ValueError:
                    pass
                else:
                    erreurs.append(
                        "Adresse IP directe interdite"
                    )

        except ValueError:
            erreurs.append(
                "URL source invalide"
            )

    try:
        instant = date_utc(
            collecte_a
        )

        reference = (
            maintenant
            if maintenant is not None
            else datetime.now(timezone.utc)
        )

        if (
            not isinstance(reference, datetime)
            or reference.tzinfo is None
            or reference.utcoffset() is None
        ):
            raise ValidationErreur(
                "Reference temporelle invalide"
            )

        reference = reference.astimezone(
            timezone.utc
        )

        age = (
            reference - instant
        ).total_seconds()

        if age < -60:
            erreurs.append(
                "Collecte datee du futur"
            )

        if age > age_max_minutes * 60:
            erreurs.append(
                "Donnees trop anciennes"
            )

    except ValidationErreur as exc:
        erreurs.append(str(exc))

    return {
        "valide": not erreurs,
        "erreurs": erreurs,
    }


def verifier_identite(course):
    erreurs = []

    if not isinstance(course, dict):
        return ["Course invalide"]

    identifiant = course.get("id")

    if (
        not isinstance(identifiant, str)
        or not ID_PATTERN.fullmatch(
            identifiant
        )
    ):
        erreurs.append(
            "Identifiant de course invalide"
        )

    hippodrome = course.get(
        "hippodrome"
    )

    if (
        not isinstance(hippodrome, str)
        or not hippodrome.strip()
        or len(hippodrome) > 120
    ):
        erreurs.append(
            "Hippodrome invalide"
        )

    return erreurs


def verifier_partants(course):
    erreurs = []

    partants = course.get(
        "partants"
    )

    if not isinstance(partants, list):
        return [
            "Liste des partants absente"
        ]

    if not (
        5 <= len(partants) <= MAX_PARTANTS
    ):
        erreurs.append(
            "Nombre de partants invalide"
        )

    numeros = set()
    actifs = 0

    for index, partant in enumerate(
        partants
    ):
        if not isinstance(partant, dict):
            erreurs.append(
                f"Partant {index} invalide"
            )
            continue

        numero = partant.get(
            "numero"
        )

        if (
            not isinstance(numero, int)
            or isinstance(numero, bool)
            or numero <= 0
        ):
            erreurs.append(
                f"Numero invalide : {index}"
            )
            continue

        if numero in numeros:
            erreurs.append(
                f"Numero duplique : {numero}"
            )

        numeros.add(numero)

        np = partant.get(
            "non_partant"
        )

        if not isinstance(np, bool):
            erreurs.append(
                f"Statut NP non verifie : {numero}"
            )
        elif np is False:
            actifs += 1

    if actifs < 5:
        erreurs.append(
            "Moins de cinq partants actifs"
        )

    return erreurs


def note_valide(valeur):
    return (
        isinstance(valeur, (int, float))
        and not isinstance(valeur, bool)
        and math.isfinite(valeur)
        and 0 <= valeur <= 100
    )


def verifier_indicateurs(
    course,
    moteur
):
    """
    Verifier les notes normalisees
    du moteur selectionne.

    Aucune note manquante n'est
    remplacee ou estimee.
    """

    if moteur not in CRITERES:
        raise ValidationErreur(
            "Moteur inconnu"
        )

    partants = course.get(
        "partants", []
    )

    if not isinstance(partants, list):
        return {
            "valide": False,
            "chevaux_complets": 0,
            "erreurs": [
                "Partants invalides"
            ],
        }

    criteres = CRITERES[moteur]
    complets = 0
    erreurs = []

    for partant in partants:
        if not isinstance(partant, dict):
            continue

        if partant.get(
            "non_partant"
        ) is not False:
            continue

        numero = partant.get(
            "numero"
        )

        indicateurs = partant.get(
            "indicateurs"
        )

        if not isinstance(
            indicateurs, dict
        ):
            erreurs.append(
                f"Indicateurs absents : {numero}"
            )
            continue

        manquants = [
            nom
            for nom in criteres
            if not note_valide(
                indicateurs.get(nom)
            )
        ]

        if manquants:
            erreurs.append(
                f"Moteur {moteur}, cheval "
                f"{numero} : "
                + ", ".join(manquants)
            )
        else:
            complets += 1

    return {
        "valide": complets >= 5,
        "chevaux_complets": complets,
        "erreurs": erreurs,
    }


def valider_course(
    course,
    provenance=None,
    maintenant=None,
):
    """
    Validation structurelle complete.

    Le resultat ne donne JAMAIS
    automatiquement une autorisation
    de pronostic.

    La confiance dans la provenance
    doit etre etablie hors de cette
    fonction, par un composant fiable.
    """

    erreurs = []

    erreurs.extend(
        verifier_identite(course)
    )

    if isinstance(course, dict):
        erreurs.extend(
            verifier_partants(course)
        )

    verification_source = (
        verifier_provenance(
            provenance,
            maintenant=maintenant,
        )
    )

    erreurs.extend(
        verification_source["erreurs"]
    )

    moteurs = {}

    if isinstance(course, dict):
        for nom in ROLES:
            moteurs[nom] = (
                verifier_indicateurs(
                    course,
                    nom
                )
            )
    else:
        for nom in ROLES:
            moteurs[nom] = {
                "valide": False,
                "chevaux_complets": 0,
                "erreurs": [
                    "Course invalide"
                ],
            }

    # Le client ne peut pas
    # accorder sa propre confiance.
    #
    # Les donnees ne sont jamais
    # marquees comme authentifiees
    # par ce validateur.
    return {
        "projet": PROJET,
        "version": VERSION,
        "validation_structurelle": (
            not erreurs
        ),
        "provenance_coherente":
            verification_source["valide"],
        "provenance_authentifiee": False,
        "donnees_verifiees": False,
        "autorisation_analyse": False,
        "erreurs": erreurs,
        "moteurs": moteurs,
        "horodatage": horodatage(),
    }


def preparer_course(
    course,
    provenance=None,
    maintenant=None,
):
    """
    Preparer une copie non fiable.

    Ne jamais injecter automatiquement
    donnees_verifiees=True.
    """

    rapport = valider_course(
        course,
        provenance,
        maintenant,
    )

    copie = copy.deepcopy(
        course
    )

    if isinstance(copie, dict):
        copie["donnees_verifiees"] = False

    return {
        "course": copie,
        "validation": rapport,
    }


def diagnostic():
    return {
        "projet": PROJET,
        "version": VERSION,
        "mode": "VALIDATION_LECTURE_SEULE",
        "moteurs": dict(ROLES),
        "fraicheur_max_minutes":
            MAX_AGE_MINUTES,
        "collecte_automatique": False,
        "pronostics_generes": False,
        "figes_modifies": False,
        "archives_modifiees": False,
        "authentification_source":
            "NON_IMPLEMENTEE",
        "horodatage": horodatage(),
    }


def tests_isoles():
    """
    Tests purement locaux.

    Aucune connexion reseau.
    Aucun fichier ecrit.
    """

    instant = datetime.now(
        timezone.utc
    )

    course = {
        "id": "TEST-V71",
        "hippodrome": "TEST",
        "donnees_verifiees": True,
        "partants": [
            {
                "numero": i,
                "non_partant": False,
                "indicateurs": {},
            }
            for i in range(1, 7)
        ],
    }

    provenance = {
        "source": "https://example.org/api",
        "collecte_a": instant.isoformat(),
    }

    rapport = valider_course(
        course,
        provenance,
        maintenant=instant,
    )

    assert (
        rapport["validation_structurelle"]
        is True
    )

    assert (
        rapport["provenance_authentifiee"]
        is False
    )

    assert (
        rapport["donnees_verifiees"]
        is False
    )

    assert (
        rapport["autorisation_analyse"]
        is False
    )

    preparation = preparer_course(
        course,
        provenance,
        maintenant=instant,
    )

    assert (
        preparation["course"][
            "donnees_verifiees"
        ] is False
    )

    assert (
        course["donnees_verifiees"]
        is True
    )

    assert all(
        not item["valide"]
        for item in rapport[
            "moteurs"
        ].values()
    )

    # Test de refus d'un doublon.
    course_invalide = copy.deepcopy(
        course
    )

    course_invalide["partants"][1][
        "numero"
    ] = 1

    rapport_invalide = valider_course(
        course_invalide,
        provenance,
        maintenant=instant,
    )

    assert (
        rapport_invalide[
            "validation_structurelle"
        ] is False
    )

    # Test de refus d'une source
    # non HTTPS.
    provenance_invalide = {
        "source": "http://example.org/api",
        "collecte_a": instant.isoformat(),
    }

    rapport_source = valider_course(
        course,
        provenance_invalide,
        maintenant=instant,
    )

    assert (
        rapport_source[
            "provenance_coherente"
        ] is False
    )

    return {
        "tests": "OK",
        "reseau": False,
        "ecriture": False,
        "pronostic": False,
        "fige": False,
    }


if __name__ == "__main__":
    print(
        json.dumps(
            {
                "diagnostic": diagnostic(),
                "tests": tests_isoles(),
            },
            ensure_ascii=False,
            indent=2
        )
    )
