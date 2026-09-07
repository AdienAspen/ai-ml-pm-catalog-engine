"""T3.5.2 template-aware PDF section reparse.

The pass preserves section-level text internally while emitting only sanitized
coverage artifacts. It is anchored to section headings, not page coordinates.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from asset_ml_feasibility.parsers.pdf_assets_of_concern import extract_pages, stable_hash  # noqa: E402


INTERNAL_REPORTS_DIR = PROJECT_ROOT / "reports" / "internal"
PATH_A_DIR = PROJECT_ROOT / "stint-1-evidence-ground-truth" / "phase_3_path_a_faultcodes"
OUTPUT_DIR = PATH_A_DIR / "outputs"
INTERNAL_OUTPUT_DIR = INTERNAL_REPORTS_DIR / "path_a_repair"

PDF_STATUS_PATH = INTERNAL_REPORTS_DIR / "pdf_assets_of_concern_file_status.csv"
VARIANT_MAP_PATH = OUTPUT_DIR / "template_variants" / "pdf_template_variant_file_map_sanitized.csv"

SECTION_ORDER = [
    "ASSET STATUS",
    "NOTES",
    "ASSETS OF CONCERN",
    "PLANNED WORK",
    "SITE ROSTER",
]
SECTION_KEY = {
    "ASSET STATUS": "asset_status_text",
    "NOTES": "notes_text",
    "ASSETS OF CONCERN": "assets_of_concern_text",
    "PLANNED WORK": "planned_work_text",
    "SITE ROSTER": "site_roster_text",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_heading(value: str) -> str:
    return re.sub(r"[^A-Z0-9 ]+", "", value.upper()).strip()


def as_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def detect_heading(line: str) -> str | None:
    heading = normalize_heading(line)
    for section in SECTION_ORDER:
        if heading == section or heading.startswith(section + " "):
            return section
    return None


def extract_sections(full_text: str) -> dict[str, str]:
    sections = {SECTION_KEY[section]: "" for section in SECTION_ORDER}
    current: str | None = None
    buffers = {section: [] for section in SECTION_ORDER}

    for raw_line in full_text.splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        if not line:
            continue
        heading = detect_heading(line)
        if heading:
            current = heading
            remainder = line[len(heading) :].strip(" :-")
            if remainder:
                buffers[current].append(remainder)
            continue
        if current:
            buffers[current].append(line)

    for section, lines in buffers.items():
        sections[SECTION_KEY[section]] = "\n".join(lines).strip()
    return sections


def detect_section_headings(full_text: str) -> dict[str, bool]:
    upper = full_text.upper()
    return {SECTION_KEY[section]: section in upper for section in SECTION_ORDER}


def content_profile(text: str) -> dict[str, object]:
    clean = re.sub(r"\s+", " ", text).strip()
    return {
        "present": bool(clean),
        "char_count": len(clean),
        "line_count": len([line for line in text.splitlines() if line.strip()]),
        "content_hash": stable_hash(clean) if clean else "",
    }


def select_validation_sample(file_map: pd.DataFrame) -> pd.DataFrame:
    rows = []
    sorted_map = file_map.sort_values(["template_variant", "path_hash", "file_hash"])
    for _, group in sorted_map.groupby("template_variant", dropna=False):
        rows.append(group.iloc[0])
    if len(rows) < 10:
        already = {(row["path_hash"], row["file_hash"]) for row in rows}
        for _, row in sorted_map[sorted_map["recognized_core_sections"] == True].iterrows():  # noqa: E712
            key = (row["path_hash"], row["file_hash"])
            if key not in already:
                rows.append(row)
                already.add(key)
            if len(rows) >= 10:
                break
    return pd.DataFrame(rows[:10])


def reparse_files(status_df: pd.DataFrame, variant_map: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    merged = status_df.merge(
        variant_map[["path_hash", "file_hash", "template_variant", "section_signature", "recognized_core_sections"]],
        on=["path_hash", "file_hash"],
        how="left",
    )
    internal_records: list[dict[str, object]] = []
    sanitized_records: list[dict[str, object]] = []

    for row in merged.itertuples(index=False):
        relative_path = as_text(getattr(row, "relative_path"))
        pdf_path = PROJECT_ROOT / relative_path
        base = {
            "path_hash": as_text(getattr(row, "path_hash")),
            "file_hash": as_text(getattr(row, "file_hash")),
            "report_year_hint": as_text(getattr(row, "report_year_hint")),
            "template_variant": as_text(getattr(row, "template_variant")),
            "recognized_core_sections": bool(getattr(row, "recognized_core_sections")),
            "section_signature": as_text(getattr(row, "section_signature")),
        }
        try:
            pages, page_count = extract_pages(pdf_path)
            full_text = "\n".join(pages)
            heading_flags = detect_section_headings(full_text)
            sections = extract_sections(full_text)
            reparse_status = "read_ok"
            error_type = ""
        except Exception as exc:  # noqa: BLE001 - status artifact, not workflow failure
            page_count = 0
            heading_flags = {SECTION_KEY[section]: False for section in SECTION_ORDER}
            sections = {SECTION_KEY[section]: "" for section in SECTION_ORDER}
            reparse_status = "read_error"
            error_type = type(exc).__name__

        profiles = {key: content_profile(text) for key, text in sections.items()}
        text_present_count = sum(1 for profile in profiles.values() if profile["present"])
        core_text_present_count = sum(
            1
            for key in ["asset_status_text", "notes_text", "assets_of_concern_text", "planned_work_text"]
            if profiles[key]["present"]
        )
        core_heading_found_count = sum(
            1
            for key in ["asset_status_text", "notes_text", "assets_of_concern_text", "planned_work_text"]
            if heading_flags[key]
        )

        internal_records.append(
            base
            | {
                "relative_path": relative_path,
                "page_count": page_count,
                "reparse_status": reparse_status,
                "error_type": error_type,
                **{f"{key}_heading_found": value for key, value in heading_flags.items()},
                **sections,
                "raw_operational_values_emitted": True,
            }
        )
        sanitized_records.append(
            base
            | {
                "page_count": page_count,
                "reparse_status": reparse_status,
                "error_type": error_type,
                "sections_text_nonempty_count": text_present_count,
                "core_sections_text_nonempty_count": core_text_present_count,
                "core_headings_found_count": core_heading_found_count,
                "raw_operational_values_emitted": False,
                **{f"{key}_heading_found": value for key, value in heading_flags.items()},
                **{
                    f"{key}_{metric}": value
                    for key, profile in profiles.items()
                    for metric, value in profile.items()
                },
            }
        )

    return pd.DataFrame(internal_records), pd.DataFrame(sanitized_records)


def build_section_manifest(file_coverage: pd.DataFrame) -> pd.DataFrame:
    records: list[dict[str, object]] = []
    for row in file_coverage.itertuples(index=False):
        base = {
            "path_hash": getattr(row, "path_hash"),
            "file_hash": getattr(row, "file_hash"),
            "template_variant": getattr(row, "template_variant"),
            "reparse_status": getattr(row, "reparse_status"),
            "raw_operational_values_emitted": False,
        }
        for section, key in SECTION_KEY.items():
            records.append(
                base
                | {
                    "section": section,
                    "section_heading_found": bool(getattr(row, f"{key}_heading_found")),
                    "section_present": bool(getattr(row, f"{key}_present")),
                    "section_char_count": int(getattr(row, f"{key}_char_count")),
                    "section_line_count": int(getattr(row, f"{key}_line_count")),
                    "section_content_hash": getattr(row, f"{key}_content_hash"),
                }
            )
    return pd.DataFrame(records)


def build_variant_coverage(file_coverage: pd.DataFrame) -> pd.DataFrame:
    aggregations = {
        "files": ("file_hash", "size"),
        "read_ok_files": ("reparse_status", lambda values: int((values == "read_ok").sum())),
        "recognized_core_files": ("recognized_core_sections", "sum"),
        "asset_status_present_files": ("asset_status_text_present", "sum"),
        "notes_present_files": ("notes_text_present", "sum"),
        "assets_of_concern_present_files": ("assets_of_concern_text_present", "sum"),
        "planned_work_present_files": ("planned_work_text_present", "sum"),
        "site_roster_present_files": ("site_roster_text_present", "sum"),
        "core_headings_found_min": ("core_headings_found_count", "min"),
        "core_headings_found_median": ("core_headings_found_count", "median"),
        "core_sections_text_nonempty_min": ("core_sections_text_nonempty_count", "min"),
        "core_sections_text_nonempty_median": ("core_sections_text_nonempty_count", "median"),
    }
    coverage = file_coverage.groupby("template_variant", dropna=False).agg(**aggregations).reset_index()
    coverage["core_4_heading_success_files"] = (
        file_coverage.groupby("template_variant")["core_headings_found_count"]
        .apply(lambda values: int((values == 4).sum()))
        .values
    )
    coverage["core_4_text_nonempty_files"] = (
        file_coverage.groupby("template_variant")["core_sections_text_nonempty_count"]
        .apply(lambda values: int((values == 4).sum()))
        .values
    )
    coverage["raw_operational_values_emitted"] = False
    return coverage.sort_values(["files", "template_variant"], ascending=[False, True])


def validate_sample(sample_df: pd.DataFrame, file_coverage: pd.DataFrame) -> pd.DataFrame:
    sample = sample_df[["path_hash", "file_hash", "template_variant", "recognized_core_sections"]].merge(
        file_coverage,
        on=["path_hash", "file_hash", "template_variant", "recognized_core_sections"],
        how="left",
    )
    records = []
    for row in sample.itertuples(index=False):
        expected_core = bool(getattr(row, "recognized_core_sections"))
        core_count = int(getattr(row, "core_headings_found_count"))
        records.append(
            {
                "path_hash": getattr(row, "path_hash"),
                "file_hash": getattr(row, "file_hash"),
                "template_variant": getattr(row, "template_variant"),
                "expected_core_template": expected_core,
                "core_headings_found_count": core_count,
                "sample_validation_status": "pass" if (not expected_core or core_count == 4) else "review",
                "raw_operational_values_emitted": False,
            }
        )
    return pd.DataFrame(records)


def write_memo(summary: dict[str, object], variant_coverage: pd.DataFrame) -> str:
    table_rows = []
    for row in variant_coverage.itertuples(index=False):
        table_rows.append(
            "| "
            + " | ".join(
                [
                    str(getattr(row, "template_variant")),
                    str(getattr(row, "files")),
                    str(getattr(row, "recognized_core_files")),
                    str(getattr(row, "core_4_heading_success_files")),
                    str(getattr(row, "core_4_text_nonempty_files")),
                    str(getattr(row, "asset_status_present_files")),
                    str(getattr(row, "notes_present_files")),
                    str(getattr(row, "assets_of_concern_present_files")),
                    str(getattr(row, "planned_work_present_files")),
                    str(getattr(row, "site_roster_present_files")),
                ]
            )
            + " |"
        )
    return "\n".join(
        [
            "# T3.5.2 Template-Aware PDF Reparse",
            "",
            "## Scope",
            "",
            "This pass reparses the Path A PDF corpus by heading anchors rather than fixed coordinates. It preserves section-level text internally and emits sanitized coverage outputs for review.",
            "",
            f"- Extraction engine: `{summary['engine']}`",
            f"- Files reparsed: `{summary['files_reparsed']}`",
            f"- Validation sample size: `{summary['validation_sample_size']}`",
            f"- Sample validation pass: `{summary['sample_validation_pass_count']}`",
            f"- Sample validation review: `{summary['sample_validation_review_count']}`",
            f"- Files with all four core headings found: `{summary['files_with_all_core_headings_found']}`",
            f"- Files with all four core section texts non-empty: `{summary['files_with_all_core_section_texts_nonempty']}`",
            f"- Raw operational values emitted in versioned outputs: `{summary['raw_operational_values_emitted']}`",
            "",
            "## Coverage By Template Variant",
            "",
            "| template_variant | files | recognised_core_files | core_4_heading_files | core_4_text_nonempty_files | asset_status_text | notes_text | assets_of_concern_text | planned_work_text | site_roster_text |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
            *table_rows,
            "",
            "## Interpretation",
            "",
            "The reparse confirms that section coverage must be evaluated by `template_variant`, not globally. Heading presence and non-empty section text are reported separately because an empty `NOTES` section is not a template failure.",
            "",
            "The internal section-preserving output is deliberately kept under `reports/internal/`; versioned outputs contain only hashes, section-presence flags, counts, and content hashes.",
            "",
            "## Next Control",
            "",
            "Use this reparse as input for `T3.5.3` notes semantics and for later snapshot deduplication. Do not promote Path A evidence to denominators from this pass alone.",
            "",
        ]
    )


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    INTERNAL_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    status_df = pd.read_csv(PDF_STATUS_PATH)
    variant_map = pd.read_csv(VARIANT_MAP_PATH)
    sample_df = select_validation_sample(variant_map)
    internal_sections, file_coverage = reparse_files(status_df, variant_map)
    section_manifest = build_section_manifest(file_coverage)
    variant_coverage = build_variant_coverage(file_coverage)
    sample_validation = validate_sample(sample_df, file_coverage)

    internal_sections_path = INTERNAL_OUTPUT_DIR / "f352_template_aware_sections_internal.csv"
    file_coverage_path = OUTPUT_DIR / "f352_template_aware_file_coverage_sanitized.csv"
    section_manifest_path = OUTPUT_DIR / "f352_template_aware_section_manifest_sanitized.csv"
    variant_coverage_path = OUTPUT_DIR / "f352_template_aware_section_coverage_by_variant_sanitized.csv"
    sample_validation_path = OUTPUT_DIR / "f352_template_aware_validation_sample_sanitized.csv"
    summary_path = OUTPUT_DIR / "f352_template_aware_pdf_reparse_summary_sanitized.json"
    memo_path = OUTPUT_DIR / "f352_template_aware_pdf_reparse_memo.md"

    internal_sections.to_csv(internal_sections_path, index=False)
    file_coverage.to_csv(file_coverage_path, index=False)
    section_manifest.to_csv(section_manifest_path, index=False)
    variant_coverage.to_csv(variant_coverage_path, index=False)
    sample_validation.to_csv(sample_validation_path, index=False)

    summary = {
        "created_at_utc": utc_now(),
        "pass_id": "T3.5.2",
        "engine": "pdfplumber_heading_anchored",
        "docling_available": False,
        "files_reparsed": int(file_coverage.shape[0]),
        "validation_sample_size": int(sample_validation.shape[0]),
        "sample_validation_pass_count": int((sample_validation["sample_validation_status"] == "pass").sum()),
        "sample_validation_review_count": int((sample_validation["sample_validation_status"] == "review").sum()),
        "files_with_all_core_headings_found": int((file_coverage["core_headings_found_count"] == 4).sum()),
        "files_with_all_core_section_texts_nonempty": int(
            (file_coverage["core_sections_text_nonempty_count"] == 4).sum()
        ),
        "template_variants_evaluated": int(variant_coverage.shape[0]),
        "raw_operational_values_emitted": False,
        "outputs": {
            "memo": str(memo_path),
            "file_coverage": str(file_coverage_path),
            "section_manifest": str(section_manifest_path),
            "variant_coverage": str(variant_coverage_path),
            "validation_sample": str(sample_validation_path),
        },
        "internal_outputs_ignored": {
            "section_text_preserving_reparse": str(internal_sections_path),
        },
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    memo_path.write_text(write_memo(summary, variant_coverage), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
