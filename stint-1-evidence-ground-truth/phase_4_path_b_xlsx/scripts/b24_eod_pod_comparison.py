from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path("/home/adien-i7-remote/workspace/fsa_bridge_ml_feasibility")
B21_DIR = PROJECT_ROOT / "stint-1-evidence-ground-truth/phase_4_path_b_xlsx/outputs/b2_snapshot_characterization"
OUTPUT_DIR = PROJECT_ROOT / "stint-1-evidence-ground-truth/phase_4_path_b_xlsx/outputs/b2_eod_pod_comparison"


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    file_df = pd.read_csv(B21_DIR / "b21_snapshot_file_inventory_sanitized.csv")
    sheet_df = pd.read_csv(B21_DIR / "b21_snapshot_sheet_profile_sanitized.csv")
    text_df = pd.read_csv(B21_DIR / "b21_snapshot_text_field_candidates_sanitized.csv")
    return file_df, sheet_df, text_df


def summarize(file_df: pd.DataFrame, sheet_df: pd.DataFrame, text_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    group_cols = ["family", "doc_type"]
    file_summary = (
        file_df.groupby(group_cols, dropna=False)
        .agg(
            files=("file_key", "nunique"),
            template_variants=("template_variant", "nunique"),
            total_non_empty_rows=("non_empty_rows", "sum"),
            files_with_candidate_text=("rows_with_candidate_text", lambda s: int((s > 0).sum())),
            total_candidate_text_rows=("rows_with_candidate_text", "sum"),
        )
        .reset_index()
    )
    file_summary["candidate_text_file_rate"] = (
        file_summary["files_with_candidate_text"] / file_summary["files"]
    ).round(6)

    sheet_summary = (
        sheet_df.groupby(group_cols + ["candidate_text_categories"], dropna=False)
        .agg(
            sheets=("sheet_key", "nunique"),
            files=("file_key", "nunique"),
            rows_with_candidate_text=("rows_with_candidate_text", "sum"),
        )
        .reset_index()
        .sort_values(["rows_with_candidate_text", "sheets"], ascending=False)
    )

    # A conservative structural proxy: issue_text/notes_text may contain pre-execution
    # context, but B2.4 cannot promote Symptom without content validation.
    symptom_like = text_df[
        text_df["candidate_text_categories"].fillna("").str.contains("issue_text|notes_text", regex=True)
    ]
    symptom_proxy = (
        symptom_like.groupby(group_cols, dropna=False)
        .agg(
            files_with_issue_or_notes=("file_key", "nunique"),
            sheets_with_issue_or_notes=("sheet_key", "nunique"),
            issue_or_notes_rows=("rows_with_candidate_text", "sum"),
        )
        .reset_index()
    )

    merged = file_summary.merge(symptom_proxy, on=group_cols, how="left").fillna(0)
    for col in ["files_with_issue_or_notes", "sheets_with_issue_or_notes", "issue_or_notes_rows"]:
        merged[col] = merged[col].astype(int)

    doc_rollup = (
        merged.groupby("doc_type", dropna=False)
        .agg(
            files=("files", "sum"),
            template_variants=("template_variants", "sum"),
            files_with_candidate_text=("files_with_candidate_text", "sum"),
            total_candidate_text_rows=("total_candidate_text_rows", "sum"),
            files_with_issue_or_notes=("files_with_issue_or_notes", "sum"),
            issue_or_notes_rows=("issue_or_notes_rows", "sum"),
        )
        .reset_index()
    )
    doc_rollup["candidate_text_file_rate"] = (
        doc_rollup["files_with_candidate_text"] / doc_rollup["files"]
    ).round(6)
    doc_rollup["issue_or_notes_file_rate"] = (
        doc_rollup["files_with_issue_or_notes"] / doc_rollup["files"]
    ).round(6)

    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "pass_id": "B2.4",
        "task_type": "eod_pod_structural_comparison",
        "source_pass": "B2.1",
        "files_compared": int(file_df["file_key"].nunique()),
        "doc_types_compared": sorted(str(x) for x in file_df["doc_type"].dropna().unique()),
        "eod_files": int((file_df["doc_type"] == "EOD").sum()),
        "pod_files": int((file_df["doc_type"] == "POD").sum()),
        "unprefixed_snapshot_files": int((file_df["doc_type"] == "snapshot_unprefixed").sum()),
        "daily_or_eod_files": int((file_df["doc_type"] == "daily_or_eod").sum()),
        "known_positive_case_validation": "pending_not_provided_for_b2_xlsx",
        "symptom_availability_verdict": "structural_opportunity_only_content_validation_pending",
        "raw_operational_values_emitted": False,
        "outputs": [
            "b24_eod_pod_comparison_memo.md",
            "b24_eod_pod_doc_type_summary_sanitized.csv",
            "b24_eod_pod_family_doc_type_summary_sanitized.csv",
            "b24_text_category_summary_sanitized.csv",
            "b24_eod_pod_summary_sanitized.json",
        ],
    }
    return doc_rollup, sheet_summary, summary


def memo(summary: dict[str, Any], doc_rollup: pd.DataFrame) -> str:
    rows = [
        f"| {row.doc_type} | {int(row.files)} | {int(row.files_with_candidate_text)} | {row.candidate_text_file_rate:.4f} | {int(row.total_candidate_text_rows)} | {int(row.files_with_issue_or_notes)} | {row.issue_or_notes_file_rate:.4f} | {int(row.issue_or_notes_rows)} |"
        for row in doc_rollup.itertuples(index=False)
    ]
    return "\n".join(
        [
            "# B2.4 EOD vs POD Structural Comparison",
            "",
            "## Scope",
            "",
            "This pass compares snapshot workbook families after B2.1 characterization. It reports structure and candidate text density only; it does not inspect or emit raw operational text.",
            "",
            "## Summary",
            "",
            f"- Files compared: `{summary['files_compared']}`",
            f"- EOD files: `{summary['eod_files']}`",
            f"- POD files: `{summary['pod_files']}`",
            f"- Unprefixed snapshot files: `{summary['unprefixed_snapshot_files']}`",
            f"- Daily/EOD ambiguous files: `{summary['daily_or_eod_files']}`",
            f"- Known-positive validation: `{summary['known_positive_case_validation']}`",
            f"- Symptom availability verdict: `{summary['symptom_availability_verdict']}`",
            "",
            "## By Document Type",
            "",
            "| doc_type | files | files_with_candidate_text | candidate_text_file_rate | candidate_text_rows | files_with_issue_or_notes | issue_or_notes_file_rate | issue_or_notes_rows |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
            *rows,
            "",
            "## Interpretation",
            "",
            "B2.4 can identify where prose-like structures exist, but it cannot conclude that a source contains Symptom, Cause, Damage, or Activity evidence until a known-positive workbook case and content-level extraction are validated.",
            "",
            "If issue/notes structures are present in EOD/POD, they remain candidates for B2.3 extraction. If absent, that absence is not interpreted until the template variant has a validated positive/negative control.",
            "",
            "raw_operational_values_emitted: false",
            "",
        ]
    )


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    file_df, sheet_df, text_df = load_inputs()
    doc_rollup, sheet_summary, summary = summarize(file_df, sheet_df, text_df)
    family_summary = (
        file_df.groupby(["family", "doc_type"], dropna=False)
        .agg(
            files=("file_key", "nunique"),
            template_variants=("template_variant", "nunique"),
            files_with_candidate_text=("rows_with_candidate_text", lambda s: int((s > 0).sum())),
            total_candidate_text_rows=("rows_with_candidate_text", "sum"),
        )
        .reset_index()
    )
    family_summary["candidate_text_file_rate"] = (
        family_summary["files_with_candidate_text"] / family_summary["files"]
    ).round(6)

    doc_rollup.to_csv(OUTPUT_DIR / "b24_eod_pod_doc_type_summary_sanitized.csv", index=False)
    family_summary.to_csv(OUTPUT_DIR / "b24_eod_pod_family_doc_type_summary_sanitized.csv", index=False)
    sheet_summary.to_csv(OUTPUT_DIR / "b24_text_category_summary_sanitized.csv", index=False)
    (OUTPUT_DIR / "b24_eod_pod_summary_sanitized.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (OUTPUT_DIR / "b24_eod_pod_comparison_memo.md").write_text(memo(summary, doc_rollup), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
