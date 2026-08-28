# FLOC Coverage Crosscheck

## Scope

T6 checks whether the reference layer has enough documented support to carry `FLOC leaf segment` forward without mixing it into the SAP S/B/C/5/A catalog namespace.

This is a reference-layer design check only. It does not run candidate extraction, does not establish runtime availability, and does not create a measurement denominator.

## Findings

- `FLOC leaf segment` is outside the SAP S/B/C/5/A catalog universe and must remain a separate namespace.
- Local source material contains FLOC and KKS supporting references.
- No controlled FLOC segment glossary is currently promoted as versioned reference-layer content in this sub-stint.
- KKS/RDS-style structure can support, explain, or validate FLOC interpretation.
- KKS must not be treated as resolving, deriving, or constructing the FLOC hierarchy.

## Source Crosscheck

| source_id | source_family | reference_layer_role | status | evidence_type | tier | measurement_denominator_use |
|---|---|---|---|---|---|---|
| RL-SOURCE-0101 | FLOC guidance source | supporting_reference | present_not_promoted | reference_evidence | silver-medium | false |
| RL-SOURCE-0102 | KKS/RDS-style source | supporting_feature_validator | present_not_resolver | reference_evidence | silver-medium | false |
| RL-SOURCE-0103 | FLOC structure guideline | supporting_reference | present_not_promoted | reference_evidence | silver-medium | false |
| RL-SOURCE-0104 | FLOC segment controlled glossary | controlled_vocabulary_candidate | not_versioned_in_reference_layer | unknown | unresolved | false |

## Decision

FLOC support is present enough to remain in the reference-layer architecture, but not enough to claim target measurability. The next promoted version must either ingest the controlled FLOC glossary with provenance or explicitly keep FLOC as unresolved/provisional.

## Downstream Rule

Any FLOC candidate emitted later must carry:

- a `floc` namespace;
- a valid canonical destination constraint;
- provenance for the source of the segment meaning;
- an explicit statement that KKS was used only as supporting feature/validator, not as the resolver.

## Non-Goals

- No raw operational values were inspected or emitted.
- No model training was performed.
- No final feasibility conclusion is included.
