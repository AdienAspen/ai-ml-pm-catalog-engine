# T5.1b2.3b - OEM Polysemic Code Profile

## Purpose

Profile OEM codes with multiple observed descriptions before any collapse, deduplication, SAP mapping, or denominator promotion.

## Results

- OEM occurrence rows: `4057`.
- Total OEM codes: `679`.
- Multi-description codes: `151`.
- Classification counts: `{'likely_polysemous': 81, 'undetermined': 29, 'likely_transcription_variant': 41}`.

## Method

Description variants are compared using `paraphrase-multilingual-MiniLM-L12-v2` embeddings over normalized descriptions. Codes are labelled as `likely_transcription_variant`, `likely_polysemous`, or `undetermined` for profiling only.

## Context Guardrail

Platform correlation is reported using hashed site and asset-type context plus date-quarter span. A context signal does not prove platform collision; it only indicates whether a composite dictionary key may be needed.

## Decision Guardrail

No code-description pair is collapsed in this pass. The internal sample is for direct review of the highest-dispersion groups.
