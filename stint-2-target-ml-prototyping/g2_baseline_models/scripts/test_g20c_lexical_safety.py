import unittest
from unittest.mock import patch

import g20c_neutral_ngram_extraction as extraction
from g20c_lexical_safety import restricted_match


class LexicalSafetyTests(unittest.TestCase):
    def test_compound_and_case(self):
        self.assertTrue(restricted_match("affectedSITEALPHA", ("sitealpha",)))
        self.assertFalse(restricted_match("bearing failure", ("sitealpha",)))

    def test_excludes_ngram_without_bridging_removed_token(self):
        with patch("g20c_lexical_safety.restricted_terms", return_value=("sitealpha",)):
            terms = list(extraction.ngrams(["main", "sitealpha", "bearing"]))
        self.assertEqual(terms, ["main", "bearing"])
        self.assertNotIn("main bearing", terms)

    def test_normalisation_and_semantic_hash_not_changed(self):
        with patch("g20c_lexical_safety.restricted_terms", return_value=("sitealpha",)):
            tokens, _ = extraction.normalise_text("main sitealpha bearing")
        self.assertEqual(tokens, ["main", "sitealpha", "bearing"])


if __name__ == "__main__":
    unittest.main()
