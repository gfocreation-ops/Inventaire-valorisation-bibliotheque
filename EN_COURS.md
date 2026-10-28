# En cours

*Dernière mise à jour : 19/10/2026.*

## Évolution V6.2.0 — Export CSV réduit — 19/10/2026

- Crée automatiquement `inventaire_réduit.csv` en complément de `inventaire.csv`, avec les colonnes compactes demandées et le séparateur `|`.
- L’export compact présente l’identification, les mentions visibles, l’état enregistré et les champs bibliographiques manquants ; il est régénéré à chaque exécution.
- Le JSON persistant reste la source de vérité : schéma 0.22 et contrat IA 1.1 inchangés.
- Tests ajoutés pour le format et la génération des deux CSV ; compilation et tests automatisés restent à exécuter.

## Évolution V6.1.33 — Allègement du résumé terminal — 19/10/2026

- Supprime l’affichage des listes « Photos ciblées utiles » et « Prochaine action utile (priorité à l’identification) ».
- Les autres lignes du bilan, les données persistantes, les exports et le traitement restent inchangés.

## Évolution V6.1.32 — Réessais Flex temporisés puis repli standard — 19/10/2026

- L’analyse photo tente d’abord `service_tier="flex"` ; si l’erreur porte le code `flex_unavailable`, deux réessais Flex sont effectués après 30 s puis 60 s.
- Après trois échecs Flex au total, le script appelle le traitement standard. Les autres erreurs API ne déclenchent ni réessai applicatif ni repli.
- Les réessais automatiques du SDK sont désactivés uniquement pour les appels Flex afin de maîtriser les délais ; le client du repli standard conserve ses réglages habituels.
- Le diagnostic indique le niveau utilisé. Schéma JSON 0.22 et contrat IA 1.1 inchangés. Tests ciblés ajoutés ; compilation et tests non exécutés dans cet environnement.

## Évolution V6.1.27 — Traitement Flex et protection contre les erreurs temporaires — 17/10/2026

- Active le niveau `service_tier="flex"` pour l’appel Responses API d’analyse photo ; schéma JSON persistant 0.22 et contrat IA 1.1 inchangés.
- En cas d’échec d’appel, le script conserve l’analyse enregistrée, note l’erreur et place la photo en `analysis_error`, statut repris lors du lancement suivant.
- Ajoute un test de non-régression simulant un échec API puis une nouvelle tentative réussie. L’exécution des tests reste à confirmer.

## Évolution V6.1.26 — Présentation synthétique de l’état dans le CSV — 16/10/2026

- Ajoute `etat_general` immédiatement après `isbn`, avec uniquement l’appréciation courte.
- Renomme l’ancienne colonne structurée en `etat_general_details`, sans modifier le contenu de l’état dans le JSON.
- Le schéma JSON persistant reste en 0.22 et le contrat IA en 1.1 ; tests adaptés, exécution locale à confirmer.

## Évolution V6.1.25 — Inventaire neuf et suppression des migrations — 16/10/2026

- Les noms `annee_edition`, `annee_impression`, `description_illustration` et `etat_general` sont conservés entre la réponse IA, la détection, la fiche persistante et l’export CSV.
- Le script n’effectue plus de migration de schéma : seuls les inventaires au schéma courant 0.22 sont acceptés. En cas d’ancien schéma, il demande de repartir d’un inventaire neuf.
- Le contrat IA reste en version 1.1 ; le fichier `structure_inventaire.json` utilise déjà les noms canoniques.
- La version du script passe à V6.1.25. Les tests restent à exécuter ; aucun résultat n’est présumé.

## Évolution V6.1.23 — Conservation des champs IA et de leur provenance — 15/10/2026

- La fiche documentaire conserve désormais la description de l’illustration et les autres textes visibles.
- Le CSV exporte ces deux champs et une colonne JSON `sources_information`, qui conserve la provenance détaillée par champ, dont confiance, origine et statut de lecture.
- La provenance des champs bibliographiques est conservée même lorsque la valeur est non visible ; les observations d’une photo complémentaire restent liées à leur photo. Une réanalyse de la même photo actualise aussi ses métadonnées de provenance.
- Le schéma persistant passe de 0.20 à 0.21 ; le contrat IA reste en version 1.1.
- Ajout d’un test de bout en bout analyse → fiche persistante → CSV, avec contrôle des champs visuels, de la provenance et de l’état.
- Le prompt n’a pas été modifié. Compilation et tests automatisés non exécutés ici.


## Évolution V6.1.21 — Cardinalité des documents par photo — 15/10/2026

- Le prompt indique explicitement qu’une photo peut montrer zéro, un ou plusieurs documents.
- L’invariant rappelle qu’un document persistant doit avoir au moins une source utilisateur (photo et/ou note).
- Le contrat 1.1 et le script acceptaient déjà zéro à plusieurs documents ; ajout d’un test ciblé pour l’analyse vide. Test ajouté, non exécuté ici.

## Correction de cardinalité photo ↔ documents — 15/10/2026

- Clarifie l’invariant : une photo peut produire zéro à plusieurs documents détectés ; un document persistant doit toujours avoir au moins une source utilisateur (photo et/ou note).
- Le script et le contrat 1.1 autorisaient déjà zéro à plusieurs documents par photo ; le conflit était dans l’invariant fonctionnel. Le prompt est désormais explicite. Le contrat et le schéma persistant ne sont pas modifiés.
- Ajoute un test vérifiant qu’une analyse vide est acceptée et enregistrée sans document détecté. Test ajouté, non exécuté ici.

## Évolution V6.1.20 — Contrat bibliographique IA structuré

- Le contrat de réponse IA 1.1 sépare l’éditeur, l’édition, l’ISBN, la collection, l’année d’édition, l’année d’impression et la date de dépôt légal.
- Le champ de description de l’illustration et les autres textes sont distincts des champs bibliographiques structurés.
- Le sous-titre est désormais conservé dans l’inventaire ; le schéma persistant passe à 0.20.
- Le prompt n’a pas été modifié. Il reste à préciser explicitement la lecture des pages intérieures ; `INVARIANTS_PROJET.md` limite encore l’analyse au texte de couverture.
- Compilation et tests automatisés non exécutés ici ; aucun appel API réel n’a été lancé.

## Évolution V6.1.19 — Commentaires personnels dans notes.txt

- La clé réservée `ignore` accepte un commentaire personnel par document.
- Le commentaire est conservé dans l’historique de lecture des notes, sans modifier la fiche du document, son statut d’identification ou ses sources d’information.
- Ajout d’un test ciblé ; l’exécution des tests reste à confirmer.

## Branche et versions

- Branche de base : `v0.6.x`.
- Branche d'essai : `v0.6.x-analyse-ia-amelioree_2`, basée sur `v0.6.x-analyse-ia-amelioree` (historique de travail distinct). La présente évolution V6.1.19 a été intégrée directement à `main` à la demande explicite de l’utilisateur.
- Script sur `main` : V6.2.0 du 19/10/2026.
- Schéma JSON persistant : 0.22.
- Contrat d'analyse IA : version 1.1.

## Évolution V6.1.16 — Réglage de détail image automatique

- Remplace `detail=high` par `detail=auto` dans l’appel image de l’API Responses.
- Le diagnostic `derniere_reponse_ia.txt` consigne le nouveau réglage.
- Aucun test automatisé ni appel API réel n’a été exécuté ici.

## Évolution V6.1.15 — Initialisation de la liste ISBN

- Les nouvelles fiches initialisent `identification.isbns_notice_ancrage` à une liste vide avant toute recherche bibliographique.

## Évolution V6.1.14 — Conservation des ISBN de la notice d’ancrage

- Conserve tous les ISBN valides de la notice d’édition d’ancrage dans `identification.isbns_notice_ancrage`, dans la provenance et dans une colonne CSV dédiée.
- Le champ ISBN unique n’est rempli automatiquement que lorsqu’un seul ISBN fiable est disponible ; plusieurs ISBN ne sont pas concaténés ni départagés arbitrairement.
- `notice_ancrage.isbn_present_dans_notice` vaut `null` lorsqu’aucun ISBN n’a été recherché ; la liste `isbns_notice` indique les ISBN réellement relevés.
- Le schéma JSON persistant passe à 0.19. Les tests ciblés ont été ajoutés, mais restent à exécuter.

## Évolution V6.1.13 — Réanalyse des états migrés

- Une fiche dont l'ancienne appréciation a été migrée vers `non_evaluable` peut recevoir le nouveau résultat d'une photo en réanalyse, même si sa base d'état existait déjà.
- Une appréciation valide du nouveau contrat reste protégée des écrasements par une photo ordinaire.

## Évolution V6.1.12 — Finalisation de la simplification de l'état

- Supprime également `etat.defauts` et `etat.informations_non_visibles` du modèle de création des nouvelles fiches.
- Aligne le calcul de progression sur les cinq nouvelles appréciations.
- Version précédente du même lot : V6.1.11, contrat IA 0.9 et schéma persistant 0.18.

## Évolution V6.1.11 — Simplification de l'état visuel et des sorties

- L'état IA contient seulement une appréciation (`tres_bon`, `bon`, `correct`, `mauvais`, `non_evaluable`) et un motif court de 15 mots maximum.
- La fiche reçoit `etat.appreciation` et `etat.observations: [motif]` ; les anciennes listes `etat.defauts` et `etat.informations_non_visibles` sont supprimées.
- Le contrat IA passe à 0.9 et relance l'analyse des photos dont le contrat enregistré est antérieur. Le schéma persistant passe à 0.18 pour retirer les champs d'état devenus obsolètes.
- Les retours à la ligne du titre, du sous-titre et des auteurs sont normalisés en espaces ; ils sont conservés pour l'éditeur seulement.
- Les demandes de photos ciblées sont regroupées par identifiant de document, sans titre ni détail de zone.
- La stabilité de l'état compare désormais uniquement les appréciations. Compilation, tests automatisés et appel API réel restent à exécuter ; aucun résultat n'est présumé.

## Évolution V6.1.10 — Changement du modèle d'analyse IA

- Configure `MODEL = "gpt-6.1-sol"` pour les appels d'analyse des photos.
- `gpt-6.1-sol` est un identifiant officiel documenté pour l'API Responses ; l'accès de la clé API du projet et un appel réel n'ont pas été testés ici.

## Évolution V6.1.9 — Validation prudente des éditions

- La recherche BnF utilise UNIMARCXCHANGE et conserve les ISBN répétés de la zone 010, ainsi que les éditeurs, dates et l’URL de notice.
- Le statut `edition_identifiee` exige une notice d’édition d’ancrage : ISBN équivalent présent dans la notice, ou score éditeur 1.0 sur une notice d’édition unique.
- Une notice Open Library de niveau œuvre ne confirme pas une édition : son année reste dans `premiere_publication_oeuvre` dans l’historique, sans compléter l’année de l’édition ni corriger le titre.
- Les cas probables restent `a_confirmer_par_recherche_bibliographique`; l’absence de l’ISBN recherché dans les identifiants de la notice et les contradictions ISBN sont tracées, affichées dans le rapport et exportées en CSV.
- Les anciennes fiches au statut `edition_identifiee` sans `notice_ancrage` sont rétrogradées à confirmer lors de la normalisation.
- **Tests automatisés, compilation et appels API réels non exécutés ici.**

## Évolution V6.1.8 — Notices classées, état structuré et demandes de photos

- Ajoute `_publisher_score` avec `None` lorsque l'éditeur manque d'un côté ; le meilleur score positif unique départage les notices titre/auteur. Les notices sont classées dans l'historique avec source, URL, score, année et rang ; une année explicitement fournie par note utilisateur peut départager un ex æquo.
- Une notice sans éditeur n'est plus considérée comme une contradiction ; un `ecart_editeur` n'est enregistré que si le score est connu et inférieur à 1, avec son score.
- Remplace l'état libre par un schéma fermé, ajoute `type_document`, conserve les défauts structurés et la portée présumée de la première photo. `non_evaluable` ne fait pas progresser vers « 4. Etat connu ».
- Les nouvelles détections n'extraient plus ISBN ni dates du contrat visuel ; les lecteurs aval restent tolérants aux anciennes données. Les autres textes répétant l'auteur ou l'éditeur sont filtrés.
- Ajoute `identification.demandes_photo`, son affichage dans le bilan et une colonne CSV.
- Ajoute `annexes/test_stabilite_etat.py`, outil distinct lançant 5 passes par photo aux températures par défaut et 0, sans écraser `derniere_reponse_ia.txt` ni écrire dans l'inventaire.
- Le contrat passe de 0.7 à 0.8 et le schéma persistant de 0.15 à 0.16. Les photos analysées avec un ancien contrat sont placées en `pending_analysis` au chargement ; le prochain lancement normal relancera donc des appels API facturés.
- Compilation, tests automatisés et appels API réels non exécutés ici.

## Évolution V6.1.7 — Nettoyage des traces IA Web et contrôle ISBN

- Supprime le champ de compatibilité `identification_web` produit par défaut lors de la conversion d'une réponse IA ; la recherche bibliographique reste exclusivement une étape distincte pilotée par le script.
- Vérifie la clé de contrôle ISBN-10/ISBN-13 avant d'utiliser l'identifiant pour une recherche ou un rapprochement. Un ISBN invalide est conservé comme donnée à vérifier, signalé dans l’historique de recherche et écarté des requêtes ISBN ; la recherche par titre/auteur reste possible.
- N'importe plus automatiquement un ISBN de catalogue si sa clé de contrôle est invalide.
- Ajoute des tests de validité, d'équivalence et de repli vers le titre/auteur. Compilation et tests automatisés non exécutés ici.

## Évolution V6.1.6 — Analyse visuelle recentrée

- Intègre le prompt fourni par l'utilisateur : texte visible, illustration, état apparent prudent.
- L'appel Responses API ne déclare plus `web_search` et ne force plus `tool_choice`.
- Le contrat IA 0.7 limite la réponse à un document principal, ajoute le statut de lecture (`lisible`, `incertain`, `non_visible`) pour le titre, le sous-titre, les auteurs et l'éditeur, et retire les champs de recherche Web, ISBN et dates du contrat de réponse.
- Le schéma JSON persistant passe de 0.13 à 0.14 ; les analyses d'un ancien contrat sont marquées pour réanalyse. Les recherches bibliographiques que le script lance séparément restent distinctes de l'appel IA avec la photo.
- Documentation et tests adaptés. Compilation, tests et appel API réel **non exécutés ici** ; vérifier localement avant validation.

## Historique obsolète (remplacé par V6.1.6) — V6.1.5 : Web Search obligatoire

- Ajoute `tool_choice="required"` à l’appel Responses API : comme Web Search est le seul outil déclaré, l’appel doit utiliser cet outil au lieu de laisser son déclenchement entièrement facultatif.
- Le diagnostic local consigne ce paramètre. Cela ne garantit ni la qualité des résultats ni l’identification correcte de l’édition ; il faudra vérifier la trace et les sources lors du test réel.
- Contrat IA 0.6 et schéma JSON 0.13 inchangés. Aucun appel API ni test n’a été exécuté ici.

## Historique obsolète (remplacé par V6.1.6) — V6.1.4 : Recherche Web exploratoire et retour des requêtes

- Réoriente le prompt : requêtes simples et variantes de titre/auteur, exploration des résultats Web et comparaison des couvertures avant de conclure sur l'édition.
- Distingue l'identification du livre de celle de son édition et maintient une évaluation prudente de la certitude.
- Le contrat IA 0.6 ajoute `identification_web.recherches_effectuees` pour conserver les requêtes réellement lancées et leur résultat, en plus des sources effectivement consultées.
- Le schéma JSON persistant passe à 0.13 et les analyses issues d'un ancien contrat sont marquées pour réanalyse.
- Compilation et tests automatisés à effectuer localement ; aucun test n'est déclaré exécuté ici.

## Évolution V6.1.3 — Prompt et contrat JSON d'analyse photo

- Le prompt distingue les observations de la photo, les informations issues du Web et les déductions.
- Chaque champ de données porte une origine (`photo`, `web`, `photo_et_web`, `deduction`, `non_etablie`) en plus de son niveau de confiance.
- Le contrat distingue une référence bibliographique exacte d'une piste plausible, conserve les parties non observables et prévoit au maximum trois demandes de complément ciblées.
- Les défauts doivent être observables ; les reflets, ombres et zones non visibles ne sont pas considérés comme des défauts ou comme une absence de défaut.
- Le contrat IA passe de 0.4 à 0.5 ; le schéma JSON persistant passe de 0.11 à 0.12. Les analyses réalisées avec un ancien contrat sont marquées pour réanalyse.
- Les tests ont été adaptés, mais ils n'ont pas été exécutés dans cet environnement ; compilation et tests locaux restent nécessaires.

## Évolution V6.1.2 — Journal complet de l'appel IA

- Le fichier de diagnostic conserve le modèle appelé, `max_output_tokens`, le nom de la photo, les paramètres utiles, le prompt final complet et les métadonnées de réponse disponibles, dont l'utilisation des tokens et le statut de fin.
- La sortie brute est délimitée par des marqueurs ; `--last-reponse` extrait cette seule section pour le rejeu.
- Les anciens fichiers qui ne contiennent que la sortie JSON restent compatibles.
- Les tests automatisés n'ont pas été exécutés dans cet environnement ; vérifier localement.

## Évolution V6.1.1 — Sauvegarde et rejeu de la réponse IA

- La sortie texte brute du dernier appel IA est sauvegardée dans `derniere_reponse_ia.txt` avant le décodage JSON, y compris si elle est vide, tronquée ou mal formée.
- Le fichier est local et exclu de Git.
- `--last-reponse` relit ce fichier sans appeler l'API ; le rejeu exige exactement une photo en attente afin d'éviter d'appliquer une réponse à plusieurs photos.
- La limite de sortie est portée à 12 000 tokens après un premier appel ayant consommé 5 804 tokens de sortie sur 6 000.
- Deux tests couvrent la sauvegarde d'une sortie JSON invalide et le rejeu sans clé API.
- Compilation et tests automatisés non exécutés dans cet environnement ; vérification locale requise.

## Historique obsolète (remplacé par V6.1.6) — V6.1.0 : Analyse photo et recherche Web dans le même appel

- L'appel multimodal GPT-4.1-mini active l'outil Web Search dans le même appel que l'analyse de l'image ; la recherche peut être ciblée sur les indices visibles pour identifier aussi les documents anciens, magazines et guides.
- Chaque détection conserve une description visuelle distincte des données bibliographiques.
- Chaque détection conserve une proposition de recherche Web : statut prudent, résumé, titre des sources, URL et apport de chaque source.
- Les pistes Web ne sont pas une validation automatique et ne créent pas seules de fiches document. Les recherches BnF/Open Library/Google Books pilotées par le script restent en place.
- La valorisation, les prix et la stratégie de vente restent hors périmètre de cette évolution.
- Le contrat IA passe de 0.3 à 0.4 ; le schéma JSON persistant passe de 0.10 à 0.11. Les photos analysées avec un ancien contrat sont marquées pour réanalyse.
- Des tests de régression ont été ajoutés pour le schéma, l'activation de Web Search, la conservation des sources et la réanalyse.
- **Compilation et tests automatisés non exécutés dans cet environnement.** Vérifier localement avant de considérer l'évolution comme testée. Les appels API avec Web Search peuvent générer des frais supplémentaires.


## Évolution V6.0.2 — Complément de prompt conditionné par `ref`

- La précision de `photos.txt` est présentée simplement comme une information fiable fournie par l'utilisateur.
- Si `ref=oui`, le prompt ajoute une seconde consigne : associer explicitement aux identifiants connus mentionnés dans la précision les observations qui les concernent et restituer ces identifiants dans `document_id_reference`.
- Si `ref=non` (ou toute valeur différente de `oui`), cette seconde consigne n'est pas ajoutée.
- Si la précision est non vide, une modification de `ref` marque aussi la photo pour une nouvelle analyse, afin que le prompt reflète le nouveau choix.
- Les consignes redondantes sur les identifiants ont été retirées du prompt général. Le schéma JSON persistant reste en `0.10` et le contrat d'analyse IA en `0.3`.
- Tests de régression ajoutés pour vérifier les deux branches du prompt. Compilation et tests automatisés restent à exécuter localement ; aucun résultat n'est présumé.

## Évolution V6.0.1 — Centralisation des précisions par photo

- Schéma JSON persistant porté de `0.9` à `0.10` pour enregistrer le suivi de `photos.txt`, la précision et la valeur `ref` par photo ainsi que l’empreinte de la précision. Le contrat d’analyse IA reste en version `0.3`.
- Les fichiers `Photo_x.txt` dans le dossier `photos/` ne sont plus lus ni suivis.
- Le fichier facultatif `photos.txt` à la racine du projet est lu comme CSV avec l’en-tête `photo;ref;precision`. Le nom de photo doit correspondre exactement à un nom de fichier unique.
- La colonne `precision` est ajoutée au prompt d’analyse de la photo ; la colonne `ref` est validée à titre informatif mais n’a pas encore d’effet fonctionnel.
- V6.0.1 : une modification de la précision d’une photo marquait cette photo pour une nouvelle analyse ; `ref` seul n’avait pas d’effet.
- Les lignes invalides ou ambiguës sont signalées et ignorées ; en cas d’en-tête CSV invalide, les précisions précédemment enregistrées ne sont pas effacées.
- Les tests automatisés ont été adaptés pour couvrir le CSV centralisé et l’ignorance des TXT accolés. Compilation et tests restent à exécuter localement.

## Évolution V6.0.0 — Renommage du script principal

- Le script `inventaire_bibliotheque.py` est renommé `creer_bibliotheque.py`.
- Version du programme portée à `6.0.0` ; la version du schéma JSON reste `0.9` et celle du contrat d'analyse IA reste `0.3`.
- Les références du README, du contexte projet, des commandes de contrôle et de l'import des tests sont mises à jour.
- Aucun changement fonctionnel n'est prévu dans cette évolution.
- Contrôles locaux non exécutés depuis cet environnement ; compilation et tests restent à effectuer dans le dépôt local.

## Évolutions préparées en V0.5.8

- Les notes explicites de l'utilisateur remplacent les valeurs issues de l'IA/photo ; le remplacement est consigné dans les notes persistantes. Si plusieurs notes d'un champ divergent, la dernière ligne du fichier prévaut.
- La séquence littérale `\\n` dans une valeur de `notes.txt` devient un saut de ligne dans le champ enregistré, ce qui permet de conserver les éditeurs multi-lignes.
- La recherche bibliographique ne considère plus une simple concordance titre/auteur comme suffisante pour confirmer une édition.
- Comparaison des ISBN-10 et ISBN-13 équivalents.
- Si un ISBN équivalent concorde avec le titre et l'auteur dans une notice unique, le statut devient `edition_identifiee` et l'année manquante peut être complétée avec provenance bibliographique. Une différence d'éditeur reste signalée.
- Sans preuve suffisante pour lever l'ambiguïté bibliographique, le document reste à l'étape 1 « À identifier » ; aucune demi-étape « édition à confirmer » n'existe.
- Recalcul de la liste des informations absentes à partir des valeurs courantes ; elles sont présentées comme des indices complémentaires, non comme des conditions obligatoires.
- Le bilan distingue les éditions identifiées, les documents identifiés dont l'édition reste à confirmer et les identifications en attente.
- Tests ajoutés pour la priorité des notes, l'éditeur multi-lignes, les ISBN équivalents et l'ambiguïté d'édition.

## Évolutions préparées en V0.5.9

- Ajout d’une colonne `statut` immédiatement après `document_id` dans le CSV, avec les étapes `1. A identifier`, `2. Identifié`, `3. Etat à préciser`, `4. Etat connu`, `5. Valorisé`. L'étape 1 bloque toute progression tant que l'identification n'est pas validée.
- Les recherches sont séquentielles et configurables par trois constantes en tête du script : BnF et Open Library sont activées, Google Books est désactivé par défaut. Les recherches réussies avec une signature inchangée restent mises en cache ; une recherche en erreur n’est pas répétée avant 24 h.
- Le compte rendu privilégie la prochaine action utile pour l’identification au lieu de présenter tous les champs secondaires absents comme obligatoires.
- Renommage du contrat expérimental `inventaire_structure.json` en `structure_inventaire.json`. Le fichier `inventaire.json` reste la base persistante de production.

## Validation restant à effectuer

Les modifications ont été préparées sur la branche dédiée, mais **la compilation et les tests n'ont pas été exécutés dans cet environnement**. Ne pas considérer la V0.5.10 comme validée avant les contrôles locaux.

Dans le dépôt local, sur cette branche, exécuter :

```bash
python3 -m py_compile creer_bibliotheque.py tests/test_regressions_v055.py
python3 -m unittest discover -s tests -v
```

Puis tester avec une copie temporaire du JSON et un `notes.txt` de test, notamment :
- `document_0001` : ISBN-13 `9782863740538` face à la notice BnF ISBN-10 `2863740539`, sans écraser la mention d'éditeur existante ;
- `document_0002` : éditeur complet `Desclée de Brouwer\\nStock/Laurence Pernoud`, date d'impression `26/04/1990`, sans confondre date d'impression et année de publication ;
- vérification de la provenance et de l'idempotence des notes ;
- export CSV et compte rendu dans LibreOffice Calc.

Aucune modification de `main` ni fusion n'a été effectuée.


## Évolutions préparées en V0.5.10

- Adoption du terme **document** dans le code, les identifiants persistants, les notes, les exports, les messages et la documentation. Les identifiants prennent la forme `document_0001`.
- Statuts de progression préfixés par l'étape : `1. A identifier`, `2. Identifié`, `3. Etat à préciser`, `4. Etat connu`, `5. Valorisé`.
- Schéma JSON porté à 0.9.

**Validation :** compilation, tests automatisés et essai sur une copie d'un inventaire existant restent à exécuter localement ; aucun résultat de test n'est présumé.


## Évolutions préparées en V0.5.11

- Progression strictement séquentielle : aucune information d'état ni de valorisation ne permet de dépasser l'étape 1 si l'identification n'est pas validée.
- Trois constantes en tête du script pilotent séparément les recherches BnF, Open Library et Google Books ; Google Books est désactivé par défaut.
- Une notice BnF peut être départagée parmi plusieurs résultats titre/auteur si l'éditeur concorde de manière unique.
- Tests ciblés ajoutés ; ils restent à exécuter localement.


## Évolutions préparées en V0.5.12

- Si un ISBN est renseigné, la première requête BnF utilise le champ ISBN exact au lieu de dépendre du titre.
- Une notice avec ISBN équivalent et auteur concordant peut être retenue malgré une variation du titre ; l'éditeur est conservé comme contrôle de cohérence et tout écart est signalé.
- Si la recherche par ISBN ne suffit pas, le script revient à la recherche BnF classique par titre/auteur, puis poursuit vers les catalogues complémentaires activés.
- Un test de non-régression couvre le cas réel de « Les Demoiselles de Beaumoereau » avec l'ISBN 9782863740538.
- Compilation, tests automatisés et vérification réelle de la requête BnF restent à exécuter localement ; aucun résultat n'est présumé.


## Évolutions préparées en V0.5.13

- Une recherche Open Library faite par ISBN peut être exploitable même si la notice retournée omet l'ISBN dans son champ d'identifiants.
- L'acceptation de ce cas exige que l'URL de recherche comporte le même ISBN, que l'auteur concorde et que le titre soit suffisamment proche (similarité minimale de 0,85). Les résultats restent enregistrés avec leur URL de recherche et leur notice.
- La stratégie enregistrée dans l'historique est harmonisée avec la clé utilisée pour détecter une recherche déjà effectuée, afin d'éviter de répéter inutilement une recherche réussie.
- Un test de non-régression reprend le cas « Les Demoiselles de Beaumoereau » / ISBN 9782863740538, dont la notice Open Library indique « Les demoiselles de Beaumoreau », Marguerite Gurgand et 1981 sans renvoyer d'ISBN.
- Compilation, tests automatisés et vérification réelle restent à exécuter ; aucun résultat n'est présumé.


## Évolutions préparées en V0.5.14

- La recherche BnF par ISBN utilise le critère documenté `bib.fuzzyISBN`, adapté aux ISBN-10/13 et EAN.
- Une réponse SRU contenant un diagnostic est enregistrée comme erreur de recherche, et non comme preuve d’absence de notice.
- Après une concordance bibliographique forte, une petite différence de titre (similarité normalisée ≥ 0,85) peut être corrigée automatiquement. L’ancienne valeur, la nouvelle, la notice et la date sont conservées dans `sources_information` et dans l’historique de recherche.
- Une correction de titre explicitement fournie par l’utilisateur via une note reste prioritaire. Les différences importantes ne sont pas écrasées et sont signalées.
- Tests de régression ajoutés pour le critère BnF, les diagnostics SRU, la correction du titre « Les demoiselles de Beaumoreau » et la priorité d’une note utilisateur.
- Les tests et la compilation n’ont pas été exécutés dans cet environnement ; ne pas considérer cette version comme validée avant les contrôles locaux.
