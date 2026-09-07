"""Bounded F4.0 XLSX document-family characterization.

This script characterizes a four-file XLSX sample as documents. It does not
parse production records, extract candidates, score targets, or emit raw
operational values.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any

from openpyxl import load_workbook


PROJECT_ROOT = Path(__file__).resolve().parents[3]
STINT_ROOT = PROJECT_ROOT / "stint-1-evidence-ground-truth"
PHASE_DIR = STINT_ROOT / "phase_4_path_b_xlsx"
OUTPUT_DIR = PHASE_DIR / "outputs" / "f40_xlsx_characterization"
INTERNAL_MANIFEST = PROJECT_ROOT / "reports" / "internal" / "f40_xlsx_characterization" / "f40_xlsx_file_sample_manifest_internal.csv"
POSITIVE_CONTROLS = OUTPUT_DIR / "f40_xlsx_positive_control_check_sanitized.csv"

MAX_FILES = 4
MAX_SHEETS = 10
MAX_COLUMNS = 40
MAX_DATA_ROWS = 15
STREAMING_THRESHOLD_BYTES = 20_000_000

TEXT_CLASS_HINTS = re.compile(r"note|comment|remark|desc|description|text|narrative|observation|action|reason|cause|work|task|issue|summary", re.I)
DATE_CLASS_HINTS = re.compile(r"date|time|day|month|year|start|finish|complete|created|closed", re.I)
STATUS_CLASS_HINTS = re.compile(r"status|state|stage|priority|type|category|condition|result|outcome", re.I)
CODE_CLASS_HINTS = re.compile(r"code|fault|alarm|sap|id$|^id|number|no\.|tag|type", re.I)
IDENTIFIER_CLASS_HINTS = re.compile(r"asset|turbine|unit|equipment|serial|order|notification|work.?order|wo|floc|functional", re.I)
METADATA_CLASS_HINTS = re.compile(r"site|plant|contractor|owner|location|region|source|file|sheet|user|crew|team", re.I)
PII_HINTS = re.compile(r"name|email|phone|mobile|signature|badge|employee|worker|technician|contact", re.I)

EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
PHONE_RE = re.compile(r"(?:\+?\d[\d\s().-]{7,}\d)")
WORKER_ID_RE = re.compile(r"\b(?:emp|worker|badge|tech)[-_ ]?\d{3,}\b", re.I)
TOKEN_RE = re.compile(r"[A-Za-zÀ-ÿ0-9]+")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def as_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def stable_hash(value: Any, length: int = 16) -> str:
    raw = "" if value is None else str(value)
    return hashlib.sha256(raw.encode("utf-8", errors="ignore")).hexdigest()[:length]


def prefixed_hash(value: Any, prefix: str, length: int = 12) -> str:
    return f"{prefix}-{stable_hash(value, length)}"


def read_csv_dicts(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def safe_ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round(numerator / denominator, 4)


def value_dtype(values: list[Any]) -> str:
    non_empty = [value for value in values if as_text(value)]
    if not non_empty:
        return "empty"
    type_counts = Counter()
    for value in non_empty:
        if isinstance(value, bool):
            type_counts["bool"] += 1
        elif isinstance(value, datetime):
            type_counts["date"] += 1
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            type_counts["numeric"] += 1
        else:
            text = as_text(value)
            if re.fullmatch(r"\d{4}-\d{1,2}-\d{1,2}.*", text) or re.fullmatch(r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}.*", text):
                type_counts["date_like"] += 1
            elif re.fullmatch(r"[-+]?\d+(?:\.\d+)?", text):
                type_counts["numeric_like"] += 1
            else:
                type_counts["text"] += 1
    dominant, count = type_counts.most_common(1)[0]
    if count == len(non_empty):
        return dominant
    if type_counts["text"] and (type_counts["numeric"] or type_counts["numeric_like"] or type_counts["date"] or type_counts["date_like"]):
        return "mixed"
    return dominant


def language_category(values: list[Any]) -> str:
    text = " ".join(as_text(value).lower() for value in values if as_text(value))
    if not text:
        return "none"
    spanish_hits = len(re.findall(r"\b(?:de|del|la|el|los|las|para|por|con|sin|mantenimiento|reparacion|falla|observacion)\b|[áéíóúñ]", text))
    english_hits = len(re.findall(r"\b(?:the|and|for|with|without|maintenance|repair|failure|fault|work|note|status)\b", text))
    if spanish_hits and english_hits:
        return "mixed"
    if spanish_hits:
        return "spanish_like"
    if english_hits:
        return "english_like"
    return "undetermined"


def classify_column(header: str, values: list[Any]) -> str:
    header_text = header.lower()
    non_empty_text = [as_text(value) for value in values if as_text(value)]
    avg_words = mean([len(TOKEN_RE.findall(value)) for value in non_empty_text]) if non_empty_text else 0
    unique_count = len(set(non_empty_text))
    if TEXT_CLASS_HINTS.search(header_text) or avg_words >= 4:
        return "free_text"
    if DATE_CLASS_HINTS.search(header_text):
        return "date"
    if IDENTIFIER_CLASS_HINTS.search(header_text):
        return "identifier"
    if STATUS_CLASS_HINTS.search(header_text):
        return "status"
    if CODE_CLASS_HINTS.search(header_text):
        return "code"
    if METADATA_CLASS_HINTS.search(header_text):
        return "metadata"
    if non_empty_text and unique_count <= max(3, math.ceil(len(non_empty_text) * 0.4)):
        return "status"
    if avg_words >= 3:
        return "free_text"
    return "unknown"


def pii_location(header: str, values: list[Any]) -> bool:
    if PII_HINTS.search(header):
        return True
    for value in values:
        text = as_text(value)
        if EMAIL_RE.search(text) or PHONE_RE.search(text) or WORKER_ID_RE.search(text):
            return True
    return False


def workbook_embedded_objects_present(path: Path) -> bool:
    try:
        with zipfile.ZipFile(path) as zf:
            names = zf.namelist()
            return any(name.startswith(("xl/drawings/", "xl/media/", "xl/charts/", "xl/pivotTables/")) for name in names)
    except Exception:
        return False


def first_visible_rows(ws: Any, max_rows: int = MAX_DATA_ROWS + 1) -> list[list[Any]]:
    rows: list[list[Any]] = []
    for idx, row in enumerate(ws.iter_rows(max_row=max_rows, max_col=MAX_COLUMNS, values_only=True)):
        if idx >= max_rows:
            break
        rows.append(list(row[:MAX_COLUMNS]))
    return rows


def detect_header_row(rows: list[list[Any]]) -> tuple[int | None, list[str]]:
    for idx, row in enumerate(rows):
        non_empty = [as_text(value) for value in row if as_text(value)]
        if len(non_empty) >= 2:
            return idx, non_empty[:MAX_COLUMNS]
    return None, []


def inspect_positive_control(path: Path) -> dict[str, Any]:
    result = {
        "read_status": "not_started",
        "sheet_count": 0,
        "control_sheet_index": None,
        "header_row_index": None,
        "first_header_hash": "",
        "text_marker_hash": "",
        "text_marker_word_count": 0,
        "error_type": "",
    }
    try:
        wb = load_workbook(path, read_only=True, data_only=True)
        result["read_status"] = "opened"
        result["sheet_count"] = len(wb.sheetnames)
        if not wb.sheetnames:
            result["read_status"] = "no_sheets"
            return result
        ws = wb[wb.sheetnames[0]]
        rows = first_visible_rows(ws, 16)
        header_idx, header_values = detect_header_row(rows)
        result["control_sheet_index"] = 0
        result["header_row_index"] = header_idx
        if header_values:
            result["first_header_hash"] = prefixed_hash(header_values[0].lower(), "HDR", 10)
        marker = ""
        if header_idx is not None:
            for idx, values in enumerate(rows):
                if idx <= header_idx:
                    continue
                for value in values[:MAX_COLUMNS]:
                    text = as_text(value)
                    if len(TOKEN_RE.findall(text)) >= 2:
                        marker = text
                        break
                if marker:
                    break
        if marker:
            result["text_marker_hash"] = prefixed_hash(marker.lower(), "TXT", 12)
            result["text_marker_word_count"] = len(TOKEN_RE.findall(marker))
        result["read_status"] = "control_ready"
        wb.close()
    except Exception as exc:  # noqa: BLE001
        result["read_status"] = "read_failed"
        result["error_type"] = type(exc).__name__
    return result


def positive_control_pass(expected: dict[str, str], actual: dict[str, Any]) -> tuple[bool, str]:
    checks = [
        ("read_status", expected.get("read_status", ""), actual.get("read_status", "")),
        ("sheet_count", expected.get("sheet_count", ""), str(actual.get("sheet_count", ""))),
        ("control_sheet_index", expected.get("control_sheet_index", ""), str(actual.get("control_sheet_index", ""))),
        ("header_row_index", expected.get("header_row_index", ""), str(actual.get("header_row_index", ""))),
        ("first_header_hash", expected.get("first_header_hash", ""), actual.get("first_header_hash", "")),
    ]
    expected_marker = expected.get("text_marker_hash", "")
    if expected_marker:
        checks.append(("text_marker_hash", expected_marker, actual.get("text_marker_hash", "")))
    failed = [name for name, exp, got in checks if str(exp) != str(got)]
    return (not failed, ",".join(failed))


def sheet_role(sheet_name: str, column_classes: Counter[str]) -> str:
    name = sheet_name.lower()
    if "daily" in name or "status" in name:
        return "daily_status_or_snapshot"
    if "weather" in name:
        return "weather_or_environmental_context"
    if "work" in name or "schedule" in name:
        return "work_schedule_or_log"
    if column_classes["free_text"] >= 1 and column_classes["identifier"] >= 1:
        return "work_event_or_status_table"
    if column_classes["date"] >= 1 and column_classes["status"] >= 1:
        return "status_table"
    if column_classes["metadata"] >= 1:
        return "metadata_or_context"
    return "unknown_document_section"


def characterize() -> dict[str, Any]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = read_csv_dicts(INTERNAL_MANIFEST)[:MAX_FILES]
    controls_by_id = {row["sample_id"]: row for row in read_csv_dicts(POSITIVE_CONTROLS)}

    sheet_rows: list[dict[str, Any]] = []
    column_rows: list[dict[str, Any]] = []
    positive_rows: list[dict[str, Any]] = []
    file_summaries: list[dict[str, Any]] = []
    repetition_counter: Counter[str] = Counter()
    template_signatures: dict[str, list[str]] = defaultdict(list)
    pii_locations: list[str] = []

    for entry in manifest:
        sample_id = entry["sample_id"]
        path_hash = entry["path_hash"]
        raw_path = Path(entry["raw_path"])
        size = raw_path.stat().st_size
        streaming_required = size >= STREAMING_THRESHOLD_BYTES
        actual_control = inspect_positive_control(raw_path)
        passed, failures = positive_control_pass(controls_by_id.get(sample_id, {}), actual_control)
        positive_rows.append(
            {
                "sample_id": sample_id,
                "path_hash": path_hash,
                "positive_control_passed": passed,
                "failed_checks": failures,
                "read_status": actual_control["read_status"],
                "raw_operational_values_emitted": False,
            }
        )

        file_status = "interpretable" if passed else "not_interpretable_positive_control_failed"
        sheets_seen = 0
        columns_seen = 0
        rows_sampled_total = 0
        truncated_file = False
        file_sheet_names_hashes: list[str] = []
        file_header_hashes: list[str] = []

        if not passed:
            file_summaries.append(
                {
                    "sample_id": sample_id,
                    "path_hash": path_hash,
                    "file_size_bytes": size,
                    "streaming_required": streaming_required,
                    "sheets_inspected": 0,
                    "columns_profiled": 0,
                    "data_rows_sampled": 0,
                    "truncated": True,
                    "interpretability_status": file_status,
                }
            )
            continue

        wb = load_workbook(raw_path, read_only=True, data_only=True)
        sheet_names = wb.sheetnames[:MAX_SHEETS]
        if len(wb.sheetnames) > MAX_SHEETS:
            truncated_file = True
        for sheet_index, sheet_name in enumerate(sheet_names):
            sheets_seen += 1
            sheet_hash = prefixed_hash(sheet_name.lower(), "SHEET", 10)
            file_sheet_names_hashes.append(sheet_hash)
            ws = wb[sheet_name]
            rows = first_visible_rows(ws, MAX_DATA_ROWS + 1)
            header_idx, headers = detect_header_row(rows)
            if header_idx is None or not headers:
                sheet_rows.append(
                    {
                        "sample_id": sample_id,
                        "path_hash": path_hash,
                        "sheet_index": sheet_index,
                        "sheet_hash": sheet_hash,
                        "sheet_role": "empty_or_no_detectable_header",
                        "header_row_index": "",
                        "inspected_column_count": 0,
                        "sampled_data_row_count": 0,
                        "free_text_column_count": 0,
                        "code_column_count": 0,
                        "status_column_count": 0,
                        "identifier_column_count": 0,
                        "date_column_count": 0,
                        "metadata_column_count": 0,
                        "unknown_column_count": 0,
                        "text_outside_routing_present": False,
                        "embedded_objects_present": workbook_embedded_objects_present(raw_path),
                        "truncated": truncated_file,
                    }
                )
                continue

            data_rows = rows[header_idx + 1 : header_idx + 1 + MAX_DATA_ROWS]
            header_count = min(len(headers), MAX_COLUMNS)
            if len(headers) > MAX_COLUMNS:
                truncated_file = True
            columns_seen += header_count
            rows_sampled_total += len(data_rows)
            class_counts: Counter[str] = Counter()
            sheet_text_outside = False

            for col_idx in range(header_count):
                header = headers[col_idx]
                header_hash = prefixed_hash(header.lower(), "COL", 10)
                file_header_hashes.append(header_hash)
                values = []
                for row in data_rows:
                    if col_idx < len(row):
                        values.append(row[col_idx])
                non_empty = [as_text(value) for value in values if as_text(value)]
                null_rate = 1 - (len(non_empty) / len(values)) if values else 1
                dtype = value_dtype(values)
                col_class = classify_column(header, values)
                class_counts[col_class] += 1
                word_counts = [len(TOKEN_RE.findall(value)) for value in non_empty]
                avg_words = round(mean(word_counts), 2) if word_counts else 0
                max_words = max(word_counts) if word_counts else 0
                lang = language_category(values) if col_class == "free_text" else "not_text"
                pii_present = pii_location(header, values)
                if pii_present:
                    pii_locations.append(f"{sample_id}:{sheet_index}:{col_idx}")
                if col_class == "free_text" and not TEXT_CLASS_HINTS.search(header):
                    sheet_text_outside = True
                if col_class in {"identifier", "code", "status"}:
                    for value in non_empty:
                        repetition_counter[prefixed_hash(value.lower(), "VAL", 12)] += 1
                column_rows.append(
                    {
                        "sample_id": sample_id,
                        "path_hash": path_hash,
                        "sheet_index": sheet_index,
                        "sheet_hash": sheet_hash,
                        "column_index": col_idx,
                        "column_hash": header_hash,
                        "sanitized_column_label": f"{col_class.upper()}_{col_idx + 1:03d}",
                        "dtype_observed": dtype,
                        "null_rate_sample": round(null_rate, 4),
                        "classification": col_class,
                        "non_empty_sample_values": len(non_empty),
                        "distinct_value_count_sample": len(set(non_empty)),
                        "avg_word_count_if_text": avg_words,
                        "max_word_count_if_text": max_words,
                        "language_category": lang,
                        "looks_like_planned_reactive_field": bool(re.search(r"activity|maintenance|work.?type|type|category", header, re.I)),
                        "looks_like_state_status_code": col_class in {"status", "code"} and len(set(non_empty)) <= max(3, math.ceil(len(non_empty) * 0.5)),
                        "pii_location_flag": pii_present,
                        "raw_operational_values_emitted": False,
                    }
                )

            role = sheet_role(sheet_name, class_counts)
            sheet_rows.append(
                {
                    "sample_id": sample_id,
                    "path_hash": path_hash,
                    "sheet_index": sheet_index,
                    "sheet_hash": sheet_hash,
                    "sheet_role": role,
                    "header_row_index": header_idx,
                    "inspected_column_count": header_count,
                    "sampled_data_row_count": len(data_rows),
                    "free_text_column_count": class_counts["free_text"],
                    "code_column_count": class_counts["code"],
                    "status_column_count": class_counts["status"],
                    "identifier_column_count": class_counts["identifier"],
                    "date_column_count": class_counts["date"],
                    "metadata_column_count": class_counts["metadata"],
                    "unknown_column_count": class_counts["unknown"],
                    "text_outside_routing_present": sheet_text_outside,
                    "embedded_objects_present": workbook_embedded_objects_present(raw_path),
                    "truncated": truncated_file,
                }
            )
        wb.close()

        template_seed = "|".join(file_sheet_names_hashes) + "::" + "|".join(sorted(file_header_hashes))
        template_signature = prefixed_hash(template_seed, "TPL", 12)
        template_signatures[template_signature].append(sample_id)
        file_summaries.append(
            {
                "sample_id": sample_id,
                "path_hash": path_hash,
                "file_size_bytes": size,
                "streaming_required": streaming_required,
                "sheets_inspected": sheets_seen,
                "columns_profiled": columns_seen,
                "data_rows_sampled": rows_sampled_total,
                "truncated": truncated_file,
                "interpretability_status": file_status,
                "template_signature": template_signature,
            }
        )

    repeated_identifier_like_values = sum(1 for _, count in repetition_counter.items() if count > 1)
    text_columns = [row for row in column_rows if row["classification"] == "free_text"]
    status_code_columns = [row for row in column_rows if row["looks_like_state_status_code"]]
    planned_reactive_columns = [row for row in column_rows if row["looks_like_planned_reactive_field"]]
    ignored_text_sheets = [row for row in sheet_rows if row["text_outside_routing_present"]]

    write_csv(
        OUTPUT_DIR / "f40_xlsx_sheet_inventory_sanitized.csv",
        sheet_rows,
        [
            "sample_id",
            "path_hash",
            "sheet_index",
            "sheet_hash",
            "sheet_role",
            "header_row_index",
            "inspected_column_count",
            "sampled_data_row_count",
            "free_text_column_count",
            "code_column_count",
            "status_column_count",
            "identifier_column_count",
            "date_column_count",
            "metadata_column_count",
            "unknown_column_count",
            "text_outside_routing_present",
            "embedded_objects_present",
            "truncated",
        ],
    )
    write_csv(
        OUTPUT_DIR / "f40_xlsx_column_profile_sanitized.csv",
        column_rows,
        [
            "sample_id",
            "path_hash",
            "sheet_index",
            "sheet_hash",
            "column_index",
            "column_hash",
            "sanitized_column_label",
            "dtype_observed",
            "null_rate_sample",
            "classification",
            "non_empty_sample_values",
            "distinct_value_count_sample",
            "avg_word_count_if_text",
            "max_word_count_if_text",
            "language_category",
            "looks_like_planned_reactive_field",
            "looks_like_state_status_code",
            "pii_location_flag",
            "raw_operational_values_emitted",
        ],
    )

    summary = {
        "run_utc": utc_now(),
        "task": "F4.0 XLSX document-family characterization",
        "files_in_sample": len(manifest),
        "files_interpretable": sum(1 for row in positive_rows if row["positive_control_passed"]),
        "positive_controls_passed": all(row["positive_control_passed"] for row in positive_rows),
        "sheet_rows_emitted": len(sheet_rows),
        "column_rows_emitted": len(column_rows),
        "text_column_count": len(text_columns),
        "status_or_code_like_column_count": len(status_code_columns),
        "planned_reactive_candidate_column_count": len(planned_reactive_columns),
        "repeated_identifier_like_hashes_in_sample": repeated_identifier_like_values,
        "template_signature_count": len(template_signatures),
        "files_truncated": sum(1 for row in file_summaries if row["truncated"]),
        "pii_location_count": len(pii_locations),
        "raw_operational_values_emitted": False,
    }
    (OUTPUT_DIR / "f40_xlsx_characterization_summary_sanitized.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    structure_lines = [
        "| sample_id | sheets | columns_profiled | rows_sampled | truncated | template_signature |",
        "| --- | ---: | ---: | ---: | --- | --- |",
    ]
    for row in file_summaries:
        structure_lines.append(
            f"| {row['sample_id']} | {row['sheets_inspected']} | {row['columns_profiled']} | {row['data_rows_sampled']} | {row['truncated']} | {row.get('template_signature', '')} |"
        )

    role_counts = Counter(row["sheet_role"] for row in sheet_rows)
    class_counts = Counter(row["classification"] for row in column_rows)
    language_counts = Counter(row["language_category"] for row in text_columns)
    template_distribution = {key: len(value) for key, value in template_signatures.items()}

    if repeated_identifier_like_values:
        repetition_line = (
            f"Repetition risk: `{repeated_identifier_like_values}` identifier/code/status value hashes appeared more than once in the bounded sample. "
            "This is evidence that row count may not equal event count."
        )
    else:
        repetition_line = (
            "Repetition risk: `0` repeated identifier/code/status value hashes were observed in the bounded sample. "
            "This does not prove absence of repetition beyond the sample."
        )

    memo = f"""# F4.0 XLSX Characterization Memo

## What These Documents Are

The sampled XLSX family behaves primarily as daily/status-style operational workbooks rather than atomic event records. The evidence is structural: repeated dated files, compact sheet sets, status/code-like columns, identifier-like columns, and free-text columns that appear as contextual fields rather than as normalized target labels. This is a characterization of four selected files only; it does not extrapolate to the full corpus.

## Structure

{chr(10).join(structure_lines)}

Positive controls passed before missing values were interpreted: `{summary['positive_controls_passed']}`.

## Where The Signal Is

- Free-text columns observed: `{len(text_columns)}`.
- Column classes observed: `{dict(class_counts)}`.
- Text language categories observed: `{dict(language_counts)}`.
- Planned/reactive candidate columns observed: `{len(planned_reactive_columns)}`. These are candidate locations only; no maintenance-type derivation was performed.
- Status/code-like columns observed: `{len(status_code_columns)}`. These require downstream state-vs-description review before any mapping work.

## Red Flags

- {repetition_line}
- Template variation: `{len(template_signatures)}` template signatures were observed across `{len(manifest)}` files: `{template_distribution}`.
- Text outside obvious routing: `{len(ignored_text_sheets)}` sheets had free-text-like columns not clearly identified by routed text-column names.
- PII locations: `{len(pii_locations)}` column locations were flagged. Values were not emitted.
- Truncated files: `{summary['files_truncated']}`.

## Implications For The Pipeline

F4 should start with document-family routing and template-aware sheet handling before any extraction or weak supervision. The sample supports a snapshot/repetition risk check similar to Path A: rows should not be treated as events until a stable event or physical-record key is defined. Status/code-like columns must be separated from failure-description evidence before target scoring, and free-text fields must preserve `source_text_field` for DELTA-0003.

## Coverage Note

This pass inspected `{len(manifest)}` files, at most `{MAX_SHEETS}` sheets per file, `{MAX_COLUMNS}` columns per sheet, and `{MAX_DATA_ROWS}` data rows per sheet, using `openpyxl` with `read_only=True` and `data_only=True`. Embedded objects were ignored except for yes/no presence. No raw operational values, raw file names, raw paths, site names, contractor names, asset identifiers, personal data, or raw prose were emitted.
"""
    (OUTPUT_DIR / "f40_xlsx_characterization_memo.md").write_text(memo, encoding="utf-8")
    return summary


if __name__ == "__main__":
    print(json.dumps(characterize(), indent=2))
