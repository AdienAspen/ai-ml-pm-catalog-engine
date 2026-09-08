from __future__ import annotations

import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path("/home/adien-i7-remote/workspace/fsa_bridge_ml_feasibility")
OUTPUT_DIR = PROJECT_ROOT / "stint-1-evidence-ground-truth/phase_5_symptom/outputs/f51_symptom_thread_resolution"

RAW_PATTERNS = [
    re.compile(r"contractor_path_001", re.I),
    re.compile(r"site_path_001", re.I),
    re.compile(r"site_path_002", re.I),
    re.compile(r"site_path_003", re.I),
    re.compile(r"site_path_004", re.I),
    re.compile(r"client_entity", re.I),
    re.compile(r"oem_entity_001", re.I),
    re.compile(r"\bge\b", re.I),
    re.compile(r"/home/adien", re.I),
    re.compile(r"data/interim/extracted_source", re.I),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(name: str) -> dict[str, Any]:
    return json.loads((OUTPUT_DIR / name).read_text(encoding="utf-8"))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def assert_sanitized(paths: list[Path]) -> None:
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="ignore")
        hits = [pattern.pattern for pattern in RAW_PATTERNS if pattern.search(text)]
        if hits:
            raise RuntimeError(f"Sanitization failed for {path.name}: {hits}")


def path_verdict(observed_rows: int, denominator: int) -> str:
    pct = (observed_rows / denominator * 100) if denominator else 0
    if observed_rows == 0:
        return "no_signal_observed"
    if pct < 1:
        return "marginal_signal"
    return "candidate_signal_present"


def main() -> None:
    f51a = load_json("f51a_b2_symptom_concepts_summary_sanitized.json")
    reason = load_json("t51b2x_reason_semantic_classification_normalized_summary_sanitized.json")
    oem = load_json("t51b23_oem_alarm_dictionary_summary_sanitized.json")
    poly = load_json("t51b23b_polysemy_profile_summary_sanitized.json")
    pattern = load_json("t51b24_other_path_oem_pattern_summary_sanitized.json")
    semantic = load_json("t51b24b_semantic_other_paths_summary_sanitized.json")

    path_rows = [
        {
            "path_bucket": "RELATIONAL_REASON",
            "text_rows_evaluated": reason["reason_non_empty_rows"],
            "oem_pattern_rows": oem["oem_occurrence_rows"],
            "semantic_observed_condition_rows": reason["observed_condition_candidate_rows"],
            "semantic_observed_condition_pct": round(reason["observed_condition_candidate_rows"] / reason["reason_non_empty_rows"] * 100, 2),
            "semantic_method": reason["label_generation_method"],
            "threshold": reason["threshold"],
            "threshold_source": "calibrated_on_model_blind_review_80_rows",
            "path_verdict": path_verdict(reason["observed_condition_candidate_rows"], reason["reason_non_empty_rows"]),
            "denominator_promotion": "not_promoted",
            "raw_operational_values_emitted": False,
        }
    ]
    for path_bucket, item in semantic["path_summary"].items():
        rows = item["text_rows_evaluated"]
        observed = item["semantic_observed_condition_rows"]
        path_rows.append(
            {
                "path_bucket": path_bucket,
                "text_rows_evaluated": rows,
                "oem_pattern_rows": item["oem_pattern_rows"],
                "semantic_observed_condition_rows": observed,
                "semantic_observed_condition_pct": round(observed / rows * 100, 2) if rows else 0,
                "semantic_method": "semantic_prototype_matching_v1_normalized_fixed_threshold_0_50",
                "threshold": semantic["threshold"],
                "threshold_source": "transferred_from_relational_reason_no_recalibration",
                "path_verdict": path_verdict(observed, rows),
                "denominator_promotion": "not_promoted",
                "raw_operational_values_emitted": False,
            }
        )

    method_rows = [
        {
            "method": "sap_mapping_symptom_thread",
            "source": "F5.1a",
            "finding": "discarded_generic_noise",
            "supporting_rows": f51a["symptom_evidence_rows"],
            "candidate_observed_condition_rows": f51a["observed_condition_like_concepts"],
            "denominator_promotion": "not_promoted",
            "raw_operational_values_emitted": False,
        },
        {
            "method": "semantic_normalized_reason",
            "source": "T5.1b2X-normalized",
            "finding": "candidate_signal_present_conservative",
            "supporting_rows": reason["reason_non_empty_rows"],
            "candidate_observed_condition_rows": reason["observed_condition_candidate_rows"],
            "denominator_promotion": "not_promoted",
            "raw_operational_values_emitted": False,
        },
        {
            "method": "oem_dictionary",
            "source": "T5.1b2.3/T5.1b2.3b",
            "finding": "strong_observed_alarm_dictionary_but_not_sap_mapping",
            "supporting_rows": oem["oem_occurrence_rows"],
            "candidate_observed_condition_rows": "",
            "denominator_promotion": "not_promoted",
            "raw_operational_values_emitted": False,
        },
        {
            "method": "other_path_oem_pattern",
            "source": "T5.1b2.4",
            "finding": pattern["answer"],
            "supporting_rows": "",
            "candidate_observed_condition_rows": "",
            "denominator_promotion": "not_promoted",
            "raw_operational_values_emitted": False,
        },
        {
            "method": "other_path_semantic_classifier",
            "source": "T5.1b2.4b",
            "finding": "candidate_signal_present_beyond_oem_pattern",
            "supporting_rows": sum(item["text_rows_evaluated"] for item in semantic["path_summary"].values()),
            "candidate_observed_condition_rows": sum(item["semantic_observed_condition_rows"] for item in semantic["path_summary"].values()),
            "denominator_promotion": "not_promoted",
            "raw_operational_values_emitted": False,
        },
    ]

    total_observed_candidate_rows = reason["observed_condition_candidate_rows"] + sum(
        item["semantic_observed_condition_rows"] for item in semantic["path_summary"].values()
    )
    summary = {
        "created_at_utc": utc_now(),
        "pass_id": "T5.1b2.5",
        "task_type": "symptom_final_verdict",
        "final_verdict": "symptom_signal_exists_as_proxy_candidate_but_is_not_ground_truth",
        "contractual_denominator_supported": False,
        "proxy_candidate_signal_supported": True,
        "proxy_candidate_observed_condition_rows_total_before_dedup": total_observed_candidate_rows,
        "reason_observed_condition_candidate_rows": reason["observed_condition_candidate_rows"],
        "other_paths_observed_condition_candidate_rows": {
            key: value["semantic_observed_condition_rows"] for key, value in semantic["path_summary"].items()
        },
        "oem_dictionary": {
            "oem_occurrence_rows": oem["oem_occurrence_rows"],
            "distinct_oem_codes": oem["distinct_oem_codes"],
            "distinct_code_normalised_description_pairs": oem["distinct_code_normalised_description_pairs"],
            "multi_description_codes": oem["codes_with_multiple_normalised_descriptions"],
            "likely_polysemous_codes": poly["polysemy_classification_counts"].get("likely_polysemous", 0),
        },
        "evidence_type": "expert_inference",
        "tier": "silver-medium",
        "label_generation_method": "semantic_prototype_matching_v2_normalised_telegram_text_and_oem_pattern_dictionary",
        "evaluation_independence": "derived_from_rules",
        "tier_ceiling_note": "tier ceiling: silver-medium for Symptom; must not be promoted above this level",
        "denominator_status": "nothing_promoted_to_contractual_or_proxy_denominator_in_this_pass",
        "raw_operational_values_emitted_to_versioned_artifacts": False,
    }

    path_summary_path = OUTPUT_DIR / "t51b25_symptom_final_path_verdict_sanitized.csv"
    method_summary_path = OUTPUT_DIR / "t51b25_symptom_final_method_summary_sanitized.csv"
    summary_path = OUTPUT_DIR / "t51b25_symptom_final_verdict_summary_sanitized.json"
    memo_path = OUTPUT_DIR / "t51b25_symptom_final_verdict_memo.md"

    write_csv(
        path_summary_path,
        path_rows,
        [
            "path_bucket",
            "text_rows_evaluated",
            "oem_pattern_rows",
            "semantic_observed_condition_rows",
            "semantic_observed_condition_pct",
            "semantic_method",
            "threshold",
            "threshold_source",
            "path_verdict",
            "denominator_promotion",
            "raw_operational_values_emitted",
        ],
    )
    write_csv(
        method_summary_path,
        method_rows,
        [
            "method",
            "source",
            "finding",
            "supporting_rows",
            "candidate_observed_condition_rows",
            "denominator_promotion",
            "raw_operational_values_emitted",
        ],
    )
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    memo_lines = [
        "# T5.1b2.5 - Final Symptom Verdict",
        "",
        "## Verdict",
        "",
        "`Symptom` is no longer a zero-signal target. The corpus contains observed-condition proxy candidates, mainly in the relational `reason` field and secondarily in Path A/B2 text. However, this is not ground truth and does not support a contractual denominator.",
        "",
        "## Path Verdicts",
        "",
        "| Path | Rows evaluated | OEM pattern rows | Semantic observed_condition | Verdict |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for row in path_rows:
        memo_lines.append(
            f"| `{row['path_bucket']}` | {row['text_rows_evaluated']} | {row['oem_pattern_rows']} | {row['semantic_observed_condition_rows']} ({row['semantic_observed_condition_pct']}%) | `{row['path_verdict']}` |"
        )
    memo_lines.extend(
        [
            "",
            "## OEM Dictionary Finding",
            "",
            f"The OEM dictionary contains `{oem['oem_occurrence_rows']}` observed occurrences, `{oem['distinct_oem_codes']}` distinct codes, and `{oem['distinct_code_normalised_description_pairs']}` code-description pairs. `{oem['codes_with_multiple_normalised_descriptions']}` codes have multiple normalized descriptions, including `{poly['polysemy_classification_counts'].get('likely_polysemous', 0)}` likely-polysemous codes. Therefore, downstream mapping must not assume `code -> description` is one-to-one.",
            "",
            "## Denominator Guardrail",
            "",
            "All Symptom signal in this memo remains `expert_inference`, maximum `silver-medium`, and `evaluation_independence = derived_from_rules`. It can seed a proxy candidate set for F6, but this pass promotes nothing to contractual or proxy denominator.",
            "",
            "## Practical Conclusion",
            "",
            "The strongest Symptom route is no longer a sentinel or placeholder. It is a conservative proxy route: normalized semantic classification over `reason`, supported by an observed OEM alarm dictionary and cross-checked against Path A/B2 text. The next decision belongs in F6: whether these candidates are admitted into a clearly labelled POC proxy denominator, never into the contractual denominator.",
        ]
    )
    memo_path.write_text("\n".join(memo_lines) + "\n", encoding="utf-8")

    assert_sanitized([path_summary_path, method_summary_path, summary_path, memo_path])
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
