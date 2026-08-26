from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


EVIDENCE_TYPES = [
    {
        "evidence_type": "real_observed_label",
        "definition": "Record-level evidence where the correct target code is observed as data.",
        "can_support_measurement": True,
        "measurement_use": "Can enter the measurement denominator after runtime availability is confirmed.",
    },
    {
        "evidence_type": "validated_mapping",
        "definition": "A mapping confirmed by an SME, mapping owner, or governed project documentation.",
        "can_support_measurement": True,
        "measurement_use": "Can enter the measurement denominator if it applies at record level.",
    },
    {
        "evidence_type": "illustrative_example",
        "definition": "An example showing intended behavior, not proof of a record-level label.",
        "can_support_measurement": False,
        "measurement_use": "Useful for interpretation only unless later validated.",
    },
    {
        "evidence_type": "reference_catalog",
        "definition": "Catalog, code list, glossary, or controlled vocabulary.",
        "can_support_measurement": False,
        "measurement_use": "Useful for matching and normalization, not a ground-truth denominator.",
    },
    {
        "evidence_type": "agent_inference",
        "definition": "A pipeline-generated hypothesis inferred from metadata or structure.",
        "can_support_measurement": False,
        "measurement_use": "Must never be used as a label.",
    },
    {
        "evidence_type": "unknown",
        "definition": "Unresolved text-code opportunity that has not been classified.",
        "can_support_measurement": False,
        "measurement_use": "Preserve for semantic reconciliation; do not promote to a target yet.",
    },
]


VALIDATION_CHAIN = [
    {
        "step": "signal_exists",
        "question": "Is there source evidence that plausibly carries target information?",
        "evidence_needed": "Safe schema/profile evidence, controlled-vocabulary overlap, row-level co-occurrence, or parser-derived structured evidence.",
    },
    {
        "step": "runtime_usable",
        "question": "Will the signal be available when the production engine runs?",
        "evidence_needed": "Runtime app/source confirmation, canonical field matrix alignment, or source owner confirmation.",
    },
    {
        "step": "valid_label_or_mapping",
        "question": "Can we prove what the correct target code was for a record?",
        "evidence_needed": "Real observed label or validated mapping. Reference catalogs and agent inference are not enough.",
    },
    {
        "step": "measurable_target",
        "question": "Is there a defensible denominator for coverage/confidence measurement?",
        "evidence_needed": "Record-level label/mapping evidence tied to runtime-available input fields.",
    },
    {
        "step": "feasible_method",
        "question": "Which method is justified by the evidence?",
        "evidence_needed": "Rules, classifier, NER, hybrid method, or unresolved status based on validated evidence.",
    },
]


METHOD_PHASES = [
    {
        "phase": "Workbench prospection",
        "purpose": "Initial manual/notebook data inventory, schema profiling, vocabulary exploration, and committee review.",
        "status": "historical_context",
        "current_role": "Findings are retained as methodological context, but the local pipeline is the reproducible source of record going forward.",
    },
    {
        "phase": "Local reproducible reconstruction",
        "purpose": "Rebuild the same evidence chain as modular Python scripts with sanitized outputs and repeatable run summaries.",
        "status": "active_source_of_record",
        "current_role": "Feeds all current report sections and can be re-run as source data, parsers, or SME decisions change.",
    },
    {
        "phase": "Controlled vocabulary prospection",
        "purpose": "Use target-specific controlled terms to reduce broad keyword noise.",
        "status": "active_supporting_method",
        "current_role": "Supports signal discovery, not final model thresholding or endpoint thresholding.",
    },
    {
        "phase": "Safe content and row-level pair discovery",
        "purpose": "Identify text-code co-occurrence opportunities without emitting raw operational values in committee-facing outputs.",
        "status": "active_supporting_method",
        "current_role": "Produces candidate opportunities that require evidence classification and runtime validation.",
    },
    {
        "phase": "Target-level evidence matrix",
        "purpose": "Organize evidence by target across signal, runtime, label/mapping, measurability, and method direction.",
        "status": "draft_dependency",
        "current_role": "Useful as a bridge to target-level feasibility, but must be regenerated after sections 5 and 7 are consolidated.",
    },
]


GUARDRAILS = [
    "No raw operational client values are emitted in versioned outputs.",
    "Reference catalogs are not ground truth.",
    "Illustrative examples do not create a measurement denominator unless validated.",
    "Agent inference must never be used as a label.",
    "A zero is reportable only when the relevant source was successfully read and the denominator is explicit.",
    "Unknown text-code opportunities are preserved for reconciliation but are not promoted to a target without validation.",
    "The dual overlap settings are prospection settings only: 0.10 for discovery and 0.20 for high-specificity sanity checks.",
    "KKS can support and validate FLOC interpretation; it must not be treated as resolving or constructing the hierarchy.",
]


@dataclass(frozen=True)
class EvidenceMethodPaths:
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


def markdown_table(rows: list[dict], columns: list[str]) -> str:
    if not rows:
        return "_No rows._"

    def fmt(value: object) -> str:
        if value is None:
            return ""
        text = str(value)
        return text.replace("|", "/").replace("\n", " ")

    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(fmt(row.get(column, "")) for column in columns) + " |")
    return "\n".join(lines)


def summarize_current_artifacts(paths: EvidenceMethodPaths) -> list[dict]:
    inventory = read_csv_if_present(paths.reports_dir / "source_file_inventory_sanitized.csv")
    structural = read_json_if_present(paths.artifacts_dir / "basic_structural_scan_summary_sanitized.json")
    schema = read_json_if_present(paths.artifacts_dir / "schema_profile_summary_sanitized.json")
    vocab = read_json_if_present(paths.artifacts_dir / "catalog_vocabulary_summary_sanitized.json")
    pair = read_json_if_present(paths.artifacts_dir / "pair_evidence_classification_summary_sanitized.json")
    pdf = read_json_if_present(paths.artifacts_dir / "pdf_assets_of_concern_summary_sanitized.json")
    readiness = read_json_if_present(paths.artifacts_dir / "report_readiness_check_summary_sanitized.json")
    target_matrix = read_json_if_present(paths.artifacts_dir / "target_level_evidence_matrix_summary_sanitized.json")

    return [
        {
            "artifact": "source_file_inventory_sanitized.csv",
            "method_use": "Defines source universe, roles, categories, and versionable sanitized scope.",
            "current_count": len(inventory) if not inventory.empty else "not_available",
        },
        {
            "artifact": "basic_structural_scan_summary_sanitized.json",
            "method_use": "Confirms structured/tabular read coverage for supported sources.",
            "current_count": structural.get("files_attempted", "not_available"),
        },
        {
            "artifact": "schema_profile_summary_sanitized.json",
            "method_use": "Profiles fields, candidate text/code signals, and safe column-level metadata.",
            "current_count": schema.get("total_columns_profiled", "not_available"),
        },
        {
            "artifact": "catalog_vocabulary_summary_sanitized.json",
            "method_use": "Loads controlled vocabulary for SAP catalog targets S/B/C/5/A.",
            "current_count": vocab.get("term_count", "not_available"),
        },
        {
            "artifact": "pair_evidence_classification_summary_sanitized.json",
            "method_use": "Classifies candidate text-code opportunities by evidence type.",
            "current_count": pair.get("classified_pair_rows", "not_available"),
        },
        {
            "artifact": "pdf_assets_of_concern_summary_sanitized.json",
            "method_use": "Documents verified PDF table extraction and file-read denominator.",
            "current_count": pdf.get("files_read_ok", "not_available"),
        },
        {
            "artifact": "report_readiness_check_summary_sanitized.json",
            "method_use": "Maps current artifacts to the requested report table of contents.",
            "current_count": readiness.get("section_count", "not_available"),
        },
        {
            "artifact": "target_level_evidence_matrix_summary_sanitized.json",
            "method_use": "Draft dependency for target-level assessment; must be regenerated after sections 5 and 7 settle.",
            "current_count": target_matrix.get("target_count", "not_available"),
        },
    ]


def build_markdown(paths: EvidenceMethodPaths) -> str:
    current_artifacts = summarize_current_artifacts(paths)
    now = datetime.now(timezone.utc).isoformat()

    lines = [
        "# Asset ML Feasibility - Evidence and Validation Method",
        "",
        "## Scope",
        "",
        "This section documents the method used to move from data prospection to defensible target-level feasibility evidence.",
        "It does not include model training, accuracy estimates, or final feasibility conclusions.",
        "",
        "The local reconstruction replaces the prior manual notebook workflow as the reproducible source of record.",
        "Historical Workbench findings remain useful context, but current report claims should cite the local sanitized artifacts.",
        "",
        "## Validation Chain",
        "",
        "`signal exists -> runtime usable -> valid label/mapping -> measurable target -> feasible method`",
        "",
        markdown_table(VALIDATION_CHAIN, ["step", "question", "evidence_needed"]),
        "",
        "## Evidence Taxonomy",
        "",
        markdown_table(EVIDENCE_TYPES, ["evidence_type", "definition", "can_support_measurement", "measurement_use"]),
        "",
        "## Method Phases",
        "",
        markdown_table(METHOD_PHASES, ["phase", "purpose", "status", "current_role"]),
        "",
        "## Current Supporting Artifacts",
        "",
        markdown_table(current_artifacts, ["artifact", "method_use", "current_count"]),
        "",
        "## Runtime Availability Rule",
        "",
        "A source signal is not treated as production-usable until the runtime owner or canonical field evidence confirms that the field is available to the engine when classification is requested.",
        "Analysis-only files, mapping examples, reference catalogs, and post-hoc exports can guide prospection but do not prove runtime availability.",
        "",
        "## Measurement Denominator Rule",
        "",
        "A target is measurable only when record-level inputs can be tied to a real observed label or validated mapping.",
        "Reference catalogs, metadata-inferred links, illustrative examples, and unresolved unknown opportunities are excluded from the measurement denominator.",
        "",
        "## Zero Interpretation Rule",
        "",
        "A zero is informative only when the relevant source class was successfully read and the zero type is explicit.",
        "If a file was not read, not attempted, or parsed by the wrong extractor, the result is not interpretable as absence of evidence.",
        "",
        "## Guardrails",
        "",
    ]
    lines.extend(f"- {guardrail}" for guardrail in GUARDRAILS)
    lines.extend(
        [
            "",
            "## Current Status",
            "",
            "This section is ready as a method section for a draft assessment.",
            "Sections on measurement readiness, cross-target gaps, and target-level feasibility must still consume the latest evidence before final report language is frozen.",
            "",
            "## Run Metadata",
            "",
            f"- Created at UTC: `{now}`",
            "- Raw operational values emitted: `false`",
        ]
    )
    return "\n".join(lines) + "\n"


def write_outputs(project_root: Path) -> dict:
    paths = EvidenceMethodPaths(project_root)
    paths.reports_dir.mkdir(parents=True, exist_ok=True)
    paths.artifacts_dir.mkdir(parents=True, exist_ok=True)

    evidence_taxonomy = pd.DataFrame(EVIDENCE_TYPES)
    validation_chain = pd.DataFrame(VALIDATION_CHAIN)
    method_phases = pd.DataFrame(METHOD_PHASES)
    supporting_artifacts = pd.DataFrame(summarize_current_artifacts(paths))

    taxonomy_path = paths.reports_dir / "evidence_taxonomy_sanitized.csv"
    chain_path = paths.reports_dir / "validation_chain_sanitized.csv"
    phases_path = paths.reports_dir / "evidence_method_phases_sanitized.csv"
    artifacts_path = paths.reports_dir / "evidence_method_supporting_artifacts_sanitized.csv"
    markdown_path = paths.reports_dir / "evidence_validation_method_sanitized.md"
    summary_path = paths.artifacts_dir / "evidence_validation_method_summary_sanitized.json"

    evidence_taxonomy.to_csv(taxonomy_path, index=False)
    validation_chain.to_csv(chain_path, index=False)
    method_phases.to_csv(phases_path, index=False)
    supporting_artifacts.to_csv(artifacts_path, index=False)
    markdown_path.write_text(build_markdown(paths), encoding="utf-8")

    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "artifact": "evidence_validation_method",
        "status": "ready_for_draft_report_section",
        "validation_chain_steps": len(VALIDATION_CHAIN),
        "evidence_type_count": len(EVIDENCE_TYPES),
        "measurement_ready_evidence_types": [
            row["evidence_type"] for row in EVIDENCE_TYPES if row["can_support_measurement"]
        ],
        "current_report_use": "section_4_evidence_and_validation_method",
        "raw_operational_values_emitted": False,
        "outputs": {
            "markdown": str(markdown_path),
            "evidence_taxonomy_csv": str(taxonomy_path),
            "validation_chain_csv": str(chain_path),
            "method_phases_csv": str(phases_path),
            "supporting_artifacts_csv": str(artifacts_path),
        },
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
