from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
STINT_ROOT = PROJECT_ROOT / "stint-1.1-reference-layer"
OUTPUTS_DIR = STINT_ROOT / "outputs"
DOCS_DIR = STINT_ROOT / "docs"
LEXICAL_DIR = STINT_ROOT / "reference_layer" / "lexical_layer"
SEMANTIC_DIR = STINT_ROOT / "reference_layer" / "semantic_normalisation"

OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR.mkdir(parents=True, exist_ok=True)
LEXICAL_DIR.mkdir(parents=True, exist_ok=True)
SEMANTIC_DIR.mkdir(parents=True, exist_ok=True)

VESTAS_SERVICE_ORDERS = (
    PROJECT_ROOT
    / "data/interim/extracted_source/package_001_37cac7fe/Data/Vestas/api_service_v1_service-orders.xlsx"
)
PDF_ROWS = PROJECT_ROOT / "reports/internal/pdf_assets_of_concern_rows.csv"

CANONICAL_TARGETS = {
    "Symptom": "header.symptom.group+header.symptom.code",
    "Object Part": "findings[].object_part",
    "Damage": "findings[].damage",
    "Cause": "findings[].cause",
    "Activity": "findings[].activity",
    "FLOC leaf": "header.functional_location",
    "Activity Type": "header.activity_type",
}

TARGET_NAMESPACES = {
    "Symptom": "catalog_s",
    "Object Part": "catalog_b",
    "Damage": "catalog_c",
    "Cause": "catalog_5",
    "Activity": "catalog_a",
    "FLOC leaf": "floc",
    "Activity Type": "mat",
}

TEXT_FIELDS = [
    ("description", "classification_input.description"),
    ("descriptionExtended", "classification_input.description_extended"),
    ("reason", "classification_input.reason"),
    ("workPerformed", "classification_input.work_performed"),
]

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
    "work",
    "works",
    "service",
    "order",
    "scheduled",
    "unscheduled",
    "additional",
    "other",
    "maintenance",
    "completed",
    "pending",
    "planned",
    "andor",
}

SENSITIVE_TERMS = {
    "aes",
    "fsa",
    "ge",
    "vestas",
    "latigo",
    "laurel",
    "prevailing",
}

TARGET_HINTS = {
    "Activity": {
        "repair",
        "replace",
        "replaced",
        "inspect",
        "inspection",
        "clean",
        "cleaning",
        "reset",
        "tighten",
        "lubricate",
        "test",
        "troubleshoot",
        "calibrate",
        "adjust",
        "service",
    },
    "Object Part": {
        "blade",
        "bearing",
        "brake",
        "gearbox",
        "generator",
        "converter",
        "transformer",
        "yaw",
        "pitch",
        "tower",
        "nacelle",
        "rotor",
        "sensor",
        "motor",
        "pump",
        "filter",
        "cable",
        "controller",
    },
    "Damage": {
        "crack",
        "leak",
        "leaking",
        "broken",
        "wear",
        "worn",
        "damage",
        "damaged",
        "corrosion",
        "fault",
        "failure",
        "failed",
        "vibration",
    },
    "Cause": {
        "loose",
        "contamination",
        "misalignment",
        "overheat",
        "overheating",
        "voltage",
        "communication",
        "temperature",
        "pressure",
    },
    "Symptom": {
        "alarm",
        "warning",
        "trip",
        "tripped",
        "stopped",
        "noisy",
        "noise",
        "vibration",
        "error",
    },
    "FLOC leaf": {
        "converter",
        "generator",
        "gearbox",
        "nacelle",
        "rotor",
        "tower",
        "yaw",
        "pitch",
        "transformer",
    },
    "Activity Type": {
        "corrective",
        "preventive",
        "scheduled",
        "unscheduled",
        "repair",
        "inspection",
    },
}


def stable_key(value: object, prefix: str) -> str:
    raw = "" if value is None or pd.isna(value) else str(value)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}-{digest}"


def maintenance_bucket(value: object) -> str:
    text = "" if value is None or pd.isna(value) else str(value).strip().lower()
    if not text:
        return "blank"
    if "unscheduled" in text or "repair" in text or "corrective" in text or "reactive" in text:
        return "reactive_like"
    if "scheduled" in text or "planned" in text or "preventive" in text:
        return "planned_like"
    if "additional" in text or "other" in text or "cim" in text:
        return "other_explicit_value"
    return "unclassified_explicit_value"


def normalise_text(text: object) -> str:
    if text is None or pd.isna(text):
        return ""
    text = str(text).lower()
    text = re.sub(r"\b[a-z]{0,3}\d+[a-z0-9_-]*\b", " ", text)
    text = re.sub(r"\b\d+[a-z0-9_-]*\b", " ", text)
    text = re.sub(r"[^a-záéíóúüñ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def term_candidates(text: object) -> set[str]:
    clean = normalise_text(text)
    tokens = [t for t in clean.split() if len(t) >= 3 and t not in STOPWORDS]
    terms: set[str] = set()
    for token in tokens:
        if len(token) >= 4 and token not in SENSITIVE_TERMS:
            terms.add(token)
    for n in (2, 3):
        for idx in range(0, max(0, len(tokens) - n + 1)):
            phrase = " ".join(tokens[idx : idx + n])
            if 5 <= len(phrase) <= 60 and not (set(phrase.split()) & SENSITIVE_TERMS):
                terms.add(phrase)
    return terms


def target_for_term(term: str) -> tuple[str, str]:
    words = set(term.split())
    scores = {
        target: len(words & hints) + (1 if term in hints else 0)
        for target, hints in TARGET_HINTS.items()
    }
    target, score = max(scores.items(), key=lambda item: item[1])
    if score <= 0:
        return "unknown", "unresolved"
    return target, "hypothesis"


def sample_vestas_records() -> tuple[list[dict], list[dict]]:
    if not VESTAS_SERVICE_ORDERS.exists():
        return [], []
    df = pd.read_excel(VESTAS_SERVICE_ORDERS, engine="openpyxl")
    df = df.copy()
    df["contractor_path"] = "CONTRACTOR_PATH_001"
    df["site_key"] = df["siteId"].map(lambda value: stable_key(value, "SITE")) if "siteId" in df.columns else "SITE-UNKNOWN"
    df["stratum"] = df["activityType"].map(maintenance_bucket) if "activityType" in df.columns else "unstratified"
    df["record_key"] = df["id"].map(lambda value: stable_key(value, "RECORD")) if "id" in df.columns else [f"RECORD-{i:06d}" for i in range(len(df))]

    sampled = []
    for _, group in df.groupby(["site_key", "stratum"], dropna=False):
        take = min(40, len(group))
        sampled.append(group.sample(n=take, random_state=17) if len(group) > take else group)
    sample = pd.concat(sampled, ignore_index=True).head(420)

    inspected = []
    observations = []
    for _, row in sample.iterrows():
        inspected.append(
            {
                "record_key": row["record_key"],
                "contractor_path": row["contractor_path"],
                "site_key": row["site_key"],
                "stratum": row["stratum"],
                "record_source": "service_orders",
                "raw_values_emitted": False,
            }
        )
        for source_col, source_field in TEXT_FIELDS:
            if source_col not in row or pd.isna(row[source_col]):
                continue
            for term in term_candidates(row[source_col]):
                observations.append(
                    {
                        "observed_term": term,
                        "record_key": row["record_key"],
                        "contractor_path": row["contractor_path"],
                        "site_key": row["site_key"],
                        "stratum": row["stratum"],
                        "source_text_field": source_field,
                        "source_family": "source_data",
                    }
                )
    return inspected, observations


def sample_pdf_records() -> tuple[list[dict], list[dict]]:
    if not PDF_ROWS.exists():
        return [], []
    df = pd.read_csv(PDF_ROWS)
    df = df.copy()
    df["contractor_path"] = "CONTRACTOR_PATH_003"
    df["site_key"] = df["site_text"].map(lambda value: stable_key(value, "SITE")) if "site_text" in df.columns else "SITE-UNKNOWN"
    df["stratum"] = "event_structural"
    df["record_key"] = df["file_hash"].astype(str).map(lambda value: stable_key(value, "PDFROW")) + "-" + df.index.astype(str)

    sampled = []
    for _, group in df.groupby(["site_key", "event"], dropna=False):
        take = min(12, len(group))
        sampled.append(group.sample(n=take, random_state=23) if len(group) > take else group)
    sample = pd.concat(sampled, ignore_index=True).head(180)

    inspected = []
    observations = []
    for _, row in sample.iterrows():
        inspected.append(
            {
                "record_key": row["record_key"],
                "contractor_path": row["contractor_path"],
                "site_key": row["site_key"],
                "stratum": row["stratum"],
                "record_source": "pdf_assets_of_concern",
                "raw_values_emitted": False,
            }
        )
        if "event" in row and not pd.isna(row["event"]):
            for term in term_candidates(row["event"]):
                observations.append(
                    {
                        "observed_term": term,
                        "record_key": row["record_key"],
                        "contractor_path": row["contractor_path"],
                        "site_key": row["site_key"],
                        "stratum": "event_structural",
                        "source_text_field": "pdf_assets_of_concern.event",
                        "source_family": "source_data",
                    }
                )
    return inspected, observations


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    inspected_v, observations_v = sample_vestas_records()
    inspected_p, observations_p = sample_pdf_records()
    inspected = inspected_v + inspected_p
    observations = observations_v + observations_p

    grouped: dict[tuple[str, str, str, str, str], dict] = {}
    for obs in observations:
        target, status = target_for_term(obs["observed_term"])
        target_field = CANONICAL_TARGETS.get(target, "")
        namespace = TARGET_NAMESPACES.get(target, "")
        key = (
            obs["observed_term"],
            obs["source_text_field"],
            obs["stratum"],
            obs["contractor_path"],
            target,
        )
        entry = grouped.setdefault(
            key,
            {
                "concept_id": stable_key("|".join(key), "LEX"),
                "observed_term": obs["observed_term"],
                "normalised_term": obs["observed_term"],
                "canonical_concept": target.lower().replace(" ", "_") if target != "unknown" else "unknown",
                "target": target,
                "namespace": namespace,
                "target_field": target_field,
                "source_text_field": obs["source_text_field"],
                "stratum": obs["stratum"],
                "contractor_path": obs["contractor_path"],
                "site_count": set(),
                "record_count": set(),
                "observed_term_origin": "real_observed_label",
                "target_assignment_evidence_type": "expert_inference" if target != "unknown" else "unknown",
                "evidence_type": "expert_inference" if target != "unknown" else "unknown",
                "tier": "silver-medium" if target != "unknown" else "unresolved",
                "status": status,
                "language_hint": "en_or_mixed",
                "raw_values_emitted": False,
            },
        )
        entry["site_count"].add(obs["site_key"])
        entry["record_count"].add(obs["record_key"])

    rows = []
    for entry in grouped.values():
        entry = entry.copy()
        entry["site_count"] = len(entry["site_count"])
        entry["record_count"] = len(entry["record_count"])
        rows.append(entry)
    rows.sort(key=lambda r: (-r["record_count"], r["target"], r["observed_term"]))

    write_csv(
        LEXICAL_DIR / "lexical_seed_dictionary_v1.csv",
        rows,
        [
            "concept_id",
            "observed_term",
            "normalised_term",
            "canonical_concept",
            "target",
            "namespace",
            "target_field",
            "source_text_field",
            "stratum",
            "contractor_path",
            "site_count",
            "record_count",
            "observed_term_origin",
            "target_assignment_evidence_type",
            "evidence_type",
            "tier",
            "status",
            "language_hint",
            "raw_values_emitted",
        ],
    )
    sanitized_rows = []
    for row in rows:
        sanitized = row.copy()
        sanitized["observed_term_key"] = stable_key(row["observed_term"], "TERM")
        sanitized["normalised_term_key"] = stable_key(row["normalised_term"], "TERM")
        sanitized.pop("observed_term", None)
        sanitized.pop("normalised_term", None)
        sanitized["contains_source_derived_terms"] = False
        sanitized_rows.append(sanitized)
    write_csv(
        LEXICAL_DIR / "lexical_seed_dictionary_v1_sanitized.csv",
        sanitized_rows,
        [
            "concept_id",
            "observed_term_key",
            "normalised_term_key",
            "canonical_concept",
            "target",
            "namespace",
            "target_field",
            "source_text_field",
            "stratum",
            "contractor_path",
            "site_count",
            "record_count",
            "observed_term_origin",
            "target_assignment_evidence_type",
            "evidence_type",
            "tier",
            "status",
            "language_hint",
            "contains_source_derived_terms",
            "raw_values_emitted",
        ],
    )
    write_csv(
        OUTPUTS_DIR / "t8_sampled_records_v1.csv",
        inspected,
        ["record_key", "contractor_path", "site_key", "stratum", "record_source", "raw_values_emitted"],
    )

    target_summary = Counter(row["target"] for row in rows)
    stratum_summary = Counter(item["stratum"] for item in inspected)
    source_field_summary = Counter(row["source_text_field"] for row in rows)

    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "task": "T8_lexical_seed_dictionary",
        "records_inspected": len(inspected),
        "minimum_required_records_inspected": 500,
        "minimum_requirement_met": len(inspected) >= 500,
        "unique_lexical_entries": len(rows),
        "target_summary": dict(target_summary),
        "sampled_record_strata": dict(stratum_summary),
        "source_text_fields": dict(source_field_summary),
        "source_text_field_required": True,
        "stratification_mixing_guardrail": "Do not mix planned/reactive strata with event_structural in the same count.",
        "candidate_generation_performed": False,
        "lexical_seed_dictionary_contains_source_derived_terms": True,
        "versioned_sanitized_dictionary_available": True,
        "raw_full_text_emitted": False,
        "raw_values_emitted": False,
        "outputs": {
            "lexical_dictionary_csv": "stint-1.1-reference-layer/reference_layer/lexical_layer/lexical_seed_dictionary_v1.csv",
            "lexical_dictionary_sanitized_csv": "stint-1.1-reference-layer/reference_layer/lexical_layer/lexical_seed_dictionary_v1_sanitized.csv",
            "sampled_records_csv": "stint-1.1-reference-layer/outputs/t8_sampled_records_v1.csv",
            "normalisation_pipeline_spec": "stint-1.1-reference-layer/reference_layer/semantic_normalisation/normalisation_pipeline_spec.md",
            "memo": "stint-1.1-reference-layer/docs/t8_lexical_seed_dictionary.md",
        },
    }
    (OUTPUTS_DIR / "t8_lexical_seed_dictionary_summary_v1.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    pipeline_lines = [
        "# Normalisation Pipeline Specification",
        "",
        "This is the specification of the flow that STINT_1 will execute; it is not a production candidate run.",
        "",
        "## Five-Step Flow",
        "",
        "1. Mask tags and identifiers: remove or mask asset IDs, order IDs, serial-like strings, dates, and numeric counters before lexical matching.",
        "2. Clean text: lowercase, normalize whitespace, remove punctuation that does not carry domain meaning, and preserve domain words.",
        "3. Expand abbreviations: use the lexical seed dictionary plus curated bilingual aliases. Abbreviation expansion must retain provenance.",
        "4. Correct spelling: apply conservative correction only when the target term is in a controlled reference layer entry.",
        "5. NER / concept routing: route normalized spans to canonical concepts and then to SAP_MAPPING candidates or FLOC/IH06 node candidates.",
        "",
        "## Guardrails",
        "",
        "- Do not pre-translate all text. Use multilingual backbone assumptions plus bilingual canonical dictionaries.",
        "- Preserve `source_text_field` for every observed term.",
        "- Preserve `stratum` and never mix planned/reactive records with `event_structural` PDF rows in the same denominator.",
        "- `Umrichter` is converter context, not generator context.",
        "- A lexical match is not a validated mapping. Promotion requires evidence triangulation in STINT_1.",
    ]
    (SEMANTIC_DIR / "normalisation_pipeline_spec.md").write_text("\n".join(pipeline_lines) + "\n", encoding="utf-8")

    memo_lines = [
        "# T8 - Lexical Seed Dictionary",
        "",
        "## Purpose",
        "",
        "T8 builds a seed lexical layer from sampled real records as a contact/calibration test for `reference-layer-v1`.",
        "",
        "It does not execute the STINT_1 candidate pipeline and does not claim target-level denominators or model performance.",
        "",
        "## Result",
        "",
        f"- Records inspected/captured by sampling: {summary['records_inspected']}",
        f"- Minimum required: {summary['minimum_required_records_inspected']}",
        f"- Minimum met: {summary['minimum_requirement_met']}",
        f"- Unique lexical entries: {summary['unique_lexical_entries']}",
        f"- Target summary: `{summary['target_summary']}`",
        f"- Sample strata: `{summary['sampled_record_strata']}`",
        "",
        "## Required Controls",
        "",
        "- `source_text_field` is populated for every lexical entry, satisfying the DELTA-0003 control for this artefact.",
        "- `event_structural` PDF rows are not mixed with planned/reactive strata.",
        "- Every non-unknown lexical entry carries a canonical destination field from `canonical-constraints.md`.",
        "- Unknown terms remain unresolved and are not promoted.",
        "- The working dictionary contains source-derived lexical terms and must remain local-only. The versionable dictionary replaces terms with stable keys.",
        "",
        "## Outputs",
        "",
        "- `reference_layer/lexical_layer/lexical_seed_dictionary_v1.csv` local-only working dictionary",
        "- `reference_layer/lexical_layer/lexical_seed_dictionary_v1_sanitized.csv` versionable keyed dictionary",
        "- `reference_layer/semantic_normalisation/normalisation_pipeline_spec.md`",
        "- `outputs/t8_sampled_records_v1.csv`",
        "- `outputs/t8_lexical_seed_dictionary_summary_v1.json`",
    ]
    (DOCS_DIR / "t8_lexical_seed_dictionary.md").write_text("\n".join(memo_lines) + "\n", encoding="utf-8")

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
