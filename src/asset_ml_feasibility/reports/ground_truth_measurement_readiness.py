from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
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

MEASUREMENT_READY_EVIDENCE_TYPES = {"real_observed_label", "validated_mapping"}
NON_MEASUREMENT_EVIDENCE_TYPES = {
    "illustrative_example",
    "reference_catalog",
    "agent_inference",
    "unknown",
}


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
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
            writer.writerow({name: row.get(name, "") for name in fieldnames})


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
    lines = []
    lines.append("| " + " | ".join(fieldnames) + " |")
    lines.append("| " + " | ".join(["---"] * len(fieldnames)) + " |")
    for row in rows:
        values = [str(row.get(field, "")).replace("\n", " ") for field in fieldnames]
        lines.append("| " + " | ".join(values) + " |")
    return lines


def classify_target_readiness(target: str, measurement_ready: int, candidate_rows: int) -> tuple[str, str, str]:
    if measurement_ready > 0:
        return (
            "measurement_candidate_found",
            "validated_denominator_candidate",
            "Confirm runtime availability and SME acceptance before any performance estimate.",
        )

    if target == "Symptom":
        return (
            "no_current_measurement_denominator",
            "no_current_demonstrable_proof_of_life",
            "Keep under explicit proof-of-life review; do not infer from broad narrative text.",
        )

    if target == "Activity Type":
        return (
            "no_current_measurement_denominator",
            "pending_controlled_mat_source",
            "Confirm the controlled source and mapping rules before treating this target as measurable.",
        )

    if target == "FLOC leaf segment":
        return (
            "no_current_measurement_denominator",
            "supporting_vocabulary_not_record_label",
            "Validate whether the glossary and KKS support are sufficient for ML/NLP use.",
        )

    if candidate_rows > 0:
        return (
            "candidate_signal_without_measurement_denominator",
            "requires_label_or_mapping_validation",
            "Validate whether candidate pairs are runtime-available record-level labels or validated mappings.",
        )

    return (
        "no_current_measurement_denominator",
        "no_candidate_pair_found_after_successful_read_or_not_target_specific",
        "Do not interpret as zero derivability; confirm source coverage and target-specific labels.",
    )


def build_section(project_root: Path) -> dict[str, Any]:
    reports_dir = project_root / "reports"
    artifacts_dir = project_root / "artifacts"

    pair_summary = read_json(artifacts_dir / "pair_evidence_classification_summary_sanitized.json")
    safe_pair_summary = read_json(artifacts_dir / "safe_content_pair_discovery_summary_sanitized.json")
    pdf_summary = read_json(artifacts_dir / "pdf_assets_of_concern_summary_sanitized.json")
    source_inventory_summary = read_json(artifacts_dir / "source_inventory_summary_sanitized.json")

    classified_rows = read_csv_rows(reports_dir / "pair_evidence_classification_sanitized.csv")
    target_review_rows = read_csv_rows(reports_dir / "target_pair_review_sanitized.csv")

    target_review_by_target: dict[str, dict[str, str]] = {
        row.get("target", ""): row for row in target_review_rows if row.get("target")
    }

    evidence_type_counts = Counter()
    measurement_ready_count = 0
    target_candidate_counts = Counter()
    target_measurement_counts = Counter()

    for row in classified_rows:
        evidence_type = row.get("evidence_type", "unknown") or "unknown"
        evidence_type_counts[evidence_type] += 1
        target = row.get("target") or row.get("target_relevance") or "unknown"
        target_candidate_counts[target] += 1
        can_support = str(row.get("can_support_measurement", "")).strip().lower() == "true"
        if evidence_type in MEASUREMENT_READY_EVIDENCE_TYPES and can_support:
            measurement_ready_count += 1
            target_measurement_counts[target] += 1

    evidence_rows: list[dict[str, Any]] = []
    for evidence_type in [
        "real_observed_label",
        "validated_mapping",
        "illustrative_example",
        "reference_catalog",
        "agent_inference",
        "unknown",
    ]:
        evidence_rows.append(
            {
                "evidence_type": evidence_type,
                "can_enter_measurement_denominator": evidence_type in MEASUREMENT_READY_EVIDENCE_TYPES,
                "current_pair_rows": int(evidence_type_counts.get(evidence_type, 0)),
                "interpretation": (
                    "eligible_after_runtime_and_sme_validation"
                    if evidence_type in MEASUREMENT_READY_EVIDENCE_TYPES
                    else "not_measurement_ready_in_current_pass"
                ),
            }
        )

    target_rows: list[dict[str, Any]] = []
    for target in TARGETS:
        review = target_review_by_target.get(target, {})
        candidate_rows = as_int(
            review.get("candidate_pair_rows"),
            default=int(target_candidate_counts.get(target, 0)),
        )
        row_level_pairs = as_int(review.get("row_level_pair_count"), default=0)
        distinct_files = as_int(review.get("distinct_files"), default=0)
        measurement_ready = as_int(
            review.get("measurement_ready_pair_count"),
            default=int(target_measurement_counts.get(target, 0)),
        )
        status, zero_type, next_action = classify_target_readiness(target, measurement_ready, candidate_rows)
        target_rows.append(
            {
                "target": target,
                "candidate_pair_rows": candidate_rows,
                "row_level_pair_count": row_level_pairs,
                "distinct_files": distinct_files,
                "measurement_ready_pair_count": measurement_ready,
                "measurement_readiness_status": status,
                "zero_type_or_denominator_status": zero_type,
                "next_required_action": next_action,
            }
        )

    unresolved_rows = [
        {
            "bucket": "unknown_text_code_opportunities",
            "candidate_pair_rows": int(target_candidate_counts.get("unknown", 0)),
            "measurement_ready_pair_rows": int(target_measurement_counts.get("unknown", 0)),
            "status": "preserved_pending_semantic_reconciliation",
            "next_required_action": "Split by target relevance, runtime availability, and evidence type before promotion.",
        },
        {
            "bucket": "external_fault_code_signal",
            "candidate_pair_rows": int(pdf_summary.get("fault_code_non_empty_rows", 0)),
            "measurement_ready_pair_rows": 0,
            "status": "controlled_source_required",
            "next_required_action": "Confirm the owning controlled vocabulary and SAP equivalence with SME or mapping owner.",
        },
    ]

    source_rows = [
        {
            "source_block": "inventoried_source_universe",
            "files_listed": int(
                source_inventory_summary.get("total_files")
                or source_inventory_summary.get("file_count", 0)
            ),
            "files_read_ok": "",
            "files_failed": "",
            "candidate_pairs_found": "",
            "measurement_ready_pairs": measurement_ready_count,
            "zero_type": "not_applicable_inventory_denominator",
        },
        {
            "source_block": "safe_content_pair_discovery",
            "files_listed": int(safe_pair_summary.get("input_source_files", 0)),
            "files_read_ok": int(safe_pair_summary.get("files_read_ok", 0)),
            "files_failed": int(safe_pair_summary.get("files_failed", 0)),
            "candidate_pairs_found": int(safe_pair_summary.get("pair_candidate_rows", 0)),
            "measurement_ready_pairs": measurement_ready_count,
            "zero_type": "candidate_pairs_found_not_measurement_ready",
        },
        {
            "source_block": "pdf_assets_of_concern_parser",
            "files_listed": int(pdf_summary.get("files_listed", 0)),
            "files_read_ok": int(pdf_summary.get("files_read_ok", 0)),
            "files_failed": int(pdf_summary.get("files_failed", 0)),
            "candidate_pairs_found": int(pdf_summary.get("fault_code_non_empty_rows", 0)),
            "measurement_ready_pairs": 0,
            "zero_type": "candidate_pairs_found_controlled_vocabulary_pending",
        },
    ]

    markdown_lines = [
        "# Asset ML Feasibility - Ground Truth and Measurement Readiness",
        "",
        "## Scope",
        "",
        "This section consolidates current ground-truth and measurement-readiness evidence for the seven target classifications. It does not include model training, accuracy estimates, or final feasibility conclusions.",
        "",
        "No raw operational client values are emitted.",
        "",
        "## Measurement Rule",
        "",
        "Only `real_observed_label` and `validated_mapping` evidence can enter a measurement denominator. Reference catalogs, illustrative examples, agent inference, and unknown opportunities remain useful for discovery but are not measurement-ready.",
        "",
        "## Current Measurement Readiness",
        "",
        f"- Measurement-ready pair rows: {measurement_ready_count}",
        f"- Classified pair rows: {int(pair_summary.get('classified_pair_rows', len(classified_rows)))}",
        f"- Unknown opportunity rows preserved: {int(target_candidate_counts.get('unknown', 0))}",
        f"- External structured fault-code signal rows: {int(pdf_summary.get('fault_code_non_empty_rows', 0))}",
        f"- Distinct external fault-code tokens: {int(pdf_summary.get('distinct_fault_code_count', 0))}",
        "",
        "## Evidence Type Summary",
        "",
        *markdown_table(
            evidence_rows,
            [
                "evidence_type",
                "can_enter_measurement_denominator",
                "current_pair_rows",
                "interpretation",
            ],
        ),
        "",
        "## Target Measurement Readiness",
        "",
        *markdown_table(
            target_rows,
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
        "## Source Denominator Summary",
        "",
        *markdown_table(
            source_rows,
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
        "## Unresolved Opportunity Buckets",
        "",
        *markdown_table(
            unresolved_rows,
            [
                "bucket",
                "candidate_pair_rows",
                "measurement_ready_pair_rows",
                "status",
                "next_required_action",
            ],
        ),
        "",
        "## Current Interpretation",
        "",
        "- The current measurable denominator remains zero because no pair has yet been confirmed as a real observed label or validated mapping.",
        "- Unknown text-code opportunities are preserved for semantic reconciliation; they are not discarded and not promoted to a target yet.",
        "- The external PDF-derived fault-code signal is structurally real, but it requires controlled-vocabulary ownership and SME/SAP mapping validation before it can support target measurement.",
        "- Zero measurement-ready evidence in this pass does not equal zero derivability.",
        "- Runtime availability still requires confirmation before any target can move from candidate evidence to measurable feasibility.",
        "",
        "## Required Follow-Up",
        "",
        "- Classify unknown text-code opportunities by target relevance and evidence type.",
        "- Confirm runtime availability for candidate source columns and parsed structured signals.",
        "- Obtain SME or mapping-owner validation for any candidate label/mapping before measurement.",
        "- Confirm the controlled source for external fault-code values and whether it maps to any SAP target.",
        "- Keep Symptom under explicit proof-of-life guardrail unless new validated evidence overturns the current status.",
        "",
        "## Non-Goals",
        "",
        "- No model training was performed.",
        "- No model accuracy estimate was produced.",
        "- No final feasibility conclusion is included.",
        "- No raw operational client values were emitted.",
    ]

    write_csv(
        reports_dir / "measurement_readiness_by_target_sanitized.csv",
        target_rows,
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
    )
    write_csv(
        reports_dir / "evidence_type_measurement_summary_sanitized.csv",
        evidence_rows,
        [
            "evidence_type",
            "can_enter_measurement_denominator",
            "current_pair_rows",
            "interpretation",
        ],
    )
    write_csv(
        reports_dir / "source_read_denominator_summary_sanitized.csv",
        source_rows,
        [
            "source_block",
            "files_listed",
            "files_read_ok",
            "files_failed",
            "candidate_pairs_found",
            "measurement_ready_pairs",
            "zero_type",
        ],
    )
    write_csv(
        reports_dir / "unresolved_opportunity_summary_sanitized.csv",
        unresolved_rows,
        [
            "bucket",
            "candidate_pair_rows",
            "measurement_ready_pair_rows",
            "status",
            "next_required_action",
        ],
    )

    markdown_path = reports_dir / "ground_truth_measurement_readiness_sanitized.md"
    markdown_path.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")

    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "artifact": "ground_truth_measurement_readiness",
        "status": "ready_for_draft_report_section_partial_for_final",
        "target_count": len(TARGETS),
        "measurement_ready_pair_rows": measurement_ready_count,
        "unknown_opportunity_rows": int(target_candidate_counts.get("unknown", 0)),
        "external_fault_code_signal_rows": int(pdf_summary.get("fault_code_non_empty_rows", 0)),
        "distinct_external_fault_code_count": int(pdf_summary.get("distinct_fault_code_count", 0)),
        "raw_operational_values_emitted": False,
        "outputs": {
            "markdown": str(markdown_path),
            "measurement_readiness_by_target_csv": str(reports_dir / "measurement_readiness_by_target_sanitized.csv"),
            "evidence_type_measurement_summary_csv": str(reports_dir / "evidence_type_measurement_summary_sanitized.csv"),
            "source_read_denominator_summary_csv": str(reports_dir / "source_read_denominator_summary_sanitized.csv"),
            "unresolved_opportunity_summary_csv": str(reports_dir / "unresolved_opportunity_summary_sanitized.csv"),
        },
    }

    summary_path = artifacts_dir / "ground_truth_measurement_readiness_summary_sanitized.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
