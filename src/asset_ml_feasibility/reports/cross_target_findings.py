from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TARGETS = [
    "Symptom",
    "Object Part",
    "Damage",
    "Cause",
    "Activity",
    "FLOC leaf segment",
    "Activity Type",
]


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists() or path.stat().st_size == 0:
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def as_int(value: Any, default: int = 0) -> int:
    try:
        if value in (None, ""):
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def markdown_table(rows: list[dict[str, Any]], fieldnames: list[str]) -> list[str]:
    if not rows:
        return ["_No rows._"]
    lines = [
        "| " + " | ".join(fieldnames) + " |",
        "| " + " | ".join(["---"] * len(fieldnames)) + " |",
    ]
    for row in rows:
        values = [str(row.get(field, "")).replace("\n", " ") for field in fieldnames]
        lines.append("| " + " | ".join(values) + " |")
    return lines


def load_error_triage_counts(reports_dir: Path, artifacts_dir: Path) -> dict[str, int]:
    summary = read_json(artifacts_dir / "error_triage_summary_sanitized.json")
    if summary:
        counts = summary.get("error_cause_counts", {})
        return {
            "raw_error_rows": as_int(summary.get("raw_error_rows")),
            "parser_issue": as_int(counts.get("parser_issue")),
            "parser_issue_on_tabular_files": as_int(summary.get("parser_issue_on_tabular_files")),
            "unreadable_file": as_int(counts.get("unreadable_file")),
        }

    rows = read_csv_rows(reports_dir / "error_triage_summary.csv")
    counts = {row.get("error_cause", ""): as_int(row.get("file_count")) for row in rows}
    return {
        "raw_error_rows": sum(counts.values()),
        "parser_issue": counts.get("parser_issue", 0),
        "parser_issue_on_tabular_files": counts.get("parser_issue", 0),
        "unreadable_file": counts.get("unreadable_file", 0),
    }


def build_cross_target_findings(project_root: Path) -> dict[str, Any]:
    reports_dir = project_root / "reports"
    artifacts_dir = project_root / "artifacts"

    inventory_summary = read_json(artifacts_dir / "source_inventory_summary_sanitized.json")
    schema_summary = read_json(artifacts_dir / "schema_profile_summary_sanitized.json")
    vocab_summary = read_json(artifacts_dir / "catalog_loading_summary_sanitized.json")
    if not vocab_summary:
        vocab_summary = read_json(artifacts_dir / "catalog_vocabulary_summary_sanitized.json")
    safe_pair_summary = read_json(artifacts_dir / "safe_content_pair_discovery_summary_sanitized.json")
    pair_summary = read_json(artifacts_dir / "pair_evidence_classification_summary_sanitized.json")
    pdf_summary = read_json(artifacts_dir / "pdf_assets_of_concern_summary_sanitized.json")
    readiness_summary = read_json(artifacts_dir / "ground_truth_measurement_readiness_summary_sanitized.json")
    error_counts = load_error_triage_counts(reports_dir, artifacts_dir)

    target_readiness = read_csv_rows(reports_dir / "measurement_readiness_by_target_sanitized.csv")
    unresolved_summary = read_csv_rows(reports_dir / "unresolved_opportunity_summary_sanitized.csv")
    source_denominators = read_csv_rows(reports_dir / "source_read_denominator_summary_sanitized.csv")

    unknown_rows = as_int(readiness_summary.get("unknown_opportunity_rows"))
    external_fault_rows = as_int(readiness_summary.get("external_fault_code_signal_rows"))
    external_fault_distinct = as_int(readiness_summary.get("distinct_external_fault_code_count"))
    measurement_ready_rows = as_int(readiness_summary.get("measurement_ready_pair_rows"))

    if not unknown_rows:
        unknown_rows = as_int(pair_summary.get("evidence_type_counts", {}).get("unknown"))
    if not external_fault_rows:
        external_fault_rows = as_int(pdf_summary.get("fault_code_non_empty_rows"))
    if not external_fault_distinct:
        external_fault_distinct = as_int(pdf_summary.get("distinct_fault_code_count"))

    finding_rows = [
        {
            "finding": "measurement_denominator_not_established",
            "affected_targets": "all",
            "current_evidence": f"{measurement_ready_rows} measurement-ready pair rows",
            "interpretation": "No target can yet receive accuracy, coverage, or final feasibility claims.",
            "required_action": "Validate real observed labels or SME-confirmed mappings by target.",
        },
        {
            "finding": "unknown_text_code_opportunities_preserved",
            "affected_targets": "all_pending_split",
            "current_evidence": f"{unknown_rows} unknown opportunity rows",
            "interpretation": "This is the largest unresolved bucket and may change target-level conclusions after semantic reconciliation.",
            "required_action": "Split by target relevance, source role, runtime availability, and evidence type.",
        },
        {
            "finding": "external_fault_code_vocabulary_gap",
            "affected_targets": "Damage/Cause/Activity/Object Part possible, pending SME",
            "current_evidence": f"{external_fault_rows} structured rows, {external_fault_distinct} distinct numeric fault-code tokens",
            "interpretation": "Structured external fault-code signal exists, but it does not currently map to the loaded Wind S/B/C/5/A catalog vocabulary.",
            "required_action": "Ask SME or mapping owner to identify the controlling source and SAP equivalence, if any.",
        },
        {
            "finding": "runtime_availability_not_closed",
            "affected_targets": "all",
            "current_evidence": "candidate signals are from historical files and parsed artifacts",
            "interpretation": "A candidate field is not usable by the engine until confirmed available at runtime.",
            "required_action": "Runtime app owner confirms available fields and stable extraction path.",
        },
        {
            "finding": "catalog_scope_gap",
            "affected_targets": "FLOC leaf segment; Activity Type",
            "current_evidence": "S/B/C/5/A vocabulary loaded; FLOC and MAT require separate controlled sources",
            "interpretation": "The five Wind catalog targets are not sufficient to validate FLOC or Activity Type.",
            "required_action": "Confirm FLOC vocabulary sufficiency and the controlled MAT source.",
        },
        {
            "finding": "symptom_proof_of_life_guardrail",
            "affected_targets": "Symptom",
            "current_evidence": "near-zero evidence across lexical, quality, Field Matrix, and ground-truth passes",
            "interpretation": "Symptom remains no-current-demonstrable-proof-of-life, not a final impossibility claim.",
            "required_action": "SME or source owner provides proof-of-life example if one exists.",
        },
        {
            "finding": "field_matrix_is_not_record_level_ground_truth",
            "affected_targets": "Object Part; Damage; Cause; Symptom",
            "current_evidence": "Field Matrix rates are treated as profiling/mapping coverage indicators",
            "interpretation": "Coverage rates do not automatically provide record-level labels for model measurement.",
            "required_action": "Field Matrix owner confirms whether rates represent mapping coverage or validated labels.",
        },
        {
            "finding": "parser_issue_information_loss_bucket",
            "affected_targets": "unknown_until_triage_closed",
            "current_evidence": f"{error_counts.get('parser_issue_on_tabular_files', 0)} parser issues on tabular files",
            "interpretation": "Parser issues are the remaining probable information-loss bucket after expected non-tabular handling.",
            "required_action": "Review parser issue files and decide whether additional parsers are needed.",
        },
        {
            "finding": "denominators_must_remain_block_specific",
            "affected_targets": "all",
            "current_evidence": "inventory, tabular/structured scan, PDF extraction, and pair discovery use different denominators",
            "interpretation": "Combining file counts across passes without labels can overstate or understate evidence.",
            "required_action": "Report files_listed, files_read_ok, files_failed, and zero_type per source block.",
        },
    ]

    gap_rows = [
        {
            "gap_id": "G01",
            "gap": "No measurement-ready denominator",
            "type": "label_mapping_gap",
            "targets": "all",
            "severity": "high",
            "owner_needed": "SME / mapping owner",
            "decision_needed": "Confirm record-level labels or validated mappings.",
        },
        {
            "gap_id": "G02",
            "gap": "Unknown text-code opportunities not split by target",
            "type": "semantic_reconciliation_gap",
            "targets": "all",
            "severity": "high",
            "owner_needed": "ML / SME / mapping owner",
            "decision_needed": "Classify unknown opportunities before promoting them.",
        },
        {
            "gap_id": "G03",
            "gap": "External fault-code vocabulary not identified",
            "type": "controlled_vocabulary_gap",
            "targets": "Damage/Cause/Activity/Object Part possible",
            "severity": "high",
            "owner_needed": "SME / source owner / SAP mapping owner",
            "decision_needed": "Identify controlling vocabulary and SAP equivalence.",
        },
        {
            "gap_id": "G04",
            "gap": "Runtime availability not validated",
            "type": "runtime_gap",
            "targets": "all",
            "severity": "high",
            "owner_needed": "runtime app owner",
            "decision_needed": "Confirm whether candidate fields exist at engine runtime.",
        },
        {
            "gap_id": "G05",
            "gap": "Activity Type controlled source pending",
            "type": "controlled_source_gap",
            "targets": "Activity Type",
            "severity": "high",
            "owner_needed": "source owner / SME",
            "decision_needed": "Confirm MAT/activity-type controlled source and mapping rules.",
        },
        {
            "gap_id": "G06",
            "gap": "FLOC support is not a label",
            "type": "target_specific_validation_gap",
            "targets": "FLOC leaf segment",
            "severity": "medium",
            "owner_needed": "SME / SAP functional owner",
            "decision_needed": "Confirm whether glossary/KKS support is sufficient and runtime-available.",
        },
        {
            "gap_id": "G07",
            "gap": "Symptom proof-of-life not demonstrated",
            "type": "proof_of_life_gap",
            "targets": "Symptom",
            "severity": "high",
            "owner_needed": "SME / Field Matrix owner",
            "decision_needed": "Provide validated example or accept current no-proof-of-life status.",
        },
        {
            "gap_id": "G08",
            "gap": "Remaining parser issues on tabular files",
            "type": "parser_gap",
            "targets": "unknown",
            "severity": "medium",
            "owner_needed": "ML engineering",
            "decision_needed": "Fix parser coverage or mark affected files out of scope.",
        },
    ]

    field_matrix_rows = [
        {
            "target": "Symptom",
            "field_matrix_signal": "0 resolvable mappings in profiling evidence",
            "current_reconciliation": "aligned_near_zero",
            "interpretation": "Supports no-current-demonstrable-proof-of-life, subject to SME override.",
        },
        {
            "target": "Object Part",
            "field_matrix_signal": "long-tail/singleton mapping difficulty indicator",
            "current_reconciliation": "requires_record_level_validated_mapping",
            "interpretation": "Reference coverage does not yet create measurement denominator.",
        },
        {
            "target": "Damage",
            "field_matrix_signal": "partial profiling/mapping coverage indicator",
            "current_reconciliation": "rates_exist_but_record_level_labels_not_confirmed",
            "interpretation": "Needs label/mapping validation before coverage or confidence estimates.",
        },
        {
            "target": "Cause",
            "field_matrix_signal": "low profiling/mapping coverage indicator",
            "current_reconciliation": "rates_exist_but_record_level_labels_not_confirmed",
            "interpretation": "Needs label/mapping validation before coverage or confidence estimates.",
        },
        {
            "target": "Activity",
            "field_matrix_signal": "no final measured derivability conclusion in this pass",
            "current_reconciliation": "candidate_signal_pending_validation",
            "interpretation": "Candidate evidence exists, but runtime and label/mapping validation are pending.",
        },
        {
            "target": "FLOC leaf segment",
            "field_matrix_signal": "glossary/supporting signal",
            "current_reconciliation": "supporting_signal_not_label",
            "interpretation": "KKS can support/validate interpretation; it must not resolve or build hierarchy.",
        },
        {
            "target": "Activity Type",
            "field_matrix_signal": "controlled MAT source pending",
            "current_reconciliation": "blocked_pending_controlled_source",
            "interpretation": "Cannot be measurement-ready until controlled source and mapping rules are confirmed.",
        },
    ]

    output_paths = {
        "markdown": reports_dir / "cross_target_findings_and_data_gaps_sanitized.md",
        "findings_csv": reports_dir / "cross_target_findings_summary_sanitized.csv",
        "gap_register_csv": reports_dir / "cross_target_gap_register_sanitized.csv",
        "field_matrix_csv": reports_dir / "field_matrix_reconciliation_sanitized.csv",
    }

    write_csv(
        output_paths["findings_csv"],
        finding_rows,
        ["finding", "affected_targets", "current_evidence", "interpretation", "required_action"],
    )
    write_csv(
        output_paths["gap_register_csv"],
        gap_rows,
        ["gap_id", "gap", "type", "targets", "severity", "owner_needed", "decision_needed"],
    )
    write_csv(
        output_paths["field_matrix_csv"],
        field_matrix_rows,
        ["target", "field_matrix_signal", "current_reconciliation", "interpretation"],
    )

    markdown_lines = [
        "# Asset ML Feasibility - Cross-Target Findings and Data Gaps",
        "",
        "## Scope",
        "",
        "This section consolidates cross-target findings and data gaps for the feasibility draft. It is an evidence-readiness section, not a model-training result, accuracy estimate, or final feasibility conclusion.",
        "",
        "No raw operational client values are emitted.",
        "",
        "## Current Cross-Target Position",
        "",
        f"- Inventoried files: {as_int(inventory_summary.get('total_files') or inventory_summary.get('file_count'))}",
        f"- Schema columns profiled: {as_int(schema_summary.get('schema_column_count') or schema_summary.get('column_count'))}",
        f"- Candidate text/signal columns: {as_int(schema_summary.get('candidate_column_count'))}",
        f"- Controlled catalog terms loaded for Wind S/B/C/5/A: {as_int(vocab_summary.get('term_count') or vocab_summary.get('catalog_term_count'))}",
        f"- Safe content pair opportunity rows: {as_int(safe_pair_summary.get('pair_candidate_rows'))}",
        f"- Unknown opportunity rows preserved: {unknown_rows}",
        f"- PDF-derived external fault-code rows: {external_fault_rows}",
        f"- Distinct external fault-code tokens: {external_fault_distinct}",
        f"- Measurement-ready pair rows: {measurement_ready_rows}",
        "",
        "## Cross-Target Findings",
        "",
        *markdown_table(
            finding_rows,
            ["finding", "affected_targets", "current_evidence", "interpretation", "required_action"],
        ),
        "",
        "## Gap Register",
        "",
        *markdown_table(
            gap_rows,
            ["gap_id", "gap", "type", "targets", "severity", "owner_needed", "decision_needed"],
        ),
        "",
        "## Field Matrix Reconciliation",
        "",
        *markdown_table(
            field_matrix_rows,
            ["target", "field_matrix_signal", "current_reconciliation", "interpretation"],
        ),
        "",
        "## Source Denominator Context",
        "",
        *markdown_table(
            source_denominators,
            [
                "source_block",
                "files_listed",
                "files_read_ok",
                "files_failed",
                "candidate_pairs_found",
                "measurement_ready_pairs",
                "zero_type",
            ],
        ),
        "",
        "## Unresolved Buckets",
        "",
        *markdown_table(
            unresolved_summary,
            [
                "bucket",
                "candidate_pair_rows",
                "measurement_ready_pair_rows",
                "status",
                "next_required_action",
            ],
        ),
        "",
        "## Target-Level Caveats",
        "",
        *markdown_table(
            target_readiness,
            [
                "target",
                "candidate_pair_rows",
                "row_level_pair_count",
                "distinct_files",
                "measurement_ready_pair_count",
                "measurement_readiness_status",
                "zero_type_or_denominator_status",
                "next_required_action",
            ],
        ),
        "",
        "## Required Committee Decisions",
        "",
        "- Confirm whether the evidence taxonomy is acceptable for the final assessment.",
        "- Confirm owners for runtime availability checks by source family.",
        "- Confirm whether Field Matrix rates represent coverage/profiling indicators or validated record-level labels.",
        "- Confirm the controlled source for external fault-code values and whether they map to any target.",
        "- Confirm whether unknown text-code opportunities should be split by SME review, rule prototypes, or both.",
        "- Confirm whether remaining parser issue files must be remediated before the report is finalized.",
        "",
        "## Mandatory Cautions",
        "",
        "- Reference catalogs are not ground truth.",
        "- Unknown opportunities are preserved but not measurement-ready.",
        "- Zero measurement-ready evidence does not automatically mean zero derivability.",
        "- Runtime availability must be confirmed before candidate evidence can become implementation evidence.",
        "- KKS may support or validate FLOC interpretation; it must not resolve or construct hierarchy.",
        "- Prospection thresholds are not model thresholds and not endpoint thresholds.",
        "",
        "## Non-Goals",
        "",
        "- No model training was performed.",
        "- No model accuracy estimate was produced.",
        "- No final feasibility conclusion is included.",
        "- No raw operational client values were emitted.",
    ]

    output_paths["markdown"].write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")

    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "artifact": "cross_target_findings_and_data_gaps",
        "status": "ready_for_draft_report_section_partial_for_final",
        "finding_count": len(finding_rows),
        "gap_count": len(gap_rows),
        "target_count": len(TARGETS),
        "unknown_opportunity_rows": unknown_rows,
        "external_fault_code_signal_rows": external_fault_rows,
        "distinct_external_fault_code_count": external_fault_distinct,
        "measurement_ready_pair_rows": measurement_ready_rows,
        "parser_issue_on_tabular_files": error_counts.get("parser_issue_on_tabular_files", 0),
        "raw_operational_values_emitted": False,
        "outputs": {name: str(path) for name, path in output_paths.items()},
    }
    summary_path = artifacts_dir / "cross_target_findings_summary_sanitized.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
