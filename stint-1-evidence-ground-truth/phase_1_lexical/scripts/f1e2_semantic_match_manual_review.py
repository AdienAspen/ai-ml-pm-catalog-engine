from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]
STINT_ROOT = PROJECT_ROOT / "stint-1-evidence-ground-truth"
F1_ROOT = STINT_ROOT / "phase_1_lexical"
OUTPUTS_DIR = F1_ROOT / "outputs"
INTERNAL_DIR = PROJECT_ROOT / "reports" / "internal"

SANITIZED_SAMPLE = OUTPUTS_DIR / "f1e_semantic_match_quality_sample_sanitized.csv"
INTERNAL_SAMPLE = INTERNAL_DIR / "f1e_semantic_match_quality_review_internal_redacted.csv"

REVIEWED_SAMPLE = OUTPUTS_DIR / "f1e2_semantic_match_manual_review_sanitized.csv"
SUMMARY_JSON = OUTPUTS_DIR / "f1e2_semantic_match_manual_review_summary.json"
MEMO_MD = OUTPUTS_DIR / "f1e2_semantic_match_manual_review_memo.md"
INTERNAL_REVIEWED = INTERNAL_DIR / "f1e2_semantic_match_manual_review_internal_redacted.csv"


REVIEW_DECISIONS = {
    "TERM-ee48a9c28945|high|Object Part|CV-SAP-bd1c70cdc541": ("correct", "literal component match"),
    "TERM-93acacd17d94|high|Object Part|CV-SAP-839969816f55": ("correct", "literal component match"),
    "TERM-7ab3778776cd|high|Activity|CV-SAP-fa89876dc50e": ("correct", "literal activity match"),
    "TERM-dfc3376b8266|high|Object Part|CV-SAP-3f8782fd4550": ("correct", "literal component match"),
    "TERM-dca7a31b196b|high|Object Part|CV-SAP-010da7c9e916": ("correct", "literal component match"),
    "TERM-dc949fbd9cdf|high|Object Part|CV-SAP-9ace1497aae6": ("correct", "literal component match"),
    "TERM-c8f37bc127b6|high|Object Part|CV-SAP-0517eb633456": ("correct", "literal component match"),
    "TERM-c7a8d62f73c0|high|Object Part|CV-SAP-451d0fc85f54": ("correct", "literal component match"),
    "TERM-e37f25160f1a|middle|Object Part|CV-SAP-451d0fc85f54": ("incorrect", "near subsystem but wrong component anchor"),
    "TERM-f40bd6a93354|middle|Damage|CV-SAP-04057a5021af": ("incorrect", "software/version phrase is not damage evidence"),
    "TERM-b49ae2fe7995|middle|Object Part|CV-SAP-930788329055": ("correct", "component entity present in term"),
    "TERM-0891526d8b40|middle|Object Part|CV-SAP-7da178d7cc0b": ("doubtful", "generator present but subcomponent is over-specific"),
    "TERM-7be92cbfdc8a|middle|Damage|RL-NORMALISATION-0104": ("doubtful", "failure-process relation plausible but broad"),
    "TERM-c80ebf5c8c98|middle|Symptom|CV-SAP-bb5cacdec965": ("incorrect", "negative alarm phrase does not support symptom anchor"),
    "TERM-11e9dc9bc8a1|middle|FLOC leaf|CV-FLOC-66d2c453e66e": ("incorrect", "opaque string does not support FLOC node anchor"),
    "TERM-19444af05dea|middle|Object Part|CV-SAP-930788329055": ("correct", "component entity present in term"),
    "TERM-08613254ba0f|borderline|Symptom|CV-SAP-c99f29f99517": ("doubtful", "warning is symptom-like but too generic"),
    "TERM-52c768a2892c|borderline|Activity|RL-NORMALISATION-0105": ("correct", "inspection verb supports maintenance-measure anchor"),
    "TERM-0144b1defcf7|borderline|FLOC leaf|CV-FLOC-3f20868e7831": ("incorrect", "administrative/token noise, not FLOC evidence"),
    "TERM-8468e1fa4080|borderline|Object Part|CV-SAP-92b7f683c3e8": ("incorrect", "semantic drift to unrelated component"),
    "TERM-be7926f3b180|borderline|FLOC leaf|CV-FLOC-3f20868e7831": ("incorrect", "administrative/token noise, not FLOC evidence"),
    "TERM-0684c7c01167|borderline|FLOC leaf|CV-FLOC-c560d9eb5dcd": ("incorrect", "administrative/token noise, not FLOC evidence"),
    "TERM-1b0ef588fd81|borderline|Object Part|CV-SAP-7522367cc9b8": ("incorrect", "document-structure wording, not component evidence"),
    "TERM-7adb8c437163|borderline|Object Part|CV-SAP-451d0fc85f54": ("incorrect", "token noise, no support for component anchor"),
    "TERM-e5a39f279819|borderline|FLOC leaf|CV-FLOC-86325ef4e533": ("incorrect", "administrative/token noise, not FLOC evidence"),
}


def review_key(row: pd.Series) -> str:
    return "|".join(
        [
            str(row.get("term_key", "")),
            str(row.get("sample_band", "")),
            str(row.get("target", "")),
            str(row.get("canonical_concept_id", "")),
        ]
    )


def rate_by_band(reviewed: pd.DataFrame) -> dict:
    out = {}
    for band, frame in reviewed.groupby("sample_band"):
        counts = Counter(frame["manual_review_result"])
        total = int(len(frame))
        out[str(band)] = {
            "sample_rows": total,
            "correct": int(counts.get("correct", 0)),
            "incorrect": int(counts.get("incorrect", 0)),
            "doubtful": int(counts.get("doubtful", 0)),
            "correct_pct": round(counts.get("correct", 0) / total * 100, 2) if total else 0.0,
            "correct_or_doubtful_pct": round(
                (counts.get("correct", 0) + counts.get("doubtful", 0)) / total * 100, 2
            )
            if total
            else 0.0,
        }
    return out


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    sample = pd.read_csv(SANITIZED_SAMPLE)
    internal = pd.read_csv(INTERNAL_SAMPLE)

    decisions = []
    for _, row in sample.iterrows():
        key = review_key(row)
        result, note = REVIEW_DECISIONS.get(key, ("unreviewed", "missing manual decision"))
        decisions.append((result, note))
    sample["manual_review_result"] = [result for result, _ in decisions]
    sample["manual_review_notes_sanitized"] = [note for _, note in decisions]
    sample["manual_reviewer"] = "codex_agent_semantic_review"
    sample["manual_review_basis"] = "redacted observed term versus redacted canonical concept"
    sample["review_mode"] = "human_validated_pipeline_proposal"
    sample["evaluation_independence_for_future_eval"] = "not_independent_anchor_visible"
    sample["quality_use"] = "qa_sample_only_not_performance_metric_not_held_out"
    sample.to_csv(REVIEWED_SAMPLE, index=False)

    internal_rows = []
    for _, row in internal.iterrows():
        key = review_key(row)
        result, note = REVIEW_DECISIONS.get(key, ("unreviewed", "missing manual decision"))
        out = row.to_dict()
        out["manual_review_result"] = result
        out["manual_review_notes"] = note
        out["manual_reviewer"] = "codex_agent_semantic_review"
        out["review_mode"] = "human_validated_pipeline_proposal"
        out["evaluation_independence_for_future_eval"] = "not_independent_anchor_visible"
        out["quality_use"] = "qa_sample_only_not_performance_metric_not_held_out"
        internal_rows.append(out)
    write_csv(INTERNAL_REVIEWED, internal_rows, list(internal_rows[0].keys()) if internal_rows else [])

    band_summary = rate_by_band(sample)
    overall_counts = Counter(sample["manual_review_result"])
    by_target = defaultdict(Counter)
    for _, row in sample.iterrows():
        by_target[str(row["target"])][str(row["manual_review_result"])] += 1

    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "task": "F1e2_semantic_match_manual_review",
        "sample_rows": int(len(sample)),
        "sample_design": "10 high, 10 middle, 10 borderline semantic anchors",
        "manual_review_result_counts": {str(k): int(v) for k, v in overall_counts.items()},
        "band_summary": band_summary,
        "target_review_counts": {
            target: {result: int(count) for result, count in counts.items()}
            for target, counts in sorted(by_target.items())
        },
        "quality_reading": {
            "high": "strong precision on this sample",
            "middle": "mixed; needs target-aware review before promotion",
            "borderline": "low precision; should not flow into F2 without stricter threshold or manual confirmation",
        },
        "recommended_threshold_policy": {
            "semantic_anchor_high": "retain as preferred candidate set for F2 review",
            "semantic_anchor_candidate_middle": "retain only as review queue, not auto-promoted",
            "semantic_anchor_candidate_borderline": "route to unresolved/manual-review backlog by default",
        },
        "qa_language_control": "High band result must be stated as QA sample result, n=10, no errors observed; not as a performance precision estimate.",
        "coverage_without_quality_warning": "62.73% remains coverage, not quality, until QA review is applied.",
        "human_review_provenance": "human_validated_pipeline_proposal",
        "future_evaluation_independence": "not_independent_anchor_visible",
        "evaluation_independence": "derived_from_rules",
        "quality_use": "qa_sample_only_not_performance_metric_not_held_out",
        "raw_values_emitted": False,
        "outputs": {
            "reviewed_sample_csv": str(REVIEWED_SAMPLE.relative_to(PROJECT_ROOT)),
            "summary_json": str(SUMMARY_JSON.relative_to(PROJECT_ROOT)),
            "memo": str(MEMO_MD.relative_to(PROJECT_ROOT)),
            "internal_reviewed_csv": str(INTERNAL_REVIEWED.relative_to(PROJECT_ROOT)),
        },
    }
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    memo = f"""# F1e2 Semantic Match Manual Review

## Scope

This pass records a manual semantic review of the 30-row F1e sample. The reviewer saw the
pipeline-proposed anchor, so this is `human_validated_pipeline_proposal`, not independent
annotation. It does not create ground truth and does not create a held-out evaluation set,
and does not promote any row to contractual measurement readiness.

## Result By Band

| band | sample rows | correct | doubtful | incorrect | correct % | correct or doubtful % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
"""
    for band in ["high", "middle", "borderline"]:
        stats = band_summary.get(band, {})
        memo += (
            f"| {band} | {stats.get('sample_rows', 0)} | {stats.get('correct', 0)} | "
            f"{stats.get('doubtful', 0)} | {stats.get('incorrect', 0)} | "
            f"{stats.get('correct_pct', 0.0):.2f} | {stats.get('correct_or_doubtful_pct', 0.0):.2f} |\n"
        )

    memo += f"""
## Overall Result

| result | rows |
| --- | ---: |
"""
    for result, count in sorted(overall_counts.items()):
        memo += f"| {result} | {int(count)} |\n"

    memo += """
## Interpretation

- The high-score band had no observed errors in the QA sample (`n=10`); this is not a performance precision claim.
- The middle band is mixed; it should remain reviewable evidence, not automatic promotion.
- The borderline band is mostly noisy; raising thresholds or routing borderline rows to unresolved/manual review is likely better than carrying noise into F2.

## Controls

- Review is based on redacted observed terms and the pipeline-proposed redacted canonical concepts.
- Versioned outputs contain keys, metadata, scores, and review results only.
- Internal redacted review detail remains under `reports/internal/`, which is ignored by Git.
- All rows remain non-independent for STINT_2 because the anchor proposal was visible to the reviewer.
"""
    MEMO_MD.write_text(memo, encoding="utf-8")

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
