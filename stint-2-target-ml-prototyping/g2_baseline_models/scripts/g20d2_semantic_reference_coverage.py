from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer

import g20c_neutral_ngram_extraction as extraction
import g20d_catalogue_free_coverage as lexical
from g20c_lexical_safety import restricted_match
from g20c_step5_coverage import add_phrase, match_segments, phrase_index

ROOT = extraction.STINT2_ROOT
OUT = ROOT / "g2_baseline_models/outputs/g20d2_semantic_reference_coverage"
EXTERNAL = lexical.EXTERNAL
LEXICAL_UNITS = lexical.OUT / "g20d_unit_coverage_sanitized.csv"
LEXICAL_SUMMARY = lexical.OUT / "g20d_domain_only_coverage_sanitized.csv"
LEXICAL_RUN = lexical.OUT / "g20d_run_manifest.json"
LEXICAL_FREEZE = lexical.OUT / "g20d_freeze_manifest.json"
T51_SCRIPT = (
    extraction.STINT1_ROOT
    / "phase_5_symptom/scripts/t51b2x_reason_semantic_classification_normalized.py"
)
T51_SUMMARY = (
    extraction.STINT1_ROOT
    / "phase_5_symptom/outputs/f51_symptom_thread_resolution/"
    "t51b2x_reason_semantic_classification_normalized_summary_sanitized.json"
)
TARGETS = lexical.TARGETS
MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
THRESHOLD = 0.50
CHUNK_SIZE = 1024


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(frame, filename):
    frame = frame.copy()
    frame["raw_operational_values_emitted"] = False
    frame.to_csv(OUT / filename, index=False)
    assert len(pd.read_csv(OUT / filename)) == len(frame)


def load_t51_scoring():
    spec = importlib.util.spec_from_file_location("t51b2x_frozen_scoring", T51_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def freeze():
    OUT.mkdir(parents=True, exist_ok=True)
    manifest_path = OUT / "g20d2_freeze_manifest.json"
    if manifest_path.exists():
        raise RuntimeError("G2.0d2 instrument already frozen")
    reference = lexical.read(EXTERNAL)
    assert len(reference) == 144 and reference.concept_id.is_unique
    assert set(reference.target) == set(TARGETS)
    old = lexical.read(lexical.OUT / "g20d_anchor_registry_sanitized.csv")
    frozen = old[old.source_artifact.eq(lexical.relative(EXTERNAL))]
    assert len(frozen) == 144
    registry = []
    for row in reference.itertuples():
        phrase = " ".join(extraction.normalise_text(row.canonical_concept)[0])
        held = not phrase or restricted_match(phrase)
        previous = frozen[frozen.source_entry_id.eq(row.concept_id)]
        assert len(previous) == 1 and previous.iloc[0].anchor_text == ("" if held else phrase)
        registry.append(dict(
            target=row.target, prototype_id=row.concept_id,
            canonical_concept_key=row.canonical_concept_key,
            prototype_text="" if held else phrase,
            prototype_hash=extraction.prefixed_hash("PROTO", phrase, 12),
            source="frozen_external_failure_vocabulary_v1",
            vocabulary_owner=row.vocabulary_owner, subsystem=row.subsystem,
            semantic_level=row.semantic_level, evidence_type=row.evidence_type,
            tier=row.tier, status="held_empty_or_restricted" if held else "active",
            construction_method="transcribed_frozen_external_canonical_phrase_only",
        ))
    registry = pd.DataFrame(registry)
    save(registry, "g20d2_prototype_registry_sanitized.csv")
    old_run = json.loads(LEXICAL_RUN.read_text())
    assert old_run["status"].startswith("provisional_b2_source_identity")
    t51 = json.loads(T51_SUMMARY.read_text())
    assert t51["threshold"] == THRESHOLD and t51["embedding_model"] == MODEL_NAME
    settings = dict(
        model=MODEL_NAME, threshold=THRESHOLD,
        threshold_source="T5.1b2X_normalized_historical_preselected_not_recalibrated",
        normalization="semantic_normalisation_v2",
        scoring="T5.1b2X_normalized_L2_cosine_max_prototype_then_abstain",
        source_segments="independent_max_per_unit_no_cross_field_join",
        prototypes="external_failure_vocabulary_v1_canonical_English_only",
        aliases=False, g20c_augmentations=False, sap_prototypes=False,
        corpus_prototypes=False, evaluation_labels_for_tuning=False,
        label_generation_method="semantic_prototype_matching_frozen_external_v1",
        interpretation="broader_semantic_estimate_not_ceiling_or_precision",
    )
    sources = [EXTERNAL, LEXICAL_UNITS, LEXICAL_SUMMARY, LEXICAL_RUN,
               LEXICAL_FREEZE, T51_SCRIPT, T51_SUMMARY, Path(extraction.__file__),
               Path(lexical.__file__), Path(__file__),
               Path(__file__).with_name("g20c_step5_coverage.py"),
               Path(__file__).with_name("g20c_lexical_safety.py")]
    manifest = dict(frozen_at_utc=datetime.now(timezone.utc).isoformat(),
                    settings=settings,
                    source_sha256={lexical.relative(p): sha(p) for p in sources},
                    inherited_corpus_input_sha256=json.loads(LEXICAL_FREEZE.read_text())[
                        "corpus_input_sha256"],
                    registry_sha256=sha(OUT / "g20d2_prototype_registry_sanitized.csv"),
                    coverage_observed=False)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(registry.groupby("target").agg(source_entries=("prototype_id", "nunique"),
                                         active=("status", lambda s: s.eq("active").sum()),
                                         concepts=("canonical_concept_key", "nunique")).to_string())
    print("Threshold and external-only prototypes frozen before semantic measurement")


def measure():
    freeze_path = OUT / "g20d2_freeze_manifest.json"
    frozen = json.loads(freeze_path.read_text())
    assert frozen["settings"]["threshold"] == THRESHOLD
    assert frozen["settings"]["model"] == MODEL_NAME
    for name, digest in frozen["source_sha256"].items():
        assert sha(extraction.PROJECT_ROOT / name) == digest, name
    assert sha(OUT / "g20d2_prototype_registry_sanitized.csv") == frozen["registry_sha256"]
    assert frozen["inherited_corpus_input_sha256"] == lexical.corpus_input_hashes()
    registry = lexical.read(OUT / "g20d2_prototype_registry_sanitized.csv")
    active = registry[registry.status.eq("active")]
    old_units = lexical.read(LEXICAL_UNITS)
    assert not old_units.duplicated(["unit_key_hash", "target"]).any()
    old_lookup = old_units.set_index(["unit_key_hash", "target"])
    core_index = phrase_index()
    for row in active.itertuples():
        add_phrase(core_index, row.prototype_text, (row.target, row.canonical_concept_key))
    extraction.LEAKAGE_PATTERNS = extraction.load_leakage_patterns()
    print("Reconstructing masked G2.0d corpus", flush=True)
    units = extraction.load_b1_units() + extraction.load_path_a_units() + extraction.load_b2_units()
    assert len(units) == 12968 and len({u["unit_key"] for u in units}) == len(units)
    segments_by_unit, unique_texts, text_to_index, core_by_unit = [], [], {}, []
    for unit in units:
        segment_tokens, indices = [], []
        for _, raw in unit["segments"]:
            masked, _, _ = extraction.apply_leakage_mask(raw, extraction.LEAKAGE_PATTERNS)
            tokens, _ = extraction.normalise_text(masked)
            segment_tokens.append(tokens)
            if tokens:
                string = " ".join(tokens)
                if string not in text_to_index:
                    text_to_index[string] = len(unique_texts)
                    unique_texts.append(string)
                indices.append(text_to_index[string])
        segments_by_unit.append(sorted(set(indices)))
        core_by_unit.append(match_segments(segment_tokens, core_index))
    del text_to_index
    print(f"Unique normalized source segments to embed: {len(unique_texts)}", flush=True)
    model = SentenceTransformer(MODEL_NAME, local_files_only=True)
    scoring = load_t51_scoring()
    prototype_vectors, prototype_rows = {}, {}
    for target in TARGETS:
        rows = active[active.target.eq(target)].reset_index(drop=True)
        prototype_rows[target] = rows
        prototype_vectors[target] = np.asarray(model.encode(
            rows.prototype_text.tolist(), normalize_embeddings=True,
            convert_to_numpy=True, show_progress_bar=False, batch_size=64), dtype=np.float32)
    vectors = []
    for start in range(0, len(unique_texts), CHUNK_SIZE):
        batch = np.asarray(model.encode(
            unique_texts[start:start + CHUNK_SIZE], normalize_embeddings=True,
            convert_to_numpy=True, show_progress_bar=False, batch_size=64), dtype=np.float32)
        vectors.append(batch)
        print(f"Embedded {min(start + CHUNK_SIZE, len(unique_texts))}/{len(unique_texts)}", flush=True)
    vectors = np.vstack(vectors)
    del unique_texts
    results = []
    for unit, segment_ids, core_matches in zip(units, segments_by_unit, core_by_unit, strict=True):
        unit_id = lexical.unit_hash(unit["unit_key"])
        for target in TARGETS:
            old = old_lookup.loc[(unit_id, target)]
            core = any(t == target for t, _ in core_matches)
            original_lexical = bool(old.domain_vocabulary)
            assert not core or original_lexical
            if segment_ids:
                scores = scoring.cosine_matrix(vectors[segment_ids], prototype_vectors[target])
                best_flat = int(scores.argmax())
                proto_idx = best_flat % len(prototype_rows[target])
                best_score = float(scores.flat[best_flat])
                matched = best_score >= THRESHOLD
                best = prototype_rows[target].iloc[proto_idx]
                concept = best.canonical_concept_key if matched else ""
                prototype = best.prototype_id if matched else ""
            else:
                best_score, matched, concept, prototype = None, False, "", ""
            results.append(dict(unit_key_hash=unit_id, target=target,
                                path_bucket=unit["path_bucket"],
                                construction_eligible=bool(old.construction_eligible),
                                construction_exclusion=old.construction_exclusion,
                                lexical_g20d=original_lexical,
                                lexical_external_only=core,
                                semantic_external_only=matched,
                                best_score=round(best_score, 6) if best_score is not None else None,
                                assigned_concept_key=concept,
                                assigned_prototype_id=prototype,
                                threshold=THRESHOLD,
                                evaluation_set_type="not_evaluation_descriptive_coverage",
                                label_generation_method="semantic_prototype_matching_frozen_external_v1"))
    frame = pd.DataFrame(results)
    assert len(frame) == 12968 * len(TARGETS)
    assert frame[frame.construction_eligible].unit_key_hash.nunique() == 10900
    old_keys = set(zip(old_units.unit_key_hash, old_units.target))
    assert set(zip(frame.unit_key_hash, frame.target)) == old_keys
    save(frame, "g20d2_unit_scores_sanitized.csv")
    comparisons, concepts = [], []
    for universe in (lexical.FULL, lexical.ELIGIBLE):
        current = frame if universe == lexical.FULL else frame[frame.construction_eligible]
        for (target, path), group in current.groupby(["target", "path_bucket"], sort=True):
            core = group.lexical_external_only
            sem = group.semantic_external_only
            matched = group[sem]
            freq = matched.assigned_concept_key.value_counts()
            top = freq.index[0] if len(freq) else ""
            top_n = int(freq.iloc[0]) if len(freq) else 0
            top_share = top_n / len(matched) if len(matched) else None
            original = int(group.lexical_g20d.sum())
            core_n = int(core.sum())
            sem_n = int(sem.sum())
            intersection = int((core & sem).sum())
            union = int((core | sem).sum())
            comparisons.append(dict(
                universe=universe, target=target, path_bucket=path,
                path_units=len(group), lexical_g20d=original,
                lexical_same_external_prototypes=core_n,
                semantic_external_prototypes=sem_n,
                semantic_minus_original_lexical=sem_n - original,
                semantic_minus_same_prototype_lexical=sem_n - core_n,
                lexical_only=core_n - intersection,
                semantic_only=sem_n - intersection,
                intersection=intersection, union=union, no_anchor=len(group) - union,
                top_concept_key=top, top_concept_units=top_n,
                top_concept_share=top_share,
                concentration_above_30pct=bool(top_share is not None and top_share > 0.30),
                threshold=THRESHOLD,
                method="semantic_normalisation_v2_minilm_max_cosine_frozen_external",
                comparison_status="provisional_inherited_b2_source_identity" if path == "B2_WORKBOOKS"
                else "same_unit_detector_comparison_no_accuracy_claim",
                evaluation_set_type="not_evaluation_descriptive_coverage"))
            for concept, count in freq.items():
                concepts.append(dict(universe=universe, target=target, path_bucket=path,
                                     canonical_concept_key=concept, assigned_units=int(count),
                                     share_of_semantic_anchored_units=int(count) / len(matched)))
    comparison = pd.DataFrame(comparisons)
    prior = lexical.read(LEXICAL_SUMMARY)
    prior = prior.set_index(["universe", "target", "path_bucket"])
    for row in comparison.itertuples():
        expected = prior.loc[(row.universe, row.target, row.path_bucket)]
        assert row.path_units == expected.path_units
        assert row.lexical_g20d == expected.units_with_domain_anchor
        assert row.lexical_only + row.intersection == row.lexical_same_external_prototypes
        assert row.semantic_only + row.intersection == row.semantic_external_prototypes
        assert row.union + row.no_anchor == row.path_units
    save(comparison, "g20d2_detector_comparison_sanitized.csv")
    save(pd.DataFrame(concepts), "g20d2_assigned_concepts_sanitized.csv")
    write_memo(comparison)
    for name, digest in frozen["source_sha256"].items():
        assert sha(extraction.PROJECT_ROOT / name) == digest, name
    assert frozen["inherited_corpus_input_sha256"] == lexical.corpus_input_hashes()
    manifest = dict(completed_at_utc=datetime.now(timezone.utc).isoformat(),
                    frozen_instrument_sha256=sha(freeze_path),
                    model=MODEL_NAME, threshold=THRESHOLD,
                    unit_target_rows=len(frame), model_eligible_units=10900,
                    labels_used_for_calibration=False,
                    status="descriptive_complete_b2_provisional_no_accuracy_claim",
                    outputs={p.name: sha(p) for p in sorted(OUT.glob("*.csv"))})
    (OUT / "g20d2_run_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(comparison[comparison.universe.eq(lexical.ELIGIBLE)][
        ["target", "path_bucket", "path_units", "lexical_g20d",
         "lexical_same_external_prototypes", "semantic_external_prototypes",
         "lexical_only", "semantic_only", "intersection", "union", "no_anchor",
         "top_concept_share"]].to_string(index=False))


def write_memo(comparison):
    lines = ["# G2.0d2 - External-vocabulary semantic detector", "",
             "The lexical exact match is a conservative floor. Prototype coverage is a broader "
             "semantic estimate; it can over-generate and is not a verified ceiling, a precision "
             "estimate or SAP truth.", "",
             "The threshold 0.50 was frozen before this run from T5.1b2.X-normalized. Its previous "
             "calibration does not establish accuracy for these new external prototypes. Only "
             "canonical phrases from the frozen 144-row external source are prototypes; no SAP, "
             "translation aliases, G2.0c augmentations, analyst examples or corpus terms enter.", "",
             "The original G2.0d lexical count used a wider registry. The same-prototype lexical "
             "column isolates the detector comparison. Lexical-only, semantic-only, intersection, "
             "union and no-anchor use that common external prototype set and unique units.", "",
             "| Universe | Target | Path | N | G2.0d lexical | Same-source lexical | Semantic | "
             "Lex only | Sem only | Both | Union | Neither | Top share |",
             "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for row in comparison.itertuples():
        share = "undefined" if pd.isna(row.top_concept_share) else f"{row.top_concept_share:.2%}"
        lines.append(f"| {row.universe} | {row.target} | {row.path_bucket} | {row.path_units} "
                     f"| {row.lexical_g20d} | {row.lexical_same_external_prototypes} "
                     f"| {row.semantic_external_prototypes} | {row.lexical_only} "
                     f"| {row.semantic_only} | {row.intersection} | {row.union} "
                     f"| {row.no_anchor} | {share} |")
    lines += ["", "A high top-concept share may reflect a coarse external taxonomy or prototype "
              "collapse. The count alone cannot distinguish the two. Source taxonomy, assigned "
              "concept distribution and representative errors need review before interpreting "
              "the signal.", "",
              "B2 uses the inherited Step 5 grouping whose source identity does not reconcile "
              "with F6; its measurements are provisional. This detector comparison does not "
              "repair upstream grouping. Path A remains separate. No F6 denominator changed; "
              "no candidate was promoted or model trained. Evaluation-set labels did not tune "
              "prototypes or threshold. No raw corpus text is emitted."]
    (OUT / "g20d2_memo.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("freeze", "measure"))
    args = parser.parse_args()
    freeze() if args.phase == "freeze" else measure()
