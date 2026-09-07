from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import re
from collections import Counter, defaultdict
from collections.abc import Mapping
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer


PROJECT_ROOT = Path("/home/adien-i7-remote/workspace/fsa_bridge_ml_feasibility")
OUTPUT_DIR = PROJECT_ROOT / "stint-1-evidence-ground-truth/phase_5_symptom/outputs/f51_symptom_thread_resolution"
INTERNAL_DIR = PROJECT_ROOT / "reports/internal/t51b23b_oem_polysemy_profile"
INTERNAL_MANIFEST = PROJECT_ROOT / "reports/internal/f40b_contractor_path_001_relational_model/f40b_contractor_path_001_entity_manifest_internal.csv"
INTERNAL_DICT = PROJECT_ROOT / "reports/internal/t51b23_oem_alarm_dictionary/t51b23_oem_alarm_dictionary_internal_raw_and_normalised.csv"

ENTITY = "api_service_v1_service-orders"
CONTRACTOR_PATH = "CONTRACTOR_PATH_001"
MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

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


def parse_date_bucket(value: object) -> str:
    text = as_text(value)
    if not text:
        return ""
    dt = pd.to_datetime(text, errors="coerce", utc=True)
    if pd.isna(dt):
        return ""
    return f"{dt.year}-Q{((dt.month - 1) // 3) + 1}"


def entropy(values: list[str]) -> float:
    total = len(values)
    if total == 0:
        return 0.0
    counts = Counter(values)
    return round(-sum((count / total) * math.log2(count / total) for count in counts.values()), 4)


def max_concentration(values: list[str]) -> float:
    if not values:
        return 0.0
    counts = Counter(values)
    return round(max(counts.values()) / len(values), 4)


def pairwise_stats(texts: list[str], embedding_cache: dict[str, np.ndarray]) -> dict[str, float]:
    if len(texts) < 2:
        return {"mean_pairwise_similarity": 1.0, "min_pairwise_similarity": 1.0, "max_pairwise_similarity": 1.0}
    embeddings = np.asarray([embedding_cache[text] for text in texts])
    sims = embeddings @ embeddings.T
    values = [float(sims[i, j]) for i, j in combinations(range(len(texts)), 2)]
    return {
        "mean_pairwise_similarity": round(float(np.mean(values)), 4),
        "min_pairwise_similarity": round(float(np.min(values)), 4),
        "max_pairwise_similarity": round(float(np.max(values)), 4),
    }


def classify_polysemy(stats: dict[str, float], n_variants: int) -> str:
    mean_sim = stats["mean_pairwise_similarity"]
    min_sim = stats["min_pairwise_similarity"]
    if n_variants == 2 and mean_sim >= 0.82:
        return "likely_transcription_variant"
    if mean_sim >= 0.78 and min_sim >= 0.68:
        return "likely_transcription_variant"
    if mean_sim <= 0.55 or min_sim <= 0.35:
        return "likely_polysemous"
    return "undetermined"


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str], mode: int | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    if mode is not None:
        os.chmod(path, mode)


def assert_sanitized(paths: list[Path]) -> None:
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="ignore")
        hits = [pattern.pattern for pattern in RAW_PATTERNS if pattern.search(text)]
        if hits:
            raise RuntimeError(f"Sanitization failed for {path.name}: {hits}")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    INTERNAL_DIR.mkdir(parents=True, exist_ok=True)

    oem = pd.read_csv(INTERNAL_DICT, dtype=str).fillna("")
    records = load_json_records(service_orders_path())
    context_by_phy: dict[str, dict[str, str]] = {}
    for idx, record in enumerate(records):
        phy = physical_record_id(record, idx)
        date_bucket = (
            parse_date_bucket(record.get("actualStartDate"))
            or parse_date_bucket(record.get("plannedStartDate"))
            or parse_date_bucket(record.get("statusUpdatedAt"))
        )
        context_by_phy[phy] = {
            "site_hash": prefixed_hash(record.get("siteId"), "SITE", 10) if as_text(record.get("siteId")) else "",
            "asset_type_hash": prefixed_hash(record.get("assetType"), "ASSETTYPE", 10) if as_text(record.get("assetType")) else "",
            "date_quarter": date_bucket,
        }

    enriched_rows: list[dict[str, Any]] = []
    for row in oem.to_dict("records"):
        context = context_by_phy.get(as_text(row.get("physical_record_id")), {})
        enriched_rows.append(
            {
                **row,
                "code_hash": prefixed_hash(row.get("code"), "OEMCODE", 10),
                "normalised_description_hash": prefixed_hash(as_text(row.get("normalised_description")).lower(), "OEMDESC", 10),
                "site_hash": context.get("site_hash", ""),
                "asset_type_hash": context.get("asset_type_hash", ""),
                "date_quarter": context.get("date_quarter", ""),
            }
        )

    by_code: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in enriched_rows:
        by_code[as_text(row["code"])].append(row)

    multi_codes = {
        code: rows
        for code, rows in by_code.items()
        if len({as_text(row["normalised_description"]).lower() for row in rows}) > 1
    }
    all_descriptions = sorted(
        {
            as_text(row["normalised_description"]).lower()
            for rows in multi_codes.values()
            for row in rows
            if as_text(row["normalised_description"])
        }
    )
    model = SentenceTransformer(MODEL_NAME)
    desc_embeddings = model.encode(all_descriptions, normalize_embeddings=True, show_progress_bar=False, batch_size=128)
    embedding_cache = {text: np.asarray(vector) for text, vector in zip(all_descriptions, desc_embeddings, strict=True)}

    profile_rows = []
    correlation_rows = []
    sample_groups = []
    histogram = Counter()

    for code, rows in sorted(multi_codes.items(), key=lambda item: (-len({as_text(r["normalised_description"]).lower() for r in item[1]}), item[0])):
        desc_counts = Counter(as_text(row["normalised_description"]).lower() for row in rows)
        raw_desc_counts = Counter(as_text(row["raw_description"]) for row in rows)
        descriptions = sorted(desc_counts)
        stats = pairwise_stats(descriptions, embedding_cache)
        classification = classify_polysemy(stats, len(descriptions))
        histogram[str(min(len(descriptions), 5)) if len(descriptions) < 5 else "5_plus"] += 1

        site_values = [as_text(row["site_hash"]) for row in rows if as_text(row["site_hash"])]
        asset_values = [as_text(row["asset_type_hash"]) for row in rows if as_text(row["asset_type_hash"])]
        date_values = [as_text(row["date_quarter"]) for row in rows if as_text(row["date_quarter"])]

        desc_site_sets = {
            prefixed_hash(desc, "OEMDESC", 10): len({as_text(row["site_hash"]) for row in rows if as_text(row["normalised_description"]).lower() == desc and as_text(row["site_hash"])})
            for desc in descriptions
        }
        desc_asset_sets = {
            prefixed_hash(desc, "OEMDESC", 10): len({as_text(row["asset_type_hash"]) for row in rows if as_text(row["normalised_description"]).lower() == desc and as_text(row["asset_type_hash"])})
            for desc in descriptions
        }

        profile_rows.append(
            {
                "code_hash": prefixed_hash(code, "OEMCODE", 10),
                "occurrence_rows": len(rows),
                "distinct_normalised_descriptions": len(descriptions),
                "distinct_raw_descriptions": len(raw_desc_counts),
                "mean_pairwise_similarity": stats["mean_pairwise_similarity"],
                "min_pairwise_similarity": stats["min_pairwise_similarity"],
                "max_pairwise_similarity": stats["max_pairwise_similarity"],
                "polysemy_classification": classification,
                "collapse_recommendation": "do_not_collapse_profile_only" if classification != "likely_transcription_variant" else "candidate_for_later_collapse_review",
                "raw_operational_values_emitted": False,
            }
        )

        correlation_rows.append(
            {
                "code_hash": prefixed_hash(code, "OEMCODE", 10),
                "polysemy_classification": classification,
                "site_context_rows": len(site_values),
                "distinct_site_hashes": len(set(site_values)),
                "site_max_concentration": max_concentration(site_values),
                "site_entropy": entropy(site_values),
                "asset_type_context_rows": len(asset_values),
                "distinct_asset_type_hashes": len(set(asset_values)),
                "asset_type_max_concentration": max_concentration(asset_values),
                "asset_type_entropy": entropy(asset_values),
                "date_context_rows": len(date_values),
                "distinct_date_quarters": len(set(date_values)),
                "context_split_signal": (
                    "possible_context_key_needed"
                    if classification == "likely_polysemous" and (len(set(site_values)) > 1 or len(set(asset_values)) > 1)
                    else "no_context_split_conclusion"
                ),
                "raw_operational_values_emitted": False,
            }
        )

        if len(sample_groups) < 20:
            variants = []
            for desc, count in desc_counts.most_common():
                raw_examples = [raw for raw, raw_count in raw_desc_counts.most_common() if raw and desc in raw.lower()]
                variants.append(
                    {
                        "normalised_description": desc,
                        "occurrence_rows": count,
                        "normalised_description_hash": prefixed_hash(desc, "OEMDESC", 10),
                        "sample_raw_description": raw_examples[0] if raw_examples else "",
                    }
                )
            sample_groups.append(
                {
                    "sample_group_id": f"T51B23B-GROUP-{len(sample_groups)+1:03d}",
                    "code": code,
                    "code_hash": prefixed_hash(code, "OEMCODE", 10),
                    "occurrence_rows": len(rows),
                    "distinct_normalised_descriptions": len(descriptions),
                    "mean_pairwise_similarity": stats["mean_pairwise_similarity"],
                    "min_pairwise_similarity": stats["min_pairwise_similarity"],
                    "polysemy_classification": classification,
                    "variants_json": json.dumps(variants, ensure_ascii=False),
                    "reviewer_assessment": "",
                    "allowed_response": "transcription_variant | true_polysemy | context_collision | undetermined",
                    "reviewer_notes": "",
                }
            )

    histogram_rows = [
        {
            "variant_count_bucket": bucket,
            "code_count": count,
            "pct_of_multi_description_codes": round(100 * count / len(multi_codes), 2) if multi_codes else 0.0,
            "raw_operational_values_emitted": False,
        }
        for bucket, count in sorted(histogram.items(), key=lambda item: item[0])
    ]

    class_counts = Counter(row["polysemy_classification"] for row in profile_rows)
    summary = {
        "created_at_utc": utc_now(),
        "pass_id": "T5.1b2.3b",
        "task_type": "oem_polysemic_code_profile",
        "oem_occurrence_rows": len(enriched_rows),
        "codes_total": len(by_code),
        "multi_description_codes": len(multi_codes),
        "polysemy_classification_counts": dict(class_counts),
        "variant_count_histogram": dict(histogram),
        "embedding_model": MODEL_NAME,
        "classification_action": "profile_only_no_collapse_no_dedup_no_sap_mapping",
        "context_fields_profiled": ["site_hash", "asset_type_hash", "date_quarter"],
        "internal_visible_sample_groups": len(sample_groups),
        "raw_operational_values_emitted_to_versioned_artifacts": False,
        "internal_visible_sample_location": "reports/internal/t51b23b_oem_polysemy_profile/",
    }

    profile_path = OUTPUT_DIR / "t51b23b_polysemy_profile_sanitized.csv"
    correlation_path = OUTPUT_DIR / "t51b23b_platform_correlation_sanitized.csv"
    histogram_path = OUTPUT_DIR / "t51b23b_polysemy_variant_histogram_sanitized.csv"
    summary_path = OUTPUT_DIR / "t51b23b_polysemy_profile_summary_sanitized.json"
    memo_path = OUTPUT_DIR / "t51b23b_polysemy_profile_memo.md"
    sample_path = INTERNAL_DIR / "t51b23b_polysemy_sample_visible_internal.csv"

    write_csv(
        profile_path,
        profile_rows,
        [
            "code_hash",
            "occurrence_rows",
            "distinct_normalised_descriptions",
            "distinct_raw_descriptions",
            "mean_pairwise_similarity",
            "min_pairwise_similarity",
            "max_pairwise_similarity",
            "polysemy_classification",
            "collapse_recommendation",
            "raw_operational_values_emitted",
        ],
    )
    write_csv(
        correlation_path,
        correlation_rows,
        [
            "code_hash",
            "polysemy_classification",
            "site_context_rows",
            "distinct_site_hashes",
            "site_max_concentration",
            "site_entropy",
            "asset_type_context_rows",
            "distinct_asset_type_hashes",
            "asset_type_max_concentration",
            "asset_type_entropy",
            "date_context_rows",
            "distinct_date_quarters",
            "context_split_signal",
            "raw_operational_values_emitted",
        ],
    )
    write_csv(histogram_path, histogram_rows, ["variant_count_bucket", "code_count", "pct_of_multi_description_codes", "raw_operational_values_emitted"])
    write_csv(
        sample_path,
        sample_groups,
        [
            "sample_group_id",
            "code",
            "code_hash",
            "occurrence_rows",
            "distinct_normalised_descriptions",
            "mean_pairwise_similarity",
            "min_pairwise_similarity",
            "polysemy_classification",
            "variants_json",
            "reviewer_assessment",
            "allowed_response",
            "reviewer_notes",
        ],
        mode=0o600,
    )
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    memo_path.write_text(
        "# T5.1b2.3b - OEM Polysemic Code Profile\n\n"
        "## Purpose\n\n"
        "Profile OEM codes with multiple observed descriptions before any collapse, deduplication, SAP mapping, or denominator promotion.\n\n"
        "## Results\n\n"
        f"- OEM occurrence rows: `{len(enriched_rows)}`.\n"
        f"- Total OEM codes: `{len(by_code)}`.\n"
        f"- Multi-description codes: `{len(multi_codes)}`.\n"
        f"- Classification counts: `{dict(class_counts)}`.\n\n"
        "## Method\n\n"
        f"Description variants are compared using `{MODEL_NAME}` embeddings over normalized descriptions. "
        "Codes are labelled as `likely_transcription_variant`, `likely_polysemous`, or `undetermined` for profiling only.\n\n"
        "## Context Guardrail\n\n"
        "Platform correlation is reported using hashed site and asset-type context plus date-quarter span. "
        "A context signal does not prove platform collision; it only indicates whether a composite dictionary key may be needed.\n\n"
        "## Decision Guardrail\n\n"
        "No code-description pair is collapsed in this pass. The internal sample is for direct review of the highest-dispersion groups.\n",
        encoding="utf-8",
    )

    assert_sanitized([profile_path, correlation_path, histogram_path, summary_path, memo_path])
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
