from __future__ import annotations

import csv
import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path("/home/adien-i7-remote/workspace/fsa_bridge_ml_feasibility")
STINT2_ROOT = PROJECT_ROOT / "stint-2-target-ml-prototyping"
G0_ROOT = STINT2_ROOT / "g0_independent_evaluation"
MANIFEST = G0_ROOT / "outputs" / "annotation_samples" / "g02_annotation_sample_manifest_sanitized.csv"
RESPONSES = G0_ROOT / "internal" / "g02_annotation_responses"
G03_OUT = G0_ROOT / "outputs" / "inter_annotator_agreement"
OUT = STINT2_ROOT / "artifacts" / "evaluation_sets" / "evaluation_set_v1"

ADMITTED_TARGETS = {
    "Cause": {"kappa": "0.743", "admission_status": "ADMIT"},
    "Object Part": {
        "kappa": "0.716",
        "admission_status": "ADMIT",
        "note": "annotator asymmetry declared; responses remain separate",
    },
    "Symptom": {"kappa": "0.613", "admission_status": "ADMIT"},
}

HELD_TARGETS = {
    "Damage": {
        "kappa": "0.196",
        "admission_status": "HOLD",
        "reason": "boundary definitions insufficient; awaiting g01-v2 full re-annotation",
    },
    "Activity": {
        "kappa": "-0.018",
        "admission_status": "HOLD",
        "reason": "prevalence-dominated; question mis-specified; awaiting separate MNGRP-level round",
    },
}

ANNOTATORS = {
    "chapter_team_annotator_01": {
        "file_label": "annotator_01",
        "folder": "annotator_1",
        "model_id": "claude-opus-5",
        "effort": "medium",
        "response_column": "annotator_response",
    },
    "chapter_team_annotator_02": {
        "file_label": "annotator_02",
        "folder": "annotator_2",
        "model_id": "gemini-3.6-flash",
        "effort": "medium",
        "response_column": "response",
    },
}

TARGET_SLUGS = {
    "Activity": "activity",
    "Cause": "cause",
    "Damage": "damage",
    "Object Part": "object_part",
    "Symptom": "symptom",
}

EXCLUDED_MECHANISMS = "rule_set_v1;semantic_prototype_matching_v1;paraphrase-multilingual-MiniLM-L12-v2"
PROTOCOL_VERSION = "g01-v1"
LABEL_GENERATION_METHOD = "blind_llm_annotation"
EVALUATION_INDEPENDENCE = "independent"
ANNOTATION_DATE = "2026-09-10"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def response_file(annotator_id: str, target: str) -> Path:
    meta = ANNOTATORS[annotator_id]
    slug = TARGET_SLUGS[target]
    return RESPONSES / meta["folder"] / f"g02_response_template_{annotator_id}_{slug}.csv"


def load_responses() -> dict[str, dict[str, str]]:
    by_annotator: dict[str, dict[str, str]] = {}
    for annotator_id, meta in ANNOTATORS.items():
        by_annotator[annotator_id] = {}
        for target in TARGET_SLUGS:
            path = response_file(annotator_id, target)
            if not path.exists():
                raise FileNotFoundError(path)
            for row in read_csv(path):
                annotation_id = row.get("annotation_id", "").strip()
                response = (row.get(meta["response_column"]) or row.get("annotator_response") or row.get("response") or "").strip()
                if not annotation_id or not response:
                    raise RuntimeError(f"Missing annotation_id or response in {path}")
                by_annotator[annotator_id][annotation_id] = response
    return by_annotator


def parse_assigned_annotators(value: str) -> list[str]:
    return [item.strip() for item in value.split(";") if item.strip()]


def admitted_record(manifest_row: dict[str, str], annotator_id: str, response: str) -> dict[str, object]:
    meta = ANNOTATORS[annotator_id]
    return {
        "sampling_unit_key": manifest_row["sampling_unit_key"],
        "source_unit_key": manifest_row["source_unit_key"],
        "target": manifest_row["target"],
        "path": manifest_row["path_bucket"],
        "response": response,
        "annotator_id": meta["model_id"],
        "annotator_effort": meta["effort"],
        "evaluation_independence": EVALUATION_INDEPENDENCE,
        "label_generation_method": LABEL_GENERATION_METHOD,
        "protocol_version": PROTOCOL_VERSION,
        "excluded_mechanisms": EXCLUDED_MECHANISMS,
        "annotation_date": ANNOTATION_DATE,
        "overlap_record": str(manifest_row["overlap_group"] == "overlap").lower(),
    }


def write_limitations() -> None:
    text = """# Evaluation Set v1 Limitations

This registration freezes the usable G0.3 result for evaluation only. It is never a training source.

- Annotators are LLMs, not human SMEs. They judge information type, not domain correctness of SAP code assignment.
- No temperature control was available in either interface. Exact reproducibility is not guaranteed.
- B2 overlap is thin, between 7 and 41 records depending on target. Agreement in that branch carries wide confidence intervals.
- 141 admitted units had no recoverable text and are absent from the sample.
- Object Part carries annotator asymmetry. Annotator 02 applies a more restrictive criterion; v1 keeps annotator files separate and does not resolve the difference.
- Damage is not admitted to v1 because boundary definitions were insufficient, especially around damage vs symptom vs action.
- Activity is not admitted to v1 because the sample is prevalence-dominated and the question is mis-specified for useful discrimination.
- Versioned artefacts contain hashes, counts, responses, and metadata only. Raw text, site names, asset identifiers, and PII remain internal.
"""
    (OUT / "evaluation_set_v1_limitations.md").write_text(text, encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    manifest = read_csv(MANIFEST)
    manifest_by_id = {row["annotation_id"]: row for row in manifest}
    responses = load_responses()

    fields = [
        "sampling_unit_key",
        "source_unit_key",
        "target",
        "path",
        "response",
        "annotator_id",
        "annotator_effort",
        "evaluation_independence",
        "label_generation_method",
        "protocol_version",
        "excluded_mechanisms",
        "annotation_date",
        "overlap_record",
    ]

    written_rows_by_annotator: dict[str, list[dict[str, object]]] = defaultdict(list)
    overlap_rows: list[dict[str, object]] = []
    exclusion_keys: dict[str, dict[str, str]] = {}

    for annotation_id, row in sorted(manifest_by_id.items()):
        target = row["target"]
        if target not in ADMITTED_TARGETS:
            continue
        assigned = parse_assigned_annotators(row["assigned_annotators"])
        for annotator_id in assigned:
            response = responses[annotator_id].get(annotation_id)
            if response is None:
                raise RuntimeError(f"Missing response for {annotator_id} {annotation_id}")
            written_rows_by_annotator[annotator_id].append(admitted_record(row, annotator_id, response))

        exclusion_keys[row["sampling_unit_key"]] = {
            "sampling_unit_key": row["sampling_unit_key"],
            "source_unit_key": row["source_unit_key"],
            "target": target,
            "path": row["path_bucket"],
        }

        if row["overlap_group"] == "overlap":
            left = responses["chapter_team_annotator_01"][annotation_id]
            right = responses["chapter_team_annotator_02"][annotation_id]
            overlap_rows.append(
                {
                    "sampling_unit_key": row["sampling_unit_key"],
                    "source_unit_key": row["source_unit_key"],
                    "target": target,
                    "path": row["path_bucket"],
                    "annotator_01_response": left,
                    "annotator_02_response": right,
                    "agreement": str(left == right).lower(),
                    "evaluation_independence": EVALUATION_INDEPENDENCE,
                    "label_generation_method": LABEL_GENERATION_METHOD,
                    "protocol_version": PROTOCOL_VERSION,
                    "excluded_mechanisms": EXCLUDED_MECHANISMS,
                    "annotation_date": ANNOTATION_DATE,
                }
            )

    expected_unique = 300 * len(ADMITTED_TARGETS)
    if len(exclusion_keys) != expected_unique:
        raise AssertionError(f"Expected {expected_unique} unique evaluation units, got {len(exclusion_keys)}")

    for annotator_id, rows in written_rows_by_annotator.items():
        write_csv(OUT / f"evaluation_set_v1_{ANNOTATORS[annotator_id]['file_label']}.csv", rows, fields)

    write_csv(
        OUT / "evaluation_set_v1_overlap_agreement.csv",
        overlap_rows,
        [
            "sampling_unit_key",
            "source_unit_key",
            "target",
            "path",
            "annotator_01_response",
            "annotator_02_response",
            "agreement",
            "evaluation_independence",
            "label_generation_method",
            "protocol_version",
            "excluded_mechanisms",
            "annotation_date",
        ],
    )

    admission_rows = []
    for target, data in {**ADMITTED_TARGETS, **HELD_TARGETS}.items():
        admission_rows.append(
            {
                "target": target,
                "admission_status": data["admission_status"],
                "cohen_kappa": data["kappa"],
                "reason_or_note": data.get("reason") or data.get("note", ""),
            }
        )
    write_csv(
        OUT / "evaluation_set_v1_target_admission_register.csv",
        admission_rows,
        ["target", "admission_status", "cohen_kappa", "reason_or_note"],
    )

    exclusion_rows = list(sorted(exclusion_keys.values(), key=lambda row: (row["target"], row["path"], row["sampling_unit_key"])))
    write_csv(
        OUT / "evaluation_set_v1_training_exclusion_keys.csv",
        exclusion_rows,
        ["sampling_unit_key", "source_unit_key", "target", "path"],
    )

    counts = Counter((row["target"], row["path"]) for row in exclusion_rows)
    count_rows = [
        {"target": target, "path": path, "excluded_units": count}
        for (target, path), count in sorted(counts.items())
    ]
    write_csv(
        OUT / "evaluation_set_v1_training_exclusion_counts.csv",
        count_rows,
        ["target", "path", "excluded_units"],
    )

    write_limitations()

    forbidden_columns = {
        "text",
        "text_pii_redacted",
        "raw_text",
        "site_name",
        "asset_id",
        "turbine",
        "description",
    }
    csv_files = sorted(OUT.glob("*.csv"))
    sanitization_failures = []
    for path in csv_files:
        with path.open(newline="", encoding="utf-8") as handle:
            headers = csv.DictReader(handle).fieldnames or []
        for header in headers:
            lowered = header.lower()
            if lowered in forbidden_columns or "text" in lowered or "pii" in lowered:
                sanitization_failures.append({"file": path.name, "column": header})
    if sanitization_failures:
        raise AssertionError(f"Sanitization failures: {sanitization_failures}")

    summary = {
        "task": "G0.4_evaluation_set_v1_registration",
        "created_at_utc": utc_now(),
        "registration_status": "frozen",
        "admitted_targets": sorted(ADMITTED_TARGETS),
        "held_targets": sorted(HELD_TARGETS),
        "unique_training_exclusion_units": len(exclusion_keys),
        "annotator_01_rows": len(written_rows_by_annotator["chapter_team_annotator_01"]),
        "annotator_02_rows": len(written_rows_by_annotator["chapter_team_annotator_02"]),
        "overlap_agreement_rows": len(overlap_rows),
        "label_generation_method": LABEL_GENERATION_METHOD,
        "protocol_version": PROTOCOL_VERSION,
        "sanitization_check": "PASS",
        "raw_text_in_versioned_outputs": False,
        "supersession_rule": "Superseded only by explicit v2 registration.",
    }
    write_json(OUT / "evaluation_set_v1_registration_summary.json", summary)


if __name__ == "__main__":
    main()
