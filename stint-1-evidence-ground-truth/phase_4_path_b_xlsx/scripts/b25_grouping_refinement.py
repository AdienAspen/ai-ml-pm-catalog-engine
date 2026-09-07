from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import re
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from openpyxl import load_workbook


PROJECT_ROOT = Path("/home/adien-i7-remote/workspace/fsa_bridge_ml_feasibility")
SCRIPT_DIR = PROJECT_ROOT / "stint-1-evidence-ground-truth/phase_4_path_b_xlsx/scripts"
OUTPUT_DIR = PROJECT_ROOT / "stint-1-evidence-ground-truth/phase_4_path_b_xlsx/outputs/b25_grouping_refinement"
B22_DIR = PROJECT_ROOT / "stint-1-evidence-ground-truth/phase_4_path_b_xlsx/outputs/b2_snapshot_dedup"

SOURCE_ROOTS = [
    PROJECT_ROOT / "data/interim/extracted_source/package_001_37cac7fe/Data/SITE_PATH_002 Wind OEM_ENTITY_001 EOD",
    PROJECT_ROOT / "data/interim/extracted_source/package_001_37cac7fe/Data/SITE_PATH_004 OEM_ENTITY_001 Info",
    PROJECT_ROOT / "data/interim/extracted_source/package_003_19512420/CONTRACTOR_PATH_002",
]

RAW_PATTERNS = [
    re.compile(r"contractor_path_001", re.I),
    re.compile(r"site_path_001", re.I),
    re.compile(r"site_path_002", re.I),
    re.compile(r"site_path_003", re.I),
    re.compile(r"site_path_004", re.I),
    re.compile(r"client_entity", re.I),
    re.compile(r"oem_entity_001", re.I),
    re.compile(r"\bge\b", re.I),
    re.compile(r"/home/adien", re.I),
    re.compile(r"data/interim/extracted_source", re.I),
]


def load_b23_module():
    spec = importlib.util.spec_from_file_location("b23", SCRIPT_DIR / "b23_snapshot_weak_supervision.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load B2.3 module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


b23 = load_b23_module()


def short_hash(value: str, prefix: str, length: int = 12) -> str:
    return f"{prefix}-{hashlib.sha256(value.encode('utf-8', errors='ignore')).hexdigest()[:length]}"


def parse_snapshot_date(bucket: str) -> date | None:
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", bucket):
            return datetime.strptime(bucket, "%Y-%m-%d").date()
    except ValueError:
        return None
    return None


DURATION_PATTERNS = [
    re.compile(r"\b(?:(\d+)\s*d(?:ay|ays)?\s*)?(?:(\d+)\s*h(?:our|ours|rs)?\s*)?(?:(\d+)\s*m(?:in|ins|inute|inutes)?\s*)?\b", re.I),
    re.compile(r"\b(\d{1,3}):(\d{2})\b"),
]


def parse_duration_days(values: list[str]) -> float | None:
    for value in values:
        text = str(value).strip().lower()
        if not text or len(text) > 80:
            continue
        for m in DURATION_PATTERNS:
            match = m.search(text)
            if not match:
                continue
            groups = match.groups()
            if len(groups) == 3 and any(groups):
                days = int(groups[0] or 0)
                hours = int(groups[1] or 0)
                minutes = int(groups[2] or 0)
                if days or hours or minutes:
                    return days + hours / 24 + minutes / 1440
            if len(groups) == 2 and all(groups):
                hours = int(groups[0])
                minutes = int(groups[1])
                if hours or minutes:
                    return hours / 24 + minutes / 1440
    return None


def iter_groupable_text_rows(path: Path) -> list[dict[str, object]]:
    family, doc_type = b23.family_for_path(path)
    snapshot_bucket = b23.date_bucket(path)
    snapshot_date = parse_snapshot_date(snapshot_bucket)
    file_key = b23.prefixed_hash(str(path.relative_to(PROJECT_ROOT)), "B2FILE", 12)
    wb = load_workbook(path, read_only=True, data_only=True)
    rows_out: list[dict[str, object]] = []
    for sheet_index, ws in enumerate(wb.worksheets, start=1):
        sample_rows = []
        for row in ws.iter_rows(min_row=1, max_row=min(ws.max_row or 1, 30), max_col=min(ws.max_column or 1, 30), values_only=True):
            sample_rows.append([b23.clean_text(v) for v in row])
        header_row, headers = b23.likely_header_row(sample_rows)
        if not header_row or not headers:
            continue
        categories = [b23.categorize_header(h) for h in headers]
        text_positions = [i + 1 for i, c in enumerate(categories) if c in {"notes_text", "work_text", "issue_text"}]
        if not text_positions:
            continue
        max_col = max(len(headers), max(text_positions))
        for row_number, row in enumerate(ws.iter_rows(min_row=header_row + 1, max_col=max_col, values_only=True), start=header_row + 1):
            row_values = [b23.clean_text(v) for v in row]
            text_chunks = [
                row_values[pos - 1]
                for pos in text_positions
                if pos - 1 < len(row_values) and len(row_values[pos - 1]) >= 8
            ]
            if not text_chunks:
                continue
            asset_key, asset_status = b23.extract_asset_key(row_values, categories)
            code_key, code_status = b23.extract_code_key(row_values, categories)
            duration_days = parse_duration_days(row_values)
            text_signature = b23.prefixed_hash("|".join(sorted(b23.normalize_text(v) for v in text_chunks)), "TEXTSIG", 12)
            base_key = "|".join([family, doc_type, asset_key, code_key, text_signature])
            dated_key = "|".join([base_key, snapshot_bucket])
            if snapshot_date and duration_days is not None and asset_status == "present":
                incident_start = snapshot_date - timedelta(days=round(duration_days))
                refined_basis = "|".join([family, doc_type, asset_key, code_key, incident_start.isoformat()])
                refined_method = "duration_estimated_incident_start"
            else:
                refined_basis = dated_key
                refined_method = "date_sensitive_fallback"
            rows_out.append(
                {
                    "snapshot_row_id": b23.prefixed_hash(f"{file_key}|{sheet_index}|{row_number}|{text_signature}", "B2ROW", 16),
                    "estimated_event_key_with_snapshot_date": b23.prefixed_hash(dated_key, "B2EVENTDAY", 12),
                    "refined_event_key": short_hash(refined_basis, "B25EVENT", 12),
                    "refined_grouping_method": refined_method,
                    "file_key": file_key,
                    "sheet_key": b23.prefixed_hash(f"{file_key}|{sheet_index}", "B2SHEET", 12),
                    "family": family,
                    "doc_type": doc_type,
                    "snapshot_date_bucket": snapshot_bucket,
                    "asset_ref_status": asset_status,
                    "code_ref_status": code_status,
                    "duration_status": "present" if duration_days is not None else "missing",
                    "text_row_count": 1,
                    "normalized_text": b23.normalize_text(" ".join(text_chunks)),
                }
            )
    wb.close()
    return rows_out


def term_index(terms: list[dict[str, object]]) -> tuple[dict[str, list[dict[str, object]]], int]:
    index: dict[str, list[dict[str, object]]] = defaultdict(list)
    max_len = 1
    for term in terms:
        norm = str(term["term_norm"])
        if norm:
            index[norm].append(term)
            max_len = max(max_len, len(norm.split()))
    return index, max_len


def text_ngrams(normalized_text: str, max_len: int) -> set[str]:
    tokens = normalized_text.split()
    grams: set[str] = set()
    for size in range(1, min(max_len, len(tokens)) + 1):
        for start in range(0, len(tokens) - size + 1):
            grams.add(" ".join(tokens[start : start + size]))
    return grams


def build_group_hits(group_rows: list[dict[str, object]], terms: list[dict[str, object]]) -> list[dict[str, object]]:
    lookup, max_len = term_index(terms)
    groups: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in group_rows:
        groups[str(row["refined_event_key"])].append(row)
    hits: list[dict[str, object]] = []
    for event_key, rows in groups.items():
        normalized_text = " ".join(str(row["normalized_text"]) for row in rows)
        matched_terms = []
        for gram in text_ngrams(normalized_text, max_len):
            matched_terms.extend(lookup.get(gram, []))
        seen: set[tuple[str, str, str]] = set()
        for term in matched_terms:
            target = str(term["target"])
            key = (target, str(term["canonical_concept_id"]), str(term["term_key"]))
            if key in seen:
                continue
            seen.add(key)
            status = "b25_grouped_text_candidate_requires_review"
            if target == "Symptom":
                status = "b25_symptom_like_candidate_source_unconfirmed"
            first = rows[0]
            hits.append(
                {
                    "record_id": short_hash(f"{event_key}|{target}|{term['canonical_concept_id']}|{term['term_key']}", "REC", 16),
                    "physical_record_id": event_key,
                    "refined_event_key": event_key,
                    "target": target,
                    "evidence_type": "expert_inference",
                    "tier": "silver-medium",
                    "status": status,
                    "source_path": str(first["family"]),
                    "source_text_field": "xlsx_snapshot.grouped_text",
                    "stratum": "event_structural",
                    "site_key": "SITE-unresolved_snapshot_family",
                    "contractor_path": "CONTRACTOR_PATH_B2_SNAPSHOT",
                    "concept_id": str(term["canonical_concept_id"]),
                    "confidence": "lexical_high_grouped_text_hit",
                    "label_generation_method": "b2_5_grouped_snapshot_lexical_layer_v2_rule",
                    "evaluation_independence": "derived_from_rules",
                    "can_support_contractual_denominator": False,
                    "can_support_proxy_denominator": False,
                    "notes": "Candidate generated after grouping and text concatenation. Requires review; grouping simulates upstream event constitution.",
                    "raw_operational_values_emitted": False,
                    "term_key": str(term["term_key"]),
                    "canonical_concept_key": str(term["canonical_concept_key"]),
                    "match_score": float(term["match_score"]),
                    "embedding_model": str(term["embedding_model"]),
                    "doc_type": str(first["doc_type"]),
                    "family": str(first["family"]),
                    "group_text_row_count": len(rows),
                    "grouping_method": str(first["refined_grouping_method"]),
                }
            )
    return hits


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def assert_sanitized(paths: list[Path]) -> None:
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="ignore")
        hits = [pattern.pattern for pattern in RAW_PATTERNS if pattern.search(text)]
        if hits:
            raise RuntimeError(f"Sanitization failed for {path.name}: {hits}")


def main() -> None:
    b22b = json.loads((B22_DIR / "b22b_dedup_method_reconciliation_summary_sanitized.json").read_text(encoding="utf-8"))
    baseline = int(b22b["recommended_b2_denominator_rows"])
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    files: list[Path] = []
    for root in SOURCE_ROOTS:
        files.extend(sorted(root.rglob("*.xls*")))
    group_rows: list[dict[str, object]] = []
    for path in sorted(files):
        group_rows.extend(iter_groupable_text_rows(path))
    terms = b23.load_high_confidence_terms()
    hits = build_group_hits(group_rows, terms)

    groups = {str(row["refined_event_key"]) for row in group_rows}
    duration_groups = {
        str(row["refined_event_key"])
        for row in group_rows
        if row["refined_grouping_method"] == "duration_estimated_incident_start"
    }
    by_doc = []
    for doc_type in sorted({str(row["doc_type"]) for row in group_rows}):
        subset = [row for row in group_rows if row["doc_type"] == doc_type]
        doc_groups = {str(row["refined_event_key"]) for row in subset}
        by_doc.append(
            {
                "doc_type": doc_type,
                "snapshot_text_rows": len(subset),
                "baseline_date_sensitive_events": len({str(row["estimated_event_key_with_snapshot_date"]) for row in subset}),
                "refined_events": len(doc_groups),
                "refined_compression_ratio": round(len(subset) / len(doc_groups), 6) if doc_groups else 0,
                "duration_present_rows": sum(row["duration_status"] == "present" for row in subset),
                "duration_grouped_events": len({str(row["refined_event_key"]) for row in subset if row["refined_grouping_method"] == "duration_estimated_incident_start"}),
            }
        )

    df = pd.DataFrame(hits)
    if df.empty:
        by_target = pd.DataFrame()
        target_counts = {}
    else:
        by_target = (
            df.groupby(["target", "status"], dropna=False)
            .agg(
                evidence_rows=("record_id", "size"),
                refined_event_units=("refined_event_key", "nunique"),
                canonical_concepts=("concept_id", "nunique"),
                term_keys=("term_key", "nunique"),
                grouped_text_rows=("group_text_row_count", "sum"),
            )
            .reset_index()
            .sort_values(["target", "status"])
        )
        by_target["raw_operational_values_emitted"] = False
        target_counts = df.groupby("target")["refined_event_key"].nunique().to_dict()

    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "pass_id": "B2.5",
        "task_type": "snapshot_grouping_refinement_and_reanchor",
        "files_scanned": len(files),
        "baseline_date_sensitive_events": baseline,
        "snapshot_text_rows": len(group_rows),
        "refined_events": len(groups),
        "refined_vs_baseline_delta": len(groups) - baseline,
        "duration_present_rows": sum(row["duration_status"] == "present" for row in group_rows),
        "duration_grouped_events": len(duration_groups),
        "fallback_grouped_events": len(groups) - len(duration_groups),
        "evidence_rows_after_reanchor": len(hits),
        "refined_event_units_with_any_candidate": int(df["refined_event_key"].nunique()) if not df.empty else 0,
        "record_target_units_with_any_candidate": int(df[["refined_event_key", "target"]].drop_duplicates().shape[0]) if not df.empty else 0,
        "target_refined_event_counts": {str(k): int(v) for k, v in sorted(target_counts.items())},
        "contractual_denominator_supported": False,
        "proxy_denominator_candidate_units_after_review": 0,
        "scope_note": "Grouping simulates the upstream event constitution role that would belong to SyncHub in production. It is needed here only to define auditable B2 event units for the POC.",
        "raw_operational_values_emitted": False,
    }

    write_csv(
        OUTPUT_DIR / "b25_grouped_snapshot_rows_sanitized.csv",
        group_rows,
        [
            "snapshot_row_id",
            "estimated_event_key_with_snapshot_date",
            "refined_event_key",
            "refined_grouping_method",
            "file_key",
            "sheet_key",
            "family",
            "doc_type",
            "snapshot_date_bucket",
            "asset_ref_status",
            "code_ref_status",
            "duration_status",
            "text_row_count",
        ],
    )
    write_csv(
        OUTPUT_DIR / "b25_grouping_by_doc_type_sanitized.csv",
        by_doc,
        [
            "doc_type",
            "snapshot_text_rows",
            "baseline_date_sensitive_events",
            "refined_events",
            "refined_compression_ratio",
            "duration_present_rows",
            "duration_grouped_events",
        ],
    )
    fieldnames = [
        "record_id",
        "physical_record_id",
        "refined_event_key",
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
        "term_key",
        "canonical_concept_key",
        "match_score",
        "embedding_model",
        "doc_type",
        "family",
        "group_text_row_count",
        "grouping_method",
    ]
    write_csv(OUTPUT_DIR / "b25_grouped_reanchored_evidence_sanitized.csv", hits, fieldnames)
    by_target.to_csv(OUTPUT_DIR / "b25_grouped_reanchored_by_target_sanitized.csv", index=False)
    (OUTPUT_DIR / "b25_grouping_refinement_summary_sanitized.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    doc_lines = [
        f"| {row['doc_type']} | {row['snapshot_text_rows']} | {row['baseline_date_sensitive_events']} | {row['refined_events']} | {row['refined_compression_ratio']} | {row['duration_present_rows']} | {row['duration_grouped_events']} |"
        for row in by_doc
    ]
    target_lines = []
    if not by_target.empty:
        for row in by_target.itertuples(index=False):
            target_lines.append(
                f"| {row.target} | {row.status} | {int(row.evidence_rows)} | {int(row.refined_event_units)} | {int(row.canonical_concepts)} | {int(row.grouped_text_rows)} |"
            )
    memo = "\n".join(
        [
            "# B2.5 Grouping Refinement",
            "",
            "## Scope",
            "",
            "This pass refines B2 event grouping and re-anchors lexical evidence on concatenated group text. It does not emit raw operational values and does not promote any candidate to a denominator.",
            "",
            "## Grouping Comparison",
            "",
            f"- Baseline date-sensitive events from B2.2b: `{summary['baseline_date_sensitive_events']}`",
            f"- Refined events: `{summary['refined_events']}`",
            f"- Refined minus baseline delta: `{summary['refined_vs_baseline_delta']}`",
            f"- Duration-present rows: `{summary['duration_present_rows']}`",
            f"- Duration-grouped events: `{summary['duration_grouped_events']}`",
            f"- Fallback grouped events: `{summary['fallback_grouped_events']}`",
            "",
            "## By Document Type",
            "",
            "| doc_type | snapshot_text_rows | baseline_date_sensitive_events | refined_events | refined_compression_ratio | duration_present_rows | duration_grouped_events |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
            *doc_lines,
            "",
            "## Re-Anchored Evidence By Target",
            "",
            "| target | status | evidence_rows | refined_event_units | canonical_concepts | grouped_text_rows |",
            "| --- | --- | ---: | ---: | ---: | ---: |",
            *target_lines,
            "",
            "## Interpretation",
            "",
            "The refined grouping is conservative where duration is unavailable. Duration-derived incident starts are used only when a parsable duration and asset reference are present; all other rows retain date-sensitive fallback grouping.",
            "",
            "Grouping simulates the behavior that would belong to SyncHub in production. It is performed here only because STINT_1 needs constituted event units before defining reviewable evidence.",
            "",
            "raw_operational_values_emitted: false",
            "",
        ]
    )
    (OUTPUT_DIR / "b25_grouping_refinement_memo.md").write_text(memo, encoding="utf-8")
    assert_sanitized(list(OUTPUT_DIR.glob("b25_*")))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
