"""T3.5.3 NOTES semantic extraction.

This pass extracts candidate maintenance semantics from Path A NOTES text.
Raw NOTES text remains internal. Versioned outputs contain stable keys, counts,
families, confidence flags, provenance, and no raw operational values.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from asset_ml_feasibility.parsers.pdf_assets_of_concern import stable_hash  # noqa: E402


INTERNAL_REPORTS_DIR = PROJECT_ROOT / "reports" / "internal"
PATH_A_DIR = PROJECT_ROOT / "stint-1-evidence-ground-truth" / "phase_3_path_a_faultcodes"
OUTPUT_DIR = PATH_A_DIR / "outputs"
INTERNAL_OUTPUT_DIR = INTERNAL_REPORTS_DIR / "path_a_repair"

NOTES_INTERNAL_PATH = INTERNAL_OUTPUT_DIR / "f352b_notes_region_text_internal.csv"
NOTES_COVERAGE_PATH = OUTPUT_DIR / "f352b_notes_region_coverage_sanitized.csv"

KNOWN_POSITIVE_MARKERS = {
    "2025-12-04": ["WTG 26", "PCH", "accumulator"],
    "2026-08-05": ["T48", "Yaw Limit", "T30", "T33", "annual maintenance", "T9", "blade repair"],
}

COMPONENT_PATTERNS = {
    "blade": r"\bblade\b",
    "yaw": r"\byaw\b",
    "pitch": r"\bpitch\b",
    "hydraulic": r"\bhydraulic\b|\baccumulator\b",
    "brake": r"\bbrake\b",
    "generator": r"\bgenerator\b|\bgen\b",
    "converter": r"\bconverter\b|\binverter\b|\bthyristor\b",
    "gearbox": r"\bgearbox\b|\bgbx\b|\btransmission\b",
    "bearing": r"\bbearing\b|\bbrg\b",
    "tower": r"\btower\b",
    "transformer": r"\btransformer\b|\bxfmr\b",
    "sensor": r"\bsensor\b|\bswitch\b|\blimit switch\b",
    "communication": r"\bcomm(?:unication)?\b|\bnetwork\b",
}

ACTION_PATTERNS = {
    "repair": r"\brepair(?:ed|ing)?\b",
    "maintenance": r"\bmaintenance\b|\bannual\b|\bpm\b",
    "replace": r"\breplac(?:e|ed|ing|ement)\b",
    "inspect": r"\binspect(?:ed|ion|ing)?\b|\bcheck(?:ed|ing)?\b",
    "troubleshoot": r"\btroubleshoot(?:ing)?\b|\bdiagnos(?:e|is|tic)",
    "reset": r"\breset\b|\brestart\b",
    "monitor": r"\bmonitor(?:ed|ing)?\b",
    "offline_or_down": r"\boffline\b|\bdown\b|\bout of service\b",
    "work_planned": r"\bplanned\b|\bscheduled\b",
}

CONDITION_PATTERNS = {
    "fault": r"\bfault\b",
    "alarm": r"\balarm\b",
    "voltage": r"\bvoltage\b|\bvolt\b",
    "vibration": r"\bvibration\b",
    "damage": r"\bdamage\b|\bcrack\b|\bleak\b|\bwear\b|\bfailed?\b",
    "limit": r"\blimit\b",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def as_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value)


def normalize_line(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def split_note_lines(text: str) -> list[str]:
    lines: list[str] = []
    for raw_line in as_text(text).splitlines():
        line = normalize_line(raw_line)
        if not line:
            continue
        if re.search(r"\bUTC\b", line, flags=re.IGNORECASE):
            continue
        if re.fullmatch(r"\d+\s+entries?", line, flags=re.IGNORECASE):
            continue
        lines.append(line)
    return lines


def find_matches(patterns: dict[str, str], text: str) -> list[str]:
    lower_text = text.lower()
    return sorted([name for name, pattern in patterns.items() if re.search(pattern, lower_text)])


def find_asset_refs(text: str) -> list[str]:
    refs = set()
    for match in re.finditer(r"\b(?:WTG|T)\s*[-#]?\s*(\d{1,3})\b", text, flags=re.IGNORECASE):
        refs.add(match.group(1).lstrip("0") or "0")
    return sorted(refs, key=lambda value: int(value) if value.isdigit() else 9999)


def contractor_candidate(text: str) -> str:
    if "-" not in text:
        return ""
    prefix = normalize_line(text.split("-", 1)[0])
    if not prefix or re.search(r"\b(?:WTG|T)\s*[-#]?\s*\d{1,3}\b", prefix, re.IGNORECASE):
        return ""
    if len(prefix.split()) > 4:
        return ""
    return prefix


def join_confidence(asset_refs: list[str], recognized_core: bool) -> str:
    if not asset_refs:
        return "none"
    if len(asset_refs) == 1 and recognized_core:
        return "medium_requires_site_validation"
    if len(asset_refs) == 1:
        return "low_template_not_core"
    return "low_multiple_asset_refs"


def candidate_targets(component_hits: list[str], action_hits: list[str], condition_hits: list[str]) -> list[str]:
    targets = set()
    if component_hits:
        targets.add("object_part")
    if action_hits:
        targets.add("activity")
    if condition_hits:
        targets.add("damage")
    return sorted(targets)


def positive_sample_label(path: str) -> str:
    for label in KNOWN_POSITIVE_MARKERS:
        if label in path:
            return label
    return ""


def build_records(notes: pd.DataFrame, coverage: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    merged = notes.merge(
        coverage[["path_hash", "file_hash", "notes_region_nonempty"]],
        on=["path_hash", "file_hash"],
        how="left",
    )
    sanitized_records: list[dict[str, object]] = []
    internal_records: list[dict[str, object]] = []
    positive_records: list[dict[str, object]] = []

    for row in merged.itertuples(index=False):
        raw_path = as_text(getattr(row, "relative_path"))
        text = as_text(getattr(row, "notes_region_text"))
        lines = split_note_lines(text)
        site_key = "SITE-" + stable_hash("/".join(raw_path.split("/")[:5]), 10)
        sample_label = positive_sample_label(raw_path)
        if sample_label:
            positive_records.append(
                {
                    "sample_label": sample_label,
                    "path_hash": getattr(row, "path_hash"),
                    "file_hash": getattr(row, "file_hash"),
                    "template_variant": getattr(row, "template_variant"),
                    "notes_region_nonempty": bool(getattr(row, "notes_region_nonempty")),
                    **{
                        f"marker_{index + 1}_found": marker.lower() in text.lower()
                        for index, marker in enumerate(KNOWN_POSITIVE_MARKERS[sample_label])
                    },
                    "raw_operational_values_emitted": False,
                }
            )

        for line_index, line in enumerate(lines, start=1):
            asset_refs = find_asset_refs(line)
            component_hits = find_matches(COMPONENT_PATTERNS, line)
            action_hits = find_matches(ACTION_PATTERNS, line)
            condition_hits = find_matches(CONDITION_PATTERNS, line)
            contractor = contractor_candidate(line)
            targets = candidate_targets(component_hits, action_hits, condition_hits)
            line_key = "NOTE-LINE-" + stable_hash(f"{getattr(row, 'path_hash')}|{line_index}|{line}", 12)

            base = {
                "note_line_key": line_key,
                "path_hash": getattr(row, "path_hash"),
                "file_hash": getattr(row, "file_hash"),
                "template_variant": getattr(row, "template_variant"),
                "site_key": site_key,
                "stratum": "event_structural_notes",
                "source_text_field": "pdf_notes_region",
                "evidence_type": "expert_inference",
                "tier": "silver-medium",
                "status": "candidate_requires_review",
                "label_generation_method": "notes_regex_semantic_extraction_v1",
                "evaluation_independence": "derived_from_rules",
                "raw_operational_values_emitted": False,
            }
            sanitized_records.append(
                base
                | {
                    "line_hash": stable_hash(line, 16),
                    "line_char_count": len(line),
                    "line_token_count": len(line.split()),
                    "candidate_asset_ref_count": len(asset_refs),
                    "candidate_asset_ref_keys": ";".join(
                        "ASSET-REF-" + stable_hash(ref, 8) for ref in asset_refs
                    ),
                    "join_confidence": join_confidence(asset_refs, bool(getattr(row, "recognized_core_sections"))),
                    "contractor_candidate_key": "CONTRACTOR-" + stable_hash(contractor, 8)
                    if contractor
                    else "",
                    "component_families": ";".join(component_hits),
                    "action_families": ";".join(action_hits),
                    "condition_families": ";".join(condition_hits),
                    "candidate_targets": ";".join(targets),
                    "has_semantic_signal": bool(targets or asset_refs or contractor),
                }
            )
            internal_records.append(
                base
                | {
                    "relative_path": raw_path,
                    "note_line_text": line,
                    "asset_refs": ";".join(asset_refs),
                    "contractor_candidate": contractor,
                    "component_families": ";".join(component_hits),
                    "action_families": ";".join(action_hits),
                    "condition_families": ";".join(condition_hits),
                    "candidate_targets": ";".join(targets),
                    "raw_operational_values_emitted": True,
                }
            )

    return pd.DataFrame(sanitized_records), pd.DataFrame(internal_records), pd.DataFrame(positive_records)


def summarise(sanitized: pd.DataFrame, notes: pd.DataFrame) -> dict[str, object]:
    nonempty_files = int(notes["notes_region_text"].fillna("").str.strip().ne("").sum())
    signal_rows = int(sanitized["has_semantic_signal"].sum()) if not sanitized.empty else 0
    return {
        "created_at_utc": utc_now(),
        "pass_id": "T3.5.3",
        "input_files": int(notes.shape[0]),
        "notes_region_nonempty_files": nonempty_files,
        "note_lines_extracted": int(sanitized.shape[0]),
        "note_lines_with_semantic_signal": signal_rows,
        "note_lines_with_asset_ref": int((sanitized["candidate_asset_ref_count"] > 0).sum())
        if not sanitized.empty
        else 0,
        "note_lines_with_candidate_contractor": int(
            sanitized["contractor_candidate_key"].fillna("").ne("").sum()
        )
        if not sanitized.empty
        else 0,
        "note_lines_with_candidate_targets": int(sanitized["candidate_targets"].fillna("").ne("").sum())
        if not sanitized.empty
        else 0,
        "raw_operational_values_emitted": False,
    }


def explode_summary(sanitized: pd.DataFrame, column: str, output_name: str) -> pd.DataFrame:
    if sanitized.empty:
        return pd.DataFrame(columns=[output_name, "note_line_count", "raw_operational_values_emitted"])
    values = []
    for item in sanitized[column].fillna(""):
        for part in str(item).split(";"):
            part = part.strip()
            if part:
                values.append(part)
    counts = Counter(values)
    return pd.DataFrame(
        [
            {output_name: key, "note_line_count": count, "raw_operational_values_emitted": False}
            for key, count in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
        ]
    )


def build_memo(summary: dict[str, object], by_variant: pd.DataFrame, by_target: pd.DataFrame) -> str:
    variant_rows = []
    for row in by_variant.itertuples(index=False):
        variant_rows.append(
            "| "
            + " | ".join(
                [
                    str(getattr(row, "template_variant")),
                    str(getattr(row, "files")),
                    str(getattr(row, "notes_nonempty_files")),
                    str(getattr(row, "note_lines")),
                    str(getattr(row, "semantic_signal_lines")),
                    str(getattr(row, "asset_ref_lines")),
                ]
            )
            + " |"
        )
    target_rows = []
    for row in by_target.itertuples(index=False):
        target_rows.append(
            "| "
            + " | ".join(
                [
                    str(getattr(row, "candidate_target")),
                    str(getattr(row, "note_line_count")),
                ]
            )
            + " |"
        )
    return "\n".join(
        [
            "# T3.5.3 NOTES Semantic Extraction",
            "",
            "## Scope",
            "",
            "This pass extracts candidate semantics from the spatial `NOTES` region. It does not promote any candidate to a denominator and does not emit raw note text in versioned outputs.",
            "",
            "## Control Rule",
            "",
            "No zero is interpreted until the extractor is validated against a known positive case. This pass consumes the `T3.5.2b` positive-control diagnostic where the known samples were recovered.",
            "",
            "## Summary",
            "",
            f"- Input files: `{summary['input_files']}`",
            f"- NOTES region non-empty files: `{summary['notes_region_nonempty_files']}`",
            f"- Note lines extracted: `{summary['note_lines_extracted']}`",
            f"- Note lines with semantic signal: `{summary['note_lines_with_semantic_signal']}`",
            f"- Note lines with candidate asset reference: `{summary['note_lines_with_asset_ref']}`",
            f"- Note lines with candidate contractor key: `{summary['note_lines_with_candidate_contractor']}`",
            f"- Note lines with candidate target family: `{summary['note_lines_with_candidate_targets']}`",
            "",
            "## Coverage By Template Variant",
            "",
            "| template_variant | files | notes_nonempty_files | note_lines | semantic_signal_lines | asset_ref_lines |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
            *variant_rows,
            "",
            "## Candidate Target Families",
            "",
            "| candidate_target | note_line_count |",
            "| --- | ---: |",
            *target_rows,
            "",
            "## Interpretation",
            "",
            "`NOTES` contains real Path A prose and should be used for candidate Object Part / Activity / Damage support. All extracted links remain `expert_inference`, `silver-medium`, `derived_from_rules`, and `candidate_requires_review`.",
            "",
            "`Txx -> asset` links are candidate joins only. They carry `join_confidence` and must be validated against `site_key` before being treated as resolved.",
            "",
            "## Next Control",
            "",
            "Proceed to `T3.5.4` snapshot deduplication using `site_key + asset/code + incident_start_estimated window`, not raw row counts.",
            "",
        ]
    )


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    INTERNAL_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    notes = pd.read_csv(NOTES_INTERNAL_PATH)
    coverage = pd.read_csv(NOTES_COVERAGE_PATH)
    sanitized, internal, positives = build_records(notes, coverage)
    summary = summarise(sanitized, notes)

    by_variant = (
        sanitized.groupby("template_variant", dropna=False)
        .agg(
            files=("file_hash", "nunique"),
            notes_nonempty_files=("file_hash", "nunique"),
            note_lines=("note_line_key", "size"),
            semantic_signal_lines=("has_semantic_signal", "sum"),
            asset_ref_lines=("candidate_asset_ref_count", lambda values: int((values > 0).sum())),
        )
        .reset_index()
        .sort_values(["note_lines", "template_variant"], ascending=[False, True])
    )
    by_variant["raw_operational_values_emitted"] = False

    by_target = explode_summary(sanitized, "candidate_targets", "candidate_target")
    by_component = explode_summary(sanitized, "component_families", "component_family")
    by_action = explode_summary(sanitized, "action_families", "action_family")
    by_condition = explode_summary(sanitized, "condition_families", "condition_family")

    sanitized_path = OUTPUT_DIR / "f353_notes_semantics_sanitized.csv"
    variant_path = OUTPUT_DIR / "f353_notes_semantics_by_variant_sanitized.csv"
    target_path = OUTPUT_DIR / "f353_notes_semantics_by_target_sanitized.csv"
    component_path = OUTPUT_DIR / "f353_notes_semantics_component_families_sanitized.csv"
    action_path = OUTPUT_DIR / "f353_notes_semantics_action_families_sanitized.csv"
    condition_path = OUTPUT_DIR / "f353_notes_semantics_condition_families_sanitized.csv"
    positive_path = OUTPUT_DIR / "f353_notes_semantics_positive_control_sanitized.csv"
    summary_path = OUTPUT_DIR / "f353_notes_semantics_summary_sanitized.json"
    memo_path = OUTPUT_DIR / "f353_notes_semantics_memo.md"
    internal_path = INTERNAL_OUTPUT_DIR / "f353_notes_semantics_internal.csv"

    sanitized.to_csv(sanitized_path, index=False)
    by_variant.to_csv(variant_path, index=False)
    by_target.to_csv(target_path, index=False)
    by_component.to_csv(component_path, index=False)
    by_action.to_csv(action_path, index=False)
    by_condition.to_csv(condition_path, index=False)
    positives.to_csv(positive_path, index=False)
    internal.to_csv(internal_path, index=False)

    summary["outputs"] = {
        "memo": str(memo_path),
        "notes_semantics": str(sanitized_path),
        "by_variant": str(variant_path),
        "by_target": str(target_path),
        "positive_control": str(positive_path),
    }
    summary["internal_outputs_ignored"] = {"notes_semantics_internal": str(internal_path)}
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    memo_path.write_text(build_memo(summary, by_variant, by_target), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
