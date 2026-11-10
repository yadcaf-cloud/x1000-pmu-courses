"""Collecte PMU V65 - Lecture seule."""
import ipaddress
import json
import os
import socket
import urllib.error
import urllib.request
from urllib.parse import urlsplit

MAX_BYTES = 2_000_000

class CollecteErreur(Exception):
    pass

def verifier_url(url):
    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower()

    autorises = {
        h.strip().lower()
        for h in os.getenv(
            "X1000_ALLOWED_HOSTS", ""
        ).split(",")
        if h.strip()
    }

    if parsed.scheme != "https":
        raise CollecteErreur("HTTPS obligatoire")

    if not host or host not in autorises:
        raise CollecteErreur("Hote non autorise")

    if parsed.username or parsed.password:
        raise CollecteErreur("Identifiants URL interdits")

    if parsed.port not in (None, 443):
        raise CollecteErreur("Port non autorise")

    try:
        addresses = socket.getaddrinfo(
            host, 443, type=socket.SOCK_STREAM
        )
        if not addresses:
            raise CollecteErreur("DNS indisponible")
        for item in addresses:
            ip = ipaddress.ip_address(item[4][0])
            if not ip.is_global:
                raise CollecteErreur(
                    "Adresse IP non publique"
                )
    except socket.gaierror as exc:
        raise CollecteErreur(
            "Resolution DNS impossible"
        ) from exc

class SansRedirection(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, url):
        raise CollecteErreur(
            "Redirection interdite"
        )

def collecter():
    url = os.getenv("X1000_SOURCE_URL", "").strip()

    if not url:
        return {
            "statut": "SOURCE_NON_CONFIGUREE",
            "courses": [],
            "source": None,
        }

    verifier_url(url)

    opener = urllib.request.build_opener(
        SansRedirection()
    )

    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "X1000-PMU-COURSES-V65"
        }
    )

    try:
        with opener.open(
            request, timeout=10
        ) as response:
            data = response.read(MAX_BYTES + 1)
    except (urllib.error.URLError, OSError) as exc:
        raise CollecteErreur(
            "Collecte impossible"
        ) from exc

    if len(data) > MAX_BYTES:
        raise CollecteErreur(
            "Reponse trop volumineuse"
        )

    try:
        payload = json.loads(data)
    except (ValueError, UnicodeError) as exc:
        raise CollecteErreur(
            "JSON invalide"
        ) from exc

    if isinstance(payload, list):
        courses = payload
    elif isinstance(payload, dict):
        courses = payload.get("courses", [])
    else:
        raise CollecteErreur("Format inconnu")

    if not isinstance(courses, list):
        raise CollecteErreur(
            "Liste des courses invalide"
        )

    return {
        "statut": "DONNEES_RECUES_NON_VERIFIEES",
        "courses": courses,
        "source": url,
    }

if __name__ == "__main__":
    print(json.dumps(
        collecter(),
        ensure_ascii=False,
        indent=2
    ))
