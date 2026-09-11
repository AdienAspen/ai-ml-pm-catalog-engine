from __future__ import annotations

import csv
import hashlib
import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from openpyxl import load_workbook


PROJECT_ROOT = Path("/home/adien-i7-remote/workspace/fsa_bridge_ml_feasibility")
STINT2_ROOT = PROJECT_ROOT / "stint-2-target-ml-prototyping"
OUT = STINT2_ROOT / "g1_actionable_zeros" / "g12_floc_alignment" / "outputs"
INTERNAL_OUT = STINT2_ROOT / "g1_actionable_zeros" / "g12_floc_alignment" / "internal"

SERVICE_ORDERS_JSON = (
    PROJECT_ROOT
    / "data/interim/extracted_source/package_001_37cac7fe/Data/Vestas/api_service_v1_service-orders.json"
)
SITES_JSON = (
    PROJECT_ROOT
    / "data/interim/extracted_source/package_001_37cac7fe/Data/Vestas/api_common_v1_sites.json"
)
IH06_XLSX = (
    PROJECT_ROOT
    / "data/interim/extracted_source/package_001_37cac7fe/Data/References/IH06 FSA Sites PRD.XLSX"
)
STINT1_BY_SITE = (
    PROJECT_ROOT / "stint-1.1-reference-layer/outputs/floc_ih06_crosscheck_by_site_v1.csv"
)

SITE_TO_IH06_ROOT = {
    "SITE04179": {"site_key": "SITE-008", "ih06_root": "9310", "alignment_basis": "site_name_contract_name_high_confidence"},
    "SITE04199": {"site_key": "SITE-009", "ih06_root": "9333", "alignment_basis": "site_name_contract_name_high_confidence"},
    "SITE04190": {"site_key": "SITE-007", "ih06_root": "9301", "alignment_basis": "site_name_contract_name_high_confidence"},
    "SITE04161": {"site_key": "SITE-003", "ih06_root": "0912", "alignment_basis": "site_name_contract_name_high_confidence"},
    "SITE04230": {"site_key": "SITE-001", "ih06_root": "0852", "alignment_basis": "site_name_contract_name_high_confidence"},
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_hash(value: object, length: int = 16) -> str:
    raw = "" if value is None else str(value)
    return hashlib.sha256(raw.encode("utf-8", errors="ignore")).hexdigest()[:length]


def prefixed_hash(prefix: str, value: object, length: int = 16) -> str:
    return f"{prefix}-{stable_hash(value, length)}"


def load_json(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise RuntimeError(f"Expected list payload in {path}")
    return payload


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str], mode_600: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    if mode_600:
        os.chmod(path, 0o600)


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def turbine_token(value: object) -> str:
    text = str(value or "").upper()
    patterns = [
        r"\bPAD[- ]?T[- ]?0*(\d{1,3})\b",
        r"(?:^|[^A-Z0-9])T[- ]?0*(\d{1,3})(?=[^A-Z0-9]|$)",
        r"\bPAD[- ]?0*(\d{1,3})\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return f"{int(match.group(1)):03d}"
    return ""


def floc_depth(floc: str) -> int:
    if not floc:
        return 0
    return len(str(floc).split("-"))


def load_ih06() -> tuple[dict[str, dict[str, dict[str, str]]], dict[str, Counter[int]], set[str]]:
    wb = load_workbook(IH06_XLSX, read_only=True, data_only=True)
    ws = wb.active
    headers = [cell.value for cell in next(ws.iter_rows(min_row=1, max_row=1))]
    idx = {header: pos for pos, header in enumerate(headers)}
    children = defaultdict(set)
    records = []
    for values in ws.iter_rows(min_row=2, values_only=True):
        floc = str(values[idx["Functional Location"]] or "").strip()
        if not floc:
            continue
        superior = str(values[idx["Superior functional location"]] or "").strip()
        if superior:
            children[superior].add(floc)
        records.append(
            {
                "floc": floc,
                "description": str(values[idx["Description of functional location"]] or "").strip(),
                "root": floc.split("-")[0],
                "depth": str(floc_depth(floc)),
                "catalog_profile_present": str(bool(str(values[idx["Catalog Profile"]] or "").strip())).lower(),
            }
        )

    by_root_turbine: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)
    depth_by_root: dict[str, Counter[int]] = defaultdict(Counter)
    leaves = set()
    for record in records:
        floc = record["floc"]
        depth_by_root[record["root"]][int(record["depth"])] += 1
        if floc not in children:
            leaves.add(floc)
        parts = floc.split("-")
        candidate_tokens = set()
        description_token = turbine_token(record["description"])
        if description_token:
            candidate_tokens.add(description_token)
        if len(parts) >= 2 and parts[1].isdigit():
            candidate_tokens.add(f"{int(parts[1]):03d}")
        for turbine in candidate_tokens:
            current = by_root_turbine[record["root"]].get(turbine)
            if current is None or int(record["depth"]) < int(current["depth"]):
                by_root_turbine[record["root"]][turbine] = record
    return by_root_turbine, depth_by_root, leaves


def leaf_count_index(leaves: set[str]) -> dict[tuple[str, str], int]:
    counts: dict[tuple[str, str], int] = defaultdict(int)
    for leaf in leaves:
        parts = leaf.split("-")
        if len(parts) >= 2 and parts[1].isdigit():
            counts[(parts[0], f"{int(parts[1]):03d}")] += 1
    return counts


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    INTERNAL_OUT.mkdir(parents=True, exist_ok=True)
    os.chmod(INTERNAL_OUT, 0o700)

    service_orders = load_json(SERVICE_ORDERS_JSON)
    sites = {row["id"]: row for row in load_json(SITES_JSON)}
    ih06_by_root_turbine, depth_by_root, leaves = load_ih06()
    leaf_counts = leaf_count_index(leaves)
    stint1_by_site = {row["site_key"]: row for row in read_csv(STINT1_BY_SITE)}

    site_rows = []
    order_rows = []
    internal_rows = []
    counters = defaultdict(Counter)

    for order in service_orders:
        site_id = str(order.get("siteId") or "").strip()
        order_id = str(order.get("id") or "").strip()
        mapping = SITE_TO_IH06_ROOT.get(site_id)
        token_sources = [
            order.get("padId"),
            order.get("assetDescription"),
            sites.get(site_id, {}).get("description"),
        ]
        token = ""
        for source in token_sources:
            token = turbine_token(source)
            if token:
                break
        match_status = "unmatched_site"
        root = ""
        site_key = ""
        matched_floc = ""
        matched_depth = ""
        reachable_leaf_count = 0
        if mapping:
            root = mapping["ih06_root"]
            site_key = mapping["site_key"]
            if token:
                candidate = ih06_by_root_turbine.get(root, {}).get(token)
                if candidate:
                    matched_floc = candidate["floc"]
                    matched_depth = candidate["depth"]
                    reachable_leaf_count = leaf_counts.get((root, token), 0)
                    match_status = "matched_asset_node"
                else:
                    match_status = "unmatched_turbine_token"
            else:
                match_status = "missing_turbine_token"

        counters[site_id]["orders"] += 1
        counters[site_id][match_status] += 1
        if token:
            counters[site_id]["orders_with_turbine_token"] += 1

        row = {
            "order_id_hash": prefixed_hash("ORDER", order_id, 16),
            "site_id_hash": prefixed_hash("SITEID", site_id, 12),
            "site_key": site_key,
            "ih06_root_hash": prefixed_hash("IH06ROOT", root, 12) if root else "",
            "asset_id_hash": prefixed_hash("ASSET", order.get("assetId"), 16),
            "pad_id_hash": prefixed_hash("PAD", order.get("padId"), 16),
            "turbine_token_hash": prefixed_hash("TURBINE", token, 12) if token else "",
            "match_status": match_status,
            "matched_depth": matched_depth,
            "reachable_leaf_count_under_asset": reachable_leaf_count,
            "alignment_provenance": "deterministic_site_turbine_token_alignment",
            "evaluation_independence": "derived_from_rules",
        }
        order_rows.append(row)
        internal_rows.append(
            {
                **row,
                "order_id": order_id,
                "site_id": site_id,
                "site_description": sites.get(site_id, {}).get("description", ""),
                "ih06_root": root,
                "pad_id": order.get("padId") or "",
                "asset_description": order.get("assetDescription") or "",
                "turbine_token": token,
                "matched_floc": matched_floc,
            }
        )

    for site_id, counts in sorted(counters.items()):
        mapping = SITE_TO_IH06_ROOT.get(site_id, {})
        site_key = mapping.get("site_key", "")
        root = mapping.get("ih06_root", "")
        by_site = stint1_by_site.get(site_key, {})
        total = counts["orders"]
        matched = counts["matched_asset_node"]
        depth_counts = depth_by_root.get(root, Counter())
        max_depth = max(depth_counts) if depth_counts else 0
        leaf_depths = [floc_depth(leaf) for leaf in leaves if leaf.split("-")[0] == root]
        reachable_leaf_depths = sorted(set(leaf_depths))
        site_rows.append(
            {
                "site_id_hash": prefixed_hash("SITEID", site_id, 12),
                "site_key": site_key,
                "ih06_root_hash": prefixed_hash("IH06ROOT", root, 12) if root else "",
                "orders": total,
                "orders_with_turbine_token": counts["orders_with_turbine_token"],
                "matched_asset_node_orders": matched,
                "asset_node_match_rate": round(matched / total * 100, 6) if total else 0,
                "unmatched_turbine_token_orders": counts["unmatched_turbine_token"],
                "missing_turbine_token_orders": counts["missing_turbine_token"],
                "ih06_record_count": by_site.get("ih06_record_count", ""),
                "ih06_leaf_record_count": by_site.get("leaf_record_count", ""),
                "ih06_max_depth": by_site.get("max_depth", str(max_depth)),
                "ih06_depth_ge_6_count": by_site.get("depth_ge_6_count", ""),
                "reachable_leaf_depths": ";".join(str(depth) for depth in reachable_leaf_depths),
                "reachability_verdict": "asset_node_reachable_leaf_requires_component_selector",
                "alignment_basis": mapping.get("alignment_basis", ""),
                "raw_values_emitted": "False",
            }
        )

    write_csv(
        OUT / "g12_floc_alignment_by_site_sanitized.csv",
        site_rows,
        [
            "site_id_hash",
            "site_key",
            "ih06_root_hash",
            "orders",
            "orders_with_turbine_token",
            "matched_asset_node_orders",
            "asset_node_match_rate",
            "unmatched_turbine_token_orders",
            "missing_turbine_token_orders",
            "ih06_record_count",
            "ih06_leaf_record_count",
            "ih06_max_depth",
            "ih06_depth_ge_6_count",
            "reachable_leaf_depths",
            "reachability_verdict",
            "alignment_basis",
            "raw_values_emitted",
        ],
    )
    write_csv(
        OUT / "g12_floc_alignment_order_level_sanitized.csv",
        order_rows,
        [
            "order_id_hash",
            "site_id_hash",
            "site_key",
            "ih06_root_hash",
            "asset_id_hash",
            "pad_id_hash",
            "turbine_token_hash",
            "match_status",
            "matched_depth",
            "reachable_leaf_count_under_asset",
            "alignment_provenance",
            "evaluation_independence",
        ],
    )
    write_csv(
        INTERNAL_OUT / "g12_floc_alignment_internal_review.csv",
        internal_rows,
        [
            "order_id",
            "site_id",
            "site_description",
            "ih06_root",
            "pad_id",
            "asset_description",
            "turbine_token",
            "matched_floc",
            "match_status",
            "matched_depth",
            "reachable_leaf_count_under_asset",
        ],
        mode_600=True,
    )

    total_orders = sum(row["orders"] for row in site_rows)
    total_matched = sum(row["matched_asset_node_orders"] for row in site_rows)
    summary = {
        "task": "G1.2_floc_ih06_alignment",
        "created_at_utc": utc_now(),
        "service_order_records": len(service_orders),
        "sites_in_relational_path": len(counters),
        "ih06_sites_relevant_to_relational_path": len(SITE_TO_IH06_ROOT),
        "matched_asset_node_orders": total_matched,
        "asset_node_match_rate": round(total_matched / total_orders * 100, 6) if total_orders else 0,
        "floc_leaf_proxy_status": "not_admitted_as_leaf_label",
        "reason": "service order asset identifiers reach IH06 turbine/asset nodes; leaf labels require component selector below asset node",
        "depth_ge_6_total_for_relevant_sites": sum(int(row["ih06_depth_ge_6_count"] or 0) for row in site_rows),
        "raw_operational_values_emitted_in_versioned_outputs": False,
        "internal_review_file_mode": "600",
        "internal_review_dir_mode": "700",
    }
    write_json(OUT / "g12_floc_alignment_summary_sanitized.json", summary)

    memo = f"""# G1.2 FLOC IH06 Alignment Memo

G1.2 tested whether relational B1 asset references can be aligned to IH06/FLOC.

## Result

- Service orders assessed: {len(service_orders):,}
- Relevant relational sites: {len(counters)}
- Orders matched to IH06 asset/turbine node: {total_matched:,}
- Asset-node match rate: {summary['asset_node_match_rate']}%

## Interpretation

The relational path can reach IH06 asset/turbine nodes by site and turbine token. This is useful structural alignment, but it is not yet a FLOC leaf label. The plan constraint still applies: the reachable IH06 leaf is component/maintainable-item depth, and a service order asset reference alone does not select one of the child leaf nodes.

Therefore G1.2 moves FLOC from a raw zero to a bounded alignment result:

- Site and turbine alignment is feasible per site.
- IH06 reachable depth is declared per site.
- FLOC leaf is not admitted as an evaluation/training label from this step alone.
- A future leaf proxy would need a component selector from text or another structured field, constrained to high-band reference anchors.

## Governance

- FLOC remains a separate namespace from SAP catalog targets.
- No cross-site depth aggregation.
- Max depth 4 at a site is not interpreted as asset property; it may reflect extract/modeling depth.
- Versioned outputs contain hashes, counts, statuses, and metadata only.
"""
    (OUT / "g12_floc_alignment_memo.md").write_text(memo, encoding="utf-8")


if __name__ == "__main__":
    main()
