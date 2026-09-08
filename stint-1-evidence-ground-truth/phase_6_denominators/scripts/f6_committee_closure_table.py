from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path("stint-1-evidence-ground-truth")
OUT = ROOT / "phase_6_denominators" / "outputs"
MATRIX = OUT / "f6_evidence_denominator_matrix_sanitized.csv"
CONSOLIDATED = OUT / "f6_committee_closure_denominator_table_sanitized.csv"
CONTEXT = OUT / "f6_committee_closure_context_sanitized.json"
MEMO = OUT / "f6_committee_closure_table_memo.md"

COUNT_UNIT_MAP = {
    "estimated_event_key_x_target": "estimated_event",
    "physical_record_id_x_target": "physical_record_id",
    "refined_event_key_x_target": "estimated_event_key_with_snapshot_date",
    "candidate_text_row_or_hash_x_target": "candidate_text_row_or_hash",
    "distinct_consolidated_term_key": "distinct_consolidated_term_key",
    "not_aggregated_across_paths": "not_aggregated_across_paths",
}

STATUS_MAP = {
    "admitted": "admitted",
    "admitted_proxy_only": "admitted",
    "admitted_proxy_only_converged": "admitted",
    "not_admitted": "not_admitted",
    "declared_no_global_denominator": "explicit_zero",
}


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def safe_int(value, default=0) -> int:
    try:
        return int(float(str(value)))
    except Exception:
        return default


def parse_delta_log(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| `DELTA-"):
            continue
        parts = [part.strip() for part in line.strip("|").split("|")]
        if len(parts) < 4:
            continue
        rows.append(
            {
                "delta_id": parts[0].strip("`"),
                "topic": parts[1],
                "status": parts[2],
                "stint1_handling": parts[3],
            }
        )
    return rows


def main() -> None:
    df = pd.read_csv(MATRIX, dtype=str).fillna("")
    df["candidate_units_i"] = df["candidate_units"].map(safe_int)
    df["admitted_units_i"] = df["admitted_denominator_units"].map(safe_int)

    rows = []
    for _, row in df.sort_values(["target", "denominator_type", "path_bucket"]).iterrows():
        status = STATUS_MAP.get(row["inclusion_decision"], "not_admitted")
        if status != "admitted":
            notes = row["blocker_or_condition"]
        elif row["denominator_type"] == "proxy_poc":
            notes = "Admitted to POC proxy only; not contractual ground truth."
        else:
            notes = "Admitted to contractual denominator."
        if row["target"] == "Symptom" and row["tier"] == "silver-medium":
            notes = f"{notes} tier ceiling: silver-medium for Symptom; must not be promoted above this level."

        rows.append(
            {
                "target": row["target"],
                "path": row["path_bucket"],
                "denominator_type": row["denominator_type"],
                "evidence_type": row["evidence_type"],
                "tier": row["tier"],
                "count_unit": COUNT_UNIT_MAP.get(row["count_unit"], row["count_unit"]),
                "stratum": row["stratum"],
                "admitted_denominator_units": row["admitted_units_i"],
                "status": status,
                "notes": notes,
            }
        )

    fields = [
        "target",
        "path",
        "denominator_type",
        "evidence_type",
        "tier",
        "count_unit",
        "stratum",
        "admitted_denominator_units",
        "status",
        "notes",
    ]
    with CONSOLIDATED.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    f352 = read_json(ROOT / "phase_3_path_a_faultcodes" / "outputs" / "f352_template_aware_pdf_reparse_summary_sanitized.json")
    f354 = read_json(ROOT / "phase_3_path_a_faultcodes" / "outputs" / "f354_snapshot_dedup_summary_sanitized.json")
    f356 = read_json(ROOT / "phase_3_path_a_faultcodes" / "outputs" / "f356_path_a_integrated_crosswalk_summary_sanitized.json")
    b1 = read_json(ROOT / "phase_4_path_b_xlsx" / "outputs" / "f40b_contractor_path_001_relational_model" / "f40b_contractor_path_001_relational_model_summary_sanitized.json")
    b2 = read_json(ROOT / "phase_4_path_b_xlsx" / "outputs" / "b2_snapshot_characterization" / "b21_snapshot_summary_sanitized.json")
    b25 = read_json(ROOT / "phase_4_path_b_xlsx" / "outputs" / "b25_grouping_refinement" / "b25_grouping_refinement_summary_sanitized.json")
    deltas = parse_delta_log(ROOT / "docs" / "canonical-delta-log.md")

    context = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "artifact": str(CONSOLIDATED),
        "corpus_files_by_family": {
            "Path A PDFs": safe_int(f352.get("files_reparsed")),
            "B1 relational/API dump family": "7 logical entities; 21 redundant structured files across json/xlsx/xml",
            "B2 snapshot workbooks": safe_int(b2.get("files_discovered")),
        },
        "records_evaluated_by_branch": {
            "Path A snapshot rows": safe_int(f354.get("snapshot_rows_evaluated")),
            "Path A estimated events": safe_int(f354.get("estimated_events")),
            "Path A integrated candidate/event keys": safe_int(f356.get("event_or_candidate_keys_with_any_integrated_evidence")),
            "B1 physical records": safe_int((b1.get("record_counts") or {}).get("api_service_v1_service-orders")),
            "B2 snapshot text rows": safe_int(b25.get("snapshot_text_rows")),
            "B2 baseline date-sensitive events": safe_int(b25.get("baseline_date_sensitive_events")),
            "B2 refined events": safe_int(b25.get("refined_events")),
        },
        "open_canonical_deltas_at_stint_close": [delta for delta in deltas if delta.get("status") == "open"],
        "canonical_deltas_all": deltas,
        "scope_controls": {
            "no_global_path_aggregation": True,
            "raw_operational_values_emitted": False,
            "symptom_b2_snapshot_365_excluded_from_proxy": True,
            "floc_leaf_explicit_zero": True,
        },
    }
    CONTEXT.write_text(json.dumps(context, indent=2), encoding="utf-8")

    memo = [
        "# F6 Committee Closure Denominator Table",
        "",
        "This memo accompanies the sanitized CSV table for the STINT_1 closing report.",
        "",
        "## Files",
        "",
        f"- Consolidated table: `{CONSOLIDATED.name}`",
        f"- Context summary: `{CONTEXT.name}`",
        "",
        "## Context Figures",
        "",
        (
            f"- Path A PDFs: `{context['corpus_files_by_family']['Path A PDFs']}` files; "
            f"`{context['records_evaluated_by_branch']['Path A snapshot rows']}` rows evaluated; "
            f"`{context['records_evaluated_by_branch']['Path A estimated events']}` estimated events."
        ),
        (
            f"- B1 relational/API branch: `{context['corpus_files_by_family']['B1 relational/API dump family']}`; "
            f"`{context['records_evaluated_by_branch']['B1 physical records']}` physical records used as the main denominator unit."
        ),
        (
            f"- B2 snapshot workbooks: `{context['corpus_files_by_family']['B2 snapshot workbooks']}` files; "
            f"`{context['records_evaluated_by_branch']['B2 snapshot text rows']}` snapshot text rows; "
            f"`{context['records_evaluated_by_branch']['B2 refined events']}` refined events."
        ),
        "",
        "## Canonical Deltas",
        "",
    ]
    for delta in deltas:
        memo.append(f"- `{delta['delta_id']}`: {delta['topic']} - `{delta['status']}`. {delta['stint1_handling']}")
    memo.extend(
        [
            "",
            "## Controls",
            "",
            "- No global denominator is reported across paths.",
            "- `count_unit` is explicit in every row.",
            "- `B2_WORKBOOK_SNAPSHOTS:365` for Symptom remains diagnostic only and is not admitted to the proxy denominator.",
            "- FLOC leaf is an explicit zero: routeability exists, admitted evidence does not.",
            "- Raw operational values emitted: `false`.",
        ]
    )
    MEMO.write_text("\n".join(memo) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "consolidated_table": str(CONSOLIDATED),
                "context": str(CONTEXT),
                "memo": str(MEMO),
                "rows": len(rows),
                "admitted_rows": int((df["admitted_units_i"] > 0).sum()),
                "explicit_zero_rows": sum(1 for r in rows if r["status"] == "explicit_zero"),
                "not_admitted_rows": sum(1 for r in rows if r["status"] == "not_admitted"),
                "raw_operational_values_emitted": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
