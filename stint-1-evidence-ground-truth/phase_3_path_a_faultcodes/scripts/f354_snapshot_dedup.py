"""T3.5.4 Path A snapshot/event deduplication.

Rows in daily PDFs are snapshots, not incidents. This pass estimates incident
groups using site + asset + code + estimated incident-start window. Exact dates
and raw values stay internal; versioned outputs are sanitized.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]
INTERNAL_REPORTS_DIR = PROJECT_ROOT / "reports" / "internal"
PATH_A_DIR = PROJECT_ROOT / "stint-1-evidence-ground-truth" / "phase_3_path_a_faultcodes"
OUTPUT_DIR = PATH_A_DIR / "outputs"
INTERNAL_OUTPUT_DIR = INTERNAL_REPORTS_DIR / "path_a_repair"

PDF_ROWS_PATH = INTERNAL_REPORTS_DIR / "pdf_assets_of_concern_rows.csv"
CODE_PARTITION_INTERNAL_PATH = INTERNAL_OUTPUT_DIR / "f35_faultcode_state_partition_internal.csv"
VARIANT_MAP_PATH = OUTPUT_DIR / "template_variants" / "pdf_template_variant_file_map_sanitized.csv"

WINDOW_TOLERANCE_DAYS = 1


@dataclass
class ParsedDuration:
    minutes: int | None
    status: str


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_hash(value: str, length: int = 16) -> str:
    import hashlib

    return hashlib.sha256(value.encode("utf-8", errors="ignore")).hexdigest()[:length]


def as_text(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    if text.endswith(".0") and text[:-2].isdigit():
        return text[:-2]
    return text


def parse_snapshot_date(path_text: str, file_name: str) -> tuple[datetime | None, str]:
    candidates = [file_name, path_text]
    patterns = [
        (r"(20\d{2})[-_ ](\d{1,2})[-_ ](\d{1,2})", "%Y-%m-%d"),
        (r"(\d{1,2})[-_ ](\d{1,2})[-_ ](20\d{2})", "%m-%d-%Y"),
        (r"(20\d{2})\s+(\d{1,2})\s+(\d{1,2})", "%Y-%m-%d"),
    ]
    for value in candidates:
        normalized = value.replace(".", "-")
        for pattern, _fmt in patterns:
            match = re.search(pattern, normalized)
            if not match:
                continue
            parts = match.groups()
            try:
                if parts[0].startswith("20"):
                    return datetime(int(parts[0]), int(parts[1]), int(parts[2])), "parsed_from_path"
                return datetime(int(parts[2]), int(parts[0]), int(parts[1])), "parsed_from_path"
            except ValueError:
                continue
    return None, "missing_or_unparsed"


def parse_duration(value: object) -> ParsedDuration:
    text = as_text(value).lower()
    if not text or text == "-":
        return ParsedDuration(None, "missing")
    days = hours = minutes = 0
    for number, unit in re.findall(r"(\d+)\s*([dhm])", text):
        if unit == "d":
            days += int(number)
        elif unit == "h":
            hours += int(number)
        elif unit == "m":
            minutes += int(number)
    total = days * 24 * 60 + hours * 60 + minutes
    if total == 0:
        return ParsedDuration(None, "unparsed")
    return ParsedDuration(total, "parsed")


def namespace_for_classification(classification: str) -> str:
    if classification == "state_code":
        return "asset_state"
    if classification == "fault_code":
        return "fault_code"
    return "undetermined_code"


def confidence_for_group(rows: pd.DataFrame) -> str:
    if rows["classification"].eq("state_code").all() and len(rows) >= 10:
        return "medium_state_consistent"
    if rows["classification"].eq("fault_code").all() and len(rows) >= 2:
        return "medium_fault_candidate"
    if len(rows) < 3:
        return "low_frequency"
    return "low_mixed_or_undetermined"


def cluster_rows(rows: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = rows.copy()
    rows["fault_code_norm"] = rows["fault_code"].map(as_text)
    rows = rows[rows["fault_code_norm"].ne("") & rows["fault_code_norm"].ne("-")].copy()
    rows["asset_norm"] = rows["asset"].map(as_text)
    rows["site_key"] = rows["site_text"].map(lambda value: "SITE-" + stable_hash(as_text(value), 10))
    rows["asset_key"] = rows["asset_norm"].map(lambda value: "ASSET-" + stable_hash(value, 10))
    rows["code_key"] = rows["fault_code_norm"].map(lambda value: "CODE-" + stable_hash(value, 10))

    dates = rows.apply(lambda row: parse_snapshot_date(as_text(row["relative_path"]), as_text(row["file_name"])), axis=1)
    rows["snapshot_date"] = [item[0] for item in dates]
    rows["snapshot_date_status"] = [item[1] for item in dates]
    durations = rows["duration"].map(parse_duration)
    rows["duration_minutes"] = [item.minutes for item in durations]
    rows["duration_status"] = [item.status for item in durations]
    rows["incident_start_estimated"] = rows.apply(
        lambda row: row["snapshot_date"] - timedelta(minutes=int(row["duration_minutes"]))
        if pd.notna(row["snapshot_date"]) and pd.notna(row["duration_minutes"])
        else pd.NaT,
        axis=1,
    )

    partitions = pd.read_csv(CODE_PARTITION_INTERNAL_PATH)
    partitions["fault_code_norm"] = partitions["fault_code"].map(as_text)
    rows = rows.merge(
        partitions[["fault_code_norm", "classification", "classification_basis"]],
        on="fault_code_norm",
        how="left",
    )
    rows["classification"] = rows["classification"].fillna("undetermined")
    rows["namespace"] = rows["classification"].map(namespace_for_classification)

    variants = pd.read_csv(VARIANT_MAP_PATH)[
        ["path_hash", "file_hash", "template_variant", "recognized_core_sections", "zero_interpretation_allowed"]
    ]
    rows = rows.merge(variants, on=["path_hash", "file_hash"], how="left")
    rows["dedup_input_status"] = rows.apply(
        lambda row: "dedup_ready"
        if pd.notna(row["incident_start_estimated"])
        else "missing_temporal_inputs",
        axis=1,
    )
    rows["source_row_key"] = rows.apply(
        lambda row: "PATHA-SRCROW-"
        + stable_hash(
            "|".join(
                [
                    str(row.get("path_hash", "")),
                    str(row.get("file_hash", "")),
                    str(row.get("asset_key", "")),
                    str(row.get("code_key", "")),
                    str(row.get("duration", "")),
                    str(row.get("event", "")),
                ]
            ),
            12,
        ),
        axis=1,
    )

    event_records: list[dict[str, object]] = []
    row_records: list[dict[str, object]] = []
    ready = rows[rows["dedup_input_status"].eq("dedup_ready")].copy()
    missing = rows[~rows["dedup_input_status"].eq("dedup_ready")].copy()

    group_cols = ["site_key", "asset_key", "code_key", "namespace", "classification"]
    for group_key, group in ready.sort_values("incident_start_estimated").groupby(group_cols, dropna=False):
        current_rows: list[int] = []
        current_anchor: datetime | None = None
        cluster_index = 0
        for idx, row in group.iterrows():
            start = row["incident_start_estimated"]
            if current_anchor is None:
                current_anchor = start
                current_rows = [idx]
                continue
            gap_days = abs((start - current_anchor).total_seconds()) / 86400
            if gap_days <= WINDOW_TOLERANCE_DAYS:
                current_rows.append(idx)
            else:
                cluster_index += 1
                append_event(event_records, row_records, rows.loc[current_rows], group_key, cluster_index)
                current_anchor = start
                current_rows = [idx]
        if current_rows:
            cluster_index += 1
            append_event(event_records, row_records, rows.loc[current_rows], group_key, cluster_index)

    for idx, row in missing.iterrows():
        group_key = (row["site_key"], row["asset_key"], row["code_key"], row["namespace"], row["classification"])
        append_event(event_records, row_records, rows.loc[[idx]], group_key, 1, forced_status="not_deduplicated_missing_temporal_inputs")

    return pd.DataFrame(event_records), pd.DataFrame(row_records)


def append_event(
    event_records: list[dict[str, object]],
    row_records: list[dict[str, object]],
    group: pd.DataFrame,
    group_key: tuple[object, ...],
    cluster_index: int,
    forced_status: str | None = None,
) -> None:
    site_key, asset_key, code_key, namespace, classification = group_key
    event_seed = "|".join([str(site_key), str(asset_key), str(code_key), str(namespace), str(cluster_index)])
    event_key = "PATHA-EVENT-" + stable_hash(event_seed, 12)
    start_values = pd.to_datetime(group["incident_start_estimated"], errors="coerce")
    snapshot_values = pd.to_datetime(group["snapshot_date"], errors="coerce")
    valid_starts = start_values.dropna()
    valid_snapshots = snapshot_values.dropna()
    span_days = (
        int((valid_snapshots.max() - valid_snapshots.min()).days) if len(valid_snapshots) >= 2 else 0
    )
    event_records.append(
        {
            "estimated_event_key": event_key,
            "site_key": site_key,
            "asset_key": asset_key,
            "code_key": code_key,
            "namespace": namespace,
            "classification": classification,
            "snapshot_row_count": int(group.shape[0]),
            "source_file_count": int(group["file_hash"].nunique(dropna=True)),
            "template_variant_count": int(group["template_variant"].nunique(dropna=True)),
            "snapshot_span_days": span_days,
            "incident_start_bucket_key": "START-" + stable_hash(valid_starts.min().strftime("%Y-%m-%d"), 10)
            if len(valid_starts)
            else "",
            "snapshot_month_min": valid_snapshots.min().strftime("%Y-%m") if len(valid_snapshots) else "",
            "snapshot_month_max": valid_snapshots.max().strftime("%Y-%m") if len(valid_snapshots) else "",
            "dedup_status": forced_status or "estimated_event",
            "dedup_window_tolerance_days": WINDOW_TOLERANCE_DAYS,
            "evidence_type": "expert_inference",
            "tier": "silver-medium" if not forced_status else "unresolved",
            "status": "estimated_event_requires_review" if not forced_status else "not_deduplicated",
            "label_generation_method": "path_a_snapshot_dedup_v1",
            "evaluation_independence": "derived_from_rules",
            "confidence": confidence_for_group(group),
            "raw_operational_values_emitted": False,
        }
    )
    for idx in group.index:
        row_records.append(
            {
                "estimated_event_key": event_key,
                "row_key": group.loc[idx, "source_row_key"],
                "path_hash": group.loc[idx, "path_hash"],
                "file_hash": group.loc[idx, "file_hash"],
                "template_variant": group.loc[idx, "template_variant"],
                "dedup_status": forced_status or "assigned_to_estimated_event",
                "raw_operational_values_emitted": False,
            }
        )


def build_memo(summary: dict[str, object], by_namespace: pd.DataFrame, by_classification: pd.DataFrame) -> str:
    namespace_rows = [
        "| "
        + " | ".join(
            [
                str(row.namespace),
                str(row.snapshot_rows),
                str(row.estimated_events),
                str(row.compression_ratio),
            ]
        )
        + " |"
        for row in by_namespace.itertuples(index=False)
    ]
    class_rows = [
        "| "
        + " | ".join(
            [
                str(row.classification),
                str(row.snapshot_rows),
                str(row.estimated_events),
                str(row.compression_ratio),
            ]
        )
        + " |"
        for row in by_classification.itertuples(index=False)
    ]
    return "\n".join(
        [
            "# T3.5.4 Path A Snapshot Deduplication",
            "",
            "## Scope",
            "",
            "This pass converts Path A code-bearing PDF rows from daily snapshots into estimated incident groups. It does not promote any event to a measurement denominator.",
            "",
            "## Deduplication Rule",
            "",
            "`incident_start_estimated = snapshot_date - duration`",
            "",
            "Grouping key:",
            "",
            "`site_key + asset_key + code_key + namespace + incident_start_estimated window`",
            "",
            f"Window tolerance: `{summary['dedup_window_tolerance_days']}` day.",
            "",
            "## Summary",
            "",
            f"- Snapshot rows evaluated: `{summary['snapshot_rows_evaluated']}`",
            f"- Rows dedup-ready: `{summary['rows_dedup_ready']}`",
            f"- Rows missing temporal inputs: `{summary['rows_missing_temporal_inputs']}`",
            f"- Estimated events: `{summary['estimated_events']}`",
            f"- Overall compression ratio: `{summary['overall_compression_ratio']}`",
            f"- Raw operational values emitted in versioned outputs: `{summary['raw_operational_values_emitted']}`",
            "",
            "## By Namespace",
            "",
            "| namespace | snapshot_rows | estimated_events | compression_ratio |",
            "| --- | ---: | ---: | ---: |",
            *namespace_rows,
            "",
            "## By Classification",
            "",
            "| classification | snapshot_rows | estimated_events | compression_ratio |",
            "| --- | ---: | ---: | ---: |",
            *class_rows,
            "",
            "## Interpretation",
            "",
            "`asset_state` remains a separate namespace. It is not automatically promoted to Activity Type; only maintenance-like state families may be reviewed later as secondary evidence.",
            "",
            "Estimated events are `expert_inference`, `silver-medium`, `derived_from_rules`, and `estimated_event_requires_review` unless temporal inputs are missing.",
            "",
        ]
    )


def summarize_events(events: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    by_namespace = (
        events.groupby("namespace", dropna=False)
        .agg(snapshot_rows=("snapshot_row_count", "sum"), estimated_events=("estimated_event_key", "size"))
        .reset_index()
    )
    by_namespace["compression_ratio"] = (
        by_namespace["snapshot_rows"] / by_namespace["estimated_events"]
    ).round(2)
    by_namespace["raw_operational_values_emitted"] = False

    by_classification = (
        events.groupby("classification", dropna=False)
        .agg(snapshot_rows=("snapshot_row_count", "sum"), estimated_events=("estimated_event_key", "size"))
        .reset_index()
    )
    by_classification["compression_ratio"] = (
        by_classification["snapshot_rows"] / by_classification["estimated_events"]
    ).round(2)
    by_classification["raw_operational_values_emitted"] = False

    rows_evaluated = int(events["snapshot_row_count"].sum()) if not events.empty else 0
    estimated_events = int(events.shape[0])
    summary = {
        "created_at_utc": utc_now(),
        "pass_id": "T3.5.4",
        "snapshot_rows_evaluated": rows_evaluated,
        "rows_dedup_ready": int(
            events.loc[events["dedup_status"].eq("estimated_event"), "snapshot_row_count"].sum()
        )
        if not events.empty
        else 0,
        "rows_missing_temporal_inputs": int(
            events.loc[events["dedup_status"].ne("estimated_event"), "snapshot_row_count"].sum()
        )
        if not events.empty
        else 0,
        "estimated_events": estimated_events,
        "overall_compression_ratio": round(rows_evaluated / estimated_events, 2)
        if estimated_events
        else 0.0,
        "dedup_window_tolerance_days": WINDOW_TOLERANCE_DAYS,
        "raw_operational_values_emitted": False,
    }
    return by_namespace, by_classification, summary


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    INTERNAL_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    rows = pd.read_csv(PDF_ROWS_PATH)
    events, row_assignments = cluster_rows(rows)
    by_namespace, by_classification, summary = summarize_events(events)

    events_path = OUTPUT_DIR / "f354_estimated_events_sanitized.csv"
    assignments_path = OUTPUT_DIR / "f354_snapshot_row_assignments_sanitized.csv"
    namespace_path = OUTPUT_DIR / "f354_dedup_by_namespace_sanitized.csv"
    classification_path = OUTPUT_DIR / "f354_dedup_by_classification_sanitized.csv"
    summary_path = OUTPUT_DIR / "f354_snapshot_dedup_summary_sanitized.json"
    memo_path = OUTPUT_DIR / "f354_snapshot_dedup_memo.md"
    internal_events_path = INTERNAL_OUTPUT_DIR / "f354_estimated_events_internal.csv"

    events.to_csv(events_path, index=False)
    row_assignments.to_csv(assignments_path, index=False)
    by_namespace.to_csv(namespace_path, index=False)
    by_classification.to_csv(classification_path, index=False)
    events.to_csv(internal_events_path, index=False)

    summary["outputs"] = {
        "memo": str(memo_path),
        "estimated_events": str(events_path),
        "row_assignments": str(assignments_path),
        "by_namespace": str(namespace_path),
        "by_classification": str(classification_path),
    }
    summary["internal_outputs_ignored"] = {"estimated_events_internal": str(internal_events_path)}
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    memo_path.write_text(build_memo(summary, by_namespace, by_classification), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
