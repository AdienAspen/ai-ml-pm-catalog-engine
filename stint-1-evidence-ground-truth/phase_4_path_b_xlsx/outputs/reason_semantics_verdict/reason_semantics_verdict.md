# B1.3 Reason Semantics Verdict

## Scope

`reason` is evaluated as a field-level semantic source in `CONTRACTOR_PATH_001`. This pass does not produce labels, candidates, mappings, or denominator rows.

## Findings

- Records evaluated: `10749`
- Non-empty `reason` rows: `10338`
- Distinct `reason` value keys: `3346`
- Most common single reason share: `2.60%`
- Median word count: `5`
- Cause-cue rows: `838`
- Motive/work-cue rows: `1270`
- Symptom-like-cue rows: `921`
- Generic/placeholder-cue rows: `748`

## Verdict

**`reason` is not confirmed as a deterministic Cause field.** It has near-complete coverage and is semantically useful, but the field can encode reason-for-work, dispatch/work motive, symptom-like trigger, or other contextual rationale. It should be routed as textual support for `Cause` and possible pre-execution signal review, not as a direct target label.

## Downstream Rule

- Do not use `reason` as `validated_mapping` or deterministic Cause.
- Use `reason` in B1.2 as source text with `evidence_type: expert_inference` unless manually/independently validated later.
- Keep `source_text_field = reason` separate from `descriptionExtended` per DELTA-0003.
- If used for Symptom exploration, declare it as `possible_pre_execution_context`, not confirmed Symptom.

raw_operational_values_emitted: false
