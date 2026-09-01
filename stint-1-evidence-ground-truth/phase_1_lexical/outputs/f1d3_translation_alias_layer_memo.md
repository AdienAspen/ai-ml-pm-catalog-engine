# F1d3 - Translation Alias Layer

## Purpose

This pass adds Spanish aliases for selected public/reference English concepts so matching can run against both canonical English terms and project-team translation aliases.

Aliases are not `reference_evidence`; they are `expert_inference` in a separate column and layer.

## Result

- Alias rows: 53
- Missing alias sources: 0
- Evidence type: `expert_inference`
- Tier: `silver-medium`
- Evaluation independence: `derived_from_rules`

## Governance

- Aliases may improve semantic matching coverage, but they are not validated mappings.
- Aliases cannot support contractual denominators.
- Matching against aliases must preserve the original canonical concept ID.
