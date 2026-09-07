"""T3.5.2b NOTES region diagnostic for two-column PDF layouts.

The previous heading-sequence extractor treated NOTES as a stacked section.
This diagnostic extracts the NOTES column spatially: from the NOTES heading
down to the next block heading and to the right of the NOTES column anchor.
Versioned outputs contain only hashes, counts, and booleans.
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

from asset_ml_feasibility.parsers.pdf_assets_of_concern import stable_hash  # noqa: E402

import pdfplumber  # noqa: E402


INTERNAL_REPORTS_DIR = PROJECT_ROOT / "reports" / "internal"
PATH_A_DIR = PROJECT_ROOT / "stint-1-evidence-ground-truth" / "phase_3_path_a_faultcodes"
OUTPUT_DIR = PATH_A_DIR / "outputs"
INTERNAL_OUTPUT_DIR = INTERNAL_REPORTS_DIR / "path_a_repair"

PDF_STATUS_PATH = INTERNAL_REPORTS_DIR / "pdf_assets_of_concern_file_status.csv"
VARIANT_MAP_PATH = OUTPUT_DIR / "template_variants" / "pdf_template_variant_file_map_sanitized.csv"
STACKED_REPARSE_PATH = OUTPUT_DIR / "f352_template_aware_file_coverage_sanitized.csv"

TARGET_SAMPLE_MARKERS = {
    "2025-12-04": ["WTG 26", "PCH", "accumulator"],
    "2026-08-05": ["T48", "Yaw Limit", "T30", "T33", "annual maintenance", "T9", "blade repair"],
}
NEXT_BLOCK_HEADINGS = {"ASSETS", "PLANNED", "SITE"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def as_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def sorted_words(page: pdfplumber.page.Page) -> list[dict[str, object]]:
    return sorted(page.extract_words(x_tolerance=1, y_tolerance=3) or [], key=lambda w: (w["top"], w["x0"]))


def locate_word(words: list[dict[str, object]], text: str) -> dict[str, object] | None:
    wanted = text.upper()
    for word in words:
        if str(word.get("text", "")).upper() == wanted:
            return word
    return None


def next_block_top(words: list[dict[str, object]], start_top: float) -> float | None:
    candidates = [
        float(word["top"])
        for word in words
        if float(word["top"]) > start_top + 8
        and str(word.get("text", "")).upper().strip(":") in NEXT_BLOCK_HEADINGS
    ]
    return min(candidates) if candidates else None


def extract_notes_region(pdf_path: Path) -> tuple[str, dict[str, object]]:
    page_texts: list[str] = []
    diagnostics: list[dict[str, object]] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_index, page in enumerate(pdf.pages):
            words = sorted_words(page)
            notes = locate_word(words, "NOTES")
            if not notes:
                diagnostics.append({"page": page_index + 1, "notes_heading_found": False})
                continue

            x0 = float(notes["x0"])
            y0 = float(notes["bottom"]) + 2
            y1 = next_block_top(words, float(notes["top"])) or float(page.height)
            region_words = [
                word
                for word in words
                if float(word["x0"]) >= x0
                and float(word["top"]) > y0
                and float(word["top"]) < y1
            ]
            lines: dict[int, list[str]] = {}
            for word in region_words:
                band = int(round(float(word["top"]) / 4.0) * 4)
                lines.setdefault(band, []).append(str(word["text"]))
            text = "\n".join(normalize_space(" ".join(parts)) for _, parts in sorted(lines.items()))
            page_texts.append(text)
            diagnostics.append(
                {
                    "page": page_index + 1,
                    "notes_heading_found": True,
                    "notes_x0": round(x0, 1),
                    "notes_y0": round(y0, 1),
                    "notes_y1": round(y1, 1),
                    "notes_region_word_count": len(region_words),
                    "notes_region_line_count": len([line for line in text.splitlines() if line.strip()]),
                }
            )
    return "\n".join(text for text in page_texts if text.strip()).strip(), {"pages": diagnostics}


def content_profile(text: str) -> dict[str, object]:
    clean = normalize_space(text)
    return {
        "notes_region_nonempty": bool(clean),
        "notes_region_char_count": len(clean),
        "notes_region_line_count": len([line for line in text.splitlines() if line.strip()]),
        "notes_region_content_hash": stable_hash(clean) if clean else "",
    }


def label_known_sample(path_text: str) -> str:
    for label in TARGET_SAMPLE_MARKERS:
        if label in path_text:
            return label
    return ""


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    INTERNAL_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    status = pd.read_csv(PDF_STATUS_PATH)
    variants = pd.read_csv(VARIANT_MAP_PATH)
    stacked = pd.read_csv(STACKED_REPARSE_PATH)[
        ["path_hash", "file_hash", "notes_text_present", "notes_text_char_count"]
    ]
    df = status.merge(
        variants[["path_hash", "file_hash", "template_variant", "recognized_core_sections"]],
        on=["path_hash", "file_hash"],
        how="left",
    ).merge(stacked, on=["path_hash", "file_hash"], how="left")

    internal_records: list[dict[str, object]] = []
    sanitized_records: list[dict[str, object]] = []
    sample_records: list[dict[str, object]] = []

    for row in df.itertuples(index=False):
        relative_path = as_text(getattr(row, "relative_path"))
        pdf_path = PROJECT_ROOT / relative_path
        try:
            notes_text, diagnostics = extract_notes_region(pdf_path)
            status_value = "read_ok"
            error_type = ""
        except Exception as exc:  # noqa: BLE001 - status artifact, not workflow failure
            notes_text = ""
            diagnostics = {"pages": []}
            status_value = "read_error"
            error_type = type(exc).__name__

        profile = content_profile(notes_text)
        base = {
            "path_hash": as_text(getattr(row, "path_hash")),
            "file_hash": as_text(getattr(row, "file_hash")),
            "template_variant": as_text(getattr(row, "template_variant")),
            "recognized_core_sections": bool(getattr(row, "recognized_core_sections")),
            "stacked_notes_nonempty": bool(getattr(row, "notes_text_present")),
            "notes_region_status": status_value,
            "error_type": error_type,
        }
        internal_records.append(
            base
            | {
                "relative_path": relative_path,
                "notes_region_text": notes_text,
                "diagnostics_json": json.dumps(diagnostics),
                "raw_operational_values_emitted": True,
            }
        )
        sanitized_records.append(base | profile | {"raw_operational_values_emitted": False})

        sample_label = label_known_sample(relative_path)
        if sample_label:
            found = {
                f"sample_marker_{index + 1}_found_in_notes_region": marker.lower() in notes_text.lower()
                for index, marker in enumerate(TARGET_SAMPLE_MARKERS[sample_label])
            }
            sample_records.append(
                {
                    "sample_label": sample_label,
                    "path_hash": base["path_hash"],
                    "file_hash": base["file_hash"],
                    "template_variant": base["template_variant"],
                    "stacked_notes_nonempty": base["stacked_notes_nonempty"],
                    **profile,
                    **found,
                    "raw_operational_values_emitted": False,
                }
            )

    sanitized = pd.DataFrame(sanitized_records)
    internal = pd.DataFrame(internal_records)
    sample = pd.DataFrame(sample_records)
    core = sanitized[sanitized["recognized_core_sections"]]

    by_variant = (
        sanitized.groupby("template_variant", dropna=False)
        .agg(
            files=("file_hash", "size"),
            core_files=("recognized_core_sections", "sum"),
            stacked_notes_nonempty=("stacked_notes_nonempty", "sum"),
            region_notes_nonempty=("notes_region_nonempty", "sum"),
            region_notes_nonempty_core=(
                "notes_region_nonempty",
                lambda values: int(values[sanitized.loc[values.index, "recognized_core_sections"]].sum()),
            ),
        )
        .reset_index()
        .sort_values(["files", "template_variant"], ascending=[False, True])
    )
    by_variant["raw_operational_values_emitted"] = False

    summary = {
        "created_at_utc": utc_now(),
        "pass_id": "T3.5.2b",
        "engine": "pdfplumber_spatial_notes_region",
        "files_evaluated": int(sanitized.shape[0]),
        "core_recognized_files": int(core.shape[0]),
        "stacked_notes_nonempty_core_files": int(core["stacked_notes_nonempty"].sum()),
        "region_notes_nonempty_core_files": int(core["notes_region_nonempty"].sum()),
        "region_notes_nonempty_core_rate": round(float(core["notes_region_nonempty"].mean()), 4)
        if not core.empty
        else 0.0,
        "known_sample_files_checked": int(sample.shape[0]),
        "known_sample_files_region_nonempty": int(sample["notes_region_nonempty"].sum()) if not sample.empty else 0,
        "known_sample_all_markers_found": bool(
            sample.filter(like="_found_in_notes_region").all(axis=None)
        )
        if not sample.empty
        else False,
        "raw_operational_values_emitted": False,
    }

    sanitized_path = OUTPUT_DIR / "f352b_notes_region_coverage_sanitized.csv"
    variant_path = OUTPUT_DIR / "f352b_notes_region_coverage_by_variant_sanitized.csv"
    sample_path = OUTPUT_DIR / "f352b_known_notes_sample_check_sanitized.csv"
    summary_path = OUTPUT_DIR / "f352b_notes_region_diagnostic_summary_sanitized.json"
    memo_path = OUTPUT_DIR / "f352b_notes_region_diagnostic_memo.md"
    internal_path = INTERNAL_OUTPUT_DIR / "f352b_notes_region_text_internal.csv"

    sanitized.to_csv(sanitized_path, index=False)
    by_variant.to_csv(variant_path, index=False)
    sample.to_csv(sample_path, index=False)
    internal.to_csv(internal_path, index=False)
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    memo_path.write_text(build_memo(summary, by_variant), encoding="utf-8")

    print(json.dumps(summary, indent=2))
    return 0


def build_memo(summary: dict[str, object], by_variant: pd.DataFrame) -> str:
    rows = []
    for row in by_variant.itertuples(index=False):
        rows.append(
            "| "
            + " | ".join(
                [
                    str(getattr(row, "template_variant")),
                    str(getattr(row, "files")),
                    str(getattr(row, "core_files")),
                    str(getattr(row, "stacked_notes_nonempty")),
                    str(getattr(row, "region_notes_nonempty")),
                    str(getattr(row, "region_notes_nonempty_core")),
                ]
            )
            + " |"
        )
    return "\n".join(
        [
            "# T3.5.2b NOTES Region Diagnostic",
            "",
            "## Scope",
            "",
            "This diagnostic tests whether `NOTES` behaves as a right-side column rather than a stacked section. It uses spatial extraction from the `NOTES` heading to the next block heading.",
            "",
            f"- Engine: `{summary['engine']}`",
            f"- Files evaluated: `{summary['files_evaluated']}`",
            f"- Core-recognized files: `{summary['core_recognized_files']}`",
            f"- Stacked extractor NOTES non-empty over core files: `{summary['stacked_notes_nonempty_core_files']}`",
            f"- Spatial NOTES region non-empty over core files: `{summary['region_notes_nonempty_core_files']}`",
            f"- Spatial NOTES region non-empty rate over core files: `{summary['region_notes_nonempty_core_rate']}`",
            f"- Known sample files checked: `{summary['known_sample_files_checked']}`",
            f"- Known sample files with non-empty NOTES region: `{summary['known_sample_files_region_nonempty']}`",
            f"- Known sample markers all found: `{summary['known_sample_all_markers_found']}`",
            "",
            "## Coverage By Template Variant",
            "",
            "| template_variant | files | core_files | stacked_notes_nonempty | region_notes_nonempty | region_notes_nonempty_core |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
            *rows,
            "",
            "## Interpretation",
            "",
            "The stacked heading extractor undercounts `NOTES` because the PDF layout places NOTES as a parallel right-side column. `NOTES` coverage must therefore be derived from the spatial region extractor, not from sequential section text.",
            "",
            "This diagnostic supersedes the earlier `NOTES non-empty = 13` interpretation for T3.5.3 planning. It does not promote any row to a denominator; it only fixes section availability accounting.",
            "",
        ]
    )


if __name__ == "__main__":
    raise SystemExit(main())
