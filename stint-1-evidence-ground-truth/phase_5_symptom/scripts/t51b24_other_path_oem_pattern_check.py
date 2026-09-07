from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from openpyxl import load_workbook


PROJECT_ROOT = Path("/home/adien-i7-remote/workspace/fsa_bridge_ml_feasibility")
STINT_ROOT = PROJECT_ROOT / "stint-1-evidence-ground-truth"
OUTPUT_DIR = STINT_ROOT / "phase_5_symptom/outputs/f51_symptom_thread_resolution"
PATH_A_NOTES = PROJECT_ROOT / "reports/internal/path_a_repair/f352b_notes_region_text_internal.csv"
PATH_A_CONCERN = PROJECT_ROOT / "reports/internal/pdf_assets_of_concern_rows.csv"
B21_SCRIPT = STINT_ROOT / "phase_4_path_b_xlsx/scripts/b21_snapshot_characterization.py"

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


def clean_text(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value).strip())


def extract_oem(text: str) -> list[dict[str, str]]:
    matches: list[dict[str, str]] = []
    seen = set()
    for pattern_name, pattern in PATTERNS:
        for match in pattern.finditer(text):
            code = match.group("code").strip()
            desc = clean_text(match.group("desc"))
            if len(code) < 3 or len(desc) < 4:
                continue
            key = (pattern_name, code, desc.lower())
            if key in seen:
                continue
            seen.add(key)
            matches.append(
                {
                    "pattern_position": pattern_name,
                    "code_hash": prefixed_hash(code, "OEMCODE", 10),
                    "description_hash": prefixed_hash(desc.lower(), "OEMDESC", 10),
                }
            )
    return matches


def import_b21_module():
    spec = importlib.util.spec_from_file_location("b21_snapshot_characterization", B21_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not import B2 characterization helpers.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def iter_path_a_notes() -> list[dict[str, str]]:
    if not PATH_A_NOTES.exists():
        return []
    df = pd.read_csv(PATH_A_NOTES, dtype=str).fillna("")
    rows = []
    for idx, row in enumerate(df.to_dict("records")):
        text = clean_text(row.get("notes_region_text"))
        if not text:
            continue
        rows.append(
            {
                "path_bucket": "PATH_A_NOTES",
                "source_text_field": "pdf_notes_region.notes_region_text",
                "record_hash": prefixed_hash(f"PATH_A_NOTES|{row.get('file_hash','')}|{idx}", "REC", 14),
                "text": text,
            }
        )
    return rows


def iter_path_a_concern() -> list[dict[str, str]]:
    if not PATH_A_CONCERN.exists():
        return []
    df = pd.read_csv(PATH_A_CONCERN, dtype=str).fillna("")
    rows = []
    for idx, row in enumerate(df.to_dict("records")):
        text = clean_text(row.get("event"))
        if not text:
            continue
        rows.append(
            {
                "path_bucket": "PATH_A_CONCERN_TABLE",
                "source_text_field": "pdf_assets_of_concern.event",
                "record_hash": prefixed_hash(f"PATH_A_CONCERN|{row.get('file_hash','')}|{idx}", "REC", 14),
                "text": text,
            }
        )
    return rows


def iter_b2_workbook_text() -> list[dict[str, str]]:
    b21 = import_b21_module()
    files: list[Path] = []
    for root in b21.SOURCE_GLOBS:
        files.extend(sorted(root.rglob("*.xls*")))
    rows_out: list[dict[str, str]] = []
    for path in sorted(files):
        family, doc_type = b21.family_for_path(path)
        file_key = prefixed_hash(str(path.relative_to(PROJECT_ROOT)), "B2FILE", 12)
        try:
            wb = load_workbook(path, read_only=True, data_only=True)
        except Exception:
            continue
        for sheet_index, ws in enumerate(wb.worksheets, start=1):
            sample_rows = []
            for row in ws.iter_rows(min_row=1, max_row=min(ws.max_row or 1, 30), max_col=min(ws.max_column or 1, 30), values_only=True):
                sample_rows.append([b21.clean_text(v) for v in row])
            header_row, headers = b21.likely_header_row(sample_rows)
            if not header_row or not headers:
                continue
            categories = [b21.categorize_header(h) for h in headers]
            text_positions = [i + 1 for i, c in enumerate(categories) if c in {"notes_text", "work_text", "issue_text"}]
            if not text_positions:
                continue
            max_col = max(len(headers), max(text_positions))
            for row_number, row in enumerate(ws.iter_rows(min_row=header_row + 1, max_col=max_col, values_only=True), start=header_row + 1):
                row_values = [b21.clean_text(v) for v in row]
                for pos in text_positions:
                    text = row_values[pos - 1] if pos - 1 < len(row_values) else ""
                    if len(text) < 8:
                        continue
                    rows_out.append(
                        {
                            "path_bucket": "B2_WORKBOOKS",
                            "source_text_field": f"xlsx_snapshot.{categories[pos - 1]}",
                            "record_hash": prefixed_hash(f"{file_key}|{sheet_index}|{row_number}|{pos}", "B2TXT", 14),
                            "text": text,
                            "family": family,
                            "doc_type": doc_type,
                        }
                    )
        wb.close()
    return rows_out


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
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    text_rows = iter_path_a_notes() + iter_path_a_concern() + iter_b2_workbook_text()

    match_rows = []
    for row in text_rows:
        matches = extract_oem(row["text"])
        for match in matches:
            match_rows.append(
                {
                    "path_bucket": row["path_bucket"],
                    "source_text_field": row["source_text_field"],
                    "record_hash": row["record_hash"],
                    "pattern_position": match["pattern_position"],
                    "code_hash": match["code_hash"],
                    "description_hash": match["description_hash"],
                    "raw_operational_values_emitted": False,
                }
            )

    text_df = pd.DataFrame(text_rows)
    match_df = pd.DataFrame(match_rows)

    verdict_rows = []
    for path_bucket in ["PATH_A_NOTES", "PATH_A_CONCERN_TABLE", "B2_WORKBOOKS"]:
        scoped = text_df[text_df["path_bucket"].eq(path_bucket)] if not text_df.empty else pd.DataFrame()
        matches = match_df[match_df["path_bucket"].eq(path_bucket)] if not match_df.empty else pd.DataFrame()
        rows_with_match = matches["record_hash"].nunique() if not matches.empty else 0
        verdict_rows.append(
            {
                "path_bucket": path_bucket,
                "text_rows_evaluated": int(len(scoped)),
                "rows_with_oem_pattern": int(rows_with_match),
                "pct_rows_with_oem_pattern": pct(int(rows_with_match), int(len(scoped))),
                "oem_occurrence_rows": int(len(matches)),
                "distinct_code_hashes": int(matches["code_hash"].nunique()) if not matches.empty else 0,
                "distinct_code_description_pairs": int(matches[["code_hash", "description_hash"]].drop_duplicates().shape[0]) if not matches.empty else 0,
                "verdict": "pattern_present" if rows_with_match else "pattern_not_observed",
                "raw_operational_values_emitted": False,
            }
        )

    field_rows = []
    if not match_df.empty:
        grouped = match_df.groupby(["path_bucket", "source_text_field", "pattern_position"], dropna=False)
        for (path_bucket, source_text_field, pattern_position), group in grouped:
            field_rows.append(
                {
                    "path_bucket": path_bucket,
                    "source_text_field": source_text_field,
                    "pattern_position": pattern_position,
                    "oem_occurrence_rows": int(len(group)),
                    "rows_with_oem_pattern": int(group["record_hash"].nunique()),
                    "distinct_code_hashes": int(group["code_hash"].nunique()),
                    "raw_operational_values_emitted": False,
                }
            )

    summary = {
        "created_at_utc": utc_now(),
        "pass_id": "T5.1b2.4",
        "task_type": "other_path_oem_pattern_check",
        "question": "Is the OEM alarm-code-description structure exclusive to the relational path?",
        "answer": "not_exclusive" if any(row["rows_with_oem_pattern"] for row in verdict_rows if row["path_bucket"] != "PATH_A_CONCERN_TABLE") else "not_observed_outside_relational_path",
        "path_verdicts": {
            row["path_bucket"]: {
                "text_rows_evaluated": row["text_rows_evaluated"],
                "rows_with_oem_pattern": row["rows_with_oem_pattern"],
                "pct_rows_with_oem_pattern": row["pct_rows_with_oem_pattern"],
                "distinct_code_hashes": row["distinct_code_hashes"],
                "verdict": row["verdict"],
            }
            for row in verdict_rows
        },
        "classification_action": "pattern_crosscheck_only_no_sap_mapping_no_denominator_promotion",
        "raw_operational_values_emitted_to_versioned_artifacts": False,
    }

    verdict_path = OUTPUT_DIR / "t51b24_other_path_oem_pattern_verdict_sanitized.csv"
    field_path = OUTPUT_DIR / "t51b24_other_path_oem_pattern_by_field_sanitized.csv"
    summary_path = OUTPUT_DIR / "t51b24_other_path_oem_pattern_summary_sanitized.json"
    memo_path = OUTPUT_DIR / "t51b24_other_path_oem_pattern_memo.md"

    write_csv(
        verdict_path,
        verdict_rows,
        [
            "path_bucket",
            "text_rows_evaluated",
            "rows_with_oem_pattern",
            "pct_rows_with_oem_pattern",
            "oem_occurrence_rows",
            "distinct_code_hashes",
            "distinct_code_description_pairs",
            "verdict",
            "raw_operational_values_emitted",
        ],
    )
    write_csv(
        field_path,
        field_rows,
        [
            "path_bucket",
            "source_text_field",
            "pattern_position",
            "oem_occurrence_rows",
            "rows_with_oem_pattern",
            "distinct_code_hashes",
            "raw_operational_values_emitted",
        ],
    )
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    memo_lines = [
        "# T5.1b2.4 - Other Path OEM Pattern Check",
        "",
        "## Purpose",
        "",
        "Check whether the OEM alarm-code-description structure observed in the relational `reason` field is exclusive to that path, or also appears in Path A and B2 sources.",
        "",
        "## Verdict By Path",
        "",
        "| Path bucket | Text rows evaluated | Rows with OEM pattern | Distinct codes | Verdict |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for row in verdict_rows:
        memo_lines.append(
            f"| `{row['path_bucket']}` | {row['text_rows_evaluated']} | {row['rows_with_oem_pattern']} ({row['pct_rows_with_oem_pattern']}%) | {row['distinct_code_hashes']} | `{row['verdict']}` |"
        )
    memo_lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "This is a pattern cross-check only. It does not map OEM codes to SAP, classify Symptom, or promote any evidence to a denominator.",
            "",
            f"Overall answer: `{summary['answer']}`.",
        ]
    )
    memo_path.write_text("\n".join(memo_lines) + "\n", encoding="utf-8")

    assert_sanitized([verdict_path, field_path, summary_path, memo_path])
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
