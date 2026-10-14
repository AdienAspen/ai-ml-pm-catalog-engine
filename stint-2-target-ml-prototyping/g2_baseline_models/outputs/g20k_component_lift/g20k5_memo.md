# G2.0k.5 - component vs turbine catalogue profiles



P1 confirmed: 2,400 original resolved-node RBNRs plus 1,534 profile-consensus RBNRs in g20i_profile_consensus_by_order_sanitized.csv, and one G2.0k.2 expanded_profile_rbnr in g20k_expansion_affected_orders_sanitized.csv. No replay needed.

P2 confirmed with missingness: G1.2 turbine FLOC and IH06 nearest-valid-ancestor profile; 3,267 PMMUWW, 668 no_profile_no_filter.

P3 confirmed: all S/B/C/5/A catalogue types and profile associations in Wind Catalog Group and Codes Final v4.xlsx (g20i_component_resolution.py:99-117).

P4 confirmed: distinct catalogue type+group+code pair. Code alone is not a unique class.

P5 confirmed: 3,013 strong G1.1 orders; crosswalk supplies Catalog B group+code pairs, matching P4. It is algorithmic consistency, not independent correctness.



Identity: {'different_rbnr': 3217, 'turbine_profile_missing': 668, 'same_rbnr': 50}. Distinct component RBNRs: 30. Top-five share: 0.5502.

The 668 missing-turbine-profile orders gained a component profile from an otherwise unfiltered catalogue space. Per-target median and max enabled pair counts are separate from the 3,267 comparison; no silent zero.

Different-RBNR comparable orders: 3217. Six-class counts by target and added/removed pair distributions are in sanitized outputs.

Strong crosswalk overlap with resolved orders: 1189 orders, 1313 order-code pairs. Membership is not precision.

G2.0k.4 carry-over: 0 of 794 tied-sibling orders have an identical IH06 description. LCA-vs-turbine RBNR/count categories are in g20k5_lca_carryover_sanitized.csv.

The earlier 1,548-order no-profile status table is not edited in this diagnostic. Its later update must account for these 668 resolved-component cases.

No new resolution, no scoring, no candidate promotion, no F6 update.
