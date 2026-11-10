"""X1000 PMU COURSES V65 - Moteurs M1 a M5."""
from datetime import datetime, timezone

ROLES = {
    "M1": "Statistiques et performances",
    "M2": "Rythme et strategie de course",
    "M3": "Cheval, jockey, terrain et parcours",
    "M4": "Forme recente et informations tardives",
    "M5": "Analyse critique et valeurs cachees",
}

def verifier_course(course):
    if not isinstance(course, dict):
        return False, "Course invalide"
    if not course.get("id"):
        return False, "Identifiant absent"
    if not course.get("hippodrome"):
        return False, "Hippodrome absent"
    if not isinstance(course.get("partants"), list):
        return False, "Partants non verifies"
    if not course["partants"]:
        return False, "Aucun partant"
    return True, "OK"

class Moteur:
    def __init__(self, nom):
        if nom not in ROLES:
            raise ValueError("Moteur inconnu")
        self.nom = nom
        self.role = ROLES[nom]

    def analyser(self, course):
        valide, raison = verifier_course(course)
        return {
            "moteur": self.nom,
            "role": self.role,
            "course_id": (
                course.get("id")
                if isinstance(course, dict) else None
            ),
            "statut": (
                "EN_ATTENTE_MODELE"
                if valide else "DONNEES_INSUFFISANTES"
            ),
            "raison": (
                "Algorithme non encore valide"
                if valide else raison
            ),
            "classement": [],
            "analyse": None,
            "pari": None,
            "fige": False,
            "horodatage": datetime.now(
                timezone.utc
            ).isoformat(),
        }

M1 = Moteur("M1")
M2 = Moteur("M2")
M3 = Moteur("M3")
M4 = Moteur("M4")
M5 = Moteur("M5")

MOTEURS = (M1, M2, M3, M4, M5)

def analyser_tous(course):
    return [m.analyser(course) for m in MOTEURS]

if __name__ == "__main__":
    assert len(MOTEURS) == 5
    assert len({m.nom for m in MOTEURS}) == 5
    print("M1-M5 : interfaces initiales OK")
