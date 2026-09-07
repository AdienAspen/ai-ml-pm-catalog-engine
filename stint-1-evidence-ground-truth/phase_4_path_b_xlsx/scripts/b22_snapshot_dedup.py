from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from openpyxl import load_workbook


PROJECT_ROOT = Path("/home/adien-i7-remote/workspace/fsa_bridge_ml_feasibility")
B21_DIR = PROJECT_ROOT / "stint-1-evidence-ground-truth/phase_4_path_b_xlsx/outputs/b2_snapshot_characterization"
OUTPUT_DIR = PROJECT_ROOT / "stint-1-evidence-ground-truth/phase_4_path_b_xlsx/outputs/b2_snapshot_dedup"

SOURCE_ROOTS = [
    PROJECT_ROOT / "data/interim/extracted_source/package_001_37cac7fe/Data/SITE_PATH_002 Wind OEM_ENTITY_001 EOD",
    PROJECT_ROOT / "data/interim/extracted_source/package_001_37cac7fe/Data/SITE_PATH_004 OEM_ENTITY_001 Info",
    PROJECT_ROOT / "data/interim/extracted_source/package_003_19512420/CONTRACTOR_PATH_002",
]

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


def short_hash(value: str, prefix: str) -> str:
    return f"{prefix}-{hashlib.sha256(value.encode('utf-8', errors='ignore')).hexdigest()[:12]}"


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).strip())


def normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def family_for_path(path: Path) -> tuple[str, str]:
    text = str(path).lower()
    name = path.name.lower()
    if "site_path_002 wind oem_entity_001 eod" in text:
        return "SNAPSHOT_FAMILY_001", "EOD"
    if "site_path_004 oem_entity_001 info" in text:
        if name.startswith("pod"):
            return "SNAPSHOT_FAMILY_002", "POD"
        return "SNAPSHOT_FAMILY_002", "daily_or_eod"
    if "contractor_path_002" in text:
        if name.startswith("pod_"):
            return "SNAPSHOT_FAMILY_003", "POD"
        return "SNAPSHOT_FAMILY_003", "snapshot_unprefixed"
    return "SNAPSHOT_FAMILY_UNKNOWN", "unknown"


def date_bucket(path: Path) -> str:
    name = path.name.lower()
    m = re.search(r"(20\d{2})[ _.-]+(\d{1,2})[ _.-]+(\d{1,2})", name)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    m = re.search(r"(\d{1,2})[ _.-]+(\d{1,2})[ _.-]+(20\d{2})", name)
    if m:
        return f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"
    month_names = {
        "january": 1,
        "february": 2,
        "march": 3,
        "april": 4,
        "may": 5,
        "june": 6,
        "july": 7,
        "august": 8,
        "september": 9,
        "october": 10,
        "november": 11,
        "december": 12,
    }
    for word, num in month_names.items():
        if word in name:
            y = re.search(r"(20\d{2})", name)
            d = re.search(rf"{word}\D+(\d{{1,2}})", name)
            if y and d:
                return f"{y.group(1)}-{num:02d}-{int(d.group(1)):02d}"
    return "unknown_date"


def categorize_header(header: str) -> str:
    h = header.lower()
    checks = [
        ("asset_ref", r"\b(wtg|turbine|asset|unit)\b"),
        ("status", r"\b(status|state|condition)\b"),
        ("notes_text", r"\b(note|comment|remark|description|desc|summary)\b"),
        ("work_text", r"\b(work|action|activity|task|repair|maintenance)\b"),
        ("issue_text", r"\b(issue|fault|alarm|problem|reason|cause)\b"),
        ("component_ref", r"\b(component|part|material|item|equipment)\b"),
        ("code_ref", r"\b(code|id|number|no\.|#)\b"),
        ("date_time", r"\b(date|time|start|end|duration)\b"),
        ("contractor_or_owner", r"\b(contractor|owner|crew|team|vendor)\b"),
        ("location_ref", r"\b(site|plant|location|area)\b"),
    ]
    for label, pattern in checks:
        if re.search(pattern, h):
            return label
    return "other"


def likely_header_row(rows: list[list[str]]) -> tuple[int | None, list[str]]:
    best_idx = None
    best_score = 0
    best_values: list[str] = []
    for idx, row in enumerate(rows):
        values = [clean_text(v) for v in row]
        non_empty = [v for v in values if v]
        if len(non_empty) < 2:
            continue
        categories = [categorize_header(v) for v in non_empty]
        useful = sum(1 for c in categories if c != "other")
        score = useful * 3 + min(len(non_empty), 12)
        if score > best_score:
            best_score = score
            best_idx = idx + 1
            best_values = values
    return best_idx, best_values


ASSET_RE = re.compile(r"\b(?:wtg|turbine|tur|t)\s*[-#:]?\s*(\d{1,3})\b", re.I)
CODE_RE = re.compile(r"\b(?:code|fault|alarm)\s*[-#:]?\s*([a-z0-9]{2,8})\b", re.I)


def extract_asset_key(row_values: list[str], categories: list[str]) -> tuple[str, str]:
    candidates = []
    for value, category in zip(row_values, categories):
        if category == "asset_ref" and value:
            candidates.append(value)
    candidates.extend(v for v in row_values if ASSET_RE.search(v))
    for value in candidates:
        m = ASSET_RE.search(value)
        token = m.group(1) if m else normalized(value)
        if token:
            return short_hash(token, "ASSET"), "present"
    return "ASSET-MISSING", "missing"


def extract_code_key(row_values: list[str], categories: list[str]) -> tuple[str, str]:
    candidates = [v for v, c in zip(row_values, categories) if c in {"code_ref", "issue_text", "status"} and v]
    for value in candidates:
        m = CODE_RE.search(value)
        token = m.group(1) if m else normalized(value)[:48]
        if token:
            return short_hash(token, "CODE"), "present"
    return "CODE-MISSING", "missing"


def iter_snapshot_rows(path: Path) -> list[dict[str, Any]]:
    family, doc_type = family_for_path(path)
    date = date_bucket(path)
    file_key = short_hash(str(path.relative_to(PROJECT_ROOT)), "B2FILE")
    wb = load_workbook(path, read_only=True, data_only=True)
    rows_out: list[dict[str, Any]] = []
    for sheet_index, ws in enumerate(wb.worksheets, start=1):
        sample_rows = []
        for row in ws.iter_rows(min_row=1, max_row=min(ws.max_row or 1, 30), max_col=min(ws.max_column or 1, 30), values_only=True):
            sample_rows.append([clean_text(v) for v in row])
        header_row, headers = likely_header_row(sample_rows)
        if not header_row or not headers:
            continue
        categories = [categorize_header(h) for h in headers]
        text_positions = [i + 1 for i, c in enumerate(categories) if c in {"notes_text", "work_text", "issue_text"}]
        if not text_positions:
            continue
        max_col = max(len(headers), max(text_positions))
        for row_number, row in enumerate(ws.iter_rows(min_row=header_row + 1, max_col=max_col, values_only=True), start=header_row + 1):
            row_values = [clean_text(v) for v in row]
            text_values = [row_values[pos - 1] for pos in text_positions if pos - 1 < len(row_values) and len(row_values[pos - 1]) >= 8]
            if not text_values:
                continue
            asset_key, asset_status = extract_asset_key(row_values, categories)
            code_key, code_status = extract_code_key(row_values, categories)
            text_signature = short_hash("|".join(sorted(normalized(v) for v in text_values)), "TEXTSIG")
            base_key = "|".join([family, doc_type, asset_key, code_key, text_signature])
            dated_key = "|".join([base_key, date])
            rows_out.append(
                {
                    "snapshot_row_id": short_hash(f"{file_key}|{sheet_index}|{row_number}|{text_signature}", "B2ROW"),
                    "estimated_event_key": short_hash(base_key, "B2EVENT"),
                    "estimated_event_key_with_snapshot_date": short_hash(dated_key, "B2EVENTDAY"),
                    "file_key": file_key,
                    "sheet_key": short_hash(f"{file_key}|{sheet_index}", "B2SHEET"),
                    "family": family,
                    "doc_type": doc_type,
                    "snapshot_date_bucket": date,
                    "asset_key": asset_key,
                    "asset_ref_status": asset_status,
                    "code_key": code_key,
                    "code_ref_status": code_status,
                    "candidate_text_field_count": len(text_positions),
                    "candidate_text_categories": ",".join(sorted(set(categories[pos - 1] for pos in text_positions))),
                    "row_signature": text_signature,
                    "dedup_method": "family_doc_type_asset_code_text_signature",
                    "raw_operational_values_emitted": False,
                }
            )
    wb.close()
    return rows_out


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def assert_sanitized(paths: list[Path]) -> None:
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="ignore")
        hits = [pattern.pattern for pattern in RAW_PATTERNS if pattern.search(text)]
        if hits:
            raise RuntimeError(f"Sanitization failed for {path.name}: {hits}")


def main() -> None:
    marker_summary = json.loads((B21_DIR / "b21b_known_positive_validation_summary_sanitized.json").read_text(encoding="utf-8"))
    if marker_summary.get("known_positive_case_validation") != "passed_direct_cell_markers":
        raise RuntimeError("B2.2 blocked: B2.1b known-positive validation is not passed.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    files: list[Path] = []
    for root in SOURCE_ROOTS:
        files.extend(sorted(root.rglob("*.xls*")))
    rows: list[dict[str, Any]] = []
    for path in sorted(files):
        rows.extend(iter_snapshot_rows(path))

    by_bucket: list[dict[str, Any]] = []
    for family, doc_type in sorted({(r["family"], r["doc_type"]) for r in rows}):
        subset = [r for r in rows if r["family"] == family and r["doc_type"] == doc_type]
        snapshot_rows = len(subset)
        estimated_events = len({r["estimated_event_key"] for r in subset})
        estimated_day_events = len({r["estimated_event_key_with_snapshot_date"] for r in subset})
        by_bucket.append(
            {
                "family": family,
                "doc_type": doc_type,
                "snapshot_rows": snapshot_rows,
                "estimated_events": estimated_events,
                "estimated_events_with_snapshot_date": estimated_day_events,
                "compression_ratio": round(snapshot_rows / estimated_events, 6) if estimated_events else 0,
                "date_sensitive_compression_ratio": round(snapshot_rows / estimated_day_events, 6) if estimated_day_events else 0,
                "asset_ref_present_rows": sum(r["asset_ref_status"] == "present" for r in subset),
                "asset_ref_present_rate": round(sum(r["asset_ref_status"] == "present" for r in subset) / snapshot_rows, 6) if snapshot_rows else 0,
                "code_ref_present_rows": sum(r["code_ref_status"] == "present" for r in subset),
                "code_ref_present_rate": round(sum(r["code_ref_status"] == "present" for r in subset) / snapshot_rows, 6) if snapshot_rows else 0,
            }
        )

    doc_rows: list[dict[str, Any]] = []
    for doc_type in sorted({r["doc_type"] for r in rows}):
        subset = [r for r in rows if r["doc_type"] == doc_type]
        snapshot_rows = len(subset)
        estimated_events = len({r["estimated_event_key"] for r in subset})
        estimated_day_events = len({r["estimated_event_key_with_snapshot_date"] for r in subset})
        doc_rows.append(
            {
                "doc_type": doc_type,
                "snapshot_rows": snapshot_rows,
                "estimated_events": estimated_events,
                "estimated_events_with_snapshot_date": estimated_day_events,
                "compression_ratio": round(snapshot_rows / estimated_events, 6) if estimated_events else 0,
                "date_sensitive_compression_ratio": round(snapshot_rows / estimated_day_events, 6) if estimated_day_events else 0,
                "asset_ref_present_rate": round(sum(r["asset_ref_status"] == "present" for r in subset) / snapshot_rows, 6) if snapshot_rows else 0,
                "code_ref_present_rate": round(sum(r["code_ref_status"] == "present" for r in subset) / snapshot_rows, 6) if snapshot_rows else 0,
            }
        )

    fieldnames = [
        "snapshot_row_id",
        "estimated_event_key",
        "estimated_event_key_with_snapshot_date",
        "file_key",
        "sheet_key",
        "family",
        "doc_type",
        "snapshot_date_bucket",
        "asset_key",
        "asset_ref_status",
        "code_key",
        "code_ref_status",
        "candidate_text_field_count",
        "candidate_text_categories",
        "row_signature",
        "dedup_method",
        "raw_operational_values_emitted",
    ]
    write_csv(OUTPUT_DIR / "b22_snapshot_rows_sanitized.csv", rows, fieldnames)
    write_csv(
        OUTPUT_DIR / "b22_snapshot_dedup_by_bucket_sanitized.csv",
        by_bucket,
        [
            "family",
            "doc_type",
            "snapshot_rows",
            "estimated_events",
            "estimated_events_with_snapshot_date",
            "compression_ratio",
            "date_sensitive_compression_ratio",
            "asset_ref_present_rows",
            "asset_ref_present_rate",
            "code_ref_present_rows",
            "code_ref_present_rate",
        ],
    )
    write_csv(
        OUTPUT_DIR / "b22_snapshot_dedup_by_doc_type_sanitized.csv",
        doc_rows,
        [
            "doc_type",
            "snapshot_rows",
            "estimated_events",
            "estimated_events_with_snapshot_date",
            "compression_ratio",
            "date_sensitive_compression_ratio",
            "asset_ref_present_rate",
            "code_ref_present_rate",
        ],
    )

    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "pass_id": "B2.2",
        "task_type": "snapshot_deduplication",
        "source_pass": "B2.1_plus_B2.1b",
        "files_scanned": len(files),
        "snapshot_rows": len(rows),
        "estimated_events": len({r["estimated_event_key"] for r in rows}),
        "estimated_events_with_snapshot_date": len({r["estimated_event_key_with_snapshot_date"] for r in rows}),
        "overall_compression_ratio": round(len(rows) / len({r["estimated_event_key"] for r in rows}), 6) if rows else 0,
        "date_sensitive_compression_ratio": round(len(rows) / len({r["estimated_event_key_with_snapshot_date"] for r in rows}), 6) if rows else 0,
        "doc_type_counts": dict(sorted(Counter(r["doc_type"] for r in rows).items())),
        "known_positive_case_validation": "passed_direct_cell_markers",
        "dedup_unit": "estimated_event_key",
        "dedup_method": "family_doc_type_asset_code_text_signature",
        "limitation": "No duration-based incident_start estimate was used because B2 XLSX duration semantics are not yet validated.",
        "raw_operational_values_emitted": False,
        "outputs": [
            "b22_snapshot_dedup_memo.md",
            "b22_snapshot_rows_sanitized.csv",
            "b22_snapshot_dedup_by_bucket_sanitized.csv",
            "b22_snapshot_dedup_by_doc_type_sanitized.csv",
            "b22_snapshot_dedup_summary_sanitized.json",
        ],
    }
    (OUTPUT_DIR / "b22_snapshot_dedup_summary_sanitized.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    doc_table = [
        f"| {r['doc_type']} | {r['snapshot_rows']} | {r['estimated_events']} | {r['compression_ratio']} | {r['estimated_events_with_snapshot_date']} | {r['date_sensitive_compression_ratio']} | {r['asset_ref_present_rate']} | {r['code_ref_present_rate']} |"
        for r in doc_rows
    ]
    memo = "\n".join(
        [
            "# B2.2 Snapshot Deduplication",
            "",
            "## Scope",
            "",
            "This pass estimates event compression for B2 snapshot workbooks after the XLSX known-positive control passed. It keeps `snapshot_rows` and `estimated_events` separate.",
            "",
            "## Summary",
            "",
            f"- Files scanned: `{summary['files_scanned']}`",
            f"- Snapshot rows: `{summary['snapshot_rows']}`",
            f"- Estimated events: `{summary['estimated_events']}`",
            f"- Compression ratio: `{summary['overall_compression_ratio']}`",
            f"- Date-sensitive estimated events: `{summary['estimated_events_with_snapshot_date']}`",
            f"- Date-sensitive compression ratio: `{summary['date_sensitive_compression_ratio']}`",
            f"- Dedup method: `{summary['dedup_method']}`",
            "",
            "## By Document Type",
            "",
            "| doc_type | snapshot_rows | estimated_events | compression_ratio | date_sensitive_events | date_sensitive_ratio | asset_ref_present_rate | code_ref_present_rate |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
            *doc_table,
            "",
            "## Interpretation",
            "",
            "The non-date event key estimates persistence across daily snapshots. The date-sensitive key is provided as a conservative upper bound that avoids merging repeated work on different days.",
            "",
            "No target evidence is promoted here. B2.2 only establishes deduplication accounting for downstream B2.3 extraction and weak supervision.",
            "",
            "raw_operational_values_emitted: false",
            "",
        ]
    )
    (OUTPUT_DIR / "b22_snapshot_dedup_memo.md").write_text(memo, encoding="utf-8")
    assert_sanitized(list(OUTPUT_DIR.glob("b22_*")))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
