
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
X1000 PMU COURSES V70
MOTEURS HIPPIQUES M1 A M5

M1 : Statistiques et performances
M2 : Rythme et strategie
M3 : Aptitudes et entourage
M4 : Forme recente et informations tardives
M5 : Analyse critique et outsiders

SECURITE :
- Donnees fournies uniquement
- Aucune collecte reseau
- Aucun fichier ecrit
- Aucun pronostic invente
- Aucun pari automatique
- Aucun FIGE
- Aucun commit, push ou deploiement

Les indicateurs numeriques attendus sont
des notes normalisees de 0 a 100,
preparees et verifiees en amont.

Aucune conversion arbitraire de chronos,
cotes ou performances brutes.
"""

from datetime import datetime, timezone
import math


VERSION = "V70"
PROJET = "X1000 PMU COURSES"

ROLES = {
    "M1": "Statistiques et performances",
    "M2": "Rythme et strategie de course",
    "M3": "Cheval, jockey, terrain et parcours",
    "M4": "Forme recente et informations tardives",
    "M5": "Analyse critique et valeurs cachees",
}

# Chaque moteur possede ses propres
# indicateurs et ponderations.
#
# Ces poids sont experimentaux.
# Ils ne constituent pas un modele
# statistiquement valide.

CRITERES = {
    "M1": {
        "performance": 0.30,
        "regularite": 0.25,
        "distance": 0.20,
        "chrono": 0.15,
        "opposition": 0.10,
    },
    "M2": {
        "rythme": 0.30,
        "placement": 0.25,
        "tactique": 0.25,
        "scenario": 0.20,
    },
    "M3": {
        "aptitude_terrain": 0.25,
        "aptitude_parcours": 0.25,
        "jockey": 0.20,
        "entraineur": 0.15,
        "aptitude_distance": 0.15,
    },
    "M4": {
        "forme_recente": 0.35,
        "condition": 0.25,
        "ferrure": 0.20,
        "informations_recentes": 0.20,
    },
    "M5": {
        "valeur_cachee": 0.30,
        "potentiel_outsider": 0.25,
        "contre_favori": 0.20,
        "rapport_valeur_cote": 0.25,
    },
}


def maintenant():
    return datetime.now(
        timezone.utc
    ).isoformat()


def numero_valide(numero):
    return (
        isinstance(numero, int)
        and not isinstance(numero, bool)
        and numero > 0
    )


def verifier_course(course):
    """
    Verifier les conditions minimales.

    Cette fonction conserve le contrat
    historique : (bool, raison).
    """

    if not isinstance(course, dict):
        return False, "Course invalide"

    if not isinstance(
        course.get("id"), str
    ) or not course["id"].strip():
        return False, "Identifiant absent"

    if not isinstance(
        course.get("hippodrome"), str
    ) or not course["hippodrome"].strip():
        return False, "Hippodrome absent"

    partants = course.get("partants")

    if not isinstance(partants, list):
        return False, "Partants invalides"

    if not partants:
        return False, "Aucun partant"

    numeros = set()

    for partant in partants:
        if not isinstance(partant, dict):
            return False, "Partant invalide"

        numero = partant.get("numero")

        if not numero_valide(numero):
            return False, "Numero invalide"

        if numero in numeros:
            return False, "Numero duplique"

        numeros.add(numero)

        # Un statut absent ne signifie
        # jamais que le cheval est actif.
        if not isinstance(
            partant.get("non_partant"),
            bool
        ):
            return False, (
                "Statut non-partant non verifie"
            )

    actifs = [
        p for p in partants
        if p["non_partant"] is False
    ]

    if len(actifs) < 5:
        return False, (
            "Moins de cinq partants actifs"
        )

    return True, "OK"


def verifier_note(valeur):
    """
    Note normalisee entre 0 et 100.
    """

    return (
        isinstance(valeur, (int, float))
        and not isinstance(valeur, bool)
        and math.isfinite(valeur)
        and 0 <= valeur <= 100
    )


def verifier_indicateurs(
    partant,
    criteres
):
    """
    Exiger tous les indicateurs du
    moteur concerne.
    """

    indicateurs = partant.get(
        "indicateurs"
    )

    if not isinstance(indicateurs, dict):
        return None

    valeurs = {}

    for nom in criteres:
        valeur = indicateurs.get(nom)

        if not verifier_note(valeur):
            return None

        valeurs[nom] = float(valeur)

    return valeurs


def calculer_score(
    indicateurs,
    criteres
):
    """
    Somme ponderee des notes.
    """

    return sum(
        indicateurs[nom] * poids
        for nom, poids in criteres.items()
    )


class Moteur:
    """
    Moteur independant.

    Aucun stockage et aucun effet
    de bord volontaire.
    """

    def __init__(self, nom):
        if nom not in ROLES:
            raise ValueError(
                "Moteur inconnu"
            )

        self.nom = nom
        self.role = ROLES[nom]
        self.criteres = CRITERES[nom]

    def resultat_attente(
        self,
        course,
        statut,
        raison
    ):
        return {
            "moteur": self.nom,
            "role": self.role,
            "version": VERSION,
            "course_id": (
                course.get("id")
                if isinstance(course, dict)
                else None
            ),
            "statut": statut,
            "raison": raison,
            "classement": [],
            "analyse": None,
            "pari": None,
            "fige": False,
            "horodatage": maintenant(),
        }

    def analyser(self, course):
        """
        Produire un classement seulement
        avec les indicateurs complets
        de ce moteur.
        """

        valide, raison = verifier_course(
            course
        )

        if not valide:
            return self.resultat_attente(
                course,
                "DONNEES_INSUFFISANTES",
                raison
            )

        # Provenance et verification
        # obligatoires pour toute
        # proposition de classement.
        #
        # Ce drapeau doit etre fourni
        # par un validateur de donnees
        # fiable, pas par une simple
        # collecte HTTP.
        if (
            course.get(
                "donnees_verifiees"
            ) is not True
        ):
            return self.resultat_attente(
                course,
                "DONNEES_NON_VERIFIEES",
                "Validation des donnees absente"
            )

        actifs = [
            p for p in course["partants"]
            if p["non_partant"] is False
        ]

        scores = []

        for partant in actifs:
            indicateurs = (
                verifier_indicateurs(
                    partant,
                    self.criteres
                )
            )

            if indicateurs is None:
                continue

            score = calculer_score(
                indicateurs,
                self.criteres
            )

            scores.append({
                "numero": partant["numero"],
                "score": score,
                "indicateurs": indicateurs,
            })

        if len(scores) < 5:
            return self.resultat_attente(
                course,
                "INDICATEURS_INSUFFISANTS",
                (
                    "Moins de cinq chevaux "
                    "avec indicateurs complets"
                )
            )

        scores.sort(
            key=lambda item: (
                -item["score"],
                item["numero"]
            )
        )

        selection = scores[:5]

        classement = [
            item["numero"]
            for item in selection
        ]

        analyse = (
            "Classement experimental "
            f"{self.nom} selon "
            "les indicateurs normalises "
            "disponibles. "
            "Aucune probabilite de "
            "victoire estimee."
        )

        return {
            "moteur": self.nom,
            "role": self.role,
            "version": VERSION,
            "course_id": course["id"],
            "statut": "ANALYSE_VALIDEE",
            "raison": (
                "Indicateurs complets "
                "et donnee declaree verifiee"
            ),
            "classement": classement,
            "analyse": analyse,
            "scores": [
                {
                    "numero": item["numero"],
                    "score": round(
                        item["score"], 4
                    ),
                }
                for item in selection
            ],
            "criteres": dict(
                self.criteres
            ),
            "pari": None,
            "fige": False,
            "horodatage": maintenant(),
        }


M1 = Moteur("M1")
M2 = Moteur("M2")
M3 = Moteur("M3")
M4 = Moteur("M4")
M5 = Moteur("M5")

MOTEURS = (
    M1,
    M2,
    M3,
    M4,
    M5,
)


def analyser_tous(course):
    """
    Execution independante des
    cinq moteurs.

    Aucune coordination implicite.
    """
    return [
        moteur.analyser(course)
        for moteur in MOTEURS
    ]


def diagnostic():
    """
    Controle structurel local.
    Aucun appel reseau.
    """

    noms = [
        moteur.nom
        for moteur in MOTEURS
    ]

    return {
        "projet": PROJET,
        "version": VERSION,
        "moteurs": noms,
        "roles": dict(ROLES),
        "nombre": len(MOTEURS),
        "identites_uniques": (
            len(set(noms)) == 5
        ),
        "collecte_reseau": False,
        "ecriture_archives": False,
        "fige_automatique": False,
        "pari_automatique": False,
        "modele_statistique_valide": False,
    }


if __name__ == "__main__":
    import json

    rapport = diagnostic()

    assert rapport["nombre"] == 5
    assert rapport["identites_uniques"]

    print(
        json.dumps(
            rapport,
            ensure_ascii=False,
            indent=2
        )
    )
