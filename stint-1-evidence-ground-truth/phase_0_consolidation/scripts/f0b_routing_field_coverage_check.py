from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]
STINT_ROOT = PROJECT_ROOT / "stint-1-evidence-ground-truth"
OUTPUTS_DIR = STINT_ROOT / "phase_0_consolidation" / "outputs"
DOCS_DIR = STINT_ROOT / "docs"

ROUTING_FIELDS = {
    "classification_input.description": "description",
    "classification_input.description_extended": "descriptionExtended",
    "classification_input.reason": "reason",
    "classification_input.work_performed": "workPerformed",
    "header.activity_type": "activityType",
}

PDF_EVENT_FIELD = "pdf_assets_of_concern.event"


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def coverage_row(source_family: str, source_text_field: str, series: pd.Series, total_rows: int) -> dict:
    non_null = int(series.notna().sum())
    non_empty = int(series.fillna("").astype(str).str.strip().ne("").sum())
    return {
        "source_family": source_family,
        "source_text_field": source_text_field,
        "records_checked": int(total_rows),
        "non_null_records": non_null,
        "non_empty_records": non_empty,
        "non_empty_pct": round(100.0 * non_empty / total_rows, 2) if total_rows else 0.0,
        "coverage_status": "available" if non_empty else "not_observed",
        "raw_values_emitted": False,
    }


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    service_files = sorted(PROJECT_ROOT.glob("data/interim/extracted_source/**/api_service_v1_service-orders.xlsx"))
    pdf_rows_path = PROJECT_ROOT / "reports" / "internal" / "pdf_assets_of_concern_rows.csv"

    rows: list[dict] = []
    service_row_count = 0
    if service_files:
        frames = [pd.read_excel(path, engine="openpyxl") for path in service_files]
        service_df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
        service_row_count = int(len(service_df))
        for source_text_field, column_name in ROUTING_FIELDS.items():
            if column_name in service_df.columns:
                rows.append(
                    coverage_row(
                        "source_data_structured",
                        source_text_field,
                        service_df[column_name],
                        service_row_count,
                    )
                )
            else:
                rows.append(
                    {
                        "source_family": "source_data_structured",
                        "source_text_field": source_text_field,
                        "records_checked": service_row_count,
                        "non_null_records": 0,
                        "non_empty_records": 0,
                        "non_empty_pct": 0.0,
                        "coverage_status": "column_not_found",
                        "raw_values_emitted": False,
                    }
                )

    pdf_row_count = 0
    if pdf_rows_path.exists():
        pdf_df = pd.read_csv(pdf_rows_path)
        pdf_row_count = int(len(pdf_df))
        if "event" in pdf_df.columns:
            rows.append(coverage_row("pdf_structural_event", PDF_EVENT_FIELD, pdf_df["event"], pdf_row_count))
        else:
            rows.append(
                {
                    "source_family": "pdf_structural_event",
                    "source_text_field": PDF_EVENT_FIELD,
                    "records_checked": pdf_row_count,
                    "non_null_records": 0,
                    "non_empty_records": 0,
                    "non_empty_pct": 0.0,
                    "coverage_status": "column_not_found",
                    "raw_values_emitted": False,
                }
            )

    description_extended = next(
        (row for row in rows if row["source_text_field"] == "classification_input.description_extended"),
        None,
    )
    description_extended_status = (
        "coverage_measured"
        if description_extended and description_extended["coverage_status"] == "available"
        else "coverage_gap_or_not_found"
    )

    target_routing_risks = [
        {
            "risk_id": "F0B-001",
            "risk": "description_extended_concentration",
            "status": description_extended_status,
            "interpretation": (
                "description_extended is primary/supporting routing for multiple targets; low coverage would affect "
                "several targets at once."
            ),
            "control": "Use measured field coverage before F1 filtering and before any denominator claim.",
        },
        {
            "risk_id": "F0B-002",
            "risk": "pdf_event_structural_support",
            "status": "policy_required",
            "interpretation": (
                "pdf_assets_of_concern.event belongs to event_structural stratum and must not be merged into "
                "planned/reactive denominators."
            ),
            "control": "Evidence using PDF event support must carry stratum=event_structural or a declared mixed-source split.",
        },
    ]

    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "task": "F0b_routing_field_coverage_check",
        "service_source_files_found": len(service_files),
        "service_records_checked": service_row_count,
        "pdf_records_checked": pdf_row_count,
        "field_coverage_rows": rows,
        "target_routing_risks": target_routing_risks,
        "description_extended_status": description_extended_status,
        "stratum_policy": (
            "PDF event evidence is event_structural. It may support Object Part or Damage, but denominators must "
            "keep event_structural separate from planned/reactive strata."
        ),
        "raw_values_emitted": False,
        "outputs": {
            "field_coverage_csv": "stint-1-evidence-ground-truth/phase_0_consolidation/outputs/f0b_routing_field_coverage.csv",
            "risk_csv": "stint-1-evidence-ground-truth/phase_0_consolidation/outputs/f0b_routing_risks.csv",
            "summary_json": "stint-1-evidence-ground-truth/phase_0_consolidation/outputs/f0b_routing_field_coverage_summary.json",
            "memo": "stint-1-evidence-ground-truth/phase_0_consolidation/outputs/f0b_routing_field_coverage_memo.md",
        },
    }

    write_csv(
        OUTPUTS_DIR / "f0b_routing_field_coverage.csv",
        rows,
        [
            "source_family",
            "source_text_field",
            "records_checked",
            "non_null_records",
            "non_empty_records",
            "non_empty_pct",
            "coverage_status",
            "raw_values_emitted",
        ],
    )
    write_csv(
        OUTPUTS_DIR / "f0b_routing_risks.csv",
        target_routing_risks,
        ["risk_id", "risk", "status", "interpretation", "control"],
    )
    (OUTPUTS_DIR / "f0b_routing_field_coverage_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    lines = [
        "# F0b - Routing Field Coverage Check",
        "",
        "## Purpose",
        "",
        "This check validates two routing risks before Phase 1: concentration on `description_extended` and the stratum boundary for PDF event support.",
        "",
        "It emits aggregate coverage only and no raw operational values.",
        "",
        "## Field Coverage",
        "",
        "| source_family | source_text_field | records_checked | non_empty_records | non_empty_pct | status |",
        "|---|---|---:|---:|---:|---|",
        *[
            f"| {row['source_family']} | `{row['source_text_field']}` | {row['records_checked']} | {row['non_empty_records']} | {row['non_empty_pct']} | {row['coverage_status']} |"
            for row in rows
        ],
        "",
        "## Controls",
        "",
        "- `description_extended` coverage must be considered before F1 filtering because multiple targets depend on it as primary or supporting text.",
        "- `pdf_assets_of_concern.event` is `event_structural`. Evidence using it as support for Object Part or Damage must keep that stratum explicit.",
        "- F6 must not merge `event_structural` evidence with planned/reactive denominators.",
        "",
        "## Decision",
        "",
        "F0 remains open only if `description_extended` is unavailable or materially sparse. Otherwise F1 can proceed while preserving the explicit stratum rule.",
    ]
    (OUTPUTS_DIR / "f0b_routing_field_coverage_memo.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
