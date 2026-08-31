# Denominator Policy

## Rules

- Never use a global denominator for the PoC.
- Denominators are target-specific.
- `expert_inference` does not enter a measurement denominator by itself.
- `reference_evidence` does not enter a measurement denominator by itself.
- `validated_mapping`, `real_observed_label`, or defensible proxy/silver evidence may enter only when provenance and target destination are explicit.
- Strata are not mixed.
- A zero denominator is a valid feasibility result.
- Denominators must be reported as:

```text
target x evidence_type x tier x contractor_path x site_key x stratum
```

## Accuracy Boundary

Do not estimate model accuracy, coverage, or contractual performance until a defensible measurement denominator exists for the target being assessed.

