# Inventaire et valorisation de bibliothèque

Projet personnel visant à inventorier et identifier environ 100 à 200 documents imprimés (livres, magazines, guides, collections, etc.), puis à estimer leur valeur et à choisir entre conservation, vente à l'unité, vente en lot ou don.

**Priorité actuelle : constituer un inventaire fiable. La valorisation viendra ensuite.**

## Principe et fonctionnement

- **Utilisateur** : fournit les photos, les notes d’inventaire et les précisions propres aux photos dans `photos.txt` ; arbitre les ambiguïtés qui ne peuvent pas être résolues de façon fiable.
- **IA d'analyse visuelle** : lit le texte visible, décrit l'illustration et évalue prudemment l'état apparent ; son appel API n'utilise ni outil Web ni recherche externe.
- **Script Python** : orchestre les traitements, contrôle les réponses, conserve l'état persistant et la provenance des informations, puis pilote les recherches bibliographiques.
- **IA de valorisation (étape ultérieure)** : examinera les informations disponibles et les données de marché pour proposer une estimation et une stratégie. Elle n'est pas activée dans cette évolution.

Une photo peut montrer zéro, un ou plusieurs documents. Un même document peut apparaître sur plusieurs photos ; une photo complémentaire peut aussi préciser la fiche d'un document déjà connu. Les photos et notes fournies par l'utilisateur sont les seules sources autorisées pour créer un document dans l'inventaire.

Le traitement est itératif : selon les résultats et les incertitudes, le script peut indiquer quelles photos ou informations complémentaires seraient utiles. Après l'analyse visuelle, le script peut lancer séparément ses recherches bibliographiques dans les catalogues activés ; ces recherches ne font pas partie de l'appel IA avec la photo. La valorisation reste hors périmètre.

## Fichiers et dossiers

| Élément | Rôle |
|---|---|
| `creer_bibliotheque.py` | Script de production : analyse des sources, gestion de l'inventaire, recherches bibliographiques et exports |
| `inventaire.json` | État persistant cumulatif ; fichier local exclu de Git |
| `structure_inventaire.json` | Contrat 1.1 de la réponse IA visuelle ; distinct de la base de production |
| `notes.txt` | Notes cumulatives de l'utilisateur au format `document_id;clé;valeur`, appliquées par le script et non transmises à l'IA |
| `photos/` | Photos de travail ; dossier local exclu de Git |
| `photos.txt` | CSV facultatif des précisions propres à chaque photo, au format `photo;ref;precision` ; fichier local exclu de Git |
| `photos_tests/` | Éventuelles images d'exemple ou de test, qui ne doivent jamais alimenter l'inventaire réel |
| `annexes/test_api_photo_haute_definition.py` | Outil de test conservé en annexe, hors du traitement de production |
| `annexes/test_stabilite_etat.py` | Mesure exploratoire de la stabilité des défauts sur 3 à 5 photos, hors production |
| `inventaire.csv` | Export cumulatif détaillé des fiches, consultable notamment dans LibreOffice Calc |
| `inventaire_réduit.csv` | Export compact de consultation, avec les colonnes `id`, `type`, `titre`, `auteurs`, `editeur`, `annee_impression`, `annee_edition`, `date_depot_legal`, `isbn`, `identif`, `mentions`, `etat` et `manque` ; séparateur `|` |
| `tests/` | Tests automatisés, à exécuter sur des données temporaires |

## Utilisation

Lancer le script depuis l'environnement Python du projet :

```bash
python3 creer_bibliotheque.py
```

Dans `notes.txt`, la clé `statut` permet de forcer le statut de progression d’un document, par exemple `document_0009;statut;9. Abandonné`. Les valeurs admises sont `1. A identifier`, `2. Identifié`, `3. Etat à préciser`, `4. Etat connu`, `5. Valorisé` et `9. Abandonné`. La valeur `auto` retire le forçage et rétablit le statut calculé automatiquement.

Le fichier facultatif `photos.txt` utilise un CSV séparé par des points-virgules, avec l’en-tête `photo;ref;precision`. Le nom de photo doit être exact. La colonne `precision` est transmise à l’IA comme information fiable fournie par l’utilisateur. Si `ref` vaut `oui`, l’IA reçoit aussi la consigne d’associer explicitement aux identifiants connus les observations qui les concernent ; si `ref` vaut `non`, cette consigne n’est pas ajoutée. Modifier `ref` relance l’analyse si une précision non vide est présente. Les fichiers `Photo_x.txt` dans `photos/` ne sont plus pris en compte.

L'analyse par IA nécessite la variable d'environnement `OPENAI_API_KEY` et le paquet Python `openai`. L'option `--no-ai` permet de mettre à jour le suivi des photos sans appeler l'API. En développement, la sortie brute du dernier appel est sauvegardée dans `derniere_reponse_ia.txt` (fichier local exclu de Git), y compris si elle ne constitue pas un JSON valide. L'option `--last-reponse` rejoue ce fichier sans nouvel appel API ; elle exige exactement une photo en attente afin de ne pas appliquer la même réponse à plusieurs photos. La limite de sortie est fixée à 12 000 tokens. Les autres options sont décrites dans le script.

En fin d'exécution, le bloc `RÉSUMÉ À COPIER / PARTAGER` permet de transmettre un état synthétique pour poursuivre l'examen du projet.

**Attention :** ne supprimez pas les fichiers de sortie pour repartir d'un état vierge sans avoir préalablement sauvegardé les données utiles. Les essais doivent utiliser des copies temporaires, jamais le JSON de production.

## État du projet

- **V0.5** : validée et fusionnée dans `main`.
- **Script sur `main`** : V6.2.4 (22/10/2026).
- **Schéma JSON persistant sur `main`** : 0.22.
- **Contrat d'analyse IA sur `main`** : 1.1.
- **Branche de base V0.6** : `v0.6.x` ; branche d'essai de cette évolution : `v0.6.x-analyse-ia-amelioree_2`.
- La branche temporaire `v0.6.x-recherche-web-document` a été fusionnée dans la branche d'essai et n'est plus requise.
- **Validation** : compilation, tests automatisés et appels API réels restent à exécuter ; aucun résultat n'est présumé. Le passage au contrat 0.9 rend les photos analysées avec un contrat antérieur éligibles à une nouvelle analyse API, potentiellement facturée.

L'état détaillé, les évolutions préparées et les contrôles restant à effectuer sont consignés dans `EN_COURS.md`. Les règles durables et décisions de référence figurent dans `INVARIANTS_PROJET.md`.

## Règles de développement

- Lire `INVARIANTS_PROJET.md`, `EN_COURS.md` et examiner les fichiers concernés avant toute évolution.
- Travailler sur la branche indiquée par l'utilisateur ; ne pas créer de branche sans demande explicite. Si `main` est indiquée, y travailler directement.
- Ne jamais fusionner sans accord explicite de l'utilisateur.
- Préserver les données validées et conserver la provenance des informations.
- Distinguer observations, informations externes, déductions et incertitudes ; ne jamais inventer de donnée bibliographique ou de défaut non observable.
- Tester sur des données temporaires, sans écriture dans le JSON de production.
- Distinguer la version du programme de celle du schéma JSON.

## Documentation

- `INVARIANTS_PROJET.md` : source de vérité des règles durables et des décisions fonctionnelles.
- `CONTEXTE_PROJET.md` : vue d'ensemble et architecture.
- `EN_COURS.md` : état d'avancement, versions, vérifications et travaux restant à traiter.
- `README.md` : présentation et utilisation du projet.


## Diagnostic des appels IA (V6.1.20)

L'appel IA avec la photo utilise le modèle configuré `gpt-6.1-sol` et un schéma JSON strict, sans outil Web déclaré ni `tool_choice`. Le contrat IA 1.1 sépare les champs bibliographiques (éditeur, édition, ISBN, collection et dates), décrit l’illustration et conserve les autres textes. Le schéma persistant 0.22 conserve aussi la description de l’illustration et les autres textes visibles dans les fiches et le CSV. Les sources d’information exportées en CSV conservent la provenance par champ (confiance, origine et statut de lecture). Le prompt n’a pas été modifié dans cette évolution. Les photos analysées avec un contrat antérieur restent marquées pour réanalyse.

`gpt-6.1-sol` est documenté officiellement pour l'API Responses ; l'accès de la clé API du projet reste à confirmer par un appel réel. Après un appel API, `derniere_reponse_ia.txt` conserve dans des sections distinctes les métadonnées de la requête (modèle, limite de sortie, nom de la photo, paramètres), le prompt final complet, les métadonnées de réponse disponibles (statut, identifiant et consommation de tokens), puis la sortie brute. Le diagnostic indique explicitement qu'aucun outil externe n'a été fourni à cet appel. `--last-reponse` ne relit que la section de sortie brute ; les anciens fichiers composés uniquement de JSON restent acceptés.
