from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]
STINT_ROOT = PROJECT_ROOT / "stint-1-evidence-ground-truth"
OUT_DIR = STINT_ROOT / "phase_6_denominators" / "outputs"

TARGETS = [
    "Symptom",
    "Object Part",
    "Damage",
    "Cause",
    "Activity",
    "FLOC leaf",
    "Activity Type / MAT",
]

PATH_A = STINT_ROOT / "phase_3_path_a_faultcodes" / "outputs"
F4 = STINT_ROOT / "phase_4_path_b_xlsx" / "outputs"
F5 = STINT_ROOT / "phase_5_symptom" / "outputs" / "f51_symptom_thread_resolution"


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str).fillna("")


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def as_bool(value: object) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def int_value(value: object) -> int:
    try:
        return int(float(str(value)))
    except Exception:
        return 0


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def make_row(
    *,
    target: str,
    denominator_type: str,
    path_bucket: str,
    source_artifact: str,
    count_unit: str,
    stratum: str,
    evidence_type: str,
    tier: str,
    status: str,
    candidate_units: int,
    admitted_units: int,
    inclusion_decision: str,
    blocker_or_condition: str,
    label_generation_method: str,
    evaluation_independence: str,
) -> dict:
    return {
        "target": target,
        "denominator_type": denominator_type,
        "path_bucket": path_bucket,
        "source_artifact": source_artifact,
        "count_unit": count_unit,
        "stratum": stratum,
        "evidence_type": evidence_type,
        "tier": tier,
        "status": status,
        "candidate_units": int(candidate_units),
        "admitted_denominator_units": int(admitted_units),
        "inclusion_decision": inclusion_decision,
        "blocker_or_condition": blocker_or_condition,
        "label_generation_method": label_generation_method,
        "evaluation_independence": evaluation_independence,
        "raw_operational_values_emitted": False,
    }


def add_zero_rows(rows: list[dict], existing: set[tuple[str, str, str]]) -> None:
    for target in TARGETS:
        for denominator_type in ["contractual", "proxy_poc"]:
            key = (target, denominator_type, "DECLARED_TARGET_TOTAL_NO_GLOBAL_AGGREGATION")
            if key in existing:
                continue
            rows.append(
                make_row(
                    target=target,
                    denominator_type=denominator_type,
                    path_bucket="DECLARED_TARGET_TOTAL_NO_GLOBAL_AGGREGATION",
                    source_artifact="F6 declaration",
                    count_unit="not_aggregated_across_paths",
                    stratum="not_applicable",
                    evidence_type="none",
                    tier="none",
                    status="declared_zero_or_no_admitted_units",
                    candidate_units=0,
                    admitted_units=0,
                    inclusion_decision="declared_no_global_denominator",
                    blocker_or_condition="Per-path denominators are authoritative; global aggregation is methodologically invalid.",
                    label_generation_method="none",
                    evaluation_independence="not_applicable",
                )
            )


def build_matrix() -> list[dict]:
    rows: list[dict] = []

    # Path A: integrated PDF/event evidence. Reconstructed expert evidence is admitted
    # to the proxy only, because the POC lacks an SME path to turn requires_review into
    # contractual ground truth.
    path_a_df = read_csv(PATH_A / "f356_path_a_integrated_crosswalk_sanitized.csv")
    if not path_a_df.empty:
        for target, group in path_a_df.groupby("target"):
            candidate_units = group["estimated_event_key"].nunique()
            evidence_types = ";".join(sorted(set(group["evidence_type"])))
            tiers = ";".join(sorted(set(group["tier"])))
            methods = ";".join(sorted(set(group["label_generation_method"])))
            independence = ";".join(sorted(set(group["evaluation_independence"])))
            rows.append(
                make_row(
                    target=target,
                    denominator_type="proxy_poc",
                    path_bucket="PATH_A_PDF_EVENTS",
                    source_artifact="f356_path_a_integrated_crosswalk_sanitized.csv",
                    count_unit="estimated_event_key_x_target",
                    stratum="event_structural",
                    evidence_type=evidence_types,
                    tier=tiers,
                    status="candidate_requires_target_review",
                    candidate_units=candidate_units,
                    admitted_units=candidate_units,
                    inclusion_decision="admitted_proxy_only",
                    blocker_or_condition="Admitted to proxy as reconstructed evidence with provenance; not contractual ground truth.",
                    label_generation_method=methods,
                    evaluation_independence=independence,
                )
            )

    # B1 deterministic structural harvest.
    b1_det = read_csv(F4 / "b1_deterministic_harvest" / "b1_deterministic_harvest_evidence_sanitized.csv")
    if not b1_det.empty:
        for target, group in b1_det.groupby("target"):
            units = group["physical_record_id"].nunique()
            contract_ok = group.apply(
                lambda row: row["evidence_type"] in {"real_observed_label", "validated_mapping"}
                and row["tier"] == "gold"
                and str(row["status"]).startswith("resolved"),
                axis=1,
            )
            contract_units = group[contract_ok]["physical_record_id"].nunique()
            evidence_types = ";".join(sorted(set(group["evidence_type"])))
            tiers = ";".join(sorted(set(group["tier"])))
            methods = ";".join(sorted(set(group["label_generation_method"])))
            independence = ";".join(sorted(set(group["evaluation_independence"])))
            status = ";".join(sorted(set(group["status"])))
            rows.append(
                make_row(
                    target=target,
                    denominator_type="contractual",
                    path_bucket="B1_RELATIONAL_STRUCTURED",
                    source_artifact="b1_deterministic_harvest_evidence_sanitized.csv",
                    count_unit="physical_record_id_x_target",
                    stratum="explicit_activity_type_or_structural_source",
                    evidence_type=evidence_types,
                    tier=tiers,
                    status=status,
                    candidate_units=units,
                    admitted_units=contract_units,
                    inclusion_decision="admitted" if contract_units else "not_admitted",
                    blocker_or_condition=(
                        "Direct observed gold label."
                        if contract_units
                        else "Structured signal requires mapping/alignment before denominator admission."
                    ),
                    label_generation_method=methods,
                    evaluation_independence=independence,
                )
            )
            rows.append(
                make_row(
                    target=target,
                    denominator_type="proxy_poc",
                    path_bucket="B1_RELATIONAL_STRUCTURED",
                    source_artifact="b1_deterministic_harvest_evidence_sanitized.csv",
                    count_unit="physical_record_id_x_target",
                    stratum="explicit_activity_type_or_structural_source",
                    evidence_type=evidence_types,
                    tier=tiers,
                    status=status,
                    candidate_units=units,
                    admitted_units=contract_units,
                    inclusion_decision="admitted" if contract_units else "not_admitted",
                    blocker_or_condition=(
                        "Contractual-quality labels also qualify for proxy evaluation."
                        if contract_units
                        else "Structured signal requires mapping/alignment before proxy denominator admission."
                    ),
                    label_generation_method=methods,
                    evaluation_independence=independence,
                )
            )

    # B1 textual residue: only convergent target-record evidence is admitted to the proxy.
    # Non-convergent rows remain candidate evidence, preserving the B1.2 distinction.
    b1_txt = read_csv(F4 / "b1_silver_labels" / "b1_silver_labels_textual_residue_sanitized.csv")
    if not b1_txt.empty:
        for target, group in b1_txt.groupby("target"):
            converged = group[group["status"].str.contains("converged", na=False)]
            admitted_units = converged["physical_record_id"].nunique()
            rows.append(
                make_row(
                    target=target,
                    denominator_type="proxy_poc",
                    path_bucket="B1_RELATIONAL_TEXTUAL",
                    source_artifact="b1_silver_labels_textual_residue_sanitized.csv",
                    count_unit="physical_record_id_x_target",
                    stratum="planned_reactive_as_declared_by_source_path",
                    evidence_type=";".join(sorted(set(group["evidence_type"]))),
                    tier=";".join(sorted(set(group["tier"]))),
                    status=";".join(sorted(set(group["status"]))),
                    candidate_units=group["physical_record_id"].nunique(),
                    admitted_units=admitted_units,
                    inclusion_decision="admitted_proxy_only_converged" if admitted_units else "not_admitted",
                    blocker_or_condition="Convergent textual evidence admitted to proxy only; non-convergent candidate evidence remains not admitted.",
                    label_generation_method=";".join(sorted(set(group["label_generation_method"]))),
                    evaluation_independence=";".join(sorted(set(group["evaluation_independence"]))),
                )
            )

    # B2 refined snapshot grouping: admitted to proxy only after event constitution;
    # still derived_from_rules and therefore not contractual. Symptom is an
    # explicit exception: F5.1a closed that thread as generic catalog noise.
    b2 = read_csv(F4 / "b25_grouping_refinement" / "b25_grouped_reanchored_evidence_sanitized.csv")
    f51a_b2_symptom = read_json(F5 / "f51a_b2_symptom_concepts_summary_sanitized.json")
    if not b2.empty:
        for target, group in b2.groupby("target"):
            candidate_units = group["refined_event_key"].nunique()
            if (
                target == "Symptom"
                and f51a_b2_symptom.get("thread_verdict") == "discard_thread_as_generic_noise"
            ):
                admitted_units = 0
                inclusion_decision = "not_admitted"
                blocker_or_condition = (
                    "Excluded from proxy admission after F5.1a: B2 snapshot Symptom-like anchors "
                    "were generic SAP catalog concepts, not observed-condition evidence."
                )
            else:
                admitted_units = candidate_units
                inclusion_decision = "admitted_proxy_only"
                blocker_or_condition = (
                    "Admitted to proxy after event constitution; grouping simulates SyncHub behavior "
                    "and remains non-contractual."
                )
            rows.append(
                make_row(
                    target=target,
                    denominator_type="proxy_poc",
                    path_bucket="B2_WORKBOOK_SNAPSHOTS",
                    source_artifact="b25_grouped_reanchored_evidence_sanitized.csv",
                    count_unit="refined_event_key_x_target",
                    stratum="snapshot_event_constituted",
                    evidence_type=";".join(sorted(set(group["evidence_type"]))),
                    tier=";".join(sorted(set(group["tier"]))),
                    status=";".join(sorted(set(group["status"]))),
                    candidate_units=candidate_units,
                    admitted_units=admitted_units,
                    inclusion_decision=inclusion_decision,
                    blocker_or_condition=blocker_or_condition,
                    label_generation_method=";".join(sorted(set(group["label_generation_method"]))),
                    evaluation_independence=";".join(sorted(set(group["evaluation_independence"]))),
                )
            )

    # F5 Symptom final verdict: observed-condition candidates are admitted to the proxy
    # by path, not aggregated, and never as ground truth.
    symptom_paths = read_csv(F5 / "t51b25_symptom_final_path_verdict_sanitized.csv")
    if not symptom_paths.empty:
        for _, row in symptom_paths.iterrows():
            candidate = int_value(row.get("semantic_observed_condition_rows"))
            rows.append(
                make_row(
                    target="Symptom",
                    denominator_type="proxy_poc",
                    path_bucket=str(row.get("path_bucket")),
                    source_artifact="t51b25_symptom_final_path_verdict_sanitized.csv",
                    count_unit="candidate_text_row_or_hash_x_target",
                    stratum="path_specific_do_not_mix",
                    evidence_type="expert_inference",
                    tier="silver-medium",
                    status="candidate_signal_present_not_ground_truth",
                    candidate_units=candidate,
                    admitted_units=candidate,
                    inclusion_decision="admitted_proxy_only",
                    blocker_or_condition="F5.1 establishes proxy candidate signal with provenance; not contractual ground truth.",
                    label_generation_method=str(row.get("semantic_method")),
                    evaluation_independence="derived_from_rules",
                )
            )

    # F5.1c lexical survivors: vocabulary support only, not record-level evidence.
    f51c = read_json(F5 / "f51c_symptom_lexicon_survival_summary_sanitized.json")
    if f51c:
        rows.append(
            make_row(
                target="Symptom",
                denominator_type="proxy_poc",
                path_bucket="LEXICAL_LAYER_V2_HIGH_BAND",
                source_artifact="f51c_symptom_lexicon_survival_summary_sanitized.json",
                count_unit="distinct_consolidated_term_key",
                stratum="lexical_support_not_record_evidence",
                evidence_type="expert_inference",
                tier="silver-medium",
                status="vocabulary_support_only",
                candidate_units=int_value(f51c.get("survived_high_band_as_symptom_distinct_term_keys")),
                admitted_units=0,
                inclusion_decision="not_admitted",
                blocker_or_condition="Lexicon terms are vocabulary support, not record-level denominator evidence.",
                label_generation_method="semantic_embedding_lexical_grouping_v2",
                evaluation_independence="derived_from_rules",
            )
        )

    return rows


def build_target_summary(rows: list[dict]) -> list[dict]:
    summary: list[dict] = []
    for target in TARGETS:
        target_rows = [row for row in rows if row["target"] == target]
        contractual_admitted_by_path = {
            row["path_bucket"]: row["admitted_denominator_units"]
            for row in target_rows
            if row["denominator_type"] == "contractual"
            and row["admitted_denominator_units"] > 0
            and row["path_bucket"] != "DECLARED_TARGET_TOTAL_NO_GLOBAL_AGGREGATION"
        }
        contractual_admitted_diagnostic_sum = sum(contractual_admitted_by_path.values())
        proxy_admitted_by_path = {
            row["path_bucket"]: row["admitted_denominator_units"]
            for row in target_rows
            if row["denominator_type"] == "proxy_poc"
            and row["admitted_denominator_units"] > 0
            and row["path_bucket"] != "DECLARED_TARGET_TOTAL_NO_GLOBAL_AGGREGATION"
        }
        proxy_admitted_diagnostic_sum = sum(proxy_admitted_by_path.values())
        proxy_candidates_by_path = {
            row["path_bucket"]: row["candidate_units"]
            for row in target_rows
            if row["denominator_type"] == "proxy_poc"
            and row["candidate_units"] > 0
            and row["path_bucket"] != "DECLARED_TARGET_TOTAL_NO_GLOBAL_AGGREGATION"
        }
        proxy_candidate_diagnostic_sum = sum(proxy_candidates_by_path.values())
        if target == "Activity Type / MAT":
            method = "deterministic_structured_source_label"
            status = "contractual_denominator_available_for_b1_only"
        elif target == "Symptom":
            method = "proxy_candidate_signal_requires_review_or_blind_annotation"
            status = (
                "proxy_denominator_available_poc_only_not_ground_truth"
                if proxy_admitted_diagnostic_sum
                else "proxy_candidate_not_ground_truth"
            )
        elif target == "FLOC leaf":
            method = "deterministic_join_then_alignment"
            status = "candidate_requires_alignment_to_valid_destination"
        else:
            method = "weak_supervision_or_hybrid_requires_review"
            status = (
                "proxy_denominator_available_poc_only_requires_review"
                if proxy_admitted_diagnostic_sum
                else "candidate_evidence_present_not_denominator_ready"
            )
        summary.append(
            {
                "target": target,
                "contractual_denominator_units_admitted_by_path_not_aggregated": ";".join(
                    f"{path}:{count}" for path, count in sorted(contractual_admitted_by_path.items())
                ),
                "contractual_denominator_units_admitted_diagnostic_sum_do_not_use_as_denominator": int(
                    contractual_admitted_diagnostic_sum
                ),
                "proxy_denominator_units_admitted_by_path_not_aggregated": ";".join(
                    f"{path}:{count}" for path, count in sorted(proxy_admitted_by_path.items())
                ),
                "proxy_denominator_units_admitted_diagnostic_sum_do_not_use_as_denominator": int(
                    proxy_admitted_diagnostic_sum
                ),
                "proxy_candidate_units_by_path_not_aggregated": ";".join(
                    f"{path}:{count}" for path, count in sorted(proxy_candidates_by_path.items())
                ),
                "proxy_candidate_units_diagnostic_sum_do_not_use_as_denominator": int(proxy_candidate_diagnostic_sum),
                "declared_route": method,
                "target_status": status,
                "global_aggregation_allowed": False,
                "raw_operational_values_emitted": False,
            }
        )
    return summary


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    matrix_rows = build_matrix()

    # Declare missing target/denominator combinations explicitly without aggregating paths.
    existing = {
        (row["target"], row["denominator_type"], row["path_bucket"])
        for row in matrix_rows
    }
    add_zero_rows(matrix_rows, existing)

    fields = [
        "target",
        "denominator_type",
        "path_bucket",
        "source_artifact",
        "count_unit",
        "stratum",
        "evidence_type",
        "tier",
        "status",
        "candidate_units",
        "admitted_denominator_units",
        "inclusion_decision",
        "blocker_or_condition",
        "label_generation_method",
        "evaluation_independence",
        "raw_operational_values_emitted",
    ]
    matrix_rows = sorted(
        matrix_rows,
        key=lambda row: (row["target"], row["denominator_type"], row["path_bucket"], row["source_artifact"]),
    )
    write_csv(OUT_DIR / "f6_evidence_denominator_matrix_sanitized.csv", matrix_rows, fields)

    summary_rows = build_target_summary(matrix_rows)
    write_csv(
        OUT_DIR / "f6_target_denominator_summary_sanitized.csv",
        summary_rows,
        [
            "target",
            "contractual_denominator_units_admitted_by_path_not_aggregated",
            "contractual_denominator_units_admitted_diagnostic_sum_do_not_use_as_denominator",
            "proxy_denominator_units_admitted_by_path_not_aggregated",
            "proxy_denominator_units_admitted_diagnostic_sum_do_not_use_as_denominator",
            "proxy_candidate_units_by_path_not_aggregated",
            "proxy_candidate_units_diagnostic_sum_do_not_use_as_denominator",
            "declared_route",
            "target_status",
            "global_aggregation_allowed",
            "raw_operational_values_emitted",
        ],
    )

    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "pass_id": "F6",
        "task_type": "denominator_consolidation",
        "contractual_denominator_rule": {
            "evidence_type": ["real_observed_label", "validated_mapping"],
            "tier": "gold",
            "status": "resolved",
        },
        "proxy_denominator_rule": "qualified silver/expert_inference with complete provenance; requires anti-circularity controls",
        "counting_units_by_path": {
            "PATH_A_PDF_EVENTS": "estimated_event_key_x_target",
            "B1_RELATIONAL_STRUCTURED": "physical_record_id_x_target",
            "B1_RELATIONAL_TEXTUAL": "physical_record_id_x_target",
            "B2_WORKBOOK_SNAPSHOTS": "refined_event_key_x_target",
            "Symptom F5 path verdict": "candidate_text_row_or_hash_x_target, proxy only",
        },
        "contractual_denominator_admitted_by_target": {
            row["target"]: {
                "by_path_not_aggregated": row["contractual_denominator_units_admitted_by_path_not_aggregated"],
                "diagnostic_sum_do_not_use_as_denominator": row[
                    "contractual_denominator_units_admitted_diagnostic_sum_do_not_use_as_denominator"
                ],
            }
            for row in summary_rows
        },
        "proxy_denominator_admitted_by_target": {
            row["target"]: {
                "by_path_not_aggregated": row["proxy_denominator_units_admitted_by_path_not_aggregated"],
                "diagnostic_sum_do_not_use_as_denominator": row[
                    "proxy_denominator_units_admitted_diagnostic_sum_do_not_use_as_denominator"
                ],
            }
            for row in summary_rows
        },
        "proxy_candidate_units_before_review_by_target": {
            row["target"]: {
                "by_path_not_aggregated": row["proxy_candidate_units_by_path_not_aggregated"],
                "diagnostic_sum_do_not_use_as_denominator": row[
                    "proxy_candidate_units_diagnostic_sum_do_not_use_as_denominator"
                ],
            }
            for row in summary_rows
        },
        "measurement_ready_targets_contractual": [
            row["target"]
            for row in summary_rows
            if row["contractual_denominator_units_admitted_diagnostic_sum_do_not_use_as_denominator"] > 0
        ],
        "measurement_ready_targets_proxy_admitted": [
            row["target"]
            for row in summary_rows
            if row["proxy_denominator_units_admitted_diagnostic_sum_do_not_use_as_denominator"] > 0
        ],
        "mandatory_scope_statements": [
            "Grouping simulates SyncHub behavior; it is not an ML workstream deliverable.",
            "Every POC metric must be measured against explicitly labeled proxy evaluation sets, never as verified production accuracy.",
            "No global denominator is valid across Path A, B1, and B2.",
            "FLOC leaf is an explicit zero: internal joins exist, but no SAP/FLOC leaf alignment evidence has been produced yet.",
            "B2 snapshot Symptom candidates are retained diagnostically but excluded from proxy admission after F5.1a classified the thread as generic catalog noise.",
        ],
        "explicit_zero_targets": {
            "FLOC leaf": (
                "B1 structural joins provide candidate routeability, but FLOC leaf has no admitted contractual "
                "or proxy denominator until SAP/FLOC leaf alignment evidence is produced."
            )
        },
        "explicit_proxy_exclusions": {
            "Symptom / B2_WORKBOOK_SNAPSHOTS": (
                "365 candidate event units excluded from proxy admission; they are the F5.1a generic-noise thread, "
                "not the later B2 semantic observed-condition signal."
            )
        },
        "raw_operational_values_emitted": False,
    }
    (OUT_DIR / "f6_denominator_consolidation_summary_sanitized.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    memo_lines = [
        "# F6 — Evidence Denominator Consolidation",
        "",
        "## Nature",
        "",
        "F6 does not generate new evidence. It consolidates the denominator status of evidence already produced by F3, F4 and F5.",
        "",
        "## Counting Rule",
        "",
        "- Path A: `estimated_event_key × target`",
        "- B1 structured/textual: `physical_record_id × target`",
        "- B2 snapshots: `refined_event_key × target`",
        "- Evidence rows are not denominators.",
        "- Path A, B1 and B2 are not globally aggregated.",
        "",
        "## Contractual Denominator",
        "",
        "A row is admitted only when all conditions hold: `evidence_type` in `real_observed_label` or `validated_mapping`, `tier = gold`, and `status = resolved`.",
        "",
        "Current result: only `Activity Type / MAT` in B1 has admitted contractual units. All other targets are declared zero for the contractual denominator.",
        "",
        "## Proxy POC Denominator",
        "",
        "The proxy denominator is declared separately from the contractual denominator. In this corrected F6 pass, qualified reconstructed evidence is admitted to the proxy even when its terminal POC status is `requires_review`.",
        "",
        "Everything derived from rules or embeddings remains non-contractual and must retain provenance and anti-circularity controls. `requires_review` blocks contractual use, but it does not automatically block proxy admission in a POC without SME closure.",
        "",
        "## Target Summary",
        "",
        "| Target | Contractual admitted by path | Proxy admitted by path | Proxy candidates by path | Status |",
        "|---|---|---|---|---|",
    ]
    for row in summary_rows:
        memo_lines.append(
            f"| {row['target']} | "
            f"{row['contractual_denominator_units_admitted_by_path_not_aggregated'] or '0'} | "
            f"{row['proxy_denominator_units_admitted_by_path_not_aggregated'] or '0'} | "
            f"{row['proxy_candidate_units_by_path_not_aggregated'] or '0'} | "
            f"{row['target_status']} |"
        )
    memo_lines.extend(
        [
            "",
            "## Scope Statements",
            "",
            "- Grouping simulates the upstream event constitution role that would belong to SyncHub in production. It is used here only to define auditable POC event units.",
            "- POC metrics must never be presented as verified production accuracy.",
            "- The contractual 95% accuracy requirement cannot be evaluated from the current reconstructed evidence layer except where a contractual denominator exists.",
            "- FLOC leaf is an explicit zero, not a silent miss: joins exist internally, but no SAP/FLOC leaf alignment evidence has been produced. This carries to STINT_2.",
            "- Symptom `B2_WORKBOOK_SNAPSHOTS` remains a diagnostic candidate only. Its 365 event units are excluded from proxy admission because F5.1a discarded that thread as generic catalog noise.",
            "- Raw operational values emitted: `false`.",
        ]
    )
    (OUT_DIR / "f6_denominator_consolidation_memo.md").write_text(
        "\n".join(memo_lines) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
