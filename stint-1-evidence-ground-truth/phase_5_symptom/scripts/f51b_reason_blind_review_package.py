from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path("/home/adien-i7-remote/workspace/fsa_bridge_ml_feasibility")
OUTPUT_DIR = PROJECT_ROOT / "stint-1-evidence-ground-truth/phase_5_symptom/outputs/f51_symptom_thread_resolution"
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

SYMPTOM_LIKE_CUES = {
    "noise",
    "vibration",
    "overheat",
    "temperature",
    "reduced",
    "low",
    "high",
    "warning",
    "stoppage",
    "overspeed",
}


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


def cue_present(text: str, cues: set[str]) -> bool:
    lowered = text.lower()
    return any(cue in lowered for cue in cues)


def redacted_shape(text: str) -> str:
    tokens = re.findall(r"[A-Za-z]+|\d+|[^\w\s]", text)
    shaped = []
    for token in tokens[:18]:
        if token.isalpha():
            shaped.append(f"<alpha:{len(token)}>")
        elif token.isdigit():
            shaped.append(f"<num:{len(token)}>")
        else:
            shaped.append(token)
    if len(tokens) > 18:
        shaped.append("...")
    return " ".join(shaped)


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


def choose_blind_sample(records: list[dict[str, object]], n: int = 20) -> list[dict[str, object]]:
    candidates = []
    for idx, record in enumerate(records):
        reason = as_text(record.get("reason"))
        if not reason or not cue_present(reason, SYMPTOM_LIKE_CUES):
            continue
        candidates.append(
            {
                "physical_record_id": physical_record_id(record, idx),
                "reason_value_hash": prefixed_hash(reason.lower(), "REASON", 12),
                "word_count": word_count(reason),
                "language_bucket": language_bucket(reason),
                "redacted_example_shape": redacted_shape(reason),
                "raw_reason": reason,
            }
        )
    # Deterministic diversity: unique reason hash, sorted by hash.
    seen = set()
    unique = []
    for row in sorted(candidates, key=lambda item: (item["reason_value_hash"], item["physical_record_id"])):
        if row["reason_value_hash"] in seen:
            continue
        seen.add(row["reason_value_hash"])
        unique.append(row)
    if len(unique) <= n:
        selected = unique
    else:
        step = max(1, len(unique) // n)
        selected = unique[::step][:n]
    for i, row in enumerate(selected, start=1):
        row["blind_review_id"] = f"F51B-REASON-{i:03d}"
    return selected


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


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    records = load_json_records(service_orders_path())
    reason_values = [as_text(record.get("reason")) for record in records]
    non_empty = [value for value in reason_values if value]
    symptom_like = [value for value in non_empty if cue_present(value, SYMPTOM_LIKE_CUES)]
    sample = choose_blind_sample(records, 20)

    review_rows = [
        {
            "blind_review_id": row["blind_review_id"],
            "reason_value_hash": row["reason_value_hash"],
            "word_count": row["word_count"],
            "language_bucket": row["language_bucket"],
            "redacted_example_shape": row["redacted_example_shape"],
            "review_question": "Does this describe an observed condition before intervention, an administrative/work motive, both, or unclear?",
            "allowed_response": "observed_pre_intervention_condition | administrative_or_work_motive | both | unclear",
            "reviewer_response": "",
            "reviewer_confidence": "",
            "review_notes": "",
            "raw_operational_values_emitted": False,
        }
        for row in sample
    ]
    internal_key_rows = [
        {
            "blind_review_id": row["blind_review_id"],
            "physical_record_id": row["physical_record_id"],
            "reason_value_hash": row["reason_value_hash"],
            "raw_operational_values_emitted": False,
        }
        for row in sample
    ]

    summary = {
        "created_at_utc": utc_now(),
        "pass_id": "F5.1b",
        "task_type": "reason_blind_review_package",
        "records_evaluated": len(records),
        "reason_non_empty_rows": len(non_empty),
        "symptom_like_cue_rows": len(symptom_like),
        "distinct_symptom_like_reason_hashes": len({prefixed_hash(value.lower(), "REASON", 12) for value in symptom_like}),
        "blind_review_rows_prepared": len(review_rows),
        "blind_review_design": "blind_no_pipeline_proposal_or_semantic_flags",
        "thread_status": "awaiting_blind_review_responses",
        "contractual_denominator_supported": False,
        "proxy_denominator_supported_now": False,
        "raw_operational_values_emitted": False,
        "outputs": [
            "f51b_reason_blind_review_memo.md",
            "f51b_reason_blind_review_packet_sanitized.csv",
            "f51b_reason_blind_review_response_template_sanitized.csv",
            "f51b_reason_blind_review_summary_sanitized.json",
        ],
        "internal_outputs_ignored": [
            "f51b_reason_blind_review_internal_key.csv",
        ],
    }

    write_csv(
        OUTPUT_DIR / "f51b_reason_blind_review_packet_sanitized.csv",
        review_rows,
        [
            "blind_review_id",
            "reason_value_hash",
            "word_count",
            "language_bucket",
            "redacted_example_shape",
            "review_question",
            "allowed_response",
            "reviewer_response",
            "reviewer_confidence",
            "review_notes",
            "raw_operational_values_emitted",
        ],
    )
    write_csv(
        OUTPUT_DIR / "f51b_reason_blind_review_response_template_sanitized.csv",
        review_rows,
        [
            "blind_review_id",
            "review_question",
            "allowed_response",
            "reviewer_response",
            "reviewer_confidence",
            "review_notes",
            "raw_operational_values_emitted",
        ],
    )
    # No raw text is written. This key only links hashed review rows back to
    # physical records for later counting and should remain ignored/internal.
    write_csv(
        OUTPUT_DIR / "f51b_reason_blind_review_internal_key.csv",
        internal_key_rows,
        ["blind_review_id", "physical_record_id", "reason_value_hash", "raw_operational_values_emitted"],
    )
    (OUTPUT_DIR / "f51b_reason_blind_review_summary_sanitized.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    memo = "\n".join(
        [
            "# F5.1b Reason Blind Review Package",
            "",
            "## Scope",
            "",
            "This pass prepares a blind review packet for the `reason` Symptom thread. The reviewer receives no pipeline classification, no cue flags, and no proposed target label.",
            "",
            "## Summary",
            "",
            f"- Records evaluated: `{summary['records_evaluated']}`",
            f"- Non-empty `reason` rows: `{summary['reason_non_empty_rows']}`",
            f"- Symptom-like cue rows: `{summary['symptom_like_cue_rows']}`",
            f"- Distinct symptom-like reason hashes: `{summary['distinct_symptom_like_reason_hashes']}`",
            f"- Blind review rows prepared: `{summary['blind_review_rows_prepared']}`",
            f"- Thread status: `{summary['thread_status']}`",
            "",
            "## Review Question",
            "",
            "`Does this describe an observed condition before intervention, an administrative/work motive, both, or unclear?`",
            "",
            "Allowed responses: `observed_pre_intervention_condition`, `administrative_or_work_motive`, `both`, `unclear`.",
            "",
            "## Interpretation",
            "",
            "F5.1b does not decide the `reason` thread. It creates the independent review design needed to avoid anchoring bias.",
            "",
            "Rows confirmed blindly as observed pre-intervention condition would become the first genuinely independent Symptom evidence candidates. Until reviewed, no denominator is supported.",
            "",
            "raw_operational_values_emitted: false",
            "",
        ]
    )
    (OUTPUT_DIR / "f51b_reason_blind_review_memo.md").write_text(memo, encoding="utf-8")
    assert_sanitized(
        [
            OUTPUT_DIR / "f51b_reason_blind_review_memo.md",
            OUTPUT_DIR / "f51b_reason_blind_review_packet_sanitized.csv",
            OUTPUT_DIR / "f51b_reason_blind_review_response_template_sanitized.csv",
            OUTPUT_DIR / "f51b_reason_blind_review_summary_sanitized.json",
        ]
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
