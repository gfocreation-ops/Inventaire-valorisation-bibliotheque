# Invariants du projet — Inventaire et valorisation de bibliothèque

Document de référence obligatoire pour toute évolution du code, du JSON, des prompts/contrats IA, des tests ou de la documentation. Il contient les règles durables ; `EN_COURS.md` seul décrit l'état d'avancement et les travaux restant à faire.

## 1. Objectif et étapes

Le projet vise à constituer un inventaire fiable d'environ 100 à 200 livres et autres documents imprimés, puis à les valoriser.

1. **Inventorier et identifier** : décrire les documents observés, constituer les fiches, rechercher les références bibliographiques et établir l'identité du document et, lorsque nécessaire, de son édition.
2. **Valoriser** : à partir de l'inventaire identifié, des informations d'état et des données de marché, estimer la valeur et recommander une stratégie (vente à l'unité, en lot, conservation ou don).

L'identification bibliographique et la valorisation sont deux étapes distinctes. Un document identifié peut encore manquer d'informations sur son état pour être valorisé.

## 2. Rôles et responsabilités

- **Utilisateur** : seule source des photos et notes, arbitre les ambiguïtés qui ne peuvent pas être résolues avec fiabilité.
- **IA d'analyse visuelle** : se limite au texte visible de la couverture, à une description concise de l'illustration et à une évaluation sommaire de l'état apparent. L'appel avec la photo n'utilise ni Internet ni les connaissances générales de l'IA sur les livres. Elle ne décide pas seule de l'état persistant de l'inventaire.
- **Script** : orchestre le traitement, conserve l'état persistant et la provenance, vérifie les identifiants et associations, applique les règles de cohérence, lance les recherches bibliographiques et contrôle l'intégration de leurs résultats.
- **IA de valorisation** : intervient dans la deuxième étape pour estimer les valeurs, évaluer la suffisance des informations d'état et proposer une stratégie de vente. Elle ne doit pas être confondue avec l'IA chargée de lire les photos.

Le script pilote séparément les recherches dans les catalogues bibliographiques et orchestre les appels IA. L'appel IA avec la photo n'effectue aucune recherche Web et ne complète pas les champs par connaissance générale. Les dates, ISBN et autres indices peuvent être exploités par les recherches bibliographiques distinctes du script. Une information déduite ou une notice candidate ne devient pas automatiquement un fait certain.

## 3. Entités, sources et relations

Entités persistantes principales : **documents**, **photos** et **notes**. Les recherches bibliographiques et leurs résultats sont également conservés comme sources externes traçables.

- Un document doit avoir au moins une source fournie par l'utilisateur : photo et/ou note. Aucun document ne peut être créé sur la seule base d'une recherche externe.
- Une photo peut montrer zéro, un ou plusieurs documents. Le cas d'une photo montrant un seul document est possible, jamais une hypothèse par défaut.
- Un même document peut être montré sur plusieurs photos ; chaque photo peut apporter des informations différentes.
- Deux objets physiques distincts ne doivent pas être fusionnés au seul motif que leur titre, auteur ou ISBN est identique.
- Une photo complémentaire peut concerner un document connu sans créer une nouvelle fiche.
- Les associations photo ↔ document doivent être réciproques et validées avant persistance.
- `photos.txt` est un CSV facultatif à la racine du projet, avec l’en-tête `photo;ref;precision`. `photo` doit correspondre exactement au nom du fichier photo, `ref` vaut `oui` ou `non` et `precision` fournit une information fiable de contexte transmise à l’IA pour cette photo. La précision est toujours introduite comme une information fiable fournie par l’utilisateur ; seule la valeur `ref=oui` ajoute la consigne d’associer explicitement les observations pertinentes aux identifiants de documents connus mentionnés dans cette précision. Les fichiers TXT accolés aux photos ne sont pas lus.
- `notes.txt` est un fichier cumulatif de faits/corrections fournis par l'utilisateur au format CSV `document_id;clé;valeur`. Il n'est jamais transmis à l'IA. Une note ne concerne qu'un document déjà identifié. Les notes concordantes peuvent compléter un champ vide. Une information explicitement fournie/corrigée par l'utilisateur est prioritaire sur une proposition de l'IA ou une observation photo ; le remplacement est tracé dans l'historique des notes. Si plusieurs notes utilisateur du même champ se contredisent, la dernière ligne de `notes.txt` prévaut et le remplacement est signalé. Une contradiction avec une notice bibliographique externe reste visible et ne remplace pas la valeur utilisateur. La clé réservée `ignore` permet de conserver un commentaire personnel dans l'historique de lecture des notes ; elle ne modifie pas la fiche du document et n'est pas ajoutée à ses sources d'information.

## 4. Observation, déduction, incertitude et provenance

- Conserver la provenance des informations et les relations entre documents, photos, notes et notices bibliographiques.
- Distinguer une valeur lue directement, une valeur issue d'une source externe, une déduction, une estimation et une information incertaine.
- Pour l'analyse visuelle, le titre, le sous-titre, les auteurs et l'éditeur doivent porter un statut de lecture parmi `lisible`, `incertain` et `non_visible`. Les informations bibliographiques non visibles ne sont pas complétées par déduction ou par connaissance externe.
- Une photo peut produire zéro, un ou plusieurs documents détectés. L’IA doit décrire tous les documents qu’elle peut identifier suffisamment sur la photo, sans imposer de document principal ni de cardinalité maximale. Une liste vide est valide si aucun document ne peut être analysé de manière suffisante.
- « Non visible » ne signifie pas « absent ». Une partie non observée ne peut être déclarée en bon état ni exempte de défaut.
- Ne jamais inventer une information bibliographique ni affirmer un défaut non observable.
- Un résultat IA invalide ou une erreur d'appel ne remplace pas la dernière analyse valide ; l'échec doit rester traçable et pouvoir être retenté.
- Les contradictions sont signalées et conservées pour arbitrage. Les données validées ne sont pas écrasées automatiquement par une nouvelle observation contradictoire.
- Fiabilité, traçabilité et prudence priment sur l'automatisation.

## 5. Identification bibliographique

### Objectif et critère de fin

Le but est de pouvoir répondre à « quel document ? » et, si nécessaire, « quelle édition/version ? ». Il n'est pas obligatoire que tous les champs de la fiche soient renseignés.

Le statut d'identification ne doit pas être calculé en exigeant systématiquement titre, auteurs, éditeur et date : selon le document, le titre et l'auteur peuvent suffire, tandis que d'autres documents exigent des indices supplémentaires. Le critère est l'absence d'ambiguïté bibliographique pertinente, appuyée par les sources disponibles. Si plusieurs références plausibles restent en concurrence, l'identification reste à confirmer et une demande ciblée peut être proposée.

Les champs secondaires enrichissent la fiche et peuvent aider à départager des éditions ; leur absence ne signifie pas automatiquement que le document est non identifié.

### Champs et dates

- `titre`, `auteurs`, `editeur`, `collection`, `annee_edition`, `edition`, `isbn`, `annee_impression`, `date_depot_legal` et autres éléments distinctifs sont des indices complémentaires ; aucun champ isolé n'est une condition universelle.
- Le champ canonique `annee_edition` correspond à **l'année de publication de l'édition**. Ne pas le confondre avec l'année d'impression ou de dépôt légal.
- `annee_impression` conserve l'année ou la date d'impression/réimpression explicitement donnée par une source.
- `date_depot_legal` conserve séparément la mention/date de dépôt légal.
- Une date de dépôt légal peut aider à rechercher ou départager une référence, mais ne prouve pas à elle seule l'année de publication ni `annee_impression`.
- La source et la nature de la date doivent rester traçables. Une déduction ne doit pas être présentée comme une mention observée.
- L'ISBN n'existe pas pour toutes les publications. Lorsqu'il existe, il doit être recherché et renseigné si une source fiable le confirme. Distinguer « inconnu/non retrouvé » de « publication sans ISBN ». L'absence d'ISBN ne bloque pas l'identification.
- Avant d'utiliser un ISBN pour rechercher, rapprocher ou importer un identifiant de catalogue, vérifier son format et sa clé de contrôle selon l'algorithme ISBN-10 ou ISBN-13. Un ISBN invalide reste une valeur à vérifier : ne pas le corriger automatiquement ni l'utiliser comme preuve ; poursuivre si possible la recherche par titre/auteur et conserver un diagnostic traçable.

### Recherche bibliographique

Le script lance les recherches à partir des métadonnées disponibles et conserve les requêtes, notices, sources, dates de recherche et erreurs. Les notices sont des candidates, pas des faits validés par défaut. Les champs de la fiche ne peuvent être complétés automatiquement que lorsque la concordance est suffisamment fiable et non contradictoire ; sinon, garder les candidats et demander un arbitrage. Les résultats de recherche doivent permettre de préciser l'identité/édition, pas seulement de remplir arbitrairement des champs vides. L'analyse visuelle ne produit aucune piste Web. Les recherches bibliographiques externes sont lancées séparément par le script ; une notice candidate ne valide ni ne remplace automatiquement les champs de la fiche.

Pour attribuer le statut `edition_identifiee`, une notice d’ancrage au niveau de l’édition est obligatoire. Elle doit concorder sur le titre et l’auteur, et fournir soit un ISBN-10/13 équivalent explicitement présent dans ses identifiants, soit un score éditeur de 1,0 sur une notice d’édition unique. Une notice au niveau de l’œuvre, même obtenue par une requête ISBN, ne confirme pas l’édition. Son année éventuelle est conservée dans l’historique comme `premiere_publication_oeuvre`, sans compléter l’année de l’édition. Les contradictions ISBN sont consignées séparément ; aucun titre, ISBN ou année d’édition ne peut être importé à partir d’une simple notice d’œuvre ou d’une notice sans ancrage. Pour la BnF, exploiter UNIMARCXCHANGE et conserver tous les ISBN répétés de la zone 010, afin de ne pas confondre un ISBN non restitué en Dublin Core avec un ISBN réellement absent de la notice. Tous les ISBN valides de la notice d’ancrage sont conservés dans `identification.isbns_notice_ancrage` et l’export CSV, sans concaténer plusieurs identifiants dans le champ ISBN unique. Si aucune recherche d’ISBN n’a été faite, `notice_ancrage.isbn_present_dans_notice` vaut `null`, pas `false`.

## 6. État matériel et valorisation

L'état décrit uniquement l'aspect global de la face observée. Ne jamais affirmer un défaut non observable ni déduire l'état d'une partie non visible.

- L'analyse visuelle restitue l'état global apparent dans un schéma fermé : `tres_bon`, `bon`, `correct`, `mauvais` ou `non_evaluable`, accompagné d'un motif d'une phrase de 15 mots maximum.
- Le motif ne liste pas les défauts. La fiche conserve l'état dans `etat_general` : l'appréciation dans `etat_general.appreciation`, le motif de l'IA dans `etat_general.observations` sous forme de liste contenant au plus une phrase, et les métadonnées de portée et de confiance. Les champs `etat_general.defauts` et `etat_general.informations_non_visibles` ne sont pas conservés.
- L'appréciation porte uniquement sur la face visible. L'âge apparent doit être pris en compte ; l'usure normale du temps ne justifie pas à elle seule une baisse de note. Les micro-marques, la texture du papier, les reflets et les ombres ne sont pas signalés.
- La portée de l'état initial est tracée par `etat_general.base = "premiere_photo_presumee_representative"` : c'est une présomption sur l'ensemble du document, pas un fait établi. `non_evaluable` ne permet pas de passer à l'étape « état connu ».

La fin de l'identification ne dépend pas de la complétude de l'état. À l'étape de valorisation, l'IA examine si les informations disponibles sont suffisantes ; si nécessaire, elle demande des photos complémentaires ciblées (par exemple intérieur, reliure, page de titre, annotations ou défaut particulier).

La valorisation doit distinguer prix de ventes réalisées, prix demandés et estimation. Elle tient compte de l'édition identifiée, de l'état comparable, de la demande, des frais et du temps de vente. La stratégie unitaire ou par lot se décide à l'échelle de l'inventaire suffisamment constitué.

## 7. Fichiers et versions

- Le JSON est l’état persistant cumulatif. Le projet repart d’un inventaire neuf : aucune migration de schéma n’est maintenue ; un ancien schéma est refusé.
- Les noms `annee_edition`, `annee_impression`, `description_illustration` et `etat_general` restent canoniques entre la réponse IA, les détections et les fiches JSON. Dans le CSV de consultation, `etat_general` est une colonne synthétique contenant uniquement l'appréciation (`tres_bon`, `bon`, `correct`, `mauvais` ou `non_evaluable`) ; le détail structuré est exporté dans `etat_general_details`.
- Les fiches persistantes utilisent directement les noms canoniques ; les anciens schémas ne sont pas convertis et doivent être remplacés par un inventaire neuf. Les alias acceptés dans `notes.txt` sont des raccourcis de saisie, pas une migration de données.
- Le CSV est un export de consultation, notamment dans LibreOffice Calc. Sa présentation peut différer du JSON, qui reste la source de vérité persistante.
- La version du programme et la version du schéma JSON sont distinctes.
- Les photos de travail restent dans le dossier local `photos/`, exclu de Git. Les photos d'exemples/test ne créent jamais de documents réels.
- Les tests ne doivent pas écrire dans le JSON de production. Tester en environnement temporaire avant toute intégration réelle.

## 8. Règles de collaboration et de développement

- Avant toute évolution, lire ce document et examiner l'état réel des fichiers concernés.
- Travailler sur la branche explicitement indiquée par l'utilisateur. Ne pas créer de branche sans demande explicite. Si l'utilisateur indique `main`, y travailler directement.
- Ne jamais fusionner sans accord explicite de l'utilisateur.
- Chaque modification du script augmente sa version et ajoute une entrée à l'historique en tête du script ; dates au format `jj/mm/aaaa`.
- Distinguer les faits vérifiés des hypothèses. Ne pas déclarer un test exécuté ou réussi sans preuve.
- Éviter de dupliquer les règles durables dans plusieurs documents : ce fichier est la source de vérité ; `README.md` présente le projet et `EN_COURS.md` son état actuel.
