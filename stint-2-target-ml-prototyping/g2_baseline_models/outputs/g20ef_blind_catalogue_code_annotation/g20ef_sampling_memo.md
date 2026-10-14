# G2.0e/G2.0f blind package preparation

Protocol: g01-v2. This registration prepares annotation inputs only; no labels
or agreement metrics have been produced.

## Sampling

| Target | B1 source units | Frozen construction exclusions | Empty text | G2.0c reviewed-concept exposure | Eligible frame | Unique sample | Shared IDs | Responses |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Activity | 10,749 | 1,486 | 2 | 8,027 | 1,234 | 300 | 75 | 375 |
| Damage | 10,749 | 1,486 | 2 | not applicable | 9,261 | 300 | 75 | 375 |

The frozen construction exclusions include evaluation_set_v1 units and
additional prior held-out content. Selected units were rechecked against both
keys and semantic-normalized content hashes: zero collisions. The 13 G2.0c
reviewed concepts are excluded from Activity by their frozen unit-exposure
register, not by reinterpreting labels.

Sampling is simple random **within each eligible frame**. Activity's frame is
only 1,234 units after the reviewed-concept exclusion, so this sample is not
representative of all 10,749 B1 orders. Do not generalize Activity rates to
the full B1 population. The two targets are sampled independently; some
physical source units may appear under both target questions.

Both targets remain `eligible_for_final_heldout=false`. Independent blind
LLM labels do not make prior corpus exposure during instrument development
disappear. Any later final-heldout claim requires a separate leakage audit
and, if necessary, fresh post-freeze data.

## Delivery and integrity

The private tree under `g2_baseline_models/internal/
g20e_g20f_blind_catalogue_code_annotation` contains the committee protocol,
four target-by-annotator JSONL packages, catalogue code lists, and blank
response templates. Annotators must receive the protocol, relevant code list,
and their own JSONL rows **pasted into their chat**. They must not be asked to
read the repository or to run code. Packages expose only `annotation_id,text`;
the target is supplied by package context. Path, scores, strata and source
keys are not visible to annotators.

Each target has 300 unique IDs, 75 shared across annotators, and 187/188
assigned IDs. JSONL round-trip, ID uniqueness, blank response templates,
catalogue cardinality (A: 5; C: 94 group-code pairs), file permissions,
G2.0b masking, and restricted-term checks passed. Packages and templates are
mode 600; private directories are mode 700. Visible text is not versioned.

The full source text is not truncated. PII and operational entities are
redacted, and catalogue assignments are masked before delivery. The four
packages contain 750 response slots; seven of those visible rows contain a
G2.0b mask token.

The committee-authored protocol remains the sole authority for label
semantics. No response file is accepted until its IDs, row count, vocabulary,
and Damage group-code pairing pass structural validation.
