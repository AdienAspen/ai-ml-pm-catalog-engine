from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
STINT_ROOT = PROJECT_ROOT / "stint-1-evidence-ground-truth"
OUTPUTS_DIR = STINT_ROOT / "phase_0_consolidation" / "outputs"
DOCS_DIR = STINT_ROOT / "docs"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    denominator = read_json(PROJECT_ROOT / "artifacts" / "denominator_reconciliation_pass_summary_sanitized.json")
    target_matrix = read_json(PROJECT_ROOT / "artifacts" / "target_level_evidence_matrix_summary_sanitized.json")
    reference_freeze = read_json(
        PROJECT_ROOT / "stint-1.1-reference-layer" / "outputs" / "reference_layer_v1_freeze_summary.json"
    )

    checks = [
        {
            "check_id": "F0-001",
            "topic": "838_vs_910_candidate_pair_rows",
            "status": "resolved",
            "evidence": "838 source opportunity rows plus 72 target-expansion rows equals 910 target-expanded rows.",
            "downstream_rule": "Use 838 for source opportunities and 910 only for target-expanded classification rows.",
        },
        {
            "check_id": "F0-002",
            "topic": "147_vs_157_file_scope",
            "status": "resolved",
            "evidence": "157 structural files equals 147 source_data plus 10 mapping/reference files.",
            "downstream_rule": "Pair discovery scope is source_data only unless explicitly widened.",
        },
        {
            "check_id": "F0-003",
            "topic": "G08_parser_gap",
            "status": "closed",
            "evidence": "Latest denominator reconciliation reports current_parser_issue_on_tabular_files=0.",
            "downstream_rule": "Do not keep G08 as an open parser gap unless new parser evidence appears.",
        },
        {
            "check_id": "F0-004",
            "topic": "Cause_Activity_ActivityType_shared_expansion",
            "status": "open_for_phase_2",
            "evidence": "36 source opportunities were expanded across Cause, Activity, and Activity Type.",
            "downstream_rule": "Treat as shared evidence, not independent target evidence, until DELTA-0009 semantic split.",
        },
        {
            "check_id": "F0-005",
            "topic": "DELTA-0002_record_identifier",
            "status": "resolved_for_poc_policy",
            "evidence": "STINT_1 defines deterministic stint1_record_id proxy.",
            "downstream_rule": "No denominator unless grouped by stint1_record_id and target.",
        },
        {
            "check_id": "F0-006",
            "topic": "DELTA-0003_primary_text_field",
            "status": "resolved_for_poc_policy",
            "evidence": "STINT_1 defines target-specific source_text_field routing.",
            "downstream_rule": "No evidence promotion without source_text_field.",
        },
    ]

    record_id_policy = {
        "record_id_field": "stint1_record_id",
        "composition": [
            "source_family",
            "source_path_key",
            "source_record_ordinal",
            "source_text_field",
        ],
        "construction": "deterministic_non_reversible_hash_over_sanitized_record_lineage",
        "stability": "stable_if_source_package_ordering_and_source_record_ordinal_are_reproducible",
        "uniqueness_scope": "unique_by_design_within_source_family_source_path_key_source_record_ordinal_source_text_field",
        "collision_policy": "check_for_duplicate_stint1_record_id_within_each_phase_output_before_denominator_use",
        "production_claim": "PoC proxy only; does not claim production runtime record identity",
    }

    source_text_routing = [
        {
            "target": "Symptom",
            "primary_source_text_field": "classification_input.description_extended",
            "allowed_supporting_fields": "classification_input.description; classification_input.reason",
            "notes": "Hypothesis/silver-medium at most until downstream validation; run on semantically reactive subsets only.",
        },
        {
            "target": "Object Part",
            "primary_source_text_field": "classification_input.description_extended",
            "allowed_supporting_fields": "classification_input.work_performed; pdf_assets_of_concern.event",
            "notes": "Use component/system mentions; do not promote if only generic action text is present.",
        },
        {
            "target": "Damage",
            "primary_source_text_field": "classification_input.description_extended",
            "allowed_supporting_fields": "classification_input.description; pdf_assets_of_concern.event",
            "notes": "Route through failure-process semantics; do not treat generic failure mode as SAP Damage.",
        },
        {
            "target": "Cause",
            "primary_source_text_field": "classification_input.reason",
            "allowed_supporting_fields": "classification_input.description_extended",
            "notes": "Never infer Cause directly from Damage; shared multi-target evidence remains blocked by DELTA-0009.",
        },
        {
            "target": "Activity",
            "primary_source_text_field": "classification_input.work_performed",
            "allowed_supporting_fields": "classification_input.description_extended",
            "notes": "Action/measure evidence can support Activity after semantic split.",
        },
        {
            "target": "FLOC leaf",
            "primary_source_text_field": "header.functional_location",
            "allowed_supporting_fields": "classification_input.description_extended",
            "notes": "Structural target; text is supporting evidence only. Resolve against IH06-derived nodes.",
        },
        {
            "target": "Activity Type",
            "primary_source_text_field": "header.activity_type",
            "allowed_supporting_fields": "classification_input.work_performed",
            "notes": "Direct field where available; inferred maintenance type remains expert_inference.",
        },
    ]

    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "task": "F0_consolidation_and_preconditions",
        "source_artifacts": {
            "denominator_reconciliation": "artifacts/denominator_reconciliation_pass_summary_sanitized.json",
            "target_level_matrix": "artifacts/target_level_evidence_matrix_summary_sanitized.json",
            "reference_layer_freeze": "stint-1.1-reference-layer/outputs/reference_layer_v1_freeze_summary.json",
        },
        "denominator_reconciliation": {
            "source_opportunity_rows": denominator["safe_content_pair_rows"],
            "target_expanded_rows": denominator["target_expanded_classification_rows"],
            "target_expansion_delta": denominator["target_expansion_delta"],
            "multi_target_hint_rows": denominator["multi_target_hint_rows"],
            "reconciled": denominator["target_expansion_reconciled"],
        },
        "file_scope_reconciliation": {
            "structural_files_attempted": denominator["structural_files_attempted"],
            "safe_content_pair_files_attempted": denominator["safe_content_pair_files_attempted"],
            "structural_attempted_by_role": denominator["structural_attempted_by_role"],
        },
        "gaps_and_deltas": {
            "G04_runtime": "closed_for_poc_by_documented_proxy_assumption",
            "G08_parser": "closed_current_tabular_parser_issues_zero",
            "DELTA-0002": "resolved_for_poc_policy",
            "DELTA-0003": "resolved_for_poc_policy",
            "DELTA-0009": "open_for_phase_2_semantic_split",
        },
        "record_id_policy": record_id_policy,
        "source_text_routing": source_text_routing,
        "reference_layer_status": {
            "freeze_status": reference_freeze["freeze_status"],
            "complete_objects": reference_freeze["complete_objects"],
            "partial_or_provisional_objects": reference_freeze["partial_or_provisional_objects"],
        },
        "target_level_baseline": {
            "target_count": target_matrix["target_count"],
            "measurement_ready_targets": target_matrix["measurement_ready_targets"],
            "current_report_use": target_matrix["current_report_use"],
        },
        "raw_values_emitted": False,
        "outputs": {
            "checks_csv": "stint-1-evidence-ground-truth/phase_0_consolidation/outputs/f0_precondition_checks.csv",
            "summary_json": "stint-1-evidence-ground-truth/phase_0_consolidation/outputs/f0_consolidation_summary.json",
            "memo": "stint-1-evidence-ground-truth/phase_0_consolidation/outputs/f0_consolidation_memo.md",
            "source_text_routing_csv": "stint-1-evidence-ground-truth/phase_0_consolidation/outputs/f0_source_text_routing.csv",
        },
    }

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(
        OUTPUTS_DIR / "f0_precondition_checks.csv",
        checks,
        ["check_id", "topic", "status", "evidence", "downstream_rule"],
    )
    write_csv(
        OUTPUTS_DIR / "f0_source_text_routing.csv",
        source_text_routing,
        ["target", "primary_source_text_field", "allowed_supporting_fields", "notes"],
    )
    (OUTPUTS_DIR / "f0_consolidation_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    lines = [
        "# F0 - Consolidation and Preconditions",
        "",
        "## Purpose",
        "",
        "Phase 0 consolidates STINT_0 accounting and STINT_1.1 reference-layer decisions before evidence reconstruction begins.",
        "",
        "This pass does not train models, estimate accuracy, create production ground truth, or modify the frozen reference layer.",
        "",
        "## Reconciled Accounting",
        "",
        f"- Source opportunity rows: {denominator['safe_content_pair_rows']}",
        f"- Target-expanded classification rows: {denominator['target_expanded_classification_rows']}",
        f"- Multi-target hint rows: {denominator['multi_target_hint_rows']}",
        f"- Expansion delta: {denominator['target_expansion_delta']}",
        f"- Structural files attempted: {denominator['structural_files_attempted']}",
        f"- Source-data pair-discovery files: {denominator['safe_content_pair_files_attempted']}",
        f"- Current tabular parser issues: {denominator['current_parser_issue_on_tabular_files']}",
        "",
        "## Decisions",
        "",
        "- `G04` is closed for PoC by documented proxy assumption, not by production runtime proof.",
        "- `G08` is closed under current evidence: tabular parser issues are zero.",
        "- Cause / Activity / Activity Type shared expansion remains open for Phase 2 semantic split.",
        "- `DELTA-0002` is resolved for PoC by `stint1_record_id` deterministic proxy policy.",
        "- `DELTA-0003` is resolved for PoC by target-specific `source_text_field` routing.",
        "",
        "## DELTA-0002 Record Identifier Specification",
        "",
        f"- Record id field: `{record_id_policy['record_id_field']}`",
        "- Composition:",
        "  - `source_family`",
        "  - `source_path_key`",
        "  - `source_record_ordinal`",
        "  - `source_text_field`",
        f"- Construction: `{record_id_policy['construction']}`",
        f"- Stability: {record_id_policy['stability']}.",
        f"- Uniqueness scope: {record_id_policy['uniqueness_scope']}.",
        f"- Collision policy: {record_id_policy['collision_policy']}.",
        f"- Production claim: {record_id_policy['production_claim']}.",
        "",
        "## DELTA-0003 Source Text Routing",
        "",
        "| target | primary_source_text_field | allowed_supporting_fields | notes |",
        "|---|---|---|---|",
        *[
            f"| {row['target']} | `{row['primary_source_text_field']}` | `{row['allowed_supporting_fields']}` | {row['notes']} |"
            for row in source_text_routing
        ],
        "",
        "PDF-derived records keep `stratum: event_structural` and must not be mixed with planned/reactive strata.",
        "",
        "## Phase Gate",
        "",
        "F0 clears the preconditions for Phase 1 lexical rework. It does not create measurement-ready targets.",
        "",
        f"Measurement-ready targets remain: {target_matrix['measurement_ready_targets']}",
        "",
        "## Governance",
        "",
        "- No raw operational values are emitted.",
        "- No global denominator is introduced.",
        "- `expert_inference` remains outside measurement denominators unless later converted through a documented validation/proxy rule.",
    ]
    (OUTPUTS_DIR / "f0_consolidation_memo.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
