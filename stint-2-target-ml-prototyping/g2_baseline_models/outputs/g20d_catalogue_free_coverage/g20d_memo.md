# G2.0d - Catalogue-free reference coverage

This is domain-supported volume, not SAP ground truth or an evaluation of a model.

## Frozen instrument

Exact frozen phrases after leakage masking and semantic_normalisation_v2; no embeddings, new aliases, synonym generation, token stemming or retrospective tuning. Domain evidence comes from the full 144-entry external reference inventory, frozen translations and the three prior reference-augmentation entries. Reference scopes, tiers and inference-derived aliases remain explicit. ZEUS containers are not converted into invented lexical anchors.

## Coverage by universe

Domain includes both-source units. Domain + SAP-only + neither equals the path universe. Top share is computed over domain-anchored units, not all units or summed mentions.

| Universe | Target | Path | N | Domain | SAP only | Neither | Top share |
|---|---|---|---:|---:|---:|---:|---:|
| full_cleaned_corpus | Cause | B1_RELATIONAL | 10749 | 44 | 307 | 10398 | 79.55% |
| full_cleaned_corpus | Cause | B2_WORKBOOKS | 1857 | 5 | 24 | 1828 | 80.00% |
| full_cleaned_corpus | Cause | PATH_A | 362 | 2 | 0 | 360 | 100.00% |
| full_cleaned_corpus | Damage | B1_RELATIONAL | 10749 | 451 | 942 | 9356 | 34.15% |
| full_cleaned_corpus | Damage | B2_WORKBOOKS | 1857 | 36 | 37 | 1784 | 66.67% |
| full_cleaned_corpus | Damage | PATH_A | 362 | 4 | 21 | 337 | 75.00% |
| full_cleaned_corpus | Symptom | B1_RELATIONAL | 10749 | 192 | 286 | 10271 | 80.73% |
| full_cleaned_corpus | Symptom | B2_WORKBOOKS | 1857 | 1 | 6 | 1850 | 100.00% |
| full_cleaned_corpus | Symptom | PATH_A | 362 | 26 | 0 | 336 | 53.85% |
| model_eligible_construction_corpus | Cause | B1_RELATIONAL | 9263 | 41 | 286 | 8936 | 78.05% |
| model_eligible_construction_corpus | Cause | B2_WORKBOOKS | 1478 | 2 | 22 | 1454 | 100.00% |
| model_eligible_construction_corpus | Cause | PATH_A | 159 | 0 | 0 | 159 | undefined |
| model_eligible_construction_corpus | Damage | B1_RELATIONAL | 9263 | 367 | 836 | 8060 | 41.14% |
| model_eligible_construction_corpus | Damage | B2_WORKBOOKS | 1478 | 0 | 34 | 1444 | undefined |
| model_eligible_construction_corpus | Damage | PATH_A | 159 | 2 | 2 | 155 | 50.00% |
| model_eligible_construction_corpus | Symptom | B1_RELATIONAL | 9263 | 187 | 174 | 8902 | 81.28% |
| model_eligible_construction_corpus | Symptom | B2_WORKBOOKS | 1478 | 0 | 5 | 1473 | undefined |
| model_eligible_construction_corpus | Symptom | PATH_A | 159 | 5 | 0 | 154 | 100.00% |

## F6 reconciliation

Cause and Damage reconcile to physical orders in B1; Cause also reconciles in Path A. Symptom B1 reconciles all 1,827 reason rows, in sequence and by hash, to distinct physical orders. The eligible comparison excludes the same order keys as G2.0c, and exclusions are reported separately. Reason-only domain coverage is also retained to distinguish field expansion from detector changes.

Symptom's 68 concern-table rows, 42 notes and 62 workbook text rows retain their own F6 strata. These are not one-to-one event denominators. Their source counts are verified, but neither addition across strata nor subtraction from constituted-event coverage is performed. Numeric deltas for those three rows remain null in both universes.

There are two additional unit-universe defects in the inherited Step 5 loader. Damage Path A has 48 PATHA-NOTE-EVENT keys outside its constituted event inventory. B2's imported family_for_path function recognizes sanitized directory tokens rather than the original input roots, yielding SNAPSHOT_FAMILY_UNKNOWN/unknown. None of the 57 Cause or 110 Damage historical B2 keys matches the reconstructed Step 5 keys. These are not evaluation exclusions or evidence of signal loss. Their F6 deltas are also null. B2 coverage is an exact replica of the inherited Step 5 universe, provisional pending an explicit source-identity repair and a re-audit of grouping and exclusions. No upstream frozen script or G2.0c membership was silently repaired.

## Limits

A reference phrase hit is not a confirmed symptom, physical damage mechanism, causal relation, subsystem assignment or SAP label. Failure modes, fault events and damage mechanisms remain distinguished in the inventory and source-specific report. Shared phrases can support several source scopes; source counts must not be summed.

Exact matching can miss inflections and unlisted expressions. Full canonical phrases containing conjunctions or slashes are normalized as whole phrases, not split into new seeds. Zero matches do not establish zero underlying signal. Historical F6 methods include semantic detectors; the contrast is descriptive, not an isolated causal estimate of catalogue over-generation. No expected outcome was used to choose rules.

No raw corpus text is emitted. G2.0c outputs, evaluation artifacts and F6 are unchanged. G2.0e, new annotation, training, promotion and denominator updates were not started.
