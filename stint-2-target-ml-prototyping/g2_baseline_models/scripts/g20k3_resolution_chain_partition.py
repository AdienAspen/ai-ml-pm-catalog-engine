"""G2.0k.3: replay the frozen B1 component-resolution chain by failure stage."""

from __future__ import annotations

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
from g20i_profile_consensus import consensus_profile


OUT = base.STINT2 / "g2_baseline_models/outputs/g20k_component_lift"
PRIVATE = base.STINT2 / "g2_baseline_models/internal/g20k_component_lift"
PLAN = base.STINT2 / "docs/PLAN-G2.0k.3 — Resolution Chain Partition.md"
CONSENSUS = base.STINT2 / "g2_baseline_models/outputs/g20i_profile_consensus/g20i_profile_consensus_by_order_sanitized.csv"
BASELINE = base.OUT / "g20i_order_resolution_sanitized.csv"
EXPANDED = OUT / "g20k_expansion_affected_orders_sanitized.csv"
K2_FREEZE = OUT / "g20k_freeze_manifest.json"
K2_RUN = OUT / "g20k_run_manifest.json"
SCRIPT = Path(__file__).resolve()
SOURCE_SCRIPTS = (
    base.STINT2 / "g2_baseline_models/scripts/g20c_step3_semantic_grouping.py",
    base.STINT2 / "g2_baseline_models/scripts/g20d2_semantic_reference_coverage.py",
    base.STINT2 / "g2_baseline_models/scripts/g20j_catalogue_code_coverage.py",
)
INPUTS = (PLAN, CONSENSUS, BASELINE, EXPANDED, K2_FREEZE, K2_RUN,
          *SOURCE_SCRIPTS, *base.SOURCES, SCRIPT)
CATEGORIES = (
    "resolved", "no_turbine_node", "no_component_concept",
    "no_profiled_component_candidate", "concept_no_node",
    "concept_ambiguous_node",
)
BANDS = ("0.55-0.60", "0.50-0.55", "0.40-0.50", "below_0.40")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def band(score: float) -> str:
    if score >= 0.55:
        return BANDS[0]
    if score >= 0.50:
        return BANDS[1]
    if score >= 0.40:
        return BANDS[2]
    return BANDS[3]


def freeze() -> None:
    base.check_freeze()
    if not PLAN.exists():
        raise FileNotFoundError(PLAN)
    k2 = json.loads(K2_RUN.read_text(encoding="utf-8"))
    if k2["summary"]["k2_vocabulary_only"] != {"resolved": 3935, "unresolved": 6814}:
        raise ValueError("G2.0k.2 diagnostic baseline changed")
    if k2["summary"]["threshold"] != base.THRESHOLD or k2["summary"]["minimum_margin"] != base.MIN_MARGIN:
        raise ValueError("G2.0k.2 decision rule changed")
    if json.loads(K2_FREEZE.read_text())["threshold"] != base.THRESHOLD:
        raise ValueError("Expansion freeze changed")
    if not all(path.exists() for path in INPUTS):
        raise FileNotFoundError("G2.0k.3 source missing")
    target = OUT / "g20k3_freeze_manifest.json"
    if target.exists():
        raise FileExistsError(target)
    payload = {
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "B1_RELATIONAL_10749_original_orders",
        "model": base.MODEL,
        "threshold": base.THRESHOLD,
        "margin": base.MIN_MARGIN,
        "scoring": "G20i_max_cosine_over_detected_concept_labels_to_profiled_IH06_node_description",
        "profile_consensus": "G20i_postrun_all_nodes_strictly_within_frozen_margin_same_RBNR",
        "k2_expansion": "frozen_G1.1e_phrase_concepts_only_on_baseline_unresolved_orders",
        "unprofiled_probe": "all_descendants_diagnostic_only_not_used_for_resolution",
        "near_miss_sample": "deterministic_round_robin_by_score_band_30_private_pairs",
        "evaluation_set_type": "not_evaluation_diagnostic_partition",
        "labels_read": False,
        "no_promotion": True,
        "source_sha256": {str(p.relative_to(base.ROOT)): base.sha(p) for p in INPUTS},
        "result_counts_seen": False,
    }
    with target.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def verify() -> dict:
    base.check_freeze()
    frozen = json.loads((OUT / "g20k3_freeze_manifest.json").read_text())
    if frozen["threshold"] != base.THRESHOLD or frozen["margin"] != base.MIN_MARGIN:
        raise ValueError("Frozen threshold or margin differs")
    for rel, digest in frozen["source_sha256"].items():
        if base.sha(base.ROOT / rel) != digest:
            raise ValueError(f"Source changed after freeze: {rel}")
    return frozen


def embed(model: SentenceTransformer, texts: list[str]) -> np.ndarray:
    batches = []
    for start in range(0, len(texts), 512):
        batches.append(np.asarray(model.encode(
            texts[start:start + 512], normalize_embeddings=True,
            convert_to_numpy=True, batch_size=64, show_progress_bar=False,
        ), dtype=np.float32))
    return np.vstack(batches)


def side_check() -> list[dict[str, object]]:
    checks = [
        ("G2.0c", "candidate_term n-grams and external anchor_text", "no", SOURCE_SCRIPTS[0], "model.encode(term_texts); model.encode(semantic_sources.anchor_text)"),
        ("G2.0d2", "normalised full source segments and frozen prototype_text", "yes", SOURCE_SCRIPTS[1], "model.encode(unique_texts); model.encode(prototype_text)"),
        ("G2.0i", "final concept canonical labels and IH06 node descriptions", "no", Path(base.__file__), "model.encode(concept_labels); model.encode(description_list)"),
        ("G2.0j", "normalised full source segments and catalogue/reference prototypes", "yes", SOURCE_SCRIPTS[2], "model.encode(texts); model.encode(descriptions)"),
    ]
    markers = {
        "G2.0c": ("term_texts =", "model.encode("),
        "G2.0d2": ("unique_texts", "model.encode("),
        "G2.0i": ("concept_vectors", "model.encode("),
        "G2.0j": ("model.encode(texts", "model.encode(descriptions"),
    }
    rows = []
    for step, embedded, affected, script, inspected in checks:
        code = script.read_text(encoding="utf-8")
        if not all(marker in code for marker in markers[step]):
            raise ValueError(f"Expected embedding call not found in {step}")
        rows.append({
            "step": step, "embedded_input": embedded,
            "affected_by_128_token_order_text_limit": affected,
            "source_script": str(script.relative_to(base.STINT2)),
            "source_sha256": base.sha(script),
            "code_inspection": inspected,
        })
    return rows


def run() -> None:
    verify()
    if (OUT / "g20k3_run_manifest.json").exists():
        raise FileExistsError("G2.0k.3 already run")
    baseline = {r["order_id_hash"]: r for r in read_csv(BASELINE)}
    consensus = {r["order_id_hash"]: r for r in read_csv(CONSENSUS)}
    expanded = {r["order_id_hash"]: r for r in read_csv(EXPANDED)}
    if len(baseline) != len(consensus) or len(consensus) != 10749 or len(expanded) != 459:
        raise ValueError("Baseline or expansion row count drift")
    concepts, old_hits, _ = base.load_concepts()
    k2 = json.loads(K2_FREEZE.read_text(encoding="utf-8"))
    new_ids = {r["concept_id"]: r["phrase"] for r in k2["terms"]}
    if len(new_ids) != 12:
        raise ValueError("Expansion concept count drift")
    labels = {**concepts, **new_ids}
    concept_ids = sorted(labels)
    concept_index = {cid: i for i, cid in enumerate(concept_ids)}
    g12 = base.read_g12()
    nodes, children = base.load_nodes()
    valid, _, _ = base.load_catalog()
    choices_by_root = {}
    profiled_descriptions, all_descriptions = set(), set()
    for source in g12:
        if source["match_status"] != "matched_asset_node":
            continue
        root = source["matched_floc"]
        if root in choices_by_root:
            continue
        profiled, all_nodes = [], []
        for node in base.descendants_of(root, children):
            if not node.startswith(root + "-") or node.split("-")[0] != root.split("-")[0]:
                raise ValueError("Candidate escaped turbine/site subtree")
            label = base.normalised(nodes[node]["description"])
            if not label:
                continue
            profile, _, _ = base.effective_profile(node, nodes, valid)
            item = (node, profile, label)
            all_nodes.append(item)
            all_descriptions.add(label)
            if profile:
                profiled.append(item)
                profiled_descriptions.add(label)
        choices_by_root[root] = (profiled, all_nodes)
    print(f"Candidate subtrees prepared: {len(choices_by_root)}", flush=True)
    model = SentenceTransformer(base.MODEL, local_files_only=True)
    # Preserve the G2.0i embedding batches for its 40 labels and candidate
    # descriptions; extra labels/nodes are embedded separately for diagnosis.
    original_ids = sorted(concepts)
    supplemental_ids = sorted(new_ids)
    if concept_ids != sorted(original_ids + supplemental_ids):
        raise ValueError("Concept ordering drift")
    original_vectors = embed(model, [base.normalised(concepts[cid]) for cid in original_ids])
    supplemental_vectors = embed(model, [base.normalised(new_ids[cid]) for cid in supplemental_ids])
    profiled_list = sorted(profiled_descriptions)
    profiled_vectors = embed(model, profiled_list)
    profiled_index = {label: i for i, label in enumerate(profiled_list)}
    all_list = sorted(all_descriptions)
    all_vectors = embed(model, all_list)
    all_index = {label: i for i, label in enumerate(all_list)}
    original_row = {cid: i for i, cid in enumerate(original_ids)}
    supplemental_row = {cid: i for i, cid in enumerate(supplemental_ids)}
    matrices = {}
    for root, (profiled, all_nodes) in choices_by_root.items():
        def score_columns(description_vectors: np.ndarray) -> np.ndarray:
            old_scores = original_vectors @ description_vectors.T
            extra_scores = supplemental_vectors @ description_vectors.T
            return np.stack([
                old_scores[original_row[cid]] if cid in original_row
                else extra_scores[supplemental_row[cid]]
                for cid in concept_ids
            ])
        matrices[root] = (
            score_columns(profiled_vectors[[profiled_index[c[2]] for c in profiled]]) if profiled else None,
            score_columns(all_vectors[[all_index[c[2]] for c in all_nodes]]) if all_nodes else None,
        )
    print("Frozen scoring matrices reproduced", flush=True)

    order_rows, near_rows = [], []
    counts, touched, multi, bands = Counter(), Counter(), Counter(), Counter()
    concept_no_node = Counter()
    ambiguous_rbnr = Counter()
    unprofiled_probe = Counter()
    original_replay = Counter()
    for source in g12:
        key = source["order_id_hash"]
        old, prior = baseline[key], consensus[key]
        added = expanded.get(key)
        old_concepts = set(old_hits.get(base.unit_hash(source["order_id"]), ()))
        new_concepts = set(added["matched_new_concept_ids"].split("|")) if added else set()
        new_concepts.discard("")
        active = sorted(old_concepts | new_concepts)
        if any(cid not in labels for cid in active):
            raise ValueError("Concept outside frozen G20i/G20k.2 registry")
        if len(active) > 1:
            multi["all_orders"] += 1
        root = source["matched_floc"] if source["match_status"] == "matched_asset_node" else ""
        category, stage, best_score, runner_score, best_cid = "", 0, None, None, ""
        top_two_same = ""
        if not root:
            category, stage = "no_turbine_node", 0
        elif not active:
            category, stage = "no_component_concept", 1
        else:
            profiled, all_nodes = choices_by_root[root]
            if not profiled:
                category, stage = "no_profiled_component_candidate", 2
            else:
                profiled_matrix, all_matrix = matrices[root]
                indices = [concept_index[cid] for cid in active]
                best, best_score, runner, runner_score = base.rank_nodes(profiled_matrix, indices)
                if not added and old["score"]:
                    if abs(float(old["score"]) - best_score) > 0.000002:
                        raise ValueError("Original G2.0i score drift")
                    if old["top_node_hash"] != base.short_hash("IH06NODE", profiled[best][0]):
                        raise ValueError(
                            f"Original G2.0i winner drift {key}: "
                            f"old={old['top_node_hash']} new={base.short_hash('IH06NODE', profiled[best][0])} "
                            f"score={best_score:.9f} old_score={old['score']} runner={runner_score:.9f}"
                        )
                    original_replay["scored"] += 1
                per_node = profiled_matrix[indices].max(axis=0)
                best_cid = max(active, key=lambda cid: (float(profiled_matrix[concept_index[cid], best]), cid))
                if best_score < base.THRESHOLD:
                    category, stage = "concept_no_node", 2
                    bands[band(best_score)] += 1
                    concept_no_node[best_cid] += 1
                    if all_matrix is not None:
                        all_scores = all_matrix[indices].max(axis=0)
                        all_best = int(np.argmax(all_scores))
                        if float(all_scores[all_best]) >= base.THRESHOLD and not all_nodes[all_best][1]:
                            unprofiled_probe["best_overall_unprofiled_above_threshold"] += 1
                        else:
                            unprofiled_probe["other"] += 1
                    near_rows.append({
                        "order_id_hash": key, "score_band": band(best_score),
                        "concept_id": best_cid, "concept_label": labels[best_cid],
                        "best_node_hash": base.short_hash("IH06NODE", profiled[best][0]),
                        "best_ih06_node_description": nodes[profiled[best][0]]["description"],
                        "score": round(best_score, 6),
                    })
                elif runner >= 0 and best_score - runner_score < base.MIN_MARGIN:
                    shared, _, _ = consensus_profile(
                        per_node, [c[1] for c in profiled], base.MIN_MARGIN
                    )
                    if shared:
                        category, stage = "resolved", 3
                    else:
                        category, stage = "concept_ambiguous_node", 2
                        top_two_same = str(profiled[best][1] == profiled[runner][1]).lower()
                        ambiguous_rbnr["same_top_two"] += int(top_two_same == "true")
                        ambiguous_rbnr["different_top_two"] += int(top_two_same == "false")
                else:
                    category, stage = "resolved", 3
        expected = added["expanded_profile_status"] if added else prior["profile_status"]
        if (category == "resolved") != expected.startswith("resolved"):
            raise ValueError(f"Profile status replay drift for {key}")
        if category == "concept_no_node" and old["score"] and not added and float(old["score"]) >= base.THRESHOLD:
            raise ValueError("Near-miss score inconsistent with original")
        counts[category] += 1
        if added:
            touched[category] += 1
        if category != "resolved" and len(active) > 1:
            multi["unresolved_orders"] += 1
        order_rows.append({
            "order_id_hash": key, "unit_key_hash": old["unit_key_hash"],
            "site_key": old["site_key"], "category": category,
            "furthest_link_reached": stage,
            "detected_concept_count": len(active),
            "supplemental_concept_count": len(new_concepts),
            "score_band": band(best_score) if category == "concept_no_node" else "",
            "winning_concept_id": best_cid if category == "concept_no_node" else "",
            "top_two_same_rbnr": top_two_same,
            "g20k2_touched": bool(added),
            "evaluation_set_type": "not_evaluation_diagnostic_partition",
            "raw_operational_values_emitted": False,
        })
    if len(order_rows) != 10749 or len({r["order_id_hash"] for r in order_rows}) != 10749:
        raise ValueError("Order coverage or uniqueness failed")
    if counts["resolved"] != 3935 or sum(counts.values()) != 10749 or sum(touched.values()) != 459:
        raise ValueError(f"Partition arithmetic failed: {counts}, touched={touched}")
    if sum(counts[c] for c in CATEGORIES if c != "resolved") != 6814:
        raise ValueError("Unresolved count drift")
    if sum(bands.values()) != counts["concept_no_node"]:
        raise ValueError("Near-miss score bands incomplete")
    if sum(ambiguous_rbnr.values()) != counts["concept_ambiguous_node"]:
        raise ValueError("Ambiguous RBNR breakdown incomplete")

    selected, by_band = [], defaultdict(list)
    for row in sorted(near_rows, key=lambda r: r["order_id_hash"]):
        by_band[row["score_band"]].append(row)
    # Round-robin selection keeps every populated score band represented.
    while len(selected) < 30 and any(by_band.values()):
        for label in BANDS:
            if by_band[label] and len(selected) < 30:
                selected.append(by_band[label].pop(0))
    if len(selected) != 30:
        raise ValueError("Insufficient near-miss pairs for sample")
    sample_counts = Counter(r["score_band"] for r in selected)
    summary = [{
        "category": category, "orders": counts[category],
        "g20k2_touched_orders": touched[category],
        "all_b1_orders": 10749,
        "partition_sum_valid": True,
        "path_bucket": "B1_RELATIONAL",
    } for category in CATEGORIES]
    near_summary = [{
        "score_band": label, "orders": bands[label], "sampled_private_pairs": sample_counts[label],
        "unprofiled_best_match_above_0_60_all_bands":
            unprofiled_probe["best_overall_unprofiled_above_threshold"] if label == BANDS[0] else "",
        "IH06_component_class_availability": "not_comparable_Object_Type_not_verified_as_component_class",
    } for label in BANDS]
    top_concepts = [{"concept_id": cid, "orders": n, "rank": i + 1}
                    for i, (cid, n) in enumerate(concept_no_node.most_common(20))]
    ambiguous = [{"top_two_rbnr_relation": relation, "orders": ambiguous_rbnr[relation]}
                 for relation in ("same_top_two", "different_top_two")]
    side = side_check()
    outputs = {
        "g20k3_partition_summary_sanitized.csv": summary,
        "g20k3_order_stage_sanitized.csv": order_rows,
        "g20k3_near_miss_summary_sanitized.csv": near_summary,
        "g20k3_near_miss_top20_concepts_sanitized.csv": top_concepts,
        "g20k3_ambiguous_rbnr_sanitized.csv": ambiguous,
        "g20k3_token_limit_scope_sanitized.csv": side,
    }
    if any((OUT / name).exists() for name in outputs):
        raise FileExistsError("G2.0k.3 output already exists")
    PRIVATE.mkdir(parents=True, exist_ok=True)
    os.chmod(PRIVATE, 0o700)
    private_path = PRIVATE / "g20k3_near_miss_pairs.csv"
    if private_path.exists():
        raise FileExistsError(private_path)
    with private_path.open("x", newline="", encoding="utf-8") as handle:
        os.chmod(private_path, 0o600)
        writer = csv.DictWriter(handle, fieldnames=list(selected[0]))
        writer.writeheader()
        writer.writerows(selected)
    if len(read_csv(private_path)) != 30:
        raise ValueError("Private sample round-trip failed")
    for name, rows in outputs.items():
        base.write_csv(OUT / name, rows, list(rows[0]))
    memo = [
        "# G2.0k.3 - frozen resolution-chain partition", "",
        "B1 only. Threshold 0.60 and node margin 0.05 unchanged; G2.0k.2 phrases only on original unresolved orders.",
        f"Partition: {dict(counts)}. The six categories sum to 10,749; unresolved sum to 6,814.",
        f"Multiple active concepts: {multi['all_orders']} orders, including {multi['unresolved_orders']} unresolved.",
        f"Near-miss score bands: {dict(bands)}. Diagnostic best overall unprofiled node >= 0.60: {unprofiled_probe['best_overall_unprofiled_above_threshold']} of {counts['concept_no_node']} near-miss orders.",
        "The unprofiled-node probe scores all descendant descriptions and never changes the frozen profiled candidate set or an order's partition category.",
        f"Ambiguous top-two RBNRs: {dict(ambiguous_rbnr)}. Same top-two RBNR is not profile consensus: a third node within the 0.05 band can differ. No promotion.",
        f"G2.0k.2 touched-order cross-tab: {dict(touched)} (n=459).",
        "Link 4 (node to profile) cannot fail: nodes without valid RBNR are removed before G2.0i scoring. The no-profiled-candidate state is a link-3 pre-score failure.",
        "IH06 has Object Type, but no verified mapping from that field to these concept classes; component-class availability is N/A.",
        "The 30 visible concept-label/IH06-description pairs are internal only (directory 700, file 600). Versioned outputs contain counts, hashes and safe concept identifiers, not the descriptions.",
        "No independent FLOC accuracy, model precision, catalogue-code accuracy, F6 denominator change or promotion is claimed.",
    ]
    (OUT / "g20k3_memo.md").write_text("\n\n".join(memo) + "\n", encoding="utf-8")
    manifest = {
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "freeze_sha256": base.sha(OUT / "g20k3_freeze_manifest.json"),
        "private_sample_sha256": base.sha(private_path),
        "private_sample_mode": oct(private_path.stat().st_mode & 0o777),
        "private_directory_mode": oct(PRIVATE.stat().st_mode & 0o777),
        "summary": {
            "category_counts": dict(counts), "touched_cross_tab": dict(touched),
            "multi_concept": dict(multi), "near_miss_bands": dict(bands),
            "unprofiled_best_above_threshold": unprofiled_probe["best_overall_unprofiled_above_threshold"],
            "ambiguous_rbnr": dict(ambiguous_rbnr),
            "original_scores_replayed": original_replay["scored"],
            "threshold": base.THRESHOLD, "margin": base.MIN_MARGIN,
            "denominator_changed": False, "promotion": False,
        },
    }
    manifest["output_sha256"] = {
        p.name: base.sha(p) for p in OUT.glob("g20k3_*")
        if p.name != "g20k3_run_manifest.json"
    }
    (OUT / "g20k3_run_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest["summary"], indent=2, sort_keys=True))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("freeze", "run"))
    args = parser.parse_args()
    freeze() if args.mode == "freeze" else run()
