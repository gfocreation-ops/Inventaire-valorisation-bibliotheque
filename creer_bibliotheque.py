#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import base64
import csv
import difflib
import hashlib
import io
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path


VERSION = "6.2.4"
VERSION_DATE = "22/10/2026"
DEFAULT_LAST_RESPONSE_FILE = Path("derniere_reponse_ia.txt")

# Activation individuelle des catalogues bibliographiques.
RECHERCHE_BNF_ACTIVE = True
RECHERCHE_OPEN_LIBRARY_ACTIVE = True
RECHERCHE_GOOGLE_BOOKS_ACTIVE = False

# Objectif du script : gérer progressivement l'inventaire et la valorisation à partir des photographies.
# ============================================================
# HISTORIQUE DES VERSIONS
#
# 6.2.4 — 22/10/2026
# - remplace la colonne « annee » de inventaire_réduit.csv par « annee_impression », « annee_edition » et « date_depot_legal », dans cet ordre.
#
# 6.2.3 — 21/10/2026
# - permet de définir le statut de progression d’un document depuis notes.txt ;
# - accepte « 9. Abandonné » et la valeur « auto » pour revenir au statut calculé.
#
# 6.2.2 — 21/10/2026
# - réexamine les rapprochements ambigus déjà enregistrés quand une photo montre plusieurs exemplaires distincts d'un même titre ;
# - permet de créer leurs fiches provisoires sans devoir relancer l'analyse IA de la photo.
#
# 6.2.1 — 21/10/2026
# - distingue les exemplaires de même titre à partir des différences bibliographiques explicites ;
# - crée une fiche provisoire si tous les documents de même titre ont au moins un champ distinctif contradictoire ;
# - conserve le rapprochement ambigu lorsqu’un document existant ne peut pas être distingué avec les informations disponibles.
#
# 6.2.0 — 19/10/2026
# - ajoute l’export de consultation simplifié inventaire_réduit.csv, séparé par des barres verticales ;
# - conserve inventaire.csv, le JSON persistant (schéma 0.22) et le contrat IA 1.1 inchangés.
#
# 6.1.33 — 19/10/2026
# - supprime du terminal, dans le résumé, les listes « Photos ciblées utiles » et « Prochaine action utile (priorité à l’identification) » ;
# - conserve les autres éléments du bilan et les données persistantes inchangés.

# 6.1.32 — 19/10/2026
# - en cas de flex_unavailable, effectue deux réessais Flex après 30 s puis 60 s avant le repli standard ;
# - désactive les réessais automatiques du SDK pour les seuls appels Flex afin de maîtriser ces délais ;
# - le traitement standard conserve ses réglages habituels ; schéma JSON 0.22 et contrat IA 1.1 inchangés.
#
# 6.1.31 — 19/10/2026
# - retente en traitement standard uniquement si le niveau Flex répond avec le code flex_unavailable ;
# - les autres erreurs API continuent à remonter sans second appel ; le schéma JSON 0.22 et le contrat IA 1.1 restent inchangés.

# 6.1.30 — 19/10/2026
# - rétablit la variable d’environnement OPENAI_API_KEY attendue avant la modification Flex.

# 6.1.29 — 19/10/2026
# - corrige l’import du client OpenAI et le message associé après une altération syntaxique.

# 6.1.28 — 18/10/2026
# - export_csv : annee_impression avant annee_edition.

# 6.1.27 — 17/10/2026
# - active le niveau de traitement API `flex` pour l’analyse des photos ;
# - confirme qu’une erreur d’appel conserve l’analyse valide précédente, marque la photo en erreur et permet une nouvelle tentative au lancement suivant ;
# - schéma JSON persistant 0.22 et contrat IA 1.1 inchangés.

# 6.1.26 — 16/10/2026
# - exporte etat_general comme appréciation courte après isbn, et conserve le détail dans etat_general_details ;
# - le JSON, le schéma persistant et le contrat IA restent inchangés.

# 6.1.25 — 16/10/2026
# - supprime la prise en charge des migrations ; seuls les inventaires au schéma courant 0.22 sont acceptés ;
# - conserve les noms canoniques des champs à chaque étape et harmonise l’export CSV.
# - contrat IA 1.1 inchangé.

# 6.1.22 — 15/10/2026
# - restaure la formulation initiale du prompt, sans ajouter de précision sur zéro document.

# 6.1.21 — 15/10/2026
# - tentative de précision de cardinalité du prompt, annulée en 6.1.22 ;
#
# 6.1.20 — 15/10/2026
# - structure le contrat IA en champs bibliographiques distincts et sépare les dates ;
# - conserve le sous-titre dans l’inventaire ; contrat IA 1.1, schéma persistant 0.20.
#
# 6.1.19 — 15/10/2026
# - reconnaît la clé réservée « ignore » dans notes.txt comme commentaire personnel ;
# - conserve ce commentaire dans l’historique des notes sans modifier la fiche ni son statut.
#
# 6.1.18 — 15/10/2026
# - accepte une concordance de titre par préfixe uniquement lorsque l’ISBN de la notice est exact ;
# - distingue les coauteurs séparés par « et » et ignore les mentions de rôle entre parenthèses.
#
# 6.1.17 — 15/10/2026
# - adapte le contrat de réponse IA au prompt simplifié ; accepte zéro à plusieurs documents par photo ;
# - retire du JSON de réponse les champs de document principal et d’observations générales ; contrat IA 1.0.
#
# 6.1.16 — 13/10/2026
# - utilise detail=auto pour transmettre les photos à l’API et consigne ce réglage dans le diagnostic.
#
# 6.1.15 — 13/10/2026
# - initialise explicitement la liste des ISBN de la notice d’ancrage dans les nouvelles fiches.
#
# 6.1.14 — 13/10/2026
# - conserve dans la fiche et le CSV tous les ISBN valides d’une notice d’ancrage, sans les confondre avec l’ISBN unique de l’exemplaire.
# - distingue une recherche ISBN non effectuée d’un ISBN recherché absent de la notice ; schéma persistant 0.19.
#
# 6.1.13 — 13/10/2026
# - permet à une réanalyse de remplacer un ancien état migré vers non_evaluable, sans écraser une appréciation nouvelle déjà valide.
#
# 6.1.12 — 13/10/2026
# - retire aussi les anciens champs d’état du modèle de création des fiches et aligne la progression sur les nouvelles appréciations.
#
# 6.1.11 — 13/10/2026
# - simplifie l’état visuel en appréciation et motif court ; contrat IA 0.9 ; schéma persistant 0.18 ;
# - normalise les retours à la ligne du titre, du sous-titre et des auteurs ; regroupe les demandes de photos.
#
# 6.1.10 — 13/10/2026
# - configure l’identifiant de modèle API `gpt-6.1-sol` pour l’analyse des photos.
#
# 6.1.9 — 13/10/2026
# - distingue les notices d’édition des notices d’œuvre pour confirmer une édition ;
# - exige une notice d’ancrage, trace les contradictions ISBN et limite les imports à cette notice ;
# - interroge la BnF en UNIMARCXCHANGE pour exploiter toutes les zones ISBN 010 ; schéma persistant 0.17.
#
# 6.1.8 — 13/10/2026
# - améliore le classement des notices par score d'éditeur et consigne ce classement ;
# - remplace l'état libre par un schéma fermé de défauts observables et une provenance explicite ;
# - ajoute le type de document, les demandes de photos ciblées et un outil de stabilité distinct ;
# - porte le contrat IA à 0.8 et le schéma JSON persistant à 0.16 ; les anciennes photos sont à réanalyser.
#
# 6.1.7 — 13/10/2026
# - retire le champ de compatibilité identification_web de la conversion des réponses IA ;
# - valide la clé de contrôle des ISBN-10 et ISBN-13 avant recherche, rapprochement ou import catalogue ;
# - conserve un ISBN invalide comme donnée à vérifier, sans l’utiliser comme identifiant de recherche ;
# - ajoute le diagnostic de contrôle ISBN à l'historique des recherches (schéma JSON 0.15).
#
# 6.1.6 — 13/10/2026
# - recentre l’analyse IA sur le texte visible, l’illustration et l’état apparent ;
# - retire l’outil Web Search et les missions d’identification externe du prompt ;
# - distingue le statut de lecture des champs bibliographiques et le document principal ;
# - porte le contrat d’analyse IA à 0.7 et le schéma JSON persistant à 0.14.
#
# 6.1.5 — 12/10/2026
# - impose l’utilisation de Web Search avec tool_choice="required" ;
# - consigne ce choix dans le diagnostic de l’appel API.
#
# 6.1.4 — 12/10/2026
# - réoriente la recherche Web vers une démarche exploratoire et conserve les requêtes/résultats ;
# - porte le contrat IA à 0.6 et le schéma JSON persistant à 0.13.
#
# 6.1.3 — 12/10/2026
# - renforce le prompt et le contrat JSON : origine par champ, référence exacte,
#   parties non observables et compléments ciblés ; contrat IA 0.5, schéma 0.12.
#
# 6.1.2 — 12/10/2026
# - enrichit derniere_reponse_ia.txt avec le modèle, la limite de sortie, la photo, le prompt complet,
#   les paramètres de requête, le statut de fin et les statistiques de tokens ;
# - conserve une section de sortie brute dédiée et rend --last-reponse compatible avec ce format.
#
# 6.1.1 — 12/10/2026
# - sauvegarde la sortie brute du dernier appel IA avant son décodage ;
# - ajoute --last-reponse pour rejouer cette sortie sans appel API ;
# - augmente la limite de sortie à 12000 tokens et refuse le rejeu ambigu sur plusieurs photos.
#
# 6.1.0 — 12/10/2026
# - étend l’analyse photo à la recherche Web dans le même appel multimodal ;
# - conserve la description visuelle et les pistes bibliographiques avec leurs sources ;
# - porte le contrat d’analyse IA à 0.4 et le schéma JSON persistant à 0.11 ;
# - relance les analyses photo dont le contrat enregistré est antérieur à 0.4.
#
# 6.0.2 — 12/10/2026
# - simplifie le complément de prompt des précisions photo ;
# - traite les précisions comme fiables et n'ajoute la consigne d'association aux identifiants
#   connus que si la colonne « ref » de photos.txt vaut « oui » ;
# - conserve le schéma JSON 0.10 et le contrat d'analyse IA 0.3.
#
# 6.0.1 — 12/10/2026
# - remplace les fichiers TXT accolés aux photos par le CSV racine photos.txt ;
# - transmet la précision de chaque photo à l’IA et relance l’analyse si elle change ;
# - conserve le champ « ref » pour un usage ultérieur sans lui donner encore d’effet ;
# - porte le schéma JSON persistant à 0.10, sans modifier le contrat d’analyse IA (0.3).
#
# 6.0.0 — 12/10/2026
# - renomme le script principal en creer_bibliotheque.py ;
# - conserve le fonctionnement existant et met à jour les références documentaires/tests.
#
# 0.5.14 — 11/10/2026
# - utilise le critère BnF fuzzyISBN et traite explicitement les diagnostics SRU ;
# - corrige les petites erreurs de titre depuis une notice bibliographique fortement concordante ;
# - conserve l’ancienne valeur, la nouvelle et la provenance sans écraser une correction utilisateur.
#
# 0.5.13 — 11/10/2026
# - exploite les recherches Open Library par ISBN même si la notice omet son identifiant ;
# - exige une concordance d’auteur et un titre suffisamment proche pour cette validation ;
# - harmonise la stratégie enregistrée et la clé de cache des recherches.
#
# 0.5.12 — 11/10/2026
# - recherche la BnF par ISBN exact en priorité, sans dépendre de la graphie du titre ;
# - conserve la recherche par titre/auteur en solution de repli.
#
# 0.5.11 — 11/10/2026
# - impose une progression strictement séquentielle, sans demi-étape d’identification ;
# - rend les catalogues activables individuellement et désactive Google Books par défaut ;
# - départage les notices BnF par éditeur et exploite les champs fiables manquants.
#
# 0.5.10 — 11/10/2026
# - adopte « document » dans les identifiants, structures, messages et exports ;
# - préfixe les statuts de progression de leur numéro d’étape ;
# - migre les anciennes clés et références ouvrage_* au chargement du JSON.
#
# 0.5.9 — 11/10/2026
# - ajoute le statut de progression au CSV ;
# - recherche BnF, Open Library puis Google Books seulement si nécessaire ;
# - hiérarchise les compléments utiles et corrige la ponctuation des avertissements.
#
# 0.5.8 — 11/10/2026
# - donne priorité aux notes utilisateur sur les valeurs issues de l’IA, avec provenance ;
# - interprète le \n littéral des notes comme un saut de ligne dans une valeur ;
# - compare les ISBN-10 et ISBN-13 équivalents et évalue les notices sur plusieurs indices ;
# - distingue l’identification de l’document de celle de son édition et précise le bilan.
#
# 0.5.7 — 11/10/2026
# - distingue année de publication, date d’impression et date de dépôt légal ;
# - rattache une photo référencée par TXT à l’document existant et intègre les observations compatibles ;
# - conserve les conflits bibliographiques sans écraser les données existantes ;
# - exporte les dates bibliographiques et distingue les champs attendus du statut d’identification ;
# - passe le schéma JSON à 0.7.
#
# 0.5.6 — 10/10/2026
# - transmet le texte libre associé à une photo avec une consigne explicite sur les identifiants document_N ;
# - restitue l’identifiant d’document référencé dans chaque détection pour le script ;
# - rend paramétrable la largeur minimale des identifiants sans modifier les identifiants existants ;
# - passe le schéma JSON à 0.6 pour le nouveau champ de référence.
#
# 0.5.5 — 10/10/2026
# - interprète notes.txt au format CSV à trois colonnes et applique les faits non contradictoires ;
# - intègre les indices bibliographiques dans la signature de recherche et permet les requêtes par ISBN ;
# - espace les nouvelles tentatives après une erreur pour éviter les appels identiques à chaque lancement ;
# - confirme le suivi du TXT associé, qui déclenche une nouvelle analyse de la photo ;
# - ajoute date_impression au schéma de fiche (schéma JSON 0.5).
#
# 0.5.4 — 10/10/2026
# - améliore la concordance BnF avec l’ordre Nom Prénom et les mentions annexes ;
# - réessaie les erreurs HTTP temporaires, dont 429, avec temporisation ;
# - distingue les documents en erreur des appels aux catalogues en erreur ;
# - utilise « document(s) » dans le bilan et ajoute un séparateur avant BILAN.
#
# 0.5.3 — 10/10/2026
# - ajoute le type de document proposé par l’IA : livre, magazine, guide ou autre ;
# - affiche le nombre de documents détectés par photo ;
# - recherche BnF d’abord, puis Open Library et Google Books si la concordance est insuffisante ;
# - affiche un bilan global des recherches bibliographiques ;
# - supprime l’option --dry-run ; JSON et CSV sont enregistrés normalement.

# 0.5.2 — 10/10/2026
# - recherche bibliographique BnF automatique pour toute fiche avec métadonnées
#   bibliographiques manquantes, même si l'ancienne liste des manques est incomplète ;
# - évite de répéter une recherche réussie sur le même titre et les mêmes auteurs ;
# - conserve les notices comme pistes sourcées, sans remplir automatiquement les fiches.
#
# 0.5.1 — 10/10/2026
# - progression affichée avant chaque appel d'analyse photo ;
# - bilan cohérent et libellé « Photos trouvées » ;
# - recherche bibliographique externe initiale ;
# - rapprochement multi-photos reporté à une phase de test dédiée.
#
# 0.5.0 — 10/10/2026
# Intégration de l'analyse multimodale simplifiée dans le script principal.
# - détection et identification structurées des documents par photo ;
# - conservation des résultats, niveaux de confiance et provenance dans le JSON ;
# - rapprochements bibliographiques prudents et signalement des ambiguïtés ;
# - export CSV des fiches d'documents ;
# - mode --dry-run pour tester sans écrire le JSON ni le CSV.
#
# 0.4.3 — 08/10/2026
# Formalisation et contrôle des invariants fondamentaux du projet.
# - trois entités : documents, photos et notes ;
# - trois acteurs : utilisateur, script et IA ;
# - un document doit avoir au moins une source photo ou note ;
# - une photo peut concerner de zéro à plusieurs documents ;
# - contrôle de cohérence des associations photo ↔ document avant sauvegarde.
#
# 0.4.2 — 08/10/2026
# Correction de la structure d’analyse pour permettre plusieurs documents par photo.
# - une photo peut contenir plusieurs documents ;
# - chaque document détecté possède sa propre correspondance, zone, confiance,
#   observations, informations manquantes, état et demande de photo complémentaire ;
#
# 0.4.1 — 08/10/2026
# Ajout de la gestion des analyses et de leur provenance.
# - stockage structuré de l’analyse d’une photo ;
# - fonction d’enregistrement d’une analyse ;
# - conservation de la provenance photo dans l’document.
#
# 0.4.0 — 08/10/2026
# Préparation du socle d’analyse multimodale et de consolidation des documents.
# - structure d’analyse propre à chaque photo ;
# - observations, niveaux de confiance et demandes de photos complémentaires ;
# - rapprochement explicite entre photo et document ;
# - provenance des informations observées sur les photos ;
# - appréciation globale de l’état matériel : bon, usé, abîmé ou mauvais ;
# - aucune recherche Web, valorisation ou déduction d’informations non visibles.
#
# 0.3.2 — 08/10/2026
# Correction de la propagation des notes vers la provenance des documents.
# - une note déjà enregistrée est également reliée à l’document lorsqu’il devient connu ultérieurement ;
# - évite les doublons dans sources_information.
#
# 0.3.1 — 08/10/2026
# Corrections techniques de la gestion des notes et du résumé.
# - détection des modifications de notes par SHA-256 ;
# - provenance des notes reliée à l’document lorsqu’il existe ;
# - intitulé du résumé simplifié.
#
# 0.3.0 — 08/10/2026
# Structure persistante des documents, rôles de photos et traçabilité des notes.
# - rôles photo : reperage, identification, etat ;
# - structure minimale des documents normalisée ;
# - notes.txt conservé comme source cumulative d’informations/corrections/précisions ;
# - aucune analyse multimodale ou valorisation automatisée.
#
# Historique cumulatif des évolutions du script. Chaque nouvelle version
# est ajoutée en tête de cette section ; les versions précédentes sont conservées.
#
# 0.2.3 — 08/10/2026
# Formatage des dates de version pour l'affichage utilisateur.
# - dates de version présentées au format jj/mm/aaaa ;
# - affichage de la version avec la même convention.
#
# 0.2.2 — 08/10/2026
# Correction de l'en-tête du script et incrémentation de version.
# - respect de l'ordre : shebang, encodage, imports, constantes de version, objectif, historique ;
# - suppression de tout contenu placé avant les imports ;
# - incrémentation de la version pour distinguer cette modification de la V0.2.1.
#
# 0.2.1 — 08/10/2026
# Correction d'une erreur d'exécution.
# - correction de print_report() afin de lui transmettre l'état persistant.
#
# 0.2.0 — 08/10/2026
# Séparation des photos de travail et des photos de test.
# - photos/ reste local et son contenu est exclu de Git.
# - photos_tests/ contient les photos de test versionnées.
# - ajout d'un résumé de fin de lancement facilement copiable.
#
# 0.1.0 — 08/10/2026
# Première version.
# - Détection des photographies du dossier local.
# - État persistant dans un fichier JSON.
# - Suivi des associations photo ↔ document.
# - Lecture d'un fichier cumulatif notes.txt.
# - Bilan de traitement au lancement.
#
# ============================================================

PHOTO_ROLES = {"reperage", "identification", "etat"}

PHOTO_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".tif",
    ".tiff",
}

DEFAULT_PHOTO_DIR = Path("photos")
DEFAULT_STATE_FILE = Path("inventaire.json")
DEFAULT_NOTES_FILE = Path("notes.txt")
DEFAULT_PHOTO_INSTRUCTIONS_FILE = Path("photos.txt")
DEFAULT_CSV_FILE = Path("inventaire.csv")
MODEL = "gpt-6.1-sol"
LARGEUR_NUMERO_DOCUMENT = 4  # largeur minimale du suffixe numérique des nouveaux identifiants


def now_iso() -> str:
    """Retourne la date/heure locale au format ISO 8601."""
    return datetime.now().astimezone().isoformat(timespec="seconds")


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Calcule l'empreinte SHA-256 d'un fichier."""
    digest = hashlib.sha256()

    with path.open("rb") as file:
        while chunk := file.read(chunk_size):
            digest.update(chunk)

    return digest.hexdigest()


def print_version() -> None:
    """Affiche la version du programme."""
    print(f"Inventaire et valorisation de bibliothèque — V{VERSION}")
    print(f"Version du {VERSION_DATE}")
    print()


def create_initial_state() -> dict:
    """Crée la structure minimale de l'état persistant."""
    return {
        "schema_version": "0.22",
        "program_version": VERSION,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "photos": {},
        "documents": {},
        "notes": {
            "file": str(DEFAULT_NOTES_FILE),
            "last_read_at": None,
            "last_size": 0,
            "last_sha256": None,
            "informations": [],
        },
        "runs": [],
    }


def normalize_state(state: dict) -> dict:
    """Complète les valeurs par défaut d'un inventaire au schéma courant, sans migration."""
    if state.get("schema_version") != "0.22":
        raise RuntimeError(
            "Version de schéma d'inventaire non prise en charge : "
            f"{state.get('schema_version')!r}. Les migrations sont désactivées ; "
            "repars d'un inventaire neuf."
        )

    state.setdefault("program_version", VERSION)
    state.setdefault("created_at", now_iso())
    state.setdefault("updated_at", now_iso())
    state.setdefault("photos", {})
    state.setdefault("documents", {})
    state.setdefault("notes", {})
    state.setdefault("runs", [])

    notes = state["notes"]
    notes.setdefault("file", str(DEFAULT_NOTES_FILE))
    notes.setdefault("last_read_at", None)
    notes.setdefault("last_size", 0)
    notes.setdefault("last_sha256", None)
    notes.setdefault("informations", [])

    for record in state["photos"].values():
        if not isinstance(record, dict):
            continue
        record.setdefault("document_ids", [])
        record.setdefault("roles", [])
        record.setdefault("role", "identification")
        record.setdefault("analysis", {})
        analysis = record["analysis"]
        analysis.setdefault("analyzed_at", None)
        analysis.setdefault("type_document", None)
        analysis.setdefault("observations", [])
        analysis.setdefault("documents_detectes", [])

    for document_id, document in state["documents"].items():
        if not isinstance(document, dict):
            continue
        document.setdefault("id", document_id)
        for key in (
            "type_document", "titre", "sous_titre", "editeur", "collection",
            "annee_edition", "edition", "annee_impression", "date_depot_legal",
            "isbn", "volume_numero", "description_illustration", "autres_textes",
        ):
            document.setdefault(key, None)
        document.setdefault("auteurs", [])
        document.setdefault("photos", [])
        document.setdefault("sources_information", [])
        document.setdefault("identification", {})
        document.setdefault("etat_general", {})

        identification = document["identification"]
        identification.setdefault("niveau_confiance", None)
        identification.setdefault("informations_manquantes", [])
        identification.setdefault("photos_complementaires", [])
        identification.setdefault("isbns_notice_ancrage", [])
        identification.setdefault("demandes_photo", {})

        etat_general = document["etat_general"]
        etat_general.setdefault("niveau_confiance", None)
        etat_general.setdefault("appreciation", None)
        etat_general.setdefault("observations", [])
        etat_general.setdefault("base", None)

    return state

def load_state(path: Path) -> dict:
    """Charge l'état existant ou crée un nouvel état."""
    if not path.exists():
        return create_initial_state()

    try:
        with path.open("r", encoding="utf-8") as file:
            state = json.load(file)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Le fichier JSON est invalide : {path}\n{exc}"
        ) from exc

    if not isinstance(state, dict):
        raise RuntimeError(
            f"Le fichier JSON ne contient pas un objet racine : {path}"
        )

    return normalize_state(state)


def validate_state_invariants(state: dict) -> None:
    """Vérifie les cardinalités et relations fondamentales avant persistance."""
    photos = state.get("photos", {})
    documents = state.get("documents", {})

    # Chaque document doit avoir au moins une source utilisateur :
    # une photo et/ou une note.
    for document_id, document in documents.items():
        document_photos = document.get("photos", [])
        sources = document.get("sources_information", [])
        has_photo_source = bool(document_photos) or any(
            isinstance(source, dict) and source.get("type") == "photo"
            for source in sources
        )
        has_note_source = any(
            isinstance(source, dict) and source.get("type") == "note"
            for source in sources
        )
        if not (has_photo_source or has_note_source):
            raise RuntimeError(
                f"Invariant violé : {document_id} n'a aucune source "
                "(photo ou note)."
            )

        for photo_path in document_photos:
            if photo_path not in photos:
                raise RuntimeError(
                    f"Invariant violé : {document_id} référence une photo "
                    f"inconnue : {photo_path}"
                )
            if document_id not in photos[photo_path].get("document_ids", []):
                raise RuntimeError(
                    f"Invariant violé : association non réciproque entre "
                    f"{document_id} et {photo_path}."
                )

        for source in sources:
            if not isinstance(source, dict):
                continue
            if source.get("type") == "photo":
                reference = source.get("reference")
                if reference not in photos:
                    raise RuntimeError(
                        f"Invariant violé : {document_id} possède une source "
                        f"photo inconnue : {reference}"
                    )

    # Une photo peut avoir zéro, un ou plusieurs documents : aucune cardinalité
    # maximale ne doit être imposée. Le cas 1 photo → 1 document est donc valide,
    # tout comme 0 ou plusieurs documents. Chaque identifiant doit exister
    # et l'association doit être réciproque.
    for photo_path, photo in photos.items():
        for document_id in photo.get("document_ids", []):
            if document_id not in documents:
                raise RuntimeError(
                    f"Invariant violé : {photo_path} référence un document "
                    f"inconnu : {document_id}"
                )
            if photo_path not in documents[document_id].get("photos", []):
                raise RuntimeError(
                    f"Invariant violé : association non réciproque entre "
                    f"{photo_path} et {document_id}."
                )


def save_state(path: Path, state: dict) -> None:
    """Sauvegarde l'état JSON de façon lisible."""
    validate_state_invariants(state)
    temporary_path = path.with_suffix(path.suffix + ".tmp")

    with temporary_path.open("w", encoding="utf-8") as file:
        json.dump(state, file, ensure_ascii=False, indent=2)
        file.write("\n")

    temporary_path.replace(path)


def list_photos(photo_dir: Path) -> list[Path]:
    """Retourne toutes les photos du dossier, récursivement."""
    if not photo_dir.exists():
        return []

    return sorted(
        (
            path
            for path in photo_dir.rglob("*")
            if path.is_file() and path.suffix.lower() in PHOTO_EXTENSIONS
        ),
        key=lambda path: path.as_posix().lower(),
    )


def scan_photos(
    photo_dir: Path, state: dict
) -> tuple[list[dict], list[dict], list[dict]]:
    """
    Compare les photos présentes sur disque avec l'état persistant.

    Une photo est identifiée par son chemin relatif et son SHA-256.
    Le programme ne cherche volontairement pas à déclarer une photo
    « inutile » ou « doublon » : plusieurs photos peuvent concerner
    le même document et chacune peut apporter des informations.
    """
    current_photos = list_photos(photo_dir)

    known_by_path = state["photos"]
    new_photos = []
    changed_photos = []

    current_paths = set()

    for path in current_photos:
        relative_path = path.relative_to(photo_dir.parent).as_posix()
        current_paths.add(relative_path)

        stat = path.stat()
        file_hash = sha256_file(path)
        record = known_by_path.get(relative_path)

        if record is None:
            record = {
                "path": relative_path,
                "sha256": file_hash,
                "size_bytes": stat.st_size,
                "modified_at": datetime.fromtimestamp(
                    stat.st_mtime
                ).astimezone().isoformat(timespec="seconds"),
                "first_seen_at": now_iso(),
                "last_seen_at": now_iso(),
                "analysis_status": "new",
                "role": "identification",
                "roles": ["identification"],
                "document_ids": [],
                "analysis": {
                    "analyzed_at": None,
                    "documents_detectes": [],
                },
            }
            known_by_path[relative_path] = record
            new_photos.append(record)
            continue

        record["last_seen_at"] = now_iso()

        if record.get("sha256") != file_hash:
            record["sha256"] = file_hash
            record["size_bytes"] = stat.st_size
            record["modified_at"] = datetime.fromtimestamp(
                stat.st_mtime
            ).astimezone().isoformat(timespec="seconds")
            record["analysis_status"] = "modified"
            changed_photos.append(record)

    missing_photos = []
    for relative_path, record in known_by_path.items():
        if relative_path not in current_paths:
            missing_photos.append(record)

    return new_photos, changed_photos, missing_photos


def read_photo_instructions(
    instructions_path: Path, photo_dir: Path, state: dict
) -> tuple[dict[str, dict], list[dict], bool, list[str]]:
    """Lit photos.txt (CSV photo;ref;precision) et rattache les précisions par nom exact."""
    instruction_state = state.setdefault("photo_instructions", {})
    saved_by_name: dict[str, list[dict]] = {}
    for record in state.get("photos", {}).values():
        name = Path(record.get("path", "")).name
        if "photo_precision" in record:
            saved_by_name.setdefault(name, []).append({
                "ref": record.get("photo_ref", ""),
                "precision": record.get("photo_precision", ""),
            })
    previous_mapping = {
        name: values[0] for name, values in saved_by_name.items() if len(values) == 1
    }
    if not instructions_path.exists():
        content, rows = "", []
    else:
        try:
            content = instructions_path.read_text(encoding="utf-8-sig")
            reader = csv.DictReader(io.StringIO(content), delimiter=";")
            if reader.fieldnames != ["photo", "ref", "precision"]:
                return previous_mapping, [], False, [
                    f"{instructions_path} : en-tête CSV attendu : photo;ref;precision ; "
                    "les dernières précisions valides sont réutilisées."
                ]
            rows = list(reader)
        except (OSError, csv.Error, UnicodeError) as exc:
            return previous_mapping, [], False, [
                f"{instructions_path} : fichier ou format CSV invalide ({exc}) ; "
                "les dernières précisions valides sont réutilisées."
            ]

    file_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    file_changed = file_hash != instruction_state.get("last_sha256")
    by_name: dict[str, list[Path]] = {}
    for path in list_photos(photo_dir):
        by_name.setdefault(path.name, []).append(path)

    warnings, mapping, invalid_names = [], {}, set()
    for line_number, row in enumerate(rows, start=2):
        photo_name = (row.get("photo") or "").strip()
        if None in row or not all(key in row for key in ("photo", "ref", "precision")):
            if photo_name:
                invalid_names.add(photo_name)
                mapping.pop(photo_name, None)
            warnings.append(f"{instructions_path} ligne {line_number} : 3 colonnes attendues ; ligne ignorée.")
            continue
        ref = (row.get("ref") or "").strip().casefold()
        precision = (row.get("precision") or "").strip()
        if not photo_name:
            warnings.append(f"{instructions_path} ligne {line_number} : nom de photo vide ; ligne ignorée.")
            continue
        if ref not in {"oui", "non"}:
            warnings.append(
                f"{instructions_path} ligne {line_number} : « ref » doit valoir oui ou non ; "
                "la précision reste utilisable, mais ref est conservé tel quel."
            )
        if photo_name in invalid_names:
            continue
        if photo_name in mapping:
            mapping.pop(photo_name, None)
            invalid_names.add(photo_name)
            warnings.append(
                f"{instructions_path} ligne {line_number} : plusieurs lignes pour {photo_name!r} ; "
                "toutes ses lignes sont ignorées."
            )
            continue
        matches = by_name.get(photo_name, [])
        if len(matches) != 1:
            reason = "aucune photo correspondante" if not matches else "nom non unique dans le dossier photos"
            if matches:
                invalid_names.add(photo_name)
            warnings.append(f"{instructions_path} ligne {line_number} : {reason} pour {photo_name!r} ; ligne ignorée.")
            continue
        mapping[photo_name] = {"ref": ref, "precision": precision}

    changed_records = []
    for record in state.get("photos", {}).values():
        photo_name = Path(record.get("path", "")).name
        if photo_name in invalid_names:
            continue
        instruction = mapping.get(photo_name, {})
        precision = instruction.get("precision", "")
        ref = instruction.get("ref", "")
        previous_ref = record.get("photo_ref", "")
        record["photo_precision"] = precision
        record["photo_ref"] = ref
        precision_hash = hashlib.sha256(precision.encode("utf-8")).hexdigest()
        previous_hash = record.get("precision_sha256")
        if previous_hash is None:
            if precision:
                record["precision_sha256"] = precision_hash
                record["analysis_status"] = "modified"
                changed_records.append(record)
            else:
                record["precision_sha256"] = precision_hash
            continue
        if previous_hash != precision_hash or (precision and previous_ref != ref):
            record["precision_sha256"] = precision_hash
            record["analysis_status"] = "modified"
            changed_records.append(record)

    instruction_state.update({"file": str(instructions_path), "last_sha256": file_hash, "last_read_at": now_iso()})
    return mapping, changed_records, file_changed, warnings


def create_document(state: dict, **initial_values) -> str:
    """Crée un document vide avec la structure V0.4."""
    existing_numbers = set()
    for existing_id in state["documents"]:
        prefix, separator, suffix = existing_id.rpartition("_")
        if prefix == "document" and separator and suffix.isdigit():
            existing_numbers.add(int(suffix))
    index = 1
    while index in existing_numbers:
        index += 1
    width = max(1, int(LARGEUR_NUMERO_DOCUMENT))
    document_id = f"document_{index:0{width}d}"
    timestamp = now_iso()
    state["documents"][document_id] = {
        "id": document_id, "type_document": initial_values.get("type_document"),
        "titre": initial_values.get("titre"), "auteurs": initial_values.get("auteurs", []),
        "editeur": initial_values.get("editeur"), "collection": initial_values.get("collection"),
        "annee_edition": initial_values.get("annee_edition"), "edition": initial_values.get("edition"),
        "annee_impression": initial_values.get("annee_impression"),
        "date_depot_legal": initial_values.get("date_depot_legal"),
        "isbn": initial_values.get("isbn"), "volume_numero": initial_values.get("volume_numero"),
        "description_illustration": initial_values.get("description_illustration"),
        "autres_textes": initial_values.get("autres_textes", []),
        "photos": [], "sources_information": [],
        "identification": {"niveau_confiance": None, "informations_manquantes": [], "photos_complementaires": [], "demandes_photo": {}, "isbns_notice_ancrage": []},
        "etat_general": {
            "niveau_confiance": None,
            "appreciation": None,
            "observations": [],
            "base": None,
        },
        "created_at": timestamp, "updated_at": timestamp,
    }
    return document_id


def associate_photo_to_document(state: dict, photo_path: str, document_id: str, role: str = "identification") -> None:
    """Maintient l'association bidirectionnelle photo ↔ document."""
    if role not in PHOTO_ROLES:
        raise ValueError(f"Rôle de photo invalide : {role}")
    if photo_path not in state["photos"] or document_id not in state["documents"]:
        raise KeyError("Photo ou document inconnu")
    photo = state["photos"][photo_path]
    document = state["documents"][document_id]
    photo.setdefault("document_ids", [])
    photo.setdefault("roles", [])
    if document_id not in photo["document_ids"]:
        photo["document_ids"].append(document_id)
    if photo_path not in document["photos"]:
        document["photos"].append(photo_path)
    if role not in photo["roles"]:
        photo["roles"].append(role)
    photo["role"] = role
    document["updated_at"] = now_iso()

def set_photo_analysis(
    state: dict,
    photo_path: str,
    *,
    documents_detectes: list[dict] | None = None,
) -> None:
    """Enregistre l'analyse structurée d'une photo pouvant montrer plusieurs documents."""
    if photo_path not in state["photos"]:
        raise KeyError(f"Photo inconnue : {photo_path}")

    analysis = state["photos"][photo_path].setdefault("analysis", {})
    analysis["analyzed_at"] = now_iso()
    analysis["documents_detectes"] = documents_detectes or []

    needs_complementary = any(
        isinstance(item, dict)
        and item.get("demande_photo_complementaire", {}).get("necessaire")
        for item in analysis["documents_detectes"]
    )
    if needs_complementary:
        state["photos"][photo_path]["analysis_status"] = "needs_complementary_photo"
    else:
        state["photos"][photo_path]["analysis_status"] = "analyzed"


def add_photo_source_to_document(
    state: dict,
    document_id: str,
    photo_path: str,
    champ: str,
    valeur,
) -> None:
    """Ajoute une provenance photo à un document sans créer de doublon."""
    if document_id not in state["documents"]:
        raise KeyError(f"Document inconnu : {document_id}")
    if photo_path not in state["photos"]:
        raise KeyError(f"Photo inconnue : {photo_path}")

    source = {
        "type": "photo",
        "reference": photo_path,
        "champ": champ,
        "valeur": valeur,
    }
    sources = state["documents"][document_id].setdefault(
        "sources_information", []
    )

    existing = next((
        item for item in sources
        if item.get("type") == source["type"]
        and item.get("reference") == source["reference"]
        and item.get("champ") == source["champ"]
    ), None)
    if existing is None:
        sources.append(source)
        state["documents"][document_id]["updated_at"] = now_iso()
    elif existing != source:
        # Une réanalyse de la même photo actualise sa proposition et ses métadonnées.
        existing.update(source)
        state["documents"][document_id]["updated_at"] = now_iso()


def _normalize_note_key(value: str) -> str:
    """Normalise une clé de notes sans tenir compte de la casse ni des accents."""
    import unicodedata
    value = unicodedata.normalize("NFKD", value.strip().casefold())
    value = "".join(char for char in value if not unicodedata.combining(char))
    return "_".join(value.replace("-", " ").split())


NOTE_FIELD_MAP = {
    "titre": "titre", "auteur": "auteurs", "auteurs": "auteurs",
    "editeur": "editeur", "collection": "collection", "annee": "annee_edition",
    "annee_edition": "annee_edition", "annee_publication": "annee_edition", "edition": "edition",
    "date": "annee_impression", "date_impression": "annee_impression", "annee_impression": "annee_impression",
    "date_depot_legal": "date_depot_legal", "depot_legal": "date_depot_legal", "isbn": "isbn",
    "volume": "volume_numero", "volume_numero": "volume_numero",
    "statut": "statut_force",
    # Clé réservée : commentaire personnel conservé dans l’historique des notes,
    # sans application à la fiche ni ajout aux sources_information du document.
    "ignore": None,
}


STATUTS_PROGRESSION = (
    "1. A identifier",
    "2. Identifié",
    "3. Etat à préciser",
    "4. Etat connu",
    "5. Valorisé",
    "9. Abandonné",
)
STATUTS_PROGRESSION_NORMALISES = {
    _normalize_note_key(value): value for value in STATUTS_PROGRESSION
}


def _note_value_for_field(field: str, value: str):
    # Dans notes.txt, la séquence littérale \\n représente un saut de ligne.
    value = value.replace(r"\n", "\n").strip()
    if field == "auteurs":
        return [part.strip() for part in value.split(";") if part.strip()]
    return value or None


def _same_note_value(field: str, current, proposed) -> bool:
    if field == "auteurs":
        return [str(x).strip().casefold() for x in (current or [])] == [
            str(x).strip().casefold() for x in (proposed or [])
        ]
    return str(current or "").strip().casefold() == str(proposed or "").strip().casefold()


def read_notes(notes_path: Path, state: dict) -> tuple[str, bool]:
    """
    Lit notes.txt au format CSV séparé par des points-virgules :
    document_id;clé;valeur. Le fichier n'est jamais modifié ni envoyé à l'IA.
    """
    if not notes_path.exists():
        return "", False

    content = notes_path.read_text(encoding="utf-8-sig")
    content_bytes = content.encode("utf-8")
    current_sha256 = hashlib.sha256(content_bytes).hexdigest()
    notes_state = state.setdefault("notes", {})
    changed = current_sha256 != notes_state.get("last_sha256")
    informations = notes_state.setdefault("informations", [])
    known_ids = set(state.get("documents", {}))
    warnings = []
    try:
        rows = list(csv.reader(content.splitlines(), delimiter=";", quotechar='"', strict=True))
    except csv.Error as exc:
        rows = []
        warnings.append(f"notes.txt : format CSV invalide ({exc})")

    for line_number, row in enumerate(rows, start=1):
        if not row or all(not part.strip() for part in row):
            continue
        if len(row) == 1 and row[0].lstrip().startswith("#"):
            continue
        if len(row) != 3:
            warnings.append(
                f"notes.txt ligne {line_number} : 3 colonnes attendues "
                "(document_id;clé;valeur) ; ligne ignorée."
            )
            continue

        document_id, key_text, raw_value = (part.strip() for part in row)
        if line_number == 1 and _normalize_note_key(document_id) in {"document", "document_id", "id_document"}:
            continue
        if not document_id or not key_text or not raw_value:
            warnings.append(f"notes.txt ligne {line_number} : champ vide ; ligne ignorée.")
            continue
        normalized_key = _normalize_note_key(key_text)
        field = NOTE_FIELD_MAP.get(normalized_key)
        fingerprint_input = "\x1f".join((document_id, normalized_key, raw_value.strip()))
        fingerprint = hashlib.sha256(fingerprint_input.encode("utf-8")).hexdigest()
        reference = f"{notes_path.as_posix()}:{line_number}"
        existing_record = next((
            item for item in informations
            if isinstance(item, dict) and item.get("empreinte_ligne") == fingerprint
        ), None)

        status, message = "en_attente", None
        if document_id not in known_ids and document_id.replace("ouvrage_", "document_", 1) not in known_ids:
            status, message = "document_inconnu", f"document inconnu « {document_id} »"
        elif document_id not in known_ids:
            document_id = document_id.replace("ouvrage_", "document_", 1)
            if normalized_key == "ignore":
                status = "commentaire_personnel_ignore"
            elif not field:
                status, message = "cle_inconnue", f"clé inconnue « {key_text} »"
            else:
                status = "en_attente"
        elif normalized_key == "ignore":
            # Commentaire personnel : conservé dans notes.informations uniquement.
            # Il ne modifie ni le document ni ses sources_information.
            status = "commentaire_personnel_ignore"
        elif normalized_key == "statut":
            book = state["documents"][document_id]
            proposed = STATUTS_PROGRESSION_NORMALISES.get(_normalize_note_key(raw_value))
            if _normalize_note_key(raw_value) == "auto":
                if book.pop("statut_force", None) is None:
                    status = "deja_concordante"
                else:
                    book["updated_at"] = now_iso()
                    status = "appliquee"
            elif proposed is None:
                status = "valeur_invalide"
                message = (
                    f"statut invalide {raw_value!r} ; valeurs admises : "
                    + ", ".join(STATUTS_PROGRESSION)
                    + " ; utiliser « auto » pour revenir au statut calculé."
                )
            else:
                current = book.get("statut_force")
                if current == proposed:
                    status = "deja_concordante"
                else:
                    book["statut_force"] = proposed
                    book["updated_at"] = now_iso()
                    status = "appliquee" if current in (None, "") else "appliquee_remplacee"
        elif not field:
            status, message = "cle_inconnue", f"clé inconnue « {key_text} »"
        else:
            proposed = _note_value_for_field(field, raw_value)
            book = state["documents"][document_id]
            current = book.get(field)
            if current in (None, "", []):
                book[field] = proposed
                book["updated_at"] = now_iso()
                status = "appliquee"
            elif _same_note_value(field, current, proposed):
                status = "deja_concordante"
            else:
                # Toute note utilisateur est prioritaire. Si plusieurs notes du
                # même champ se contredisent, la dernière ligne du fichier prévaut.
                previous_value = current
                book[field] = proposed
                book["updated_at"] = now_iso()
                status = "appliquee_remplacee"
                message = (
                    f"{document_id}.{field} : la valeur précédente {previous_value!r} "
                    "a été remplacée par la valeur explicite de notes.txt."
                )

        if status in {"appliquee", "appliquee_remplacee"} and field in {"titre", "auteurs", "editeur", "collection", "annee_edition", "edition", "annee_impression", "date_depot_legal", "isbn"}:
            identification = state["documents"][document_id].setdefault("identification", {})
            identification["statut"] = "a_confirmer_par_recherche_bibliographique"
            identification["niveau_confiance"] = None

        if existing_record is None:
            informations.append({
                "type": "note", "reference": reference, "document_id": document_id,
                "cle": key_text, "champ": field, "contenu": raw_value,
                "empreinte_ligne": fingerprint, "statut_application": status,
                "message": message, "recorded_at": now_iso(),
            })
        else:
            existing_record.update({
                "reference": reference, "statut_application": status, "message": message,
            })
        if message:
            warnings.append(f"notes.txt ligne {line_number} : {message}.")

        if document_id in known_ids and normalized_key != "ignore":
            source = {"type": "note", "reference": reference, "champ": field, "contenu": raw_value}
            sources = state["documents"][document_id].setdefault("sources_information", [])
            if not any(
                item.get("type") == "note" and item.get("reference") == reference
                and item.get("champ") == field and item.get("contenu") == raw_value
                for item in sources
            ):
                sources.append(source)

    notes_state.update({
        "file": str(notes_path), "last_read_at": now_iso(),
        "last_size": len(content_bytes), "last_sha256": current_sha256,
        "informations": informations,
    })
    for warning in warnings:
        print("AVERTISSEMENT — " + warning.rstrip().rstrip("."))
    return content, changed


def set_photo_role(state: dict, photo_path: str, role: str) -> None:
    """Définit le rôle d’une photo : reperage, identification ou etat."""
    if role not in PHOTO_ROLES:
        raise ValueError(f"Rôle de photo invalide : {role}")
    if photo_path not in state["photos"]:
        raise KeyError(f"Photo inconnue : {photo_path}")
    photo = state["photos"][photo_path]
    photo.setdefault("roles", [])
    if role not in photo["roles"]:
        photo["roles"].append(role)
    photo["role"] = role


def update_photo_analysis_status(state: dict) -> None:
    """
    Marque les nouvelles photos comme « pending_analysis ».

    Le script ne réalise pas encore l'analyse multimodale.
    """
    for record in state["photos"].values():
        if record.get("analysis_status") in {"new", "modified"}:
            record["analysis_status"] = "pending_analysis"


def print_report(
    photo_dir: Path,
    state: dict,
    state_path: Path,
    notes_path: Path,
    new_photos: list[dict],
    changed_photos: list[dict],
    missing_photos: list[dict],
    notes_changed: bool,
) -> None:
    """Affiche le bilan détaillé puis un résumé destiné au partage."""
    photos = state["photos"]
    documents = state["documents"]

    pending = sum(
        1
        for record in photos.values()
        if record.get("analysis_status") == "pending_analysis"
    )

    print("=" * 60)
    print("BILAN")
    print("-----")
    print(f"Dossier photos       : {photo_dir}")
    print(f"État JSON            : {state_path}")
    print(f"Fichier de notes     : {notes_path}")
    print()
    print(f"Photos trouvées      : {len(photos)}")
    print(f"Nouvelles photos     : {len(new_photos)}")
    print(f"Photos modifiées     : {len(changed_photos)}")
    print(f"Photos absentes      : {len(missing_photos)}")
    print(f"Photos encore en attente : {pending}")
    print(f"Documents dans l’inventaire : {len(documents)}")
    status_counts = {}
    for document in documents.values():
        status = document.get("identification", {}).get("statut") or "a_completer"
        status_counts[status] = status_counts.get(status, 0) + 1
    print(f"Documents identifiés : {sum(count for status, count in status_counts.items() if status in {'edition_identifiee', 'identifie'})}")
    print(f"Documents restant à identifier : {sum(count for status, count in status_counts.items() if status not in {'edition_identifiee', 'identifie'})}")
    progression_counts = {}
    for document in documents.values():
        step = progression_status(document)
        progression_counts[step] = progression_counts.get(step, 0) + 1
    print("Progression des documents :")
    for step in ("1. A identifier", "2. Identifié", "3. Etat à préciser", "4. Etat connu", "5. Valorisé"):
        print(f"  {step} : {progression_counts.get(step, 0)}")
    print(f"Notes modifiées      : {'oui' if notes_changed else 'non'}")
    print()

    if new_photos:
        print("Nouvelles photos :")
        for record in new_photos:
            print(f"  + {record['path']}")
        print()

    if changed_photos:
        print("Photos modifiées :")
        for record in changed_photos:
            print(f"  * {record['path']}")
        print()

    if missing_photos:
        print("Photos absentes du dossier :")
        for record in missing_photos:
            print(f"  - {record['path']}")
        print()

    if pending:
        print(f"Photos en attente d’analyse : {pending}")
    elif new_photos or changed_photos:
        print("Les photos nouvelles/modifiées de ce lancement ont été traitées.")
    else:
        print("Aucune photo nouvelle ou modifiée à analyser.")

    print()
    print("=" * 60)
    print("RÉSUMÉ")
    print("=" * 60)
    print(f"Version : V{VERSION}")
    print(f"Photos trouvées : {len(photos)}")
    print(f"Nouvelles photos : {len(new_photos)}")
    print(f"Photos modifiées : {len(changed_photos)}")
    print(f"Photos absentes : {len(missing_photos)}")
    print(f"Photos encore en attente : {pending}")
    print(f"Documents dans l’inventaire : {len(documents)}")
    print(f"Documents identifiés : {sum(count for status, count in status_counts.items() if status in {'edition_identifiee', 'identifie'})}")
    print(f"Documents restant à identifier : {sum(count for status, count in status_counts.items() if status not in {'edition_identifiee', 'identifie'})}")
    progression_counts = {}
    for document in documents.values():
        step = progression_status(document)
        progression_counts[step] = progression_counts.get(step, 0) + 1
    print("Progression des documents :")
    for step in ("1. A identifier", "2. Identifié", "3. Etat à préciser", "4. Etat connu", "5. Valorisé"):
        print(f"  {step} : {progression_counts.get(step, 0)}")
    print(f"Notes modifiées : {'oui' if notes_changed else 'non'}")
    isbn_alerts = [
        (document_id, document.get("titre") or "[titre inconnu]", (document.get("recherches_bibliographiques") or [{}])[-1].get("contradictions_isbn") or [])
        for document_id, document in sorted(documents.items())
        if (document.get("recherches_bibliographiques") or [{}])[-1].get("contradictions_isbn")
    ]
    if isbn_alerts:
        print("Contradictions ISBN à examiner :")
        for document_id, titre, contradictions in isbn_alerts:
            for contradiction in contradictions:
                print(f"  - {document_id} — {titre} : ISBN recherché {contradiction.get('isbn_recherche')} ; notice {', '.join(contradiction.get('isbns_notice') or [])} ; {contradiction.get('url_notice') or 'URL inconnue'}")

    if new_photos:
        print("Nouvelles : " + " | ".join(r["path"] for r in new_photos))
    if changed_photos:
        print("Modifiées : " + " | ".join(r["path"] for r in changed_photos))
    if missing_photos:
        print("Absentes : " + " | ".join(r["path"] for r in missing_photos))

    if pending or missing_photos or notes_changed:
        print("Situation : ACTIONS / ANALYSE À POURSUIVRE")
    else:
        print("Situation : RIEN DE NOUVEAU À TRAITER")
    print("=" * 60)


def field_schema(*, lecture: bool = False):
    """Schéma d'un champ observé ; les champs bibliographiques portent un statut de lecture."""
    properties = {
        "valeur": {"type": ["string", "null"]},
        "confiance": {"type": "string", "enum": ["élevée", "moyenne", "faible"]},
        "origine": {"type": "string", "enum": ["photo", "non_etablie"]},
    }
    required = ["valeur", "confiance", "origine"]
    if lecture:
        properties["statut_lecture"] = {
            "type": "string",
            "enum": ["lisible", "incertain", "non_visible"],
        }
        required.append("statut_lecture")
    return {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }


ETAT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["appreciation", "motif"],
    "properties": {
        "appreciation": {"type": "string", "enum": ["tres_bon", "bon", "correct", "mauvais", "non_evaluable"]},
        "motif": {"type": "string"},
    },
}


def response_schema():
    """Contrat JSON de l'analyse visuelle, sans recherche ni identification Web."""
    bibliographic_field = field_schema(lecture=True)
    document = {
        "type": "object",
        "properties": {
            "reference": {"type": "string"},
            "document_id_reference": {"type": ["string", "null"]},
            "position": {"type": "string"},
            "type_document": {"type": "string", "enum": ["livre", "magazine", "guide", "autre", "indetermine"]},
            "titre": bibliographic_field,
            "sous_titre": bibliographic_field,
            "auteurs": bibliographic_field,
            "editeur": bibliographic_field,
            "edition": bibliographic_field,
            "isbn": bibliographic_field,
            "collection": bibliographic_field,
            "annee_edition": bibliographic_field,
            "annee_impression": bibliographic_field,
            "date_depot_legal": bibliographic_field,
            "description_illustration": {"type": "string"},
            "autres_textes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "texte": {"type": "string"},
                        "statut_lecture": {"type": "string", "enum": ["lisible", "incertain"]},
                        "hesitation": {"type": "string"},
                    },
                    "required": ["texte", "statut_lecture", "hesitation"],
                    "additionalProperties": False,
                },
            },
            "etat_general": ETAT_SCHEMA,
        },
        "required": [
            "reference", "document_id_reference", "position", "type_document",
            "titre", "sous_titre", "auteurs", "editeur", "edition", "isbn", "collection",
            "annee_edition", "annee_impression", "date_depot_legal",
            "description_illustration", "autres_textes", "etat_general",
        ],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {
            "documents": {"type": "array", "items": document},
        },
        "required": ["documents"],
        "additionalProperties": False,
    }


def _is_flex_unavailable_error(exc: Exception) -> bool:
    """Reconnaît exclusivement l'erreur temporaire propre au traitement Flex."""
    if getattr(exc, "code", None) == "flex_unavailable":
        return True
    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        error = body.get("error")
        if isinstance(error, dict) and error.get("code") == "flex_unavailable":
            return True
    response = getattr(exc, "response", None)
    json_method = getattr(response, "json", None)
    if callable(json_method):
        try:
            payload = json_method()
        except Exception:
            payload = None
        if isinstance(payload, dict):
            error = payload.get("error")
            if isinstance(error, dict) and error.get("code") == "flex_unavailable":
                return True
    return False


def analyze_photo(
    photo_file: Path,
    precision: str = "",
    ref: str = "non",
    *,
    use_last_response: bool = False,
    last_response_path: Path = DEFAULT_LAST_RESPONSE_FILE,
    temperature: float | None = None,
) -> dict:
    """Analyse une photo ou rejoue la dernière sortie brute sans appeler l'API."""
    if use_last_response:
        if not last_response_path.is_file():
            raise RuntimeError(f"Fichier de dernière réponse introuvable : {last_response_path}")
        saved_content = last_response_path.read_text(encoding="utf-8")
        # Compatibilité : les anciens fichiers ne contiennent que la sortie JSON brute.
        raw_marker = "===== DÉBUT DE LA SORTIE BRUTE DE L’API ====="
        if raw_marker in saved_content:
            raw_response = saved_content.split(raw_marker, 1)[1]
            if raw_response.startswith("\n"):
                raw_response = raw_response[1:]
            end_marker = "\n===== FIN DE LA SORTIE BRUTE DE L’API ====="
            if end_marker in raw_response:
                raw_response = raw_response.split(end_marker, 1)[0]
        else:
            raw_response = saved_content
    else:
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY n'est pas définie.")
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("Le paquet Python openai doit être installé dans l'environnement actif.") from exc

        encoded = base64.b64encode(photo_file.read_bytes()).decode("ascii")
        suffix = photo_file.suffix.lower()
        mime = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
                ".webp": "image/webp", ".tif": "image/tiff", ".tiff": "image/tiff"}.get(suffix)
        if mime is None:
            raise RuntimeError(f"Format d'image non pris en charge par l'appel API : {suffix}")

    prompt = """Voici une photo d'un ou plusieurs documents.
Chaque document est du type livre ou magasine ou guide ou autre.

Pour chaque document que tu identifies sur la photo tu dois :
1. identifier son type
2. reconnaitre les textes et comprendre à quoi ils correspondent : titre, sous-titre, auteur(s), éditeur, collection, isbn, dates, etc (champs de la structure JSON pour la réponse)
3. décrire en une phrase simple l'illustration si elle existe
4. donner un état général par rapport à ce que tu vois : « tres_bon » (aspect proche du neuf), « bon » (usure normale d'un livre lu ou ancien : petites marques, légers frottements), « correct » (dégradations nettement visibles mais document complet), « mauvais » (déchirures, taches importantes, couverture abîmée) ou « non_evaluable »

Attention :
- ne prend pas des reflets pour des défauts du document
- n'invente pas de fausse information et soit factuel

Répond uniquement avec la structure JSON fournie en faisant correspondre au mieux ce que tu as lu avec les champs proposés ("origine" vaut "photo" et "confiance" parmi [élevée|moyenne|faible])."""

    if precision.strip():
        prompt += (
            "\n\nLa précision suivante est une information fiable fournie par l’utilisateur. "
            "Tiens-en compte pour analyser cette photo.\n"
        )
        if ref.strip().casefold() == "oui":
            prompt += (
                "Si cette précision mentionne explicitement un identifiant de document connu, "
                "associe à cet identifiant les informations détectées qui le concernent et "
                "restitue-le dans « document_id_reference ». N'invente aucun identifiant.\n"
            )
        prompt += "\nPrécision fournie par l’utilisateur :\n" + precision.strip()

    if not use_last_response:
        client = OpenAI()
        request_kwargs = {
            "model": MODEL,
            "max_output_tokens": 12000,
            "input": [{"role": "user", "content": [
                {"type": "input_text", "text": prompt},
                {"type": "input_image", "image_url": "data:" + mime + ";base64," + encoded, "detail": "auto"},
            ]}],
            "text": {"format": {"type": "json_schema", "name": "inventaire_photo", "strict": True, "schema": response_schema()}},
            **({"temperature": temperature} if temperature is not None else {}),
        }
        service_tier_used = "flex"
        # Le SDK peut réessayer automatiquement certaines erreurs HTTP (dont des 429).
        # Les désactiver pour Flex permet de respecter exactement les délais ci-dessous.
        flex_client = client.with_options(max_retries=0)
        for attempt, delay in enumerate((30, 60, None)):
            try:
                response = flex_client.responses.create(**request_kwargs, service_tier="flex")
                break
            except Exception as exc:
                if not _is_flex_unavailable_error(exc):
                    raise
                if delay is not None:
                    time.sleep(delay)
                    continue
                # Après l'appel initial et les deux réessais Flex, repli standard.
                # Le client standard conserve les réglages de réessai habituels du SDK.
                response = client.responses.create(**request_kwargs)
                service_tier_used = "standard (repli après flex_unavailable)"
        raw_response = response.output_text or ""

        # Capturer les métadonnées disponibles sur l'objet de réponse, sans supposer
        # que toutes les versions du SDK exposent exactement les mêmes champs.
        usage = getattr(response, "usage", None)
        if usage is not None and hasattr(usage, "model_dump"):
            usage = usage.model_dump()
        elif usage is not None and not isinstance(usage, (dict, list, str, int, float, bool)):
            usage = str(usage)
        metadata = {
            "response_id": getattr(response, "id", None),
            "status": getattr(response, "status", None),
            "incomplete_details": getattr(response, "incomplete_details", None),
            "usage": usage,
        }
        if hasattr(metadata["incomplete_details"], "model_dump"):
            metadata["incomplete_details"] = metadata["incomplete_details"].model_dump()
        elif metadata["incomplete_details"] is not None and not isinstance(metadata["incomplete_details"], (dict, list, str, int, float, bool)):
            metadata["incomplete_details"] = str(metadata["incomplete_details"])

        # Les métadonnées et le prompt sont séparés de la sortie JSON,
        # que --last-reponse extrait sans les transmettre à json.loads.
        diagnostic = (
            "===== MÉTADONNÉES DE L’APPEL API =====\n"
            f"Modèle appelé : {MODEL}\n"
            f"Limite max_output_tokens : 12000\n"
            f"Niveau de traitement API : {service_tier_used}\n"
            f"Température : {temperature if temperature is not None else 'paramètre par défaut du modèle'}\n"
            f"Outils externes : aucun\n"
            f"Photo envoyée : {photo_file.name}\n"
            f"Date/heure de sauvegarde : {datetime.now().astimezone().isoformat(timespec='seconds')}\n"
            "Paramètres complémentaires :\n"
            "- Aucun outil externe ; analyse fondée sur la photo fournie\n"
            "- Image : detail=auto\n"
            "- Format de sortie : JSON Schema strict, nom inventaire_photo\n"
            "Métadonnées de réponse (statut, identifiant, tokens consommés et détails disponibles) :\n"
            + json.dumps(metadata, ensure_ascii=False, indent=2, default=str)
            + "\n\n===== PROMPT COMPLET ENVOYÉ =====\n"
            + prompt
            + "\n\n===== DÉBUT DE LA SORTIE BRUTE DE L’API =====\n"
            + raw_response
            + "\n===== FIN DE LA SORTIE BRUTE DE L’API =====\n"
        )
        # Sauvegarder avant json.loads : même une sortie tronquée conserve son diagnostic.
        last_response_path.write_text(diagnostic, encoding="utf-8")
    result = json.loads(raw_response)
    if not isinstance(result, dict) or not isinstance(result.get("documents"), list):
        raise RuntimeError("La réponse IA ne respecte pas le contrat attendu.")
    for index, document in enumerate(result["documents"], start=1):
        if not isinstance(document, dict) or not isinstance(document.get("titre"), dict):
            raise RuntimeError("Une détection IA ne respecte pas le contrat attendu.")
        document.setdefault("reference", "detection_" + str(index))
        document.setdefault("position", "position non précisée")
        document.setdefault("type_document", "indetermine")
    return result


def _dedoublonner_autres(autres, auteurs, editeur_lignes):
    """Écarte les mentions de couverture qui répètent auteur ou éditeur."""
    deja = {_norm(x) for x in [*auteurs, *editeur_lignes] if x}
    return [
        item for item in autres
        if _norm(item.get("texte", "")) not in deja
    ]


def _etat_propose_depuis_document(document):
    """Convertit l'état global du contrat 0.9 vers la proposition persistante."""
    raw = document.get("etat_general")
    if isinstance(raw, dict) and "appreciation" in raw:
        motif = raw.get("motif", "")
        return {
            "appreciation": raw.get("appreciation", "non_evaluable"),
            "motif": motif.strip() if isinstance(motif, str) else "",
            "origine": "photo",
            "statut": "propose_non_verifie",
        }
    # Une ancienne phrase libre ne doit pas être réinterprétée comme un motif fiable.
    return {
        "appreciation": "non_evaluable",
        "motif": "",
        "origine": raw.get("origine", "photo") if isinstance(raw, dict) else "photo",
        "statut": "propose_non_verifie",
    }


def document_to_detection(document: dict) -> dict:
    """Convertit le contrat IA 1.1 en détection persistante avec champs bibliographiques distincts."""
    def field(key):
        raw = document.get(key, {})
        if not isinstance(raw, dict):
            return {"valeur": None, "confiance": None, "origine": None, "statut_lecture": "non_visible"}
        value = raw.get("valeur")
        if key in {"titre", "sous_titre", "auteurs"} and isinstance(value, str):
            value = " ".join(value.split())
        return {
            "valeur": value, "confiance": raw.get("confiance"),
            "origine": raw.get("origine"), "statut_lecture": raw.get("statut_lecture"),
        }

    authors_text = field("auteurs")["valeur"]
    authors = [part.strip() for part in authors_text.split(";") if part.strip()] if authors_text else []
    other_texts = document.get("autres_textes", [])
    other_texts = _dedoublonner_autres(other_texts, authors, [field("editeur")["valeur"] or ""])
    proposed = {key: field(key) for key in (
        "titre", "sous_titre", "auteurs", "editeur", "edition", "isbn", "collection",
        "annee_edition", "annee_impression", "date_depot_legal",
    )}
    # Compatibilité des noms utilisés par les traitements aval.
    proposed["edition_editeur"] = proposed["editeur"]
    proposed["autres_textes"] = other_texts
    return {
        "reference": document.get("reference"),
        "document_id_reference": document.get("document_id_reference"),
        "position": document.get("position"),
        "type_document": document.get("type_document", "indetermine"),
        "identification_proposee": proposed,
        "description_illustration": document.get("description_illustration", ""),
        "autres_textes": other_texts,
        "etat_general": _etat_propose_depuis_document(document),
        "rapprochement": {"statut": "a_examiner", "candidats_document_ids": []},
    }

def _integrer_etat_propose(state, photo_path, document_id, detection):
    """Intègre prudemment l'appréciation globale et son motif court."""
    proposed = detection.get("etat_general", {})
    if not isinstance(proposed, dict):
        return
    appreciation = proposed.get("appreciation")
    valid_appreciations = {"tres_bon", "bon", "correct", "mauvais", "non_evaluable"}
    if appreciation not in valid_appreciations:
        return
    book = state["documents"][document_id]
    etat = book.setdefault("etat_general", {})
    photo_role = state.get("photos", {}).get(photo_path, {}).get("role", "identification")
    current = etat.get("appreciation")
    if etat.get("base") and photo_role != "etat" and current in valid_appreciations - {"non_evaluable"}:
        return
    if (
        current in (None, "", "non_evaluable")
        or current not in valid_appreciations
        or (photo_role == "etat" and appreciation != "non_evaluable")
    ):
        etat["appreciation"] = appreciation
        motif = proposed.get("motif")
        etat["observations"] = [motif.strip()] if isinstance(motif, str) and motif.strip() else []
    etat.pop("defauts", None)
    etat.pop("informations_non_visibles", None)
    if not etat.get("base"):
        etat["base"] = "premiere_photo_presumee_representative"
    add_photo_source_to_document(state, document_id, photo_path, "etat_general", {
        "valeur": {
            "appreciation": appreciation,
            "motif": proposed.get("motif", ""),
        },
        "origine": proposed.get("origine", "photo"),
        "statut": proposed.get("statut", "propose_non_verifie"),
    })


def _integrate_referenced_detection(state: dict, photo_path: str, document_id: str, detection: dict) -> None:
    """Intègre prudemment les observations d'une photo explicitement rattachée par TXT."""
    book = state["documents"][document_id]
    proposed = detection.get("identification_proposee", {})
    field_map = {
        "titre": "titre", "sous_titre": "sous_titre", "auteurs": "auteurs",
        "editeur": "editeur", "edition": "edition", "collection": "collection",
        "isbn": "isbn", "annee_edition": "annee_edition",
        "annee_impression": "annee_impression", "date_depot_legal": "date_depot_legal",
    }
    conflicts = detection.setdefault("conflits_identification", [])
    for target_field, proposed_key in field_map.items():
        item = proposed.get(proposed_key, {})
        if not isinstance(item, dict):
            item = {}
        raw_value = item.get("valeur")
        value = raw_value
        if target_field == "auteurs" and value not in (None, "", []):
            value = [part.strip() for part in str(value).split(";") if part.strip()]
        # Garder la provenance de chaque champ, même si la valeur est non visible.
        add_photo_source_to_document(state, document_id, photo_path, target_field, {
            "valeur": value, "confiance": item.get("confiance"),
            "origine": item.get("origine"),
            "statut_lecture": item.get("statut_lecture"),
        })
        if raw_value in (None, "", []):
            continue
        current = book.get(target_field)
        if current in (None, "", []):
            book[target_field] = value
        elif not _same_note_value(target_field, current, value):
            conflict = {
                "champ": target_field, "valeur_existante": current,
                "valeur_observee": value, "photo": photo_path,
                "confiance": item.get("confiance"),
                "origine": item.get("origine"),
                "statut_lecture": item.get("statut_lecture"),
            }
            if conflict not in conflicts:
                conflicts.append(conflict)
    visual_description = detection.get("description_illustration", "")
    if visual_description and not book.get("description_illustration"):
        book["description_illustration"] = visual_description
    add_photo_source_to_document(state, document_id, photo_path, "description_illustration", {
        "valeur": visual_description, "origine": "photo",
    })
    other_texts = detection.get("autres_textes", [])
    if other_texts and not book.get("autres_textes"):
        book["autres_textes"] = other_texts
    add_photo_source_to_document(state, document_id, photo_path, "autres_textes", {
        "valeur": other_texts, "origine": "photo",
    })
    _integrer_etat_propose(state, photo_path, document_id, detection)
    if conflicts:
        detection["action_utilisateur_suggeree"] = (
            "Des informations observées contredisent la fiche existante ; "
            "les valeurs existantes ont été conservées et les conflits sont tracés."
        )
    book["updated_at"] = now_iso()


def apply_photo_analysis(state: dict, photo_path: str, result: dict) -> None:
    """Persiste les propositions IA dans la fiche photo sans fusionner automatiquement les documents."""
    if photo_path not in state["photos"]:
        raise KeyError("Photo inconnue : " + photo_path)
    photo = state["photos"][photo_path]
    detections = [document_to_detection(doc) for doc in result["documents"]]
    photo["analysis"] = {
        "analyzed_at": now_iso(),
        "observations_generales": result.get("observations_generales", ""),
        "document_principal_reference": result.get("document_principal_reference"),
        "documents_detectes": detections,
        "model": MODEL,
        "contract_version": "1.1",
    }
    photo["analysis_status"] = "analyzed_pending_reconciliation"

    # Un titre ressemblant à celui d'un document existant déclenche une revue,
    # jamais une fusion automatique : plusieurs exemplaires physiques sont possibles.
    for detection in detections:
        referenced_id = detection.get("document_id_reference")
        if referenced_id:
            if referenced_id in state.get("documents", {}):
                detection["rapprochement"] = {
                    "statut": "cible_indiquee_par_txt",
                    "candidats_document_ids": [referenced_id],
                }
                # Référence explicite fournie par l'utilisateur : rattachement
                # bidirectionnel et intégration prudente des observations.
                associate_photo_to_document(
                    state, photo_path, referenced_id,
                    role=state["photos"][photo_path].get("role", "identification"),
                )
                _integrate_referenced_detection(state, photo_path, referenced_id, detection)
                continue
            detection["rapprochement"] = {
                "statut": "identifiant_reference_inconnu",
                "candidats_document_ids": [],
            }
            detection["action_utilisateur_suggeree"] = (
                f"L'identifiant {referenced_id} fourni dans le texte complémentaire "
                "n'existe pas dans l'inventaire chargé ; vérifier le texte."
            )
            continue
        title = (detection.get("identification_proposee", {}).get("titre", {}).get("valeur") or "").strip().casefold()
        if not title:
            detection["rapprochement"] = {"statut": "identification_insuffisante", "candidats_document_ids": []}
            detection["action_utilisateur_suggeree"] = "Fournir une photo plus lisible de la couverture ou de la page de titre."
            continue
        candidates = []
        for document_id, document in state.get("documents", {}).items():
            known_title = (document.get("titre") or "").strip().casefold()
            if known_title and known_title == title:
                candidates.append(document_id)

        # Un titre identique ne suffit pas à identifier le même exemplaire :
        # pour les périodiques, l'année ou le numéro peut distinguer les éditions.
        proposed = detection.get("identification_proposee", {})
        distinctive_fields = (
            ("isbn", "isbn"),
            ("edition", "edition"),
            ("collection", "collection"),
            ("annee_edition", "annee_edition"),
            ("annee_impression", "annee_impression"),
            ("date_depot_legal", "date_depot_legal"),
            ("sous_titre", "sous_titre"),
        )

        def normalized(value):
            if value is None:
                return ""
            if isinstance(value, (int, float)):
                return str(value).strip().casefold()
            if isinstance(value, str):
                return " ".join(value.split()).strip().casefold()
            return ""

        unresolved_candidates = []
        for candidate_id in candidates:
            document = state["documents"][candidate_id]
            has_conflict = False
            for proposed_key, document_key in distinctive_fields:
                proposed_value = normalized((proposed.get(proposed_key) or {}).get("valeur"))
                existing_value = normalized(document.get(document_key))
                if proposed_value and existing_value and proposed_value != existing_value:
                    has_conflict = True
                    break
            if not has_conflict:
                unresolved_candidates.append(candidate_id)

        # Si chaque candidat existant contredit au moins une donnée distinctive
        # visible, il s'agit d'un exemplaire différent. Si les données manquent
        # ou concordent, on garde la revue manuelle pour éviter un doublon.
        detection["rapprochement"] = {
            "statut": "ambigu" if unresolved_candidates else "nouvel_document_a_valider",
            "candidats_document_ids": unresolved_candidates if unresolved_candidates else candidates,
        }
    photo["analysis_status"] = "analyzed"


def progression_status(document: dict) -> str:
    """Retourne le statut forcé par notes.txt, sinon l'étape calculée."""
    statut_force = document.get("statut_force")
    if statut_force in STATUTS_PROGRESSION:
        return statut_force
    identification = document.get("identification") or {}
    if identification.get("statut") not in {"edition_identifiee", "identifie"}:
        return "1. A identifier"
    if "etat_general" not in document:
        return "2. Identifié"
    etat = document.get("etat_general") or {}
    if identification.get("photos_complementaires"):
        return "3. Etat à préciser"
    appreciation = etat.get("appreciation")
    if appreciation == "non_evaluable":
        return "3. Etat à préciser"
    if appreciation not in {"tres_bon", "bon", "correct", "mauvais"} and not (etat.get("observations") or []):
        return "3. Etat à préciser"
    valuation = document.get("valorisation") or {}
    if isinstance(valuation, dict) and (
        valuation.get("statut") in {"valorise", "valorisé", "terminee", "terminée"}
        or valuation.get("date_valorisation")
    ):
        return "5. Valorisé"
    return "4. Etat connu"


def export_csv(state: dict, csv_path: Path) -> None:
    """Exporte une ligne par document, avec ses sources et informations manquantes."""
    fields = [
        "document_id", "statut", "type_document", "titre", "sous_titre", "auteurs", "editeur", "collection",
        "annee_impression", "annee_edition", "date_depot_legal", "edition", "isbn",
        "etat_general", "description_illustration", "autres_textes", "etat_general_details",
        "niveau_confiance_identification", "informations_manquantes", "demandes_photo", "photos",
        "statut_identification", "notice_ancrage", "isbns_notice_ancrage", "contradictions_isbn",
        "sources_information",
    ]
    temporary_path = csv_path.with_suffix(csv_path.suffix + ".tmp")
    with temporary_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter=";")
        writer.writeheader()
        for document_id, document in sorted(state.get("documents", {}).items()):
            writer.writerow({
                "document_id": document_id,
                "statut": progression_status(document),
                "type_document": document.get("type_document") or "",
                "titre": document.get("titre") or "",
                "sous_titre": document.get("sous_titre") or "",
                "auteurs": "; ".join(document.get("auteurs") or []),
                "editeur": document.get("editeur") or "",
                "collection": document.get("collection") or "",
                "annee_impression": document.get("annee_impression") or "",
                "annee_edition": document.get("annee_edition") or "",
                "date_depot_legal": document.get("date_depot_legal") or "",
                "edition": document.get("edition") or "",
                "isbn": document.get("isbn") or "",
                "etat_general": (document.get("etat_general") or {}).get("appreciation") or "",
                "description_illustration": document.get("description_illustration") or "",
                "autres_textes": json.dumps(document.get("autres_textes") or [], ensure_ascii=False),
                "etat_general_details": json.dumps(document.get("etat_general") or {}, ensure_ascii=False),
                "niveau_confiance_identification": document.get("identification", {}).get("niveau_confiance") or "",
                "informations_manquantes": "; ".join(document.get("identification", {}).get("informations_manquantes") or []),
                "demandes_photo": "; ".join(f"{champ} : {photo}" for champ, photo in (document.get("identification", {}).get("demandes_photo") or {}).items()),
                "photos": "; ".join(document.get("photos") or []),
                "statut_identification": document.get("identification", {}).get("statut") or "à compléter",
                "notice_ancrage": json.dumps(document.get("identification", {}).get("notice_ancrage"), ensure_ascii=False) if document.get("identification", {}).get("notice_ancrage") else "",
                "isbns_notice_ancrage": json.dumps(document.get("identification", {}).get("isbns_notice_ancrage") or [], ensure_ascii=False),
                "contradictions_isbn": json.dumps((document.get("recherches_bibliographiques") or [{}])[-1].get("contradictions_isbn", []), ensure_ascii=False),
                "sources_information": json.dumps(document.get("sources_information") or [], ensure_ascii=False),
            })
    temporary_path.replace(csv_path)


def export_csv_reduit(state: dict, csv_path: Path) -> None:
    """Exporte une vue de consultation compacte, sans modifier les données persistantes."""
    fields = [
        "id", "type", "titre", "auteurs", "editeur", "annee_impression", "annee_edition", "date_depot_legal", "isbn",
        "identif", "mentions", "etat", "manque",
    ]
    temporary_path = csv_path.with_suffix(csv_path.suffix + ".tmp")
    with temporary_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="|")
        writer.writeheader()
        for document_id, document in sorted(state.get("documents", {}).items()):
            identification = document.get("identification") or {}
            anchor = identification.get("notice_ancrage") or {}
            status = identification.get("statut") or ""
            source = str(anchor.get("source") or "")
            if status == "edition_identifiee":
                if source.startswith("BnF"):
                    identif = "confirmée (BnF)"
                elif source:
                    identif = f"confirmée ({source})"
                else:
                    identif = "confirmée"
            elif status == "identifie":
                identif = "confirmée"
            elif status == "a_confirmer_par_recherche_bibliographique":
                identif = "à confirmer"
            elif status in {"provisoire", "a_completer"}:
                identif = "provisoire"
            else:
                identif = "à identifier"

            mentions = []
            for item in document.get("autres_textes") or []:
                if isinstance(item, dict):
                    value = str(item.get("texte") or "").strip()
                else:
                    value = str(item or "").strip()
                if value and value not in mentions:
                    mentions.append(value)

            etat_general = document.get("etat_general") or {}
            appreciation = etat_general.get("appreciation") or ""
            observations = [
                str(value).strip()
                for value in (etat_general.get("observations") or [])
                if str(value).strip()
            ]
            etat = ", ".join(([appreciation] if appreciation else []) + observations)

            missing_fields = [
                (field, label)
                for field, label in (
                    ("editeur", "éditeur"),
                    ("collection", "collection"),
                    ("annee_edition", "année"),
                    ("edition", "édition"),
                    ("annee_impression", "impression"),
                    ("date_depot_legal", "dépôt légal"),
                    ("isbn", "ISBN"),
                )
                if document.get(field) in (None, "", [])
            ]
            writer.writerow({
                "id": document_id,
                "type": document.get("type_document") or "",
                "titre": document.get("titre") or "",
                "auteurs": "; ".join(document.get("auteurs") or []),
                "editeur": document.get("editeur") or "",
                "annee_impression": document.get("annee_impression") or "",
                "annee_edition": document.get("annee_edition") or "",
                "date_depot_legal": document.get("date_depot_legal") or "",
                "isbn": document.get("isbn") or "",
                "identif": identif,
                "mentions": " ; ".join(mentions),
                "etat": etat,
                "manque": " ; ".join(label for _, label in missing_fields),
            })
    temporary_path.replace(csv_path)


def integrate_unambiguous_detections(state: dict) -> None:
    """Crée les nouveaux documents et distingue les exemplaires multiples visibles sur une même photo."""
    distinctive_fields = (
        "isbn", "edition", "collection", "annee_edition",
        "annee_impression", "date_depot_legal", "sous_titre",
    )

    def normalized(value):
        if value is None:
            return ""
        if isinstance(value, (int, float)):
            return str(value).strip().casefold()
        if isinstance(value, str):
            return " ".join(value.split()).strip().casefold()
        return ""

    for photo_path, photo in state.get("photos", {}).items():
        analysis = photo.get("analysis", {})
        detections = analysis.get("documents_detectes", [])

        # Une photo peut montrer plusieurs exemplaires du même périodique.
        # Si leurs positions sont distinctes et qu'au moins un champ bibliographique
        # visible diffère entre eux, ces détections sont des objets distincts.
        by_title = {}
        for item in detections:
            item_proposed = item.get("identification_proposee", {})
            item_title = normalized((item_proposed.get("titre") or {}).get("valeur"))
            if item_title:
                by_title.setdefault(item_title, []).append(item)
        for same_title_detections in by_title.values():
            positions = {
                normalized(item.get("position"))
                for item in same_title_detections
                if normalized(item.get("position"))
            }
            if len(positions) < 2:
                continue
            has_distinctive_difference = False
            for field in distinctive_fields:
                values = {
                    normalized((item.get("identification_proposee", {}).get(field) or {}).get("valeur"))
                    for item in same_title_detections
                }
                values.discard("")
                if len(values) > 1:
                    has_distinctive_difference = True
                    break
            if has_distinctive_difference:
                for item in same_title_detections:
                    reconciliation = item.setdefault("rapprochement", {})
                    if reconciliation.get("statut") == "ambigu" and not item.get("document_id"):
                        reconciliation["statut"] = "nouvel_document_a_valider"

        for detection in detections:
            reconciliation = detection.get("rapprochement", {})
            if reconciliation.get("statut") != "nouvel_document_a_valider":
                continue
            proposed = detection.get("identification_proposee", {})
            title = proposed.get("titre", {}).get("valeur")
            if not title:
                reconciliation["statut"] = "identification_insuffisante"
                continue
            authors_text = proposed.get("auteurs", {}).get("valeur")
            authors = [part.strip() for part in authors_text.split(";") if part.strip()] if authors_text else []
            publisher = proposed.get("editeur", {}).get("valeur")
            edition_text = proposed.get("edition", {}).get("valeur")
            collection = proposed.get("collection", {}).get("valeur")
            subtitle = proposed.get("sous_titre", {}).get("valeur")
            isbn = proposed.get("isbn", {}).get("valeur")
            year = proposed.get("annee_edition", {}).get("valeur")
            print_date = proposed.get("annee_impression", {}).get("valeur")
            legal_date = proposed.get("date_depot_legal", {}).get("valeur")
            # Do not create the same physical record twice for the same detection.
            existing_detection_id = detection.get("document_id")
            if existing_detection_id in state.get("documents", {}):
                continue
            document_id = create_document(
                state, type_document=detection.get("type_document"), titre=title,
                auteurs=authors, editeur=publisher, collection=collection, edition=edition_text,
                isbn=isbn, annee_edition=year, annee_impression=print_date, date_depot_legal=legal_date,
                description_illustration=detection.get("description_illustration", ""),
                autres_textes=detection.get("autres_textes", []),
            )
            detection["document_id"] = document_id
            associate_photo_to_document(
                state, photo_path, document_id,
                role=photo.get("role", "identification"),
            )
            document = state["documents"][document_id]
            document["sous_titre"] = subtitle
            document["description_illustration"] = detection.get("description_illustration", "")
            document["autres_textes"] = detection.get("autres_textes", [])
            document["identification"]["statut"] = "provisoire"
            document["identification"]["niveau_confiance"] = proposed.get("titre", {}).get("confiance")
            missing = []
            # Ces champs sont utiles mais ne constituent pas à eux seuls
            # des conditions universelles d'identification.
            document["identification"]["informations_manquantes"] = []
            document["identification"]["statut"] = "a_confirmer_par_recherche_bibliographique"
            complementary = []
            document["identification"]["photos_complementaires"] = complementary
            _integrer_etat_propose(state, photo_path, document_id, detection)
            for field_name, proposed_key in [
                ("titre", "titre"), ("sous_titre", "sous_titre"), ("auteurs", "auteurs"),
                ("editeur", "editeur"), ("edition", "edition"), ("collection", "collection"),
                ("isbn", "isbn"), ("annee_edition", "annee_edition"),
                ("annee_impression", "annee_impression"), ("date_depot_legal", "date_depot_legal"),
            ]:
                item = proposed.get(proposed_key, {})
                add_photo_source_to_document(state, document_id, photo_path, field_name, {
                    "valeur": item.get("valeur"),
                    "confiance": item.get("confiance"),
                    "origine": item.get("origine"),
                    "statut_lecture": item.get("statut_lecture"),
                })
            add_photo_source_to_document(
                state, document_id, photo_path, "description_illustration",
                {"valeur": detection.get("description_illustration", ""), "origine": "photo"},
            )
            add_photo_source_to_document(
                state, document_id, photo_path, "autres_textes",
                {"valeur": detection.get("autres_textes", []), "origine": "photo"},
            )
            reconciliation["statut"] = "document_cree_provisoirement"
    validate_state_invariants(state)


def refresh_missing_information(state: dict) -> None:
    """Recalcule les indices absents sans en faire des conditions obligatoires d'identification."""
    optional_fields = [
        ("editeur", "éditeur/mentions d’édition"),
        ("collection", "collection"),
        ("annee_edition", "année de publication"),
        ("edition", "précision d’édition"),
        ("annee_impression", "année d’impression"),
        ("date_depot_legal", "date de dépôt légal"),
        ("isbn", "ISBN (si cette publication en comporte un)"),
    ]
    for book in state.get("documents", {}).values():
        identification = book.setdefault("identification", {})
        missing = [
            label for field, label in optional_fields
            if book.get(field) in (None, "", [])
        ]
        identification["informations_manquantes"] = missing
        photo_pour_champ = {
            "isbn": "code-barres / 4e de couverture",
            "edition": "page de titre et son verso",
            "date_depot_legal": "verso de la page de titre ou achevé d'imprimer (dernière page)",
            "annee_impression": "achevé d'imprimer (dernière page)",
            "collection": "page de titre ou bandeau de couverture",
        }
        identification["demandes_photo"] = {
            field: photo_pour_champ[field]
            for field in photo_pour_champ
            if field in photo_pour_champ and book.get(field) in (None, "", [])
            and not (field == "isbn" and book.get("type_document") == "magazine")
        }


def write_outputs(state: dict, state_path: Path, csv_path: Path) -> None:
    save_state(state_path, state)
    export_csv(state, csv_path)
    export_csv_reduit(state, csv_path.with_name("inventaire_réduit.csv"))


def _norm(s):
    import unicodedata
    s = unicodedata.normalize("NFKD", s or "")
    return " ".join("".join(c.lower() if c.isalnum() else " " for c in s if not unicodedata.combining(c)).split())


def _get_json(url, source):
    """Charge une réponse JSON en réessayant les erreurs HTTP temporaires."""
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": f"InventaireBibliotheque/{VERSION}"})
            with urllib.request.urlopen(req, timeout=15) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code == 429 or 500 <= exc.code <= 599:
                if attempt < 2:
                    try:
                        delay = min(30.0, max(1.0, float(exc.headers.get("Retry-After", 2 ** (attempt + 1)))))
                    except (TypeError, ValueError):
                        delay = float(2 ** (attempt + 1))
                    time.sleep(delay)
                    continue
            return {"_error": f"HTTP {exc.code}: {exc.reason}"}
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            return {"_error": str(exc)}
    return {"_error": f"{source}: échec après plusieurs tentatives"}


def search_bnf(title, authors=None, limit=5, isbn=None):
    if isbn:
        normalized_isbn = "".join(char for char in str(isbn) if char.isdigit() or char.upper() == "X")
        query = 'bib.fuzzyISBN any "' + normalized_isbn + '"'
    else:
        query = 'bib.title all "' + " ".join(title.split()).replace('"', " ") + '"'
        if authors:
            query = "(" + query + ') and bib.author all "' + " ".join(authors.split()).replace('"', " ") + '"'
    url = "https://catalogue.bnf.fr/api/SRU?" + urllib.parse.urlencode({"version":"1.2","operation":"searchRetrieve","query":query,"recordSchema":"unimarcxchange","maximumRecords":str(limit),"startRecord":"1"})
    try:
        req = urllib.request.Request(url, headers={"User-Agent":f"InventaireBibliotheque/{VERSION}"})
        with urllib.request.urlopen(req, timeout=15) as response:
            root = ET.fromstring(response.read())
    except (urllib.error.URLError, TimeoutError, ET.ParseError) as exc:
        return {"source":"BnF Catalogue général (SRU)", "status":"erreur_recherche", "query_url":url, "error":str(exc), "results":[]}
    diagnostics = [
        (node.text or "").strip()
        for node in root.iter()
        if node.tag.rsplit("}", 1)[-1] == "message" and (node.text or "").strip()
    ]
    if diagnostics:
        return {
            "source": "BnF Catalogue général (SRU)",
            "status": "erreur_recherche",
            "query_url": url,
            "searched_at": now_iso(),
            "error": "Diagnostic SRU : " + " | ".join(diagnostics),
            "results": [],
        }
    results = []
    # Ne traiter que le record MARC interne, pas son enveloppe SRU.
    for rec in root.iter():
        if rec.tag.rsplit("}", 1)[-1] != "record":
            continue
        if not any(child.tag.rsplit("}", 1)[-1] in {"leader", "controlfield", "datafield"} for child in rec):
            continue
        fields = {}
        for node in rec.iter():
            local = node.tag.rsplit("}", 1)[-1]
            if local not in {"datafield", "controlfield"}:
                continue
            tag = node.attrib.get("tag", "")
            if local == "controlfield":
                value = (node.text or "").strip()
                if tag in {"001", "003"} and value:
                    fields.setdefault(tag, []).append(value)
                continue
            for subfield in node:
                if subfield.tag.rsplit("}", 1)[-1] != "subfield":
                    continue
                code = subfield.attrib.get("code", "")
                value = (subfield.text or "").strip()
                if value:
                    fields.setdefault(tag + "$" + code, []).append(value)
        if not fields:
            continue
        titles = fields.get("200$a", [])
        authors_found = fields.get("200$f", []) + fields.get("700$a", []) + fields.get("701$a", []) + fields.get("702$a", [])
        publishers = fields.get("210$c", [])
        dates = fields.get("210$d", [])
        for raw in fields.get("100$a", []):
            import re
            match = re.search(r"(?:^|[a-z])(\d{4})(?:\s|$)", raw)
            if match:
                dates.append(match.group(1))
        identifiers = []
        for value in fields.get("010$a", []):
            normalized = _isbn_digits(value)
            identifiers.append(normalized or value)
        identifiers.extend(fields.get("001", []))
        identifiers.extend(fields.get("003", []))
        url_notice = next((value for value in identifiers if "catalogue.bnf.fr/ark:/12148/" in value), None)
        if not url_notice:
            url_notice = next((value for value in fields.get("003", []) if "ark:/12148/" in value), None)
        if titles or authors_found or publishers or identifiers:
            results.append({
                "titre": titles, "auteurs": authors_found, "editeurs": publishers,
                "dates": dates, "identifiants": list(dict.fromkeys(identifiers)),
                "url_notice": url_notice,
                "niveau_notice": "edition" if fields.get("010$a") else "indetermine",
            })
        if len(results) >= limit:
            break
    return {"source":"BnF Catalogue général (SRU)", "status":"resultats" if results else "aucun_resultat", "query_url":url, "searched_at":now_iso(), "results":results}


def search_open_library(title, authors=None, limit=5, isbn=None):
    params={"title":title,"limit":str(limit)}
    if isbn:
        params={"isbn":isbn,"limit":str(limit)}
    elif authors:
        params["author"]=authors
    url="https://openlibrary.org/search.json?"+urllib.parse.urlencode(params)
    data=_get_json(url,"Open Library")
    if "_error" in data: return {"source":"Open Library","status":"erreur_recherche","query_url":url,"error":data["_error"],"results":[]}
    results=[]
    for d in data.get("docs",[])[:limit]:
        key=d.get("key")
        results.append({"titre":[d["title"]] if d.get("title") else [],"auteurs":d.get("author_name",[]),"editeurs":d.get("publisher",[])[:5],"dates":[str(d["first_publish_year"])] if d.get("first_publish_year") else [],"identifiants":d.get("isbn",[])[:10],"url_notice":"https://openlibrary.org"+key if key else None})
    return {"source":"Open Library","status":"resultats" if results else "aucun_resultat","query_url":url,"results":results}


def search_google_books(title, authors=None, limit=5, isbn=None):
    query=("isbn:"+isbn) if isbn else ("intitle:"+title+((" inauthor:"+authors) if authors else ""))
    url="https://www.googleapis.com/books/v1/volumes?"+urllib.parse.urlencode({"q":query,"maxResults":str(limit)})
    data=_get_json(url,"Google Books")
    if "_error" in data: return {"source":"Google Books","status":"erreur_recherche","query_url":url,"error":data["_error"],"results":[]}
    results=[]
    for item in data.get("items",[])[:limit]:
        d=item.get("volumeInfo",{})
        results.append({"titre":[d["title"]] if d.get("title") else [],"auteurs":d.get("authors",[]),"editeurs":[d["publisher"]] if d.get("publisher") else [],"dates":[str(d["publishedDate"])] if d.get("publishedDate") else [],"identifiants":[x.get("identifier") for x in d.get("industryIdentifiers",[]) if x.get("identifier")],"url_notice":d.get("infoLink")})
    return {"source":"Google Books","status":"resultats" if results else "aucun_resultat","query_url":url,"results":results}


def _isbn_digits(value):
    """Extrait un ISBN-10/13 d'une valeur de catalogue."""
    import re
    text = str(value or "").upper()
    # Priorité aux groupes de 10 ou 13 chiffres dans les identifiants de notices.
    candidates = re.findall(r"(?<![0-9X])(?:97[89][ -]?)?(?:[0-9][ -]?){9}[0-9X](?![0-9X])", text)
    for candidate in candidates:
        digits = "".join(char for char in candidate if char.isdigit() or char == "X")
        if len(digits) in {10, 13}:
            return digits
    digits = "".join(char for char in text if char.isdigit() or char == "X")
    return digits if len(digits) in {10, 13} else None


def _isbn_valid(value):
    """Vérifie le format et la clé de contrôle d'un ISBN-10 ou ISBN-13."""
    isbn = _isbn_digits(value)
    if not isbn:
        return False
    if len(isbn) == 10:
        if not isbn[:9].isdigit() or not (isbn[9].isdigit() or isbn[9] == "X"):
            return False
        total = sum(int(digit) * weight for digit, weight in zip(isbn[:9], range(10, 1, -1)))
        check = 10 if isbn[9] == "X" else int(isbn[9])
        return (total + check) % 11 == 0
    if len(isbn) == 13 and isbn.isdigit():
        total = sum(int(digit) * (1 if index % 2 == 0 else 3) for index, digit in enumerate(isbn[:12]))
        return (total + int(isbn[12])) % 10 == 0
    return False


def _isbn13_from_10(isbn):
    isbn = _isbn_digits(isbn)
    if not isbn or len(isbn) != 10 or not _isbn_valid(isbn):
        return None
    core = "978" + isbn[:9]
    checksum = (10 - sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(core)) % 10) % 10
    return core + str(checksum)


def _isbn_equivalent(left, right):
    a, b = _isbn_digits(left), _isbn_digits(right)
    if not a or not b or not _isbn_valid(a) or not _isbn_valid(b):
        return False
    if a == b:
        return True
    if len(a) == 10:
        a = _isbn13_from_10(a)
    if len(b) == 10:
        b = _isbn13_from_10(b)
    return bool(a and b and a == b)


def _title_match(record, title):
    wanted = _norm(title)
    return bool(wanted) and any(
        _norm(item) == wanted or (len(wanted) > 12 and wanted in _norm(item))
        for item in record.get("titre", [])
    )


def _author_match(record, authors):
    """Vérifie chaque auteur séparément, y compris ceux regroupés par « et » dans une note."""
    import re

    raw_authors = authors if isinstance(authors, (list, tuple)) else str(authors or "").split(";")
    author_names = []
    for raw_author in raw_authors:
        # Les parenthèses finales indiquent souvent un rôle (« entretiens »),
        # qui ne fait pas partie du nom à comparer.
        value = re.sub(r"\s*\([^()]*\)\s*$", "", str(raw_author or "")).strip()
        for part in re.split(r"\s+(?:et|&)\s+", value, flags=re.IGNORECASE):
            normalized = _norm(part)
            if normalized:
                author_names.append(normalized)
    if not author_names:
        return True
    names = [_norm(item) for item in record.get("auteurs", [])]
    # La BnF présente parfois « Nom Prénom » avec dates et rôles.
    return all(
        any(set(author.split()).issubset(set(name.split())) for name in names)
        for author in author_names if author.split()
    )


_EDITEUR_VIDES = {"editions", "edition", "ed", "eds", "librairie", "les", "la", "le", "de", "du", "des", "et", "paris", "societe", "sa"}


def _editeur_tokens(value):
    return {token for token in _norm(value).split() if token not in _EDITEUR_VIDES}


def _publisher_score(record, publisher):
    """Part des éditeurs de la notice retrouvés dans les lignes lues ; None si inconnu."""
    lues = [tokens for tokens in (_editeur_tokens(part) for part in str(publisher or "").splitlines() if part.strip()) if tokens]
    notice = [tokens for tokens in (_editeur_tokens(value) for value in record.get("editeurs", []) if value) if tokens]
    if not lues or not notice:
        return None
    toutes = set().union(*lues)
    return sum(1 for tokens in notice if tokens <= toutes) / len(notice)


def _publisher_match(record, publisher):
    """Compatibilité : vrai si au moins un éditeur de la notice concorde."""
    score = _publisher_score(record, publisher)
    return score is not None and score > 0


def _notice_year(record):
    return next((str(date)[:4] for date in record.get("dates", [])
                 if len(str(date)[:4]) >= 4 and str(date)[:4][:4].isdigit()), None)


def _year_from_user_note(book):
    note_sources = [
        source for source in book.get("sources_information", [])
        if isinstance(source, dict) and source.get("type") == "note"
        and str(source.get("champ", "")).casefold() in {"annee_edition", "annee", "annee_publication", "année", "année_publication"}
    ]
    if not note_sources:
        return None
    # read_notes applique déjà la dernière ligne utilisateur : privilégier la valeur courante.
    current = str(book.get("annee_edition") or "").strip()[:4]
    if len(current) == 4 and current.isdigit():
        return current
    for source in reversed(note_sources):
        raw = source.get("contenu", source.get("valeur", ""))
        year = str(raw or "").strip()[:4]
        if len(year) == 4 and year.isdigit():
            return year
    return None



def _candidate_isbn_match(record, isbn):
    return bool(isbn) and any(
        _isbn_equivalent(isbn, identifier)
        for identifier in record.get("identifiants", [])
    )


def _record_is_work_level(record):
    """Reconnaît une notice d’œuvre, qui ne suffit pas à identifier une édition."""
    url = str(record.get("url_notice") or "").casefold()
    return record.get("niveau_notice") == "oeuvre" or "/works/" in url or "/work/" in url


def _title_match_or_near(record, title, subtitle=None):
    """Compare une notice au titre seul ou au titre accompagné de son sous-titre."""
    candidates = []
    title = str(title or "").strip()
    subtitle = str(subtitle or "").strip()
    if title:
        candidates.append(title)
        if subtitle:
            candidates.append(f"{title} {subtitle}")
    normalized_candidates = list(dict.fromkeys(_norm(value) for value in candidates if _norm(value)))
    if not normalized_candidates:
        return False
    record_titles = [_norm(value) for value in record.get("titre", []) if value]
    if any(_title_match(record, candidate) for candidate in candidates):
        return True
    return any(
        difflib.SequenceMatcher(None, wanted, actual).ratio() >= 0.85
        for wanted in normalized_candidates
        for actual in record_titles
        if actual
    )


def _title_prefix_match(record, title):
    """Détecte un titre suivi d’un complément (souvent un sous-titre) dans la notice."""
    wanted = _norm(title)
    if not wanted:
        return False
    return any(
        _norm(value).startswith(wanted + " ")
        for value in record.get("titre", [])
        if value
    )


def _title_matches_for_isbn_anchor(record, title, isbn, subtitle=None):
    """Autorise le titre abrégé de la fiche si l’ISBN exact ancre la notice."""
    return (
        _title_match_or_near(record, title, subtitle)
        or (_candidate_isbn_match(record, isbn) and _title_prefix_match(record, title))
    )


def _is_isbn_query(source):
    query = urllib.parse.parse_qs(urllib.parse.urlparse(source.get("query_url", "")).query)
    return any("fuzzyisbn" in value.casefold() or "isbn" in value.casefold() for value in query.get("query", [])) or bool(query.get("isbn"))


def _isbn_values(record):
    return list(dict.fromkeys(value for value in (_isbn_digits(identifier) for identifier in record.get("identifiants", [])) if value and _isbn_valid(value)))


def _record_is_edition_notice(source, record):
    """N’accepte pas une notice d’œuvre comme ancre d’une édition."""
    if _record_is_work_level(record) or not record.get("url_notice"):
        return False
    url = str(record.get("url_notice") or "").casefold()
    if record.get("niveau_notice") == "edition" or "/books/" in url or "books.google." in url or "books.googleusercontent." in url:
        return True
    return source.get("source", "").startswith("BnF") and bool(_isbn_values(record))


def _make_notice_anchor(source, record, isbn, publisher, *, unique_publisher=False):
    if not _record_is_edition_notice(source, record):
        return None
    score = _publisher_score(record, publisher)
    isbn_match = bool(isbn and _candidate_isbn_match(record, isbn))
    if isbn and not isbn_match:
        return None
    if not isbn and not (unique_publisher and score == 1.0):
        return None
    return {"source": source.get("source"), "url_notice": record.get("url_notice"), "isbn_recherche": isbn or None, "isbn_present_dans_notice": isbn_match if isbn else None, "isbns_notice": _isbn_values(record), "score_editeur": score, "annee": _notice_year(record), "niveau_notice": "edition"}


def _find_isbn_contradictions(sources, title, authors, isbn, subtitle=None):
    """Trace les notices d’édition concordantes sur le titre/auteur mais pas sur l’ISBN."""
    if not isbn:
        return []
    contradictions, seen = [], set()
    for source in sources:
        if not _is_isbn_query(source):
            continue
        for record in source.get("results", []):
            if not _title_match_or_near(record, title, subtitle) or not _author_match(record, authors) or not _record_is_edition_notice(source, record):
                continue
            values = _isbn_values(record)
            if not values or any(_isbn_equivalent(isbn, value) for value in values):
                continue
            key = (record.get("url_notice"), tuple(values))
            if key in seen:
                continue
            seen.add(key)
            contradictions.append({"source": source.get("source"), "url_notice": record.get("url_notice"), "isbn_recherche": isbn, "isbns_notice": values, "motif": "Notice d’édition concordante sur le titre/auteur, mais aucun ISBN de la notice n’est équivalent à l’ISBN recherché"})
    return contradictions


def _isbn_query_supports_record(source, record, isbn, title, authors, subtitle=None):
    """Valide prudemment une notice issue d'une requête ISBN si son ISBN n'est pas renvoyé."""
    if not isbn or not _author_match(record, authors):
        return False
    query_url = source.get("query_url", "")
    query = urllib.parse.parse_qs(urllib.parse.urlparse(query_url).query)
    queried_isbns = query.get("isbn", [])
    if not any(_isbn_equivalent(isbn, value) for value in queried_isbns):
        return False
    wanted_titles = [_norm(value) for value in (title, f"{title} {subtitle}" if subtitle else "") if _norm(value)]
    candidate_titles = [_norm(value) for value in record.get("titre", [])]
    return bool(wanted_titles) and any(
        wanted and value and difflib.SequenceMatcher(None, wanted, value).ratio() >= 0.85
        for wanted in wanted_titles for value in candidate_titles
    )


def _bnf_satisfactory(result, title, authors, book=None):
    """Évalue une notice ; un ISBN exact peut primer sur une variation de titre."""
    book = book or {}
    isbn = (book.get("isbn") or "").strip()
    if isbn and not _isbn_valid(isbn):
        # Un ISBN mal formé ne doit pas bloquer la recherche par titre/auteur.
        isbn = ""
    publisher = (book.get("editeur") or "").strip()
    records = result.get("results", [])
    if isbn:
        # Une notice peut omettre l'ISBN malgré une recherche exacte par ISBN.
        # Dans ce cas, accepter uniquement une notice de cette requête, avec auteur
        # concordant et titre très proche ; sinon exiger l'ISBN dans la notice.
        return any(
            (_candidate_isbn_match(record, isbn) and _author_match(record, authors))
            or _isbn_query_supports_record(result, record, isbn, title, authors, book.get("sous_titre"))
            for record in records
        )
    matching = [
        record for record in records
        if _title_match(record, title) and _author_match(record, authors)
    ]
    if publisher:
        scores = [(record, _publisher_score(record, publisher)) for record in matching]
        best = max((score for _, score in scores if score is not None), default=None)
        if best is None or best <= 0:
            return False
        best_records = [record for record, score in scores if score == best]
        if len(best_records) == 1:
            return True
        # Une année explicitement notée par l'utilisateur peut départager un ex æquo.
        note_year = _year_from_user_note(book)
        if note_year:
            year_matches = [record for record in best_records if _notice_year(record) == note_year]
            return len(year_matches) == 1
        return False
    # Si aucun éditeur/ISBN n'est disponible, une notice unique titre/auteur peut suffire.
    return len(matching) == 1


def enrich_bibliographic_candidates(state):
    summary={"documents_recherches":0,"bnf_concordant":0,"catalogues_complementaires":0,"open_library_notices":0,"google_books_notices":0,"documents_sans_notice":0,"documents_avec_erreur":0,"erreurs_sources":0}
    todo=[]
    for oid,book in sorted(state.get("documents",{}).items()):
        title=(book.get("titre") or "").strip()
        if not title: continue
        missing=book.get("identification",{}).get("informations_manquantes",[])
        gaps=[label for field,label in (("editeur","éditeur"),("collection","collection"),("annee_edition","année de publication"),("edition","édition"),("annee_impression","année d’impression"),("date_depot_legal","date de dépôt légal"),("isbn","ISBN à rechercher si présent")) if not book.get(field)]
        isbn_saisi = (book.get("isbn") or "").strip()
        isbn_invalide = bool(isbn_saisi) and not _isbn_valid(isbn_saisi)
        if not gaps and not isbn_invalide and not any(x in missing for x in ("éditeur/édition","année de publication","ISBN")) and book.get("identification", {}).get("statut") not in {"a_confirmer_par_recherche_bibliographique"}: continue
        authors="; ".join(book.get("auteurs") or [])
        hints = {
            "isbn": (book.get("isbn") or "").strip(),
            "annee_edition": str(book.get("annee_edition") or "").strip(),
            "annee_impression": (book.get("annee_impression") or "").strip(),
            "date_depot_legal": (book.get("date_depot_legal") or "").strip(),
            "editeur": (book.get("editeur") or "").strip(),
            "collection": (book.get("collection") or "").strip(),
        }
        signature_payload = json.dumps(
            {"titre": title.casefold(), "auteurs": authors.casefold(), "indices": hints},
            ensure_ascii=False, sort_keys=True,
        )
        sig=hashlib.sha256(signature_payload.encode()).hexdigest()
        hist=book.setdefault("recherches_bibliographiques",[])
        previous = next((
            x for x in reversed(hist)
            if x.get("query_signature") == sig
            and x.get("strategie") == "BnF par ISBN valide puis par titre/auteur si nécessaire, puis catalogues complémentaires"
        ), None)
        if previous:
            if previous.get("status") not in {"erreur_recherche","erreur_partielle"}:
                continue
            # Après une erreur, attendre 24 h avant une nouvelle tentative identique.
            try:
                elapsed = (datetime.now().astimezone() - datetime.fromisoformat(previous.get("searched_at"))).total_seconds()
            except (TypeError, ValueError):
                elapsed = 0
            if elapsed < 24 * 60 * 60:
                continue
        todo.append((oid,title,authors,gaps,sig,hist))
    if todo: print("Recherches bibliographiques en cours…",flush=True)
    for oid,title,authors,gaps,sig,hist in todo:
        summary["documents_recherches"]+=1
        book = state["documents"][oid]
        sources = []
        good = False
        isbn_saisi = (book.get("isbn") or "").strip()
        isbn_valide = _isbn_valid(isbn_saisi) if isbn_saisi else False
        isbn_hint = isbn_saisi if isbn_valide else ""
        if isbn_saisi and not isbn_valide:
            print(f"Attention : ISBN invalide pour {oid} ({isbn_saisi}) ; contrôle de clé échoué, recherche par titre/auteur utilisée.", flush=True)
        if RECHERCHE_BNF_ACTIVE:
            bnf = search_bnf(title, authors, isbn=isbn_hint or None)
            sources.append(bnf)
            good = _bnf_satisfactory(bnf, title, authors, book)
            # Si la recherche par ISBN ne suffit pas, conserver la recherche classique.
            if isbn_hint and not good:
                bnf_title = search_bnf(title, authors)
                sources.append(bnf_title)
                good = _bnf_satisfactory(bnf_title, title, authors, book)
        if good and sources and sources[0].get("source", "").startswith("BnF"):
            summary["bnf_concordant"] += 1
        else:
            if RECHERCHE_OPEN_LIBRARY_ACTIVE or RECHERCHE_GOOGLE_BOOKS_ACTIVE:
                summary["catalogues_complementaires"] += 1
            if RECHERCHE_OPEN_LIBRARY_ACTIVE:
                open_library = search_open_library(title, authors, isbn=isbn_hint or None)
                sources.append(open_library)
                good = _bnf_satisfactory(open_library, title, authors, book)
            if not good and RECHERCHE_GOOGLE_BOOKS_ACTIVE:
                time.sleep(1.0)
                google_books = search_google_books(title, authors, isbn=isbn_hint or None)
                sources.append(google_books)
                good = _bnf_satisfactory(google_books, title, authors, book)
        has_error = any(source.get("status") == "erreur_recherche" for source in sources)
        if has_error:
            summary["documents_avec_erreur"] += 1
        for s in sources:
            if s.get("status")=="erreur_recherche": summary["erreurs_sources"]+=1
            if s.get("source")=="Open Library": summary["open_library_notices"]+=len(s.get("results",[]))
            if s.get("source")=="Google Books": summary["google_books_notices"]+=len(s.get("results",[]))
        total=sum(len(s.get("results",[])) for s in sources)
        if not total: summary["documents_sans_notice"]+=1
        book = state["documents"][oid]
        history_item = {
            "document_id": oid, "titre_recherche": title, "auteurs_recherche": authors,
            "champs_manquants": gaps, "query_signature": sig, "searched_at": now_iso(),
            "status": "erreur_partielle" if any(src.get("status") == "erreur_recherche" for src in sources) else ("resultats" if total else "aucun_resultat"),
            "strategie": "BnF par ISBN valide puis par titre/auteur si nécessaire, puis catalogues complémentaires",
            "isbn_controle": {
                "valeur": isbn_saisi or None,
                "valide": isbn_valide if isbn_saisi else None,
                "action": "utilise_pour_recherche" if isbn_valide else ("recherche_titre_auteur" if isbn_saisi else "aucun_isbn_fourni"),
            },
            "source_principale_satisfaisante": next(
                (source.get("source") for source in sources
                 if _bnf_satisfactory(source, title, authors, book)),
                None,
            ),
            "sources": sources,
            "note": "Les notices sont des pistes ; seules les notices d’édition d’ancrage peuvent compléter la fiche. Les contradictions ISBN sont conservées séparément."
        }
        isbn = (book.get("isbn") or "").strip()
        if isbn and not _isbn_valid(isbn):
            isbn = ""
        history_item["contradictions_isbn"] = _find_isbn_contradictions(sources, title, authors, isbn, book.get("sous_titre"))
        strong_records = []
        # Une ancre exige une notice d’édition et un lien de notice consultable.
        if isbn:
            for source in sources:
                for record in source.get("results", []):
                    if not _title_matches_for_isbn_anchor(record, title, isbn, book.get("sous_titre")) or not _author_match(record, authors):
                        continue
                    anchor = _make_notice_anchor(source, record, isbn, book.get("editeur", ""))
                    if anchor:
                        strong_records.append((source, record, anchor))
        else:
            publisher_candidates = []
            for source in sources:
                for record in source.get("results", []):
                    if not _title_match_or_near(record, title, book.get("sous_titre")) or not _author_match(record, authors):
                        continue
                    score = _publisher_score(record, book.get("editeur", ""))
                    if score == 1.0 and _record_is_edition_notice(source, record):
                        publisher_candidates.append((source, record, score))
            unique_urls = {record.get("url_notice") for _, record, _ in publisher_candidates if record.get("url_notice")}
            if len(unique_urls) == 1:
                source, record, _ = next(item for item in publisher_candidates if item[1].get("url_notice") in unique_urls)
                anchor = _make_notice_anchor(source, record, "", book.get("editeur", ""), unique_publisher=True)
                if anchor:
                    strong_records.append((source, record, anchor))
        strong_records.sort(key=lambda item: 0 if item[0].get("source", "").startswith("BnF") else 1)

        title_author_records = [
            record for source in sources for record in source.get("results", [])
            if _title_match_or_near(record, title, book.get("sous_titre")) and _author_match(record, authors)
        ]
        note_year = _year_from_user_note(book)
        ranking_rows = []
        for source in sources:
            for record in source.get("results", []):
                if not (_title_match_or_near(record, title, book.get("sous_titre")) and _author_match(record, authors)):
                    continue
                score = _publisher_score(record, book.get("editeur"))
                year = _notice_year(record)
                ranking_rows.append({
                    "source": source.get("source"),
                    "url_notice": record.get("url_notice"),
                    "score_editeur": score,
                    "annee": year,
                    "_annee_note_match": bool(note_year and year == note_year),
                    "_ordre": len(ranking_rows),
                })
        ranking_rows.sort(key=lambda row: (
            row["score_editeur"] if row["score_editeur"] is not None else -1,
            row["_annee_note_match"],
            -row["_ordre"],
        ), reverse=True)
        history_item["classement_notices"] = [
            {key: row[key] for key in ("source", "url_notice", "score_editeur", "annee")} | {"rang": rank}
            for rank, row in enumerate(ranking_rows, start=1)
        ]
        if strong_records:
            # Les champs bibliographiques ne sont intégrés qu'à partir de la notice d'ancrage.
            _, record, notice_ancrage = strong_records[0]
            identification = book.setdefault("identification", {})
            identification["statut"] = "edition_identifiee"
            identification["notice_ancrage"] = notice_ancrage
            identification["isbns_notice_ancrage"] = _isbn_values(record)
            identification["niveau_confiance"] = "élevée"
            if not any(
                isinstance(source_info, dict)
                and source_info.get("type") == "bibliographie"
                and source_info.get("champ") == "isbns_notice_ancrage"
                and source_info.get("reference") == record.get("url_notice")
                for source_info in book.setdefault("sources_information", [])
            ):
                book["sources_information"].append({
                    "type": "bibliographie",
                    "reference": record.get("url_notice") or "notice bibliographique",
                    "champ": "isbns_notice_ancrage",
                    "valeur": _isbn_values(record),
                    "motif": "ISBN valides relevés dans la notice d’ancrage ; liste vide si aucun n’a été relevé",
                    "recorded_at": now_iso(),
                })
            history_item["evaluation_candidat"] = {
                "niveau": "forte",
                "motif": (
                    "ISBN-10/13 équivalent présent dans une notice d’édition d’ancrage ; titre et auteur concordants"
                    if isbn else "Titre, auteur et éditeur concordants avec une notice d’édition unique"
                ),
                "url_notice": record.get("url_notice"),
            }
            # Une notice fortement concordante avec l’ISBN peut corriger une petite
            # erreur de transcription du titre. Une correction utilisateur explicite
            # reste prioritaire ; tout changement bibliographique est tracé.
            candidate_title = next(
                (value.strip() for value in record.get("titre", []) if value and value.strip()),
                None,
            )
            current_title = (book.get("titre") or "").strip()
            user_title_source = any(
                source.get("type") == "note"
                and str(source.get("champ", "")).casefold() in {"titre", "title"}
                for source in book.get("sources_information", [])
                if isinstance(source, dict)
            )
            if (
                candidate_title and current_title and not user_title_source
                and difflib.SequenceMatcher(None, _norm(current_title), _norm(candidate_title)).ratio() >= 0.85
                and current_title != candidate_title
            ):
                book["titre"] = candidate_title
                book.setdefault("sources_information", []).append({
                    "type": "bibliographie",
                    "reference": record.get("url_notice") or "notice bibliographique",
                    "champ": "titre",
                    "ancienne_valeur": current_title,
                    "valeur": candidate_title,
                    "motif": "Correction d’une variation mineure après concordance bibliographique forte",
                    "recorded_at": now_iso(),
                })
                history_item["correction_titre"] = {
                    "ancienne_valeur": current_title,
                    "nouvelle_valeur": candidate_title,
                    "reference": record.get("url_notice"),
                }
            elif (
                candidate_title and current_title and current_title != candidate_title
                and difflib.SequenceMatcher(None, _norm(current_title), _norm(candidate_title)).ratio() < 0.85
            ):
                history_item["ecart_titre"] = {
                    "valeur_fiche": current_title,
                    "valeur_notice": candidate_title,
                    "motif": "Écart trop important pour une correction automatique",
                }
            if not book.get("annee_edition"):
                year = next((str(date)[:4] for date in record.get("dates", [])
                             if len(str(date)[:4]) == 4 and str(date)[:4].isdigit()), None)
                if year:
                    book["annee_edition"] = year
                    source_ref = record.get("url_notice") or next(
                        (src.get("source") for src in sources if record in src.get("results", [])),
                        "notice bibliographique"
                    )
                    book.setdefault("sources_information", []).append({
                        "type": "bibliographie", "reference": source_ref,
                        "champ": "annee_edition", "valeur": year
                    })
            if not book.get("isbn"):
                candidate_isbns = sorted({
                    digits for identifier in record.get("identifiants", [])
                    if (digits := _isbn_digits(identifier)) and _isbn_valid(digits)
                })
                if len(candidate_isbns) == 1:
                    book["isbn"] = candidate_isbns[0]
                    book.setdefault("sources_information", []).append({
                        "type": "bibliographie",
                        "reference": record.get("url_notice") or "notice bibliographique",
                        "champ": "isbn", "valeur": candidate_isbns[0],
                    })
            publisher = (book.get("editeur") or "").strip()
            if publisher:
                score_editeur = _publisher_score(record, publisher)
                if score_editeur is not None and score_editeur < 1:
                    history_item["evaluation_candidat"]["ecart_editeur"] = {
                        "valeur_fiche": publisher,
                        "valeurs_notice": record.get("editeurs", []),
                        "score_editeur": score_editeur,
                    }
        elif title_author_records:
            identification = book.setdefault("identification", {})
            if (
                identification.get("statut") not in {"edition_identifiee", "identifie"}
                or not isinstance(identification.get("notice_ancrage"), dict)
            ):
                identification["statut"] = "a_confirmer_par_recherche_bibliographique"
            work_records = [
                record for source in sources for record in source.get("results", [])
                if _record_is_work_level(record) and _title_match_or_near(record, title, book.get("sous_titre"))
                and _author_match(record, authors)
            ]
            work_years = list(dict.fromkeys(year for year in (_notice_year(record) for record in work_records) if year))
            if work_years:
                history_item["premiere_publication_oeuvre"] = work_years[0]
            isbn_query_support = bool(isbn and any(
                _is_isbn_query(source) and _title_match_or_near(record, title, book.get("sous_titre")) and _author_match(record, authors)
                for source in sources for record in source.get("results", [])
            ))
            publisher_agrees = any(_publisher_score(record, book.get("editeur", "")) == 1.0 for record in title_author_records)
            if isbn_query_support and not any(_candidate_isbn_match(record, isbn) for record in title_author_records):
                history_item["isbn_note_absent_des_identifiants_notice"] = True
                reason = "La recherche ISBN mène à une notice sans ISBN explicite ; édition non confirmée"
            elif work_records:
                reason = "Seule une notice d’œuvre concorde ; elle ne prouve pas l’édition"
            elif publisher_agrees:
                reason = "Éditeur concordant, mais aucune notice d’édition suffisamment ancrée"
            else:
                reason = "Titre/auteur concordants, mais édition non départagée"
            history_item["evaluation_candidat"] = {
                "niveau": "a_verifier",
                "motif": reason,
                "nombre_candidats_titre_auteur": len(title_author_records),
            }
        else:
            history_item["evaluation_candidat"] = {
                "niveau": "faible_ou_aucune",
                "motif": "Aucune concordance titre/auteur suffisante",
                "nombre_candidats_titre_auteur": 0,
            }
        hist.append(history_item)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Socle de gestion progressive de l'inventaire "
            "de livres et autres documents."
        )
    )

    parser.add_argument(
        "--photos",
        type=Path,
        default=DEFAULT_PHOTO_DIR,
        help="Dossier contenant les photos (défaut : photos/).",
    )
    parser.add_argument(
        "--state",
        type=Path,
        default=DEFAULT_STATE_FILE,
        help="Fichier JSON persistant (défaut : inventaire.json).",
    )
    parser.add_argument(
        "--csv", type=Path, default=DEFAULT_CSV_FILE,
        help="Fichier CSV de sortie (défaut : inventaire.csv).",
    )
    mode_ai = parser.add_mutually_exclusive_group()
    mode_ai.add_argument(
        "--no-ai", action="store_true",
        help="Met à jour le suivi des photos sans appeler l’API IA.",
    )
    mode_ai.add_argument(
        "--last-reponse", action="store_true",
        help="Réutilise derniere_reponse_ia.txt sans appeler l'API (une seule photo en attente).",
    )
    parser.add_argument(
        "--notes",
        type=Path,
        default=DEFAULT_NOTES_FILE,
        help="Fichier cumulatif de notes (défaut : notes.txt).",
    )
    parser.add_argument(
        "--photo-instructions", type=Path, default=DEFAULT_PHOTO_INSTRUCTIONS_FILE,
        help="CSV des précisions par photo (défaut : photos.txt).",
    )

    return parser.parse_args()


def main() -> int:
    print_version()
    args = parse_args()
    photo_dir, state_path, notes_path, csv_path = args.photos, args.state, args.notes, args.csv
    instructions_path = args.photo_instructions
    state = load_state(state_path)
    new_photos, changed_photos, missing_photos = scan_photos(photo_dir, state)
    photo_instructions, precision_changed, instructions_file_changed, instructions_warnings = (
        read_photo_instructions(instructions_path, photo_dir, state)
    )
    for record in precision_changed:
        if record not in changed_photos and record not in new_photos:
            changed_photos.append(record)
    _, notes_changed = read_notes(notes_path, state)

    pending_records = [
        record for record in state["photos"].values()
        if record.get("analysis_status") in {"new", "modified", "pending_analysis", "analysis_error"}
    ]
    api_errors = []
    analyzed = 0
    if args.last_reponse and len(pending_records) != 1:
        raise SystemExit(
            "--last-reponse exige exactement une photo en attente d'analyse "
            "pour éviter d'appliquer la même réponse à plusieurs photos."
        )
    if not args.no_ai:
        for record in pending_records:
            photo_path = record["path"]
            image_path = Path(photo_path)
            if not image_path.is_absolute():
                image_path = photo_dir.parent / image_path
            try:
                print(f"Analyse de la photo {photo_path} en cours…", flush=True)
                photo_instruction = photo_instructions.get(Path(photo_path).name, {})
                precision = photo_instruction.get("precision", "")
                ref = photo_instruction.get("ref", "non")
                result = analyze_photo(
                    image_path,
                    precision=precision,
                    ref=ref,
                    use_last_response=args.last_reponse,
                )
                apply_photo_analysis(state, photo_path, result)
                analyzed += 1
                count = len(result.get("documents", []))
                label = "document détecté" if count == 1 else "documents détectés"
                print(f"  → {count} {label}", flush=True)
            except Exception as exc:
                # Ne jamais écraser une analyse valide en cas d'erreur d'appel.
                record["analysis_status"] = "analysis_error"
                record["last_error"] = str(exc)
                api_errors.append((photo_path, str(exc)))

    integrate_unambiguous_detections(state)
    biblio_summary = enrich_bibliographic_candidates(state)
    refresh_missing_information(state)
    state["program_version"] = VERSION
    state["updated_at"] = now_iso()
    state.setdefault("runs", []).append({
        "started_at": now_iso(),
        "program_version": VERSION,
        "new_photos": len(new_photos),
        "changed_photos": len(changed_photos),
        "missing_photos": len(missing_photos),
        "notes_changed": notes_changed,
        "photo_instructions_changed": instructions_file_changed,
        "photos_with_precision_changed": len(precision_changed),
        "photos_analyzed": analyzed,
        "api_errors": len(api_errors),
        "bibliographic_searches": biblio_summary,
    })

    write_outputs(state, state_path, csv_path)

    print_report(photo_dir, state, state_path, notes_path, new_photos, changed_photos, missing_photos, notes_changed)
    print(f"Fichier de précisions par photo : {instructions_path}")
    if instructions_file_changed:
        print("Le contenu de photos.txt a changé.")
    for warning in instructions_warnings:
        print(f"  ! {warning}")
    print(f"Photos analysées pendant ce lancement : {analyzed}")
    print(f"Erreurs d'analyse : {len(api_errors)}")
    print("Bilan des recherches bibliographiques :")
    print("  Documents recherchés : " + str(biblio_summary["documents_recherches"]))
    print("  Correspondance BnF satisfaisante : " + str(biblio_summary["bnf_concordant"]))
    print("  Documents passés aux catalogues complémentaires : " + str(biblio_summary["catalogues_complementaires"]))
    print("  Notices Open Library : " + str(biblio_summary["open_library_notices"]))
    print("  Notices Google Books : " + str(biblio_summary["google_books_notices"]))
    print("  Documents sans notice : " + str(biblio_summary["documents_sans_notice"]))
    print("  Documents avec au moins une erreur : " + str(biblio_summary["documents_avec_erreur"]))
    print("  Appels aux catalogues en erreur : " + str(biblio_summary["erreurs_sources"]))
    print("Les notices restent des pistes ; seuls les champs manquants appuyés par une concordance fiable sont complétés. Les données utilisateur ne sont pas écrasées.")
    for photo_path, error in api_errors:
        print(f"  ! {photo_path} : {error}")
    print(f"CSV exporté : {csv_path}")
    pending_reconciliation = sum(
        1 for photo in state["photos"].values()
        for detection in photo.get("analysis", {}).get("documents_detectes", [])
        if detection.get("rapprochement", {}).get("statut") == "ambigu"
    )
    if pending_reconciliation:
        print(f"Rapprochements ambigus à examiner : {pending_reconciliation}")
        print("Pour les résoudre, préciser dans notes.txt le document concerné ou fournir une photo de détail utile.")

    secondary_missing = sum(
        bool(document.get("identification", {}).get("informations_manquantes"))
        for document in state.get("documents", {}).values()
    )
    if secondary_missing:
        print(f"Fiches avec des champs secondaires encore inconnus : {secondary_missing} (détail dans le CSV ; ces champs ne bloquent pas tous l'identification).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
