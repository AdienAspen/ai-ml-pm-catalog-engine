from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]
REFERENCE_ROOT = PROJECT_ROOT / "stint-1.1-reference-layer"
STINT_ROOT = PROJECT_ROOT / "stint-1-evidence-ground-truth"
F1_ROOT = STINT_ROOT / "phase_1_lexical"
OUTPUTS_DIR = F1_ROOT / "outputs"
LEXICAL_V2 = OUTPUTS_DIR / "lexical_layer_v2" / "lexical_layer_v2_sanitized.csv"
GROUPED_DIR = OUTPUTS_DIR / "lexical_layer_v2"

RAW_LEXICAL_V1 = (
    REFERENCE_ROOT
    / "reference_layer"
    / "lexical_layer"
    / "lexical_seed_dictionary_v1.csv"
)
CANONICAL_VOCAB_WORKING = OUTPUTS_DIR / "canonical_vocabulary" / "canonical_vocabulary_v1_working.csv"
EXTERNAL_FAILURE_VOCAB = OUTPUTS_DIR / "canonical_vocabulary" / "external_failure_vocabulary_v1.csv"


ABBREVIATIONS = {
    "gb": "gearbox",
    "gbx": "gearbox",
    "gen": "generator",
    "conv": "converter",
    "cnv": "converter",
    "xfmr": "transformer",
    "trafo": "transformer",
    "brg": "bearing",
    "brake": "brake",
    "brakes": "brake",
    "insp": "inspect",
    "inspection": "inspect",
    "inspected": "inspect",
    "repl": "replace",
    "replaced": "replace",
    "replacement": "replace",
    "repairs": "repair",
    "repaired": "repair",
    "maint": "maintenance",
    "comm": "communication",
    "comms": "communication",
    "temp": "temperature",
    "vib": "vibration",
    "vibrations": "vibration",
    "umrichter": "converter",
}

SUFFIXES = ("ing", "ed", "es", "s")

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "the",
    "to",
    "with",
}


def stable_key(value: object, prefix: str) -> str:
    raw = "" if value is None or pd.isna(value) else str(value)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}-{digest}"


def normalize_token(token: str) -> str:
    token = token.lower().strip()
    token = ABBREVIATIONS.get(token, token)
    for suffix in SUFFIXES:
        if len(token) > len(suffix) + 4 and token.endswith(suffix):
            candidate = token[: -len(suffix)]
            return ABBREVIATIONS.get(candidate, candidate)
    return token


def normalize_text(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    text = str(value).lower()
    text = re.sub(r"[^a-z0-9áéíóúüñ]+", " ", text)
    tokens = [normalize_token(t) for t in text.split() if t and t not in STOPWORDS]
    return " ".join(tokens)


def term_tokens(value: object) -> set[str]:
    return {t for t in normalize_text(value).split() if len(t) >= 3}


def consolidate_term(term: object) -> str:
    tokens = [normalize_token(t) for t in normalize_text(term).split() if t]
    collapsed: list[str] = []
    for token in tokens:
        if not collapsed or collapsed[-1] != token:
            collapsed.append(token)
    return " ".join(collapsed)


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def load_observed_terms() -> dict[str, str]:
    if not RAW_LEXICAL_V1.exists():
        raise FileNotFoundError(f"Missing raw lexical working input: {RAW_LEXICAL_V1}")
    raw = pd.read_csv(RAW_LEXICAL_V1)
    if "observed_term" not in raw.columns:
        raise ValueError("Raw lexical input must contain observed_term.")
    raw["consolidated_term"] = raw["observed_term"].map(consolidate_term)
    raw["term_key"] = raw["consolidated_term"].map(lambda value: stable_key(value, "TERM"))
    # Local-only lookup. It is never emitted.
    lookup = {}
    for term_key, group in raw.groupby("term_key"):
        values = sorted(set(str(v) for v in group["consolidated_term"].dropna() if str(v).strip()))
        if values:
            lookup[term_key] = values[0]
    return lookup


def load_vocabulary() -> list[dict]:
    frames = []
    if CANONICAL_VOCAB_WORKING.exists():
        frames.append(pd.read_csv(CANONICAL_VOCAB_WORKING))
    if EXTERNAL_FAILURE_VOCAB.exists():
        frames.append(pd.read_csv(EXTERNAL_FAILURE_VOCAB))
    if not frames:
        raise FileNotFoundError("Missing canonical vocabulary inputs for F1d.")
    vocab = pd.concat(frames, ignore_index=True, sort=False)
    if "canonical_concept" not in vocab.columns:
        raise ValueError("Vocabulary working inputs must include canonical_concept.")
    vocab = vocab[vocab["canonical_concept"].notna()].copy()
    vocab["concept_norm"] = vocab["canonical_concept"].map(normalize_text)
    vocab["concept_tokens"] = vocab["canonical_concept"].map(term_tokens)
    vocab = vocab[vocab["concept_norm"].astype(bool)]
    return vocab.to_dict("records")


def build_token_index(vocab_records: list[dict]) -> dict[str, list[int]]:
    index: dict[str, list[int]] = {}
    for idx, record in enumerate(vocab_records):
        for token in record.get("concept_tokens", set()):
            index.setdefault(token, []).append(idx)
    return index


def score_match(term: str, concept_norm: str, concept_tokens: set[str]) -> tuple[float, str]:
    term_norm = normalize_text(term)
    tokens = term_tokens(term)
    if not term_norm or not tokens or not concept_norm or not concept_tokens:
        return 0.0, "no_signal"
    if term_norm == concept_norm:
        return 1.0, "exact_normalized"
    if len(tokens) == 1 and term_norm in concept_tokens and len(concept_tokens) == 1:
        return 0.95, "single_token_exact"
    shared = tokens & concept_tokens
    if len(shared) >= 2:
        if term_norm in concept_norm or concept_norm in term_norm:
            return 0.9, "phrase_containment"
        union = tokens | concept_tokens
        jaccard = len(shared) / len(union)
        if jaccard >= 0.5:
            return round(jaccard, 4), "token_overlap"
    return 0.0, "below_threshold"


def candidate_targets(observed_target: str) -> set[str]:
    if observed_target and observed_target != "unknown":
        return {observed_target}
    return {"Symptom", "Object Part", "Damage", "Cause", "Activity", "FLOC leaf", "Activity Type"}


def tier_for_match(score: float, observed_target: str, concept_target: str, source_tier: str) -> str:
    if score >= 0.95 and observed_target == concept_target and source_tier == "gold":
        return "silver-high"
    if score >= 0.9 and observed_target == concept_target:
        return "silver-medium"
    return "silver-medium"


def main() -> None:
    if not LEXICAL_V2.exists():
        raise FileNotFoundError(f"Missing lexical v2 input: {LEXICAL_V2}")

    term_lookup = load_observed_terms()
    vocab = load_vocabulary()
    token_index = build_token_index(vocab)
    lexical = pd.read_csv(LEXICAL_V2)
    rows: list[dict] = []

    for _, lex in lexical.iterrows():
        term_key = str(lex.get("term_key", ""))
        observed_term = term_lookup.get(term_key, "")
        observed_target = str(lex.get("target", "") or "unknown")
        allowed_targets = candidate_targets(observed_target)
        token_hits = set()
        for token in term_tokens(observed_term):
            token_hits.update(token_index.get(token, []))
        candidates = [vocab[idx] for idx in token_hits if str(vocab[idx].get("target", "")) in allowed_targets]

        best = None
        best_score = 0.0
        best_method = "unresolved"
        for cand in candidates:
            score, method = score_match(observed_term, cand["concept_norm"], cand["concept_tokens"])
            if score > best_score:
                best = cand
                best_score = score
                best_method = method

        mapped = best is not None and best_score >= 0.5
        if mapped:
            concept_id = best.get("concept_id")
            canonical_concept_key = best.get("canonical_concept_key", stable_key(best.get("canonical_concept"), "CONCEPT"))
            owner = best.get("vocabulary_owner", "")
            semantic_level = best.get("semantic_level", "")
            subsystem = best.get("subsystem", "")
            source_tier = best.get("tier", "")
            target = best.get("target", observed_target)
            status = "mapped_to_canonical_concept"
            grouping_tier = tier_for_match(best_score, observed_target, str(target), str(source_tier))
        else:
            concept_id = ""
            canonical_concept_key = ""
            owner = ""
            semantic_level = ""
            subsystem = ""
            target = observed_target
            status = "unresolved"
            grouping_tier = "unresolved"

        rows.append(
            {
                "term_key": term_key,
                "source_concept_id": lex.get("concept_id"),
                "target": target,
                "observed_target_hint": observed_target,
                "source_text_field": lex.get("source_text_field"),
                "stratum": lex.get("stratum"),
                "contractor_path": lex.get("contractor_path"),
                "record_count": int(lex.get("record_count", 0) or 0),
                "mapped_to_canonical_concept": bool(mapped),
                "canonical_concept_id": concept_id,
                "canonical_concept_key": canonical_concept_key,
                "vocabulary_owner": owner,
                "subsystem": subsystem,
                "semantic_level": semantic_level,
                "match_score": round(float(best_score), 4),
                "match_method": best_method,
                "evidence_type": "expert_inference" if mapped else "unresolved",
                "tier": grouping_tier,
                "status": status,
                "label_generation_method": "domain_grouping_rule_set_v1",
                "evaluation_independence": "derived_from_rules",
                "can_support_contractual_denominator": False,
                "can_support_proxy_denominator": bool(mapped),
                "raw_values_emitted": False,
            }
        )

    fields = [
        "term_key",
        "source_concept_id",
        "target",
        "observed_target_hint",
        "source_text_field",
        "stratum",
        "contractor_path",
        "record_count",
        "mapped_to_canonical_concept",
        "canonical_concept_id",
        "canonical_concept_key",
        "vocabulary_owner",
        "subsystem",
        "semantic_level",
        "match_score",
        "match_method",
        "evidence_type",
        "tier",
        "status",
        "label_generation_method",
        "evaluation_independence",
        "can_support_contractual_denominator",
        "can_support_proxy_denominator",
        "raw_values_emitted",
    ]
    output_csv = GROUPED_DIR / "lexical_domain_grouping_v1_sanitized.csv"
    write_csv(output_csv, rows, fields)

    mapped_rows = [row for row in rows if row["mapped_to_canonical_concept"]]
    unresolved_rows = [row for row in rows if not row["mapped_to_canonical_concept"]]
    target_summary = {}
    for target, group in pd.DataFrame(rows).groupby("observed_target_hint", dropna=False):
        target_rows = group.to_dict("records")
        mapped_count = sum(1 for row in target_rows if row["mapped_to_canonical_concept"])
        target_summary[str(target)] = {
            "rows": len(target_rows),
            "mapped_rows": mapped_count,
            "unresolved_rows": len(target_rows) - mapped_count,
            "mapped_pct": round(100 * mapped_count / len(target_rows), 2) if target_rows else 0.0,
            "distinct_canonical_concepts": int(group.loc[group["mapped_to_canonical_concept"], "canonical_concept_id"].nunique()),
        }

    owner_counts = Counter(row["vocabulary_owner"] or "unresolved" for row in rows)
    semantic_counts = Counter(row["semantic_level"] or "unresolved" for row in rows)
    method_counts = Counter(row["match_method"] for row in rows)

    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "task": "F1d_domain_grouping",
        "input_rows": len(rows),
        "mapped_rows": len(mapped_rows),
        "unresolved_rows": len(unresolved_rows),
        "mapped_pct": round(100 * len(mapped_rows) / len(rows), 2) if rows else 0.0,
        "distinct_term_keys": len({row["term_key"] for row in rows}),
        "distinct_canonical_concepts_mapped": len({row["canonical_concept_id"] for row in mapped_rows}),
        "target_summary": target_summary,
        "vocabulary_owner_counts": dict(owner_counts),
        "semantic_level_counts": dict(semantic_counts),
        "match_method_counts": dict(method_counts),
        "symptom_expectation": "Symptom has few public anchors; high unresolved is expected and not a grouping failure.",
        "damage_expectation": "Damage has the broadest external vocabulary but semantic levels must remain separated.",
        "cause_expectation": "Cause is supported by WMEP causes but still lacks observed project labels.",
        "label_generation_method": "domain_grouping_rule_set_v1",
        "evaluation_independence": "derived_from_rules",
        "raw_values_emitted": False,
        "outputs": {
            "grouping_csv": "stint-1-evidence-ground-truth/phase_1_lexical/outputs/lexical_layer_v2/lexical_domain_grouping_v1_sanitized.csv",
            "summary_json": "stint-1-evidence-ground-truth/phase_1_lexical/outputs/f1d_domain_grouping_summary.json",
            "memo": "stint-1-evidence-ground-truth/phase_1_lexical/outputs/f1d_domain_grouping_memo.md",
        },
    }
    (OUTPUTS_DIR / "f1d_domain_grouping_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    lines = [
        "# F1d - Domain Grouping Against Canonical Vocabulary",
        "",
        "## Purpose",
        "",
        "This pass anchors observed lexical term keys to canonical vocabulary concepts where a conservative domain match exists.",
        "",
        "It does not emit observed terms or canonical text, and it does not create validated mappings.",
        "",
        "## Expectations Before Run",
        "",
        "- Damage should anchor better than before because F1c2 added external failure/damage vocabulary.",
        "- Cause may anchor where WMEP causes apply.",
        "- Symptom is expected to remain mostly unresolved because only eight public failure-effect anchors are available.",
        "",
        "## Results",
        "",
        f"- Input rows: {summary['input_rows']}",
        f"- Mapped rows: {summary['mapped_rows']}",
        f"- Unresolved rows: {summary['unresolved_rows']}",
        f"- Mapped percentage: {summary['mapped_pct']}%",
        f"- Distinct term keys: {summary['distinct_term_keys']}",
        f"- Distinct canonical concepts mapped: {summary['distinct_canonical_concepts_mapped']}",
        "",
        "## Target Summary",
        "",
        "| target | rows | mapped_rows | unresolved_rows | mapped_pct | distinct_canonical_concepts |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for target, stats in sorted(target_summary.items()):
        lines.append(
            f"| {target} | {stats['rows']} | {stats['mapped_rows']} | "
            f"{stats['unresolved_rows']} | {stats['mapped_pct']} | {stats['distinct_canonical_concepts']} |"
        )
    lines.extend(
        [
            "",
            "## Governance",
            "",
            "- Grouping links are `expert_inference`, not `validated_mapping`.",
            "- All rows are `derived_from_rules`; they cannot be used as independent held-out labels for STINT_2.",
            "- `unresolved` is an expected output and must not be forced into a concept.",
            "- Damage-adjacent evidence preserves vocabulary owner, subsystem, and semantic level to avoid flattening heterogeneous evidence sets.",
        ]
    )
    (OUTPUTS_DIR / "f1d_domain_grouping_memo.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )

    print(
        json.dumps(
            {
                "task": summary["task"],
                "mapped_rows": summary["mapped_rows"],
                "unresolved_rows": summary["unresolved_rows"],
                "mapped_pct": summary["mapped_pct"],
                "distinct_canonical_concepts_mapped": summary["distinct_canonical_concepts_mapped"],
                "raw_values_emitted": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
