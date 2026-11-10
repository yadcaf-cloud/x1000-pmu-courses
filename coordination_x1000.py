"""Coordination centrale X1000 V65."""
from moteurs import analyser_tous

def coordonner(course):
    resultats = analyser_tous(course)

    valides = [
        r for r in resultats
        if r["statut"] == "ANALYSE_VALIDEE"
        and len(r["classement"]) == 5
    ]

    # Ne jamais fabriquer un classement.
    # Aucun arbitrage sans moteur valide.
    return {
        "moteur": "X1000",
        "course_id": course.get("id"),
        "statut": (
            "PRET_POUR_ARBITRAGE"
            if valides else "EN_ATTENTE_ANALYSES"
        ),
        "moteurs_consultes": len(resultats),
        "moteurs_valides": len(valides),
        "classement": [],
        "analyse": None,
        "pari": None,
        "fige": False,
        "details": resultats,
    }
