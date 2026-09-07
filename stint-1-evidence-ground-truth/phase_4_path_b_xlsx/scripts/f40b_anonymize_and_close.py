"""Anonymize and close F4.0b characterization outputs.

This post-process replaces vendor-facing labels with CONTRACTOR_PATH_001,
adds an explicit relationship match-rate table, and records a redacted QA
check for the `reason` field without emitting raw operational values.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]
PHASE_DIR = PROJECT_ROOT / "stint-1-evidence-ground-truth" / "phase_4_path_b_xlsx"
PROMPT_DIR = PHASE_DIR / "prompts"
SCRIPT_DIR = PHASE_DIR / "scripts"
OLD_OUTPUT_DIR = PHASE_DIR / "outputs" / "f40b_contractor_path_001_relational_model"
NEW_OUTPUT_DIR = PHASE_DIR / "outputs" / "f40b_contractor_path_001_relational_model"
OLD_INTERNAL_DIR = PROJECT_ROOT / "reports" / "internal" / "f40b_contractor_path_001_relational_model"
NEW_INTERNAL_DIR = PROJECT_ROOT / "reports" / "internal" / "f40b_contractor_path_001_relational_model"

OLD_PROMPT = PROMPT_DIR / "Mini-Plan-F4.0b-CONTRACTOR_PATH_001_relat_model_Caract.md"
NEW_PROMPT = PROMPT_DIR / "Mini-Plan-F4.0b-CONTRACTOR_PATH_001_relational_model_characterization.md"
OLD_PREFLIGHT_SCRIPT = SCRIPT_DIR / "f40b_prepare_contractor_path_001_relational_inputs.py"
NEW_PREFLIGHT_SCRIPT = SCRIPT_DIR / "f40b_prepare_contractor_path_001_relational_inputs.py"

SENSITIVE_REPLACEMENTS = {
    "CONTRACTOR_PATH_001": "CONTRACTOR_PATH_001",
    "contractor_path_001": "contractor_path_001",
}

RELATIONSHIP_RE = re.compile(
    r"^\| `(?P<src_entity>[^`]+)` \| `(?P<src_field>[^`]+)` \| `(?P<tgt_entity>[^`]+)` "
    r"\| `(?P<tgt_field>[^`]+)` \| (?P<cardinality>[^|]+) \| (?P<match_rate>[^|]+) "
    r"\| (?P<source_non_null_count>[^|]+) \|$"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_hash(value: object, length: int = 16) -> str:
    raw = "" if value is None else str(value)
    return hashlib.sha256(raw.encode("utf-8", errors="ignore")).hexdigest()[:length]


def prefixed_hash(value: object, prefix: str, length: int = 12) -> str:
    return f"{prefix}-{stable_hash(value, length)}"


def replace_text(text: str) -> str:
    for source, target in SENSITIVE_REPLACEMENTS.items():
        text = text.replace(source, target)
    return text


def ensure_output_dir() -> None:
    NEW_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if OLD_OUTPUT_DIR.exists():
        for path in OLD_OUTPUT_DIR.iterdir():
            new_name = replace_text(path.name)
            target = NEW_OUTPUT_DIR / new_name
            if target.exists():
                continue
            path.rename(target)
        try:
            OLD_OUTPUT_DIR.rmdir()
        except OSError:
            pass


def ensure_internal_dir() -> None:
    NEW_INTERNAL_DIR.mkdir(parents=True, exist_ok=True)
    if OLD_INTERNAL_DIR.exists():
        for path in OLD_INTERNAL_DIR.iterdir():
            target = NEW_INTERNAL_DIR / replace_text(path.name)
            if target.exists():
                continue
            path.rename(target)
        try:
            OLD_INTERNAL_DIR.rmdir()
        except OSError:
            pass


def sanitize_file_contents(root: Path) -> None:
    for path in root.glob("**/*"):
        if not path.is_file() or path.suffix.lower() not in {".md", ".csv", ".json", ".py"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        sanitized = replace_text(text)
        if sanitized != text:
            path.write_text(sanitized, encoding="utf-8")


def rename_prompt_and_script() -> None:
    if OLD_PROMPT.exists() and not NEW_PROMPT.exists():
        OLD_PROMPT.rename(NEW_PROMPT)
    if OLD_PREFLIGHT_SCRIPT.exists() and not NEW_PREFLIGHT_SCRIPT.exists():
        OLD_PREFLIGHT_SCRIPT.rename(NEW_PREFLIGHT_SCRIPT)


def relationship_rates_from_key_graph() -> list[dict[str, object]]:
    key_graph = NEW_OUTPUT_DIR / "f40b_contractor_path_001_key_graph.md"
    rows: list[dict[str, object]] = []
    for line in key_graph.read_text(encoding="utf-8").splitlines():
        match = RELATIONSHIP_RE.match(line)
        if not match:
            continue
        item = match.groupdict()
        item["match_rate_pct"] = float(item.pop("match_rate").strip().rstrip("%"))
        item["estimated_cardinality"] = item.pop("cardinality").strip()
        item["source_non_null_count"] = int(item["source_non_null_count"].strip())
        item["raw_operational_values_emitted"] = False
        rows.append(item)
    return rows


def write_relationship_rates() -> None:
    rows = relationship_rates_from_key_graph()
    path = NEW_OUTPUT_DIR / "f40b_contractor_path_001_relationship_match_rates_sanitized.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "src_entity",
            "src_field",
            "tgt_entity",
            "tgt_field",
            "estimated_cardinality",
            "match_rate_pct",
            "source_non_null_count",
            "raw_operational_values_emitted",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def load_json_records(path: Path) -> list[dict[str, object]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ["data", "items", "value", "records", "results"]:
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        list_values = [value for value in payload.values() if isinstance(value, list)]
        if len(list_values) == 1:
            return [item for item in list_values[0] if isinstance(item, dict)]
    return []


def redacted_shape(value: str) -> str:
    tokens = re.findall(r"[A-Za-z]+|\d+|[^\w\s]", value)
    shaped = []
    for token in tokens[:12]:
        if token.isalpha():
            shaped.append("<alpha>")
        elif token.isdigit():
            shaped.append("<num>")
        else:
            shaped.append(token)
    return " ".join(shaped)


def contains_any(text: str, terms: set[str]) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in terms)


def write_reason_qa() -> dict[str, object]:
    manifest = pd.read_csv(NEW_INTERNAL_DIR / "f40b_contractor_path_001_entity_manifest_internal.csv")
    service_orders = manifest.loc[
        manifest["entity_label"].eq("api_service_v1_service-orders"),
        "json_path",
    ].iloc[0]
    records = load_json_records(Path(service_orders))
    total = len(records)
    non_empty = [str(record.get("reason", "")).strip() for record in records if str(record.get("reason", "")).strip()]
    cause_terms = {
        "cause",
        "caused",
        "because",
        "due",
        "failure",
        "fault",
        "damage",
        "broken",
        "leak",
    }
    motive_terms = {
        "maintenance",
        "inspection",
        "repair",
        "service",
        "visit",
        "work",
        "planned",
    }
    pii_terms = {"@", "phone", "email", "signature", "badge"}

    sample_values = non_empty[:3]
    sample_rows = []
    for idx, value in enumerate(sample_values, start=1):
        sample_rows.append(
            {
                "sample_id": f"REASON-QA-{idx:03d}",
                "reason_value_hash": prefixed_hash(value.lower(), "REASON", 12),
                "word_count": len(re.findall(r"[A-Za-z0-9]+", value)),
                "redacted_example_shape": redacted_shape(value),
                "cause_cue_present": contains_any(value, cause_terms),
                "visit_or_work_motive_cue_present": contains_any(value, motive_terms),
                "pii_indicator_present": contains_any(value, pii_terms),
                "raw_operational_values_emitted": False,
            }
        )

    csv_path = NEW_OUTPUT_DIR / "f40b_contractor_path_001_reason_field_qa_sanitized.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "sample_id",
            "reason_value_hash",
            "word_count",
            "redacted_example_shape",
            "cause_cue_present",
            "visit_or_work_motive_cue_present",
            "pii_indicator_present",
            "raw_operational_values_emitted",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(sample_rows)

    md_path = NEW_OUTPUT_DIR / "f40b_contractor_path_001_reason_field_qa_sanitized.md"
    md_path.write_text(
        "\n".join(
            [
                "# F4.0b Reason Field QA",
                "",
                "`reason` is confirmed as a non-empty free-text field in the service-order entity, but it is not confirmed as a root-cause label.",
                "",
                f"- Records profiled: `{total}`",
                f"- Non-empty `reason` rows: `{len(non_empty)}`",
                f"- Redacted examples reviewed: `{len(sample_rows)}`",
                "- Verdict: `cause_semantics_unconfirmed`",
                "- Downstream handling: keep as candidate textual support for Cause; do not treat as deterministic Cause mapping.",
                "",
                "The redacted sample emits token shapes and cue flags only, not raw values.",
                "",
                "raw_operational_values_emitted: false",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return {
        "records_profiled": total,
        "non_empty_reason_rows": len(non_empty),
        "redacted_examples": len(sample_rows),
        "cause_semantics_confirmed": False,
    }


def update_boundary() -> None:
    path = NEW_OUTPUT_DIR / "f40b_contractor_path_001_deterministic_ml_boundary_sanitized.csv"
    df = pd.read_csv(path)
    mask = df["target"].eq("Cause")
    df.loc[mask, "resolvable_by_join_or_rule"] = "no_deterministic_rule_confirmed"
    df.loc[mask, "requires_ml"] = "yes_or_manual_review"
    df.loc[mask, "rationale_sanitized"] = (
        "`reason` exists as free text, but its root-cause semantics are unconfirmed; "
        "it may encode visit/work motive rather than failure cause."
    )
    df.to_csv(path, index=False)


def update_memo(reason_summary: dict[str, object]) -> None:
    memo = NEW_OUTPUT_DIR / "f40b_contractor_path_001_relational_model_memo.md"
    text = memo.read_text(encoding="utf-8")
    text = text.replace(
        "| Cause | partial_yes | yes | A reason field exists, but it is free text rather than a closed deterministic cause catalog. |",
        "| Cause | no_deterministic_rule_confirmed | yes_or_manual_review | `reason` exists as free text, but root-cause semantics are unconfirmed; it may encode visit/work motive rather than failure cause. |",
    )
    insertion = (
        "\n## Reason Field QA\n\n"
        f"`reason` is non-empty in `{reason_summary['non_empty_reason_rows']}` of "
        f"`{reason_summary['records_profiled']}` profiled records, but three redacted shapes do not establish it as a root-cause label. "
        "It remains candidate textual support for Cause, not deterministic Cause evidence.\n"
    )
    if "## Reason Field QA" not in text:
        text = text.replace("\n## Symptom Verdict\n", insertion + "\n## Symptom Verdict\n")
    memo.write_text(text, encoding="utf-8")


def update_summary(reason_summary: dict[str, object]) -> None:
    path = NEW_OUTPUT_DIR / "f40b_contractor_path_001_relational_model_summary_sanitized.json"
    summary = json.loads(path.read_text(encoding="utf-8"))
    summary["created_at_utc"] = utc_now()
    summary["subject_label"] = "CONTRACTOR_PATH_001"
    summary["reason_field_cause_semantics_confirmed"] = False
    summary["reason_field_qa"] = reason_summary
    outputs = list(summary.get("outputs", []))
    for output in [
        "f40b_contractor_path_001_relationship_match_rates_sanitized.csv",
        "f40b_contractor_path_001_reason_field_qa_sanitized.csv",
        "f40b_contractor_path_001_reason_field_qa_sanitized.md",
    ]:
        if output not in outputs:
            outputs.append(output)
    summary["outputs"] = outputs
    path.write_text(json.dumps(summary, indent=2), encoding="utf-8")


def main() -> None:
    ensure_output_dir()
    ensure_internal_dir()
    rename_prompt_and_script()
    sanitize_file_contents(NEW_OUTPUT_DIR)
    sanitize_file_contents(PROMPT_DIR)
    sanitize_file_contents(SCRIPT_DIR)
    write_relationship_rates()
    reason_summary = write_reason_qa()
    update_boundary()
    update_memo(reason_summary)
    update_summary(reason_summary)
    print(
        json.dumps(
            {
                "output_dir": str(NEW_OUTPUT_DIR),
                "reason_qa": reason_summary,
                "relationship_rates_rows": len(relationship_rates_from_key_graph()),
                "raw_operational_values_emitted": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
