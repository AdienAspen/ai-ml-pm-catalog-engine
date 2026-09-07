from __future__ import annotations

import csv
import hashlib
import json
import os
import re
from collections import Counter, defaultdict
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path("/home/adien-i7-remote/workspace/fsa_bridge_ml_feasibility")
OUTPUT_DIR = PROJECT_ROOT / "stint-1-evidence-ground-truth/phase_5_symptom/outputs/f51_symptom_thread_resolution"
INTERNAL_DIR = PROJECT_ROOT / "reports/internal/t51b23_oem_alarm_dictionary"
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

STOP_TOKENS_RE = re.compile(
    r"\b(?:WTG|T)\s*\d+\b|_{2,}|\b(?:Cnt|deg|day|days|hr|hrs|alarm|error|fault)\b[:._ -]*$",
    re.I,
)

PATTERNS = [
    (
        "prefix_dash_or_colon",
        re.compile(
            r"(?<![A-Za-z0-9])(?P<code>\d{3,6})\s*[-:–]{1,2}\s*(?P<desc>[A-Za-z][A-Za-z0-9_ ./()&+-]{3,120})",
            re.I,
        ),
    ),
    (
        "prefix_space",
        re.compile(
            r"(?<![A-Za-z0-9])(?P<code>\d{3,6})\s+(?P<desc>[A-Za-z][A-Za-z0-9_./()&+-]{3,120})",
            re.I,
        ),
    ),
    (
        "suffix_dash_or_colon",
        re.compile(
            r"(?P<desc>[A-Za-z][A-Za-z0-9_ ./()&+-]{3,120}?)\s*[-:–]{1,2}\s*(?P<code>\d{3,6})(?![A-Za-z0-9])",
            re.I,
        ),
    ),
    (
        "embedded_terminal_code",
        re.compile(
            r"(?P<desc>[A-Za-z][A-Za-z0-9_ ./()&+-]{3,100}?)\s+(?P<code>\d{3,6})(?:\s+(?:WTG|T)\s*\d+)?(?:\s|$)",
            re.I,
        ),
    ),
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


def physical_record_id(record: Mapping[str, object], fallback_index: int) -> str:
    record_key = as_text(record.get("id")) or str(fallback_index)
    return prefixed_hash(f"{CONTRACTOR_PATH}|{ENTITY}|{record_key}", "PHY", 16)


def clean_description(desc: str) -> str:
    value = desc.strip()
    value = STOP_TOKENS_RE.sub(" ", value)
    value = re.sub(r"\b(?:WTG|T)\s*\d+\b.*$", " ", value, flags=re.I)
    value = re.sub(r"\b\d{1,4}\b.*$", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip(" -:._/")


def normalise_description(desc: str) -> str:
    value = clean_description(desc)
    value = re.sub(r"[_/.-]+", " ", value)
    value = re.sub(r"([a-z])([A-Z])", r"\1 \2", value)
    value = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", value)
    value = re.sub(r"([A-Za-z])(\d)", r"\1 \2", value)
    value = re.sub(r"(\d)([A-Za-z])", r"\1 \2", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip().lower()


def description_shape(desc: str) -> str:
    words = re.findall(r"[A-Za-z]+", desc)
    nums = re.findall(r"\d+", desc)
    return f"words_{len(words)}_nums_{len(nums)}_chars_{len(desc)}"


def extract_candidates(text: str) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    seen = set()
    for pattern_name, pattern in PATTERNS:
        for match in pattern.finditer(text):
            code = match.group("code").strip()
            raw_desc = clean_description(match.group("desc"))
            normalised = normalise_description(raw_desc)
            if len(code) < 3 or not normalised or len(normalised) < 4:
                continue
            key = (pattern_name, code, normalised)
            if key in seen:
                continue
            seen.add(key)
            out.append(
                {
                    "pattern_position": pattern_name,
                    "code": code,
                    "raw_description": raw_desc,
                    "normalised_description": normalised,
                }
            )
    return out


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
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    INTERNAL_DIR.mkdir(parents=True, exist_ok=True)
    records = load_json_records(service_orders_path())

    occurrence_rows = []
    for idx, record in enumerate(records):
        reason = as_text(record.get("reason"))
        if not reason:
            continue
        for candidate in extract_candidates(reason):
            occurrence_rows.append(
                {
                    "physical_record_id": physical_record_id(record, idx),
                    "reason_hash": prefixed_hash(reason.lower(), "REASON", 12),
                    **candidate,
                }
            )

    pair_counter = Counter((row["code"], row["normalised_description"]) for row in occurrence_rows)
    pattern_counter = Counter(row["pattern_position"] for row in occurrence_rows)
    code_to_desc = defaultdict(set)
    code_to_raw_desc = defaultdict(set)
    for row in occurrence_rows:
        code_to_desc[row["code"]].add(row["normalised_description"])
        code_to_raw_desc[row["code"]].add(row["raw_description"])

    public_pair_rows = []
    for (code, normalised_desc), count in pair_counter.most_common():
        public_pair_rows.append(
            {
                "code_hash": prefixed_hash(code, "OEMCODE", 10),
                "normalised_description_hash": prefixed_hash(normalised_desc, "OEMDESC", 10),
                "normalised_description_shape": description_shape(normalised_desc),
                "occurrence_rows": count,
                "code_distinct_normalised_descriptions": len(code_to_desc[code]),
                "code_distinct_raw_descriptions": len(code_to_raw_desc[code]),
                "assume_one_to_one_mapping": False,
                "evidence_type": "real_observed_label",
                "tier": "silver-medium",
                "status": "observed_oem_dictionary_candidate_not_sap_mapping",
                "raw_operational_values_emitted": False,
            }
        )

    dispersion_rows = []
    for code, descriptions in sorted(code_to_desc.items(), key=lambda item: (-len(item[1]), item[0])):
        dispersion_rows.append(
            {
                "code_hash": prefixed_hash(code, "OEMCODE", 10),
                "occurrence_rows": sum(count for (pair_code, _), count in pair_counter.items() if pair_code == code),
                "distinct_normalised_descriptions": len(descriptions),
                "distinct_raw_descriptions": len(code_to_raw_desc[code]),
                "one_to_many_observed": len(descriptions) > 1 or len(code_to_raw_desc[code]) > 1,
                "raw_operational_values_emitted": False,
            }
        )

    pattern_rows = [
        {
            "pattern_position": pattern,
            "occurrence_rows": count,
            "pct_of_oem_occurrences": pct(count, len(occurrence_rows)),
            "raw_operational_values_emitted": False,
        }
        for pattern, count in pattern_counter.most_common()
    ]

    internal_rows = [
        {
            "physical_record_id": row["physical_record_id"],
            "reason_hash": row["reason_hash"],
            "pattern_position": row["pattern_position"],
            "code": row["code"],
            "raw_description": row["raw_description"],
            "normalised_description": row["normalised_description"],
        }
        for row in occurrence_rows
    ]

    summary = {
        "created_at_utc": utc_now(),
        "pass_id": "T5.1b2.3",
        "task_type": "oem_alarm_code_description_dictionary",
        "reason_non_empty_rows": sum(1 for record in records if as_text(record.get("reason"))),
        "oem_occurrence_rows": len(occurrence_rows),
        "distinct_oem_codes": len(code_to_desc),
        "distinct_code_normalised_description_pairs": len(pair_counter),
        "codes_with_multiple_normalised_descriptions": sum(1 for values in code_to_desc.values() if len(values) > 1),
        "codes_with_multiple_raw_descriptions": sum(1 for values in code_to_raw_desc.values() if len(values) > 1),
        "pattern_position_counts": dict(pattern_counter),
        "raw_and_normalised_forms_preserved": "raw_internal_only_normalised_hashed_in_versioned_outputs",
        "sap_mapping_status": "not_attempted",
        "classification_action": "dictionary_extraction_only_no_symptom_classification_no_denominator_promotion",
        "raw_operational_values_emitted_to_versioned_artifacts": False,
        "internal_raw_dictionary_location": "reports/internal/t51b23_oem_alarm_dictionary/",
    }

    public_pairs_path = OUTPUT_DIR / "t51b23_oem_alarm_dictionary_pairs_sanitized.csv"
    dispersion_path = OUTPUT_DIR / "t51b23_oem_alarm_dictionary_code_dispersion_sanitized.csv"
    pattern_path = OUTPUT_DIR / "t51b23_oem_alarm_dictionary_pattern_coverage_sanitized.csv"
    summary_path = OUTPUT_DIR / "t51b23_oem_alarm_dictionary_summary_sanitized.json"
    memo_path = OUTPUT_DIR / "t51b23_oem_alarm_dictionary_memo.md"
    internal_path = INTERNAL_DIR / "t51b23_oem_alarm_dictionary_internal_raw_and_normalised.csv"

    write_csv(
        public_pairs_path,
        public_pair_rows,
        [
            "code_hash",
            "normalised_description_hash",
            "normalised_description_shape",
            "occurrence_rows",
            "code_distinct_normalised_descriptions",
            "code_distinct_raw_descriptions",
            "assume_one_to_one_mapping",
            "evidence_type",
            "tier",
            "status",
            "raw_operational_values_emitted",
        ],
    )
    write_csv(
        dispersion_path,
        dispersion_rows,
        [
            "code_hash",
            "occurrence_rows",
            "distinct_normalised_descriptions",
            "distinct_raw_descriptions",
            "one_to_many_observed",
            "raw_operational_values_emitted",
        ],
    )
    write_csv(
        pattern_path,
        pattern_rows,
        ["pattern_position", "occurrence_rows", "pct_of_oem_occurrences", "raw_operational_values_emitted"],
    )
    write_csv(
        internal_path,
        internal_rows,
        ["physical_record_id", "reason_hash", "pattern_position", "code", "raw_description", "normalised_description"],
        mode=0o600,
    )
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    memo = f"""# T5.1b2.3 - OEM Alarm Dictionary

## Purpose

Extract observed OEM-style code-description pairs from `reason` without assuming prefix-only format or one-to-one code semantics.

## Pattern Coverage

This pass detects code-description evidence in four positions: prefix with separator, prefix with space, suffix with separator, and embedded/terminal code. It preserves raw descriptions only in ignored internal storage and emits hashes plus normalized shapes in versioned outputs.

## Results

- OEM occurrence rows: `{len(occurrence_rows)}`.
- Distinct OEM codes: `{len(code_to_desc)}`.
- Distinct code-normalized-description pairs: `{len(pair_counter)}`.
- Codes with multiple normalized descriptions: `{summary['codes_with_multiple_normalised_descriptions']}`.
- Codes with multiple raw descriptions: `{summary['codes_with_multiple_raw_descriptions']}`.

## Guardrails

- This is an observed OEM dictionary, not a SAP mapping.
- A code may map to multiple observed descriptions; no one-to-one assumption is made.
- No target denominator is affected by this pass.
"""
    memo_path.write_text(memo, encoding="utf-8")

    assert_sanitized([public_pairs_path, dispersion_path, pattern_path, summary_path, memo_path])
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
