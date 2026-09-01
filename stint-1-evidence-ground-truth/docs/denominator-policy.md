# Denominator Policy

## Rules

- Never use a global denominator for the PoC.
- Denominators are target-specific.
- The default STINT_1 denominator unit is a `record-field` evidence unit, not a physical record.
- Because `stint1_record_id` includes `source_text_field`, one physical source record can contribute multiple denominator units when different fields provide distinct target evidence.
- Physical-record denominators, if needed, must be reported separately by deduplicating on source lineage without `source_text_field`.
- Evidence supported by `pdf_assets_of_concern.event` carries `event_structural` stratum. If combined with structured source-data evidence, counts must be split by stratum or explicitly marked as mixed-source support before F6.
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
