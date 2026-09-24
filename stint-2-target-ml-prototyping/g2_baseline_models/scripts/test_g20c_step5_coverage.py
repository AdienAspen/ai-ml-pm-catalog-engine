import unittest

import pandas as pd
from g20c_step5_coverage import add_phrase, bucket, match_segments, phrase_index, summarize


class CoverageTests(unittest.TestCase):
    def test_duplicate_mentions_count_once(self):
        index = phrase_index()
        add_phrase(index, "bearing", ("Object Part", "C1"))
        add_phrase(index, "main bearing", ("Object Part", "C1"))
        self.assertEqual(
            match_segments([["main", "bearing", "bearing"], ["bearing"]], index),
            {("Object Part", "C1")},
        )

    def test_no_cross_segment_match(self):
        index = phrase_index()
        add_phrase(index, "main bearing", "C1")
        self.assertEqual(match_segments([["main"], ["bearing"]], index), set())

    def test_boundaries_and_empty_text(self):
        index = phrase_index()
        add_phrase(index, "ring", "C1")
        self.assertEqual(match_segments([["bearing"], []], index), set())
        self.assertEqual(match_segments([["ring"]], index), {"C1"})

    def test_multi_target_and_multi_concept_not_collapsed(self):
        index = phrase_index()
        add_phrase(index, "replace ring", ("Activity", "C1"))
        add_phrase(index, "replace ring", ("Object Part", "C2"))
        self.assertEqual(len(match_segments([["replace", "ring"]], index)), 2)

    def test_partition(self):
        self.assertEqual(
            [bucket(d, s) for d, s in [(False, False), (True, False), (False, True), (True, True)]],
            ["no_anchor", "domain_vocabulary_only", "sap_catalog_only", "both"],
        )

    def test_paths_and_targets_stay_separate_and_exact_gate(self):
        records = []
        for path, target, n in [
            ("B1", "Activity", 10),
            ("B2", "Activity", 2),
            ("B1", "Object Part", 1),
        ]:
            for i in range(n):
                records.append(
                    dict(
                        path_bucket=path,
                        target=target,
                        domain_vocabulary={f"C{i // 3}"},
                        sap_catalog=set(),
                        anchor_bucket="domain_vocabulary_only",
                        reviewed_concept_exposure=False,
                    )
                )
        summary, _ = summarize(pd.DataFrame(records), "test")
        by_key = {(r["path_bucket"], r["target"]): r for r in summary}
        b1 = by_key[("B1", "Activity")]
        self.assertEqual(b1["domain_vocabulary_top_concept_share"], 0.3)
        self.assertFalse(b1["domain_vocabulary_concentration_above_30pct"])
        self.assertTrue(by_key[("B2", "Activity")]["domain_vocabulary_concentration_above_30pct"])
        self.assertEqual(len(summary), 3)

    def test_zero_anchors_share_undefined(self):
        summary, concepts = summarize(
            pd.DataFrame(
                [
                    dict(
                        path_bucket="A",
                        target="Activity",
                        domain_vocabulary=set(),
                        sap_catalog=set(),
                        anchor_bucket="no_anchor",
                        reviewed_concept_exposure=False,
                    )
                ]
            ),
            "test",
        )
        self.assertIsNone(summary[0]["domain_vocabulary_top_concept_share"])
        self.assertEqual(summary[0]["no_anchor"], 1)
        self.assertEqual(concepts, [])


if __name__ == "__main__":
    unittest.main()
