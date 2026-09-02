from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]
STINT_ROOT = PROJECT_ROOT / "stint-1-evidence-ground-truth"
F1_ROOT = STINT_ROOT / "phase_1_lexical"
OUTPUTS_DIR = F1_ROOT / "outputs"
LAYER_DIR = OUTPUTS_DIR / "lexical_layer_v2"
EVIDENCE_ROOT = STINT_ROOT / "evidence"

F1D4 = LAYER_DIR / "lexical_semantic_domain_grouping_with_aliases_v1_sanitized.csv"
F1E2_REVIEW = OUTPUTS_DIR / "f1e2_semantic_match_manual_review_sanitized.csv"

FROZEN_CANDIDATES = LAYER_DIR / "lexical_layer_v2_high_confidence_candidates_sanitized.csv"
UNRESOLVED_ROUTING = LAYER_DIR / "lexical_layer_v2_unresolved_routing_sanitized.csv"
INDEPENDENT_REVIEW_SEED = OUTPUTS_DIR / "f1e2_manual_review_seed_sanitized.csv"
SUMMARY_JSON = OUTPUTS_DIR / "f1f_lexical_layer_freeze_decision_summary.json"
MEMO_MD = OUTPUTS_DIR / "f1f_lexical_layer_freeze_decision_memo.md"


def score_band(row: pd.Series) -> str:
    if not bool(row["mapped_to_canonical_concept"]):
        return "unresolved_below_threshold"
    score = float(row["match_score"])
    threshold = float(row["match_threshold"])
    if score >= max(0.70, threshold + 0.12):
        return "high"
    if score < threshold + 0.06:
        return "borderline"
    return "middle"


def main() -> None:
    if not F1D4.exists():
        raise FileNotFoundError(f"Missing F1d4 input: {F1D4}")
    if not F1E2_REVIEW.exists():
        raise FileNotFoundError(f"Missing F1e2 review input: {F1E2_REVIEW}")

    df = pd.read_csv(F1D4)
    df["score_band"] = df.apply(score_band, axis=1)

    high = df[df["score_band"] == "high"].copy()
    non_high = df[df["score_band"] != "high"].copy()

    high["f1_consumption_status"] = "usable_high_confidence_candidate"
    high["recommended_next_step"] = "consume_in_f2_with_target_review"
    high["can_support_proxy_denominator"] = True
    high["can_support_contractual_denominator"] = False
    high["quality_basis"] = "F1e2 high band manual sample: 10 correct of 10"

    non_high["f1_consumption_status"] = "unresolved_pending_rework_or_manual_review"
    non_high["recommended_next_step"] = non_high["score_band"].map(
        {
            "middle": "route_to_unresolved_not_auto_promoted",
            "borderline": "route_to_unresolved_not_auto_promoted",
            "unresolved_below_threshold": "remain_unresolved",
        }
    )
    non_high["can_support_proxy_denominator"] = False
    non_high["can_support_contractual_denominator"] = False
    non_high["quality_basis"] = non_high["score_band"].map(
        {
            "middle": "F1e2 middle band manual sample: 3 correct, 2 doubtful, 5 incorrect of 10",
            "borderline": "F1e2 borderline manual sample: 1 correct, 2 doubtful, 7 incorrect of 10",
            "unresolved_below_threshold": "below semantic threshold",
        }
    )

    high.to_csv(FROZEN_CANDIDATES, index=False)
    non_high.to_csv(UNRESOLVED_ROUTING, index=False)

    review = pd.read_csv(F1E2_REVIEW)
    review_seed = review.copy()
    review_seed["evaluation_independence"] = "independent_manual_review"
    review_seed["evidence_type"] = "expert_review_quality_check"
    review_seed["tier"] = "silver-medium"
    review_seed["can_support_contractual_denominator"] = False
    review_seed["can_support_proxy_denominator"] = review_seed["manual_review_result"].eq("correct")
    review_seed["quality_use"] = "held_out_seed_for_future_calibration_not_production_accuracy"
    review_seed.to_csv(INDEPENDENT_REVIEW_SEED, index=False)

    target_summary = {}
    for target, frame in df.groupby("target"):
        high_frame = high[high["target"] == target]
        target_summary[str(target)] = {
            "rows": int(len(frame)),
            "usable_high_confidence_rows": int(len(high_frame)),
            "usable_high_confidence_pct": round(float(len(high_frame) / len(frame) * 100), 2)
            if len(frame)
            else 0.0,
            "high_confidence_distinct_canonical_concepts": int(
                high_frame["canonical_concept_id"].dropna().nunique()
            ),
            "unresolved_or_routed_out_rows": int(len(non_high[non_high["target"] == target])),
        }

    observed_hint_summary = {}
    for hint, frame in df.groupby("observed_target_hint"):
        high_frame = high[high["observed_target_hint"] == hint]
        observed_hint_summary[str(hint)] = {
            "rows": int(len(frame)),
            "usable_high_confidence_rows": int(len(high_frame)),
            "usable_high_confidence_pct": round(float(len(high_frame) / len(frame) * 100), 2)
            if len(frame)
            else 0.0,
            "high_confidence_distinct_canonical_concepts": int(
                high_frame["canonical_concept_id"].dropna().nunique()
            ),
            "unresolved_or_routed_out_rows": int(
                len(non_high[non_high["observed_target_hint"] == hint])
            ),
        }

    review_counts = Counter(review["manual_review_result"])
    band_counts = Counter(df["score_band"])
    high_owner_counts = Counter(high["vocabulary_owner"].fillna(""))

    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "task": "F1f_lexical_layer_freeze_decision",
        "input_rows": int(len(df)),
        "reported_coverage_rows_prior_to_quality_filter": int(df["mapped_to_canonical_concept"].sum()),
        "reported_coverage_pct_prior_to_quality_filter": round(
            float(df["mapped_to_canonical_concept"].sum() / len(df) * 100), 2
        ),
        "usable_high_confidence_rows": int(len(high)),
        "usable_high_confidence_pct": round(float(len(high) / len(df) * 100), 2),
        "routed_to_unresolved_or_rework_rows": int(len(non_high)),
        "high_confidence_distinct_canonical_concepts": int(
            high["canonical_concept_id"].dropna().nunique()
        ),
        "score_band_counts": {str(k): int(v) for k, v in sorted(band_counts.items())},
        "manual_review_result_counts": {str(k): int(v) for k, v in sorted(review_counts.items())},
        "manual_review_seed_rows": int(len(review_seed)),
        "manual_review_seed_independence": "independent_manual_review",
        "target_summary": target_summary,
        "observed_target_hint_summary": observed_hint_summary,
        "high_confidence_vocabulary_owner_counts": {
            str(k): int(v) for k, v in sorted(high_owner_counts.items()) if str(k)
        },
        "decision": {
            "LEXICAL_LAYER": "closed_for_F2_as_high_confidence_candidate_layer",
            "middle_band": "route_to_unresolved_not_auto_promoted",
            "borderline_band": "route_to_unresolved_not_auto_promoted",
            "unresolved_below_threshold": "remain_unresolved",
            "translation_alias_layer": "kept_as_expert_inference_but_low_net_gain",
        },
        "denominator_controls": {
            "contractual": "not_supported",
            "poc_proxy": "high_confidence_candidates_can_enter_F2_review_queue_only",
            "independent_evaluation": "only_manual_review_seed_is_independent_from_embedding_rule_set",
        },
        "raw_values_emitted": False,
        "outputs": {
            "high_confidence_candidates": str(FROZEN_CANDIDATES.relative_to(PROJECT_ROOT)),
            "unresolved_routing": str(UNRESOLVED_ROUTING.relative_to(PROJECT_ROOT)),
            "independent_review_seed": str(INDEPENDENT_REVIEW_SEED.relative_to(PROJECT_ROOT)),
            "summary_json": str(SUMMARY_JSON.relative_to(PROJECT_ROOT)),
            "memo": str(MEMO_MD.relative_to(PROJECT_ROOT)),
        },
    }

    SUMMARY_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    memo = f"""# F1f Lexical Layer Freeze Decision

## Decision

`LEXICAL_LAYER v2` is closed for F2 consumption as a high-confidence candidate layer.
The prior semantic mapping coverage is retained as diagnostic coverage, not quality.

## Coverage After Quality Filter

| metric | value |
| --- | ---: |
| input rows | {summary["input_rows"]} |
| mapped rows before quality filter | {summary["reported_coverage_rows_prior_to_quality_filter"]} |
| mapped pct before quality filter | {summary["reported_coverage_pct_prior_to_quality_filter"]:.2f}% |
| usable high-confidence rows | {summary["usable_high_confidence_rows"]} |
| usable high-confidence pct | {summary["usable_high_confidence_pct"]:.2f}% |
| high-confidence distinct canonical concepts | {summary["high_confidence_distinct_canonical_concepts"]} |
| routed to unresolved/rework | {summary["routed_to_unresolved_or_rework_rows"]} |

## Manual Review Basis

| score band | manual review result |
| --- | --- |
| high | 10 correct / 0 doubtful / 0 incorrect |
| middle | 3 correct / 2 doubtful / 5 incorrect |
| borderline | 1 correct / 2 doubtful / 7 incorrect |

## Routing Rule

- `semantic_anchor_high` is retained as the F2 candidate input.
- `middle` is routed to unresolved/rework, not auto-promoted.
- `borderline` is routed to unresolved/rework, not auto-promoted.
- `unresolved_below_threshold` remains unresolved.

## Controls

- The high-confidence layer remains `expert_inference` and `derived_from_rules`.
- It can support POC proxy review workflows after F2 target review.
- It cannot support contractual denominators.
- The 30 manually reviewed rows are preserved as an independent manual-review seed for future calibration, not as verified production accuracy.
"""
    MEMO_MD.write_text(memo, encoding="utf-8")

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
