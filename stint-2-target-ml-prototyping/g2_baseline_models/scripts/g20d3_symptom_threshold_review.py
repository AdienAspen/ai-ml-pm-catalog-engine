from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer

import g20c_neutral_ngram_extraction as extraction
import g20d2_semantic_reference_coverage as prior
from g20c_lexical_safety import restricted_match


OUT = extraction.STINT2_ROOT / "g2_baseline_models/outputs/g20d3_symptom_threshold_review"
SCORES = prior.OUT / "g20d2_unit_scores_sanitized.csv"
REGISTRY = prior.OUT / "g20d2_prototype_registry_sanitized.csv"
FREEZE_D2 = prior.OUT / "g20d2_freeze_manifest.json"
ZEUS_DISPOSITION = (
    extraction.STINT2_ROOT
    / "g2_baseline_models/outputs/g20d_catalogue_free_coverage/"
    "g20d_zeus_source_disposition_sanitized.csv"
)
THRESHOLDS = (0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60)
MODEL = prior.MODEL_NAME
UNIVERSE = "model_eligible_construction_corpus"
PATH = "B1_RELATIONAL"
TARGET = "Symptom"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(frame: pd.DataFrame, name: str) -> None:
    frame = frame.copy()
    frame["raw_operational_values_emitted"] = False
    frame.to_csv(OUT / name, index=False)
    assert len(pd.read_csv(OUT / name)) == len(frame)


def freeze() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = OUT / "g20d3_freeze_manifest.json"
    if manifest.exists():
        raise RuntimeError("G2.0d3 review already frozen")
    registry = pd.read_csv(REGISTRY).fillna("")
    symptom = registry[registry.target.eq(TARGET)]
    assert len(symptom) == 8 and symptom.status.eq("active").all()
    assert set(symptom.vocabulary_owner) == {"WMEP_EFFECTS"}
    assert set(symptom.source) == {"frozen_external_failure_vocabulary_v1"}
    assert not any(restricted_match(value) for value in symptom.prototype_text)
    zeus = pd.read_csv(ZEUS_DISPOSITION).fillna("")
    detection = zeus[zeus.zeus_category.eq("detection_symptom")]
    assert len(detection) == 1
    assert detection.iloc[0].g20d_disposition == "held_category_definition_not_materialized_lexicon"
    prior_freeze = json.loads(FREEZE_D2.read_text())
    assert prior_freeze["settings"]["model"] == MODEL
    assert prior_freeze["settings"]["normalization"] == "semantic_normalisation_v2"
    sources = [SCORES, REGISTRY, FREEZE_D2, ZEUS_DISPOSITION,
               extraction.SERVICE_ORDERS_JSON, extraction.LEAKAGE_REGEX_CATALOG,
               Path(extraction.__file__), Path(prior.__file__), Path(__file__),
               prior.T51_SCRIPT]
    result = dict(frozen_at_utc=datetime.now(timezone.utc).isoformat(),
                  thresholds=list(THRESHOLDS), target=TARGET, path=PATH,
                  universe=UNIVERSE, model=MODEL,
                  normalization="semantic_normalisation_v2",
                  scoring="T5.1b2X_L2_cosine_max_prototype_per_source_segment",
                  prototype_scope="same_eight_frozen_WMEP_effects_as_G2.0d2",
                  zeus_disposition="category_definition_only_no_lexical_prototype",
                  threshold_selected=False, evaluation_labels_used=False,
                  source_sha256={prior.lexical.relative(p): sha(p) for p in sources},
                  coverage_observed=False)
    manifest.write_text(json.dumps(result, indent=2) + "\n")
    print("Seven thresholds and eight WMEP prototypes frozen; no threshold selected")


def measure() -> None:
    manifest_path = OUT / "g20d3_freeze_manifest.json"
    frozen = json.loads(manifest_path.read_text())
    assert frozen["thresholds"] == list(THRESHOLDS)
    assert frozen["threshold_selected"] is False
    for name, digest in frozen["source_sha256"].items():
        assert sha(extraction.PROJECT_ROOT / name) == digest, name
    ledger = pd.read_csv(SCORES).fillna("")
    ledger = ledger[ledger.target.eq(TARGET) & ledger.path_bucket.eq(PATH)
                    & ledger.construction_eligible].copy()
    assert len(ledger) == 9263 and ledger.unit_key_hash.is_unique
    by_unit = ledger.set_index("unit_key_hash")
    prototype = pd.read_csv(REGISTRY).fillna("")
    prototype = prototype[prototype.target.eq(TARGET) & prototype.status.eq("active")]
    assert len(prototype) == 8

    extraction.LEAKAGE_PATTERNS = extraction.load_leakage_patterns()
    units, unique_texts, text_index, segments = [], [], {}, []
    for unit in extraction.load_b1_units():
        hashed = prior.lexical.unit_hash(unit["unit_key"])
        if hashed not in by_unit.index:
            continue
        selected = []
        for _, raw in unit["segments"]:
            masked, _, _ = extraction.apply_leakage_mask(raw, extraction.LEAKAGE_PATTERNS)
            tokens, _ = extraction.normalise_text(masked)
            if not tokens:
                continue
            text = " ".join(tokens)
            if text not in text_index:
                text_index[text] = len(unique_texts)
                unique_texts.append(text)
            selected.append(text_index[text])
        units.append(hashed)
        segments.append(sorted(set(selected)))
    assert len(units) == len(by_unit) and len(set(units)) == len(units)
    print(f"Eligible B1 units: {len(units)}; unique normalized segments: {len(unique_texts)}", flush=True)

    model = SentenceTransformer(MODEL, local_files_only=True)
    scoring = prior.load_t51_scoring()
    proto_vectors = np.asarray(model.encode(
        prototype.prototype_text.tolist(), normalize_embeddings=True,
        convert_to_numpy=True, show_progress_bar=False, batch_size=64), dtype=np.float32)
    batches = []
    for start in range(0, len(unique_texts), prior.CHUNK_SIZE):
        batches.append(np.asarray(model.encode(
            unique_texts[start:start + prior.CHUNK_SIZE], normalize_embeddings=True,
            convert_to_numpy=True, show_progress_bar=False, batch_size=64), dtype=np.float32))
        print(f"Embedded {min(start + prior.CHUNK_SIZE, len(unique_texts))}/{len(unique_texts)}", flush=True)
    vectors = np.vstack(batches)
    result_rows = []
    for key, segment_ids in zip(units, segments, strict=True):
        prior_row = by_unit.loc[key]
        if segment_ids:
            scores = scoring.cosine_matrix(vectors[segment_ids], proto_vectors)
            best_flat = int(scores.argmax())
            best = prototype.iloc[best_flat % len(prototype)]
            score = float(scores.flat[best_flat])
            concept = best.canonical_concept_key
            entry = best.prototype_id
        else:
            score, concept, entry = None, "", ""
        old_score = prior_row.best_score
        if score is None:
            assert old_score == ""
        else:
            assert abs(score - float(old_score)) <= 0.0001, key
            assert (score >= 0.50) == bool(prior_row.semantic_external_only), key
            if score >= 0.50:
                assert concept == prior_row.assigned_concept_key
                assert entry == prior_row.assigned_prototype_id
        result_rows.append(dict(unit_key_hash=key,
                                conservative_lexical_floor=bool(prior_row.lexical_external_only),
                                best_score=round(score, 7) if score is not None else None,
                                best_concept_key=concept,
                                best_prototype_id=entry,
                                prior_050_assignment=bool(prior_row.semantic_external_only)))
    scores = pd.DataFrame(result_rows)
    assert len(scores) == 9263 and scores.unit_key_hash.is_unique
    save(scores, "g20d3_symptom_b1_best_scores_sanitized.csv")

    curve, concept_rows = [], []
    for threshold in THRESHOLDS:
        lexical = scores.conservative_lexical_floor
        semantic = scores.best_score.ge(threshold).fillna(False)
        selected = scores[semantic]
        freq = selected.best_concept_key.value_counts()
        top_key = freq.index[0] if len(freq) else ""
        top_units = int(freq.iloc[0]) if len(freq) else 0
        top_share = top_units / len(selected) if len(selected) else None
        row = dict(target=TARGET, path_bucket=PATH, universe=UNIVERSE,
                   threshold=threshold, total_units=len(scores),
                   conservative_lexical_floor=int(lexical.sum()),
                   broader_semantic_estimate=int(semantic.sum()),
                   assigned=int(semantic.sum()), abstained=int((~semantic).sum()),
                   coverage=float(semantic.mean()), lexical_only=int((lexical & ~semantic).sum()),
                   semantic_only=int((~lexical & semantic).sum()),
                   intersection=int((lexical & semantic).sum()),
                   union=int((lexical | semantic).sum()),
                   no_anchor=int((~lexical & ~semantic).sum()),
                   available_external_concepts=8, matched_semantic_concepts=len(freq),
                   top_concept_key=top_key, top_concept_units=top_units,
                   top_concept_share=top_share,
                   concentration_above_30pct=bool(top_share is not None and top_share > 0.30),
                   threshold_selected=False,
                   evaluation_set_type="not_evaluation_diagnostic_threshold_sweep")
        assert row["assigned"] + row["abstained"] == row["total_units"]
        assert row["union"] + row["no_anchor"] == row["total_units"]
        assert row["lexical_only"] + row["intersection"] == row["conservative_lexical_floor"]
        assert row["semantic_only"] + row["intersection"] == row["assigned"]
        curve.append(row)
        for concept, count in freq.items():
            concept_rows.append(dict(target=TARGET, path_bucket=PATH, universe=UNIVERSE,
                                     threshold=threshold, canonical_concept_key=concept,
                                     assigned_units=int(count), share_of_assigned=int(count) / len(selected)))
    output = pd.DataFrame(curve)
    at_050 = output[output.threshold.eq(0.50)].iloc[0]
    assert (at_050["assigned"], at_050["intersection"], at_050["union"]) == (104, 4, 287)
    assert output.sort_values("threshold").intersection.is_monotonic_decreasing
    save(output, "g20d3_symptom_b1_threshold_curve_sanitized.csv")
    save(pd.DataFrame(concept_rows), "g20d3_symptom_b1_concept_distribution_sanitized.csv")
    write_memo(output)
    for name, digest in frozen["source_sha256"].items():
        assert sha(extraction.PROJECT_ROOT / name) == digest, name
    run = dict(completed_at_utc=datetime.now(timezone.utc).isoformat(),
               freeze_sha256=sha(manifest_path), target=TARGET, path=PATH,
               universe=UNIVERSE, threshold_selected=False, evaluation_labels_used=False,
               status="diagnostic_curve_only_no_threshold_selection",
               outputs={path.name: sha(path) for path in sorted(OUT.glob("*.csv"))})
    (OUT / "g20d3_run_manifest.json").write_text(json.dumps(run, indent=2) + "\n")
    print(output[["threshold", "assigned", "abstained", "coverage", "lexical_only",
                  "semantic_only", "intersection", "union", "top_concept_share"]].to_string(index=False))


def write_memo(curve: pd.DataFrame) -> None:
    lines = ["# G2.0d3 - Symptom threshold review", "",
             "Diagnostic curve only; no threshold is selected. Selection requires independent "
             "evaluation material. These counts are not precision, F1, a denominator or SAP truth.", "",
             "The eight Symptom prototypes are frozen WMEP failure effects. ZEUS supplied a "
             "detection-symptom category definition but no materialized lexical prototype, "
             "so ZEUS contributed zero prototypes in G2.0d2 and in this review.", "",
             "The same 9,263 eligible B1 units, G2.0b leakage mask, semantic_normalisation_v2, "
             "MiniLM vectors and per-segment max-cosine scoring are retained. Scores at 0.50 "
             "were reconciled against the original G2.0d2 ledger before this curve was accepted.", "",
             "| Threshold | Assigned | Abstained | Coverage | Lexical only | Semantic only | "
             "Intersection | Union | No anchor | Matched concepts | Top share |",
             "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for row in curve.itertuples():
        share = "undefined" if pd.isna(row.top_concept_share) else f"{row.top_concept_share:.2%}"
        lines.append(f"| {row.threshold:.2f} | {row.assigned} | {row.abstained} "
                     f"| {row.coverage:.2%} | {row.lexical_only} | {row.semantic_only} "
                     f"| {row.intersection} | {row.union} | {row.no_anchor} "
                     f"| {row.matched_semantic_concepts} | {share} |")
    first, last = curve.iloc[0], curve.iloc[-1]
    lines += ["", f"As the cutoff rises from {first.threshold:.2f} to {last.threshold:.2f}, "
              f"the overlap with the lexical detector moves from {first.intersection} to "
              f"{last.intersection} units. This curve diagnoses score transfer; it does not "
              "validate a replacement threshold.", "",
              "The original 0.50 threshold came from T5.1b2.X against `reason` and a different "
              "prototype set. A low overlap at that cutoff is not proof of absent symptom "
              "signal. The lexical floor is not mathematically nested in semantic assignments.", "",
              "No F6 update, candidate promotion or model training was performed. No visible "
              "operational text is emitted."]
    (OUT / "g20d3_memo.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("freeze", "measure"))
    args = parser.parse_args()
    freeze() if args.phase == "freeze" else measure()
