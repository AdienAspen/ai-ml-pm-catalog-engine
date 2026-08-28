from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median

from openpyxl import load_workbook


PROJECT_ROOT = Path(__file__).resolve().parents[2]
STINT_ROOT = PROJECT_ROOT / "stint-1.1-reference-layer"
OUTPUTS_DIR = STINT_ROOT / "outputs"
DOCS_DIR = STINT_ROOT / "docs"
SOURCE_DESIGNATIONS_DIR = STINT_ROOT / "reference_layer" / "source_designations"

IH06_GLOB = "data/interim/extracted_source/**/IH06*PRD*.XLSX"
IEC_NODES_PATH = SOURCE_DESIGNATIONS_DIR / "iec_logical_nodes_21_reference_v1.csv"


def safe_str(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def norm_header(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "_", safe_str(value).lower()).strip("_")


def floc_depth(floc: str) -> int:
    return len([part for part in floc.split("-") if part])


def iso14224_proxy(depth: int) -> str:
    if depth <= 1:
        return "site_or_plant"
    if depth == 2:
        return "unit_or_section"
    if depth == 3:
        return "system"
    if depth == 4:
        return "subsystem"
    if depth == 5:
        return "assembly_or_equipment_unit"
    return "maintainable_item_or_part"


def observed_node_tokens(floc: str) -> list[str]:
    parts = [part for part in floc.split("-") if part]
    tokens: list[str] = []
    for part in parts[2:]:
        match = re.match(r"([A-Z]{2,4})", part.upper())
        if match:
            tokens.append(match.group(1))
    return tokens


def find_ih06() -> Path:
    matches = sorted(PROJECT_ROOT.glob(IH06_GLOB))
    if not matches:
        raise FileNotFoundError(f"No IH06 workbook found with glob: {IH06_GLOB}")
    return matches[0]


def site_key_map(raw_sites: list[str]) -> dict[str, str]:
    unique = sorted({site or "UNKNOWN_SITE" for site in raw_sites})
    return {site: f"SITE-{idx:03d}" for idx, site in enumerate(unique, start=1)}


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def build_iec_contrast(
    iec_nodes: list[dict[str, str]],
    node_acc: Counter[tuple[str, str]],
) -> list[dict[str, object]]:
    node_totals: Counter[str] = Counter()
    node_sites: dict[str, set[str]] = defaultdict(set)
    for (site_key, node), count in node_acc.items():
        node_totals[node] += count
        node_sites[node].add(site_key)

    contrast_rows: list[dict[str, object]] = []
    for row in iec_nodes:
        node_id = row["node_id"]
        scope = row["ih06_contrast_scope"]
        observed_count = int(node_totals.get(node_id, 0))
        if scope == "physical_subsystem":
            status = (
                "observed_in_ih06_token_inventory"
                if observed_count
                else "not_observed_in_ih06_token_inventory_crosswalk_required"
            )
        elif scope == "physical_root_context":
            status = (
                "root_context_observed_in_ih06_token_inventory"
                if observed_count
                else "root_context_not_observed_not_missing_subsystem_claim"
            )
        else:
            status = "not_applicable_to_ih06_physical_subsystem_contrast"

        contrast_rows.append(
            {
                "concept_id": row["concept_id"],
                "node_id": node_id,
                "published_description": row["published_description"],
                "clause_table": row["clause_table"],
                "iec_node_category": row["iec_node_category"],
                "ih06_contrast_scope": scope,
                "observed_in_ih06_token_inventory": bool(observed_count),
                "total_observed_rows": observed_count,
                "observed_site_count": len(node_sites.get(node_id, set())),
                "contrast_status": status,
                "evidence_type": row["evidence_type"],
                "tier": row["tier"],
                "source_caveat": row["source_caveat"],
                "raw_values_emitted": False,
            }
        )
    return contrast_rows


def main() -> dict[str, object]:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    ih06_path = find_ih06()
    workbook = load_workbook(ih06_path, read_only=True, data_only=True)
    sheet = workbook[workbook.sheetnames[0]]

    rows_iter = sheet.iter_rows(values_only=True)
    headers = [norm_header(value) for value in next(rows_iter)]
    index = {name: idx for idx, name in enumerate(headers)}

    required = {
        "functional_location",
        "description_of_functional_location",
        "maintenance_plant",
        "planning_plant",
        "catalog_profile",
        "superior_functional_location",
    }
    missing = sorted(required - set(index))
    if missing:
        raise RuntimeError(f"IH06 required columns missing: {missing}")

    raw_records: list[dict[str, object]] = []
    raw_sites: list[str] = []
    superior_locations: set[str] = set()

    for row in rows_iter:
        floc = safe_str(row[index["functional_location"]])
        if not floc:
            continue
        superior = safe_str(row[index["superior_functional_location"]])
        site_raw = safe_str(row[index["maintenance_plant"]]) or safe_str(row[index["planning_plant"]]) or floc.split("-")[0]
        raw_sites.append(site_raw)
        if superior:
            superior_locations.add(superior)
        raw_records.append(
            {
                "floc": floc,
                "site_raw": site_raw,
                "depth": floc_depth(floc),
                "catalog_profile_present": bool(safe_str(row[index["catalog_profile"]])),
                "description_present": bool(safe_str(row[index["description_of_functional_location"]])),
                "nodes": observed_node_tokens(floc),
            }
        )

    site_map = site_key_map(raw_sites)

    by_site_acc: dict[str, dict[str, object]] = defaultdict(
        lambda: {
            "records": 0,
            "leaf_records": 0,
            "depths": [],
            "nodes": Counter(),
            "catalog_profile_present": 0,
            "description_present": 0,
        }
    )
    node_acc: Counter[tuple[str, str]] = Counter()
    iso_acc: Counter[tuple[str, str]] = Counter()

    for record in raw_records:
        site_key = site_map[str(record["site_raw"])]
        depth = int(record["depth"])
        floc = str(record["floc"])
        acc = by_site_acc[site_key]
        acc["records"] = int(acc["records"]) + 1
        acc["leaf_records"] = int(acc["leaf_records"]) + (0 if floc in superior_locations else 1)
        acc["depths"].append(depth)
        acc["catalog_profile_present"] = int(acc["catalog_profile_present"]) + int(bool(record["catalog_profile_present"]))
        acc["description_present"] = int(acc["description_present"]) + int(bool(record["description_present"]))
        iso_acc[(site_key, iso14224_proxy(depth))] += 1
        for node in record["nodes"]:
            acc["nodes"][node] += 1
            node_acc[(site_key, node)] += 1

    by_site_rows: list[dict[str, object]] = []
    for site_key, acc in sorted(by_site_acc.items()):
        depths = list(acc["depths"])
        records = int(acc["records"])
        max_depth = max(depths) if depths else 0
        by_site_rows.append(
            {
                "site_key": site_key,
                "ih06_record_count": records,
                "leaf_record_count": int(acc["leaf_records"]),
                "min_depth": min(depths) if depths else 0,
                "median_depth": round(float(median(depths)), 2) if depths else 0,
                "mean_depth": round(float(mean(depths)), 2) if depths else 0,
                "max_depth": max_depth,
                "depth_ge_6_count": sum(1 for depth in depths if depth >= 6),
                "depth_ge_6_share": round(sum(1 for depth in depths if depth >= 6) / records, 4) if records else 0,
                "unique_observed_node_count": len(acc["nodes"]),
                "catalog_profile_present_count": int(acc["catalog_profile_present"]),
                "description_present_count": int(acc["description_present"]),
                "depth_consistency_flag": "deep_structure_present" if max_depth >= 6 else "shallower_structure",
                "raw_values_emitted": False,
            }
        )

    observed_node_rows = [
        {
            "site_key": site_key,
            "observed_node_token": node,
            "row_count": count,
            "iec_21_node_status": "matched_against_materialized_iec_reference",
            "raw_values_emitted": False,
        }
        for (site_key, node), count in sorted(node_acc.items())
    ]

    iso_rows = [
        {
            "site_key": site_key,
            "iso14224_level_proxy": level,
            "row_count": count,
            "mapping_status": "proxy_depth_based_not_validated",
            "raw_values_emitted": False,
        }
        for (site_key, level), count in sorted(iso_acc.items())
    ]

    iec_nodes = read_csv_rows(IEC_NODES_PATH)
    iec_contrast_rows = build_iec_contrast(iec_nodes, node_acc)

    by_site_path = OUTPUTS_DIR / "floc_ih06_crosscheck_by_site_v1.csv"
    nodes_path = OUTPUTS_DIR / "floc_ih06_observed_nodes_v1.csv"
    iso_path = OUTPUTS_DIR / "floc_ih06_iso14224_proxy_v1.csv"
    iec_contrast_path = OUTPUTS_DIR / "floc_ih06_iec_node_contrast_v1.csv"
    summary_path = OUTPUTS_DIR / "floc_ih06_crosscheck_summary_v1.json"
    memo_path = DOCS_DIR / "floc_ih06_crosscheck.md"

    write_csv(
        by_site_path,
        by_site_rows,
        [
            "site_key",
            "ih06_record_count",
            "leaf_record_count",
            "min_depth",
            "median_depth",
            "mean_depth",
            "max_depth",
            "depth_ge_6_count",
            "depth_ge_6_share",
            "unique_observed_node_count",
            "catalog_profile_present_count",
            "description_present_count",
            "depth_consistency_flag",
            "raw_values_emitted",
        ],
    )
    write_csv(
        nodes_path,
        observed_node_rows,
        ["site_key", "observed_node_token", "row_count", "iec_21_node_status", "raw_values_emitted"],
    )
    write_csv(
        iso_path,
        iso_rows,
        ["site_key", "iso14224_level_proxy", "row_count", "mapping_status", "raw_values_emitted"],
    )
    write_csv(
        iec_contrast_path,
        iec_contrast_rows,
        [
            "concept_id",
            "node_id",
            "published_description",
            "clause_table",
            "iec_node_category",
            "ih06_contrast_scope",
            "observed_in_ih06_token_inventory",
            "total_observed_rows",
            "observed_site_count",
            "contrast_status",
            "evidence_type",
            "tier",
            "source_caveat",
            "raw_values_emitted",
        ],
    )

    max_depths = [int(row["max_depth"]) for row in by_site_rows]
    depth_ge_6_total = sum(int(row["depth_ge_6_count"]) for row in by_site_rows)
    physical_contrast_rows = [row for row in iec_contrast_rows if row["ih06_contrast_scope"] == "physical_subsystem"]
    physical_observed = [
        row for row in physical_contrast_rows if bool(row["observed_in_ih06_token_inventory"])
    ]
    physical_not_observed = [
        row for row in physical_contrast_rows if not bool(row["observed_in_ih06_token_inventory"])
    ]
    non_physical_excluded = [
        row for row in iec_contrast_rows if row["ih06_contrast_scope"] != "physical_subsystem"
    ]
    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "task": "T6b_IH06_crosscheck",
        "ih06_workbook_found": True,
        "ih06_rows_read": len(raw_records),
        "site_count_sanitized": len(by_site_rows),
        "observed_node_rows": len(observed_node_rows),
        "iso14224_proxy_rows": len(iso_rows),
        "iec_nodes_materialized": len(iec_nodes),
        "iec_physical_subsystem_nodes_for_contrast": len(physical_contrast_rows),
        "iec_physical_subsystem_nodes_observed_by_token": len(physical_observed),
        "iec_physical_subsystem_nodes_not_observed_by_token": len(physical_not_observed),
        "iec_non_physical_nodes_excluded_from_missing_subsystem_claims": len(non_physical_excluded),
        "max_depth_min_by_site": min(max_depths) if max_depths else 0,
        "max_depth_max_by_site": max(max_depths) if max_depths else 0,
        "depth_ge_6_total": depth_ge_6_total,
        "iec_21_node_contrast_status": "completed_as_token_proxy_requires_crosswalk_for_final_missing_system_claims",
        "raw_values_emitted": False,
        "outputs": {
            "by_site_csv": str(by_site_path.relative_to(PROJECT_ROOT)),
            "observed_nodes_csv": str(nodes_path.relative_to(PROJECT_ROOT)),
            "iso14224_proxy_csv": str(iso_path.relative_to(PROJECT_ROOT)),
            "iec_node_contrast_csv": str(iec_contrast_path.relative_to(PROJECT_ROOT)),
            "memo": str(memo_path.relative_to(PROJECT_ROOT)),
        },
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    memo = f"""# FLOC IH06 Crosscheck

## Scope

T6b crosscheck over the IH06 reference/master-data workbook. This is a sanitized, aggregate-only pass.

No raw operational values, plant names, or functional-location identifiers are emitted.

## What Was Read

- IH06 workbook found: yes
- IH06 rows read: {summary["ih06_rows_read"]}
- Sanitized site groups: {summary["site_count_sanitized"]}
- Observed logical-node rows emitted: {summary["observed_node_rows"]}
- ISO 14224 proxy rows emitted: {summary["iso14224_proxy_rows"]}
- IEC logical nodes materialized: {summary["iec_nodes_materialized"]}
- IEC physical subsystem nodes used for IH06 contrast: {summary["iec_physical_subsystem_nodes_for_contrast"]}
- IEC physical subsystem nodes observed by direct token match: {summary["iec_physical_subsystem_nodes_observed_by_token"]}
- IEC physical subsystem nodes not observed by direct token match: {summary["iec_physical_subsystem_nodes_not_observed_by_token"]}
- Non-physical IEC nodes excluded from missing-subsystem claims: {summary["iec_non_physical_nodes_excluded_from_missing_subsystem_claims"]}

## Questions From Plan v2

### What IEC systems do not appear in IH06?

Status: completed as a token-level proxy. The 21-node IEC reference set is now materialized from accessible preview/table material. Only physical turbine subsystem nodes are used for IH06 missing-system contrast.

Direct token matching did not observe {summary["iec_physical_subsystem_nodes_not_observed_by_token"]} of {summary["iec_physical_subsystem_nodes_for_contrast"]} physical subsystem nodes. This does not yet prove absence of those systems because IH06 may use site-specific FLOC segment codes rather than IEC logical-node identifiers. A crosswalk is required before final missing-system claims.

### Where is IH06 deeper than the standard?

Status: measured with a depth proxy. Depth by site was measured, and no rows at depth >= 6 were observed in this pass. Therefore, no deeper-than-proxy claim is made. This remains a depth-based proxy, not a validated ISO mapping.

### Is the depth consistent between plants?

Status: measured by sanitized site key. Site-level min/median/mean/max depth and depth >= 6 share are reported in the by-site table.

## Outputs

- `{summary["outputs"]["by_site_csv"]}`
- `{summary["outputs"]["observed_nodes_csv"]}`
- `{summary["outputs"]["iso14224_proxy_csv"]}`
- `{summary["outputs"]["iec_node_contrast_csv"]}`
- `{summary["outputs"]["memo"]}`

## Interpretation

This pass turns T6 from a support-source inventory into an actual IH06 structure crosscheck. The IEC 21-node contrast is no longer blocked by missing reference materialization.

The contrast is still a token-level proxy: it can show direct matches or non-matches between IH06 FLOC tokens and IEC node identifiers, but it cannot by itself prove physical-system absence without a FLOC-to-IEC crosswalk.

FLOC remains a separate namespace. KKS/RDS-PP can support and validate interpretation, but it does not resolve or construct hierarchy.

## Next Actions

- Build or obtain a FLOC-to-IEC crosswalk before final missing-system claims.
- Review site-level depth outliers using internal-only raw lookup if needed.
- Keep all public/versioned outputs sanitized.
"""
    memo_path.write_text(memo, encoding="utf-8")

    print(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    main()
