#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
X1000 PMU COURSES V66
COLLECTE PMU REELLE - LECTURE SEULE

Compatible avec api.py V66.

SECURITE :
- Aucune collecte sans source configuree.
- HTTPS obligatoire.
- Domaines explicitement autorises.
- Refus des IP privees et locales.
- Redirections interdites.
- Taille maximale de reponse.
- Aucune ecriture dans les archives.
- Aucun pronostic, pari ou FIGE.
- Aucun commit, push ou deploiement.
"""

import ipaddress
import json
import os
import socket
import urllib.error
import urllib.request

from datetime import datetime, timezone
from urllib.parse import urlsplit


VERSION = "V66"
PROJET = "X1000 PMU COURSES"

MAX_BYTES = 2_000_000
TIMEOUT = 10

# Configuration par variables d'environnement.
#
# X1000_SOURCE_URL :
# URL HTTPS d'une source autorisee.
#
# X1000_ALLOWED_HOSTS :
# Domaines explicitement autorises,
# separes par des virgules.
#
# Exemple de format uniquement :
#
# X1000_SOURCE_URL =
#   https://source.example/endpoint
#
# X1000_ALLOWED_HOSTS =
#   source.example
#
# Aucune source reelle n'est activee
# automatiquement.


class CollecteErreur(Exception):
    """Erreur de collecte controlee."""
    pass


def configuration():
    """Lire la configuration sans rien modifier."""

    url = os.getenv(
        "X1000_SOURCE_URL", ""
    ).strip()

    hosts = {
        host.strip().lower().rstrip(".")
        for host in os.getenv(
            "X1000_ALLOWED_HOSTS", ""
        ).split(",")
        if host.strip()
    }

    return {
        "url": url,
        "hosts": hosts,
        "active": bool(url and hosts),
    }


def verifier_url(url):
    """Verifier la destination HTTPS."""

    if not isinstance(url, str):
        raise CollecteErreur(
            "URL invalide"
        )

    try:
        parsed = urlsplit(url)
        host = (
            parsed.hostname or ""
        ).lower().rstrip(".")
        port = parsed.port
    except ValueError as exc:
        raise CollecteErreur(
            "Adresse URL invalide"
        ) from exc

    config = configuration()

    if parsed.scheme != "https":
        raise CollecteErreur(
            "HTTPS obligatoire"
        )

    if not host:
        raise CollecteErreur(
            "Domaine absent"
        )

    if host not in config["hosts"]:
        raise CollecteErreur(
            "Domaine non autorise"
        )

    if parsed.username or parsed.password:
        raise CollecteErreur(
            "Identifiants URL interdits"
        )

    if port not in (None, 443):
        raise CollecteErreur(
            "Port non autorise"
        )

    if parsed.fragment:
        raise CollecteErreur(
            "Fragment URL interdit"
        )

    try:
        if ipaddress.ip_address(host):
            raise CollecteErreur(
                "Adresse IP directe interdite"
            )
    except ValueError:
        pass

    try:
        addresses = socket.getaddrinfo(
            host,
            443,
            type=socket.SOCK_STREAM
        )
    except socket.gaierror as exc:
        raise CollecteErreur(
            "Resolution DNS impossible"
        ) from exc

    if not addresses:
        raise CollecteErreur(
            "Aucune adresse DNS"
        )

    for item in addresses:
        try:
            ip = ipaddress.ip_address(
                item[4][0]
            )
        except ValueError as exc:
            raise CollecteErreur(
                "Adresse DNS invalide"
            ) from exc

        if not ip.is_global:
            raise CollecteErreur(
                "Adresse non publique interdite"
            )

    return True


class SansRedirection(
    urllib.request.HTTPRedirectHandler
):
    """Interdire toute redirection HTTP."""

    def redirect_request(
        self,
        req,
        fp,
        code,
        msg,
        headers,
        newurl
    ):
        raise CollecteErreur(
            "Redirection interdite"
        )


def verifier_courses(courses):
    """
    Verifier uniquement la structure JSON.

    Cette verification ne constitue pas
    une certification sportive ou officielle.
    """

    if not isinstance(courses, list):
        raise CollecteErreur(
            "Liste des courses invalide"
        )

    for index, course in enumerate(courses):
        if not isinstance(course, dict):
            raise CollecteErreur(
                f"Course invalide a l'index {index}"
            )

    return courses


def collecter():
    """
    Collecter les donnees d'une source
    explicitement configuree.

    Retour compatible avec api.py V66 :
    - statut
    - courses
    - source

    Aucun fichier n'est modifie.
    """

    config = configuration()

    if not config["active"]:
        return {
            "statut": "SOURCE_NON_CONFIGUREE",
            "courses": [],
            "source": None,
        }

    url = config["url"]

    verifier_url(url)

    # Le proxy de l'environnement est desactive
    # pour limiter les chemins reseau implicites.
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}),
        SansRedirection()
    )

    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent":
                "X1000-PMU-COURSES-V66"
        },
        method="GET"
    )

    try:
        with opener.open(
            request,
            timeout=TIMEOUT
        ) as response:

            if response.status != 200:
                raise CollecteErreur(
                    "Reponse HTTP non valide"
                )

            content_type = (
                response.headers.get(
                    "Content-Type", ""
                ).lower()
            )

            if (
                "application/json" not in content_type
                and "+json" not in content_type
            ):
                raise CollecteErreur(
                    "Reponse non JSON"
                )

            data = response.read(
                MAX_BYTES + 1
            )

    except CollecteErreur:
        raise

    except (
        urllib.error.URLError,
        OSError,
        TimeoutError
    ) as exc:
        raise CollecteErreur(
            "Collecte impossible"
        ) from exc

    if len(data) > MAX_BYTES:
        raise CollecteErreur(
            "Reponse trop volumineuse"
        )

    try:
        payload = json.loads(
            data.decode("utf-8")
        )
    except (
        ValueError,
        UnicodeError
    ) as exc:
        raise CollecteErreur(
            "JSON invalide"
        ) from exc

    if isinstance(payload, list):
        courses = payload

    elif isinstance(payload, dict):
        courses = payload.get(
            "courses", []
        )

    else:
        raise CollecteErreur(
            "Format JSON non reconnu"
        )

    courses = verifier_courses(
        courses
    )

    return {
        "statut":
            "DONNEES_RECUES_NON_VERIFIEES",
        "courses": courses,
        "source": url,
    }


def diagnostic():
    """Diagnostic sans declencher de collecte."""

    config = configuration()

    return {
        "projet": PROJET,
        "version": VERSION,
        "mode": "LECTURE_SEULE",
        "source_configuree": bool(
            config["url"]
        ),
        "domaines_autorises": sorted(
            config["hosts"]
        ),
        "collecte_automatique": False,
        "pronostics_generes": False,
        "paris_generes": False,
        "figes_modifies": False,
        "archives_modifiees": False,
        "port_production": 8765,
        "horodatage": datetime.now(
            timezone.utc
        ).isoformat(),
    }


if __name__ == "__main__":

    print(json.dumps(
        diagnostic(),
        ensure_ascii=False,
        indent=2
    ))
