"""B1.2 textual residue weak-supervision pass for CONTRACTOR_PATH_001.

This pass applies the F1 high-confidence lexical layer to bounded textual
fields in the relational branch. It emits candidate silver labels with full
provenance and keeps contractual denominator support false.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]
STINT_ROOT = PROJECT_ROOT / "stint-1-evidence-ground-truth"
PHASE_DIR = STINT_ROOT / "phase_4_path_b_xlsx"
OUTPUT_DIR = PHASE_DIR / "outputs" / "b1_silver_labels"
INTERNAL_MANIFEST = (
    PROJECT_ROOT
    / "reports"
    / "internal"
    / "f40b_contractor_path_001_relational_model"
    / "f40b_contractor_path_001_entity_manifest_internal.csv"
)
RAW_LEXICAL_V1 = (
    PROJECT_ROOT
    / "stint-1.1-reference-layer"
    / "reference_layer"
    / "lexical_layer"
    / "lexical_seed_dictionary_v1.csv"
)
HIGH_CONFIDENCE_LEXICAL = (
    STINT_ROOT
    / "phase_1_lexical"
    / "outputs"
    / "lexical_layer_v2"
    / "lexical_layer_v2_high_confidence_candidates_sanitized.csv"
)
REASON_VERDICT = (
    PHASE_DIR
    / "outputs"
    / "reason_semantics_verdict"
    / "reason_semantics_routing_sanitized.csv"
)

CONTRACTOR_PATH = "CONTRACTOR_PATH_001"
SOURCE_FAMILY = "SOURCE_FAMILY_CONTRACTOR_PATH_001_API_DUMP"
ENTITY = "api_service_v1_service-orders"
TEXT_FIELDS = ["descriptionExtended", "reason"]
TARGETS = {"Activity", "Cause", "Damage"}

ABBREVIATIONS = {
    "gb": "gearbox",
    "gbx": "gearbox",
    "gen": "generator",
    "conv": "converter",
    "cnv": "converter",
    "xfmr": "transformer",
    "trafo": "transformer",
    "brg": "bearing",
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
}


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
    return str(value).strip()


def normalize_text(value: object) -> str:
    text = as_text(value).lower()
    text = re.sub(r"[^a-z0-9áéíóúüñ]+", " ", text)
    tokens = []
    for token in text.split():
        token = ABBREVIATIONS.get(token.strip(), token.strip())
        if token:
            tokens.append(token)
    return " ".join(tokens)


def stable_term_key(value: object) -> str:
    return prefixed_hash(normalize_text(value), "TERM", 12)


def load_json_records(path: Path) -> list[dict[str, object]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, Mapping)]
    if isinstance(payload, Mapping):
        for key in ["data", "items", "value", "records", "results"]:
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, Mapping)]
        list_values = [value for value in payload.values() if isinstance(value, list)]
        if len(list_values) == 1:
            return [item for item in list_values[0] if isinstance(item, Mapping)]
    return []


def service_orders_path() -> Path:
    manifest = pd.read_csv(INTERNAL_MANIFEST)
    value = manifest.loc[manifest["entity_label"].eq(ENTITY), "json_path"].iloc[0]
    return Path(value)


def physical_record_id(record: Mapping[str, object], fallback_index: int) -> str:
    record_key = as_text(record.get("id")) or str(fallback_index)
    return prefixed_hash(f"{CONTRACTOR_PATH}|{ENTITY}|{record_key}", "PHY", 16)


def site_key(record: Mapping[str, object]) -> str:
    value = as_text(record.get("siteId"))
    return prefixed_hash(value, "SITE", 10) if value else "SITE-unknown"


def load_term_lookup() -> dict[str, str]:
    raw = pd.read_csv(RAW_LEXICAL_V1)
    if "observed_term" not in raw.columns:
        raise ValueError("Missing observed_term in raw lexical dictionary.")
    raw["term_key"] = raw["observed_term"].map(stable_term_key)
    lookup: dict[str, str] = {}
    for term_key, group in raw.groupby("term_key"):
        terms = sorted({normalize_text(value) for value in group["observed_term"] if normalize_text(value)})
        if terms:
            lookup[str(term_key)] = terms[0]
    return lookup


def load_high_confidence_terms() -> list[dict[str, object]]:
    term_lookup = load_term_lookup()
    high = pd.read_csv(HIGH_CONFIDENCE_LEXICAL)
    high = high[
        high["target"].isin(TARGETS)
        & high["status"].eq("semantic_anchor_high")
        & high["f1_consumption_status"].eq("usable_high_confidence_candidate")
    ].copy()
    terms: list[dict[str, object]] = []
    seen: set[tuple[str, str, str]] = set()
    for row in high.itertuples(index=False):
        term_key = str(row.term_key)
        term_text = term_lookup.get(term_key, "")
        if not term_text:
            continue
        key = (term_key, str(row.target), str(row.canonical_concept_id))
        if key in seen:
            continue
        seen.add(key)
        terms.append(
            {
                "term_key": term_key,
                "term_norm": term_text,
                "target": str(row.target),
                "canonical_concept_id": str(row.canonical_concept_id),
                "canonical_concept_key": str(row.canonical_concept_key),
                "match_score": float(row.match_score),
                "embedding_model": str(row.embedding_model),
                "lexical_source_text_field": str(row.source_text_field),
            }
        )
    return sorted(terms, key=lambda item: (-len(str(item["term_norm"]).split()), str(item["term_key"])))


def contains_term(normalized_text: str, term: str) -> bool:
    if not normalized_text or not term:
        return False
    return re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", normalized_text) is not None


def build_field_hits(records: list[dict[str, object]], terms: list[dict[str, object]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for idx, record in enumerate(records):
        phy_id = physical_record_id(record, idx)
        for field in TEXT_FIELDS:
            text = as_text(record.get(field))
            if not text:
                continue
            normalized = normalize_text(text)
            for term in terms:
                if not contains_term(normalized, str(term["term_norm"])):
                    continue
                target = str(term["target"])
                rows.append(
                    {
                        "record_id": prefixed_hash(f"{phy_id}|{target}|{field}|{term['canonical_concept_id']}", "REC", 16),
                        "physical_record_id": phy_id,
                        "target": target,
                        "evidence_type": "expert_inference",
                        "tier": "silver-medium",
                        "status": "textual_residue_candidate_requires_review",
                        "source_path": SOURCE_FAMILY,
                        "source_text_field": field,
                        "stratum": "explicit_activity_type",
                        "site_key": site_key(record),
                        "contractor_path": CONTRACTOR_PATH,
                        "concept_id": str(term["canonical_concept_id"]),
                        "confidence": "lexical_high_exact_term_hit",
                        "label_generation_method": "b1_2_textual_residue_lexical_layer_v2_rule",
                        "evaluation_independence": "derived_from_rules",
                        "can_support_contractual_denominator": False,
                        "can_support_proxy_denominator": False,
                        "notes": "High-confidence lexical anchor observed in textual residue. Requires target review before proxy denominator use.",
                        "raw_operational_values_emitted": False,
                        "term_key": str(term["term_key"]),
                        "canonical_concept_key": str(term["canonical_concept_key"]),
                        "match_score": float(term["match_score"]),
                        "embedding_model": str(term["embedding_model"]),
                    }
                )
    return rows


def add_convergence(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    by_record_target_concept: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    for row in rows:
        key = (str(row["physical_record_id"]), str(row["target"]), str(row["concept_id"]))
        by_record_target_concept[key].add(str(row["source_text_field"]))
    for row in rows:
        key = (str(row["physical_record_id"]), str(row["target"]), str(row["concept_id"]))
        fields = sorted(by_record_target_concept[key])
        row["field_convergence_count"] = len(fields)
        row["field_convergence_sources"] = ";".join(fields)
        if len(fields) >= 2:
            row["status"] = "textual_residue_converged_candidate_requires_review"
            row["confidence"] = "lexical_high_multi_field_convergence"
            row["can_support_proxy_denominator"] = True
            row["notes"] = (
                "Same concept appears in multiple routed text fields. Proxy use still requires review and anti-circular evaluation controls."
            )
    return rows


def summarize(rows: list[dict[str, object]], records: list[dict[str, object]], terms: list[dict[str, object]]) -> tuple[pd.DataFrame, dict[str, object]]:
    df = pd.DataFrame(rows)
    if df.empty:
        summary_df = pd.DataFrame()
        target_counts = {}
        converged_records = 0
        converged_record_targets = 0
        any_record_targets = 0
    else:
        summary_df = (
            df.groupby(["target", "source_text_field", "status"], dropna=False)
            .agg(
                evidence_rows=("record_id", "size"),
                physical_records=("physical_record_id", "nunique"),
                canonical_concepts=("concept_id", "nunique"),
                term_keys=("term_key", "nunique"),
            )
            .reset_index()
            .sort_values(["target", "source_text_field", "status"])
        )
        summary_df["raw_operational_values_emitted"] = False
        target_counts = df.groupby("target")["physical_record_id"].nunique().to_dict()
        converged_records = int(
            df.loc[df["status"].eq("textual_residue_converged_candidate_requires_review"), "physical_record_id"].nunique()
        )
        converged_record_targets = int(
            df.loc[df["status"].eq("textual_residue_converged_candidate_requires_review"), ["physical_record_id", "target"]]
            .drop_duplicates()
            .shape[0]
        )
        any_record_targets = int(df[["physical_record_id", "target"]].drop_duplicates().shape[0])

    text_coverage = {}
    for field in TEXT_FIELDS:
        non_empty = sum(bool(as_text(record.get(field))) for record in records)
        text_coverage[field] = {
            "non_empty_rows": int(non_empty),
            "coverage_rate": round(non_empty / len(records), 6) if records else 0,
        }

    summary = {
        "created_at_utc": utc_now(),
        "pass_id": "B1.2",
        "contractor_path": CONTRACTOR_PATH,
        "task_type": "textual_residue_silver_label_candidates",
        "records_evaluated": len(records),
        "lexical_high_terms_loaded": len(terms),
        "text_coverage": text_coverage,
        "evidence_rows": len(rows),
        "physical_records_with_any_textual_candidate": int(df["physical_record_id"].nunique()) if not df.empty else 0,
        "record_target_units_with_any_textual_candidate": any_record_targets,
        "physical_records_with_converged_textual_candidate": converged_records,
        "record_target_units_with_converged_textual_candidate": converged_record_targets,
        "target_physical_record_counts": {str(k): int(v) for k, v in sorted(target_counts.items())},
        "contractual_denominator_supported": False,
        "proxy_denominator_candidate_unit": "physical_record_id x target",
        "proxy_denominator_candidate_units_after_review": converged_record_targets,
        "proxy_denominator_candidate_evidence_rows_not_denominator": int(
            sum(bool(row.get("can_support_proxy_denominator")) for row in rows)
        ),
        "raw_operational_values_emitted": False,
        "outputs": [
            "b1_silver_labels_memo.md",
            "b1_silver_labels_textual_residue_sanitized.csv",
            "b1_silver_labels_by_target_field_sanitized.csv",
            "b1_silver_labels_summary_sanitized.json",
        ],
    }
    return summary_df, summary


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def build_memo(summary: dict[str, object], by_target: pd.DataFrame) -> str:
    target_rows = []
    if not by_target.empty:
        for row in by_target.itertuples(index=False):
            target_rows.append(
                "| "
                + " | ".join(
                    [
                        str(row.target),
                        str(row.source_text_field),
                        str(row.status),
                        str(row.evidence_rows),
                        str(row.physical_records),
                        str(row.canonical_concepts),
                    ]
                )
                + " |"
            )
    return "\n".join(
        [
            "# B1.2 Textual Residue Silver Labels",
            "",
            "## Scope",
            "",
            "This pass applies `LEXICAL_LAYER v2` high-confidence anchors to `CONTRACTOR_PATH_001` textual residue. It does not use `activityType`, does not map materials, and does not support contractual denominators.",
            "",
            "## Summary",
            "",
            f"- Records evaluated: `{summary['records_evaluated']}`",
            f"- Lexical high-confidence terms loaded: `{summary['lexical_high_terms_loaded']}`",
            f"- `descriptionExtended` non-empty rows: `{summary['text_coverage']['descriptionExtended']['non_empty_rows']}`",
            f"- `reason` non-empty rows: `{summary['text_coverage']['reason']['non_empty_rows']}`",
            f"- Textual evidence rows: `{summary['evidence_rows']}`",
            f"- Physical records with any textual candidate: `{summary['physical_records_with_any_textual_candidate']}`",
            f"- Record-target units with any textual candidate: `{summary['record_target_units_with_any_textual_candidate']}`",
            f"- Physical records with multi-field convergence: `{summary['physical_records_with_converged_textual_candidate']}`",
            f"- Record-target units with multi-field convergence: `{summary['record_target_units_with_converged_textual_candidate']}`",
            f"- Proxy denominator candidate unit: `{summary['proxy_denominator_candidate_unit']}`",
            f"- Proxy denominator candidate units after review: `{summary['proxy_denominator_candidate_units_after_review']}`",
            f"- Proxy candidate evidence rows, not denominator: `{summary['proxy_denominator_candidate_evidence_rows_not_denominator']}`",
            f"- Contractual denominator supported: `{summary['contractual_denominator_supported']}`",
            "",
            "## By Target And Field",
            "",
            "| target | source_text_field | status | evidence_rows | physical_records | canonical_concepts |",
            "| --- | --- | --- | ---: | ---: | ---: |",
            *target_rows,
            "",
            "## Interpretation",
            "",
            "These rows are weak-supervision candidates generated from a rule-derived lexical layer. They can support B1 target review and later proxy workflows, but they cannot evaluate the same rules that generated them.",
            "",
            "Denominator-style counts use `physical_record_id x target`; evidence rows remain separate so multi-field convergence does not inflate `N`.",
            "",
            "`reason` remains textual support only. B1.3 explicitly rejected deterministic Cause promotion.",
            "",
            "raw_operational_values_emitted: false",
            "",
        ]
    )


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if not REASON_VERDICT.exists():
        raise FileNotFoundError(f"Missing B1.3 reason verdict: {REASON_VERDICT}")
    records = load_json_records(service_orders_path())
    terms = load_high_confidence_terms()
    rows = add_convergence(build_field_hits(records, terms))
    by_target, summary = summarize(rows, records, terms)

    fieldnames = [
        "record_id",
        "physical_record_id",
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
        "field_convergence_count",
        "field_convergence_sources",
    ]
    write_csv(OUTPUT_DIR / "b1_silver_labels_textual_residue_sanitized.csv", rows, fieldnames)
    by_target.to_csv(OUTPUT_DIR / "b1_silver_labels_by_target_field_sanitized.csv", index=False)
    (OUTPUT_DIR / "b1_silver_labels_summary_sanitized.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    (OUTPUT_DIR / "b1_silver_labels_memo.md").write_text(build_memo(summary, by_target), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
