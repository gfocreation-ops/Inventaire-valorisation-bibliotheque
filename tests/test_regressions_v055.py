#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests de non-régression ciblés pour le script ; tous les fichiers utilisés sont temporaires."""

import csv
import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import creer_bibliotheque as app


class PhotoInstructionsTests(unittest.TestCase):
    def test_fichier_txt_accole_ignore_et_photos_txt_centralise_les_precisions(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            photo_dir = root / "photos"
            photo_dir.mkdir()
            photo = photo_dir / "Photo_1.jpg"
            photo.write_bytes(b"image de test")
            photo.with_suffix(".txt").write_text("TEXTE_OBSOLETE", encoding="utf-8")
            state = app.create_initial_state()

            new, changed, _ = app.scan_photos(photo_dir, state)
            self.assertEqual(len(new), 1)
            state["photos"]["photos/Photo_1.jpg"]["analysis_status"] = "analyzed"
            _, changed, _ = app.scan_photos(photo_dir, state)
            self.assertEqual(changed, [])

            instructions = root / "photos.txt"
            instructions.write_text(
                "photo;ref;precision\nPhoto_1.jpg;non;3 rangées de 6 livres de face\n",
                encoding="utf-8",
            )
            mapping, precision_changed, file_changed, warnings = app.read_photo_instructions(
                instructions, photo_dir, state
            )
            self.assertTrue(file_changed)
            self.assertEqual(warnings, [])
            self.assertEqual(mapping["Photo_1.jpg"]["ref"], "non")
            self.assertEqual(mapping["Photo_1.jpg"]["precision"], "3 rangées de 6 livres de face")
            self.assertEqual([r["path"] for r in precision_changed], ["photos/Photo_1.jpg"])
            self.assertEqual(state["photos"]["photos/Photo_1.jpg"]["analysis_status"], "modified")

            state["photos"]["photos/Photo_1.jpg"]["analysis_status"] = "analyzed"
            instructions.write_text(
                "photo;ref;precision\nPhoto_1.jpg;oui;3 rangées de 6 livres de face\n",
                encoding="utf-8",
            )
            mapping, precision_changed, _, warnings = app.read_photo_instructions(
                instructions, photo_dir, state
            )
            self.assertEqual(mapping["Photo_1.jpg"]["ref"], "oui")
            self.assertEqual([r["path"] for r in precision_changed], ["photos/Photo_1.jpg"])
            self.assertEqual(state["photos"]["photos/Photo_1.jpg"]["analysis_status"], "modified")
            self.assertEqual(warnings, [])

            instructions.write_text(
                "photo;ref;precision\nPhoto_1.jpg;oui;Le 3e livre à gauche est document_0005\n",
                encoding="utf-8",
            )
            mapping, precision_changed, _, warnings = app.read_photo_instructions(
                instructions, photo_dir, state
            )
            self.assertEqual(mapping["Photo_1.jpg"]["ref"], "oui")
            self.assertEqual(len(precision_changed), 1)
            self.assertEqual(state["photos"]["photos/Photo_1.jpg"]["analysis_status"], "modified")
            self.assertEqual(warnings, [])

    def test_csv_invalide_reutilise_la_derniere_precision_valide(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            photo_dir = root / "photos"
            photo_dir.mkdir()
            (photo_dir / "Photo_1.jpg").write_bytes(b"image de test")
            state = app.create_initial_state()
            app.scan_photos(photo_dir, state)
            instructions = root / "photos.txt"
            instructions.write_text(
                "photo;ref;precision\nPhoto_1.jpg;non;Précision conservée\n",
                encoding="utf-8",
            )
            app.read_photo_instructions(instructions, photo_dir, state)
            state["photos"]["photos/Photo_1.jpg"]["analysis_status"] = "analyzed"

            instructions.write_text(
                "photo;precision\nPhoto_1.jpg;en-tête invalide\n",
                encoding="utf-8",
            )
            mapping, changed, _, warnings = app.read_photo_instructions(
                instructions, photo_dir, state
            )
            self.assertEqual(mapping["Photo_1.jpg"]["precision"], "Précision conservée")
            self.assertEqual(changed, [])
            self.assertEqual(state["photos"]["photos/Photo_1.jpg"]["analysis_status"], "analyzed")
            self.assertTrue(warnings)


    def test_precision_centrale_est_transmise_au_prompt_et_pas_le_txt_accole(self):
        with tempfile.TemporaryDirectory() as temporary:
            photo = Path(temporary) / "Photo_1.jpg"
            photo.write_bytes(b"fake image bytes")
            photo.with_suffix(".txt").write_text("TEXTE_OBSOLETE_INTERDIT", encoding="utf-8")
            captured = {}

            class FakeResponses:
                def create(self, **kwargs):
                    captured.update(kwargs)
                    return types.SimpleNamespace(
                        output_text='{"documents":[]}'
                    )

            fake_openai = types.SimpleNamespace(
                OpenAI=lambda: types.SimpleNamespace(responses=FakeResponses())
            )
            with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}), patch.dict(
                sys.modules, {"openai": fake_openai}
            ):
                app.analyze_photo(photo, precision="TEST_PRECISION_CENTRALE", ref="non")

            prompt = captured["input"][0]["content"][0]["text"]
            self.assertIn("TEST_PRECISION_CENTRALE", prompt)
            self.assertNotIn("Si cette précision mentionne explicitement un identifiant", prompt)
            self.assertNotIn("TEXTE_OBSOLETE_INTERDIT", prompt)
            self.assertIn("information fiable fournie par l’utilisateur", prompt)
            self.assertNotIn("Si cette précision mentionne explicitement un identifiant", prompt)

    def test_ref_oui_ajoute_la_consigne_d_association_aux_identifiants(self):
        with tempfile.TemporaryDirectory() as temporary:
            photo = Path(temporary) / "Photo_1.jpg"
            photo.write_bytes(b"fake image bytes")
            captured = {}

            class FakeResponses:
                def create(self, **kwargs):
                    captured.update(kwargs)
                    return types.SimpleNamespace(
                        output_text='{"documents":[]}'
                    )

            fake_openai = types.SimpleNamespace(
                OpenAI=lambda: types.SimpleNamespace(responses=FakeResponses())
            )
            with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}), patch.dict(
                sys.modules, {"openai": fake_openai}
            ):
                app.analyze_photo(
                    photo,
                    precision="Il s’agit du document_0007",
                    ref="oui",
                )

            prompt = captured["input"][0]["content"][0]["text"]
            self.assertIn("information fiable fournie par l’utilisateur", prompt)
            self.assertIn(
                "Si cette précision mentionne explicitement un identifiant de document connu",
                prompt,
            )
            self.assertIn("document_0007", prompt)

class StructuredNotesTests(unittest.TestCase):
    def test_notes_remplissent_champs_vides_sans_transmettre_le_fichier_a_l_ia(self):
        with tempfile.TemporaryDirectory() as temporary:
            notes = Path(temporary) / "notes.txt"
            state = app.create_initial_state()
            oid = app.create_document(state, titre="Livre test")
            notes.write_text(
                f"{oid};annee_impression;26/04/1990\n{oid};ISBN;9782234022119\n",
                encoding="utf-8",
            )

            returned_content, changed = app.read_notes(notes, state)
            self.assertTrue(changed)
            self.assertIn("annee_impression;26/04/1990", returned_content)
            self.assertEqual(state["documents"][oid]["annee_impression"], "26/04/1990")
            self.assertEqual(state["documents"][oid]["isbn"], "9782234022119")
            self.assertEqual(
                [item["statut_application"] for item in state["notes"]["informations"]],
                ["appliquee", "appliquee"],
            )

    def test_note_utilisateur_remplace_une_valeur_issue_de_photo(self):
        with tempfile.TemporaryDirectory() as temporary:
            notes = Path(temporary) / "notes.txt"
            state = app.create_initial_state()
            oid = app.create_document(state, titre="Livre test", isbn="1111111111111")
            state["documents"][oid]["sources_information"].append({
                "type": "photo", "champ": "isbn", "valeur": "1111111111111"
            })
            notes.write_text(f"{oid};ISBN;2222222222222\n", encoding="utf-8")

            app.read_notes(notes, state)
            self.assertEqual(state["documents"][oid]["isbn"], "2222222222222")
            self.assertEqual(state["notes"]["informations"][0]["statut_application"], "appliquee_remplacee")

    def test_note_decode_le_saut_de_ligne_litteral_dans_editeur(self):
        with tempfile.TemporaryDirectory() as temporary:
            notes = Path(temporary) / "notes.txt"
            state = app.create_initial_state()
            oid = app.create_document(state, titre="Dieu en questions", editeur="Stock/Laurence Pernoud")
            notes.write_text(
                f"{oid};editeur;Desclée de Brouwer\\nStock/Laurence Pernoud\n",
                encoding="utf-8",
            )
            app.read_notes(notes, state)
            self.assertEqual(state["documents"][oid]["editeur"], "Desclée de Brouwer\nStock/Laurence Pernoud")
            self.assertEqual(state["notes"]["informations"][0]["statut_application"], "appliquee_remplacee")


class ReferencedBookTests(unittest.TestCase):
    def test_identifiant_indique_dans_la_precision_est_restitue_et_controle_par_le_script(self):
        state = app.create_initial_state()
        oid = app.create_document(state, titre="Livre déjà connu")
        photo_path = "photos/Photo_2.jpg"
        state["photos"][photo_path] = {"path": photo_path, "document_ids": []}
        field = lambda value: {
            "valeur": value, "confiance": "élevée", "origine": "photo",
            "statut_lecture": "non_visible" if value is None else "lisible",
        }
        result = {"documents": [{
            "reference": "detection_1", "document_id_reference": oid,
            "position": "centre", "type_document": "livre",
            "titre": field("Livre déjà connu"), "sous_titre": field(None),
            "auteurs": field(None), "editeur": field(None), "edition": field(None),
            "isbn": field("9780000000000"), "collection": field(None),
            "annee_edition": field(None), "annee_impression": field(None),
            "date_depot_legal": field(None), "description_illustration": "",
            "autres_textes": [],
            "etat_general": {"appreciation": "non_evaluable", "motif": ""},
        }]}
        app.apply_photo_analysis(state, photo_path, result)
        detection = state["photos"][photo_path]["analysis"]["documents_detectes"][0]
        self.assertEqual(detection["document_id_reference"], oid)
        self.assertEqual(detection["rapprochement"]["statut"], "cible_indiquee_par_txt")
        self.assertEqual(detection["rapprochement"]["candidats_document_ids"], [oid])

    def test_largeur_minimale_configurable_sans_collision_avec_anciens_ids(self):
        state = app.create_initial_state()
        state["documents"]["document_0001"] = {"id": "document_0001"}
        with patch.object(app, "LARGEUR_NUMERO_DOCUMENT", 3):
            oid = app.create_document(state, titre="Nouveau livre")
        self.assertEqual(oid, "document_002")
        self.assertIn("document_0001", state["documents"])




class IdentificationAndDateTests(unittest.TestCase):
    def test_photo_referencee_complete_fiche_sans_ecraser_et_rattache_la_photo(self):
        state = app.create_initial_state()
        oid = app.create_document(state, titre="Livre déjà connu", auteurs=["A. Auteur"])
        photo_path = "photos/Photo_2.jpg"
        state["photos"][photo_path] = {"path": photo_path, "document_ids": [], "roles": []}
        field = lambda value: {
            "valeur": value, "confiance": "élevée", "origine": "photo",
            "statut_lecture": "non_visible" if value is None else "lisible",
        }
        result = {"documents": [{
            "reference": "detection_1", "document_id_reference": oid,
            "position": "centre", "type_document": "livre",
            "titre": field("Livre déjà connu"), "sous_titre": field(None),
            "auteurs": field("A. Auteur"), "editeur": field("Éditions Test"),
            "edition": field("1re édition"), "isbn": field("9780000000000"),
            "collection": field(None), "annee_edition": field("1990"),
            "annee_impression": field("26/04/1990"), "date_depot_legal": field("04/1990"),
            "description_illustration": "", "autres_textes": [],
            "etat_general": {"appreciation": "non_evaluable", "motif": ""},
        }]}
        app.apply_photo_analysis(state, photo_path, result)
        book = state["documents"][oid]
        self.assertIn(photo_path, book["photos"])
        self.assertIn(oid, state["photos"][photo_path]["document_ids"])
        self.assertEqual(book["editeur"], "Éditions Test")
        self.assertEqual(book["isbn"], "9780000000000")
        self.assertEqual(book["annee_edition"], "1990")
        self.assertEqual(book["annee_impression"], "26/04/1990")
        self.assertEqual(book["date_depot_legal"], "04/1990")
        self.assertTrue(any(source.get("champ") == "isbn" for source in book["sources_information"]))

    def test_photo_referencee_ne_remplace_pas_un_isbn_contradictoire(self):
        state = app.create_initial_state()
        oid = app.create_document(state, titre="Livre déjà connu", isbn="1111111111111")
        photo_path = "photos/Photo_2.jpg"
        state["photos"][photo_path] = {"path": photo_path, "document_ids": [], "roles": []}
        field = lambda value: {
            "valeur": value, "confiance": "élevée", "origine": "photo",
            "statut_lecture": "non_visible" if value is None else "lisible",
        }
        result = {"documents": [{
            "reference": "detection_1", "document_id_reference": oid,
            "position": "centre", "type_document": "livre",
            "titre": field("Livre déjà connu"), "sous_titre": field(None),
            "auteurs": field(None), "editeur": field(None), "edition": field(None),
            "isbn": field("2222222222222"), "collection": field(None),
            "annee_edition": field(None), "annee_impression": field(None),
            "date_depot_legal": field(None), "description_illustration": "",
            "autres_textes": [],
            "etat_general": {"appreciation": "non_evaluable", "motif": ""},
        }]}
        app.apply_photo_analysis(state, photo_path, result)
        book = state["documents"][oid]
        self.assertEqual(book["isbn"], "1111111111111")
        detection = state["photos"][photo_path]["analysis"]["documents_detectes"][0]
        self.assertEqual(detection["conflits_identification"][0]["champ"], "isbn")

    def test_date_depot_legal_est_un_champ_distinct_et_exporte(self):
        state = app.create_initial_state()
        oid = app.create_document(
            state, titre="Livre daté", annee_edition="1989",
            annee_impression="26/04/1990", date_depot_legal="04/1990",
        )
        with tempfile.TemporaryDirectory() as temporary:
            csv_path = Path(temporary) / "inventaire.csv"
            app.export_csv(state, csv_path)
            rows = list(__import__("csv").DictReader(csv_path.open(encoding="utf-8-sig"), delimiter=";"))
        self.assertEqual(rows[0]["annee_edition"], "1989")
        self.assertEqual(rows[0]["annee_impression"], "26/04/1990")
        self.assertEqual(rows[0]["date_depot_legal"], "04/1990")


class V058StateTests(unittest.TestCase):
    def test_informations_manquantes_recalculees_selon_les_valeurs_presentes(self):
        state = app.create_initial_state()
        oid = app.create_document(
            state, titre="Livre test", auteurs=["A. Auteur"],
            isbn="9782234022119", annee_impression="26/04/1990",
        )
        state["documents"][oid]["identification"]["informations_manquantes"] = [
            "ISBN à rechercher si présent", "date d’impression"
        ]
        app.refresh_missing_information(state)
        missing = state["documents"][oid]["identification"]["informations_manquantes"]
        self.assertNotIn("ISBN à rechercher si présent", missing)
        self.assertNotIn("date d’impression", missing)
        self.assertIn("année de publication", missing)


class BibliographicMatchingTests(unittest.TestCase):
    def test_isbn_10_et_isbn_13_sont_reconnus_equivalents_apres_controle(self):
        self.assertTrue(app._isbn_valid("9782863740538"))
        self.assertTrue(app._isbn_valid("2863740539"))
        self.assertTrue(app._isbn_equivalent("9782863740538", "2863740539"))
        self.assertTrue(app._isbn_equivalent("2863740539", "9782863740538"))
        self.assertFalse(app._isbn_equivalent("9782863740538", "9782234022119"))

    def test_isbn_a_cle_de_controle_invalide_est_refuse(self):
        self.assertFalse(app._isbn_valid("9780306406158"))
        self.assertFalse(app._isbn_valid("0306406153"))
        self.assertFalse(app._isbn_equivalent("9780306406158", "0306406152"))
        self.assertFalse(app._isbn_valid("9780000000000"))

    def test_isbn_invalide_ne_bloque_pas_le_rapprochement_titre_auteur(self):
        result = {"results": [{
            "titre": ["Titre de test"], "auteurs": ["Auteur Test"],
            "editeurs": [], "dates": [], "identifiants": [],
        }]}
        book = {"isbn": "9780306406158", "editeur": ""}
        self.assertTrue(app._bnf_satisfactory(result, "Titre de test", "Auteur Test", book))

    def test_isbn_invalide_est_exclu_des_requetes_et_signale(self):
        state = app.create_initial_state()
        oid = app.create_document(state, titre="Titre de test", auteurs=["Auteur Test"], isbn="9780306406158")
        with patch.object(app, "search_bnf", return_value={
            "source": "BnF Catalogue général (SRU)", "status": "aucun_resultat", "results": []
        }) as bnf:
            with patch.object(app, "search_open_library", return_value={
                "source": "Open Library", "status": "aucun_resultat", "results": []
            }):
                app.enrich_bibliographic_candidates(state)
        self.assertIsNone(bnf.call_args_list[0].kwargs.get("isbn"))
        history = state["documents"][oid]["recherches_bibliographiques"][-1]
        self.assertEqual(history["isbn_controle"]["valide"], False)
        self.assertEqual(history["isbn_controle"]["action"], "recherche_titre_auteur")

    def test_isbn_invalide_declenche_un_controle_meme_si_fiche_complete(self):
        state = app.create_initial_state()
        oid = app.create_document(
            state, titre="Titre complet", auteurs=["Auteur Test"], editeur="Éditions Test",
            collection="Collection Test", annee_edition="1990", edition="1re édition",
            annee_impression="1990", date_depot_legal="1990", isbn="9780306406158",
        )
        state["documents"][oid]["identification"]["statut"] = "edition_identifiee"
        with patch.object(app, "search_bnf", return_value={
            "source": "BnF Catalogue général (SRU)", "status": "aucun_resultat", "results": []
        }) as bnf:
            with patch.object(app, "search_open_library", return_value={
                "source": "Open Library", "status": "aucun_resultat", "results": []
            }):
                app.enrich_bibliographic_candidates(state)
        bnf.assert_called()
        self.assertIsNone(bnf.call_args_list[0].kwargs.get("isbn"))

    def test_isbn_bnf_prioritaire_tolere_une_faute_dans_le_titre(self):
        state = app.create_initial_state()
        oid = app.create_document(
            state, titre="Les Demoiselles de Beaumoereau",
            auteurs=["Marguerite Gurgand"], editeur="Mazarine",
            isbn="9782863740538",
        )
        candidate = {
            "titre": ["Les Demoiselles de Beaumoreau"],
            "auteurs": ["Gurgand, Marguerite"],
            "editeurs": ["Mazarine"],
            "dates": ["1981"],
            "identifiants": ["ISBN 2863740539"],
            "url_notice": "https://example.invalid/notice",
        }
        with patch.object(app, "search_bnf", return_value={
            "source": "BnF Catalogue général (SRU)", "status": "resultats",
            "query_url": "https://example.invalid/sru", "results": [candidate],
        }) as search_bnf:
            with patch.object(app, "search_open_library") as open_library:
                with patch.object(app, "search_google_books") as google_books:
                    app.enrich_bibliographic_candidates(state)
        search_bnf.assert_called_once_with(
            "Les Demoiselles de Beaumoereau", "Marguerite Gurgand",
            isbn="9782863740538",
        )
        open_library.assert_not_called()
        google_books.assert_not_called()
        document = state["documents"][oid]
        self.assertEqual(document["identification"]["statut"], "edition_identifiee")
        self.assertEqual(document["annee_edition"], "1981")
        self.assertEqual(
            document["recherches_bibliographiques"][-1]["evaluation_candidat"]["niveau"],
            "forte",
        )

    def test_bnf_recherche_isbn_utilise_fuzzyisbn(self):
        with patch.object(app.urllib.request, "urlopen") as urlopen:
            urlopen.return_value.__enter__.return_value.read.return_value = b"<root/>"
            result = app.search_bnf("Titre ignore", "Auteur ignore", isbn="9782863740538")
        self.assertIn("bib.fuzzyISBN", result["query_url"])
        self.assertIn("9782863740538", result["query_url"])
        self.assertIn("recordSchema=unimarcxchange", result["query_url"])

    def test_bnf_unimarc_conserve_tous_les_isbn_de_la_zone_010(self):
        xml = """<srw:searchRetrieveResponse xmlns:srw="http://www.loc.gov/zing/srw/" xmlns:u="http://www.bncf.firenze.sbn.it/unimarcxchange">
          <srw:numberOfRecords>1</srw:numberOfRecords><srw:records><srw:record><srw:recordData><u:record>
            <u:leader>00000nam a2200000 i 4500</u:leader>
            <u:controlfield tag="003">http://catalogue.bnf.fr/ark:/12148/cb35074863k</u:controlfield>
            <u:datafield tag="010"><u:subfield code="a">2-220-03132-2</u:subfield><u:subfield code="b">DDB</u:subfield></u:datafield>
            <u:datafield tag="010"><u:subfield code="a">2-234-02211-8</u:subfield><u:subfield code="b">Stock</u:subfield></u:datafield>
            <u:datafield tag="100"><u:subfield code="a">19900521d1990    m  y0frey50</u:subfield></u:datafield>
            <u:datafield tag="200"><u:subfield code="a">Dieu en questions</u:subfield><u:subfield code="f">André Frossard,...</u:subfield></u:datafield>
            <u:datafield tag="210"><u:subfield code="c">Desclée de Brouwer</u:subfield><u:subfield code="c">Stock</u:subfield><u:subfield code="d">1990</u:subfield></u:datafield>
          </u:record></srw:recordData></srw:record></srw:records>
        </srw:searchRetrieveResponse>"""
        with patch.object(app.urllib.request, "urlopen") as urlopen:
            urlopen.return_value.__enter__.return_value.read.return_value = xml.encode("utf-8")
            result = app.search_bnf("Dieu en questions", "André Frossard", isbn="9782234022119")
        self.assertEqual(len(result["results"]), 1)
        record = result["results"][0]
        self.assertEqual(record["niveau_notice"], "edition")
        self.assertIn("2220031322", record["identifiants"])
        self.assertIn("2234022118", record["identifiants"])
        self.assertEqual(record["url_notice"], "http://catalogue.bnf.fr/ark:/12148/cb35074863k")
        self.assertEqual(record["dates"][0], "1990")

    def test_bnf_diagnostic_sru_est_une_erreur_pas_une_absence_de_notice(self):
        xml = b"""<srw:searchRetrieveResponse xmlns:srw="http://www.loc.gov/zing/srw/" xmlns:sd="http://www.loc.gov/zing/srw/diagnostic/"><srw:diagnostics><sd:diagnostic><sd:message>Version non supportee</sd:message></sd:diagnostic></srw:diagnostics></srw:searchRetrieveResponse>"""
        with patch.object(app.urllib.request, "urlopen") as urlopen:
            urlopen.return_value.__enter__.return_value.read.return_value = xml
            result = app.search_bnf("Titre", isbn="9782863740538")
        self.assertEqual(result["status"], "erreur_recherche")
        self.assertIn("Version non supportee", result["error"])

    def test_notice_isbn_corrige_titre_proche_avec_provenance(self):
        state = app.create_initial_state()
        oid = app.create_document(
            state, titre="Les Demoiselles de Beaumoereau",
            auteurs=["Marguerite Gurgand"], editeur="Mazarine",
            isbn="9782863740538",
        )
        candidate = {
            "titre": ["Les demoiselles de Beaumoreau"],
            "auteurs": ["Gurgand, Marguerite"], "editeurs": ["Mazarine"],
            "dates": ["1981"], "identifiants": [],
            "url_notice": "https://openlibrary.org/works/OL5514803W",
        }
        state["documents"][oid]["recherches_bibliographiques"] = [{
            "query_signature": "old", "strategie": "old", "status": "resultats"
        }]
        with patch.object(app, "search_bnf", side_effect=[
            {"source": "BnF", "status": "aucun_resultat", "results": []},
            {"source": "BnF", "status": "aucun_resultat", "results": []},
        ]):
            with patch.object(app, "search_open_library", return_value={
                "source": "Open Library", "status": "resultats",
                "query_url": "https://openlibrary.org/search.json?isbn=9782863740538&limit=5",
                "results": [candidate],
            }):
                with patch.object(app, "search_google_books") as google_books:
                    app.enrich_bibliographic_candidates(state)
        document = state["documents"][oid]
        self.assertEqual(document["titre"], "Les Demoiselles de Beaumoereau")
        self.assertFalse(any(item.get("champ") == "titre" and item.get("type") == "bibliographie"
                             for item in document["sources_information"]))
        self.assertIsNone(document["annee_edition"])
        history = document["recherches_bibliographiques"][-1]
        self.assertEqual(history["evaluation_candidat"]["niveau"], "a_verifier")
        self.assertEqual(history["premiere_publication_oeuvre"], "1981")
        self.assertEqual(document["identification"]["statut"], "a_confirmer_par_recherche_bibliographique")
        google_books.assert_not_called()

    def test_notice_bibliographique_ne_remplace_pas_titre_corrige_par_utilisateur(self):
        state = app.create_initial_state()
        oid = app.create_document(state, titre="Titre confirmé par utilisateur",
                                  auteurs=["A. Auteur"], isbn="9780000000002")
        state["documents"][oid]["sources_information"].append({
            "type": "note", "champ": "titre", "contenu": "Titre confirmé par utilisateur"
        })
        candidate = {
            "titre": ["Titre confirme par utilisateur"], "auteurs": ["A. Auteur"],
            "editeurs": [], "dates": [], "identifiants": ["9780000000002"],
            "url_notice": "https://example.invalid/notice",
        }
        with patch.object(app, "search_bnf", return_value={
            "source": "BnF", "status": "resultats", "results": [candidate]
        }):
            app.enrich_bibliographic_candidates(state)
        self.assertEqual(state["documents"][oid]["titre"], "Titre confirmé par utilisateur")

    def test_open_library_recherche_par_isbn_accepte_notice_sans_isbn_renvoye(self):
        state = app.create_initial_state()
        oid = app.create_document(
            state, titre="Les Demoiselles de Beaumoereau",
            auteurs=["Marguerite Gurgand"], editeur="Mazarine",
            isbn="9782863740538",
        )
        candidate = {
            "titre": ["Les demoiselles de Beaumoreau"],
            "auteurs": ["Marguerite Gurgand"],
            "editeurs": [],
            "dates": ["1981"],
            "identifiants": [],
            "url_notice": "https://openlibrary.org/works/OL5514803W",
        }
        with patch.object(app, "search_bnf", side_effect=[
            {"source": "BnF Catalogue général (SRU)", "status": "aucun_resultat",
             "query_url": "https://example.invalid/sru?query=isbn", "results": []},
            {"source": "BnF Catalogue général (SRU)", "status": "aucun_resultat",
             "query_url": "https://example.invalid/sru?query=title", "results": []},
        ]):
            with patch.object(app, "search_open_library", return_value={
                "source": "Open Library", "status": "resultats",
                "query_url": "https://openlibrary.org/search.json?isbn=9782863740538&limit=5",
                "results": [candidate],
            }):
                with patch.object(app, "search_google_books") as google_books:
                    app.enrich_bibliographic_candidates(state)
        document = state["documents"][oid]
        self.assertEqual(document["identification"]["statut"], "a_confirmer_par_recherche_bibliographique")
        self.assertNotIn("notice_ancrage", document["identification"])
        self.assertIsNone(document["annee_edition"])
        history = document["recherches_bibliographiques"][-1]
        self.assertEqual(history["evaluation_candidat"]["niveau"], "a_verifier")
        self.assertTrue(history["isbn_note_absent_des_identifiants_notice"])
        self.assertEqual(history["premiere_publication_oeuvre"], "1981")
        self.assertIn("Open Library", history["source_principale_satisfaisante"])
        google_books.assert_not_called()

    def test_contradiction_isbn_est_tracee_sans_confondre_notice_oeuvre(self):
        sources = [{
            "source": "BnF Catalogue général (SRU)",
            "query_url": "https://catalogue.bnf.fr/api/SRU?query=bib.fuzzyISBN+any+%229782234022119%22",
            "results": [
                {
                    "titre": ["Dieu en questions"], "auteurs": ["André Frossard"],
                    "editeurs": ["Stock"], "dates": ["1990"],
                    "identifiants": ["2220031322"],
                    "url_notice": "https://catalogue.bnf.fr/ark:/12148/cb35074863j",
                    "niveau_notice": "edition",
                },
                {
                    "titre": ["Dieu en questions"], "auteurs": ["André Frossard"],
                    "editeurs": [], "dates": ["1985"], "identifiants": [],
                    "url_notice": "https://openlibrary.org/works/OL123W",
                },
            ],
        }]
        contradictions = app._find_isbn_contradictions(sources, "Dieu en questions", "André Frossard", "9782234022119")
        self.assertEqual(len(contradictions), 1)
        self.assertEqual(contradictions[0]["isbns_notice"], ["2220031322"])
        self.assertEqual(contradictions[0]["isbn_recherche"], "9782234022119")

    def test_titre_auteur_seuls_ne_confirment_pas_une_edition(self):
        result = {
            "results": [{
                "titre": ["Dieu en questions"],
                "auteurs": ["Frossard, André"],
                "editeurs": ["Desclée de Brouwer"],
                "dates": ["1990"],
                "identifiants": [],
            }]
        }
        book = {"editeur": "Stock/Laurence Pernoud", "isbn": ""}
        self.assertFalse(app._bnf_satisfactory(result, "Dieu en questions", "André Frossard", book))

    def test_bnf_departage_plusieurs_notices_par_editeur(self):
        result = {"results": [
            {"titre": ["Dieu en questions"], "auteurs": ["Frossard, André"], "editeurs": ["France loisirs (Paris)"], "dates": ["1990"], "identifiants": ["ISBN 2724261429"]},
            {"titre": ["Dieu en questions"], "auteurs": ["Frossard, André"], "editeurs": ["Desclée de Brouwer (Paris)", "Stock (Paris)"], "dates": ["1990"], "identifiants": ["ISBN 2220031322"]},
            {"titre": ["Dieu en questions"], "auteurs": ["Frossard, André"], "editeurs": ["Librairie générale française (Paris)"], "dates": ["1991"], "identifiants": ["ISBN 2253058327"]},
        ]}
        book = {"editeur": "Desclée de Brouwer\nStock/Laurence Pernoud", "isbn": ""}
        self.assertTrue(app._bnf_satisfactory(result, "DIEU EN QUESTIONS", "André Frossard", book))

    def test_isbn_concordant_peut_confirmer_edition_et_completer_annee(self):
        state = app.create_initial_state()
        oid = app.create_document(
            state, titre="Les Demoiselles de Beaumoreau",
            auteurs=["Marguerite Gurgand"], editeur="Mazarin",
            isbn="9782863740538",
        )
        candidate = {
            "titre": ["Les Demoiselles de Beaumoreau"],
            "auteurs": ["Gurgand, Marguerite"],
            "editeurs": ["Mazarine"],
            "dates": ["1981"],
            "identifiants": ["2863740539"],
            "url_notice": "https://example.invalid/notice",
        }
        state["documents"][oid]["recherches_bibliographiques"] = [{
            "query_signature": "old", "strategie": "old", "status": "resultats"
        }]
        with patch.object(app, "search_bnf", return_value={"source": "BnF", "status": "resultats", "results": [candidate]}):
            with patch.object(app, "search_open_library") as open_library, patch.object(app, "search_google_books") as google_books:
                app.enrich_bibliographic_candidates(state)
        book = state["documents"][oid]
        self.assertEqual(book["identification"]["statut"], "edition_identifiee")
        self.assertEqual(book["identification"]["notice_ancrage"]["url_notice"], candidate["url_notice"])
        self.assertTrue(book["identification"]["notice_ancrage"]["isbn_present_dans_notice"])
        self.assertEqual(book["annee_edition"], "1981")
        self.assertTrue(any(source.get("type") == "bibliographie" and source.get("champ") == "annee_edition" for source in book["sources_information"]))
        open_library.assert_not_called()
        google_books.assert_not_called()



    def test_notice_ancrage_conserve_plusieurs_isbn_sans_en_choisir_un(self):
        state = app.create_initial_state()
        document_id = app.create_document(
            state, titre="Dieu en questions", auteurs=["André Frossard"], editeur="Stock"
        )
        candidate = {
            "titre": ["Dieu en questions"],
            "auteurs": ["Frossard, André"],
            "editeurs": ["Stock"],
            "dates": ["1990"],
            "identifiants": ["ISBN 2220031322", "ISBN 2234022118"],
            "url_notice": "https://example.invalid/dieu-en-questions",
        }
        with patch.object(app, "search_bnf", return_value={"source": "BnF", "status": "resultats", "results": [candidate]}):
            with patch.object(app, "search_open_library") as open_library, patch.object(app, "search_google_books") as google_books:
                app.enrich_bibliographic_candidates(state)
        book = state["documents"][document_id]
        self.assertFalse(book.get("isbn"))
        identification = book["identification"]
        self.assertEqual(identification["isbns_notice_ancrage"], ["2220031322", "2234022118"])
        anchor = identification["notice_ancrage"]
        self.assertIsNone(anchor["isbn_recherche"])
        self.assertIsNone(anchor["isbn_present_dans_notice"])
        self.assertEqual(anchor["isbns_notice"], ["2220031322", "2234022118"])
        self.assertTrue(any(
            source.get("champ") == "isbns_notice_ancrage"
            and source.get("valeur") == ["2220031322", "2234022118"]
            for source in book["sources_information"]
        ))
        with tempfile.TemporaryDirectory() as temporary:
            csv_path = Path(temporary) / "inventaire.csv"
            app.export_csv(state, csv_path)
            csv_text = csv_path.read_text(encoding="utf-8-sig")
            self.assertIn("isbns_notice_ancrage", csv_text)
            with csv_path.open(encoding="utf-8-sig", newline="") as handle:
                row = next(csv.DictReader(handle, delimiter=";"))
            self.assertEqual(json.loads(row["isbns_notice_ancrage"]), ["2220031322", "2234022118"])
        open_library.assert_not_called()
        google_books.assert_not_called()

class ProgressionAndSearchStrategyTests(unittest.TestCase):
    def test_identification_non_validee_bloque_toutes_les_etapes_suivantes(self):
        book = {"identification": {"statut": "document_identifie_edition_a_confirmer"},
                "etat_general": {"appreciation": "bon", "observations": ["Couverture propre"]},
                "valorisation": {"statut": "valorisé"}}
        self.assertEqual(app.progression_status(book), "1. A identifier")
        book.pop("valorisation")
        book["identification"]["statut"] = "a_confirmer_par_recherche_bibliographique"
        self.assertEqual(app.progression_status(book), "1. A identifier")
        book["identification"]["statut"] = "edition_identifiee"
        book["etat_general"] = {"appreciation": None, "observations": []}
        self.assertEqual(app.progression_status(book), "3. Etat à préciser")
        book["etat_general"] = {"appreciation": "usé", "observations": ["Usure visible"]}
        book["identification"]["photos_complementaires"] = [{"necessaire": True}]
        self.assertEqual(app.progression_status(book), "3. Etat à préciser")
        book["identification"]["photos_complementaires"] = []
        self.assertEqual(app.progression_status(book), "4. Etat connu")
        book["valorisation"] = {"statut": "valorisé"}
        self.assertEqual(app.progression_status(book), "5. Valorisé")

    def test_google_books_est_desactive_par_defaut(self):
        self.assertFalse(app.RECHERCHE_GOOGLE_BOOKS_ACTIVE)

    def test_google_books_n_est_pas_appele_si_open_library_suffit(self):
        state = app.create_initial_state()
        oid = app.create_document(state, titre="Livre test", auteurs=["A. Auteur"], editeur="Éditions Test")
        candidate = {
            "titre": ["Livre test"], "auteurs": ["A. Auteur"],
            "editeurs": ["Éditions Test"], "dates": ["1990"],
            "identifiants": [], "url_notice": "https://example.invalid/ol",
        }
        with patch.object(app, "search_bnf", return_value={"source": "BnF", "status": "aucun_resultat", "results": []}):
            with patch.object(app, "search_open_library", return_value={"source": "Open Library", "status": "resultats", "results": [candidate]}):
                with patch.object(app, "search_google_books") as google_books:
                    app.enrich_bibliographic_candidates(state)
        google_books.assert_not_called()


class LastAIResponseTests(unittest.TestCase):
    def test_sortie_brute_est_sauvegardee_avant_le_decodage_json(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            photo = root / "Photo_1.jpg"
            photo.write_bytes(b"fake image bytes")
            raw = '{"documents": "sortie tronquee'
            last_response = root / "derniere_reponse_ia.txt"
            captured = {}

            class FakeResponses:
                def create(self, **kwargs):
                    captured.update(kwargs)
                    return types.SimpleNamespace(
                        output_text=raw,
                        id="resp_test",
                        status="incomplete",
                        incomplete_details={"reason": "max_output_tokens"},
                        usage={"input_tokens": 321, "output_tokens": 12000, "total_tokens": 12321},
                    )

            fake_openai = types.SimpleNamespace(
                OpenAI=lambda: types.SimpleNamespace(responses=FakeResponses())
            )
            with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}), patch.dict(
                sys.modules, {"openai": fake_openai}
            ):
                with self.assertRaises(__import__("json").JSONDecodeError):
                    app.analyze_photo(photo, last_response_path=last_response)

            saved = last_response.read_text(encoding="utf-8")
            self.assertIn(f"Modèle appelé : {app.MODEL}", saved)
            self.assertIn("Limite max_output_tokens : 12000", saved)
            self.assertIn("Photo envoyée : Photo_1.jpg", saved)
            self.assertIn("===== PROMPT COMPLET ENVOYÉ =====", saved)
            self.assertIn("Voici une photo d'un ou plusieurs documents.", saved)
            self.assertIn("\"input_tokens\": 321", saved)
            self.assertIn("\"output_tokens\": 12000", saved)
            self.assertEqual(captured["max_output_tokens"], 12000)

    def test_rejeu_derniere_reponse_ne_demande_pas_de_cle_api(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            last_response = root / "derniere_reponse_ia.txt"
            last_response.write_text(
                "===== MÉTADONNÉES DE L’APPEL API =====\n"
                f"Modèle appelé : {app.MODEL}\n"
                "===== PROMPT COMPLET ENVOYÉ =====\nPrompt de test\n"
                "===== DÉBUT DE LA SORTIE BRUTE DE L’API =====\n"
                '{"documents":[]}'
                "\n===== FIN DE LA SORTIE BRUTE DE L’API =====\n",
                encoding="utf-8",
            )
            with patch.dict(os.environ, {}, clear=True), patch.dict(
                sys.modules, {"openai": None}
            ):
                result = app.analyze_photo(
                    root / "photo_absente.jpg",
                    use_last_response=True,
                    last_response_path=last_response,
                )
            self.assertEqual(result["documents"], [])


if __name__ == "__main__":
    unittest.main()


class DocumentVocabularyV0510Tests(unittest.TestCase):
    def test_statuts_sont_numerotes_dans_l_ordre_du_parcours(self):
        cases = [
            ({"identification": {"statut": "a_confirmer_par_recherche_bibliographique"}, "etat_general": {}}, "1. A identifier"),
            ({"identification": {"statut": "edition_identifiee"}, "etat_general": {}}, "3. Etat à préciser"),
            ({"identification": {"statut": "edition_identifiee"}}, "2. Identifié"),
            ({"identification": {"statut": "edition_identifiee", "photos_complementaires": [{"necessaire": True}]}, "etat_general": {}}, "3. Etat à préciser"),
            ({"identification": {"statut": "edition_identifiee"}, "etat_general": {"appreciation": "bon"}}, "4. Etat connu"),
            ({"identification": {"statut": "edition_identifiee"}, "etat_general": {"appreciation": "non_evaluable", "observations": ["ancienne observation"]}}, "3. Etat à préciser"),
            ({"identification": {"statut": "edition_identifiee"}, "etat_general": {"appreciation": "bon"}, "valorisation": {"statut": "valorisé"}}, "5. Valorisé"),
        ]
        for document, expected in cases:
            with self.subTest(expected=expected):
                self.assertEqual(app.progression_status(document), expected)

class PublisherScoreTests(unittest.TestCase):
    def test_score_editeur_departage_trois_notices_simulees(self):
        publisher = "Desclée de Brouwer Stock/Laurence Pernoud"
        records = [
            {"titre": ["Dieu en questions"], "auteurs": ["A. Frossard"],
             "editeurs": ["Éditions du Cerf", "Gallimard"], "dates": ["1990"],
             "identifiants": [], "url_notice": "https://catalogue.bnf.fr/ark:/12148/cb35074863j"},
            {"titre": ["Dieu en questions"], "auteurs": ["A. Frossard"],
             "editeurs": ["Desclée de Brouwer", "Stock/Laurence Pernoud"], "dates": ["1991"],
             "identifiants": [], "url_notice": "https://catalogue.bnf.fr/ark:/12148/cb35074863k"},
            {"titre": ["Dieu en questions"], "auteurs": ["A. Frossard"],
             "editeurs": ["Gallimard"], "dates": ["1992"],
             "identifiants": [], "url_notice": "https://catalogue.bnf.fr/ark:/12148/cb35074863m"},
        ]
        self.assertEqual([app._publisher_score(record, publisher) for record in records], [0.0, 1.0, 0.0])
        publisher_multiligne = "Desclée de Brouwer\nStock/Laurence Pernoud"
        self.assertEqual([app._publisher_score(record, publisher_multiligne) for record in records], [0.0, 1.0, 0.0])
        result = {"source": "BnF Catalogue général (SRU)", "results": records}
        self.assertTrue(app._bnf_satisfactory(result, "Dieu en questions", "A. Frossard", {"editeur": publisher}))
        self.assertIsNone(app._publisher_score({"editeurs": []}, publisher))
        self.assertFalse(app._publisher_match({"editeurs": []}, publisher))

    def test_annee_de_la_derniere_note_departage_un_ex_aequo(self):
        publisher = "Desclée de Brouwer Stock/Laurence Pernoud"
        records = [
            {"titre": ["Dieu en questions"], "auteurs": ["A. Frossard"],
             "editeurs": ["Desclée de Brouwer", "Stock/Laurence Pernoud"], "dates": ["1990"]},
            {"titre": ["Dieu en questions"], "auteurs": ["A. Frossard"],
             "editeurs": ["Desclée de Brouwer", "Stock/Laurence Pernoud"], "dates": ["1991"]},
        ]
        result = {"results": records}
        sans_note = {"editeur": publisher}
        avec_note = {
            "editeur": publisher, "annee_edition": "1991",
            "sources_information": [
                {"type": "note", "champ": "annee_edition", "contenu": "1990"},
                {"type": "note", "champ": "annee_edition", "contenu": "1991"},
            ],
        }
        self.assertFalse(app._bnf_satisfactory(result, "Dieu en questions", "A. Frossard", sans_note))
        self.assertTrue(app._bnf_satisfactory(result, "Dieu en questions", "A. Frossard", avec_note))

    def test_classement_historique_reprend_score_et_absence_editeur_sans_ecart(self):
        state = app.create_initial_state()
        oid = app.create_document(
            state, titre="Dieu en questions", auteurs=["A. Frossard"],
            editeur="Desclée de Brouwer Stock/Laurence Pernoud",
        )
        records = [
            {"titre": ["Dieu en questions"], "auteurs": ["A. Frossard"],
             "editeurs": ["Desclée de Brouwer", "Stock/Laurence Pernoud"], "dates": ["1991"],
             "identifiants": [], "url_notice": "https://catalogue.bnf.fr/ark:/12148/cb35074863k"},
            {"titre": ["Dieu en questions"], "auteurs": ["A. Frossard"],
             "editeurs": [], "dates": ["1991"], "identifiants": [],
             "url_notice": "https://openlibrary.org/works/OL000W"},
        ]
        result = {"source": "BnF Catalogue général (SRU)", "status": "resultats", "results": records}
        with patch.object(app, "search_bnf", return_value=result):
            app.enrich_bibliographic_candidates(state)
        history = state["documents"][oid]["recherches_bibliographiques"][-1]
        ranking = history["classement_notices"]
        self.assertEqual(ranking[0]["url_notice"], "https://catalogue.bnf.fr/ark:/12148/cb35074863k")
        self.assertEqual(ranking[0]["score_editeur"], 1.0)
        self.assertIsNone(next(row for row in ranking if row["url_notice"].endswith("OL000W"))["score_editeur"])
        self.assertNotIn("ecart_editeur", history.get("evaluation_candidat", {}))


class StructuredStateTests(unittest.TestCase):
    def test_demandes_photo_sont_ciblees_et_excluent_isbn_pour_magazine(self):
        state = app.create_initial_state()
        livre_id = app.create_document(state, type_document="livre", titre="Livre test")
        magazine_id = app.create_document(state, type_document="magazine", titre="Magazine test")
        app.refresh_missing_information(state)
        demandes_livre = state["documents"][livre_id]["identification"]["demandes_photo"]
        demandes_magazine = state["documents"][magazine_id]["identification"]["demandes_photo"]
        self.assertEqual(demandes_livre["isbn"], "code-barres / 4e de couverture")
        self.assertEqual(demandes_livre["edition"], "page de titre et son verso")
        self.assertNotIn("isbn", demandes_magazine)
        with tempfile.TemporaryDirectory() as temporary:
            csv_path = Path(temporary) / "inventaire.csv"
            app.export_csv(state, csv_path)
            csv_text = csv_path.read_text(encoding="utf-8-sig")
        self.assertIn("demandes_photo", csv_text)
        self.assertIn("code-barres / 4e de couverture", csv_text)

    def test_etat_general_est_integre_et_non_evaluable_ne_fait_pas_progresser(self):
        state = app.create_initial_state()
        oid = app.create_document(state, titre="Livre test")
        state["documents"][oid]["identification"]["statut"] = "edition_identifiee"
        photo_path = "photos/Photo_1.jpg"
        state["photos"][photo_path] = {
            "path": photo_path, "document_ids": [], "roles": [],
            "analysis_status": "pending_analysis",
        }
        field = lambda value: {
            "valeur": value, "confiance": "élevée", "origine": "photo",
            "statut_lecture": "non_visible" if value is None else "lisible",
        }
        result = {"documents": [{
            "reference": "detection_1", "document_id_reference": oid,
            "position": "centre", "type_document": "livre",
            "titre": field("Livre test"), "sous_titre": field(None),
            "auteurs": field(None), "editeur": field(None), "edition": field(None),
            "isbn": field(None), "collection": field(None),
            "annee_edition": field(None), "annee_impression": field(None),
            "date_depot_legal": field(None), "description_illustration": "",
            "autres_textes": [],
            "etat_general": {"appreciation": "bon", "motif": "Couverture propre, usure légère compatible avec un livre lu."},
        }]}
        app.apply_photo_analysis(state, photo_path, result)
        etat_general = state["documents"][oid]["etat_general"]
        self.assertEqual(etat_general["appreciation"], "bon")
        self.assertEqual(etat_general["observations"], ["Couverture propre, usure légère compatible avec un livre lu."])
        self.assertNotIn("defauts", etat_general)
        self.assertNotIn("informations_non_visibles", etat_general)
        self.assertEqual(etat_general["base"], "premiere_photo_presumee_representative")
        self.assertEqual(app.progression_status(state["documents"][oid]), "4. Etat connu")
        etat_general["appreciation"] = "non_evaluable"
        etat_general["observations"] = ["ancienne observation"]
        self.assertEqual(app.progression_status(state["documents"][oid]), "3. Etat à préciser")

    def test_document_to_detection_normalise_les_retours_a_la_ligne(self):
        field = lambda value: {"valeur": value, "confiance": "élevée", "origine": "photo", "statut_lecture": "lisible"}
        detection = app.document_to_detection({
            "titre": field("DIEU\nEN QUESTIONS"),
            "sous_titre": field("Un\nessai"),
            "auteurs": field("André\nFrossard"),
            "editeur": field("DDB\nStock"),
            "etat_general": {"appreciation": "bon", "motif": "Couverture propre."},
        })
        propose = detection["identification_proposee"]
        self.assertEqual(propose["titre"]["valeur"], "DIEU EN QUESTIONS")
        self.assertEqual(propose["sous_titre"]["valeur"], "Un essai")
        self.assertEqual(propose["auteurs"]["valeur"], "André Frossard")
        self.assertEqual(propose["editeur"]["valeur"], "DDB\nStock")
        self.assertEqual(detection["etat_general"], {
            "appreciation": "bon", "motif": "Couverture propre.",
            "origine": "photo", "statut": "propose_non_verifie",
        })

    def test_reanalyse_remplace_etat_non_evaluable(self):
        state = app.create_initial_state()
        document_id = app.create_document(state, titre="Livre test")
        state["documents"][document_id]["etat_general"].update({
            "appreciation": "non_evaluable",
            "observations": [],
            "base": "premiere_photo_presumee_representative",
        })
        photo_path = "photos/Photo_1.jpg"
        state["photos"][photo_path] = {"role": "identification"}
        app._integrer_etat_propose(state, photo_path, document_id, {
            "etat_general": {
                "appreciation": "bon",
                "motif": "Usure normale d'un livre lu.",
                "origine": "photo",
                "statut": "propose_non_verifie",
            }
        })
        etat = state["documents"][document_id]["etat_general"]
        self.assertEqual(etat["appreciation"], "bon")
        self.assertEqual(etat["observations"], ["Usure normale d'un livre lu."])

class ExtendedAIAnalysisTests(unittest.TestCase):
    def test_schema_ia_conserve_les_noms_canoniques(self):
        schema = app.response_schema()
        self.assertEqual(set(schema["properties"]), {"documents"})
        document = schema["properties"]["documents"]["items"]
        expected = {
            "reference", "document_id_reference", "position", "type_document",
            "titre", "sous_titre", "auteurs", "editeur", "edition", "isbn",
            "collection", "annee_edition", "annee_impression", "date_depot_legal",
            "description_illustration", "autres_textes", "etat_general",
        }
        self.assertEqual(set(document["properties"]), expected)
        for key in ("annee_edition", "annee_impression"):
            self.assertIn(key, document["required"])
        self.assertIn("description_illustration", document["required"])
        self.assertIn("etat_general", document["required"])
        self.assertNotIn("annee", document["properties"])
        self.assertNotIn("date_impression", document["properties"])
        self.assertNotIn("description_visuelle", document["properties"])
        etat = document["properties"]["etat_general"]
        self.assertEqual(set(etat["required"]), {"appreciation", "motif"})
        self.assertEqual(set(etat["properties"]), {"appreciation", "motif"})
        self.assertEqual(etat["properties"]["appreciation"]["enum"], ["tres_bon", "bon", "correct", "mauvais", "non_evaluable"])
        self.assertFalse(etat["additionalProperties"])

    def test_analyse_photo_n_active_aucun_outil_web_et_envoie_le_prompt_attendu(self):
        with tempfile.TemporaryDirectory() as temporary:
            photo = Path(temporary) / "Photo_1.jpg"
            photo.write_bytes(b"fake image bytes")
            captured = {}
            class FakeResponses:
                def create(self, **kwargs):
                    captured.update(kwargs)
                    return types.SimpleNamespace(output_text='{"documents":[]}')
            fake_openai = types.SimpleNamespace(OpenAI=lambda: types.SimpleNamespace(responses=FakeResponses()))
            with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}), patch.dict(sys.modules, {"openai": fake_openai}):
                app.analyze_photo(photo)
            self.assertNotIn("tools", captured)
            self.assertNotIn("tool_choice", captured)
            self.assertEqual(captured["service_tier"], "flex")
            api_schema = captured["text"]["format"]["schema"]
            self.assertEqual(set(api_schema["properties"]), {"documents"})
            prompt = captured["input"][0]["content"][0]["text"]
            self.assertIn("Voici une photo d'un ou plusieurs documents.", prompt)
            self.assertIn("décrire en une phrase simple l'illustration", prompt)
            self.assertIn("donner un état général", prompt)
            self.assertIn("n'invente pas de fausse information", prompt)
            self.assertNotIn("identification_web", prompt)
            self.assertNotIn("sources effectivement consultées", prompt)
        self.assertNotIn("temperature", captured)

    def test_temperature_optionnelle_est_transmise_et_diagnostic_est_separe(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            photo = root / "Photo_1.jpg"
            photo.write_bytes(b"fake image bytes")
            diagnostic = root / "diagnostic_temporaire.txt"
            captured = {}
            class FakeResponses:
                def create(self, **kwargs):
                    captured.update(kwargs)
                    return types.SimpleNamespace(output_text='{"documents":[]}')
            fake_openai = types.SimpleNamespace(OpenAI=lambda: types.SimpleNamespace(responses=FakeResponses()))
            with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}), patch.dict(sys.modules, {"openai": fake_openai}):
                app.analyze_photo(photo, temperature=0, last_response_path=diagnostic)
            self.assertEqual(captured["temperature"], 0)
            self.assertTrue(diagnostic.is_file())
            self.assertIn("Température : 0", diagnostic.read_text(encoding="utf-8"))

    def test_conversion_conserve_description_et_statuts_etat_general(self):
        field = lambda value, status="lisible": {
            "valeur": value, "confiance": "élevée", "origine": "photo",
            "statut_lecture": status,
        }
        doc = {
            "reference": "detection_1", "document_id_reference": None,
            "position": "centre", "type_document": "guide",
            "titre": field("Titre test"),
            "sous_titre": field(None, "non_visible"),
            "auteurs": field("Auteur Test"),
            "editeur": field("Éditions incertaines", "incertain"),
            "edition": field(None, "non_visible"),
            "isbn": field(None, "non_visible"),
            "collection": field(None, "non_visible"),
            "annee_edition": field(None, "non_visible"),
            "annee_impression": field(None, "non_visible"),
            "date_depot_legal": field(None, "non_visible"),
            "description_illustration": "Illustration beige et rouge, avec un château",
            "autres_textes": [
                {"texte": "Auteur Test", "statut_lecture": "lisible", "hesitation": ""},
                {"texte": "Collection A", "statut_lecture": "lisible", "hesitation": ""},
            ],
            "etat_general": {"appreciation": "bon", "motif": "Couverture propre."},
        }
        detection = app.document_to_detection(doc)
        self.assertEqual(detection["description_illustration"], doc["description_illustration"])
        self.assertEqual(detection["type_document"], "guide")
        self.assertEqual(detection["identification_proposee"]["titre"]["statut_lecture"], "lisible")
        self.assertEqual(detection["identification_proposee"]["auteurs"]["statut_lecture"], "lisible")
        self.assertEqual(detection["identification_proposee"]["editeur"]["statut_lecture"], "incertain")
        self.assertEqual(detection["autres_textes"], [
            {"texte": "Collection A", "statut_lecture": "lisible", "hesitation": ""},
        ])
        self.assertEqual(detection["etat_general"]["origine"], "photo")
        self.assertEqual(detection["etat_general"]["appreciation"], "bon")
        self.assertEqual(detection["etat_general"]["motif"], "Couverture propre.")
        for legacy_field in ("annee", "date_impression", "description_visuelle"):
            self.assertNotIn(legacy_field, detection)

class TemporaryAIErrorHandlingTests(unittest.TestCase):
    def test_erreur_api_preserve_analyse_valide_et_retentative_au_lancement_suivant(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            photo_path = "photos/Photo_1.jpg"
            previous_analysis = {
                "analyzed_at": "2026-10-16T12:00:00+02:00",
                "documents_detectes": [{"reference": "resultat_valide"}],
                "marker": "dernier_resultat_valide",
            }
            photo_record = {
                "path": photo_path,
                "analysis_status": "pending_analysis",
                "analysis": json.loads(json.dumps(previous_analysis)),
            }
            state = {
                "photos": {photo_path: photo_record},
                "documents": {},
                "runs": [],
            }
            args = types.SimpleNamespace(
                last_reponse=False,
                no_ai=False,
                photos=root / "photos",
                state=root / "inventaire.json",
                notes=root / "notes.txt",
                csv=root / "inventaire.csv",
                photo_instructions=root / "photos.txt",
            )
            biblio_summary = {
                "documents_recherches": 0,
                "bnf_concordant": 0,
                "catalogues_complementaires": 0,
                "open_library_notices": 0,
                "google_books_notices": 0,
                "documents_sans_notice": 0,
                "documents_avec_erreur": 0,
                "erreurs_sources": 0,
            }

            def run_main(analyze_kwargs):
                with (
                    patch.object(app, "print_version"),
                    patch.object(app, "parse_args", return_value=args),
                    patch.object(app, "load_state", return_value=state),
                    patch.object(app, "scan_photos", return_value=([], [], [])),
                    patch.object(app, "read_photo_instructions", return_value=({}, [], False, [])),
                    patch.object(app, "read_notes", return_value=(None, False)),
                    patch.object(app, "integrate_unambiguous_detections"),
                    patch.object(app, "enrich_bibliographic_candidates", return_value=biblio_summary),
                    patch.object(app, "refresh_missing_information"),
                    patch.object(app, "write_outputs"),
                    patch.object(app, "print_report"),
                    patch.object(app, "analyze_photo", **analyze_kwargs) as analyze_mock,
                ):
                    result = app.main()
                return result, analyze_mock

            result, first_call = run_main({
                "side_effect": RuntimeError("Flex temporairement indisponible")
            })
            self.assertEqual(result, 0)
            self.assertEqual(first_call.call_count, 1)
            self.assertEqual(photo_record["analysis_status"], "analysis_error")
            self.assertEqual(photo_record["last_error"], "Flex temporairement indisponible")
            self.assertEqual(photo_record["analysis"], previous_analysis)
            self.assertEqual(state["runs"][-1]["api_errors"], 1)

            # Le statut analysis_error est inclus dans les photos à retenter au prochain lancement.
            result, second_call = run_main({"return_value": {"documents": []}})
            self.assertEqual(result, 0)
            self.assertEqual(second_call.call_count, 1)
            self.assertEqual(photo_record["analysis_status"], "analyzed")
            self.assertEqual(photo_record["analysis"]["documents_detectes"], [])
            self.assertEqual(state["runs"][-1]["api_errors"], 0)

class FlexFallbackTests(unittest.TestCase):
    def test_flex_unavailable_reessaie_apres_30_et_60_secondes_puis_repli_standard(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            photo = root / "Photo_1.jpg"
            photo.write_bytes(b"fake image bytes")
            diagnostic = root / "diagnostic_temporaire.txt"
            calls = []
            client_options = []

            class FlexUnavailableError(Exception):
                code = "flex_unavailable"
                body = {"error": {"code": "flex_unavailable"}}

            class FakeResponses:
                def create(self, **kwargs):
                    calls.append(kwargs)
                    if "service_tier" in kwargs:
                        raise FlexUnavailableError("Flex processing is temporarily unavailable")
                    return types.SimpleNamespace(output_text='{"documents":[]}')

            class FakeClient:
                responses = FakeResponses()

                def with_options(self, **kwargs):
                    client_options.append(kwargs)
                    return self

            fake_openai = types.SimpleNamespace(OpenAI=lambda: FakeClient())
            with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}), patch.dict(
                sys.modules, {"openai": fake_openai}
            ), patch.object(app.time, "sleep") as sleep:
                result = app.analyze_photo(photo, last_response_path=diagnostic)

            self.assertEqual(result, {"documents": []})
            self.assertEqual(len(calls), 4)
            self.assertTrue(all(call["service_tier"] == "flex" for call in calls[:3]))
            self.assertNotIn("service_tier", calls[3])
            self.assertEqual([call.args for call in sleep.call_args_list], [(30,), (60,)])
            self.assertEqual(client_options, [{"max_retries": 0}])
            self.assertIn(
                "Niveau de traitement API : standard (repli après flex_unavailable)",
                diagnostic.read_text(encoding="utf-8"),
            )

    def test_flex_reussi_apres_un_reessai_ne_declenche_pas_le_repli(self):
        with tempfile.TemporaryDirectory() as temporary:
            photo = Path(temporary) / "Photo_1.jpg"
            photo.write_bytes(b"fake image bytes")
            calls = []

            class FlexUnavailableError(Exception):
                code = "flex_unavailable"

            class FakeResponses:
                def create(self, **kwargs):
                    calls.append(kwargs)
                    if len(calls) == 1:
                        raise FlexUnavailableError("Flex processing is temporarily unavailable")
                    return types.SimpleNamespace(output_text='{"documents":[]}')

            class FakeClient:
                responses = FakeResponses()

                def with_options(self, **kwargs):
                    return self

            fake_openai = types.SimpleNamespace(OpenAI=lambda: FakeClient())
            with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}), patch.dict(
                sys.modules, {"openai": fake_openai}
            ), patch.object(app.time, "sleep") as sleep:
                result = app.analyze_photo(photo)

            self.assertEqual(result, {"documents": []})
            self.assertEqual(len(calls), 2)
            self.assertTrue(all(call["service_tier"] == "flex" for call in calls))
            sleep.assert_called_once_with(30)

    def test_autre_erreur_api_ne_declenche_pas_de_reessai_ni_de_repli(self):
        with tempfile.TemporaryDirectory() as temporary:
            photo = Path(temporary) / "Photo_1.jpg"
            photo.write_bytes(b"fake image bytes")
            calls = []
            client_options = []

            class FakeResponses:
                def create(self, **kwargs):
                    calls.append(kwargs)
                    raise RuntimeError("Erreur API non liée à Flex")

            class FakeClient:
                responses = FakeResponses()

                def with_options(self, **kwargs):
                    client_options.append(kwargs)
                    return self

            fake_openai = types.SimpleNamespace(OpenAI=lambda: FakeClient())
            with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}), patch.dict(
                sys.modules, {"openai": fake_openai}
            ):
                with self.assertRaisesRegex(RuntimeError, "non liée à Flex"):
                    app.analyze_photo(photo)

            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0]["service_tier"], "flex")
            self.assertEqual(client_options, [{"max_retries": 0}])
