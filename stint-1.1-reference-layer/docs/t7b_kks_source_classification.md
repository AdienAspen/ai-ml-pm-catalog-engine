# T7b - KKS / RDS Candidate Source Classification

## Purpose

This short follow-up classifies the files that produced KKS / RDS-like pattern hits in T7. The goal is to determine whether any hit corresponds to a real client mapping file, generic documentation/manual material, external reference code, or generated project artefact.

No raw operational values are emitted in this note.

## Candidate Files Reviewed

| candidate | classification | finding | impact on G06 |
| --- | --- | --- | --- |
| `rds_pp_normative_pattern_presence_v1.csv` | generated T7 artefact | Aggregate output created by the T7 presence check. It only records the seven normative RDS-PP letter codes from the plan and their zero-hit status. | No additional evidence. |
| `Plan Tecnico v2 - STINT_1.1-reference-layer.md` | internal planning source | Planning document that names RDS-PP patterns as check criteria. It is not a data source, mapping file, or client reference. | No additional evidence. |
| `external/malyi/src/taxonomy_handler.py` | external reference code | Generic open-source taxonomy handling code. The apparent KKS/RDS hit comes from an illustrative hierarchical code example in source comments/code context. | External corroboration only; not FSA-specific. |
| `floc_ih06_observed_nodes_v1.csv` | generated IH06 aggregate artefact | Sanitized aggregate output from the IH06 structural/token pass. It contains observed node tokens and counts, not a controlled KKS mapping table. | Supports nomenclature-gap diagnosis, but does not resolve FLOC. |

## Conclusion

T7b did not find a standalone KKS/RDS client mapping file, manual, controlled code list, or customer-specific crosswalk in the scanned corpus.

The available evidence remains consistent with the previous T6/T7 interpretation:

- KKS / RDS-PP is useful as supporting reference context.
- It does not currently provide a resolutor for FLOC leaf assignment.
- Numeric/project-specific KKS segments must not be interpreted without an authoritative project-specific source.
- G06 remains open as a controlled-source / crosswalk dependency, not as a parser failure.

## Decision

Keep KKS/RDS evidence in the reference layer as support evidence only. Do not promote it to `validated_mapping` or target-level ground truth.
