"""G2.0k diagnostic: audit windowing premise and expand Object Part phrases."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer

import g20c_neutral_ngram_extraction as extraction
import g20i_component_resolution as base
from g20i_profile_consensus import consensus_profile


OUT = base.STINT2 / "g2_baseline_models/outputs/g20k_component_lift"
CONSENSUS = base.STINT2 / "g2_baseline_models/outputs/g20i_profile_consensus/g20i_profile_consensus_by_order_sanitized.csv"
BASE_ROWS = base.OUT / "g20i_order_resolution_sanitized.csv"
SAMPLE = base.STINT2 / "g1_actionable_zeros/g11_object_part_crosswalk/internal/g11e_group_b_blind_order_sample_internal.csv"
PREPARED = base.STINT2 / "g2_baseline_models/internal/g20j_catalogue_code_coverage/g20j_prepared_corpus_internal.json"
PLAN = base.STINT2 / "docs/PLAN-G2.0k—Lifting Component Resolution.md"
TERMS = (
    "yaw ring", "torque arm bushing", "pitch manifold accumulator",
    "hub safety pilot valve", "deck hatches", "lift guide arm",
    "bottom cover", "generator bearing DE/NonDE", "smoke detector",
    "M12 connector", "MSC/LSC stack", "PMG encoder",
)
INPUTS = (CONSENSUS, BASE_ROWS, SAMPLE, PREPARED, PLAN, *base.SOURCES)
RESOLVED = {"resolved_node", "resolved_node_ambiguous"}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def term_id(term: str) -> str:
    return base.short_hash("G20KTERM", term, 16)


def phrase_hits(segments: list[list[str]], phrases: dict[str, tuple[str, ...]]) -> set[str]:
    found = set()
    for term, phrase in phrases.items():
        for segment in segments:
            if any(tuple(segment[i:i + len(phrase)]) == phrase
                   for i in range(len(segment) - len(phrase) + 1)):
                found.add(term)
                break
    return found


def write_csv(path: Path, rows: list[dict[str, object]], columns: list[str]) -> None:
    if path.exists():
        raise FileExistsError(path)
    base.write_csv(path, rows, columns)


def freeze() -> None:
    base.check_freeze()
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / "g20k_freeze_manifest.json"
    if target.exists():
        raise FileExistsError(target)
    phrases = {term: tuple(extraction.normalise_text(term)[0]) for term in TERMS}
    if len(set(phrases.values())) != len(TERMS) or any(not p for p in phrases.values()):
        raise ValueError("Expansion terms normalize to empty or duplicate phrases")
    sample = read_csv(SAMPLE)
    if len(sample) != 20 or len({r["order_id_hash"] for r in sample}) != 20:
        raise ValueError("G1.1e blind sample changed")
    with target.open("x", encoding="utf-8") as handle:
        json.dump({
            "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
            "scope": "B1_RELATIONAL_full_10749; expansion_only_on_6815_unresolved_profiles",
            "k1_status": "not_applicable_original_G20i_uses_untruncated_exact_phrase_hits_not_order_embeddings",
            "k2_detector": "exact_contiguous_normalised_phrase_per_masked_source_segment",
            "k2_construction_method": "derived_from_corpus_inspection",
            "k2_source": "g11e_blind_sample",
            "new_concepts": "one_supplemental_phrase_concept_per_listed_term_no_reclustering",
            "prototype_source": "G1.1e_only_never_G2.0_prototypes",
            "model": base.MODEL,
            "threshold": base.THRESHOLD,
            "minimum_margin": base.MIN_MARGIN,
            "profile_consensus_rule": "all_nodes_strictly_within_margin_share_RBNR",
            "labels_read": False,
            "independent_evaluation_claim": False,
            "terms": [{"concept_id": term_id(t), "phrase": " ".join(phrases[t])} for t in TERMS],
            "g11e_order_exclusion_hashes": sorted(r["order_id_hash"] for r in sample),
            "source_sha256": {str(p.relative_to(base.ROOT)): sha(p) for p in INPUTS},
            "coverage_observed": False,
        }, handle, indent=2, sort_keys=True)
        handle.write("\n")


def verify() -> dict:
    base.check_freeze()
    frozen = json.loads((OUT / "g20k_freeze_manifest.json").read_text())
    if frozen["threshold"] != base.THRESHOLD or frozen["minimum_margin"] != base.MIN_MARGIN:
        raise ValueError("Frozen decision rule drift")
    for rel, digest in frozen["source_sha256"].items():
        if sha(base.ROOT / rel) != digest:
            raise ValueError(f"Frozen source changed: {rel}")
    if [r["concept_id"] for r in frozen["terms"]] != [term_id(t) for t in TERMS]:
        raise ValueError("Expansion registry drift")
    return frozen


def window_audit(consensus: dict[str, dict], unit_to_order: dict[str, str]) -> dict:
    prepared = json.loads(PREPARED.read_text(encoding="utf-8"))
    tokenizer = AutoTokenizer.from_pretrained(
        "sentence-transformers/" + base.MODEL, local_files_only=True
    )
    long_indices = {i for i, text in enumerate(prepared["texts"])
                    if len(tokenizer.tokenize(text)) + tokenizer.num_special_tokens_to_add() > 128}
    counts = Counter()
    for unit in prepared["units"]:
        if unit["path_bucket"] != "B1_RELATIONAL":
            continue
        if long_indices.intersection(unit["segment_indices"]):
            order = unit_to_order[unit["unit_key_hash"]]
            counts[consensus[order]["profile_status"]] += 1
    if sum(counts.values()) != 702:
        raise ValueError(f"G2.0j long-order count drift: {counts}")
    return {
        "long_model_eligible_orders": 702,
        "by_existing_profile_status": dict(sorted(counts.items())),
        "long_already_profile_resolved": sum(counts[s] for s in RESOLVED),
        "long_still_unresolved": counts["ambiguous"] + counts["abstained"],
        "segmentation_candidate_order_count": 0,
        "reason": "G20i order text enters via exact untruncated phrase matching; only short concept labels and IH06 descriptions are embedded",
    }


def run() -> None:
    frozen = verify()
    if (OUT / "g20k_run_manifest.json").exists():
        raise FileExistsError("G2.0k run already recorded")
    original = {r["order_id_hash"]: r for r in read_csv(BASE_ROWS)}
    consensus = {r["order_id_hash"]: r for r in read_csv(CONSENSUS)}
    if len(original) != len(consensus) or len(consensus) != 10749:
        raise ValueError("G2.0i baseline mismatch")
    unit_to_order = {r["unit_key_hash"]: r["order_id_hash"] for r in original.values()}
    audit = window_audit(consensus, unit_to_order)
    concepts, old_hits, _ = base.load_concepts()
    orders = json.loads(base.SOURCES[3].read_text(encoding="utf-8"))
    if len(orders) != 10749:
        raise ValueError("B1 source order drift")
    patterns = extraction.load_leakage_patterns()
    phrases = {term: tuple(extraction.normalise_text(term)[0]) for term in TERMS}
    g12 = {r["order_id_hash"]: r for r in base.read_g12()}
    detected = {}
    counts = Counter()
    for order in orders:
        order_hash = base.short_hash("ORDER", str(order["id"]))
        if consensus[order_hash]["profile_status"] in RESOLVED:
            continue
        counts["unresolved_baseline"] += 1
        segments = []
        for field in ("reason", "descriptionExtended"):
            masked, _, _ = extraction.apply_leakage_mask(str(order.get(field) or ""), patterns)
            segments.append(extraction.normalise_text(masked)[0])
        found = phrase_hits(segments, phrases)
        if found:
            detected[order_hash] = found
            counts["unresolved_with_supplemental_phrase"] += 1
    if counts["unresolved_baseline"] != 6815:
        raise ValueError("Baseline unresolved count drift")

    nodes, children = base.load_nodes()
    valid, _, _ = base.load_catalog()
    choices_by_root, descriptions = {}, set()
    for order_hash in detected:
        source = g12[order_hash]
        if source["match_status"] != "matched_asset_node":
            continue
        root = source["matched_floc"]
        if root in choices_by_root:
            continue
        choices = []
        for node in base.descendants_of(root, children):
            if not node.startswith(root + "-") or node.split("-")[0] != root.split("-")[0]:
                raise ValueError("Candidate escaped site/turbine scope")
            profile, _, _ = base.effective_profile(node, nodes, valid)
            label = base.normalised(nodes[node]["description"])
            if profile and label:
                choices.append((node, profile, label))
                descriptions.add(label)
        choices_by_root[root] = choices

    model = SentenceTransformer(base.MODEL, local_files_only=True)
    original_ids = sorted(concepts)
    ids = original_ids + [term_id(t) for t in TERMS]
    labels = [base.normalised(concepts[cid]) for cid in original_ids] + [
        " ".join(phrases[t]) for t in TERMS
    ]
    vectors = np.asarray(model.encode(labels, normalize_embeddings=True,
                                      convert_to_numpy=True, batch_size=64,
                                      show_progress_bar=False), dtype=np.float32)
    desc_list = sorted(descriptions)
    desc_vec = np.asarray(model.encode(desc_list, normalize_embeddings=True,
                                       convert_to_numpy=True, batch_size=64,
                                       show_progress_bar=False), dtype=np.float32)
    desc_idx = {label: i for i, label in enumerate(desc_list)}
    matrices = {root: vectors @ desc_vec[[desc_idx[c[2]] for c in choices]].T
                for root, choices in choices_by_root.items() if choices}
    idx = {cid: i for i, cid in enumerate(ids)}
    term_counts = Counter()
    new_profiles = Counter()
    results = []
    for order_hash, found in sorted(detected.items()):
        old = original[order_hash]
        prior = consensus[order_hash]
        source = g12[order_hash]
        root = source["matched_floc"] if source["match_status"] == "matched_asset_node" else ""
        state = prior["profile_status"]
        profile = prior["resolved_rbnr"]
        winner = ""
        if root in matrices:
            choices = choices_by_root[root]
            matrix = matrices[root]
            old_indices = [idx[cid] for cid in sorted(old_hits.get(base.unit_hash(source["order_id"]), ())) ]
            if old["score"] and old_indices:
                _, old_score, _, _ = base.rank_nodes(matrix, old_indices)
                if abs(old_score - float(old["score"])) > 0.000002:
                    raise ValueError("Frozen baseline score failed to replay")
            active = old_indices + [idx[term_id(t)] for t in sorted(found)]
            per_node = matrix[active].max(axis=0)
            best, score, runner, runner_score = base.rank_nodes(matrix, active)
            if score < base.THRESHOLD:
                state, profile = "abstained", ""
            elif score - runner_score >= base.MIN_MARGIN:
                state, profile = "resolved_node", choices[best][1]
            else:
                profile, _, _ = consensus_profile(
                    per_node, [c[1] for c in choices], base.MIN_MARGIN
                )
                state = "resolved_node_ambiguous" if profile else "ambiguous"
            if state in RESOLVED:
                contributors = [term_id(t) for t in sorted(found)
                                if float(matrix[idx[term_id(t)], best]) >= score - 1e-6]
                winner = "|".join(contributors)
        for term in found:
            term_counts[term] += 1
        if state in RESOLVED:
            new_profiles[state] += 1
        results.append({
            "order_id_hash": order_hash,
            "baseline_profile_status": prior["profile_status"],
            "expanded_profile_status": state,
            "expanded_profile_rbnr": profile,
            "matched_new_concept_ids": "|".join(sorted(term_id(t) for t in found)),
            "best_new_concept_ids": winner,
            "independent_code_evaluation_eligible": False,
            "label_generation_method": "g20k_corpus_inspection_expanded_concepts_diagnostic",
        })
    if len(results) != counts["unresolved_with_supplemental_phrase"]:
        raise ValueError("Supplemental match count drift")
    registry = [{
        "concept_id": term_id(term), "normalised_phrase": " ".join(phrases[term]),
        "source": "g11e_blind_sample", "construction_method": "derived_from_corpus_inspection",
        "unresolved_orders_with_exact_phrase": term_counts[term],
        "newly_resolved_orders_with_best_concept": sum(
            term_id(term) in row["best_new_concept_ids"].split("|") and
            row["expanded_profile_status"] in RESOLVED for row in results
        ),
        "evaluation_exclusion": "G1.1e_20_reviewed_orders",
    } for term in TERMS]
    write_csv(OUT / "g20k_expansion_registry_sanitized.csv", registry,
              list(registry[0]))
    write_csv(OUT / "g20k_expansion_affected_orders_sanitized.csv", results,
              list(results[0]))
    gained = sum(r["expanded_profile_status"] in RESOLVED for r in results)
    summary = {
        "baseline_resolved": 3934,
        "baseline_unresolved": 6815,
        "k1_segmentation_only": {"resolved": 3934, "unresolved": 6815,
                                  "status": "not_applicable_to_frozen_detector_not_an_executed_window_rerun"},
        "k2_vocabulary_only": {"resolved": 3934 + gained, "unresolved": 6815 - gained},
        "combined": {"resolved": 3934 + gained, "unresolved": 6815 - gained,
                     "status": "identical_to_k2_because_k1_is_noop_for_this_pipeline"},
        "k2_new_resolved_by_status": dict(new_profiles),
        "k2_affected_unresolved_orders": len(results),
        "k1_window_audit": audit,
        "threshold": base.THRESHOLD,
        "minimum_margin": base.MIN_MARGIN,
        "quality_or_precision_measured": False,
        "denominator_changed": False,
        "promotion": False,
    }
    (OUT / "g20k_memo.md").write_text(
        "# G2.0k diagnostic lift\n\n"
        "G2.0k.1 is not applicable to the frozen G2.0i pipeline: order text was matched by exact, untruncated phrases. "
        "MiniLM embedded short concept labels and IH06 descriptions, not full order text. "
        "The 702 long eligible B1 orders include 234 already resolved and 468 unresolved. "
        "A windowed full-text semantic detector would be a new instrument, not a controlled segmentation rerun.\n\n"
        f"G2.0k.2 adds 12 G1.1e-derived phrase concepts and yields {gained} additional diagnostic profile candidates "
        f"among {len(results)} affected unresolved orders, at the unchanged 0.60 score and 0.05 margin. "
        "This is not precision, independent FLOC evidence, or catalogue-code accuracy. "
        "The 20 G1.1e reviewed orders are excluded from future Object Part evaluation. "
        "The source is masked before normalization. No F6 change or candidate promotion.\n",
        encoding="utf-8",
    )
    (OUT / "g20k_run_manifest.json").write_text(json.dumps({
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "freeze_sha256": sha(OUT / "g20k_freeze_manifest.json"),
        "summary": summary,
        "outputs_sha256": {p.name: sha(p) for p in OUT.iterdir()
                           if p.name != "g20k_run_manifest.json"},
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("freeze", "run"))
    args = parser.parse_args()
    freeze() if args.mode == "freeze" else run()
