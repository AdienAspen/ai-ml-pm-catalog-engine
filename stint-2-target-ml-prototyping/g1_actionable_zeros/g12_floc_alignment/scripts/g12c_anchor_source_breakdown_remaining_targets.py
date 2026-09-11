from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path("/home/adien-i7-remote/workspace/fsa_bridge_ml_feasibility")
STINT2_ROOT = PROJECT_ROOT / "stint-2-target-ml-prototyping"
OUT = STINT2_ROOT / "g1_actionable_zeros" / "g12_floc_alignment" / "outputs"

STINT1 = PROJECT_ROOT / "stint-1-evidence-ground-truth"
CANONICAL_VOCAB = STINT1 / "phase_1_lexical/outputs/canonical_vocabulary/canonical_vocabulary_v1_working.csv"
B1 = STINT1 / "phase_4_path_b_xlsx/outputs/b1_silver_labels/b1_silver_labels_textual_residue_sanitized.csv"
B25 = STINT1 / "phase_4_path_b_xlsx/outputs/b25_grouping_refinement/b25_grouped_reanchored_evidence_sanitized.csv"
PATHA = STINT1 / "phase_3_path_a_faultcodes/outputs/f356_path_a_integrated_crosswalk_sanitized.csv"
PATHA_CONCEPTS = STINT1 / "phase_3_path_a_faultcodes/outputs/f355_path_a_crosswalk_v2_sanitized.csv"
SYM_REASON = STINT1 / "phase_5_symptom/outputs/f51_symptom_thread_resolution/t51b2x_reason_semantic_classification_normalized.csv"
SYM_OTHER = STINT1 / "phase_5_symptom/outputs/f51_symptom_thread_resolution/t51b24b_semantic_other_paths.csv"

TARGETS = ["Symptom", "Damage", "Cause", "Activity"]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def owner_to_anchor_source(owner: object, source: object = "", namespace: object = "") -> str:
    owner_norm = str(owner or "").strip().lower()
    source_norm = str(source or "").strip().lower()
    if owner_norm == "sap_mapping" or "sap mapping" in source_norm:
        return "sap_catalog"
    if "domain" in owner_norm or owner_norm == "zeus_scaffold":
        return "domain_vocabulary"
    if "structural" in owner_norm:
        return "structural_field"
    if owner_norm.startswith("converter_field") or owner_norm.startswith("external"):
        return "domain_vocabulary"
    return "unknown"


def fallback_anchor_source(concept_id: object, current_source: object) -> str:
    if pd.isna(current_source):
        current = ""
    else:
        current = str(current_source or "").strip()
    if current.lower() == "nan":
        current = ""
    if current and current != "unknown":
        return current
    concept = str(concept_id or "").strip()
    if concept.startswith("CV-EXT"):
        return "domain_vocabulary"
    if concept.startswith("CV-SAP"):
        return "sap_catalog"
    if concept.startswith("RL-"):
        return "domain_vocabulary"
    return "unknown"


def classify_sources(sources: set[str]) -> str:
    clean = {source for source in sources if source and source != "unknown"}
    if not clean:
        return "no_anchor_source_recorded"
    has_domain = "domain_vocabulary" in clean
    has_sap = "sap_catalog" in clean
    if has_domain and has_sap and clean <= {"domain_vocabulary", "sap_catalog"}:
        return "both"
    if has_domain and clean <= {"domain_vocabulary"}:
        return "domain_vocabulary_only"
    if has_sap and clean <= {"sap_catalog"}:
        return "sap_catalog_only"
    return "other_or_mixed"


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def concept_map() -> pd.DataFrame:
    vocab = read_csv(CANONICAL_VOCAB)
    vocab["anchor_source_derived"] = vocab.apply(
        lambda row: owner_to_anchor_source(row.get("vocabulary_owner"), row.get("source"), row.get("namespace")),
        axis=1,
    )
    return vocab[
        [
            "concept_id",
            "canonical_concept_key",
            "vocabulary_owner",
            "target",
            "target_code",
            "code_group",
            "anchor_source_derived",
        ]
    ].drop_duplicates()


def field_status(artifact: str, df: pd.DataFrame, target: str, path_bucket: str) -> dict[str, object]:
    if "anchor_source" not in df.columns:
        return {
            "target": target,
            "path_bucket": path_bucket,
            "source_artifact": artifact,
            "anchor_source_field_present": False,
            "anchor_source_non_null_rows": 0,
            "anchor_source_field_status": "missing",
        }
    non_null = int(df["anchor_source"].notna().sum())
    return {
        "target": target,
        "path_bucket": path_bucket,
        "source_artifact": artifact,
        "anchor_source_field_present": True,
        "anchor_source_non_null_rows": non_null,
        "anchor_source_field_status": "populated" if non_null else "present_but_null",
    }


def unit_breakdown_rows(units: pd.DataFrame) -> list[dict[str, object]]:
    rows = []
    if units.empty:
        return rows
    unit_classes = (
        units.groupby(["target", "path_bucket", "unit_key"])["anchor_source"]
        .apply(lambda values: classify_sources(set(values)))
        .reset_index(name="anchor_source_breakdown")
    )
    for (target, path_bucket), part in unit_classes.groupby(["target", "path_bucket"]):
        total = len(part)
        counts = part["anchor_source_breakdown"].value_counts().to_dict()
        for bucket in [
            "domain_vocabulary_only",
            "sap_catalog_only",
            "both",
            "no_anchor_source_recorded",
            "other_or_mixed",
        ]:
            count = int(counts.get(bucket, 0))
            rows.append(
                {
                    "target": target,
                    "path_bucket": path_bucket,
                    "anchor_source_breakdown": bucket,
                    "admitted_units": count,
                    "share_of_target_path_units": round(count / total * 100, 6) if total else 0,
                    "target_path_total_units": total,
                }
            )
    return rows


def build_records() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    cmap = concept_map()
    records = []
    concept_records = []
    status_rows = []

    b1 = read_csv(B1)
    status_rows.extend(
        field_status("b1_silver_labels_textual_residue_sanitized.csv", b1, target, "B1_RELATIONAL")
        for target in ["Activity", "Cause", "Damage"]
    )
    b1 = b1[(b1["target"].isin(["Activity", "Cause", "Damage"])) & (b1["status"].str.contains("converged", na=False))]
    b1 = b1.merge(cmap, on=["concept_id", "canonical_concept_key"], how="left", suffixes=("", "_vocab"))
    b1["anchor_source"] = b1.apply(
        lambda row: fallback_anchor_source(row.get("concept_id"), row.get("anchor_source_derived")),
        axis=1,
    )
    for row in b1.itertuples(index=False):
        records.append({"target": row.target, "path_bucket": "B1_RELATIONAL", "unit_key": row.physical_record_id, "anchor_source": row.anchor_source})
        concept_records.append(
            {
                "target": row.target,
                "path_bucket": "B1_RELATIONAL",
                "unit_key": row.physical_record_id,
                "canonical_concept_key": row.canonical_concept_key,
                "concept_id": row.concept_id,
                "target_code": getattr(row, "target_code", ""),
                "code_group": getattr(row, "code_group", ""),
                "vocabulary_owner": getattr(row, "vocabulary_owner_vocab", getattr(row, "vocabulary_owner", "")),
                "anchor_source": row.anchor_source,
            }
        )

    b25 = read_csv(B25)
    status_rows.extend(
        field_status("b25_grouped_reanchored_evidence_sanitized.csv", b25, target, "B2_WORKBOOKS")
        for target in ["Activity", "Cause", "Damage"]
    )
    b25 = b25[b25["target"].isin(["Activity", "Cause", "Damage"])].copy()
    b25 = b25.merge(cmap, on=["concept_id", "canonical_concept_key"], how="left", suffixes=("", "_vocab"))
    b25["anchor_source"] = b25.apply(
        lambda row: fallback_anchor_source(row.get("concept_id"), row.get("anchor_source_derived")),
        axis=1,
    )
    for row in b25.itertuples(index=False):
        records.append({"target": row.target, "path_bucket": "B2_WORKBOOKS", "unit_key": row.refined_event_key, "anchor_source": row.anchor_source})
        concept_records.append(
            {
                "target": row.target,
                "path_bucket": "B2_WORKBOOKS",
                "unit_key": row.refined_event_key,
                "canonical_concept_key": row.canonical_concept_key,
                "concept_id": row.concept_id,
                "target_code": getattr(row, "target_code", ""),
                "code_group": getattr(row, "code_group", ""),
                "vocabulary_owner": getattr(row, "vocabulary_owner_vocab", getattr(row, "vocabulary_owner", "")),
                "anchor_source": row.anchor_source,
            }
        )

    pa = read_csv(PATHA)
    pa = pa[pa["target"].isin(["Activity", "Cause", "Damage"])].copy()
    status_rows.extend(
        field_status("f356_path_a_integrated_crosswalk_sanitized.csv", pa[pa["target"].eq(target)], target, "PATH_A")
        for target in ["Activity", "Cause", "Damage"]
    )
    pac = read_csv(PATHA_CONCEPTS)
    pac = pac[
        (pac["target"].isin(["Cause", "Damage"]))
        & (pac["status"].isin(["candidate_high_requires_review", "candidate_medium_requires_review"]))
    ].copy()
    pac["anchor_source"] = pac["vocabulary_owner"].map(owner_to_anchor_source)
    pa_sources = pac.groupby(["target", "estimated_event_key"])["anchor_source"].apply(set).to_dict()
    pa_concepts = pac[
        [
            "target",
            "estimated_event_key",
            "candidate_concept_id",
            "candidate_concept_key",
            "vocabulary_owner",
            "anchor_source",
        ]
    ].drop_duplicates()
    for row in pa.itertuples(index=False):
        sources = pa_sources.get((row.target, row.estimated_event_key), set())
        if not sources:
            records.append({"target": row.target, "path_bucket": "PATH_A", "unit_key": row.estimated_event_key, "anchor_source": "unknown"})
        else:
            for source in sources:
                records.append({"target": row.target, "path_bucket": "PATH_A", "unit_key": row.estimated_event_key, "anchor_source": source})
    for row in pa_concepts.itertuples(index=False):
        concept_records.append(
            {
                "target": row.target,
                "path_bucket": "PATH_A",
                "unit_key": row.estimated_event_key,
                "canonical_concept_key": row.candidate_concept_key,
                "concept_id": row.candidate_concept_id,
                "target_code": "",
                "code_group": "",
                "vocabulary_owner": row.vocabulary_owner,
                "anchor_source": row.anchor_source,
            }
        )

    sym_reason = read_csv(SYM_REASON)
    status_rows.append(field_status("t51b2x_reason_semantic_classification_normalized.csv", sym_reason, "Symptom", "B1_RELATIONAL"))
    sym_reason = sym_reason[sym_reason["predicted_class"].eq("observed_condition")].copy()
    for idx, row in enumerate(sym_reason.itertuples(index=False)):
        # F6 admits RELATIONAL_REASON at row-level. Do not collapse repeated reason_hash values.
        records.append(
            {
                "target": "Symptom",
                "path_bucket": "B1_RELATIONAL",
                "unit_key": f"REL_REASON_ROW-{idx:06d}-{row.reason_hash}",
                "anchor_source": "unknown",
            }
        )

    sym_other = read_csv(SYM_OTHER)
    status_rows.append(field_status("t51b24b_semantic_other_paths.csv", sym_other, "Symptom", "PATH_A"))
    status_rows.append(field_status("t51b24b_semantic_other_paths.csv", sym_other, "Symptom", "B2_WORKBOOKS"))
    sym_other = sym_other[sym_other["predicted_class"].eq("observed_condition")].copy()
    path_map = {
        "PATH_A_NOTES": "PATH_A",
        "PATH_A_CONCERN_TABLE": "PATH_A",
        "B2_WORKBOOKS": "B2_WORKBOOKS",
    }
    for idx, row in enumerate(sym_other.itertuples(index=False)):
        # Other Symptom paths are also admitted as candidate text rows/hashes; preserve row-level units.
        records.append(
            {
                "target": "Symptom",
                "path_bucket": path_map.get(row.path_bucket, row.path_bucket),
                "unit_key": f"{row.path_bucket}_ROW-{idx:06d}-{row.record_hash}",
                "anchor_source": "unknown",
            }
        )

    return pd.DataFrame(records), pd.DataFrame(concept_records), pd.DataFrame(status_rows)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    records, concepts, status = build_records()

    unit_breakdown = pd.DataFrame(unit_breakdown_rows(records))
    unit_breakdown.to_csv(OUT / "g12c_anchor_source_unit_breakdown_sanitized.csv", index=False)

    if concepts.empty:
        concept_breakdown = pd.DataFrame(columns=["target", "path_bucket", "anchor_source", "distinct_high_band_concepts", "share_of_target_path_concepts"])
        top10 = pd.DataFrame()
    else:
        concept_unique = concepts.drop_duplicates(["target", "path_bucket", "canonical_concept_key", "anchor_source"])
        concept_breakdown = (
            concept_unique.groupby(["target", "path_bucket", "anchor_source"], dropna=False)["canonical_concept_key"]
            .nunique()
            .reset_index(name="distinct_high_band_concepts")
        )
        totals = concept_unique.groupby(["target", "path_bucket"])["canonical_concept_key"].nunique().reset_index(name="target_path_concepts")
        concept_breakdown = concept_breakdown.merge(totals, on=["target", "path_bucket"], how="left")
        concept_breakdown["share_of_target_path_concepts"] = (
            concept_breakdown["distinct_high_band_concepts"] / concept_breakdown["target_path_concepts"] * 100
        ).round(6)

        unit_totals = records.groupby("target")["unit_key"].nunique().to_dict()
        top_parts = []
        for target, target_df in concepts.groupby("target"):
            counts = (
                target_df.groupby(
                    ["canonical_concept_key", "anchor_source"],
                    dropna=False,
                )
                .agg(
                    unit_count=("unit_key", "nunique"),
                    concept_ids=("concept_id", lambda values: "|".join(sorted({str(value) for value in values if pd.notna(value)}))),
                    target_codes=("target_code", lambda values: "|".join(sorted({str(value) for value in values if pd.notna(value)}))),
                    code_groups=("code_group", lambda values: "|".join(sorted({str(value) for value in values if pd.notna(value)}))),
                    vocabulary_owners=("vocabulary_owner", lambda values: "|".join(sorted({str(value) for value in values if pd.notna(value)}))),
                )
                .reset_index()
                .sort_values(["unit_count", "canonical_concept_key"], ascending=[False, True])
                .head(10)
            )
            counts.insert(0, "target", target)
            total = unit_totals.get(target, 0)
            counts["share_of_target_admitted_units"] = (counts["unit_count"] / total * 100).round(6) if total else 0
            counts["gt_10pct_of_target_admitted_units"] = counts["share_of_target_admitted_units"] > 10
            top_parts.append(counts)
        top10 = pd.concat(top_parts, ignore_index=True) if top_parts else pd.DataFrame()

    concept_breakdown.to_csv(OUT / "g12c_anchor_source_concept_breakdown_sanitized.csv", index=False)
    top10.to_csv(OUT / "g12c_anchor_source_top10_concepts_sanitized.csv", index=False)
    status.to_csv(OUT / "g12c_anchor_source_field_population_sanitized.csv", index=False)

    unit_pivot = unit_breakdown.pivot_table(
        index=["target", "path_bucket", "target_path_total_units"],
        columns="anchor_source_breakdown",
        values="admitted_units",
        fill_value=0,
        aggfunc="sum",
    ).reset_index()
    unit_pivot.to_csv(OUT / "g12c_anchor_source_unit_breakdown_wide_sanitized.csv", index=False)

    summary = {
        "task": "G1.2c_anchor_source_breakdown_remaining_targets",
        "created_at_utc": utc_now(),
        "targets": TARGETS,
        "paths_normalized": ["B1_RELATIONAL", "PATH_A", "B2_WORKBOOKS"],
        "counting_only": True,
        "candidate_promotion_performed": False,
        "denominator_change_performed": False,
        "anchor_source_field_on_evidence_rows": "missing in inspected evidence artefacts; analytical source is derived from concept/vocabulary_owner where concept anchors exist, otherwise no_anchor_source_recorded.",
        "canonical_vocabulary_anchor_source_column_present": False,
        "outputs": [
            "g12c_anchor_source_unit_breakdown_sanitized.csv",
            "g12c_anchor_source_unit_breakdown_wide_sanitized.csv",
            "g12c_anchor_source_concept_breakdown_sanitized.csv",
            "g12c_anchor_source_top10_concepts_sanitized.csv",
            "g12c_anchor_source_field_population_sanitized.csv",
        ],
    }
    (OUT / "g12c_anchor_source_breakdown_summary_sanitized.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )

    memo = """# G1.2c Anchor Source Breakdown Memo

G1.2c profiles admitted proxy evidence for Symptom, Damage, Cause, and Activity across B1 relational, Path A, and B2 workbook paths.

The evidence artefacts inspected do not contain a literal `anchor_source` column. Where concept anchors exist, `anchor_source` is derived from the canonical concept/vocabulary owner (`SAP_MAPPING` -> `sap_catalog`; external/domain owners -> `domain_vocabulary`). Where the admitted units come from semantic-prototype outputs or note-only rows without concept anchors, the unit is reported as `no_anchor_source_recorded`.

Counting only: no promotion, no denominator change, no blind sampling.
"""
    (OUT / "g12c_anchor_source_breakdown_memo.md").write_text(memo, encoding="utf-8")


if __name__ == "__main__":
    main()
