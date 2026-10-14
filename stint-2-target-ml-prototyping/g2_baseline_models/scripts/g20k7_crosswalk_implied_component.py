"""G2.0k.7: compare item-description crosswalk profiles with IH06 nodes."""

import argparse
import csv
import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone

import g20i_component_resolution as base
import g20k5_component_profile_comparison as k5
import g20k6_semantic_crosswalk_membership as k6

OUT = k5.OUT
PRIVATE = k5.PRIVATE
PLAN = base.STINT2 / "docs/PLAN-G2.0k.7—crosswalk-Implied-component.md"
COMPLETE = PRIVATE / "g20k7_enabling_sets_complete.csv"
DETAIL = PRIVATE / "g20k7_detail.csv"
PAIR_OUT = OUT / "g20k7_implied_pairs_sanitized.csv"
ORDER_OUT = OUT / "g20k7_implied_orders_sanitized.csv"
AGREEMENT_OUT = OUT / "g20k7_g20i_agreement_sanitized.csv"
COVERAGE_OUT = OUT / "g20k7_coverage_sanitized.csv"
MEMO = OUT / "g20k7_memo.md"
MANIFEST = OUT / "g20k7_run_manifest.json"
PAIR_CLASSES = (
    "no_turbine_subtree", "implied_single_node",
    "implied_multi_node_one_rbnr", "implied_multi_rbnr", "implied_none",
)
NODE_CLASSES = (
    "same_node", "same_rbnr_other_node", "same_subsystem",
    "different_subsystem", "no_implied_node",
)
PROFILE_CLASSES = ("same_rbnr", "different_rbnr", "no_implied_node")


def write_csv(path, rows, *, private=False):
    if not rows:
        raise ValueError("Refusing empty CSV " + str(path))
    with path.open("x", newline="", encoding="utf-8") as handle:
        if private:
            os.chmod(path, 0o600)
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    if len(k5.read_csv(path)) != len(rows):
        raise ValueError("CSV round-trip drift " + str(path))


def split_pipes(value):
    return set(value.split("|")) if value else set()


def profile_sources():
    consensus = {r["order_id_hash"]: r for r in k5.read_csv(k5.CONSENSUS)}
    expansion = {r["order_id_hash"]: r for r in k5.read_csv(k5.EXPANSION)}
    profiles = k5.resolved_profiles()
    if len(consensus) != 10749 or len(profiles) != 3935:
        raise ValueError("G2.0i profile source count drift")
    resolved = [key for key, row in consensus.items() if row["profile_status"].startswith("resolved")]
    node_count = sum(bool(consensus[key]["resolved_node_hash"]) for key in resolved)
    if (len(resolved), node_count) != (3934, 2400):
        raise ValueError("R4 base node/profile split drift")
    added = set(profiles) - set(resolved)
    if len(added) != 1:
        raise ValueError("R4 expansion count drift")
    only = next(iter(added))
    if (expansion[only]["expanded_profile_status"] != "resolved_node_ambiguous" or
            consensus[only]["resolved_node_hash"]):
        raise ValueError("R4 expanded profile unexpectedly has a node")
    return consensus, profiles


def completed_enablers():
    k5.verify()
    if not PLAN.exists():
        raise FileNotFoundError(PLAN)
    allowed, descriptions, _ = k6.catalog_with_descriptions()
    by_pair = defaultdict(set)
    b_pairs = {(group, code) for typ, group, code in descriptions if typ == "B"}
    for (rbnr, typ), groups in allowed.items():
        if typ != "B":
            continue
        for group, code in b_pairs:
            if group in groups:
                by_pair[(group, code)].add(rbnr)
    full = [r for r in k5.read_csv(k6.DETAIL_OUT)
            if r["analysis"] == "crosswalk_membership" and r["population"] == "full"]
    summary = {r["category"]: int(r["count"])
               for r in k5.read_csv(k6.MEMBERSHIP_OUT)
               if r["population"] == "full" and r["unit"] == "pair"
               and r["record_type"] == "category"}
    if len(full) != 5778 or len({(r["order_id_hash"], r["group"], r["code"]) for r in full}) != 5778:
        raise ValueError("R2 full per-pair records drift")
    profiles = k5.resolved_profiles()
    counts = Counter()
    rows = []
    for row in full:
        key = row["order_id_hash"]
        pair = row["group"], row["code"]
        enabling = by_pair[pair]
        if not enabling:
            raise ValueError("Strong crosswalk pair has no enabling profile")
        old = split_pipes(row["other_enabling_rbnrs"])
        if row["membership_category"] == "in_other_profile" and old != enabling:
            raise ValueError("G2.0k.6 persisted enabling set differs")
        if row["membership_category"] == "in_component_profile":
            if old or profiles.get(key) not in enabling:
                raise ValueError("R2 11-pair completion inconsistent")
        counts[row["membership_category"]] += 1
        rows.append({
            "order_id_hash": key, "group": pair[0], "code": pair[1],
            "component_rbnr": profiles.get(key, ""),
            "g20k6_membership_category": row["membership_category"],
            "enabling_rbnrs": "|".join(sorted(enabling)),
            "enabling_rbnr_count": len(enabling),
            "completion_source": "g20k6_persisted" if old else "g20k6_unchanged_catalogue_logic",
        })
    if counts != Counter(summary) or (
        counts["in_pmmuww"], counts["in_component_profile"],
        counts["in_other_profile"]
    ) != (0, 11, 5767):
        raise ValueError("R2 0/11/5767 gate mismatch")
    if sum(r["completion_source"] == "g20k6_unchanged_catalogue_logic" for r in rows) != 11:
        raise ValueError("R2 did not complete exactly 11 pair records")
    return rows, counts


def preflight(*, persist=False):
    rows, counts = completed_enablers()
    consensus, profiles = profile_sources()
    strong = k5.strong_crosswalk()
    overlap = set(strong) & set(profiles)
    node_overlap = sum(bool(consensus[key]["resolved_node_hash"]) for key in overlap)
    if (len(strong), len(overlap), node_overlap, len(overlap) - node_overlap) != (3013, 1189, 770, 419):
        raise ValueError("R4/R5 scope count drift")
    g12 = base.read_g12()
    source = {r["order_id_hash"]: r for r in g12}
    if len(source) != 10749 or not set(strong) <= set(source):
        raise ValueError("R5 strong orders not contained in B1 G1.2 source")
    nodes, children = base.load_nodes()
    valid, _, _ = base.load_catalog()
    if not nodes or not children or not valid:
        raise ValueError("R3/R6 IH06 hierarchy absent")
    facts = {
        "R1": {"state": "confirmed", "source": "g11_material_to_catalog_b_crosswalk.py:248-261 itemDescription; G2.0i-resolution-chain-code-spec.md:Inputs/2 reason + descriptionExtended", "reading": "different text fields, not text-free independence"},
        "R2": {"state": "confirmed", "source": "g20k6_detail.csv full population + Wind Catalog Group and Codes Final v4.xlsx profile/type/group and B group/code", "pair_counts": dict(counts), "completed_pair_rows": 11},
        "R3": {"state": "confirmed", "source": "g20i_component_resolution.py:load_nodes, descendants_of, effective_profile; g20k4_tie_structure_diagnostic.py:ancestor_path", "rule": "site-aware reachable descendants with nearest-valid-ancestor RBNR"},
        "R4": {"state": "confirmed", "source": "g20i_profile_consensus_by_order_sanitized.csv:resolved_node_hash/resolved_rbnr; g20k_expansion_affected_orders_sanitized.csv:expanded_profile_status", "unique_node_all": 2400, "profile_only_all": 1535, "unique_node_overlap": 770, "profile_only_overlap": 419},
        "R5": {"state": "confirmed", "source": "g11_item_signal_rows_sanitized.csv joined to B1 service-orders; G1.2 B1 order keys", "strong_orders": 3013, "overlap_orders": 1189},
        "R6": {"state": "confirmed", "source": "g20i_component_resolution.py:load_nodes uses IH06; g20i_postrun_audit.md:assetId to IH08 zero of 10749", "candidate_source": "IH06 functional locations only"},
    }
    if persist:
        if COMPLETE.exists():
            raise FileExistsError(COMPLETE)
        if not PRIVATE.is_dir() or PRIVATE.stat().st_mode & 0o777 != 0o700:
            raise PermissionError("Private directory must be 700")
        write_csv(COMPLETE, rows, private=True)
    return facts, rows, consensus, profiles, strong, source, nodes, children, valid


def ancestor_path(node, root, nodes):
    path, seen = [], set()
    while node in nodes and node not in seen:
        seen.add(node)
        path.append(node)
        if node == root:
            return tuple(reversed(path))
        node = nodes[node]["parent"]
    return ()


def implied_class(nodes_for_pair, root_present, effective):
    if not root_present:
        return "no_turbine_subtree"
    if not nodes_for_pair:
        return "implied_none"
    if len(nodes_for_pair) == 1:
        return "implied_single_node"
    if len({effective[node] for node in nodes_for_pair}) == 1:
        return "implied_multi_node_one_rbnr"
    return "implied_multi_rbnr"


def size_band(n):
    return "1" if n == 1 else "2-5" if n <= 5 else "6-20" if n <= 20 else ">20"


def run():
    targets = (PAIR_OUT, ORDER_OUT, AGREEMENT_OUT, COVERAGE_OUT, DETAIL, MEMO, MANIFEST)
    if any(path.exists() for path in targets):
        raise FileExistsError("G2.0k.7 output already exists")
    if not COMPLETE.exists() or COMPLETE.stat().st_mode & 0o777 != 0o600:
        raise FileNotFoundError("R2 completed enabling sets missing or wrong mode")
    facts, expected_rows, consensus, profiles, strong, source, nodes, children, valid = preflight()
    completed_rows = k5.read_csv(COMPLETE)
    if completed_rows != [
        {key: str(value) for key, value in row.items()} for row in expected_rows
    ]:
        raise ValueError("R2 persisted complete sets differ from pre-flight")
    by_order = defaultdict(list)
    for row in completed_rows:
        by_order[row["order_id_hash"]].append(row)
    if len(by_order) != 3013:
        raise ValueError("Full strong-order population drift")
    node_by_hash = {base.short_hash("IH06NODE", node): node for node in nodes}
    if len(node_by_hash) != len(nodes):
        raise ValueError("IH06 hashed node collision")
    pair_count, order_count = Counter(), Counter()
    size_count = Counter()
    agreement = Counter()
    coverage = Counter()
    different_pairs = 0
    control_11 = 0
    private = []
    subtree_cache = {}
    for key, pair_rows in sorted(by_order.items()):
        src = source[key]
        root = src["matched_floc"] if src["match_status"] == "matched_asset_node" else ""
        if root and root not in nodes:
            raise ValueError("Matched turbine root absent from IH06")
        if root and root not in subtree_cache:
            descendants = base.descendants_of(root, children)
            effective = {}
            for node in descendants:
                if not node.startswith(root + "-") or node.split("-")[0] != root.split("-")[0]:
                    raise ValueError("R3 IH06 candidate escaped site/turbine subtree")
                if not ancestor_path(node, root, nodes):
                    raise ValueError("R3 reachable node has incomplete ancestor path")
                profile, _, _ = base.effective_profile(node, nodes, valid)
                if profile:
                    effective[node] = profile
            subtree_cache[root] = effective
        effective = subtree_cache.get(root, {})
        union = set()
        pair_sets = []
        for row in pair_rows:
            enabling = split_pipes(row["enabling_rbnrs"])
            implied = {node for node, profile in effective.items() if profile in enabling}
            category = implied_class(implied, bool(root), effective)
            pair_count[category] += 1
            size_count[size_band(len(enabling))] += 1
            union |= implied
            pair_sets.append(implied)
            private.append({
                "order_id_hash": key, "turbine_node": root,
                "crosswalk_group": row["group"], "crosswalk_code": row["code"],
                "enabling_rbnrs": row["enabling_rbnrs"],
                "implied_nodes": "|".join(sorted(implied)),
                "implied_rbnrs": "|".join(sorted({effective[n] for n in implied})),
                "pair_category": category, "order_category": "",
                "g20i_profile": profiles.get(key, ""), "g20i_node": "",
                "agreement_level": "", "agreement_category": "",
            })
        order_category = implied_class(union, bool(root), effective)
        order_count[order_category] += 1
        nonempty = [s for s in pair_sets if s]
        if len(nonempty) >= 2 and any(nonempty[i].isdisjoint(nonempty[j])
                                      for i in range(len(nonempty)) for j in range(i + 1, len(nonempty))):
            different_pairs += 1
        level, category, g20i_node = "", "", ""
        if key in profiles:
            prior = consensus[key]
            g20i_profile = profiles[key]
            g20i_node_hash = prior["resolved_node_hash"]
            if not union:
                category = "no_implied_node"
            if g20i_node_hash:
                level = "node"
                g20i_node = node_by_hash.get(g20i_node_hash, "")
                if not g20i_node or not root or not ancestor_path(g20i_node, root, nodes):
                    raise ValueError("G2.0i resolved node cannot be located in turbine subtree")
                if union:
                    implied_profiles = {effective[n] for n in union}
                    if g20i_node in union:
                        category = "same_node"
                    elif g20i_profile in implied_profiles:
                        category = "same_rbnr_other_node"
                    elif any(ancestor_path(node, root, nodes)[1:] and
                             any(a == b for a, b in zip(ancestor_path(g20i_node, root, nodes)[1:],
                                                         ancestor_path(node, root, nodes)[1:]))
                             for node in union):
                        category = "same_subsystem"
                    else:
                        category = "different_subsystem"
                agreement[(level, category)] += 1
            else:
                level = "profile"
                if union:
                    category = ("same_rbnr" if g20i_profile in {effective[n] for n in union}
                                else "different_rbnr")
                agreement[(level, category)] += 1
            if any(row["g20k6_membership_category"] == "in_component_profile" for row in pair_rows):
                control_11 += 1
                if not ((level == "node" and category in ("same_node", "same_rbnr_other_node")) or
                        (level == "profile" and category == "same_rbnr")):
                    raise ValueError("11-order R2 component membership control failed")
        else:
            coverage[order_category] += 1
        for row in private[-len(pair_rows):]:
            row["order_category"] = order_category
            row["g20i_node"] = g20i_node
            row["agreement_level"] = level
            row["agreement_category"] = category
    if sum(pair_count.values()) != 5778 or sum(order_count.values()) != 3013:
        raise ValueError("Section 1 population sum drift")
    if sum(agreement[("node", c)] for c in NODE_CLASSES) != 770:
        raise ValueError("Section 2a sum drift")
    if sum(agreement[("profile", c)] for c in PROFILE_CLASSES) != 419:
        raise ValueError("Section 2b sum drift")
    if sum(coverage.values()) != 1824 or control_11 != 11:
        raise ValueError("Section 3 or 11-order control drift")
    if sum(size_count.values()) != 5778:
        raise ValueError("Enabling-set band sum drift")
    pair_rows = [{"record_type": "availability", "category": c,
                  "count": pair_count[c], "denominator": 5778, "sum_valid": True}
                 for c in PAIR_CLASSES]
    pair_rows += [{"record_type": "enabling_set_size", "category": c,
                   "count": size_count[c], "denominator": 5778, "sum_valid": True}
                  for c in ("1", "2-5", "6-20", ">20")]
    order_rows = [{"record_type": "availability", "category": c,
                   "count": order_count[c], "denominator": 3013,
                   "pairs_point_to_different_nodes": different_pairs, "sum_valid": True}
                  for c in PAIR_CLASSES]
    agreement_rows = [{"level": level, "category": c,
                       "count": agreement[(level, c)], "denominator": denominator,
                       "sum_valid": True, "comparison_type": "agreement_not_precision"}
                      for level, classes, denominator in (("node", NODE_CLASSES, 770),
                                                           ("profile", PROFILE_CLASSES, 419))
                      for c in classes]
    coverage_rows = [{"category": c, "count": coverage[c],
                      "without_g20i_profile": 1824,
                      "potential_profile_determinable": c in
                      ("implied_single_node", "implied_multi_node_one_rbnr"),
                      "sum_valid": True}
                     for c in PAIR_CLASSES]
    if DETAIL.exists():
        raise FileExistsError(DETAIL)
    if PRIVATE.stat().st_mode & 0o777 != 0o700:
        raise PermissionError("Private directory mode is not 700")
    write_csv(DETAIL, private, private=True)
    for path, rows in ((PAIR_OUT, pair_rows), (ORDER_OUT, order_rows),
                       (AGREEMENT_OUT, agreement_rows), (COVERAGE_OUT, coverage_rows)):
        write_csv(path, rows)
    memo = [
        "# G2.0k.7 - crosswalk-implied component",
        "", "Diagnostic only, B1 only. No G2.0i replay, scoring, promotion or F6 change.",
        "", "## Pre-flight",
    ]
    for gate, value in facts.items():
        memo.append(f"- **{gate}: {value['state']}** - {value['source']}. " +
                    json.dumps({k: v for k, v in value.items() if k not in ("state", "source")}, sort_keys=True))
    memo += [
        "", "## Results",
        "- Pair availability: " + ", ".join(f"{c}={pair_count[c]}" for c in PAIR_CLASSES) + ".",
        "- Order availability: " + ", ".join(f"{c}={order_count[c]}" for c in PAIR_CLASSES) + ".",
        f"- Orders whose separate crosswalk pairs imply disjoint nonempty node sets: {different_pairs}.",
        "- Node-level agreement (770): " + ", ".join(f"{c}={agreement[('node', c)]}" for c in NODE_CLASSES) + ".",
        "- Profile-level agreement (419): " + ", ".join(f"{c}={agreement[('profile', c)]}" for c in PROFILE_CLASSES) + ". No node agreement is computed for these orders.",
        f"- Strong-crosswalk orders without G2.0i profile: {sum(coverage.values())}; profile-determinable potential: {coverage['implied_single_node'] + coverage['implied_multi_node_one_rbnr']}. No profile is assigned.",
        "- Crosswalk and G2.0i are both text-derived from different fields (itemDescription versus reason/descriptionExtended). Agreement is not precision or ground truth.",
        "- IH06 descendant nodes use effective nearest-valid-ancestor RBNR; no IH08 equipment nodes are candidates.",
        "- Client node identifiers, non-PMMUWW RBNRs and per-order pairs remain only in internal/ at mode 600.",
    ]
    MEMO.write_text("\n".join(memo) + "\n", encoding="utf-8")
    manifest = {
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "B1_diagnostic_only", "no_text_fields_reread": True,
        "no_replay_or_scoring": True, "no_promotion": True,
        "denominator_changed": False,
        "source_sha256": {str(p.relative_to(base.ROOT)): base.sha(p) for p in
                          (PLAN, k6.DETAIL_OUT, k6.MEMBERSHIP_OUT, COMPLETE,
                           k5.CONSENSUS, k5.EXPANSION, base.SOURCES[0],
                           base.SOURCES[2], base.SOURCES[4], base.SOURCES[5])},
        "output_sha256": {p.name: base.sha(p) for p in
                          (PAIR_OUT, ORDER_OUT, AGREEMENT_OUT, COVERAGE_OUT, MEMO)},
        "private_sha256": {p.name: base.sha(p) for p in (COMPLETE, DETAIL)},
        "private_mode": oct(DETAIL.stat().st_mode & 0o777),
        "private_directory_mode": oct(PRIVATE.stat().st_mode & 0o777),
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "pair_categories": dict(pair_count), "order_categories": dict(order_count),
        "node_agreement": {c: agreement[("node", c)] for c in NODE_CLASSES},
        "profile_agreement": {c: agreement[("profile", c)] for c in PROFILE_CLASSES},
        "coverage_without_g20i": dict(coverage), "control_11": control_11,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("preflight", "run"))
    args = parser.parse_args()
    if args.mode == "preflight":
        print(json.dumps(preflight(persist=True)[0], indent=2, sort_keys=True))
    else:
        run()
