#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
X1000 PMU COURSES V75
COLLECTE PMU HTTPS SECURISEE

Compatible avec api.py V74.

OBJECTIFS
- HTTPS uniquement.
- Liste blanche stricte des domaines.
- DNS public verifie.
- Connexion TCP sur IP validee.
- Validation TLS du domaine original.
- Aucun proxy implicite.
- Aucune redirection.
- Taille JSON limitee.
- Diagnostic HTTP 400 sans fuite de secrets.
- Verification structurelle des courses.
- Aucune confiance dans les declarations client.

GARANTIES
- Aucune collecte au demarrage.
- Aucune collecte programmee.
- Aucune ecriture de fichier.
- Aucun pronostic invente.
- Aucun pari automatique.
- Aucun FIGE.
- Aucune modification des archives.
- Aucun commit, push ou deploiement.
"""

import http.client
import ipaddress
import json
import os
import re
import socket
import ssl

from datetime import datetime, timezone
from urllib.parse import urlsplit


PROJET = "X1000 PMU COURSES"
VERSION = "V75"

PORT_LOCAL = 8765

MAX_BYTES = 2_000_000
MAX_COURSES = 10000
MAX_PARTANTS = 40

TIMEOUT = 10

HOST_PATTERN = re.compile(
    r"^[a-z0-9-]+(?:\.[a-z0-9-]+)+$"
)

PARAMETRES_SENSIBLES = {
    "token",
    "key",
    "api_key",
    "apikey",
    "secret",
    "password",
    "authorization",
    "access_token",
}


class CollecteErreur(Exception):
    """Erreur controlee de collecte."""

    def __init__(
        self,
        message,
        http_status=None,
        code="COLLECTE_ERREUR",
    ):
        super().__init__(message)
        self.http_status = http_status
        self.code = code


def maintenant():
    return datetime.now(
        timezone.utc
    ).isoformat()


def configuration():
    """
    Configuration sans connexion reseau.
    """

    url = os.getenv(
        "X1000_SOURCE_URL", ""
    ).strip()

    hosts = set()

    valeurs = os.getenv(
        "X1000_ALLOWED_HOSTS", ""
    )

    for element in valeurs.split(","):
        host = element.strip().lower()

        if not host:
            continue

        if (
            len(host) > 253
            or not HOST_PATTERN.fullmatch(host)
            or any(
                len(label) > 63
                or label.startswith("-")
                or label.endswith("-")
                for label in host.split(".")
            )
        ):
            raise CollecteErreur(
                "Domaine autorise invalide",
                code="CONFIGURATION_INVALIDE",
            )

        hosts.add(host)

    return {
        "url": url,
        "hosts": hosts,
        "active": bool(url and hosts),
    }


def verifier_url(url, hosts=None):
    """
    Valider l'URL sans effectuer
    de connexion reseau.
    """

    if (
        not isinstance(url, str)
        or not url
        or len(url) > 4096
        or any(
            ord(c) < 33 or ord(c) == 127
            for c in url
        )
    ):
        raise CollecteErreur(
            "URL invalide",
            code="URL_INVALIDE",
        )

    try:
        parsed = urlsplit(url)
        host = parsed.hostname
        port = parsed.port
    except ValueError as exc:
        raise CollecteErreur(
            "URL invalide",
            code="URL_INVALIDE",
        ) from exc

    if (
        parsed.scheme != "https"
        or not host
        or parsed.username is not None
        or parsed.password is not None
        or port not in (None, 443)
        or parsed.fragment
        or "\\" in url
    ):
        raise CollecteErreur(
            "Destination HTTPS invalide",
            code="URL_INVALIDE",
        )

    if (
        len(host) > 253
        or not HOST_PATTERN.fullmatch(host)
        or any(
            len(label) > 63
            or label.startswith("-")
            or label.endswith("-")
            for label in host.split(".")
        )
    ):
        raise CollecteErreur(
            "Domaine invalide",
            code="URL_INVALIDE",
        )

    if hosts is None:
        hosts = configuration()["hosts"]

    if host not in hosts:
        raise CollecteErreur(
            "Domaine non autorise",
            code="DOMAINE_INTERDIT",
        )

    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise CollecteErreur(
            "Adresse IP directe interdite",
            code="IP_INTERDITE",
        )

    target = parsed.path or "/"

    if parsed.query:
        target += "?" + parsed.query

    if (
        not target.startswith("/")
        or target.startswith("//")
        or any(
            ord(c) < 32 or ord(c) == 127
            for c in target
        )
    ):
        raise CollecteErreur(
            "Chemin URL invalide",
            code="URL_INVALIDE",
        )

    return {
        "host": host,
        "port": 443,
        "target": target,
    }


def resoudre_ips_publiques(host):
    """
    Refuser toute resolution DNS
    contenant une adresse non publique.
    """

    try:
        addresses = socket.getaddrinfo(
            host,
            443,
            family=socket.AF_UNSPEC,
            type=socket.SOCK_STREAM,
            proto=socket.IPPROTO_TCP,
        )
    except socket.gaierror as exc:
        raise CollecteErreur(
            "Resolution DNS impossible",
            code="DNS_ERREUR",
        ) from exc

    if not addresses:
        raise CollecteErreur(
            "Resolution DNS vide",
            code="DNS_VIDE",
        )

    ips = []

    for item in addresses:
        try:
            ip = ipaddress.ip_address(
                item[4][0]
            )
        except ValueError as exc:
            raise CollecteErreur(
                "Adresse DNS invalide",
                code="DNS_INVALIDE",
            ) from exc

        if not ip.is_global:
            raise CollecteErreur(
                "Adresse DNS non publique",
                code="DNS_NON_PUBLIC",
            )

        value = str(ip)

        if value not in ips:
            ips.append(value)

    return ips


class ConnexionHTTPSControlee(
    http.client.HTTPSConnection
):
    """
    Connexion TCP vers une IP
    prealablement validee.

    SNI et verification TLS utilisent
    toujours le domaine original.
    """

    def __init__(
        self,
        host,
        ip,
        timeout=TIMEOUT,
    ):
        context = ssl.create_default_context()

        super().__init__(
            host=host,
            port=443,
            timeout=timeout,
            context=context,
        )

        self.ip_validee = ip

    def connect(self):
        raw_socket = socket.create_connection(
            (self.ip_validee, 443),
            timeout=self.timeout,
        )

        try:
            self.sock = self._context.wrap_socket(
                raw_socket,
                server_hostname=self.host,
            )
        except BaseException:
            raw_socket.close()
            raise


def verifier_json(data):
    """
    Parser exclusivement un JSON
    de taille limitee.
    """

    if not isinstance(
        data, (bytes, bytearray)
    ):
        raise CollecteErreur(
            "Reponse invalide",
            code="REPONSE_INVALIDE",
        )

    if len(data) > MAX_BYTES:
        raise CollecteErreur(
            "Reponse trop volumineuse",
            code="TAILLE_DEPASSEE",
        )

    try:
        texte = data.decode("utf-8")
        payload = json.loads(
            texte,
            parse_constant=lambda value: (
                _refuser_constante(value)
            ),
        )
    except (
        UnicodeError,
        ValueError,
        TypeError,
    ) as exc:
        raise CollecteErreur(
            "JSON invalide",
            code="JSON_INVALIDE",
        ) from exc

    return payload


def _refuser_constante(value):
    raise ValueError(
        "Constante JSON non standard"
    )


def verifier_courses(courses):
    """
    Controle structurel.

    Ne certifie jamais les
    informations sportives.
    """

    if not isinstance(courses, list):
        raise CollecteErreur(
            "Liste des courses invalide",
            code="COURSES_INVALIDES",
        )

    if len(courses) > MAX_COURSES:
        raise CollecteErreur(
            "Trop de courses",
            code="COURSES_TROP_NOMBREUSES",
        )

    for index, course in enumerate(courses):
        if not isinstance(course, dict):
            raise CollecteErreur(
                "Course invalide",
                code="COURSE_INVALIDE",
            )

        if "partants" in course:
            partants = course["partants"]

            if not isinstance(partants, list):
                raise CollecteErreur(
                    "Partants invalides",
                    code="PARTANTS_INVALIDES",
                )

            if len(partants) > MAX_PARTANTS:
                raise CollecteErreur(
                    "Trop de partants",
                    code="PARTANTS_TROP_NOMBREUX",
                )

            for partant in partants:
                if not isinstance(
                    partant, dict
                ):
                    raise CollecteErreur(
                        "Partant invalide",
                        code="PARTANT_INVALIDE",
                    )

        # Aucun drapeau de verification
        # transmis par la source n'est
        # considere comme une preuve.
        #
        # Les champs bruts sont conserves.
        # L'API indique explicitement
        # donnees_verifiees=False.

    return courses


def extraire_courses(payload):
    """
    Formats reconnus :
    - liste de courses
    - objet {"courses": [...]}

    Aucun format PMU non documente
    n'est devine.
    """

    if isinstance(payload, list):
        return verifier_courses(payload)

    if isinstance(payload, dict):
        if "courses" not in payload:
            raise CollecteErreur(
                "Cle courses absente",
                code="FORMAT_JSON_INCONNU",
            )

        return verifier_courses(
            payload["courses"]
        )

    raise CollecteErreur(
        "Format JSON inconnu",
        code="FORMAT_JSON_INCONNU",
    )


def diagnostic_http(status):
    """
    Diagnostic sans afficher l'URL,
    les parametres ni les secrets.
    """

    if status == 400:
        return {
            "code": "SOURCE_HTTP_400",
            "message": (
                "La source refuse la requete. "
                "Verifier le chemin, la date, "
                "les parametres obligatoires "
                "et le format attendu."
            ),
            "correction_automatique": False,
        }

    if status in (401, 403):
        return {
            "code": "SOURCE_ACCES_REFUSE",
            "message": (
                "Acces refuse par la source."
            ),
            "correction_automatique": False,
        }

    if status == 404:
        return {
            "code": "SOURCE_HTTP_404",
            "message": (
                "Ressource introuvable."
            ),
            "correction_automatique": False,
        }

    if status == 429:
        return {
            "code": "SOURCE_HTTP_429",
            "message": (
                "Limite de requetes atteinte."
            ),
            "correction_automatique": False,
        }

    if 300 <= status < 400:
        return {
            "code": "REDIRECTION_INTERDITE",
            "message": (
                "Redirection HTTPS refusee."
            ),
            "correction_automatique": False,
        }

    return {
        "code": "SOURCE_HTTP_ERREUR",
        "message": (
            "Erreur HTTP de la source."
        ),
        "correction_automatique": False,
    }


def requete_https(url, hosts):
    """
    Une seule requete GET explicite.

    Aucun retry automatique.
    Aucune redirection.
    Aucun proxy.
    Aucun cookie.
    """

    destination = verifier_url(
        url, hosts
    )

    host = destination["host"]
    ips = resoudre_ips_publiques(host)

    connexion = ConnexionHTTPSControlee(
        host=host,
        ip=ips[0],
        timeout=TIMEOUT,
    )

    try:
        connexion.request(
            "GET",
            destination["target"],
            headers={
                "Accept": "application/json",
                "User-Agent":
                    "X1000-PMU-COURSES-V75",
                "Connection": "close",
            },
        )

        response = connexion.getresponse()
        status = response.status

        if status != 200:
            info = diagnostic_http(status)

            raise CollecteErreur(
                info["message"],
                http_status=status,
                code=info["code"],
            )

        content_type = (
            response.getheader(
                "Content-Type", ""
            ) or ""
        ).lower()

        media_type = content_type.split(
            ";", 1
        )[0].strip()

        if not (
            media_type == "application/json"
            or media_type.endswith("+json")
        ):
            raise CollecteErreur(
                "Content-Type non JSON",
                code="CONTENT_TYPE_INVALIDE",
            )

        longueur = response.getheader(
            "Content-Length"
        )

        if longueur is not None:
            try:
                taille = int(longueur)
            except ValueError as exc:
                raise CollecteErreur(
                    "Content-Length invalide",
                    code="TAILLE_INVALIDE",
                ) from exc

            if (
                taille < 0
                or taille > MAX_BYTES
            ):
                raise CollecteErreur(
                    "Taille interdite",
                    code="TAILLE_DEPASSEE",
                )

        data = response.read(
            MAX_BYTES + 1
        )

        if len(data) > MAX_BYTES:
            raise CollecteErreur(
                "Reponse trop volumineuse",
                code="TAILLE_DEPASSEE",
            )

        return data

    except CollecteErreur:
        raise

    except (
        OSError,
        TimeoutError,
        ssl.SSLError,
        http.client.HTTPException,
    ) as exc:
        raise CollecteErreur(
            "Connexion HTTPS impossible",
            code="CONNEXION_ERREUR",
        ) from exc

    finally:
        connexion.close()


def collecter():
    """
    Collecte explicite en lecture seule.

    Retour compatible avec api.py :
    {
        "statut": ...,
        "courses": [...],
        "source": ...
    }

    Ne lance aucun moteur.
    Ne modifie aucun fichier.
    """

    config = configuration()

    if not config["active"]:
        return {
            "statut": "SOURCE_NON_CONFIGUREE",
            "courses": [],
            "source": None,
        }

    url = config["url"]

    destination = verifier_url(
        url,
        config["hosts"],
    )

    data = requete_https(
        url,
        config["hosts"],
    )

    payload = verifier_json(data)
    courses = extraire_courses(payload)

    return {
        "statut":
            "DONNEES_RECUES_NON_VERIFIEES",
        "courses": courses,
        "source": destination["host"],
    }


def diagnostic():
    """
    Aucun appel reseau.
    Aucun secret affiche.
    """

    try:
        config = configuration()

        source_configuree = bool(
            config["url"]
        )

        active = config["active"]

        domaines = sorted(
            config["hosts"]
        )

        configuration_valide = True

    except CollecteErreur:
        source_configuree = False
        active = False
        domaines = []
        configuration_valide = False

    return {
        "projet": PROJET,
        "version": VERSION,
        "mode": "LECTURE_SEULE",
        "source_configuree":
            source_configuree,
        "configuration_active": active,
        "configuration_valide":
            configuration_valide,
        "domaines_autorises":
            domaines,
        "collecte_automatique": False,
        "source_authentifiee": False,
        "donnees_verifiees": False,
        "pronostics_generes": False,
        "figes_modifies": False,
        "archives_modifiees": False,
        "port_local_preserve":
            PORT_LOCAL,
        "horodatage": maintenant(),
    }


def tests_isoles():
    """
    Tests sans reseau ni ecriture.
    """

    # Source non autorisee.
    try:
        verifier_url(
            "http://example.org/api",
            {"example.org"},
        )
    except CollecteErreur:
        pass
    else:
        raise AssertionError(
            "HTTP non securise accepte"
        )

    # Domaine interdit.
    try:
        verifier_url(
            "https://example.org/api",
            {"autre.example.org"},
        )
    except CollecteErreur:
        pass
    else:
        raise AssertionError(
            "Domaine interdit accepte"
        )

    # Format valide.
    resultat = extraire_courses(
        {
            "courses": [
                {
                    "id": "TEST-V75",
                    "hippodrome": "TEST",
                    "partants": [],
                }
            ]
        }
    )

    assert len(resultat) == 1

    # Format invalide.
    try:
        extraire_courses(
            {"reunions": []}
        )
    except CollecteErreur as exc:
        assert (
            exc.code
            == "FORMAT_JSON_INCONNU"
        )
    else:
        raise AssertionError(
            "Format inconnu accepte"
        )

    # Diagnostic HTTP 400.
    info = diagnostic_http(400)

    assert info["code"] == (
        "SOURCE_HTTP_400"
    )

    assert (
        info["correction_automatique"]
        is False
    )

    # Aucun NaN JSON accepte.
    try:
        verifier_json(
            b'{"courses":[NaN]}'
        )
    except CollecteErreur:
        pass
    else:
        raise AssertionError(
            "NaN accepte"
        )

    return {
        "statut": "TESTS_OK",
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
            indent=2,
        )
    )
