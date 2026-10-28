import csv
import json
import tempfile
import unittest
from pathlib import Path

import creer_bibliotheque as cb


class ContratIA11Tests(unittest.TestCase):
    def test_schema_reponse_contient_champs_bibliographiques_distincts(self):
        schema = cb.response_schema()
        document = schema["properties"]["documents"]["items"]
        properties = document["properties"]
        expected = {
            "type_document", "titre", "sous_titre", "auteurs", "editeur",
            "edition", "isbn", "collection", "annee_edition",
            "annee_impression", "date_depot_legal",
            "description_illustration", "autres_textes", "etat_general",
        }
        self.assertTrue(expected.issubset(properties))
        self.assertTrue(expected.issubset(set(document["required"])))
        self.assertNotIn("edition_editeur", properties)
        self.assertNotIn("autres_textes_couverture", properties)

    def test_une_photo_peut_avoir_zero_document_detecte(self):
        schema = cb.response_schema()["properties"]["documents"]
        self.assertEqual(schema["type"], "array")
        self.assertNotIn("minItems", schema)
        self.assertNotIn("maxItems", schema)

        state = {"photos": {"photos/vide.jpg": {}}, "documents": {}}
        cb.apply_photo_analysis(state, "photos/vide.jpg", {"documents": []})
        self.assertEqual(
            state["photos"]["photos/vide.jpg"]["analysis"]["documents_detectes"],
            [],
        )
        self.assertEqual(state["photos"]["photos/vide.jpg"]["analysis_status"], "analyzed")

    def test_analyse_vers_fiche_et_csv_conserve_illustration_textes_et_provenance(self):
        def field(value, status="lisible"):
            return {
                "valeur": value,
                "confiance": "élevée",
                "origine": "photo",
                "statut_lecture": status,
            }

        raw = {
            "reference": "detection_1", "document_id_reference": None,
            "position": "couverture", "type_document": "livre",
            "titre": field("Le livre test"),
            "sous_titre": field("Sous-titre test"),
            "auteurs": field("Auteur Test"),
            "editeur": field("Éditions Test"),
            "edition": field("Deuxième édition"),
            "isbn": field("9780000000002"),
            "collection": field("Collection Test"),
            "annee_edition": field("1985"),
            "annee_impression": field(None, "non_visible"),
            "date_depot_legal": field(None, "non_visible"),
            "description_illustration": "Un paysage bleu avec un arbre.",
            "autres_textes": [{
                "texte": "Prix : 25 F",
                "statut_lecture": "lisible",
                "hesitation": "",
            }],
            "etat_general": {"appreciation": "bon", "motif": "Couverture bien conservée."},
        }
        state = {
            "photos": {
                "photos/test.jpg": {
                    "document_ids": [], "roles": [], "role": "identification",
                },
            },
            "documents": {},
        }

        cb.apply_photo_analysis(state, "photos/test.jpg", {"documents": [raw]})
        cb.integrate_unambiguous_detections(state)
        document = next(iter(state["documents"].values()))

        self.assertEqual(document["description_illustration"], raw["description_illustration"])
        self.assertEqual(document["annee_edition"], "1985")
        self.assertIsNone(document["annee_impression"])
        self.assertIn("etat_general", document)
        for legacy_key in ("annee", "date_impression", "etat"):
            self.assertNotIn(legacy_key, document)
        self.assertEqual(document["autres_textes"], raw["autres_textes"])
        title_source = next(
            source for source in document["sources_information"]
            if source["champ"] == "titre"
        )
        self.assertEqual(title_source["valeur"]["confiance"], "élevée")
        self.assertEqual(title_source["valeur"]["origine"], "photo")
        self.assertEqual(title_source["valeur"]["statut_lecture"], "lisible")
        hidden_date_source = next(
            source for source in document["sources_information"]
            if source["champ"] == "annee_impression"
        )
        self.assertEqual(hidden_date_source["valeur"]["statut_lecture"], "non_visible")

        with tempfile.TemporaryDirectory() as directory:
            csv_path = Path(directory) / "inventaire.csv"
            cb.export_csv(state, csv_path)
            with csv_path.open(encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle, delimiter=";")
                self.assertEqual(reader.fieldnames[reader.fieldnames.index("isbn") + 1], "etat_general")
                self.assertIn("etat_general_details", reader.fieldnames)
                row = next(reader)
            self.assertEqual(row["etat_general"], "bon")
            self.assertEqual(row["description_illustration"], raw["description_illustration"])
            self.assertEqual(row["annee_edition"], "1985")
            self.assertEqual(row["annee_impression"], "")
            for legacy_column in ("annee", "date_impression", "etat", "etat_appreciation", "etat_observations"):
                self.assertNotIn(legacy_column, row)
            self.assertEqual(json.loads(row["autres_textes"]), raw["autres_textes"])
            sources = json.loads(row["sources_information"])
            csv_title_source = next(source for source in sources if source["champ"] == "titre")
            self.assertEqual(csv_title_source["valeur"]["statut_lecture"], "lisible")
            etat_general = json.loads(row["etat_general_details"])
            self.assertEqual(etat_general["appreciation"], "bon")
            self.assertEqual(etat_general["observations"], ["Couverture bien conservée."])

    def test_export_csv_reduit_respecte_le_format_compact(self):
        state = {
            "photos": {},
            "documents": {
                "document_0001": {
                    "id": "document_0001",
                    "type_document": "livre",
                    "titre": "Couleur du temps",
                    "auteurs": ["Françoise Chandernagor"],
                    "editeur": "Gallimard",
                    "annee_edition": "2004",
                    "isbn": "9782070771837",
                    "collection": None,
                    "edition": None,
                    "annee_impression": None,
                    "date_depot_legal": None,
                    "autres_textes": [
                        {"texte": "de l’Académie Goncourt"},
                        {"texte": "roman"},
                    ],
                    "etat_general": {
                        "appreciation": "bon",
                        "observations": ["légers frottements"],
                    },
                    "identification": {
                        "statut": "edition_identifiee",
                        "notice_ancrage": {
                            "source": "BnF Catalogue général (SRU)",
                        },
                    },
                },
            },
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "inventaire_réduit.csv"
            cb.export_csv_reduit(state, path)
            with path.open(encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle, delimiter="|")
                self.assertEqual(reader.fieldnames, [
                    "id", "type", "titre", "auteurs", "editeur", "annee",
                    "isbn", "identif", "mentions", "etat", "manque",
                ])
                row = next(reader)
        self.assertEqual(row["id"], "document_0001")
        self.assertEqual(row["type"], "livre")
        self.assertEqual(row["titre"], "Couleur du temps")
        self.assertEqual(row["auteurs"], "Françoise Chandernagor")
        self.assertEqual(row["editeur"], "Gallimard")
        self.assertEqual(row["annee"], "2004")
        self.assertEqual(row["isbn"], "9782070771837")
        self.assertEqual(row["identif"], "confirmée (BnF)")
        self.assertEqual(row["mentions"], "de l’Académie Goncourt ; roman")
        self.assertEqual(row["etat"], "bon, légers frottements")
        self.assertEqual(row["manque"], "collection ; édition ; impression ; dépôt légal")

    def test_write_outputs_cree_les_deux_exports_csv(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state_path = root / "inventaire.json"
            csv_path = root / "inventaire.csv"
            cb.write_outputs({"photos": {}, "documents": {}}, state_path, csv_path)
            self.assertTrue(state_path.is_file())
            self.assertTrue(csv_path.is_file())
            self.assertTrue((root / "inventaire_réduit.csv").is_file())

    def test_conversion_separe_annees_et_mentions(self):
        def field(value):
            return {
                "valeur": value, "confiance": "élevée", "origine": "photo",
                "statut_lecture": "lisible" if value is not None else "non_visible",
            }

        raw = {
            "reference": "detection_1", "document_id_reference": None,
            "position": "page intérieure", "type_document": "livre",
            "titre": field(None), "sous_titre": field(None), "auteurs": field(None),
            "editeur": field("Firmin-Didot S.A."),
            "edition": field("4264"), "isbn": field("2-246-00257-5"),
            "collection": field(None), "annee_edition": field(None),
            "annee_impression": field("1975"),
            "date_depot_legal": field("3e trimestre 1975"),
            "description_illustration": "Aucune illustration.",
            "autres_textes": [{
                "texte": "Numéro d’impression : 7458",
                "statut_lecture": "lisible", "hesitation": "",
            }],
            "etat_general": {"appreciation": "non_evaluable", "motif": "Page intérieure seulement."},
        }
        converted = cb.document_to_detection(raw)
        proposed = converted["identification_proposee"]
        self.assertEqual(proposed["editeur"]["valeur"], "Firmin-Didot S.A.")
        self.assertEqual(proposed["edition"]["valeur"], "4264")
        self.assertEqual(proposed["isbn"]["valeur"], "2-246-00257-5")
        self.assertIsNone(proposed["annee_edition"]["valeur"])
        self.assertEqual(proposed["annee_impression"]["valeur"], "1975")
        self.assertEqual(proposed["date_depot_legal"]["valeur"], "3e trimestre 1975")
        self.assertNotIn("annee", proposed)
        self.assertNotIn("date_impression", proposed)
        self.assertEqual(converted["description_illustration"], "Aucune illustration.")
        self.assertEqual(proposed["autres_textes"][0]["texte"], "Numéro d’impression : 7458")

    def test_inventaire_ancien_schema_est_refuse(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "inventaire.json"
            path.write_text(json.dumps({"schema_version": "0.21"}), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "repars d'un inventaire neuf"):
                cb.load_state(path)


if __name__ == "__main__":
    unittest.main()
