# G2.0 Diagnostic Addendum

This addendum responds to the post-run interpretation risk: one held-out cell has n=17, and B1 abstention cannot yet distinguish weak prototypes from absent corpus signal.

Generated diagnostics:

- `g20_pre_abstention_best_class_distribution_sanitized.csv`: best prototype class distribution before threshold abstention.
- `g20_score_band_distribution_sanitized.csv`: score bands by target and path before abstention.
- `g20_b1_object_part_subthreshold_sample_manifest_sanitized.csv`: sanitized manifest for a 20-row internal visible-text review sample.

The internal visible sample is stored under `g2_baseline_models/internal/g20_zero_shot_prototype_baseline/` with mode 600. It is not versioned and emits raw text only inside the closed environment.

Interpretation rule: the Object Part PATH_A held-out point is reported as insufficient evaluation support, not as a performance claim. Precision 17/17 means no observed errors in 17 covered held-out rows; it does not establish perfect precision.
