import unittest

import pandas as pd

import g20d_catalogue_free_coverage as g


class MatchingContract(unittest.TestCase):
    def test_no_cross_segment_match(self):
        index = g.phrase_index()
        g.add_phrase(index, "bearing failure", ("Damage", "example"))
        self.assertEqual(g.match_segments([["bearing"], ["failure"]], index), set())

    def test_repetitions_count_once_and_targets_stay_separate(self):
        index = g.phrase_index()
        for target in ("Cause", "Damage"):
            g.add_phrase(index, "assembly damage", (target, "same-key"))
        self.assertEqual(
            g.match_segments([["assembly", "damage"]] * 3, index),
            {("Cause", "same-key"), ("Damage", "same-key")},
        )

    def test_source_buckets_are_exclusive(self):
        self.assertEqual(g.bucket(set(), set()), "no_anchor")
        self.assertEqual(g.bucket({1}, set()), "domain_vocabulary_only")
        self.assertEqual(g.bucket(set(), {1}), "sap_catalog_only")
        self.assertEqual(g.bucket({1}, {2}), "both")


class MeasuredArtifacts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not (g.OUT / "g20d_run_manifest.json").exists():
            raise unittest.SkipTest("Measurement artifacts not produced yet")
        cls.units = g.read(g.OUT / "g20d_unit_coverage_sanitized.csv")
        cls.hits = g.read(g.OUT / "g20d_unit_concept_hits_sanitized.csv")
        cls.summary = g.read(g.OUT / "g20d_domain_only_coverage_sanitized.csv")

    def test_universe_and_unique_grain(self):
        self.assertEqual(len(self.units), 12968 * 3)
        self.assertFalse(self.units.duplicated(["unit_key_hash", "target"]).any())
        self.assertFalse(self.hits.duplicated(
            ["unit_key_hash", "target", "anchor_source", "concept_id"]).any())
        self.assertEqual(self.units[self.units.construction_eligible].unit_key_hash.nunique(), 10900)
        self.assertEqual(self.units[self.units.leakage_mask_applied].unit_key_hash.nunique(), 13)

    def test_independent_counts_from_hit_ledger(self):
        self.assertEqual(len(self.summary), 18)
        for row in self.summary.itertuples():
            units = self.units[self.units.target.eq(row.target) & self.units.path_bucket.eq(row.path_bucket)]
            hits = self.hits[self.hits.target.eq(row.target) & self.hits.path_bucket.eq(row.path_bucket)]
            if row.universe == g.ELIGIBLE:
                units = units[units.construction_eligible]
                hits = hits[hits.construction_eligible]
            domain = set(hits[hits.anchor_source.eq("domain_vocabulary")].unit_key_hash)
            sap = set(hits[hits.anchor_source.eq("sap_catalog")].unit_key_hash)
            self.assertEqual(len(units), row.path_units)
            self.assertEqual(len(domain), row.units_with_domain_anchor)
            self.assertEqual(len(sap), row.units_with_sap_anchor)
            self.assertEqual(len(domain & sap), row.both)
            self.assertEqual(len(sap - domain), row.sap_catalog_only)
            self.assertEqual(len(set(units.unit_key_hash) - domain - sap), row.no_anchor)

    def test_f6_incomparable_deltas_are_null_not_zero(self):
        frame = pd.read_csv(g.OUT / "g20d_f6_contrast_sanitized.csv")
        blocked = frame.comparison_status.str.startswith("blocked_")
        self.assertEqual(int(blocked.sum()), 12)
        self.assertTrue(frame.loc[blocked, "same_universe_delta"].isna().all())
        good = frame[~blocked]
        self.assertTrue((good.f6_same_universe_units + good.f6_excluded_for_evaluation_or_heldout
                         == good.f6_declared_full_units).all())
        self.assertTrue((good.domain_supported_units - good.f6_same_universe_units
                         == good.same_universe_delta).all())


if __name__ == "__main__":
    unittest.main()
