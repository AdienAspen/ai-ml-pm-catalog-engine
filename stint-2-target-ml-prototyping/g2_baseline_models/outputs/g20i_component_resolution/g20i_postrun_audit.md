# G2.0i post-run audit - profile funnel, B1 only

The scoring instrument was frozen before results at cosine >= 0.60 and
top-two-node margin >= 0.05. This audit reads its outputs; it does not
select another threshold, promote candidates, or change F6.

## Scope and structural inventory

G1.2 linked 10,699 of 10,749 B1 orders to a turbine node; 50 lacked a
structural turbine match. The 274 matched turbine nodes span five sites.
One SITE-001 node has no profiled component candidate (six orders).
Across the subtrees there are 52,993 descendant nodes, 52,977 with a
resolvable profile, and 41,763 terminal leaves. SITE-003 contributes
the 16 unprofiled depth-3 descendants found in G2.0h; their profiled
children do not confer an upward profile.

The historical G2.0c Object Part count of 7,668 units included hits
from three concepts whose final target is `unassigned`. G2.0i admits
only the 40 final Object Part concepts, leaving 7,393 units with
concept signal; the 275-unit difference is an instrument change, not
a loss of source text.

## Per-order outcomes

| State | Orders | Interpretation |
|---|---:|---|
| Resolved | 2,400 | One node candidate passes frozen score and margin; not verified FLOC |
| Ambiguous | 3,772 | Score passes, but two nodes are within margin |
| Abstained | 4,577 | No structural scope, no concept, no candidate, or score below cut |

Of the 2,400 resolved candidates, 1,342 are IH06 leaves and 1,058
are internal nodes. All resolved nodes are at depth 3 or 4; none is at
depth 5. Thus `resolved component node` must not be equated with
`resolved FLOC leaf`. The 4,577 abstentions comprise 3,308 without an
assigned Object Part concept, 1,213 below score threshold, 50 without
a G1.2 turbine match, and 6 without a profiled descendant candidate.

| Site key | Resolved | Ambiguous | Abstained |
|---|---:|---:|---:|
| SITE-001 | 159 | 332 | 288 |
| SITE-003 | 561 | 382 | 638 |
| SITE-007 | 426 | 742 | 1,131 |
| SITE-008 | 901 | 1,539 | 1,752 |
| SITE-009 | 353 | 777 | 768 |

## Catalogue answer space

The answer space was recomputed independently for every one of the
12,000 resolved-order x catalog-type rows from the workbook, traversing
`profile -> type -> permitted group -> distinct (group, code)`.
The comparison below is **paired**: the same 1,839 orders have both a
turbine profile and a proposed component profile. SITE-003's 561
resolved orders have no turbine-level RBNR and are not mixed in.

| Target / catalog | Turbine groups, median | Component groups, median | Turbine codes, median | Component codes, median |
|---|---:|---:|---:|---:|
| Symptom / S | 1 | 1 | 6 | 14 |
| Object Part / B | 1 | 1 | 1 | 7 |
| Damage / C | 9 | 1 | 94 | 19 |
| Cause / 5 | 1 | 1 | 13 | 21 |
| Activity / A | 1 | 1 | 5 | 7 |

Across all 2,400 proposed component profiles, 202 have **no allowed
Activity A group**. The target's information may still be present in
the order; absence of a group in this profile is not evidence that
no activity occurred.

These are code-space sizes conditional on a text-derived node, not
classification accuracy, admitted denominators, or evidence that one
specific SAP code is correct. Information-type presence was measured
earlier; classification into catalog codes has not been measured.

## Independence and integrity

Exact and zero-stripped `assetId -> IH08.Equipment` and serial joins
yielded no order-level equipment/FLOC references; `rdsPpReference`
also yielded no exact IH06 FLOC. Site/turbine containment is an
independent **scope check**, not child-node ground truth. Therefore no
FLOC accuracy can be computed for this run. The same Object Part text
signal selected the node that restricts its catalog code space; it
cannot independently evaluate subsequent code classification.

The 10,749 order records are unique and use hashed IDs. The 12,000
catalog rows reconcile to five targets per resolved order. Source and
output hashes match their manifests, the full catalogue chain was
recomputed, and no raw site name or asset identifier was emitted.

Provenance: `expert_inference`, `silver-medium` maximum,
`semantic_component_node_resolution_v1`,
`paraphrase-multilingual-MiniLM-L12-v2`, `domain_vocabulary`,
`evaluation_independence=derived_from_rules`. No promotion, training,
denominator change, or F6 update.
