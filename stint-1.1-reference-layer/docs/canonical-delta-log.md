# Canonical Delta Log

This log records any divergence between the frozen interface assumptions and evidence found during reference-layer construction.

No interface assumption is overwritten silently.

| delta_id | date | object | field_or_concept | observed_issue | evidence_source | evidence_type | proposed_action | status | decision_owner |
|---|---|---|---|---|---|---|---|---|---|
| DELTA-0001 | TBD | canonical_constraints | TBD | Bootstrap placeholder. | T1 bootstrap | expert_inference | Populate during reconciliation. | pending | project team |
| DELTA-0002 | 2026-08-28 | canonical_constraints | record_identifier | Malyi external schema requires `WO_ID`; current canonical constraints do not yet name the record identifier field. | Malyi schema delta | external_corroboration | Add or confirm canonical record identifier constraint before measurement denominators are claimed. | open | project team |
| DELTA-0003 | 2026-08-28 | canonical_constraints | primary_text_signal | Malyi external schema centers `Descriptions`; current canonical constraints do not yet bind the primary runtime text field per target. | Malyi schema delta | external_corroboration | Add primary text-signal constraint per target or mark unresolved. | open | project team |
| DELTA-0004 | 2026-08-28 | reference_layer | component_taxonomy | Malyi uses RDS-PP-style `System_Code`/`System_Name`; project targets use SAP Catalog B plus FLOC/KKS support. | Malyi schema delta | external_corroboration | Keep as architecture corroboration only; do not promote to validated mapping. | open | project team |
| DELTA-0005 | 2026-08-28 | target | activity_type | Malyi includes `Maintenance_Type`, but project Activity Type / MAT remains pending controlled-source confirmation. | Malyi schema delta | external_corroboration | Keep Activity Type blocked/pending until controlled source or documented proxy is confirmed. | open | project team |
| DELTA-0006 | 2026-08-28 | output_contract | target_code_validity | Malyi generated labels do not directly equal project SAP target-code mappings. | Malyi schema delta | external_corroboration | Require SAP_MAPPING candidate plus valid canonical destination before promotion. | open | project team |
