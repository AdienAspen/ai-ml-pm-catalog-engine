"""F3.5 PDF template inventory and fault-code/state-code partition.

This pass is intentionally conservative. It detects PDF template variants by
section headings before interpreting code/event patterns, and it emits only
sanitized, versionable outputs.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from asset_ml_feasibility.parsers.pdf_assets_of_concern import extract_pages, stable_hash  # noqa: E402


INTERNAL_REPORTS_DIR = PROJECT_ROOT / "reports" / "internal"
OUTPUT_DIR = PROJECT_ROOT / "stint-1-evidence-ground-truth" / "phase_3_path_a_faultcodes" / "outputs"
VARIANT_DIR = OUTPUT_DIR / "template_variants"
INTERNAL_OUTPUT_DIR = INTERNAL_REPORTS_DIR / "path_a_repair"

PDF_STATUS_PATH = INTERNAL_REPORTS_DIR / "pdf_assets_of_concern_file_status.csv"
PDF_ROWS_PATH = INTERNAL_REPORTS_DIR / "pdf_assets_of_concern_rows.csv"

CORE_SECTIONS = ["ASSET STATUS", "NOTES", "ASSETS OF CONCERN", "PLANNED WORK"]
OPTIONAL_SECTIONS = ["SITE ROSTER", "NO ATTACHMENTS", "ATTACHMENTS"]
ALL_SECTIONS = CORE_SECTIONS + OPTIONAL_SECTIONS

STATE_CODE_VALUES = {"T", "I", "S", "R", "M", "NC", "O", "A"}
STATE_EVENT_PATTERNS = {
    "repair": r"\brepair\b",
    "maintenance": r"\bmaintenance\b",
    "no_communication": r"\bno\s+communication\b",
    "no_errors": r"\bno\s+errors?\b",
    "tripped": r"\btripp?ed\b",
    "stopped": r"\bstopped\b",
    "impacted": r"\bimpacted\b",
    "available_or_online": r"\b(available|online)\b",
}
TECHNICAL_EVENT_PATTERNS = {
    "fault": r"\bfault\b",
    "alarm": r"\balarm\b",
    "voltage": r"\bvoltage\b|\bvolt\b",
    "vibration": r"\bvibration\b",
    "temperature": r"\btemperature\b|\btemp\b|\boverheat",
    "yaw": r"\byaw\b",
    "pitch": r"\bpitch\b",
    "blade": r"\bblade\b",
    "brake": r"\bbrake\b",
    "converter": r"\bconverter\b|\bthyristor\b",
    "generator": r"\bgenerator\b",
    "bearing": r"\bbearing\b",
    "hydraulic": r"\bhydraulic\b",
    "lubrication": r"\blubricat",
    "sensor": r"\bsensor\b",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def as_text(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    if text.endswith(".0") and text[:-2].isdigit():
        return text[:-2]
    return text


def detect_sections(full_text: str) -> dict[str, bool]:
    upper = full_text.upper()
    flags: dict[str, bool] = {}
    for section in CORE_SECTIONS + ["SITE ROSTER", "NO ATTACHMENTS"]:
        flags[section.lower().replace(" ", "_")] = section in upper
    flags["attachments"] = bool(re.search(r"(?m)^\s*ATTACHMENTS\s*$", upper))
    return flags


def section_signature(flags: dict[str, bool]) -> str:
    present = [section for section in ALL_SECTIONS if flags.get(section.lower().replace(" ", "_"), False)]
    return "; ".join(present) if present else "NO_KNOWN_SECTIONS"


def parse_month_hint(path_text: str, year_hint: str) -> str:
    match = re.search(r"(20\d{2})[-_/ ](0[1-9]|1[0-2])", path_text)
    if match:
        return f"{match.group(1)}-{match.group(2)}"
    month_names = {
        "january": "01",
        "february": "02",
        "march": "03",
        "april": "04",
        "may": "05",
        "june": "06",
        "july": "07",
        "august": "08",
        "september": "09",
        "october": "10",
        "november": "11",
        "december": "12",
    }
    lower = path_text.lower()
    for name, number in month_names.items():
        if name in lower and str(year_hint).isdigit():
            return f"{year_hint}-{number}"
    return str(year_hint) if str(year_hint).isdigit() else "unknown"


def inventory_template_variants(status_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    records: list[dict[str, object]] = []
    for row in status_df.itertuples(index=False):
        relative_path = as_text(getattr(row, "relative_path"))
        pdf_path = PROJECT_ROOT / relative_path
        base = {
            "path_hash": as_text(getattr(row, "path_hash")),
            "file_hash": as_text(getattr(row, "file_hash")),
            "report_year_hint": as_text(getattr(row, "report_year_hint")),
            "report_month_hint": parse_month_hint(relative_path, as_text(getattr(row, "report_year_hint"))),
            "read_status": as_text(getattr(row, "read_status")),
            "section_status": as_text(getattr(row, "section_status")),
            "raw_operational_values_emitted": False,
        }
        try:
            pages, page_count = extract_pages(pdf_path)
            full_text = "\n".join(pages)
            flags = detect_sections(full_text)
            error_type = ""
        except Exception as exc:  # noqa: BLE001 - status artifact, not workflow failure
            page_count = 0
            flags = {section.lower().replace(" ", "_"): False for section in ALL_SECTIONS}
            error_type = type(exc).__name__

        signature = section_signature(flags)
        recognized_core = all(flags.get(section.lower().replace(" ", "_"), False) for section in CORE_SECTIONS)
        records.append(
            base
            | flags
            | {
                "page_count_rechecked": page_count,
                "section_signature": signature,
                "recognized_core_sections": recognized_core,
                "zero_interpretation_allowed": bool(recognized_core and base["read_status"] == "read_ok"),
                "template_read_error_type": error_type,
            }
        )

    file_map = pd.DataFrame(records)
    signatures = sorted(file_map["section_signature"].fillna("NO_KNOWN_SECTIONS").unique())
    variant_ids = {signature: f"PDF-TPL-{index + 1:03d}" for index, signature in enumerate(signatures)}
    file_map["template_variant"] = file_map["section_signature"].map(variant_ids)

    grouped = (
        file_map.groupby(["template_variant", "section_signature"], dropna=False)
        .agg(
            file_count=("file_hash", "size"),
            report_year_min=("report_year_hint", "min"),
            report_year_max=("report_year_hint", "max"),
            report_month_min=("report_month_hint", "min"),
            report_month_max=("report_month_hint", "max"),
            read_ok_files=("read_status", lambda values: int((values == "read_ok").sum())),
            recognized_core_files=("recognized_core_sections", "sum"),
            zero_interpretation_allowed_files=("zero_interpretation_allowed", "sum"),
            has_asset_status=("asset_status", "max"),
            has_notes=("notes", "max"),
            has_assets_of_concern=("assets_of_concern", "max"),
            has_planned_work=("planned_work", "max"),
            has_site_roster=("site_roster", "max"),
            has_no_attachments=("no_attachments", "max"),
        )
        .reset_index()
        .sort_values(["file_count", "template_variant"], ascending=[False, True])
    )
    grouped["raw_operational_values_emitted"] = False

    summary = {
        "created_at_utc": utc_now(),
        "pass_id": "F3.5.0",
        "files_profiled": int(file_map.shape[0]),
        "template_variants": int(grouped.shape[0]),
        "recognized_core_files": int(file_map["recognized_core_sections"].sum()),
        "zero_interpretation_allowed_files": int(file_map["zero_interpretation_allowed"].sum()),
        "raw_operational_values_emitted": False,
    }
    return grouped, file_map, summary


def event_family(event_text: str) -> tuple[str, list[str], list[str]]:
    normalized = re.sub(r"\s+", " ", event_text.lower()).strip()
    state_hits = [name for name, pattern in STATE_EVENT_PATTERNS.items() if re.search(pattern, normalized)]
    technical_hits = [name for name, pattern in TECHNICAL_EVENT_PATTERNS.items() if re.search(pattern, normalized)]
    if technical_hits:
        family = "technical_condition"
    elif state_hits:
        family = "status_or_work_state"
    elif normalized in {"", "-"}:
        family = "blank_or_placeholder"
    else:
        family = "undetermined_text"
    return family, state_hits, technical_hits


def partition_fault_codes(rows_df: pd.DataFrame, file_map: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    rows = rows_df.copy()
    rows["fault_code_norm"] = rows["fault_code"].map(as_text)
    rows = rows[rows["fault_code_norm"].ne("") & rows["fault_code_norm"].ne("-")].copy()
    rows["state_norm"] = rows["state"].map(as_text)
    rows["event_norm"] = rows["event"].map(as_text)

    variant_cols = ["path_hash", "file_hash", "template_variant", "zero_interpretation_allowed"]
    rows = rows.merge(file_map[variant_cols], on=["path_hash", "file_hash"], how="left")
    families = rows["event_norm"].map(event_family)
    rows["event_family"] = [item[0] for item in families]
    rows["state_hit_count"] = [len(item[1]) for item in families]
    rows["technical_hit_count"] = [len(item[2]) for item in families]

    output_rows: list[dict[str, object]] = []
    internal_rows: list[dict[str, object]] = []
    for code, group in rows.groupby("fault_code_norm", dropna=False):
        frequency = int(group.shape[0])
        technical_rows = int((group["technical_hit_count"] > 0).sum())
        state_rows = int((group["state_hit_count"] > 0).sum())
        placeholder_rows = int((group["event_family"] == "blank_or_placeholder").sum())
        state_code_score = round(state_rows / frequency, 4) if frequency else 0.0
        fault_code_score = round(technical_rows / frequency, 4) if frequency else 0.0

        if fault_code_score >= 0.35 and technical_rows >= 2:
            classification = "fault_code"
            basis = "technical_event_terms_present"
        elif state_code_score >= 0.70 and fault_code_score <= 0.10:
            classification = "state_code"
            basis = "status_or_work_state_terms_dominate"
        else:
            classification = "undetermined"
            basis = "mixed_or_insufficient_context"

        state_counts = Counter(group["state_norm"].dropna())
        dominant_state = state_counts.most_common(1)[0][0] if state_counts else "unknown"
        family_counts = Counter(group["event_family"].dropna())
        dominant_family = family_counts.most_common(1)[0][0] if family_counts else "unknown"
        variant_count = int(group["template_variant"].nunique(dropna=True))

        output_rows.append(
            {
                "fault_code_key": f"FAULT-CODE-{stable_hash(str(code), 10)}",
                "fault_code_length": len(str(code)),
                "frequency": frequency,
                "template_variant_count": variant_count,
                "dominant_state_code": dominant_state,
                "dominant_event_family": dominant_family,
                "state_code_score": state_code_score,
                "fault_code_score": fault_code_score,
                "classification": classification,
                "classification_basis": basis,
                "status": "provisional_requires_template_aware_reparse",
                "raw_operational_values_emitted": False,
            }
        )
        internal_rows.append(
            {
                "fault_code": code,
                "frequency": frequency,
                "dominant_state_code": dominant_state,
                "dominant_event_family": dominant_family,
                "state_code_score": state_code_score,
                "fault_code_score": fault_code_score,
                "classification": classification,
                "classification_basis": basis,
            }
        )

    partition = pd.DataFrame(output_rows).sort_values(["classification", "frequency"], ascending=[True, False])
    internal = pd.DataFrame(internal_rows).sort_values(["classification", "frequency"], ascending=[True, False])
    class_counts = partition.groupby("classification").size().to_dict() if not partition.empty else {}
    summary = {
        "created_at_utc": utc_now(),
        "pass_id": "T3.5.1",
        "non_empty_code_rows_evaluated": int(rows.shape[0]),
        "distinct_code_keys_evaluated": int(partition.shape[0]),
        "classification_counts": {str(key): int(value) for key, value in class_counts.items()},
        "classification_status": "provisional_requires_template_aware_reparse",
        "raw_operational_values_emitted": False,
    }
    return partition, internal, summary


def write_memo(variant_summary: dict[str, object], partition_summary: dict[str, object], variant_inventory: pd.DataFrame) -> str:
    variant_rows = []
    for row in variant_inventory.itertuples(index=False):
        core_recognised = int(getattr(row, "recognized_core_files")) == int(getattr(row, "file_count"))
        variant_rows.append(
            "| "
            + " | ".join(
                [
                    str(getattr(row, "template_variant")),
                    str(getattr(row, "file_count")),
                    str(getattr(row, "report_month_min")),
                    str(getattr(row, "report_month_max")),
                    str(getattr(row, "section_signature")),
                    str(core_recognised),
                ]
            )
            + " |"
        )
    counts = partition_summary.get("classification_counts", {})
    return "\n".join(
        [
            "# F3.5.0 / T3.5.1 Path A Template and Code-State Check",
            "",
            "## Scope",
            "",
            "This pass inventories PDF template variants before interpreting code/event rows, then performs a conservative provisional partition of non-empty code tokens into `state_code`, `fault_code`, or `undetermined`.",
            "",
            "No raw operational values, file names, asset identifiers, site names, or event descriptions are emitted in versioned outputs.",
            "",
            "## F3.5.0 Template Variant Inventory",
            "",
            f"- Files profiled: `{variant_summary['files_profiled']}`",
            f"- Template variants detected: `{variant_summary['template_variants']}`",
            f"- Files with all core sections recognised: `{variant_summary['recognized_core_files']}`",
            f"- Files eligible for zero interpretation under recognised-template rule: `{variant_summary['zero_interpretation_allowed_files']}`",
            "",
            "| template_variant | file_count | month_min | month_max | section_signature | core_recognised |",
            "| --- | ---: | --- | --- | --- | --- |",
            *variant_rows,
            "",
            "## T3.5.1 Code-State Hypothesis Check",
            "",
            f"- Non-empty code rows evaluated: `{partition_summary['non_empty_code_rows_evaluated']}`",
            f"- Distinct code keys evaluated: `{partition_summary['distinct_code_keys_evaluated']}`",
            f"- Provisional `fault_code`: `{counts.get('fault_code', 0)}`",
            f"- Provisional `state_code`: `{counts.get('state_code', 0)}`",
            f"- Provisional `undetermined`: `{counts.get('undetermined', 0)}`",
            "",
            "## Interpretation",
            "",
            "The partition is provisional because it is based on the existing table extraction and event-family distribution. It is suitable for triage, not for denominator promotion.",
            "",
            "The template inventory is now a precondition for Path A repair: every downstream extracted row must carry `template_variant`, and no zero should be interpreted for a file whose template is not recognised.",
            "",
            "## Next Control",
            "",
            "Before rerunning Path A crosswalks, execute a template-aware reparse that preserves `ASSET STATUS`, `NOTES`, `ASSETS OF CONCERN`, and `PLANNED WORK`, with coverage reported by template variant.",
            "",
        ]
    )


def main() -> int:
    VARIANT_DIR.mkdir(parents=True, exist_ok=True)
    INTERNAL_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    status_df = pd.read_csv(PDF_STATUS_PATH)
    rows_df = pd.read_csv(PDF_ROWS_PATH)

    variant_inventory, file_map, variant_summary = inventory_template_variants(status_df)
    partition, internal_partition, partition_summary = partition_fault_codes(rows_df, file_map)

    variant_inventory_path = VARIANT_DIR / "pdf_template_variant_inventory_sanitized.csv"
    file_map_path = VARIANT_DIR / "pdf_template_variant_file_map_sanitized.csv"
    partition_path = OUTPUT_DIR / "f35_faultcode_state_partition_sanitized.csv"
    summary_path = OUTPUT_DIR / "f35_faultcode_state_partition_summary.json"
    memo_path = OUTPUT_DIR / "f35_template_variant_and_state_partition_memo.md"
    internal_partition_path = INTERNAL_OUTPUT_DIR / "f35_faultcode_state_partition_internal.csv"

    variant_inventory.to_csv(variant_inventory_path, index=False)
    file_map.to_csv(file_map_path, index=False)
    partition.to_csv(partition_path, index=False)
    internal_partition.to_csv(internal_partition_path, index=False)

    summary = {
        "template_inventory": variant_summary,
        "code_state_partition": partition_summary,
        "outputs": {
            "template_variant_inventory": str(variant_inventory_path),
            "template_variant_file_map": str(file_map_path),
            "faultcode_state_partition": str(partition_path),
            "memo": str(memo_path),
        },
        "internal_outputs_ignored": {
            "faultcode_state_partition_internal": str(internal_partition_path),
        },
        "raw_operational_values_emitted": False,
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    memo_path.write_text(write_memo(variant_summary, partition_summary, variant_inventory), encoding="utf-8")

    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
