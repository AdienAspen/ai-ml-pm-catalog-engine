from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path("/home/adien-i7-remote/workspace/fsa_bridge_ml_feasibility")
STINT2_ROOT = PROJECT_ROOT / "stint-2-target-ml-prototyping"
OUT = STINT2_ROOT / "g2_baseline_models/outputs/g20_corpus_native_domain_vocab"
CANDIDATES = OUT / "g20c_candidate_terms_sanitized.csv"
SUMMARY = OUT / "g20c_step1_extraction_summary_sanitized.json"

BEFORE_CANDIDATES = {
    "B1_RELATIONAL": 76157,
    "B2_WORKBOOKS": 1752,
    "PATH_A": 1987,
}
BEFORE_ELIGIBLE_UNITS = {
    "B1_RELATIONAL": 9278,
    "B2_WORKBOOKS": 1479,
    "PATH_A": 159,
}


def main() -> None:
    candidates = pd.read_csv(CANDIDATES)
    current_candidates = candidates.groupby("path_bucket").size().to_dict()
    summary = pd.DataFrame(json.loads(SUMMARY.read_text(encoding="utf-8")))
    eligible = summary[
        summary["universe"].eq("model_eligible_construction_corpus")
    ]
    current_units = eligible.set_index("path_bucket")["units"].astype(int).to_dict()

    rows = []
    reason = (
        "semantic_normalisation_v2 rerun split hyphenated compounds and removed "
        "operational entity sub-tokens before hashing and n-gram emission; "
        "release lexical safety then excludes 39 restricted path-term rows "
        "without changing semantic normalization or exclusion hashes"
    )
    for path in BEFORE_CANDIDATES:
        rows.append(
            {
                "path_bucket": path,
                "candidate_terms_before_sanitization_rerun": BEFORE_CANDIDATES[path],
                "candidate_terms_after_sanitization_rerun": current_candidates[path],
                "candidate_term_delta": current_candidates[path]
                - BEFORE_CANDIDATES[path],
                "eligible_units_before_sanitization_rerun": BEFORE_ELIGIBLE_UNITS[path],
                "eligible_units_after_sanitization_rerun": current_units[path],
                "eligible_unit_delta": current_units[path]
                - BEFORE_ELIGIBLE_UNITS[path],
                "reconciliation_reason": reason,
                "raw_operational_values_emitted": False,
            }
        )
    rows.append(
        {
            "path_bucket": "ALL",
            "candidate_terms_before_sanitization_rerun": sum(
                BEFORE_CANDIDATES.values()
            ),
            "candidate_terms_after_sanitization_rerun": sum(
                current_candidates.values()
            ),
            "candidate_term_delta": sum(current_candidates.values())
            - sum(BEFORE_CANDIDATES.values()),
            "eligible_units_before_sanitization_rerun": sum(
                BEFORE_ELIGIBLE_UNITS.values()
            ),
            "eligible_units_after_sanitization_rerun": sum(current_units.values()),
            "eligible_unit_delta": sum(current_units.values())
            - sum(BEFORE_ELIGIBLE_UNITS.values()),
            "reconciliation_reason": reason,
            "raw_operational_values_emitted": False,
        }
    )
    reconciliation = pd.DataFrame(rows)
    all_row = reconciliation[reconciliation["path_bucket"].eq("ALL")].iloc[0]
    if int(all_row["candidate_terms_before_sanitization_rerun"]) != 79896:
        raise RuntimeError("Unexpected pre-rerun candidate total")
    if int(all_row["candidate_terms_after_sanitization_rerun"]) != 79330:
        raise RuntimeError("Unexpected post-rerun candidate total")
    if int(all_row["candidate_term_delta"]) != -566:
        raise RuntimeError("Step 1 rerun delta did not reconcile")

    reconciliation.to_csv(
        OUT / "g20c_step1_rerun_reconciliation_sanitized.csv",
        index=False,
        lineterminator="\n",
    )
    memo = """# G2.0c Step 1 Sanitization Rerun Reconciliation

The original neutral Step 1 run emitted 79,896 candidate terms. A later quality
gate found an operational contractor name inside a hyphenated compound. The
normalizer was corrected to split compounds and remove operational entity
sub-tokens before semantic hashing and n-gram emission.

The first corrected rerun emitted 79,369 terms, a reduction of 527:

- B1_RELATIONAL: 76,157 -> 75,633 (-524).
- B2_WORKBOOKS: 1,752 -> 1,752 (0).
- PATH_A: 1,987 -> 1,984 (-3).

Because semantic hashes changed, conservative duplicate-text exclusion also changed
the eligible construction universe from 9,278 to 9,263 B1 units and from 1,479 to
1,478 B2 units. Path A remained at 159. Step 2 consumed only the corrected 79,369-row
pool. No operational values were emitted.

Release correction: the final assertion above was incomplete. A broader local
restricted-term check found 39 additional path-term rows, including compound
tokens. A separate lexical safety filter now removes them before candidate
emission. The current pool is 79,330 (B1 75,615; B2 1,752; Path A 1,963),
566 below the original 79,896. Normalization and exclusion hashes are unchanged;
the construction universe remains B1 9,263; B2 1,478; Path A 159.
"""
    (OUT / "g20c_step1_rerun_reconciliation_memo.md").write_text(
        memo, encoding="utf-8"
    )
    print(reconciliation.to_string(index=False))


if __name__ == "__main__":
    main()
