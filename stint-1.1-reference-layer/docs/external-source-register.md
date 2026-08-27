# External Source Register

This register documents the external sources admitted into `reference-layer-v1`.
It is part of `T2 - External ingest`.

## Admission Rules

- External material must have a stable public URL, commit hash, and license status.
- External material is reference input, not client ground truth.
- External material must not be promoted to measurement evidence without target-specific validation.
- Dummy or placeholder datasets are not ingested as evidence.
- Evidence type and evidence tier remain separate fields.

## Sources

| source_id | role | upstream_url | pinned_commit | license | ingest_status | notes |
| --- | --- | --- | --- | --- | --- | --- |
| `maintie` | maintenance NLP corpus and annotation schema | `https://github.com/nlp-tlp/maintie` | `825e7710e4129598da997276a38b3cb40b200bc2` | MIT | partial_ingest | Public maintenance annotation scheme, guidelines, and model notes are versioned. Corpus releases are fetchable by script but not committed by default. They can support semantic vocabulary design and benchmarking, not client ground truth. |
| `malyi` | wind maintenance log labelling reference implementation | `https://github.com/mvmalyi/llm-driven-wind-turbine-maintenance-log-labelling` | `e55006f26c02e17f1d8bd1954a6b722450b649c3` | MIT | partial_ingest | Code, prompts, templates, and taxonomy handling are admitted. `data/placeholder` is not evidence. |

## Versioned MaintIE Files

- `README.md`
- `LICENSE.md`
- `SCHEME.md`
- `GUIDELINES.md`
- `MODELS.md`
- `RESULTS.md`
- `data/scheme.json`

## Ingested Malyi Files

- `README.md`
- `LICENSE`
- `requirements.txt`
- `orchestration_template.ipynb`
- `prompts/`
- `src/`

## Explicit Exclusions

- Malyi `data/placeholder` is excluded because it is not an evidence-bearing dataset.
- MaintIE `data/gold_release.json` and `data/silver_release.json` are fetchable local reference corpora but are not versioned by default.
- Repository `.git/` folders are excluded.
- External sources do not establish runtime availability, validated mappings, or model denominators by themselves.

## Evidence Use

| source_id | allowed_use | forbidden_use |
| --- | --- | --- |
| `maintie` | semantic pattern reference, annotation-design reference, auxiliary benchmark design | production accuracy, client ground truth, target denominator |
| `malyi` | taxonomy design, prompt/schema reference, weak-supervision architecture reference | direct labels, client ground truth, direct SAP mapping proof |
