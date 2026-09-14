# G2.0b Step 2 - Leakage Materiality Decision

Decision: `not_material_for_G2_0`.

Rule branch applied:

```text
0 leaked rows above threshold
  -> not material for G2.0 · exclude and proceed
```

Inputs from Step 1:

```text
rows_with_leakage        13
regex_hit_rows           13
rows_above_threshold     0
evaluation_set_v1 leaks  0
annotation package leaks 1
```

Interpretation:

The leakage exists and is real, but no leaked row is part of a G2.0 assigned unit above threshold. Under the stated materiality rule, G2.0 does not require a rerun and the catalogue-vs-prototype comparison does not require recomputation for this leakage issue.

The evaluation set v1 check is separate from G2.0 materiality. It found zero leaked rows, so no v1 cleaning action is required.

The clean Object Part B1 annotation package manifest contains one leaked source unit. That package had already masked the visible text for annotation; the source unit is retained in the masking manifest for future corpus use.

No recalibration, rerun, candidate promotion, or denominator change was performed.
