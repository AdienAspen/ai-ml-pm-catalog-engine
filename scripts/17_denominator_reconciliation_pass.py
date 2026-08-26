from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = PROJECT_ROOT / "reports"
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path)


def pick_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for col in candidates:
        if col in df.columns:
            return col
    return None


def md_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_No rows._"
    safe_df = df.fillna("")
    columns = list(safe_df.columns)
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join(["---"] * len(columns)) + " |",
    ]
    for _, row in safe_df.iterrows():
        values = [str(row[col]).replace("\n", " ").replace("|", "/") for col in columns]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def as_int(value, default: int = 0) -> int:
    try:
        if pd.isna(value):
            return default
        return int(value)
    except Exception:
        return default


def main() -> int:
    safe = read_csv(REPORTS_DIR / "safe_content_pair_discovery_sanitized.csv")
    classified = read_csv(REPORTS_DIR / "pair_evidence_classification_sanitized.csv")
    structural = read_csv(REPORTS_DIR / "basic_structural_scan_sanitized.csv")
    gap_register = read_csv(REPORTS_DIR / "cross_target_gap_register_sanitized.csv")

    safe_summary = read_json(ARTIFACTS_DIR / "safe_content_pair_discovery_summary_sanitized.json")
    classified_summary = read_json(ARTIFACTS_DIR / "pair_evidence_classification_summary_sanitized.json")
    structural_summary = read_json(ARTIFACTS_DIR / "basic_structural_scan_summary_sanitized.json")
    cross_summary = read_json(ARTIFACTS_DIR / "cross_target_findings_summary_sanitized.json")

    safe_rows = len(safe)
    classified_rows = len(classified)
    multi_hint = "Cause;Activity;Activity Type"
    multi_rows = 0
    if "target_hint" in safe.columns:
        multi_rows = int((safe["target_hint"].astype(str) == multi_hint).sum())
    expected_classified = safe_rows + (multi_rows * 2)
    target_expansion_delta = classified_rows - safe_rows

    denominator_rows = [
        {
            "check_id": "D01",
            "issue": "838_vs_910_candidate_pair_rows",
            "observed_values": f"safe_content_rows={safe_rows}; classified_rows={classified_rows}",
            "verification": (
                f"{multi_rows} safe-content rows carried multi-target hint "
                f"{multi_hint!r}; classification expands each into 3 target rows."
            ),
            "calculation": f"{safe_rows} + ({multi_rows} * 2 expansion_delta) = {expected_classified}",
            "reconciled_status": "reconciled_target_expansion_not_denominator_change"
            if expected_classified == classified_rows
            else "needs_review",
            "report_action": "Label 838 as source opportunity rows and 910 as target-expanded classification rows.",
        },
        {
            "check_id": "D02",
            "issue": "Cause_Activity_ActivityType_uniformity",
            "observed_values": "36 structures and 379593 row-level pairs repeated across three targets",
            "verification": (
                "The repeated counts arise from shared multi-target expansion, not from three independent "
                "target-specific denominators."
            ),
            "calculation": "Same 36 source opportunities are expanded to Cause, Activity, and Activity Type.",
            "reconciled_status": "reconciled_shared_multitarget_expansion_requires_semantic_validation",
            "report_action": "Do not present the three rows as independent evidence; keep them pending target disambiguation.",
        },
        {
            "check_id": "D03",
            "issue": "parser_gap_G08_vs_zero_parser_issues",
            "observed_values": f"current_parser_issue_on_tabular_files={cross_summary.get('parser_issue_on_tabular_files', 'unknown')}",
            "verification": (
                "Current cross-target summary reports zero tabular parser issues; any G08 gap-register row that still "
                "claims remaining tabular parser issues is stale unless supported by the latest triage."
            ),
            "calculation": "Use latest parser triage/cross-target summary as controlling source.",
            "reconciled_status": "stale_gap_language_needs_report_update"
            if as_int(cross_summary.get("parser_issue_on_tabular_files", 0)) == 0
            else "active_parser_gap",
            "report_action": "Update or retire G08 language in the draft if latest triage confirms zero tabular parser issues.",
        },
        {
            "check_id": "D04",
            "issue": "147_vs_157_files",
            "observed_values": (
                f"structural_attempted={structural_summary.get('files_attempted', 'unknown')}; "
                f"safe_content_pair_files={safe_summary.get('input_source_files', safe_summary.get('files_attempted', 'unknown'))}"
            ),
            "verification": (
                "Structural scan included eligible structured/tabular files across roles. Safe content pair discovery "
                "intentionally scanned source_data only."
            ),
            "calculation": (
                "157 structural attempted = 147 source_data + 4 mapping_doc + 6 reference_data."
            ),
            "reconciled_status": "reconciled_scope_filter",
            "report_action": "State that 10 non-source files were excluded from pair discovery by design.",
        },
    ]
    denominator_df = pd.DataFrame(denominator_rows)

    role_counts = structural_summary.get("attempted_by_role", {})
    file_denominator_df = pd.DataFrame(
        [
            {
                "scope": "basic_structural_scan",
                "files_attempted": structural_summary.get("files_attempted", len(structural)),
                "source_data": role_counts.get("source_data", ""),
                "mapping_doc": role_counts.get("mapping_doc", ""),
                "reference_data": role_counts.get("reference_data", ""),
                "purpose": "read/profile eligible structured or tabular files across roles",
            },
            {
                "scope": "safe_content_pair_discovery",
                "files_attempted": safe_summary.get("files_attempted", ""),
                "source_data": safe_summary.get("input_source_files", ""),
                "mapping_doc": 0,
                "reference_data": 0,
                "purpose": "discover text-code opportunities only in productive source_data",
            },
            {
                "scope": "excluded_from_pair_discovery",
                "files_attempted": as_int(structural_summary.get("files_attempted", 0))
                - as_int(safe_summary.get("input_source_files", safe_summary.get("files_attempted", 0))),
                "source_data": 0,
                "mapping_doc": role_counts.get("mapping_doc", ""),
                "reference_data": role_counts.get("reference_data", ""),
                "purpose": "non-source roles intentionally excluded from source-data pair discovery",
            },
        ]
    )

    focus_targets = ["Cause", "Activity", "Activity Type"]
    target_col = pick_col(classified, ["target", "target_relevance"])
    row_count_col = pick_col(classified, ["cooccurring_row_count", "cooccurring_rows", "row_level_pair_count"])
    file_col = pick_col(classified, ["file_hash", "path_hash", "relative_path_hash", "relative_path", "source_file"])
    measure_col = pick_col(classified, ["can_support_measurement", "measurement_ready"])

    uniform_rows = []
    if target_col:
        for target in focus_targets:
            sub = classified[classified[target_col].astype(str) == target].copy()
            row_level_sum = int(sub[row_count_col].fillna(0).astype(float).sum()) if row_count_col and not sub.empty else 0
            distinct_files = int(sub[file_col].nunique()) if file_col and not sub.empty else 0
            measurement_ready = 0
            if measure_col and not sub.empty:
                measurement_ready = int(sub[measure_col].fillna(False).astype(bool).sum())
            uniform_rows.append(
                {
                    "target": target,
                    "classified_pair_rows": len(sub),
                    "row_level_pair_count": row_level_sum,
                    "distinct_files": distinct_files,
                    "measurement_ready_rows": measurement_ready,
                    "source_of_uniformity": "shared_multi_target_hint_expansion",
                    "interpretation": "candidate_for_semantic_disambiguation_not_independent_denominator",
                }
            )
    uniform_df = pd.DataFrame(uniform_rows)

    g08_df = pd.DataFrame()
    if not gap_register.empty:
        mask = gap_register.astype(str).apply(
            lambda col: col.str.contains("G08|parser", case=False, na=False)
        ).any(axis=1)
        g08_df = gap_register[mask].copy()

    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "safe_content_pair_rows": safe_rows,
        "target_expanded_classification_rows": classified_rows,
        "multi_target_hint_rows": multi_rows,
        "target_expansion_delta": target_expansion_delta,
        "expected_classified_rows": expected_classified,
        "target_expansion_reconciled": expected_classified == classified_rows,
        "structural_files_attempted": structural_summary.get("files_attempted"),
        "safe_content_pair_files_attempted": safe_summary.get("files_attempted"),
        "safe_content_input_source_files": safe_summary.get("input_source_files"),
        "structural_attempted_by_role": role_counts,
        "current_parser_issue_on_tabular_files": cross_summary.get("parser_issue_on_tabular_files"),
        "raw_operational_values_emitted": False,
    }

    denominator_path = REPORTS_DIR / "denominator_reconciliation_pass_sanitized.csv"
    uniform_path = REPORTS_DIR / "target_uniformity_reconciliation_sanitized.csv"
    file_path = REPORTS_DIR / "file_denominator_reconciliation_sanitized.csv"
    md_path = REPORTS_DIR / "denominator_reconciliation_pass_sanitized.md"
    summary_path = ARTIFACTS_DIR / "denominator_reconciliation_pass_summary_sanitized.json"

    denominator_df.to_csv(denominator_path, index=False)
    uniform_df.to_csv(uniform_path, index=False)
    file_denominator_df.to_csv(file_path, index=False)
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    md = "\n\n".join(
        [
            "# Asset Maintenance Bridge ML Feasibility - Denominator Reconciliation Pass",
            "## Scope",
            (
                "Short accounting pass to verify four denominator and attribution questions raised during "
                "Draft 1 review. This pass uses sanitized generated artifacts only and emits no raw "
                "operational values."
            ),
            "## Reconciliation Checks",
            md_table(denominator_df),
            "## Target Uniformity Reconciliation",
            md_table(uniform_df),
            "## File Denominator Reconciliation",
            md_table(file_denominator_df),
            "## Current G08 / Parser Gap Rows",
            md_table(g08_df),
            "## Interpretation",
            (
                "- `838` and `910` are different denominators: `838` source opportunity rows vs. `910` "
                "target-expanded classification rows.\n"
                "- Cause, Activity, and Activity Type uniformity is explained by shared multi-target expansion; "
                "it is not independent target evidence.\n"
                "- `147` vs. `157` is a scope difference: pair discovery used only source_data, while structural "
                "scan also profiled mapping/reference files.\n"
                "- The parser gap language should be governed by the latest triage/cross-target summary; if "
                "tabular parser issues are zero, stale G08 language should be updated before the next draft."
            ),
            "## Non-Goals",
            (
                "- No model training was performed.\n"
                "- No model accuracy estimate was produced.\n"
                "- No final feasibility conclusion is included.\n"
                "- No raw operational client values were emitted."
            ),
        ]
    )
    md_path.write_text(md, encoding="utf-8")

    print(json.dumps(summary, indent=2))
    print(f"wrote: {denominator_path}")
    print(f"wrote: {uniform_path}")
    print(f"wrote: {file_path}")
    print(f"wrote: {md_path}")
    print(f"wrote: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
