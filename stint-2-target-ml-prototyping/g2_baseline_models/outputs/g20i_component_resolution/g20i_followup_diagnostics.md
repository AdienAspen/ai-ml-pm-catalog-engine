# G2.0i follow-up - depth-5 ambiguity and missing Activity A groups

Read-only diagnosis of the frozen G2.0i run. No threshold, assignment,
denominator, or F6 change. Counts are B1-only and refer to the original
10,749-order run unless a narrower subset is stated.

## Why no depth-5 node resolved

Depth-5 nodes were not invisible to the matcher. They were the top
candidate for 545 ambiguous orders and 22 below-threshold orders;
none met both the frozen score and node-margin rule for `resolved`.
Among the 545 ambiguous top-depth-5 cases:

| Diagnostic | Count |
|---|---:|
| Runner-up also at depth 5 | 451 |
| Top and runner-up have identical normalized descriptions | 353 |
| Top and runner-up carry the same RBNR | 545 |
| Median top-two score margin | 0.000 |

Within the exact turbine subtrees traversed by G2.0i, 10,071 depth-5
nodes reduce to only 33 distinct descriptions after
`semantic_normalisation_v2`. For comparison, depth 3 has 9,250 nodes /
99 distinct descriptions, and depth 4 has 33,672 nodes / 400 distinct
descriptions. These counts use IH06 parent links, not a loose FLOC-prefix
match.
These are corpus/description diagnostics, not an estimate of accuracy.

The immediate blocker is **node-level ambiguity**, often repeated
descriptions across different branches of the same turbine. The top
two sharing RBNR suggests a profile may sometimes be more identifiable
than the exact node, but it is insufficient to assert profile certainty:
other near-score nodes may carry a different RBNR. A profile-level
claim would require checking the entire frozen score band, without
changing the node-level result or reusing it as independent evaluation.

## Why 202 resolved candidates have no Activity A group

All 202 are in SITE-003, all are depth-4 terminal nodes, and all have
zero type-A associations in the source workbook. Their profiles are:

| Catalog profile | Workbook description | Orders |
|---|---|---:|
| PMQPBI | Detector, Fume | 183 |
| PMGHMCC | MCC - Motor Control Center | 13 |
| PM-SPS | Switch, Pressure | 5 |
| PMACPF | Air Cooled Heat Exchanger | 1 |

For all four, the same workbook does contain S, B, C, and 5 group
associations (C has nine groups). The 183 Detector/Fume candidates all
have a frozen Object Part concept hit for `smoke detector`, so the
semantic resolution is plausible but **not independently verified**.
Median node score/margin in the 202 is 0.842/0.122; the corresponding
medians across all 2,400 resolved candidates are 0.811/0.087. This
does not prove the selected node is correct.

The G2.0c Activity domain vocabulary detects an Activity concept in
169/202 of these orders (83.7%). Within SITE-003's other 359 resolved
orders whose profile does permit A, it detects 250/359 (69.6%).
These are information-presence anchors, **not SAP A labels**.
Therefore `no allowed A group` cannot be interpreted as `no activity`.
The present evidence cannot distinguish an intentionally sparse A
configuration from a wrong text-derived node; that requires SAP catalog
owner confirmation or independent structural child-node evidence.

Neither diagnostic promotes FLOC candidates or establishes catalog
code classification performance. The Object Part signal used for node
selection remains ineligible as an independent test of that node's
profile-restricted code space.
