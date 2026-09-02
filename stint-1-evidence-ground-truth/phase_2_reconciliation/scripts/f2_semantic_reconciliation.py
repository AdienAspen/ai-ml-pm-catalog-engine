from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]
STINT_ROOT = PROJECT_ROOT / "stint-1-evidence-ground-truth"
F2_ROOT = STINT_ROOT / "phase_2_reconciliation"
OUTPUTS_DIR = F2_ROOT / "outputs"
UNKNOWN_DIR = OUTPUTS_DIR / "unknown_reconciliation"
MULTITARGET_DIR = OUTPUTS_DIR / "multitarget_split"

PAIR_CLASSIFICATION = PROJECT_ROOT / "reports" / "pair_evidence_classification_sanitized.csv"
PAIR_INTERNAL = PROJECT_ROOT / "reports" / "internal" / "safe_content_pair_discovery.csv"
F1_HIGH = (
    STINT_ROOT
    / "phase_1_lexical"
    / "outputs"
    / "lexical_layer_v2"
    / "lexical_layer_v2_high_confidence_candidates_sanitized.csv"
)
F1D_BASELINE_SUMMARY = STINT_ROOT / "phase_1_lexical" / "outputs" / "f1d_domain_grouping_summary.json"
F1D4_SEMANTIC_SUMMARY = (
    STINT_ROOT / "phase_1_lexical" / "outputs" / "f1d4_semantic_grouping_with_aliases_summary.json"
)
F1_UNRESOLVED = (
    STINT_ROOT
    / "phase_1_lexical"
    / "outputs"
    / "lexical_layer_v2"
    / "lexical_layer_v2_unresolved_routing_sanitized.csv"
)

UNKNOWN_GROUPS = UNKNOWN_DIR / "unknown_reconciliation_groups_sanitized.csv"
UNKNOWN_LEXICAL = UNKNOWN_DIR / "unknown_lexical_reconciliation_summary_sanitized.csv"
UNKNOWN_REPORT = UNKNOWN_DIR / "unknown_reconciliation_report.md"
UNKNOWN_SUMMARY = UNKNOWN_DIR / "unknown_reconciliation_summary.json"

MULTITARGET_GROUPS = MULTITARGET_DIR / "multitarget_split_groups_sanitized.csv"
MULTITARGET_REPORT = MULTITARGET_DIR / "multitarget_split_report.md"
MULTITARGET_SUMMARY = MULTITARGET_DIR / "multitarget_split_summary.json"


def stable_key(value: object, prefix: str) -> str:
    raw = "" if value is None or pd.isna(value) else str(value)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}-{digest}"


def clean(value: object) -> str:
    return "" if value is None or pd.isna(value) else str(value)


def generic_col_family(name: object) -> str:
    col = clean(name)
    lowered = col.lower()
    if re.match(r"^unnamed:\s*\d+$", lowered):
        return "spreadsheet_unnamed_column"
    if lowered in {"description", "descriptionextended", "title", "name", "resources"}:
        return "textual_narrative_field"
    if lowered in {"reason"}:
        return "reason_text_field"
    if lowered in {"activitytype", "type", "status"}:
        return "status_or_type_field"
    if "date" in lowered or "start" in lowered or "finish" in lowered:
        return "temporal_field"
    if lowered in {"padid", "assetid", "assetserialno", "siteid", "customerid", "contractid", "orderid", "servicecontractid", "_serviceorderid", "id", "serialno", "tag"}:
        return "administrative_identifier_field"
    if "duration" in lowered or "consumption" in lowered:
        return "duration_or_quantity_field"
    if lowered.startswith("classification."):
        return "nested_classification_metadata"
    return "other_schema_field"


def source_scope(relative_path: object, likely_role: object) -> str:
    role = clean(likely_role)
    path = clean(relative_path).lower()
    if role != "source_data":
        return role or "unknown_role"
    if "api_" in path:
        return "structured_api_source_data"
    if "eod" in path or "pod" in path or "daily" in path:
        return "daily_report_source_data"
    return "source_data"


def classify_unknown_group(text_family: str, code_family: str, scope: str) -> tuple[str, str, str]:
    if text_family == "spreadsheet_unnamed_column":
        return (
            "out_of_scope",
            "spreadsheet_layout_artifact",
            "Unnamed spreadsheet columns paired with report-title/header style fields; not target evidence.",
        )
    if text_family == "temporal_field" or code_family in {"temporal_field", "duration_or_quantity_field"}:
        return (
            "out_of_scope",
            "temporal_or_quantity_metadata",
            "Scheduling, duration, or quantity co-occurrence is not a target label/mapping.",
        )
    if code_family == "administrative_identifier_field":
        if text_family in {"textual_narrative_field", "reason_text_field", "status_or_type_field"}:
            return (
                "pending",
                "text_to_identifier_cooccurrence",
                "Narrative/status text co-occurs with administrative identifiers; useful as context but not mapping evidence.",
            )
        return (
            "unrelated_cooccurrence",
            "administrative_identifier_join",
            "Identifier joins explain the co-occurrence; not target-level mapping evidence.",
        )
    if text_family == "status_or_type_field":
        return (
            "pending",
            "status_type_signal_needs_target_routing",
            "Status/type field may carry activity-type semantics but needs target-specific validation.",
        )
    if text_family in {"textual_narrative_field", "reason_text_field"}:
        return (
            "matched_vocabulary",
            "narrative_candidate_supported_by_F1",
            "Can be compared against the F1 high-confidence lexical layer, but remains non-contractual.",
        )
    return (
        "pending",
        "schema_context_unclear",
        "Pattern is not sufficient for target attribution without further semantic review.",
    )


def text_signal_family_for_multitarget(name: object) -> tuple[str, str, str]:
    col = clean(name).lower()
    if col == "reason":
        return (
            "cause_specific_reason_signal",
            "Cause",
            "Reason text is the only target-specific candidate for Cause, but pair code fields are identifiers and not validated mappings.",
        )
    if col == "activitytype":
        return (
            "activity_type_structural_signal",
            "Activity Type",
            "Activity Type is a structural source field, but it still requires MAT/catalog validation before promotion.",
        )
    if col in {"description", "descriptionextended"}:
        return (
            "shared_narrative_signal",
            "shared_not_independent",
            "General narrative supports downstream semantic review but cannot independently prove Cause, Activity, or Activity Type.",
        )
    return (
        "non_target_metadata_signal",
        "none",
        "Field does not provide target-specific evidence for the three expanded targets.",
    )


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_unknown_reconciliation(classified: pd.DataFrame, internal: pd.DataFrame) -> dict:
    unknown = classified[classified["target"] == "unknown"].copy()
    merged = unknown.merge(internal, on="pair_hash", how="left", suffixes=("", "_internal"))
    merged["text_family"] = merged["text_column_name"].map(generic_col_family)
    merged["code_family"] = merged["code_column_name"].map(generic_col_family)
    merged["source_scope"] = merged.apply(
        lambda row: source_scope(row.get("relative_path"), row.get("likely_role")), axis=1
    )
    classifications = [
        classify_unknown_group(row["text_family"], row["code_family"], row["source_scope"])
        for _, row in merged.iterrows()
    ]
    merged["reconciliation_class"] = [item[0] for item in classifications]
    merged["pattern_group"] = [item[1] for item in classifications]
    merged["interpretation"] = [item[2] for item in classifications]

    group_cols = ["source_scope", "text_family", "code_family", "reconciliation_class", "pattern_group"]
    grouped = (
        merged.groupby(group_cols, dropna=False)
        .agg(
            source_pair_rows=("pair_hash", "nunique"),
            packages=("package_id", "nunique"),
            path_hashes=("path_hash", "nunique"),
            sheet_hashes=("sheet_hash", "nunique"),
            cooccurring_rows_total=("cooccurring_rows", "sum"),
            median_cooccurrence_rate=("cooccurrence_rate", "median"),
            median_code_distinct_count=("code_distinct_count", "median"),
            median_text_distinct_count=("text_distinct_count", "median"),
        )
        .reset_index()
        .sort_values(["source_pair_rows", "cooccurring_rows_total"], ascending=False)
    )
    group_rows = []
    for idx, row in grouped.reset_index(drop=True).iterrows():
        group_rows.append(
            {
                "reconciliation_group_id": f"F2-UNK-{idx+1:03d}",
                "source_scope": row["source_scope"],
                "text_family": row["text_family"],
                "code_family": row["code_family"],
                "reconciliation_class": row["reconciliation_class"],
                "pattern_group": row["pattern_group"],
                "source_pair_rows": int(row["source_pair_rows"]),
                "packages": int(row["packages"]),
                "path_hashes": int(row["path_hashes"]),
                "sheet_hashes": int(row["sheet_hashes"]),
                "cooccurring_rows_total": int(row["cooccurring_rows_total"]),
                "median_cooccurrence_rate": round(float(row["median_cooccurrence_rate"]), 4),
                "median_code_distinct_count": round(float(row["median_code_distinct_count"]), 2),
                "median_text_distinct_count": round(float(row["median_text_distinct_count"]), 2),
                "validation_status": "agent_pattern_review_pending_human_confirmation",
                "raw_values_emitted": False,
            }
        )
    write_csv(
        UNKNOWN_GROUPS,
        group_rows,
        [
            "reconciliation_group_id",
            "source_scope",
            "text_family",
            "code_family",
            "reconciliation_class",
            "pattern_group",
            "source_pair_rows",
            "packages",
            "path_hashes",
            "sheet_hashes",
            "cooccurring_rows_total",
            "median_cooccurrence_rate",
            "median_code_distinct_count",
            "median_text_distinct_count",
            "validation_status",
            "raw_values_emitted",
        ],
    )

    high = pd.read_csv(F1_HIGH)
    unresolved = pd.read_csv(F1_UNRESOLVED)
    baseline_unknown_mapped = None
    semantic_unknown_mapped = None
    if F1D_BASELINE_SUMMARY.exists():
        baseline = json.loads(F1D_BASELINE_SUMMARY.read_text(encoding="utf-8"))
        baseline_unknown_mapped = baseline.get("target_summary", {}).get("unknown", {}).get("mapped_rows")
    if F1D4_SEMANTIC_SUMMARY.exists():
        semantic = json.loads(F1D4_SEMANTIC_SUMMARY.read_text(encoding="utf-8"))
        semantic_unknown_mapped = semantic.get("target_summary", {}).get("unknown", {}).get("mapped_rows")
    high_unknown = high[high["observed_target_hint"] == "unknown"].copy()
    unresolved_unknown = unresolved[unresolved["observed_target_hint"] == "unknown"].copy()
    f1d4_target_unknown_rows = int(
        len(
            pd.concat([high, unresolved], ignore_index=True, sort=False).query(
                "target == 'unknown'"
            )
        )
    )
    lexical_rows = []
    for target, frame in high_unknown.groupby("target"):
        lexical_rows.append(
            {
                "observed_target_hint": "unknown",
                "assigned_target": target,
                "high_confidence_rows": int(len(frame)),
                "unresolved_or_rework_rows": 0,
                "distinct_term_keys": int(frame["term_key"].nunique()),
                "distinct_canonical_concepts": int(frame["canonical_concept_id"].nunique()),
                "dominant_vocabulary_owner": clean(frame["vocabulary_owner"].mode().iloc[0])
                if not frame["vocabulary_owner"].dropna().empty
                else "",
                "status": "candidate_target_assignment_for_F2_review",
                "evidence_type": "expert_inference",
                "evaluation_independence": "derived_from_rules",
                "raw_values_emitted": False,
            }
        )
    lexical_rows.append(
        {
            "observed_target_hint": "unknown",
            "assigned_target": "unresolved_or_rework",
            "high_confidence_rows": 0,
            "unresolved_or_rework_rows": int(len(unresolved_unknown)),
            "distinct_term_keys": int(unresolved_unknown["term_key"].nunique()),
            "distinct_canonical_concepts": 0,
            "dominant_vocabulary_owner": "",
            "status": "unresolved_after_F1_quality_filter",
            "evidence_type": "unresolved",
            "evaluation_independence": "derived_from_rules",
            "raw_values_emitted": False,
        }
    )
    write_csv(
        UNKNOWN_LEXICAL,
        lexical_rows,
        [
            "observed_target_hint",
            "assigned_target",
            "high_confidence_rows",
            "unresolved_or_rework_rows",
            "distinct_term_keys",
            "distinct_canonical_concepts",
            "dominant_vocabulary_owner",
            "status",
            "evidence_type",
            "evaluation_independence",
            "raw_values_emitted",
        ],
    )

    class_counts = Counter(row["reconciliation_class"] for row in group_rows for _ in range(row["source_pair_rows"]))
    lexical_counts = {row["assigned_target"]: row["high_confidence_rows"] for row in lexical_rows}
    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "task": "F2_unknown_reconciliation",
        "source_unknown_pair_rows": int(len(unknown)),
        "reconciliation_groups": int(len(group_rows)),
        "classification_counts_by_pair_row": {str(k): int(v) for k, v in sorted(class_counts.items())},
        "lexical_unknown_high_confidence_rows": int(len(high_unknown)),
        "lexical_unknown_unresolved_or_rework_rows": int(len(unresolved_unknown)),
        "count_reconciliation": {
            "f1d1_baseline_unknown_mapped_rows": baseline_unknown_mapped,
            "f1d4_semantic_unknown_mapped_rows_before_quality_filter": semantic_unknown_mapped,
            "f1d4_final_target_unknown_rows_after_semantic_matching": f1d4_target_unknown_rows,
            "f1f_observed_unknown_high_confidence_rows": int(len(high_unknown)),
            "why_different": (
                "192 belongs to the F1d1 string/token baseline, not to F1d4. "
                "F1d4 used multilingual semantic matching and mapped 2689 of the 4600 originally unknown-hint rows before quality filtering. "
                "F1f then retained 1414 of those originally unknown-hint rows as high-confidence candidates."
            ),
            "no_expansion_or_rerun": True,
        },
        "lexical_unknown_assignment_counts": {str(k): int(v) for k, v in sorted(lexical_counts.items())},
        "validation_status": "agent_pattern_review_pending_human_confirmation",
        "raw_values_emitted": False,
        "outputs": {
            "unknown_groups_csv": str(UNKNOWN_GROUPS.relative_to(PROJECT_ROOT)),
            "unknown_lexical_summary_csv": str(UNKNOWN_LEXICAL.relative_to(PROJECT_ROOT)),
            "unknown_report": str(UNKNOWN_REPORT.relative_to(PROJECT_ROOT)),
            "unknown_summary_json": str(UNKNOWN_SUMMARY.relative_to(PROJECT_ROOT)),
        },
    }
    UNKNOWN_SUMMARY.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    report = f"""# F2 Unknown Reconciliation Report

## Scope

This report reconciles the historical `unknown` pair-discovery rows and the newer F1
high-confidence lexical assignments whose observed target hint was `unknown`.

## Pair-Discovery Unknowns

| metric | value |
| --- | ---: |
| unknown pair rows | {summary["source_unknown_pair_rows"]} |
| pattern groups | {summary["reconciliation_groups"]} |

| classification | pair rows |
| --- | ---: |
"""
    for key, value in summary["classification_counts_by_pair_row"].items():
        report += f"| {key} | {value} |\n"

    report += f"""
## F1 Lexical Unknowns

| metric | value |
| --- | ---: |
| high-confidence target assignments from unknown hint | {summary["lexical_unknown_high_confidence_rows"]} |
| unresolved/rework rows from unknown hint | {summary["lexical_unknown_unresolved_or_rework_rows"]} |

| assigned target | high-confidence rows |
| --- | ---: |
"""
    for row in lexical_rows:
        report += f"| {row['assigned_target']} | {row['high_confidence_rows']} |\n"

    report += f"""
Rows routed to unresolved/rework from unknown hint: `{summary["lexical_unknown_unresolved_or_rework_rows"]}`.

## Count Reconciliation

`192` and `1,414` are different stages/views of the lexical layer, not an undeclared
expansion:

- `192` = originally-unknown rows mapped by the F1d1 string/token baseline.
- `2,689` = originally-unknown rows mapped by F1d4 semantic matching before quality filtering.
- `1,414` = originally-unknown rows that F1f retained as
  high-confidence candidate targets after the quality filter.

Therefore `1,414 > 192` is valid because it compares F1f high-confidence semantic matches
against the earlier F1d1 baseline, not against the same matching method.

## Out-of-Scope Rule

Rows are classified as `out_of_scope` when their pattern is explained by spreadsheet layout
artifacts, temporal fields, scheduling fields, duration/quantity fields, or similar metadata
co-occurrences rather than by a source text concept paired to a target code or controlled
vocabulary.
"""

    report += """
## Interpretation

- The historical `unknown` pair rows are not a single backlog. They split into schema/layout artifacts, identifier joins, temporal metadata, and a smaller set of narrative/status candidates.
- The F1 lexical layer assigns some formerly `unknown` lexical evidence to candidate targets, but those assignments remain `expert_inference` and `derived_from_rules`.
- No row is promoted to contractual evidence by this pass.
- Group review is pattern-based and sanitized. Human confirmation can be applied at group level without inspecting all 802 rows.
"""
    UNKNOWN_REPORT.write_text(report, encoding="utf-8")
    return summary


def build_multitarget_split(classified: pd.DataFrame, internal: pd.DataFrame) -> dict:
    mt = classified[classified["target"].isin(["Cause", "Activity", "Activity Type"])].copy()
    merged = mt.merge(internal, on="pair_hash", how="left", suffixes=("", "_internal"))
    unique_pairs = merged.drop_duplicates("pair_hash").copy()
    unique_pairs["text_signal_family"] = unique_pairs["text_column_name"].map(
        lambda value: text_signal_family_for_multitarget(value)[0]
    )
    unique_pairs["candidate_owner_target"] = unique_pairs["text_column_name"].map(
        lambda value: text_signal_family_for_multitarget(value)[1]
    )
    unique_pairs["split_interpretation"] = unique_pairs["text_column_name"].map(
        lambda value: text_signal_family_for_multitarget(value)[2]
    )
    unique_pairs["code_family"] = unique_pairs["code_column_name"].map(generic_col_family)
    unique_pairs["source_scope"] = unique_pairs.apply(
        lambda row: source_scope(row.get("relative_path"), row.get("likely_role")), axis=1
    )
    group_cols = ["source_scope", "text_signal_family", "candidate_owner_target", "code_family"]
    grouped = (
        unique_pairs.groupby(group_cols, dropna=False)
        .agg(
            unique_pair_structures=("pair_hash", "nunique"),
            cooccurring_rows_total=("cooccurring_rows", "sum"),
            median_code_distinct_count=("code_distinct_count", "median"),
            median_text_distinct_count=("text_distinct_count", "median"),
        )
        .reset_index()
        .sort_values(["unique_pair_structures", "cooccurring_rows_total"], ascending=False)
    )

    rows = []
    for idx, row in grouped.reset_index(drop=True).iterrows():
        if row["candidate_owner_target"] in {"Cause", "Activity Type"}:
            target_specificity = "target_specific_candidate_not_validated_mapping"
            can_promote = False
        elif row["candidate_owner_target"] == "shared_not_independent":
            target_specificity = "shared_evidence_not_independent"
            can_promote = False
        else:
            target_specificity = "not_target_evidence"
            can_promote = False
        rows.append(
            {
                "split_group_id": f"F2-MT-{idx+1:03d}",
                "source_scope": row["source_scope"],
                "text_signal_family": row["text_signal_family"],
                "code_family": row["code_family"],
                "candidate_owner_target": row["candidate_owner_target"],
                "target_specificity": target_specificity,
                "unique_pair_structures": int(row["unique_pair_structures"]),
                "expanded_target_rows_prior": int(row["unique_pair_structures"] * 3),
                "cooccurring_rows_total": int(row["cooccurring_rows_total"]),
                "median_code_distinct_count": round(float(row["median_code_distinct_count"]), 2),
                "median_text_distinct_count": round(float(row["median_text_distinct_count"]), 2),
                "can_promote_to_target_measurement": can_promote,
                "required_next_step": "target_specific_validation_in_F4_or_denominator_exclusion",
                "validation_status": "agent_schema_review_pending_human_confirmation",
                "raw_values_emitted": False,
            }
        )
    write_csv(
        MULTITARGET_GROUPS,
        rows,
        [
            "split_group_id",
            "source_scope",
            "text_signal_family",
            "code_family",
            "candidate_owner_target",
            "target_specificity",
            "unique_pair_structures",
            "expanded_target_rows_prior",
            "cooccurring_rows_total",
            "median_code_distinct_count",
            "median_text_distinct_count",
            "can_promote_to_target_measurement",
            "required_next_step",
            "validation_status",
            "raw_values_emitted",
        ],
    )

    prior_counts = mt["target"].value_counts().to_dict()
    unique_structures = int(unique_pairs["pair_hash"].nunique())
    family_counts = {
        str(k): int(v) for k, v in unique_pairs["text_signal_family"].value_counts().sort_index().items()
    }
    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "task": "F2_multitarget_split_DELTA_0009",
        "expanded_rows_prior": int(len(mt)),
        "prior_target_counts": {str(k): int(v) for k, v in sorted(prior_counts.items())},
        "unique_pair_structures": unique_structures,
        "split_groups": int(len(rows)),
        "text_signal_family_counts": family_counts,
        "decision": {
            "shared_expansion_confirmed": True,
            "activity_cause_activity_type_not_independent": True,
            "promoted_targets": [],
            "cause": "reason_text_field is target-specific candidate only, not validated mapping",
            "activity_type": "activityType structural field is target-specific candidate only, pending MAT/catalog validation",
            "activity": "no independent Activity evidence demonstrated by these 36 structures",
        },
        "precondition_status": "DELTA-0009 split completed_for_planning_but_not_measurement_promotion",
        "raw_values_emitted": False,
        "outputs": {
            "multitarget_groups_csv": str(MULTITARGET_GROUPS.relative_to(PROJECT_ROOT)),
            "multitarget_report": str(MULTITARGET_REPORT.relative_to(PROJECT_ROOT)),
            "multitarget_summary_json": str(MULTITARGET_SUMMARY.relative_to(PROJECT_ROOT)),
        },
    }
    MULTITARGET_SUMMARY.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    report = f"""# F2 Multitarget Split Report

## Scope

This report resolves `DELTA-0009` for the 36 pair structures previously expanded across
Cause, Activity, and Activity Type.

## Reconciliation

| metric | value |
| --- | ---: |
| expanded rows before split | {summary["expanded_rows_prior"]} |
| unique pair structures | {summary["unique_pair_structures"]} |
| split groups | {summary["split_groups"]} |

| prior target | expanded rows |
| --- | ---: |
"""
    for key, value in summary["prior_target_counts"].items():
        report += f"| {key} | {value} |\n"

    report += """
## Decision

The 36 structures are shared-expanded evidence, not three independent target signals.
No target is promoted to measurement readiness by this split.

- `reason` is a Cause-specific candidate field, but its paired code fields are identifiers or metadata, not validated mappings.
- `activityType` is an Activity Type structural candidate, pending MAT/catalog validation.
- `description` and `descriptionExtended` are shared narrative evidence; they support downstream weak supervision but do not independently prove Cause, Activity, or Activity Type.
- No independent Activity evidence is demonstrated by these 36 structures.

## Implication

The apparent uniform evidence for Cause, Activity, and Activity Type is downgraded to
shared evidence. F4/F6 must treat each target separately and must not count the same shared
source structure as three independent denominators.
"""
    MULTITARGET_REPORT.write_text(report, encoding="utf-8")
    return summary


def main() -> None:
    classified = pd.read_csv(PAIR_CLASSIFICATION)
    internal = pd.read_csv(PAIR_INTERNAL)
    unknown_summary = build_unknown_reconciliation(classified, internal)
    multitarget_summary = build_multitarget_split(classified, internal)
    print(
        json.dumps(
            {
                "unknown_reconciliation": unknown_summary,
                "multitarget_split": multitarget_summary,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
