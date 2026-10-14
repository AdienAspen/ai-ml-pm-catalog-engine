"""G2.0i: diagnostic, site-aware component-node proposals from frozen concepts."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from openpyxl import load_workbook

import g20c_neutral_ngram_extraction as extraction


ROOT = Path("/home/adien-i7-remote/workspace/fsa_bridge_ml_feasibility")
STINT2 = ROOT / "stint-2-target-ml-prototyping"
DATA = ROOT / "data/interim/extracted_source/package_001_37cac7fe/Data"
G12 = STINT2 / "g1_actionable_zeros/g12_floc_alignment"
G20C = STINT2 / "g2_baseline_models/outputs/g20_corpus_native_domain_vocab"
OUT = STINT2 / "g2_baseline_models/outputs/g20i_component_resolution"
SCRIPT = Path(__file__).resolve()
MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
THRESHOLD = 0.60
MIN_MARGIN = 0.05
TYPES = ("S", "B", "C", "5", "A")
TYPE_NAMES = {"S": "Symptom", "B": "Object Part", "C": "Damage", "5": "Cause", "A": "Activity"}

SOURCES = (
    DATA / "References/IH06 FSA Sites PRD.XLSX",
    DATA / "References/IH08 FSA Sites PRD.XLSX",
    DATA / "References/Wind Catalog Group and Codes Final v4.xlsx",
    DATA / "Vestas/api_service_v1_service-orders.json",
    G12 / "internal/g12_floc_alignment_internal_review.csv",
    G12 / "outputs/g12_floc_alignment_order_level_sanitized.csv",
    G20C / "g20c_domain_vocabulary_sanitized.csv",
    G20C / "g20c_step5_unit_concept_hits_sanitized.csv",
    G20C / "g20c_step5_coverage_manifest.json",
    Path(extraction.__file__).resolve(),
    SCRIPT,
)


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def short_hash(prefix: str, value: str, size: int = 16) -> str:
    return f"{prefix}-{hashlib.sha256(value.encode('utf-8')).hexdigest()[:size]}"


def unit_hash(order_id: str) -> str:
    physical = short_hash(
        "PHY", f"CONTRACTOR_PATH_001|api_service_v1_service-orders|{order_id}"
    )
    return short_hash("UNIT", physical, 12)


def normalised(value: str) -> str:
    return " ".join(extraction.normalise_text(value)[0])


def load_nodes() -> tuple[dict[str, dict[str, str]], dict[str, set[str]]]:
    wb = load_workbook(SOURCES[0], read_only=True, data_only=True)
    values = wb.active.values
    head = next(values)
    ix = {name: pos for pos, name in enumerate(head)}
    nodes, children = {}, defaultdict(set)
    for row in values:
        floc = str(row[ix["Functional Location"]] or "").strip()
        if not floc:
            continue
        if floc in nodes:
            raise ValueError("Duplicate IH06 FLOC")
        parent = str(row[ix["Superior functional location"]] or "").strip()
        nodes[floc] = {
            "parent": parent,
            "profile": str(row[ix["Catalog Profile"]] or "").strip(),
            "description": str(row[ix["Description of functional location"]] or "").strip(),
        }
        if parent:
            children[parent].add(floc)
    wb.close()
    return nodes, children


def load_catalog() -> tuple[set[str], dict[tuple[str, str], set[str]], dict[tuple[str, str], int]]:
    wb = load_workbook(SOURCES[2], read_only=True, data_only=True)
    listed = {str(row[0]).strip() for row in list(wb["Catalog Profile List"].values)[1:] if row[0]}
    groups = defaultdict(set)
    for row in list(wb["Catalog Profile and Code Groups"].values)[1:]:
        groups[(str(row[0]).strip(), str(row[2]).strip())].add(str(row[3]).strip())
    valid = listed & {key[0] for key in groups}
    codes = {}
    for cat in TYPES:
        by_group = defaultdict(set)
        for row in list(wb[f"Catalog. {cat} - Group and Code"].values)[1:]:
            assert str(row[0]).strip() == cat
            by_group[str(row[1]).strip()].add(str(row[2]).strip())
        for group, values in by_group.items():
            codes[(cat, group)] = len(values)
    wb.close()
    for (profile, cat), allowed in groups.items():
        if profile not in valid or cat not in TYPES:
            raise ValueError("Invalid profile/type association")
        if any((cat, group) not in codes for group in allowed):
            raise ValueError("Profile group absent from code sheet")
    return valid, groups, codes


def effective_profile(
    node: str, nodes: dict[str, dict[str, str]], valid: set[str]
) -> tuple[str, str, int]:
    seen = set()
    current = node
    depth = 0
    while current in nodes:
        if current in seen:
            raise ValueError("IH06 parent cycle")
        seen.add(current)
        profile = nodes[current]["profile"]
        if profile in valid:
            return profile, "node" if depth == 0 else "ancestor", depth
        current = nodes[current]["parent"]
        depth += 1
    return "", "no_profile_no_filter", depth


def read_g12() -> list[dict[str, str]]:
    with SOURCES[4].open(newline="", encoding="utf-8") as handle:
        internal = list(csv.DictReader(handle))
    with SOURCES[5].open(newline="", encoding="utf-8") as handle:
        sanitized = list(csv.DictReader(handle))
    if len(internal) != len(sanitized) or len(internal) != 10749:
        raise ValueError("G1.2 order count drift")
    rows = []
    for raw, clean in zip(internal, sanitized, strict=True):
        if clean["order_id_hash"] != short_hash("ORDER", raw["order_id"]):
            raise ValueError("G1.2 order alignment drift")
        if clean["match_status"] != raw["match_status"]:
            raise ValueError("G1.2 match status drift")
        rows.append({**raw, "order_id_hash": clean["order_id_hash"], "site_key": clean["site_key"]})
    if len({row["order_id_hash"] for row in rows}) != len(rows):
        raise ValueError("Duplicate G1.2 order")
    return rows


def load_concepts() -> tuple[dict[str, str], dict[str, set[str]], dict[str, object]]:
    vocab = pd.read_csv(SOURCES[6]).fillna("")
    assigned = vocab[vocab.target.eq("Object Part")]
    if len(assigned) != 40 or not assigned.concept_id.is_unique:
        raise ValueError("Final Object Part concept set changed")
    concepts = dict(zip(assigned.concept_id, assigned.canonical_label, strict=True))
    if any(not normalised(label) for label in concepts.values()):
        raise ValueError("Empty normalized Object Part concept label")
    hits = pd.read_csv(SOURCES[7]).fillna("")
    hits = hits[
        hits.target.eq("Object Part")
        & hits.path_bucket.eq("B1_RELATIONAL")
        & hits.anchor_source.eq("domain_vocabulary")
    ]
    all_ids = set(hits.concept_id)
    if len(all_ids) != 43 or hits.unit_key_hash.nunique() != 7668:
        raise ValueError("G2.0c historical Object Part coverage changed")
    excluded = all_ids - set(concepts)
    if len(excluded) != 3 or set(vocab[vocab.concept_id.isin(excluded)].target) != {"unassigned"}:
        raise ValueError("Unexpected non-Object Part concepts in historical hits")
    selected = hits[hits.concept_id.isin(concepts)]
    if selected.unit_key_hash.nunique() != 7393:
        raise ValueError("G2.0c assigned-only coverage changed")
    by_unit = defaultdict(set)
    for row in selected.itertuples(index=False):
        by_unit[row.unit_key_hash].add(row.concept_id)
    reconciliation = {
        "historical_units_with_any_domain_hit": 7668,
        "historical_concepts_in_hits": 43,
        "final_assigned_object_part_concepts": 40,
        "unassigned_concepts_excluded": 3,
        "assigned_only_units": len(by_unit),
        "units_removed_by_assignment_filter": 7668 - len(by_unit),
    }
    return concepts, by_unit, reconciliation


def descendants_of(
    root: str, children: dict[str, set[str]]
) -> list[str]:
    result, pending, seen = [], sorted(children.get(root, ())), {root}
    while pending:
        node = pending.pop()
        if node in seen:
            raise ValueError("IH06 descendant cycle")
        seen.add(node)
        result.append(node)
        pending.extend(sorted(children.get(node, ())))
    return sorted(result)


def rank_nodes(matrix: np.ndarray, concept_indices: list[int]) -> tuple[int, float, int, float]:
    best_per_node = matrix[concept_indices].max(axis=0)
    order = np.argsort(-best_per_node, kind="stable")
    best = int(order[0])
    runner = int(order[1]) if len(order) > 1 else -1
    return best, float(best_per_node[best]), runner, float(best_per_node[runner]) if runner >= 0 else -1.0


def freeze() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = OUT / "g20i_freeze_manifest.json"
    if manifest.exists():
        raise RuntimeError("G2.0i already frozen; no silent re-freeze")
    _, _, reconciliation = load_concepts()
    valid, groups, codes = load_catalog()
    if len(valid) != 162:
        raise ValueError("Catalog profile count changed")
    settings = {
        "scope": "B1_RELATIONAL_only_10749_orders",
        "construction": "final_G2.0c_Object_Part_concepts_only; exclude_unassigned",
        "normalisation": "semantic_normalisation_v2",
        "embedding_model": MODEL,
        "prototype_text": "final_concept_canonical_label_only",
        "candidate_text": "IH06_description_normalized_same_pipeline",
        "candidate_scope": "strict_descendant_of_G1.2_site_and_turbine_node_with_valid_effective_RBNR",
        "score": "max_L2_cosine_over_detected_concepts_per_node",
        "threshold": THRESHOLD,
        "minimum_top_two_node_margin": MIN_MARGIN,
        "threshold_selection": "pre_result_conservative_diagnostic_no_labels",
        "states": "resolved|ambiguous|abstained",
        "answer_space_chain": "profile_to_type_to_allowed_group_to_distinct_group_code_pairs",
        "evaluation_independence": "derived_from_rules",
        "independent_code_evaluation_eligible": False,
        "no_response_labels_read": True,
    }
    source_hashes = {p.relative_to(ROOT).as_posix(): sha(p) for p in SOURCES}
    payload = {
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "settings": settings,
        "source_sha256": source_hashes,
        "concept_reconciliation": reconciliation,
        "catalog_profiles": len(valid),
        "profile_type_associations": sum(len(x) for x in groups.values()),
        "distinct_catalog_group_code_pairs": sum(codes.values()),
        "scores_observed": False,
    }
    manifest.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"frozen": str(manifest), "settings": settings, "concepts": reconciliation}, indent=2))


def check_freeze() -> dict[str, object]:
    frozen = json.loads((OUT / "g20i_freeze_manifest.json").read_text())
    if frozen["settings"]["threshold"] != THRESHOLD or frozen["settings"]["minimum_top_two_node_margin"] != MIN_MARGIN:
        raise ValueError("Frozen decision rule differs from script")
    for path in SOURCES:
        if frozen["source_sha256"][path.relative_to(ROOT).as_posix()] != sha(path):
            raise ValueError(f"Frozen input changed: {path.name}")
    return frozen


def write_csv(path: Path, rows: list[dict[str, object]], columns: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)
    with path.open(newline="", encoding="utf-8") as handle:
        if len(list(csv.DictReader(handle))) != len(rows):
            raise ValueError("CSV round-trip row count mismatch")


def structural_references(orders: list[dict[str, object]]) -> dict[str, str]:
    wb = load_workbook(SOURCES[1], read_only=True, data_only=True)
    values = wb.active.values
    head = next(values)
    ix = {name: pos for pos, name in enumerate(head)}
    equipment, serial = defaultdict(set), defaultdict(set)
    for row in values:
        floc = str(row[ix["Functional Location"]] or "").strip()
        for index, column in [(equipment, "Equipment"), (serial, "Manufacturer's Serial Number")]:
            key = str(row[ix[column]] or "").strip().lstrip("0")
            if key and floc:
                index[key].add(floc)
    wb.close()
    reference = {}
    for order in orders:
        matches = set()
        for index, field in [(equipment, "assetId"), (serial, "assetSerialNo")]:
            key = str(order.get(field) or "").strip().lstrip("0")
            if key:
                matches.update(index.get(key, ()))
        if len(matches) == 1:
            reference[str(order["id"])] = next(iter(matches))
    return reference


def run() -> None:
    from sentence_transformers import SentenceTransformer

    frozen = check_freeze()
    if (OUT / "g20i_run_manifest.json").exists():
        raise RuntimeError("G2.0i run already recorded")
    nodes, children = load_nodes()
    valid, groups, codes = load_catalog()
    rows = read_g12()
    concepts, hits, reconciliation = load_concepts()
    if reconciliation != frozen["concept_reconciliation"]:
        raise ValueError("Concept reconciliation drift")
    orders = json.loads(SOURCES[3].read_text(encoding="utf-8"))
    if len(orders) != 10749 or len({str(o["id"]) for o in orders}) != 10749:
        raise ValueError("Source order count/keys drift")
    refs = structural_references(orders)
    order_keys = {str(o["id"]) for o in orders}
    if {r["order_id"] for r in rows} != order_keys:
        raise ValueError("G1.2/source order IDs differ")

    turbines = {}
    for row in rows:
        if row["match_status"] != "matched_asset_node":
            continue
        root = row["matched_floc"]
        if root not in nodes:
            raise ValueError("G1.2 turbine absent in IH06")
        if root in turbines and turbines[root]["site_key"] != row["site_key"]:
            raise ValueError("Same turbine assigned to multiple sites")
        turbines[root] = {"site_key": row["site_key"]}
    inventory = []
    candidates = {}
    descriptions = set()
    for root, meta in sorted(turbines.items()):
        descendants = descendants_of(root, children)
        by_depth = defaultdict(list)
        usable = []
        for node in descendants:
            if not node.startswith(root + "-") or node.split("-")[0] != root.split("-")[0]:
                raise ValueError("Candidate escaped turbine/site subtree")
            profile, source, walked = effective_profile(node, nodes, valid)
            label = normalised(nodes[node]["description"])
            leaf = not children.get(node)
            depth = len(node.split("-"))
            by_depth[depth].append((profile, bool(label), leaf))
            if profile and label:
                usable.append((node, profile, source, walked, label, leaf))
                descriptions.add(label)
        candidates[root] = usable
        for depth, items in sorted(by_depth.items()):
            inventory.append({
                "site_key": meta["site_key"], "turbine_hash": short_hash("IH06NODE", root),
                "depth": depth, "node_count": len(items),
                "profile_resolvable_count": sum(bool(x[0]) for x in items),
                "text_and_profile_candidate_count": sum(bool(x[0]) and x[1] for x in items),
                "leaf_count": sum(x[2] for x in items),
                "profiled_leaf_count": sum(bool(x[0]) and x[2] for x in items),
            })
    print(f"IH06 turbine nodes={len(turbines)} candidates={sum(map(len,candidates.values()))} unique_descriptions={len(descriptions)}", flush=True)

    concept_ids = sorted(concepts)
    concept_idx = {cid: i for i, cid in enumerate(concept_ids)}
    description_list = sorted(descriptions)
    desc_idx = {label: i for i, label in enumerate(description_list)}
    model = SentenceTransformer(MODEL, local_files_only=True)
    concept_vectors = np.asarray(model.encode(
        [normalised(concepts[cid]) for cid in concept_ids], normalize_embeddings=True,
        convert_to_numpy=True, batch_size=64, show_progress_bar=False,
    ), dtype=np.float32)
    batches = []
    for start in range(0, len(description_list), 512):
        batches.append(np.asarray(model.encode(
            description_list[start:start + 512], normalize_embeddings=True,
            convert_to_numpy=True, batch_size=64, show_progress_bar=False,
        ), dtype=np.float32))
    desc_vectors = np.vstack(batches)
    score_by_turbine = {
        root: (concept_vectors @ desc_vectors[[desc_idx[c[4]] for c in choices]].T)
        for root, choices in candidates.items() if choices
    }
    print("Semantic scoring matrix ready", flush=True)

    order_out, funnel = [], []
    for row in rows:
        root = row["matched_floc"] if row["match_status"] == "matched_asset_node" else ""
        unit = unit_hash(row["order_id"])
        detected = sorted(hits.get(unit, ()))
        status, reason = "abstained", ""
        best_i, runner_i, best_score, runner_score = -1, -1, None, None
        choices = candidates.get(root, [])
        if not root:
            reason = "no_structural_turbine_match"
        elif not detected:
            reason = "no_assigned_object_part_concept"
        elif not choices:
            reason = "no_profiled_component_candidate"
        else:
            best_i, best_score, runner_i, runner_score = rank_nodes(
                score_by_turbine[root], [concept_idx[cid] for cid in detected]
            )
            if best_score < THRESHOLD:
                reason = "below_frozen_threshold"
            elif best_score - runner_score < MIN_MARGIN:
                status, reason = "ambiguous", "top_two_node_margin_below_frozen_minimum"
            else:
                status, reason = "resolved", "semantic_candidate_only"
        selected = choices[best_i] if best_i >= 0 else None
        runner = choices[runner_i] if runner_i >= 0 else None
        result = {
            "order_id_hash": row["order_id_hash"], "unit_key_hash": unit,
            "site_key": row["site_key"], "turbine_hash": short_hash("IH06NODE", root) if root else "",
            "status": status, "reason": reason, "detected_concept_count": len(detected),
            "top_node_hash": short_hash("IH06NODE", selected[0]) if selected else "",
            "runner_node_hash": short_hash("IH06NODE", runner[0]) if runner else "",
            "resolved_node_hash": short_hash("IH06NODE", selected[0]) if selected and status == "resolved" else "",
            "score": round(best_score, 6) if best_score is not None else "",
            "runner_score": round(runner_score, 6) if runner_score is not None and runner_i >= 0 else "",
            "margin": round(best_score - runner_score, 6) if runner_i >= 0 else "",
            "resolved_node_is_leaf": str(selected[5]).lower() if selected and status == "resolved" else "",
            "resolved_node_depth": len(selected[0].split("-")) if selected and status == "resolved" else "",
            "resolved_rbnr": selected[1] if selected and status == "resolved" else "",
            "resolved_profile_source": selected[2] if selected and status == "resolved" else "",
            "anchor_source": "domain_vocabulary", "evaluation_independence": "derived_from_rules",
            "label_generation_method": "semantic_component_node_resolution_v1",
            "independent_code_evaluation_eligible": False,
        }
        order_out.append(result)
        if status == "resolved":
            turbine_profile, _, _ = effective_profile(root, nodes, valid)
            for cat in TYPES:
                component_groups = groups[(selected[1], cat)]
                turbine_groups = groups[(turbine_profile, cat)] if turbine_profile else set()
                funnel.append({
                    "order_id_hash": row["order_id_hash"], "site_key": row["site_key"],
                    "resolved_node_hash": result["resolved_node_hash"],
                    "component_rbnr": selected[1], "turbine_rbnr": turbine_profile,
                    "catalog_type": cat, "target": TYPE_NAMES[cat],
                    "component_group_count": len(component_groups),
                    "component_code_pair_count": sum(codes[(cat, g)] for g in component_groups),
                    "turbine_group_count": len(turbine_groups) if turbine_profile else "",
                    "turbine_code_pair_count": sum(codes[(cat, g)] for g in turbine_groups) if turbine_profile else "",
                    "answer_space_claim": "text_derived_profile_candidate_not_verified_code_classification",
                })

    if len(order_out) != 10749 or len({r["order_id_hash"] for r in order_out}) != 10749:
        raise ValueError("Output does not cover each order exactly once")
    if len(funnel) != 5 * sum(r["status"] == "resolved" for r in order_out):
        raise ValueError("Profile funnel target count drift")
    write_csv(OUT / "g20i_inventory_by_turbine_depth_sanitized.csv", inventory,
              ["site_key", "turbine_hash", "depth", "node_count", "profile_resolvable_count", "text_and_profile_candidate_count", "leaf_count", "profiled_leaf_count"])
    write_csv(OUT / "g20i_order_resolution_sanitized.csv", order_out,
              ["order_id_hash", "unit_key_hash", "site_key", "turbine_hash", "status", "reason", "detected_concept_count", "top_node_hash", "runner_node_hash", "resolved_node_hash", "score", "runner_score", "margin", "resolved_node_is_leaf", "resolved_node_depth", "resolved_rbnr", "resolved_profile_source", "anchor_source", "evaluation_independence", "label_generation_method", "independent_code_evaluation_eligible"])
    write_csv(OUT / "g20i_profile_funnel_sanitized.csv", funnel,
              ["order_id_hash", "site_key", "resolved_node_hash", "component_rbnr", "turbine_rbnr", "catalog_type", "target", "component_group_count", "component_code_pair_count", "turbine_group_count", "turbine_code_pair_count", "answer_space_claim"])

    status_counts = Counter(r["status"] for r in order_out)
    reason_counts = Counter(r["reason"] for r in order_out)
    leaf_counts = Counter(r["resolved_node_is_leaf"] for r in order_out if r["status"] == "resolved")
    structural = Counter()
    by_order = {str(o["id"]): o for o in orders}
    for source, result in zip(rows, order_out, strict=True):
        reference = refs.get(source["order_id"])
        if reference:
            structural["orders_with_unique_ih08_floc"] += 1
            if result["status"] == "resolved":
                structural["resolved_with_independent_ih08_floc"] += 1
                if result["resolved_node_hash"] == short_hash("IH06NODE", reference):
                    structural["exact_node_agreement"] += 1
        if str(by_order[source["order_id"]].get("rdsPpReference") or "").strip() in nodes:
            structural["rdspp_exact_ih06_floc"] += 1
    by_site = defaultdict(Counter)
    for r in order_out:
        by_site[r["site_key"]][r["status"]] += 1
    summary = {
        "status_counts": dict(status_counts), "reason_counts": dict(reason_counts),
        "resolved_leaf_status": dict(leaf_counts),
        "per_site_status": {site: dict(count) for site, count in sorted(by_site.items())},
        "independent_structural_evidence": dict(structural),
        "inventory_turbine_nodes": len(turbines),
        "inventory_descendant_nodes": sum(r["node_count"] for r in inventory),
        "inventory_profiled_nodes": sum(r["profile_resolvable_count"] for r in inventory),
        "inventory_leaf_nodes": sum(r["leaf_count"] for r in inventory),
        "concept_reconciliation": reconciliation,
        "no_accuracy_claim": True, "denominator_changed": False,
    }
    memo = [
        "# G2.0i - component-node diagnostic resolution",
        "",
        "B1_RELATIONAL only. Frozen MiniLM cosine >= 0.60, node margin >= 0.05, semantic_normalisation_v2.",
        "40 final Object Part concepts; the 3 unassigned concepts in the historical 7,668-unit count were excluded, leaving 7,393 units with an assigned concept.",
        "",
        f"- Orders: {len(order_out):,}; resolved candidates: {status_counts['resolved']:,}; ambiguous: {status_counts['ambiguous']:,}; abstained: {status_counts['abstained']:,}.",
        f"- Resolved candidates that are terminal IH06 leaves: {leaf_counts['true']:,}; non-leaf candidates: {leaf_counts['false']:,}.",
        f"- Reasons: {dict(reason_counts)}.",
        f"- Site breakdown: {summary['per_site_status']}.",
        f"- Structural references: {dict(structural)}. Site/turbine containment is a scope check, not independent child-node ground truth.",
        "",
        "The component node, RBNR, and all five target code spaces are text-derived candidates. No code assignment accuracy or FLOC accuracy is measured where an independent structural child reference is absent.",
        "Object Part concept evidence used for node selection is ineligible as independent evaluation of the catalog code space restricted by that same node's profile.",
        "Presence of an information type and classification into a catalog code remain separate claims; the latter is not measured here.",
        "No promotion, training, F6 update, or denominator change.",
    ]
    (OUT / "g20i_memo.md").write_text("\n".join(memo) + "\n", encoding="utf-8")
    run_manifest = {
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "freeze_manifest_sha256": sha(OUT / "g20i_freeze_manifest.json"),
        "outputs_sha256": {path.name: sha(path) for path in sorted(OUT.iterdir()) if path.name not in ("g20i_run_manifest.json",)},
        "summary": summary,
    }
    (OUT / "g20i_run_manifest.json").write_text(json.dumps(run_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("freeze", "run"))
    args = parser.parse_args()
    freeze() if args.mode == "freeze" else run()
