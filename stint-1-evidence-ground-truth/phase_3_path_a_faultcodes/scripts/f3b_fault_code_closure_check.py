from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]
STINT_ROOT = PROJECT_ROOT / "stint-1-evidence-ground-truth"
F3_ROOT = STINT_ROOT / "phase_3_path_a_faultcodes"
OUTPUTS_DIR = F3_ROOT / "outputs"

SCORING_MATRIX = OUTPUTS_DIR / "oem_fault_code_crosswalk_sanitized.csv"
TARGET_SUMMARY = OUTPUTS_DIR / "oem_fault_code_crosswalk_target_summary.csv"

HIGH_REVIEW = OUTPUTS_DIR / "oem_fault_code_high_candidate_review_sanitized.csv"
SUMMARY_JSON = OUTPUTS_DIR / "f3b_fault_code_closure_summary.json"
MEMO_MD = OUTPUTS_DIR / "f3b_fault_code_closure_memo.md"


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    df = pd.read_csv(SCORING_MATRIX)
    high = df[df["status"].eq("candidate_high_requires_review")].copy()
    target_summary = pd.read_csv(TARGET_SUMMARY)

    high_by_code = (
        high.groupby("fault_code_key")
        .agg(
            high_target_count=("target", "nunique"),
            high_targets=("target", lambda values: ";".join(sorted(set(values)))),
            high_rows=("target", "size"),
            frequency=("frequency", "first"),
            max_match_score=("match_score", "max"),
            candidate_concepts=("candidate_concept_id", lambda values: ";".join(sorted(set(str(v) for v in values if str(v))))),
        )
        .reset_index()
        .sort_values(["high_target_count", "frequency", "fault_code_key"], ascending=[False, False, True])
    )
    high_by_code["multi_target_high_candidate"] = high_by_code["high_target_count"] > 1
    high_by_code["review_requirement"] = high_by_code["multi_target_high_candidate"].map(
        {
            True: "blind_or_target_specific_review_required_before_counting",
            False: "blind_review_required_before_promotion",
        }
    )
    high_by_code["raw_values_emitted"] = False
    high_by_code.to_csv(HIGH_REVIEW, index=False)

    status_counts = Counter(df["status"])
    activity = target_summary[target_summary["target"].eq("Activity")]
    activity_high = int(activity["fault_code_candidates_high"].iloc[0]) if not activity.empty else 0
    activity_medium = int(activity["fault_code_candidates_medium"].iloc[0]) if not activity.empty else 0
    activity_unresolved = int(activity["fault_code_unresolved"].iloc[0]) if not activity.empty else 0

    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "task": "F3b_fault_code_closure_check",
        "scoring_matrix_rows": int(len(df)),
        "scoring_matrix_definition": "79 fault-code keys scored against 4 target families; not emitted mappings",
        "candidate_rows_total": int(status_counts.get("candidate_high_requires_review", 0) + status_counts.get("candidate_medium_requires_review", 0)),
        "candidate_high_rows": int(status_counts.get("candidate_high_requires_review", 0)),
        "candidate_medium_rows": int(status_counts.get("candidate_medium_requires_review", 0)),
        "unresolved_rows": int(status_counts.get("unresolved_below_threshold", 0)),
        "high_candidate_distinct_fault_code_keys": int(high["fault_code_key"].nunique()),
        "high_candidate_codes_with_single_target": int((high_by_code["high_target_count"] == 1).sum()),
        "high_candidate_codes_with_multiple_targets": int((high_by_code["high_target_count"] > 1).sum()),
        "activity_result": {
            "candidate_high": activity_high,
            "candidate_medium": activity_medium,
            "unresolved": activity_unresolved,
            "interpretation": "fault codes describe condition/state, not technician action; Activity=0 is a domain finding, not a parser failure.",
        },
        "manual_review_status": "high_candidates_identified_not_blind_reviewed",
        "blind_review_required": True,
        "measurement_readiness_change": "none",
        "raw_values_emitted": False,
        "outputs": {
            "high_candidate_review_csv": str(HIGH_REVIEW.relative_to(PROJECT_ROOT)),
            "summary_json": str(SUMMARY_JSON.relative_to(PROJECT_ROOT)),
            "memo": str(MEMO_MD.relative_to(PROJECT_ROOT)),
        },
    }
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    memo = f"""# F3b Fault Code Closure Check

## Scope

This mini-pass closes the F3 accounting language before Path B. It does not change the
F3 scoring results and does not manually validate candidate mappings.

## Scoring Matrix, Not Crosswalk

| metric | value |
| --- | ---: |
| scoring matrix rows | {summary["scoring_matrix_rows"]} |
| high candidate rows | {summary["candidate_high_rows"]} |
| medium candidate rows | {summary["candidate_medium_rows"]} |
| unresolved rows | {summary["unresolved_rows"]} |

The `316` rows are a scoring matrix: `79` fault-code keys scored against `4` target
families. They are not `316` mappings.

## High Candidate Review Queue

| metric | value |
| --- | ---: |
| high candidate rows | {summary["candidate_high_rows"]} |
| distinct fault-code keys with high candidates | {summary["high_candidate_distinct_fault_code_keys"]} |
| codes with one high target | {summary["high_candidate_codes_with_single_target"]} |
| codes with multiple high targets | {summary["high_candidate_codes_with_multiple_targets"]} |

The 12 high rows correspond to 10 fault-code keys. Two keys have high candidates in more
than one target family, so downstream denominators must not count them as independent
evidence without target-specific review.

## Activity Finding

`Activity` has zero high and zero medium candidates across the 79 fault-code keys. This is
treated as a domain finding: fault codes describe condition/state, not technician action.

## Controls

- No high candidate is promoted by F3b.
- Blind review is required before any candidate can become independent review evidence.
- All F3 candidates remain `expert_inference`, `silver-medium`, and `derived_from_rules`.
- Measurement readiness remains unchanged.
"""
    MEMO_MD.write_text(memo, encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
