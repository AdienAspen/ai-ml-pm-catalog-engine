"""Consensus must include every node in the frozen score band."""

import unittest

import numpy as np

from g20i_profile_consensus import consensus_profile


class ProfileConsensusTests(unittest.TestCase):
    def test_all_nearby_nodes_share_profile(self):
        result = consensus_profile(np.array([0.8, 0.78, 0.77, 0.6]),
                                   ["P1", "P1", "P1", "P2"], 0.05)
        self.assertEqual(result, ("P1", 3, 1))

    def test_third_node_can_defeat_top_two_agreement(self):
        result = consensus_profile(np.array([0.8, 0.79, 0.77]),
                                   ["P1", "P1", "P2"], 0.05)
        self.assertEqual(result, ("", 3, 2))

    def test_node_at_margin_boundary_is_not_in_band(self):
        result = consensus_profile(np.array([0.8, 0.75]), ["P1", "P2"], 0.05)
        self.assertEqual(result, ("P1", 1, 1))


if __name__ == "__main__":
    unittest.main()
