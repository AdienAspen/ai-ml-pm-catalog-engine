# G2.0k.7 - crosswalk-implied component

Diagnostic only, B1 only. No G2.0i replay, scoring, promotion or F6 change.

## Pre-flight
- **R1: confirmed** - g11_material_to_catalog_b_crosswalk.py:248-261 itemDescription; G2.0i-resolution-chain-code-spec.md:Inputs/2 reason + descriptionExtended. {"reading": "different text fields, not text-free independence"}
- **R2: confirmed** - g20k6_detail.csv full population + Wind Catalog Group and Codes Final v4.xlsx profile/type/group and B group/code. {"completed_pair_rows": 11, "pair_counts": {"in_component_profile": 11, "in_other_profile": 5767}}
- **R3: confirmed** - g20i_component_resolution.py:load_nodes, descendants_of, effective_profile; g20k4_tie_structure_diagnostic.py:ancestor_path. {"rule": "site-aware reachable descendants with nearest-valid-ancestor RBNR"}
- **R4: confirmed** - g20i_profile_consensus_by_order_sanitized.csv:resolved_node_hash/resolved_rbnr; g20k_expansion_affected_orders_sanitized.csv:expanded_profile_status. {"profile_only_all": 1535, "profile_only_overlap": 419, "unique_node_all": 2400, "unique_node_overlap": 770}
- **R5: confirmed** - g11_item_signal_rows_sanitized.csv joined to B1 service-orders; G1.2 B1 order keys. {"overlap_orders": 1189, "strong_orders": 3013}
- **R6: confirmed** - g20i_component_resolution.py:load_nodes uses IH06; g20i_postrun_audit.md:assetId to IH08 zero of 10749. {"candidate_source": "IH06 functional locations only"}

## Results
- Pair availability: no_turbine_subtree=13, implied_single_node=177, implied_multi_node_one_rbnr=1282, implied_multi_rbnr=0, implied_none=4306.
- Order availability: no_turbine_subtree=2, implied_single_node=99, implied_multi_node_one_rbnr=987, implied_multi_rbnr=121, implied_none=1804.
- Orders whose separate crosswalk pairs imply disjoint nonempty node sets: 121.
- Node-level agreement (770): same_node=11, same_rbnr_other_node=0, same_subsystem=82, different_subsystem=0, no_implied_node=677.
- Profile-level agreement (419): same_rbnr=0, different_rbnr=155, no_implied_node=264. No node agreement is computed for these orders.
- Strong-crosswalk orders without G2.0i profile: 1824; profile-determinable potential: 842. No profile is assigned.
- Crosswalk and G2.0i are both text-derived from different fields (itemDescription versus reason/descriptionExtended). Agreement is not precision or ground truth.
- IH06 descendant nodes use effective nearest-valid-ancestor RBNR; no IH08 equipment nodes are candidates.
- Client node identifiers, non-PMMUWW RBNRs and per-order pairs remain only in internal/ at mode 600.
