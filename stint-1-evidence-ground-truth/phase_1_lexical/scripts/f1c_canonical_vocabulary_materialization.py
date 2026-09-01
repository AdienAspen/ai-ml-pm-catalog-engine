from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]
REFERENCE_ROOT = PROJECT_ROOT / "stint-1.1-reference-layer"
STINT_ROOT = PROJECT_ROOT / "stint-1-evidence-ground-truth"
F1_ROOT = STINT_ROOT / "phase_1_lexical"
OUTPUTS_DIR = F1_ROOT / "outputs"
VOCAB_DIR = OUTPUTS_DIR / "canonical_vocabulary"

SAP_MAPPING = REFERENCE_ROOT / "reference_layer" / "sap_mapping" / "sap_mapping_catalog_v1.csv"
IH06_NODES = REFERENCE_ROOT / "outputs" / "floc_ih06_observed_nodes_v1.csv"
ZEUS_SCAFFOLD = (
    REFERENCE_ROOT / "reference_layer" / "semantic_normalisation" / "zeus_semantic_scaffold_v1.csv"
)

SOURCE_DATE = "2026-08-31"


def stable_key(value: object, prefix: str) -> str:
    raw = "" if value is None or pd.isna(value) else str(value)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}-{digest}"


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def add_sap_mapping_rows(rows: list[dict], working_rows: list[dict]) -> None:
    if not SAP_MAPPING.exists():
        rows.append(pending_row("SAP_MAPPING", "all_catalog_targets", "missing_source_file"))
        return
    df = pd.read_csv(SAP_MAPPING)
    for _, row in df.iterrows():
        concept_source_key = "|".join(
            str(row.get(col, ""))
            for col in ["target", "namespace", "catalog", "code_group", "code", "short_text"]
        )
        concept_id = stable_key(concept_source_key, "CV-SAP")
        base = {
            "concept_id": concept_id,
            "canonical_concept_key": stable_key(row.get("short_text", ""), "CONCEPT"),
            "vocabulary_owner": "SAP_MAPPING",
            "target": row.get("target"),
            "namespace": row.get("namespace"),
            "target_field": row.get("canonical_field"),
            "concept_role": "valid_target_code",
            "source": "SAP mapping catalog",
            "source_version": row.get("source_version", "reference-layer-v1"),
            "source_date": SOURCE_DATE,
            "evidence_type": row.get("evidence_type", "reference_evidence"),
            "tier": row.get("tier", "gold"),
            "status": row.get("status", "active"),
            "can_support_contractual_denominator": False,
            "can_support_proxy_denominator": False,
            "requires_mapping_from_observed_text": True,
            "label_generation_method": "reference_catalog_ingest",
            "evaluation_independence": "independent",
            "raw_values_emitted": False,
        }
        rows.append(base)
        working_rows.append(
            {
                **base,
                "canonical_concept": row.get("short_text", ""),
                "target_code": row.get("code", ""),
                "code_group": row.get("code_group", ""),
            }
        )


def add_ih06_rows(rows: list[dict], working_rows: list[dict]) -> None:
    if not IH06_NODES.exists():
        rows.append(pending_row("IH06_OBSERVED_NODES", "FLOC leaf", "missing_source_file"))
        return
    df = pd.read_csv(IH06_NODES)
    for _, row in df.iterrows():
        token = row.get("observed_node_token", "")
        source_key = f"FLOC leaf|floc|{token}"
        concept_id = stable_key(source_key, "CV-FLOC")
        base = {
            "concept_id": concept_id,
            "canonical_concept_key": stable_key(token, "CONCEPT"),
            "vocabulary_owner": "IH06_OBSERVED_NODES",
            "target": "FLOC leaf",
            "namespace": "floc",
            "target_field": "header.functional_location",
            "concept_role": "observed_floc_node",
            "source": "IH06 observed node inventory",
            "source_version": "reference-layer-v1",
            "source_date": SOURCE_DATE,
            "evidence_type": "reference_evidence",
            "tier": "silver-high",
            "status": "active",
            "can_support_contractual_denominator": False,
            "can_support_proxy_denominator": False,
            "requires_mapping_from_observed_text": True,
            "label_generation_method": "reference_inventory_ingest",
            "evaluation_independence": "independent",
            "raw_values_emitted": False,
        }
        rows.append(base)
        working_rows.append({**base, "canonical_concept": token, "target_code": "", "code_group": ""})


def add_zeus_rows(rows: list[dict], working_rows: list[dict]) -> None:
    if not ZEUS_SCAFFOLD.exists():
        rows.append(pending_row("ZEUS_SCAFFOLD", "semantic_frame", "missing_source_file"))
        return
    df = pd.read_csv(ZEUS_SCAFFOLD)
    target_field_by_target = {
        "Symptom": "header.symptom.group+header.symptom.code",
        "Object Part": "findings[].object_part",
        "Damage": "findings[].damage",
        "Cause": "findings[].cause",
        "Activity": "findings[].activity",
        "FLOC leaf": "header.functional_location",
        "Activity Type": "header.activity_type",
    }
    namespace_by_target = {
        "Symptom": "catalog_s",
        "Object Part": "catalog_b",
        "Damage": "catalog_c",
        "Cause": "catalog_5",
        "Activity": "catalog_a",
        "FLOC leaf": "floc",
        "Activity Type": "mat",
    }
    for _, row in df.iterrows():
        target_hint = str(row.get("nearest_project_target_or_use", "") or "")
        target = target_hint.split("/")[0].strip() if "/" in target_hint else target_hint.strip()
        if target not in target_field_by_target:
            target = "semantic_frame"
        concept_text = row.get("zeus_category", "")
        concept_id = row.get("concept_id") or stable_key(concept_text, "CV-ZEUS")
        base = {
            "concept_id": concept_id,
            "canonical_concept_key": stable_key(concept_text, "CONCEPT"),
            "vocabulary_owner": "ZEUS_SCAFFOLD",
            "target": target,
            "namespace": namespace_by_target.get(target, "semantic"),
            "target_field": target_field_by_target.get(target, ""),
            "concept_role": "semantic_container",
            "source": "ZEUS semantic scaffold",
            "source_version": "reference-layer-v1",
            "source_date": SOURCE_DATE,
            "evidence_type": row.get("category_evidence_type", "reference_evidence"),
            "tier": row.get("tier", "silver-medium"),
            "status": row.get("status", "hypothesis"),
            "can_support_contractual_denominator": False,
            "can_support_proxy_denominator": False,
            "requires_mapping_from_observed_text": True,
            "label_generation_method": "semantic_scaffold_ingest",
            "evaluation_independence": "independent",
            "raw_values_emitted": False,
        }
        rows.append(base)
        working_rows.append({**base, "canonical_concept": concept_text, "target_code": "", "code_group": ""})


def add_malyi_schema_rows(rows: list[dict], working_rows: list[dict]) -> None:
    schema_items = [
        ("record_identifier", "record identity", "interface_support"),
        ("technician_text", "primary text signal", "text_signal_support"),
        ("system_code", "system or component code", "component_context_support"),
        ("system_name", "system or component name", "component_context_support"),
        ("maintenance_type", "maintenance class", "maintenance_type_support"),
    ]
    for item_key, concept_text, role in schema_items:
        concept_id = stable_key(f"MALYI|{item_key}", "CV-MALYI")
        base = {
            "concept_id": concept_id,
            "canonical_concept_key": stable_key(concept_text, "CONCEPT"),
            "vocabulary_owner": "MALYI_SCHEMA",
            "target": "method_support",
            "namespace": "external_schema",
            "target_field": "",
            "concept_role": role,
            "source": "Malyi maintenance log labelling framework",
            "source_version": "reference-layer-v1",
            "source_date": SOURCE_DATE,
            "evidence_type": "external_corroboration",
            "tier": "silver-high",
            "status": "schema_only",
            "can_support_contractual_denominator": False,
            "can_support_proxy_denominator": False,
            "requires_mapping_from_observed_text": False,
            "label_generation_method": "external_schema_ingest",
            "evaluation_independence": "independent",
            "raw_values_emitted": False,
        }
        rows.append(base)
        working_rows.append({**base, "canonical_concept": concept_text, "target_code": "", "code_group": ""})


def pending_row(owner: str, target: str, reason: str) -> dict:
    return {
        "concept_id": stable_key(f"{owner}|{target}|{reason}", "CV-PENDING"),
        "canonical_concept_key": "",
        "vocabulary_owner": owner,
        "target": target,
        "namespace": "",
        "target_field": "",
        "concept_role": "pending_source_capture",
        "source": owner,
        "source_version": "",
        "source_date": "",
        "evidence_type": "reference_evidence",
        "tier": "silver-medium",
        "status": "source_capture_pending",
        "can_support_contractual_denominator": False,
        "can_support_proxy_denominator": False,
        "requires_mapping_from_observed_text": True,
        "label_generation_method": "not_generated",
        "evaluation_independence": "unknown",
        "raw_values_emitted": False,
    }


def main() -> None:
    VOCAB_DIR.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []
    working_rows: list[dict] = []
    add_sap_mapping_rows(rows, working_rows)
    add_ih06_rows(rows, working_rows)
    add_zeus_rows(rows, working_rows)
    add_malyi_schema_rows(rows, working_rows)
    rows.append(pending_row("WMEP", "Cause/Symptom", "source_capture_pending"))
    rows.append(pending_row("NREL_GRD", "Damage/Object Part", "source_capture_pending"))

    fieldnames = [
        "concept_id",
        "canonical_concept_key",
        "vocabulary_owner",
        "target",
        "namespace",
        "target_field",
        "concept_role",
        "source",
        "source_version",
        "source_date",
        "evidence_type",
        "tier",
        "status",
        "can_support_contractual_denominator",
        "can_support_proxy_denominator",
        "requires_mapping_from_observed_text",
        "label_generation_method",
        "evaluation_independence",
        "raw_values_emitted",
    ]
    write_csv(VOCAB_DIR / "canonical_vocabulary_v1_sanitized.csv", rows, fieldnames)
    write_csv(
        VOCAB_DIR / "canonical_vocabulary_v1_working.csv",
        working_rows,
        fieldnames + ["canonical_concept", "target_code", "code_group"],
    )

    owner_counts = Counter(row["vocabulary_owner"] for row in rows)
    target_counts = Counter(row["target"] for row in rows)
    status_counts = Counter(row["status"] for row in rows)
    evidence_counts = Counter(row["evidence_type"] for row in rows)
    pending_sources = [
        row["vocabulary_owner"] for row in rows if row["status"] == "source_capture_pending"
    ]

    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "task": "F1c_canonical_vocabulary_materialization",
        "canonical_vocabulary_rows": len(rows),
        "working_vocabulary_rows": len(working_rows),
        "distinct_concept_ids": len({row["concept_id"] for row in rows}),
        "owner_counts": dict(owner_counts),
        "target_counts": dict(target_counts),
        "status_counts": dict(status_counts),
        "evidence_type_counts": dict(evidence_counts),
        "pending_sources": pending_sources,
        "concept_id_semantics": "concept_level_identifier_not_row_identifier",
        "sap_mapping_policy": "reference_evidence_valid_code_universe_not_validated_mapping",
        "observed_to_concept_mapping_performed": False,
        "raw_values_emitted": False,
        "outputs": {
            "sanitized_vocabulary_csv": "stint-1-evidence-ground-truth/phase_1_lexical/outputs/canonical_vocabulary/canonical_vocabulary_v1_sanitized.csv",
            "working_vocabulary_csv": "stint-1-evidence-ground-truth/phase_1_lexical/outputs/canonical_vocabulary/canonical_vocabulary_v1_working.csv",
            "summary_json": "stint-1-evidence-ground-truth/phase_1_lexical/outputs/f1c_canonical_vocabulary_summary.json",
            "memo": "stint-1-evidence-ground-truth/phase_1_lexical/outputs/f1c_canonical_vocabulary_memo.md",
        },
    }
    (OUTPUTS_DIR / "f1c_canonical_vocabulary_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    lines = [
        "# F1c - Canonical Vocabulary Materialization",
        "",
        "## Purpose",
        "",
        "This pass materializes the canonical vocabulary owners that F1d can use for domain grouping.",
        "",
        "It does not map observed terms to concepts and does not emit raw operational values.",
        "",
        "## Result",
        "",
        f"- Sanitized vocabulary rows: {summary['canonical_vocabulary_rows']}",
        f"- Working vocabulary rows: {summary['working_vocabulary_rows']}",
        f"- Distinct concept IDs: {summary['distinct_concept_ids']}",
        "- `concept_id` is a concept-level identifier, not a row identifier.",
        "",
        "## Vocabulary Owners",
        "",
    ]
    for owner, count in sorted(owner_counts.items()):
        lines.append(f"- {owner}: {count}")
    lines.extend(["", "## Status", ""])
    for status, count in sorted(status_counts.items()):
        lines.append(f"- {status}: {count}")
    lines.extend(
        [
            "",
            "## Pending Sources",
            "",
            "- WMEP remains `source_capture_pending`; no source rows were invented.",
            "- NREL GRD remains `source_capture_pending`; no source rows were invented.",
            "",
            "## Governance",
            "",
            "- SAP catalog rows are `reference_evidence`: they define valid target-code universe, not observed mappings.",
            "- Observed text to canonical concept links will be `expert_inference` unless independently corroborated.",
            "- `unresolved` remains a valid downstream outcome.",
        ]
    )
    (OUTPUTS_DIR / "f1c_canonical_vocabulary_memo.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )

    print(
        json.dumps(
            {
                "task": summary["task"],
                "canonical_vocabulary_rows": summary["canonical_vocabulary_rows"],
                "distinct_concept_ids": summary["distinct_concept_ids"],
                "pending_sources": pending_sources,
                "raw_values_emitted": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
