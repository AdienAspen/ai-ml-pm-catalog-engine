# Normalisation Pipeline Specification

This is the specification of the flow that STINT_1 will execute; it is not a production candidate run.

## Five-Step Flow

1. Mask tags and identifiers: remove or mask asset IDs, order IDs, serial-like strings, dates, and numeric counters before lexical matching.
2. Clean text: lowercase, normalize whitespace, remove punctuation that does not carry domain meaning, and preserve domain words.
3. Expand abbreviations: use the lexical seed dictionary plus curated bilingual aliases. Abbreviation expansion must retain provenance.
4. Correct spelling: apply conservative correction only when the target term is in a controlled reference layer entry.
5. NER / concept routing: route normalized spans to canonical concepts and then to SAP_MAPPING candidates or FLOC/IH06 node candidates.

## Guardrails

- Do not pre-translate all text. Use multilingual backbone assumptions plus bilingual canonical dictionaries.
- Preserve `source_text_field` for every observed term.
- Preserve `stratum` and never mix planned/reactive records with `event_structural` PDF rows in the same denominator.
- `Umrichter` is converter context, not generator context.
- A lexical match is not a validated mapping. Promotion requires evidence triangulation in STINT_1.
