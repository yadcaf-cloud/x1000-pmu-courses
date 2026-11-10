"""X1000 PMU COURSES V66 — Compatibilité M1 à M5.

Réutilise les moteurs V65 existants.
Aucun pronostic, pari ou FIGÉ artificiel.
Aucune écriture dans les archives.
"""

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


def verifier_installation():
    noms = [m.nom for m in MOTEURS]

    return {
        "projet": "X1000 PMU COURSES",
        "version": "V66",
        "moteurs_installes": len(MOTEURS),
        "moteurs_uniques": len(set(noms)) == 5,
        "noms": noms,
        "algorithmes_valides": False,
        "pronostics_generes": False,
        "figes_modifies": False,
    }


if __name__ == "__main__":
    import json

    rapport = verifier_installation()

    assert rapport["moteurs_installes"] == 5
    assert rapport["moteurs_uniques"]

    print(json.dumps(
        rapport,
        indent=2,
        ensure_ascii=False
    ))
