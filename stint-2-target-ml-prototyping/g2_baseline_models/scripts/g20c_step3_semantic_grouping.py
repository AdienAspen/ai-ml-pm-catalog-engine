from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.cluster import MiniBatchKMeans
from sklearn.metrics import silhouette_score

PROJECT_ROOT = Path("/home/adien-i7-remote/workspace/fsa_bridge_ml_feasibility")
STINT1_ROOT = PROJECT_ROOT / "stint-1-evidence-ground-truth"
REFERENCE_ROOT = PROJECT_ROOT / "stint-1.1-reference-layer/reference_layer"
STINT2_ROOT = PROJECT_ROOT / "stint-2-target-ml-prototyping"
OUT = STINT2_ROOT / "g2_baseline_models/outputs/g20_corpus_native_domain_vocab"

FILTERED_TERMS = OUT / "g20c_filtered_terms_sanitized.csv"
EXTERNAL_REFERENCE = OUT / "g20c_external_reference_augmentation_sanitized.csv"
ZEUS_SCAFFOLD = (
    REFERENCE_ROOT / "semantic_normalisation/zeus_semantic_scaffold_v1.csv"
)
IEC_NODES = (
    REFERENCE_ROOT / "source_designations/iec_logical_nodes_21_reference_v1.csv"
)
EXTERNAL_FAILURE_VOCAB = (
    STINT1_ROOT
    / "phase_1_lexical/outputs/canonical_vocabulary/external_failure_vocabulary_v1.csv"
)

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
RANDOM_STATE = 20260921
K_CANDIDATES = [256, 384, 512, 768]
SILHOUETTE_SAMPLE_SIZE = 3000
MIN_MEMBER_SIMILARITY = 0.50
MIN_CONCEPT_MEMBERS = 2
ACTIVITY_SCORE_THRESHOLD = 0.40
OBJECT_PART_SCORE_THRESHOLD = 0.40
TARGET_MARGIN = 0.05
ACTION_SHARE_THRESHOLD = 0.15

OPERATIONAL_ENTITY_TOKENS = {
    "aes",
    "ge",
    "latigo",
    "pioneer",
    "takkion",
    "vestas",
}

ACTION_TOKENS = {
    "adjust",
    "adjusted",
    "align",
    "aligned",
    "assemble",
    "assembled",
    "calibrate",
    "calibrated",
    "change",
    "changed",
    "clean",
    "cleaned",
    "cleaning",
    "close",
    "closed",
    "commission",
    "commissioned",
    "connect",
    "connected",
    "correct",
    "corrected",
    "diagnose",
    "diagnosed",
    "disconnect",
    "disconnected",
    "drain",
    "drained",
    "fill",
    "filled",
    "inspect",
    "inspected",
    "inspection",
    "inspections",
    "install",
    "installed",
    "installation",
    "installations",
    "lubricate",
    "lubricated",
    "maintenance",
    "measure",
    "measured",
    "measurement",
    "measurements",
    "monitor",
    "monitored",
    "monitoring",
    "open",
    "opened",
    "perform",
    "performed",
    "remove",
    "removed",
    "removal",
    "removals",
    "repair",
    "repaired",
    "replace",
    "replaced",
    "replacement",
    "replacements",
    "reset",
    "restore",
    "restored",
    "retrofit",
    "retrofitted",
    "service",
    "serviced",
    "test",
    "tested",
    "tighten",
    "tightened",
    "torque",
    "torqued",
    "troubleshoot",
    "troubleshooting",
    "update",
    "updated",
    "upgrade",
    "upgraded",
    "verify",
    "verified",
    "wash",
    "washed",
}

COMPONENT_TOKENS = {
    "actuator",
    "anemometer",
    "battery",
    "bearing",
    "blade",
    "bolt",
    "brake",
    "bushing",
    "cable",
    "connector",
    "contactor",
    "controller",
    "converter",
    "cooler",
    "cylinder",
    "detector",
    "encoder",
    "fan",
    "filter",
    "fuse",
    "gearbox",
    "generator",
    "hatch",
    "hose",
    "manifold",
    "module",
    "motor",
    "panel",
    "pipe",
    "pump",
    "radiator",
    "relay",
    "ring",
    "sensor",
    "shaft",
    "stack",
    "switch",
    "transformer",
    "valve",
}


def stable_id(prefix: str, value: str, length: int = 14) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:length]
    return f"{prefix}-{digest}"


def normalise_rows(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return matrix / norms


def has_action_token(term: object) -> bool:
    return bool(set(str(term).lower().split()) & ACTION_TOKENS)


def has_component_token(term: object) -> bool:
    return bool(set(str(term).lower().split()) & COMPONENT_TOKENS)


def has_operational_entity_token(term: object) -> bool:
    return bool(set(str(term).lower().split()) & OPERATIONAL_ENTITY_TOKENS)


def build_target_assignment_sources() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    zeus = pd.read_csv(ZEUS_SCAFFOLD).fillna("")
    activity = zeus[zeus["zeus_category"].eq("maintenance_measure")]
    for _, row in activity.iterrows():
        rows.append(
            {
                "anchor_id": str(row["concept_id"]),
                "target": "Activity",
                "anchor_kind": "reference_definition",
                "anchor_text": f"maintenance measure {row['working_definition']}",
                "source_artifact": (
                    "../stint-1.1-reference-layer/reference_layer/"
                    "semantic_normalisation/zeus_semantic_scaffold_v1.csv"
                ),
                "evidence_type": "reference_evidence",
                "construction_method": "transcribed_from_frozen_reference",
                "evaluation_text_used": False,
                "g20_prototype_reused": False,
            }
        )
    rows.append(
        {
            "anchor_id": "G20C-ACTIVITY-GENERIC",
            "target": "Activity",
            "anchor_kind": "generic_target_descriptor",
            "anchor_text": "maintenance action performed on equipment",
            "source_artifact": "analyst_authored_no_evaluation_text",
            "evidence_type": "expert_inference",
            "construction_method": "analyst_authored_generic_target_descriptor",
            "evaluation_text_used": False,
            "g20_prototype_reused": False,
        }
    )

    iec = pd.read_csv(IEC_NODES).fillna("")
    physical = iec[
        iec["ih06_contrast_scope"].isin({"physical_subsystem", "physical_root_context"})
    ]
    for _, row in physical.iterrows():
        rows.append(
            {
                "anchor_id": str(row["concept_id"]),
                "target": "Object Part",
                "anchor_kind": "reference_component_scope",
                "anchor_text": str(row["published_description"]),
                "source_artifact": (
                    "../stint-1.1-reference-layer/reference_layer/"
                    "source_designations/iec_logical_nodes_21_reference_v1.csv"
                ),
                "evidence_type": "reference_evidence",
                "construction_method": "transcribed_from_frozen_reference",
                "evaluation_text_used": False,
                "g20_prototype_reused": False,
            }
        )

    external = pd.read_csv(EXTERNAL_FAILURE_VOCAB).fillna("")
    for subsystem in sorted(
        value
        for value in set(external["subsystem"].astype(str))
        if value.strip()
    ):
        rows.append(
            {
                "anchor_id": stable_id("G20C-SUBSYSTEM", subsystem),
                "target": "Object Part",
                "anchor_kind": "reference_subsystem_scope",
                "anchor_text": subsystem.replace("_", " "),
                "source_artifact": (
                    "../stint-1-evidence-ground-truth/phase_1_lexical/outputs/"
                    "canonical_vocabulary/external_failure_vocabulary_v1.csv"
                ),
                "evidence_type": "reference_evidence",
                "construction_method": "distinct_scope_from_frozen_reference",
                "evaluation_text_used": False,
                "g20_prototype_reused": False,
            }
        )
    rows.append(
        {
            "anchor_id": "G20C-OBJECT-PART-GENERIC",
            "target": "Object Part",
            "anchor_kind": "generic_target_descriptor",
            "anchor_text": "physical component or replaceable part of equipment",
            "source_artifact": "analyst_authored_no_evaluation_text",
            "evidence_type": "expert_inference",
            "construction_method": "analyst_authored_generic_target_descriptor",
            "evaluation_text_used": False,
            "g20_prototype_reused": False,
        }
    )
    for token in sorted(ACTION_TOKENS):
        rows.append(
            {
                "anchor_id": stable_id("G20C-ACTION", token),
                "target": "Activity",
                "anchor_kind": "generic_action_token",
                "anchor_text": token,
                "source_artifact": "analyst_authored_no_evaluation_text",
                "evidence_type": "expert_inference",
                "construction_method": "analyst_authored_generic_maintenance_action_lexicon_v1",
                "evaluation_text_used": False,
                "g20_prototype_reused": False,
            }
        )
    for token in sorted(COMPONENT_TOKENS):
        rows.append(
            {
                "anchor_id": stable_id("G20C-COMPONENT", token),
                "target": "Object Part",
                "anchor_kind": "generic_component_head_token",
                "anchor_text": token,
                "source_artifact": "analyst_authored_no_evaluation_text",
                "evidence_type": "expert_inference",
                "construction_method": (
                    "analyst_authored_generic_component_head_lexicon_v1"
                ),
                "evaluation_text_used": False,
                "g20_prototype_reused": False,
            }
        )
    sources = pd.DataFrame(rows)
    if sources["evaluation_text_used"].any() or sources["g20_prototype_reused"].any():
        raise RuntimeError("Target-assignment source independence guard failed")
    return sources


def target_for_cluster(
    activity_score: float,
    object_score: float,
    action_share: float,
    component_share: float,
) -> tuple[str, str]:
    activity_evidence = (
        activity_score >= ACTIVITY_SCORE_THRESHOLD
        and action_share >= ACTION_SHARE_THRESHOLD
    )
    activity_evidence = bool(
        activity_evidence
        or action_share >= 0.35
        or (activity_score >= 0.55 and action_share >= 0.10)
    )
    object_evidence = bool(
        (
            object_score >= OBJECT_PART_SCORE_THRESHOLD
            and component_share >= 0.10
        )
        or component_share >= 0.35
    )
    if activity_evidence and object_evidence:
        if (
            action_share >= 0.35
            and component_share < 0.35
            and object_score - activity_score < 0.10
        ):
            return "Activity", "strong_action_share_without_object_margin"
        if component_share >= 0.35 and action_share < 0.35:
            return "Object Part", "strong_component_head_share"
        if activity_score - object_score >= TARGET_MARGIN and action_share >= 0.25:
            return "Activity", "activity_score_margin_with_action_support"
        if object_score - activity_score >= TARGET_MARGIN and action_share < 0.25:
            return "Object Part", "object_score_margin_with_low_action_share"
        return "ambiguous", "both_target_signals_without_margin"
    if activity_evidence:
        return "Activity", "activity_anchor_plus_action_share"
    if object_evidence:
        return "Object Part", "object_anchor_plus_component_head_share"
    return "unassigned", "insufficient_target_evidence"


def target_concentration_diagnostics(
    model: MiniBatchKMeans,
    embeddings: np.ndarray,
    terms: pd.DataFrame,
    activity_anchors: np.ndarray,
    object_anchors: np.ndarray,
) -> dict[str, object]:
    labels = model.labels_
    centers = normalise_rows(model.cluster_centers_.astype(np.float32))
    member_similarity = np.sum(embeddings * centers[labels], axis=1)
    assignments = []
    concept_counts = {"Activity": 0, "Object Part": 0}
    for cluster_number in range(model.n_clusters):
        member_idx = np.flatnonzero(
            (labels == cluster_number)
            & (member_similarity >= MIN_MEMBER_SIMILARITY)
        )
        if len(member_idx) < MIN_CONCEPT_MEMBERS:
            continue
        cluster = terms.iloc[member_idx]
        center = centers[cluster_number]
        activity_score = float(np.max(activity_anchors @ center))
        object_score = float(np.max(object_anchors @ center))
        action_share = float(cluster["candidate_term"].map(has_action_token).mean())
        component_share = float(
            cluster["candidate_term"].map(has_component_token).mean()
        )
        target, _ = target_for_cluster(
            activity_score,
            object_score,
            action_share,
            component_share,
        )
        if target not in concept_counts:
            continue
        concept_counts[target] += 1
        for path, path_members in cluster.groupby("path_bucket"):
            assignments.append(
                {
                    "cluster_number": cluster_number,
                    "target": target,
                    "path_bucket": path,
                    "member_rows": len(path_members),
                    "unit_mention_weight": int(path_members["units_with_term"].sum()),
                }
            )
    frame = pd.DataFrame(assignments)
    max_surface_share = 0.0
    max_weight_share = 0.0
    if not frame.empty:
        for _, group in frame.groupby(["target", "path_bucket"]):
            member_total = int(group["member_rows"].sum())
            weight_total = int(group["unit_mention_weight"].sum())
            max_surface_share = max(
                max_surface_share,
                float(group["member_rows"].max() / member_total),
            )
            if weight_total:
                max_weight_share = max(
                    max_weight_share,
                    float(group["unit_mention_weight"].max() / weight_total),
                )
    return {
        "activity_concepts": concept_counts["Activity"],
        "object_part_concepts": concept_counts["Object Part"],
        "max_target_path_surface_variant_share": max_surface_share,
        "max_target_path_unit_mention_weight_share": max_weight_share,
        "activity_object_surface_concentration_gate_pass": bool(
            max_surface_share <= 0.30
        ),
        "unit_mention_weight_warning_over_30pct": bool(max_weight_share > 0.30),
    }


def candidate_models(
    embeddings: np.ndarray,
    terms: pd.DataFrame,
    activity_anchors: np.ndarray,
    object_anchors: np.ndarray,
) -> tuple[MiniBatchKMeans, pd.DataFrame]:
    rng = np.random.default_rng(RANDOM_STATE)
    sample_size = min(SILHOUETTE_SAMPLE_SIZE, len(embeddings))
    sample_idx = np.sort(rng.choice(len(embeddings), sample_size, replace=False))
    records = []
    best_model = None
    best_metric = -np.inf
    fallback_model = None
    fallback_metric = (np.inf, np.inf)
    for k in K_CANDIDATES:
        model = MiniBatchKMeans(
            n_clusters=k,
            random_state=RANDOM_STATE,
            batch_size=2048,
            n_init=3,
            max_iter=100,
            reassignment_ratio=0.01,
        )
        labels = model.fit_predict(embeddings)
        centers = normalise_rows(model.cluster_centers_.astype(np.float32))
        member_similarity = np.sum(embeddings * centers[labels], axis=1)
        sizes = np.bincount(labels, minlength=k)
        sample_score = float(
            silhouette_score(
                embeddings[sample_idx],
                labels[sample_idx],
                metric="cosine",
            )
        )
        max_share = float(sizes.max() / len(labels))
        target_diagnostics = target_concentration_diagnostics(
            model,
            embeddings,
            terms,
            activity_anchors,
            object_anchors,
        )
        valid_for_selection = bool(
            max_share <= 0.30
            and target_diagnostics[
                "activity_object_surface_concentration_gate_pass"
            ]
        )
        records.append(
            {
                "k": k,
                "silhouette_cosine_sample": round(sample_score, 6),
                "sample_size": sample_size,
                "mean_member_centroid_similarity": round(
                    float(member_similarity.mean()), 6
                ),
                "p10_member_centroid_similarity": round(
                    float(np.quantile(member_similarity, 0.10)), 6
                ),
                "median_member_centroid_similarity": round(
                    float(np.median(member_similarity)), 6
                ),
                "largest_cluster_member_share": round(max_share, 6),
                "activity_concepts": target_diagnostics["activity_concepts"],
                "object_part_concepts": target_diagnostics["object_part_concepts"],
                "max_target_path_surface_variant_share": round(
                    float(
                        target_diagnostics["max_target_path_surface_variant_share"]
                    ),
                    6,
                ),
                "max_target_path_unit_mention_weight_share": round(
                    float(
                        target_diagnostics[
                            "max_target_path_unit_mention_weight_share"
                        ]
                    ),
                    6,
                ),
                "activity_object_surface_concentration_gate_pass": (
                    target_diagnostics[
                        "activity_object_surface_concentration_gate_pass"
                    ]
                ),
                "unit_mention_weight_warning_over_30pct": target_diagnostics[
                    "unit_mention_weight_warning_over_30pct"
                ],
                "valid_for_selection": valid_for_selection,
                "selection_rule": (
                    "highest_cosine_silhouette_among_candidates_passing_"
                    "global_and_activity_object_target_path_surface_"
                    "concentration_gates"
                ),
            }
        )
        if valid_for_selection and sample_score > best_metric:
            best_metric = sample_score
            best_model = model
        concentration_metric = (
            float(target_diagnostics["max_target_path_surface_variant_share"]),
            -sample_score,
        )
        if concentration_metric < fallback_metric:
            fallback_metric = concentration_metric
            fallback_model = model
    if best_model is None:
        best_model = fallback_model
    if best_model is None:
        raise RuntimeError("No candidate clustering could be selected")
    metrics = pd.DataFrame(records)
    metrics["selected"] = metrics["k"].eq(best_model.n_clusters)
    metrics["selection_status"] = np.where(
        metrics["selected"] & metrics["valid_for_selection"],
        "selected_gate_pass",
        np.where(
            metrics["selected"],
            "diagnostic_fallback_minimum_surface_concentration_gate_failed",
            "not_selected",
        ),
    )
    return best_model, metrics


def main() -> None:
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    terms = pd.read_csv(FILTERED_TERMS).fillna("")
    if len(terms) != 24841:
        raise RuntimeError(f"Unexpected Step 2 input count: {len(terms)}")
    if set(terms["target"]) != {"unassigned"}:
        raise RuntimeError("Step 3 requires target-neutral input")
    if not terms["retained_step2"].astype(str).str.lower().eq("true").all():
        raise RuntimeError("Step 3 input contains terms not retained by Step 2")

    model = SentenceTransformer(MODEL_NAME)
    term_texts = terms["candidate_term"].astype(str).tolist()
    embeddings = model.encode(
        term_texts,
        batch_size=256,
        normalize_embeddings=True,
        show_progress_bar=True,
    )
    embeddings = np.asarray(embeddings, dtype=np.float32)

    sources = build_target_assignment_sources()
    semantic_sources = sources[
        ~sources["anchor_kind"].isin(
            {"generic_action_token", "generic_component_head_token"}
        )
    ]
    anchor_embeddings = model.encode(
        semantic_sources["anchor_text"].astype(str).tolist(),
        batch_size=64,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    anchor_embeddings = np.asarray(anchor_embeddings, dtype=np.float32)
    activity_anchor_idx = np.flatnonzero(
        semantic_sources["target"].eq("Activity").to_numpy()
    )
    object_anchor_idx = np.flatnonzero(
        semantic_sources["target"].eq("Object Part").to_numpy()
    )
    activity_anchors = anchor_embeddings[activity_anchor_idx]
    object_anchors = anchor_embeddings[object_anchor_idx]

    cluster_model, selection = candidate_models(
        embeddings,
        terms,
        activity_anchors,
        object_anchors,
    )
    labels = cluster_model.labels_
    centers = normalise_rows(cluster_model.cluster_centers_.astype(np.float32))
    member_similarity = np.sum(embeddings * centers[labels], axis=1)
    terms["cluster_number"] = labels
    terms["member_centroid_similarity"] = member_similarity
    terms["passes_member_similarity"] = (
        terms["member_centroid_similarity"] >= MIN_MEMBER_SIMILARITY
    )
    terms["has_action_token"] = terms["candidate_term"].map(has_action_token)
    terms["has_component_token"] = terms["candidate_term"].map(
        has_component_token
    )

    concept_rows = []
    member_rows = []
    cluster_to_concept: dict[int, str] = {}
    cluster_target: dict[int, str] = {}
    for cluster_number in sorted(set(labels)):
        cluster = terms[
            terms["cluster_number"].eq(cluster_number)
            & terms["passes_member_similarity"]
        ].copy()
        if len(cluster) < MIN_CONCEPT_MEMBERS:
            continue
        center = centers[cluster_number]
        activity_score = float(np.max(activity_anchors @ center))
        object_score = float(np.max(object_anchors @ center))
        action_share = float(cluster["has_action_token"].mean())
        component_share = float(cluster["has_component_token"].mean())
        target, target_reason = target_for_cluster(
            activity_score,
            object_score,
            action_share,
            component_share,
        )
        cluster["canonical_rank_score"] = (
            cluster["member_centroid_similarity"]
            + 0.015 * np.log1p(cluster["units_with_term"].astype(float))
            - 0.02 * (cluster["ngram_length"].astype(float) - 1.0)
        )
        canonical = cluster.sort_values(
            ["canonical_rank_score", "ngram_length", "units_with_term", "candidate_term"],
            ascending=[False, True, False, True],
        ).iloc[0]
        member_signature = "|".join(sorted(cluster["term_hash"].astype(str)))
        concept_id = stable_id(
            "G20C-CONCEPT",
            f"{canonical['candidate_term']}|{member_signature}",
        )
        cluster_to_concept[cluster_number] = concept_id
        cluster_target[cluster_number] = target
        variants = (
            cluster.sort_values(
                ["units_with_term", "member_centroid_similarity", "candidate_term"],
                ascending=[False, False, True],
            )["candidate_term"]
            .drop_duplicates()
            .head(20)
            .tolist()
        )
        concept_rows.append(
            {
                "concept_id": concept_id,
                "canonical_label": canonical["candidate_term"],
                "target": target,
                "target_assignment_reason": target_reason,
                "activity_anchor_score": round(activity_score, 6),
                "object_part_anchor_score": round(object_score, 6),
                "action_member_share": round(action_share, 6),
                "component_head_member_share": round(component_share, 6),
                "member_rows": len(cluster),
                "distinct_surface_variants": cluster["candidate_term"].nunique(),
                "paths_present": "|".join(sorted(set(cluster["path_bucket"]))),
                "top_surface_variants": "|".join(variants),
                "mean_member_centroid_similarity": round(
                    float(cluster["member_centroid_similarity"].mean()), 6
                ),
                "minimum_member_centroid_similarity": round(
                    float(cluster["member_centroid_similarity"].min()), 6
                ),
                "embedding_model": MODEL_NAME,
                "grouping_method": "minibatch_kmeans_on_normalized_semantic_embeddings_v1",
                "canonical_selection_method": (
                    "centroid_similarity_plus_log_frequency_minus_length_penalty_v1"
                ),
                "selected_k": cluster_model.n_clusters,
                "evidence_type": "expert_inference",
                "anchor_source": "domain_vocabulary",
                "mapping_status": "not_mapped_step3",
                "raw_operational_values_emitted": False,
            }
        )
        for _, row in cluster.iterrows():
            member_rows.append(
                {
                    "concept_id": concept_id,
                    "canonical_label": canonical["candidate_term"],
                    "target": target,
                    "path_bucket": row["path_bucket"],
                    "candidate_term": row["candidate_term"],
                    "term_hash": row["term_hash"],
                    "ngram_length": int(row["ngram_length"]),
                    "units_with_term": int(row["units_with_term"]),
                    "member_centroid_similarity": round(
                        float(row["member_centroid_similarity"]), 6
                    ),
                    "grouping_status": "semantic_cluster_member",
                    "embedding_model": MODEL_NAME,
                    "raw_operational_values_emitted": False,
                }
            )

    concepts = pd.DataFrame(concept_rows)
    members = pd.DataFrame(member_rows)
    terms["concept_id"] = terms["cluster_number"].map(cluster_to_concept).fillna("")
    terms.loc[~terms["passes_member_similarity"], "concept_id"] = ""
    terms["assigned_target"] = terms["cluster_number"].map(cluster_target).fillna(
        "unassigned"
    )
    terms.loc[~terms["passes_member_similarity"], "assigned_target"] = "unassigned"
    terms["grouping_status_step3"] = np.where(
        terms["concept_id"].astype(bool),
        "semantic_cluster_member",
        "unresolved_or_low_similarity",
    )

    concentration_rows = []
    for (target, path), group in members.groupby(["target", "path_bucket"]):
        by_concept = group.groupby("concept_id").agg(
            member_rows=("candidate_term", "size"),
            unit_mention_weight=("units_with_term", "sum"),
        )
        member_total = int(by_concept["member_rows"].sum())
        weight_total = int(by_concept["unit_mention_weight"].sum())
        for concept_id, row in by_concept.iterrows():
            concentration_rows.append(
                {
                    "target": target,
                    "path_bucket": path,
                    "concept_id": concept_id,
                    "concept_count_in_target_path": len(by_concept),
                    "surface_variant_share": round(
                        float(row["member_rows"] / member_total), 6
                    ),
                    "unit_mention_weight_share": round(
                        float(row["unit_mention_weight"] / weight_total), 6
                    )
                    if weight_total
                    else 0.0,
                    "surface_concentration_over_30pct": bool(
                        row["member_rows"] / member_total > 0.30
                    ),
                    "unit_mention_weight_over_30pct_warning": bool(
                        weight_total
                        and row["unit_mention_weight"] / weight_total > 0.30
                    ),
                    "metric_scope": (
                        "surface_variant_share_is_step3_gate;"
                        "unit_mention_weight_is_non_deduplicated_diagnostic;"
                        "exact_physical_unit_coverage_deferred_to_step5"
                    ),
                }
            )
    concentration = pd.DataFrame(concentration_rows)

    summary_rows = []
    for path in sorted(members["path_bucket"].unique()):
        for target in ["Activity", "Object Part", "ambiguous", "unassigned"]:
            subset = members[
                members["path_bucket"].eq(path) & members["target"].eq(target)
            ]
            concentration_subset = concentration[
                concentration["path_bucket"].eq(path)
                & concentration["target"].eq(target)
            ]
            gate_applies = target in {"Activity", "Object Part"}
            summary_rows.append(
                {
                    "path_bucket": path,
                    "target": target,
                    "concepts": subset["concept_id"].nunique(),
                    "member_rows": len(subset),
                    "max_surface_variant_share": round(
                        float(
                            concentration_subset["surface_variant_share"].max()
                        ),
                        6,
                    )
                    if not concentration_subset.empty
                    else 0.0,
                    "max_unit_mention_weight_share": round(
                        float(
                            concentration_subset["unit_mention_weight_share"].max()
                        ),
                        6,
                    )
                    if not concentration_subset.empty
                    else 0.0,
                    "surface_concentration_gate_applies": gate_applies,
                    "surface_concentration_gate_pass": bool(
                        not gate_applies
                        or concentration_subset.empty
                        or not concentration_subset[
                            "surface_concentration_over_30pct"
                        ].any()
                    ),
                    "unit_mention_weight_over_30pct_warning": bool(
                        not concentration_subset.empty
                        and concentration_subset[
                            "unit_mention_weight_over_30pct_warning"
                        ].any()
                    ),
                }
            )
    summary = pd.DataFrame(summary_rows)

    external = pd.read_csv(EXTERNAL_REFERENCE).fillna("")
    external_rows = []
    for _, row in external.iterrows():
        external_rows.append(
            {
                "reference_entry_id": row["reference_entry_id"],
                "reference_term": row["reference_term"],
                "reference_target": row["reference_target"],
                "step3_status": "retained_separate_out_of_scope_target",
                "included_in_clustering": False,
                "included_in_target_assignment": False,
                "included_in_concentration": False,
                "evaluation_text_used": False,
            }
        )
    external_status = pd.DataFrame(external_rows)

    if len(terms) != len(pd.read_csv(FILTERED_TERMS)):
        raise RuntimeError("Step 3 input parity failed")
    if concepts["concept_id"].duplicated().any():
        raise RuntimeError("Duplicate concept IDs")
    if not members["target"].isin(
        {"Activity", "Object Part", "ambiguous", "unassigned"}
    ).all():
        raise RuntimeError("Unexpected assigned target")
    forbidden_source = sources["source_artifact"].astype(str).str.contains(
        r"g0_independent_evaluation|evaluation_set", case=False, regex=True
    )
    if forbidden_source.any():
        raise RuntimeError("Evaluation source leaked into target assignment")
    operational_hits = pd.concat(
        [
            concepts["canonical_label"],
            members["candidate_term"],
            terms["candidate_term"],
        ],
        ignore_index=True,
    ).map(has_operational_entity_token)
    if operational_hits.any():
        raise RuntimeError("Operational entity token leaked into Step 3 output")

    selection.to_csv(
        OUT / "g20c_step3_cluster_selection_sanitized.csv",
        index=False,
        lineterminator="\n",
    )
    sources.to_csv(
        OUT / "g20c_step3_target_assignment_sources_sanitized.csv",
        index=False,
        lineterminator="\n",
    )
    concepts.sort_values(["target", "canonical_label"]).to_csv(
        OUT / "g20c_domain_vocabulary_sanitized.csv",
        index=False,
        lineterminator="\n",
    )
    members.sort_values(["target", "concept_id", "path_bucket", "candidate_term"]).to_csv(
        OUT / "g20c_concept_members_sanitized.csv",
        index=False,
        lineterminator="\n",
    )
    terms.sort_values(["path_bucket", "candidate_term"]).to_csv(
        OUT / "g20c_step3_grouping_decisions_sanitized.csv",
        index=False,
        lineterminator="\n",
    )
    concentration.sort_values(["target", "path_bucket", "concept_id"]).to_csv(
        OUT / "g20c_step3_concentration_by_target_path_sanitized.csv",
        index=False,
        lineterminator="\n",
    )
    summary.to_csv(
        OUT / "g20c_step3_grouping_summary_sanitized.csv",
        index=False,
        lineterminator="\n",
    )
    external_status.to_csv(
        OUT / "g20c_step3_external_reference_status_sanitized.csv",
        index=False,
        lineterminator="\n",
    )

    summary_json = {
        "input_terms": len(terms),
        "selected_k": int(cluster_model.n_clusters),
        "concepts": len(concepts),
        "grouped_member_rows": len(members),
        "unresolved_member_rows": int(
            terms["grouping_status_step3"].eq("unresolved_or_low_similarity").sum()
        ),
        "embedding_model": MODEL_NAME,
        "grouping_method": "minibatch_kmeans_on_normalized_semantic_embeddings_v1",
        "target_assignment": (
            "post_grouping_reference_anchors_plus_declared_action_and_"
            "component_lexicons_v1"
        ),
        "evaluation_text_used": False,
        "g20_prototype_reused": False,
        "operational_entity_token_hits": int(operational_hits.sum()),
        "all_target_path_surface_concentration_gates_pass": bool(
            summary.loc[
                summary["surface_concentration_gate_applies"],
                "surface_concentration_gate_pass",
            ].all()
        ),
        "any_unit_mention_weight_warning_over_30pct": bool(
            summary["unit_mention_weight_over_30pct_warning"].any()
        ),
    }
    (OUT / "g20c_step3_grouping_summary_sanitized.json").write_text(
        json.dumps(summary_json, indent=2), encoding="utf-8"
    )
    memo = f"""# G2.0c Step 3 - Semantic Grouping

## Method

The {len(terms):,} Step 2 terms were embedded with `{MODEL_NAME}` and grouped with
MiniBatchKMeans over normalized semantic embeddings. String distance was not used.
Candidate cluster counts were compared using cosine silhouette on a deterministic
{SILHOUETTE_SAMPLE_SIZE:,}-term sample; `k={cluster_model.n_clusters}` was selected.

Members below cosine {MIN_MEMBER_SIMILARITY:.2f} or clusters with fewer than
{MIN_CONCEPT_MEMBERS} accepted members remain unresolved. The resulting vocabulary
contains {len(concepts):,} concepts and {len(members):,} grouped path-term rows.

## Target assignment

Target assignment occurred only after semantic grouping. It used frozen ZEUS/IEC/F1c2
reference scopes, one generic descriptor per target, a declared generic maintenance
action lexicon, and a declared generic component-head lexicon. No G2.0 prototype or
evaluation text was reused; both lexical lists are registered as analyst-authored rather
than corpus-derived evidence. Object Part was never assigned as the residual class;
insufficient or conflicting evidence yields `unassigned` or `ambiguous`.

## Concentration

Concentration is reported separately by target and path. The Step 3 blocking gate is
surface-variant concentration, the quantity directly governed by semantic grouping.
Non-deduplicated unit-mention weight is retained as a diagnostic warning only: overlapping
n-grams can count the same physical unit repeatedly (for example, `blades`, `ground blades`,
and `high ground blades`). Exact `physical_record x target` coverage requires the unit-level
pass in Step 5 and is not inferred here.

## External reference layer

The three B2 external reference terms remain separate because their frozen target is
Damage, outside this Activity/Object Part grouping scope. They did not affect clustering,
target assignment, or concentration.

## Boundaries

No SAP mapping, catalogue-gap decision, denominator change, candidate promotion, model
training, or G2.0 rerun occurred.
"""
    (OUT / "g20c_step3_semantic_grouping_memo.md").write_text(
        memo, encoding="utf-8"
    )

    print(selection.to_string(index=False))
    print(summary.to_string(index=False))
    print(json.dumps(summary_json, indent=2))


if __name__ == "__main__":
    main()
