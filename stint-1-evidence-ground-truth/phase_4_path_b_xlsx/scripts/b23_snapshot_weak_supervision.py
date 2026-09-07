from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from openpyxl import load_workbook


PROJECT_ROOT = Path("/home/adien-i7-remote/workspace/fsa_bridge_ml_feasibility")
STINT_ROOT = PROJECT_ROOT / "stint-1-evidence-ground-truth"
OUTPUT_DIR = STINT_ROOT / "phase_4_path_b_xlsx/outputs/b2_silver_labels"
B21_DIR = STINT_ROOT / "phase_4_path_b_xlsx/outputs/b2_snapshot_characterization"
B22_DIR = STINT_ROOT / "phase_4_path_b_xlsx/outputs/b2_snapshot_dedup"
RAW_LEXICAL_V1 = PROJECT_ROOT / "stint-1.1-reference-layer/reference_layer/lexical_layer/lexical_seed_dictionary_v1.csv"
HIGH_CONFIDENCE_LEXICAL = STINT_ROOT / "phase_1_lexical/outputs/lexical_layer_v2/lexical_layer_v2_high_confidence_candidates_sanitized.csv"

SOURCE_ROOTS = [
    PROJECT_ROOT / "data/interim/extracted_source/package_001_37cac7fe/Data/SITE_PATH_002 Wind OEM_ENTITY_001 EOD",
    PROJECT_ROOT / "data/interim/extracted_source/package_001_37cac7fe/Data/SITE_PATH_004 OEM_ENTITY_001 Info",
    PROJECT_ROOT / "data/interim/extracted_source/package_003_19512420/CONTRACTOR_PATH_002",
]

TARGETS = {"Activity", "Cause", "Damage", "Object Part", "Symptom"}
CONTRACTOR_PATH = "CONTRACTOR_PATH_B2_SNAPSHOT"

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


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).strip())


def normalize_text(value: object) -> str:
    text = clean_text(value).lower()
    text = re.sub(r"[^a-z0-9áéíóúüñ]+", " ", text)
    tokens = []
    for token in text.split():
        token = ABBREVIATIONS.get(token.strip(), token.strip())
        if token:
            tokens.append(token)
    return " ".join(tokens)


def stable_term_key(value: object) -> str:
    return prefixed_hash(normalize_text(value), "TERM", 12)


def contains_term(normalized_text: str, term: str) -> bool:
    if not normalized_text or not term:
        return False
    return re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", normalized_text) is not None


def family_for_path(path: Path) -> tuple[str, str]:
    text = str(path).lower()
    name = path.name.lower()
    if "site_path_002 wind oem_entity_001 eod" in text:
        return "SNAPSHOT_FAMILY_001", "EOD"
    if "site_path_004 oem_entity_001 info" in text:
        if name.startswith("pod"):
            return "SNAPSHOT_FAMILY_002", "POD"
        return "SNAPSHOT_FAMILY_002", "daily_or_eod"
    if "contractor_path_002" in text:
        if name.startswith("pod_"):
            return "SNAPSHOT_FAMILY_003", "POD"
        return "SNAPSHOT_FAMILY_003", "snapshot_unprefixed"
    return "SNAPSHOT_FAMILY_UNKNOWN", "unknown"


def date_bucket(path: Path) -> str:
    name = path.name.lower()
    m = re.search(r"(20\d{2})[ _.-]+(\d{1,2})[ _.-]+(\d{1,2})", name)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    m = re.search(r"(\d{1,2})[ _.-]+(\d{1,2})[ _.-]+(20\d{2})", name)
    if m:
        return f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"
    month_names = {
        "january": 1,
        "february": 2,
        "march": 3,
        "april": 4,
        "may": 5,
        "june": 6,
        "july": 7,
        "august": 8,
        "september": 9,
        "october": 10,
        "november": 11,
        "december": 12,
    }
    for word, num in month_names.items():
        if word in name:
            y = re.search(r"(20\d{2})", name)
            d = re.search(rf"{word}\D+(\d{{1,2}})", name)
            if y and d:
                return f"{y.group(1)}-{num:02d}-{int(d.group(1)):02d}"
    return "unknown_date"


def categorize_header(header: str) -> str:
    h = header.lower()
    checks = [
        ("asset_ref", r"\b(wtg|turbine|asset|unit)\b"),
        ("status", r"\b(status|state|condition)\b"),
        ("notes_text", r"\b(note|comment|remark|description|desc|summary)\b"),
        ("work_text", r"\b(work|action|activity|task|repair|maintenance)\b"),
        ("issue_text", r"\b(issue|fault|alarm|problem|reason|cause)\b"),
        ("component_ref", r"\b(component|part|material|item|equipment)\b"),
        ("code_ref", r"\b(code|id|number|no\.|#)\b"),
        ("date_time", r"\b(date|time|start|end|duration)\b"),
        ("contractor_or_owner", r"\b(contractor|owner|crew|team|vendor)\b"),
        ("location_ref", r"\b(site|plant|location|area)\b"),
    ]
    for label, pattern in checks:
        if re.search(pattern, h):
            return label
    return "other"


def likely_header_row(rows: list[list[str]]) -> tuple[int | None, list[str]]:
    best_idx = None
    best_score = 0
    best_values: list[str] = []
    for idx, row in enumerate(rows):
        values = [clean_text(v) for v in row]
        non_empty = [v for v in values if v]
        if len(non_empty) < 2:
            continue
        categories = [categorize_header(v) for v in non_empty]
        useful = sum(1 for c in categories if c != "other")
        score = useful * 3 + min(len(non_empty), 12)
        if score > best_score:
            best_score = score
            best_idx = idx + 1
            best_values = values
    return best_idx, best_values


ASSET_RE = re.compile(r"\b(?:wtg|turbine|tur|t)\s*[-#:]?\s*(\d{1,3})\b", re.I)
CODE_RE = re.compile(r"\b(?:code|fault|alarm)\s*[-#:]?\s*([a-z0-9]{2,8})\b", re.I)


def extract_asset_key(row_values: list[str], categories: list[str]) -> tuple[str, str]:
    candidates = []
    for value, category in zip(row_values, categories):
        if category == "asset_ref" and value:
            candidates.append(value)
    candidates.extend(v for v in row_values if ASSET_RE.search(v))
    for value in candidates:
        m = ASSET_RE.search(value)
        token = m.group(1) if m else normalize_text(value)
        if token:
            return prefixed_hash(token, "ASSET", 12), "present"
    return "ASSET-MISSING", "missing"


def extract_code_key(row_values: list[str], categories: list[str]) -> tuple[str, str]:
    candidates = [v for v, c in zip(row_values, categories) if c in {"code_ref", "issue_text", "status"} and v]
    for value in candidates:
        m = CODE_RE.search(value)
        token = m.group(1) if m else normalize_text(value)[:48]
        if token:
            return prefixed_hash(token, "CODE", 12), "present"
    return "CODE-MISSING", "missing"


def load_term_lookup() -> dict[str, str]:
    raw = pd.read_csv(RAW_LEXICAL_V1)
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


def iter_text_rows(path: Path) -> list[dict[str, object]]:
    family, doc_type = family_for_path(path)
    date = date_bucket(path)
    file_key = prefixed_hash(str(path.relative_to(PROJECT_ROOT)), "B2FILE", 12)
    wb = load_workbook(path, read_only=True, data_only=True)
    rows_out: list[dict[str, object]] = []
    for sheet_index, ws in enumerate(wb.worksheets, start=1):
        sample_rows = []
        for row in ws.iter_rows(min_row=1, max_row=min(ws.max_row or 1, 30), max_col=min(ws.max_column or 1, 30), values_only=True):
            sample_rows.append([clean_text(v) for v in row])
        header_row, headers = likely_header_row(sample_rows)
        if not header_row or not headers:
            continue
        categories = [categorize_header(h) for h in headers]
        text_positions = [i + 1 for i, c in enumerate(categories) if c in {"notes_text", "work_text", "issue_text"}]
        if not text_positions:
            continue
        max_col = max(len(headers), max(text_positions))
        for row_number, row in enumerate(ws.iter_rows(min_row=header_row + 1, max_col=max_col, values_only=True), start=header_row + 1):
            row_values = [clean_text(v) for v in row]
            text_chunks = [
                (pos, row_values[pos - 1])
                for pos in text_positions
                if pos - 1 < len(row_values) and len(row_values[pos - 1]) >= 8
            ]
            if not text_chunks:
                continue
            asset_key, asset_status = extract_asset_key(row_values, categories)
            code_key, code_status = extract_code_key(row_values, categories)
            text_signature = prefixed_hash("|".join(sorted(normalize_text(v) for _, v in text_chunks)), "TEXTSIG", 12)
            base_key = "|".join([family, doc_type, asset_key, code_key, text_signature])
            dated_key = "|".join([base_key, date])
            for pos, text in text_chunks:
                rows_out.append(
                    {
                        "physical_record_id": prefixed_hash(dated_key, "B2PHY", 16),
                        "snapshot_row_id": prefixed_hash(f"{file_key}|{sheet_index}|{row_number}|{text_signature}", "B2ROW", 16),
                        "estimated_event_key": prefixed_hash(base_key, "B2EVENT", 12),
                        "estimated_event_key_with_snapshot_date": prefixed_hash(dated_key, "B2EVENTDAY", 12),
                        "file_key": file_key,
                        "sheet_key": prefixed_hash(f"{file_key}|{sheet_index}", "B2SHEET", 12),
                        "family": family,
                        "doc_type": doc_type,
                        "snapshot_date_bucket": date,
                        "asset_ref_status": asset_status,
                        "code_ref_status": code_status,
                        "source_text_field": f"xlsx_snapshot.{categories[pos - 1]}",
                        "source_text_category": categories[pos - 1],
                        "normalized_text": normalize_text(text),
                    }
                )
    wb.close()
    return rows_out


def term_index(terms: list[dict[str, object]]) -> tuple[dict[str, list[dict[str, object]]], int]:
    index: dict[str, list[dict[str, object]]] = defaultdict(list)
    max_len = 1
    for term in terms:
        norm = str(term["term_norm"])
        if not norm:
            continue
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


def build_hits(text_rows: list[dict[str, object]], terms: list[dict[str, object]]) -> list[dict[str, object]]:
    hits: list[dict[str, object]] = []
    lookup, max_len = term_index(terms)
    for text_row in text_rows:
        normalized_text = str(text_row["normalized_text"])
        matched_terms = []
        for gram in text_ngrams(normalized_text, max_len):
            matched_terms.extend(lookup.get(gram, []))
        for term in matched_terms:
            target = str(term["target"])
            status = "b2_snapshot_text_candidate_requires_review"
            confidence = "lexical_high_exact_term_hit"
            can_support_proxy = False
            notes = "High-confidence lexical anchor observed in B2 snapshot text. Requires review before proxy denominator use."
            if target == "Symptom":
                status = "b2_symptom_like_candidate_source_unconfirmed"
                notes = "Symptom-like lexical anchor observed, but B2 has no confirmed initial problem report field."
            hits.append(
                {
                    "record_id": prefixed_hash(f"{text_row['physical_record_id']}|{target}|{text_row['source_text_field']}|{term['canonical_concept_id']}", "REC", 16),
                    "physical_record_id": text_row["physical_record_id"],
                    "estimated_event_key": text_row["estimated_event_key"],
                    "estimated_event_key_with_snapshot_date": text_row["estimated_event_key_with_snapshot_date"],
                    "target": target,
                    "evidence_type": "expert_inference",
                    "tier": "silver-medium",
                    "status": status,
                    "source_path": str(text_row["family"]),
                    "source_text_field": text_row["source_text_field"],
                    "stratum": "event_structural",
                    "site_key": "SITE-unresolved_snapshot_family",
                    "contractor_path": CONTRACTOR_PATH,
                    "concept_id": str(term["canonical_concept_id"]),
                    "confidence": confidence,
                    "label_generation_method": "b2_3_snapshot_lexical_layer_v2_rule",
                    "evaluation_independence": "derived_from_rules",
                    "can_support_contractual_denominator": False,
                    "can_support_proxy_denominator": can_support_proxy,
                    "notes": notes,
                    "raw_operational_values_emitted": False,
                    "term_key": str(term["term_key"]),
                    "canonical_concept_key": str(term["canonical_concept_key"]),
                    "match_score": float(term["match_score"]),
                    "embedding_model": str(term["embedding_model"]),
                    "doc_type": str(text_row["doc_type"]),
                    "family": str(text_row["family"]),
                    "asset_ref_status": str(text_row["asset_ref_status"]),
                    "code_ref_status": str(text_row["code_ref_status"]),
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
    if b22b.get("recommended_b2_denominator_key") != "estimated_event_key_with_snapshot_date":
        raise RuntimeError("B2.3 blocked: B2.2b conservative event key decision is missing.")
    b21b = json.loads((B21_DIR / "b21b_known_positive_validation_summary_sanitized.json").read_text(encoding="utf-8"))
    if b21b.get("known_positive_case_validation") != "passed_direct_cell_markers":
        raise RuntimeError("B2.3 blocked: B2.1b known-positive validation is not passed.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    terms = load_high_confidence_terms()
    files: list[Path] = []
    for root in SOURCE_ROOTS:
        files.extend(sorted(root.rglob("*.xls*")))
    text_rows: list[dict[str, object]] = []
    for path in sorted(files):
        text_rows.extend(iter_text_rows(path))
    hits = build_hits(text_rows, terms)
    df = pd.DataFrame(hits)

    if df.empty:
        by_target = pd.DataFrame()
        by_doc = pd.DataFrame()
        target_event_counts = {}
    else:
        by_target = (
            df.groupby(["target", "status"], dropna=False)
            .agg(
                evidence_rows=("record_id", "size"),
                conservative_event_units=("physical_record_id", "nunique"),
                persistence_clusters=("estimated_event_key", "nunique"),
                canonical_concepts=("concept_id", "nunique"),
                term_keys=("term_key", "nunique"),
            )
            .reset_index()
            .sort_values(["target", "status"])
        )
        by_target["raw_operational_values_emitted"] = False
        by_doc = (
            df.groupby(["doc_type", "target"], dropna=False)
            .agg(
                evidence_rows=("record_id", "size"),
                conservative_event_units=("physical_record_id", "nunique"),
                persistence_clusters=("estimated_event_key", "nunique"),
                canonical_concepts=("concept_id", "nunique"),
            )
            .reset_index()
            .sort_values(["doc_type", "target"])
        )
        by_doc["raw_operational_values_emitted"] = False
        target_event_counts = df.groupby("target")["physical_record_id"].nunique().to_dict()

    text_doc_counts = Counter(str(row["doc_type"]) for row in text_rows)
    summary = {
        "created_at_utc": utc_now(),
        "pass_id": "B2.3",
        "task_type": "snapshot_text_weak_supervision",
        "files_scanned": len(files),
        "text_rows_extracted": len(text_rows),
        "text_rows_by_doc_type": dict(sorted(text_doc_counts.items())),
        "lexical_high_terms_loaded": len(terms),
        "evidence_rows": len(hits),
        "conservative_event_unit": "estimated_event_key_with_snapshot_date",
        "conservative_event_units_with_any_candidate": int(df["physical_record_id"].nunique()) if not df.empty else 0,
        "record_target_units_with_any_candidate": int(df[["physical_record_id", "target"]].drop_duplicates().shape[0]) if not df.empty else 0,
        "target_conservative_event_counts": {str(k): int(v) for k, v in sorted(target_event_counts.items())},
        "contractual_denominator_supported": False,
        "proxy_denominator_candidate_units_after_review": 0,
        "symptom_status": "symptom_like_terms_possible_but_initial_problem_source_unconfirmed",
        "label_generation_method": "b2_3_snapshot_lexical_layer_v2_rule",
        "evaluation_independence": "derived_from_rules",
        "raw_operational_values_emitted": False,
        "outputs": [
            "b23_snapshot_silver_labels_memo.md",
            "b23_snapshot_silver_labels_sanitized.csv",
            "b23_snapshot_by_target_sanitized.csv",
            "b23_snapshot_by_doc_type_target_sanitized.csv",
            "b23_snapshot_summary_sanitized.json",
        ],
    }

    fieldnames = [
        "record_id",
        "physical_record_id",
        "estimated_event_key",
        "estimated_event_key_with_snapshot_date",
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
        "asset_ref_status",
        "code_ref_status",
    ]
    write_csv(OUTPUT_DIR / "b23_snapshot_silver_labels_sanitized.csv", hits, fieldnames)
    by_target.to_csv(OUTPUT_DIR / "b23_snapshot_by_target_sanitized.csv", index=False)
    by_doc.to_csv(OUTPUT_DIR / "b23_snapshot_by_doc_type_target_sanitized.csv", index=False)
    (OUTPUT_DIR / "b23_snapshot_summary_sanitized.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    target_lines = []
    if not by_target.empty:
        for row in by_target.itertuples(index=False):
            target_lines.append(
                f"| {row.target} | {row.status} | {int(row.evidence_rows)} | {int(row.conservative_event_units)} | {int(row.persistence_clusters)} | {int(row.canonical_concepts)} |"
            )
    memo = "\n".join(
        [
            "# B2.3 Snapshot Text Weak Supervision",
            "",
            "## Scope",
            "",
            "This pass applies `LEXICAL_LAYER v2` high-confidence anchors to validated B2 snapshot workbook text structures. It uses the conservative date-sensitive event unit selected in B2.2b.",
            "",
            "## Summary",
            "",
            f"- Files scanned: `{summary['files_scanned']}`",
            f"- Text rows extracted: `{summary['text_rows_extracted']}`",
            f"- Lexical high-confidence terms loaded: `{summary['lexical_high_terms_loaded']}`",
            f"- Evidence rows: `{summary['evidence_rows']}`",
            f"- Conservative event units with any candidate: `{summary['conservative_event_units_with_any_candidate']}`",
            f"- Record-target units with any candidate: `{summary['record_target_units_with_any_candidate']}`",
            f"- Contractual denominator supported: `{summary['contractual_denominator_supported']}`",
            f"- Proxy denominator candidate units after review: `{summary['proxy_denominator_candidate_units_after_review']}`",
            "",
            "## By Target",
            "",
            "| target | status | evidence_rows | conservative_event_units | persistence_clusters | canonical_concepts |",
            "| --- | --- | ---: | ---: | ---: | ---: |",
            *target_lines,
            "",
            "## Interpretation",
            "",
            "B2.3 emits weak-supervision candidates only. Because labels are generated by lexical rules, `evaluation_independence` is `derived_from_rules` and no contractual denominator is supported.",
            "",
            "Symptom-like anchors are retained as candidates but not promoted: B2 still has no confirmed initial problem report field.",
            "",
            "The safe event unit is `estimated_event_key_with_snapshot_date`; persistence clusters are reported only for context.",
            "",
            "raw_operational_values_emitted: false",
            "",
        ]
    )
    (OUTPUT_DIR / "b23_snapshot_silver_labels_memo.md").write_text(memo, encoding="utf-8")
    assert_sanitized(list(OUTPUT_DIR.glob("b23_*")))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
