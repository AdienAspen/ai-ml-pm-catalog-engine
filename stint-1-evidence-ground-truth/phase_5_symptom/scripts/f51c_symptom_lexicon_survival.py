from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]
REFERENCE_ROOT = PROJECT_ROOT / "stint-1.1-reference-layer"
STINT_ROOT = PROJECT_ROOT / "stint-1-evidence-ground-truth"
F1_DIR = STINT_ROOT / "phase_1_lexical" / "outputs" / "lexical_layer_v2"
F5_OUT = STINT_ROOT / "phase_5_symptom" / "outputs" / "f51_symptom_thread_resolution"

SEED_CONSOLIDATED = (
    REFERENCE_ROOT
    / "reference_layer"
    / "lexical_layer"
    / "lexical_seed_dictionary_v1_consolidated_sanitized.csv"
)
SEED_SANITIZED = (
    REFERENCE_ROOT
    / "reference_layer"
    / "lexical_layer"
    / "lexical_seed_dictionary_v1_sanitized.csv"
)
F1_V2 = F1_DIR / "lexical_layer_v2_sanitized.csv"
F1_HIGH = F1_DIR / "lexical_layer_v2_high_confidence_candidates_sanitized.csv"
F1_UNRESOLVED = F1_DIR / "lexical_layer_v2_unresolved_routing_sanitized.csv"


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def as_bool(value: object) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path, dtype=str).fillna("")


def classify_survival(row: pd.Series, high_lookup: dict[str, pd.Series], unresolved_keys: set[str], v2_keys: set[str]) -> dict:
    term_key = str(row["consolidated_term_key"])
    high = high_lookup.get(term_key)

    if high is not None:
        high_target = str(high.get("target", ""))
        if high_target == "Symptom":
            status = "survived_high_band_as_symptom"
        else:
            status = "survived_high_band_retargeted"
        return {
            "survival_status": status,
            "f1_target": high_target,
            "canonical_concept_id": high.get("canonical_concept_id", ""),
            "vocabulary_owner": high.get("vocabulary_owner", ""),
            "score_band": high.get("score_band", ""),
            "match_method": high.get("match_method", ""),
            "f1_consumption_status": high.get("f1_consumption_status", ""),
        }

    if term_key in unresolved_keys:
        return {
            "survival_status": "fell_to_f1_unresolved_rework",
            "f1_target": "",
            "canonical_concept_id": "",
            "vocabulary_owner": "",
            "score_band": "unresolved",
            "match_method": "",
            "f1_consumption_status": "unresolved_rework",
        }

    if term_key in v2_keys:
        return {
            "survival_status": "retained_in_f1_v2_not_high_band",
            "f1_target": "",
            "canonical_concept_id": "",
            "vocabulary_owner": "",
            "score_band": "not_high",
            "match_method": "",
            "f1_consumption_status": "retained_not_high",
        }

    return {
        "survival_status": "discarded_before_or_during_f1_v2",
        "f1_target": "",
        "canonical_concept_id": "",
        "vocabulary_owner": "",
        "score_band": "discarded",
        "match_method": "",
        "f1_consumption_status": "discarded_or_not_routed",
    }


def main() -> None:
    seed_raw_sanitized = load_csv(SEED_SANITIZED)
    seed = load_csv(SEED_CONSOLIDATED)
    v2 = load_csv(F1_V2)
    high = load_csv(F1_HIGH)
    unresolved = load_csv(F1_UNRESOLVED)

    symptom_raw_seed = seed_raw_sanitized[seed_raw_sanitized["target"].eq("Symptom")].copy()
    symptom_seed = seed[seed["target"].eq("Symptom")].copy()
    if len(symptom_raw_seed) != 289:
        expected_note = f"Expected historical Symptom lexical rows = 289; observed = {len(symptom_raw_seed)}."
    else:
        expected_note = "Historical Symptom lexical rows reconciled at 289; F1 consumes their consolidated term keys."

    high_lookup = {str(row["term_key"]): row for _, row in high.iterrows()}
    unresolved_keys = set(str(v) for v in unresolved["term_key"])
    v2_keys = set(str(v) for v in v2["term_key"])

    rows: list[dict] = []
    for _, row in symptom_seed.iterrows():
        survival = classify_survival(row, high_lookup, unresolved_keys, v2_keys)
        rows.append(
            {
                "term_key": row["consolidated_term_key"],
                "source_concept_id": row["concept_id"],
                "source_text_field": row["source_text_field"],
                "stratum": row["stratum"],
                "contractor_path": row["contractor_path"],
                "seed_record_count": row["record_count"],
                "seed_source_row_count": row["source_row_count"],
                "seed_observed_variant_count": row["observed_variant_count"],
                "survival_status": survival["survival_status"],
                "f1_target": survival["f1_target"],
                "canonical_concept_id": survival["canonical_concept_id"],
                "vocabulary_owner": survival["vocabulary_owner"],
                "score_band": survival["score_band"],
                "match_method": survival["match_method"],
                "f1_consumption_status": survival["f1_consumption_status"],
                "evidence_type": "expert_inference",
                "tier": "silver-medium",
                "evaluation_independence": "derived_from_rules",
                "raw_values_emitted": False,
            }
        )

    by_status = Counter(row["survival_status"] for row in rows)
    by_field_status = Counter((row["source_text_field"], row["survival_status"]) for row in rows)
    by_stratum_status = Counter((row["stratum"], row["survival_status"]) for row in rows)
    high_targets = Counter(row["f1_target"] for row in rows if row["survival_status"].startswith("survived_high"))

    detail_path = F5_OUT / "f51c_symptom_lexicon_survival_sanitized.csv"
    status_path = F5_OUT / "f51c_symptom_lexicon_survival_by_status_sanitized.csv"
    field_path = F5_OUT / "f51c_symptom_lexicon_survival_by_field_sanitized.csv"
    stratum_path = F5_OUT / "f51c_symptom_lexicon_survival_by_stratum_sanitized.csv"
    summary_path = F5_OUT / "f51c_symptom_lexicon_survival_summary_sanitized.json"
    memo_path = F5_OUT / "f51c_symptom_lexicon_survival_memo.md"

    write_csv(
        detail_path,
        rows,
        [
            "term_key",
            "source_concept_id",
            "source_text_field",
            "stratum",
            "contractor_path",
            "seed_record_count",
            "seed_source_row_count",
            "seed_observed_variant_count",
            "survival_status",
            "f1_target",
            "canonical_concept_id",
            "vocabulary_owner",
            "score_band",
            "match_method",
            "f1_consumption_status",
            "evidence_type",
            "tier",
            "evaluation_independence",
            "raw_values_emitted",
        ],
    )

    status_rows = [
        {"survival_status": key, "term_count": int(value), "raw_values_emitted": False}
        for key, value in sorted(by_status.items())
    ]
    write_csv(status_path, status_rows, ["survival_status", "term_count", "raw_values_emitted"])

    field_rows = [
        {
            "source_text_field": field,
            "survival_status": status,
            "term_count": int(count),
            "raw_values_emitted": False,
        }
        for (field, status), count in sorted(by_field_status.items())
    ]
    write_csv(field_path, field_rows, ["source_text_field", "survival_status", "term_count", "raw_values_emitted"])

    stratum_rows = [
        {
            "stratum": stratum,
            "survival_status": status,
            "term_count": int(count),
            "raw_values_emitted": False,
        }
        for (stratum, status), count in sorted(by_stratum_status.items())
    ]
    write_csv(stratum_path, stratum_rows, ["stratum", "survival_status", "term_count", "raw_values_emitted"])

    total = len(rows)
    total_distinct_keys = len(set(row["term_key"] for row in rows))
    survived_high = sum(count for status, count in by_status.items() if status.startswith("survived_high"))
    survived_high_keys = len(
        set(row["term_key"] for row in rows if row["survival_status"].startswith("survived_high"))
    )
    survived_symptom = by_status.get("survived_high_band_as_symptom", 0)
    survived_symptom_keys = len(
        set(row["term_key"] for row in rows if row["survival_status"] == "survived_high_band_as_symptom")
    )
    retargeted = by_status.get("survived_high_band_retargeted", 0)
    retargeted_keys = len(
        set(row["term_key"] for row in rows if row["survival_status"] == "survived_high_band_retargeted")
    )
    unresolved_rework = by_status.get("fell_to_f1_unresolved_rework", 0)
    unresolved_rework_keys = len(
        set(row["term_key"] for row in rows if row["survival_status"] == "fell_to_f1_unresolved_rework")
    )
    discarded = by_status.get("discarded_before_or_during_f1_v2", 0)
    discarded_keys = len(
        set(row["term_key"] for row in rows if row["survival_status"] == "discarded_before_or_during_f1_v2")
    )
    retained_not_high = by_status.get("retained_in_f1_v2_not_high_band", 0)
    retained_not_high_keys = len(
        set(row["term_key"] for row in rows if row["survival_status"] == "retained_in_f1_v2_not_high_band")
    )

    def sum_int(status: str, column: str) -> int:
        return int(
            sum(
                int(row[column] or 0)
                for row in rows
                if row["survival_status"] == status and str(row[column]).isdigit()
            )
        )

    source_rows_by_status = {
        status: sum_int(status, "seed_source_row_count")
        for status in sorted(by_status)
    }
    record_count_by_status = {
        status: sum_int(status, "seed_record_count")
        for status in sorted(by_status)
    }

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "task": "F5.1c",
        "question": "Whether the 289 Symptom lexical terms survived F1 high band or fell into discarded/rework outputs.",
        "source_seed_path": str(SEED_CONSOLIDATED),
        "f1_high_band_path": str(F1_HIGH),
        "expected_note": expected_note,
        "seed_symptom_terms": int(total),
        "historical_seed_rows": int(len(symptom_raw_seed)),
        "consolidated_seed_rows": int(total),
        "distinct_consolidated_term_keys": int(total_distinct_keys),
        "survived_high_band_total": int(survived_high),
        "survived_high_band_distinct_term_keys": int(survived_high_keys),
        "survived_high_band_as_symptom": int(survived_symptom),
        "survived_high_band_as_symptom_distinct_term_keys": int(survived_symptom_keys),
        "survived_high_band_retargeted": int(retargeted),
        "survived_high_band_retargeted_distinct_term_keys": int(retargeted_keys),
        "retained_in_f1_v2_not_high_band": int(retained_not_high),
        "retained_in_f1_v2_not_high_band_distinct_term_keys": int(retained_not_high_keys),
        "fell_to_f1_unresolved_rework": int(unresolved_rework),
        "fell_to_f1_unresolved_rework_distinct_term_keys": int(unresolved_rework_keys),
        "discarded_before_or_during_f1_v2": int(discarded),
        "discarded_before_or_during_f1_v2_distinct_term_keys": int(discarded_keys),
        "source_rows_by_status": source_rows_by_status,
        "record_count_by_status": record_count_by_status,
        "survived_high_band_pct": round((survived_high / total * 100), 2) if total else 0.0,
        "survived_high_band_distinct_key_pct": round((survived_high_keys / total_distinct_keys * 100), 2)
        if total_distinct_keys
        else 0.0,
        "survived_high_band_as_symptom_pct": round((survived_symptom / total * 100), 2) if total else 0.0,
        "survived_high_band_as_symptom_distinct_key_pct": round(
            (survived_symptom_keys / total_distinct_keys * 100), 2
        )
        if total_distinct_keys
        else 0.0,
        "high_band_targets": dict(sorted(high_targets.items())),
        "raw_values_emitted": False,
        "denominator_promotion": False,
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    memo = [
        "# F5.1c — Symptom Lexicon Survival Check",
        "",
        "## Objective",
        "",
        "Verify whether the 289 historical Symptom lexical terms from `reference-layer-v1` survived into the F1 high-confidence lexical band or fell into the F1 unresolved/discarded population.",
        "",
        "## Inputs",
        "",
        f"- Historical Symptom lexical rows: `{len(symptom_raw_seed)}`",
        f"- Consolidated Symptom rows consumed by F1: `{total}`",
        f"- Distinct consolidated term keys: `{total_distinct_keys}`",
        "- Source: `lexical_seed_dictionary_v1_consolidated_sanitized.csv`",
        "- Comparator: `lexical_layer_v2_high_confidence_candidates_sanitized.csv`",
        "- Raw terms emitted: `false`",
        "",
        "## Result",
        "",
        f"- Survived high band, any target: `{survived_high}` consolidated rows / `{survived_high_keys}` distinct keys",
        f"- Survived high band as Symptom: `{survived_symptom}` consolidated rows / `{survived_symptom_keys}` distinct keys",
        f"- Survived high band but retargeted: `{retargeted}` consolidated rows / `{retargeted_keys}` distinct keys",
        f"- Retained in F1 v2 but not high band: `{retained_not_high}` consolidated rows / `{retained_not_high_keys}` distinct keys",
        f"- Fell to unresolved/rework: `{unresolved_rework}` consolidated rows / `{unresolved_rework_keys}` distinct keys",
        f"- Discarded before or during F1 v2 routing: `{discarded}` consolidated rows / `{discarded_keys}` distinct keys",
        "",
        "## Source-Row Accounting",
        "",
        f"- Historical source rows represented by high-band survivors: `{source_rows_by_status.get('survived_high_band_as_symptom', 0)}`",
        f"- Historical source rows represented by unresolved/rework: `{source_rows_by_status.get('fell_to_f1_unresolved_rework', 0)}`",
        "",
        "## Interpretation",
        "",
        "The historical Symptom lexical pool does not provide an independent Symptom-ready layer unless terms survive as high-confidence Symptom anchors. Terms that survive only after retargeting may still support other targets, but they do not close the Symptom evidence thread.",
        "",
        "This check is diagnostic only. It does not promote any row into a contractual or proxy denominator.",
        "",
        "## Governance",
        "",
        "- Evidence type: `expert_inference`",
        "- Tier: `silver-medium` maximum",
        "- Evaluation independence: `derived_from_rules`",
        "- Raw operational values emitted: `false`",
    ]
    memo_path.write_text("\n".join(memo) + "\n", encoding="utf-8")

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
