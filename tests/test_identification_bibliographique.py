"""Tests de régression ciblés pour l’identification bibliographique."""
import unittest

import creer_bibliotheque as cb


class TestIdentificationBibliographique(unittest.TestCase):
    def test_titre_avec_sous_titre(self):
        record = {"titre": ["François Ier ou Le rêve italien"]}
        self.assertTrue(cb._title_match_or_near(record, "François Ier", "ou le rêve italien"))

    def test_titre_abrege_accepte_avec_isbn_exact(self):
        record = {
            "titre": ["François Ier ou Le rêve italien"],
            "identifiants": ["9782262012281"],
        }
        self.assertTrue(cb._title_matches_for_isbn_anchor(record, "François Ier", "9782262012281"))

    def test_titre_abrege_refuse_sans_isbn_exact(self):
        record = {
            "titre": ["François Ier ou Le rêve italien"],
            "identifiants": ["9780000000002"],
        }
        self.assertFalse(cb._title_matches_for_isbn_anchor(record, "François Ier", "9782262012281"))

    def test_auteurs_multiples_separes_par_et_et_role(self):
        record = {
            "auteurs": [
                "Lustiger, Jean-Marie",
                "Missika, Jean-Louis",
                "Wolton, Dominique",
            ]
        }
        self.assertTrue(cb._author_match(
            record,
            "Jean-Marie Lustiger; Jean-Louis Missika et Dominique Wolton (entretiens)",
        ))

    def test_auteur_manquant_ne_concorde_pas(self):
        record = {
            "auteurs": ["Lustiger, Jean-Marie", "Missika, Jean-Louis"]
        }
        self.assertFalse(cb._author_match(
            record,
            "Jean-Marie Lustiger; Jean-Louis Missika et Dominique Wolton (entretiens)",
        ))


if __name__ == "__main__":
    unittest.main()
