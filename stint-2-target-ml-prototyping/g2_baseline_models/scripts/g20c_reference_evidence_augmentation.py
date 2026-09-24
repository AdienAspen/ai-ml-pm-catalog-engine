from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path("/home/adien-i7-remote/workspace/fsa_bridge_ml_feasibility")
STINT1_ROOT = PROJECT_ROOT / "stint-1-evidence-ground-truth"
STINT2_ROOT = PROJECT_ROOT / "stint-2-target-ml-prototyping"
SOURCE = (
    STINT1_ROOT
    / "phase_1_lexical/outputs/canonical_vocabulary/external_failure_vocabulary_v1.csv"
)
OUT = STINT2_ROOT / "g2_baseline_models/outputs/g20_corpus_native_domain_vocab"
SOURCE_RELATIVE = (
    "../stint-1-evidence-ground-truth/phase_1_lexical/outputs/"
    "canonical_vocabulary/external_failure_vocabulary_v1.csv"
)

REVIEW_TERMS = [
    "bearing failure",
    "main bearing failure",
    "crack",
    "cracking",
    "casting",
    "hub casting",
]


def stable_id(value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]
    return f"G20C-REF-{digest}"


def joined(values: pd.Series) -> str:
    return "|".join(sorted({str(value) for value in values if pd.notna(value)}))


def support_record(
    term: str,
    rows: pd.DataFrame,
    match_type: str,
    construction_method: str,
    semantic_scope: str,
) -> dict[str, object]:
    if rows.empty:
        raise RuntimeError(f"No frozen reference support found for admitted term: {term}")
    if rows["vocabulary_owner"].str.contains("SAP", case=False, na=False).any():
        raise RuntimeError(f"SAP-derived support is forbidden for external term: {term}")
    return {
        "reference_entry_id": stable_id(term),
        "reference_term": term,
        "target": "unassigned",
        "reference_target": joined(rows["target"]),
        "reference_source": joined(rows["vocabulary_owner"]),
        "reference_source_row_ids": joined(rows["concept_id"]),
        "reference_concept_keys": joined(rows["canonical_concept_key"]),
        "source_artifact": SOURCE_RELATIVE,
        "evidence_type": "reference_evidence",
        "anchor_source": "domain_vocabulary",
        "construction_method": construction_method,
        "reference_match_type": match_type,
        "semantic_scope": semantic_scope,
        "evaluation_text_used": False,
        "eligible_for_step2_reference_coverage": True,
        "eligible_for_frequency_filter": False,
        "eligible_for_denominator_promotion": False,
        "prototype_seed_used": False,
        "raw_operational_values_emitted": False,
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    source = pd.read_csv(SOURCE).fillna("")
    required = {
        "concept_id",
        "canonical_concept",
        "canonical_concept_key",
        "vocabulary_owner",
        "target",
        "evidence_type",
    }
    missing = required - set(source.columns)
    if missing:
        raise RuntimeError(f"Missing source columns: {sorted(missing)}")

    canonical = source["canonical_concept"].astype(str).str.strip().str.lower()
    bearing = source[canonical.eq("bearing failure")].copy()
    crack_family = source[
        canonical.str.contains(r"\bcrack(?:s|ing)?\b", regex=True, na=False)
    ].copy()

    augmentation = pd.DataFrame(
        [
            support_record(
                "bearing failure",
                bearing,
                "exact_external_reference_term",
                "external_reference_import_not_corpus_extracted",
                "failure event; source scope remains generator-specific",
            ),
            support_record(
                "crack",
                crack_family,
                "morphological_family_from_external_reference_terms",
                "analyst_derived_lexical_variant_from_external_reference",
                "damage mechanism; retain subsystem constraints during grouping",
            ),
            support_record(
                "cracking",
                crack_family,
                "morphological_family_from_external_reference_terms",
                "analyst_derived_lexical_variant_from_external_reference",
                "damage mechanism; retain subsystem constraints during grouping",
            ),
        ]
    ).sort_values("reference_term")

    admitted = set(augmentation["reference_term"])
    decisions = []
    held_reasons = {
        "main bearing failure": (
            "No exact frozen F1c2 term. Main-bearing scope and bearing-failure "
            "evidence exist separately; composition was not promoted automatically."
        ),
        "casting": "No frozen F1c2/NREL/subsystem reference term was found.",
        "hub casting": "No frozen F1c2/NREL/subsystem reference term was found.",
    }
    for term in REVIEW_TERMS:
        is_admitted = term in admitted
        decisions.append(
            {
                "review_term": term,
                "decision": "admitted_reference_augmentation" if is_admitted else "held",
                "reason": (
                    "Frozen external reference support verified; kept outside the "
                    "corpus-native pool."
                    if is_admitted
                    else held_reasons[term]
                ),
                "evaluation_set_modified": False,
                "evaluation_text_used": False,
                "eligible_for_frequency_filter": False,
            }
        )
    decisions_frame = pd.DataFrame(decisions)

    if set(augmentation["reference_term"]) != {"bearing failure", "crack", "cracking"}:
        raise RuntimeError("Unexpected admitted reference augmentation terms")
    if augmentation["evaluation_text_used"].any():
        raise RuntimeError("Evaluation text must never support reference augmentation")
    if augmentation["eligible_for_frequency_filter"].any():
        raise RuntimeError("External reference terms must not enter corpus frequency filters")

    augmentation.to_csv(
        OUT / "g20c_external_reference_augmentation_sanitized.csv",
        index=False,
        lineterminator="\n",
    )
    decisions_frame.to_csv(
        OUT / "g20c_external_reference_augmentation_decisions_sanitized.csv",
        index=False,
        lineterminator="\n",
    )

    memo = """# G2.0c External Reference Augmentation

## Purpose

Preserve externally supported domain signal that disappeared from the model-eligible
B2 construction corpus because every observed occurrence was excluded with the
evaluation set. The evaluation set is unchanged and none of its text is used.

## Admitted

- `bearing failure`: exact term in the frozen F1c2 external vocabulary.
- `crack` and `cracking`: morphological variants backed by the frozen crack-family
  reference terms. Their subsystem constraints remain active during grouping.

All admitted rows carry `evidence_type=reference_evidence` and
`anchor_source=domain_vocabulary`. They are a separate reference layer, not
corpus-native terms, and never contribute to frequency thresholds.

## Held

- `main bearing failure`: main-bearing scope and bearing-failure evidence exist, but
  the exact compound is absent from the frozen reference vocabulary.
- `casting` and `hub casting`: no frozen F1c2/NREL/subsystem term was found.

Held terms are documented but not added. This avoids silently turning compositional
inference or committee recollection into documentary provenance.

## Step 2 Rules

- Filter corpus-native terms with path-specific frequency thresholds.
- Keep this external reference layer outside the reduction curve and term-frequency
  statistics.
- Permit it only as external coverage evidence during semantic grouping.
- Do not perform additional B2 recovery, touch the evaluation set, promote a
  denominator, map to SAP, or re-run G2.0 in this pass.
"""
    (OUT / "g20c_external_reference_augmentation_memo.md").write_text(
        memo, encoding="utf-8"
    )

    print(
        {
            "reviewed_terms": len(REVIEW_TERMS),
            "admitted_terms": len(augmentation),
            "held_terms": len(REVIEW_TERMS) - len(augmentation),
            "evaluation_set_modified": False,
        }
    )


if __name__ == "__main__":
    main()
