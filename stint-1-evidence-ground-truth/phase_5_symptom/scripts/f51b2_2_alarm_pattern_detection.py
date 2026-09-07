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
F5_OUTPUT = PROJECT_ROOT / "stint-1-evidence-ground-truth/phase_5_symptom/outputs/f51_symptom_thread_resolution"
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

OEM_ALARM_RE = re.compile(
    r"(?<![A-Za-z0-9])(?P<code>[A-Z]{0,4}\d{2,6}[A-Z]{0,4}|[A-Z]{2,8}\d{1,5})\s*[-:–]\s*(?P<desc>[A-Za-z][A-Za-z0-9 /_.,()]{4,})",
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


def text_length_bucket(text: str) -> str:
    wc = word_count(text)
    if wc <= 3:
        return "01_very_short_1_3_words"
    if wc <= 8:
        return "02_short_4_8_words"
    if wc <= 20:
        return "03_medium_9_20_words"
    return "04_long_21_plus_words"


def language_bucket(text: str) -> str:
    lowered = text.lower()
    english_hits = sum(cue in lowered for cue in ["the", "and", "for", "with", "repair", "maintenance", "fault", "alarm"])
    spanish_hits = sum(cue in lowered for cue in ["para", "con", "por", "repar", "manten", "falla", "alarma"])
    if english_hits and spanish_hits:
        return "mixed_or_ambiguous"
    if english_hits:
        return "english_like"
    if spanish_hits:
        return "spanish_like"
    return "undetermined"


def code_shape(code: str) -> str:
    letters = len(re.findall(r"[A-Za-z]", code))
    digits = len(re.findall(r"\d", code))
    return f"alpha{letters}_digit{digits}_len{len(code)}"


def dispatch_categories(text: str) -> list[str]:
    return [name for name, pattern in DISPATCH_MOTIVE_PATTERNS.items() if pattern.search(text)]


def match_row(reason: str) -> dict[str, Any]:
    oem_match = OEM_ALARM_RE.search(reason)
    cms_match = CMS_RE.search(reason)
    dispatch_hits = dispatch_categories(reason)

    if oem_match:
        exclusive_bucket = "oem_alarm_pattern"
    elif cms_match:
        exclusive_bucket = "cms_alert_pattern"
    elif dispatch_hits:
        exclusive_bucket = "dispatch_motive_pattern"
    else:
        exclusive_bucket = "residual_no_pattern"

    severity = ""
    if cms_match:
        severity = cms_match.group("severity") or ""

    return {
        "oem_alarm_pattern": bool(oem_match),
        "cms_alert_pattern": bool(cms_match),
        "dispatch_motive_pattern": bool(dispatch_hits),
        "residual_no_pattern": not (oem_match or cms_match or dispatch_hits),
        "exclusive_bucket": exclusive_bucket,
        "oem_code_shape": code_shape(oem_match.group("code")) if oem_match else "",
        "cms_severity": severity,
        "dispatch_pattern_categories": dispatch_hits,
    }


def pct(count: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round(100 * count / denominator, 2)


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
    F5_OUTPUT.mkdir(parents=True, exist_ok=True)
    records = load_json_records(service_orders_path())

    rows = []
    for idx, record in enumerate(records):
        reason = as_text(record.get("reason"))
        if not reason:
            continue
        matched = match_row(reason)
        rows.append(
            {
                "physical_record_id": physical_record_id(record, idx),
                "reason_hash": prefixed_hash(reason.lower(), "REASON", 12),
                "word_count_bucket": text_length_bucket(reason),
                "language_bucket": language_bucket(reason),
                **matched,
            }
        )

    denominator = len(rows)
    flag_counts = {
        "oem_alarm_pattern": sum(1 for row in rows if row["oem_alarm_pattern"]),
        "cms_alert_pattern": sum(1 for row in rows if row["cms_alert_pattern"]),
        "dispatch_motive_pattern": sum(1 for row in rows if row["dispatch_motive_pattern"]),
        "residual_no_pattern": sum(1 for row in rows if row["residual_no_pattern"]),
    }
    exclusive_counts = Counter(str(row["exclusive_bucket"]) for row in rows)
    severity_counts = Counter(str(row["cms_severity"]) for row in rows if row["cms_severity"])
    oem_shape_counts = Counter(str(row["oem_code_shape"]) for row in rows if row["oem_code_shape"])
    dispatch_category_counts = Counter(cat for row in rows for cat in row["dispatch_pattern_categories"])
    residue_language_counts = Counter(str(row["language_bucket"]) for row in rows if row["exclusive_bucket"] == "residual_no_pattern")
    residue_length_counts = Counter(str(row["word_count_bucket"]) for row in rows if row["exclusive_bucket"] == "residual_no_pattern")

    pattern_rows = []
    for pattern_name in ["oem_alarm_pattern", "cms_alert_pattern", "dispatch_motive_pattern", "residual_no_pattern"]:
        pattern_rows.append(
            {
                "pass_id": "F5.1b2.2",
                "pattern_track": pattern_name,
                "flag_rows": flag_counts.get(pattern_name, 0),
                "flag_pct_of_reason_non_empty": pct(flag_counts.get(pattern_name, 0), denominator),
                "exclusive_rows": exclusive_counts.get(pattern_name, 0),
                "exclusive_pct_of_reason_non_empty": pct(exclusive_counts.get(pattern_name, 0), denominator),
                "classification_action": "count_and_profile_only_no_target_promotion",
                "raw_operational_values_emitted": False,
            }
        )

    detail_rows = []
    for shape, count in oem_shape_counts.most_common():
        detail_rows.append({"detail_type": "oem_code_shape", "detail_bucket": shape, "row_count": count})
    for severity, count in severity_counts.most_common():
        detail_rows.append({"detail_type": "cms_severity", "detail_bucket": f"severity_{severity}", "row_count": count})
    for category, count in dispatch_category_counts.most_common():
        detail_rows.append({"detail_type": "dispatch_category", "detail_bucket": category, "row_count": count})
    for lang, count in residue_language_counts.most_common():
        detail_rows.append({"detail_type": "residue_language_bucket", "detail_bucket": lang, "row_count": count})
    for length, count in residue_length_counts.most_common():
        detail_rows.append({"detail_type": "residue_length_bucket", "detail_bucket": length, "row_count": count})

    summary = {
        "created_at_utc": utc_now(),
        "pass_id": "F5.1b2.2",
        "task_type": "automatic_alarm_pattern_detection_count_and_profile_only",
        "scope": "complete_non_empty_reason_universe",
        "records_evaluated": len(records),
        "reason_non_empty_rows": denominator,
        "tracks": {
            "F5.1b2.2a": "OEM alarm pattern coverage",
            "F5.1b2.2b": "CMS pattern coverage with severity extracted",
            "F5.1b2.2c": "dispatch_motive exclusion by pattern",
            "F5.1b2.2d": "residual without pattern where technician prose may live",
        },
        "flag_counts": {k: {"rows": v, "pct": pct(v, denominator)} for k, v in flag_counts.items()},
        "exclusive_bucket_counts": {k: {"rows": v, "pct": pct(v, denominator)} for k, v in sorted(exclusive_counts.items())},
        "cms_severity_buckets": dict(sorted(severity_counts.items())),
        "dispatch_pattern_category_counts": dict(dispatch_category_counts.most_common()),
        "residual_profile": {
            "language_buckets": dict(residue_language_counts.most_common()),
            "word_count_buckets": dict(residue_length_counts.most_common()),
        },
        "pattern_precedence_for_exclusive_bucket": [
            "oem_alarm_pattern",
            "cms_alert_pattern",
            "dispatch_motive_pattern",
            "residual_no_pattern",
        ],
        "promotion_status": "none_count_and_profile_only",
        "raw_operational_values_emitted_to_versioned_artifacts": False,
    }

    pattern_path = F5_OUTPUT / "f51b2_2_alarm_pattern_detection_counts_sanitized.csv"
    detail_path = F5_OUTPUT / "f51b2_2_alarm_pattern_detection_detail_profile_sanitized.csv"
    summary_path = F5_OUTPUT / "f51b2_2_alarm_pattern_detection_summary_sanitized.json"
    memo_path = F5_OUTPUT / "f51b2_2_alarm_pattern_detection_memo.md"

    write_csv(
        pattern_path,
        pattern_rows,
        [
            "pass_id",
            "pattern_track",
            "flag_rows",
            "flag_pct_of_reason_non_empty",
            "exclusive_rows",
            "exclusive_pct_of_reason_non_empty",
            "classification_action",
            "raw_operational_values_emitted",
        ],
    )
    write_csv(detail_path, detail_rows, ["detail_type", "detail_bucket", "row_count"])
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    memo = f"""# F5.1b2.2 - Automatic Alarm Pattern Detection

## Purpose

Count and profile four reason-text pattern families before any Symptom classification or target promotion.

## Scope

- Source universe: complete non-empty `reason` field for `CONTRACTOR_PATH_001`.
- Rows evaluated: `{denominator}` non-empty reason rows from `{len(records)}` service-order records.
- This pass counts and profiles only. It does not classify Symptom, create denominator rows, or promote evidence.

## Pattern Tracks

| Track | Meaning | Flag rows | Exclusive rows |
| --- | --- | ---: | ---: |
| F5.1b2.2a | OEM alarm pattern coverage | {flag_counts.get('oem_alarm_pattern', 0)} | {exclusive_counts.get('oem_alarm_pattern', 0)} |
| F5.1b2.2b | CMS pattern coverage with severity extracted | {flag_counts.get('cms_alert_pattern', 0)} | {exclusive_counts.get('cms_alert_pattern', 0)} |
| F5.1b2.2c | Dispatch-motive exclusion by pattern | {flag_counts.get('dispatch_motive_pattern', 0)} | {exclusive_counts.get('dispatch_motive_pattern', 0)} |
| F5.1b2.2d | Residual without pattern; likely location for technician prose | {flag_counts.get('residual_no_pattern', 0)} | {exclusive_counts.get('residual_no_pattern', 0)} |

## Counting Note

Flag counts are independent pattern hits and may overlap. Exclusive bucket counts apply this precedence: OEM alarm, then CMS alert, then dispatch motive, then residual. This prevents double counting while preserving separate pattern coverage.

## Interpretation Guardrail

Dispatch-motive rows are actively separated so administrative, inspection, upgrade, testing, planned, or adjustment text does not remain hidden inside the residual pool. The residual is not Symptom evidence by itself; it is the candidate area where free technician prose may live and still requires downstream review.

## Privacy

No raw reason text, operational values, source paths, site names, contractor names, or customer identifiers are emitted in versioned artifacts.
"""
    memo_path.write_text(memo, encoding="utf-8")

    assert_sanitized([pattern_path, detail_path, summary_path, memo_path])
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
