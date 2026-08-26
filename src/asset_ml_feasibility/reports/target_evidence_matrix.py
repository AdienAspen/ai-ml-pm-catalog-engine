from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


TARGETS = [
    "Symptom",
    "Object Part",
    "Damage",
    "Cause",
    "Activity",
    "FLOC leaf segment",
    "Activity Type",
]

MEASUREMENT_READY_TYPES = {"real_observed_label", "validated_mapping"}


@dataclass(frozen=True)
class MatrixPaths:
    root: Path

    @property
    def reports_dir(self) -> Path:
        return self.root / "reports"

    @property
    def artifacts_dir(self) -> Path:
        return self.root / "artifacts"


def read_csv_if_present(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path)


def read_json_if_present(path: Path) -> dict:
    if not path.exists() or path.stat().st_size == 0:
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def yes_no_unknown(value: object) -> str:
    if pd.isna(value):
        return "unknown"
    if bool(value):
        return "yes"
    return "no"


def target_rows(df: pd.DataFrame, target: str) -> pd.DataFrame:
    if df.empty or "target" not in df.columns:
        return pd.DataFrame()
    return df[df["target"].astype(str).eq(target)].copy()


def evidence_signal_status(
    target: str,
    mapping_rows: pd.DataFrame,
    pair_rows: pd.DataFrame,
    pdf_summary: dict,
) -> str:
    if target == "Symptom":
        return "near_zero_current_evidence"
    if target == "FLOC leaf segment":
        return "provisional_glossary_or_supporting_signal"
    if target == "Activity Type":
        if not pair_rows.empty or not mapping_rows.empty:
            return "pending_controlled_source_signal"
        return "pending_controlled_source"
    if target == "Activity" and not pair_rows.empty:
        return "candidate_text_code_signal"
    if target in {"Damage", "Cause", "Object Part"}:
        if not mapping_rows.empty or not pair_rows.empty:
            return "limited_or_uncertain_signal"
        if pdf_summary.get("fault_code_non_empty_rows", 0):
            return "external_fault_code_signal_not_mapped_to_current_catalog"
        return "not_demonstrated_in_current_pass"
    return "not_demonstrated_in_current_pass"


def runtime_status(mapping_rows: pd.DataFrame, pair_rows: pd.DataFrame, target: str) -> str:
    if target == "Symptom":
        return "not_demonstrated"
    if target == "Activity Type":
        return "pending_controlled_source_confirmation"

    runtime_values: set[str] = set()
    for df in (mapping_rows, pair_rows):
        if not df.empty and "runtime_likelihood" in df.columns:
            runtime_values.update(df["runtime_likelihood"].dropna().astype(str).unique().tolist())

    if any("potential_runtime" in value or "source_signal" in value for value in runtime_values):
        return "candidate_requires_runtime_validation"
    if not mapping_rows.empty or not pair_rows.empty:
        return "requires_runtime_validation"
    return "not_demonstrated"


def label_status(pair_rows: pd.DataFrame, target: str) -> str:
    if target == "Activity Type":
        return "pending_controlled_source_confirmation"
    if pair_rows.empty:
        return "not_demonstrated"

    if "evidence_type" not in pair_rows.columns:
        return "requires_validation"

    evidence_types = set(pair_rows["evidence_type"].dropna().astype(str).unique().tolist())
    if evidence_types & MEASUREMENT_READY_TYPES:
        return "measurement_candidate_present"
    if "unknown" in evidence_types:
        return "unknown_requires_semantic_reconciliation"
    if "agent_inference" in evidence_types:
        return "metadata_or_agent_inference_not_label"
    if "reference_catalog" in evidence_types:
        return "reference_catalog_not_record_label"
    return "requires_validation"


def measurement_status(pair_rows: pd.DataFrame) -> tuple[int, str]:
    if pair_rows.empty:
        return 0, "not_currently_measurable"
    if "can_support_measurement" not in pair_rows.columns:
        return 0, "requires_evidence_type_validation"
    ready = pair_rows[pair_rows["can_support_measurement"].astype(str).str.lower().eq("true")]
    if len(ready):
        return int(len(ready)), "measurement_candidate_present"
    return 0, "not_currently_measurable"


def recommended_method(target: str, signal_status: str, label_status_value: str) -> str:
    if target == "Symptom":
        return "blocked_pending_new_evidence_or_sme_proof_of_life"
    if target == "Activity Type":
        return "blocked_pending_controlled_mat_source"
    if target == "FLOC leaf segment":
        return "rules_or_classifier_candidate_with_kks_supporting_validator"
    if "external_fault_code_signal" in signal_status:
        return "requires_controlled_fault_vocabulary_before_method_selection"
    if label_status_value == "measurement_candidate_present":
        return "hybrid_rules_or_supervised_classifier_candidate"
    if signal_status in {"candidate_text_code_signal", "limited_or_uncertain_signal"}:
        return "candidate_pending_ground_truth_and_runtime_validation"
    return "unresolved_pending_evidence"


def feasibility_level(
    target: str,
    signal_status: str,
    runtime_status_value: str,
    label_status_value: str,
    measurement_status_value: str,
) -> str:
    if target == "Symptom":
        return "not_demonstrable_with_current_evidence"
    if target == "Activity Type":
        return "blocked_pending_controlled_source"
    if measurement_status_value == "measurement_candidate_present":
        return "candidate_measurable_pending_validation"
    if "external_fault_code_signal" in signal_status:
        return "candidate_signal_requires_vocab_mapping"
    if runtime_status_value.startswith("candidate") and "requires" in label_status_value:
        return "candidate_signal_not_yet_measurable"
    if signal_status in {"limited_or_uncertain_signal", "candidate_text_code_signal"}:
        return "partial_candidate_requires_validation"
    return "insufficient_current_evidence"


def blocker_and_owner(target: str, signal_status: str) -> tuple[str, str]:
    if target == "Symptom":
        return (
            "No current demonstrable proof-of-life under available evidence.",
            "SME / technical lead / field matrix owner",
        )
    if target == "Activity Type":
        return (
            "Controlled source for activity type code remains unconfirmed.",
            "OEM SME / mapping owner / technical lead",
        )
    if target == "FLOC leaf segment":
        return (
            "Glossary or KKS support must be validated as ML/NLP signal, not resolver.",
            "SAP functional owner / SME / technical lead",
        )
    if "external_fault_code_signal" in signal_status:
        return (
            "Fault-code vocabulary owner or crosswalk to SAP catalog is not confirmed.",
            "OEM SME / controls owner / mapping owner",
        )
    return (
        "Runtime availability and record-level label or validated mapping support are not closed.",
        "SME / mapping owner / runtime application owner",
    )


def field_matrix_reference(target: str) -> str:
    references = {
        "Symptom": "0 resolvable mappings in profiling evidence.",
        "Object Part": "Long-tail and singleton behavior reported; record-level mappings still need confirmation.",
        "Damage": "Partial profiling or mapping coverage reported; record-level labels not demonstrated here.",
        "Cause": "Low profiling or mapping coverage reported; record-level labels not demonstrated here.",
        "Activity": "No final measured derivability conclusion in this pass.",
        "FLOC leaf segment": "Glossary-based support exists; KKS is supporting validator only.",
        "Activity Type": "Controlled MAT/activity-type source pending.",
    }
    return references[target]


def markdown_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_No rows._"

    safe_df = df.fillna("").astype(str)
    columns = safe_df.columns.tolist()
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join(["---"] * len(columns)) + " |",
    ]
    for _, row in safe_df.iterrows():
        values = [str(row[column]).replace("|", "/") for column in columns]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def build_target_evidence_matrix(root: Path) -> tuple[pd.DataFrame, dict]:
    paths = MatrixPaths(root=root)
    mapping = read_csv_if_present(paths.reports_dir / "preliminary_target_mapping_sanitized.csv")
    pair_review = read_csv_if_present(paths.reports_dir / "target_pair_review_sanitized.csv")
    pair_classification = read_csv_if_present(paths.reports_dir / "pair_evidence_classification_sanitized.csv")
    pdf_summary = read_json_if_present(paths.artifacts_dir / "pdf_assets_of_concern_summary_sanitized.json")

    rows: list[dict] = []
    for target in TARGETS:
        target_mapping = target_rows(mapping, target)
        target_pair_review = target_rows(pair_review, target)
        target_pairs = target_rows(pair_classification, target)

        signal_status = evidence_signal_status(target, target_mapping, target_pairs, pdf_summary)
        runtime_status_value = runtime_status(target_mapping, target_pairs, target)
        label_status_value = label_status(target_pairs, target)
        measurement_count, measurement_status_value = measurement_status(target_pairs)
        blocker, owner = blocker_and_owner(target, signal_status)

        rows.append(
            {
                "target": target,
                "available_source_signal": signal_status,
                "runtime_usability": runtime_status_value,
                "ground_truth_or_mapping_support": label_status_value,
                "measurable_target_status": measurement_status_value,
                "measurement_ready_pair_rows": measurement_count,
                "preliminary_mapping_rows": int(len(target_mapping)),
                "classified_pair_rows": int(len(target_pairs)),
                "row_level_pair_count": int(
                    target_pair_review["row_level_pair_count"].sum()
                    if not target_pair_review.empty and "row_level_pair_count" in target_pair_review
                    else 0
                ),
                "derivability_assessment": feasibility_level(
                    target,
                    signal_status,
                    runtime_status_value,
                    label_status_value,
                    measurement_status_value,
                ),
                "recommended_method": recommended_method(target, signal_status, label_status_value),
                "coverage_confidence_status": "not_estimated_no_validated_denominator",
                "primary_blocker": blocker,
                "needed_from_whom": owner,
                "field_matrix_reference": field_matrix_reference(target),
                "raw_operational_values_emitted": False,
            }
        )

    matrix = pd.DataFrame(rows)
    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "artifact": "target_level_evidence_matrix",
        "target_count": len(matrix),
        "measurement_ready_targets": int(
            (matrix["measurement_ready_pair_rows"].astype(int) > 0).sum()
        ),
        "blocked_or_not_demonstrable_targets": int(
            matrix["derivability_assessment"]
            .astype(str)
            .str.contains("blocked|not_demonstrable|insufficient", regex=True)
            .sum()
        ),
        "current_report_use": "input_to_target_level_feasibility_assessment_draft",
        "raw_operational_values_emitted": False,
    }
    return matrix, summary


def write_markdown(matrix: pd.DataFrame, summary: dict, path: Path) -> None:
    lines = [
        "# Target-Level Evidence Matrix",
        "",
        "This matrix is a prerequisite input to the Target-Level Feasibility Assessment.",
        "It does not provide model accuracy, endpoint thresholds, or final feasibility conclusions.",
        "",
        "## Summary",
        "",
        f"- Targets covered: {summary['target_count']}",
        f"- Measurement-ready targets: {summary['measurement_ready_targets']}",
        f"- Blocked or not-demonstrable targets: {summary['blocked_or_not_demonstrable_targets']}",
        "- Raw operational values emitted: false",
        "",
        "## Matrix",
        "",
        markdown_table(matrix),
        "",
        "## Interpretation Guardrails",
        "",
        "- A candidate signal is not a validated label.",
        "- Runtime availability must be confirmed before a source can become a usable feature.",
        "- Only real observed labels or validated mappings can support measurement.",
        "- Zero measurement-ready rows does not automatically mean zero derivability.",
        "- KKS can support or validate FLOC interpretation; it must not be treated as a resolver.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_outputs(root: Path) -> dict:
    paths = MatrixPaths(root=root)
    matrix, summary = build_target_evidence_matrix(root)
    paths.reports_dir.mkdir(parents=True, exist_ok=True)
    paths.artifacts_dir.mkdir(parents=True, exist_ok=True)

    csv_path = paths.reports_dir / "target_level_evidence_matrix_sanitized.csv"
    md_path = paths.reports_dir / "target_level_evidence_matrix_sanitized.md"
    json_path = paths.artifacts_dir / "target_level_evidence_matrix_summary_sanitized.json"

    matrix.to_csv(csv_path, index=False)
    write_markdown(matrix, summary, md_path)
    summary["outputs"] = {
        "csv": str(csv_path),
        "markdown": str(md_path),
    }
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
