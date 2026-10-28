"""Tests ciblés de la clé réservée ignore dans notes.txt."""

import copy
import tempfile
import unittest
from pathlib import Path

import creer_bibliotheque as cb


class TestNotesIgnore(unittest.TestCase):
    def _document(self):
        return {
            "titre": "Livre à vérifier",
            "isbn": "",
            "updated_at": "2026-10-01T12:00:00",
            "identification": {
                "statut": "edition_identifiee",
                "niveau_confiance": "élevée",
            },
            "sources_information": [],
        }

    def test_ignore_conserve_le_commentaire_sans_modifier_le_document(self):
        document = self._document()
        original = copy.deepcopy(document)
        state = {"documents": {"document_0009": document}}
        with tempfile.TemporaryDirectory() as directory:
            notes = Path(directory) / "notes.txt"
            notes.write_text(
                "document_0009;ignore;note pour moi : livre à vérifier\n",
                encoding="utf-8",
            )
            _, changed = cb.read_notes(notes, state)

        self.assertTrue(changed)
        self.assertEqual(state["documents"]["document_0009"], original)
        self.assertEqual(len(state["notes"]["informations"]), 1)
        self.assertEqual(
            state["notes"]["informations"][0]["statut_application"],
            "commentaire_personnel_ignore",
        )
        self.assertEqual(
            state["notes"]["informations"][0]["contenu"],
            "note pour moi : livre à vérifier",
        )

    def test_une_cle_bibliographique_continue_a_s_appliquer(self):
        state = {"documents": {"document_0009": self._document()}}
        with tempfile.TemporaryDirectory() as directory:
            notes = Path(directory) / "notes.txt"
            notes.write_text(
                "document_0009;isbn;9782262012281\n",
                encoding="utf-8",
            )
            cb.read_notes(notes, state)

        document = state["documents"]["document_0009"]
        self.assertEqual(document["isbn"], "9782262012281")
        self.assertEqual(
            document["identification"]["statut"],
            "a_confirmer_par_recherche_bibliographique",
        )

    def test_statut_force_depuis_notes(self):
        state = {"documents": {"document_0009": self._document()}}
        with tempfile.TemporaryDirectory() as directory:
            notes = Path(directory) / "notes.txt"
            notes.write_text(
                "document_0009;statut;9. Abandonné\n",
                encoding="utf-8",
            )
            cb.read_notes(notes, state)

        document = state["documents"]["document_0009"]
        self.assertEqual(document["statut_force"], "9. Abandonné")
        self.assertEqual(cb.progression_status(document), "9. Abandonné")

    def test_statut_auto_retablit_le_calcul(self):
        document = self._document()
        document["statut_force"] = "9. Abandonné"
        state = {"documents": {"document_0009": document}}
        with tempfile.TemporaryDirectory() as directory:
            notes = Path(directory) / "notes.txt"
            notes.write_text("document_0009;statut;auto\n", encoding="utf-8")
            cb.read_notes(notes, state)

        self.assertNotIn("statut_force", document)
        self.assertEqual(cb.progression_status(document), "2. Identifié")

    def test_statut_invalide_est_refuse(self):
        state = {"documents": {"document_0009": self._document()}}
        with tempfile.TemporaryDirectory() as directory:
            notes = Path(directory) / "notes.txt"
            notes.write_text("document_0009;statut;inconnu\n", encoding="utf-8")
            cb.read_notes(notes, state)

        document = state["documents"]["document_0009"]
        self.assertNotIn("statut_force", document)
        self.assertEqual(cb.progression_status(document), "2. Identifié")
        self.assertEqual(state["notes"]["informations"][0]["statut_application"], "valeur_invalide")


if __name__ == "__main__":
    unittest.main()
