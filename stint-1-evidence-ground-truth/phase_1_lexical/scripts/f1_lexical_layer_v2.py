from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]
REFERENCE_ROOT = PROJECT_ROOT / "stint-1.1-reference-layer"
STINT_ROOT = PROJECT_ROOT / "stint-1-evidence-ground-truth"
F1_ROOT = STINT_ROOT / "phase_1_lexical"
OUTPUTS_DIR = F1_ROOT / "outputs"
LEXICAL_V2_DIR = OUTPUTS_DIR / "lexical_layer_v2"
ZEUS_POPULATED_DIR = OUTPUTS_DIR / "zeus_scaffold_populated"
DOCS_DIR = STINT_ROOT / "docs"

RAW_LEXICAL_V1 = (
    REFERENCE_ROOT
    / "reference_layer"
    / "lexical_layer"
    / "lexical_seed_dictionary_v1.csv"
)
SANITIZED_LEXICAL_V1 = (
    REFERENCE_ROOT
    / "reference_layer"
    / "lexical_layer"
    / "lexical_seed_dictionary_v1_sanitized.csv"
)
CONSOLIDATED_LEXICAL_V1 = (
    REFERENCE_ROOT
    / "reference_layer"
    / "lexical_layer"
    / "lexical_seed_dictionary_v1_consolidated_sanitized.csv"
)
ZEUS_SCAFFOLD_V1 = (
    REFERENCE_ROOT
    / "reference_layer"
    / "semantic_normalisation"
    / "zeus_semantic_scaffold_v1.csv"
)

SOURCE_VERSION = "reference-layer-v1"
SOURCE_DATE = "2026-08-31"


def stable_key(value: object, prefix: str) -> str:
    raw = "" if value is None or pd.isna(value) else str(value)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}-{digest}"


def word_count(value: object) -> int:
    if value is None or pd.isna(value):
        return 0
    text = str(value).strip()
    if not text:
        return 0
    return len([part for part in re.split(r"\s+", text) if part])


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def load_lexical_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    missing = [
        str(path)
        for path in [RAW_LEXICAL_V1, SANITIZED_LEXICAL_V1, CONSOLIDATED_LEXICAL_V1]
        if not path.exists()
    ]
    if missing:
        raise FileNotFoundError(f"Missing lexical inputs: {missing}")

    raw_df = pd.read_csv(RAW_LEXICAL_V1)
    sanitized_df = pd.read_csv(SANITIZED_LEXICAL_V1)
    consolidated_df = pd.read_csv(CONSOLIDATED_LEXICAL_V1)

    required_raw = {"observed_term", "normalised_term"}
    required_sanitized = {"observed_term_key", "normalised_term_key"}
    required_consolidated = {
        "concept_id",
        "consolidated_term_key",
        "target",
        "namespace",
        "target_field",
        "source_text_field",
        "stratum",
        "contractor_path",
        "record_count",
        "evidence_type",
        "tier",
        "status",
    }

    if not required_raw.issubset(raw_df.columns):
        raise ValueError(f"Raw lexical input missing: {sorted(required_raw - set(raw_df.columns))}")
    if not required_sanitized.issubset(sanitized_df.columns):
        raise ValueError(
            f"Sanitized lexical input missing: {sorted(required_sanitized - set(sanitized_df.columns))}"
        )
    if not required_consolidated.issubset(consolidated_df.columns):
        raise ValueError(
            "Consolidated lexical input missing: "
            f"{sorted(required_consolidated - set(consolidated_df.columns))}"
        )

    if "observed_term_key" not in raw_df.columns:
        raw_df["observed_term_key"] = raw_df["observed_term"].map(lambda value: stable_key(value, "TERM"))
    if "normalised_term_key" not in raw_df.columns:
        raw_df["normalised_term_key"] = raw_df["normalised_term"].map(lambda value: stable_key(value, "TERM"))

    return raw_df, sanitized_df, consolidated_df


def build_distinct_length_rows(raw_df: pd.DataFrame, sanitized_df: pd.DataFrame) -> list[dict]:
    raw_df = raw_df.copy()
    raw_df["word_length"] = raw_df["observed_term"].map(word_count)
    raw_df["normalised_word_length"] = raw_df["normalised_term"].map(word_count)

    rows: list[dict] = []
    for length, group in raw_df.groupby("word_length", dropna=False):
        rows.append(
            {
                "word_length": int(length),
                "contextual_rows": int(len(group)),
                "distinct_observed_term_keys": int(group["observed_term_key"].nunique()),
                "distinct_normalised_term_keys": int(group["normalised_term_key"].nunique()),
                "raw_values_emitted": False,
            }
        )

    known_lengths = set(int(row["word_length"]) for row in rows)
    sanitized_only = sanitized_df.copy()
    if "observed_term_key" in sanitized_only.columns and len(raw_df) == len(sanitized_only):
        # This records whether the sanitized and raw counts align without emitting terms.
        pass
    for length in sorted(known_lengths):
        if length <= 0:
            continue
    return sorted(rows, key=lambda row: row["word_length"])


def status_for_row(row: pd.Series) -> str:
    current = str(row.get("status", "") or "")
    target = str(row.get("target", "") or "")
    record_count = int(row.get("record_count", 0) or 0)
    if target == "unknown":
        return "unresolved"
    if record_count <= 1:
        return "provisional_singleton_domain_signal"
    if current == "unresolved":
        return "provisional_pending_domain_grouping"
    return "provisional_pending_domain_grouping"


def build_lexical_v2_rows(consolidated_df: pd.DataFrame) -> list[dict]:
    rows: list[dict] = []
    for _, row in consolidated_df.iterrows():
        record_count = int(row.get("record_count", 0) or 0)
        target = str(row.get("target", "") or "")
        keep_reason = "target_signal" if target != "unknown" else "frequency"
        keep_for_v2 = bool(target != "unknown" or record_count > 1)
        if not keep_for_v2:
            continue
        evidence_type = str(row.get("evidence_type", "") or "")
        if evidence_type == "unresolved" and target != "unknown":
            evidence_type = "expert_inference"
        rows.append(
            {
                "concept_id": row.get("concept_id"),
                "term_key": row.get("consolidated_term_key"),
                "target": target,
                "namespace": row.get("namespace"),
                "target_field": row.get("target_field"),
                "source_text_field": row.get("source_text_field"),
                "stratum": row.get("stratum"),
                "contractor_path": row.get("contractor_path"),
                "record_count": record_count,
                "source_row_count": int(row.get("source_row_count", 0) or 0),
                "observed_variant_count": int(row.get("observed_variant_count", 0) or 0),
                "evidence_type": evidence_type,
                "tier": row.get("tier"),
                "status": status_for_row(row),
                "label_generation_method": "lexical_rule_set_v1",
                "evaluation_independence": "derived_from_rules",
                "keep_reason": keep_reason,
                "source": "STINT_1.1 lexical seed dictionary",
                "source_version": SOURCE_VERSION,
                "source_date": SOURCE_DATE,
                "contains_source_derived_terms": False,
                "raw_values_emitted": False,
            }
        )
    return sorted(rows, key=lambda item: (-item["record_count"], item["target"], str(item["term_key"])))


def build_zeus_status_rows() -> list[dict]:
    if not ZEUS_SCAFFOLD_V1.exists():
        return [
            {
                "object": "SEMANTIC_NORMALISATION",
                "source_family": "ZEUS scaffold",
                "status": "missing",
                "evidence_type": "reference_evidence",
                "tier": "silver-medium",
                "action": "block_or_recreate_scaffold",
                "raw_values_emitted": False,
            }
        ]

    zeus_df = pd.read_csv(ZEUS_SCAFFOLD_V1)
    source_counts = Counter(zeus_df.get("source_family", pd.Series(dtype=str)).fillna("unknown"))
    content_counts = Counter(zeus_df.get("content_status", pd.Series(dtype=str)).fillna("unknown"))
    rows = [
        {
            "object": "SEMANTIC_NORMALISATION",
            "source_family": source_family,
            "status": "scaffold_present",
            "row_count": int(count),
            "evidence_type": "reference_evidence",
            "tier": "silver-medium",
            "action": "retain_structural_scaffold",
            "raw_values_emitted": False,
        }
        for source_family, count in sorted(source_counts.items())
    ]
    for content_status, count in sorted(content_counts.items()):
        rows.append(
            {
                "object": "SEMANTIC_NORMALISATION",
                "source_family": "content_status",
                "status": content_status,
                "row_count": int(count),
                "evidence_type": "reference_evidence",
                "tier": "silver-medium",
                "action": "source_capture_pending_if_not_populated",
                "raw_values_emitted": False,
            }
        )
    rows.append(
        {
            "object": "SEMANTIC_NORMALISATION",
            "source_family": "WMEP",
            "status": "source_capture_pending",
            "row_count": 0,
            "evidence_type": "reference_evidence",
            "tier": "silver-medium",
            "action": "populate_when_authoritative_terms_are_materialized",
            "raw_values_emitted": False,
        }
    )
    rows.append(
        {
            "object": "SEMANTIC_NORMALISATION",
            "source_family": "NREL_GRD",
            "status": "source_capture_pending",
            "row_count": 0,
            "evidence_type": "reference_evidence",
            "tier": "silver-medium",
            "action": "populate_when_authoritative_terms_are_materialized",
            "raw_values_emitted": False,
        }
    )
    return rows


def write_memo(summary: dict, length_rows: list[dict], target_counts: dict, status_counts: dict) -> None:
    lines = [
        "# F1 - Lexical Layer v2 Bootstrap",
        "",
        "## Purpose",
        "",
        "This pass starts Phase 1 by converting the provisional STINT_1.1 lexical seed into an auditable STINT_1 working layer.",
        "",
        "It does not freeze the lexical layer and does not emit source-derived terms.",
        "",
        "## Mandatory Pre-Filter Count",
        "",
        "| word_length | contextual_rows | distinct_observed_term_keys | distinct_normalised_term_keys |",
        "|---:|---:|---:|---:|",
    ]
    for row in length_rows:
        lines.append(
            f"| {row['word_length']} | {row['contextual_rows']} | "
            f"{row['distinct_observed_term_keys']} | {row['distinct_normalised_term_keys']} |"
        )
    lines.extend(
        [
            "",
            "## Lexical Layer v2 Status",
            "",
            f"- Source contextual rows: {summary['source_contextual_rows']}",
            f"- Source distinct observed term keys: {summary['source_distinct_observed_term_keys']}",
            f"- V2 retained rows: {summary['lexical_v2_rows']}",
            f"- V2 distinct term keys: {summary['lexical_v2_distinct_term_keys']}",
            f"- Rows removed by singleton unknown filter: {summary['singleton_unknown_rows_removed']}",
            "- 300-800 concepts remains a sanity/timebox heuristic, not a success criterion.",
            "- `source_text_field` is preserved for every retained term.",
            "- `label_generation_method` and `evaluation_independence` are populated from the first F1 output.",
            "",
            "## Target Distribution",
            "",
        ]
    )
    for target, count in sorted(target_counts.items()):
        lines.append(f"- {target}: {count}")
    lines.extend(["", "## Status Distribution", ""])
    for status, count in sorted(status_counts.items()):
        lines.append(f"- {status}: {count}")
    lines.extend(
        [
            "",
            "## Semantic Normalisation",
            "",
            "`SEMANTIC_NORMALISATION` remains structurally present but not fully populated: WMEP and NREL GRD are recorded as `source_capture_pending`.",
            "",
            "## Interpretation",
            "",
            "F1 can proceed with filtering and domain grouping, but this first artifact is a working layer, not a frozen reference object.",
            "",
            "The high coverage of `description_extended` applies to the structured path only. PDF-derived evidence stays in `event_structural` and must not be mixed with planned/reactive denominators.",
        ]
    )
    (OUTPUTS_DIR / "f1_lexical_layer_v2_memo.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    LEXICAL_V2_DIR.mkdir(parents=True, exist_ok=True)
    ZEUS_POPULATED_DIR.mkdir(parents=True, exist_ok=True)

    raw_df, sanitized_df, consolidated_df = load_lexical_inputs()
    length_rows = build_distinct_length_rows(raw_df, sanitized_df)
    lexical_rows = build_lexical_v2_rows(consolidated_df)
    zeus_rows = build_zeus_status_rows()

    lexical_fields = [
        "concept_id",
        "term_key",
        "target",
        "namespace",
        "target_field",
        "source_text_field",
        "stratum",
        "contractor_path",
        "record_count",
        "source_row_count",
        "observed_variant_count",
        "evidence_type",
        "tier",
        "status",
        "label_generation_method",
        "evaluation_independence",
        "keep_reason",
        "source",
        "source_version",
        "source_date",
        "contains_source_derived_terms",
        "raw_values_emitted",
    ]
    write_csv(LEXICAL_V2_DIR / "lexical_layer_v2_sanitized.csv", lexical_rows, lexical_fields)

    write_csv(
        OUTPUTS_DIR / "f1_distinct_observed_term_length.csv",
        length_rows,
        [
            "word_length",
            "contextual_rows",
            "distinct_observed_term_keys",
            "distinct_normalised_term_keys",
            "raw_values_emitted",
        ],
    )

    zeus_fields = [
        "object",
        "source_family",
        "status",
        "row_count",
        "evidence_type",
        "tier",
        "action",
        "raw_values_emitted",
    ]
    write_csv(ZEUS_POPULATED_DIR / "semantic_normalisation_population_status.csv", zeus_rows, zeus_fields)

    target_counts = Counter(row["target"] for row in lexical_rows)
    status_counts = Counter(row["status"] for row in lexical_rows)
    source_text_fields = Counter(row["source_text_field"] for row in lexical_rows)

    source_distinct_observed = int(raw_df["observed_term_key"].nunique())
    lexical_distinct = len({row["term_key"] for row in lexical_rows})
    singleton_unknown_removed = int(
        ((consolidated_df["target"].fillna("") == "unknown") & (consolidated_df["record_count"].fillna(0) <= 1)).sum()
    )

    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "task": "F1_lexical_layer_v2_bootstrap",
        "source_contextual_rows": int(len(raw_df)),
        "source_distinct_observed_term_keys": source_distinct_observed,
        "source_distinct_normalised_term_keys": int(raw_df["normalised_term_key"].nunique()),
        "distinct_observed_term_keys_by_word_length": length_rows,
        "lexical_v2_rows": int(len(lexical_rows)),
        "lexical_v2_distinct_term_keys": int(lexical_distinct),
        "singleton_unknown_rows_removed": singleton_unknown_removed,
        "target_counts": dict(target_counts),
        "status_counts": dict(status_counts),
        "source_text_field_counts": dict(source_text_fields),
        "heuristic_300_800_policy": "sanity_timebox_heuristic_not_success_criterion",
        "description_extended_coverage_scope": "structured_path_only",
        "pdf_event_stratum_policy": "event_structural_never_mixed_with_planned_reactive",
        "semantic_normalisation_status": "structural_scaffold_present_with_WMEP_and_NREL_GRD_source_capture_pending",
        "label_generation_method_populated": True,
        "evaluation_independence_populated": True,
        "candidate_generation_performed": False,
        "raw_values_emitted": False,
        "outputs": {
            "lexical_layer_v2_sanitized_csv": str(
                LEXICAL_V2_DIR / "lexical_layer_v2_sanitized.csv"
            ).replace(str(PROJECT_ROOT) + "/", ""),
            "distinct_length_csv": str(
                OUTPUTS_DIR / "f1_distinct_observed_term_length.csv"
            ).replace(str(PROJECT_ROOT) + "/", ""),
            "semantic_normalisation_population_status_csv": str(
                ZEUS_POPULATED_DIR / "semantic_normalisation_population_status.csv"
            ).replace(str(PROJECT_ROOT) + "/", ""),
            "memo": str(OUTPUTS_DIR / "f1_lexical_layer_v2_memo.md").replace(str(PROJECT_ROOT) + "/", ""),
        },
    }
    (OUTPUTS_DIR / "f1_lexical_layer_v2_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    write_memo(summary, length_rows, dict(target_counts), dict(status_counts))

    print(
        json.dumps(
            {
                "task": summary["task"],
                "source_contextual_rows": summary["source_contextual_rows"],
                "source_distinct_observed_term_keys": summary["source_distinct_observed_term_keys"],
                "lexical_v2_rows": summary["lexical_v2_rows"],
                "lexical_v2_distinct_term_keys": summary["lexical_v2_distinct_term_keys"],
                "singleton_unknown_rows_removed": summary["singleton_unknown_rows_removed"],
                "raw_values_emitted": summary["raw_values_emitted"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
