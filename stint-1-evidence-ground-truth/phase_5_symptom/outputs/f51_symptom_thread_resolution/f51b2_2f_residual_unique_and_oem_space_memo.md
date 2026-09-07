# F5.1b2.2f - Residual Unique Sample and OEM Space Pattern Expansion

## Purpose

Correct the residual blind-review sample so it is drawn from distinct `reason_hash` values, and measure the OEM alarm pattern missed by strict code-description separators.

## Results

- Strict residual before OEM-space expansion: `5819` rows.
- Distinct residual reason hashes: `1870`.
- OEM-space rows recovered from strict residual: `398`.
- Residual after OEM-space expansion: `5421` rows.
- Blind residual sample prepared: `40` distinct values, one per `reason_hash`.

## Method Note

The prior residual blind sample was row-based and therefore frequency-weighted. This replacement sample is value-based: one row per distinct `reason_hash`. It is suitable for judging residual composition, not for estimating row-weighted prevalence.

## OEM Code-Description Guardrail

The expanded OEM profile counts code-description pairs and explicitly allows one code to have multiple observed descriptions. No one-to-one OEM dictionary assumption is made.

## Privacy

Versioned outputs contain only counts, hashes, and sanitized metadata. Visible reason text is internal-only under `reports/internal/*` and ignored by Git.
