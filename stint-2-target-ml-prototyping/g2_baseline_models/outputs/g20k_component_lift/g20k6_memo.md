# G2.0k.6 - semantic disjunction and crosswalk membership

Diagnostic only; B1 only. Exact normalized description match is a conservative semantic proxy, not proof of equivalent meaning.

## Pre-flight
- **Q1: confirmed** — Wind Catalog Group and Codes Final v4.xlsx: Catalog Profile and Code Groups, columns A/C/D; g20k5_component_profile_comparison.py:catalogue/code_set. {"expansion": "exact group membership; no wildcard expansion", "profile_group_associations": 1392, "wildcard_rows": 0}
- **Q2: confirmed** — Wind Catalog Group and Codes Final v4.xlsx: Catalog. S/B/C/5/A - Group and Code, column D Short Text for Code. {"language": "English text in one untagged description column; no locale field", "per_type": {"5": {"blank_descriptions": 0, "conflicting_pair_descriptions": 0}, "A": {"blank_descriptions": 0, "conflicting_pair_descriptions": 0}, "B": {"blank_descriptions": 0, "conflicting_pair_descriptions": 0}, "C": {"blank_descriptions": 0, "conflicting_pair_descriptions": 0}, "S": {"blank_descriptions": 0, "conflicting_pair_descriptions": 0}}}
- **Q3: confirmed** — g20k5_codeset_detail.csv + g20k5_codeset_comparison_sanitized.csv; g20k5_run_manifest.json. {"category_replay_identical": true, "different_rbnr_orders": 3217, "distinct_component_rbnrs": 17}
- **Q4: confirmed** — g11_item_signal_rows_sanitized.csv joined to g11_material_to_catalog_b_crosswalk_sanitized.csv; g20k5_component_profile_comparison.py:strong_crosswalk. {"catalogue_type": "B", "full_pairs": 5778, "overlap_orders": 1189, "overlap_pairs": 1313, "strong_orders": 3013}
- **Q5: confirmed** — same workbook, columns B/C grouped within catalogue type. {"distinct_code_values_in_multiple_groups": {"5": 247, "A": 16, "B": 227, "C": 177, "S": 167}}

## Accounting
- Distinct RBNR view: 17 component RBNRs per target; order-weighted view: 3,217 different-RBNR orders per target.
- Crosswalk pair view: 1,313 overlap pairs and 5,778 full-set pairs.
- Crosswalk order view: 1,189 overlap orders and 3,013 full-set orders. An order takes its highest-precedence pair category.
- Multi-pair orders: 97 overlap; 821 full set. Mixed-membership counts are in the membership CSV, not a sixth category.
- Shared code values are controls only; their descriptions may differ. See code_description_control rows.
- Description-unit order-weighted categories: Symptom overlapping=3217; Object Part disjoint=3217; Damage same_set=58, overlapping=3159; Cause wider=696, overlapping=2521; Activity overlapping=2560, disjoint=657.
- Strong crosswalk full-set pair categories: in_component_profile=11, in_pmmuww=0, in_other_profile=5767, in_no_profile=0, not_in_catalog=0. Top-five other-profile IDs and counts are anonymized in the membership CSV.
- G1 crosswalk pairs are deterministic inference, not independent SAP assignments; membership is not correctness.
- No order text, scoring, model replay, mapping promotion, or F6 denominator change.
