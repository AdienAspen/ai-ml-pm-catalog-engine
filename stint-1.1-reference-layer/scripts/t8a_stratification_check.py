from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
STINT_ROOT = PROJECT_ROOT / "stint-1.1-reference-layer"
DOCS_DIR = STINT_ROOT / "docs"
OUTPUTS_DIR = STINT_ROOT / "outputs"

DOCS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

SCHEMA_PROFILE = PROJECT_ROOT / "reports/internal/schema_profile.csv"
PDF_ROWS = PROJECT_ROOT / "reports/internal/pdf_assets_of_concern_rows.csv"
PDF_STATUS = PROJECT_ROOT / "reports/internal/pdf_assets_of_concern_file_status.csv"
VESTAS_SERVICE_ORDERS = (
    PROJECT_ROOT
    / "data/interim/extracted_source/package_001_37cac7fe/Data/Vestas/api_service_v1_service-orders.xlsx"
)


def stable_key(value: object, prefix: str) -> str:
    raw = "" if pd.isna(value) else str(value)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:8]
    return f"{prefix}-{digest}"


def pct(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round(100.0 * numerator / denominator, 2)


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def source_family(relative_path: str) -> str:
    lower = relative_path.lower()
    if "/vestas/" in lower:
        return "CONTRACTOR_PATH_001"
    if "latigo" in lower:
        return "CONTRACTOR_PATH_002"
    if "laurel" in lower:
        return "CONTRACTOR_PATH_003"
    if "prevailing" in lower:
        return "CONTRACTOR_PATH_004"
    return "UNKNOWN_PATH"


def maintenance_bucket(value: object) -> str:
    text = "" if pd.isna(value) else str(value).strip().lower()
    if not text:
        return "blank"
    if "unscheduled" in text or "repair" in text or "corrective" in text or "reactive" in text:
        return "reactive_like"
    if "scheduled" in text or "maintenance" in text or "planned" in text or "preventive" in text:
        return "planned_like"
    if "additional" in text or "other" in text or "cim" in text:
        return "other_explicit_value"
    return "unclassified_explicit_value"


def load_vestas_activity_type() -> tuple[list[dict], list[dict]]:
    rows: list[dict] = []
    coverage_rows: list[dict] = []
    if not VESTAS_SERVICE_ORDERS.exists():
        return rows, coverage_rows

    df = pd.read_excel(VESTAS_SERVICE_ORDERS, engine="openpyxl")
    total = len(df)
    source_field = "activityType"
    site_field = "siteId"
    activity_present = source_field in df.columns
    site_present = site_field in df.columns

    coverage_rows.append(
        {
            "contractor_path": "CONTRACTOR_PATH_001",
            "source_family": "source_data",
            "source_file_role": "service_orders",
            "records": total,
            "maintenance_type_field": source_field if activity_present else "",
            "maintenance_type_field_present": activity_present,
            "maintenance_type_non_null_rows": int(df[source_field].notna().sum()) if activity_present else 0,
            "maintenance_type_coverage_pct": pct(int(df[source_field].notna().sum()), total) if activity_present else 0.0,
            "site_field": site_field if site_present else "",
            "site_field_present": site_present,
            "site_non_null_rows": int(df[site_field].notna().sum()) if site_present else 0,
            "site_coverage_pct": pct(int(df[site_field].notna().sum()), total) if site_present else 0.0,
            "raw_values_emitted": False,
        }
    )

    if activity_present:
        group_cols = [source_field]
        if site_present:
            group_cols.append(site_field)
        grouped = df.groupby(group_cols, dropna=False).size().reset_index(name="row_count")
        for _, record in grouped.iterrows():
            value = record[source_field]
            rows.append(
                {
                    "contractor_path": "CONTRACTOR_PATH_001",
                    "site_key": stable_key(record[site_field], "SITE") if site_present else "SITE-UNKNOWN",
                    "source_family": "source_data",
                    "maintenance_type_source": "explicit_field",
                    "source_field": source_field,
                    "source_value_bucket": maintenance_bucket(value),
                    "source_value_key": stable_key(value, "VALUE"),
                    "row_count": int(record["row_count"]),
                    "evidence_type": "real_observed_label",
                    "raw_values_emitted": False,
                }
            )
    return rows, coverage_rows


def load_pdf_event_distribution() -> tuple[list[dict], list[dict]]:
    rows: list[dict] = []
    coverage_rows: list[dict] = []
    if not PDF_ROWS.exists():
        return rows, coverage_rows

    df = pd.read_csv(PDF_ROWS)
    total = len(df)
    event_present = "event" in df.columns
    site_present = "site_text" in df.columns
    file_present = "file_hash" in df.columns

    coverage_rows.append(
        {
            "contractor_path": "CONTRACTOR_PATH_003",
            "source_family": "source_data",
            "source_file_role": "pdf_assets_of_concern",
            "records": total,
            "maintenance_type_field": "event" if event_present else "",
            "maintenance_type_field_present": event_present,
            "maintenance_type_non_null_rows": int(df["event"].notna().sum()) if event_present else 0,
            "maintenance_type_coverage_pct": pct(int(df["event"].notna().sum()), total) if event_present else 0.0,
            "site_field": "site_text" if site_present else "",
            "site_field_present": site_present,
            "site_non_null_rows": int(df["site_text"].notna().sum()) if site_present else 0,
            "site_coverage_pct": pct(int(df["site_text"].notna().sum()), total) if site_present else 0.0,
            "raw_values_emitted": False,
        }
    )

    if event_present:
        group_cols = ["event"]
        if site_present:
            group_cols.append("site_text")
        if file_present:
            file_counts = df.groupby(group_cols, dropna=False)["file_hash"].nunique().reset_index(name="file_count")
        else:
            file_counts = None
        grouped = df.groupby(group_cols, dropna=False).size().reset_index(name="row_count")
        if file_counts is not None:
            grouped = grouped.merge(file_counts, on=group_cols, how="left")
        else:
            grouped["file_count"] = 0
        for _, record in grouped.iterrows():
            value = record["event"]
            rows.append(
                {
                    "contractor_path": "CONTRACTOR_PATH_003",
                    "site_key": stable_key(record["site_text"], "SITE") if site_present else "SITE-UNKNOWN",
                    "source_family": "source_data",
                    "maintenance_type_source": "structured_event_field_not_maintenance_type",
                    "source_field": "event",
                    "source_value_bucket": maintenance_bucket(value),
                    "source_value_key": stable_key(value, "VALUE"),
                    "row_count": int(record["row_count"]),
                    "evidence_type": "real_observed_label",
                    "raw_values_emitted": False,
                }
            )
    return rows, coverage_rows


def candidate_field_inventory() -> list[dict]:
    if not SCHEMA_PROFILE.exists():
        return []
    df = pd.read_csv(SCHEMA_PROFILE)
    safe_fields = {
        "activitytype": "activity_type",
        "activity_type": "activity_type",
        "maintactivitytype": "activity_type",
        "maintenance_plant": "site_or_plant",
        "planning_plant": "site_or_plant",
        "siteid": "site_or_plant",
        "site_id": "site_or_plant",
        "order_type": "order_type",
        "priority": "priority",
        "priority_text": "priority",
        "event": "structured_event",
        "fault_code": "fault_signal",
        "contractid": "contract_identifier",
        "servicecontractid": "contract_identifier",
    }
    rows: list[dict] = []
    for _, r in df.iterrows():
        normalized = str(r.get("normalized_column_name", "")).lower()
        matched_role = ""
        for field_name, field_role in safe_fields.items():
            if normalized == field_name:
                matched_role = field_role
                break
        if not matched_role:
            continue
        rows.append(
            {
                "contractor_path": source_family(str(r.get("relative_path", ""))),
                "likely_role": r.get("likely_role", ""),
                "data_family": r.get("data_family", ""),
                "runtime_likelihood": r.get("runtime_likelihood", ""),
                "column_role": r.get("candidate_bucket", ""),
                "safe_field_name": normalized,
                "safe_field_role": matched_role,
                "column_key": stable_key(r.get("column_name", ""), "COLUMN"),
                "row_count_estimate": int(r.get("row_count_estimate") or 0),
                "null_rate": r.get("null_rate", ""),
                "raw_values_emitted": False,
            }
        )
    return rows


def main() -> None:
    distribution_rows: list[dict] = []
    coverage_rows: list[dict] = []

    v_dist, v_cov = load_vestas_activity_type()
    p_dist, p_cov = load_pdf_event_distribution()
    distribution_rows.extend(v_dist)
    distribution_rows.extend(p_dist)
    coverage_rows.extend(v_cov)
    coverage_rows.extend(p_cov)

    field_rows = candidate_field_inventory()

    write_csv(
        OUTPUTS_DIR / "t8a_maintenance_type_distribution_v1.csv",
        distribution_rows,
        [
            "contractor_path",
            "site_key",
            "source_family",
            "maintenance_type_source",
            "source_field",
            "source_value_bucket",
            "source_value_key",
            "row_count",
            "evidence_type",
            "raw_values_emitted",
        ],
    )
    write_csv(
        OUTPUTS_DIR / "t8a_stratification_coverage_v1.csv",
        coverage_rows,
        [
            "contractor_path",
            "source_family",
            "source_file_role",
            "records",
            "maintenance_type_field",
            "maintenance_type_field_present",
            "maintenance_type_non_null_rows",
            "maintenance_type_coverage_pct",
            "site_field",
            "site_field_present",
            "site_non_null_rows",
            "site_coverage_pct",
            "raw_values_emitted",
        ],
    )
    write_csv(
        OUTPUTS_DIR / "t8a_candidate_stratification_fields_v1.csv",
        field_rows,
        [
            "contractor_path",
            "likely_role",
            "data_family",
            "runtime_likelihood",
            "column_role",
            "safe_field_name",
            "safe_field_role",
            "column_key",
            "row_count_estimate",
            "null_rate",
            "raw_values_emitted",
        ],
    )

    explicit_direct = any(
        row["maintenance_type_source"] == "explicit_field" and row["source_field"] == "activityType"
        for row in distribution_rows
    )
    structured_event = any(row["maintenance_type_source"].startswith("structured_event") for row in distribution_rows)

    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "task": "T8a_stratification_check",
        "output_case": "A_partial_B_pending",
        "explicit_maintenance_type_available": explicit_direct,
        "explicit_maintenance_type_scope": "CONTRACTOR_PATH_001 service orders only" if explicit_direct else "",
        "structured_event_field_available": structured_event,
        "structured_event_field_scope": "CONTRACTOR_PATH_003 PDF assets-of-concern rows" if structured_event else "",
        "maintenance_distribution_rows": len(distribution_rows),
        "coverage_rows": len(coverage_rows),
        "candidate_field_rows": len(field_rows),
        "free_text_inference_performed": False,
        "raw_values_emitted": False,
        "outputs": {
            "distribution_csv": "stint-1.1-reference-layer/outputs/t8a_maintenance_type_distribution_v1.csv",
            "coverage_csv": "stint-1.1-reference-layer/outputs/t8a_stratification_coverage_v1.csv",
            "candidate_fields_csv": "stint-1.1-reference-layer/outputs/t8a_candidate_stratification_fields_v1.csv",
            "memo": "stint-1.1-reference-layer/docs/t8a_stratification_check.md",
        },
    }
    (OUTPUTS_DIR / "t8a_stratification_summary_v1.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    coverage_by_role = {row["source_file_role"]: row for row in coverage_rows}
    service_orders = coverage_by_role.get("service_orders", {})
    pdf_rows = coverage_by_role.get("pdf_assets_of_concern", {})

    lines = [
        "# T8a - Stratification Check",
        "",
        "## Purpose",
        "",
        "This precondition check determines whether T8 lexical sampling can be stratified by maintenance type and by contractor/site before dictionary construction begins.",
        "",
        "No free-text maintenance-type inference is performed in this task. Outputs are aggregate and sanitized.",
        "",
        "## Answers to Required Questions",
        "",
        "### 1. Explicit Maintenance-Type Field",
        "",
        "- `CONTRACTOR_PATH_001` service orders contain an explicit `activityType` field.",
        f"- Coverage: {service_orders.get('maintenance_type_non_null_rows', 0)} / {service_orders.get('records', 0)} rows ({service_orders.get('maintenance_type_coverage_pct', 0.0)}%).",
        "- This supports direct stratification for that path.",
        "- For the PDF assets-of-concern path, `event` exists as a structured table field, but it is not declared as maintenance type. It can support a separate event stratum, not a direct planned/reactive label without downstream rules.",
        f"- PDF event coverage: {pdf_rows.get('maintenance_type_non_null_rows', 0)} / {pdf_rows.get('records', 0)} rows ({pdf_rows.get('maintenance_type_coverage_pct', 0.0)}%).",
        "",
        "### 2. Values and Distribution",
        "",
        "- Value distributions are emitted in `outputs/t8a_maintenance_type_distribution_v1.csv` using value keys and coarse buckets, not raw operational text.",
        "- Nomenclature is path-specific and must not be unified at T8a. `activityType` and PDF `event` are separate fields with different semantics.",
        "",
        "### 3. Derivable Fields",
        "",
        "- Potential derivation fields exist, including order type, priority, event, and fault-code presence.",
        "- No derivation rule is applied here, because deriving maintenance type from text or mixed operational signals belongs to STINT_1 evidence engineering, not this pre-sampling profile check.",
        "",
        "### 4. Contractor/Site Segmentation",
        "",
        "- Contractor/path segmentation is direct from source path families and is emitted as sanitized `CONTRACTOR_PATH_*` keys.",
        f"- `CONTRACTOR_PATH_001` service orders contain `siteId` with {service_orders.get('site_non_null_rows', 0)} / {service_orders.get('records', 0)} rows ({service_orders.get('site_coverage_pct', 0.0)}%).",
        f"- PDF assets-of-concern rows contain structured site text with {pdf_rows.get('site_non_null_rows', 0)} / {pdf_rows.get('records', 0)} rows ({pdf_rows.get('site_coverage_pct', 0.0)}%).",
        "",
        "## Declared Output Case",
        "",
        "Case `A_partial_B_pending` applies.",
        "",
        "- A: direct stratification is available for the service-order path through `activityType`.",
        "- A-event: PDF rows have a structured `event` field, but this is not equivalent to maintenance type and must remain separate.",
        "- B pending: other source paths may require derivation from order type, priority, event, fault-code presence, or description patterns, but no such inference is performed in T8a.",
        "",
        "## Implication for T8 Sampling",
        "",
        "- T8 must stratify `CONTRACTOR_PATH_001` by `activityType` and site key.",
        "- T8 may stratify PDF rows by structured `event` and site key, but must not call that planned/reactive maintenance type without a documented STINT_1 rule.",
        "- T8 must record `source_text_field` for every sampled term, per `DELTA-0003`.",
        "- Symptom and Cause sampling must avoid mixing planned-like and reactive-like strata when a direct stratum exists.",
        "",
        "## Outputs",
        "",
        "- `outputs/t8a_maintenance_type_distribution_v1.csv`",
        "- `outputs/t8a_stratification_coverage_v1.csv`",
        "- `outputs/t8a_candidate_stratification_fields_v1.csv`",
        "- `outputs/t8a_stratification_summary_v1.json`",
    ]
    (DOCS_DIR / "t8a_stratification_check.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
