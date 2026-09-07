from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path("/home/adien-i7-remote/workspace/fsa_bridge_ml_feasibility")
B22_DIR = PROJECT_ROOT / "stint-1-evidence-ground-truth/phase_4_path_b_xlsx/outputs/b2_snapshot_dedup"


def main() -> None:
    summary = json.loads((B22_DIR / "b22_snapshot_dedup_summary_sanitized.json").read_text(encoding="utf-8"))
    by_doc = pd.read_csv(B22_DIR / "b22_snapshot_dedup_by_doc_type_sanitized.csv")
    by_bucket = pd.read_csv(B22_DIR / "b22_snapshot_dedup_by_bucket_sanitized.csv")

    reconciliation = {
        "pass_id": "B2.2b",
        "task_type": "snapshot_dedup_method_reconciliation",
        "source_pass": "B2.2",
        "snapshot_rows": int(summary["snapshot_rows"]),
        "estimated_events_without_date": int(summary["estimated_events"]),
        "estimated_events_with_snapshot_date": int(summary["estimated_events_with_snapshot_date"]),
        "without_date_key_definition": "family + doc_type + asset_key + code_key + text_signature",
        "with_date_key_definition": "family + doc_type + asset_key + code_key + text_signature + snapshot_date_bucket",
        "recommended_b2_denominator_key": "estimated_event_key_with_snapshot_date",
        "recommended_b2_denominator_rows": int(summary["estimated_events_with_snapshot_date"]),
        "persistence_cluster_key": "estimated_event_key",
        "persistence_cluster_rows": int(summary["estimated_events"]),
        "rationale": "The non-date key can merge repeated conditions across different snapshot dates. Until B2 duration/incidence semantics are validated, the date-sensitive key is the conservative unit for B2.3.",
        "daily_or_eod_status": "small_ambiguous_bucket_low_compression_characterize_separately",
        "symptom_branch_status": "third_family_without_confirmed_initial_problem_report_field",
        "raw_operational_values_emitted": False,
    }

    (B22_DIR / "b22b_dedup_method_reconciliation_summary_sanitized.json").write_text(
        json.dumps(reconciliation, indent=2),
        encoding="utf-8",
    )

    rows = [
        f"| {row.doc_type} | {int(row.snapshot_rows)} | {int(row.estimated_events)} | {row.compression_ratio} | {int(row.estimated_events_with_snapshot_date)} | {row.date_sensitive_compression_ratio} |"
        for row in by_doc.itertuples(index=False)
    ]
    bucket_rows = [
        f"| {row.family} | {row.doc_type} | {int(row.snapshot_rows)} | {int(row.estimated_events)} | {row.compression_ratio} | {int(row.estimated_events_with_snapshot_date)} | {row.date_sensitive_compression_ratio} |"
        for row in by_bucket.itertuples(index=False)
    ]

    memo = "\n".join(
        [
            "# B2.2b Dedup Method Reconciliation",
            "",
            "## Question",
            "",
            "B2.2 produced two event counts from the same snapshot universe. This note defines both counts and declares which one B2.3 may use.",
            "",
            "## Definitions",
            "",
            "- `snapshot_rows`: extracted rows from validated workbook text structures.",
            "- `estimated_event_key`: `family + doc_type + asset_key + code_key + text_signature`; it intentionally excludes date and therefore measures persistence clusters.",
            "- `estimated_event_key_with_snapshot_date`: same key plus `snapshot_date_bucket`; it prevents merging similar rows that occur on different snapshot dates.",
            "",
            "## Counts",
            "",
            f"- `snapshot_rows`: `{reconciliation['snapshot_rows']}`",
            f"- `estimated_events_without_date`: `{reconciliation['estimated_events_without_date']}`",
            f"- `estimated_events_with_snapshot_date`: `{reconciliation['estimated_events_with_snapshot_date']}`",
            "",
            "## By Document Type",
            "",
            "| doc_type | snapshot_rows | events_without_date | compression_without_date | events_with_date | compression_with_date |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
            *rows,
            "",
            "## By Bucket",
            "",
            "| family | doc_type | snapshot_rows | events_without_date | compression_without_date | events_with_date | compression_with_date |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
            *bucket_rows,
            "",
            "## Decision",
            "",
            "`estimated_event_key` is retained as a persistence-cluster metric, not as the B2 denominator. It is useful to show repeated snapshot state, but it can merge separate events from different days.",
            "",
            "B2.3 must use `estimated_event_key_with_snapshot_date` as the conservative event unit until duration or incident-start semantics are validated for B2 workbooks.",
            "",
            "`daily_or_eod` remains a small ambiguous bucket. Its low compression suggests more event-like behavior, but it must be characterized separately before promotion.",
            "",
            "B2.4 status: EOD/POD/snapshot buckets show prose-like structures but no confirmed initial problem report field. This is the third family without confirmed Symptom source.",
            "",
            "raw_operational_values_emitted: false",
            "",
        ]
    )
    (B22_DIR / "b22b_dedup_method_reconciliation_memo.md").write_text(memo, encoding="utf-8")
    print(json.dumps(reconciliation, indent=2))


if __name__ == "__main__":
    main()
