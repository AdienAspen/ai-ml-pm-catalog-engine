from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = PROJECT_ROOT / "reports"
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"


def exists(path: str) -> bool:
    return (PROJECT_ROOT / path).exists()


def load_json(path: str) -> dict:
    p = PROJECT_ROOT / path
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def status_from_required(required: list[str], blockers: list[str] | None = None) -> str:
    blockers = blockers or []
    if blockers:
        return "blocked"
    present = sum(1 for item in required if exists(item))
    if present == len(required):
        return "ready"
    if present > 0:
        return "partial"
    return "blocked"


def artifact_list(items: list[str]) -> str:
    present = [item for item in items if exists(item)]
    missing = [item for item in items if not exists(item)]
    parts = []
    if present:
        parts.append("present: " + ", ".join(present))
    if missing:
        parts.append("missing: " + ", ".join(missing))
    return " | ".join(parts)


def main() -> int:
    inventory = load_json("artifacts/source_inventory_summary_sanitized.json")
    structural = load_json("artifacts/basic_structural_scan_summary_sanitized.json")
    schema = load_json("artifacts/schema_profile_summary_sanitized.json")
    catalog = load_json("artifacts/catalog_loading_summary_sanitized.json")
    overlap = load_json("artifacts/vocabulary_column_overlap_summary_sanitized.json")
    target_mapping = load_json("artifacts/preliminary_target_mapping_summary_sanitized.json")
    content_pairs = load_json("artifacts/safe_content_pair_discovery_summary_sanitized.json")
    evidence = load_json("artifacts/pair_evidence_classification_summary_sanitized.json")
    pdf_parser = load_json("artifacts/pdf_assets_of_concern_summary_sanitized.json")

    rows = [
        {
            "section": "1. Executive Summary",
            "status": "partial",
            "feeding_artifacts": artifact_list(
                [
                    "artifacts/source_inventory_summary_sanitized.json",
                    "artifacts/schema_profile_summary_sanitized.json",
                    "artifacts/pair_evidence_classification_summary_sanitized.json",
                    "artifacts/pdf_assets_of_concern_summary_sanitized.json",
                ]
            ),
            "current_basis": "Enough for a draft summary of current evidence, but not for final feasibility status.",
            "blockers_or_gaps": "Final feasibility decisions, SME validation, runtime validation, and measurement denominator are not closed.",
            "safe_to_report_now": "draft_only",
        },
        {
            "section": "2. Assessment Scope & Questions",
            "status": "ready",
            "feeding_artifacts": "Project methodology and seven-target scope; no data artifact required.",
            "current_basis": "Scope, non-goals, seven targets, and validation chain are stable.",
            "blockers_or_gaps": "None for methodology framing.",
            "safe_to_report_now": "yes",
        },
        {
            "section": "3. Data Universe & Effective Read Coverage",
            "status": "partial",
            "feeding_artifacts": artifact_list(
                [
                    "reports/source_file_inventory_sanitized.csv",
                    "reports/basic_structural_scan_sanitized.csv",
                    "reports/pdf_assets_of_concern_file_profile_sanitized.csv",
                    "artifacts/source_inventory_summary_sanitized.json",
                    "artifacts/basic_structural_scan_summary_sanitized.json",
                    "artifacts/pdf_assets_of_concern_summary_sanitized.json",
                ]
            ),
            "current_basis": (
                f"Inventory files: {inventory.get('file_count', 'unknown')}; "
                f"structural read attempts: {structural.get('files_attempted', 'unknown')}; "
                f"PDF files listed/read OK: {pdf_parser.get('files_listed', 'unknown')}/"
                f"{pdf_parser.get('files_read_ok', 'unknown')}."
            ),
            "blockers_or_gaps": "Remaining parser/source gaps require explicit zero_type handling in the final report.",
            "safe_to_report_now": "with_cautions",
        },
        {
            "section": "4. Evidence & Validation Method",
            "status": "partial",
            "feeding_artifacts": artifact_list(
                [
                    "reports/catalog_vocabulary_terms_sanitized.csv",
                    "reports/vocabulary_column_overlap_sanitized.csv",
                    "reports/preliminary_target_mapping_sanitized.csv",
                    "reports/pair_evidence_classification_sanitized.csv",
                ]
            ),
            "current_basis": (
                "Controlled vocabulary, safe overlap, target mapping, and evidence taxonomy are implemented. "
                "The validation chain is defined and enforced conservatively."
            ),
            "blockers_or_gaps": "Runtime availability remains a validation gap, not a completed check.",
            "safe_to_report_now": "with_cautions",
        },
        {
            "section": "5. Ground-Truth & Measurement Readiness",
            "status": "partial",
            "feeding_artifacts": artifact_list(
                [
                    "reports/pair_evidence_classification_sanitized.csv",
                    "reports/target_pair_review_sanitized.csv",
                    "artifacts/pair_evidence_classification_summary_sanitized.json",
                    "reports/safe_content_pair_discovery_sanitized.csv",
                ]
            ),
            "current_basis": (
                f"Classified pair rows: {evidence.get('classified_pair_rows', 'unknown')}; "
                f"measurement-ready pair rows: {evidence.get('measurement_ready_pair_rows', 'unknown')}; "
                f"unknown evidence rows: {evidence.get('evidence_type_counts', {}).get('unknown', 'unknown')}."
            ),
            "blockers_or_gaps": "No measurement-ready denominator yet; unknown opportunities require semantic reconciliation and SME/runtime validation.",
            "safe_to_report_now": "with_cautions",
        },
        {
            "section": "6. Target-Level Feasibility Assessment",
            "status": "blocked",
            "feeding_artifacts": artifact_list(
                [
                    "reports/target_pair_review_sanitized.csv",
                    "reports/preliminary_target_mapping_sanitized.csv",
                    "reports/pdf_assets_of_concern_fault_code_profile_sanitized.csv",
                ]
            ),
            "current_basis": "Target-level signals and candidate states exist, but feasibility by target is not yet established.",
            "blockers_or_gaps": "Needs valid labels/mappings, runtime confirmation, SME inputs, and target-specific method decisions.",
            "safe_to_report_now": "no_final_conclusion",
        },
        {
            "section": "7. Cross-Target Findings & Data Gaps",
            "status": "partial",
            "feeding_artifacts": artifact_list(
                [
                    "reports/candidate_schema_columns_sanitized.csv",
                    "reports/safe_content_pair_discovery_sanitized.csv",
                    "reports/pdf_assets_of_concern_fault_code_profile_sanitized.csv",
                    "artifacts/pdf_assets_of_concern_summary_sanitized.json",
                ]
            ),
            "current_basis": (
                f"Safe content pair candidate rows: {content_pairs.get('pair_candidate_rows', 'unknown')}; "
                f"PDF non-empty fault-code rows: {pdf_parser.get('fault_code_non_empty_rows', 'unknown')}; "
                f"distinct PDF fault codes: {pdf_parser.get('distinct_fault_code_count', 'unknown')}."
            ),
            "blockers_or_gaps": "Field Matrix reconciliation and unknown bucket semantic split remain incomplete in the current POC evidence set.",
            "safe_to_report_now": "with_cautions",
        },
        {
            "section": "8. Feasibility Matrix & Recommended Technical Direction",
            "status": "blocked",
            "feeding_artifacts": artifact_list(
                [
                    "reports/target_pair_review_sanitized.csv",
                    "artifacts/pair_evidence_classification_summary_sanitized.json",
                ]
            ),
            "current_basis": "A draft readiness matrix can be created, but recommended technical direction cannot be finalized.",
            "blockers_or_gaps": "Target-specific feasibility levels depend on ground-truth, runtime, and SME decisions.",
            "safe_to_report_now": "draft_matrix_only",
        },
        {
            "section": "9. Required Inputs, Owners & Decisions",
            "status": "partial",
            "feeding_artifacts": artifact_list(
                [
                    "reports/target_pair_review_sanitized.csv",
                    "reports/pdf_assets_of_concern_fault_code_profile_sanitized.csv",
                ]
            ),
            "current_basis": "Known asks can be listed by target and evidence gap.",
            "blockers_or_gaps": "Owner names should be assigned by the project team; avoid client-specific identifiers in versioned artifacts.",
            "safe_to_report_now": "with_cautions",
        },
        {
            "section": "10. Conclusions & Next Steps",
            "status": "partial",
            "feeding_artifacts": artifact_list(
                [
                    "artifacts/pair_evidence_classification_summary_sanitized.json",
                    "artifacts/pdf_assets_of_concern_summary_sanitized.json",
                ]
            ),
            "current_basis": "Next steps are clear: semantic reconciliation, runtime validation, SME vocabulary ownership, and parser gap closure.",
            "blockers_or_gaps": "Conclusions must remain non-final until measurement readiness exists.",
            "safe_to_report_now": "next_steps_only",
        },
        {
            "section": "Appendix A. Source and Effective-Read Inventory",
            "status": "partial",
            "feeding_artifacts": artifact_list(
                [
                    "reports/source_file_inventory_sanitized.csv",
                    "reports/basic_structural_scan_sanitized.csv",
                    "reports/pdf_assets_of_concern_file_profile_sanitized.csv",
                ]
            ),
            "current_basis": "Sanitized source and effective-read artifacts exist.",
            "blockers_or_gaps": "Needs final consolidation across parser families with zero_type.",
            "safe_to_report_now": "with_cautions",
        },
        {
            "section": "Appendix B. Ground-Truth Evidence Tables",
            "status": "partial",
            "feeding_artifacts": artifact_list(
                [
                    "reports/pair_evidence_classification_sanitized.csv",
                    "reports/target_pair_review_sanitized.csv",
                ]
            ),
            "current_basis": "Evidence classification tables exist and are conservative.",
            "blockers_or_gaps": "Unknown opportunities and measurement-ready denominator remain unresolved.",
            "safe_to_report_now": "with_cautions",
        },
        {
            "section": "Appendix C. Target Reconciliation Matrix",
            "status": "partial",
            "feeding_artifacts": artifact_list(
                [
                    "reports/preliminary_target_mapping_sanitized.csv",
                    "reports/target_pair_review_sanitized.csv",
                ]
            ),
            "current_basis": "Preliminary target mapping exists.",
            "blockers_or_gaps": "Full Field Matrix reconciliation is not yet rebuilt in local STINT_0 artifacts.",
            "safe_to_report_now": "with_cautions",
        },
        {
            "section": "Appendix D. Prospection / Threshold / Stage-Loss Evidence",
            "status": "partial",
            "feeding_artifacts": artifact_list(
                [
                    "reports/vocabulary_column_overlap_sanitized.csv",
                    "reports/preliminary_target_mapping_sanitized.csv",
                ]
            ),
            "current_basis": (
                f"Vocabulary rows: {catalog.get('catalog_term_count', 'unknown')}; "
                f"overlap rows: {overlap.get('overlap_rows', 'unknown')}; "
                f"target mapping rows: {target_mapping.get('mapping_rows', 'unknown')}."
            ),
            "blockers_or_gaps": "Dual-threshold and stage-loss evidence should be consolidated as POC prospection methodology before final reporting.",
            "safe_to_report_now": "partial_only",
        },
        {
            "section": "Appendix E. Parser, PDF and Remaining Data-Quality Issues",
            "status": "partial",
            "feeding_artifacts": artifact_list(
                [
                    "reports/pdf_assets_of_concern_file_profile_sanitized.csv",
                    "reports/pdf_assets_of_concern_fault_code_profile_sanitized.csv",
                    "artifacts/pdf_assets_of_concern_summary_sanitized.json",
                    "reports/internal/basic_structural_scan_errors.csv",
                ]
            ),
            "current_basis": "PDF parser is rebuilt, verified, and batch-run with sanitized outputs.",
            "blockers_or_gaps": "Remaining tabular parser issues and non-PDF parser refinements should be triaged before final conclusions.",
            "safe_to_report_now": "with_cautions",
        },
    ]

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    csv_path = REPORTS_DIR / "report_readiness_check_sanitized.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    status_counts: dict[str, int] = {}
    for row in rows:
        status_counts[row["status"]] = status_counts.get(row["status"], 0) + 1

    md_lines = [
        "# Asset ML Feasibility - Report Readiness Check",
        "",
        "## Scope",
        "",
        "Readiness check against the requested technical assessment table of contents. This is a sanitized planning artifact: no raw operational values, no model training, no accuracy estimates, and no final feasibility conclusions.",
        "",
        "## Overall Status",
        "",
        f"- Ready sections: {status_counts.get('ready', 0)}",
        f"- Partial sections: {status_counts.get('partial', 0)}",
        f"- Blocked sections: {status_counts.get('blocked', 0)}",
        "- Current report mode: draft / evidence-readiness only",
        "",
        "## Readiness Matrix",
        "",
        "| Section | Status | Safe to report now | Feeding artifacts | Blockers or gaps |",
        "| --- | --- | --- | --- | --- |",
    ]

    for row in rows:
        md_lines.append(
            "| "
            + " | ".join(
                [
                    row["section"].replace("|", "/"),
                    row["status"],
                    row["safe_to_report_now"],
                    row["feeding_artifacts"].replace("|", "/"),
                    row["blockers_or_gaps"].replace("|", "/"),
                ]
            )
            + " |"
        )

    md_lines.extend(
        [
            "",
            "## Key Interpretation",
            "",
            "- The report can be drafted as an evidence-readiness assessment, not as a final feasibility conclusion.",
            "- Sections 1, 3, 4, 5, 7, 9, 10, and Appendices A-E have enough current evidence for controlled drafting with caveats.",
            "- Section 6 and Section 8 remain blocked for final target feasibility because runtime availability, valid labels/mappings, and SME decisions are not closed.",
            "- The controlled validation chain remains mandatory: signal exists -> runtime usable -> valid label/mapping -> measurable target -> feasible method.",
            "",
            "## Immediate Gaps To Close",
            "",
            "- Reconstruct dual-threshold and stage-loss evidence locally if it must be cited in the final report.",
            "- Reconcile unknown text-code opportunities before promoting them to any target.",
            "- Confirm runtime availability for candidate source fields.",
            "- Obtain SME or mapping-owner validation for candidate labels/mappings and PDF-derived fault-code vocabulary ownership.",
            "- Keep zero findings labeled with the effective-read denominator and zero_type.",
        ]
    )

    md_path = REPORTS_DIR / "report_readiness_check_sanitized.md"
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "artifact": "report_readiness_check",
        "raw_operational_values_emitted": False,
        "section_count": len(rows),
        "status_counts": status_counts,
        "current_report_mode": "draft_evidence_readiness_only",
        "outputs": {
            "csv": str(csv_path.relative_to(PROJECT_ROOT)),
            "markdown": str(md_path.relative_to(PROJECT_ROOT)),
        },
    }

    summary_path = ARTIFACTS_DIR / "report_readiness_check_summary_sanitized.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
