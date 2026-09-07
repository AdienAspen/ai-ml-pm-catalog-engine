from __future__ import annotations

import csv
import hashlib
import json
import os
import re
from collections import Counter
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path("/home/adien-i7-remote/workspace/fsa_bridge_ml_feasibility")
F5_OUTPUT = PROJECT_ROOT / "stint-1-evidence-ground-truth/phase_5_symptom/outputs/f51_symptom_thread_resolution"
INTERNAL_DIR = PROJECT_ROOT / "reports/internal/f51b2_2f_residual_unique_and_oem_space"
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

OEM_STRICT_RE = re.compile(
    r"(?<![A-Za-z0-9])(?P<code>[A-Z]{0,4}\d{2,6}[A-Z]{0,4}|[A-Z]{2,8}\d{1,5})\s*[-:–]\s*(?P<desc>[A-Za-z][A-Za-z0-9 /_.,()]{4,})",
    re.I,
)
OEM_SPACE_RE = re.compile(
    r"(?<![A-Za-z0-9])(?P<code>\d{3,6})\s+(?P<desc>[A-Za-z][A-Za-z0-9/_.,()]{4,}(?:\s+[A-Za-z][A-Za-z0-9/_.,()]{1,}){0,5})",
    re.I,
)
CMS_RE = re.compile(
    r"\bCMS[_ -]?(?P<cms_id>[A-Za-z0-9]+)(?:[_ -](?P<date>\d{4}[-_]?\d{2}[-_]?\d{2}|\d{6,8}))?(?:[_ -](?P<seq>\d+))?\b(?P<trail>.{0,80})?\bSev(?:erity)?\s*[:# -]?\s*(?P<severity>\d+)\b",
    re.I,
)
DISPATCH_MOTIVE_PATTERNS = {
    "inspection": re.compile(r"\b(inspect(?:ion|ed)?|walkdown|visual check|site visit)\b", re.I),
    "upgrade_or_retrofit": re.compile(r"\b(upgrade|retrofit|campaign|bulletin|modification)\b", re.I),
    "testing_or_commissioning": re.compile(r"\b(test(?:ing)?|commission(?:ing)?|trial|calibration)\b", re.I),
    "planned_or_periodic": re.compile(r"\b(planned|scheduled|annual|monthly|quarterly|periodic|pm\b|preventive)\b", re.I),
    "administrative_or_logistics": re.compile(r"\b(admin(?:istrative)?|paperwork|logistic(?:s)?|permit|access|escort|meeting)\b", re.I),
    "adjustment_or_settings": re.compile(r"\b(adjust(?:ment|ed)?|setting(?:s)?|parameter(?:s)?|reset|software)\b", re.I),
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


def physical_record_id(record: Mapping[str, object], fallback_index: int) -> str:
    record_key = as_text(record.get("id")) or str(fallback_index)
    return prefixed_hash(f"{CONTRACTOR_PATH}|{ENTITY}|{record_key}", "PHY", 16)


def word_count(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9]+", text))


def dispatch_categories(text: str) -> list[str]:
    return [name for name, pattern in DISPATCH_MOTIVE_PATTERNS.items() if pattern.search(text)]


def is_strict_residual(text: str) -> bool:
    return not (OEM_STRICT_RE.search(text) or CMS_RE.search(text) or dispatch_categories(text))


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


def pct(count: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round(100 * count / denominator, 2)


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str], mode: int | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    if mode is not None:
        os.chmod(path, mode)


def assert_sanitized(paths: list[Path]) -> None:
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="ignore")
        hits = [pattern.pattern for pattern in RAW_PATTERNS if pattern.search(text)]
        if hits:
            raise RuntimeError(f"Sanitization failed for {path.name}: {hits}")


def main() -> None:
    F5_OUTPUT.mkdir(parents=True, exist_ok=True)
    INTERNAL_DIR.mkdir(parents=True, exist_ok=True)
    records = load_json_records(service_orders_path())

    reason_rows = []
    for idx, record in enumerate(records):
        reason = as_text(record.get("reason"))
        if not reason:
            continue
        strict_oem = bool(OEM_STRICT_RE.search(reason))
        space_oem = bool(OEM_SPACE_RE.search(reason))
        cms = bool(CMS_RE.search(reason))
        dispatch = bool(dispatch_categories(reason))
        strict_residual = not (strict_oem or cms or dispatch)
        expanded_residual = not (strict_oem or space_oem or cms or dispatch)
        reason_rows.append(
            {
                "physical_record_id": physical_record_id(record, idx),
                "reason_hash": prefixed_hash(reason.lower(), "REASON", 12),
                "reason": reason,
                "strict_oem": strict_oem,
                "space_oem": space_oem,
                "cms": cms,
                "dispatch": dispatch,
                "strict_residual": strict_residual,
                "expanded_residual": expanded_residual,
            }
        )

    total_non_empty = len(reason_rows)
    strict_residual_rows = [row for row in reason_rows if row["strict_residual"]]
    recovered_oem_space_rows = [row for row in strict_residual_rows if row["space_oem"]]
    expanded_residual_rows = [row for row in reason_rows if row["expanded_residual"]]

    unique_strict_residual: dict[str, dict[str, Any]] = {}
    for row in strict_residual_rows:
        unique_strict_residual.setdefault(str(row["reason_hash"]), row)

    unique_sample = sorted(
        unique_strict_residual.values(),
        key=lambda row: stable_hash(f"F5.1b2.2f|{row['reason_hash']}", 16),
    )[:40]
    for i, row in enumerate(unique_sample, start=1):
        row["blind_review_id"] = f"F51B2-RESIDU-{i:03d}"

    visible_rows = [
        {
            "blind_review_id": row["blind_review_id"],
            "reason_hash": row["reason_hash"],
            "reason_text_pii_redacted": redact_pii(str(row["reason"])),
            "reviewer_response": "",
            "allowed_response": "observed_condition | dispatch_motive | ambiguous | not_interpretable",
            "reviewer_notes": "",
        }
        for row in unique_sample
    ]
    response_rows = [
        {
            "reason_hash": row["reason_hash"],
            "reviewer_response": "",
            "allowed_response": "observed_condition | dispatch_motive | ambiguous | not_interpretable",
            "reviewer_notes": "",
        }
        for row in unique_sample
    ]

    profile_rows = [
        {
            "profile_metric": "reason_non_empty_rows",
            "row_count": total_non_empty,
            "pct_of_reason_non_empty": 100.0,
            "raw_operational_values_emitted": False,
        },
        {
            "profile_metric": "strict_residual_rows_before_oem_space",
            "row_count": len(strict_residual_rows),
            "pct_of_reason_non_empty": pct(len(strict_residual_rows), total_non_empty),
            "raw_operational_values_emitted": False,
        },
        {
            "profile_metric": "strict_residual_distinct_reason_hashes",
            "row_count": len(unique_strict_residual),
            "pct_of_reason_non_empty": pct(len(unique_strict_residual), total_non_empty),
            "raw_operational_values_emitted": False,
        },
        {
            "profile_metric": "oem_space_rows_recovered_from_strict_residual",
            "row_count": len(recovered_oem_space_rows),
            "pct_of_reason_non_empty": pct(len(recovered_oem_space_rows), total_non_empty),
            "raw_operational_values_emitted": False,
        },
        {
            "profile_metric": "residual_rows_after_oem_space_expansion",
            "row_count": len(expanded_residual_rows),
            "pct_of_reason_non_empty": pct(len(expanded_residual_rows), total_non_empty),
            "raw_operational_values_emitted": False,
        },
        {
            "profile_metric": "unique_blind_sample_rows_prepared",
            "row_count": len(visible_rows),
            "pct_of_reason_non_empty": pct(len(visible_rows), total_non_empty),
            "raw_operational_values_emitted": False,
        },
    ]

    code_desc_counts = Counter()
    code_distinct_desc: dict[str, set[str]] = {}
    for row in recovered_oem_space_rows:
        match = OEM_SPACE_RE.search(str(row["reason"]))
        if not match:
            continue
        code_hash = prefixed_hash(match.group("code"), "OEMCODE", 10)
        desc_hash = prefixed_hash(match.group("desc").lower(), "OEMDESC", 10)
        code_desc_counts[(code_hash, desc_hash)] += 1
        code_distinct_desc.setdefault(code_hash, set()).add(desc_hash)

    oem_rows = []
    for (code_hash, desc_hash), count in code_desc_counts.most_common():
        oem_rows.append(
            {
                "code_hash": code_hash,
                "description_hash": desc_hash,
                "row_count": count,
                "code_distinct_description_hashes": len(code_distinct_desc[code_hash]),
                "assume_one_to_one_mapping": False,
                "raw_operational_values_emitted": False,
            }
        )

    summary = {
        "created_at_utc": utc_now(),
        "pass_id": "F5.1b2.2f",
        "task_type": "residual_unique_sample_and_oem_space_pattern_expansion",
        "reason_non_empty_rows": total_non_empty,
        "strict_residual_rows_before_oem_space": len(strict_residual_rows),
        "strict_residual_distinct_reason_hashes": len(unique_strict_residual),
        "oem_space_rows_recovered_from_strict_residual": len(recovered_oem_space_rows),
        "residual_rows_after_oem_space_expansion": len(expanded_residual_rows),
        "unique_blind_sample_rows_prepared": len(visible_rows),
        "sample_basis": "distinct_reason_hashes_from_strict_residual_one_row_per_hash",
        "oem_code_description_note": "code-to-description is counted as one-to-many capable; no one-to-one assumption is made",
        "classification_action": "profile_only_no_target_promotion",
        "raw_operational_values_emitted_to_versioned_artifacts": False,
        "internal_visible_sample_location": "reports/internal/f51b2_2f_residual_unique_and_oem_space/",
    }

    profile_path = F5_OUTPUT / "f51b2_2f_residual_unique_and_oem_space_profile_sanitized.csv"
    oem_path = F5_OUTPUT / "f51b2_2f_oem_space_code_description_profile_sanitized.csv"
    summary_path = F5_OUTPUT / "f51b2_2f_residual_unique_and_oem_space_summary_sanitized.json"
    memo_path = F5_OUTPUT / "f51b2_2f_residual_unique_and_oem_space_memo.md"
    visible_path = INTERNAL_DIR / "f51b2_2f_residual_unique_blind_review_visible_internal.csv"
    responses_path = INTERNAL_DIR / "f51b2_2f_residual_unique_blind_review_responses_only.csv"

    write_csv(profile_path, profile_rows, ["profile_metric", "row_count", "pct_of_reason_non_empty", "raw_operational_values_emitted"])
    write_csv(
        oem_path,
        oem_rows,
        ["code_hash", "description_hash", "row_count", "code_distinct_description_hashes", "assume_one_to_one_mapping", "raw_operational_values_emitted"],
    )
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    write_csv(
        visible_path,
        visible_rows,
        ["blind_review_id", "reason_hash", "reason_text_pii_redacted", "reviewer_response", "allowed_response", "reviewer_notes"],
        mode=0o600,
    )
    write_csv(
        responses_path,
        response_rows,
        ["reason_hash", "reviewer_response", "allowed_response", "reviewer_notes"],
        mode=0o600,
    )

    memo = f"""# F5.1b2.2f - Residual Unique Sample and OEM Space Pattern Expansion

## Purpose

Correct the residual blind-review sample so it is drawn from distinct `reason_hash` values, and measure the OEM alarm pattern missed by strict code-description separators.

## Results

- Strict residual before OEM-space expansion: `{len(strict_residual_rows)}` rows.
- Distinct residual reason hashes: `{len(unique_strict_residual)}`.
- OEM-space rows recovered from strict residual: `{len(recovered_oem_space_rows)}`.
- Residual after OEM-space expansion: `{len(expanded_residual_rows)}` rows.
- Blind residual sample prepared: `{len(visible_rows)}` distinct values, one per `reason_hash`.

## Method Note

The prior residual blind sample was row-based and therefore frequency-weighted. This replacement sample is value-based: one row per distinct `reason_hash`. It is suitable for judging residual composition, not for estimating row-weighted prevalence.

## OEM Code-Description Guardrail

The expanded OEM profile counts code-description pairs and explicitly allows one code to have multiple observed descriptions. No one-to-one OEM dictionary assumption is made.

## Privacy

Versioned outputs contain only counts, hashes, and sanitized metadata. Visible reason text is internal-only under `reports/internal/*` and ignored by Git.
"""
    memo_path.write_text(memo, encoding="utf-8")

    assert_sanitized([profile_path, oem_path, summary_path, memo_path])
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
