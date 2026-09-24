"""Focused mapping contract tests; no model download or evaluation labels."""

import unittest

import numpy as np
from g20c_step4_catalogue_mapping import accepted_indices, lexical_support, read_catalogue


class MappingContracts(unittest.TestCase):
    def test_zero_candidates_is_allowed(self):
        self.assertEqual(accepted_indices(np.array([0.59, 0.2])).tolist(), [])
        self.assertEqual(accepted_indices(np.array([])).tolist(), [])

    def test_all_ties_are_preserved_without_top_k(self):
        self.assertEqual(len(accepted_indices(np.repeat(0.9, 100))), 100)

    def test_threshold_and_near_best_margin(self):
        self.assertEqual(accepted_indices(np.array([0.8, 0.75, 0.65])).tolist(), [0, 1])
        self.assertEqual(accepted_indices(np.array([0.6])).tolist(), [0])

    def test_wrong_components_are_rejected(self):
        for query, candidate in [
            ("crane", "Rotor"),
            ("stack", "Cpu"),
            ("yaw motor", "Yaw Bearing"),
            ("yaw lubrication pump", "Oil, Lubricant"),
        ]:
            with self.subTest(query=query):
                self.assertEqual(lexical_support(query, candidate, "Object Part"), "")

    def test_action_and_plural_forms(self):
        self.assertEqual(lexical_support("replace", "REPLACED", "Activity"), "replace")
        self.assertEqual(lexical_support("motors", "Motor", "Object Part"), "motor")
        self.assertEqual(lexical_support("assessment", "ADJUSTED", "Activity"), "")

    def test_catalogue_keys_and_anomaly(self):
        source = read_catalogue()
        self.assertEqual(source.catalogue.value_counts().to_dict(), {"B": 1240, "A": 490})
        self.assertTrue(source.catalogue_key.is_unique)
        # Description duplication across code groups must survive source loading.
        self.assertGreater(len(source[source.catalogue_description.eq("REPLACED")]), 1)
        anomalies = source[source.source_anomaly.ne("")]
        self.assertEqual(anomalies.catalogue_key.tolist(), ["A|PMKNFAN|PMKN"])


if __name__ == "__main__":
    unittest.main()
