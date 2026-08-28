from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "stint-1.1-reference-layer" / "reference_layer" / "sap_mapping"
DOCS_DIR = PROJECT_ROOT / "stint-1.1-reference-layer" / "docs"

CATALOG_PATTERNS = (
    "*Wind*Catalog*Group*Code*.xlsx",
    "*Wind*Catalog*Codes*.xlsx",
    "*Catalog*Group*Codes*.xlsx",
)

SHEET_TARGETS = {
    "Catalog. S - Group and Code": {
        "catalog": "S",
        "target": "Symptom",
        "canonical_field": "symptom_code",
        "namespace": "catalog_s",
    },
    "Catalog. B - Group and Code": {
        "catalog": "B",
        "target": "Object Part",
        "canonical_field": "object_part_code",
        "namespace": "catalog_b",
    },
    "Catalog. C - Group and Code": {
        "catalog": "C",
        "target": "Damage",
        "canonical_field": "damage_code",
        "namespace": "catalog_c",
    },
    "Catalog. 5 - Group and Code": {
        "catalog": "5",
        "target": "Cause",
        "canonical_field": "cause_code",
        "namespace": "catalog_5",
    },
    "Catalog. A - Group and Code": {
        "catalog": "A",
        "target": "Activity",
        "canonical_field": "activity_code",
        "namespace": "catalog_a",
    },
}

REQUIRED_COLUMNS = ["Catalog", "Code Group", "Code", "Short Text for Code"]


def normalise_token(value: object) -> str:
    text = "" if pd.isna(value) else str(value).strip()
    text = re.sub(r"\s+", " ", text)
    return text


def find_catalog() -> Path:
    candidates: list[Path] = []
    data_dir = PROJECT_ROOT / "data"
    for pattern in CATALOG_PATTERNS:
        candidates.extend(data_dir.rglob(pattern))
    candidates = sorted({path for path in candidates if path.is_file()})
    if not candidates:
        raise FileNotFoundError("No Wind Catalog Group/Codes workbook found under data/.")
    if len(candidates) > 1:
        preferred = [path for path in candidates if "final" in path.name.lower()]
        if len(preferred) == 1:
            return preferred[0]
        raise RuntimeError(
            "Multiple catalog workbook candidates found; choose one explicitly: "
            + "; ".join(str(path.relative_to(PROJECT_ROOT)) for path in candidates)
        )
    return candidates[0]


def load_catalog_rows(catalog_path: Path) -> pd.DataFrame:
    excel = pd.ExcelFile(catalog_path)
    missing_sheets = sorted(set(SHEET_TARGETS) - set(excel.sheet_names))
    if missing_sheets:
        raise RuntimeError(f"Missing required catalog sheets: {missing_sheets}")

    frames: list[pd.DataFrame] = []
    for sheet_name, meta in SHEET_TARGETS.items():
        sheet = pd.read_excel(catalog_path, sheet_name=sheet_name, dtype=str)
        missing_columns = [col for col in REQUIRED_COLUMNS if col not in sheet.columns]
        if missing_columns:
            raise RuntimeError(f"{sheet_name} missing required columns: {missing_columns}")

        sheet = sheet[REQUIRED_COLUMNS].copy()
        for col in REQUIRED_COLUMNS:
            sheet[col] = sheet[col].map(normalise_token)
        sheet = sheet[(sheet["Code Group"] != "") & (sheet["Code"] != "")]

        sheet["target"] = meta["target"]
        sheet["canonical_field"] = meta["canonical_field"]
        sheet["namespace"] = meta["namespace"]
        sheet["source_sheet"] = sheet_name
        frames.append(sheet)

    catalog = pd.concat(frames, ignore_index=True)
    catalog["catalog"] = catalog["Catalog"].where(catalog["Catalog"] != "", catalog["target"])
    catalog["sap_mapping_id"] = catalog.apply(
        lambda row: "SAPMAP-"
        + "-".join(
            [
                re.sub(r"[^A-Za-z0-9]+", "", str(row["Catalog"])) or "CAT",
                re.sub(r"[^A-Za-z0-9]+", "", str(row["Code Group"])) or "GROUP",
                re.sub(r"[^A-Za-z0-9]+", "", str(row["Code"])) or "CODE",
            ]
        ),
        axis=1,
    )
    catalog["code_group"] = catalog["Code Group"]
    catalog["code"] = catalog["Code"]
    catalog["short_text"] = catalog["Short Text for Code"]
    catalog["source"] = "Wind Catalog Group and Codes Final"
    catalog["source_version"] = "v4"
    catalog["source_file"] = catalog_path.name
    catalog["evidence_type"] = "reference_evidence"
    catalog["tier"] = "gold"
    catalog["authority_level"] = "authoritative_catalog"
    catalog["can_support_measurement_denominator"] = False
    catalog["evidence_use"] = "valid_answer_universe_only"
    catalog["status"] = "active"
    catalog["notes"] = (
        "Authoritative target-code reference. Does not prove any source text to code mapping."
    )

    ordered_columns = [
        "sap_mapping_id",
        "target",
        "canonical_field",
        "namespace",
        "catalog",
        "code_group",
        "code",
        "short_text",
        "source",
        "source_version",
        "source_file",
        "source_sheet",
        "evidence_type",
        "tier",
        "authority_level",
        "can_support_measurement_denominator",
        "evidence_use",
        "status",
        "notes",
    ]
    return catalog[ordered_columns].sort_values(
        ["target", "catalog", "code_group", "code"], kind="stable"
    )


def build_summary(catalog: pd.DataFrame, catalog_path: Path) -> dict:
    key_columns = ["catalog", "code_group", "code"]
    duplicate_key_rows = int(catalog.duplicated(key_columns, keep=False).sum())
    missing_required_rows = int(
        catalog[["target", "canonical_field", "catalog", "code_group", "code"]]
        .eq("")
        .any(axis=1)
        .sum()
    )
    return {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_file": catalog_path.name,
        "source_path_redacted": True,
        "rows": int(len(catalog)),
        "targets": catalog["target"].nunique(),
        "rows_by_target": catalog.groupby("target").size().sort_index().to_dict(),
        "evidence_type_counts": catalog["evidence_type"].value_counts().to_dict(),
        "tier_counts": catalog["tier"].value_counts().to_dict(),
        "measurement_denominator_eligible_rows": int(
            catalog["can_support_measurement_denominator"].fillna(False).sum()
        ),
        "duplicate_catalog_code_rows": duplicate_key_rows,
        "missing_required_rows": missing_required_rows,
        "output_csv": "stint-1.1-reference-layer/reference_layer/sap_mapping/sap_mapping_catalog_v1.csv",
        "output_jsonl": "stint-1.1-reference-layer/reference_layer/sap_mapping/sap_mapping_catalog_v1.jsonl",
        "duplicate_keys_csv": "stint-1.1-reference-layer/reference_layer/sap_mapping/sap_mapping_catalog_duplicate_keys.csv",
        "raw_operational_values_emitted": False,
    }


def main() -> int:
    catalog_path = find_catalog()
    catalog = load_catalog_rows(catalog_path)
    summary = build_summary(catalog, catalog_path)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = OUTPUT_DIR / "sap_mapping_catalog_v1.csv"
    jsonl_path = OUTPUT_DIR / "sap_mapping_catalog_v1.jsonl"
    summary_path = OUTPUT_DIR / "sap_mapping_catalog_summary.json"
    duplicate_path = OUTPUT_DIR / "sap_mapping_catalog_duplicate_keys.csv"

    catalog.to_csv(csv_path, index=False)
    duplicate_keys = (
        catalog.groupby(["target", "catalog", "code_group", "code"], dropna=False)
        .size()
        .reset_index(name="row_count")
    )
    duplicate_keys = duplicate_keys[duplicate_keys["row_count"] > 1]
    duplicate_keys.to_csv(duplicate_path, index=False)
    with jsonl_path.open("w", encoding="utf-8") as handle:
        for record in catalog.to_dict(orient="records"):
            handle.write(json.dumps(record, ensure_ascii=True) + "\n")
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=True), encoding="utf-8")

    print(json.dumps(summary, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
