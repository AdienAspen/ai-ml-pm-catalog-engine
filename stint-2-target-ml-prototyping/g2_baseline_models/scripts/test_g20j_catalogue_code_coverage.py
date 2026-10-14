"""Tests for declared partitions, ties and unit-level residual counting."""

import unittest

import numpy as np

import g20j_catalogue_code_coverage as run


class FakeScoring:
    @staticmethod
    def cosine_matrix(left, right):
        return np.asarray(left) @ np.asarray(right).T


class FakeModel:
    def encode(self, texts, **kwargs):
        return np.tile([1.0, 0.0], (len(texts), 1))


class RunTests(unittest.TestCase):
    def test_four_partitions_are_disjoint(self):
        values = [run.partition(c, d) for c in (False, True) for d in (False, True)]
        self.assertEqual(set(values), {'no_anchor_at_all', 'no_catalogue_code',
                                      'catalogue_only', 'catalogue_and_domain'})

    def test_duplicate_descriptions_are_ties_not_two_units(self):
        scores, tied = run.segment_winners(np.array([[1.,0.],[0.,1.]]),
                                          np.array([[1.,0.],[1.,0.],[0.,1.]]), FakeScoring)
        self.assertEqual(run.unit_winner([0], scores, tied), (1.0, 0, 2))
        self.assertEqual(run.unit_winner([0,1], scores, tied), (1.0, 0, 3))
        self.assertEqual(run.unit_winner([], scores, tied), (None, -1, 0))

    def test_best_score_does_not_combine_source_fields(self):
        scores, tied = run.segment_winners(np.array([[0.3,0.],[0.4,0.]]),
                                          np.array([[1.,0.]]), FakeScoring)
        score, _, _ = run.unit_winner([0,1], scores, tied)
        self.assertAlmostEqual(score, 0.4)
        self.assertLess(score, run.SETTINGS['catalogue_threshold'])

    def test_no_empty_residual_silently_disappears(self):
        rows, audit = run.residual_concepts([], {'texts':[]}, 'Cause',
                                            'PATH_A', 'profile_scoped', FakeModel())
        self.assertEqual(rows, [])
        self.assertEqual(audit['residual_units'], 0)
        self.assertEqual(audit['concept_count'], 0)

    def test_frequency_is_distinct_units_not_ngram_mentions(self):
        units = [{'unit_key_hash':'one', 'residual_segments':['worn bearing worn bearing']},
                 {'unit_key_hash':'two', 'residual_segments':['worn bearing']}]
        rows, audit = run.residual_concepts(units, {}, 'Symptom', 'PATH_A',
                                            'profile_scoped', FakeModel())
        self.assertTrue(rows)
        self.assertTrue(all(row['unit_count'] <= 2 for row in rows))
        self.assertTrue(all(row['share_of_residual'] <= 1 for row in rows))
        self.assertEqual(audit['residual_units'], 2)


if __name__ == '__main__':
    unittest.main()
