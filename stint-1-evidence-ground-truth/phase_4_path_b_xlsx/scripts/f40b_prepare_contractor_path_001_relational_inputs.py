"""Prepare bounded inputs for F4.0b relational-model characterization.

This preflight inventories the CONTRACTOR_PATH_001 API-dump entity files, selects JSON as
the preferred characterization format, and creates sanitized positive controls.
It does not extract evidence, emit raw operational values, or produce mappings.
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = (
    PROJECT_ROOT
    / "stint-1-evidence-ground-truth"
    / "phase_4_path_b_xlsx"
    / "outputs"
    / "f40b_contractor_path_001_relational_model"
)
INTERNAL_DIR = PROJECT_ROOT / "reports" / "internal" / "f40b_contractor_path_001_relational_model"
CONTRACTOR_PATH_001_DIR = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "extracted_source"
    / "package_001_37cac7fe"
    / "Data"
    / "CONTRACTOR_PATH_001"
)

EXPECTED_ENTITIES = [
    "api_common_v1_assets",
    "api_common_v1_contracts",
    "api_common_v1_customers",
    "api_common_v1_sites",
    "api_service_v1_service-orders",
    "api_service_v1_service-orders_consumption",
    "api_service_v1_service-visits",
]

REQUIRED_FIELD_MARKERS = {
    "api_service_v1_service-orders": ["activityType", "descriptionExtended"],
    "api_service_v1_service-orders_consumption": ["_serviceOrderId", "orderId"],
    "api_service_v1_service-visits": ["orderId"],
    "api_common_v1_assets": ["siteId"],
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_hash(value: object, length: int = 16) -> str:
    raw = "" if value is None else str(value)
    return hashlib.sha256(raw.encode("utf-8", errors="ignore")).hexdigest()[:length]


def prefixed_hash(value: object, prefix: str, length: int = 12) -> str:
    return f"{prefix}-{stable_hash(value, length)}"


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def load_json_payload(path: Path) -> object:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def extract_records(payload: object) -> list[object]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, Mapping):
        for key in ["data", "items", "value", "records", "results"]:
            value = payload.get(key)
            if isinstance(value, list):
                return value
        list_values = [value for value in payload.values() if isinstance(value, list)]
        if len(list_values) == 1:
            return list_values[0]
    return []


def infer_top_keys(records: list[object], limit: int = 50) -> set[str]:
    keys: set[str] = set()
    for record in records[:limit]:
        if isinstance(record, Mapping):
            keys.update(str(key) for key in record.keys())
    return keys


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    INTERNAL_DIR.mkdir(parents=True, exist_ok=True)

    entity_rows: list[dict[str, object]] = []
    internal_rows: list[dict[str, object]] = []
    control_rows: list[dict[str, object]] = []
    total_json_records = 0

    for entity in EXPECTED_ENTITIES:
        files = {path.suffix.lower().lstrip("."): path for path in sorted(CONTRACTOR_PATH_001_DIR.glob(f"{entity}.*"))}
        entity_key = prefixed_hash(entity, "ENTITY", 10)
        json_path = files.get("json")
        record_count = ""
        top_key_count = ""
        read_status = "json_missing"
        top_keys: set[str] = set()
        if json_path is not None:
            try:
                payload = load_json_payload(json_path)
                records = extract_records(payload)
                top_keys = infer_top_keys(records)
                record_count = len(records)
                top_key_count = len(top_keys)
                total_json_records += len(records)
                read_status = "json_control_ready"
            except Exception as exc:  # noqa: BLE001 - report type only.
                read_status = f"json_read_failed:{type(exc).__name__}"

        entity_rows.append(
            {
                "entity_key": entity_key,
                "entity_label": entity,
                "role": "master_data" if entity.startswith("api_common") else "transactional",
                "formats_present": ";".join(sorted(files)),
                "preferred_format": "json" if json_path is not None else "",
                "json_file_size_bytes": json_path.stat().st_size if json_path is not None else "",
                "json_record_count": record_count,
                "json_top_level_field_count": top_key_count,
                "read_status": read_status,
                "raw_operational_values_emitted": False,
            }
        )
        internal_rows.append(
            {
                "entity_key": entity_key,
                "entity_label": entity,
                "json_path": str(json_path or ""),
                "xlsx_path": str(files.get("xlsx", "")),
                "xml_path": str(files.get("xml", "")),
            }
        )

        for marker in REQUIRED_FIELD_MARKERS.get(entity, []):
            control_rows.append(
                {
                    "entity_key": entity_key,
                    "entity_label": entity,
                    "marker_type": "field_exists",
                    "marker_name": marker,
                    "marker_hash": prefixed_hash(marker.lower(), "FIELD", 10),
                    "present_in_json_sample": marker in top_keys,
                    "read_status": read_status,
                    "raw_operational_values_emitted": False,
                }
            )

    write_csv(
        OUTPUT_DIR / "f40b_contractor_path_001_entity_inventory_preflight_sanitized.csv",
        entity_rows,
        [
            "entity_key",
            "entity_label",
            "role",
            "formats_present",
            "preferred_format",
            "json_file_size_bytes",
            "json_record_count",
            "json_top_level_field_count",
            "read_status",
            "raw_operational_values_emitted",
        ],
    )
    write_csv(
        INTERNAL_DIR / "f40b_contractor_path_001_entity_manifest_internal.csv",
        internal_rows,
        ["entity_key", "entity_label", "json_path", "xlsx_path", "xml_path"],
    )
    write_csv(
        OUTPUT_DIR / "f40b_contractor_path_001_positive_controls_sanitized.csv",
        control_rows,
        [
            "entity_key",
            "entity_label",
            "marker_type",
            "marker_name",
            "marker_hash",
            "present_in_json_sample",
            "read_status",
            "raw_operational_values_emitted",
        ],
    )

    summary = {
        "created_at_utc": utc_now(),
        "pass_id": "F4.0b-preflight",
        "expected_entities": len(EXPECTED_ENTITIES),
        "entities_with_json": sum("json" in str(row["formats_present"]).split(";") for row in entity_rows),
        "entities_with_xlsx": sum("xlsx" in str(row["formats_present"]).split(";") for row in entity_rows),
        "entities_with_xml": sum("xml" in str(row["formats_present"]).split(";") for row in entity_rows),
        "total_json_records": total_json_records,
        "positive_control_markers": len(control_rows),
        "positive_control_markers_present": sum(bool(row["present_in_json_sample"]) for row in control_rows),
        "raw_operational_values_emitted": False,
        "outputs": {
            "entity_inventory": str(OUTPUT_DIR / "f40b_contractor_path_001_entity_inventory_preflight_sanitized.csv"),
            "positive_controls": str(OUTPUT_DIR / "f40b_contractor_path_001_positive_controls_sanitized.csv"),
            "internal_manifest": str(INTERNAL_DIR / "f40b_contractor_path_001_entity_manifest_internal.csv"),
        },
    }
    (OUTPUT_DIR / "f40b_contractor_path_001_preflight_summary_sanitized.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
