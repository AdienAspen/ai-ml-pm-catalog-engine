from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path


STINT2_ROOT = Path("/home/adien-i7-remote/workspace/fsa_bridge_ml_feasibility/stint-2-target-ml-prototyping")
G12 = STINT2_ROOT / "g1_actionable_zeros" / "g12_floc_alignment"
INTERNAL = G12 / "internal" / "g12_floc_alignment_internal_review.csv"
OUT = G12 / "outputs"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    rows = read_csv(INTERNAL)
    site003_missing = [
        row
        for row in rows
        if row["site_id"] == "SITE04161" and row["match_status"] == "missing_turbine_token"
    ]
    asset_counter = Counter(row["asset_description"] for row in site003_missing)
    pad_counter = Counter(row["pad_id"] for row in site003_missing)
    audit_rows = [
        {
            "site_key": "SITE-003",
            "site_id_hash": "SITEID-3edc899252b6",
            "exception_scope": "missing_turbine_token",
            "exception_orders": len(site003_missing),
            "dominant_pad_hash": "PAD-7973a52ff6421d11",
            "dominant_pad_share": round(pad_counter.most_common(1)[0][1] / len(site003_missing) * 100, 6)
            if site003_missing
            else 0,
            "dominant_asset_class": "Substation",
            "dominant_asset_orders": asset_counter.get("Substation - Mountain View", 0),
            "secondary_asset_class": "SCADA System",
            "secondary_asset_orders": asset_counter.get("SCADA System - Mountain View", 0),
            "verdict": "explained_non_turbine_assets_not_parser_failure",
            "path_a_concern_table_same_count": "coincidental_count_same_number_different_namespace",
        }
    ]
    write_csv(
        OUT / "g12_site003_exception_audit_sanitized.csv",
        audit_rows,
        [
            "site_key",
            "site_id_hash",
            "exception_scope",
            "exception_orders",
            "dominant_pad_hash",
            "dominant_pad_share",
            "dominant_asset_class",
            "dominant_asset_orders",
            "secondary_asset_class",
            "secondary_asset_orders",
            "verdict",
            "path_a_concern_table_same_count",
        ],
    )

    summary_path = OUT / "g12_floc_alignment_summary_sanitized.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["site003_exception_audit"] = {
        "exception_orders": len(site003_missing),
        "dominant_asset_class": "Substation",
        "dominant_asset_orders": asset_counter.get("Substation - Mountain View", 0),
        "secondary_asset_class": "SCADA System",
        "secondary_asset_orders": asset_counter.get("SCADA System - Mountain View", 0),
        "verdict": "explained_non_turbine_assets_not_parser_failure",
        "path_a_concern_table_same_count": "coincidental_count_same_number_different_namespace",
    }
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")

    memo_path = OUT / "g12_floc_alignment_memo.md"
    memo = memo_path.read_text(encoding="utf-8")
    section = """
## SITE-003 Exception Audit

SITE-003 has 33 unmatched orders, an order of magnitude more than the other sites. The exception is explained: all 33 use the site-level `Other Equip.` pad, with 32 Substation orders and 1 SCADA System order. They do not carry turbine tokens, so the turbine-node alignment correctly leaves them unmatched.

The count of 1,581 SITE-003 service orders matches the Path A concern-table row count, but this is a numeric coincidence across different namespaces and branches. It is not treated as evidence of overlap.
"""
    marker = "\n## SITE-003 Exception Audit\n"
    if marker in memo:
        memo = memo.split(marker)[0].rstrip() + "\n" + section
    else:
        memo = memo.rstrip() + "\n" + section
    memo_path.write_text(memo, encoding="utf-8")


if __name__ == "__main__":
    main()
