from __future__ import annotations

import csv
import hashlib
import json
import os
import re
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path("/home/adien-i7-remote/workspace/fsa_bridge_ml_feasibility")
F5_OUTPUT = PROJECT_ROOT / "stint-1-evidence-ground-truth/phase_5_symptom/outputs/f51_symptom_thread_resolution"
INTERNAL_DIR = PROJECT_ROOT / "reports/internal/f51b2_reason_blind_review_unbiased"
INTERNAL_MANIFEST = (
    PROJECT_ROOT
    / "reports/internal/f40b_contractor_path_001_relational_model/f40b_contractor_path_001_entity_manifest_internal.csv"
)

ENTITY = "api_service_v1_service-orders"
CONTRACTOR_PATH = "CONTRACTOR_PATH_001"

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


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_hash(value: object, length: int = 16) -> str:
    raw = "" if value is None or pd.isna(value) else str(value)
    return hashlib.sha256(raw.encode("utf-8", errors="ignore")).hexdigest()[:length]


def prefixed_hash(value: object, prefix: str, length: int = 12) -> str:
    return f"{prefix}-{stable_hash(value, length)}"


def as_text(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def load_json_records(path: Path) -> list[dict[str, object]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, Mapping)]
    if isinstance(payload, Mapping):
        for key in ["data", "items", "value", "records", "results"]:
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, Mapping)]
        list_values = [value for value in payload.values() if isinstance(value, list)]
        if len(list_values) == 1:
            return [item for item in list_values[0] if isinstance(item, Mapping)]
    return []


def service_orders_path() -> Path:
    manifest = pd.read_csv(INTERNAL_MANIFEST)
    value = manifest.loc[manifest["entity_label"].eq(ENTITY), "json_path"].iloc[0]
    return Path(value)


def word_count(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9]+", text))


def redact_pii(text: str) -> str:
    value = text
    value = re.sub(r"https?://\S+|www\.\S+", "<URL>", value, flags=re.I)
    value = re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", "<EMAIL>", value)
    value = re.sub(r"\+?\b(?:\d[\s()./-]*){8,}\b", "<NUMBER>", value)
    value = re.sub(
        r"\b(?:badge|employee|emp|phone|mobile|cell|email)\s*[:#-]?\s*[A-Za-z0-9._%+-]+\b",
        "<PII_REF>",
        value,
        flags=re.I,
    )
    return re.sub(r"\s+", " ", value).strip()


def language_bucket(text: str) -> str:
    lowered = text.lower()
    english_hits = sum(cue in lowered for cue in ["the", "and", "for", "with", "repair", "maintenance"])
    spanish_hits = sum(cue in lowered for cue in ["para", "con", "por", "repar", "manten", "falla"])
    if english_hits and spanish_hits:
        return "mixed_or_ambiguous"
    if english_hits:
        return "english_like"
    if spanish_hits:
        return "spanish_like"
    return "undetermined"


def physical_record_id(record: Mapping[str, object], fallback_index: int) -> str:
    record_key = as_text(record.get("id")) or str(fallback_index)
    return prefixed_hash(f"{CONTRACTOR_PATH}|{ENTITY}|{record_key}", "PHY", 16)


def choose_unbiased_sample(records: list[dict[str, object]], n: int = 40) -> tuple[list[dict[str, object]], int]:
    unique: dict[str, dict[str, object]] = {}
    for idx, record in enumerate(records):
        reason = as_text(record.get("reason"))
        if not reason:
            continue
        reason_hash = prefixed_hash(reason.lower(), "REASON", 12)
        if reason_hash in unique:
            continue
        unique[reason_hash] = {
            "physical_record_id": physical_record_id(record, idx),
            "reason_hash": reason_hash,
            "reason_text_pii_redacted": redact_pii(reason),
            "word_count": word_count(reason),
            "language_bucket": language_bucket(reason),
            "selection_sort_key": stable_hash(f"F5.1b2.1|{reason_hash}", 16),
        }
    selected = sorted(unique.values(), key=lambda row: str(row["selection_sort_key"]))[:n]
    for i, row in enumerate(selected, start=1):
        row["blind_review_id"] = f"F51B2-REASON-{i:03d}"
    return selected, len(unique)


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    os.chmod(path, 0o600)


def assert_sanitized(paths: list[Path]) -> None:
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="ignore")
        hits = [pattern.pattern for pattern in RAW_PATTERNS if pattern.search(text)]
        if hits:
            raise RuntimeError(f"Sanitization failed for {path.name}: {hits}")


def main() -> None:
    INTERNAL_DIR.mkdir(parents=True, exist_ok=True)
    F5_OUTPUT.mkdir(parents=True, exist_ok=True)
    records = load_json_records(service_orders_path())
    reason_non_empty = [as_text(record.get("reason")) for record in records if as_text(record.get("reason"))]
    selected, distinct_reason_hashes = choose_unbiased_sample(records, 40)

    visible_rows = [
        {
            "blind_review_id": row["blind_review_id"],
            "reason_hash": row["reason_hash"],
            "reason_text_pii_redacted": row["reason_text_pii_redacted"],
            "reviewer_response": "",
            "allowed_response": "observed_condition | dispatch_motive | ambiguous | not_interpretable",
            "reviewer_notes": "",
        }
        for row in selected
    ]
    response_rows = [
        {
            "reason_hash": row["reason_hash"],
            "reviewer_response": "",
            "allowed_response": "observed_condition | dispatch_motive | ambiguous | not_interpretable",
            "reviewer_notes": "",
        }
        for row in selected
    ]
    internal_key_rows = [
        {
            "blind_review_id": row["blind_review_id"],
            "physical_record_id": row["physical_record_id"],
            "reason_hash": row["reason_hash"],
        }
        for row in selected
    ]

    visible_path = INTERNAL_DIR / "f51b2_reason_blind_review_unbiased_visible_internal.csv"
    responses_path = INTERNAL_DIR / "f51b2_reason_blind_review_unbiased_responses_only.csv"
    key_path = INTERNAL_DIR / "f51b2_reason_blind_review_unbiased_internal_key.csv"
    write_csv(
        visible_path,
        visible_rows,
        [
            "blind_review_id",
            "reason_hash",
            "reason_text_pii_redacted",
            "reviewer_response",
            "allowed_response",
            "reviewer_notes",
        ],
    )
    write_csv(
        responses_path,
        response_rows,
        ["reason_hash", "reviewer_response", "allowed_response", "reviewer_notes"],
    )
    write_csv(key_path, internal_key_rows, ["blind_review_id", "physical_record_id", "reason_hash"])

    summary = {
        "created_at_utc": utc_now(),
        "pass_id": "F5.1b2.1",
        "task_type": "unbiased_reason_blind_review_package",
        "records_evaluated": len(records),
        "reason_non_empty_rows": len(reason_non_empty),
        "distinct_reason_hashes": distinct_reason_hashes,
        "sample_rows": len(selected),
        "sample_basis": "complete_non_empty_reason_universe_no_cue_preselection",
        "reviewer_response_allowed_values": [
            "observed_condition",
            "dispatch_motive",
            "ambiguous",
            "not_interpretable",
        ],
        "visible_internal_file": str(visible_path),
        "responses_only_file": str(responses_path),
        "internal_key_file": str(key_path),
        "git_policy": "reports/internal/* is ignored; do not commit these files",
        "pipeline_proposal_shown": False,
        "semantic_flags_shown": False,
        "pii_redacted": True,
        "raw_operational_values_emitted_to_versioned_artifacts": False,
    }
    summary_path = INTERNAL_DIR / "f51b2_reason_blind_review_unbiased_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    os.chmod(summary_path, 0o600)

    public_summary = {
        key: value
        for key, value in summary.items()
        if key not in {"visible_internal_file", "responses_only_file", "internal_key_file"}
    }
    public_summary["internal_artifacts_location"] = "reports/internal/f51b2_reason_blind_review_unbiased/"
    public_path = F5_OUTPUT / "f51b2_reason_blind_review_unbiased_public_summary_sanitized.json"
    public_path.write_text(json.dumps(public_summary, indent=2), encoding="utf-8")
    assert_sanitized([public_path])
    print(json.dumps(public_summary, indent=2))


if __name__ == "__main__":
    main()
