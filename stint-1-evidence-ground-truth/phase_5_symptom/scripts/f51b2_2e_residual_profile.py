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
INTERNAL_DIR = PROJECT_ROOT / "reports/internal/f51b2_2e_reason_residual_profile"
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
WEAK_DISPATCH_CUES = {
    "inspection_like": re.compile(r"\b(inspec|insp\b|visual|check|walk|visit|audit|review)\b", re.I),
    "planning_like": re.compile(r"\b(plan|sched|annual|month|quarter|prevent|routine|service)\b", re.I),
    "change_like": re.compile(r"\b(upgrad|retro|modif|campaign|bulletin|install|replace per|change out)\b", re.I),
    "test_like": re.compile(r"\b(test|trial|commission|calibrat|verify|validation)\b", re.I),
    "admin_like": re.compile(r"\b(admin|paper|permit|access|escort|meet|support|assist)\b", re.I),
    "adjust_like": re.compile(r"\b(adjust|setting|parameter|reset|config|software|firmware)\b", re.I),
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


def dispatch_categories(text: str) -> list[str]:
    return [name for name, pattern in DISPATCH_MOTIVE_PATTERNS.items() if pattern.search(text)]


def weak_dispatch_cues(text: str) -> list[str]:
    return [name for name, pattern in WEAK_DISPATCH_CUES.items() if pattern.search(text)]


def is_residual(text: str) -> bool:
    return not (OEM_ALARM_RE.search(text) or CMS_RE.search(text) or dispatch_categories(text))


def leading_pattern_bucket(text: str) -> str:
    value = text.strip()
    if re.match(r"^\d+\s*[-:./_]", value):
        return "numeric_prefix_with_separator"
    if re.match(r"^\d+\s+[A-Za-z]", value):
        return "numeric_prefix_then_text"
    if re.match(r"^[A-Za-z]{1,8}\d{1,6}", value):
        return "alnum_code_like_prefix"
    if re.match(r"^[A-Z]{2,8}[_-]", value):
        return "upper_token_prefix"
    if re.match(r"^[A-Za-z]", value):
        return "text_prefix"
    return "other_prefix"


def token_shape(token: str) -> str:
    if token.isdigit():
        return f"num_len_{len(token)}"
    if token.isalpha():
        return f"alpha_len_{len(token)}"
    letters = len(re.findall(r"[A-Za-z]", token))
    digits = len(re.findall(r"\d", token))
    return f"mixed_alpha{letters}_digit{digits}_len{len(token)}"


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

    residual_rows = []
    for idx, record in enumerate(records):
        reason = as_text(record.get("reason"))
        if not reason or not is_residual(reason):
            continue
        tokens = re.findall(r"[A-Za-z0-9][A-Za-z0-9_/-]*", reason)
        first_token = tokens[0] if tokens else ""
        residual_rows.append(
            {
                "physical_record_id": physical_record_id(record, idx),
                "reason_hash": prefixed_hash(reason.lower(), "REASON", 12),
                "word_count_bucket": text_length_bucket(reason),
                "language_bucket": language_bucket(reason),
                "leading_pattern_bucket": leading_pattern_bucket(reason),
                "first_token_shape": token_shape(first_token) if first_token else "empty",
                "has_numeric_prefix": bool(re.match(r"^\s*\d", reason)),
                "has_code_like_prefix": leading_pattern_bucket(reason) in {"numeric_prefix_with_separator", "numeric_prefix_then_text", "alnum_code_like_prefix", "upper_token_prefix"},
                "weak_dispatch_cues": weak_dispatch_cues(reason),
                "reason_text_pii_redacted": redact_pii(reason),
            }
        )

    denominator = len(residual_rows)
    length_counts = Counter(str(row["word_count_bucket"]) for row in residual_rows)
    language_counts = Counter(str(row["language_bucket"]) for row in residual_rows)
    leading_counts = Counter(str(row["leading_pattern_bucket"]) for row in residual_rows)
    first_shape_counts = Counter(str(row["first_token_shape"]) for row in residual_rows)
    weak_cue_counts = Counter(cue for row in residual_rows for cue in row["weak_dispatch_cues"])
    numeric_prefix_rows = sum(1 for row in residual_rows if row["has_numeric_prefix"])
    code_like_prefix_rows = sum(1 for row in residual_rows if row["has_code_like_prefix"])
    weak_dispatch_rows = sum(1 for row in residual_rows if row["weak_dispatch_cues"])

    profile_rows = []
    for detail_type, counter in [
        ("word_count_bucket", length_counts),
        ("language_bucket", language_counts),
        ("leading_pattern_bucket", leading_counts),
        ("first_token_shape", first_shape_counts),
        ("weak_dispatch_cue", weak_cue_counts),
    ]:
        for bucket, count in counter.most_common():
            profile_rows.append(
                {
                    "pass_id": "F5.1b2.2e",
                    "detail_type": detail_type,
                    "detail_bucket": bucket,
                    "row_count": count,
                    "pct_of_residual": pct(count, denominator),
                    "raw_operational_values_emitted": False,
                }
            )

    selected = sorted(
        residual_rows,
        key=lambda row: stable_hash(f"F5.1b2.2e|{row['reason_hash']}", 16),
    )[:40]
    for i, row in enumerate(selected, start=1):
        row["blind_review_id"] = f"F51B2-RESID-{i:03d}"

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

    summary = {
        "created_at_utc": utc_now(),
        "pass_id": "F5.1b2.2e",
        "task_type": "residual_reason_profile_count_only",
        "scope": "reason rows not matched by OEM alarm, CMS alert, or dispatch motive strict patterns",
        "residual_rows": denominator,
        "numeric_prefix_rows": {"rows": numeric_prefix_rows, "pct": pct(numeric_prefix_rows, denominator)},
        "code_like_prefix_rows": {"rows": code_like_prefix_rows, "pct": pct(code_like_prefix_rows, denominator)},
        "weak_dispatch_cue_rows": {"rows": weak_dispatch_rows, "pct": pct(weak_dispatch_rows, denominator)},
        "top_profile_buckets_are_sanitized": True,
        "blind_residual_review_rows_prepared": len(visible_rows),
        "classification_action": "profile_only_no_target_promotion",
        "raw_operational_values_emitted_to_versioned_artifacts": False,
        "internal_visible_sample_location": "reports/internal/f51b2_2e_reason_residual_profile/",
    }

    profile_path = F5_OUTPUT / "f51b2_2e_reason_residual_profile_sanitized.csv"
    summary_path = F5_OUTPUT / "f51b2_2e_reason_residual_profile_summary_sanitized.json"
    memo_path = F5_OUTPUT / "f51b2_2e_reason_residual_profile_memo.md"
    visible_path = INTERNAL_DIR / "f51b2_2e_reason_residual_blind_review_visible_internal.csv"
    response_path = INTERNAL_DIR / "f51b2_2e_reason_residual_blind_review_responses_only.csv"

    write_csv(
        profile_path,
        profile_rows,
        ["pass_id", "detail_type", "detail_bucket", "row_count", "pct_of_residual", "raw_operational_values_emitted"],
    )
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    write_csv(
        visible_path,
        visible_rows,
        ["blind_review_id", "reason_hash", "reason_text_pii_redacted", "reviewer_response", "allowed_response", "reviewer_notes"],
        mode=0o600,
    )
    write_csv(
        response_path,
        response_rows,
        ["reason_hash", "reviewer_response", "allowed_response", "reviewer_notes"],
        mode=0o600,
    )

    memo = f"""# F5.1b2.2e - Residual Reason Profile

## Purpose

Profile the residual `reason` universe after strict OEM alarm, CMS alert, and dispatch-motive patterns have been removed.

## Results

- Residual rows: `{denominator}`.
- Numeric-prefix rows: `{numeric_prefix_rows}` (`{pct(numeric_prefix_rows, denominator)}%`).
- Code-like-prefix rows: `{code_like_prefix_rows}` (`{pct(code_like_prefix_rows, denominator)}%`).
- Rows with weaker dispatch-like cues not captured by the strict exclusion: `{weak_dispatch_rows}` (`{pct(weak_dispatch_rows, denominator)}%`).
- Blind residual sample prepared: `{len(visible_rows)}` rows in ignored internal storage.

## Interpretation Guardrail

This is a profile, not a Symptom classifier. The residual is not assumed to be technician prose. It now has a measurable residual structure that can be reviewed before downstream classification.

## Privacy

Versioned outputs contain only counts, hashes, buckets, and sanitized metadata. The visible text sample is internal-only under `reports/internal/*` and is ignored by Git.
"""
    memo_path.write_text(memo, encoding="utf-8")

    assert_sanitized([profile_path, summary_path, memo_path])
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
