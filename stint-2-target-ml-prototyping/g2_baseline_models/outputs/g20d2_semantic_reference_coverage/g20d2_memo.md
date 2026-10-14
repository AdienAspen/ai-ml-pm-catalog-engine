# G2.0d2 - External-vocabulary detector comparison

`conservative_lexical_floor` reproduces G2.0d's wider lexical registry. `conservative_lexical_floor_same_prototypes` uses only canonical frozen external phrases; the five overlap groups compare it with `broader_semantic_estimate` on identical units and phrases.

The semantic estimate is not a proven ceiling, precision measurement or SAP truth. Its fixed 0.50 score cutoff was frozen before measurement, inherited from T5.1b2.X-normalized, and was not recalibrated here. No G0 labels or observed corpus text were used to construct prototypes.

Cause has 16 available external concepts: 9 WMEP cause categories and 7 NREL GRD concepts. A high top-concept share can reflect coarse taxonomy rather than prototype collapse; counts and this table alone cannot separate those explanations. Review concept-level assignments and errors before interpreting a concentration flag.

| Universe | Target | Path | N | Conservative lexical floor | Same-prototype lexical | Broader semantic estimate | Lexical only | Semantic only | Intersection | Union | No anchor | Available concepts | Matched concepts | Top concept share | Flag >30% |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| full_cleaned_corpus | Cause | B1_RELATIONAL | 10749 | 44 | 44 | 545 | 43 | 544 | 1 | 588 | 10161 | 16 | 13 | 47.71% | yes |
| full_cleaned_corpus | Cause | B2_WORKBOOKS | 1857 | 5 | 5 | 162 | 4 | 161 | 1 | 166 | 1691 | 16 | 10 | 63.58% | yes |
| full_cleaned_corpus | Cause | PATH_A | 362 | 2 | 2 | 156 | 0 | 154 | 2 | 156 | 206 | 16 | 9 | 57.05% | yes |
| full_cleaned_corpus | Damage | B1_RELATIONAL | 10749 | 451 | 443 | 3820 | 123 | 3500 | 320 | 3943 | 6806 | 113 | 83 | 15.05% | no |
| full_cleaned_corpus | Damage | B2_WORKBOOKS | 1857 | 36 | 24 | 623 | 0 | 599 | 24 | 623 | 1234 | 113 | 47 | 23.60% | no |
| full_cleaned_corpus | Damage | PATH_A | 362 | 4 | 4 | 298 | 1 | 295 | 3 | 299 | 63 | 113 | 31 | 23.49% | no |
| full_cleaned_corpus | Symptom | B1_RELATIONAL | 10749 | 192 | 192 | 122 | 187 | 117 | 5 | 309 | 10440 | 8 | 6 | 55.74% | yes |
| full_cleaned_corpus | Symptom | B2_WORKBOOKS | 1857 | 1 | 1 | 27 | 0 | 26 | 1 | 27 | 1830 | 8 | 5 | 85.19% | yes |
| full_cleaned_corpus | Symptom | PATH_A | 362 | 26 | 26 | 73 | 0 | 47 | 26 | 73 | 289 | 8 | 4 | 39.73% | yes |
| model_eligible_construction_corpus | Cause | B1_RELATIONAL | 9263 | 41 | 41 | 289 | 40 | 288 | 1 | 329 | 8934 | 16 | 13 | 25.61% | no |
| model_eligible_construction_corpus | Cause | B2_WORKBOOKS | 1478 | 2 | 2 | 123 | 1 | 122 | 1 | 124 | 1354 | 16 | 9 | 77.24% | yes |
| model_eligible_construction_corpus | Cause | PATH_A | 159 | 0 | 0 | 70 | 0 | 70 | 0 | 70 | 89 | 16 | 6 | 57.14% | yes |
| model_eligible_construction_corpus | Damage | B1_RELATIONAL | 9263 | 367 | 359 | 3078 | 77 | 2796 | 282 | 3155 | 6108 | 113 | 83 | 11.70% | no |
| model_eligible_construction_corpus | Damage | B2_WORKBOOKS | 1478 | 0 | 0 | 368 | 0 | 368 | 0 | 368 | 1110 | 113 | 36 | 24.18% | no |
| model_eligible_construction_corpus | Damage | PATH_A | 159 | 2 | 2 | 111 | 1 | 110 | 1 | 112 | 47 | 113 | 23 | 18.92% | no |
| model_eligible_construction_corpus | Symptom | B1_RELATIONAL | 9263 | 187 | 187 | 104 | 183 | 100 | 4 | 287 | 8976 | 8 | 6 | 60.58% | yes |
| model_eligible_construction_corpus | Symptom | B2_WORKBOOKS | 1478 | 0 | 0 | 21 | 0 | 21 | 0 | 21 | 1457 | 8 | 1 | 100.00% | yes |
| model_eligible_construction_corpus | Symptom | PATH_A | 159 | 5 | 5 | 20 | 0 | 15 | 5 | 20 | 139 | 8 | 2 | 55.00% | yes |

B2 remains provisional because inherited Step 5 source identity does not reconcile with F6. Path A is reported separately. No F6 denominator, prototype, threshold, unit score or model result was changed. The original report and manifest are retained with `pre_addendum` names.
