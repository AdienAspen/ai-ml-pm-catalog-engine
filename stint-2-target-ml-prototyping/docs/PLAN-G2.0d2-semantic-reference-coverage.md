# G2.0d2 - Frozen external vocabulary, semantic detector

## Instrument frozen before measurement

- Target scope: Cause, Damage, Symptom; B1, Path A, B2 separately.
- Universe: G2.0d full cleaned and model-eligible memberships, including the
  same G2.0b leakage mask and evaluation/held-out exclusions.
- Prototypes: canonical English phrases from the frozen 144-row
  `external_failure_vocabulary_v1.csv` only. No Spanish translation aliases,
  G2.0c reference augmentations, SAP catalogue terms, analyst-written examples,
  G2.0 prototypes or observed corpus phrases.
- Normalize each source segment and prototype with `semantic_normalisation_v2`.
  Embed using `paraphrase-multilingual-MiniLM-L12-v2` with L2-normalized vectors.
  Select the highest cosine-scoring external prototype independently per target,
  then abstain if its score is below **0.50**. This fixed cutoff comes from
  T5.1b2.X-normalized; it is not calibrated or validated for this instrument.
  Source segments are scored separately; the maximum is retained at unit level.
- Keep the historical G2.0d lexical figures and also calculate an exact-match
  floor using precisely the 144 external phrases. G2.0d's original lexical
  registry included 53 translated aliases and three earlier augmentations;
  that original count alone cannot isolate the effect of the detector.
- The pair of same-prototype detectors yields lexical-only, semantic-only,
  intersection, union and neither, using distinct physical/event units.
- Top concept share is the frequency of the best assigned canonical concept
  divided by semantically anchored units in that target/path/universe. Flag >30%.

## Interpretation and controls

Exact matching is a conservative lexical floor; semantic matching is a broader
estimate. The latter can over-generate and is not a proven ceiling. Neither
coverage figure is precision, SAP truth or independent evaluation. The 0.50
cutoff is historical and can affect coverage substantially.

Report B2 as provisional due to the inherited Step 5 source identity defect;
do not convert F6's incompatible event and text-row strata into zeros or
silently repair upstream keys. Path A and B2 are reported separately. No F6
denominator change, candidate promotion, training or G2.0e work is authorized
by this step.
