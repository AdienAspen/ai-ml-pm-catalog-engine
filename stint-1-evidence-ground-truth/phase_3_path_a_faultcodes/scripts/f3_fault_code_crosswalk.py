from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer


PROJECT_ROOT = Path(__file__).resolve().parents[3]
STINT_ROOT = PROJECT_ROOT / "stint-1-evidence-ground-truth"
F3_ROOT = STINT_ROOT / "phase_3_path_a_faultcodes"
OUTPUTS_DIR = F3_ROOT / "outputs"
INTERNAL_DIR = PROJECT_ROOT / "reports" / "internal"

PDF_ROWS = PROJECT_ROOT / "reports" / "internal" / "pdf_assets_of_concern_rows.csv"
CANONICAL_VOCAB_WORKING = (
    STINT_ROOT / "phase_1_lexical" / "outputs" / "canonical_vocabulary" / "canonical_vocabulary_v1_working.csv"
)
EXTERNAL_FAILURE_VOCAB = (
    STINT_ROOT / "phase_1_lexical" / "outputs" / "canonical_vocabulary" / "external_failure_vocabulary_v1.csv"
)
TRANSLATION_ALIASES_ES = (
    STINT_ROOT / "phase_1_lexical" / "outputs" / "canonical_vocabulary" / "translation_aliases_es_v1.csv"
)

CROSSWALK = OUTPUTS_DIR / "oem_fault_code_crosswalk_sanitized.csv"
CODE_PROFILE = OUTPUTS_DIR / "oem_fault_code_profile_sanitized.csv"
TARGET_SUMMARY = OUTPUTS_DIR / "oem_fault_code_crosswalk_target_summary.csv"
SUMMARY_JSON = OUTPUTS_DIR / "oem_fault_code_crosswalk_summary.json"
REPORT_MD = OUTPUTS_DIR / "oem_fault_code_crosswalk_report.md"
INTERNAL_REVIEW = INTERNAL_DIR / "oem_fault_code_crosswalk_internal_review_redacted.csv"

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
TARGETS = ["Object Part", "Damage", "Cause", "Activity"]
MIN_CANDIDATE_SCORE = 0.62
HIGH_CANDIDATE_SCORE = 0.70


def stable_key(value: object, prefix: str) -> str:
    raw = "" if value is None or pd.isna(value) else str(value)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}-{digest}"


def normalize_text(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    text = str(value).lower()
    text = re.sub(r"[^a-z0-9áéíóúüñ]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def redacted_text(value: object) -> str:
    text = "" if value is None or pd.isna(value) else str(value)
    text = re.sub(r"\b\d+(?:[.,:/-]\d+)*\b", "<NUM>", text)
    text = re.sub(r"\b[A-Z]{2,}[-_/]?[A-Z0-9]{2,}\b", "<CODE>", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:160]


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def load_fault_rows() -> pd.DataFrame:
    rows = pd.read_csv(PDF_ROWS)
    rows["fault_code"] = rows["fault_code"].astype(str).str.strip()
    rows = rows[rows["fault_code"].notna() & rows["fault_code"].ne("") & rows["fault_code"].ne("-")].copy()
    rows["fault_code_key"] = rows["fault_code"].map(lambda value: stable_key(value, "FAULT"))
    rows["event_norm"] = rows["event"].map(normalize_text)
    rows["event_key"] = rows["event_norm"].map(lambda value: stable_key(value, "EVENT"))
    rows["physical_record_id"] = rows.apply(
        lambda row: stable_key(
            f"{row.get('path_hash')}|{row.name}|{row.get('fault_code')}|{row.get('state')}|{row.get('event_key')}",
            "PDFREC",
        ),
        axis=1,
    )
    return rows


def load_vocab() -> pd.DataFrame:
    frames = []
    for path in [CANONICAL_VOCAB_WORKING, EXTERNAL_FAILURE_VOCAB]:
        if path.exists():
            frames.append(pd.read_csv(path))
    vocab = pd.concat(frames, ignore_index=True, sort=False)
    vocab = vocab[vocab["target"].isin(TARGETS)].copy()
    vocab = vocab[vocab["canonical_concept"].notna()].copy()
    vocab["match_text"] = vocab["canonical_concept"]
    vocab["match_text_source"] = "canonical_concept"

    if TRANSLATION_ALIASES_ES.exists():
        aliases = pd.read_csv(TRANSLATION_ALIASES_ES)
        alias_rows = []
        for _, row in aliases[aliases["target"].isin(TARGETS)].iterrows():
            alias_rows.append(
                {
                    "concept_id": row.get("canonical_concept_id", ""),
                    "canonical_concept_key": row.get("canonical_concept_key", ""),
                    "canonical_concept": row.get("canonical_alias_es", ""),
                    "target": row.get("target", ""),
                    "namespace": row.get("namespace", ""),
                    "target_field": row.get("target_field", ""),
                    "vocabulary_owner": row.get("vocabulary_owner", ""),
                    "subsystem": row.get("subsystem", ""),
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
    vocab = vocab[vocab["match_text_norm"].astype(bool)].copy()
    return vocab.reset_index(drop=True)


def build_context(group: pd.DataFrame) -> str:
    event_counts = Counter(v for v in group["event_norm"] if v and v != "-")
    top_events = [event for event, _ in event_counts.most_common(12)]
    state_counts = Counter(str(v) for v in group["state"].dropna())
    state_tokens = [f"state {state}" for state, _ in state_counts.most_common()]
    return " ".join(top_events + state_tokens)


def status_for_score(score: float) -> str:
    if score >= HIGH_CANDIDATE_SCORE:
        return "candidate_high_requires_review"
    if score >= MIN_CANDIDATE_SCORE:
        return "candidate_medium_requires_review"
    return "unresolved_below_threshold"


def main() -> None:
    rows = load_fault_rows()
    vocab = load_vocab()

    model = SentenceTransformer(MODEL_NAME)
    vocab_texts = vocab["match_text_norm"].tolist()
    vocab_embeddings = np.asarray(
        model.encode(vocab_texts, normalize_embeddings=True, show_progress_bar=False),
        dtype=np.float32,
    )

    vocab_by_target = {
        target: vocab.index[vocab["target"].eq(target)].tolist()
        for target in TARGETS
    }
    contexts = {}
    for fault_code_key, group in rows.groupby("fault_code_key"):
        contexts[fault_code_key] = build_context(group)
    code_keys = list(contexts.keys())
    context_embeddings = np.asarray(
        model.encode([contexts[key] for key in code_keys], normalize_embeddings=True, show_progress_bar=False),
        dtype=np.float32,
    )

    crosswalk_rows = []
    internal_rows = []
    profile_rows = []

    group_lookup = {key: group for key, group in rows.groupby("fault_code_key")}

    for idx, fault_code_key in enumerate(code_keys):
        group = group_lookup[fault_code_key]
        event_count = int(group["event_key"].nunique())
        profile_rows.append(
            {
                "fault_code_key": fault_code_key,
                "frequency": int(len(group)),
                "distinct_event_keys": event_count,
                "distinct_file_hashes": int(group["file_hash"].nunique()),
                "state_count": int(group["state"].nunique()),
                "year_count": int(group["report_year_hint"].nunique()),
                "context_key": stable_key(contexts[fault_code_key], "FCTX"),
                "raw_values_emitted": False,
            }
        )

        for target in TARGETS:
            candidate_idx = vocab_by_target[target]
            if not candidate_idx or not contexts[fault_code_key]:
                best_score = 0.0
                best = None
            else:
                scores = vocab_embeddings[candidate_idx] @ context_embeddings[idx]
                best_local = int(np.argmax(scores))
                best_score = float(scores[best_local])
                best = vocab.iloc[candidate_idx[best_local]]

            status = status_for_score(best_score)
            mapped = status != "unresolved_below_threshold"
            confidence = "silver-medium" if mapped else "unresolved"
            concept_id = best.get("concept_id", "") if best is not None and mapped else ""
            concept_key = best.get("canonical_concept_key", "") if best is not None and mapped else ""
            owner = best.get("vocabulary_owner", "") if best is not None and mapped else ""
            semantic_level = best.get("semantic_level", "") if best is not None and mapped else ""
            match_source = best.get("match_text_source", "") if best is not None and mapped else ""

            crosswalk_rows.append(
                {
                    "fault_code_key": fault_code_key,
                    "target": target,
                    "frequency": int(len(group)),
                    "distinct_event_keys": event_count,
                    "candidate_concept_id": concept_id,
                    "candidate_concept_key": concept_key,
                    "vocabulary_owner": owner,
                    "semantic_level": semantic_level,
                    "match_score": round(best_score, 4),
                    "match_threshold": MIN_CANDIDATE_SCORE,
                    "match_text_source": match_source,
                    "status": status,
                    "evidence_type": "expert_inference" if mapped else "unresolved",
                    "tier": confidence,
                    "label_generation_method": "fault_code_context_semantic_embedding_rule_set_v1",
                    "evaluation_independence": "derived_from_rules",
                    "can_support_contractual_denominator": False,
                    "can_support_proxy_denominator": False,
                    "requires_target_review": True,
                    "raw_values_emitted": False,
                }
            )

            if best is not None:
                internal_rows.append(
                    {
                        "fault_code_key": fault_code_key,
                        "fault_code_redacted": redacted_text(group["fault_code"].iloc[0]),
                        "target": target,
                        "frequency": int(len(group)),
                        "context_redacted": redacted_text(contexts[fault_code_key]),
                        "candidate_concept_id": concept_id,
                        "candidate_concept_redacted": redacted_text(best.get("canonical_concept", "")),
                        "vocabulary_owner": owner,
                        "match_score": round(best_score, 4),
                        "status": status,
                        "manual_review_result": "",
                        "manual_review_notes": "",
                    }
                )

    write_csv(
        CODE_PROFILE,
        sorted(profile_rows, key=lambda row: (-row["frequency"], row["fault_code_key"])),
        [
            "fault_code_key",
            "frequency",
            "distinct_event_keys",
            "distinct_file_hashes",
            "state_count",
            "year_count",
            "context_key",
            "raw_values_emitted",
        ],
    )
    write_csv(
        CROSSWALK,
        crosswalk_rows,
        [
            "fault_code_key",
            "target",
            "frequency",
            "distinct_event_keys",
            "candidate_concept_id",
            "candidate_concept_key",
            "vocabulary_owner",
            "semantic_level",
            "match_score",
            "match_threshold",
            "match_text_source",
            "status",
            "evidence_type",
            "tier",
            "label_generation_method",
            "evaluation_independence",
            "can_support_contractual_denominator",
            "can_support_proxy_denominator",
            "requires_target_review",
            "raw_values_emitted",
        ],
    )
    write_csv(
        INTERNAL_REVIEW,
        internal_rows,
        [
            "fault_code_key",
            "fault_code_redacted",
            "target",
            "frequency",
            "context_redacted",
            "candidate_concept_id",
            "candidate_concept_redacted",
            "vocabulary_owner",
            "match_score",
            "status",
            "manual_review_result",
            "manual_review_notes",
        ],
    )

    target_rows = []
    crosswalk_df = pd.DataFrame(crosswalk_rows)
    for target, frame in crosswalk_df.groupby("target"):
        target_rows.append(
            {
                "target": target,
                "fault_code_candidates_high": int(frame["status"].eq("candidate_high_requires_review").sum()),
                "fault_code_candidates_medium": int(frame["status"].eq("candidate_medium_requires_review").sum()),
                "fault_code_unresolved": int(frame["status"].eq("unresolved_below_threshold").sum()),
                "distinct_candidate_concepts": int(
                    frame.loc[frame["candidate_concept_id"].astype(bool), "candidate_concept_id"].nunique()
                ),
                "raw_values_emitted": False,
            }
        )
    write_csv(
        TARGET_SUMMARY,
        target_rows,
        [
            "target",
            "fault_code_candidates_high",
            "fault_code_candidates_medium",
            "fault_code_unresolved",
            "distinct_candidate_concepts",
            "raw_values_emitted",
        ],
    )

    status_counts = Counter(row["status"] for row in crosswalk_rows)
    code_any_candidate = defaultdict(int)
    for row in crosswalk_rows:
        if row["status"] != "unresolved_below_threshold":
            code_any_candidate[row["fault_code_key"]] += 1

    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "task": "F3_oem_fault_code_crosswalk_path_a",
        "input_fault_code_rows": int(len(rows)),
        "distinct_fault_code_keys": int(rows["fault_code_key"].nunique()),
        "crosswalk_rows": int(len(crosswalk_rows)),
        "target_count": len(TARGETS),
        "candidate_status_counts": {str(k): int(v) for k, v in sorted(status_counts.items())},
        "fault_codes_with_any_candidate": int(len(code_any_candidate)),
        "fault_codes_without_candidate": int(rows["fault_code_key"].nunique() - len(code_any_candidate)),
        "min_candidate_score": MIN_CANDIDATE_SCORE,
        "high_candidate_score": HIGH_CANDIDATE_SCORE,
        "embedding_model": MODEL_NAME,
        "evidence_type_for_candidates": "expert_inference",
        "tier_for_candidates": "silver-medium",
        "evaluation_independence": "derived_from_rules",
        "contractual_denominator_supported": False,
        "poc_proxy_denominator_supported": False,
        "decision": "candidate_crosswalk_for_review_only_no_1_to_1_mapping_claim",
        "raw_values_emitted": False,
        "outputs": {
            "crosswalk_csv": str(CROSSWALK.relative_to(PROJECT_ROOT)),
            "code_profile_csv": str(CODE_PROFILE.relative_to(PROJECT_ROOT)),
            "target_summary_csv": str(TARGET_SUMMARY.relative_to(PROJECT_ROOT)),
            "summary_json": str(SUMMARY_JSON.relative_to(PROJECT_ROOT)),
            "report_md": str(REPORT_MD.relative_to(PROJECT_ROOT)),
            "internal_review_csv": str(INTERNAL_REVIEW.relative_to(PROJECT_ROOT)),
        },
    }
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    report = f"""# F3 OEM Fault Code Crosswalk Report

## Scope

This pass processes the corrected PDF `Assets of Concern` extraction for Path A. It uses
fault-code context to create candidate maintenance concepts against the available reference
layer. It does not claim an OEM-to-SAP 1:1 mapping.

## Input Coverage

| metric | value |
| --- | ---: |
| fault-code rows | {summary["input_fault_code_rows"]} |
| distinct fault-code keys | {summary["distinct_fault_code_keys"]} |
| crosswalk candidate rows | {summary["crosswalk_rows"]} |

## Candidate Status

| status | rows |
| --- | ---: |
"""
    for status, count in summary["candidate_status_counts"].items():
        report += f"| {status} | {count} |\n"

    report += f"""
## Interpretation

- Fault codes are treated as OEM/contextual evidence, not SAP codes.
- A fault code may map to multiple candidate targets, one candidate target, or none.
- Candidate rows are `expert_inference`, `silver-medium`, and `derived_from_rules`.
- No candidate can support the contractual denominator without later validation.
- No candidate is included in the POC proxy denominator yet; F3 emits a review queue.

## Controls

- Versioned outputs use fault-code keys, concept IDs, counts, scores, and provenance only.
- Raw fault codes, event text, asset identifiers, and file paths are not emitted in versioned outputs.
- An internal redacted review file exists under `reports/internal/` for human review.
"""
    REPORT_MD.write_text(report, encoding="utf-8")

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
