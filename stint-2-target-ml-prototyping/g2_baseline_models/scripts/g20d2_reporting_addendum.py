from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

import g20d2_semantic_reference_coverage as original


OUT = original.OUT
COMPARISON = OUT / "g20d2_detector_comparison_sanitized.csv"
MEMO = OUT / "g20d2_memo.md"
RUN = OUT / "g20d2_run_manifest.json"
BACKUPS = {
    COMPARISON: OUT / "g20d2_detector_comparison_pre_addendum_sanitized.csv",
    MEMO: OUT / "g20d2_memo_pre_addendum.md",
    RUN: OUT / "g20d2_run_manifest_pre_addendum.json",
}
ADDENDUM = OUT / "g20d2_reporting_addendum_manifest.json"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if ADDENDUM.exists() or any(path.exists() for path in BACKUPS.values()):
        raise RuntimeError("Reporting addendum already applied")
    frozen = json.loads((OUT / "g20d2_freeze_manifest.json").read_text())
    runner_key = original.lexical.relative(Path(original.__file__))
    assert digest(Path(original.__file__)) == frozen["source_sha256"][runner_key]
    run = json.loads(RUN.read_text())
    for filename, expected in run["outputs"].items():
        assert digest(OUT / filename) == expected, filename
    assert run["status"] == "descriptive_complete_b2_provisional_no_accuracy_claim"

    source = pd.read_csv(OUT / "g20d2_prototype_registry_sanitized.csv")
    assert len(source) == 144
    available = source.groupby("target").canonical_concept_key.nunique().to_dict()
    cause_owners = source[source.target.eq("Cause")].groupby(
        "vocabulary_owner").canonical_concept_key.nunique().to_dict()
    assert cause_owners == {"NREL_GRD": 7, "WMEP_CAUSES": 9}
    assigned = pd.read_csv(OUT / "g20d2_assigned_concepts_sanitized.csv")
    assigned_count = assigned.groupby(
        ["universe", "target", "path_bucket"]
    ).canonical_concept_key.nunique().to_dict()
    old = pd.read_csv(COMPARISON)
    assert len(old) == 18
    renamed = old.rename(columns={
        "lexical_g20d": "conservative_lexical_floor",
        "lexical_same_external_prototypes": "conservative_lexical_floor_same_prototypes",
        "semantic_external_prototypes": "broader_semantic_estimate",
        "semantic_minus_original_lexical": "broader_semantic_minus_g20d_floor",
        "semantic_minus_same_prototype_lexical": "broader_semantic_minus_same_prototype_floor",
    })
    renamed.insert(renamed.columns.get_loc("top_concept_share"),
                   "available_external_concepts", renamed.target.map(available))
    renamed.insert(renamed.columns.get_loc("top_concept_share"),
                   "matched_semantic_concepts",
                   [assigned_count.get((r.universe, r.target, r.path_bucket), 0)
                    for r in renamed.itertuples()])
    assert (renamed.matched_semantic_concepts <= renamed.available_external_concepts).all()
    assert (renamed.lexical_only + renamed.intersection
            == renamed.conservative_lexical_floor_same_prototypes).all()
    assert (renamed.semantic_only + renamed.intersection
            == renamed.broader_semantic_estimate).all()
    assert (renamed.union + renamed.no_anchor == renamed.path_units).all()

    memo = ["# G2.0d2 - External-vocabulary detector comparison", "",
            "`conservative_lexical_floor` reproduces G2.0d's wider lexical registry. "
            "`conservative_lexical_floor_same_prototypes` uses only canonical frozen "
            "external phrases; the five overlap groups compare it with "
            "`broader_semantic_estimate` on identical units and phrases.", "",
            "The semantic estimate is not a proven ceiling, precision measurement or SAP "
            "truth. Its fixed 0.50 score cutoff was frozen before measurement, inherited "
            "from T5.1b2.X-normalized, and was not recalibrated here. No G0 labels or "
            "observed corpus text were used to construct prototypes.", "",
            "Cause has 16 available external concepts: 9 WMEP cause categories and 7 "
            "NREL GRD concepts. A high top-concept share can reflect coarse taxonomy "
            "rather than prototype collapse; counts and this table alone cannot "
            "separate those explanations. Review concept-level assignments and errors "
            "before interpreting a concentration flag.", "",
            "| Universe | Target | Path | N | Conservative lexical floor | "
            "Same-prototype lexical | Broader semantic estimate | Lexical only | "
            "Semantic only | Intersection | Union | No anchor | Available concepts | "
            "Matched concepts | Top concept share | Flag >30% |",
            "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
    for row in renamed.itertuples():
        share = "undefined" if pd.isna(row.top_concept_share) else f"{row.top_concept_share:.2%}"
        memo.append(f"| {row.universe} | {row.target} | {row.path_bucket} | {row.path_units} "
                    f"| {row.conservative_lexical_floor} "
                    f"| {row.conservative_lexical_floor_same_prototypes} "
                    f"| {row.broader_semantic_estimate} | {row.lexical_only} "
                    f"| {row.semantic_only} | {row.intersection} | {row.union} "
                    f"| {row.no_anchor} | {row.available_external_concepts} "
                    f"| {row.matched_semantic_concepts} | {share} "
                    f"| {'yes' if row.concentration_above_30pct else 'no'} |")
    memo += ["", "B2 remains provisional because inherited Step 5 source identity "
             "does not reconcile with F6. Path A is reported separately. No F6 "
             "denominator, prototype, threshold, unit score or model result was changed. "
             "The original report and manifest are retained with `pre_addendum` names."]

    old_hashes = {path.name: digest(path) for path in BACKUPS}
    for path, backup in BACKUPS.items():
        shutil.copy2(path, backup)
        assert digest(path) == digest(backup)
    renamed.to_csv(COMPARISON, index=False)
    MEMO.write_text("\n".join(memo) + "\n")
    assert len(pd.read_csv(COMPARISON)) == len(old)
    run["outputs"][COMPARISON.name] = digest(COMPARISON)
    run["reporting_addendum"] = (
        "renamed_detector_measures_and_added_available_and_matched_concept_counts"
    )
    run["method_and_unit_scores_unchanged"] = True
    RUN.write_text(json.dumps(run, indent=2) + "\n")
    addendum = dict(applied_at_utc=datetime.now(timezone.utc).isoformat(),
                    frozen_instrument_sha256=digest(OUT / "g20d2_freeze_manifest.json"),
                    unit_scores_sha256=digest(OUT / "g20d2_unit_scores_sanitized.csv"),
                    prior_artifact_sha256=old_hashes,
                    corrected_artifact_sha256={p.name: digest(p)
                                               for p in (COMPARISON, MEMO, RUN)},
                    reporting_script_sha256=digest(Path(__file__)),
                    no_model_rerun=True, method_unchanged=True)
    ADDENDUM.write_text(json.dumps(addendum, indent=2) + "\n")
    print(renamed[renamed.universe.eq(original.lexical.ELIGIBLE)][
        ["target", "path_bucket", "conservative_lexical_floor",
         "broader_semantic_estimate", "available_external_concepts",
         "matched_semantic_concepts", "top_concept_share"]].to_string(index=False))


if __name__ == "__main__":
    main()
