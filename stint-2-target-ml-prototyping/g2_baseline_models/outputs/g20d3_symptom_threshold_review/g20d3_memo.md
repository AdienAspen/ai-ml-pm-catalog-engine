# G2.0d3 - Symptom threshold review

Diagnostic curve only; no threshold is selected. Selection requires independent evaluation material. These counts are not precision, F1, a denominator or SAP truth.

The eight Symptom prototypes are frozen WMEP failure effects. ZEUS supplied a detection-symptom category definition but no materialized lexical prototype, so ZEUS contributed zero prototypes in G2.0d2 and in this review.

The same 9,263 eligible B1 units, G2.0b leakage mask, semantic_normalisation_v2, MiniLM vectors and per-segment max-cosine scoring are retained. Scores at 0.50 were reconciled against the original G2.0d2 ledger before this curve was accepted.

| Threshold | Assigned | Abstained | Coverage | Lexical only | Semantic only | Intersection | Union | No anchor | Matched concepts | Top share |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.30 | 3314 | 5949 | 35.78% | 2 | 3129 | 185 | 3316 | 5947 | 8 | 40.53% |
| 0.35 | 1541 | 7722 | 16.64% | 169 | 1523 | 18 | 1710 | 7553 | 8 | 44.06% |
| 0.40 | 713 | 8550 | 7.70% | 179 | 705 | 8 | 892 | 8371 | 8 | 58.63% |
| 0.45 | 285 | 8978 | 3.08% | 180 | 278 | 7 | 465 | 8798 | 8 | 48.77% |
| 0.50 | 104 | 9159 | 1.12% | 183 | 100 | 4 | 287 | 8976 | 6 | 60.58% |
| 0.55 | 66 | 9197 | 0.71% | 184 | 63 | 3 | 250 | 9013 | 4 | 62.12% |
| 0.60 | 20 | 9243 | 0.22% | 185 | 18 | 2 | 205 | 9058 | 3 | 75.00% |

As the cutoff rises from 0.30 to 0.60, the overlap with the lexical detector moves from 185 to 2 units. This curve diagnoses score transfer; it does not validate a replacement threshold.

The original 0.50 threshold came from T5.1b2.X against `reason` and a different prototype set. A low overlap at that cutoff is not proof of absent symptom signal. The lexical floor is not mathematically nested in semantic assignments.

No F6 update, candidate promotion or model training was performed. No visible operational text is emitted.

## Concept-level agreement within shared units

Unit overlap alone does not establish agreement on the symptom concept. The best semantic prototype is compared with the full set of lexical concepts recorded for that unit; no response labels are involved.

| Threshold | Shared units | Same concept | Different best concept | Same-concept share | Top mismatch count |
|---:|---:|---:|---:|---:|---:|
| 0.30 | 185 | 16 | 169 | 8.65% | 151 |
| 0.35 | 18 | 11 | 7 | 61.11% | 5 |
| 0.40 | 8 | 7 | 1 | 87.50% | 1 |
| 0.45 | 7 | 7 | 0 | 100.00% | 0 |
| 0.50 | 4 | 4 | 0 | 100.00% | 0 |
| 0.55 | 3 | 3 | 0 | 100.00% | 0 |
| 0.60 | 2 | 2 | 0 | 100.00% | 0 |

At 0.30, overlap reaches 185 of the 187 lexical units, but only 16 shared units retain the same concept. In 151 units, the lexical concept `overload` maps to the semantic best concept `reduced power`. Lowering the threshold therefore recovers unit overlap while losing concept agreement. This does not justify choosing 0.30 or establish that the 0.50 cutoff was merely too high; independent evaluation would be required to judge either assignment.
