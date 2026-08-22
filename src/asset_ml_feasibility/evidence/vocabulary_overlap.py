from __future__ import annotations

import csv
import hashlib
import json
import re
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
VOCABULARY_PATH = INTERNAL_REPORTS_DIR / "catalog_vocabulary_terms.csv"

INTERNAL_OVERLAP_PATH = INTERNAL_REPORTS_DIR / "vocabulary_column_overlap.csv"
SANITIZED_OVERLAP_PATH = REPORTS_DIR / "vocabulary_column_overlap_sanitized.csv"
INTERNAL_SUMMARY_PATH = INTERNAL_ARTIFACTS_DIR / "vocabulary_column_overlap_summary.json"
SANITIZED_SUMMARY_PATH = ARTIFACTS_DIR / "vocabulary_column_overlap_summary_sanitized.json"

DISCOVERY_THRESHOLD = 0.10
HIGH_SPECIFICITY_THRESHOLD = 0.20

GENERIC_TERMS = {
    "activity",
    "asset",
    "catalog",
    "code",
    "comment",
    "date",
    "desc",
    "description",
    "event",
    "field",
    "group",
    "id",
    "item",
    "long",
    "name",
    "note",
    "notes",
    "notification",
    "number",
    "order",
    "plant",
    "record",
    "report",
    "short",
    "site",
    "status",
    "system",
    "text",
    "time",
    "type",
    "value",
}

TARGET_ANCHOR_TOKENS = {
    "Symptom": {"symptom", "problem", "complaint"},
    "Object Part": {"objectpart", "component", "part", "assembly", "subassembly"},
    "Damage": {"damage", "fault", "failure", "defect"},
    "Cause": {"cause", "reason", "rootcause"},
    "Activity": {"activity", "action", "repair", "work", "operation"},
    "FLOC leaf segment": {"floc", "kks", "functional", "location", "segment"},
    "Activity Type": {"activitytype", "mat"},
}

TARGET_ORDER = [
    "Symptom",
    "Object Part",
    "Damage",
    "Cause",
    "Activity",
    "FLOC leaf segment",
    "Activity Type",
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="ignore")).hexdigest()[:16]


def normalize_text(value: Any) -> str:
    value = "" if value is None else str(value)
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def tokenize(value: Any) -> set[str]:
    normalized = normalize_text(value)
    tokens = {token for token in normalized.split() if len(token) >= 2}
    return tokens


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames: list[str] = []
    for row in rows:
        for key in row.keys():
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def read_required_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Required input not found: {path}")
    if path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path)


def build_target_vocabulary_tokens(vocabulary: pd.DataFrame) -> dict[str, set[str]]:
    target_tokens: dict[str, set[str]] = {}
    if vocabulary.empty:
        return target_tokens

    for target, group in vocabulary.groupby("target", dropna=False):
        if not isinstance(target, str) or not target:
            continue
        tokens: set[str] = set()
        for column in ["catalog", "code_group", "code", "official_description", "normalized_description"]:
            if column not in group.columns:
                continue
            for value in group[column].dropna().astype(str):
                tokens.update(tokenize(value))
        target_tokens[target] = tokens - GENERIC_TERMS
    for target, anchors in TARGET_ANCHOR_TOKENS.items():
        target_tokens.setdefault(target, set()).update(anchors)
    return target_tokens


def select_schema_candidates(schema: pd.DataFrame) -> pd.DataFrame:
    if schema.empty:
        return schema
    selected = schema.copy()
    selected = selected[selected["likely_role"].fillna("") == "source_data"]
    selected = selected[selected["is_placeholder_column"].fillna(False).astype(str).str.lower() != "true"]

    candidate_flags = [
        "is_candidate_text",
        "is_candidate_id_or_code",
        "is_catalog_signal",
    ]
    mask = pd.Series(False, index=selected.index)
    for flag in candidate_flags:
        if flag in selected.columns:
            mask = mask | (selected[flag].fillna(False).astype(str).str.lower() == "true")

    if "candidate_bucket" in selected.columns:
        mask = mask | (selected["candidate_bucket"].fillna("other") != "other")

    return selected[mask].copy()


def score_column_against_targets(schema_candidates: pd.DataFrame, target_tokens: dict[str, set[str]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for _, column_row in schema_candidates.iterrows():
        column_name = str(column_row.get("column_name", ""))
        normalized_column_name = str(column_row.get("normalized_column_name", column_name))
        column_tokens = tokenize(normalized_column_name) - GENERIC_TERMS
        if not column_tokens:
            continue

        for target in TARGET_ORDER:
            vocab_tokens = target_tokens.get(target, set())
            if not vocab_tokens:
                continue
            matched_tokens = column_tokens.intersection(vocab_tokens)
            matched_token_count = len(matched_tokens)
            matched_anchor_count = len(matched_tokens.intersection(TARGET_ANCHOR_TOKENS.get(target, set())))
            column_token_count = len(column_tokens)
            overlap_rate = matched_token_count / column_token_count if column_token_count else 0.0
            if matched_token_count == 0:
                continue

            relative_path = str(column_row.get("relative_path", ""))
            file_name = str(column_row.get("file_name", ""))
            sheet_name = str(column_row.get("sheet_name", ""))
            row = {
                "target": target,
                "relative_path": relative_path,
                "file_name": file_name,
                "sheet_name": sheet_name,
                "column_name": column_name,
                "path_hash": column_row.get("path_hash", stable_hash(relative_path)),
                "sheet_hash": column_row.get("sheet_hash", stable_hash(f"{relative_path}|{sheet_name}")),
                "column_hash": column_row.get("column_hash", stable_hash(f"{relative_path}|{sheet_name}|{column_name}")),
                "likely_role": column_row.get("likely_role", ""),
                "data_family": column_row.get("data_family", ""),
                "runtime_likelihood": column_row.get("runtime_likelihood", ""),
                "candidate_bucket": column_row.get("candidate_bucket", ""),
                "matched_token_count": matched_token_count,
                "matched_anchor_token_count": matched_anchor_count,
                "column_token_count": column_token_count,
                "overlap_rate": round(overlap_rate, 6),
                "passes_discovery_threshold_0_10": overlap_rate >= DISCOVERY_THRESHOLD,
                "passes_high_specificity_threshold_0_20": overlap_rate >= HIGH_SPECIFICITY_THRESHOLD,
                "raw_operational_values_emitted": False,
            }
            rows.append(row)
    return rows


def count_matches(rows: list[dict[str, Any]], flag: str) -> dict[str, int]:
    counts = Counter()
    for row in rows:
        if bool(row.get(flag)):
            counts[str(row["target"])] += 1
    return {target: counts.get(target, 0) for target in TARGET_ORDER}


def distinct_column_counts(rows: list[dict[str, Any]], flag: str) -> dict[str, int]:
    seen: dict[str, set[str]] = {target: set() for target in TARGET_ORDER}
    for row in rows:
        if bool(row.get(flag)):
            seen[str(row["target"])].add(str(row["column_hash"]))
    return {target: len(seen[target]) for target in TARGET_ORDER}


def sanitize_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    safe_keys = [
        "target",
        "path_hash",
        "sheet_hash",
        "column_hash",
        "likely_role",
        "data_family",
        "runtime_likelihood",
        "candidate_bucket",
        "matched_token_count",
        "matched_anchor_token_count",
        "column_token_count",
        "overlap_rate",
        "passes_discovery_threshold_0_10",
        "passes_high_specificity_threshold_0_20",
        "raw_operational_values_emitted",
    ]
    return [{key: row.get(key, "") for key in safe_keys} for row in rows]


def run_vocabulary_column_overlap() -> dict[str, Any]:
    schema = read_required_csv(SCHEMA_PROFILE_PATH)
    vocabulary = read_required_csv(VOCABULARY_PATH)
    target_tokens = build_target_vocabulary_tokens(vocabulary)
    schema_candidates = select_schema_candidates(schema)
    rows = score_column_against_targets(schema_candidates, target_tokens)
    sanitized_rows = sanitize_rows(rows)

    write_csv(INTERNAL_OVERLAP_PATH, rows)
    write_csv(SANITIZED_OVERLAP_PATH, sanitized_rows)

    summary = {
        "created_at_utc": now_utc(),
        "input_schema_columns": int(len(schema)),
        "input_catalog_terms": int(len(vocabulary)),
        "schema_candidate_columns_evaluated": int(len(schema_candidates)),
        "overlap_rows": int(len(rows)),
        "distinct_columns_with_any_overlap": int(len({str(row["column_hash"]) for row in rows})),
        "settings": {
            "discovery_threshold": DISCOVERY_THRESHOLD,
            "high_specificity_threshold": HIGH_SPECIFICITY_THRESHOLD,
            "generic_terms_excluded": True,
            "target_header_anchors_enabled": True,
            "method_scope": "metadata_header_level_vocabulary_overlap_only",
            "not_model_threshold": True,
            "not_endpoint_classify_threshold": True,
        },
        "match_rows_by_target_at_0_10": count_matches(rows, "passes_discovery_threshold_0_10"),
        "distinct_columns_by_target_at_0_10": distinct_column_counts(rows, "passes_discovery_threshold_0_10"),
        "match_rows_by_target_at_0_20": count_matches(rows, "passes_high_specificity_threshold_0_20"),
        "distinct_columns_by_target_at_0_20": distinct_column_counts(rows, "passes_high_specificity_threshold_0_20"),
        "targets_without_loaded_vocabulary": [
            target for target in TARGET_ORDER if target not in set(vocabulary.get("target", pd.Series(dtype=str)).dropna())
        ],
        "outputs": {
            "internal_overlap_csv": "reports/internal/vocabulary_column_overlap.csv",
            "sanitized_overlap_csv": "reports/vocabulary_column_overlap_sanitized.csv",
            "internal_summary_json": "artifacts/internal/vocabulary_column_overlap_summary.json",
            "sanitized_summary_json": "artifacts/vocabulary_column_overlap_summary_sanitized.json",
        },
        "raw_operational_values_emitted": False,
    }

    INTERNAL_SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    SANITIZED_SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    INTERNAL_SUMMARY_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    SANITIZED_SUMMARY_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
