"""Focused tests for format-only provenance and agreement counting."""

import unittest

from g20ef_close_annotation_round import compare_damage, damage_categories, pair_label, wilson
from g20ef_register_and_analyze_responses import nominal_metrics


class ClosureTests(unittest.TestCase):
    def test_only_authorized_format_repairs(self):
        original = [
            {'annotation_id': '01', 'group': 'none_applicable', 'code': 'none_applicable'},
            {'annotation_id': '02', 'group': 'none_applicable', 'code': None},
            {'annotation_id': '03', 'group': 'MEC', 'code': 'MFLC'},
        ]
        new = [dict(r) for r in original]
        new[0]['code'] = new[1]['code'] = ''
        self.assertEqual(len(compare_damage(original, new)), 2)
        self.assertEqual(original[0]['code'], 'none_applicable')
        self.assertIsNone(original[1]['code'])

    def test_reject_changed_code_or_group_or_id_order(self):
        original = [{'annotation_id': '01', 'group': 'MEC', 'code': 'MFLC'}]
        for change in ({'code': 'MFLK'}, {'group': 'EXT'}, {'annotation_id': '02'}):
            with self.assertRaises(ValueError):
                compare_damage(original, [{**original[0], **change}])

    def test_exit_is_not_a_blank_catalogue_code(self):
        self.assertEqual(pair_label({'group': 'none_applicable', 'code': ''}), 'none_applicable')
        self.assertEqual(pair_label({'group': 'MEC', 'code': 'abstain'}), 'MEC|abstain')
        self.assertNotEqual(pair_label({'group': 'MEC', 'code': 'X'}),
                            pair_label({'group': 'EXT', 'code': 'X'}))

    def test_balanced_agreement_and_class_denominators(self):
        metric, classes, matrix = nominal_metrics(['a', 'a', 'b', 'b'],
                                                  ['a', 'b', 'a', 'b'], ['a', 'b', 'c'])
        self.assertAlmostEqual(metric['raw_agreement'], 0.5)
        self.assertAlmostEqual(metric['cohen_kappa'], 0)
        self.assertAlmostEqual(classes[0]['specific_agreement'], 0.5)
        self.assertEqual(classes[2]['specific_agreement'], '')
        self.assertEqual(sum(row['count'] for row in matrix), 4)

    def test_degenerate_agreement_is_not_estimable_kappa(self):
        metric, _, _ = nominal_metrics(['a'] * 4, ['a'] * 4, ['a', 'b'])
        self.assertIsNone(metric['cohen_kappa'])
        self.assertEqual(metric['raw_agreement'], 1)
        self.assertEqual(metric['gwet_ac1'], 1)

    def test_zero_and_small_conditional_sample(self):
        self.assertEqual(wilson(0, 0), (None, None))
        low, high = wilson(7, 7)
        self.assertLess(low, 0.8)
        self.assertAlmostEqual(high, 1)

    def test_categories_preserve_code_pairs_and_abstention_exits(self):
        catalogue = [{'group': f'G{i % 9}', 'code': f'C{i}'} for i in range(94)]
        groups, pairs, codes = damage_categories(catalogue)
        self.assertEqual((len(groups), len(pairs), len(codes)), (12, 106, 94))


if __name__ == '__main__':
    unittest.main()
