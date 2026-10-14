from __future__ import annotations

import hashlib
import json
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

import g20d3_symptom_threshold_review as review


OUT = review.OUT
SCORES = OUT / "g20d3_symptom_b1_best_scores_sanitized.csv"
CURVE = OUT / "g20d3_symptom_b1_threshold_curve_sanitized.csv"
LEXICAL_HITS = (
    review.extraction.STINT2_ROOT
    / "g2_baseline_models/outputs/g20d_catalogue_free_coverage/"
    "g20d_unit_concept_hits_sanitized.csv"
)
AUDIT = OUT / "g20d3_overlap_concept_alignment_sanitized.csv"
MANIFEST = OUT / "g20d3_overlap_concept_audit_manifest.json"
MEMO = OUT / "g20d3_memo.md"
RUN = OUT / "g20d3_run_manifest.json"
MEMO_BACKUP = OUT / "g20d3_memo_pre_concept_audit.md"
RUN_BACKUP = OUT / "g20d3_run_manifest_pre_concept_audit.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if any(path.exists() for path in (AUDIT, MANIFEST, MEMO_BACKUP, RUN_BACKUP)):
        raise RuntimeError("Concept audit already applied")
    frozen = json.loads((OUT / "g20d3_freeze_manifest.json").read_text())
    assert frozen["thresholds"] == list(review.THRESHOLDS)
    assert frozen["threshold_selected"] is False
    original_run = json.loads(RUN.read_text())
    for filename, expected in original_run["outputs"].items():
        assert sha(OUT / filename) == expected
    scores = pd.read_csv(SCORES)
    curve = pd.read_csv(CURVE)
    assert len(scores) == 9263 and len(curve) == 7
    hits = pd.read_csv(LEXICAL_HITS)
    hits = hits[hits.target.eq(review.TARGET)
                & hits.path_bucket.eq(review.PATH)
                & hits.anchor_source.eq("domain_vocabulary")
                & hits.construction_eligible]
    concepts_by_unit = hits.groupby("unit_key_hash").concept_id.apply(
        lambda values: set(values)).to_dict()
    lexical_units = set(scores.loc[scores.conservative_lexical_floor, "unit_key_hash"])
    assert lexical_units == set(concepts_by_unit) and len(lexical_units) == 187
    registry = pd.read_csv(review.REGISTRY)
    names = registry[registry.target.eq(review.TARGET)].set_index(
        "canonical_concept_key").prototype_text.to_dict()
    rows = []
    for threshold in review.THRESHOLDS:
        shared = scores[scores.conservative_lexical_floor & scores.best_score.ge(threshold)]
        matched = 0
        disagreements = Counter()
        for item in shared.itertuples():
            old_concepts = concepts_by_unit[item.unit_key_hash]
            if item.best_concept_key in old_concepts:
                matched += 1
            else:
                for old_concept in old_concepts:
                    disagreements[(old_concept, item.best_concept_key)] += 1
        previous = curve[curve.threshold.eq(threshold)].iloc[0]
        assert len(shared) == previous.intersection
        most_common = disagreements.most_common(1)
        pair, pair_count = most_common[0] if most_common else (("", ""), 0)
        rows.append(dict(target=review.TARGET, path_bucket=review.PATH,
                         universe=review.UNIVERSE, threshold=threshold,
                         intersection_units=len(shared),
                         same_concept_units=matched,
                         different_best_concept_units=len(shared) - matched,
                         same_concept_share=matched / len(shared) if len(shared) else None,
                         leading_mismatch_lexical_concept_key=pair[0],
                         leading_mismatch_semantic_concept_key=pair[1],
                         leading_mismatch_units=pair_count,
                         threshold_selected=False,
                         evaluation_set_type="not_evaluation_diagnostic_threshold_sweep",
                         raw_operational_values_emitted=False))
    result = pd.DataFrame(rows)
    at_030 = result[result.threshold.eq(0.30)].iloc[0]
    assert at_030.intersection_units == 185
    assert at_030.same_concept_units == 16
    assert at_030.leading_mismatch_units == 151
    assert names[at_030.leading_mismatch_lexical_concept_key] == "overload"
    assert names[at_030.leading_mismatch_semantic_concept_key] == "reduced power"

    old_memo_sha, old_run_sha = sha(MEMO), sha(RUN)
    shutil.copy2(MEMO, MEMO_BACKUP)
    shutil.copy2(RUN, RUN_BACKUP)
    assert sha(MEMO_BACKUP) == old_memo_sha and sha(RUN_BACKUP) == old_run_sha
    result.to_csv(AUDIT, index=False)
    assert len(pd.read_csv(AUDIT)) == len(result)
    lines = ["", "## Concept-level agreement within shared units", "",
             "Unit overlap alone does not establish agreement on the symptom concept. "
             "The best semantic prototype is compared with the full set of lexical "
             "concepts recorded for that unit; no response labels are involved.", "",
             "| Threshold | Shared units | Same concept | Different best concept | "
             "Same-concept share | Top mismatch count |",
             "|---:|---:|---:|---:|---:|---:|"]
    for row in result.itertuples():
        share = "undefined" if pd.isna(row.same_concept_share) else f"{row.same_concept_share:.2%}"
        lines.append(f"| {row.threshold:.2f} | {row.intersection_units} "
                     f"| {row.same_concept_units} | {row.different_best_concept_units} "
                     f"| {share} | {row.leading_mismatch_units} |")
    lines += ["", "At 0.30, overlap reaches 185 of the 187 lexical units, but only "
              "16 shared units retain the same concept. In 151 units, the lexical "
              "concept `overload` maps to the semantic best concept `reduced power`. "
              "Lowering the threshold therefore recovers unit overlap while losing "
              "concept agreement. This does not justify choosing 0.30 or establish "
              "that the 0.50 cutoff was merely too high; independent evaluation "
              "would be required to judge either assignment."]
    MEMO.write_text(MEMO.read_text() + "\n".join(lines) + "\n")
    original_run["outputs"][AUDIT.name] = sha(AUDIT)
    original_run["concept_alignment_audit"] = "reported_separately_no_threshold_selected"
    RUN.write_text(json.dumps(original_run, indent=2) + "\n")
    MANIFEST.write_text(json.dumps(dict(
        created_at_utc=datetime.now(timezone.utc).isoformat(),
        original_freeze_sha256=sha(OUT / "g20d3_freeze_manifest.json"),
        score_ledger_sha256=sha(SCORES),
        lexical_hits_sha256=sha(LEXICAL_HITS),
        curve_sha256=sha(CURVE),
        prior_memo_sha256=old_memo_sha, prior_run_manifest_sha256=old_run_sha,
        corrected_memo_sha256=sha(MEMO), corrected_run_manifest_sha256=sha(RUN),
        audit_sha256=sha(AUDIT), script_sha256=sha(Path(__file__)),
        threshold_selected=False, source_scores_unchanged=True,
    ), indent=2) + "\n")
    print(result[["threshold", "intersection_units", "same_concept_units",
                  "different_best_concept_units", "same_concept_share",
                  "leading_mismatch_units"]].to_string(index=False))


if __name__ == "__main__":
    main()
