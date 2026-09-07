"""B1.3 reason semantics verdict for CONTRACTOR_PATH_001.

This pass evaluates whether `reason` behaves like root cause, dispatch motive,
or pre-execution symptom support. It emits sanitized distributions only and
does not produce target labels, mappings, or candidate evidence rows.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]
PHASE_DIR = PROJECT_ROOT / "stint-1-evidence-ground-truth" / "phase_4_path_b_xlsx"
OUTPUT_DIR = PHASE_DIR / "outputs" / "reason_semantics_verdict"
INTERNAL_MANIFEST = (
    PROJECT_ROOT
    / "reports"
    / "internal"
    / "f40b_contractor_path_001_relational_model"
    / "f40b_contractor_path_001_entity_manifest_internal.csv"
)

CONTRACTOR_PATH = "CONTRACTOR_PATH_001"
ENTITY = "api_service_v1_service-orders"

CAUSE_CUES = {
    "cause",
    "caused",
    "because",
    "due",
    "failure",
    "failed",
    "fault",
    "damage",
    "broken",
    "leak",
    "trip",
    "alarm",
}
MOTIVE_OR_WORK_CUES = {
    "maintenance",
    "inspection",
    "repair",
    "service",
    "visit",
    "work",
    "planned",
    "schedule",
    "corrective",
}
SYMPTOM_LIKE_CUES = {
    "noise",
    "vibration",
    "overheat",
    "temperature",
    "reduced",
    "low",
    "high",
    "warning",
    "stoppage",
    "overspeed",
}
GENERIC_PLACEHOLDER_CUES = {
    "other",
    "unknown",
    "na",
    "n/a",
    "none",
    "not",
}
PII_CUES = {
    "@",
    "email",
    "phone",
    "signature",
    "badge",
    "employee",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_hash(value: object, length: int = 16) -> str:
    raw = "" if value is None or pd.isna(value) else str(value)
    return hashlib.sha256(raw.encode("utf-8", errors="ignore")).hexdigest()[:length]


def prefixed_hash(value: object, prefix: str, length: int = 12) -> str:
    return f"{prefix}-{stable_hash(value, length)}"


def as_text(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def load_json_records(path: Path) -> list[dict[str, object]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, Mapping)]
    if isinstance(payload, Mapping):
        for key in ["data", "items", "value", "records", "results"]:
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, Mapping)]
        list_values = [value for value in payload.values() if isinstance(value, list)]
        if len(list_values) == 1:
            return [item for item in list_values[0] if isinstance(item, Mapping)]
    return []


def service_orders_path() -> Path:
    manifest = pd.read_csv(INTERNAL_MANIFEST)
    value = manifest.loc[manifest["entity_label"].eq(ENTITY), "json_path"].iloc[0]
    return Path(value)


def word_count(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9]+", text))


def cue_present(text: str, cues: set[str]) -> bool:
    lowered = text.lower()
    return any(cue in lowered for cue in cues)


def language_bucket(text: str) -> str:
    lowered = text.lower()
    english_hits = sum(cue in lowered for cue in ["the", "and", "for", "with", "repair", "maintenance"])
    spanish_hits = sum(cue in lowered for cue in ["para", "con", "por", "repar", "manten", "falla"])
    if english_hits and spanish_hits:
        return "mixed_or_ambiguous"
    if english_hits:
        return "english_like"
    if spanish_hits:
        return "spanish_like"
    return "undetermined"


def redacted_shape(text: str) -> str:
    tokens = re.findall(r"[A-Za-z]+|\d+|[^\w\s]", text)
    shaped = []
    for token in tokens[:12]:
        if token.isalpha():
            shaped.append("<alpha>")
        elif token.isdigit():
            shaped.append("<num>")
        else:
            shaped.append(token)
    return " ".join(shaped)


def choose_redacted_samples(records: list[dict[str, object]]) -> list[dict[str, object]]:
    buckets = [
        ("cause_cue", lambda text: cue_present(text, CAUSE_CUES)),
        ("motive_or_work_cue", lambda text: cue_present(text, MOTIVE_OR_WORK_CUES)),
        ("symptom_like_cue", lambda text: cue_present(text, SYMPTOM_LIKE_CUES)),
    ]
    chosen: list[dict[str, object]] = []
    seen_hashes: set[str] = set()
    for bucket, predicate in buckets:
        for record in records:
            reason = as_text(record.get("reason"))
            if not reason or not predicate(reason):
                continue
            h = prefixed_hash(reason.lower(), "REASON", 12)
            if h in seen_hashes:
                continue
            seen_hashes.add(h)
            chosen.append(
                {
                    "sample_id": f"REASON-B1-3-{len(chosen)+1:03d}",
                    "selection_bucket": bucket,
                    "reason_value_hash": h,
                    "word_count": word_count(reason),
                    "redacted_example_shape": redacted_shape(reason),
                    "cause_cue_present": cue_present(reason, CAUSE_CUES),
                    "motive_or_work_cue_present": cue_present(reason, MOTIVE_OR_WORK_CUES),
                    "symptom_like_cue_present": cue_present(reason, SYMPTOM_LIKE_CUES),
                    "language_bucket": language_bucket(reason),
                    "raw_operational_values_emitted": False,
                }
            )
            break
    return chosen[:3]


def build_memo(summary: dict[str, object]) -> str:
    return "\n".join(
        [
            "# B1.3 Reason Semantics Verdict",
            "",
            "## Scope",
            "",
            "`reason` is evaluated as a field-level semantic source in `CONTRACTOR_PATH_001`. This pass does not produce labels, candidates, mappings, or denominator rows.",
            "",
            "## Findings",
            "",
            f"- Records evaluated: `{summary['records_evaluated']}`",
            f"- Non-empty `reason` rows: `{summary['reason_non_empty_rows']}`",
            f"- Distinct `reason` value keys: `{summary['distinct_reason_keys']}`",
            f"- Most common single reason share: `{summary['top_reason_share_pct']:.2f}%`",
            f"- Median word count: `{summary['median_word_count']}`",
            f"- Cause-cue rows: `{summary['cue_counts']['cause_cue']}`",
            f"- Motive/work-cue rows: `{summary['cue_counts']['motive_or_work_cue']}`",
            f"- Symptom-like-cue rows: `{summary['cue_counts']['symptom_like_cue']}`",
            f"- Generic/placeholder-cue rows: `{summary['cue_counts']['generic_placeholder_cue']}`",
            "",
            "## Verdict",
            "",
            "**`reason` is not confirmed as a deterministic Cause field.** It is fully populated and semantically useful, but the field can encode reason-for-work, dispatch/work motive, symptom-like trigger, or other contextual rationale. It should be routed as textual support for `Cause` and possible pre-execution signal review, not as a direct target label.",
            "",
            "## Downstream Rule",
            "",
            "- Do not use `reason` as `validated_mapping` or deterministic Cause.",
            "- Use `reason` in B1.2 as source text with `evidence_type: expert_inference` unless manually/independently validated later.",
            "- Keep `source_text_field = reason` separate from `descriptionExtended` per DELTA-0003.",
            "- If used for Symptom exploration, declare it as `possible_pre_execution_context`, not confirmed Symptom.",
            "",
            "raw_operational_values_emitted: false",
            "",
        ]
    )


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    records = load_json_records(service_orders_path())
    reason_values = [as_text(record.get("reason")) for record in records]
    non_empty = [value for value in reason_values if value]
    word_counts = [word_count(value) for value in non_empty]
    reason_hashes = [prefixed_hash(value.lower(), "REASON", 12) for value in non_empty]
    reason_counter = Counter(reason_hashes)
    language_counter = Counter(language_bucket(value) for value in non_empty)
    activity_reason_pairs = {
        (
            prefixed_hash(as_text(record.get("activityType")).lower(), "MAT-SRC", 12),
            prefixed_hash(as_text(record.get("reason")).lower(), "REASON", 12),
        )
        for record in records
        if as_text(record.get("activityType")) and as_text(record.get("reason"))
    }

    cue_counts = {
        "cause_cue": sum(cue_present(value, CAUSE_CUES) for value in non_empty),
        "motive_or_work_cue": sum(cue_present(value, MOTIVE_OR_WORK_CUES) for value in non_empty),
        "symptom_like_cue": sum(cue_present(value, SYMPTOM_LIKE_CUES) for value in non_empty),
        "generic_placeholder_cue": sum(cue_present(value, GENERIC_PLACEHOLDER_CUES) for value in non_empty),
        "pii_indicator_cue": sum(cue_present(value, PII_CUES) for value in non_empty),
    }

    distribution_rows = []
    for bucket_name, counter in [
        ("language_bucket", language_counter),
        ("word_count", Counter(word_counts)),
    ]:
        for key, count in sorted(counter.items(), key=lambda item: (-item[1], str(item[0]))):
            distribution_rows.append(
                {
                    "metric": bucket_name,
                    "bucket": key,
                    "row_count": count,
                    "share_pct": round((count / len(non_empty) * 100), 4) if non_empty else 0,
                    "raw_operational_values_emitted": False,
                }
            )
    with (OUTPUT_DIR / "reason_field_distribution_sanitized.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["metric", "bucket", "row_count", "share_pct", "raw_operational_values_emitted"],
        )
        writer.writeheader()
        writer.writerows(distribution_rows)

    sample_rows = choose_redacted_samples(records)
    with (OUTPUT_DIR / "reason_field_redacted_sample_sanitized.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "sample_id",
                "selection_bucket",
                "reason_value_hash",
                "word_count",
                "redacted_example_shape",
                "cause_cue_present",
                "motive_or_work_cue_present",
                "symptom_like_cue_present",
                "language_bucket",
                "raw_operational_values_emitted",
            ],
        )
        writer.writeheader()
        writer.writerows(sample_rows)

    semantic_rows = [
        {
            "field": "reason",
            "candidate_target": "Cause",
            "verdict": "not_deterministic_cause",
            "routing_decision": "textual_support_only",
            "evidence_type_if_used_downstream": "expert_inference",
            "tier_if_used_downstream": "silver-medium",
            "label_generation_method_if_used": "semantic_or_rule_reconstruction_required",
            "evaluation_independence_if_used": "derived_from_rules_unless_blind_manual_label",
            "raw_operational_values_emitted": False,
        },
        {
            "field": "reason",
            "candidate_target": "Symptom",
            "verdict": "possible_pre_execution_context_unconfirmed",
            "routing_decision": "review_after_b2_symptom_check",
            "evidence_type_if_used_downstream": "expert_inference",
            "tier_if_used_downstream": "silver-medium",
            "label_generation_method_if_used": "semantic_or_manual_reconstruction_required",
            "evaluation_independence_if_used": "derived_from_rules_unless_blind_manual_label",
            "raw_operational_values_emitted": False,
        },
    ]
    with (OUTPUT_DIR / "reason_semantics_routing_sanitized.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(semantic_rows[0].keys()))
        writer.writeheader()
        writer.writerows(semantic_rows)

    median_word_count = int(pd.Series(word_counts).median()) if word_counts else 0
    summary = {
        "created_at_utc": utc_now(),
        "pass_id": "B1.3",
        "contractor_path": CONTRACTOR_PATH,
        "task_type": "reason_semantics_verdict",
        "records_evaluated": len(records),
        "reason_non_empty_rows": len(non_empty),
        "reason_non_empty_rate": round(len(non_empty) / len(records), 6) if records else 0,
        "distinct_reason_keys": len(reason_counter),
        "top_reason_share_pct": round(max(reason_counter.values()) / len(non_empty) * 100, 4) if non_empty else 0,
        "median_word_count": median_word_count,
        "activity_type_reason_pair_keys": len(activity_reason_pairs),
        "cue_counts": cue_counts,
        "language_distribution": dict(language_counter),
        "verdict": "reason_not_confirmed_as_deterministic_cause",
        "downstream_status": "textual_support_only_pending_semantic_or_manual_validation",
        "contractual_denominator_supported": False,
        "poc_proxy_denominator_supported_now": False,
        "raw_operational_values_emitted": False,
        "outputs": [
            "reason_semantics_verdict.md",
            "reason_field_distribution_sanitized.csv",
            "reason_field_redacted_sample_sanitized.csv",
            "reason_semantics_routing_sanitized.csv",
            "reason_semantics_verdict_summary_sanitized.json",
        ],
    }
    (OUTPUT_DIR / "reason_semantics_verdict_summary_sanitized.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    (OUTPUT_DIR / "reason_semantics_verdict.md").write_text(build_memo(summary), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
