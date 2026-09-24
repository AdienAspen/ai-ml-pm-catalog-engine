# G2.0c - Step 5 coverage report

Descriptive lexical coverage only. No accuracy, admission, F6 change, or training.

## Method

Frozen Step 3b surface variants are matched exactly after G2.0b masking and semantic_normalisation_v2. The same frozen global lexicon is applied to each path, with no cross-path count aggregation. Source segment boundaries are preserved. Each concept counts at most once per unit and target. All 67 assigned concepts participate, including concepts without a Step 4 catalogue match.

The paired SAP comparator uses frozen high-band SAP-owned canonical phrases with the same normalization and units. This is a lexical comparator, not a replay of the historical semantic admission mechanism. anchor_source is explicit; for SAP it is derived from frozen ownership, not originally populated evidence.

Top share is concept units / units anchored by the same source, target and path. Multi-concept hits are allowed; concept counts must not be summed into a denominator. A flag is not proof that a concept is semantically generic, but requires review before using coverage to scope modelling.

## Full corpus, statistics only

| Target | Path | Units | Domain (including both) | Both | SAP only | Neither | Domain concepts | Top share | Gate |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| Activity | B1_RELATIONAL | 10749 | 7606 | 1306 | 3 | 3140 | 24 | 37.27% | FLAG |
| Activity | B2_WORKBOOKS | 1857 | 213 | 5 | 0 | 1644 | 19 | 20.66% | within limit |
| Activity | PATH_A | 362 | 321 | 1 | 0 | 41 | 20 | 60.44% | FLAG |
| Object Part | B1_RELATIONAL | 10749 | 7668 | 5628 | 891 | 2190 | 43 | 20.33% | within limit |
| Object Part | B2_WORKBOOKS | 1857 | 353 | 182 | 152 | 1352 | 31 | 31.73% | FLAG |
| Object Part | PATH_A | 362 | 289 | 257 | 16 | 57 | 29 | 46.37% | FLAG |

## Historical reconciliation

The plan's Activity 52.7% was 858/1628 across paths. B1 alone is 832/1215 = 68.48%. This report corrects the comparison without rewriting frozen G1.2c evidence. Object Part 3737 is restricted to 6670 no-item orders. A separate same-subset file retains that scope. Historical membership contrasts are descriptive, not a claim of equivalent detector methods.

## Integrity and limitations

The 13 masked units match G2.0b exactly. The 10900 eligible keys and all 24405 frozen member frequencies reconcile. Current evaluation and heldout manifests were rechecked; any drift aborts the run. The 13 reviewed-concept exclusions are retained and their unit exposure is explicit for both targets. No response labels were read. No reviewed concept becomes eligible for evaluation here.

Path A construction uses only 159 units. B2 coverage may miss surface forms excluded with evaluation text. Exact lexical hits, cluster coherence, component presence and SAP coding correctness are different questions. The measured coverage does not validate the latter three.

Only hashed unit/concept identifiers, counts and metadata are emitted. No source text or new visible-text sample is written. Upstream files and evaluation artifacts are verified unchanged by SHA-256.

Step 5 is executed; concentration flags remain open findings. No model training or G2 closure is implied.
