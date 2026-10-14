"""G1.1f diagnostic replay with turbine-subtree profile restrictions."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "g1_actionable_zeros/g11_object_part_crosswalk/scripts"))
sys.path.insert(0, str(ROOT / "g2_baseline_models/scripts"))

import g11_material_to_catalog_b_crosswalk as g11
import g20i_component_resolution as base
import g20k5_component_profile_comparison as k5
import g20k6_semantic_crosswalk_membership as k6
import g20k7_crosswalk_implied_component as k7

OUT = ROOT / "g1_actionable_zeros/g11_object_part_crosswalk/outputs/g11f_profile_constrained"
PRIVATE = ROOT / "g1_actionable_zeros/g11_object_part_crosswalk/internal/g11f_profile_constrained"
CLASSES = (
    "no_turbine_subtree", "original_code_available", "exact_equivalent",
    "restricted_strong", "restricted_medium_weak",
    "no_enabled_codes_under_subtree", "enabled_codes_no_score",
)
G11_CROSSWALK = g11.OUT / "g11_material_to_catalog_b_crosswalk_sanitized.csv"
G11_ITEMS = g11.OUT / "g11_item_signal_rows_sanitized.csv"
G11_INTERNAL = g11.INTERNAL_OUT / "g11_material_to_catalog_b_crosswalk_internal_review.csv"


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def normalized_description(value):
    return re.sub(r"\s+", " ", str(value).strip().lower())


def write_csv(path, rows, fields, private=False):
    if private:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        handle = os.fdopen(descriptor, "w", newline="", encoding="utf-8")
    else:
        handle = path.open("x", newline="", encoding="utf-8")
    with handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)
    if len(read_csv(path)) != len(rows):
        raise ValueError(f"CSV round-trip mismatch: {path}")


def main():
    targets = [
        OUT / "g11f_pair_categories_sanitized.csv",
        OUT / "g11f_order_categories_sanitized.csv",
        OUT / "g11f_component_byproduct_sanitized.csv",
        OUT / "g11f_memo.md",
        OUT / "g11f_run_manifest.json",
        PRIVATE / "g11f_detail.csv",
        PRIVATE / "g11f_sample_30.csv",
    ]
    if any(path.exists() for path in targets):
        raise FileExistsError("G1.1f outputs already exist")

    # F1-F4: use the frozen scorer and reconstruct the profile -> group -> code chain.
    k5.verify()
    catalog = g11.read_catalog_b()
    allowed, descriptions, _ = k6.catalog_with_descriptions()
    catalog_by_pair = {(row["Code Group"], row["Code"]): row for row in catalog}
    if len(catalog) != 1240 or len(catalog_by_pair) != len(catalog):
        raise ValueError("Catalog B pair count drift")
    enabled_by_profile = defaultdict(set)
    for (profile, typ), groups in allowed.items():
        if typ == "B":
            enabled_by_profile[profile] = {
                pair for pair in catalog_by_pair if pair[0] in groups
            }
    expected, membership = k7.completed_enablers()
    if len(expected) != 5778 or tuple(membership[c] for c in
            ("in_pmmuww", "in_component_profile", "in_other_profile")) != (0, 11, 5767):
        raise ValueError("F4 membership count mismatch")
    for row in expected:
        pair = (row["group"], row["code"])
        actual = {p for p, codes in enabled_by_profile.items() if pair in codes}
        if actual != k7.split_pipes(row["enabling_rbnrs"]):
            raise ValueError("F4 rebuilt enabling set differs from G2.0k.7")

    # F6: independent unrestricted replay of all 708 concept choices and pairs.
    saved = {r["source_item_concept_key"]: r for r in read_csv(G11_CROSSWALK)}
    visible = {r["source_item_concept_key"]: r for r in read_csv(G11_INTERNAL)}
    if len(saved) != len(visible) or len(saved) != 708:
        raise ValueError("F6 concept count drift")
    scored = {}
    for concept, original in saved.items():
        material = visible[concept]["item_description"]
        candidates = sorted(
            ((g11.score_candidate(material, row["Short Text for Code"]),
              row["Code Group"], row["Code"]) for row in catalog),
            key=lambda item: (-item[0], item[1], item[2]),
        )
        best = candidates[0]
        status = g11.status_for_score(best[0])
        chosen = best[1:] if best[0] > 0 else ("", "")
        if (chosen != (original["catalog_b_code_group"], original["catalog_b_code"])
                or status != original["crosswalk_status"]
                or float(original["match_score"]) != best[0]):
            raise ValueError(f"F6 concept replay mismatch: {concept}")
        scored[concept] = candidates
    by_pair_concepts = defaultdict(set)
    for item in read_csv(G11_ITEMS):
        concept = item["source_item_concept_key"]
        original = saved[concept]
        if original["crosswalk_status"] == "auto_candidate_strong":
            pair = (original["catalog_b_code_group"], original["catalog_b_code"])
            by_pair_concepts[(item["order_id_hash"], pair)].add(concept)
    prior_pairs = {(r["order_id_hash"], (r["group"], r["code"])) for r in expected}
    if len(by_pair_concepts) != 5778 or set(by_pair_concepts) != prior_pairs:
        raise ValueError("F6 5,778-pair replay mismatch")
    multi_concept_pairs = sum(len(v) > 1 for v in by_pair_concepts.values())

    # F5: replicate G2.0k.7's reachable, site-aware turbine subtree.
    source = {r["order_id_hash"]: r for r in base.read_g12()}
    nodes, children = base.load_nodes()
    valid, _, _ = base.load_catalog()
    profiles = k5.resolved_profiles()
    old_detail = {(r["order_id_hash"], (r["crosswalk_group"], r["crosswalk_code"])): r
                  for r in read_csv(k7.DETAIL)}
    if len(old_detail) != 5778:
        raise ValueError("G2.0k.7 detail count drift")
    subtree_cache = {}
    pair_counts = Counter()
    order_counts = Counter()
    implied_none_counts = Counter()
    byproduct = Counter()
    byproduct_orders = Counter()
    detail = []
    by_order = defaultdict(list)
    for order, pair in sorted(by_pair_concepts):
        src = source[order]
        root = src["matched_floc"] if src["match_status"] == "matched_asset_node" else ""
        if root and root not in nodes:
            raise ValueError("Matched turbine absent from IH06")
        if root and root not in subtree_cache:
            effective = {}
            for node in base.descendants_of(root, children):
                if not node.startswith(root + "-") or node.split("-")[0] != root.split("-")[0]:
                    raise ValueError("F5 subtree escaped site/turbine")
                if not k7.ancestor_path(node, root, nodes):
                    raise ValueError("F5 incomplete IH06 path")
                profile, _, _ = base.effective_profile(node, nodes, valid)
                if profile:
                    effective[node] = profile
            subtree_cache[root] = effective
        effective = subtree_cache.get(root, {})
        enabled = set().union(*(enabled_by_profile[p] for p in set(effective.values()))) if effective else set()
        old = old_detail[(order, pair)]
        old_available = bool(old["implied_nodes"])
        if old_available != (pair in enabled):
            raise ValueError("F5 original-code availability differs from G2.0k.7")

        original_desc = catalog_by_pair[pair]["Short Text for Code"]
        candidates = []
        for concept in sorted(by_pair_concepts[(order, pair)]):
            material = visible[concept]["item_description"]
            best_restricted = next((item for item in scored[concept] if item[1:] in enabled), None)
            exact = [item for item in scored[concept]
                     if item[1:] in enabled and normalized_description(
                         catalog_by_pair[item[1:]]["Short Text for Code"]
                     ) == normalized_description(original_desc) and item[1:] != pair]
            if not root:
                category, selected = "no_turbine_subtree", None
            elif pair in enabled:
                category, selected = "original_code_available", scored[concept][0]
            elif exact:
                category, selected = "exact_equivalent", exact[0]
            elif best_restricted and best_restricted[0] >= 0.85:
                category, selected = "restricted_strong", best_restricted
            elif best_restricted and best_restricted[0] > 0:
                category, selected = "restricted_medium_weak", best_restricted
            elif not enabled:
                category, selected = "no_enabled_codes_under_subtree", None
            else:
                category, selected = "enabled_codes_no_score", best_restricted
            candidates.append((CLASSES.index(category), concept, category, selected, material))
        _, concept, category, selected, material = min(candidates, key=lambda x: (x[0], x[1]))
        pair_counts[category] += 1
        by_order[order].append(category)
        selected_pair = selected[1:] if selected else ("", "")
        selected_desc = catalog_by_pair[selected_pair]["Short Text for Code"] if selected_pair in catalog_by_pair else ""
        implied = {node for node, profile in effective.items()
                   if selected_pair and selected_pair in enabled_by_profile[profile]}
        if category in ("exact_equivalent", "restricted_strong", "restricted_medium_weak"):
            if not implied:
                raise ValueError("Restricted candidate has no implied node")
            if len(implied) == 1:
                node_class = "single_node"
            elif len({effective[n] for n in implied}) == 1:
                node_class = "multi_node_one_rbnr"
            else:
                node_class = "multi_rbnr"
            agreement = ("same_rbnr" if profiles.get(order) in {effective[n] for n in implied}
                         else "different_rbnr") if order in profiles else "no_g20i_profile"
            byproduct[(category, node_class, agreement)] += 1
        else:
            node_class, agreement = "", ""
        detail.append({
            "order_id_hash": order, "original_group": pair[0], "original_code": pair[1],
            "material_concept_count": len(by_pair_concepts[(order, pair)]),
            "material_concepts": "|".join(sorted(by_pair_concepts[(order, pair)])),
            "representative_concept": concept, "material_description": material,
            "original_description": original_desc, "selected_group": selected_pair[0],
            "selected_code": selected_pair[1], "selected_description": selected_desc,
            "selected_score": selected[0] if selected else "", "category": category,
            "implied_node_count": len(implied), "implied_rbnr_count": len({effective[n] for n in implied}),
            "node_class": node_class, "g20i_profile_agreement": agreement,
            "prior_order_category": old["order_category"],
        })

    if sum(pair_counts.values()) != 5778 or len(by_order) != 3013:
        raise ValueError("Pair/order population drift")
    prior_category_by_order = {}
    for row in detail:
        order = row["order_id_hash"]
        previous = prior_category_by_order.setdefault(order, row["prior_order_category"])
        if previous != row["prior_order_category"]:
            raise ValueError("G2.0k.7 order category differs among its pairs")
    for order, categories in by_order.items():
        chosen = min(categories, key=CLASSES.index)
        order_counts[chosen] += 1
        if prior_category_by_order[order] == "implied_none":
            implied_none_counts[chosen] += 1
    mixed = sum(len(set(categories)) > 1 for categories in by_order.values())
    mixed_implied_none = sum(len(set(categories)) > 1 for order, categories in by_order.items()
                             if prior_category_by_order[order] == "implied_none")
    detail_by_order = defaultdict(list)
    for row in detail:
        detail_by_order[row["order_id_hash"]].append(row)
    for order, rows in detail_by_order.items():
        relevant = [row for row in rows if row["node_class"]]
        if relevant:
            selected = min(relevant, key=lambda row: CLASSES.index(row["category"]))
            byproduct_orders[(selected["category"], selected["node_class"],
                              selected["g20i_profile_agreement"])] += 1
    if (pair_counts["original_code_available"] != 1459 or
            order_counts["original_code_available"] != 1207 or
            sum(order_counts.values()) != 3013 or
            sum(implied_none_counts.values()) != 1804):
        raise ValueError("G1.1f control count mismatch")

    # Produce a deterministic diagnostic sample with separate 6a/6b strata.
    sample_pool = defaultdict(list)
    for row in detail:
        if row["prior_order_category"] == "implied_none" and row["category"] in CLASSES[2:]:
            sample_pool[row["category"]].append(row)
    for rows in sample_pool.values():
        rows.sort(key=lambda r: hashlib.sha256(
            f"g11f-sample|{r['order_id_hash']}|{r['original_group']}|{r['original_code']}".encode()
        ).hexdigest())
    sample = []
    strata = [c for c in CLASSES[2:] if sample_pool[c]]
    while len(sample) < 30 and any(sample_pool[c] for c in strata):
        for category in strata:
            if len(sample) == 30:
                break
            if sample_pool[category]:
                sample.append(sample_pool[category].pop(0))
    if len(sample) != 30:
        raise ValueError("Insufficient pairs for 30-row sample")

    # Nothing is written until all gates and sum checks have passed.
    OUT.mkdir(parents=True, exist_ok=True)
    PRIVATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    if PRIVATE.stat().st_mode & 0o777 != 0o700:
        raise PermissionError("Private directory must be 700")
    write_csv(targets[0], [{"category": c, "pairs": pair_counts[c], "denominator": 5778}
                           for c in CLASSES], ["category", "pairs", "denominator"])
    write_csv(targets[1], [{"population": p, "category": c, "orders": counts[c],
                            "denominator": n, "mixed_category_orders": mixed_count}
                           for p, counts, n, mixed_count in (("full", order_counts, 3013, mixed),
                                                ("prior_implied_none", implied_none_counts, 1804, mixed_implied_none))
                           for c in CLASSES],
              ["population", "category", "orders", "denominator", "mixed_category_orders"])
    write_csv(targets[2], [{"unit": unit, "pair_category": c, "node_class": node,
                            "g20i_profile_agreement": a, "count": count}
                           for unit, source_counts in (("pair", byproduct), ("order", byproduct_orders))
                           for (c, node, a), count in sorted(source_counts.items())],
              ["unit", "pair_category", "node_class", "g20i_profile_agreement", "count"])
    detail_fields = list(detail[0])
    write_csv(targets[5], detail, detail_fields, private=True)
    write_csv(targets[6], sample, detail_fields, private=True)
    memo = [
        "# G1.1f — Profile-constrained crosswalk diagnostic", "",
        "B1 only. No code assignment, candidate promotion or F6 change.", "",
        "## Pre-flight", "",
        "- F1 confirmed: G1.1 compares consumed `items[].itemDescription` to Catalog B `Short Text for Code` by token-overlap score with head/subset bonuses; no embeddings or group-description matching.",
        "- F2 confirmed: absolute score only; strong >= 0.85, medium >= 0.55, weak > 0. No second-best margin.",
        "- F3 confirmed: 5,778 distinct order x (Catalog B group, code) pairs from 3,013 orders; concepts are retained beneath each pair.",
        f"- F3 multi-concept pairs: {multi_concept_pairs}.",
        "- F4 confirmed: complete enabled Catalog B pair sets rebuilt through profile -> type B -> group -> code; G2.0k.6 membership 0 / 11 / 5,767 and G2.0k.7 enabling sets reproduced.",
        "- F5 confirmed: reachable IH06 subtree via Superior functional location; inherited nearest-valid RBNR; turbine profile included, with site/turbine boundary assertions.",
        "- F6 confirmed: unrestricted G1.1 code, score and tier replay identical for all 708 concepts and 5,778 pairs.",
        "", "## Controls", "",
        "- Original code available: 1,459 pairs and 1,207 orders, as in G2.0k.7.",
        f"- Mixed-category orders: {mixed} of 3,013.",
        f"- Mixed-category orders in the prior implied-none subset: {mixed_implied_none} of 1,804.",
        "- The prior `implied_none` subset has exactly 1,804 orders and is reported separately.",
        "- Category 6a is structural absence of enabled Catalog B codes under the subtree. Category 6b is a zero lexical score despite enabled codes; it does not establish a client-configuration gap.",
        "- Exact normalized descriptions support a lexical equivalence only; restricted strong matches remain unvalidated candidate matches, not precision estimates.",
        "- Pair categories follow the highest-precedence outcome among source material concepts; order categories follow the highest-precedence pair.",
        "- The 30-pair sample is diagnostic, private, and stratified across categories 3, 4, 5, 6a, and 6b where present.",
        "", "## Counts", "",
        "| Category | Pairs | Orders | Prior implied-none orders |", "|---|---:|---:|---:|",
    ]
    for category in CLASSES:
        memo.append(f"| {category} | {pair_counts[category]} | {order_counts[category]} | {implied_none_counts[category]} |")
    targets[3].write_text("\n".join(memo) + "\n", encoding="utf-8")
    manifest = {
        "run_at_utc": datetime.now(timezone.utc).isoformat(),
        "method": "g11_lexical_unchanged_profile_restricted_diagnostic",
        "pair_count": 5778, "order_count": 3013, "prior_implied_none_orders": 1804,
        "sample_pairs": 30, "multi_concept_pairs": multi_concept_pairs,
        "mixed_category_orders": mixed, "mixed_prior_implied_none_orders": mixed_implied_none,
        "controls": {"f4_membership": [0, 11, 5767], "f6_concepts": 708,
                     "original_code_available_pairs": 1459,
                     "original_code_available_orders": 1207},
        "input_sha256": {str(path): base.sha(path) for path in
                         (G11_CROSSWALK, G11_ITEMS, G11_INTERNAL, k7.COMPLETE,
                          k7.DETAIL, base.SOURCES[0], base.SOURCES[2])},
    }
    targets[4].write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"pair_categories": dict(pair_counts), "order_categories": dict(order_counts),
                      "prior_implied_none": dict(implied_none_counts),
                      "multi_concept_pairs": multi_concept_pairs, "mixed_orders": mixed,
                      "mixed_prior_implied_none_orders": mixed_implied_none}, sort_keys=True))


if __name__ == "__main__":
    main()
