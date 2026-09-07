"""T3.5.6 Path A integrated code + NOTES crosswalk.

T3.5.5 scored the cleaned code universe and used NOTES only as context. This
pass emits the missing NOTES-derived candidate rows and marks event/target
convergence between code evidence and NOTES evidence.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]
STINT_ROOT = PROJECT_ROOT / "stint-1-evidence-ground-truth"
PATH_A_DIR = STINT_ROOT / "phase_3_path_a_faultcodes"
OUTPUT_DIR = PATH_A_DIR / "outputs"
INTERNAL_DIR = PROJECT_ROOT / "reports" / "internal"
INTERNAL_PATH_A_DIR = INTERNAL_DIR / "path_a_repair"

PDF_ROWS = INTERNAL_DIR / "pdf_assets_of_concern_rows.csv"
ROW_ASSIGNMENTS = OUTPUT_DIR / "f354_snapshot_row_assignments_sanitized.csv"
EVENTS = OUTPUT_DIR / "f354_estimated_events_sanitized.csv"
CODE_CROSSWALK = OUTPUT_DIR / "f355_path_a_crosswalk_v2_sanitized.csv"
NOTES_SANITIZED = OUTPUT_DIR / "f353_notes_semantics_sanitized.csv"
NOTES_INTERNAL = INTERNAL_PATH_A_DIR / "f353_notes_semantics_internal.csv"

NOTES_TARGETS = {"activity", "object_part", "damage"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_hash(value: object, length: int = 16) -> str:
    import hashlib

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


def target_label(value: str) -> str:
    mapping = {
        "activity": "Activity",
        "object_part": "Object Part",
        "damage": "Damage",
    }
    return mapping.get(value, value)


def load_event_row_map() -> pd.DataFrame:
    rows = pd.read_csv(PDF_ROWS)
    rows["fault_code_norm"] = rows["fault_code"].map(as_text)
    rows = rows[rows["fault_code_norm"].ne("") & rows["fault_code_norm"].ne("-")].copy()
    rows["site_key"] = rows["site_text"].map(lambda value: prefixed_hash(as_text(value), "SITE", 10))
    rows["path_site_key"] = rows["relative_path"].map(
        lambda value: prefixed_hash("/".join(as_text(value).split("/")[:5]), "SITE", 10)
    )
    rows["asset_key"] = rows["asset"].map(lambda value: prefixed_hash(as_text(value), "ASSET", 10))
    rows["code_key"] = rows["fault_code_norm"].map(lambda value: prefixed_hash(value, "CODE", 10))
    rows["row_key"] = rows.apply(
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

    assignments = pd.read_csv(ROW_ASSIGNMENTS)
    event_rows = rows.merge(
        assignments[["row_key", "estimated_event_key"]],
        on="row_key",
        how="inner",
    )
    return event_rows[
        ["estimated_event_key", "path_hash", "file_hash", "site_key", "path_site_key", "asset_key", "row_key"]
    ].drop_duplicates()


def split_targets(value: object) -> list[str]:
    targets = []
    for part in as_text(value).split(";"):
        part = part.strip()
        if part in NOTES_TARGETS:
            targets.append(part)
    return sorted(set(targets))


def split_asset_refs(value: object) -> list[str]:
    refs = []
    for part in as_text(value).split(";"):
        part = part.strip()
        if part:
            refs.append(prefixed_hash(part, "ASSET", 10))
    return sorted(set(refs))


def build_notes_event_candidates(event_rows: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    notes_s = pd.read_csv(NOTES_SANITIZED)
    notes_i = pd.read_csv(NOTES_INTERNAL)[["note_line_key", "asset_refs"]]
    notes = notes_s.merge(notes_i, on="note_line_key", how="left")
    notes["target_list"] = notes["candidate_targets"].map(split_targets)
    notes["asset_key_list"] = notes["asset_refs"].map(split_asset_refs)
    notes = notes[
        notes["target_list"].map(bool)
        & notes["asset_key_list"].map(bool)
        & notes["join_confidence"].astype(str).ne("none")
    ].copy()

    records: list[dict[str, object]] = []
    event_lookup = event_rows.groupby(["file_hash", "path_site_key"])
    event_namespace = events.set_index("estimated_event_key")["namespace"].to_dict()
    for note in notes.itertuples(index=False):
        key = (note.file_hash, note.site_key)
        candidates = pd.DataFrame()
        if key in event_lookup.groups:
            candidates = event_lookup.get_group(key)
            asset_keys = set(note.asset_key_list)
            candidates = candidates[candidates["asset_key"].isin(asset_keys)]

        if candidates.empty:
            event_keys = [prefixed_hash(f"{note.note_line_key}|notes-only", "PATHA-NOTE-EVENT", 12)]
            namespaces = ["notes_only_event_candidate"]
            join_type = "notes_asset_ref_without_code_event"
            join_confidence = "low_requires_site_asset_validation"
        else:
            event_keys = sorted(candidates["estimated_event_key"].dropna().unique())
            namespaces = [event_namespace.get(event_key, "unknown") for event_key in event_keys]
            join_type = "candidate_asset_ref_join"
            join_confidence = str(note.join_confidence) + "_path_site_confirmed"

        for event_key, namespace in zip(event_keys, namespaces, strict=False):
            for target in note.target_list:
                records.append(
                    {
                        "estimated_event_key": event_key,
                        "target": target_label(target),
                        "evidence_source": "notes_region",
                        "source_row_key": note.note_line_key,
                        "namespace": namespace,
                        "join_type": join_type,
                        "join_confidence": join_confidence,
                        "component_families": note.component_families,
                        "action_families": note.action_families,
                        "condition_families": note.condition_families,
                        "status": "notes_candidate_requires_review",
                        "evidence_type": "expert_inference",
                        "tier": "silver-medium",
                        "label_generation_method": "notes_regex_semantic_extraction_v1",
                        "evaluation_independence": "derived_from_rules",
                        "can_support_contractual_denominator": False,
                        "can_support_proxy_denominator": False,
                        "requires_target_review": True,
                        "raw_operational_values_emitted": False,
                    }
                )
    if not records:
        return pd.DataFrame()
    return pd.DataFrame(records).drop_duplicates()


def build_code_candidates() -> pd.DataFrame:
    code = pd.read_csv(CODE_CROSSWALK)
    code = code[code["status"].astype(str).str.startswith("candidate_", na=False)].copy()
    if code.empty:
        return pd.DataFrame()
    return pd.DataFrame(
        {
            "estimated_event_key": code["estimated_event_key"],
            "target": code["target"],
            "evidence_source": "code_context",
            "source_row_key": code["estimated_event_key"].map(lambda value: prefixed_hash(value, "CODE-SRC", 12)),
            "namespace": code["namespace"],
            "join_type": "same_estimated_event",
            "join_confidence": "not_applicable_code_event",
            "component_families": "",
            "action_families": "",
            "condition_families": "",
            "status": code["status"],
            "evidence_type": code["evidence_type"],
            "tier": code["tier"],
            "label_generation_method": code["label_generation_method"],
            "evaluation_independence": code["evaluation_independence"],
            "can_support_contractual_denominator": False,
            "can_support_proxy_denominator": False,
            "requires_target_review": True,
            "raw_operational_values_emitted": False,
        }
    ).drop_duplicates()


def add_convergence(evidence: pd.DataFrame) -> pd.DataFrame:
    if evidence.empty:
        evidence["event_target_evidence_sources"] = ""
        evidence["has_code_notes_convergence"] = False
        return evidence
    sources = (
        evidence.groupby(["estimated_event_key", "target"])["evidence_source"]
        .apply(lambda values: ";".join(sorted(set(values))))
        .reset_index(name="event_target_evidence_sources")
    )
    evidence = evidence.merge(sources, on=["estimated_event_key", "target"], how="left")
    evidence["has_code_notes_convergence"] = evidence["event_target_evidence_sources"].map(
        lambda value: "code_context" in value and "notes_region" in value
    )
    return evidence


def summarize(evidence: pd.DataFrame, events: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    by_source_target = (
        evidence.groupby(["evidence_source", "target"], dropna=False)
        .agg(rows=("source_row_key", "size"), event_targets=("estimated_event_key", "nunique"))
        .reset_index()
        .sort_values(["evidence_source", "target"])
    )
    by_source_target["raw_operational_values_emitted"] = False

    converged = evidence[evidence["has_code_notes_convergence"]].copy()
    convergence = (
        converged.groupby("target", dropna=False)
        .agg(rows=("source_row_key", "size"), converged_events=("estimated_event_key", "nunique"))
        .reset_index()
        .sort_values("target")
    )
    if convergence.empty:
        convergence = pd.DataFrame(columns=["target", "rows", "converged_events"])
    convergence["raw_operational_values_emitted"] = False

    source_counts = evidence.groupby("evidence_source")["source_row_key"].size().to_dict()
    target_counts = evidence.groupby("target")["source_row_key"].size().to_dict()
    code_event_keys = set(events["estimated_event_key"].dropna().astype(str))
    integrated_event_keys = set(evidence["estimated_event_key"].dropna().astype(str))
    note_only_event_keys = {key for key in integrated_event_keys if key.startswith("PATHA-NOTE-EVENT-")}
    summary = {
        "created_at_utc": utc_now(),
        "pass_id": "T3.5.6",
        "estimated_events_input": int(events["estimated_event_key"].nunique()),
        "integrated_evidence_rows": int(evidence.shape[0]),
        "integrated_event_targets": int(evidence[["estimated_event_key", "target"]].drop_duplicates().shape[0]),
        "code_estimated_events_with_any_integrated_evidence": int(len(integrated_event_keys & code_event_keys)),
        "notes_only_event_candidate_keys": int(len(note_only_event_keys)),
        "event_or_candidate_keys_with_any_integrated_evidence": int(len(integrated_event_keys)),
        "code_candidate_rows": int(source_counts.get("code_context", 0)),
        "notes_candidate_rows": int(source_counts.get("notes_region", 0)),
        "target_candidate_rows": {str(k): int(v) for k, v in sorted(target_counts.items())},
        "converged_event_targets": int(
            evidence.loc[evidence["has_code_notes_convergence"], ["estimated_event_key", "target"]]
            .drop_duplicates()
            .shape[0]
        ),
        "contractual_denominator_supported": False,
        "poc_proxy_denominator_supported": False,
        "raw_operational_values_emitted": False,
    }
    return by_source_target, convergence, summary


def build_memo(summary: dict[str, object], by_source_target: pd.DataFrame, convergence: pd.DataFrame) -> str:
    source_rows = [
        "| " + " | ".join([str(row.evidence_source), str(row.target), str(row.rows), str(row.event_targets)]) + " |"
        for row in by_source_target.itertuples(index=False)
    ]
    convergence_rows = [
        "| " + " | ".join([str(row.target), str(row.rows), str(row.converged_events)]) + " |"
        for row in convergence.itertuples(index=False)
    ]
    return "\n".join(
        [
            "# T3.5.6 Path A Integrated NOTES Crosswalk",
            "",
            "## Scope",
            "",
            "This pass integrates code-derived candidates from `T3.5.5` with NOTES-derived candidates from `T3.5.3`. It fixes the gap where NOTES prose was used only as code context but not emitted as its own evidence source.",
            "",
            "## Summary",
            "",
            f"- Estimated events input: `{summary['estimated_events_input']}`",
            f"- Integrated evidence rows: `{summary['integrated_evidence_rows']}`",
            f"- Integrated event-target pairs: `{summary['integrated_event_targets']}`",
            f"- Code estimated events with any integrated evidence: `{summary['code_estimated_events_with_any_integrated_evidence']}`",
            f"- NOTES-only event candidate keys: `{summary['notes_only_event_candidate_keys']}`",
            f"- Event or candidate keys with any integrated evidence: `{summary['event_or_candidate_keys_with_any_integrated_evidence']}`",
            f"- Code candidate rows: `{summary['code_candidate_rows']}`",
            f"- NOTES candidate rows: `{summary['notes_candidate_rows']}`",
            f"- Converged event-target pairs: `{summary['converged_event_targets']}`",
            f"- Contractual denominator supported: `{summary['contractual_denominator_supported']}`",
            f"- POC proxy denominator supported: `{summary['poc_proxy_denominator_supported']}`",
            "",
            "## By Source And Target",
            "",
            "| evidence_source | target | rows | event_targets |",
            "| --- | --- | ---: | ---: |",
            *source_rows,
            "",
            "## Code + NOTES Convergence",
            "",
            "| target | rows | converged_events |",
            "| --- | ---: | ---: |",
            *convergence_rows,
            "",
            "## Interpretation",
            "",
            "Activity appears only through `NOTES`, as expected. Numeric codes remain weak for Activity because they describe state/condition rather than technician action.",
            "",
            "The integrated evidence includes both deduplicated code-table events and NOTES-only event candidates. These are reported separately so the code event universe is not confused with candidate events created from prose.",
            "",
            "`asset_state` remains separate and is not promoted to Activity Type. All NOTES joins are candidate joins and require target review before denominator use.",
            "",
            "The `910` scoring rows in `T3.5.5` are unrelated to the historical `910` denominator issue; here they are the explicit expansion of the cleaned code event universe.",
            "",
        ]
    )


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    events = pd.read_csv(EVENTS)
    event_rows = load_event_row_map()
    code_candidates = build_code_candidates()
    notes_candidates = build_notes_event_candidates(event_rows, events)
    evidence = pd.concat([code_candidates, notes_candidates], ignore_index=True, sort=False)
    evidence = add_convergence(evidence)
    by_source_target, convergence, summary = summarize(evidence, events)

    evidence_path = OUTPUT_DIR / "f356_path_a_integrated_crosswalk_sanitized.csv"
    source_target_path = OUTPUT_DIR / "f356_path_a_integrated_crosswalk_by_source_target_sanitized.csv"
    convergence_path = OUTPUT_DIR / "f356_path_a_code_notes_convergence_sanitized.csv"
    summary_path = OUTPUT_DIR / "f356_path_a_integrated_crosswalk_summary_sanitized.json"
    memo_path = OUTPUT_DIR / "f356_path_a_integrated_crosswalk_memo.md"

    evidence.to_csv(evidence_path, index=False)
    by_source_target.to_csv(source_target_path, index=False)
    convergence.to_csv(convergence_path, index=False)
    summary["outputs"] = {
        "memo": str(memo_path),
        "integrated_crosswalk": str(evidence_path),
        "by_source_target": str(source_target_path),
        "convergence": str(convergence_path),
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    memo_path.write_text(build_memo(summary, by_source_target, convergence), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
