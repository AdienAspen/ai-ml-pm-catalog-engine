from __future__ import annotations

import csv
import json
from pathlib import Path


STINT2_ROOT = Path("/home/adien-i7-remote/workspace/fsa_bridge_ml_feasibility/stint-2-target-ml-prototyping")
G12_OUT = STINT2_ROOT / "g1_actionable_zeros" / "g12_floc_alignment" / "outputs"
G11_OUT = STINT2_ROOT / "g1_actionable_zeros" / "g11_object_part_crosswalk" / "outputs"


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    g12_summary_path = G12_OUT / "g12_floc_alignment_summary_sanitized.json"
    g11_summary_path = G11_OUT / "g11_crosswalk_summary_sanitized.json"
    g12_summary = json.loads(g12_summary_path.read_text(encoding="utf-8"))
    g11_summary = json.loads(g11_summary_path.read_text(encoding="utf-8"))

    matched = int(g12_summary["matched_asset_node_orders"])
    match_rate = float(g12_summary["asset_node_match_rate"])
    consumption_reachable = int(g11_summary["orders_with_strong_or_medium_candidate"])
    universe = int(g12_summary["service_order_records"])
    consumption_reachable_rate = round(consumption_reachable / universe * 100, 6)

    target_rows = [
        {
            "target": "FLOC leaf",
            "admission_status": "HOLD",
            "admitted_units": 0,
            "match_rate": "",
            "granularity": "component_or_maintainable_item_leaf",
            "reason": "component not reachable from service-order asset reference alone",
            "provenance": "not_admitted",
            "downstream_status": "component descent registered as G2_or_later debt",
        },
        {
            "target": "FLOC turbine",
            "admission_status": "ADMIT",
            "admitted_units": matched,
            "match_rate": match_rate,
            "granularity": "site_plus_turbine_asset_node",
            "reason": "deterministic site and turbine-token alignment to IH06 asset node",
            "provenance": "derived_from_rules",
            "downstream_status": "usable as declared turbine-granularity structural target",
        },
    ]
    write_csv(
        G12_OUT / "g12_floc_target_reachability_register_sanitized.csv",
        target_rows,
        [
            "target",
            "admission_status",
            "admitted_units",
            "match_rate",
            "granularity",
            "reason",
            "provenance",
            "downstream_status",
        ],
    )

    debt_rows = [
        {
            "debt_id": "G12-DEBT-0001",
            "scope": "FLOC leaf component descent",
            "status": "registered_debt_not_open_g1_blocker",
            "dependency": "G1.1 consumption material to Catalog B crosswalk",
            "reachable_orders_via_consumption_strong_or_medium": consumption_reachable,
            "service_order_universe": universe,
            "reachable_share_of_universe": consumption_reachable_rate,
            "handoff_phase": "G2_or_later",
            "reason": "component is inferable only where consumption item signal exists; this is downstream feature/label construction, not G1 alignment",
        }
    ]
    write_csv(
        G12_OUT / "g12_component_descent_debt_register_sanitized.csv",
        debt_rows,
        [
            "debt_id",
            "scope",
            "status",
            "dependency",
            "reachable_orders_via_consumption_strong_or_medium",
            "service_order_universe",
            "reachable_share_of_universe",
            "handoff_phase",
            "reason",
        ],
    )

    g12_summary.update(
        {
            "registered_targets": {
                "FLOC leaf": {
                    "admission_status": "HOLD",
                    "admitted_units": 0,
                    "reason": "component not reachable from service-order asset reference alone",
                },
                "FLOC turbine": {
                    "admission_status": "ADMIT",
                    "admitted_units": matched,
                    "match_rate": match_rate,
                    "granularity": "site_plus_turbine_asset_node",
                },
            },
            "component_descent_debt": {
                "status": "registered_debt_not_open_g1_blocker",
                "dependency": "G1.1 consumption material to Catalog B crosswalk",
                "reachable_orders": consumption_reachable,
                "reachable_share_of_universe": consumption_reachable_rate,
                "handoff_phase": "G2_or_later",
            },
        }
    )
    g12_summary_path.write_text(json.dumps(g12_summary, indent=2, sort_keys=True), encoding="utf-8")

    memo_path = G12_OUT / "g12_floc_alignment_memo.md"
    memo = memo_path.read_text(encoding="utf-8")
    marker = "\n## Target Registration\n"
    registration = f"""
## Target Registration

G1.2 closes with two distinct target names:

| Target | Registration | Units | Granularity |
|---|---:|---:|---|
| FLOC leaf | HOLD | 0 | component/maintainable-item leaf not reachable from source alone |
| FLOC turbine | ADMIT | {matched:,} | site + turbine asset node, match rate {match_rate}% |

The descent from turbine to component is registered as debt, not as an open G1 blocker. The only currently available component selector is the G1.1 consumption path, which reaches {consumption_reachable:,} of {universe:,} orders ({consumption_reachable_rate}%) through strong/medium material-to-Catalog-B candidates. That work belongs to G2 or later.
"""
    if marker in memo:
        memo = memo.split(marker)[0].rstrip() + registration
    else:
        memo = memo.rstrip() + "\n" + registration
    memo_path.write_text(memo, encoding="utf-8")


if __name__ == "__main__":
    main()
