import json
import unittest

import pandas as pd

import g20d3_symptom_threshold_review as review


class SymptomSweep(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.freeze = json.loads((review.OUT / "g20d3_freeze_manifest.json").read_text())
        cls.run_manifest = json.loads((review.OUT / "g20d3_run_manifest.json").read_text())
        cls.curve = pd.read_csv(review.OUT / "g20d3_symptom_b1_threshold_curve_sanitized.csv")
        cls.scores = pd.read_csv(review.OUT / "g20d3_symptom_b1_best_scores_sanitized.csv")
        cls.alignment = pd.read_csv(review.OUT / "g20d3_overlap_concept_alignment_sanitized.csv")

    def test_frozen_scope_and_no_selection(self):
        self.assertEqual(self.freeze["thresholds"], list(review.THRESHOLDS))
        self.assertFalse(self.freeze["coverage_observed"])
        self.assertFalse(self.freeze["threshold_selected"])
        self.assertFalse(self.run_manifest["threshold_selected"])
        self.assertEqual(self.freeze["prototype_scope"],
                         "same_eight_frozen_WMEP_effects_as_G2.0d2")
        self.assertEqual(len(self.scores), 9263)
        self.assertTrue(self.scores.unit_key_hash.is_unique)

    def test_curve_recomputed_from_unit_scores(self):
        self.assertEqual(len(self.curve), 7)
        for row in self.curve.itertuples():
            lexical = self.scores.conservative_lexical_floor
            semantic = self.scores.best_score.ge(row.threshold).fillna(False)
            matched = self.scores[semantic]
            frequencies = matched.best_concept_key.value_counts()
            self.assertEqual(row.assigned, int(semantic.sum()))
            self.assertEqual(row.abstained, int((~semantic).sum()))
            self.assertEqual(row.lexical_only, int((lexical & ~semantic).sum()))
            self.assertEqual(row.semantic_only, int((~lexical & semantic).sum()))
            self.assertEqual(row.intersection, int((lexical & semantic).sum()))
            self.assertEqual(row.union, int((lexical | semantic).sum()))
            self.assertEqual(row.no_anchor, int((~lexical & ~semantic).sum()))
            self.assertEqual(row.matched_semantic_concepts, len(frequencies))
            self.assertEqual(row.top_concept_units,
                             int(frequencies.iloc[0]) if len(frequencies) else 0)

    def test_overlap_concept_audit(self):
        self.assertEqual(len(self.alignment), 7)
        for row in self.alignment.itertuples():
            curve = self.curve[self.curve.threshold.eq(row.threshold)].iloc[0]
            self.assertEqual(row.intersection_units, curve.intersection)
            self.assertEqual(row.same_concept_units + row.different_best_concept_units,
                             row.intersection_units)
        low = self.alignment[self.alignment.threshold.eq(0.30)].iloc[0]
        self.assertEqual((low.intersection_units, low.same_concept_units,
                          low.leading_mismatch_units), (185, 16, 151))
        baseline = self.curve[self.curve.threshold.eq(0.50)].iloc[0]
        self.assertEqual((baseline.assigned, baseline.intersection, baseline.union),
                         (104, 4, 287))


if __name__ == "__main__":
    unittest.main()
