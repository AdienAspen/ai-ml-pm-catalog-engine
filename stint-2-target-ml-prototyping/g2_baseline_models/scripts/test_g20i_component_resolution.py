"""Focused invariant tests for the G2.0i diagnostic resolver."""

import unittest

import numpy as np

import g20i_component_resolution as g20i


class ComponentResolutionTests(unittest.TestCase):
    def test_descendants_follow_edges(self):
        children = {"site-turbine": {"site-turbine-a"}, "site-turbine-a": {"site-turbine-a-leaf"}}
        self.assertEqual(
            g20i.descendants_of("site-turbine", children),
            ["site-turbine-a", "site-turbine-a-leaf"],
        )

    def test_descendant_cycle_rejected(self):
        with self.assertRaises(ValueError):
            g20i.descendants_of("t", {"t": {"a"}, "a": {"t"}})

    def test_nearest_valid_profile(self):
        nodes = {
            "leaf": {"parent": "assembly", "profile": "INVALID"},
            "assembly": {"parent": "turbine", "profile": "P_ASSEMBLY"},
            "turbine": {"parent": "", "profile": "P_TURBINE"},
        }
        self.assertEqual(
            g20i.effective_profile("leaf", nodes, {"P_ASSEMBLY", "P_TURBINE"}),
            ("P_ASSEMBLY", "ancestor", 1),
        )
        self.assertEqual(
            g20i.effective_profile("leaf", nodes, set())[1], "no_profile_no_filter"
        )

    def test_rank_uses_all_detected_concepts_and_second_node(self):
        matrix = np.array([[0.70, 0.30, 0.20], [0.20, 0.64, 0.10]], dtype=np.float32)
        best, top, runner, second = g20i.rank_nodes(matrix, [0, 1])
        self.assertEqual((best, runner), (0, 1))
        self.assertAlmostEqual(top, 0.70, places=5)
        self.assertAlmostEqual(second, 0.64, places=5)


if __name__ == "__main__":
    unittest.main()
