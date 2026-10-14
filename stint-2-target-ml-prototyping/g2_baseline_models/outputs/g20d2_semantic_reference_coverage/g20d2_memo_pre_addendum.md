# G2.0d2 - External-vocabulary semantic detector

The lexical exact match is a conservative floor. Prototype coverage is a broader semantic estimate; it can over-generate and is not a verified ceiling, a precision estimate or SAP truth.

The threshold 0.50 was frozen before this run from T5.1b2.X-normalized. Its previous calibration does not establish accuracy for these new external prototypes. Only canonical phrases from the frozen 144-row external source are prototypes; no SAP, translation aliases, G2.0c augmentations, analyst examples or corpus terms enter.

The original G2.0d lexical count used a wider registry. The same-prototype lexical column isolates the detector comparison. Lexical-only, semantic-only, intersection, union and no-anchor use that common external prototype set and unique units.

| Universe | Target | Path | N | G2.0d lexical | Same-source lexical | Semantic | Lex only | Sem only | Both | Union | Neither | Top share |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| full_cleaned_corpus | Cause | B1_RELATIONAL | 10749 | 44 | 44 | 545 | 43 | 544 | 1 | 588 | 10161 | 47.71% |
| full_cleaned_corpus | Cause | B2_WORKBOOKS | 1857 | 5 | 5 | 162 | 4 | 161 | 1 | 166 | 1691 | 63.58% |
| full_cleaned_corpus | Cause | PATH_A | 362 | 2 | 2 | 156 | 0 | 154 | 2 | 156 | 206 | 57.05% |
| full_cleaned_corpus | Damage | B1_RELATIONAL | 10749 | 451 | 443 | 3820 | 123 | 3500 | 320 | 3943 | 6806 | 15.05% |
| full_cleaned_corpus | Damage | B2_WORKBOOKS | 1857 | 36 | 24 | 623 | 0 | 599 | 24 | 623 | 1234 | 23.60% |
| full_cleaned_corpus | Damage | PATH_A | 362 | 4 | 4 | 298 | 1 | 295 | 3 | 299 | 63 | 23.49% |
| full_cleaned_corpus | Symptom | B1_RELATIONAL | 10749 | 192 | 192 | 122 | 187 | 117 | 5 | 309 | 10440 | 55.74% |
| full_cleaned_corpus | Symptom | B2_WORKBOOKS | 1857 | 1 | 1 | 27 | 0 | 26 | 1 | 27 | 1830 | 85.19% |
| full_cleaned_corpus | Symptom | PATH_A | 362 | 26 | 26 | 73 | 0 | 47 | 26 | 73 | 289 | 39.73% |
| model_eligible_construction_corpus | Cause | B1_RELATIONAL | 9263 | 41 | 41 | 289 | 40 | 288 | 1 | 329 | 8934 | 25.61% |
| model_eligible_construction_corpus | Cause | B2_WORKBOOKS | 1478 | 2 | 2 | 123 | 1 | 122 | 1 | 124 | 1354 | 77.24% |
| model_eligible_construction_corpus | Cause | PATH_A | 159 | 0 | 0 | 70 | 0 | 70 | 0 | 70 | 89 | 57.14% |
| model_eligible_construction_corpus | Damage | B1_RELATIONAL | 9263 | 367 | 359 | 3078 | 77 | 2796 | 282 | 3155 | 6108 | 11.70% |
| model_eligible_construction_corpus | Damage | B2_WORKBOOKS | 1478 | 0 | 0 | 368 | 0 | 368 | 0 | 368 | 1110 | 24.18% |
| model_eligible_construction_corpus | Damage | PATH_A | 159 | 2 | 2 | 111 | 1 | 110 | 1 | 112 | 47 | 18.92% |
| model_eligible_construction_corpus | Symptom | B1_RELATIONAL | 9263 | 187 | 187 | 104 | 183 | 100 | 4 | 287 | 8976 | 60.58% |
| model_eligible_construction_corpus | Symptom | B2_WORKBOOKS | 1478 | 0 | 0 | 21 | 0 | 21 | 0 | 21 | 1457 | 100.00% |
| model_eligible_construction_corpus | Symptom | PATH_A | 159 | 5 | 5 | 20 | 0 | 15 | 5 | 20 | 139 | 55.00% |

A high top-concept share may reflect a coarse external taxonomy or prototype collapse. The count alone cannot distinguish the two. Source taxonomy, assigned concept distribution and representative errors need review before interpreting the signal.

B2 uses the inherited Step 5 grouping whose source identity does not reconcile with F6; its measurements are provisional. This detector comparison does not repair upstream grouping. Path A remains separate. No F6 denominator changed; no candidate was promoted or model trained. Evaluation-set labels did not tune prototypes or threshold. No raw corpus text is emitted.
