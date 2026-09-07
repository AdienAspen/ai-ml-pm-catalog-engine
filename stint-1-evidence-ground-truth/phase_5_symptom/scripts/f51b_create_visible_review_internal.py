from __future__ import annotations

import csv
import hashlib
import json
import os
import re
from collections.abc import Mapping
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path("/home/adien-i7-remote/workspace/fsa_bridge_ml_feasibility")
F5_OUTPUT = PROJECT_ROOT / "stint-1-evidence-ground-truth/phase_5_symptom/outputs/f51_symptom_thread_resolution"
INTERNAL_DIR = PROJECT_ROOT / "reports/internal/f51b_reason_blind_review_visible"
INTERNAL_MANIFEST = (
    PROJECT_ROOT
    / "reports/internal/f40b_contractor_path_001_relational_model/f40b_contractor_path_001_entity_manifest_internal.csv"
)

ENTITY = "api_service_v1_service-orders"
CONTRACTOR_PATH = "CONTRACTOR_PATH_001"


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


def redact_pii(text: str) -> str:
    value = text
    value = re.sub(r"https?://\S+|www\.\S+", "<URL>", value, flags=re.I)
    value = re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", "<EMAIL>", value)
    value = re.sub(r"\+?\b(?:\d[\s()./-]*){8,}\b", "<NUMBER>", value)
    value = re.sub(r"\b(?:badge|employee|emp|phone|mobile|cell|email)\s*[:#-]?\s*[A-Za-z0-9._%+-]+\b", "<PII_REF>", value, flags=re.I)
    return re.sub(r"\s+", " ", value).strip()


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    os.chmod(path, 0o600)


def main() -> None:
    packet = pd.read_csv(F5_OUTPUT / "f51b_reason_blind_review_packet_sanitized.csv")
    wanted = {str(v) for v in packet["reason_value_hash"].dropna()}
    records = load_json_records(service_orders_path())
    raw_by_hash: dict[str, str] = {}
    for record in records:
        reason = as_text(record.get("reason"))
        if not reason:
            continue
        reason_hash = prefixed_hash(reason.lower(), "REASON", 12)
        if reason_hash in wanted and reason_hash not in raw_by_hash:
            raw_by_hash[reason_hash] = redact_pii(reason)

    rows = []
    for row in packet.itertuples(index=False):
        reason_hash = str(row.reason_value_hash)
        rows.append(
            {
                "blind_review_id": str(row.blind_review_id),
                "reason_hash": reason_hash,
                "reason_text_pii_redacted": raw_by_hash.get(reason_hash, "<NOT_FOUND>"),
                "reviewer_response": "",
                "allowed_response": "observed_condition | dispatch_motive | ambiguous | not_interpretable",
                "reviewer_notes": "",
            }
        )

    response_rows = [
        {
            "reason_hash": row["reason_hash"],
            "reviewer_response": "",
            "allowed_response": row["allowed_response"],
            "reviewer_notes": "",
        }
        for row in rows
    ]

    write_csv(
        INTERNAL_DIR / "f51b_reason_blind_review_visible_internal.csv",
        rows,
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
        INTERNAL_DIR / "f51b_reason_blind_review_responses_only_template.csv",
        response_rows,
        ["reason_hash", "reviewer_response", "allowed_response", "reviewer_notes"],
    )
    summary = {
        "pass_id": "F5.1b-visible-internal",
        "visible_internal_file": str(INTERNAL_DIR / "f51b_reason_blind_review_visible_internal.csv"),
        "responses_only_template": str(INTERNAL_DIR / "f51b_reason_blind_review_responses_only_template.csv"),
        "rows": len(rows),
        "missing_raw_reason_rows": sum(row["reason_text_pii_redacted"] == "<NOT_FOUND>" for row in rows),
        "git_policy": "reports/internal/* is ignored; do not commit this file",
        "pipeline_proposal_shown": False,
        "semantic_flags_shown": False,
        "pii_redacted": True,
    }
    (INTERNAL_DIR / "f51b_reason_blind_review_visible_internal_summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    os.chmod(INTERNAL_DIR / "f51b_reason_blind_review_visible_internal_summary.json", 0o600)
    print(json.dumps({k: v for k, v in summary.items() if k != "visible_internal_file" and k != "responses_only_template"}, indent=2))


if __name__ == "__main__":
    main()
