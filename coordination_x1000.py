"""X1000 PMU COURSES V66 — Coordination centrale.

M1 à M5 indépendants.
Validation des classements.
Aucun pari ni FIGÉ automatique.
Aucune écriture dans les archives.
"""

from datetime import datetime, timezone
from moteurs import MOTEURS


def verifier_classement(resultat, course):
    """Valide cinq numéros distincts de partants actifs."""

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
        isinstance(n, bool) or not isinstance(n, int)
        for n in classement
    ):
        return False

    if len(set(classement)) != 5:
        return False

    partants = course.get("partants", [])

    numeros = {
        p.get("numero")
        for p in partants
        if isinstance(p, dict)
        and p.get("non_partant") is False
        and isinstance(p.get("numero"), int)
        and not isinstance(p.get("numero"), bool)
    }

    return all(n in numeros for n in classement)


def coordonner(course):
    """Consulte chaque moteur sans fabriquer de résultat."""

    if not isinstance(course, dict):
        raise ValueError("Course invalide")

    details = []
    valides = []

    for moteur in MOTEURS:
        try:
            resultat = moteur.analyser(course)

            if verifier_classement(resultat, course):
                valides.append(resultat)

            details.append(resultat)

        except Exception as exc:
            details.append({
                "moteur": moteur.nom,
                "statut": "ERREUR_MOTEUR",
                "erreur_type": type(exc).__name__,
                "classement": [],
                "pari": None,
                "fige": False,
            })

    return {
        "moteur": "X1000",
        "version": "V66",
        "course_id": course.get("id"),
        "statut": (
            "PRET_POUR_ARBITRAGE"
            if valides
            else "EN_ATTENTE_ANALYSES"
        ),
        "moteurs_consultes": len(details),
        "moteurs_valides": len(valides),
        "classement": [],
        "analyse": None,
        "pari": None,
        "fige": False,
        "details": details,
        "horodatage": datetime.now(
            timezone.utc
        ).isoformat(),
    }


if __name__ == "__main__":
    course_test = {
        "id": "TEST-V66",
        "hippodrome": "TEST",
        "partants": [
            {"numero": i, "non_partant": False}
            for i in range(1, 7)
        ],
    }

    resultat = coordonner(course_test)

    assert resultat["moteurs_consultes"] == 5
    assert resultat["classement"] == []
    assert resultat["pari"] is None
    assert resultat["fige"] is False

    print("Coordination X1000 V66 : tests OK")
