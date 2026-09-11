from __future__ import annotations

import csv
import json
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve()
STINT2_ROOT = SCRIPT_PATH.parents[2]
REPO_ROOT = STINT2_ROOT.parent
STINT1_ROOT = REPO_ROOT / "stint-1-evidence-ground-truth"
SYMPTOM_OUTPUTS = STINT1_ROOT / "phase_5_symptom" / "outputs" / "f51_symptom_thread_resolution"
OUT_DIR = STINT2_ROOT / "g0_independent_evaluation" / "outputs" / "annotation_samples"

RELATIONAL_SOURCE = SYMPTOM_OUTPUTS / "t51b2x_reason_semantic_classification_normalized.csv"
OTHER_PATHS_SOURCE = SYMPTOM_OUTPUTS / "t51b24b_semantic_other_paths.csv"

EXPECTED_COUNTS = {
    "RELATIONAL_REASON": 1827,
    "PATH_A_CONCERN_TABLE": 68,
    "PATH_A_NOTES": 42,
    "B2_WORKBOOKS": 62,
}

SOURCE_BY_PATH = {
    "RELATIONAL_REASON": RELATIONAL_SOURCE,
    "PATH_A_CONCERN_TABLE": OTHER_PATHS_SOURCE,
    "PATH_A_NOTES": OTHER_PATHS_SOURCE,
    "B2_WORKBOOKS": OTHER_PATHS_SOURCE,
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def with_source_row_number(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    numbered: list[dict[str, str]] = []
    for idx, row in enumerate(rows, start=1):
        copied = dict(row)
        copied["_source_row_number"] = str(idx)
        numbered.append(copied)
    return numbered


def recover_units() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    recovered: list[dict[str, object]] = []
    reconciliation: list[dict[str, object]] = []

    relational_rows = with_source_row_number(read_csv(RELATIONAL_SOURCE))
    other_rows = with_source_row_number(read_csv(OTHER_PATHS_SOURCE))

    selected_by_path: dict[str, list[dict[str, str]]] = {
        "RELATIONAL_REASON": [
            row
            for row in relational_rows
            if row.get("predicted_class") == "observed_condition" and row.get("abstained") == "False"
        ],
        "PATH_A_CONCERN_TABLE": [
            row
            for row in other_rows
            if row.get("path_bucket") == "PATH_A_CONCERN_TABLE"
            and row.get("predicted_class") == "observed_condition"
            and row.get("abstained") == "False"
        ],
        "PATH_A_NOTES": [
            row
            for row in other_rows
            if row.get("path_bucket") == "PATH_A_NOTES"
            and row.get("predicted_class") == "observed_condition"
            and row.get("abstained") == "False"
        ],
        "B2_WORKBOOKS": [
            row
            for row in other_rows
            if row.get("path_bucket") == "B2_WORKBOOKS"
            and row.get("predicted_class") == "observed_condition"
            and row.get("abstained") == "False"
        ],
    }

    for path_bucket, rows in selected_by_path.items():
        source_path = SOURCE_BY_PATH[path_bucket]
        unit_field = "reason_hash" if path_bucket == "RELATIONAL_REASON" else "record_hash"
        unique_units = {row.get(unit_field, "") for row in rows if row.get(unit_field, "")}
        expected = EXPECTED_COUNTS[path_bucket]
        reconciliation.append(
            {
                "target": "Symptom",
                "path_bucket": path_bucket,
                "source_artifact": source_path.name,
                "selection_rule": "predicted_class=observed_condition;abstained=False",
                "unit_field": unit_field,
                "expected_f6_admitted_units": expected,
                "recovered_rows": len(rows),
                "recovered_unique_units": len(unique_units),
                "reconciles_to_f6": len(rows) == expected,
                "unique_units_equal_rows": len(unique_units) == len(rows),
                "raw_operational_values_emitted": False,
            }
        )
        for ordinal, row in enumerate(rows, start=1):
            sampling_unit_key = f"SYMPTOM-{path_bucket}-{ordinal:06d}"
            recovered.append(
                {
                    "target": "Symptom",
                    "path_bucket": path_bucket,
                    "sampling_unit_key": sampling_unit_key,
                    "source_row_number": row.get("_source_row_number", ""),
                    "source_unit_key": row.get(unit_field, ""),
                    "unit_key_type": unit_field,
                    "source_text_field": row.get("source_text_field", "reason"),
                    "predicted_class": row.get("predicted_class", ""),
                    "confidence": row.get("confidence", ""),
                    "anchor_prototype_hash": row.get("anchor_prototype_hash", ""),
                    "evidence_type": row.get("evidence_type", ""),
                    "tier": row.get("tier", ""),
                    "status": row.get("status", ""),
                    "label_generation_method": row.get("label_generation_method", ""),
                    "embedding_model": row.get("embedding_model", ""),
                    "evaluation_independence": row.get("evaluation_independence", ""),
                    "raw_operational_values_emitted": False,
                }
            )

    return recovered, reconciliation


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    recovered, reconciliation = recover_units()
    all_reconciled = all(row["reconciles_to_f6"] for row in reconciliation)

    write_csv(
        OUT_DIR / "g00b_symptom_row_level_units_sanitized.csv",
        recovered,
        [
            "target",
            "path_bucket",
            "sampling_unit_key",
            "source_row_number",
            "source_unit_key",
            "unit_key_type",
            "source_text_field",
            "predicted_class",
            "confidence",
            "anchor_prototype_hash",
            "evidence_type",
            "tier",
            "status",
            "label_generation_method",
            "embedding_model",
            "evaluation_independence",
            "raw_operational_values_emitted",
        ],
    )
    write_csv(
        OUT_DIR / "g00b_symptom_reconciliation_sanitized.csv",
        reconciliation,
        [
            "target",
            "path_bucket",
            "source_artifact",
            "selection_rule",
            "unit_field",
            "expected_f6_admitted_units",
            "recovered_rows",
            "recovered_unique_units",
            "reconciles_to_f6",
            "unique_units_equal_rows",
            "raw_operational_values_emitted",
        ],
    )

    summary = {
        "task": "G0.0b_recover_symptom_row_level_units",
        "source_artifacts": {
            "RELATIONAL_REASON": str(RELATIONAL_SOURCE.relative_to(REPO_ROOT)),
            "other_paths": str(OTHER_PATHS_SOURCE.relative_to(REPO_ROOT)),
        },
        "selection_rule": "predicted_class=observed_condition;abstained=False",
        "expected_f6_admitted_units": EXPECTED_COUNTS,
        "recovered_total_rows": len(recovered),
        "all_paths_reconcile_to_f6": all_reconciled,
        "raw_operational_values_emitted": False,
    }
    with (OUT_DIR / "g00b_symptom_recovery_summary_sanitized.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, sort_keys=True)

    memo = [
        "# G0.0b Symptom Row-Level Unit Recovery",
        "",
        "## Purpose",
        "",
        "Recover row-level unit keys for Symptom paths that F6 retained only as aggregate admitted counts.",
        "",
        "## Selection Rule",
        "",
        "`predicted_class = observed_condition` and `abstained = False`.",
        "",
        "## Reconciliation",
        "",
    ]
    for row in reconciliation:
        status = "reconciled" if row["reconciles_to_f6"] else "mismatch"
        memo.append(
            f"- `{row['path_bucket']}`: expected `{row['expected_f6_admitted_units']}`, "
            f"recovered `{row['recovered_rows']}` rows, `{row['recovered_unique_units']}` unique units: `{status}`."
        )
    memo.extend(
        [
            "",
            "## Sampling Key",
            "",
            "`sampling_unit_key` is unique per recovered row. Source hashes are retained as provenance, but `RELATIONAL_REASON` contains repeated `reason_hash` values and must not use that hash alone as the sampling key.",
            "",
            "## Decision Impact",
            "",
            "The Symptom aggregate-only blocker is recoverable for the four admitted paths. These row-level keys can support G0 protocol sampling, but they remain `derived_from_rules` labels until blind annotation creates independent labels.",
            "",
            "No raw operational values are emitted.",
        ]
    )
    (OUT_DIR / "g00b_symptom_recovery_memo.md").write_text("\n".join(memo) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
