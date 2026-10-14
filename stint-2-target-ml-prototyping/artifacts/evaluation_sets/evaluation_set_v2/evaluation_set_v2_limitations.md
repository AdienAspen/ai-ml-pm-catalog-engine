# Evaluation set v2 - limitations and scope

This is a separate diagnostic registration for Damage (`g01-v2`) and Activity (`g01-v2.1`, A3 rewritten). It does not replace or merge with `evaluation_set_v1`. Each target has 300 distinct source units, 75 shared between annotators, and 375 responses. Annotator responses remain separate; disagreements are not adjudicated.

The annotators are LLMs, not human SAP subject-matter experts. The lead identified annotator 01 as Claude Opus 5 (medium effort) and annotator 02 as GPT 5.6; this identity comes from lead attestation, not the CSV receipts. Effort for annotator 02 and annotation dates were not supplied. Interface temperature and exact response process cannot be verified from the CSVs. Mechanical independence from the pipeline does not make these human-independent labels.

`evaluation_independence=independent` records blind label generation, while `evaluation_role=diagnostic` and `eligible_for_final_heldout=false` explicitly forbid treating this set as a final held-out test. Activity came from a 1,234-unit eligible pool after prior corpus-vocabulary exposure; Damage used a 9,261-unit pool with its own construction exclusions. Neither sample is a clean untouched final test. The 128-token text limit and B1-only scope apply to interpretations.

Activity measures two distinct exits: `none_applicable` (no performed work established) and `no_applicable_code` (work described, no fitting code). Damage has a two-level group/code instrument. High agreement on group or assigned code is not population catalogue coverage or proof of SAP-code correctness. Kappa can be prevalence-sensitive; consult raw agreement, AC1, per-class tables and confusion matrices together.

All 600 v2 `sampling_unit_key` values are training exclusions. The union with v1 is 1,500 keys (900 v1 + 600 v2, zero key overlap), asserted by the registration script. This is a prohibition list for future fitting, not evidence that an already fitted model used the list.

Visible-text packages and original responses remain in `internal/`. Versioned files contain hashed identifiers, labels and metadata only. Supersession requires an explicit new registration and protocol version.
