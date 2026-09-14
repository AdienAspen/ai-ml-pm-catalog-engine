# G2.0b Step 1 - Target Leakage Count

This is the counting step only. No materiality decision, rerun, recalibration, candidate promotion, or denominator change was performed.

The scan searched all three paths for target-label assignment patterns across Object Part, Damage, Cause, Activity, Symptom, FLOC/Functional Location and Activity Type/MAT/ILART variants, including German variants `Schadensbild`, `Ursache`, and `Maßnahme`.

The decisive field for Step 2 is `rows_above_threshold` in `g20b_leakage_count_sanitized.csv`, not percent of corpus. Evaluation-set contamination is reported separately in `g20b_evaluation_set_v1_leakage_check_sanitized.csv`.
