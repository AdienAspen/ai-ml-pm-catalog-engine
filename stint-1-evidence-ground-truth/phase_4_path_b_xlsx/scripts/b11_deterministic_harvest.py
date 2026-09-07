"""B1.1 deterministic harvest for CONTRACTOR_PATH_001.

This pass harvests structural evidence from the relational API-dump family.
It does not perform ML, text classification, SAP catalog mapping, or candidate
crosswalk scoring.
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]
STINT_ROOT = PROJECT_ROOT / "stint-1-evidence-ground-truth"
PHASE_DIR = STINT_ROOT / "phase_4_path_b_xlsx"
OUTPUT_DIR = PHASE_DIR / "outputs" / "b1_deterministic_harvest"
INTERNAL_MANIFEST = (
    PROJECT_ROOT
    / "reports"
    / "internal"
    / "f40b_contractor_path_001_relational_model"
    / "f40b_contractor_path_001_entity_manifest_internal.csv"
)
RELATIONSHIP_RATES = (
    PHASE_DIR
    / "outputs"
    / "f40b_contractor_path_001_relational_model"
    / "f40b_contractor_path_001_relationship_match_rates_sanitized.csv"
)

CONTRACTOR_PATH = "CONTRACTOR_PATH_001"
SOURCE_FAMILY = "SOURCE_FAMILY_CONTRACTOR_PATH_001_API_DUMP"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_hash(value: object, length: int = 16) -> str:
    raw = "" if value is None or pd.isna(value) else str(value)
    return hashlib.sha256(raw.encode("utf-8", errors="ignore")).hexdigest()[:length]


def prefixed_hash(value: object, prefix: str, length: int = 12) -> str:
    return f"{prefix}-{stable_hash(value, length)}"


def as_text(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    text = str(value).strip()
    if text.endswith(".0") and text[:-2].isdigit():
        return text[:-2]
    return text


def load_json_records(path: Path) -> list[dict[str, object]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, Mapping)]
    if isinstance(payload, Mapping):
        for key in ["data", "items", "value", "records", "results"]:
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, Mapping)]
        list_values = [value for value in payload.values() if isinstance(value, list)]
        if len(list_values) == 1:
            return [item for item in list_values[0] if isinstance(item, Mapping)]
    return []


def entity_paths() -> dict[str, Path]:
    manifest = pd.read_csv(INTERNAL_MANIFEST)
    return {
        str(row.entity_label): Path(str(row.json_path))
        for row in manifest.itertuples(index=False)
        if str(row.json_path)
    }


def physical_record_id(entity: str, record: Mapping[str, object], fallback_index: int) -> str:
    record_key = as_text(record.get("id")) or as_text(record.get("orderId")) or str(fallback_index)
    return prefixed_hash(f"{CONTRACTOR_PATH}|{entity}|{record_key}", "PHY", 16)


def site_key(record: Mapping[str, object]) -> str:
    value = as_text(record.get("siteId"))
    return prefixed_hash(value, "SITE", 10) if value else "SITE-unknown"


def activity_type_harvest(service_orders: list[dict[str, object]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for idx, record in enumerate(service_orders):
        value = as_text(record.get("activityType"))
        if not value:
            continue
        phy_id = physical_record_id("api_service_v1_service-orders", record, idx)
        rows.append(
            {
                "record_id": prefixed_hash(f"{phy_id}|Activity Type / MAT|activityType", "REC", 16),
                "physical_record_id": phy_id,
                "target": "Activity Type / MAT",
                "evidence_type": "real_observed_label",
                "tier": "gold",
                "status": "resolved_observed_source_label",
                "source_path": SOURCE_FAMILY,
                "source_text_field": "activityType",
                "stratum": "explicit_activity_type",
                "site_key": site_key(record),
                "contractor_path": CONTRACTOR_PATH,
                "concept_id": prefixed_hash(value.lower(), "MAT-SRC", 12),
                "confidence": "observed_field",
                "label_generation_method": "observed_structured_field:activityType",
                "evaluation_independence": "independent",
                "can_support_contractual_denominator": True,
                "can_support_proxy_denominator": True,
                "notes": "Direct source label in CONTRACTOR_PATH_001 API family. Not an ML input.",
                "raw_operational_values_emitted": False,
            }
        )
    return rows


def flatten_consumption_signals(consumption_records: list[dict[str, object]]) -> tuple[list[dict[str, object]], dict[str, int]]:
    rows: list[dict[str, object]] = []
    counters: Counter[str] = Counter()
    for idx, record in enumerate(consumption_records):
        order_id = as_text(record.get("orderId")) or as_text(record.get("_serviceOrderId"))
        phy_id = prefixed_hash(f"{CONTRACTOR_PATH}|api_service_v1_service-orders_consumption|{order_id or idx}", "PHY", 16)
        nested_items = record.get("items") if isinstance(record.get("items"), list) else []
        nested_resources = record.get("resources") if isinstance(record.get("resources"), list) else []
        counters["records"] += 1
        counters["records_with_items"] += int(bool(nested_items))
        counters["records_with_resources"] += int(bool(nested_resources))
        counters["item_rows"] += len(nested_items)
        counters["resource_rows"] += len(nested_resources)

        for item_index, item in enumerate(nested_items):
            if not isinstance(item, Mapping):
                continue
            item_id = as_text(item.get("itemId"))
            item_description = as_text(item.get("itemDescription"))
            quantity_present = as_text(item.get("quantity")) != ""
            if not item_id and not item_description:
                continue
            material_key_seed = item_id or item_description
            rows.append(
                {
                    "record_id": prefixed_hash(f"{phy_id}|Object Part|item|{item_index}|{material_key_seed}", "REC", 16),
                    "physical_record_id": phy_id,
                    "target": "Object Part",
                    "evidence_type": "real_observed_label",
                    "tier": "silver-high",
                    "status": "structured_source_material_observed_mapping_required",
                    "source_path": SOURCE_FAMILY,
                    "source_text_field": "items[]",
                    "stratum": "explicit_activity_type",
                    "site_key": "SITE-unresolved_from_consumption_record",
                    "contractor_path": CONTRACTOR_PATH,
                    "concept_id": prefixed_hash(material_key_seed.lower(), "MATITEM-SRC", 12),
                    "confidence": "structured_source_code_present" if item_id else "structured_source_description_present",
                    "label_generation_method": "observed_nested_consumption_item",
                    "evaluation_independence": "independent",
                    "can_support_contractual_denominator": False,
                    "can_support_proxy_denominator": False,
                    "notes": "Observed consumption item/resource signal. SAP Catalog B mapping is not established in this pass.",
                    "raw_operational_values_emitted": False,
                    "order_key": prefixed_hash(order_id, "ORDER", 12) if order_id else "ORDER-missing",
                    "item_id_present": bool(item_id),
                    "item_description_present": bool(item_description),
                    "quantity_present": quantity_present,
                }
            )
    return rows, dict(counters)


def floc_join_harvest(
    service_orders: list[dict[str, object]],
    assets: list[dict[str, object]],
    sites: list[dict[str, object]],
) -> tuple[list[dict[str, object]], dict[str, object]]:
    asset_ids = {as_text(record.get("id")) for record in assets if as_text(record.get("id"))}
    site_ids = {as_text(record.get("id")) for record in sites if as_text(record.get("id"))}
    rows: list[dict[str, object]] = []
    order_count = 0
    asset_match = 0
    site_match = 0
    for idx, record in enumerate(service_orders):
        order_count += 1
        asset_id = as_text(record.get("assetId"))
        site_id = as_text(record.get("siteId"))
        has_asset_match = asset_id in asset_ids
        has_site_match = site_id in site_ids
        asset_match += int(has_asset_match)
        site_match += int(has_site_match)
        if not (asset_id or site_id):
            continue
        phy_id = physical_record_id("api_service_v1_service-orders", record, idx)
        rows.append(
            {
                "record_id": prefixed_hash(f"{phy_id}|FLOC leaf|asset-site", "REC", 16),
                "physical_record_id": phy_id,
                "target": "FLOC leaf",
                "evidence_type": "real_observed_label",
                "tier": "silver-high",
                "status": "internal_asset_site_join_resolved_external_floc_alignment_required",
                "source_path": SOURCE_FAMILY,
                "source_text_field": "assetId;siteId",
                "stratum": "explicit_activity_type",
                "site_key": prefixed_hash(site_id, "SITE", 10) if site_id else "SITE-missing",
                "contractor_path": CONTRACTOR_PATH,
                "concept_id": prefixed_hash(f"{asset_id}|{site_id}", "FLOC-SRC", 12),
                "confidence": "asset_and_site_joined" if has_asset_match and has_site_match else "partial_internal_join",
                "label_generation_method": "observed_internal_api_join",
                "evaluation_independence": "independent",
                "can_support_contractual_denominator": False,
                "can_support_proxy_denominator": False,
                "notes": "Internal API graph supports route context. SAP/IH06 FLOC leaf alignment is required before target promotion.",
                "raw_operational_values_emitted": False,
                "asset_join_resolved": has_asset_match,
                "site_join_resolved": has_site_match,
            }
        )
    summary = {
        "service_order_records": order_count,
        "asset_join_match_rate": round(asset_match / order_count, 6) if order_count else 0,
        "site_join_match_rate": round(site_match / order_count, 6) if order_count else 0,
    }
    return rows, summary


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def summarize_targets(evidence_rows: list[dict[str, object]]) -> pd.DataFrame:
    df = pd.DataFrame(evidence_rows)
    if df.empty:
        return pd.DataFrame()
    return (
        df.groupby(["target", "evidence_type", "tier", "status"], dropna=False)
        .agg(
            evidence_rows=("record_id", "size"),
            physical_records=("physical_record_id", "nunique"),
            can_support_contractual_denominator=("can_support_contractual_denominator", "sum"),
            can_support_proxy_denominator=("can_support_proxy_denominator", "sum"),
        )
        .reset_index()
        .sort_values(["target", "status"])
    )


def build_memo(
    summary: dict[str, object],
    target_summary: pd.DataFrame,
    relationship_rates: pd.DataFrame,
) -> str:
    target_rows = [
        "| "
        + " | ".join(
            [
                str(row.target),
                str(row.status),
                str(row.evidence_rows),
                str(row.physical_records),
                str(row.can_support_contractual_denominator),
            ]
        )
        + " |"
        for row in target_summary.itertuples(index=False)
    ]
    relation_rows = [
        "| "
        + " | ".join(
            [
                str(row.src_entity),
                str(row.src_field),
                str(row.tgt_entity),
                str(row.tgt_field),
                f"{float(row.match_rate_pct):.2f}%",
            ]
        )
        + " |"
        for row in relationship_rates.itertuples(index=False)
    ]
    return "\n".join(
        [
            "# B1.1 Deterministic Harvest",
            "",
            "## Scope",
            "",
            "This pass harvests deterministic structural evidence for `CONTRACTOR_PATH_001`. It does not run ML, infer text labels, or map source material codes to SAP catalogs.",
            "",
            "## Summary",
            "",
            f"- Service-order records: `{summary['service_order_records']}`",
            f"- Activity Type / MAT observed labels: `{summary['activity_type_rows']}`",
            f"- Consumption records: `{summary['consumption_records']}`",
            f"- Consumption item rows with usable source signal: `{summary['consumption_item_signal_rows']}`",
            f"- Orders with structured consumption records: `{summary['orders_with_consumption_records']}`",
            f"- FLOC route context rows: `{summary['floc_route_context_rows']}`",
            f"- Asset join match rate: `{summary['asset_join_match_rate']:.2%}`",
            f"- Site join match rate: `{summary['site_join_match_rate']:.2%}`",
            f"- Contractual denominator rows supported now: `{summary['contractual_denominator_rows_supported_now']}`",
            "",
            "## Target Summary",
            "",
            "| target | status | evidence_rows | physical_records | contractual_rows_now |",
            "| --- | --- | ---: | ---: | ---: |",
            *target_rows,
            "",
            "## Relationship Rates Used",
            "",
            "| source_entity | source_field | target_entity | target_field | match_rate |",
            "| --- | --- | --- | --- | ---: |",
            *relation_rows,
            "",
            "## Interpretation",
            "",
            "`activityType` is harvested as a direct observed source label for Activity Type / MAT and is outside the ML scope for this branch.",
            "",
            "`consumption` provides structured Object Part signal, but this pass does not establish material-to-SAP Catalog B equivalence. Those rows remain mapping-required and do not support denominator promotion yet.",
            "",
            "FLOC route context closes strongly inside the API graph, but SAP/IH06 FLOC leaf alignment remains required before promotion to a target label.",
            "",
            "raw_operational_values_emitted: false",
            "",
        ]
    )


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    paths = entity_paths()
    service_orders = load_json_records(paths["api_service_v1_service-orders"])
    consumption = load_json_records(paths["api_service_v1_service-orders_consumption"])
    assets = load_json_records(paths["api_common_v1_assets"])
    sites = load_json_records(paths["api_common_v1_sites"])

    activity_rows = activity_type_harvest(service_orders)
    object_rows, consumption_summary = flatten_consumption_signals(consumption)
    floc_rows, floc_summary = floc_join_harvest(service_orders, assets, sites)
    evidence_rows = activity_rows + object_rows + floc_rows

    base_fields = [
        "record_id",
        "physical_record_id",
        "target",
        "evidence_type",
        "tier",
        "status",
        "source_path",
        "source_text_field",
        "stratum",
        "site_key",
        "contractor_path",
        "concept_id",
        "confidence",
        "label_generation_method",
        "evaluation_independence",
        "can_support_contractual_denominator",
        "can_support_proxy_denominator",
        "notes",
        "raw_operational_values_emitted",
    ]
    write_csv(OUTPUT_DIR / "b1_deterministic_harvest_evidence_sanitized.csv", evidence_rows, base_fields)

    target_summary = summarize_targets(evidence_rows)
    target_summary["raw_operational_values_emitted"] = False
    target_summary.to_csv(OUTPUT_DIR / "b1_deterministic_harvest_by_target_sanitized.csv", index=False)

    relationship_rates = pd.read_csv(RELATIONSHIP_RATES)
    relationship_rates.to_csv(OUTPUT_DIR / "b1_deterministic_harvest_relationship_rates_sanitized.csv", index=False)

    activity_df = pd.DataFrame(activity_rows)
    mat_distribution = (
        activity_df.groupby("concept_id")
        .agg(rows=("record_id", "size"), physical_records=("physical_record_id", "nunique"))
        .reset_index()
        .sort_values(["rows", "concept_id"], ascending=[False, True])
    )
    mat_distribution["raw_operational_values_emitted"] = False
    mat_distribution.to_csv(OUTPUT_DIR / "b1_activity_type_distribution_sanitized.csv", index=False)

    object_df = pd.DataFrame(object_rows)
    object_summary = {
        "consumption_records": int(consumption_summary.get("records", 0)),
        "consumption_records_with_items": int(consumption_summary.get("records_with_items", 0)),
        "consumption_records_with_resources": int(consumption_summary.get("records_with_resources", 0)),
        "item_rows": int(consumption_summary.get("item_rows", 0)),
        "resource_rows": int(consumption_summary.get("resource_rows", 0)),
        "object_part_signal_rows": int(object_df.shape[0]) if not object_df.empty else 0,
        "distinct_source_item_concepts": int(object_df["concept_id"].nunique()) if not object_df.empty else 0,
        "raw_operational_values_emitted": False,
    }
    (OUTPUT_DIR / "b1_consumption_object_part_summary_sanitized.json").write_text(
        json.dumps(object_summary, indent=2),
        encoding="utf-8",
    )

    summary = {
        "created_at_utc": utc_now(),
        "pass_id": "B1.1",
        "contractor_path": CONTRACTOR_PATH,
        "task_type": "deterministic_structural_harvest",
        "service_order_records": len(service_orders),
        "activity_type_rows": len(activity_rows),
        "activity_type_distinct_source_labels": int(activity_df["concept_id"].nunique()) if not activity_df.empty else 0,
        "consumption_records": int(consumption_summary.get("records", 0)),
        "consumption_item_signal_rows": len(object_rows),
        "orders_with_consumption_records": int(consumption_summary.get("records", 0)),
        "floc_route_context_rows": len(floc_rows),
        "asset_join_match_rate": float(floc_summary["asset_join_match_rate"]),
        "site_join_match_rate": float(floc_summary["site_join_match_rate"]),
        "contractual_denominator_rows_supported_now": len(activity_rows),
        "raw_operational_values_emitted": False,
        "outputs": [
            "b1_deterministic_harvest_memo.md",
            "b1_deterministic_harvest_evidence_sanitized.csv",
            "b1_deterministic_harvest_by_target_sanitized.csv",
            "b1_deterministic_harvest_relationship_rates_sanitized.csv",
            "b1_activity_type_distribution_sanitized.csv",
            "b1_consumption_object_part_summary_sanitized.json",
            "b1_deterministic_harvest_summary_sanitized.json",
        ],
    }
    (OUTPUT_DIR / "b1_deterministic_harvest_summary_sanitized.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    (OUTPUT_DIR / "b1_deterministic_harvest_memo.md").write_text(
        build_memo(summary, target_summary, relationship_rates),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
