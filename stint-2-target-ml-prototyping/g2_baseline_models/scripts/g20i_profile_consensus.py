"""Additive G2.0i profile consensus when the frozen node decision is ambiguous."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

import g20i_component_resolution as original


OUT = original.STINT2 / "g2_baseline_models/outputs/g20i_profile_consensus"
INPUT = original.OUT
SCRIPT = Path(__file__).resolve()
SOURCES = (
    INPUT / "g20i_freeze_manifest.json",
    INPUT / "g20i_run_manifest.json",
    INPUT / "g20i_order_resolution_sanitized.csv",
    INPUT / "g20i_profile_funnel_sanitized.csv",
    Path(original.__file__).resolve(),
    SCRIPT,
)


def consensus_profile(
    scores: np.ndarray, profiles: list[str], margin: float
) -> tuple[str, int, int]:
    """Require every node within the frozen top-score margin to share RBNR."""
    top = float(scores.max())
    nearby = np.flatnonzero((top - scores) < margin)
    values = {profiles[int(i)] for i in nearby}
    return (next(iter(values)) if len(values) == 1 else "", len(nearby), len(values))


def source_hashes() -> dict[str, str]:
    return {p.relative_to(original.ROOT).as_posix(): original.sha(p) for p in SOURCES}


def freeze() -> None:
    original.check_freeze()
    if not (INPUT / "g20i_run_manifest.json").exists():
        raise RuntimeError("Original G2.0i run must exist")
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / "g20i_profile_consensus_freeze.json"
    if target.exists():
        raise RuntimeError("Profile-consensus rule already frozen")
    payload = {
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "rule_status": "postrun_additive_diagnostic_not_original_frozen_instrument",
        "node_decisions_modified": False,
        "threshold": original.THRESHOLD,
        "margin": original.MIN_MARGIN,
        "candidate_band": "all_nodes_with_top_score_minus_node_score_strictly_below_0.05",
        "profile_rule": "emit_RBNR_only_if_every_node_in_band_has_same_valid_effective_RBNR",
        "ambiguity_scope": "original_node_status_ambiguous_only",
        "normalisation": "semantic_normalisation_v2",
        "model": original.MODEL,
        "evaluation_independence": "derived_from_rules",
        "eligible_for_independent_code_evaluation": False,
        "source_sha256": source_hashes(),
        "coverage_observed": False,
    }
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Frozen profile-consensus rule: {target}")


def read_original() -> list[dict[str, str]]:
    with (INPUT / "g20i_order_resolution_sanitized.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 10749 or len({r["order_id_hash"] for r in rows}) != len(rows):
        raise ValueError("Original order output drift")
    return rows


def run() -> None:
    from sentence_transformers import SentenceTransformer

    original.check_freeze()
    frozen = json.loads((OUT / "g20i_profile_consensus_freeze.json").read_text())
    if source_hashes() != frozen["source_sha256"]:
        raise ValueError("Original G2.0i outputs or consensus instrument changed")
    if frozen["threshold"] != original.THRESHOLD or frozen["margin"] != original.MIN_MARGIN:
        raise ValueError("Frozen cutoff mismatch")
    if (OUT / "g20i_profile_consensus_run.json").exists():
        raise RuntimeError("Profile-consensus run already recorded")

    original_rows = read_original()
    g12_rows = original.read_g12()
    if len(g12_rows) != len(original_rows):
        raise ValueError("Order alignment drift")
    nodes, children = original.load_nodes()
    valid, groups, codes = original.load_catalog()
    concepts, hits, _ = original.load_concepts()
    concept_ids = sorted(concepts)
    concept_idx = {cid: i for i, cid in enumerate(concept_ids)}

    candidates, descriptions = {}, set()
    for row in g12_rows:
        if row["match_status"] != "matched_asset_node":
            continue
        root = row["matched_floc"]
        if root in candidates:
            continue
        choices = []
        for node in original.descendants_of(root, children):
            if not node.startswith(root + "-") or node.split("-")[0] != root.split("-")[0]:
                raise ValueError("Candidate escaped site/turbine scope")
            profile, source, depth = original.effective_profile(node, nodes, valid)
            label = original.normalised(nodes[node]["description"])
            if profile and label:
                choices.append((node, profile, label))
                descriptions.add(label)
        candidates[root] = choices

    # Mirrors original candidate ordering and embedding inputs exactly.
    model = SentenceTransformer(original.MODEL, local_files_only=True)
    concept_vectors = np.asarray(model.encode(
        [original.normalised(concepts[cid]) for cid in concept_ids],
        normalize_embeddings=True, convert_to_numpy=True, batch_size=64,
        show_progress_bar=False,
    ), dtype=np.float32)
    description_list = sorted(descriptions)
    desc_idx = {label: i for i, label in enumerate(description_list)}
    batches = []
    for start in range(0, len(description_list), 512):
        batches.append(np.asarray(model.encode(
            description_list[start:start + 512], normalize_embeddings=True,
            convert_to_numpy=True, batch_size=64, show_progress_bar=False,
        ), dtype=np.float32))
    desc_vectors = np.vstack(batches)
    matrices = {
        root: concept_vectors @ desc_vectors[[desc_idx[c[2]] for c in choices]].T
        for root, choices in candidates.items() if choices
    }

    rows, funnel = [], []
    score_checks = 0
    for source, old in zip(g12_rows, original_rows, strict=True):
        if source["order_id_hash"] != old["order_id_hash"]:
            raise ValueError("Original row order drift")
        node_status = old["status"]
        state = "abstained" if node_status == "abstained" else "resolved_node" if node_status == "resolved" else "ambiguous"
        profile = old["resolved_rbnr"] if node_status == "resolved" else ""
        close_nodes, close_profiles, best_depth = 0, 0, ""
        if old["score"]:
            root = source["matched_floc"]
            choices = candidates[root]
            unit = original.unit_hash(source["order_id"])
            ids = [concept_idx[cid] for cid in sorted(hits[unit])]
            per_node = matrices[root][ids].max(axis=0)
            best, score, runner, runner_score = original.rank_nodes(matrices[root], ids)
            if old["top_node_hash"] != original.short_hash("IH06NODE", choices[best][0]):
                raise ValueError("Original top node changed")
            if old["runner_node_hash"] != original.short_hash("IH06NODE", choices[runner][0]):
                raise ValueError("Original runner-up changed")
            if abs(float(old["score"]) - score) > 0.000002:
                raise ValueError("Original semantic score changed")
            recomputed = (
                "abstained" if score < original.THRESHOLD else
                "ambiguous" if score - runner_score < original.MIN_MARGIN else
                "resolved"
            )
            if recomputed != node_status:
                raise ValueError("Original node state changed")
            score_checks += 1
            if node_status == "ambiguous":
                profile, close_nodes, close_profiles = consensus_profile(
                    per_node, [c[1] for c in choices], original.MIN_MARGIN
                )
                state = "resolved_node_ambiguous" if profile else "ambiguous"
                best_depth = len(choices[best][0].split("-"))
        rows.append({
            "order_id_hash": old["order_id_hash"], "site_key": old["site_key"],
            "node_status_unchanged": node_status,
            "profile_status": state, "resolved_rbnr": profile,
            "close_node_count": close_nodes if node_status == "ambiguous" else "",
            "distinct_close_profiles": close_profiles if node_status == "ambiguous" else "",
            "top_node_depth": best_depth,
            "top_node_hash": old["top_node_hash"],
            "resolved_node_hash": old["resolved_node_hash"],
            "profile_generation_method": "all_near_top_nodes_same_RBNR_postrun_v1" if node_status == "ambiguous" else "original_g20i_node_resolution_v1" if node_status == "resolved" else "none",
            "evaluation_independence": "derived_from_rules",
            "independent_code_evaluation_eligible": False,
        })
        if node_status == "ambiguous" and profile:
            for cat in original.TYPES:
                allowed = groups[(profile, cat)]
                funnel.append({
                    "order_id_hash": old["order_id_hash"], "site_key": old["site_key"],
                    "profile_rbnr": profile, "catalog_type": cat,
                    "target": original.TYPE_NAMES[cat],
                    "allowed_group_count": len(allowed),
                    "reachable_group_code_pair_count": sum(codes[(cat, g)] for g in allowed),
                    "node_status": "ambiguous", "profile_status": "resolved_node_ambiguous",
                    "answer_space_claim": "text_derived_profile_consensus_not_verified_code_classification",
                })

    if score_checks != 7385 or len(rows) != 10749:
        raise ValueError(f"Recomputed score count drift: {score_checks}")
    new = sum(r["profile_status"] == "resolved_node_ambiguous" for r in rows)
    if len(funnel) != new * len(original.TYPES):
        raise ValueError("Consensus funnel count drift")
    original.write_csv(OUT / "g20i_profile_consensus_by_order_sanitized.csv", rows,
        ["order_id_hash", "site_key", "node_status_unchanged", "profile_status", "resolved_rbnr", "close_node_count", "distinct_close_profiles", "top_node_depth", "top_node_hash", "resolved_node_hash", "profile_generation_method", "evaluation_independence", "independent_code_evaluation_eligible"])
    original.write_csv(OUT / "g20i_profile_consensus_funnel_sanitized.csv", funnel,
        ["order_id_hash", "site_key", "profile_rbnr", "catalog_type", "target", "allowed_group_count", "reachable_group_code_pair_count", "node_status", "profile_status", "answer_space_claim"])
    state_counts = Counter(r["profile_status"] for r in rows)
    added_by_site = Counter(r["site_key"] for r in rows if r["profile_status"] == "resolved_node_ambiguous")
    added_by_depth = Counter(r["top_node_depth"] for r in rows if r["profile_status"] == "resolved_node_ambiguous")
    close_counts = Counter(r["close_node_count"] for r in rows if r["profile_status"] == "resolved_node_ambiguous")
    summary = {
        "original_node_status": dict(Counter(r["node_status_unchanged"] for r in rows)),
        "profile_status": dict(state_counts),
        "original_profile_resolved": 2400,
        "additional_ambiguous_node_profile_resolved": new,
        "total_profile_resolved_diagnostic": 2400 + new,
        "additional_by_site": dict(sorted(added_by_site.items())),
        "additional_by_top_node_depth": dict(sorted(added_by_depth.items())),
        "additional_close_node_counts": dict(sorted(close_counts.items())),
        "semantic_scores_reproduced": score_checks,
        "node_results_modified": False,
        "independent_structural_accuracy_measured": False,
        "denominator_changed": False,
    }
    memo = [
        "# G2.0i - additive profile consensus",
        "",
        "Post-run diagnostic extension. The original frozen node threshold (0.60), margin (0.05), and all 10,749 node states are unchanged.",
        "All candidate nodes strictly within 0.05 of the best score must share one valid RBNR; checking only the top two is insufficient.",
        "",
        f"- Additional profiles with ambiguous nodes: {new:,} of the original 3,772 ambiguous orders.",
        f"- Total diagnostic profile coverage: {2400 + new:,} orders; original resolved-node coverage remains 2,400.",
        f"- Remaining profile-ambiguous: {state_counts['ambiguous']:,}; profile-abstained: {state_counts['abstained']:,}.",
        f"- Additional by site: {dict(sorted(added_by_site.items()))}.",
        f"- Additional by top-node depth: {dict(sorted(added_by_depth.items()))}.",
        "",
        "This is a text-derived RBNR candidate, not an independent FLOC assignment or catalog code label. The same Object Part signal cannot independently evaluate the profile-restricted code space it helped derive.",
        "No node promotion, threshold retuning, F6 or denominator change.",
    ]
    (OUT / "g20i_profile_consensus_memo.md").write_text("\n".join(memo) + "\n", encoding="utf-8")
    manifest = {
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "freeze_manifest_sha256": original.sha(OUT / "g20i_profile_consensus_freeze.json"),
        "output_sha256": {p.name: original.sha(p) for p in sorted(OUT.iterdir()) if p.name != "g20i_profile_consensus_run.json"},
        "summary": summary,
    }
    (OUT / "g20i_profile_consensus_run.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("freeze", "run"))
    args = parser.parse_args()
    freeze() if args.mode == "freeze" else run()
