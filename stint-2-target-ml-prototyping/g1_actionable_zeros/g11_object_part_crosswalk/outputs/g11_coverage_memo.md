# G1.1 Material to Catalog B Crosswalk Memo

G1.1 profiles the consumption item signal that blocked Object Part in B1.

## Source Inventory

- Consumption records: 10,749
- Orders with item signal: 4,079
- Orders without item signal: 6,670
- Item signal rows: 15,358
- Distinct source item concepts: 708
- Catalog B rows in Wind Catalog: 1,240

## Crosswalk Status

This run emits candidate mappings from material concepts to Catalog B. The material item signal is a real observed label. The crosswalk row is an inferred candidate and remains `derived_from_rules` until explicitly reviewed.

Status counts:

- auto_candidate_medium: 5
- auto_candidate_strong: 498
- auto_candidate_weak: 58
- no_catalog_b_candidate: 147

Strong or medium candidates cover 3,027 unique item-bearing orders. Coverage is reported against the 4,079 orders with consumption items, not against the MAT denominator.

## 62% Without Consumption

The absence profile is emitted in `g11_consumption_absence_by_activity_type_sanitized.csv`. It bounds where Object Part is reachable from consumption and should be interpreted by activity type, not as random missingness.

## Governance

- Do not aggregate this with Path A or B2.
- Do not treat Catalog B candidate output as independent evaluation.
- Do not use `evaluation_set_v1` units for training.
- Use the internal review file only in the closed environment; it contains visible material descriptions and has mode 600.
