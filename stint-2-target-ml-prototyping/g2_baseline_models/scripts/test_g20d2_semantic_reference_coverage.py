import json
import unittest

import pandas as pd

import g20d2_semantic_reference_coverage as run


class FrozenInstrument(unittest.TestCase):
    def test_external_only_and_predeclared_cutoff(self):
        frozen = json.loads((run.OUT / "g20d2_freeze_manifest.json").read_text())
        self.assertFalse(frozen["coverage_observed"])
        self.assertEqual(frozen["settings"]["threshold"], 0.50)
        registry = pd.read_csv(run.OUT / "g20d2_prototype_registry_sanitized.csv")
        source = pd.read_csv(run.EXTERNAL)
        self.assertEqual(len(registry), len(source))
        self.assertEqual(len(registry), 144)
        self.assertEqual(set(registry.prototype_id), set(source.concept_id))
        self.assertEqual(set(registry.source), {"frozen_external_failure_vocabulary_v1"})
        self.assertEqual(registry.groupby("target").size().to_dict(),
                         {"Cause": 16, "Damage": 120, "Symptom": 8})


class ComparisonLedger(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not (run.OUT / "g20d2_run_manifest.json").exists():
            raise unittest.SkipTest("G2.0d2 measurement has not run")
        cls.units = pd.read_csv(run.OUT / "g20d2_unit_scores_sanitized.csv")
        cls.comparison = pd.read_csv(run.OUT / "g20d2_detector_comparison_sanitized.csv")

    def test_unit_grain_and_score_cutoff(self):
        self.assertEqual(len(self.units), 12968 * 3)
        self.assertFalse(self.units.duplicated(["unit_key_hash", "target"]).any())
        self.assertEqual(self.units[self.units.construction_eligible].unit_key_hash.nunique(), 10900)
        self.assertTrue((self.units.loc[self.units.semantic_external_only, "best_score"]
                         >= run.THRESHOLD - 0.000001).all())
        self.assertTrue((self.units.loc[~self.units.semantic_external_only, "best_score"]
                         .dropna() < run.THRESHOLD + 0.000001).all())

    def test_partition_recomputed_per_target_path_universe(self):
        self.assertEqual(len(self.comparison), 18)
        expected_available = {"Cause": 16, "Damage": 113, "Symptom": 8}
        for row in self.comparison.itertuples():
            group = self.units[self.units.target.eq(row.target)
                               & self.units.path_bucket.eq(row.path_bucket)]
            if row.universe == run.lexical.ELIGIBLE:
                group = group[group.construction_eligible]
            l = group.lexical_external_only
            s = group.semantic_external_only
            self.assertEqual(len(group), row.path_units)
            self.assertEqual(int(group.lexical_g20d.sum()), row.conservative_lexical_floor)
            self.assertEqual(int(l.sum()), row.conservative_lexical_floor_same_prototypes)
            self.assertEqual(int(s.sum()), row.broader_semantic_estimate)
            self.assertEqual(int((l & ~s).sum()), row.lexical_only)
            self.assertEqual(int((~l & s).sum()), row.semantic_only)
            self.assertEqual(int((l & s).sum()), row.intersection)
            self.assertEqual(int((l | s).sum()), row.union)
            self.assertEqual(int((~l & ~s).sum()), row.no_anchor)
            matches = group[group.semantic_external_only]
            top = matches.assigned_concept_key.value_counts()
            self.assertEqual((int(top.iloc[0]) if len(top) else 0), row.top_concept_units)
            self.assertEqual(len(top), row.matched_semantic_concepts)
            self.assertEqual(row.available_external_concepts, expected_available[row.target])
            self.assertLessEqual(row.matched_semantic_concepts, row.available_external_concepts)
            self.assertEqual(bool(row.concentration_above_30pct),
                             bool(len(top) and top.iloc[0] / len(matches) > 0.30))

    def test_reporting_addendum_keeps_instrument_and_scores(self):
        addendum = json.loads((run.OUT / "g20d2_reporting_addendum_manifest.json").read_text())
        import hashlib
        def digest(filename):
            return hashlib.sha256((run.OUT / filename).read_bytes()).hexdigest()
        self.assertTrue(addendum["no_model_rerun"])
        self.assertEqual(addendum["frozen_instrument_sha256"],
                         digest("g20d2_freeze_manifest.json"))
        self.assertEqual(addendum["unit_scores_sha256"],
                         digest("g20d2_unit_scores_sanitized.csv"))
        for filename, expected in addendum["prior_artifact_sha256"].items():
            if filename == "g20d2_detector_comparison_sanitized.csv":
                backup = "g20d2_detector_comparison_pre_addendum_sanitized.csv"
            elif filename == "g20d2_memo.md":
                backup = "g20d2_memo_pre_addendum.md"
            elif filename == "g20d2_run_manifest.json":
                backup = "g20d2_run_manifest_pre_addendum.json"
            self.assertEqual(digest(backup), expected)


if __name__ == "__main__":
    unittest.main()
