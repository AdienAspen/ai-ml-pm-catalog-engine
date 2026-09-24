"""Candidate-only 0..N mapping from the frozen Step 3b vocabulary."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

import numpy as np
import pandas as pd
from g20c_step3_semantic_grouping import COMPONENT_TOKENS
from openpyxl import load_workbook
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "g2_baseline_models/outputs/g20_corpus_native_domain_vocab"
CATALOG = ROOT.parent / (
    "data/interim/extracted_source/package_001_37cac7fe/Data/References/"
    "Wind Catalog Group and Codes Final v4.xlsx"
)
VOCAB = OUT / "g20c_domain_vocabulary_step3b_sanitized.csv"
MEMBERS = OUT / "g20c_concept_members_step3b_sanitized.csv"
EXCLUSIONS = OUT / "g20c_step3b_construction_exclusions_sanitized.csv"
MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
TARGET_CATALOG = {"Activity": "A", "Object Part": "B"}
MIN_SCORE = 0.60
NEAR_BEST_MARGIN = 0.08
STRONG_SCORE = 0.80
MEDIUM_SCORE = 0.70
SOURCE_ANOMALIES = {("A", "PMKNFAN", "PMKN"): "system_description_in_activity_catalogue"}
# Mapping-only morphology. This does not change the frozen vocabulary or target assignment.
MORPHOLOGY = {
    "cleaned": "clean",
    "cleaning": "clean",
    "installed": "install",
    "installation": "install",
    "removed": "remove",
    "replaced": "replace",
    "replacement": "replace",
    "tested": "test",
    "testing": "test",
    "adjusted": "adjust",
    "adjustment": "adjust",
    "calibrated": "calibrate",
    "repaired": "repair",
    "lubricated": "lubricate",
    "tightened": "tighten",
    "secured": "secure",
    "added": "add",
    "bypassed": "bypass",
    "flushed": "flush",
    "detection": "detector",
}
ACTION_HEADS = set(MORPHOLOGY.values()) - {"detector"} | {"reset", "setting"}
COMPONENT_HEADS = set(COMPONENT_TOKENS) | {"terminal", "duct", "crane", "lock", "box"}
MAPPING_COLUMNS = [
    "concept_id",
    "canonical_label",
    "target",
    "catalogue",
    "code_group",
    "code",
    "catalogue_description",
    "catalogue_key",
    "source_sheet",
    "source_artifact",
    "source_row",
    "match_confidence",
    "confidence_kind",
    "tier",
    "evidence_type",
    "anchor_source",
    "mapping_method",
    "mapping_status",
    "lexical_support",
    "equivalence_status",
    "candidate_rank",
    "candidate_count",
    "distinct_candidate_descriptions",
    "ambiguity_status",
    "profile_selection_status",
    "concept_inspected_during_construction",
    "eligible_for_future_evaluation",
    "evaluation_exclusion",
    "path",
    "evaluation_set_type",
    "threshold",
    "margin",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalize(value: object) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", str(value).lower()))


def lemmas(value: str) -> list[str]:
    result = []
    for token in normalize(value).split():
        token = MORPHOLOGY.get(token, token)
        if token.endswith("s") and len(token) > 3 and not token.endswith(("ss", "us")):
            token = token[:-1]
        result.append(token)
    return result


def lexical_support(query: str, description: str, target: str) -> str:
    allowed = ACTION_HEADS if target == "Activity" else COMPONENT_HEADS
    query_heads = [word for word in lemmas(query) if word in allowed]
    if not query_heads:
        return ""
    # The last component head prevents yaw motor -> yaw bearing or pump -> lubricant.
    required = set(query_heads if target == "Activity" else query_heads[-1:])
    return "|".join(sorted(required & set(lemmas(description))))


def reference(path: Path) -> str:
    return os.path.relpath(path, ROOT)


def tier(score: float) -> str:
    if score >= STRONG_SCORE:
        return "candidate_strong"
    if score >= MEDIUM_SCORE:
        return "candidate_medium"
    return "candidate_weak"


def accepted_indices(scores: np.ndarray) -> np.ndarray:
    if not len(scores):
        return np.array([], dtype=int)
    return np.flatnonzero(
        (scores >= MIN_SCORE) & (scores >= float(scores.max()) - NEAR_BEST_MARGIN)
    )


def read_catalogue() -> pd.DataFrame:
    rows = []
    workbook = load_workbook(CATALOG, read_only=True, data_only=True)
    try:
        for catalog in TARGET_CATALOG.values():
            sheet = f"Catalog. {catalog} - Group and Code"
            values = workbook[sheet].iter_rows(values_only=True)
            headers = next(values)
            for number, values_row in enumerate(values, start=2):
                source = dict(zip(headers, values_row, strict=True))
                if not source.get("Code"):
                    continue
                key = tuple(str(source[k] or "").strip() for k in ["Catalog", "Code Group", "Code"])
                description = str(source.get("Short Text for Code") or "").strip()
                if key[0] != catalog or not all(key) or not description:
                    raise ValueError(f"Invalid catalogue record in {sheet}, row {number}")
                rows.append(
                    {
                        "catalogue": key[0],
                        "code_group": key[1],
                        "code": key[2],
                        "catalogue_description": description,
                        "normalized_description": normalize(description),
                        "catalogue_key": "|".join(key),
                        "source_artifact": reference(CATALOG),
                        "source_sheet": sheet,
                        "source_row": number,
                        "source_anomaly": SOURCE_ANOMALIES.get(key, ""),
                    }
                )
    finally:
        workbook.close()
    result = pd.DataFrame(rows)
    if result.catalogue_key.duplicated().any():
        raise ValueError("Catalogue composite key is not unique")
    return result


def write_csv(frame: pd.DataFrame, path: Path) -> None:
    frame.to_csv(path, index=False, lineterminator="\n")
    reread = pd.read_csv(path, dtype=str, keep_default_na=False)
    assert len(reread) == len(frame) and list(reread.columns) == list(frame.columns)


def main(output: Path) -> None:
    inputs = [VOCAB, MEMBERS, EXCLUSIONS, CATALOG]
    hashes = {reference(path): sha256(path) for path in inputs}
    vocabulary = pd.read_csv(VOCAB, keep_default_na=False)
    exclusions = pd.read_csv(EXCLUSIONS, keep_default_na=False)
    assert vocabulary.concept_id.is_unique and len(vocabulary) == 256
    assert vocabulary.target.value_counts().to_dict() == {
        "Activity": 24,
        "Object Part": 43,
        "ambiguous": 4,
        "unassigned": 185,
    }
    reviewed = set(exclusions.concept_id)
    assert len(reviewed) == 13
    catalogue = read_catalogue()
    eligible_catalogue = catalogue[catalogue.source_anomaly.eq("")].copy()
    descriptions = (
        eligible_catalogue[["catalogue", "normalized_description"]]
        .drop_duplicates()
        .sort_values(["catalogue", "normalized_description"])
        .reset_index(drop=True)
    )
    assigned = vocabulary[vocabulary.target.isin(TARGET_CATALOG)].sort_values("concept_id")
    model = SentenceTransformer(MODEL, local_files_only=True)
    query_embeddings = model.encode(
        assigned.canonical_label.map(normalize).tolist(),
        normalize_embeddings=True,
        show_progress_bar=False,
        batch_size=64,
    )
    description_embeddings = model.encode(
        descriptions.normalized_description.tolist(),
        normalize_embeddings=True,
        show_progress_bar=False,
        batch_size=64,
    )
    scores = np.clip(query_embeddings @ description_embeddings.T, -1.0, 1.0)
    score_lookup = {cid: scores[i] for i, cid in enumerate(assigned.concept_id)}
    mapping_rows, register_rows, pair_rows = [], [], []
    for concept in vocabulary.sort_values("concept_id").itertuples():
        inspected = concept.concept_id in reviewed
        status = "held_ambiguous" if concept.target == "ambiguous" else "held_unassigned"
        best_score, nearest, count, description_count = None, "", 0, 0
        best_compatible_score, gap_reason = "", ""
        ambiguity = "not_applicable"
        if concept.target in TARGET_CATALOG:
            catalog_id = TARGET_CATALOG[concept.target]
            indexes = descriptions.index[descriptions.catalogue.eq(catalog_id)].to_numpy()
            local_scores = score_lookup[concept.concept_id][indexes].copy()
            normalized_query = normalize(concept.canonical_label)
            # Identical normalized labels receive exact similarity, independent of float error.
            local_scores[
                descriptions.loc[indexes, "normalized_description"].eq(normalized_query).to_numpy()
            ] = 1.0
            best_score = float(local_scores.max())
            nearest = descriptions.loc[
                indexes[int(local_scores.argmax())], "normalized_description"
            ]
            support = [
                lexical_support(
                    normalized_query, descriptions.loc[i, "normalized_description"], concept.target
                )
                for i in indexes
            ]
            compatible = np.flatnonzero(np.array([bool(value) for value in support]))
            if len(compatible):
                best_compatible_score = round(float(local_scores[compatible].max()), 8)
            accepted = set(compatible[accepted_indices(local_scores[compatible])].tolist())
            selected_descriptions = []
            for local_index, index in enumerate(indexes):
                score = float(local_scores[local_index])
                description = descriptions.loc[index, "normalized_description"]
                pair_rows.append(
                    {
                        "concept_id": concept.concept_id,
                        "target": concept.target,
                        "catalogue": catalog_id,
                        "normalized_catalogue_description": description,
                        "cosine_similarity": round(score, 8),
                        "lexical_support": support[local_index],
                        "selected": local_index in accepted,
                        "decision": "candidate"
                        if local_index in accepted
                        else (
                            "incompatible_action_or_component_head"
                            if not support[local_index]
                            else "below_min_score"
                            if score < MIN_SCORE
                            else "outside_near_best_margin"
                        ),
                    }
                )
                if local_index in accepted:
                    selected_descriptions.append((description, score))
            selected_descriptions.sort(key=lambda pair: (-pair[1], pair[0]))
            candidates = []
            for description, score in selected_descriptions:
                matches = eligible_catalogue[
                    eligible_catalogue.catalogue.eq(catalog_id)
                    & eligible_catalogue.normalized_description.eq(description)
                ].sort_values("catalogue_key")
                candidates.extend((source, score) for source in matches.itertuples())
            count = len(candidates)
            description_count = len(selected_descriptions)
            status = "candidate_mapping_available" if count else "candidate_catalogue_gap"
            if not count:
                if not lexical_support(normalized_query, normalized_query, concept.target):
                    gap_reason = "canonical_label_has_no_supported_action_or_component_head"
                elif not len(compatible):
                    gap_reason = "no_compatible_catalogue_head_under_declared_lexicon"
                else:
                    gap_reason = "compatible_descriptions_below_similarity_threshold"
            ambiguity = (
                "multiple_descriptions_and_or_groups"
                if description_count > 1
                else "multiple_code_groups"
                if count > 1
                else "single_candidate"
                if count
                else "no_candidate"
            )
            for rank, (source, score) in enumerate(candidates, start=1):
                mapping_rows.append(
                    {
                        "concept_id": concept.concept_id,
                        "canonical_label": concept.canonical_label,
                        "target": concept.target,
                        "catalogue": source.catalogue,
                        "code_group": source.code_group,
                        "code": source.code,
                        "catalogue_description": source.catalogue_description,
                        "catalogue_key": source.catalogue_key,
                        "source_sheet": source.source_sheet,
                        "source_artifact": source.source_artifact,
                        "source_row": source.source_row,
                        "match_confidence": round(score, 8),
                        "confidence_kind": "uncalibrated_cosine_similarity_not_probability",
                        "tier": tier(score),
                        "evidence_type": "expert_inference",
                        "anchor_source": "domain_vocabulary",
                        "mapping_method": "canonical_semantic_with_lexical_guard_v1",
                        "mapping_status": "candidate_only_not_validated_mapping",
                        "lexical_support": lexical_support(
                            normalized_query, source.catalogue_description, concept.target
                        ),
                        "equivalence_status": (
                            "normalized_label_equal"
                            if normalized_query == source.normalized_description
                            else "requires_domain_review"
                        ),
                        "candidate_rank": rank,
                        "candidate_count": count,
                        "distinct_candidate_descriptions": description_count,
                        "ambiguity_status": ambiguity,
                        "profile_selection_status": "requires_asset_profile_context",
                        "concept_inspected_during_construction": inspected,
                        "eligible_for_future_evaluation": False if inspected else "not_established",
                        "evaluation_exclusion": "instrument_construction_g20c_step3b"
                        if inspected
                        else "",
                        "path": "concept_level_no_path_aggregation",
                        "evaluation_set_type": "not_evaluated_candidate_mapping",
                        "threshold": MIN_SCORE,
                        "margin": NEAR_BEST_MARGIN,
                    }
                )
        register_rows.append(
            {
                "concept_id": concept.concept_id,
                "canonical_label": concept.canonical_label,
                "target": concept.target,
                "catalogue": TARGET_CATALOG.get(concept.target, ""),
                "mapping_status": status,
                "candidate_count": count,
                "distinct_candidate_descriptions": description_count,
                "ambiguity_status": ambiguity,
                "best_similarity": round(best_score, 8) if best_score is not None else "",
                "nearest_description_diagnostic_only": nearest,
                "best_compatible_similarity": best_compatible_score,
                "no_candidate_reason": gap_reason,
                "concept_inspected_during_construction": inspected,
                "eligible_for_future_evaluation": False if inspected else "not_established",
                "gap_interpretation": (
                    "no_candidate_under_declared_method_not_proof_of_catalogue_absence"
                    if status == "candidate_catalogue_gap"
                    else ""
                ),
            }
        )

    mapping = pd.DataFrame(mapping_rows, columns=MAPPING_COLUMNS)
    register = pd.DataFrame(register_rows)
    pairs = pd.DataFrame(pair_rows)
    assert len(register) == 256 and register.concept_id.is_unique
    assert not mapping.duplicated(["concept_id", "catalogue", "code_group", "code"]).any()
    actual = mapping.groupby("concept_id").size().reindex(register.concept_id, fill_value=0)
    assert actual.tolist() == register.candidate_count.tolist()
    assert set(mapping.catalogue_key) <= set(eligible_catalogue.catalogue_key)
    assert all(
        TARGET_CATALOG[t] == c for t, c in zip(mapping.target, mapping.catalogue, strict=True)
    )
    assert set(register[register.concept_inspected_during_construction].concept_id) == reviewed
    assert (mapping.match_confidence >= MIN_SCORE).all()
    assert mapping.lexical_support.ne("").all()
    assert hashes == {reference(path): sha256(path) for path in inputs}

    summary_rows = []
    for target, catalog_id in TARGET_CATALOG.items():
        r = register[register.target.eq(target)]
        m = mapping[mapping.target.eq(target)]
        summary_rows.append(
            {
                "target": target,
                "catalogue": catalog_id,
                "n_concepts": len(r),
                "zero_candidates": int(r.candidate_count.eq(0).sum()),
                "one_candidate": int(r.candidate_count.eq(1).sum()),
                "multiple_candidates": int(r.candidate_count.gt(1).sum()),
                "candidate_edges": len(m),
                "max_candidates_per_concept": int(r.candidate_count.max()),
                "path": "concept_level_no_path_aggregation",
                "threshold": MIN_SCORE,
                "near_best_margin": NEAR_BEST_MARGIN,
                "evaluation_set_type": "not_evaluated_candidate_mapping",
            }
        )
    summary = pd.DataFrame(summary_rows)
    output.mkdir(parents=True, exist_ok=True)
    for frame, name in [
        (mapping, "g20c_vocabulary_to_catalogue_map_sanitized.csv"),
        (register, "g20c_step4_mapping_register_sanitized.csv"),
        (
            register[register.mapping_status.eq("candidate_catalogue_gap")],
            "g20c_catalogue_gaps_sanitized.csv",
        ),
        (catalogue, "g20c_step4_catalogue_source_register_sanitized.csv"),
        (pairs, "g20c_step4_description_scores_sanitized.csv"),
        (summary, "g20c_step4_mapping_summary_sanitized.csv"),
    ]:
        write_csv(frame, output / name)
    manifest = {
        "method": "canonical_semantic_with_lexical_guard_v1",
        "embedding_model": MODEL,
        "model_revision": model[0].auto_model.config._commit_hash,
        "input_sha256": hashes,
        "script_sha256": sha256(Path(__file__)),
        "threshold": MIN_SCORE,
        "near_best_margin": NEAR_BEST_MARGIN,
        "strong_tier_min": STRONG_SCORE,
        "medium_tier_min": MEDIUM_SCORE,
        "threshold_selection": "analyst_defined_before_scoring_not_calibrated_on_evaluation",
        "lexical_guard_construction": "analyst_authored_after_candidate_diagnostics",
        "mapping_morphology": MORPHOLOGY,
        "mapping_action_heads": sorted(ACTION_HEADS),
        "mapping_component_heads": sorted(COMPONENT_HEADS),
        "top_k_truncation": False,
        "catalogue_key": ["catalogue", "code_group", "code"],
        "corpus_text_or_evaluation_labels_read": False,
        "source_anomaly_count": int(catalogue.source_anomaly.ne("").sum()),
        "unchanged_input_hashes_verified": True,
        "summary": summary.to_dict("records"),
        "output_sha256": {
            p.name: sha256(p)
            for p in sorted(output.glob("g20c*sanitized.csv"))
            if p.name
            in {
                "g20c_vocabulary_to_catalogue_map_sanitized.csv",
                "g20c_step4_mapping_register_sanitized.csv",
                "g20c_catalogue_gaps_sanitized.csv",
            }
        },
    }
    (output / "g20c_step4_mapping_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    memo = f"""# G2.0c Step 4 - Concept to Catalogue Candidates

Input: the unchanged Step 3b vocabulary (24 Activity, 43 Object Part, 4 ambiguous,
185 unassigned). Activity uses catalogue A; Object Part uses B in the same Wind
workbook used by G1.1. The 189 unresolved concepts are retained as held in the
256-row status register, and are not declared catalogue gaps.

## Method and confidence

Encode canonical labels and unique catalogue descriptions with `{MODEL}`.
Embedding normalization lowercases, splits punctuation, and collapses spaces only.
A separate lexical guard uses the declared morphology table and singular/plural
normalization. Activity requires shared action support; Object Part requires the
last recognized component head from the canonical label. The guard is
analyst_authored_after_candidate_diagnostics, retained in the manifest. It removes
related-but-incompatible proposals such as crane -> rotor and stack -> cpu.
Query only the assigned target's catalogue; accept every compatible description
with cosine >= {MIN_SCORE} and within {NEAR_BEST_MARGIN} of the best compatible
description for that concept.
There is no top-k truncation. Exact normalized descriptions score 1. Tiers are
candidate_strong >= {STRONG_SCORE}, candidate_medium >= {MEDIUM_SCORE}, and
candidate_weak >= {MIN_SCORE}. These are analyst-defined retrieval settings,
not calibrated probabilities, evaluated accuracy, or validated mappings.

All composite keys (catalogue, code group, code) for each retained description
are preserved. Group alternatives require asset/profile context; a high score
does not resolve that context. Source sheet, row, and file hash are recorded.
One Activity source anomaly, A/PMKNFAN/PMKN, contains a cooling-system description
instead of an action and is explicitly excluded from retrieval.

## Results

{summary.to_string(index=False)}

The edge table contains only actual candidates. The status register declares all
zero mappings. Assigned concepts with no candidate under this retrieval rule are
listed as candidate_catalogue_gap: this is not proof of catalogue absence.
Mapping uses canonical labels only; mixed clusters or unrepresentative labels
can cause missed or inappropriate candidates. No member text or evaluation
labels were used to broaden queries. Human/domain review is still required.
The lexical guard can miss synonyms, and candidate_catalogue_gap includes
retrieval failures: for example, a low score on setting does not establish that
the catalogue lacks a software/firmware setting adjustment entry. All rejected
description scores and gate reasons are retained for review. No similarity tier
establishes equivalence or validates the additional specificity of a catalogue code.

## Provenance and boundaries

Catalogue mapping carries expert_inference and anchor_source=domain_vocabulary.
The 13 Step 3b construction exclusions propagate to the status register and edge
rows; eligibility of other concepts remains not_established. Inputs and frozen
references are checked byte-for-byte unchanged. Mapping is stored separately;
no target, denominator, calibration, model, or Step 5 result is changed here.
Counts describe vocabulary concepts, not physical records or path coverage.
"""
    (output / "g20c_step4_mapping_memo.md").write_text(memo, encoding="utf-8")
    print(summary.to_string(index=False))
    print(
        "Held:",
        register[register.mapping_status.str.startswith("held_")]
        .mapping_status.value_counts()
        .to_dict(),
    )
    print(
        "Candidate gaps:",
        register[register.mapping_status.eq("candidate_catalogue_gap")][
            ["target", "canonical_label", "best_similarity"]
        ].to_dict("records"),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=OUT)
    main(parser.parse_args().output_dir)
