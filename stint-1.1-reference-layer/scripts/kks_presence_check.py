from __future__ import annotations

import csv
import json
import re
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import openpyxl
import pdfplumber


PROJECT_ROOT = Path(__file__).resolve().parents[2]
STINT_ROOT = PROJECT_ROOT / "stint-1.1-reference-layer"
OUTPUTS_DIR = STINT_ROOT / "outputs"
DOCS_DIR = STINT_ROOT / "docs"
SOURCE_DESIGNATIONS_DIR = STINT_ROOT / "reference_layer" / "source_designations"

OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR.mkdir(parents=True, exist_ok=True)
SOURCE_DESIGNATIONS_DIR.mkdir(parents=True, exist_ok=True)

RDS_PP_CODES = ["MDA", "MDK", "MDL", "MKA", "MSE", "MST", "MUD"]

PATTERNS = [
    {
        "pattern_id": "rds_pp_m_designation",
        "pattern_family": "rds_pp",
        "description": "RDS-PP-like mounted designation beginning with =M",
        "regex": re.compile(r"=M[A-Z0-9]{2,}", re.IGNORECASE),
        "emit_token": False,
    },
    {
        "pattern_id": "rds_pp_u_designation",
        "pattern_family": "rds_pp",
        "description": "RDS-PP-like mounted designation beginning with =U",
        "regex": re.compile(r"=U[A-Z0-9]{2,}", re.IGNORECASE),
        "emit_token": False,
    },
    {
        "pattern_id": "rds_pp_normative_letter_code",
        "pattern_family": "rds_pp",
        "description": "Normative/supporting RDS-PP letter codes referenced in the plan",
        "regex": re.compile(r"\b(?:" + "|".join(RDS_PP_CODES) + r")\b", re.IGNORECASE),
        "emit_token": True,
    },
    {
        "pattern_id": "classic_kks_candidate",
        "pattern_family": "kks_classic",
        "description": "Classic KKS-like alphanumeric designation candidate. Numeric project-specific portion is not interpreted.",
        "regex": re.compile(r"\b\d{1,2}[A-Z]{2,4}\d{2,4}[A-Z0-9]{0,4}\b"),
        "emit_token": False,
    },
]

TEXT_SUFFIXES = {
    ".csv",
    ".json",
    ".jsonl",
    ".md",
    ".txt",
    ".xml",
    ".html",
    ".htm",
    ".py",
    ".toml",
    ".yaml",
    ".yml",
}
ZIP_TEXT_SUFFIXES = {".docx", ".pptx"}
XLSX_SUFFIXES = {".xlsx", ".xlsm"}
PDF_SUFFIXES = {".pdf"}
SKIP_DIR_NAMES = {".git", ".venv", "__pycache__"}


def scope_for(path: Path) -> str:
    rel = path.relative_to(PROJECT_ROOT).as_posix()
    if rel.startswith("stint-1.1-reference-layer/"):
        return "reference_layer_artifact"
    if "/References/" in rel or "/latest/" in rel:
        return "reference_or_contract_source"
    if rel.startswith("data/interim/extracted_source/"):
        return "source_or_extracted_data"
    return "other_repo_source"


def iter_files() -> list[Path]:
    files = []
    for path in PROJECT_ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIR_NAMES for part in path.parts):
            continue
        if path.suffix.lower() == ".zip":
            continue
        if path.suffix.lower() in TEXT_SUFFIXES | ZIP_TEXT_SUFFIXES | XLSX_SUFFIXES | PDF_SUFFIXES:
            files.append(path)
    return sorted(files)


def read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def read_zip_text(path: Path) -> str:
    chunks: list[str] = []
    with zipfile.ZipFile(path) as zf:
        for name in zf.namelist():
            if name.endswith(".xml"):
                chunks.append(zf.read(name).decode("utf-8", errors="ignore"))
    return "\n".join(chunks)


def read_xlsx_text(path: Path) -> str:
    chunks: list[str] = []
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        for ws in wb.worksheets:
            chunks.append(str(ws.title))
            for row in ws.iter_rows(values_only=True):
                for value in row:
                    if value is not None:
                        chunks.append(str(value))
    finally:
        wb.close()
    return "\n".join(chunks)


def read_pdf_text(path: Path) -> str:
    chunks: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            chunks.append(page.extract_text(x_tolerance=1, y_tolerance=3) or "")
    return "\n".join(chunks)


def read_supported_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in TEXT_SUFFIXES:
        return read_text_file(path)
    if suffix in ZIP_TEXT_SUFFIXES:
        return read_zip_text(path)
    if suffix in XLSX_SUFFIXES:
        return read_xlsx_text(path)
    if suffix in PDF_SUFFIXES:
        return read_pdf_text(path)
    return ""


def scan_text(text: str) -> list[dict]:
    hits = []
    for pattern in PATTERNS:
        matches = list(pattern["regex"].finditer(text))
        if not matches:
            continue
        token_counts = Counter(m.group(0).upper() for m in matches) if pattern["emit_token"] else Counter()
        hits.append(
            {
                "pattern_id": pattern["pattern_id"],
                "pattern_family": pattern["pattern_family"],
                "hit_count": len(matches),
                "token_counts": token_counts,
            }
        )
    return hits


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    files = iter_files()
    by_pattern_scope: dict[tuple[str, str, str], dict] = {}
    by_scope_ext: dict[tuple[str, str], dict] = {}
    explicit_token_counts = Counter()
    errors = []

    for file_path in files:
        rel = file_path.relative_to(PROJECT_ROOT).as_posix()
        scope = scope_for(file_path)
        ext = file_path.suffix.lower() or "[no_extension]"
        scope_key = (scope, ext)
        by_scope_ext.setdefault(
            scope_key,
            {
                "scope": scope,
                "extension": ext,
                "files_scanned": 0,
                "files_with_any_hit": 0,
                "pattern_hit_count": 0,
                "raw_values_emitted": False,
            },
        )
        by_scope_ext[scope_key]["files_scanned"] += 1
        try:
            text = read_supported_text(file_path)
            hits = scan_text(text)
            if hits:
                by_scope_ext[scope_key]["files_with_any_hit"] += 1
            for hit in hits:
                pattern_key = (scope, ext, hit["pattern_id"])
                by_pattern_scope.setdefault(
                    pattern_key,
                    {
                        "scope": scope,
                        "extension": ext,
                        "pattern_id": hit["pattern_id"],
                        "pattern_family": hit["pattern_family"],
                        "files_with_hit": 0,
                        "hit_count": 0,
                        "raw_values_emitted": False,
                    },
                )
                by_pattern_scope[pattern_key]["files_with_hit"] += 1
                by_pattern_scope[pattern_key]["hit_count"] += hit["hit_count"]
                by_scope_ext[scope_key]["pattern_hit_count"] += hit["hit_count"]
                explicit_token_counts.update(hit["token_counts"])
        except Exception as exc:
            errors.append(
                {
                    "scope": scope,
                    "extension": ext,
                    "error_type": type(exc).__name__,
                    "raw_values_emitted": False,
                }
            )

    pattern_rows = sorted(by_pattern_scope.values(), key=lambda r: (r["scope"], r["extension"], r["pattern_id"]))
    scope_rows = sorted(by_scope_ext.values(), key=lambda r: (r["scope"], r["extension"]))
    token_rows = [
        {
            "normative_letter_code": code,
            "hit_count": explicit_token_counts.get(code, 0),
            "evidence_type": "reference_evidence",
            "tier": "silver-high",
            "source_note": "RDS-PP pattern list from STINT_1.1 plan; numeric project-specific segments are not interpreted.",
            "raw_values_emitted": False,
        }
        for code in RDS_PP_CODES
    ]
    error_rows = [
        {
            "scope": key[0],
            "extension": key[1],
            "error_type": key[2],
            "file_count": count,
            "raw_values_emitted": False,
        }
        for key, count in Counter((r["scope"], r["extension"], r["error_type"]) for r in errors).items()
    ]

    write_csv(
        OUTPUTS_DIR / "kks_presence_check_pattern_counts_v1.csv",
        pattern_rows,
        ["scope", "extension", "pattern_id", "pattern_family", "files_with_hit", "hit_count", "raw_values_emitted"],
    )
    write_csv(
        OUTPUTS_DIR / "kks_presence_check_scope_summary_v1.csv",
        scope_rows,
        ["scope", "extension", "files_scanned", "files_with_any_hit", "pattern_hit_count", "raw_values_emitted"],
    )
    write_csv(
        SOURCE_DESIGNATIONS_DIR / "rds_pp_normative_pattern_presence_v1.csv",
        token_rows,
        ["normative_letter_code", "hit_count", "evidence_type", "tier", "source_note", "raw_values_emitted"],
    )
    write_csv(
        OUTPUTS_DIR / "kks_presence_check_errors_v1.csv",
        error_rows,
        ["scope", "extension", "error_type", "file_count", "raw_values_emitted"],
    )

    total_hits = sum(row["hit_count"] for row in pattern_rows)
    total_files_with_hits = sum(row["files_with_any_hit"] for row in scope_rows)
    source_data_rows = [row for row in scope_rows if row["scope"] == "source_or_extracted_data"]
    source_data_pattern_rows = [row for row in pattern_rows if row["scope"] == "source_or_extracted_data"]
    source_data_files_scanned = sum(row["files_scanned"] for row in source_data_rows)
    source_data_files_with_hits = sum(row["files_with_any_hit"] for row in source_data_rows)
    source_data_pattern_hit_count = sum(row["pattern_hit_count"] for row in source_data_rows)
    source_data_classic_kks_hit_count = sum(
        row["hit_count"] for row in source_data_pattern_rows if row["pattern_id"] == "classic_kks_candidate"
    )
    source_data_rds_pp_hit_count = sum(
        row["hit_count"] for row in source_data_pattern_rows if row["pattern_family"] == "rds_pp"
    )
    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "task": "T7_KKS_presence_check",
        "files_scanned": len(files),
        "files_with_any_hit_scope_summed": total_files_with_hits,
        "pattern_hit_count": total_hits,
        "source_or_extracted_data_files_scanned": source_data_files_scanned,
        "source_or_extracted_data_files_with_any_hit": source_data_files_with_hits,
        "source_or_extracted_data_pattern_hit_count": source_data_pattern_hit_count,
        "source_or_extracted_data_classic_kks_candidate_hit_count": source_data_classic_kks_hit_count,
        "source_or_extracted_data_rds_pp_hit_count": source_data_rds_pp_hit_count,
        "pattern_rows": len(pattern_rows),
        "scan_errors": len(errors),
        "rds_pp_normative_codes_checked": len(RDS_PP_CODES),
        "rds_pp_normative_codes_with_hits": sum(1 for row in token_rows if row["hit_count"] > 0),
        "numeric_project_specific_segments_interpreted": False,
        "raw_values_emitted": False,
        "outputs": {
            "pattern_counts_csv": "stint-1.1-reference-layer/outputs/kks_presence_check_pattern_counts_v1.csv",
            "scope_summary_csv": "stint-1.1-reference-layer/outputs/kks_presence_check_scope_summary_v1.csv",
            "rds_pp_presence_csv": "stint-1.1-reference-layer/reference_layer/source_designations/rds_pp_normative_pattern_presence_v1.csv",
            "errors_csv": "stint-1.1-reference-layer/outputs/kks_presence_check_errors_v1.csv",
            "memo": "stint-1.1-reference-layer/docs/kks_presence_check.md",
        },
    }
    (OUTPUTS_DIR / "kks_presence_check_summary_v1.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    lines = [
        "# T7 KKS / RDS-PP Presence Check",
        "",
        "## Scope",
        "",
        "This note records a repository-level presence check for inherited KKS/RDS-PP-style designations.",
        "",
        "No raw operational values are emitted. Numeric project-specific portions of KKS-like strings are not parsed or interpreted.",
        "",
        "## Patterns Checked",
        "",
        "- RDS-PP mounted designation pattern beginning with `=M`.",
        "- RDS-PP mounted designation pattern beginning with `=U`.",
        "- Plan-specified RDS-PP letter codes: `MDA`, `MDK`, `MDL`, `MKA`, `MSE`, `MST`, `MUD`.",
        "- Classic KKS-like alphanumeric candidates, counted only as presence evidence.",
        "",
        "## Summary",
        "",
        f"- Files scanned: {summary['files_scanned']}",
        f"- Source/extracted data files scanned: {summary['source_or_extracted_data_files_scanned']}",
        f"- Source/extracted data files with KKS/RDS hits: {summary['source_or_extracted_data_files_with_any_hit']}",
        f"- Source/extracted data KKS/RDS hit count: {summary['source_or_extracted_data_pattern_hit_count']}",
        f"- Source/extracted data classic KKS candidate hit count: {summary['source_or_extracted_data_classic_kks_candidate_hit_count']}",
        f"- Source/extracted data RDS-PP hit count: {summary['source_or_extracted_data_rds_pp_hit_count']}",
        f"- Total repository-level pattern hit count: {summary['pattern_hit_count']}",
        f"- Pattern rows emitted: {summary['pattern_rows']}",
        f"- Scan errors: {summary['scan_errors']}",
        f"- RDS-PP normative letter codes with hits: {summary['rds_pp_normative_codes_with_hits']} / {summary['rds_pp_normative_codes_checked']}",
        "",
        "## Interpretation",
        "",
        "This is a presence check, not a resolver. KKS/RDS-PP evidence may support FLOC interpretation, validation, or crosswalk construction, but it must not be treated as resolving or constructing the final hierarchy by itself.",
        "",
        "The corrected regex pass finds KKS-like candidate hits in `source_or_extracted_data`, all under the broad `classic_kks_candidate` pattern. It does not find RDS-PP scoped hits in source/extracted data.",
        "",
        "The large repository-level count is not a source-data denominator: it includes reference documents, planning material, generated artefacts, and external support code. Scope separation is therefore part of the control.",
        "",
        "The result should feed STINT_1 as supporting source-designation evidence for FLOC and related semantic reconciliation work.",
        "",
        "## Outputs",
        "",
        "- `outputs/kks_presence_check_pattern_counts_v1.csv`",
        "- `outputs/kks_presence_check_scope_summary_v1.csv`",
        "- `outputs/kks_presence_check_errors_v1.csv`",
        "- `reference_layer/source_designations/rds_pp_normative_pattern_presence_v1.csv`",
        "- `outputs/kks_presence_check_summary_v1.json`",
        "",
        "## Guardrails",
        "",
        "- Do not parse the project-specific numeric portion of KKS-like strings.",
        "- Do not promote KKS/RDS-PP presence to ground truth.",
        "- Do not treat KKS/RDS-PP as a hierarchy resolver.",
        "- Preserve namespace separation: IEC id != RDS-PP != ISO != FLOC != EQUNR != technician term.",
    ]
    (DOCS_DIR / "kks_presence_check.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
