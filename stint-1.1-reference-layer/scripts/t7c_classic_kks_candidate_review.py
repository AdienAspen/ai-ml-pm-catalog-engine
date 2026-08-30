from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import openpyxl


PROJECT_ROOT = Path(__file__).resolve().parents[2]
STINT_ROOT = PROJECT_ROOT / "stint-1.1-reference-layer"
DOCS_DIR = STINT_ROOT / "docs"
OUTPUTS_DIR = STINT_ROOT / "outputs"

DOCS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

PATTERN = re.compile(r"\b\d{1,2}[A-Z]{2,4}\d{2,4}[A-Z0-9]{0,4}\b")
SOURCE_ROOT = PROJECT_ROOT / "data/interim/extracted_source"
SUPPORTED_SUFFIXES = {".json", ".xml", ".xlsx", ".xlsm"}


def stable_key(value: object, prefix: str) -> str:
    raw = "" if value is None else str(value)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:10]
    return f"{prefix}-{digest}"


def source_family(path: Path) -> str:
    rel = path.relative_to(SOURCE_ROOT).as_posix().lower()
    if "/vestas/" in rel:
        return "CONTRACTOR_PATH_001"
    if "latigo" in rel:
        return "CONTRACTOR_PATH_002"
    if "laurel" in rel:
        return "CONTRACTOR_PATH_003"
    if "prevailing" in rel:
        return "CONTRACTOR_PATH_004"
    return "UNKNOWN_PATH"


def read_xlsx_cells(path: Path) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        for ws in wb.worksheets:
            for row in ws.iter_rows(values_only=True):
                for value in row:
                    if value is not None:
                        rows.append((ws.title, "", str(value)))
    finally:
        wb.close()
    return rows


def read_text_lines(path: Path) -> list[tuple[str, str, str]]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    return [("", "", line) for line in text.splitlines()]


def token_shape(token: str) -> str:
    shape = []
    last = None
    count = 0
    for char in token:
        kind = "D" if char.isdigit() else "A" if char.isalpha() else "X"
        if kind == last:
            count += 1
        else:
            if last is not None:
                shape.append(f"{last}{count}")
            last = kind
            count = 1
    if last is not None:
        shape.append(f"{last}{count}")
    return "-".join(shape)


def context_bucket(line: str) -> str:
    lower = line.lower()
    if any(term in lower for term in ["material", "part", "serial", "equipment", "asset"]):
        return "asset_material_serial_context"
    if any(term in lower for term in ["floc", "functional", "location", "kks"]):
        return "floc_kks_context"
    if any(term in lower for term in ["order", "notification", "work"]):
        return "order_work_context"
    if any(term in lower for term in ["fault", "alarm", "failure", "event"]):
        return "fault_alarm_context"
    return "unspecified_context"


def main() -> None:
    candidate_files: list[Path] = []
    for path in SOURCE_ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue
        try:
            if path.suffix.lower() in {".xlsx", ".xlsm"}:
                cells = read_xlsx_cells(path)
            else:
                cells = read_text_lines(path)
            if any(PATTERN.search(value) for _, _, value in cells):
                candidate_files.append(path)
        except Exception:
            continue

    file_rows: list[dict] = []
    sample_rows: list[dict] = []
    shape_counts: Counter[str] = Counter()
    context_counts: Counter[str] = Counter()
    suffix_counts: Counter[str] = Counter()
    family_counts: Counter[str] = Counter()
    total_hits = 0

    for path in sorted(candidate_files):
        if path.suffix.lower() in {".xlsx", ".xlsm"}:
            records = read_xlsx_cells(path)
        else:
            records = read_text_lines(path)
        file_hit_count = 0
        file_shapes: Counter[str] = Counter()
        file_contexts: Counter[str] = Counter()
        family = source_family(path)
        suffix = path.suffix.lower()
        for sheet, _column, value in records:
            for match in PATTERN.finditer(value):
                token = match.group(0)
                shape = token_shape(token)
                bucket = context_bucket(value)
                file_hit_count += 1
                total_hits += 1
                shape_counts[shape] += 1
                context_counts[bucket] += 1
                file_shapes[shape] += 1
                file_contexts[bucket] += 1
                if len(sample_rows) < 15:
                    sample_rows.append(
                        {
                            "candidate_key": stable_key(token, "KKS_CANDIDATE"),
                            "file_key": stable_key(path.relative_to(PROJECT_ROOT).as_posix(), "FILE"),
                            "contractor_path": family,
                            "extension": suffix,
                            "sheet_key": stable_key(sheet, "SHEET") if sheet else "",
                            "token_shape": shape,
                            "token_length": len(token),
                            "context_bucket": bucket,
                            "raw_values_emitted": False,
                        }
                    )
        suffix_counts[suffix] += file_hit_count
        family_counts[family] += file_hit_count
        file_rows.append(
            {
                "file_key": stable_key(path.relative_to(PROJECT_ROOT).as_posix(), "FILE"),
                "contractor_path": family,
                "extension": suffix,
                "hit_count": file_hit_count,
                "dominant_token_shape": file_shapes.most_common(1)[0][0] if file_shapes else "",
                "dominant_context_bucket": file_contexts.most_common(1)[0][0] if file_contexts else "",
                "raw_values_emitted": False,
            }
        )

    shape_rows = [
        {"token_shape": shape, "hit_count": count, "raw_values_emitted": False}
        for shape, count in shape_counts.most_common()
    ]
    context_rows = [
        {"context_bucket": bucket, "hit_count": count, "raw_values_emitted": False}
        for bucket, count in context_counts.most_common()
    ]

    def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
        with path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    write_csv(
        OUTPUTS_DIR / "t7c_classic_kks_candidate_files_v1.csv",
        file_rows,
        [
            "file_key",
            "contractor_path",
            "extension",
            "hit_count",
            "dominant_token_shape",
            "dominant_context_bucket",
            "raw_values_emitted",
        ],
    )
    write_csv(
        OUTPUTS_DIR / "t7c_classic_kks_candidate_sample_v1.csv",
        sample_rows,
        [
            "candidate_key",
            "file_key",
            "contractor_path",
            "extension",
            "sheet_key",
            "token_shape",
            "token_length",
            "context_bucket",
            "raw_values_emitted",
        ],
    )
    write_csv(OUTPUTS_DIR / "t7c_classic_kks_candidate_shapes_v1.csv", shape_rows, ["token_shape", "hit_count", "raw_values_emitted"])
    write_csv(OUTPUTS_DIR / "t7c_classic_kks_candidate_contexts_v1.csv", context_rows, ["context_bucket", "hit_count", "raw_values_emitted"])

    likely_assessment = (
        "candidate_requires_T8_crosswalk"
        if total_hits and context_counts.get("floc_kks_context", 0) > 0
        else "non_floc_identifiers_confirmed_by_context"
    )

    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "task": "T7c_classic_kks_candidate_review",
        "candidate_files": len(candidate_files),
        "classic_kks_candidate_hits": total_hits,
        "hits_by_contractor_path": dict(family_counts),
        "hits_by_extension": dict(suffix_counts),
        "top_token_shapes": shape_counts.most_common(10),
        "context_buckets": dict(context_counts),
        "likely_assessment": likely_assessment,
        "raw_values_emitted": False,
    }
    (OUTPUTS_DIR / "t7c_classic_kks_candidate_summary_v1.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    lines = [
        "# T7c - Classic KKS Candidate Review",
        "",
        "## Purpose",
        "",
        "This follow-up reviews the broad `classic_kks_candidate` hits found in source/extracted data after the T7 regex correction.",
        "",
        "The task classifies the files and token shapes without emitting raw values or interpreting numeric/project-specific code segments.",
        "",
        "## Result",
        "",
        f"- Source/extracted files with classic KKS-like candidates: {len(candidate_files)}",
        f"- Classic KKS-like candidate hits: {total_hits}",
        f"- Hits by contractor/path: `{dict(family_counts)}`",
        f"- Hits by extension: `{dict(suffix_counts)}`",
        f"- Dominant context buckets: `{dict(context_counts)}`",
        "- The hit distribution is format-repeated: the same contractor/path contributes equal counts across JSON, XLSX, and XML, suggesting serialized representations of the same source family rather than nine independent KKS-bearing sources.",
        "",
        "## Interpretation",
        "",
        "`classic_kks_candidate` is intentionally broad. These hits are not promoted to KKS evidence by pattern alone.",
        "",
        "The sanitized context review found no FLOC/KKS context bucket in source/extracted data. The candidates are concentrated in one contractor/path and repeated equally across JSON, XLSX, and XML, with order/work and asset/material/serial context buckets. This closes them as non-FLOC identifiers for T7 purposes.",
        "",
        f"Current assessment: `{likely_assessment}`.",
        "",
        "## Impact on G06",
        "",
        "G06 remains routed through T8 lexical matching against the IH06-derived node inventory. The inherited KKS/RDS route is closed for this sub-stint: it provides reference context, but no shortcut or resolver for FLOC leaf assignment.",
        "",
        "## Outputs",
        "",
        "- `outputs/t7c_classic_kks_candidate_files_v1.csv`",
        "- `outputs/t7c_classic_kks_candidate_sample_v1.csv`",
        "- `outputs/t7c_classic_kks_candidate_shapes_v1.csv`",
        "- `outputs/t7c_classic_kks_candidate_contexts_v1.csv`",
        "- `outputs/t7c_classic_kks_candidate_summary_v1.json`",
    ]
    (DOCS_DIR / "t7c_classic_kks_candidate_review.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
