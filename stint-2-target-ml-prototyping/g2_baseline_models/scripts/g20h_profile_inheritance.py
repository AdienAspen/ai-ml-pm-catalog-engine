"""Audit IH06 ancestor-profile inheritance for G1.2 B1 turbine matches."""

from __future__ import annotations

import csv
import hashlib
from collections import Counter, defaultdict
from pathlib import Path

from openpyxl import load_workbook


ROOT = Path("/home/adien-i7-remote/workspace/fsa_bridge_ml_feasibility")
STINT2 = ROOT / "stint-2-target-ml-prototyping"
IH06 = ROOT / "data/interim/extracted_source/package_001_37cac7fe/Data/References/IH06 FSA Sites PRD.XLSX"
CATALOG = ROOT / "data/interim/extracted_source/package_001_37cac7fe/Data/References/Wind Catalog Group and Codes Final v4.xlsx"
G12 = STINT2 / "g1_actionable_zeros/g12_floc_alignment"
OUT = STINT2 / "g2_baseline_models/outputs/g20h_profile_inheritance"


def hashed_node(value: str) -> str:
    return "IH06NODE-" + hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], columns: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def load_ih06() -> dict[str, dict[str, str]]:
    wb = load_workbook(IH06, read_only=True, data_only=True)
    values = wb.active.values
    headers = next(values)
    idx = {name: pos for pos, name in enumerate(headers)}
    nodes = {}
    for row in values:
        floc = str(row[idx["Functional Location"]] or "").strip()
        if not floc:
            continue
        if floc in nodes:
            raise ValueError(f"Duplicate IH06 node: {floc}")
        nodes[floc] = {
            "parent": str(row[idx["Superior functional location"]] or "").strip(),
            "profile": str(row[idx["Catalog Profile"]] or "").strip(),
            "description": str(row[idx["Description of functional location"]] or "").strip(),
        }
    wb.close()
    return nodes


def load_valid_profiles() -> set[str]:
    wb = load_workbook(CATALOG, read_only=True, data_only=True)
    listed = {str(row[0]).strip() for row in list(wb["Catalog Profile List"].values)[1:] if row[0]}
    associated = {str(row[0]).strip() for row in list(wb["Catalog Profile and Code Groups"].values)[1:] if row[0]}
    wb.close()
    return listed & associated


def walk_ancestors(
    nodes: dict[str, dict[str, str]], start: str, valid_profiles: set[str]
) -> tuple[str, str, int, str]:
    """Return status, inherited profile, edges walked, terminal node."""
    seen = {start}
    current = start
    edges = 0
    while True:
        parent = nodes[current]["parent"]
        if not parent:
            return "no_profile_no_filter", "", edges, current
        edges += 1
        if parent in seen:
            return "cycle", "", edges, current
        if parent not in nodes:
            return "missing_parent_node", "", edges, current
        seen.add(parent)
        current = parent
        if nodes[current]["profile"] in valid_profiles:
            return "inherited", nodes[current]["profile"], edges, current


def main() -> None:
    nodes = load_ih06()
    valid_profiles = load_valid_profiles()
    internal = read_csv(G12 / "internal/g12_floc_alignment_internal_review.csv")
    sanitized = read_csv(G12 / "outputs/g12_floc_alignment_order_level_sanitized.csv")
    if len(internal) != len(sanitized) or len(internal) != 10749:
        raise ValueError("G1.2 row counts do not reconcile to 10,749 orders")
    if len({r["order_id"] for r in internal}) != len(internal):
        raise ValueError("G1.2 internal order IDs are not unique")
    if len({r["order_id_hash"] for r in sanitized}) != len(sanitized):
        raise ValueError("G1.2 sanitized order hashes are not unique")

    order_rows = []
    node_orders = defaultdict(list)
    baseline = Counter()
    for source, clean in zip(internal, sanitized, strict=True):
        expected_hash = "ORDER-" + hashlib.sha256(source["order_id"].encode("utf-8")).hexdigest()[:16]
        if clean["order_id_hash"] != expected_hash or source["match_status"] != clean["match_status"]:
            raise ValueError("G1.2 internal/sanitized rows are not aligned")
        if source["match_status"] != "matched_asset_node":
            baseline["unmatched"] += 1
            continue
        floc = source["matched_floc"]
        if floc not in nodes:
            raise ValueError("G1.2 matched node absent from IH06")
        if nodes[floc]["profile"] in valid_profiles:
            baseline["direct_profile"] += 1
            continue

        status, profile, edges, terminal = walk_ancestors(nodes, floc, valid_profiles)
        baseline[status] += 1
        row = {
            "order_id_hash": clean["order_id_hash"],
            "node_hash": hashed_node(floc),
            "site_key": clean["site_key"],
            "node_depth": source["matched_depth"],
            "edges_walked": edges,
            "inherited_rbnr": profile,
            "status": status,
            "terminal_node_hash": hashed_node(terminal),
            "evidence_type": "structural_hierarchy_lookup",
            "evaluation_independence": "derived_from_rules",
        }
        order_rows.append(row)
        node_orders[floc].append(row)

    if sum(baseline.values()) != 10749 or len(order_rows) != 1548:
        raise ValueError(f"Unexpected G1.2 partition: {dict(baseline)}")

    node_rows = []
    for floc, orders in sorted(node_orders.items()):
        descendants = [v for key, v in nodes.items() if key.startswith(floc + "-")]
        profiles_below = sum(bool(v["profile"]) for v in descendants)
        node_rows.append({
            "node_hash": hashed_node(floc),
            "site_key": orders[0]["site_key"],
            "order_count": len(orders),
            "node_depth": orders[0]["node_depth"],
            "status": orders[0]["status"],
            "edges_walked": orders[0]["edges_walked"],
            "node_description_has_turbine_marker": str(
                ", T" in nodes[floc]["description"]
            ).lower(),
            "descendant_nodes": len(descendants),
            "profiled_descendant_nodes": profiles_below,
            "asset_characterization": "turbine_node_from_g12_alignment",
        })

    OUT.mkdir(parents=True, exist_ok=True)
    write_csv(
        OUT / "g20h_profile_inheritance_sanitized.csv",
        order_rows,
        ["order_id_hash", "node_hash", "site_key", "node_depth", "edges_walked", "inherited_rbnr", "status", "terminal_node_hash", "evidence_type", "evaluation_independence"],
    )
    write_csv(
        OUT / "g20h_unresolved_node_profile_sanitized.csv",
        [r for r in node_rows if r["status"] != "inherited"],
        ["node_hash", "site_key", "order_count", "node_depth", "status", "edges_walked", "node_description_has_turbine_marker", "descendant_nodes", "profiled_descendant_nodes", "asset_characterization"],
    )

    depth_counts = Counter(str(r["edges_walked"]) for r in order_rows)
    profile_counts = Counter(r["inherited_rbnr"] for r in order_rows if r["inherited_rbnr"])
    site_counts = Counter(r["site_key"] for r in order_rows)
    lines = [
        "# G2.0h - IH06 profile inheritance audit",
        "",
        "Scope: B1 relational, 10,749 orders; G1.2 matched turbine nodes only.",
        "Hierarchy: exact `Superior functional location` links in IH06. No default profile.",
        "",
        f"- Direct RBNR on matched node: {baseline['direct_profile']:,} orders.",
        f"- No RBNR on matched node, tested for inheritance: {len(order_rows):,} orders across {len(node_rows)} nodes.",
        f"- Inherited RBNR: {baseline['inherited']:,} orders; distribution: {dict(profile_counts)}.",
        f"- `no_profile_no_filter` (no valid RBNR on any ancestor): {baseline['no_profile_no_filter']:,} orders.",
        f"- Missing parent node: {baseline['missing_parent_node']:,}; cycles: {baseline['cycle']:,}.",
        f"- Walked edges (all tested orders): {dict(sorted(depth_counts.items()))}.",
        f"- Site keys of tested orders: {dict(sorted(site_counts.items()))}.",
        f"- G1.2 unmatched orders outside inheritance scope: {baseline['unmatched']:,}.",
        "",
        "## Unresolved node characterization",
        "",
        f"- {len(node_rows)} distinct G1.2 turbine nodes remain unresolved by upward inheritance.",
        f"- IH06 turbine-description marker present on {sum(r['node_description_has_turbine_marker'] == 'true' for r in node_rows)} of {len(node_rows)} nodes.",
        "- The parent root has no RBNR and no further ancestor. These are not classified as substation, SCADA, or balance-of-plant assets.",
        "- Each unresolved turbine node has profiled descendants. Their RBNR values are not inherited upward and require component/leaf resolution (G2.0i).",
        "",
        "## G2.0i controls carried forward",
        "",
        "- Text-derived Object Part evidence cannot independently evaluate the FLOC/profile-constrained code space it helped create.",
        "- Evaluate FLOC against independent structural evidence where available; otherwise declare the dependency.",
        "- Match within site and turbine, report resolved/ambiguous/abstained per order, and verify profile -> type -> group -> codes before any answer-space figure.",
        "- Information-type presence and classification into catalog codes are separate claims; the latter has not been measured here.",
        "",
        "No mapping, candidate promotion, or F6 denominator change was made.",
    ]
    (OUT / "g20h_memo.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
