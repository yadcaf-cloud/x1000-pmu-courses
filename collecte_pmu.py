#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
X1000 PMU COURSES V67
COLLECTE HTTPS CONTROLEE - LECTURE SEULE

Compatible avec api.py V67.

GARANTIES :
- Aucune source active par defaut.
- HTTPS obligatoire.
- Domaines explicitement autorises.
- IP publiques uniquement.
- Connexion liee a une IP DNS validee.
- Verification TLS du domaine original.
- Redirections interdites.
- Aucun proxy implicite.
- Taille de reponse limitee.
- Validation stricte du JSON.
- Diagnostic HTTP sans exposer les secrets.
- Aucun pronostic, pari ou FIGE.
- Aucune ecriture dans les archives.
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


VERSION = "V67"
PROJET = "X1000 PMU COURSES"

MAX_BYTES = 2_000_000
TIMEOUT = 10

PORT_PRODUCTION = 8765

MAX_COURSES = 10000

HOST_PATTERN = re.compile(
    r"^[a-z0-9-]+(?:\.[a-z0-9-]+)+$"
)


class CollecteErreur(Exception):
    """Erreur de collecte controlee."""

    def __init__(
        self,
        message,
        http_status=None,
        code="COLLECTE_ERREUR"
    ):
        super().__init__(message)
        self.http_status = http_status
        self.code = code


def configuration():
    """
    Configuration exclusivement par
    variables d'environnement.
    """

    url = os.getenv(
        "X1000_SOURCE_URL", ""
    ).strip()

    hosts = set()

    for value in os.getenv(
        "X1000_ALLOWED_HOSTS", ""
    ).split(","):

        host = value.strip().lower()

        if not host:
            continue

        if (
            host.endswith(".")
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
                code="CONFIGURATION_INVALIDE"
            )

        hosts.add(host)

    return {
        "url": url,
        "hosts": hosts,
        "active": bool(url and hosts),
    }


def verifier_url(url, hosts=None):
    """
    Valider l'URL sans connexion reseau.

    Le DNS est resolu separement et
    la connexion utilise ensuite une
    adresse IP explicitement validee.
    """

    if not isinstance(url, str):
        raise CollecteErreur(
            "URL invalide",
            code="URL_INVALIDE"
        )

    if not url or any(
        ord(c) < 33 or ord(c) == 127
        for c in url
    ):
        raise CollecteErreur(
            "URL invalide",
            code="URL_INVALIDE"
        )

    try:
        parsed = urlsplit(url)
        host = parsed.hostname
        port = parsed.port
    except ValueError as exc:
        raise CollecteErreur(
            "Adresse URL invalide",
            code="URL_INVALIDE"
        ) from exc

    if (
        parsed.scheme != "https"
        or not host
        or parsed.username is not None
        or parsed.password is not None
        or port not in (None, 443)
        or parsed.fragment
    ):
        raise CollecteErreur(
            "Destination HTTPS invalide",
            code="URL_INVALIDE"
        )

    # Refuser les variantes ambigues
    # de l'autorite URL.
    if (
        not HOST_PATTERN.fullmatch(host)
        or host != host.lower()
        or host.endswith(".")
    ):
        raise CollecteErreur(
            "Nom de domaine invalide",
            code="URL_INVALIDE"
        )

    if hosts is None:
        hosts = configuration()["hosts"]

    if host not in hosts:
        raise CollecteErreur(
            "Domaine non autorise",
            code="DOMAINE_INTERDIT"
        )

    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise CollecteErreur(
            "Adresse IP directe interdite",
            code="IP_INTERDITE"
        )

    path = parsed.path or "/"

    if not path.startswith("/"):
        raise CollecteErreur(
            "Chemin URL invalide",
            code="URL_INVALIDE"
        )

    target = path

    if parsed.query:
        target += "?" + parsed.query

    return {
        "host": host,
        "port": 443,
        "target": target,
    }


def resoudre_ips_publiques(host):
    """
    Resoudre le DNS et refuser toute
    adresse non globalement routable.
    """

    try:
        addresses = socket.getaddrinfo(
            host,
            443,
            family=socket.AF_UNSPEC,
            type=socket.SOCK_STREAM,
            proto=socket.IPPROTO_TCP
        )
    except socket.gaierror as exc:
        raise CollecteErreur(
            "Resolution DNS impossible",
            code="DNS_ERREUR"
        ) from exc

    if not addresses:
        raise CollecteErreur(
            "Aucune adresse DNS",
            code="DNS_VIDE"
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
                code="DNS_INVALIDE"
            ) from exc

        if not ip.is_global:
            raise CollecteErreur(
                "Adresse DNS non publique",
                code="DNS_NON_PUBLIC"
            )

        value = str(ip)

        if value not in ips:
            ips.append(value)

    return ips


class ConnexionHTTPSControlee(
    http.client.HTTPSConnection
):
    """
    HTTPS avec IP epinglee pour la
    connexion TCP.

    Le nom original reste utilise
    pour SNI et validation du
    certificat TLS.
    """

    def __init__(
        self,
        host,
        ip,
        timeout=TIMEOUT
    ):
        context = ssl.create_default_context()

        super().__init__(
            host=host,
            port=443,
            timeout=timeout,
            context=context
        )

        self.ip_validee = ip

    def connect(self):
        """
        Ne jamais refaire une resolution
        DNS implicite du domaine original.
        """

        raw_socket = socket.create_connection(
            (
                self.ip_validee,
                443
            ),
            timeout=self.timeout
        )

        try:
            self.sock = self._context.wrap_socket(
                raw_socket,
                server_hostname=self.host
            )
        except BaseException:
            raw_socket.close()
            raise


def verifier_courses(courses):
    """
    Verification structurelle seulement.

    Ne constitue pas une validation
    officielle des donnees sportives.
    """

    if not isinstance(courses, list):
        raise CollecteErreur(
            "Liste des courses invalide",
            code="COURSES_INVALIDES"
        )

    if len(courses) > MAX_COURSES:
        raise CollecteErreur(
            "Nombre de courses excessif",
            code="COURSES_TROP_NOMBREUSES"
        )

    for index, course in enumerate(courses):

        if not isinstance(course, dict):
            raise CollecteErreur(
                "Course invalide a l'index "
                + str(index),
                code="COURSE_INVALIDE"
            )

    return courses


def extraire_courses(payload):
    """
    Formats acceptes :
    - liste JSON de courses
    - objet JSON avec cle 'courses'

    Aucun autre format n'est suppose.
    """

    if isinstance(payload, list):
        return verifier_courses(payload)

    if isinstance(payload, dict):

        if "courses" not in payload:
            raise CollecteErreur(
                "Cle courses absente",
                code="FORMAT_JSON_INCONNU"
            )

        return verifier_courses(
            payload["courses"]
        )

    raise CollecteErreur(
        "Structure JSON non reconnue",
        code="FORMAT_JSON_INCONNU"
    )


def requete_https(url, hosts):
    """
    Une seule requete GET.

    Pas de redirection.
    Pas de cookie.
    Pas de proxy.
    Pas de reessai automatique.
    """

    destination = verifier_url(
        url,
        hosts
    )

    host = destination["host"]

    ips = resoudre_ips_publiques(host)

    # Choisir une IP issue de la
    # resolution validee.
    # Aucun nouveau DNS pendant
    # la connexion TCP.
    ip = ips[0]

    connexion = ConnexionHTTPSControlee(
        host=host,
        ip=ip,
        timeout=TIMEOUT
    )

    try:
        connexion.request(
            "GET",
            destination["target"],
            headers={
                "Accept": "application/json",
                "User-Agent":
                    "X1000-PMU-COURSES-V67",
                "Connection": "close",
            }
        )

        response = connexion.getresponse()

        status = response.status

        if status != 200:

            if 300 <= status < 400:
                raise CollecteErreur(
                    "Redirection HTTP interdite",
                    http_status=status,
                    code="REDIRECTION_INTERDITE"
                )

            raise CollecteErreur(
                "Erreur HTTP de la source",
                http_status=status,
                code="SOURCE_HTTP_ERREUR"
            )

        content_type = (
            response.getheader(
                "Content-Type", ""
            ) or ""
        ).lower()

        if (
            "application/json" not in content_type
            and "+json" not in content_type
        ):
            raise CollecteErreur(
                "Reponse non JSON",
                code="CONTENT_TYPE_INVALIDE"
            )

        taille = response.getheader(
            "Content-Length"
        )

        if taille is not None:
            try:
                taille_int = int(taille)
            except ValueError as exc:
                raise CollecteErreur(
                    "Content-Length invalide",
                    code="TAILLE_INVALIDE"
                ) from exc

            if (
                taille_int < 0
                or taille_int > MAX_BYTES
            ):
                raise CollecteErreur(
                    "Reponse trop volumineuse",
                    code="TAILLE_DEPASSEE"
                )

        data = response.read(
            MAX_BYTES + 1
        )

        if len(data) > MAX_BYTES:
            raise CollecteErreur(
                "Reponse trop volumineuse",
                code="TAILLE_DEPASSEE"
            )

        return data

    except CollecteErreur:
        raise

    except (
        OSError,
        TimeoutError,
        ssl.SSLError,
        http.client.HTTPException
    ) as exc:
        raise CollecteErreur(
            "Connexion HTTPS impossible",
            code="CONNEXION_ERREUR"
        ) from exc

    finally:
        connexion.close()


def collecter():
    """
    Fonction compatible avec
    api.py V66 et V67.

    Retour :
    {
      "statut": ...,
      "courses": [...],
      "source": ...
    }

    Aucun fichier n'est ecrit.
    """

    config = configuration()

    if not config["active"]:
        return {
            "statut": "SOURCE_NON_CONFIGUREE",
            "courses": [],
            "source": None,
        }

    url = config["url"]

    # Les parametres HTTP 400
    # ne sont pas inventes.
    # L'URL doit etre configuree
    # avec les parametres reels
    # exiges par la source.
    data = requete_https(
        url,
        config["hosts"]
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
            "JSON invalide",
            code="JSON_INVALIDE"
        ) from exc

    courses = extraire_courses(
        payload
    )

    # Eviter de renvoyer une URL
    # susceptible de contenir
    # des parametres sensibles.
    host = verifier_url(
        url,
        config["hosts"]
    )["host"]

    return {
        "statut":
            "DONNEES_RECUES_NON_VERIFIEES",
        "courses": courses,
        "source": host,
    }


def diagnostic():
    """
    Diagnostic local sans collecte
    et sans connexion reseau.
    """

    config = configuration()

    return {
        "projet": PROJET,
        "version": VERSION,
        "mode": "LECTURE_SEULE",
        "source_configuree": bool(
            config["url"]
        ),
        "configuration_active":
            config["active"],
        "domaines_autorises": sorted(
            config["hosts"]
        ),
        "collecte_automatique": False,
        "pronostics_generes": False,
        "paris_generes": False,
        "figes_modifies": False,
        "archives_modifiees": False,
        "port_production":
            PORT_PRODUCTION,
        "horodatage": datetime.now(
            timezone.utc
        ).isoformat(),
    }


if __name__ == "__main__":
    print(
        json.dumps(
            diagnostic(),
            ensure_ascii=False,
            indent=2
        )
    )
