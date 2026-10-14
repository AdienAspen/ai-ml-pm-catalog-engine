# G1.1f — Profile-constrained crosswalk diagnostic

B1 only. No code assignment, candidate promotion or F6 change.

## Pre-flight

- F1 confirmed: G1.1 compares consumed `items[].itemDescription` to Catalog B `Short Text for Code` by token-overlap score with head/subset bonuses; no embeddings or group-description matching.
- F2 confirmed: absolute score only; strong >= 0.85, medium >= 0.55, weak > 0. No second-best margin.
- F3 confirmed: 5,778 distinct order x (Catalog B group, code) pairs from 3,013 orders; concepts are retained beneath each pair.
- F3 multi-concept pairs: 1673.
- F4 confirmed: complete enabled Catalog B pair sets rebuilt through profile -> type B -> group -> code; G2.0k.6 membership 0 / 11 / 5,767 and G2.0k.7 enabling sets reproduced.
- F5 confirmed: reachable IH06 subtree via Superior functional location; inherited nearest-valid RBNR; turbine profile included, with site/turbine boundary assertions.
- F6 confirmed: unrestricted G1.1 code, score and tier replay identical for all 708 concepts and 5,778 pairs.

## Controls

- Original code available: 1,459 pairs and 1,207 orders, as in G2.0k.7.
- Mixed-category orders: 684 of 3,013.
- Mixed-category orders in the prior implied-none subset: 79 of 1,804.
- The prior `implied_none` subset has exactly 1,804 orders and is reported separately.
- Category 6a is structural absence of enabled Catalog B codes under the subtree. Category 6b is a zero lexical score despite enabled codes; it does not establish a client-configuration gap.
- Exact normalized descriptions support a lexical equivalence only; restricted strong matches remain unvalidated candidate matches, not precision estimates.
- Pair categories follow the highest-precedence outcome among source material concepts; order categories follow the highest-precedence pair.
- The 30-pair sample is diagnostic, private, and stratified across categories 3, 4, 5, 6a, and 6b where present.

## Counts

| Category | Pairs | Orders | Prior implied-none orders |
|---|---:|---:|---:|
| no_turbine_subtree | 13 | 2 | 0 |
| original_code_available | 1459 | 1207 | 0 |
| exact_equivalent | 3101 | 1401 | 1401 |
| restricted_strong | 501 | 230 | 230 |
| restricted_medium_weak | 128 | 30 | 30 |
| no_enabled_codes_under_subtree | 0 | 0 | 0 |
| enabled_codes_no_score | 576 | 143 | 143 |
