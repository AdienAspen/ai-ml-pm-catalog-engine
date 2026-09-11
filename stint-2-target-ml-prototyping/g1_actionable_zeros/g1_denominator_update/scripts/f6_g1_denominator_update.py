from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path("/home/adien-i7-remote/workspace/fsa_bridge_ml_feasibility")
STINT2_ROOT = PROJECT_ROOT / "stint-2-target-ml-prototyping"
F6_OUT = PROJECT_ROOT / "stint-1-evidence-ground-truth" / "phase_6_denominators" / "outputs"
G1_OUT = STINT2_ROOT / "g1_actionable_zeros" / "g1_denominator_update" / "outputs"

F6_MATRIX = F6_OUT / "f6_evidence_denominator_matrix_sanitized.csv"
F6_CLOSURE = F6_OUT / "f6_committee_closure_denominator_table_sanitized.csv"
G11_SUMMARY = (
    STINT2_ROOT
    / "g1_actionable_zeros"
    / "g11_object_part_crosswalk"
    / "outputs"
    / "g11_crosswalk_summary_sanitized.json"
)
G12_SUMMARY = (
    STINT2_ROOT
    / "g1_actionable_zeros"
    / "g12_floc_alignment"
    / "outputs"
    / "g12_floc_alignment_summary_sanitized.json"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return list(reader), list(reader.fieldnames or [])


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def global_zero_row_matrix(target: str, denominator_type: str) -> dict[str, object]:
    return {
        "target": target,
        "denominator_type": denominator_type,
        "path_bucket": "DECLARED_TARGET_TOTAL_NO_GLOBAL_AGGREGATION",
        "source_artifact": "F6-G1 denominator update",
        "count_unit": "not_aggregated_across_paths",
        "stratum": "not_applicable",
        "evidence_type": "none",
        "tier": "none",
        "status": "declared_zero_or_no_global_denominator",
        "candidate_units": 0,
        "admitted_denominator_units": 0,
        "inclusion_decision": "declared_no_global_denominator",
        "blocker_or_condition": "Per-path denominators are authoritative; global aggregation is methodologically invalid.",
        "label_generation_method": "none",
        "evaluation_independence": "not_applicable",
        "raw_operational_values_emitted": "False",
    }


def global_zero_row_closure(target: str, denominator_type: str) -> dict[str, object]:
    return {
        "target": target,
        "path": "DECLARED_TARGET_TOTAL_NO_GLOBAL_AGGREGATION",
        "denominator_type": denominator_type,
        "evidence_type": "none",
        "tier": "none",
        "count_unit": "not_aggregated_across_paths",
        "stratum": "not_applicable",
        "admitted_denominator_units": 0,
        "status": "explicit_zero",
        "notes": "Per-path denominators are authoritative; global aggregation is methodologically invalid.",
    }


def main() -> None:
    G1_OUT.mkdir(parents=True, exist_ok=True)
    g11 = json.loads(G11_SUMMARY.read_text(encoding="utf-8"))
    g12 = json.loads(G12_SUMMARY.read_text(encoding="utf-8"))

    object_part_b1_strong = int(g11["orders_with_strong_or_medium_candidate"])
    floc_turbine_units = int(g12["matched_asset_node_orders"])
    assert object_part_b1_strong == 3027, object_part_b1_strong
    assert floc_turbine_units == 10699, floc_turbine_units

    matrix_rows, matrix_fields = read_csv(F6_MATRIX)
    updated_matrix = []
    changes = []

    for row in matrix_rows:
        row = dict(row)
        if (
            row["target"] == "Object Part"
            and row["denominator_type"] == "proxy_poc"
            and row["path_bucket"] == "B1_RELATIONAL_STRUCTURED"
        ):
            changes.append(
                {
                    "target": "Object Part",
                    "path": "B1_RELATIONAL_STRUCTURED",
                    "denominator_type": "proxy_poc",
                    "old_admitted_units": row["admitted_denominator_units"],
                    "new_admitted_units": object_part_b1_strong,
                    "change_basis": "G1.1 strong material-to-Catalog-B crosswalk candidates only",
                }
            )
            row.update(
                {
                    "candidate_units": object_part_b1_strong,
                    "admitted_denominator_units": object_part_b1_strong,
                    "evidence_type": "expert_inference",
                    "tier": "silver-high:strong_only",
                    "status": "g1_1_crosswalk_strong_candidate_admitted_proxy",
                    "inclusion_decision": "admitted_proxy_only_strong_tier",
                    "blocker_or_condition": "Only strong G1.1 consumption material to Catalog B candidates admitted; medium/weak/no_candidate excluded from this denominator tier.",
                    "label_generation_method": "g1_1_material_to_catalog_b_crosswalk_strong",
                    "evaluation_independence": "derived_from_rules",
                    "raw_operational_values_emitted": "False",
                }
            )
        updated_matrix.append(row)

    for denominator_type in ["contractual", "proxy_poc"]:
        updated_matrix.append(global_zero_row_matrix("FLOC turbine", denominator_type))
    updated_matrix.append(
        {
            "target": "FLOC turbine",
            "denominator_type": "proxy_poc",
            "path_bucket": "B1_RELATIONAL_STRUCTURED",
            "source_artifact": "g12_floc_alignment_order_level_sanitized.csv",
            "count_unit": "physical_record_id_x_target",
            "stratum": "site_plus_turbine_asset_node",
            "evidence_type": "deterministic_structural_alignment",
            "tier": "silver-high:turbine_granularity",
            "status": "g1_2_floc_turbine_admitted_proxy",
            "candidate_units": floc_turbine_units,
            "admitted_denominator_units": floc_turbine_units,
            "inclusion_decision": "admitted_proxy_only_declared_turbine_granularity",
            "blocker_or_condition": "FLOC turbine admitted; FLOC leaf remains held because component/maintainable-item selector is not reachable from service-order asset reference alone.",
            "label_generation_method": "g1_2_site_turbine_token_to_ih06_asset_node_alignment",
            "evaluation_independence": "derived_from_rules",
            "raw_operational_values_emitted": "False",
        }
    )
    changes.append(
        {
            "target": "FLOC turbine",
            "path": "B1_RELATIONAL_STRUCTURED",
            "denominator_type": "proxy_poc",
            "old_admitted_units": 0,
            "new_admitted_units": floc_turbine_units,
            "change_basis": "G1.2 deterministic site+turbine-token alignment to IH06 asset node",
        }
    )

    write_csv(G1_OUT / "f6_g1_evidence_denominator_matrix_sanitized.csv", updated_matrix, matrix_fields)

    closure_rows, closure_fields = read_csv(F6_CLOSURE)
    updated_closure = []
    for row in closure_rows:
        row = dict(row)
        if (
            row["target"] == "Object Part"
            and row["denominator_type"] == "proxy_poc"
            and row["path"] == "B1_RELATIONAL_STRUCTURED"
        ):
            row.update(
                {
                    "evidence_type": "expert_inference",
                    "tier": "silver-high:strong_only",
                    "admitted_denominator_units": object_part_b1_strong,
                    "status": "admitted",
                    "notes": "G1.1 update: admitted strong material-to-Catalog-B crosswalk candidates only; medium/weak/no_candidate remain excluded tiers.",
                }
            )
        updated_closure.append(row)
    for denominator_type in ["contractual", "proxy_poc"]:
        updated_closure.append(global_zero_row_closure("FLOC turbine", denominator_type))
    updated_closure.append(
        {
            "target": "FLOC turbine",
            "path": "B1_RELATIONAL_STRUCTURED",
            "denominator_type": "proxy_poc",
            "evidence_type": "deterministic_structural_alignment",
            "tier": "silver-high:turbine_granularity",
            "count_unit": "physical_record_id",
            "stratum": "site_plus_turbine_asset_node",
            "admitted_denominator_units": floc_turbine_units,
            "status": "admitted",
            "notes": "G1.2 update: admitted at turbine granularity only; FLOC leaf remains held.",
        }
    )
    write_csv(G1_OUT / "f6_g1_committee_closure_denominator_table_sanitized.csv", updated_closure, closure_fields)

    write_csv(
        G1_OUT / "f6_g1_denominator_delta_log_sanitized.csv",
        changes,
        ["target", "path", "denominator_type", "old_admitted_units", "new_admitted_units", "change_basis"],
    )

    summary = {
        "task": "F6_G1_denominator_update",
        "created_at_utc": utc_now(),
        "source_f6_matrix": str(F6_MATRIX.relative_to(PROJECT_ROOT)),
        "source_f6_closure": str(F6_CLOSURE.relative_to(PROJECT_ROOT)),
        "stint1_f6_mutated": False,
        "updates": {
            "Object Part|B1_RELATIONAL_STRUCTURED|proxy_poc": {
                "old_admitted_units": 0,
                "new_admitted_units": object_part_b1_strong,
                "tier": "strong_only",
                "excluded_tiers": "medium;weak;no_candidate",
            },
            "FLOC turbine|B1_RELATIONAL_STRUCTURED|proxy_poc": {
                "old_admitted_units": 0,
                "new_admitted_units": floc_turbine_units,
                "granularity": "site_plus_turbine_asset_node",
            },
            "FLOC leaf": {
                "admitted_units": 0,
                "status": "held",
                "reason": "component not reachable from service-order asset reference alone",
            },
        },
        "g2_must_use": "f6_g1_evidence_denominator_matrix_sanitized.csv",
        "raw_operational_values_emitted": False,
    }
    write_json(G1_OUT / "f6_g1_denominator_update_summary_sanitized.json", summary)

    memo = """# F6-G1 Denominator Update Memo

This artefact updates the effective STINT_2 denominator matrix after G1. It does not mutate the frozen STINT_1 F6 closure.

## Changes

| Target | Path | Previous | Updated | Basis |
|---|---|---:|---:|---|
| Object Part | B1_RELATIONAL_STRUCTURED | 0 | 3,027 | G1.1 strong material-to-Catalog-B crosswalk candidates only |
| FLOC turbine | B1_RELATIONAL_STRUCTURED | 0 | 10,699 | G1.2 site + turbine-token alignment to IH06 asset node |

## Held

FLOC leaf remains 0 admitted. The source reaches turbine asset nodes, not component or maintainable-item leaf nodes. Component descent via consumption is registered as G2-or-later debt and is not an open G1 blocker.

## Tier Rule

For Object Part B1, only `strong` G1.1 candidates enter the denominator update. Medium, weak, and no-candidate residuals remain declared but excluded from this denominator tier.

## G2 Rule

G2 must consume `f6_g1_evidence_denominator_matrix_sanitized.csv`, not the STINT_1 F6 matrix, or it will train/evaluate against stale denominators.
"""
    (G1_OUT / "f6_g1_denominator_update_memo.md").write_text(memo, encoding="utf-8")


if __name__ == "__main__":
    main()
