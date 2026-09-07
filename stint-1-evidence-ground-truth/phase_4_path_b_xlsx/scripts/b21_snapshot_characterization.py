from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from openpyxl import load_workbook


PROJECT_ROOT = Path("/home/adien-i7-remote/workspace/fsa_bridge_ml_feasibility")
OUTPUT_DIR = PROJECT_ROOT / "stint-1-evidence-ground-truth/phase_4_path_b_xlsx/outputs/b2_snapshot_characterization"

SOURCE_GLOBS = [
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
    text = str(value).strip()
    text = re.sub(r"\s+", " ", text)
    return text


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


def month_bucket(path: Path) -> str:
    name = path.name.lower()
    m = re.search(r"(20\d{2})[ _.-]+(\d{1,2})", name)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}"
    m = re.search(r"(\d{1,2})[ _.-]+(\d{1,2})[ _.-]+(20\d{2})", name)
    if m:
        return f"{m.group(3)}-{int(m.group(1)):02d}"
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
            if y:
                return f"{y.group(1)}-{num:02d}"
    return "unknown_month"


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
            best_values = non_empty
    return best_idx, best_values


def sheet_sample(ws, max_rows: int = 30, max_cols: int = 30) -> list[list[str]]:
    rows: list[list[str]] = []
    for row in ws.iter_rows(min_row=1, max_row=min(ws.max_row or 1, max_rows), max_col=min(ws.max_column or 1, max_cols), values_only=True):
        rows.append([clean_text(v) for v in row])
    return rows


def non_empty_rows(ws) -> int:
    count = 0
    for row in ws.iter_rows(values_only=True):
        if any(clean_text(v) for v in row):
            count += 1
    return count


def text_density_from_header(ws, header_row: int | None, headers: list[str]) -> dict[str, Any]:
    if not header_row or not headers:
        return {"candidate_text_columns": 0, "candidate_text_categories": "", "rows_with_candidate_text": 0}
    categories = [categorize_header(h) for h in headers]
    candidate_positions = [i + 1 for i, c in enumerate(categories) if c in {"notes_text", "work_text", "issue_text"}]
    rows_with_text = 0
    if candidate_positions:
        for row in ws.iter_rows(min_row=header_row + 1, max_col=max(candidate_positions), values_only=True):
            if any(len(clean_text(row[pos - 1] if pos - 1 < len(row) else "")) >= 8 for pos in candidate_positions):
                rows_with_text += 1
    return {
        "candidate_text_columns": len(candidate_positions),
        "candidate_text_categories": ",".join(sorted(set(categories[pos - 1] for pos in candidate_positions))),
        "rows_with_candidate_text": rows_with_text,
    }


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def scan() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    files: list[Path] = []
    for root in SOURCE_GLOBS:
        files.extend(sorted(root.rglob("*.xls*")))
    file_rows: list[dict[str, Any]] = []
    sheet_rows: list[dict[str, Any]] = []
    text_rows: list[dict[str, Any]] = []
    template_counter: Counter[str] = Counter()
    template_files: defaultdict[str, set[str]] = defaultdict(set)
    failures: list[dict[str, str]] = []

    for path in sorted(files):
        family, doc_type = family_for_path(path)
        file_key = short_hash(str(path.relative_to(PROJECT_ROOT)), "B2FILE")
        try:
            wb = load_workbook(path, read_only=True, data_only=True)
        except Exception as exc:  # noqa: BLE001
            failures.append({"file_key": file_key, "family": family, "error_type": type(exc).__name__})
            continue

        sheet_names = wb.sheetnames
        sheet_sig_parts = []
        total_non_empty_rows = 0
        total_text_rows = 0
        header_categories_all: list[str] = []
        for ws in wb.worksheets:
            sample = sheet_sample(ws)
            header_row, headers = likely_header_row(sample)
            categories = [categorize_header(h) for h in headers]
            category_counts = Counter(categories)
            header_sig = short_hash("|".join(sorted(categories)) + f"|{len(headers)}", "HDRSIG")
            sheet_sig_parts.append(f"{ws.title}:{header_sig}")
            non_empty = non_empty_rows(ws)
            density = text_density_from_header(ws, header_row, headers)
            total_non_empty_rows += non_empty
            total_text_rows += int(density["rows_with_candidate_text"])
            header_categories_all.extend(categories)
            sheet_key = short_hash(str(path.relative_to(PROJECT_ROOT)) + "|" + ws.title, "B2SHEET")
            sheet_rows.append(
                {
                    "file_key": file_key,
                    "sheet_key": sheet_key,
                    "family": family,
                    "doc_type": doc_type,
                    "month_bucket": month_bucket(path),
                    "sheet_index": len(sheet_rows) + 1,
                    "max_rows": ws.max_row,
                    "max_columns": ws.max_column,
                    "non_empty_rows": non_empty,
                    "header_row_detected": header_row or "",
                    "header_signature": header_sig,
                    "header_category_counts": json.dumps(dict(sorted(category_counts.items()))),
                    **density,
                }
            )
            if density["candidate_text_columns"]:
                text_rows.append(
                    {
                        "file_key": file_key,
                        "sheet_key": sheet_key,
                        "family": family,
                        "doc_type": doc_type,
                        "month_bucket": month_bucket(path),
                        "header_signature": header_sig,
                        "candidate_text_columns": density["candidate_text_columns"],
                        "candidate_text_categories": density["candidate_text_categories"],
                        "rows_with_candidate_text": density["rows_with_candidate_text"],
                    }
                )

        template_sig = short_hash("||".join(sorted(sheet_sig_parts)), "B2TPL")
        template_counter[template_sig] += 1
        template_files[template_sig].add(family)
        file_rows.append(
            {
                "file_key": file_key,
                "family": family,
                "doc_type": doc_type,
                "month_bucket": month_bucket(path),
                "sheet_count": len(sheet_names),
                "template_variant": template_sig,
                "non_empty_rows": total_non_empty_rows,
                "rows_with_candidate_text": total_text_rows,
                "header_category_counts": json.dumps(dict(sorted(Counter(header_categories_all).items()))),
                "status": "read_ok",
            }
        )
        wb.close()

    template_rows = []
    for sig, count in template_counter.most_common():
        subset = [row for row in file_rows if row["template_variant"] == sig]
        template_rows.append(
            {
                "template_variant": sig,
                "file_count": count,
                "families": ",".join(sorted(template_files[sig])),
                "doc_types": ",".join(sorted(set(str(row["doc_type"]) for row in subset))),
                "month_buckets": ",".join(sorted(set(str(row["month_bucket"]) for row in subset))),
                "total_non_empty_rows": sum(int(row["non_empty_rows"]) for row in subset),
                "total_rows_with_candidate_text": sum(int(row["rows_with_candidate_text"]) for row in subset),
            }
        )

    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "pass_id": "B2.1",
        "task_type": "snapshot_workbook_template_characterization",
        "files_discovered": len(files),
        "files_read_ok": len(file_rows),
        "files_failed": len(failures),
        "families": dict(sorted(Counter(row["family"] for row in file_rows).items())),
        "doc_types": dict(sorted(Counter(row["doc_type"] for row in file_rows).items())),
        "template_variants": len(template_rows),
        "sheets_profiled": len(sheet_rows),
        "sheets_with_candidate_text": len(text_rows),
        "rows_with_candidate_text": sum(int(row["rows_with_candidate_text"]) for row in file_rows),
        "known_positive_case_validation": "pending_not_provided_for_b2_xlsx",
        "raw_operational_values_emitted": False,
        "outputs": [
            "b21_snapshot_characterization_memo.md",
            "b21_snapshot_file_inventory_sanitized.csv",
            "b21_snapshot_sheet_profile_sanitized.csv",
            "b21_snapshot_template_variants_sanitized.csv",
            "b21_snapshot_text_field_candidates_sanitized.csv",
            "b21_snapshot_summary_sanitized.json",
        ],
    }
    return file_rows, sheet_rows, template_rows, text_rows, summary


def assert_sanitized(paths: list[Path]) -> None:
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="ignore")
        hits = [pattern.pattern for pattern in RAW_PATTERNS if pattern.search(text)]
        if hits:
            raise RuntimeError(f"Sanitization failed for {path.name}: {hits}")


def memo(summary: dict[str, Any], template_rows: list[dict[str, Any]]) -> str:
    top_templates = template_rows[:8]
    template_lines = [
        f"| {row['template_variant']} | {row['file_count']} | {row['families']} | {row['doc_types']} | {row['month_buckets']} | {row['total_rows_with_candidate_text']} |"
        for row in top_templates
    ]
    return "\n".join(
        [
            "# B2.1 Snapshot Workbook Characterization",
            "",
            "## Scope",
            "",
            "This pass characterizes snapshot-style workbooks before extraction. It inventories workbook families, detects template variants through sheet/header signatures, and identifies candidate prose-bearing areas without emitting operational values.",
            "",
            "## Summary",
            "",
            f"- Files discovered: `{summary['files_discovered']}`",
            f"- Files read OK: `{summary['files_read_ok']}`",
            f"- Files failed: `{summary['files_failed']}`",
            f"- Template variants: `{summary['template_variants']}`",
            f"- Sheets profiled: `{summary['sheets_profiled']}`",
            f"- Sheets with candidate text: `{summary['sheets_with_candidate_text']}`",
            f"- Rows with candidate text: `{summary['rows_with_candidate_text']}`",
            f"- Known-positive validation: `{summary['known_positive_case_validation']}`",
            "",
            "## Top Template Variants",
            "",
            "| template_variant | file_count | families | doc_types | month_buckets | candidate_text_rows |",
            "| --- | ---: | --- | --- | --- | ---: |",
            *template_lines,
            "",
            "## Interpretation",
            "",
            "B2.1 is characterization only. No row is promoted to a target, no denominator is created, and no absence is interpreted until a known-positive workbook case is validated.",
            "",
            "B2 sources remain `event_structural`; they must not be mixed with planned/reactive strata from the relational branch.",
            "",
            "raw_operational_values_emitted: false",
            "",
        ]
    )


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    file_rows, sheet_rows, template_rows, text_rows, summary = scan()
    write_csv(
        OUTPUT_DIR / "b21_snapshot_file_inventory_sanitized.csv",
        file_rows,
        ["file_key", "family", "doc_type", "month_bucket", "sheet_count", "template_variant", "non_empty_rows", "rows_with_candidate_text", "header_category_counts", "status"],
    )
    write_csv(
        OUTPUT_DIR / "b21_snapshot_sheet_profile_sanitized.csv",
        sheet_rows,
        ["file_key", "sheet_key", "family", "doc_type", "month_bucket", "sheet_index", "max_rows", "max_columns", "non_empty_rows", "header_row_detected", "header_signature", "header_category_counts", "candidate_text_columns", "candidate_text_categories", "rows_with_candidate_text"],
    )
    write_csv(
        OUTPUT_DIR / "b21_snapshot_template_variants_sanitized.csv",
        template_rows,
        ["template_variant", "file_count", "families", "doc_types", "month_buckets", "total_non_empty_rows", "total_rows_with_candidate_text"],
    )
    write_csv(
        OUTPUT_DIR / "b21_snapshot_text_field_candidates_sanitized.csv",
        text_rows,
        ["file_key", "sheet_key", "family", "doc_type", "month_bucket", "header_signature", "candidate_text_columns", "candidate_text_categories", "rows_with_candidate_text"],
    )
    (OUTPUT_DIR / "b21_snapshot_summary_sanitized.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (OUTPUT_DIR / "b21_snapshot_characterization_memo.md").write_text(memo(summary, template_rows), encoding="utf-8")
    assert_sanitized(list(OUTPUT_DIR.glob("b21_*")))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
