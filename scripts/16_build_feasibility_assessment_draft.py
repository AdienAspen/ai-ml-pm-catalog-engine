from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = PROJECT_ROOT / "reports"
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"

OUT_MD = REPORTS_DIR / "ai_ml_data_feasibility_assessment_draft1_sanitized.md"
OUT_JSON = ARTIFACTS_DIR / "ai_ml_data_feasibility_assessment_draft1_summary_sanitized.json"


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path)


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists() or path.stat().st_size == 0:
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def value(obj: dict[str, Any], key: str, default: Any = 0) -> Any:
    return obj.get(key, default)


def nested_value(obj: dict[str, Any], keys: list[str], default: Any = "unknown") -> Any:
    current: Any = obj
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def first_value(obj: dict[str, Any], keys: list[str], default: Any = "unknown") -> Any:
    for key in keys:
        if key in obj and obj[key] not in (None, ""):
            return obj[key]
    return default


def structural_output_count(summary: dict[str, Any]) -> Any:
    return first_value(
        summary,
        ["output_rows", "scan_rows", "schema_rows", "sheet_rows", "record_count"],
        default=read_ok_count(summary),
    )


def read_ok_count(summary: dict[str, Any]) -> Any:
    if "files_read_ok" in summary:
        return summary["files_read_ok"]
    read_status_counts = summary.get("read_status_counts", {})
    if not isinstance(read_status_counts, dict):
        return "unknown"
    total = 0
    for key, count in read_status_counts.items():
        normalized_key = str(key).lower()
        if "ok" in normalized_key or "success" in normalized_key:
            total += int(count)
    return total if total else "unknown"


def unknown_opportunity_rows(pair_summary: dict[str, Any]) -> Any:
    return nested_value(
        pair_summary,
        ["evidence_type_counts", "unknown"],
        default=nested_value(pair_summary, ["target_classification_counts", "unknown"], default="unknown"),
    )


def md_table(df: pd.DataFrame, columns: list[str] | None = None, max_rows: int | None = None) -> str:
    if df.empty:
        return "_No rows._"

    view = df.copy()
    if columns:
        existing = [column for column in columns if column in view.columns]
        view = view[existing]
    if max_rows is not None:
        view = view.head(max_rows)

    if view.empty:
        return "_No rows._"

    def clean_cell(cell: Any) -> str:
        if pd.isna(cell):
            return ""
        text = str(cell).replace("\n", " ").replace("|", "/").strip()
        return text

    headers = [clean_cell(column) for column in view.columns]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for _, row in view.iterrows():
        lines.append("| " + " | ".join(clean_cell(row[column]) for column in view.columns) + " |")
    return "\n".join(lines)


def bullets(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items]


def section(title: str, lines: list[str]) -> list[str]:
    return [f"## {title}", "", *lines, ""]


def target_sections(target_matrix: pd.DataFrame) -> list[str]:
    lines: list[str] = []
    ordered_targets = [
        "Symptom",
        "Object Part",
        "Damage",
        "Cause",
        "Activity",
        "FLOC leaf segment",
        "Activity Type",
    ]
    by_target = {str(row["target"]): row for _, row in target_matrix.iterrows()} if not target_matrix.empty else {}

    for index, target in enumerate(ordered_targets, start=1):
        row = by_target.get(target)
        lines.extend([f"### 6.{index} {target}", ""])
        if row is None:
            lines.extend(["No current target-level row is available in the sanitized evidence matrix.", ""])
            continue

        lines.extend(
            bullets(
                [
                    f"Available source signal: `{row.get('available_source_signal', '')}`.",
                    f"Runtime usability: `{row.get('runtime_usability', '')}`.",
                    f"Ground-truth / mapping support: `{row.get('ground_truth_or_mapping_support', '')}`.",
                    f"Measurable target status: `{row.get('measurable_target_status', '')}`.",
                    f"Current measurement-ready pair rows: `{row.get('measurement_ready_pair_rows', 0)}`.",
                    f"Derivability assessment: `{row.get('derivability_assessment', '')}`.",
                    f"Recommended method direction: `{row.get('recommended_method', '')}`.",
                    f"Coverage/confidence status: `{row.get('coverage_confidence_status', '')}`.",
                    f"Primary blocker: {row.get('primary_blocker', '')}",
                    f"Input needed from: {row.get('needed_from_whom', '')}",
                ]
            )
        )
        lines.append("")

    return lines


def main() -> int:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    inventory_summary = read_json(ARTIFACTS_DIR / "source_inventory_summary_sanitized.json")
    structural_summary = read_json(ARTIFACTS_DIR / "basic_structural_scan_summary_sanitized.json")
    schema_summary = read_json(ARTIFACTS_DIR / "schema_profile_summary_sanitized.json")
    vocab_summary = read_json(ARTIFACTS_DIR / "catalog_loading_summary_sanitized.json")
    overlap_summary = read_json(ARTIFACTS_DIR / "vocabulary_column_overlap_summary_sanitized.json")
    mapping_summary = read_json(ARTIFACTS_DIR / "preliminary_target_mapping_summary_sanitized.json")
    pair_summary = read_json(ARTIFACTS_DIR / "pair_evidence_classification_summary_sanitized.json")
    pdf_summary = read_json(ARTIFACTS_DIR / "pdf_assets_of_concern_summary_sanitized.json")
    readiness_summary = read_json(ARTIFACTS_DIR / "report_section_readiness_update_summary_sanitized.json")

    target_matrix = read_csv(REPORTS_DIR / "target_level_evidence_matrix_sanitized.csv")
    readiness = read_csv(REPORTS_DIR / "report_section_readiness_update_sanitized.csv")
    source_denominators = read_csv(REPORTS_DIR / "source_read_denominator_summary_sanitized.csv")
    measurement = read_csv(REPORTS_DIR / "measurement_readiness_by_target_sanitized.csv")
    taxonomy = read_csv(REPORTS_DIR / "evidence_taxonomy_sanitized.csv")
    chain = read_csv(REPORTS_DIR / "validation_chain_sanitized.csv")
    method_phases = read_csv(REPORTS_DIR / "evidence_method_phases_sanitized.csv")
    findings = read_csv(REPORTS_DIR / "cross_target_findings_summary_sanitized.csv")
    gaps = read_csv(REPORTS_DIR / "cross_target_gap_register_sanitized.csv")
    fault_profile = read_csv(REPORTS_DIR / "pdf_assets_of_concern_fault_code_profile_sanitized.csv")

    measurement_ready_targets = (
        int((target_matrix["measurement_ready_pair_rows"].fillna(0).astype(int) > 0).sum())
        if not target_matrix.empty and "measurement_ready_pair_rows" in target_matrix.columns
        else 0
    )
    target_count = len(target_matrix) if not target_matrix.empty else 7
    high_gap_count = int((gaps["severity"].astype(str).str.lower() == "high").sum()) if not gaps.empty else 0

    lines: list[str] = [
        "# Asset Maintenance Bridge - AI/ML Data Feasibility Assessment",
        "",
        "**Draft status:** Draft 1 / evidence-based technical memo.",
        "",
        "**Scope guardrail:** no model training, no accuracy estimate, and no final feasibility conclusion are included in this draft.",
        "",
        "**Data governance guardrail:** no raw operational client values are emitted in this report.",
        "",
        "## Table of Contents",
        "",
        "1. Executive Summary",
        "2. Assessment Scope & Questions",
        "3. Data Universe & Effective Read Coverage",
        "4. Evidence & Validation Method",
        "5. Ground-Truth & Measurement Readiness",
        "6. Target-Level Feasibility Assessment",
        "7. Cross-Target Findings & Data Gaps",
        "8. Feasibility Matrix & Recommended Technical Direction",
        "9. Required Inputs, Owners & Decisions",
        "10. Conclusions & Next Steps",
        "Appendices A-E",
        "",
    ]

    lines.extend(
        section(
            "1. Executive Summary",
            [
                "This assessment implements the AI/ML data feasibility evidence chain as a local, reproducible, sanitized POC pipeline. The current result is an evidence-readiness view, not a final feasibility decision.",
                "",
                *bullets(
                    [
                        f"Targets assessed: `{target_count}`.",
                        f"Current measurement-ready targets: `{measurement_ready_targets}`.",
                        f"Inventoried source universe: `{first_value(inventory_summary, ['file_count', 'total_files'], 'unknown')}` files.",
                        f"Structured/tabular output rows emitted by the structural pass: `{structural_output_count(structural_summary)}`.",
                        f"Candidate safe content pair rows classified: `{first_value(pair_summary, ['classified_pair_rows', 'classified_rows'], 'unknown')}`.",
                        f"External PDF-derived fault-code rows with non-empty code signal: `{value(pdf_summary, 'fault_code_non_empty_rows', 'unknown')}`.",
                        f"Distinct external fault-code tokens profiled: `{value(pdf_summary, 'distinct_fault_code_count', 'unknown')}`.",
                        f"High-severity open gaps: `{high_gap_count}`.",
                    ]
                ),
                "",
                "Main finding: the corpus contains meaningful source signal and structured opportunities, but no target currently has a validated measurement denominator. The next decision is therefore not model selection; it is validation of runtime availability and true labels or SME-confirmed mappings.",
            ],
        )
    )

    lines.extend(
        section(
            "2. Assessment Scope & Questions",
            [
                "The objective is to assess whether available historical and reference data can support AI/ML-assisted extraction or classification into the seven target outcomes.",
                "",
                *bullets(
                    [
                        "Symptom / Catalog S.",
                        "Object Part / Catalog B.",
                        "Damage / Catalog C.",
                        "Cause / Catalog 5.",
                        "Activity / Catalog A.",
                        "FLOC leaf segment.",
                        "Activity Type / MAT.",
                    ]
                ),
                "",
                "This assessment measures evidence readiness: source signal, runtime plausibility, label/mapping support, measurement readiness, and method direction. It does not train models, estimate production accuracy, or set endpoint thresholds.",
            ],
        )
    )

    lines.extend(
        section(
            "3. Data Universe & Effective Read Coverage",
            [
                "The local POC pipeline separates inventory from effective read coverage. A listed file is not treated as read unless the parser opened it successfully.",
                "",
                md_table(source_denominators),
                "",
                *bullets(
                    [
                        f"Source inventory files: `{first_value(inventory_summary, ['file_count', 'total_files'], 'unknown')}`.",
                        f"Structural scan files attempted: `{value(structural_summary, 'files_attempted', 'unknown')}`.",
                        f"Structural scan output rows emitted: `{structural_output_count(structural_summary)}`.",
                        f"PDF files listed in the external fault-code parser pass: `{value(pdf_summary, 'files_listed', 'unknown')}`.",
                        f"PDF files read successfully: `{value(pdf_summary, 'files_read_ok', 'unknown')}`.",
                        f"PDF parser failures: `{value(pdf_summary, 'files_failed', 'unknown')}`.",
                    ]
                ),
                "",
                "Remaining gaps are tracked as parser, vocabulary, runtime, and SME-confirmation dependencies rather than as negative feasibility findings.",
            ],
        )
    )

    lines.extend(
        section(
            "4. Evidence & Validation Method",
            [
                "The local POC assessment uses a conservative validation chain:",
                "",
                md_table(chain),
                "",
                "Evidence types are explicitly separated so that reference material, inferred relationships, and examples do not become artificial ground truth.",
                "",
                md_table(taxonomy),
                "",
                "Method phases:",
                "",
                md_table(method_phases),
                "",
                "Controlled vocabulary and prospection notes:",
                "",
                *bullets(
                    [
                        f"Controlled catalog vocabulary rows loaded: `{first_value(vocab_summary, ['vocabulary_rows', 'catalog_term_count', 'master_vocabulary_rows', 'catalog_rows', 'term_rows', 'row_count'], 'unknown')}`.",
                        f"Vocabulary overlap rows: `{value(overlap_summary, 'overlap_rows', 'unknown')}`.",
                        "Prospection thresholds are methodological filters only; they are not model confidence thresholds and are not endpoint thresholds.",
                        "Stage-loss evidence is used to explain filtering behavior, not to estimate final model performance.",
                    ]
                ),
            ],
        )
    )

    lines.extend(
        section(
            "5. Ground-Truth & Measurement Readiness",
            [
                "Current ground-truth status remains conservative. Candidate pairs are preserved for review, but none are measurement-ready until runtime availability and label/mapping validity are confirmed.",
                "",
                md_table(
                    measurement,
                    [
                        "target",
                        "candidate_pair_rows",
                        "row_level_pair_count",
                        "distinct_files",
                        "measurement_ready_pair_count",
                        "measurement_readiness_status",
                        "zero_type_or_denominator_status",
                        "next_required_action",
                    ],
                ),
                "",
                *bullets(
                    [
                        f"Measurement-ready pair rows after conservative classification: `{first_value(pair_summary, ['measurement_ready_pair_rows', 'measurement_ready_rows'], 0)}`.",
                        f"Unknown opportunity rows preserved for later semantic reconciliation: `{unknown_opportunity_rows(pair_summary)}`.",
                        "Reference/catalog evidence is useful for matching and rule design, but it does not create a record-level measurement denominator.",
                        "Agent inference is never used as a label.",
                    ]
                ),
            ],
        )
    )

    lines.extend(["## 6. Target-Level Feasibility Assessment", ""])
    lines.extend(
        [
            "This section is intentionally written as target-level evidence readiness. It does not claim final feasibility, coverage, or confidence because validated denominators are not yet established.",
            "",
        ]
    )
    lines.extend(target_sections(target_matrix))

    lines.extend(
        section(
            "7. Cross-Target Findings & Data Gaps",
            [
                "Cross-target findings show that the principal current risk is not lack of text signal; it is unresolved target relevance, runtime usability, and label/mapping confirmation.",
                "",
                md_table(findings, max_rows=12),
                "",
                "Open gap register:",
                "",
                md_table(gaps, max_rows=12),
                "",
                "External PDF-derived fault-code evidence is a material finding: the parser recovered structured fault-code signal, but those codes do not currently map to the loaded S/B/C/5/A vocabulary. This points to a separate controlled fault/alarm vocabulary or crosswalk that requires SME or source-owner confirmation.",
            ],
        )
    )

    feasibility_columns = [
        "target",
        "available_source_signal",
        "measurable_target_status",
        "recommended_method",
        "coverage_confidence_status",
        "primary_blocker",
    ]
    lines.extend(
        section(
            "8. Feasibility Matrix & Recommended Technical Direction",
            [
                "The matrix below is directional. It supports prioritization and next-step planning, but not final go/no-go feasibility decisions.",
                "",
                md_table(target_matrix, feasibility_columns),
            ],
        )
    )

    lines.extend(
        section(
            "9. Required Inputs, Owners & Decisions",
            [
                "The following inputs are needed before any target can move from evidence readiness to measured feasibility.",
                "",
                md_table(gaps, ["gap_id", "gap", "targets", "severity", "owner_needed", "decision_needed"], max_rows=12),
                "",
                *bullets(
                    [
                        "Confirm which candidate signals are available at runtime.",
                        "Confirm which text-code relationships are real observed labels or SME-validated record-level mappings.",
                        "Confirm the controlled source for Activity Type / MAT.",
                        "Provide or confirm the controlled vocabulary/crosswalk for external fault-code signals.",
                        "Continue treating Symptom as no-current-demonstrable-proof-of-life unless SME evidence overturns it.",
                    ]
                ),
            ],
        )
    )

    lines.extend(
        section(
            "10. Conclusions & Next Steps",
            [
                "This draft is ready as an evidence-based technical memo, with explicit limitations.",
                "",
                *bullets(
                    [
                        "Proceed with SME/runtime validation before any modeling work.",
                        "Use unknown opportunities as a preserved discovery backlog, not as target evidence.",
                        "Use the external fault-code appendix as a concrete SME ask for vocabulary ownership and crosswalk confirmation.",
                        "Do not estimate model accuracy or coverage until a measurement denominator exists.",
                        "After SME validation, update the target matrix and only then decide whether rules, NER, classical ML, or hybrid methods are justified per target.",
                    ]
                ),
            ],
        )
    )

    lines.extend(
        [
            "## Appendices",
            "",
            "### Appendix A. Source and Effective-Read Inventory",
            "",
            md_table(source_denominators),
            "",
            "### Appendix B. Ground-Truth Evidence Tables",
            "",
            "The evidence tables are included as denominator-readiness evidence, not as final performance evidence.",
            "",
            md_table(measurement),
            "",
            "### Appendix C. Target Reconciliation Matrix",
            "",
            md_table(target_matrix),
            "",
            "### Appendix D. Prospection / Threshold / Stage-Loss Evidence",
            "",
            "The prospection history supports methodological defensibility. It shows why broad text availability was insufficient and why controlled vocabulary, threshold sensitivity, and stage-loss accounting were required. These artifacts are not accuracy measurements.",
            "",
            *bullets(
                [
                    f"Vocabulary overlap rows: `{value(overlap_summary, 'overlap_rows', 'unknown')}`.",
                    f"Preliminary target mapping rows: `{first_value(mapping_summary, ['preliminary_mapping_rows', 'mapping_rows'], 'unknown')}`.",
                    "Dual-threshold interpretation remains methodological: lower threshold for discovery, higher threshold for high-specificity sanity checks.",
                ]
            ),
            "",
            "### Appendix E. Parser, PDF and Remaining Data-Quality Issues",
            "",
            "External fault-code profile, sanitized:",
            "",
            md_table(fault_profile.head(20)),
            "",
            "Parser and data-quality caveats:",
            "",
            *bullets(
                [
                    "PDF parser results are structured and sanitized; raw operational text is not emitted here.",
                    "External fault-code values are represented in sanitized profile form for versioned outputs.",
                    "Remaining data-quality issues should be handled as parser or source-owner follow-up, not as negative feasibility conclusions.",
                ]
            ),
            "",
        ]
    )

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "artifact": "ai_ml_data_feasibility_assessment_draft1_sanitized",
        "output_markdown": str(OUT_MD.relative_to(PROJECT_ROOT)),
        "target_count": target_count,
        "measurement_ready_targets": measurement_ready_targets,
        "high_severity_gap_count": high_gap_count,
        "section_status_counts": readiness_summary.get("status_counts", {}),
        "report_mode": "draft_evidence_readiness_assessment",
        "raw_operational_values_emitted": False,
    }
    OUT_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
