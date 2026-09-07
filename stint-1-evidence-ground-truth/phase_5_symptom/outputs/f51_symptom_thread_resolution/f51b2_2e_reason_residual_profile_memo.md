# F5.1b2.2e - Residual Reason Profile

## Purpose

Profile the residual `reason` universe after strict OEM alarm, CMS alert, and dispatch-motive patterns have been removed.

## Results

- Residual rows: `5819`.
- Numeric-prefix rows: `307` (`5.28%`).
- Code-like-prefix rows: `2041` (`35.07%`).
- Rows with weaker dispatch-like cues not captured by the strict exclusion: `1549` (`26.62%`).
- Blind residual sample prepared: `40` rows in ignored internal storage.

## Interpretation Guardrail

This is a profile, not a Symptom classifier. The residual is not assumed to be technician prose. It now has a measurable residual structure that can be reviewed before downstream classification.

## Privacy

Versioned outputs contain only counts, hashes, buckets, and sanitized metadata. The visible text sample is internal-only under `reports/internal/*` and is ignored by Git.
