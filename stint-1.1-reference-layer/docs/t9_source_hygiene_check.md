# T9 Source Hygiene Check

## Purpose

This check verifies that discarded sources and ChatGPT tracking URL parameters are not used as primary/source-of-record references in `reference-layer-v1`.

## Patterns Checked

- `studylib`
- `scribd`
- `researchgate`
- `utm_source=chatgpt.com`

## Result

The formal reference-layer source records are clean:

- `docs/external-source-register.md`: no hits
- `external/source-manifest.json`: no hits
- `docs/reference-layer-v1-freeze-note.md`: no hits
- `docs/reference-layer-v1-freeze-checklist.md`: no hits

## Incidental Hits

Two non-blocking incidental hits were observed in broader repository scope:

- `docs/Plan Tecnico v2 - STINT_1.1-reference-layer.md`: planning instruction text that names discarded-source cleanup as a requirement. This file is ignored and is not a source-of-record reference.
- `external/malyi/README.md`: upstream third-party README badge/link for ResearchGate. This is part of the pinned upstream project metadata and is not used as a primary source in the reference layer.

## Decision

No discarded source is admitted as a primary reference source for `reference-layer-v1`.

No `utm_source=chatgpt.com` tracking parameter is present in the formal source records checked.

This closes the T9 source-hygiene control for PoC freeze.
