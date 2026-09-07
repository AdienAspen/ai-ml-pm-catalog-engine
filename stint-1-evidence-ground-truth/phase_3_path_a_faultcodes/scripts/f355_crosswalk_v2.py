"""T3.5.5 Path A crosswalk v2.

Uses the cleaned Path A universe:
- estimated events from snapshot deduplication;
- code namespace partition (`fault_code`, `asset_state`, `undetermined_code`);
- NOTES semantic support as candidate evidence only.

No versioned output emits raw codes, event text, notes, asset ids, site names,
or file paths.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer


PROJECT_ROOT = Path(__file__).resolve().parents[3]
STINT_ROOT = PROJECT_ROOT / "stint-1-evidence-ground-truth"
PATH_A_DIR = STINT_ROOT / "phase_3_path_a_faultcodes"
OUTPUT_DIR = PATH_A_DIR / "outputs"
INTERNAL_DIR = PROJECT_ROOT / "reports" / "internal"
INTERNAL_PATH_A_DIR = INTERNAL_DIR / "path_a_repair"

PDF_ROWS = INTERNAL_DIR / "pdf_assets_of_concern_rows.csv"
EVENTS = OUTPUT_DIR / "f354_estimated_events_sanitized.csv"
ROW_ASSIGNMENTS = OUTPUT_DIR / "f354_snapshot_row_assignments_sanitized.csv"
NOTES_INTERNAL = INTERNAL_PATH_A_DIR / "f353_notes_semantics_internal.csv"
CANONICAL_VOCAB = (
    STINT_ROOT / "phase_1_lexical" / "outputs" / "canonical_vocabulary" / "canonical_vocabulary_v1_working.csv"
)
EXTERNAL_FAILURE_VOCAB = (
    STINT_ROOT / "phase_1_lexical" / "outputs" / "canonical_vocabulary" / "external_failure_vocabulary_v1.csv"
)
TRANSLATION_ALIASES_ES = (
    STINT_ROOT / "phase_1_lexical" / "outputs" / "canonical_vocabulary" / "translation_aliases_es_v1.csv"
)

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
FAULT_TARGETS = ["Object Part", "Damage", "Cause"]
NOTES_TARGETS = ["Object Part", "Damage", "Activity"]
TARGET_THRESHOLDS = {
    "Object Part": 0.67,
    "Damage": 0.70,
    "Cause": 0.72,
}
HIGH_MARGIN = 0.05


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


def normalize_text(value: object) -> str:
    text = as_text(value).lower()
    text = re.sub(r"[^a-z0-9áéíóúüñ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def redacted_text(value: object) -> str:
    text = as_text(value)
    text = re.sub(r"\b\d+(?:[.,:/-]\d+)*\b", "<NUM>", text)
    text = re.sub(r"\b[A-Z]{2,}[-_/]?[A-Z0-9]{2,}\b", "<CODE>", text)
    return re.sub(r"\s+", " ", text).strip()[:180]


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def load_vocab() -> pd.DataFrame:
    frames = []
    for path in [CANONICAL_VOCAB, EXTERNAL_FAILURE_VOCAB]:
        if path.exists():
            frames.append(pd.read_csv(path))
    vocab = pd.concat(frames, ignore_index=True, sort=False)
    vocab = vocab[vocab["target"].isin(FAULT_TARGETS)].copy()
    vocab = vocab[vocab["canonical_concept"].notna()].copy()
    vocab["match_text"] = vocab["canonical_concept"]
    vocab["match_text_source"] = "canonical_concept"

    if TRANSLATION_ALIASES_ES.exists():
        aliases = pd.read_csv(TRANSLATION_ALIASES_ES)
        alias_rows = []
        for _, row in aliases[aliases["target"].isin(FAULT_TARGETS)].iterrows():
            alias_rows.append(
                {
                    "concept_id": row.get("canonical_concept_id", ""),
                    "canonical_concept_key": row.get("canonical_concept_key", ""),
                    "canonical_concept": row.get("canonical_alias_es", ""),
                    "target": row.get("target", ""),
                    "namespace": row.get("namespace", ""),
                    "target_field": row.get("target_field", ""),
                    "vocabulary_owner": row.get("vocabulary_owner", ""),
                    "semantic_level": row.get("semantic_level", ""),
                    "tier": row.get("tier", "silver-medium"),
                    "evidence_type": row.get("evidence_type", "expert_inference"),
                    "match_text": row.get("canonical_alias_es", ""),
                    "match_text_source": "translation_alias_es",
                }
            )
        if alias_rows:
            vocab = pd.concat([vocab, pd.DataFrame(alias_rows)], ignore_index=True, sort=False)

    vocab["match_text_norm"] = vocab["match_text"].map(normalize_text)
    return vocab[vocab["match_text_norm"].astype(bool)].reset_index(drop=True)


def load_raw_rows_with_assignments() -> pd.DataFrame:
    rows = pd.read_csv(PDF_ROWS)
    rows["fault_code_norm"] = rows["fault_code"].map(as_text)
    rows = rows[rows["fault_code_norm"].ne("") & rows["fault_code_norm"].ne("-")].copy()
    rows["site_key"] = rows["site_text"].map(lambda value: prefixed_hash(as_text(value), "SITE", 10))
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
    rows = rows.merge(
        assignments[["row_key", "estimated_event_key", "dedup_status"]],
        on="row_key",
        how="left",
    )
    rows["event_norm"] = rows["event"].map(normalize_text)
    return rows


def load_notes_support() -> pd.DataFrame:
    if not NOTES_INTERNAL.exists():
        return pd.DataFrame()
    notes = pd.read_csv(NOTES_INTERNAL)
    notes["asset_key_join"] = notes["asset_refs"].fillna("").map(
        lambda value: {prefixed_hash(part.strip(), "ASSET", 10) for part in str(value).split(";") if part.strip()}
    )
    notes["note_norm"] = notes["note_line_text"].map(normalize_text)
    return notes


def notes_for_event(event_rows: pd.DataFrame, notes: pd.DataFrame) -> pd.DataFrame:
    if (
        notes.empty
        or event_rows.empty
        or "file_hash" not in event_rows.columns
        or "site_key" not in event_rows.columns
        or "asset_key" not in event_rows.columns
    ):
        return pd.DataFrame()
    file_hashes = set(event_rows["file_hash"].dropna())
    site_keys = set(event_rows["site_key"].dropna())
    asset_keys = set(event_rows["asset_key"].dropna())
    candidates = notes[
        notes["file_hash"].isin(file_hashes)
        & notes["site_key"].isin(site_keys)
        & notes["asset_key_join"].map(lambda values: bool(values & asset_keys))
    ].copy()
    return candidates


def context_for_event(event_key: str, event_rows: pd.DataFrame, notes: pd.DataFrame) -> dict[str, object]:
    if event_rows.empty or "event_norm" not in event_rows.columns:
        code_context = ""
    else:
        code_context = " ".join(
            event for event, _count in Counter(event_rows["event_norm"].dropna()).most_common(8) if event
        )
    linked_notes = notes_for_event(event_rows, notes)
    notes_context = " ".join(
        text for text, _count in Counter(linked_notes.get("note_norm", pd.Series(dtype=str))).most_common(8) if text
    )
    return {
        "estimated_event_key": event_key,
        "code_context": code_context,
        "notes_context": notes_context,
        "combined_context": " ".join(part for part in [code_context, notes_context] if part),
        "linked_note_line_count": int(linked_notes.shape[0]),
        "linked_note_target_families": sorted(
            {
                target
                for targets in linked_notes.get("candidate_targets", pd.Series(dtype=str)).fillna("")
                for target in str(targets).split(";")
                if target
            }
        ),
    }


def status_for_score(score: float, target: str) -> str:
    threshold = TARGET_THRESHOLDS[target]
    if score >= threshold + HIGH_MARGIN:
        return "candidate_high_requires_review"
    if score >= threshold:
        return "candidate_medium_requires_review"
    return "unresolved_below_threshold"


def build_scoring_rows(events: pd.DataFrame, rows: pd.DataFrame, notes: pd.DataFrame, vocab: pd.DataFrame) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    model = SentenceTransformer(MODEL_NAME)
    vocab_texts = vocab["match_text_norm"].tolist()
    vocab_embeddings = np.asarray(
        model.encode(vocab_texts, normalize_embeddings=True, show_progress_bar=False), dtype=np.float32
    )
    vocab_by_target = {target: vocab.index[vocab["target"].eq(target)].tolist() for target in FAULT_TARGETS}

    event_groups = {key: group for key, group in rows.groupby("estimated_event_key", dropna=False)}
    event_contexts = []
    for event in events.itertuples(index=False):
        event_rows = event_groups.get(event.estimated_event_key, pd.DataFrame())
        event_contexts.append(context_for_event(event.estimated_event_key, event_rows, notes))
    context_embeddings = np.asarray(
        model.encode([ctx["combined_context"] for ctx in event_contexts], normalize_embeddings=True, show_progress_bar=False),
        dtype=np.float32,
    )

    output_rows: list[dict[str, object]] = []
    internal_rows: list[dict[str, object]] = []

    for idx, event in enumerate(events.itertuples(index=False)):
        event_key = event.estimated_event_key
        namespace = event.namespace
        classification = event.classification
        ctx = event_contexts[idx]
        if namespace == "asset_state":
            output_rows.append(asset_state_row(event, ctx))
            continue

        for target in FAULT_TARGETS:
            candidate_idx = vocab_by_target.get(target, [])
            if namespace != "fault_code" or not candidate_idx or not ctx["combined_context"]:
                best_score = 0.0
                best = None
                status = "not_applicable_to_fault_crosswalk" if namespace != "fault_code" else "unresolved_below_threshold"
            else:
                scores = vocab_embeddings[candidate_idx] @ context_embeddings[idx]
                best_local = int(np.argmax(scores))
                best_score = float(scores[best_local])
                best = vocab.iloc[candidate_idx[best_local]]
                status = status_for_score(best_score, target)

            mapped = status.startswith("candidate_")
            output_rows.append(
                {
                    "estimated_event_key": event_key,
                    "namespace": namespace,
                    "classification": classification,
                    "target": target,
                    "snapshot_row_count": int(event.snapshot_row_count),
                    "source_file_count": int(event.source_file_count),
                    "linked_note_line_count": int(ctx["linked_note_line_count"]),
                    "linked_note_target_families": ";".join(ctx["linked_note_target_families"]),
                    "candidate_concept_id": best.get("concept_id", "") if best is not None and mapped else "",
                    "candidate_concept_key": best.get("canonical_concept_key", "") if best is not None and mapped else "",
                    "vocabulary_owner": best.get("vocabulary_owner", "") if best is not None and mapped else "",
                    "semantic_level": best.get("semantic_level", "") if best is not None and mapped else "",
                    "match_score": round(best_score, 4),
                    "match_threshold": TARGET_THRESHOLDS.get(target, ""),
                    "match_text_source": best.get("match_text_source", "") if best is not None and mapped else "",
                    "status": status,
                    "evidence_type": "expert_inference" if mapped else "unresolved",
                    "tier": "silver-medium" if mapped else "unresolved",
                    "label_generation_method": "path_a_crosswalk_v2_embedding_with_notes_support",
                    "evaluation_independence": "derived_from_rules",
                    "can_support_contractual_denominator": False,
                    "can_support_proxy_denominator": False,
                    "requires_target_review": True,
                    "raw_operational_values_emitted": False,
                }
            )
            if best is not None:
                internal_rows.append(
                    {
                        "estimated_event_key": event_key,
                        "namespace": namespace,
                        "target": target,
                        "code_context_redacted": redacted_text(ctx["code_context"]),
                        "notes_context_redacted": redacted_text(ctx["notes_context"]),
                        "candidate_concept_redacted": redacted_text(best.get("canonical_concept", "")),
                        "match_score": round(best_score, 4),
                        "status": status,
                    }
                )
    return output_rows, internal_rows


def asset_state_row(event: object, ctx: dict[str, object]) -> dict[str, object]:
    classification = getattr(event, "classification")
    confidence = getattr(event, "confidence")
    if confidence == "medium_state_consistent":
        review_route = "review_repair_or_maintenance_as_secondary_activity_type_signal"
    else:
        review_route = "keep_as_asset_state_operational_context"
    return {
        "estimated_event_key": getattr(event, "estimated_event_key"),
        "namespace": "asset_state",
        "classification": classification,
        "target": "asset_state",
        "snapshot_row_count": int(getattr(event, "snapshot_row_count")),
        "source_file_count": int(getattr(event, "source_file_count")),
        "linked_note_line_count": int(ctx["linked_note_line_count"]),
        "linked_note_target_families": ";".join(ctx["linked_note_target_families"]),
        "candidate_concept_id": "",
        "candidate_concept_key": "",
        "vocabulary_owner": "",
        "semantic_level": "operational_state",
        "match_score": "",
        "match_threshold": "",
        "match_text_source": "",
        "status": review_route,
        "evidence_type": "expert_inference",
        "tier": "silver-medium" if confidence == "medium_state_consistent" else "unresolved",
        "label_generation_method": "path_a_state_code_partition_v1",
        "evaluation_independence": "derived_from_rules",
        "can_support_contractual_denominator": False,
        "can_support_proxy_denominator": False,
        "requires_target_review": True,
        "raw_operational_values_emitted": False,
    }


def summarize(crosswalk: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    by_target = (
        crosswalk.groupby(["target", "status"], dropna=False)
        .agg(rows=("estimated_event_key", "size"), estimated_events=("estimated_event_key", "nunique"))
        .reset_index()
        .sort_values(["target", "status"])
    )
    by_target["raw_operational_values_emitted"] = False

    by_namespace = (
        crosswalk.groupby(["namespace", "target"], dropna=False)
        .agg(rows=("estimated_event_key", "size"), estimated_events=("estimated_event_key", "nunique"))
        .reset_index()
        .sort_values(["namespace", "target"])
    )
    by_namespace["raw_operational_values_emitted"] = False

    candidate_mask = crosswalk["status"].astype(str).str.startswith("candidate_")
    summary = {
        "created_at_utc": utc_now(),
        "pass_id": "T3.5.5",
        "estimated_events_input": int(crosswalk["estimated_event_key"].nunique()),
        "scoring_rows": int(crosswalk.shape[0]),
        "candidate_rows": int(candidate_mask.sum()),
        "candidate_events": int(crosswalk.loc[candidate_mask, "estimated_event_key"].nunique()),
        "asset_state_events": int(crosswalk.loc[crosswalk["namespace"].eq("asset_state"), "estimated_event_key"].nunique()),
        "fault_code_events": int(crosswalk.loc[crosswalk["namespace"].eq("fault_code"), "estimated_event_key"].nunique()),
        "undetermined_code_events": int(
            crosswalk.loc[crosswalk["namespace"].eq("undetermined_code"), "estimated_event_key"].nunique()
        ),
        "embedding_model": MODEL_NAME,
        "target_thresholds": TARGET_THRESHOLDS,
        "contractual_denominator_supported": False,
        "poc_proxy_denominator_supported": False,
        "raw_operational_values_emitted": False,
    }
    return by_target, by_namespace, summary


def build_memo(summary: dict[str, object], by_target: pd.DataFrame, by_namespace: pd.DataFrame) -> str:
    target_rows = [
        "| " + " | ".join([str(row.target), str(row.status), str(row.rows), str(row.estimated_events)]) + " |"
        for row in by_target.itertuples(index=False)
    ]
    namespace_rows = [
        "| "
        + " | ".join([str(row.namespace), str(row.target), str(row.rows), str(row.estimated_events)])
        + " |"
        for row in by_namespace.itertuples(index=False)
    ]
    return "\n".join(
        [
            "# T3.5.5 Path A Crosswalk v2",
            "",
            "## Scope",
            "",
            "This pass reruns Path A crosswalk scoring against the cleaned event universe from `T3.5.4`. It separates `asset_state` from `fault_code` and uses `NOTES` semantics only as candidate support.",
            "",
            "## Summary",
            "",
            f"- Estimated events input: `{summary['estimated_events_input']}`",
            f"- Scoring rows emitted: `{summary['scoring_rows']}`",
            f"- Candidate rows: `{summary['candidate_rows']}`",
            f"- Candidate events: `{summary['candidate_events']}`",
            f"- Asset-state events kept in separate namespace: `{summary['asset_state_events']}`",
            f"- Fault-code events evaluated: `{summary['fault_code_events']}`",
            f"- Undetermined-code events carried forward: `{summary['undetermined_code_events']}`",
            f"- Contractual denominator supported: `{summary['contractual_denominator_supported']}`",
            f"- POC proxy denominator supported: `{summary['poc_proxy_denominator_supported']}`",
            "",
            "## By Target And Status",
            "",
            "| target | status | rows | estimated_events |",
            "| --- | --- | ---: | ---: |",
            *target_rows,
            "",
            "## By Namespace And Target",
            "",
            "| namespace | target | rows | estimated_events |",
            "| --- | --- | ---: | ---: |",
            *namespace_rows,
            "",
            "## Interpretation",
            "",
            "`asset_state` is not promoted to Activity Type. Maintenance-like state evidence is routed only as secondary review material, while operational states remain operational context.",
            "",
            "Fault-code crosswalk candidates remain `expert_inference`, `silver-medium`, `derived_from_rules`, and `requires_target_review`. No row supports the contractual or POC proxy denominator yet.",
            "",
        ]
    )


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    INTERNAL_PATH_A_DIR.mkdir(parents=True, exist_ok=True)

    events = pd.read_csv(EVENTS)
    raw_rows = load_raw_rows_with_assignments()
    notes = load_notes_support()
    vocab = load_vocab()
    crosswalk_rows, internal_rows = build_scoring_rows(events, raw_rows, notes, vocab)

    crosswalk = pd.DataFrame(crosswalk_rows)
    by_target, by_namespace, summary = summarize(crosswalk)

    crosswalk_path = OUTPUT_DIR / "f355_path_a_crosswalk_v2_sanitized.csv"
    by_target_path = OUTPUT_DIR / "f355_path_a_crosswalk_v2_by_target_sanitized.csv"
    by_namespace_path = OUTPUT_DIR / "f355_path_a_crosswalk_v2_by_namespace_sanitized.csv"
    summary_path = OUTPUT_DIR / "f355_path_a_crosswalk_v2_summary_sanitized.json"
    memo_path = OUTPUT_DIR / "f355_path_a_crosswalk_v2_memo.md"
    internal_path = INTERNAL_PATH_A_DIR / "f355_path_a_crosswalk_v2_internal_review_redacted.csv"

    crosswalk.to_csv(crosswalk_path, index=False)
    by_target.to_csv(by_target_path, index=False)
    by_namespace.to_csv(by_namespace_path, index=False)
    write_csv(internal_path, internal_rows, list(internal_rows[0].keys()) if internal_rows else ["empty"])

    summary["outputs"] = {
        "memo": str(memo_path),
        "crosswalk_v2": str(crosswalk_path),
        "by_target": str(by_target_path),
        "by_namespace": str(by_namespace_path),
    }
    summary["internal_outputs_ignored"] = {"review_redacted": str(internal_path)}
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    memo_path.write_text(build_memo(summary, by_target, by_namespace), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
