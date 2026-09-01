from __future__ import annotations

import csv
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]
REFERENCE_ROOT = PROJECT_ROOT / "stint-1.1-reference-layer"
STINT_ROOT = PROJECT_ROOT / "stint-1-evidence-ground-truth"
F1_ROOT = STINT_ROOT / "phase_1_lexical"
OUTPUTS_DIR = F1_ROOT / "outputs"
GROUPED_DIR = OUTPUTS_DIR / "lexical_layer_v2"
INTERNAL_DIR = PROJECT_ROOT / "reports" / "internal"

RAW_LEXICAL_V1 = (
    REFERENCE_ROOT
    / "reference_layer"
    / "lexical_layer"
    / "lexical_seed_dictionary_v1.csv"
)
GROUPED = GROUPED_DIR / "lexical_semantic_domain_grouping_with_aliases_v1_sanitized.csv"
CANONICAL_VOCAB_WORKING = OUTPUTS_DIR / "canonical_vocabulary" / "canonical_vocabulary_v1_working.csv"
EXTERNAL_FAILURE_VOCAB = OUTPUTS_DIR / "canonical_vocabulary" / "external_failure_vocabulary_v1.csv"
TRANSLATION_ALIASES_ES = OUTPUTS_DIR / "canonical_vocabulary" / "translation_aliases_es_v1.csv"

SCORE_DISTRIBUTION_CSV = OUTPUTS_DIR / "f1e_semantic_match_score_distribution.csv"
SANITIZED_SAMPLE_CSV = OUTPUTS_DIR / "f1e_semantic_match_quality_sample_sanitized.csv"
UNRESOLVED_PROFILE_CSV = OUTPUTS_DIR / "f1e_unresolved_profile.csv"
SUMMARY_JSON = OUTPUTS_DIR / "f1e_semantic_match_quality_summary.json"
MEMO_MD = OUTPUTS_DIR / "f1e_semantic_match_quality_memo.md"
INTERNAL_REVIEW_CSV = INTERNAL_DIR / "f1e_semantic_match_quality_review_internal_redacted.csv"


ABBREVIATIONS = {
    "gb": "gearbox",
    "gbx": "gearbox",
    "gen": "generator",
    "conv": "converter",
    "cnv": "converter",
    "xfmr": "transformer",
    "trafo": "transformer",
    "brg": "bearing",
    "brake": "brake",
    "brakes": "brake",
    "insp": "inspect",
    "inspection": "inspect",
    "inspected": "inspect",
    "repl": "replace",
    "replaced": "replace",
    "replacement": "replace",
    "repairs": "repair",
    "repaired": "repair",
    "maint": "maintenance",
    "comm": "communication",
    "comms": "communication",
    "temp": "temperature",
    "vib": "vibration",
    "vibrations": "vibration",
    "umrichter": "converter",
}


def stable_key(value: object, prefix: str) -> str:
    raw = "" if value is None or pd.isna(value) else str(value)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}-{digest}"


def normalize_text(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    text = str(value).lower()
    text = re.sub(r"[^a-z0-9áéíóúüñ]+", " ", text)
    tokens = []
    for token in text.split():
        token = ABBREVIATIONS.get(token.strip(), token.strip())
        if token:
            tokens.append(token)
    return " ".join(tokens)


def consolidate_term(term: object) -> str:
    tokens = normalize_text(term).split()
    collapsed: list[str] = []
    for token in tokens:
        if not collapsed or collapsed[-1] != token:
            collapsed.append(token)
    return " ".join(collapsed)


def redacted_text(value: object) -> str:
    text = "" if value is None or pd.isna(value) else str(value)
    text = re.sub(r"\b\d+(?:[.,:/-]\d+)*\b", "<NUM>", text)
    text = re.sub(r"\b[A-Z]{2,}[-_/]?[A-Z0-9]{2,}\b", "<CODE>", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:120]


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def load_term_lookup() -> dict[str, str]:
    raw = pd.read_csv(RAW_LEXICAL_V1)
    raw["consolidated_term"] = raw["observed_term"].map(consolidate_term)
    raw["term_key"] = raw["consolidated_term"].map(lambda value: stable_key(value, "TERM"))
    lookup: dict[str, str] = {}
    for term_key, group in raw.groupby("term_key"):
        values = sorted(set(str(v) for v in group["consolidated_term"].dropna() if str(v).strip()))
        if values:
            lookup[str(term_key)] = values[0]
    return lookup


def load_concept_lookup() -> dict[str, dict[str, str]]:
    frames = []
    for path in [CANONICAL_VOCAB_WORKING, EXTERNAL_FAILURE_VOCAB]:
        if path.exists():
            frames.append(pd.read_csv(path))
    vocab = pd.concat(frames, ignore_index=True, sort=False)
    records: dict[str, dict[str, str]] = {}
    for _, row in vocab.iterrows():
        concept_id = str(row.get("concept_id", "") or "")
        if concept_id and concept_id not in records:
            records[concept_id] = {
                "canonical_concept": str(row.get("canonical_concept", "") or ""),
                "vocabulary_owner": str(row.get("vocabulary_owner", "") or ""),
                "target": str(row.get("target", "") or ""),
            }
    if TRANSLATION_ALIASES_ES.exists():
        aliases = pd.read_csv(TRANSLATION_ALIASES_ES)
        for _, row in aliases.iterrows():
            concept_id = str(row.get("canonical_concept_id", "") or "")
            if concept_id and concept_id not in records:
                records[concept_id] = {
                    "canonical_concept": str(row.get("canonical_alias_es", "") or ""),
                    "vocabulary_owner": str(row.get("vocabulary_owner", "") or ""),
                    "target": str(row.get("target", "") or ""),
                }
    return records


def score_bucket(row: pd.Series) -> str:
    if not bool(row["mapped_to_canonical_concept"]):
        return "unresolved_below_threshold"
    score = float(row["match_score"])
    threshold = float(row["match_threshold"])
    if score >= max(0.70, threshold + 0.12):
        return "high"
    if score < threshold + 0.06:
        return "borderline"
    return "middle"


def choose_sample(mapped: pd.DataFrame) -> pd.DataFrame:
    parts = []
    high = mapped[mapped["score_band"] == "high"].sort_values("match_score", ascending=False).head(10)
    middle = mapped[mapped["score_band"] == "middle"].copy()
    if not middle.empty:
        middle["mid_distance"] = (middle["match_score"] - 0.62).abs()
        middle = middle.sort_values(["mid_distance", "match_score"]).head(10)
    borderline = mapped[mapped["score_band"] == "borderline"].copy()
    if not borderline.empty:
        borderline["threshold_margin"] = borderline["match_score"] - borderline["match_threshold"]
        borderline = borderline.sort_values(["threshold_margin", "match_score"]).head(10)
    for label, frame in [("high", high), ("middle", middle), ("borderline", borderline)]:
        frame = frame.copy()
        frame["sample_band"] = label
        parts.append(frame)
    return pd.concat(parts, ignore_index=True, sort=False)


def main() -> None:
    if not GROUPED.exists():
        raise FileNotFoundError(f"Missing grouped input: {GROUPED}")
    grouped = pd.read_csv(GROUPED)
    grouped["score_band"] = grouped.apply(score_bucket, axis=1)
    mapped = grouped[grouped["mapped_to_canonical_concept"] == True].copy()
    unresolved = grouped[grouped["mapped_to_canonical_concept"] == False].copy()

    distribution = (
        grouped.groupby(["target", "score_band"], dropna=False)
        .size()
        .reset_index(name="row_count")
        .sort_values(["target", "score_band"])
    )
    distribution.to_csv(SCORE_DISTRIBUTION_CSV, index=False)

    unresolved_profile = (
        unresolved.groupby(["observed_target_hint", "source_text_field", "stratum"], dropna=False)
        .agg(row_count=("term_key", "size"), distinct_term_keys=("term_key", "nunique"))
        .reset_index()
        .sort_values(["row_count"], ascending=False)
    )
    unresolved_profile.to_csv(UNRESOLVED_PROFILE_CSV, index=False)

    sample = choose_sample(mapped)
    sanitized_fields = [
        "sample_band",
        "term_key",
        "target",
        "observed_target_hint",
        "source_text_field",
        "stratum",
        "contractor_path",
        "record_count",
        "canonical_concept_id",
        "canonical_concept_key",
        "vocabulary_owner",
        "semantic_level",
        "match_score",
        "match_threshold",
        "match_text_source",
        "status",
        "label_generation_method",
        "evaluation_independence",
        "raw_values_emitted",
    ]
    sample[sanitized_fields].to_csv(SANITIZED_SAMPLE_CSV, index=False)

    term_lookup = load_term_lookup()
    concept_lookup = load_concept_lookup()
    internal_rows = []
    for _, row in sample.iterrows():
        concept_id = str(row.get("canonical_concept_id", "") or "")
        concept = concept_lookup.get(concept_id, {})
        internal_rows.append(
            {
                "sample_band": row.get("sample_band", ""),
                "term_key": row.get("term_key", ""),
                "observed_term_redacted": redacted_text(term_lookup.get(str(row.get("term_key", "")), "")),
                "target": row.get("target", ""),
                "canonical_concept_id": concept_id,
                "canonical_concept_redacted": redacted_text(concept.get("canonical_concept", "")),
                "vocabulary_owner": row.get("vocabulary_owner", ""),
                "match_score": row.get("match_score", ""),
                "match_threshold": row.get("match_threshold", ""),
                "match_text_source": row.get("match_text_source", ""),
                "manual_review_result": "",
                "manual_review_notes": "",
            }
        )
    write_csv(
        INTERNAL_REVIEW_CSV,
        internal_rows,
        [
            "sample_band",
            "term_key",
            "observed_term_redacted",
            "target",
            "canonical_concept_id",
            "canonical_concept_redacted",
            "vocabulary_owner",
            "match_score",
            "match_threshold",
            "match_text_source",
            "manual_review_result",
            "manual_review_notes",
        ],
    )

    score_stats = {}
    for band, frame in mapped.groupby("score_band"):
        score_stats[band] = {
            "rows": int(len(frame)),
            "min": round(float(frame["match_score"].min()), 4),
            "p25": round(float(frame["match_score"].quantile(0.25)), 4),
            "median": round(float(frame["match_score"].median()), 4),
            "p75": round(float(frame["match_score"].quantile(0.75)), 4),
            "max": round(float(frame["match_score"].max()), 4),
        }

    threshold_by_hint = (
        grouped.groupby("observed_target_hint")["match_threshold"]
        .agg(lambda values: sorted(set(float(v) for v in values)))
        .to_dict()
    )
    threshold_by_hint = {
        str(target): [round(v, 2) for v in values]
        for target, values in threshold_by_hint.items()
    }

    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "task": "F1e_semantic_match_quality_check",
        "input_rows": int(len(grouped)),
        "mapped_rows": int(len(mapped)),
        "unresolved_rows": int(len(unresolved)),
        "mapped_pct": round(float(len(mapped) / len(grouped) * 100), 2),
        "score_band_counts": {str(k): int(v) for k, v in grouped["score_band"].value_counts().sort_index().items()},
        "mapped_score_stats": score_stats,
        "thresholds_by_observed_target_hint": threshold_by_hint,
        "manual_review_sample_rows": int(len(sample)),
        "manual_review_sample_design": "10 high, 10 middle, 10 borderline semantic anchors when available",
        "internal_review_file_is_gitignored": True,
        "translation_alias_net_gain_note": "F1d4 added 9 mapped rows and 6 mapped concepts over F1d2; 80 mapped rows selected translation_alias_es as match text.",
        "evaluation_independence": "derived_from_rules",
        "label_generation_method": "semantic_embedding_plus_translation_alias_rule_set_v1",
        "quality_decision": "pending_manual_review",
        "raw_values_emitted": False,
        "outputs": {
            "score_distribution_csv": str(SCORE_DISTRIBUTION_CSV.relative_to(PROJECT_ROOT)),
            "sanitized_sample_csv": str(SANITIZED_SAMPLE_CSV.relative_to(PROJECT_ROOT)),
            "unresolved_profile_csv": str(UNRESOLVED_PROFILE_CSV.relative_to(PROJECT_ROOT)),
            "summary_json": str(SUMMARY_JSON.relative_to(PROJECT_ROOT)),
            "memo": str(MEMO_MD.relative_to(PROJECT_ROOT)),
            "internal_review_csv": str(INTERNAL_REVIEW_CSV.relative_to(PROJECT_ROOT)),
        },
    }
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    memo = f"""# F1e Semantic Match Quality Check

## Scope

This pass audits the F1d4 semantic grouping output before freezing the F1 lexical layer.
It does not create additional labels and does not promote any evidence to contractual
measurement readiness.

## Thresholds

F1d4 used target-specific cosine thresholds:

| target | threshold |
| --- | ---: |
"""
    for target, thresholds in summary["thresholds_by_observed_target_hint"].items():
        joined = ", ".join(f"{threshold:.2f}" for threshold in thresholds)
        memo += f"| {target} | {joined} |\n"

    memo += f"""
## Score Bands

| band | rows |
| --- | ---: |
"""
    for band, count in summary["score_band_counts"].items():
        memo += f"| {band} | {count} |\n"

    memo += """
## Interpretation

- `high` means the semantic score is at least `max(0.70, threshold + 0.12)`.
- `middle` means the score is above threshold but not close to either the high band or the cutoff.
- `borderline` means the score is within `0.06` of the target threshold.
- `unresolved_below_threshold` remains unresolved and is not promoted.

## Manual Review Sample

A 30-row sample was generated for precision review: 10 high-score anchors, 10 middle-score
anchors, and 10 borderline anchors, subject to availability. The versioned sample contains
only keys, target metadata, thresholds, scores, provenance fields, and no raw operational
values. An internal redacted review file was also generated under `reports/internal/`, which
is ignored by Git.

## Controls

- All rows remain `expert_inference` or `unresolved`.
- All mapped rows remain `evaluation_independence = derived_from_rules`.
- These anchors may support weak supervision and POC proxy evidence after review.
- They do not support contractual denominators or independent STINT_2 evaluation as-is.
- `translation_alias_es` added little net coverage, which supports the multilingual-backbone
  decision over broad pre-translation.

## Decision

F1 is not frozen by this pass. The semantic layer is ready for manual precision review.
"""
    MEMO_MD.write_text(memo, encoding="utf-8")

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
