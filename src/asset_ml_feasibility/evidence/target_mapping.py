from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
REPORTS_DIR = PROJECT_ROOT / "reports"
INTERNAL_REPORTS_DIR = REPORTS_DIR / "internal"
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
INTERNAL_ARTIFACTS_DIR = ARTIFACTS_DIR / "internal"

SCHEMA_PROFILE_PATH = INTERNAL_REPORTS_DIR / "schema_profile.csv"
STRUCTURAL_SCAN_PATH = INTERNAL_REPORTS_DIR / "basic_structural_scan.csv"
VOCABULARY_OVERLAP_PATH = INTERNAL_REPORTS_DIR / "vocabulary_column_overlap.csv"
CATALOG_VOCABULARY_PATH = INTERNAL_REPORTS_DIR / "catalog_vocabulary_terms.csv"

INTERNAL_TARGET_MAPPING_PATH = INTERNAL_REPORTS_DIR / "preliminary_target_mapping.csv"
SANITIZED_TARGET_MAPPING_PATH = REPORTS_DIR / "preliminary_target_mapping_sanitized.csv"
INTERNAL_SUMMARY_PATH = INTERNAL_ARTIFACTS_DIR / "preliminary_target_mapping_summary.json"
SANITIZED_SUMMARY_PATH = ARTIFACTS_DIR / "preliminary_target_mapping_summary_sanitized.json"

TARGET_ORDER = [
    "Symptom",
    "Object Part",
    "Damage",
    "Cause",
    "Activity",
    "FLOC leaf segment",
    "Activity Type",
]

TARGET_STATUS_DEFAULTS = {
    "Symptom": "requires_explicit_proof_of_life_review",
    "Object Part": "requires_long_tail_mapping_validation",
    "Damage": "requires_record_level_label_validation",
    "Cause": "requires_record_level_label_validation",
    "Activity": "requires_runtime_and_mapping_validation",
    "FLOC leaf segment": "requires_separate_floc_glossary_runtime_validation",
    "Activity Type": "pending_ge_mat_controlled_source",
}

TARGET_HEADER_ANCHORS = {
    "Symptom": {"symptom", "complaint", "problem"},
    "Object Part": {"objectpart", "object part", "part", "component", "assembly"},
    "Damage": {"damage", "fault", "failure", "defect"},
    "Cause": {"cause", "reason", "rootcause", "root cause"},
    "Activity": {"activity", "action", "repair", "operation", "work"},
    "FLOC leaf segment": {"floc", "functional location", "kks", "segment"},
    "Activity Type": {"activitytype", "activity type", "mat"},
}


def vocabulary_status_for_target(target: str, loaded_vocab_targets: set[str]) -> str:
    if target == "Activity Type":
        return "pending_ge_mat_controlled_source"
    if target == "FLOC leaf segment":
        return "requires_floc_glossary_or_runtime_feature_validation"
    if target in loaded_vocab_targets:
        return "loaded"
    return "not_loaded_requires_separate_source"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="ignore")).hexdigest()[:16]


def read_csv_if_present(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def as_bool(value: Any) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def select_source_schema(schema: pd.DataFrame) -> pd.DataFrame:
    if schema.empty:
        return schema
    selected = schema.copy()
    selected = selected[selected["likely_role"].fillna("") == "source_data"]
    if "is_placeholder_column" in selected.columns:
        selected = selected[~selected["is_placeholder_column"].map(as_bool)]
    return selected


def infer_anchor_targets(normalized_column_name: str) -> list[str]:
    value = str(normalized_column_name or "").replace("_", " ").lower()
    targets: list[str] = []
    for target in TARGET_ORDER:
        if any(anchor in value for anchor in TARGET_HEADER_ANCHORS[target]):
            targets.append(target)
    return targets


def build_sheet_context(schema: pd.DataFrame) -> dict[tuple[str, str], dict[str, Any]]:
    context: dict[tuple[str, str], dict[str, Any]] = {}
    for _, row in schema.iterrows():
        path_hash = str(row.get("path_hash", ""))
        sheet_hash = str(row.get("sheet_hash", ""))
        key = (path_hash, sheet_hash)
        item = context.setdefault(
            key,
            {
                "text_column_hashes": set(),
                "code_column_hashes": set(),
                "catalog_signal_hashes": set(),
                "candidate_column_count": 0,
                "relative_path": row.get("relative_path", ""),
                "file_name": row.get("file_name", ""),
                "sheet_name": row.get("sheet_name", ""),
            },
        )
        item["candidate_column_count"] += 1
        column_hash = str(row.get("column_hash", stable_hash(str(row.get("column_name", "")))))
        if as_bool(row.get("is_candidate_text")):
            item["text_column_hashes"].add(column_hash)
        if as_bool(row.get("is_candidate_id_or_code")):
            item["code_column_hashes"].add(column_hash)
        if as_bool(row.get("is_catalog_signal")):
            item["catalog_signal_hashes"].add(column_hash)
    return context


def derive_rows(
    schema: pd.DataFrame,
    structural: pd.DataFrame,
    overlap: pd.DataFrame,
    vocabulary: pd.DataFrame,
) -> list[dict[str, Any]]:
    source_schema = select_source_schema(schema)
    sheet_context = build_sheet_context(source_schema)
    loaded_vocab_targets = set(vocabulary.get("target", pd.Series(dtype=str)).dropna().astype(str).unique())

    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str]] = set()

    def add_row(
        *,
        target: str,
        signal_type: str,
        source_row: pd.Series,
        evidence_strength: str,
        overlap_rate: float | None = None,
    ) -> None:
        path_hash = str(source_row.get("path_hash", ""))
        sheet_hash = str(source_row.get("sheet_hash", ""))
        column_hash = str(source_row.get("column_hash", ""))
        dedupe_key = (target, signal_type, path_hash, column_hash)
        if dedupe_key in seen:
            return
        seen.add(dedupe_key)
        context = sheet_context.get((path_hash, sheet_hash), {})
        has_text_and_code_context = bool(context.get("text_column_hashes")) and bool(context.get("code_column_hashes"))
        vocabulary_status = vocabulary_status_for_target(target, loaded_vocab_targets)

        rows.append(
            {
                "target": target,
                "mapping_signal_type": signal_type,
                "evidence_stage": "preliminary_catalog_target_mapping",
                "evidence_strength": evidence_strength,
                "vocabulary_status": vocabulary_status,
                "target_status": TARGET_STATUS_DEFAULTS[target],
                "path_hash": path_hash,
                "sheet_hash": sheet_hash,
                "column_hash": column_hash,
                "likely_role": source_row.get("likely_role", ""),
                "data_family": source_row.get("data_family", ""),
                "runtime_likelihood": source_row.get("runtime_likelihood", ""),
                "candidate_bucket": source_row.get("candidate_bucket", ""),
                "has_text_and_code_context": has_text_and_code_context,
                "sheet_text_candidate_count": len(context.get("text_column_hashes", set())),
                "sheet_code_candidate_count": len(context.get("code_column_hashes", set())),
                "sheet_catalog_signal_count": len(context.get("catalog_signal_hashes", set())),
                "overlap_rate": overlap_rate if overlap_rate is not None else "",
                "pair_discovery_ready": has_text_and_code_context,
                "can_support_measurement": False,
                "needs_runtime_validation": True,
                "needs_label_validation": True,
                "raw_operational_values_emitted": False,
                "relative_path": source_row.get("relative_path", ""),
                "file_name": source_row.get("file_name", ""),
                "sheet_name": source_row.get("sheet_name", ""),
                "column_name": source_row.get("column_name", ""),
                "normalized_column_name": source_row.get("normalized_column_name", ""),
            }
        )

    if not overlap.empty:
        for _, row in overlap.iterrows():
            target = str(row.get("target", ""))
            if target not in TARGET_ORDER:
                continue
            if not as_bool(row.get("passes_discovery_threshold_0_10")):
                continue
            add_row(
                target=target,
                signal_type="catalog_or_anchor_overlap",
                source_row=row,
                evidence_strength="metadata_header_signal",
                overlap_rate=float(row.get("overlap_rate", 0.0) or 0.0),
            )

    for _, row in source_schema.iterrows():
        normalized_name = str(row.get("normalized_column_name", ""))
        anchor_targets = infer_anchor_targets(normalized_name)
        if not anchor_targets:
            continue
        for target in anchor_targets:
            add_row(
                target=target,
                signal_type="target_header_anchor",
                source_row=row,
                evidence_strength="metadata_header_signal",
            )

    # Add sheet-level readiness rows for sheets that contain both text and code-like columns,
    # without assigning them to a target unless a target-specific signal is present elsewhere.
    mapped_sheet_keys = {(row["target"], row["path_hash"], row["sheet_hash"]) for row in rows}
    for (path_hash, sheet_hash), context in sheet_context.items():
        if not context.get("text_column_hashes") or not context.get("code_column_hashes"):
            continue
        for target in TARGET_ORDER:
            if (target, path_hash, sheet_hash) not in mapped_sheet_keys:
                continue
            rows.append(
                {
                    "target": target,
                    "mapping_signal_type": "text_code_sheet_context",
                    "evidence_stage": "preliminary_catalog_target_mapping",
                    "evidence_strength": "sheet_level_pair_discovery_readiness",
                    "vocabulary_status": vocabulary_status_for_target(target, loaded_vocab_targets),
                    "target_status": TARGET_STATUS_DEFAULTS[target],
                    "path_hash": path_hash,
                    "sheet_hash": sheet_hash,
                    "column_hash": "",
                    "likely_role": "source_data",
                    "data_family": "",
                    "runtime_likelihood": "potential_runtime_or_source_signal",
                    "candidate_bucket": "",
                    "has_text_and_code_context": True,
                    "sheet_text_candidate_count": len(context.get("text_column_hashes", set())),
                    "sheet_code_candidate_count": len(context.get("code_column_hashes", set())),
                    "sheet_catalog_signal_count": len(context.get("catalog_signal_hashes", set())),
                    "overlap_rate": "",
                    "pair_discovery_ready": True,
                    "can_support_measurement": False,
                    "needs_runtime_validation": True,
                    "needs_label_validation": True,
                    "raw_operational_values_emitted": False,
                    "relative_path": context.get("relative_path", ""),
                    "file_name": context.get("file_name", ""),
                    "sheet_name": context.get("sheet_name", ""),
                    "column_name": "",
                    "normalized_column_name": "",
                }
            )

    return rows


def sanitize_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    safe_keys = [
        "target",
        "mapping_signal_type",
        "evidence_stage",
        "evidence_strength",
        "vocabulary_status",
        "target_status",
        "path_hash",
        "sheet_hash",
        "column_hash",
        "likely_role",
        "data_family",
        "runtime_likelihood",
        "candidate_bucket",
        "has_text_and_code_context",
        "sheet_text_candidate_count",
        "sheet_code_candidate_count",
        "sheet_catalog_signal_count",
        "overlap_rate",
        "pair_discovery_ready",
        "can_support_measurement",
        "needs_runtime_validation",
        "needs_label_validation",
        "raw_operational_values_emitted",
    ]
    return [{key: row.get(key, "") for key in safe_keys} for row in rows]


def count_by(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counter = Counter(str(row.get(key, "")) for row in rows)
    return dict(sorted(counter.items()))


def target_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counter = Counter(str(row.get("target", "")) for row in rows)
    return {target: counter.get(target, 0) for target in TARGET_ORDER}


def distinct_counts_by_target(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    values: dict[str, set[str]] = {target: set() for target in TARGET_ORDER}
    for row in rows:
        target = str(row.get("target", ""))
        value = str(row.get(key, ""))
        if target in values and value:
            values[target].add(value)
    return {target: len(values[target]) for target in TARGET_ORDER}


def run_preliminary_target_mapping() -> dict[str, Any]:
    schema = read_csv_if_present(SCHEMA_PROFILE_PATH)
    structural = read_csv_if_present(STRUCTURAL_SCAN_PATH)
    overlap = read_csv_if_present(VOCABULARY_OVERLAP_PATH)
    vocabulary = read_csv_if_present(CATALOG_VOCABULARY_PATH)

    rows = derive_rows(schema, structural, overlap, vocabulary)
    sanitized_rows = sanitize_rows(rows)

    write_csv(INTERNAL_TARGET_MAPPING_PATH, rows)
    write_csv(SANITIZED_TARGET_MAPPING_PATH, sanitized_rows)

    source_schema = select_source_schema(schema)
    loaded_vocab_targets = sorted(set(vocabulary.get("target", pd.Series(dtype=str)).dropna().astype(str).unique()))
    targets_without_loaded_vocabulary = [target for target in TARGET_ORDER if target not in loaded_vocab_targets]

    summary = {
        "created_at_utc": now_utc(),
        "input_schema_columns": int(len(schema)),
        "input_structural_rows": int(len(structural)),
        "input_overlap_rows": int(len(overlap)),
        "input_catalog_terms": int(len(vocabulary)),
        "source_schema_columns_evaluated": int(len(source_schema)),
        "source_sheets_evaluated": int(source_schema[["path_hash", "sheet_hash"]].drop_duplicates().shape[0])
        if not source_schema.empty
        else 0,
        "preliminary_mapping_rows": int(len(rows)),
        "measurement_ready_rows": 0,
        "pair_discovery_ready_rows": int(sum(bool(row.get("pair_discovery_ready")) for row in rows)),
        "target_mapping_rows_by_target": target_counts(rows),
        "distinct_sheets_by_target": distinct_counts_by_target(rows, "sheet_hash"),
        "distinct_columns_by_target": distinct_counts_by_target(rows, "column_hash"),
        "mapping_signal_type_counts": count_by(rows, "mapping_signal_type"),
        "vocabulary_status_counts": count_by(rows, "vocabulary_status"),
        "targets_without_loaded_vocabulary": targets_without_loaded_vocabulary,
        "settings": {
            "method_scope": "preliminary_catalog_target_mapping_from_schema_profile_and_vocabulary_overlap",
            "content_values_scanned": False,
            "row_level_pair_validation_performed": False,
            "not_ground_truth": True,
            "not_model_threshold": True,
            "not_endpoint_classify_threshold": True,
        },
        "outputs": {
            "internal_target_mapping_csv": "reports/internal/preliminary_target_mapping.csv",
            "sanitized_target_mapping_csv": "reports/preliminary_target_mapping_sanitized.csv",
            "internal_summary_json": "artifacts/internal/preliminary_target_mapping_summary.json",
            "sanitized_summary_json": "artifacts/preliminary_target_mapping_summary_sanitized.json",
        },
        "raw_operational_values_emitted": False,
    }

    INTERNAL_SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    SANITIZED_SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    INTERNAL_SUMMARY_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    SANITIZED_SUMMARY_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
