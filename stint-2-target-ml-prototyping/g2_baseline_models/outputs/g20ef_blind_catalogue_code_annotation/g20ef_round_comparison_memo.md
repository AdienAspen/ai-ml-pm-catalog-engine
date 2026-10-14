# G2.0e/f - Closing comparison memo

All four external resubmissions passed the structural gate: 187/188
rows per target, exact IDs, valid controlled responses, mode 600.
Same 300 physical units per target, exactly 75 shared IDs; no resampling.
Original receipts, packages, catalogue and original reports are unchanged.

## Damage format-only verification

142 serialization repairs verified; no judgement changed.
01: duplicate none_applicable removed from code, retaining group.
02: the explicit empty third field for 0293 was supplied by the user
in a separate correction message; that supplied correction is included.
No DevOps response assignment or adjudication occurred.

## Agreement on the overlap

| Target / level | n | matching | raw | kappa | AC1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| activity / response | 75 | 71 | 0.946667 | 0.892704 | 0.943144 |
| damage / group | 75 | 67 | 0.893333 | 0.604222 | 0.890690 |
| damage / group_code | 75 | 67 | 0.893333 | 0.608866 | 0.893059 |
| damage / both_assigned_group_code | 7 | 7 | 1.000000 | 1.000000 | 1.000000 |

Activity original v2 vs v2.1 on the same 75 units:
raw 0.560000 -> 0.946667; kappa 0.086379 -> 0.892704.

## Assigned-code conditioning

activity: both assigned 0; only 01 0; only 02 0; neither 75. Conditional exact group/code matches 0/0.
damage: both assigned 7; only 01 8; only 02 0; neither 60. Conditional exact group/code matches 7/7.

Full confusion matrices and per-class specific agreement are separate
sanitized CSVs. Specific agreement = 2*diagonal/(row+column marginal);
an unobserved class has no estimable agreement, not zero.
Damage code level uses group|code pairs, never code strings alone.
Level-one exits remain distinct outcomes, not matching empty codes.
Conditional agreement selects cases both annotators chose to code;
it is not catalogue coverage, SAP correctness, or corpus precision.

## Methods and limitations

Unweighted nominal kappa and Gwet AC1; no ordinal AC2 is appropriate.
AC1 uses fixed complete vocabularies: Activity 9, Damage group 12,
Damage group/code 106 (94 pairs + 3 exits + 9 group/code abstentions).
Both-assigned subset uses 5/94 catalogue outcomes respectively.
Category-count policy is explicit; AC1 depends on this choice.
Formula reference: https://pmc.ncbi.nlm.nih.gov/articles/PMC5965565/
Wilson intervals are descriptive, not guarantees of SAP accuracy.
Both annotators are LLMs, not SMEs. Models, annotation timestamps and
no-script compliance cannot be verified from CSV labels alone.
A3 was approved and communicated before re-annotation per chat;
the v2.1 repository addendum is an after-receipt archival snapshot,
not a retroactive claim that a file was frozen before annotation.
Activity frame is 1,234 units; rates describe the sample, not B1.
All metrics: B1_RELATIONAL, stated n, blind_llm_annotation, protocol
v2/v2.1 as declared, no classifier threshold. Non-final diagnostic:
eligible_for_final_heldout=false. No F6 or frozen evaluation change.
