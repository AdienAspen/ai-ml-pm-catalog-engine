from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from collections import Counter, defaultdict
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import pandas as pd
from g20c_lexical_safety import POLICY as LEXICAL_SAFETY_POLICY
from g20c_lexical_safety import restricted_match

PROJECT_ROOT = Path("/home/adien-i7-remote/workspace/fsa_bridge_ml_feasibility")
STINT2_ROOT = PROJECT_ROOT / "stint-2-target-ml-prototyping"
STINT1_ROOT = PROJECT_ROOT / "stint-1-evidence-ground-truth"
OUT = STINT2_ROOT / "g2_baseline_models/outputs/g20_corpus_native_domain_vocab"

SERVICE_ORDERS_JSON = PROJECT_ROOT / (
    "data/interim/extracted_source/package_001_37cac7fe/Data/Vestas/"
    "api_service_v1_service-orders.json"
)
PATH_A_EVENTS = (
    STINT1_ROOT / "phase_3_path_a_faultcodes/outputs/f354_estimated_events_sanitized.csv"
)
PATH_A_ASSIGNMENTS = (
    STINT1_ROOT / "phase_3_path_a_faultcodes/outputs/f354_snapshot_row_assignments_sanitized.csv"
)
PATH_A_PDF_ROWS = PROJECT_ROOT / "reports/internal/pdf_assets_of_concern_rows.csv"
PATH_A_NOTES = PROJECT_ROOT / "reports/internal/path_a_repair/f353_notes_semantics_internal.csv"
B25_SCRIPT = STINT1_ROOT / "phase_4_path_b_xlsx/scripts/b25_grouping_refinement.py"
B2_SOURCE_ROOTS = [
    PROJECT_ROOT / "data/interim/extracted_source/package_001_37cac7fe/Data/Latigo Wind GE EOD",
    PROJECT_ROOT
    / "data/interim/extracted_source/package_001_37cac7fe/Data/Pioneer GE Info/Pioneer GE Info",
    PROJECT_ROOT / "data/interim/extracted_source/package_003_19512420/GE Prevailing",
]

EVAL_V1_EXCLUSIONS = (
    STINT2_ROOT
    / "artifacts/evaluation_sets/evaluation_set_v1/evaluation_set_v1_training_exclusion_keys.csv"
)
LEAKAGE_REGEX_CATALOG = STINT2_ROOT / (
    "g2_baseline_models/outputs/g20_target_leakage_quantification/"
    "g20b_leakage_regex_catalog_sanitized.csv"
)
LEAKAGE_MASKING_MANIFEST = STINT2_ROOT / (
    "g2_baseline_models/outputs/g20_target_leakage_quantification/"
    "g20b_masking_manifest_sanitized.csv"
)
G02_SAMPLE_MANIFEST = STINT2_ROOT / (
    "g0_independent_evaluation/outputs/annotation_samples/"
    "g02_annotation_sample_manifest_sanitized.csv"
)
G02_VISIBLE_PACKAGES = [
    STINT2_ROOT
    / (
        "g0_independent_evaluation/internal/g02_annotation_packages/"
        "g02_visible_package_chapter_team_annotator_01.csv"
    ),
    STINT2_ROOT
    / (
        "g0_independent_evaluation/internal/g02_annotation_packages/"
        "g02_visible_package_chapter_team_annotator_02.csv"
    ),
]

NORMALISATION_VERSION = "semantic_normalisation_v2"
EXTRACTION_METHOD = "corpus_native_neutral_ngram_extraction_v2"
CONSTRUCTION_METHOD = (
    "corpus_extracted_neutral_ngram_target_assignment_deferred_to_semantic_grouping"
)
TARGET_ASSIGNMENT = "none_step1_target_unassigned"

# Generic maintenance abbreviations only. This map is analyst-authored and is
# recorded separately. It is not sourced from G2.0 prototypes or SAP/ZEUS.
ABBREVIATIONS = {
    "assy": "assembly",
    "brg": "bearing",
    "brgs": "bearings",
    "conv": "converter",
    "det": "detector",
    "gen": "generator",
    "gbx": "gearbox",
    "insp": "inspection",
    "maint": "maintenance",
    "repl": "replace",
    "svc": "service",
    "temp": "temperature",
    "xfmr": "transformer",
}

# Operational organisation/site tokens are neither domain concepts nor valid
# corpus-native vocabulary seeds.
OPERATIONAL_ENTITY_TOKENS = {
    "aes",
    "ge",
    "latigo",
    "pioneer",
    "takkion",
    "vestas",
}


def as_text(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def stable_hash(value: object, length: int = 16) -> str:
    return hashlib.sha256(as_text(value).encode("utf-8", errors="ignore")).hexdigest()[:length]


def prefixed_hash(prefix: str, value: object, length: int = 16) -> str:
    return f"{prefix}-{stable_hash(value, length)}"


def physical_record_id(order_id: object) -> str:
    return prefixed_hash(
        "PHY", f"CONTRACTOR_PATH_001|api_service_v1_service-orders|{as_text(order_id)}", 16
    )


def load_json_records(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        for key in ["data", "items", "value", "records", "results"]:
            if isinstance(payload.get(key), list):
                return [row for row in payload[key] if isinstance(row, dict)]
    raise RuntimeError(f"Unsupported JSON payload: {path}")


def load_b1_units() -> list[dict[str, Any]]:
    units = []
    for record in load_json_records(SERVICE_ORDERS_JSON):
        key = physical_record_id(record.get("id"))
        units.append(
            {
                "unit_key": key,
                "source_unit_key": key,
                "path_bucket": "B1_RELATIONAL",
                "segments": [
                    ("reason", as_text(record.get("reason"))),
                    ("descriptionExtended", as_text(record.get("descriptionExtended"))),
                ],
            }
        )
    return units


def load_b25_module():
    spec = importlib.util.spec_from_file_location("b25", B25_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load B25 module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_b2_units() -> list[dict[str, Any]]:
    b25 = load_b25_module()
    files = []
    for root in B2_SOURCE_ROOTS:
        files.extend(sorted(root.rglob("*.xls*")))
    if not files:
        raise RuntimeError("No B2 workbook files found")
    grouped: dict[str, list[str]] = defaultdict(list)
    for path in files:
        for row in b25.iter_groupable_text_rows(path):
            grouped[str(row["refined_event_key"])].append(str(row["normalized_text"]))
    units = []
    for key, texts in grouped.items():
        text = " ".join(texts)
        units.append(
            {
                "unit_key": key,
                "source_unit_key": key,
                "path_bucket": "B2_WORKBOOKS",
                "source_text_hash": semantic_text_hash(text),
                "segments": [("b25_groupable_text", text)],
            }
        )
    return units


def load_path_a_units() -> list[dict[str, Any]]:
    events = pd.read_csv(PATH_A_EVENTS)
    assignments = pd.read_csv(PATH_A_ASSIGNMENTS)
    pdf = pd.read_csv(PATH_A_PDF_ROWS).fillna("")
    pdf["fault_code_norm"] = pdf["fault_code"].map(as_text)
    pdf["row_key"] = pdf.apply(
        lambda row: (
            "PATHA-SRCROW-"
            + stable_hash(
                "|".join(
                    [
                        str(row.get("path_hash", "")),
                        str(row.get("file_hash", "")),
                        prefixed_hash("ASSET", row.get("asset", ""), 10),
                        prefixed_hash("CODE", row.get("fault_code_norm", ""), 10),
                        str(row.get("duration", "")),
                        str(row.get("event", "")),
                    ]
                ),
                12,
            )
        ),
        axis=1,
    )
    event_rows = assignments[["estimated_event_key", "row_key"]].merge(
        pdf, on="row_key", how="left"
    )
    text_by_event: dict[str, list[str]] = defaultdict(list)
    for row in event_rows.itertuples(index=False):
        text_by_event[str(row.estimated_event_key)].append(
            " ".join(
                [
                    as_text(getattr(row, "event", "")),
                    as_text(getattr(row, "fault_code", "")),
                    as_text(getattr(row, "state", "")),
                ]
            )
        )
    notes = pd.read_csv(PATH_A_NOTES).fillna("")
    if {"file_hash", "note_line_text"}.issubset(
        notes.columns
    ) and "file_hash" in event_rows.columns:
        event_files = event_rows[["estimated_event_key", "file_hash"]].drop_duplicates()
        for row in notes.merge(event_files, on="file_hash", how="inner").itertuples(index=False):
            text_by_event[str(row.estimated_event_key)].append(as_text(row.note_line_text))
    return [
        {
            "unit_key": key,
            "source_unit_key": key,
            "path_bucket": "PATH_A",
            "segments": [("path_a_constituted_text", text) for text in text_by_event.get(key, [])],
        }
        for key in events["estimated_event_key"].astype(str)
    ]


def load_leakage_patterns() -> list[tuple[re.Pattern[str], str, str]]:
    catalog = pd.read_csv(LEAKAGE_REGEX_CATALOG).fillna("")
    patterns = []
    for row in catalog.to_dict("records"):
        canonical = as_text(row["canonical_target"])
        token = (
            "[MASKED_" + re.sub(r"[^A-Z0-9]+", "_", canonical.upper()).strip("_") + "_ASSIGNMENT]"
        )
        patterns.append((re.compile(as_text(row["regex"]), re.I), token, canonical))
    return patterns


def apply_leakage_mask(
    text: str, patterns: list[tuple[re.Pattern[str], str, str]]
) -> tuple[str, int, set[str]]:
    value = text
    total = 0
    targets: set[str] = set()
    for pattern, token, canonical in patterns:
        value, count = pattern.subn(token, value)
        if count:
            total += count
            targets.add(canonical)
    return value, total, targets


def normalise_text(text: str) -> tuple[list[str], int]:
    value = text
    value = re.sub(r"\[MASKED_[A-Z0-9_]+\]", " ", value, flags=re.I)
    value = re.sub(r"https?://\S+|www\.\S+", " ", value, flags=re.I)
    value = re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", " ", value)
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"^\s*\d{2,6}\s*[-:– ]\s*", " ", value)
    value = re.sub(r"\b\d{2,6}\s*[-:–]\s*", " ", value)
    value = re.sub(r"[_]+", " ", value)
    value = re.sub(r"[:./|]+", " ", value)
    value = re.sub(r"([a-z])([A-Z])", r"\1 \2", value)
    value = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", value)
    value = re.sub(r"([A-Za-z])(\d)", r"\1 \2", value)
    value = re.sub(r"(\d)([A-Za-z])", r"\1 \2", value)
    value = re.sub(r"\b\d+\b", " ", value)
    value = re.sub(r"\b(?:deg|c|cnt|day|days|hr|hrs|wtg|t)\b", " ", value, flags=re.I)
    value = re.sub(r"[^A-Za-zÀ-ÖØ-öø-ÿß\s'-]+", " ", value)
    raw_tokens = []
    for token in value.split():
        parts = [part.lower() for part in re.split(r"[-']+", token) if part]
        raw_tokens.extend(part for part in parts if part not in OPERATIONAL_ENTITY_TOKENS)
    expansion_count = sum(1 for token in raw_tokens if token in ABBREVIATIONS)
    return [ABBREVIATIONS.get(token, token) for token in raw_tokens], expansion_count


def semantic_text_hash(text: str) -> str:
    masked, _, _ = apply_leakage_mask(text, LEAKAGE_PATTERNS)
    tokens, _ = normalise_text(masked)
    return prefixed_hash("SEMTEXT", " ".join(tokens), 16)


def unit_semantic_hashes(unit: dict[str, Any]) -> set[str]:
    texts = [as_text(text) for _, text in unit["segments"] if as_text(text)]
    hashes = {semantic_text_hash(text) for text in texts}
    if texts:
        hashes.add(semantic_text_hash(" ".join(texts)))
    return hashes


def ngrams(tokens: list[str]) -> Iterable[str]:
    for size in (1, 2, 3):
        for start in range(0, len(tokens) - size + 1):
            term = " ".join(tokens[start : start + size])
            if not restricted_match(term):
                yield term


def load_exclusions() -> tuple[set[str], set[str], set[str], set[str], list[dict[str, object]]]:
    eval_keys = set(pd.read_csv(EVAL_V1_EXCLUSIONS)["source_unit_key"].dropna().astype(str))
    heldout_keys: set[str] = set()
    sources = []
    for path in sorted(STINT2_ROOT.rglob("*split_manifest*.csv")):
        frame = pd.read_csv(path).fillna("")
        key_col = next(
            (col for col in ["source_unit_key", "split_unit_key"] if col in frame.columns), None
        )
        if key_col is None:
            continue
        subset_cols = [
            col
            for col in frame.columns
            if col in {"calibration_subset", "split", "subset", "evaluation_subset"}
        ]
        if not subset_cols:
            continue
        heldout_mask = pd.Series(False, index=frame.index)
        for col in subset_cols:
            heldout_mask |= frame[col].astype(str).str.contains("heldout", case=False, regex=False)
        keys = set(frame.loc[heldout_mask, key_col].astype(str))
        heldout_keys.update(key for key in keys if key)
        sources.append(
            {
                "exclusion_source": str(path.relative_to(STINT2_ROOT)),
                "exclusion_type": "heldout_manifest",
                "rows_scanned": len(frame),
                "heldout_rows": int(heldout_mask.sum()),
                "distinct_source_unit_keys": len(keys),
                "raw_operational_values_emitted": False,
            }
        )
    sources.append(
        {
            "exclusion_source": str(EVAL_V1_EXCLUSIONS.relative_to(STINT2_ROOT)),
            "exclusion_type": "evaluation_set_v1",
            "rows_scanned": sum(1 for _ in open(EVAL_V1_EXCLUSIONS, encoding="utf-8")) - 1,
            "heldout_rows": 0,
            "distinct_source_unit_keys": len(eval_keys),
            "raw_operational_values_emitted": False,
        }
    )
    sample_manifest = pd.read_csv(G02_SAMPLE_MANIFEST).fillna("")
    package_frames = [
        pd.read_csv(path, usecols=["annotation_id", "text_pii_redacted"]).fillna("")
        for path in G02_VISIBLE_PACKAGES
    ]
    package_text = pd.concat(package_frames, ignore_index=True).drop_duplicates("annotation_id")
    package_map = sample_manifest.loc[:, ["annotation_id", "source_unit_key", "path_bucket"]].merge(
        package_text, on="annotation_id", how="inner", validate="one_to_one"
    )
    package_map["text_hash"] = package_map["text_pii_redacted"].map(semantic_text_hash)
    package_map = (
        package_map[["source_unit_key", "path_bucket", "text_hash"]].drop_duplicates().fillna("")
    )
    eval_content_hashes = set(
        package_map.loc[
            package_map["source_unit_key"].astype(str).isin(eval_keys), "text_hash"
        ].astype(str)
    )
    heldout_content_hashes = set(
        package_map.loc[
            package_map["source_unit_key"].astype(str).isin(heldout_keys), "text_hash"
        ].astype(str)
    )
    sources.append(
        {
            "exclusion_source": "g02_internal_visible_packages_joined_to_sample_manifest",
            "exclusion_type": "cross_namespace_reconciliation_by_semantic_normalised_text_hash",
            "rows_scanned": len(package_map),
            "heldout_rows": len(heldout_content_hashes),
            "distinct_source_unit_keys": len(eval_content_hashes | heldout_content_hashes),
            "raw_operational_values_emitted": False,
        }
    )
    return eval_keys, heldout_keys, eval_content_hashes, heldout_content_hashes, sources


def exclusion_reason(
    unit: dict[str, Any],
    eval_keys: set[str],
    heldout_keys: set[str],
    eval_content_hashes: set[str],
    heldout_content_hashes: set[str],
) -> str:
    key = unit["source_unit_key"]
    content_hashes = unit_semantic_hashes(unit)
    if key in eval_keys or content_hashes & eval_content_hashes:
        return "evaluation_set_v1"
    if key in heldout_keys or content_hashes & heldout_content_hashes:
        return "additional_heldout"
    return ""


def aggregate_candidates(
    units: list[dict[str, Any]], path_sizes: dict[str, int]
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, dict[str, int]]]:
    term_frequency: Counter[tuple[str, str]] = Counter()
    unit_frequency: Counter[tuple[str, str]] = Counter()
    source_fields: dict[tuple[str, str], set[str]] = defaultdict(set)
    audits = []
    path_totals: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for unit in units:
        unit_counts: Counter[str] = Counter()
        path = unit["path_bucket"]
        token_count = 0
        expansion_count = 0
        nonempty_segments = 0
        for field, raw_text in unit["segments"]:
            masked_text, mask_count, _ = apply_leakage_mask(raw_text, LEAKAGE_PATTERNS)
            tokens, expansions = normalise_text(masked_text)
            if tokens:
                nonempty_segments += 1
            token_count += len(tokens)
            expansion_count += expansions
            segment_counts = Counter(ngrams(tokens))
            unit_counts.update(segment_counts)
            for term in segment_counts:
                source_fields[(path, term)].add(field)
            path_totals[path]["mask_segments"] += int(mask_count > 0)
            path_totals[path]["mask_matches"] += mask_count
        for term, count in unit_counts.items():
            key = (path, term)
            term_frequency[key] += count
            unit_frequency[key] += 1
        path_totals[path]["tokens"] += token_count
        path_totals[path]["expansions"] += expansion_count
        path_totals[path]["zero_token_units"] += int(token_count == 0)
        audits.append(
            {
                "universe": "model_eligible_construction_corpus",
                "path_bucket": path,
                "unit_key_hash": prefixed_hash("UNIT", unit["unit_key"], 12),
                "normalised_token_count": token_count,
                "nonempty_source_segments": nonempty_segments,
                "abbreviation_expansions": expansion_count,
                "raw_operational_values_emitted": False,
            }
        )

    rows = []
    for (path, term), frequency in term_frequency.items():
        units_with_term = unit_frequency[(path, term)]
        rows.append(
            {
                "target": "unassigned",
                "path_bucket": path,
                "candidate_term": term,
                "term_hash": prefixed_hash("TERM", term, 16),
                "ngram_length": len(term.split()),
                "source_text_fields": ";".join(sorted(source_fields[(path, term)])),
                "term_frequency": frequency,
                "units_with_term": units_with_term,
                "path_units": path_sizes[path],
                "unit_coverage_pct": round(100 * units_with_term / path_sizes[path], 6),
                "construction_universe": "model_eligible_construction_corpus",
                "normalisation_pipeline": NORMALISATION_VERSION,
                "extraction_method": EXTRACTION_METHOD,
                "lexical_safety_policy": LEXICAL_SAFETY_POLICY,
                "construction_method": CONSTRUCTION_METHOD,
                "ngram_to_target_assignment": TARGET_ASSIGNMENT,
                "grouping_status": "not_grouped_step1",
                "mapping_status": "not_mapped_step1",
                "prototype_seed_used": False,
                "evidence_type": "reference_evidence",
                "anchor_source": "domain_vocabulary",
                "raw_operational_values_emitted": False,
            }
        )
    candidates = pd.DataFrame(rows).sort_values(
        ["path_bucket", "units_with_term", "term_frequency", "candidate_term"],
        ascending=[True, False, False, True],
    )
    return candidates, pd.DataFrame(audits), path_totals


def build_top_term_retention(
    descriptive_candidates: pd.DataFrame,
    eligible_candidates: pd.DataFrame,
    top_n: int = 100,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    eligible_lookup = {
        (str(row.path_bucket), str(row.candidate_term)): row
        for row in eligible_candidates.itertuples(index=False)
    }
    rows = []
    for path, group in descriptive_candidates.groupby("path_bucket", sort=True):
        ranked = group.sort_values(
            ["units_with_term", "term_frequency", "candidate_term"],
            ascending=[False, False, True],
        ).head(top_n)
        for rank, row in enumerate(ranked.itertuples(index=False), start=1):
            eligible = eligible_lookup.get((str(path), str(row.candidate_term)))
            eligible_frequency = int(eligible.term_frequency) if eligible is not None else 0
            eligible_units = int(eligible.units_with_term) if eligible is not None else 0
            eligible_path_units = int(eligible.path_units) if eligible is not None else 0
            rows.append(
                {
                    "path_bucket": path,
                    "descriptive_rank": rank,
                    "candidate_term": row.candidate_term,
                    "term_hash": row.term_hash,
                    "ngram_length": row.ngram_length,
                    "descriptive_term_frequency": int(row.term_frequency),
                    "descriptive_units_with_term": int(row.units_with_term),
                    "descriptive_path_units": int(row.path_units),
                    "descriptive_unit_coverage_pct": row.unit_coverage_pct,
                    "eligible_term_frequency": eligible_frequency,
                    "eligible_units_with_term": eligible_units,
                    "eligible_path_units": eligible_path_units,
                    "eligible_unit_coverage_pct": (
                        round(100 * eligible_units / eligible_path_units, 6)
                        if eligible_path_units
                        else 0.0
                    ),
                    "retained_in_eligible": eligible is not None,
                    "term_frequency_retention_pct": round(
                        100 * eligible_frequency / int(row.term_frequency), 6
                    ),
                    "unit_count_retention_pct": round(
                        100 * eligible_units / int(row.units_with_term), 6
                    ),
                    "exclusion_bias_flag": (
                        "fully_lost"
                        if eligible is None
                        else "retained_below_50pct"
                        if eligible_units < 0.5 * int(row.units_with_term)
                        else "retained"
                    ),
                    "descriptive_full_corpus_use": "statistics_only",
                    "eligible_construction_use": "vocabulary_construction",
                    "target": "unassigned",
                    "normalisation_pipeline": NORMALISATION_VERSION,
                    "raw_operational_values_emitted": False,
                }
            )
    report = pd.DataFrame(rows)
    summary = (
        report.groupby("path_bucket", as_index=False)
        .agg(
            top_terms_checked=("candidate_term", "size"),
            terms_retained=("retained_in_eligible", "sum"),
            median_unit_count_retention_pct=("unit_count_retention_pct", "median"),
            minimum_unit_count_retention_pct=("unit_count_retention_pct", "min"),
            fully_lost_terms=(
                "exclusion_bias_flag",
                lambda values: int((values == "fully_lost").sum()),
            ),
            retained_below_50pct_terms=(
                "exclusion_bias_flag",
                lambda values: int((values == "retained_below_50pct").sum()),
            ),
        )
        .sort_values("path_bucket")
    )
    summary["terms_retained_pct"] = (
        100 * summary["terms_retained"] / summary["top_terms_checked"]
    ).round(6)
    summary["diagnostic_scope"] = "top_terms_from_descriptive_full_corpus"
    summary["candidate_construction_from_full_corpus"] = False
    summary["raw_operational_values_emitted"] = False
    return report, summary


def descriptive_stats(
    units: list[dict[str, Any]], universe: str
) -> tuple[list[dict[str, object]], dict[str, dict[str, int]]]:
    rows = []
    totals: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for unit in units:
        path = unit["path_bucket"]
        terms: set[str] = set()
        occurrence_count = 0
        token_count = 0
        mask_matches = 0
        for _, raw_text in unit["segments"]:
            masked, count, _ = apply_leakage_mask(raw_text, LEAKAGE_PATTERNS)
            tokens, expansions = normalise_text(masked)
            generated = list(ngrams(tokens))
            terms.update(generated)
            occurrence_count += len(generated)
            token_count += len(tokens)
            mask_matches += count
            totals[path]["expansions"] += expansions
        totals[path]["units"] += 1
        totals[path]["tokens"] += token_count
        totals[path]["ngram_occurrences"] += occurrence_count
        totals[path]["masked_units"] += int(mask_matches > 0)
        totals[path]["mask_matches"] += mask_matches
        totals[path]["zero_token_units"] += int(token_count == 0)
        rows.append(
            {
                "universe": universe,
                "path_bucket": path,
                "unit_key_hash": prefixed_hash("UNIT", unit["unit_key"], 12),
                "normalised_token_count": token_count,
                "distinct_ngrams_in_unit": len(terms),
                "ngram_occurrences_in_unit": occurrence_count,
                "leakage_mask_matches": mask_matches,
                "raw_operational_values_emitted": False,
            }
        )
    return rows, totals


def write_outputs() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    global LEAKAGE_PATTERNS
    LEAKAGE_PATTERNS = load_leakage_patterns()

    units = load_b1_units() + load_path_a_units() + load_b2_units()
    expected_path_sizes = {"B1_RELATIONAL": 10749, "PATH_A": 362, "B2_WORKBOOKS": 1857}
    actual_path_sizes = Counter(unit["path_bucket"] for unit in units)
    assert dict(actual_path_sizes) == expected_path_sizes, (actual_path_sizes, expected_path_sizes)
    assert len({unit["source_unit_key"] for unit in units}) == len(units), "Duplicate source units"

    expected_masked = set(
        pd.read_csv(LEAKAGE_MASKING_MANIFEST)["source_unit_key"].dropna().astype(str)
    )
    observed_masked = set()
    for unit in units:
        unit_mask_count = 0
        for _, text in unit["segments"]:
            _, count, _ = apply_leakage_mask(text, LEAKAGE_PATTERNS)
            unit_mask_count += count
        if unit_mask_count:
            observed_masked.add(unit["source_unit_key"])
    if observed_masked != expected_masked:
        raise RuntimeError(
            "G2.0b masking mismatch: "
            f"expected={len(expected_masked)} observed={len(observed_masked)} "
            f"missing={sorted(expected_masked - observed_masked)} "
            f"extra={sorted(observed_masked - expected_masked)}"
        )

    (
        eval_keys,
        heldout_keys,
        eval_content_hashes,
        heldout_content_hashes,
        exclusion_sources,
    ) = load_exclusions()
    content_match_counts = Counter()
    for unit in units:
        hashes = unit_semantic_hashes(unit)
        content_match_counts[(unit["path_bucket"], "evaluation_set_v1")] += int(
            bool(hashes & eval_content_hashes)
        )
        content_match_counts[(unit["path_bucket"], "additional_heldout")] += int(
            bool(hashes & heldout_content_hashes)
        )
    for path in expected_path_sizes:
        if content_match_counts[(path, "evaluation_set_v1")] == 0:
            raise RuntimeError(
                f"{path} content reconciliation produced zero evaluation-set matches"
            )
    reasons = {
        unit["unit_key"]: exclusion_reason(
            unit, eval_keys, heldout_keys, eval_content_hashes, heldout_content_hashes
        )
        for unit in units
    }
    eligible_units = [unit for unit in units if not reasons[unit["unit_key"]]]
    eligible_sizes = Counter(unit["path_bucket"] for unit in eligible_units)

    full_rows, full_totals = descriptive_stats(units, "descriptive_full_corpus")
    eligible_rows, eligible_totals = descriptive_stats(
        eligible_units, "model_eligible_construction_corpus"
    )
    candidates, eligible_audit, _ = aggregate_candidates(eligible_units, dict(eligible_sizes))
    descriptive_candidates, _, _ = aggregate_candidates(units, expected_path_sizes)
    retention_report, retention_summary = build_top_term_retention(
        descriptive_candidates, candidates
    )

    assert candidates["target"].eq("unassigned").all()
    assert candidates["prototype_seed_used"].eq(False).all()
    assert candidates["construction_universe"].eq("model_eligible_construction_corpus").all()
    assert (
        not candidates["construction_method"]
        .str.contains("prototype|sap|zeus", case=False, regex=True)
        .any()
    )

    candidates.to_csv(OUT / "g20c_candidate_terms_sanitized.csv", index=False)
    retention_report.to_csv(OUT / "g20c_step1_top_term_retention_sanitized.csv", index=False)
    retention_summary.to_csv(
        OUT / "g20c_step1_top_term_retention_summary_sanitized.csv", index=False
    )

    universe_rows = []
    for path in expected_path_sizes:
        full_count = actual_path_sizes[path]
        eligible_count = eligible_sizes[path]
        eval_excluded = sum(
            unit["path_bucket"] == path and reasons[unit["unit_key"]] == "evaluation_set_v1"
            for unit in units
        )
        heldout_excluded = sum(
            unit["path_bucket"] == path and reasons[unit["unit_key"]] == "additional_heldout"
            for unit in units
        )
        universe_rows.extend(
            [
                {
                    "universe": "descriptive_full_corpus",
                    "path_bucket": path,
                    "units": full_count,
                    "evaluation_set_v1_excluded": 0,
                    "additional_heldout_excluded": 0,
                    "candidate_construction_allowed": False,
                    "statistics_only": True,
                    "normalisation_pipeline": NORMALISATION_VERSION,
                    "raw_operational_values_emitted": False,
                },
                {
                    "universe": "model_eligible_construction_corpus",
                    "path_bucket": path,
                    "units": eligible_count,
                    "evaluation_set_v1_excluded": eval_excluded,
                    "additional_heldout_excluded": heldout_excluded,
                    "candidate_construction_allowed": True,
                    "statistics_only": False,
                    "normalisation_pipeline": NORMALISATION_VERSION,
                    "raw_operational_values_emitted": False,
                },
            ]
        )
    pd.DataFrame(universe_rows).to_csv(
        OUT / "g20c_step1_universe_register_sanitized.csv", index=False
    )
    pd.DataFrame(exclusion_sources).to_csv(
        OUT / "g20c_step1_exclusion_sources_sanitized.csv", index=False
    )
    reconciliation_rows = []
    for path in expected_path_sizes:
        reconciliation_rows.extend(
            [
                {
                    "path_bucket": path,
                    "exclusion_type": exclusion_type,
                    "current_units_matching_content_hash": content_match_counts[
                        (path, exclusion_type)
                    ],
                    "normalisation_pipeline": NORMALISATION_VERSION,
                    "matching_method": (
                        "exact_semantic_normalised_text_hash_on_segment_or_combined_text"
                    ),
                    "duplicate_text_exclusion": True,
                    "raw_operational_values_emitted": False,
                }
                for exclusion_type in ["evaluation_set_v1", "additional_heldout"]
            ]
        )
    pd.DataFrame(reconciliation_rows).to_csv(
        OUT / "g20c_step1_exclusion_reconciliation_sanitized.csv", index=False
    )

    audit_frame = pd.concat(
        [pd.DataFrame(full_rows), pd.DataFrame(eligible_rows)], ignore_index=True
    )
    summary_rows = []
    for universe, frame in audit_frame.groupby("universe"):
        for path, group in frame.groupby("path_bucket"):
            subset = (
                candidates[candidates["path_bucket"].eq(path)]
                if universe.startswith("model")
                else None
            )
            summary_rows.append(
                {
                    "universe": universe,
                    "path_bucket": path,
                    "units": len(group),
                    "mean_normalised_tokens": round(group["normalised_token_count"].mean(), 6),
                    "median_normalised_tokens": round(group["normalised_token_count"].median(), 6),
                    "zero_token_units": int(group["normalised_token_count"].eq(0).sum()),
                    "masked_units": int(group["leakage_mask_matches"].gt(0).sum()),
                    "mask_matches": int(group["leakage_mask_matches"].sum()),
                    "candidate_terms_emitted": len(subset) if subset is not None else 0,
                    "candidate_emission_allowed": subset is not None,
                    "target": "unassigned",
                    "normalisation_pipeline": NORMALISATION_VERSION,
                    "construction_method": CONSTRUCTION_METHOD,
                    "raw_operational_values_emitted": False,
                }
            )
    summary = pd.DataFrame(summary_rows)
    summary.to_csv(OUT / "g20c_step1_extraction_summary_sanitized.csv", index=False)
    (OUT / "g20c_step1_extraction_summary_sanitized.json").write_text(
        json.dumps(summary.to_dict("records"), indent=2), encoding="utf-8"
    )

    eligible_audit.to_csv(OUT / "g20c_step1_normalization_audit_sanitized.csv", index=False)
    candidates.groupby("path_bucket", group_keys=False).head(50).to_csv(
        OUT / "g20c_step1_top_terms_preview_sanitized.csv", index=False
    )

    rules = pd.DataFrame(
        [
            (
                "universe_split",
                "full_statistics_vs_model_eligible_construction",
                "governance",
                False,
            ),
            (
                "evaluation_exclusion",
                "evaluation_set_v1_plus_detected_heldout_manifests",
                "manifest_driven",
                False,
            ),
            (
                "cross_namespace_reconciliation",
                "g02_visible_text_semantic_hash_alias_and_duplicate_exclusion",
                "g02_internal_packages",
                False,
            ),
            ("leakage_masking", "g20b_regex_catalog_applied_before_normalisation", "g20b", False),
            (
                "operational_entity_masking",
                "known_organisation_and_site_tokens_removed_before_ngrams",
                "sanitisation_guard",
                False,
            ),
            (
                "normalisation",
                NORMALISATION_VERSION,
                "t51b2x_plus_declared_generic_abbreviations",
                False,
            ),
            ("extract_ngrams", "one_to_three_word_ngrams", "corpus", False),
            ("target_assignment", TARGET_ASSIGNMENT, CONSTRUCTION_METHOD, False),
            ("semantic_grouping", "deferred_to_step3", "not_executed", False),
            ("catalogue_mapping", "deferred_until_after_semantic_grouping", "not_executed", False),
            ("prototype_seed", "prohibited_and_not_used", "g20_prototypes", False),
        ],
        columns=["step", "rule", "provenance", "raw_operational_values_emitted"],
    )
    rules.to_csv(OUT / "g20c_step1_extraction_rules_sanitized.csv", index=False)

    pd.DataFrame(
        [
            {
                "abbreviation": key,
                "expansion": value,
                "construction_method": "analyst_authored_generic_maintenance_abbreviation_map",
                "prototype_seed_used": False,
                "catalogue_seed_used": False,
                "raw_operational_values_emitted": False,
            }
            for key, value in sorted(ABBREVIATIONS.items())
        ]
    ).to_csv(OUT / "g20c_step1_abbreviation_map_sanitized.csv", index=False)

    decision_rows = pd.DataFrame(
        [
            {
                "decision_id": "G20C-STRUCT-01",
                "decision": "extract_then_semantically_group_then_map",
                "status": "enforced",
            },
            {
                "decision_id": "G20C-STRUCT-02",
                "decision": "semantic_grouping_not_string_grouping",
                "status": "deferred_to_step3",
            },
            {
                "decision_id": "G20C-STRUCT-03",
                "decision": "g20_prototypes_must_not_seed_vocabulary",
                "status": "enforced_not_used",
            },
            {
                "decision_id": "G20C-STRUCT-04",
                "decision": "top_concept_share_detector_retained",
                "status": "deferred_to_step5",
            },
        ]
    )
    decision_rows["raw_operational_values_emitted"] = False
    decision_rows.to_csv(OUT / "g20c_step1_structural_decisions_sanitized.csv", index=False)

    retention_by_path = retention_summary.set_index("path_bucket")
    b2_lost_terms = retention_report.loc[
        retention_report["path_bucket"].eq("B2_WORKBOOKS")
        & retention_report["exclusion_bias_flag"].eq("fully_lost"),
        "candidate_term",
    ].tolist()

    memo = f"""# G2.0c Step 1 - Neutral Corpus-Native N-gram Extraction Rerun

## Status

Step 1 was regenerated as a target-neutral extraction. No filtering, semantic grouping,
catalogue mapping, candidate promotion, denominator change, or G2.0 rerun was performed.

## Universes

Two universes are registered:

- `descriptive_full_corpus`: all source units, used for descriptive statistics only.
- `model_eligible_construction_corpus`: excludes every `evaluation_set_v1` source unit
  and every source unit currently marked held-out in a split manifest. Only this universe
  emits candidate terms and may construct the future vocabulary.

Some B1, Path A, and B2 evidence uses historical or surface-specific namespaces. Frozen
G0/G2 exclusions are reconciled through a `semantic_normalisation_v2` fingerprint of the
internal G0.2 visible text. Each source segment and the combined unit text are checked; every
current unit sharing an excluded hash is removed. This also
prevents duplicate text from re-entering under a regenerated event ID.

This duplicate-text exclusion is intentionally conservative and systematically removes
more copies of frequent repeated text. The top-100 term-retention diagnostic compares the
full descriptive universe with the eligible universe without allowing full-corpus terms to
construct the vocabulary.

## Path A limitation

Path A retains 159 of 362 units. The other 203 units (56.08%) are excluded because they
belong to evaluation or share text with evaluation records. Path A vocabulary coverage must
therefore be reported as a small and selectively reduced construction sample.

## Frequent-term retention gate

{retention_summary.to_string(index=False)}

Interpretation:

- B1 retains all top-100 terms; median unit-count retention is
  {retention_by_path.loc["B1_RELATIONAL", "median_unit_count_retention_pct"]:.2f}%.
- Path A retains all top-100 term forms, but
  {int(retention_by_path.loc["PATH_A", "retained_below_50pct_terms"])} of them retain less
  than half their original unit count. Eligible Path A frequencies are not population
  prevalence estimates.
- B2 retains {int(retention_by_path.loc["B2_WORKBOOKS", "terms_retained"])} of its top 100.
  The fully lost terms are: {", ".join(b2_lost_terms)}. These remain descriptive findings
  only and may not be reintroduced as vocabulary seeds from evaluation text.

## Leakage masking

The G2.0b regex catalogue is applied before normalisation. The expected 13 leaked B1
source rows were all detected and masked on the G2.0c source fields. Mask tokens are
removed before n-gram emission and cannot become candidate terms.

## Normalisation and extraction

- Normalisation version: `{NORMALISATION_VERSION}`.
- B1 source fields: `reason` and `descriptionExtended` only.
- N-grams: 1 to 3 words.
- Generic maintenance abbreviations use the separately versioned analyst-authored map.
- Known operational organisation and site tokens are removed before n-gram extraction.
- G2.0 prototypes, ZEUS target prototypes, and SAP catalogue concepts were not used as seeds.

## Target assignment

Every row has `target=unassigned`. The `construction_method` is
`{CONSTRUCTION_METHOD}`. Assignment to Activity or Object Part is explicitly deferred
until after Step 2 filtering and Step 3 semantic grouping.

## Structural decisions

1. Extract, then group semantically, then map to the catalogue.
2. Group by semantic similarity, not string distance.
3. Never use G2.0 prototypes as vocabulary seeds.
4. Retain `top_concept_share` as a Step 5 generic-concept detector.
"""
    (OUT / "g20c_step1_extraction_memo.md").write_text(memo, encoding="utf-8")

    print(summary.to_string(index=False))
    print(f"candidate_rows={len(candidates)}")
    print(retention_summary.to_string(index=False))
    print(f"masked_expected={len(expected_masked)} masked_observed={len(observed_masked)}")
    print(f"eval_v1_exclusion_keys={len(eval_keys)} heldout_exclusion_keys={len(heldout_keys)}")
    print(
        f"eval_content_hashes={len(eval_content_hashes)} "
        f"heldout_content_hashes={len(heldout_content_hashes)}"
    )


if __name__ == "__main__":
    LEAKAGE_PATTERNS: list[tuple[re.Pattern[str], str, str]] = []
    write_outputs()
