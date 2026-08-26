from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = PROJECT_ROOT / "reports"
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"


FOCUS_SECTIONS = [
    "6. Target-Level Feasibility Assessment",
    "8. Feasibility Matrix & Recommended Technical Direction",
    "9. Required Inputs, Owners & Decisions",
    "10. Conclusions & Next Steps",
    "Appendix A. Source and Effective-Read Inventory",
    "Appendix B. Ground-Truth Evidence Tables",
    "Appendix C. Target Reconciliation Matrix",
    "Appendix D. Prospection / Threshold / Stage-Loss Evidence",
    "Appendix E. Parser, PDF and Remaining Data-Quality Issues",
]


def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path)


def safe_int(value: object, default: int = 0) -> int:
    try:
        if pd.isna(value):
            return default
        return int(value)
    except Exception:
        return default


def md_table(rows: list[dict[str, object]]) -> str:
    if not rows:
        return "_No rows._"
    df = pd.DataFrame(rows)
    headers = list(df.columns)
    rendered_rows = [
        [str(value).replace("\n", " ").replace("|", "\\|") for value in row]
        for row in df.fillna("").itertuples(index=False, name=None)
    ]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rendered_rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def main() -> int:
    target_matrix = load_csv(REPORTS_DIR / "target_level_evidence_matrix_sanitized.csv")
    readiness = load_csv(REPORTS_DIR / "report_readiness_check_sanitized.csv")
    measurement = load_csv(REPORTS_DIR / "measurement_readiness_by_target_sanitized.csv")
    gaps = load_csv(REPORTS_DIR / "cross_target_gap_register_sanitized.csv")

    target_count = len(target_matrix)
    measurement_ready_targets = safe_int(
        (target_matrix.get("measurement_ready_pair_rows", pd.Series(dtype=int)) > 0).sum()
        if not target_matrix.empty
        else 0
    )
    high_gaps = safe_int((gaps.get("severity", pd.Series(dtype=str)) == "high").sum() if not gaps.empty else 0)

    source_artifacts = {
        "target_matrix": "reports/target_level_evidence_matrix_sanitized.csv",
        "target_matrix_md": "reports/target_level_evidence_matrix_sanitized.md",
        "measurement_readiness": "reports/measurement_readiness_by_target_sanitized.csv",
        "ground_truth_readiness_md": "reports/ground_truth_measurement_readiness_sanitized.md",
        "cross_target_findings_md": "reports/cross_target_findings_and_data_gaps_sanitized.md",
        "gap_register": "reports/cross_target_gap_register_sanitized.csv",
        "readiness_baseline": "reports/report_readiness_check_sanitized.csv",
    }

    rows = [
        {
            "section": "6. Target-Level Feasibility Assessment",
            "updated_status": "partial",
            "report_mode": "draft_evidence_readiness_assessment",
            "basis": f"Target-level matrix available for {target_count} targets; measurement-ready targets: {measurement_ready_targets}.",
            "what_can_be_written_now": "Per-target signal, runtime status, mapping/label support, method direction, blockers, and SME inputs.",
            "remaining_gap": "Cannot claim final feasibility, coverage, or confidence until runtime and validated labels/mappings are confirmed.",
            "primary_artifact": source_artifacts["target_matrix_md"],
        },
        {
            "section": "8. Feasibility Matrix & Recommended Technical Direction",
            "updated_status": "partial",
            "report_mode": "directional_matrix_only",
            "basis": "Recommended method and blocker fields are now present in the target matrix.",
            "what_can_be_written_now": "A conservative technical direction matrix can be drafted with blocked/candidate/provisional statuses.",
            "remaining_gap": "Final feasibility level and confidence remain unavailable because measurement denominator is still zero.",
            "primary_artifact": source_artifacts["target_matrix"],
        },
        {
            "section": "9. Required Inputs, Owners & Decisions",
            "updated_status": "ready_for_draft",
            "report_mode": "actionable_inputs_by_target",
            "basis": f"Gap register contains {len(gaps)} gaps, including {high_gaps} high-severity gaps.",
            "what_can_be_written_now": "Target-level owner/input asks can be derived from primary_blocker and needed_from_whom.",
            "remaining_gap": "Named client owners should be filled by project leadership, not inferred by the analysis pipeline.",
            "primary_artifact": source_artifacts["gap_register"],
        },
        {
            "section": "10. Conclusions & Next Steps",
            "updated_status": "ready_for_draft",
            "report_mode": "checkpoint_conclusions_only",
            "basis": "Sections 4, 5, 7, and the regenerated target matrix provide enough evidence for a checkpoint conclusion.",
            "what_can_be_written_now": "State what can proceed to validation, what remains blocked, and what additional evidence is needed.",
            "remaining_gap": "Do not present final feasibility conclusions or model performance estimates.",
            "primary_artifact": "reports/cross_target_findings_and_data_gaps_sanitized.md",
        },
        {
            "section": "Appendix A. Source and Effective-Read Inventory",
            "updated_status": "ready_for_draft",
            "report_mode": "sanitized_inventory_appendix",
            "basis": "Sanitized inventory and read-denominator artifacts exist.",
            "what_can_be_written_now": "Source universe, effective read coverage, parser/read status, and denominators.",
            "remaining_gap": "Keep raw paths/names out of committee-facing/public artifacts.",
            "primary_artifact": "reports/source_read_denominator_summary_sanitized.csv",
        },
        {
            "section": "Appendix B. Ground-Truth Evidence Tables",
            "updated_status": "partial",
            "report_mode": "evidence_tables_no_denominator_claim",
            "basis": "Measurement readiness and classified pair artifacts exist, but measurement-ready rows remain zero.",
            "what_can_be_written_now": "Evidence taxonomy counts, unresolved opportunities, and target readiness tables.",
            "remaining_gap": "No validated denominator yet; unknown opportunities require semantic reconciliation.",
            "primary_artifact": source_artifacts["measurement_readiness"],
        },
        {
            "section": "Appendix C. Target Reconciliation Matrix",
            "updated_status": "ready_for_draft",
            "report_mode": "target_matrix_appendix",
            "basis": "Regenerated target-level evidence matrix is available.",
            "what_can_be_written_now": "Full target-by-target reconciliation across signal, runtime, mapping/label support, and blockers.",
            "remaining_gap": "Future SME/runtime validation may update statuses.",
            "primary_artifact": source_artifacts["target_matrix"],
        },
        {
            "section": "Appendix D. Prospection / Threshold / Stage-Loss Evidence",
            "updated_status": "partial",
            "report_mode": "method_history_summary",
            "basis": "Current POC pipeline has catalog loading, overlap, target mapping, and pair discovery artifacts.",
            "what_can_be_written_now": "Summarize controlled vocabulary, conservative overlap, and why thresholds are prospection-only.",
            "remaining_gap": "Threshold/stage-loss evidence should be framed as prospection methodology, not model or endpoint performance.",
            "primary_artifact": "reports/vocabulary_column_overlap_sanitized.csv",
        },
        {
            "section": "Appendix E. Parser, PDF and Remaining Data-Quality Issues",
            "updated_status": "ready_for_draft",
            "report_mode": "parser_and_quality_appendix",
            "basis": "PDF parser outputs, file profiles, and gap register exist.",
            "what_can_be_written_now": "PDF parser validation, external fault-code finding, and remaining parser/source quality gaps.",
            "remaining_gap": "External fault-code vocabulary owner/crosswalk remains an SME dependency.",
            "primary_artifact": "reports/pdf_assets_of_concern_fault_code_profile_sanitized.csv",
        },
    ]

    output_df = pd.DataFrame(rows)
    csv_path = REPORTS_DIR / "report_section_readiness_update_sanitized.csv"
    md_path = REPORTS_DIR / "report_section_readiness_update_sanitized.md"
    json_path = ARTIFACTS_DIR / "report_section_readiness_update_summary_sanitized.json"

    output_df.to_csv(csv_path, index=False)

    md_lines = [
        "# Asset Maintenance Bridge ML Feasibility - Report Section Readiness Update",
        "",
        "## Scope",
        "",
        "Focused readiness review for report sections 6, 8, 9, 10, and appendices after regenerating the target-level evidence matrix.",
        "",
        "No raw operational values are emitted.",
        "",
        "## Readiness Table",
        "",
        md_table(rows),
        "",
        "## Interpretation",
        "",
        "- Section 6 can now be drafted as target-level evidence/readiness assessment, not final feasibility.",
        "- Section 8 can be drafted as directional technical guidance, not model-ready recommendation.",
        "- Sections 9 and 10 are ready for draft using blockers, owners, and next actions from the current evidence matrix.",
        "- Appendices are mostly ready for draft; Appendix D should summarize threshold sensitivity and stage-loss as POC prospection evidence.",
        "- Final feasibility, coverage, and confidence remain gated by runtime validation and validated label/mapping evidence.",
    ]
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "artifact": "report_section_readiness_update",
        "focused_section_count": len(rows),
        "status_counts": output_df["updated_status"].value_counts().to_dict(),
        "target_count": target_count,
        "measurement_ready_targets": measurement_ready_targets,
        "high_severity_gap_count": high_gaps,
        "raw_operational_values_emitted": False,
        "outputs": {
            "csv": str(csv_path.relative_to(PROJECT_ROOT)),
            "markdown": str(md_path.relative_to(PROJECT_ROOT)),
            "summary_json": str(json_path.relative_to(PROJECT_ROOT)),
        },
    }
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
