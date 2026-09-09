# Reference Pointers

Do not copy frozen artifacts into this worktree.

Reference frozen inputs by relative path:

```python
REFERENCE_LAYER = "../stint-1.1-reference-layer/reference_layer"
STINT_1_OUTPUTS = "../stint-1-evidence-ground-truth"
F6_DENOMINATORS = STINT_1_OUTPUTS + "/phase_6_denominators/outputs"
```

## Frozen Inputs

- `../stint-1.1-reference-layer/`
- `../stint-1-evidence-ground-truth/`

## Boundary

If a frozen artifact is ever unfrozen, no divergent copies should exist in STINT 2.

STINT 2 may read frozen upstream artifacts, but changes to those artifacts must be made in their own branches and documented as upstream deltas.
