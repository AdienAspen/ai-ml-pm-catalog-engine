from __future__ import annotations

import csv
import json
from collections import defaultdict
from itertools import combinations
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve()
STINT2_ROOT = SCRIPT_PATH.parents[2]
REPO_ROOT = STINT2_ROOT.parent
STINT1_ROOT = REPO_ROOT / "stint-1-evidence-ground-truth"
F6_OUTPUTS = STINT1_ROOT / "phase_6_denominators" / "outputs"
OUT_DIR = STINT2_ROOT / "g0_independent_evaluation" / "outputs" / "annotation_samples"

F6_MATRIX = F6_OUTPUTS / "f6_evidence_denominator_matrix_sanitized.csv"

SOURCE_ARTIFACT_PATHS = {
    "b1_silver_labels_textual_residue_sanitized.csv": STINT1_ROOT
    / "phase_4_path_b_xlsx"
    / "outputs"
    / "b1_silver_labels"
    / "b1_silver_labels_textual_residue_sanitized.csv",
    "b25_grouped_reanchored_evidence_sanitized.csv": STINT1_ROOT
    / "phase_4_path_b_xlsx"
    / "outputs"
    / "b25_grouping_refinement"
    / "b25_grouped_reanchored_evidence_sanitized.csv",
    "f356_path_a_integrated_crosswalk_sanitized.csv": STINT1_ROOT
    / "phase_3_path_a_faultcodes"
    / "outputs"
    / "f356_path_a_integrated_crosswalk_sanitized.csv",
    "b1_deterministic_harvest_evidence_sanitized.csv": STINT1_ROOT
    / "phase_4_path_b_xlsx"
    / "outputs"
    / "b1_deterministic_harvest"
    / "b1_deterministic_harvest_evidence_sanitized.csv",
    "t51b25_symptom_final_path_verdict_sanitized.csv": STINT1_ROOT
    / "phase_5_symptom"
    / "outputs"
    / "f51_symptom_thread_resolution"
    / "t51b25_symptom_final_path_verdict_sanitized.csv",
}

UNIT_COLUMN_BY_ARTIFACT = {
    "b1_silver_labels_textual_residue_sanitized.csv": "physical_record_id",
    "b25_grouped_reanchored_evidence_sanitized.csv": "refined_event_key",
    "f356_path_a_integrated_crosswalk_sanitized.csv": "estimated_event_key",
    "b1_deterministic_harvest_evidence_sanitized.csv": "physical_record_id",
}

AGGREGATE_ONLY_ARTIFACTS = {
    "t51b25_symptom_final_path_verdict_sanitized.csv",
    "f51c_symptom_lexicon_survival_summary_sanitized.json",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def as_int(value: str) -> int:
    if value in ("", None):
        return 0
    return int(float(value))


def anchor_source(row: dict[str, str]) -> str:
    source_text_field = row.get("source_text_field", "")
    concept_id = row.get("concept_id", "")
    namespace = row.get("namespace", "")
    evidence_source = row.get("evidence_source", "")
    label_method = row.get("label_generation_method", "")

    if source_text_field in {"activityType", "assetId;siteId", "items[]"}:
        return "structural_field"
    if concept_id.startswith("CV-SAP"):
        return "sap_catalog"
    if concept_id.startswith("CV-EXT"):
        return "domain_vocabulary"
    if namespace == "fault_code" or evidence_source in {"code_context", "notes_context"}:
        return "domain_vocabulary"
    if "observed_structured_field" in label_method or "observed_internal_api_join" in label_method:
        return "structural_field"
    return "unknown"


def infer_id_namespace(path_bucket: str, unit_col: str) -> str:
    if path_bucket.startswith("B1_"):
        return "B1_PHYSICAL_RECORD"
    if path_bucket.startswith("B2_"):
        return "B2_REFINED_EVENT"
    if path_bucket.startswith("PATH_A"):
        return "PATH_A_ESTIMATED_EVENT"
    if path_bucket == "RELATIONAL_REASON":
        return "B1_PHYSICAL_RECORD"
    return unit_col or "AGGREGATE"


def load_row_level_units(f6_row: dict[str, str]) -> tuple[set[str], set[str], dict[str, set[str]]]:
    artifact = f6_row["source_artifact"]
    path = SOURCE_ARTIFACT_PATHS[artifact]
    unit_col = UNIT_COLUMN_BY_ARTIFACT[artifact]
    target = f6_row["target"]
    candidate_units: set[str] = set()
    admitted_units: set[str] = set()
    anchor_units: dict[str, set[str]] = defaultdict(set)

    for row in read_csv(path):
        if row.get("target") != target:
            continue
        unit = row.get(unit_col, "")
        if not unit:
            continue
        candidate_units.add(unit)
        anchor_units[anchor_source(row)].add(unit)
        if row.get("can_support_proxy_denominator") == "True" or row.get("can_support_contractual_denominator") == "True":
            admitted_units.add(unit)

    if not admitted_units and as_int(f6_row.get("admitted_denominator_units", "0")) > 0:
        admitted_units = set(candidate_units)

    return candidate_units, admitted_units, anchor_units


def build_inventory() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    f6_rows = read_csv(F6_MATRIX)

    inventory_rows: list[dict[str, object]] = []
    anchor_rows: list[dict[str, object]] = []
    issue_rows: list[dict[str, object]] = []
    overlap_inputs: dict[str, dict[str, dict[str, object]]] = defaultdict(dict)
    aggregate_only = 0
    row_level = 0

    for row in f6_rows:
        target = row["target"]
        denominator_type = row["denominator_type"]
        path_bucket = row["path_bucket"]
        artifact = row["source_artifact"]
        f6_candidate = as_int(row.get("candidate_units", "0"))
        f6_admitted = as_int(row.get("admitted_denominator_units", "0"))

        if denominator_type not in {"proxy_poc", "contractual"}:
            continue
        if f6_candidate == 0 and f6_admitted == 0:
            continue

        aggregate = artifact in AGGREGATE_ONLY_ARTIFACTS or artifact not in UNIT_COLUMN_BY_ARTIFACT
        unit_col = UNIT_COLUMN_BY_ARTIFACT.get(artifact, "")
        id_namespace = infer_id_namespace(path_bucket, unit_col)

        candidate_units: set[str] = set()
        admitted_units: set[str] = set()
        anchor_units: dict[str, set[str]] = defaultdict(set)

        candidate_pool_units = f6_candidate
        protocol_v1_sampling_ceiling = f6_admitted
        if f6_admitted > 0:
            sampling_basis = "admitted_denominator_units"
            protocol_v1_inclusion = "include_in_protocol_v1"
        elif f6_candidate > 0:
            sampling_basis = "excluded_candidate_pool_pending_admission"
            protocol_v1_inclusion = "exclude_from_protocol_v1_pending_g1_or_row_level_recovery"
        else:
            sampling_basis = "no_units"
            protocol_v1_inclusion = "exclude_no_units"

        if aggregate:
            aggregate_only += 1
            row_level_status = "aggregate_only_from_f6"
            if f6_admitted > 0:
                protocol_v1_inclusion = "blocked_until_row_level_units_recovered"
                sampling_basis = "admitted_count_exists_but_row_level_units_missing"
            issue_rows.append(
                {
                    "target": target,
                    "path_bucket": path_bucket,
                    "issue_type": "aggregate_only_no_row_level_units",
                    "candidate_units": f6_candidate,
                    "admitted_denominator_units": f6_admitted,
                    "protocol_impact": "cannot_sample_until_row_level_units_are_recovered",
                    "source_artifact": artifact,
                }
            )
        else:
            row_level += 1
            candidate_units, admitted_units, anchor_units = load_row_level_units(row)
            row_level_status = "row_level_units_available"
            candidate_pool_units = len(candidate_units)
            protocol_v1_sampling_ceiling = len(admitted_units) if f6_admitted > 0 else 0
            overlap_inputs[target][path_bucket] = {
                "units": admitted_units,
                "id_namespace": id_namespace,
            }

        inventory_rows.append(
            {
                "target": target,
                "path_bucket": path_bucket,
                "denominator_type": denominator_type,
                "source_artifact": artifact,
                "row_level_status": row_level_status,
                "unit_column": unit_col,
                "id_namespace": id_namespace,
                "f6_candidate_units": f6_candidate,
                "f6_admitted_denominator_units": f6_admitted,
                "row_level_candidate_units": len(candidate_units) if not aggregate else "",
                "row_level_admitted_units": len(admitted_units) if not aggregate else "",
                "candidate_pool_units": candidate_pool_units,
                "protocol_v1_sampling_ceiling": protocol_v1_sampling_ceiling,
                "protocol_v1_sampling_basis": sampling_basis,
                "protocol_v1_inclusion": protocol_v1_inclusion,
                "anchor_source_assessable": not aggregate,
                "overlap_assessable_exact_key": not aggregate,
                "evaluation_independence": row.get("evaluation_independence", ""),
                "label_generation_method": row.get("label_generation_method", ""),
                "status": row.get("status", ""),
            }
        )

        if aggregate:
            anchor_rows.append(
                {
                    "target": target,
                    "path_bucket": path_bucket,
                    "denominator_type": denominator_type,
                    "anchor_source": "not_assessable_aggregate_only",
                    "unique_units": "",
                    "share_of_path_units_pct": "",
                    "share_note": "aggregate_only_from_f6",
                    "source_artifact": artifact,
                }
            )
        else:
            denominator = len(candidate_units) or 1
            for source, units in sorted(anchor_units.items()):
                anchor_rows.append(
                    {
                        "target": target,
                        "path_bucket": path_bucket,
                        "denominator_type": denominator_type,
                        "anchor_source": source,
                        "unique_units": len(units),
                        "share_of_path_units_pct": round((len(units) / denominator) * 100, 2),
                        "share_note": "non_exclusive_unit_membership; shares may sum above 100",
                        "source_artifact": artifact,
                    }
                )

    overlap_rows: list[dict[str, object]] = []
    for target, by_path in sorted(overlap_inputs.items()):
        for left, right in combinations(sorted(by_path), 2):
            left_units = by_path[left]["units"]
            right_units = by_path[right]["units"]
            left_namespace = by_path[left]["id_namespace"]
            right_namespace = by_path[right]["id_namespace"]
            comparable = left_namespace == right_namespace
            overlap = len(left_units & right_units) if comparable else ""
            overlap_rows.append(
                {
                    "target": target,
                    "left_path_bucket": left,
                    "right_path_bucket": right,
                    "left_id_namespace": left_namespace,
                    "right_id_namespace": right_namespace,
                    "exact_key_overlap_assessable": comparable,
                    "left_units": len(left_units),
                    "right_units": len(right_units),
                    "overlap_units": overlap,
                    "note": ""
                    if comparable
                    else "Exact overlap is not assessable because STINT 1 uses different event/record namespaces across these paths.",
                }
            )

    summary = {
        "task": "G0.0_STINT1_inventory_for_annotation_protocol",
        "source_commit": "stint1-denominator-closure-v0.7",
        "f6_matrix": str(F6_MATRIX.relative_to(REPO_ROOT)),
        "target_path_rows": len(inventory_rows),
        "row_level_rows": row_level,
        "aggregate_only_rows": aggregate_only,
            "critical_findings": {
            "cause_path_a_protocol_ceiling": next(
                (
                    r["protocol_v1_sampling_ceiling"]
                    for r in inventory_rows
                    if r["target"] == "Cause" and r["path_bucket"] == "PATH_A_PDF_EVENTS"
                ),
                None,
            ),
            "object_part_admitted_proxy_units_by_path": {
                r["path_bucket"]: r["protocol_v1_sampling_ceiling"]
                for r in inventory_rows
                if r["target"] == "Object Part" and r["f6_admitted_denominator_units"]
            },
            "object_part_b1_candidate_units_requires_crosswalk": next(
                (
                    r["candidate_pool_units"]
                    for r in inventory_rows
                    if r["target"] == "Object Part" and r["path_bucket"] == "B1_RELATIONAL_STRUCTURED"
                ),
                None,
            ),
            "symptom_aggregate_only_admitted_units": sum(
                int(r["f6_admitted_denominator_units"])
                for r in inventory_rows
                if r["target"] == "Symptom" and r["row_level_status"] == "aggregate_only_from_f6"
            ),
        },
        "raw_operational_values_emitted": False,
    }

    write_csv(
        OUT_DIR / "g00_target_path_inventory_sanitized.csv",
        inventory_rows,
        [
            "target",
            "path_bucket",
            "denominator_type",
            "source_artifact",
            "row_level_status",
            "unit_column",
            "id_namespace",
            "f6_candidate_units",
            "f6_admitted_denominator_units",
            "row_level_candidate_units",
            "row_level_admitted_units",
            "candidate_pool_units",
            "protocol_v1_sampling_ceiling",
            "protocol_v1_sampling_basis",
            "protocol_v1_inclusion",
            "anchor_source_assessable",
            "overlap_assessable_exact_key",
            "evaluation_independence",
            "label_generation_method",
            "status",
        ],
    )
    write_csv(
        OUT_DIR / "g00_anchor_source_distribution_sanitized.csv",
        anchor_rows,
        [
            "target",
            "path_bucket",
            "denominator_type",
            "anchor_source",
            "unique_units",
            "share_of_path_units_pct",
            "share_note",
            "source_artifact",
        ],
    )
    write_csv(
        OUT_DIR / "g00_cross_path_overlap_sanitized.csv",
        overlap_rows,
        [
            "target",
            "left_path_bucket",
            "right_path_bucket",
            "left_id_namespace",
            "right_id_namespace",
            "exact_key_overlap_assessable",
            "left_units",
            "right_units",
            "overlap_units",
            "note",
        ],
    )
    write_csv(
        OUT_DIR / "g00_protocol_blockers_sanitized.csv",
        issue_rows,
        [
            "target",
            "path_bucket",
            "issue_type",
            "candidate_units",
            "admitted_denominator_units",
            "protocol_impact",
            "source_artifact",
        ],
    )
    with (OUT_DIR / "g00_inventory_summary_sanitized.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, sort_keys=True)

    memo = [
        "# G0.0 STINT 1 Inventory for Annotation Protocol",
        "",
        "## Purpose",
        "",
        "This inventory supports the STINT 2 blind annotation protocol. It counts available units by target and path before sample sizes are declared.",
        "",
        "## Findings",
        "",
        f"- Target-path rows inventoried: `{len(inventory_rows)}`.",
        f"- Row-level rows with unit identifiers: `{row_level}`.",
        f"- Aggregate-only rows from F6 summaries: `{aggregate_only}`.",
        f"- Cause on `PATH_A_PDF_EVENTS` has a protocol ceiling of `{summary['critical_findings']['cause_path_a_protocol_ceiling']}` units.",
        "- Protocol v1 samples admitted units only.",
        "- Rows with zero admitted units but positive candidates are G1 candidate pools, not protocol v1 evaluation material.",
        f"- Symptom has `{summary['critical_findings']['symptom_aggregate_only_admitted_units']}` admitted units in aggregate-only F6 rows; row-level units must be recovered before Symptom can enter protocol v1.",
        "- Cross-path exact overlap is generally not assessable where STINT 1 uses different record/event namespaces across paths.",
        "- Cross-path deduplication is not required for protocol v1 because F6 forbids aggregation across paths.",
        "- `anchor_source` can be derived for row-level artifacts; membership is non-exclusive and shares may sum above 100%.",
        "- Aggregate-only Symptom paths require protocol-level handling before row-level sampling.",
        "",
        "## Outputs",
        "",
        "- `g00_target_path_inventory_sanitized.csv`",
        "- `g00_anchor_source_distribution_sanitized.csv`",
        "- `g00_cross_path_overlap_sanitized.csv`",
        "- `g00_protocol_blockers_sanitized.csv`",
        "- `g00_inventory_summary_sanitized.json`",
        "",
        "No raw operational values are emitted.",
    ]
    (OUT_DIR / "g00_inventory_memo.md").write_text("\n".join(memo) + "\n", encoding="utf-8")


if __name__ == "__main__":
    build_inventory()
