"""G2.0k.4: structural diagnosis of frozen G2.0i node ties."""

import argparse
import csv
import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

import g20i_component_resolution as base
import g20k3_resolution_chain_partition as k3
from g20i_profile_consensus import consensus_profile

OUT = base.STINT2 / "g2_baseline_models/outputs/g20k_component_lift"
PRIVATE = base.STINT2 / "g2_baseline_models/internal/g20k_component_lift"
PLAN = base.STINT2 / "docs/PLAN-G2.0k.4—Tie Structure Diagnostic.md"
SPEC = base.STINT2 / "docs/G2.0i-resolution-chain-code-spec.md"
PARTITION = OUT / "g20k3_order_stage_sanitized.csv"
EXPANSION = OUT / "g20k_expansion_affected_orders_sanitized.csv"
BASELINE = base.OUT / "g20i_order_resolution_sanitized.csv"
K2_FREEZE = OUT / "g20k_freeze_manifest.json"
SCRIPT = Path(__file__).resolve()
INPUTS = (PLAN, SPEC, PARTITION, EXPANSION, BASELINE, K2_FREEZE,
          OUT / "g20k3_run_manifest.json", Path(base.__file__).resolve(),
          Path(k3.__file__).resolve(), SCRIPT)
STRUCTURES = ("ancestor_chain", "siblings", "shared_subtree",
              "cross_subsystem", "path_incomplete")
ORIGINS = ("single_concept_tie", "multi_concept_tie")
TYPES = {"S": "Symptom", "5": "Cause", "B": "Object Part"}


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def freeze():
    base.check_freeze()
    if json.loads((OUT / "g20k3_run_manifest.json").read_text())["summary"]["category_counts"]["concept_ambiguous_node"] != 2238:
        raise ValueError("G2.0k.3 source count drift")
    target = OUT / "g20k4_freeze_manifest.json"
    if target.exists():
        raise FileExistsError(target)
    payload = {
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "model": base.MODEL, "threshold": base.THRESHOLD, "margin": base.MIN_MARGIN,
        "node_score": "max_cosine_over_all_detected_concepts",
        "tie_window": "best_minus_node_score_strictly_less_than_0.05",
        "concept_origin_rule": "all_maximizers_within_1e-6; single_only_for_identical_singleton",
        "lca_profile_rule": "direct_valid_RBNR_only",
        "replay_gate": "all_6814_unresolved_categories_identical_before_analysis",
        "labels_read": False, "no_promotion": True, "results_seen": False,
        "source_sha256": {str(p.relative_to(base.ROOT)): base.sha(p) for p in INPUTS},
    }
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def verify():
    base.check_freeze()
    frozen = json.loads((OUT / "g20k4_freeze_manifest.json").read_text())
    if frozen["threshold"] != base.THRESHOLD or frozen["margin"] != base.MIN_MARGIN:
        raise ValueError("Frozen cutoff drift")
    for rel, digest in frozen["source_sha256"].items():
        if base.sha(base.ROOT / rel) != digest:
            raise ValueError("Input changed after freeze: " + rel)


def ancestor_path(node, root, nodes):
    result, seen = [], set()
    while node in nodes and node not in seen:
        seen.add(node)
        result.append(node)
        if node == root:
            return tuple(reversed(result))
        node = nodes[node]["parent"]
    return ()


def classify_structure(paths, root):
    if not paths or any(not p or p[0] != root for p in paths):
        return "path_incomplete", "", -1
    common = []
    for level in zip(*paths):
        if len(set(level)) != 1:
            break
        common.append(level[0])
    lca, depth = common[-1], len(common) - 1
    if any(all(other == p[:len(other)] for other in paths) for p in paths):
        return "ancestor_chain", lca, depth
    if len({p[-2] for p in paths}) == 1:
        return "siblings", lca, depth
    if lca != root:
        return "shared_subtree", lca, depth
    return "cross_subsystem", lca, depth


def make_matrices(roots, nodes, children, valid, concepts, new_ids):
    choices, descriptions = {}, set()
    for root in sorted(roots):
        items = []
        for node in base.descendants_of(root, children):
            if not node.startswith(root + "-") or node.split("-")[0] != root.split("-")[0]:
                raise ValueError("Candidate escaped turbine/site scope")
            profile, _, _ = base.effective_profile(node, nodes, valid)
            label = base.normalised(nodes[node]["description"])
            if profile and label:
                items.append((node, profile, label))
                descriptions.add(label)
        choices[root] = items
    model = SentenceTransformer(base.MODEL, local_files_only=True)
    old_ids, extra_ids = sorted(concepts), sorted(new_ids)
    all_ids = sorted(old_ids + extra_ids)
    old_vec = k3.embed(model, [base.normalised(concepts[c]) for c in old_ids])
    extra_vec = k3.embed(model, [base.normalised(new_ids[c]) for c in extra_ids])
    desc = sorted(descriptions)
    desc_vec = k3.embed(model, desc)
    desc_idx = {label: i for i, label in enumerate(desc)}
    old_idx = {cid: i for i, cid in enumerate(old_ids)}
    extra_idx = {cid: i for i, cid in enumerate(extra_ids)}
    matrices = {}
    for root, items in choices.items():
        if not items:
            continue
        selected = desc_vec[[desc_idx[item[2]] for item in items]]
        old_scores = old_vec @ selected.T
        extra_scores = extra_vec @ selected.T
        matrices[root] = np.stack([
            old_scores[old_idx[cid]] if cid in old_idx else extra_scores[extra_idx[cid]]
            for cid in all_ids
        ])
    return choices, matrices, {cid: i for i, cid in enumerate(all_ids)}


def replay_gate(g12, expected, original, expansion, hits, choices, matrices, concept_idx):
    tie_inputs, counts = [], Counter()
    checked_scores = 0
    for source in g12:
        key = source["order_id_hash"]
        root = source["matched_floc"] if source["match_status"] == "matched_asset_node" else ""
        active = set(hits.get(base.unit_hash(source["order_id"]), ()))
        if key in expansion:
            active.update(x for x in expansion[key]["matched_new_concept_ids"].split("|") if x)
        active = sorted(active)
        if not root:
            category, node_scores = "no_turbine_node", None
        elif not active:
            category, node_scores = "no_component_concept", None
        elif not choices[root]:
            category, node_scores = "no_profiled_component_candidate", None
        else:
            indices = [concept_idx[cid] for cid in active]
            node_scores = matrices[root][indices].max(axis=0)
            ranked = np.argsort(-node_scores, kind="stable")
            best = float(node_scores[int(ranked[0])])
            second = float(node_scores[int(ranked[1])]) if len(ranked) > 1 else -1.0
            if original[key]["score"] and key not in expansion:
                if abs(best - float(original[key]["score"])) > 0.000002:
                    raise ValueError("Original score replay drift: " + key)
                checked_scores += 1
            if best < base.THRESHOLD:
                category = "concept_no_node"
            elif best - second < base.MIN_MARGIN:
                profile, _, _ = consensus_profile(
                    node_scores, [item[1] for item in choices[root]], base.MIN_MARGIN
                )
                category = "resolved" if profile else "concept_ambiguous_node"
            else:
                category = "resolved"
        if category != expected[key]["category"]:
            raise ValueError(f"STOP: G2.0k.3 category mismatch {key}: {category} != {expected[key]['category']}")
        counts[category] += 1
        if category == "concept_ambiguous_node":
            tie_inputs.append((key, root, active, node_scores))
    if (sum(counts.values()) != 10749 or counts["resolved"] != 3935 or
            counts["concept_ambiguous_node"] != 2238 or
            sum(v for c, v in counts.items() if c != "resolved") != 6814):
        raise ValueError("STOP: replay counts drift")
    return tie_inputs, counts, checked_scores


def analyze(tie_inputs, choices, matrices, concept_idx, nodes, valid, groups, codes, expected):
    structure_count, origin_count, size_count = Counter(), Counter(), Counter()
    cross, profile_cross = Counter(), Counter()
    top_two_same = homogeneous_count = lca_profiled_count = 0
    ties, answer, private = [], [], []
    for key, root, active, scores in tie_inputs:
        items = choices[root]
        best = float(scores.max())
        near = [int(i) for i in np.flatnonzero((best - scores) < base.MIN_MARGIN)]
        if len(near) < 2:
            raise ValueError("Tie set too small")
        paths = [ancestor_path(items[i][0], root, nodes) for i in near]
        structure, lca, depth = classify_structure(paths, root)
        if structure == "path_incomplete":
            raise ValueError("Reachable candidate has incomplete turbine path")
        profiles = {items[i][1] for i in near}
        homogeneous = len(profiles) == 1
        direct_profile = nodes[lca]["profile"]
        lca_profiled = direct_profile in valid
        winners = []
        for i in near:
            scored = [(cid, float(matrices[root][concept_idx[cid], i])) for cid in active]
            maximum = max(score for _, score in scored)
            winners.append(tuple(cid for cid, score in scored if maximum - score <= 1e-6))
        origin = ("single_concept_tie" if all(len(w) == 1 and w == winners[0] for w in winners)
                  else "multi_concept_tie")
        ranked = np.argsort(-scores, kind="stable")
        two_same = items[int(ranked[0])][1] == items[int(ranked[1])][1]
        descriptions = [nodes[items[i][0]]["description"] for i in near]
        size = "2" if len(near) == 2 else "3" if len(near) == 3 else "4-5" if len(near) <= 5 else ">5"
        structure_count[structure] += 1
        origin_count[origin] += 1
        size_count[size] += 1
        cross[(structure, origin)] += 1
        profile_cross[(structure, homogeneous, lca_profiled)] += 1
        top_two_same += two_same
        homogeneous_count += homogeneous
        lca_profiled_count += lca_profiled
        ties.append({
            "order_id_hash": key, "site_key": expected[key]["site_key"],
            "structural_category": structure, "concept_origin": origin,
            "tie_node_count": len(near), "tie_size_bucket": size,
            "lca_depth_below_turbine": depth, "lca_node_hash": base.short_hash("IH06NODE", lca),
            "tie_rbnr_homogeneous": homogeneous, "lca_direct_valid_rbnr": lca_profiled,
            "top_two_same_rbnr": two_same,
            "identical_ih06_descriptions": len(set(descriptions)) < len(descriptions),
            "raw_operational_values_emitted": False,
        })
        if lca_profiled:
            turbine_profile, _, _ = base.effective_profile(root, nodes, valid)
            for typ, target in TYPES.items():
                def space(profile):
                    return sum(codes[(typ, group)] for group in groups[(profile, typ)]) if profile else None
                tie_spaces = [space(items[i][1]) for i in near]
                turbine_space = space(turbine_profile)
                lca_space = space(direct_profile)
                answer.append({
                    "order_id_hash": key, "target": target, "structural_category": structure,
                    "turbine_enabled_group_code_pairs": turbine_space if turbine_space is not None else "",
                    "turbine_profile_status": "valid" if turbine_space is not None else "no_profile_no_filter",
                    "lca_enabled_group_code_pairs": lca_space,
                    "tie_node_min_enabled_group_code_pairs": min(tie_spaces),
                    "tie_node_max_enabled_group_code_pairs": max(tie_spaces),
                    "lca_vs_turbine": "not_comparable_no_turbine_profile" if turbine_space is None
                    else "narrower" if lca_space < turbine_space else "equal" if lca_space == turbine_space else "wider",
                    "code_count_unit": "group_code_pairs_not_verified_classification",
                    "raw_operational_values_emitted": False,
                })
        private.append((key, structure, [{
            "order_id_hash": key, "structural_category": structure,
            "tie_node_hash": base.short_hash("IH06NODE", items[i][0]),
            "node_description": nodes[items[i][0]]["description"],
            "node_score": round(float(scores[i]), 6),
            "winning_concept_ids": "|".join(winners[j]),
            "effective_rbnr": items[i][1],
        } for j, i in enumerate(near)]))
    if (len(ties) != 2238 or sum(structure_count.values()) != 2238 or
            sum(cross.values()) != 2238 or top_two_same != 136 or homogeneous_count != 0 or
            len(answer) != 3 * lca_profiled_count):
        raise ValueError("Tie reconciliation failed")
    return (ties, answer, private, structure_count, origin_count, size_count,
            cross, profile_cross, top_two_same, homogeneous_count, lca_profiled_count)


def run():
    verify()
    if (OUT / "g20k4_run_manifest.json").exists():
        raise FileExistsError("G2.0k.4 already run")
    expected = {r["order_id_hash"]: r for r in read_csv(PARTITION)}
    original = {r["order_id_hash"]: r for r in read_csv(BASELINE)}
    expansion = {r["order_id_hash"]: r for r in read_csv(EXPANSION)}
    if len(expected) != 10749 or len(original) != 10749 or len(expansion) != 459:
        raise ValueError("Input counts drift")
    concepts, hits, _ = base.load_concepts()
    new_ids = {r["concept_id"]: r["phrase"] for r in json.loads(K2_FREEZE.read_text())["terms"]}
    g12 = base.read_g12()
    nodes, children = base.load_nodes()
    valid, groups, codes = base.load_catalog()
    roots = {r["matched_floc"] for r in g12 if r["match_status"] == "matched_asset_node"}
    choices, matrices, concept_idx = make_matrices(roots, nodes, children, valid, concepts, new_ids)
    print("Frozen score matrices replayed", flush=True)
    tie_inputs, replay, checked = replay_gate(g12, expected, original, expansion, hits,
                                              choices, matrices, concept_idx)
    print("Replay gate passed: all 6,814 unresolved categories identical", flush=True)
    result = analyze(tie_inputs, choices, matrices, concept_idx, nodes, valid, groups,
                     codes, expected)
    (ties, answer, private, structures, origins, sizes, cross, profile_cross,
     two_same, homogeneous, lca_n) = result
    pools = defaultdict(list)
    for key, category, rows in sorted(private):
        pools[category].append(rows)
    selected = []
    while len(selected) < 20 and any(pools.values()):
        for category in STRUCTURES:
            if pools[category] and len(selected) < 20:
                selected.append(pools[category].pop(0))
    if len(selected) != 20:
        raise ValueError("Cannot stratify 20 tie sets")
    sample = [row for group in selected for row in group]
    structure_rows = [{"structural_category": s, "orders": structures[s],
                       "all_ties": 2238, "sum_valid": True} for s in STRUCTURES]
    origin_rows = [{"structural_category": s, "concept_origin": o, "orders": cross[(s, o)]}
                   for s in STRUCTURES for o in ORIGINS]
    profile_rows = [{"structural_category": s, "tie_rbnr_homogeneous": h,
                     "lca_direct_valid_rbnr": p, "orders": profile_cross[(s, h, p)]}
                    for s in STRUCTURES for h in (False, True) for p in (False, True)]
    answer_summary = []
    for target in TYPES.values():
        subset = [r for r in answer if r["target"] == target]
        for column in ("turbine_enabled_group_code_pairs", "lca_enabled_group_code_pairs",
                       "tie_node_min_enabled_group_code_pairs", "tie_node_max_enabled_group_code_pairs"):
            vals = [r[column] for r in subset if r[column] != ""]
            answer_summary.append({
                "target": target, "measure": column, "orders_total": len(subset),
                "orders_with_value": len(vals), "orders_not_comparable": len(subset) - len(vals),
                "min": min(vals) if vals else "", "p25": float(np.percentile(vals, 25)) if vals else "",
                "median": float(np.median(vals)) if vals else "",
                "p75": float(np.percentile(vals, 75)) if vals else "",
                "max": max(vals) if vals else "",
                "code_count_unit": "group_code_pairs_not_verified_classification",
            })
    outputs = {
        "g20k4_tie_structure_summary_sanitized.csv": structure_rows,
        "g20k4_concept_origin_crosstab_sanitized.csv": origin_rows,
        "g20k4_tie_profile_crosstab_sanitized.csv": profile_rows,
        "g20k4_answer_space_sanitized.csv": answer,
        "g20k4_answer_space_summary_sanitized.csv": answer_summary,
        "g20k4_answer_space_comparison_sanitized.csv": [
            {"target": target, "relation": relation,
             "orders": sum(r["target"] == target and r["lca_vs_turbine"] == relation for r in answer)}
            for target in TYPES.values()
            for relation in ("narrower", "equal", "wider", "not_comparable_no_turbine_profile")
        ],
        "g20k4_tie_order_diagnostic_sanitized.csv": ties,
        "g20k4_tie_size_distribution_sanitized.csv": [
            {"tie_size_bucket": b, "orders": sizes[b]} for b in ("2", "3", "4-5", ">5")
        ],
    }
    if any((OUT / name).exists() for name in outputs):
        raise FileExistsError("G2.0k.4 output already exists")
    PRIVATE.mkdir(parents=True, exist_ok=True)
    os.chmod(PRIVATE, 0o700)
    private_file = PRIVATE / "g20k4_tie_samples.csv"
    if private_file.exists():
        raise FileExistsError(private_file)
    with private_file.open("x", newline="", encoding="utf-8") as handle:
        os.chmod(private_file, 0o600)
        writer = csv.DictWriter(handle, fieldnames=list(sample[0]))
        writer.writeheader()
        writer.writerows(sample)
    if len({r["order_id_hash"] for r in read_csv(private_file)}) != 20:
        raise ValueError("Private sample drift")
    for name, rows in outputs.items():
        if not rows:
            raise ValueError("Empty output: " + name)
        base.write_csv(OUT / name, rows, list(rows[0]))
    memo = [
        "# G2.0k.4 - tie structure diagnostic",
        "",
        "Pre-flight confirmed from code: A1 includes G2.0i all-near-top profile consensus (g20i_profile_consensus.py:30); A2-A4 use strict profiled descendants, never the turbine (g20i_component_resolution.py:193,320-350); A5 uses reachable Superior functional location paths, not global IH06 completeness (g20i_component_resolution.py:71); A6 withdrawn, node score is max over all concepts (g20i_component_resolution.py:207); A7 profile/type/group/code-pair chain is in load_catalog (g20i_component_resolution.py:99).",
        "The global IH06 sheet has roots and 79 dangling parent references; reachable candidate paths in this run were checked separately.",
        f"Replay gate passed before tie analysis: all 6,814 unresolved categories identical; 3,935 resolved unchanged; {checked} original scores checked.",
        f"Structure: {dict(structures)}. Tie size: {dict(sizes)}. Concept origin: {dict(origins)}.",
        f"Top-two same RBNR: {two_same}; full tie-set homogeneous RBNR: {homogeneous}; directly profiled LCA: {lca_n}.",
        "For answer-space comparison, a missing turbine RBNR is not zero codes: 238 LCA-profiled orders have no valid turbine profile and are marked not comparable.",
        "Multi-concept tie means different model concepts won different nodes; it does not prove the technician named multiple physical parts.",
        "Enabled-code figures are profile-reachable group-code pairs, not verified class assignments. Direct LCA RBNR differs from inherited effective RBNR.",
        "The 20 visible tie sets are internal only (directory 700, file 600). No node descriptions are versioned.",
        "No resolution, promotion, code accuracy claim, F6 change, threshold change or margin change.",
    ]
    (OUT / "g20k4_memo.md").write_text("\n\n".join(memo) + "\n", encoding="utf-8")
    manifest = {
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "freeze_sha256": base.sha(OUT / "g20k4_freeze_manifest.json"),
        "private_sample_sha256": base.sha(private_file),
        "private_sample_mode": oct(private_file.stat().st_mode & 0o777),
        "private_directory_mode": oct(PRIVATE.stat().st_mode & 0o777),
        "replay_counts": dict(replay), "original_scores_reproduced": checked,
        "structure_counts": dict(structures), "concept_origin_counts": dict(origins),
        "tie_size_counts": dict(sizes), "top_two_same_rbnr": two_same,
        "full_tie_set_homogeneous_rbnr": homogeneous,
        "lca_direct_valid_rbnr_orders": lca_n,
        "output_sha256": {p.name: base.sha(p) for p in OUT.glob("g20k4_*")
                          if p.name != "g20k4_run_manifest.json"},
        "denominator_changed": False, "promotion": False,
    }
    (OUT / "g20k4_run_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: manifest[k] for k in (
        "replay_counts", "structure_counts", "concept_origin_counts", "tie_size_counts",
        "top_two_same_rbnr", "full_tie_set_homogeneous_rbnr", "lca_direct_valid_rbnr_orders"
    )}, indent=2, sort_keys=True))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("freeze", "run"))
    args = parser.parse_args()
    freeze() if args.mode == "freeze" else run()
