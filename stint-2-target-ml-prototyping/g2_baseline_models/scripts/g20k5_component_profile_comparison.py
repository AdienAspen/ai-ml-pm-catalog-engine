"""G2.0k.5: compare component and turbine catalogue-profile code sets."""

import argparse
import csv
import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from openpyxl import load_workbook

import g20i_component_resolution as base

OUT = base.STINT2 / "g2_baseline_models/outputs/g20k_component_lift"
PRIVATE = base.STINT2 / "g2_baseline_models/internal/g20k_component_lift"
PLAN = base.STINT2 / "docs/PLAN-G2.0k.5—component-profile_vs_turbine-profile.md"
SPEC = base.STINT2 / "docs/G2.0i-resolution-chain-code-spec.md"
CONSENSUS = base.STINT2 / "g2_baseline_models/outputs/g20i_profile_consensus/g20i_profile_consensus_by_order_sanitized.csv"
EXPANSION = OUT / "g20k_expansion_affected_orders_sanitized.csv"
K4 = OUT / "g20k4_tie_order_diagnostic_sanitized.csv"
ITEMS = base.STINT2 / "g1_actionable_zeros/g11_object_part_crosswalk/outputs/g11_item_signal_rows_sanitized.csv"
CROSSWALK = base.STINT2 / "g1_actionable_zeros/g11_object_part_crosswalk/outputs/g11_material_to_catalog_b_crosswalk_sanitized.csv"
SCRIPT = Path(__file__).resolve()
INPUTS = (PLAN, SPEC, CONSENSUS, EXPANSION, K4, ITEMS, CROSSWALK,
          OUT / "g20k4_run_manifest.json", *base.SOURCES, SCRIPT)
TYPES = {"S": "Symptom", "B": "Object Part", "C": "Damage",
         "5": "Cause", "A": "Activity"}
CLASSES = ("component_empty", "same_set", "narrower", "wider",
           "overlapping", "disjoint")
IDENTITY = ("turbine_profile_missing", "same_rbnr", "different_rbnr")


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def catalogue():
    book = load_workbook(base.SOURCES[2], read_only=True, data_only=True)
    allowed, pairs = defaultdict(set), defaultdict(set)
    try:
        for row in list(book["Catalog Profile and Code Groups"].values)[1:]:
            if row[0] and row[2] and row[3]:
                allowed[(str(row[0]).strip(), str(row[2]).strip())].add(str(row[3]).strip())
        for typ in TYPES:
            for row in list(book["Catalog. " + typ + " - Group and Code"].values)[1:]:
                if str(row[0]).strip() == typ and row[1] and row[2]:
                    pairs[typ].add((str(row[1]).strip(), str(row[2]).strip()))
    finally:
        book.close()
    if set(pairs) != set(TYPES):
        raise ValueError("Missing catalogue type")
    return allowed, pairs


def code_set(profile, typ, allowed, pairs):
    return {(group, code) for group, code in pairs[typ]
            if group in allowed[(profile, typ)]}


def classify(component, turbine):
    if not component:
        return "component_empty"
    if component == turbine:
        return "same_set"
    if component < turbine:
        return "narrower"
    if component > turbine:
        return "wider"
    if component & turbine:
        return "overlapping"
    return "disjoint"


def freeze():
    base.check_freeze()
    target = OUT / "g20k5_freeze_manifest.json"
    if target.exists():
        raise FileExistsError(target)
    allowed, pairs = catalogue()
    if len(pairs) != 5:
        raise ValueError("Catalogue type count drift")
    payload = {
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "B1_3935_resolved_component_profiles",
        "code_set_unit": "distinct_catalogue_type_group_code_pairs",
        "precedence": list(CLASSES),
        "comparable_turbine_profile": "PMMUWW",
        "missing_turbine_profile_policy": "not_comparable_not_zero",
        "crosswalk_role": "deterministic_consistency_not_ground_truth",
        "threshold_unchanged": base.THRESHOLD, "margin_unchanged": base.MIN_MARGIN,
        "no_scoring": True, "no_promotion": True, "results_seen": False,
        "source_sha256": {str(p.relative_to(base.ROOT)): base.sha(p) for p in INPUTS},
    }
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n",
                      encoding="utf-8")


def verify():
    base.check_freeze()
    frozen = json.loads((OUT / "g20k5_freeze_manifest.json").read_text())
    if frozen["precedence"] != list(CLASSES) or frozen["threshold_unchanged"] != base.THRESHOLD or frozen["margin_unchanged"] != base.MIN_MARGIN:
        raise ValueError("Frozen policy drift")
    for rel, digest in frozen["source_sha256"].items():
        if base.sha(base.ROOT / rel) != digest:
            raise ValueError("Input changed after freeze: " + rel)


def resolved_profiles():
    base_rows = {r["order_id_hash"]: r for r in read_csv(CONSENSUS)}
    expansion = {r["order_id_hash"]: r for r in read_csv(EXPANSION)}
    if len(base_rows) != 10749 or len(expansion) != 459:
        raise ValueError("Profile source counts drift")
    profiles = {}
    for key, row in base_rows.items():
        if row["profile_status"].startswith("resolved"):
            profiles[key] = row["resolved_rbnr"]
    if len(profiles) != 3934 or any(not x for x in profiles.values()):
        raise ValueError("G2.0i persisted profile count drift")
    added = 0
    for key, row in expansion.items():
        if row["expanded_profile_status"].startswith("resolved"):
            if key in profiles or not row["expanded_profile_rbnr"]:
                raise ValueError("G2.0k.2 profile duplicate or missing")
            profiles[key] = row["expanded_profile_rbnr"]
            added += 1
    if added != 1 or len(profiles) != 3935:
        raise ValueError("G2.0k.2 profile count drift")
    return profiles


def strong_crosswalk():
    rows = read_csv(CROSSWALK)
    by_item = {r["source_item_concept_key"]: r for r in rows}
    if len(by_item) != 708:
        raise ValueError("G1.1 crosswalk concept count drift")
    by_order = defaultdict(set)
    for item in read_csv(ITEMS):
        entry = by_item[item["source_item_concept_key"]]
        if entry["crosswalk_status"] == "auto_candidate_strong":
            by_order[item["order_id_hash"]].add(
                (entry["catalog_b_code_group"], entry["catalog_b_code"])
            )
    if len(by_order) != 3013 or any(not codes for codes in by_order.values()):
        raise ValueError("G1.1 strong-order count drift")
    return by_order


def carryover(nodes, valid, allowed, pairs, g12):
    rows = read_csv(K4)
    if len(rows) != 2238:
        raise ValueError("G2.0k.4 tie count drift")
    siblings = [r for r in rows if r["structural_category"] == "siblings"]
    identical = sum(r["identical_ih06_descriptions"].lower() == "true" for r in siblings)
    by_hash = {base.short_hash("IH06NODE", node): node for node in nodes}
    by_order = {r["order_id_hash"]: r for r in g12}
    counts = Counter()
    for row in rows:
        if row["lca_direct_valid_rbnr"].lower() != "true":
            continue
        node = by_hash[row["lca_node_hash"]]
        lca = nodes[node]["profile"]
        root = by_order[row["order_id_hash"]]["matched_floc"]
        turbine, _, _ = base.effective_profile(root, nodes, valid)
        for typ, target in TYPES.items():
            if not turbine:
                relation = "turbine_profile_missing"
            elif lca == turbine:
                relation = "same_rbnr"
            elif len(code_set(lca, typ, allowed, pairs)) == len(code_set(turbine, typ, allowed, pairs)):
                relation = "different_rbnr_same_code_count"
            else:
                relation = "different_rbnr_different_code_count"
            counts[(target, relation)] += 1
    if sum(counts[("Symptom", c)] for c in (
        "turbine_profile_missing", "same_rbnr",
        "different_rbnr_same_code_count", "different_rbnr_different_code_count")) != 2201:
        raise ValueError("LCA carryover count drift")
    return len(siblings), identical, counts


def run():
    verify()
    if (OUT / "g20k5_run_manifest.json").exists():
        raise FileExistsError("G2.0k.5 already run")
    profiles = resolved_profiles()
    nodes, _ = base.load_nodes()
    valid, _, _ = base.load_catalog()
    allowed, pairs = catalogue()
    g12 = base.read_g12()
    source_by_order = {r["order_id_hash"]: r for r in g12}
    identity = Counter()
    component_counts = Counter(profiles.values())
    comparable = {}
    missing = {}
    for key, component in profiles.items():
        source = source_by_order[key]
        if source["match_status"] != "matched_asset_node":
            raise ValueError("Resolved component without turbine root")
        turbine, _, _ = base.effective_profile(source["matched_floc"], nodes, valid)
        if not turbine:
            identity["turbine_profile_missing"] += 1
            missing[key] = component
        elif component == turbine:
            identity["same_rbnr"] += 1
            comparable[key] = (component, turbine)
        else:
            identity["different_rbnr"] += 1
            comparable[key] = (component, turbine)
        if turbine and turbine != "PMMUWW":
            raise ValueError("Comparable resolved order has unexpected turbine profile")
    if sum(identity.values()) != 3935 or len(comparable) != 3267 or len(missing) != 668:
        raise ValueError(f"Profile identity arithmetic: {identity}")
    strong = strong_crosswalk()
    if any(code not in pairs["B"] for codes in strong.values() for code in codes):
        raise ValueError("Strong crosswalk contains group+code absent from catalogue B")

    comparison = Counter()
    order_counts, private_detail = [], []
    differences = defaultdict(list)
    for key, (component, turbine) in comparable.items():
        if component == turbine:
            continue
        for typ, target in TYPES.items():
            cset = code_set(component, typ, allowed, pairs)
            tset = code_set(turbine, typ, allowed, pairs)
            category = classify(cset, tset)
            comparison[(target, category)] += 1
            added, removed = cset - tset, tset - cset
            differences[target].append((len(added), len(removed)))
            order_counts.append({
                "order_id_hash": key, "target": target, "category": category,
                "component_code_pair_count": len(cset),
                "turbine_code_pair_count": len(tset),
                "added_pairs": len(added), "removed_pairs": len(removed),
                "raw_operational_values_emitted": False,
            })
            private_detail.append({
                "order_id_hash": key, "catalogue_type": typ,
                "component_rbnr": component, "turbine_rbnr": turbine,
                "component_group_code_pairs": "|".join(sorted(g + ":" + c for g, c in cset)),
                "turbine_group_code_pairs": "|".join(sorted(g + ":" + c for g, c in tset)),
                "added_group_code_pairs": "|".join(sorted(g + ":" + c for g, c in added)),
                "removed_group_code_pairs": "|".join(sorted(g + ":" + c for g, c in removed)),
            })
    for target in TYPES.values():
        if sum(comparison[(target, c)] for c in CLASSES) != identity["different_rbnr"]:
            raise ValueError("Six-class sum drift: " + target)

    missing_summary = []
    for typ, target in TYPES.items():
        sizes = [len(code_set(component, typ, allowed, pairs)) for component in missing.values()]
        missing_summary.append({
            "target": target, "orders_without_turbine_profile": len(sizes),
            "component_enabled_pairs_median": float(np.median(sizes)),
            "component_enabled_pairs_max": max(sizes),
            "full_catalogue_group_code_pairs": len(pairs[typ]),
            "interpretation": "component_profile_obtained_from_previously_unfiltered_order_not_accuracy",
        })

    consistency = Counter()
    consistency_by_order = []
    overlap = sorted(set(profiles) & set(strong))
    for key in overlap:
        component = profiles[key]
        source = source_by_order[key]
        turbine, _, _ = base.effective_profile(source["matched_floc"], nodes, valid)
        cset = code_set(component, "B", allowed, pairs)
        tset = code_set(turbine, "B", allowed, pairs) if turbine else set()
        component_members = turbine_members = 0
        for code in strong[key]:
            c, t = code in cset, code in tset if turbine else None
            component_members += int(c)
            turbine_members += int(bool(t))
            relation = ("both" if c and t else "component_only" if c else
                        "turbine_only" if t else "neither") if turbine else (
                        "component_only_turbine_not_comparable" if c else
                        "component_absent_turbine_not_comparable")
            consistency[relation] += 1
        consistency_by_order.append({
            "order_id_hash": key,
            "strong_group_code_pairs": len(strong[key]),
            "pairs_in_component_profile": component_members,
            "pairs_in_turbine_profile": turbine_members if turbine else "",
            "turbine_profile_status": "valid" if turbine else "no_profile_no_filter",
            "any_pair_in_component_profile": component_members > 0,
            "any_pair_in_turbine_profile": turbine_members > 0 if turbine else "",
            "raw_operational_values_emitted": False,
        })
    if sum(consistency.values()) != sum(len(strong[key]) for key in overlap):
        raise ValueError("Crosswalk pair count drift")

    siblings, identical_siblings, lca = carryover(
        nodes, valid, allowed, pairs, g12
    )
    identity_rows = [{"category": c, "orders": identity[c],
                      "resolved_total": 3935, "sum_valid": True}
                     for c in IDENTITY]
    comparison_rows = [{
        "target": target, "category": category,
        "orders": comparison[(target, category)],
        "different_rbnr_comparable_orders": identity["different_rbnr"],
        "sum_valid": True,
    } for target in TYPES.values() for category in CLASSES]
    difference_rows = []
    for target in TYPES.values():
        values = differences[target]
        difference_rows.append({
            "target": target, "orders": len(values),
            "added_median": float(np.median([a for a, _ in values])) if values else "",
            "added_max": max((a for a, _ in values), default=""),
            "removed_median": float(np.median([b for _, b in values])) if values else "",
            "removed_max": max((b for _, b in values), default=""),
        })
    consistency_rows = [{
        "category": category, "order_code_pairs": consistency[category],
        "resolved_orders_with_strong_crosswalk": len(overlap),
    } for category in (
        "both", "component_only", "turbine_only", "neither",
        "component_only_turbine_not_comparable",
        "component_absent_turbine_not_comparable")]
    lca_rows = [{
        "target": target, "relation": relation, "orders": lca[(target, relation)],
        "lca_direct_profiled_tie_sets": 2201,
    } for target in TYPES.values() for relation in (
        "turbine_profile_missing", "same_rbnr",
        "different_rbnr_same_code_count", "different_rbnr_different_code_count")]
    outputs = {
        "g20k5_profile_identity_sanitized.csv": identity_rows,
        "g20k5_codeset_comparison_sanitized.csv": comparison_rows,
        "g20k5_codeset_order_counts_sanitized.csv": order_counts,
        "g20k5_added_removed_distribution_sanitized.csv": difference_rows,
        "g20k5_missing_turbine_profile_sanitized.csv": missing_summary,
        "g20k5_object_part_consistency_sanitized.csv": consistency_rows,
        "g20k5_object_part_consistency_by_order_sanitized.csv": consistency_by_order,
        "g20k5_object_part_consistency_orders_summary_sanitized.csv": [
            {"category": category, "orders": count, "resolved_strong_overlap_orders": len(overlap)}
            for category, count in (
                ("any_pair_in_component_profile", sum(r["any_pair_in_component_profile"] for r in consistency_by_order)),
                ("no_pair_in_component_profile", sum(not r["any_pair_in_component_profile"] for r in consistency_by_order)),
                ("turbine_profile_missing", sum(r["turbine_profile_status"] != "valid" for r in consistency_by_order)),
            )
        ],
        "g20k5_lca_carryover_sanitized.csv": lca_rows,
    }
    if any((OUT / name).exists() for name in outputs):
        raise FileExistsError("G2.0k.5 outputs already exist")
    PRIVATE.mkdir(parents=True, exist_ok=True)
    os.chmod(PRIVATE, 0o700)
    private_file = PRIVATE / "g20k5_codeset_detail.csv"
    if private_file.exists():
        raise FileExistsError(private_file)
    with private_file.open("x", newline="", encoding="utf-8") as handle:
        os.chmod(private_file, 0o600)
        writer = csv.DictWriter(handle, fieldnames=list(private_detail[0]))
        writer.writeheader()
        writer.writerows(private_detail)
    if len(read_csv(private_file)) != len(private_detail):
        raise ValueError("Private detail round-trip drift")
    for name, rows in outputs.items():
        if not rows:
            raise ValueError("Empty output: " + name)
        base.write_csv(OUT / name, rows, list(rows[0]))
    top5 = sum(n for _, n in component_counts.most_common(5)) / 3935
    memo = [
        "# G2.0k.5 - component vs turbine catalogue profiles",
        "",
        "P1 confirmed: 2,400 original resolved-node RBNRs plus 1,534 profile-consensus RBNRs in g20i_profile_consensus_by_order_sanitized.csv, and one G2.0k.2 expanded_profile_rbnr in g20k_expansion_affected_orders_sanitized.csv. No replay needed.",
        "P2 confirmed with missingness: G1.2 turbine FLOC and IH06 nearest-valid-ancestor profile; 3,267 PMMUWW, 668 no_profile_no_filter.",
        "P3 confirmed: all S/B/C/5/A catalogue types and profile associations in Wind Catalog Group and Codes Final v4.xlsx (g20i_component_resolution.py:99-117).",
        "P4 confirmed: distinct catalogue type+group+code pair. Code alone is not a unique class.",
        "P5 confirmed: 3,013 strong G1.1 orders; crosswalk supplies Catalog B group+code pairs, matching P4. It is algorithmic consistency, not independent correctness.",
        "",
        f"Identity: {dict(identity)}. Distinct component RBNRs: {len(component_counts)}. Top-five share: {top5:.4f}.",
        "The 668 missing-turbine-profile orders gained a component profile from an otherwise unfiltered catalogue space. Per-target median and max enabled pair counts are separate from the 3,267 comparison; no silent zero.",
        f"Different-RBNR comparable orders: {identity['different_rbnr']}. Six-class counts by target and added/removed pair distributions are in sanitized outputs.",
        f"Strong crosswalk overlap with resolved orders: {len(overlap)} orders, {sum(consistency.values())} order-code pairs. Membership is not precision.",
        f"G2.0k.4 carry-over: {identical_siblings} of {siblings} tied-sibling orders have an identical IH06 description. LCA-vs-turbine RBNR/count categories are in g20k5_lca_carryover_sanitized.csv.",
        "The earlier 1,548-order no-profile status table is not edited in this diagnostic. Its later update must account for these 668 resolved-component cases.",
        "No new resolution, no scoring, no candidate promotion, no F6 update.",
    ]
    (OUT / "g20k5_memo.md").write_text("\n\n".join(memo) + "\n", encoding="utf-8")
    manifest = {
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "freeze_sha256": base.sha(OUT / "g20k5_freeze_manifest.json"),
        "private_detail_sha256": base.sha(private_file),
        "private_file_mode": oct(private_file.stat().st_mode & 0o777),
        "private_directory_mode": oct(PRIVATE.stat().st_mode & 0o777),
        "identity_counts": dict(identity),
        "different_rbnr_comparable": identity["different_rbnr"],
        "strong_overlap_orders": len(overlap),
        "output_sha256": {p.name: base.sha(p) for p in OUT.glob("g20k5_*")
                          if p.name != "g20k5_run_manifest.json"},
        "denominator_changed": False, "promotion": False,
    }
    (OUT / "g20k5_run_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"identity": dict(identity), "different_rbnr": identity["different_rbnr"],
                      "distinct_component_profiles": len(component_counts),
                      "top5_share": top5,
                      "strong_overlap_orders": len(overlap)}, indent=2, sort_keys=True))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("freeze", "run"))
    args = parser.parse_args()
    freeze() if args.mode == "freeze" else run()
