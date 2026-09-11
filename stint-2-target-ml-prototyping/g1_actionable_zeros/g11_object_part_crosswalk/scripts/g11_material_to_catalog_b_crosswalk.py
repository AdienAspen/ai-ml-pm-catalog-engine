from __future__ import annotations

import ast
import csv
import hashlib
import json
import math
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from openpyxl import load_workbook


PROJECT_ROOT = Path("/home/adien-i7-remote/workspace/fsa_bridge_ml_feasibility")
STINT2_ROOT = PROJECT_ROOT / "stint-2-target-ml-prototyping"
OUT = STINT2_ROOT / "g1_actionable_zeros" / "g11_object_part_crosswalk" / "outputs"
INTERNAL_OUT = STINT2_ROOT / "g1_actionable_zeros" / "g11_object_part_crosswalk" / "internal"

CONSUMPTION_XLSX = (
    PROJECT_ROOT
    / "data/interim/extracted_source/package_001_37cac7fe/Data/Vestas/api_service_v1_service-orders_consumption.xlsx"
)
CONSUMPTION_JSON = (
    PROJECT_ROOT
    / "data/interim/extracted_source/package_001_37cac7fe/Data/Vestas/api_service_v1_service-orders_consumption.json"
)
WIND_CATALOG_XLSX = (
    PROJECT_ROOT
    / "data/interim/extracted_source/package_001_37cac7fe/Data/References/Wind Catalog Group and Codes Final v4.xlsx"
)

STOPWORDS = {
    "a",
    "an",
    "and",
    "assy",
    "assembly",
    "ea",
    "for",
    "f",
    "in",
    "kit",
    "mm",
    "non",
    "none",
    "of",
    "std",
    "the",
    "v",
    "with",
    "wr",
}

MATERIAL_SYNONYMS = {
    "accu": "accumulator",
    "accumulator": "accumulator",
    "airfilter": "filter",
    "bearing": "bearing",
    "blade": "blade",
    "bolt": "bolt",
    "brake": "brake",
    "brush": "brush",
    "cable": "cable",
    "can": "reservoir",
    "cb": "circuit breaker",
    "contactor": "contactor",
    "detector": "detector",
    "detectors": "detector",
    "fan": "fan",
    "filter": "filter",
    "filterpad": "filter",
    "fitting": "fitting",
    "grease": "oil",
    "hose": "hose",
    "hpu": "hydraulic power unit",
    "hub": "hub",
    "lubricant": "oil",
    "motor": "motor",
    "nut": "nut",
    "oring": "o ring",
    "o": "o ring",
    "oil": "oil",
    "relay": "relay",
    "seal": "seal",
    "sensor": "sensor",
    "sensors": "sensor",
    "switch": "switch",
    "terminal": "terminal",
    "tie": "cable",
    "tower": "tower",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_hash(value: object, length: int = 16) -> str:
    raw = "" if value is None else str(value)
    return hashlib.sha256(raw.encode("utf-8", errors="ignore")).hexdigest()[:length]


def prefixed_hash(prefix: str, value: object, length: int = 16) -> str:
    return f"{prefix}-{stable_hash(value, length)}"


def normalize(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def tokens(value: object) -> list[str]:
    result = []
    for token in normalize(value).split():
        if token.isdigit() or token in STOPWORDS or len(token) <= 1:
            continue
        result.append(MATERIAL_SYNONYMS.get(token, token))
    expanded = " ".join(result).split()
    return [token for token in expanded if token and token not in STOPWORDS and not token.isdigit()]


def read_consumption_rows() -> list[dict[str, Any]]:
    payload = json.loads(CONSUMPTION_JSON.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise RuntimeError(f"Expected list payload in {CONSUMPTION_JSON}")
    rows = []
    for record in payload:
        record = dict(record)
        record["orderId"] = str(record.get("orderId") or "").strip()
        record["items_parsed"] = record.get("items") or []
        record["resources_parsed"] = record.get("resources") or []
        rows.append(record)
    return rows


def read_catalog_b() -> list[dict[str, str]]:
    wb = load_workbook(WIND_CATALOG_XLSX, read_only=True, data_only=True)
    ws = wb["Catalog. B - Group and Code"]
    headers = [cell.value for cell in next(ws.iter_rows(min_row=1, max_row=1))]
    rows = []
    for values in ws.iter_rows(min_row=2, values_only=True):
        record = {str(key): "" if value is None else str(value).strip() for key, value in zip(headers, values)}
        if record.get("Catalog") == "B" and record.get("Code") and record.get("Short Text for Code"):
            record["catalog_tokens"] = " ".join(tokens(record["Short Text for Code"]))
            rows.append(record)
    return rows


def material_head(description: str) -> str:
    material_tokens = tokens(description)
    if not material_tokens:
        return ""
    joined = " ".join(material_tokens)
    for phrase in [
        "circuit breaker",
        "hydraulic power unit",
        "o ring",
        "smoke detector",
        "motor brush",
        "fan blade",
    ]:
        if phrase in joined:
            return phrase
    return material_tokens[0]


def score_candidate(material_description: str, catalog_description: str) -> float:
    material = set(tokens(material_description))
    catalog = set(tokens(catalog_description))
    if not material or not catalog:
        return 0.0
    intersection = material & catalog
    score = len(intersection) / len(catalog)
    head = material_head(material_description)
    if head and set(head.split()) <= catalog:
        score += 0.35
    if catalog <= material:
        score += 0.25
    return round(min(score, 1.0), 6)


def status_for_score(score: float) -> str:
    if score >= 0.85:
        return "auto_candidate_strong"
    if score >= 0.55:
        return "auto_candidate_medium"
    if score > 0:
        return "auto_candidate_weak"
    return "no_catalog_b_candidate"


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str], mode_600: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    if mode_600:
        os.chmod(path, 0o600)


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    INTERNAL_OUT.mkdir(parents=True, exist_ok=True)
    os.chmod(INTERNAL_OUT, 0o700)

    consumption = read_consumption_rows()
    catalog_b = read_catalog_b()

    item_rows = []
    concept_orders: dict[str, set[str]] = defaultdict(set)
    concept_counts: Counter[str] = Counter()
    concept_descriptions: dict[str, Counter[str]] = defaultdict(Counter)
    concept_item_ids: dict[str, Counter[str]] = defaultdict(Counter)

    orders_with_items = set()
    orders_without_items = set()
    activity_with_items: Counter[str] = Counter()
    activity_without_items: Counter[str] = Counter()

    for record in consumption:
        order_id = record["orderId"]
        items = record["items_parsed"]
        resources = record["resources_parsed"]
        activity_labels = sorted(
            {
                normalize(resource.get("activityTypeId") or resource.get("activityType") or "unknown_activity")
                for resource in resources
            }
        ) or ["no_resource_activity"]
        if items:
            orders_with_items.add(order_id)
            for label in activity_labels:
                activity_with_items[label] += 1
        else:
            orders_without_items.add(order_id)
            for label in activity_labels:
                activity_without_items[label] += 1

        for item in items:
            item_id = str(item.get("itemId") or "").strip()
            description = str(item.get("itemDescription") or "").strip()
            concept_key = prefixed_hash("ITEM", item_id or normalize(description), 16)
            concept_counts[concept_key] += 1
            concept_orders[concept_key].add(order_id)
            concept_descriptions[concept_key][description] += 1
            concept_item_ids[concept_key][item_id] += 1
            item_rows.append(
                {
                    "order_id_hash": prefixed_hash("ORDER", order_id, 16),
                    "source_item_concept_key": concept_key,
                    "item_id_hash": prefixed_hash("ITEMID", item_id, 16),
                    "item_description_hash": stable_hash(description, 16),
                    "quantity_sign": "negative" if float(item.get("quantity") or 0) < 0 else "non_negative",
                    "unit_of_measure": str(item.get("unitOfMeasure") or ""),
                }
            )

    crosswalk_rows = []
    internal_rows = []
    for concept_key, count in concept_counts.most_common():
        description, description_count = concept_descriptions[concept_key].most_common(1)[0]
        item_id, _ = concept_item_ids[concept_key].most_common(1)[0]
        scored = [
            (score_candidate(description, row["Short Text for Code"]), row)
            for row in catalog_b
        ]
        scored.sort(key=lambda item: (-item[0], item[1]["Code Group"], item[1]["Code"]))
        best_score, best = scored[0]
        status = status_for_score(best_score)
        row = {
            "source_item_concept_key": concept_key,
            "item_id_hash": prefixed_hash("ITEMID", item_id, 16),
            "item_description_hash": stable_hash(description, 16),
            "item_rows": count,
            "orders_covered": len(concept_orders[concept_key]),
            "order_coverage_percent": round(len(concept_orders[concept_key]) / len(orders_with_items) * 100, 6),
            "material_head_hash": stable_hash(material_head(description), 12),
            "catalog": best["Catalog"] if best_score > 0 else "",
            "catalog_b_code_group": best["Code Group"] if best_score > 0 else "",
            "catalog_b_code": best["Code"] if best_score > 0 else "",
            "catalog_b_description": best["Short Text for Code"] if best_score > 0 else "",
            "match_score": best_score,
            "crosswalk_status": status,
            "source_label_provenance": "real_observed_label",
            "crosswalk_provenance": "algorithmic_candidate_for_expert_review",
            "evaluation_independence": "derived_from_rules",
        }
        crosswalk_rows.append(row)
        internal_rows.append(
            {
                **row,
                "item_id": item_id,
                "item_description": description,
                "material_head": material_head(description),
            }
        )

    crosswalk_fields = [
        "source_item_concept_key",
        "item_id_hash",
        "item_description_hash",
        "item_rows",
        "orders_covered",
        "order_coverage_percent",
        "material_head_hash",
        "catalog",
        "catalog_b_code_group",
        "catalog_b_code",
        "catalog_b_description",
        "match_score",
        "crosswalk_status",
        "source_label_provenance",
        "crosswalk_provenance",
        "evaluation_independence",
    ]
    write_csv(OUT / "g11_material_to_catalog_b_crosswalk_sanitized.csv", crosswalk_rows, crosswalk_fields)
    write_csv(INTERNAL_OUT / "g11_material_to_catalog_b_crosswalk_internal_review.csv", internal_rows, [*crosswalk_fields, "item_id", "item_description", "material_head"], mode_600=True)
    write_csv(
        OUT / "g11_item_signal_rows_sanitized.csv",
        item_rows,
        [
            "order_id_hash",
            "source_item_concept_key",
            "item_id_hash",
            "item_description_hash",
            "quantity_sign",
            "unit_of_measure",
        ],
    )

    activity_rows = []
    all_activity = sorted(set(activity_with_items) | set(activity_without_items))
    for label in all_activity:
        with_count = activity_with_items[label]
        without_count = activity_without_items[label]
        activity_rows.append(
            {
                "activity_type_normalized": label,
                "orders_with_items": with_count,
                "orders_without_items": without_count,
                "without_items_share_of_activity": round(without_count / (with_count + without_count) * 100, 6)
                if with_count + without_count
                else 0,
            }
        )
    write_csv(
        OUT / "g11_consumption_absence_by_activity_type_sanitized.csv",
        activity_rows,
        ["activity_type_normalized", "orders_with_items", "orders_without_items", "without_items_share_of_activity"],
    )

    status_counts = Counter(row["crosswalk_status"] for row in crosswalk_rows)
    strong_or_medium_concepts = {
        row["source_item_concept_key"]
        for row in crosswalk_rows
        if row["crosswalk_status"] in {"auto_candidate_strong", "auto_candidate_medium"}
    }
    orders_with_strong_or_medium_candidate = {
        row["order_id_hash"]
        for row in item_rows
        if row["source_item_concept_key"] in strong_or_medium_concepts
    }
    summary = {
        "task": "G1.1_material_to_catalog_b_crosswalk",
        "created_at_utc": utc_now(),
        "consumption_records": len(consumption),
        "orders_with_items": len(orders_with_items),
        "orders_without_items": len(orders_without_items),
        "item_signal_rows": len(item_rows),
        "distinct_source_item_concepts": len(crosswalk_rows),
        "distinct_catalog_b_codes": len({(row["Code Group"], row["Code"]) for row in catalog_b}),
        "catalog_b_rows": len(catalog_b),
        "crosswalk_status_counts": dict(status_counts),
        "orders_with_strong_or_medium_candidate": len(orders_with_strong_or_medium_candidate),
        "orders_with_strong_or_medium_candidate_percent_of_item_orders": round(
            len(orders_with_strong_or_medium_candidate) / len(orders_with_items) * 100, 6
        ),
        "raw_operational_values_emitted_in_versioned_outputs": False,
        "internal_review_file_mode": "600",
        "internal_review_dir_mode": "700",
        "promotion_rule": "A candidate crosswalk is not contractual truth and requires explicit review before admission.",
    }
    write_json(OUT / "g11_crosswalk_summary_sanitized.json", summary)

    memo = f"""# G1.1 Material to Catalog B Crosswalk Memo

G1.1 profiles the consumption item signal that blocked Object Part in B1.

## Source Inventory

- Consumption records: {len(consumption):,}
- Orders with item signal: {len(orders_with_items):,}
- Orders without item signal: {len(orders_without_items):,}
- Item signal rows: {len(item_rows):,}
- Distinct source item concepts: {len(crosswalk_rows):,}
- Catalog B rows in Wind Catalog: {len(catalog_b):,}

## Crosswalk Status

This run emits candidate mappings from material concepts to Catalog B. The material item signal is a real observed label. The crosswalk row is an inferred candidate and remains `derived_from_rules` until explicitly reviewed.

Status counts:

"""
    for status, count in sorted(status_counts.items()):
        memo += f"- {status}: {count}\n"
    memo += f"""
Strong or medium candidates cover {len(orders_with_strong_or_medium_candidate):,} unique item-bearing orders. Coverage is reported against the 4,079 orders with consumption items, not against the MAT denominator.

## 62% Without Consumption

The absence profile is emitted in `g11_consumption_absence_by_activity_type_sanitized.csv`. It bounds where Object Part is reachable from consumption and should be interpreted by activity type, not as random missingness.

## Governance

- Do not aggregate this with Path A or B2.
- Do not treat Catalog B candidate output as independent evaluation.
- Do not use `evaluation_set_v1` units for training.
- Use the internal review file only in the closed environment; it contains visible material descriptions and has mode 600.
"""
    (OUT / "g11_coverage_memo.md").write_text(memo, encoding="utf-8")


if __name__ == "__main__":
    main()
