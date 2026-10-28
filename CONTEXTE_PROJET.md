# Contexte du projet — Inventaire et valorisation de bibliothèque

Vue d'ensemble du projet et de son architecture logicielle. Les règles durables et décisions fonctionnelles sont centralisées dans [`INVARIANTS_PROJET.md`](INVARIANTS_PROJET.md) ; l'avancement réel et les tâches restantes sont dans [`EN_COURS.md`](EN_COURS.md).

## Objectif

Constituer un inventaire fiable d'environ 100 à 200 documents imprimés (livres, magazines, guides, etc.), puis estimer leur valeur et choisir entre vente à l'unité, vente en lot, conservation ou don. La fiabilité de l'inventaire est prioritaire.

## Chaîne de traitement

1. Les photos et les notes sont fournies par l'utilisateur.
2. L'IA multimodale lit le texte visible, décrit l'illustration et évalue sommairement l'état apparent, sans recherche Internet ni connaissances externes sur les livres.
3. Le script contrôle les réponses, met à jour l'état persistant et conserve les provenances.
4. Dans une étape distincte, le script peut lancer les recherches bibliographiques dans les catalogues activés ; les cas ambigus restent à examiner.
5. Dans une étape ultérieure, l'IA analyse les informations d'état et les données de marché pour proposer une valorisation et une stratégie.

Le détail des responsabilités, des critères d'identification, des dates bibliographiques et des règles de prudence est défini uniquement dans `INVARIANTS_PROJET.md`.

## Architecture et fichiers

| Fichier ou dossier | Rôle |
|---|---|
| `creer_bibliotheque.py` | Script principal : suivi des sources, analyse IA, recherches bibliographiques et exports |
| `inventaire.json` | État persistant cumulatif ; local, exclu de Git |
| `structure_inventaire.json` | Contrat de la réponse IA expérimentale ; distinct de la base persistante |
| `inventaire.csv` | Export des fiches pour consultation |
| `notes.txt` | Notes cumulatives fournies par l'utilisateur ; local, exclu de Git |
| `photos/` | Photos de travail ; local, exclu de Git |
| `photos.txt` | CSV des précisions par photo au format `photo;ref;precision` ; local, exclu de Git |
| `photos_tests/` | Éventuels exemples de développement, jamais des sources d'inventaire réel |
| `tests/` | Tests automatisés, à exécuter sur des données temporaires |
| `annexes/test_stabilite_etat.py` | Outil exploratoire d'appels API répétés, hors du traitement de production |
| `README.md` | Présentation courte et utilisation |
| `INVARIANTS_PROJET.md` | Source de vérité des règles et décisions durables |
| `EN_COURS.md` | État de la branche, versions, contrôles effectués et travaux restant à faire |

## Collaboration et évolution

Avant tout changement, lire `INVARIANTS_PROJET.md`, examiner les fichiers réellement présents sur la branche indiquée et consulter `EN_COURS.md`. Travailler sur la branche explicitement indiquée par l'utilisateur ; ne pas créer de branche sans demande. Si `main` est indiquée, y travailler directement. Ne pas fusionner une autre branche sans accord explicite. Les évolutions, résultats de tests et limites vérifiées sont consignés dans `EN_COURS.md`.
