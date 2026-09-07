from __future__ import annotations

import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path("/home/adien-i7-remote/workspace/fsa_bridge_ml_feasibility")
F5_OUTPUT = PROJECT_ROOT / "stint-1-evidence-ground-truth/phase_5_symptom/outputs/f51_symptom_thread_resolution"
B25_EVIDENCE = (
    PROJECT_ROOT
    / "stint-1-evidence-ground-truth/phase_4_path_b_xlsx/outputs/b25_grouping_refinement/b25_grouped_reanchored_evidence_sanitized.csv"
)
LEXICAL_HIGH = (
    PROJECT_ROOT
    / "stint-1-evidence-ground-truth/phase_1_lexical/outputs/lexical_layer_v2/lexical_layer_v2_high_confidence_candidates_sanitized.csv"
)

RAW_PATTERNS = [
    re.compile(r"contractor_path_001", re.I),
    re.compile(r"site_path_001", re.I),
    re.compile(r"site_path_002", re.I),
    re.compile(r"site_path_003", re.I),
    re.compile(r"site_path_004", re.I),
    re.compile(r"client_entity", re.I),
    re.compile(r"oem_entity_001", re.I),
    re.compile(r"\bge\b", re.I),
    re.compile(r"/home/adien", re.I),
    re.compile(r"data/interim/extracted_source", re.I),
]


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def assert_sanitized(paths: list[Path]) -> None:
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="ignore")
        hits = [pattern.pattern for pattern in RAW_PATTERNS if pattern.search(text)]
        if hits:
            raise RuntimeError(f"Sanitization failed for {path.name}: {hits}")


def classify_concept(row: pd.Series) -> tuple[str, str]:
    owner = str(row.get("vocabulary_owner", ""))
    semantic_level = str(row.get("semantic_level", ""))
    # Only externally attested symptom/effect vocabularies are condition-like
    # enough to survive this thread. SAP/catalog anchors can still be useful
    # later, but they do not confirm an observed symptom source in B2.
    if owner == "WMEP_EFFECTS" or "effect" in semantic_level.lower() or "symptom" in semantic_level.lower():
        return (
            "observed_condition_like_requires_blind_review",
            "Concept is aligned with effect/symptom semantics, but B2 source field remains unconfirmed.",
        )
    return (
        "generic_or_unusable_for_symptom_thread",
        "Concept is not specific enough to confirm observed pre-intervention symptom evidence.",
    )


def main() -> None:
    F5_OUTPUT.mkdir(parents=True, exist_ok=True)
    evidence = pd.read_csv(B25_EVIDENCE)
    lexical = pd.read_csv(LEXICAL_HIGH)
    symptom = evidence[evidence["target"].eq("Symptom")].copy()
    lexical_meta = (
        lexical[lexical["target"].eq("Symptom")]
        [
            [
                "canonical_concept_id",
                "canonical_concept_key",
                "vocabulary_owner",
                "subsystem",
                "semantic_level",
                "match_method",
                "match_text_source",
                "match_threshold",
                "embedding_model",
            ]
        ]
        .drop_duplicates()
    )
    grouped = (
        symptom.groupby(["concept_id", "canonical_concept_key"], dropna=False)
        .agg(
            evidence_rows=("record_id", "size"),
            refined_event_units=("refined_event_key", "nunique"),
            persistence_clusters=("physical_record_id", "nunique"),
            term_keys=("term_key", "nunique"),
            doc_types=("doc_type", lambda s: ",".join(sorted({str(v) for v in s}))),
            families=("family", lambda s: ",".join(sorted({str(v) for v in s}))),
        )
        .reset_index()
        .merge(
            lexical_meta,
            left_on=["concept_id", "canonical_concept_key"],
            right_on=["canonical_concept_id", "canonical_concept_key"],
            how="left",
        )
        .drop_duplicates(subset=["concept_id", "canonical_concept_key"])
        .sort_values(["refined_event_units", "evidence_rows"], ascending=False)
    )
    rows: list[dict[str, Any]] = []
    for item in grouped.itertuples(index=False):
        row = pd.Series(item._asdict())
        verdict, rationale = classify_concept(row)
        rows.append(
            {
                "thread": "B2_symptom_like_6_concepts",
                "concept_id": str(row["concept_id"]),
                "canonical_concept_key": str(row["canonical_concept_key"]),
                "vocabulary_owner": str(row.get("vocabulary_owner", "")),
                "semantic_level": str(row.get("semantic_level", "")),
                "evidence_rows": int(row["evidence_rows"]),
                "refined_event_units": int(row["refined_event_units"]),
                "persistence_clusters": int(row["persistence_clusters"]),
                "term_keys": int(row["term_keys"]),
                "doc_types": str(row["doc_types"]),
                "families": str(row["families"]),
                "f51a_verdict": verdict,
                "review_required": verdict == "observed_condition_like_requires_blind_review",
                "promotion_status": "not_promoted_source_unconfirmed",
                "rationale": rationale,
                "raw_operational_values_emitted": False,
            }
        )

    review_candidates = [row for row in rows if row["review_required"]]
    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "pass_id": "F5.1a",
        "task_type": "b2_symptom_concept_thread_resolution",
        "source_pass": "B2.5",
        "symptom_concepts_evaluated": len(rows),
        "symptom_evidence_rows": int(symptom.shape[0]),
        "symptom_refined_event_units": int(symptom["refined_event_key"].nunique()),
        "observed_condition_like_concepts": len(review_candidates),
        "generic_or_unusable_concepts": len(rows) - len(review_candidates),
        "blind_review_needed": bool(review_candidates),
        "blind_review_event_sample_size": min(20, sum(int(row["refined_event_units"]) for row in review_candidates)),
        "thread_verdict": "pending_blind_review" if review_candidates else "discard_thread_as_generic_noise",
        "promotion_status": "not_promoted_source_unconfirmed",
        "contractual_denominator_supported": False,
        "proxy_denominator_supported_now": False,
        "raw_operational_values_emitted": False,
        "outputs": [
            "f51a_b2_symptom_concepts_memo.md",
            "f51a_b2_symptom_concepts_sanitized.csv",
            "f51a_b2_symptom_concepts_summary_sanitized.json",
        ],
    }

    write_csv(
        F5_OUTPUT / "f51a_b2_symptom_concepts_sanitized.csv",
        rows,
        [
            "thread",
            "concept_id",
            "canonical_concept_key",
            "vocabulary_owner",
            "semantic_level",
            "evidence_rows",
            "refined_event_units",
            "persistence_clusters",
            "term_keys",
            "doc_types",
            "families",
            "f51a_verdict",
            "review_required",
            "promotion_status",
            "rationale",
            "raw_operational_values_emitted",
        ],
    )
    (F5_OUTPUT / "f51a_b2_symptom_concepts_summary_sanitized.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    table_rows = [
        f"| {row['concept_id']} | {row['vocabulary_owner']} | {row['semantic_level']} | {row['evidence_rows']} | {row['refined_event_units']} | {row['term_keys']} | {row['f51a_verdict']} |"
        for row in rows
    ]
    memo = "\n".join(
        [
            "# F5.1a B2 Symptom Concept Thread",
            "",
            "## Scope",
            "",
            "This pass resolves the B2 Symptom-like thread at concept level. It uses B2.5 grouped snapshot candidates and emits only sanitized concept identifiers and counts.",
            "",
            "## Summary",
            "",
            f"- Symptom concepts evaluated: `{summary['symptom_concepts_evaluated']}`",
            f"- Symptom evidence rows: `{summary['symptom_evidence_rows']}`",
            f"- Symptom refined event units: `{summary['symptom_refined_event_units']}`",
            f"- Observed-condition-like concepts: `{summary['observed_condition_like_concepts']}`",
            f"- Generic/unusable concepts: `{summary['generic_or_unusable_concepts']}`",
            f"- Blind review needed: `{summary['blind_review_needed']}`",
            f"- Blind review event sample size: `{summary['blind_review_event_sample_size']}`",
            f"- Thread verdict: `{summary['thread_verdict']}`",
            "",
            "## Concept-Level Verdict",
            "",
            "| concept_id | vocabulary_owner | semantic_level | evidence_rows | refined_event_units | term_keys | f51a_verdict |",
            "| --- | --- | --- | ---: | ---: | ---: | --- |",
            *table_rows,
            "",
            "## Interpretation",
            "",
            "F5.1a does not promote Symptom. It only decides whether the concentrated B2 six-concept thread is worth blind review.",
            "",
            "Any concept classified as condition-like remains `source_unconfirmed`; only a blind review of events can determine whether it reflects an observed pre-intervention symptom or post/status wording.",
            "",
            "raw_operational_values_emitted: false",
            "",
        ]
    )
    (F5_OUTPUT / "f51a_b2_symptom_concepts_memo.md").write_text(memo, encoding="utf-8")
    assert_sanitized(list(F5_OUTPUT.glob("f51a_*")))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
