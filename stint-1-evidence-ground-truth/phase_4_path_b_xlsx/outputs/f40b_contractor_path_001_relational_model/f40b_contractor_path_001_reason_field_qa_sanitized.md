# F4.0b Reason Field QA

`reason` is confirmed as a non-empty free-text field in the service-order entity, but it is not confirmed as a root-cause label.

- Records profiled: `10749`
- Non-empty `reason` rows: `10749`
- Redacted examples reviewed: `3`
- Verdict: `cause_semantics_unconfirmed`
- Downstream handling: keep as candidate textual support for Cause; do not treat as deterministic Cause mapping.

The redacted sample emits token shapes and cue flags only, not raw values.

raw_operational_values_emitted: false
