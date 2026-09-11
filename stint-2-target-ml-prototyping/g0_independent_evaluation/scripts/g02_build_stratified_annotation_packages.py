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
from pathlib import Path
from typing import Any

from openpyxl import load_workbook


PROJECT_ROOT = Path("/home/adien-i7-remote/workspace/fsa_bridge_ml_feasibility")
STINT2_ROOT = PROJECT_ROOT / "stint-2-target-ml-prototyping"
STINT1_ROOT = PROJECT_ROOT / "stint-1-evidence-ground-truth"
G0_OUT = STINT2_ROOT / "g0_independent_evaluation" / "outputs" / "annotation_samples"
INTERNAL_OUT = STINT2_ROOT / "g0_independent_evaluation" / "internal" / "g02_annotation_packages"

PROTOCOL_VERSION = "G0.1-v1"
TARGET_SAMPLE_SIZE = 300
OVERLAP_RATE = 0.25
MAX_SOURCE_UNIT_SHARE = 0.05
RANDOM_SEED = "STINT2-G0.2-v1"
ANNOTATORS = ["chapter_team_annotator_01", "chapter_team_annotator_02"]

SERVICE_ORDER_ENTITY = "api_service_v1_service-orders"
CONTRACTOR_PATH = "CONTRACTOR_PATH_001"
INTERNAL_MANIFEST = PROJECT_ROOT / "reports/internal/f40b_contractor_path_001_relational_model/f40b_contractor_path_001_entity_manifest_internal.csv"

B1_TEXTUAL = STINT1_ROOT / "phase_4_path_b_xlsx/outputs/b1_silver_labels/b1_silver_labels_textual_residue_sanitized.csv"
B25_EVIDENCE = STINT1_ROOT / "phase_4_path_b_xlsx/outputs/b25_grouping_refinement/b25_grouped_reanchored_evidence_sanitized.csv"
B25_ROWS = STINT1_ROOT / "phase_4_path_b_xlsx/outputs/b25_grouping_refinement/b25_grouped_snapshot_rows_sanitized.csv"
PATH_A_EVIDENCE = STINT1_ROOT / "phase_3_path_a_faultcodes/outputs/f356_path_a_integrated_crosswalk_sanitized.csv"
PATH_A_REVIEW = PROJECT_ROOT / "reports/internal/path_a_repair/f355_path_a_crosswalk_v2_internal_review_redacted.csv"
PATH_A_NOTES = PROJECT_ROOT / "reports/internal/path_a_repair/f353_notes_semantics_internal.csv"
B1_DETERMINISTIC = STINT1_ROOT / "phase_4_path_b_xlsx/outputs/b1_deterministic_harvest/b1_deterministic_harvest_evidence_sanitized.csv"
SYMPTOM_UNITS = G0_OUT / "g00b_symptom_row_level_units_sanitized.csv"
INVENTORY = G0_OUT / "g00_target_path_inventory_sanitized.csv"

B2_SOURCE_ROOTS = [
    (
        PROJECT_ROOT / "data/interim/extracted_source/package_001_37cac7fe/Data/Latigo Wind GE EOD",
        PROJECT_ROOT / "data/interim/extracted_source/package_001_37cac7fe/Data/Latigo Wind GE EOD",
    ),
    (
        PROJECT_ROOT / "data/interim/extracted_source/package_001_37cac7fe/Data/Pioneer GE Info",
        PROJECT_ROOT / "data/interim/extracted_source/package_001_37cac7fe/Data/Pioneer GE Info",
    ),
    (
        PROJECT_ROOT / "data/interim/extracted_source/package_003_19512420/GE Prevailing",
        PROJECT_ROOT / "data/interim/extracted_source/package_003_19512420/GE Prevailing",
    ),
]
PATH_A_CONCERN_ROWS = PROJECT_ROOT / "reports/internal/pdf_assets_of_concern_rows.csv"

VOCAB = {
    "Symptom": "observed_condition | dispatch_motive | ambiguous | not_interpretable | abstain",
    "Damage": "damage_present | symptom_not_damage | action_not_damage | not_interpretable | abstain",
    "Cause": "cause_present | no_cause_stated | not_interpretable | abstain",
    "Activity": "activity_present | condition_not_activity | not_interpretable | abstain",
    "Object Part": "component_identified | system_only | no_component | not_interpretable | abstain",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_hash(value: object, length: int = 16) -> str:
    raw = "" if value is None else str(value)
    return hashlib.sha256(raw.encode("utf-8", errors="ignore")).hexdigest()[:length]


def prefixed_hash(value: object, prefix: str, length: int = 12) -> str:
    return f"{prefix}-{stable_hash(value, length)}"


def deterministic_sort_key(*parts: object) -> str:
    return stable_hash("|".join(str(part) for part in (RANDOM_SEED, *parts)), 32)


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).strip())


def redact_pii(text: str) -> str:
    value = clean_text(text)
    value = re.sub(r"https?://\S+|www\.\S+", "<URL>", value, flags=re.I)
    value = re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", "<EMAIL>", value)
    value = re.sub(r"\+?\b(?:\d[\s()./-]*){8,}\b", "<NUMBER>", value)
    value = re.sub(
        r"\b(?:badge|employee|emp|phone|mobile|cell|email)\s*[:#-]?\s*[A-Za-z0-9._%+-]+\b",
        "<PII_REF>",
        value,
        flags=re.I,
    )
    return re.sub(r"\s+", " ", value).strip()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str], mode_600: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})
    if mode_600:
        os.chmod(path, 0o600)


def write_json(path: Path, payload: dict[str, object], mode_600: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    if mode_600:
        os.chmod(path, 0o600)


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
    for row in read_csv(INTERNAL_MANIFEST):
        if row.get("entity_label") == SERVICE_ORDER_ENTITY:
            return Path(row["json_path"])
    raise RuntimeError(f"Missing manifest entity {SERVICE_ORDER_ENTITY}")


def physical_record_id(record: Mapping[str, object], fallback_index: int) -> str:
    record_key = clean_text(record.get("id")) or str(fallback_index)
    return prefixed_hash(f"{CONTRACTOR_PATH}|{SERVICE_ORDER_ENTITY}|{record_key}", "PHY", 16)


def load_service_order_texts() -> tuple[dict[str, dict[str, str]], dict[str, str], list[str]]:
    by_phy: dict[str, dict[str, str]] = {}
    reason_by_hash: dict[str, str] = {}
    reason_rows: list[str] = []
    for idx, record in enumerate(load_json_records(service_orders_path())):
        phy = physical_record_id(record, idx)
        reason = clean_text(record.get("reason"))
        desc = clean_text(record.get("descriptionExtended"))
        by_phy[phy] = {
            "reason": redact_pii(reason),
            "descriptionExtended": redact_pii(desc),
        }
        if reason:
            reason_hash = prefixed_hash(reason.lower(), "REASON", 12)
            reason_by_hash.setdefault(reason_hash, redact_pii(reason))
            reason_rows.append(redact_pii(reason))
    return by_phy, reason_by_hash, reason_rows


def b2_short_hash(value: str, prefix: str, length: int = 12) -> str:
    return f"{prefix}-{hashlib.sha256(value.encode('utf-8', errors='ignore')).hexdigest()[:length]}"


def b2_normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def b2_family_for_path(path: Path) -> tuple[str, str]:
    text = str(path).lower()
    name = path.name.lower()
    if "site_path_002 wind oem_entity_001 eod" in text or "latigo wind ge eod" in text:
        return "SNAPSHOT_FAMILY_001", "EOD"
    if "site_path_004 oem_entity_001 info" in text or "pioneer ge info" in text:
        if name.startswith("pod"):
            return "SNAPSHOT_FAMILY_002", "POD"
        return "SNAPSHOT_FAMILY_002", "daily_or_eod"
    if "contractor_path_002" in text or "ge prevailing" in text or "ge laurel mountain" in text:
        if name.startswith("pod_"):
            return "SNAPSHOT_FAMILY_003", "POD"
        return "SNAPSHOT_FAMILY_003", "snapshot_unprefixed"
    return "SNAPSHOT_FAMILY_UNKNOWN", "unknown"


def b2_date_bucket(path: Path) -> str:
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


def b2_categorize_header(header: str) -> str:
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


def b2_likely_header_row(rows: list[list[str]]) -> tuple[int | None, list[str]]:
    best_idx = None
    best_score = 0
    best_values: list[str] = []
    for idx, row in enumerate(rows):
        values = [clean_text(v) for v in row]
        non_empty = [v for v in values if v]
        if len(non_empty) < 2:
            continue
        categories = [b2_categorize_header(v) for v in non_empty]
        useful = sum(1 for c in categories if c != "other")
        score = useful * 3 + min(len(non_empty), 12)
        if score > best_score:
            best_score = score
            best_idx = idx + 1
            best_values = values
    return best_idx, best_values


ASSET_RE = re.compile(r"\b(?:wtg|turbine|tur|t)\s*[-#:]?\s*(\d{1,3})\b", re.I)
CODE_RE = re.compile(r"\b(?:code|fault|alarm)\s*[-#:]?\s*([a-z0-9]{2,8})\b", re.I)


def b2_extract_asset_key(row_values: list[str], categories: list[str]) -> str:
    candidates = [v for v, c in zip(row_values, categories) if c == "asset_ref" and v]
    candidates.extend(v for v in row_values if ASSET_RE.search(v))
    for value in candidates:
        m = ASSET_RE.search(value)
        token = m.group(1) if m else b2_normalized(value)
        if token:
            return b2_short_hash(token, "ASSET")
    return "ASSET-MISSING"


def b2_extract_code_key(row_values: list[str], categories: list[str]) -> str:
    candidates = [v for v, c in zip(row_values, categories) if c in {"code_ref", "issue_text", "status"} and v]
    for value in candidates:
        m = CODE_RE.search(value)
        token = m.group(1) if m else b2_normalized(value)[:48]
        if token:
            return b2_short_hash(token, "CODE")
    return "CODE-MISSING"


def load_b2_text_maps() -> tuple[dict[str, str], dict[str, str]]:
    row_to_refined: dict[str, set[str]] = defaultdict(set)
    for row in read_csv(B25_ROWS):
        row_to_refined[row["snapshot_row_id"]].add(row["refined_event_key"])

    event_texts: dict[str, list[str]] = defaultdict(list)
    classifier_texts: dict[str, str] = {}
    files: list[Path] = []
    aliases: dict[Path, Path] = {}
    for actual_root, alias_root in B2_SOURCE_ROOTS:
        for path in sorted(actual_root.rglob("*.xls*")) if actual_root.exists() else []:
            files.append(path)
            aliases[path] = alias_root / path.relative_to(actual_root)
    for path in sorted(files):
        alias_path = aliases[path]
        family, doc_type = b2_family_for_path(alias_path)
        date = b2_date_bucket(path)
        file_key = b2_short_hash(str(alias_path.relative_to(PROJECT_ROOT)), "B2FILE")
        try:
            wb = load_workbook(path, read_only=True, data_only=True)
        except Exception:
            continue
        for sheet_index, ws in enumerate(wb.worksheets, start=1):
            sample_rows: list[list[str]] = []
            for row in ws.iter_rows(min_row=1, max_row=min(ws.max_row or 1, 30), max_col=min(ws.max_column or 1, 30), values_only=True):
                sample_rows.append([clean_text(v) for v in row])
            header_row, headers = b2_likely_header_row(sample_rows)
            if not header_row or not headers:
                continue
            categories = [b2_categorize_header(h) for h in headers]
            text_positions = [i + 1 for i, c in enumerate(categories) if c in {"notes_text", "work_text", "issue_text"}]
            if not text_positions:
                continue
            max_col = max(len(headers), max(text_positions))
            for row_number, row in enumerate(ws.iter_rows(min_row=header_row + 1, max_col=max_col, values_only=True), start=header_row + 1):
                row_values = [clean_text(v) for v in row]
                text_values = [row_values[pos - 1] for pos in text_positions if pos - 1 < len(row_values) and len(row_values[pos - 1]) >= 8]
                if not text_values:
                    continue
                asset_key = b2_extract_asset_key(row_values, categories)
                code_key = b2_extract_code_key(row_values, categories)
                text_signature = b2_short_hash("|".join(sorted(b2_normalized(v) for v in text_values)), "TEXTSIG")
                snapshot_row_id = b2_short_hash(f"{file_key}|{sheet_index}|{row_number}|{text_signature}", "B2ROW", 16)
                for refined in row_to_refined.get(snapshot_row_id, set()):
                    event_texts[refined].extend(redact_pii(value) for value in text_values)
                for pos in text_positions:
                    text = row_values[pos - 1] if pos - 1 < len(row_values) else ""
                    if len(text) >= 8:
                        record_hash = b2_short_hash(f"{file_key}|{sheet_index}|{row_number}|{pos}", "B2TXT")
                        classifier_texts.setdefault(record_hash, redact_pii(text))
    return {key: " | ".join(dict.fromkeys(values)) for key, values in event_texts.items()}, classifier_texts


def load_path_a_concern_text() -> dict[str, str]:
    out: dict[str, str] = {}
    if not PATH_A_CONCERN_ROWS.exists():
        return out
    for idx, row in enumerate(read_csv(PATH_A_CONCERN_ROWS)):
        key = f"AOC-{row.get('file_hash', '')}-{idx}"
        text = row.get("event", "")
        if key and text:
            out[key] = redact_pii(text)
    return out


def load_path_a_text() -> tuple[dict[tuple[str, str], str], dict[str, str]]:
    by_event_target: dict[tuple[str, str], list[str]] = defaultdict(list)
    if PATH_A_REVIEW.exists():
        for row in read_csv(PATH_A_REVIEW):
            pieces = [row.get("code_context_redacted", ""), row.get("notes_context_redacted", "")]
            text = " | ".join(redact_pii(piece) for piece in pieces if clean_text(piece))
            if text:
                by_event_target[(row.get("estimated_event_key", ""), row.get("target", ""))].append(text)
    note_text: dict[str, str] = {}
    if PATH_A_NOTES.exists():
        for row in read_csv(PATH_A_NOTES):
            key = row.get("note_line_key", "")
            text = row.get("note_line_text", "")
            if key and text:
                note_text[key] = redact_pii(text)
    return {key: " | ".join(dict.fromkeys(values)) for key, values in by_event_target.items()}, note_text


def anchor_source_for_row(row: dict[str, str]) -> str:
    source_text_field = row.get("source_text_field", "")
    concept_id = row.get("concept_id", "")
    namespace = row.get("namespace", "")
    evidence_source = row.get("evidence_source", "")
    label_method = row.get("label_generation_method", "")
    if source_text_field in {"activityType", "assetId;siteId", "items[]"}:
        return "structural_field"
    if concept_id.startswith("CV-SAP"):
        return "sap_catalog"
    if concept_id.startswith("CV-EXT"):
        return "domain_vocabulary"
    if namespace == "fault_code" or evidence_source in {"code_context", "notes_context"}:
        return "domain_vocabulary"
    if "observed_structured_field" in label_method or "observed_internal_api_join" in label_method:
        return "structural_field"
    return "unknown"


def add_frame_row(
    rows: list[dict[str, object]],
    target: str,
    path_bucket: str,
    source_unit_key: str,
    text: str,
    stratum: str,
    anchor_source: str,
    source_artifact: str,
) -> None:
    clean = redact_pii(text)
    rows.append(
        {
            "target": target,
            "path_bucket": path_bucket,
            "sampling_unit_key": f"{target}|{path_bucket}|{source_unit_key}",
            "source_unit_key": source_unit_key,
            "text_pii_redacted": clean,
            "text_available": bool(clean),
            "stratum": stratum,
            "anchor_source": anchor_source,
            "source_artifact": source_artifact,
        }
    )


def build_sampling_frame() -> list[dict[str, object]]:
    service_text, reason_by_hash, reason_rows = load_service_order_texts()
    b2_text, b2_classifier_text = load_b2_text_maps()
    path_a_text, path_a_note_text = load_path_a_text()
    path_a_concern_text = load_path_a_concern_text()
    frame: list[dict[str, object]] = []

    b1_group: dict[tuple[str, str], dict[str, object]] = {}
    for row in read_csv(B1_TEXTUAL):
        if row.get("can_support_proxy_denominator") != "True":
            continue
        target = row["target"]
        phy = row["physical_record_id"]
        key = (target, phy)
        entry = b1_group.setdefault(
            key,
            {
                "fields": set(),
                "stratum": row.get("stratum", ""),
                "anchors": set(),
            },
        )
        entry["fields"].add(row.get("source_text_field", ""))
        entry["anchors"].add(anchor_source_for_row(row))
    for (target, phy), entry in b1_group.items():
        fields = sorted(entry["fields"])
        text_parts = [service_text.get(phy, {}).get(field, "") for field in fields]
        text = " | ".join(part for part in text_parts if part)
        anchors = sorted(entry["anchors"])
        add_frame_row(
            frame,
            target,
            "B1_RELATIONAL_TEXTUAL",
            phy,
            text,
            str(entry["stratum"]),
            "+".join(anchors) if anchors else "unknown",
            B1_TEXTUAL.name,
        )

    b25_group: dict[tuple[str, str], dict[str, object]] = {}
    for row in read_csv(B25_EVIDENCE):
        if row.get("target") == "Symptom":
            continue
        target = row["target"]
        refined = row["refined_event_key"]
        key = (target, refined)
        entry = b25_group.setdefault(
            key,
            {
                "stratum": row.get("stratum", ""),
                "anchors": set(),
            },
        )
        entry["anchors"].add(anchor_source_for_row(row))
    for (target, refined), entry in b25_group.items():
        anchors = sorted(entry["anchors"])
        add_frame_row(
            frame,
            target,
            "B2_WORKBOOK_SNAPSHOTS",
            refined,
            b2_text.get(refined, ""),
            str(entry["stratum"]),
            "+".join(anchors) if anchors else "unknown",
            B25_EVIDENCE.name,
        )

    path_a_group: dict[tuple[str, str], dict[str, object]] = {}
    for row in read_csv(PATH_A_EVIDENCE):
        target = row["target"]
        event = row["estimated_event_key"]
        key = (target, event)
        entry = path_a_group.setdefault(
            key,
            {
                "stratum": "event_structural",
                "anchors": set(),
                "note_keys": set(),
            },
        )
        entry["anchors"].add(anchor_source_for_row(row))
        source_key = row.get("source_row_key", "")
        if source_key.startswith("NOTE-LINE"):
            entry["note_keys"].add(source_key)
    for (target, event), entry in path_a_group.items():
        text = path_a_text.get((event, target), "")
        if not text:
            note_parts = [path_a_note_text.get(key, "") for key in sorted(entry["note_keys"])]
            text = " | ".join(part for part in note_parts if part)
        anchors = sorted(entry["anchors"])
        add_frame_row(
            frame,
            target,
            "PATH_A_PDF_EVENTS",
            event,
            text,
            str(entry["stratum"]),
            "+".join(anchors) if anchors else "unknown",
            PATH_A_EVIDENCE.name,
        )

    for row in read_csv(SYMPTOM_UNITS):
        path_bucket = row["path_bucket"]
        source_key = row["source_unit_key"]
        if path_bucket == "RELATIONAL_REASON":
            text = reason_by_hash.get(source_key, "")
        elif path_bucket == "B2_WORKBOOKS":
            text = b2_classifier_text.get(source_key, "")
        elif path_bucket in {"PATH_A_CONCERN_TABLE", "PATH_A_NOTES"}:
            text = path_a_concern_text.get(source_key, "") if path_bucket == "PATH_A_CONCERN_TABLE" else path_a_note_text.get(source_key, "")
        else:
            text = ""
        add_frame_row(
            frame,
            "Symptom",
            path_bucket,
            str(row["sampling_unit_key"]),
            text,
            "as_declared_by_source_path",
            "not_shown_to_annotator",
            SYMPTOM_UNITS.name,
        )

    return frame


def cap_and_select(candidates: list[dict[str, object]], n: int) -> list[dict[str, object]]:
    if n <= 0:
        return []
    cap = max(1, math.floor(n * MAX_SOURCE_UNIT_SHARE))
    selected: list[dict[str, object]] = []
    counts: Counter[str] = Counter()
    ordered = sorted(candidates, key=lambda row: deterministic_sort_key(row["target"], row["path_bucket"], row["sampling_unit_key"]))
    for row in ordered:
        source_key = str(row["source_unit_key"])
        if counts[source_key] >= cap:
            continue
        selected.append(row)
        counts[source_key] += 1
        if len(selected) >= n:
            break
    return selected


def allocate_target_sample(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    available = [row for row in rows if row["text_available"]]
    target_n = min(TARGET_SAMPLE_SIZE, len(available))
    if target_n == 0:
        return []
    by_path: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in available:
        by_path[str(row["path_bucket"])].append(row)

    selected: list[dict[str, object]] = []
    small_paths = {path for path, items in by_path.items() if len(items) <= 75}
    for path in sorted(small_paths):
        selected.extend(cap_and_select(by_path[path], min(len(by_path[path]), target_n - len(selected))))
    remaining_n = target_n - len(selected)
    if remaining_n > 0:
        remaining_paths = {path: items for path, items in by_path.items() if path not in small_paths}
        total_remaining = sum(len(items) for items in remaining_paths.values())
        allocations: dict[str, int] = {}
        if total_remaining:
            for path, items in remaining_paths.items():
                allocations[path] = min(len(items), max(1, round(remaining_n * len(items) / total_remaining)))
            while sum(allocations.values()) > remaining_n:
                path = max(allocations, key=lambda p: allocations[p])
                allocations[path] -= 1
            while sum(allocations.values()) < remaining_n:
                path = max(remaining_paths, key=lambda p: len(remaining_paths[p]) - allocations.get(p, 0))
                allocations[path] = allocations.get(path, 0) + 1
        for path, take in sorted(allocations.items()):
            selected.extend(cap_and_select(remaining_paths[path], take))
    return selected[:target_n]


def assign_annotators(selected: list[dict[str, object]]) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    by_target: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in selected:
        by_target[str(row["target"])].append(row)
    for target, rows in sorted(by_target.items()):
        ordered = sorted(rows, key=lambda row: deterministic_sort_key("assign", row["target"], row["sampling_unit_key"]))
        overlap_n = round(len(ordered) * OVERLAP_RATE)
        overlap = set(str(row["sampling_unit_key"]) for row in ordered[:overlap_n])
        rest = ordered[overlap_n:]
        for idx, row in enumerate(ordered):
            assigned = ANNOTATORS if str(row["sampling_unit_key"]) in overlap else [ANNOTATORS[idx % 2]]
            row = dict(row)
            row["overlap_group"] = "overlap" if len(assigned) == 2 else "single"
            row["assigned_annotators"] = ";".join(assigned)
            out.append(row)
    return out


def build_packages(assigned_rows: list[dict[str, object]]) -> tuple[list[dict[str, object]], list[dict[str, object]], dict[str, object]]:
    manifest_rows: list[dict[str, object]] = []
    package_rows: dict[str, list[dict[str, object]]] = {annotator: [] for annotator in ANNOTATORS}
    response_rows: dict[str, list[dict[str, object]]] = {annotator: [] for annotator in ANNOTATORS}
    for idx, row in enumerate(sorted(assigned_rows, key=lambda r: (str(r["target"]), str(r["sampling_unit_key"]))), start=1):
        annotation_id = f"G02-ANN-{idx:05d}"
        assigned = str(row["assigned_annotators"]).split(";")
        manifest_rows.append(
            {
                "annotation_id": annotation_id,
                "sampling_unit_key": row["sampling_unit_key"],
                "source_unit_key": row["source_unit_key"],
                "target": row["target"],
                "path_bucket": row["path_bucket"],
                "stratum": row["stratum"],
                "anchor_source": row["anchor_source"],
                "overlap_group": row["overlap_group"],
                "assigned_annotators": row["assigned_annotators"],
                "protocol_version": PROTOCOL_VERSION,
                "evaluation_independence": "independent_after_annotation",
                "label_generation_method": "blind_llm_annotation",
                "excluded_mechanisms": "rule_set_v1;semantic_prototype_matching_v1;paraphrase-multilingual-MiniLM-L12-v2",
                "text_in_versioned_artifact": False,
            }
        )
        for annotator in assigned:
            package_rows[annotator].append(
                {
                    "annotation_id": annotation_id,
                    "target": row["target"],
                    "text_pii_redacted": row["text_pii_redacted"],
                    "allowed_response": VOCAB[str(row["target"])],
                    "annotator_response": "",
                    "annotator_notes": "",
                }
            )
            response_rows[annotator].append(
                {
                    "annotation_id": annotation_id,
                    "annotator_id": annotator,
                    "annotator_response": "",
                    "annotator_notes": "",
                    "protocol_version": PROTOCOL_VERSION,
                }
            )
    summary = {
        "task": "G0.2_stratified_annotation_sample",
        "created_at_utc": utc_now(),
        "protocol_version": PROTOCOL_VERSION,
        "target_sample_size": TARGET_SAMPLE_SIZE,
        "overlap_rate": OVERLAP_RATE,
        "max_source_unit_share": MAX_SOURCE_UNIT_SHARE,
        "annotators": ANNOTATORS,
        "sampled_records": len(manifest_rows),
        "overlap_records": sum(1 for row in manifest_rows if row["overlap_group"] == "overlap"),
        "package_rows_by_annotator": {annotator: len(rows) for annotator, rows in package_rows.items()},
        "raw_operational_values_emitted_in_versioned_outputs": False,
        "visible_text_packages_versioned": False,
    }
    for annotator in ANNOTATORS:
        package_path = INTERNAL_OUT / f"g02_visible_package_{annotator}.csv"
        response_path = INTERNAL_OUT / f"g02_response_template_{annotator}.csv"
        by_target_dir = INTERNAL_OUT / "by_target"
        by_target_dir.mkdir(parents=True, exist_ok=True)
        annotator_package_rows = sorted(
            package_rows[annotator],
            key=lambda row: deterministic_sort_key("package-order", annotator, row["target"], row["annotation_id"]),
        )
        annotator_response_rows = sorted(
            response_rows[annotator],
            key=lambda row: deterministic_sort_key("response-order", annotator, row["annotation_id"]),
        )
        write_csv(
            package_path,
            annotator_package_rows,
            ["annotation_id", "target", "text_pii_redacted", "allowed_response", "annotator_response", "annotator_notes"],
            mode_600=True,
        )
        write_csv(
            response_path,
            annotator_response_rows,
            ["annotation_id", "annotator_id", "annotator_response", "annotator_notes", "protocol_version"],
            mode_600=True,
        )
        for target in sorted({str(row["target"]) for row in package_rows[annotator]}):
            target_slug = target.lower().replace(" ", "_").replace("/", "_")
            target_package = [
                row for row in annotator_package_rows if row["target"] == target
            ]
            target_responses = [
                row for row in annotator_response_rows if any(
                    pkg["annotation_id"] == row["annotation_id"] and pkg["target"] == target
                    for pkg in target_package
                )
            ]
            write_csv(
                by_target_dir / f"g02_visible_package_{annotator}_{target_slug}.csv",
                target_package,
                ["annotation_id", "target", "text_pii_redacted", "allowed_response", "annotator_response", "annotator_notes"],
                mode_600=True,
            )
            write_csv(
                by_target_dir / f"g02_response_template_{annotator}_{target_slug}.csv",
                target_responses,
                ["annotation_id", "annotator_id", "annotator_response", "annotator_notes", "protocol_version"],
                mode_600=True,
            )
    os.chmod(INTERNAL_OUT, 0o700)
    os.chmod(INTERNAL_OUT / "by_target", 0o700)
    return manifest_rows, response_rows[ANNOTATORS[0]] + response_rows[ANNOTATORS[1]], summary


def main() -> None:
    frame = build_sampling_frame()
    frame_rows = [
        {
            key: row.get(key, "")
            for key in [
                "target",
                "path_bucket",
                "sampling_unit_key",
                "source_unit_key",
                "text_available",
                "stratum",
                "anchor_source",
                "source_artifact",
            ]
        }
        for row in frame
    ]

    selected: list[dict[str, object]] = []
    for target in ["Symptom", "Activity", "Damage", "Cause", "Object Part"]:
        rows = [row for row in frame if row["target"] == target]
        selected.extend(allocate_target_sample(rows))
    assigned = assign_annotators(selected)
    manifest_rows, _response_rows, summary = build_packages(assigned)

    target_counts = Counter(row["target"] for row in manifest_rows)
    path_counts = Counter((row["target"], row["path_bucket"]) for row in manifest_rows)
    missing_text = Counter((row["target"], row["path_bucket"]) for row in frame if not row["text_available"])
    summary["sampled_by_target"] = dict(sorted(target_counts.items()))
    summary["sampled_by_target_path"] = {f"{target}|{path}": count for (target, path), count in sorted(path_counts.items())}
    summary["missing_text_units_by_target_path"] = {f"{target}|{path}": count for (target, path), count in sorted(missing_text.items())}
    blocker_rows = [
        {
            "target": target,
            "path_bucket": path,
            "missing_text_units": count,
            "protocol_impact": "excluded_from_visible_annotation_package_until_text_recovered",
            "note": "Sampling unit exists, but visible PII-redacted text could not be reconstructed from available closed-environment artifacts.",
        }
        for (target, path), count in sorted(missing_text.items())
        if count
    ]

    write_csv(
        G0_OUT / "g02_sampling_frame_availability_sanitized.csv",
        frame_rows,
        ["target", "path_bucket", "sampling_unit_key", "source_unit_key", "text_available", "stratum", "anchor_source", "source_artifact"],
    )
    write_csv(
        G0_OUT / "g02_annotation_sample_manifest_sanitized.csv",
        manifest_rows,
        [
            "annotation_id",
            "sampling_unit_key",
            "source_unit_key",
            "target",
            "path_bucket",
            "stratum",
            "anchor_source",
            "overlap_group",
            "assigned_annotators",
            "protocol_version",
            "evaluation_independence",
            "label_generation_method",
            "excluded_mechanisms",
            "text_in_versioned_artifact",
        ],
    )
    write_json(G0_OUT / "g02_sampling_summary_sanitized.json", summary)
    write_csv(
        G0_OUT / "g02_text_recovery_blockers_sanitized.csv",
        blocker_rows,
        ["target", "path_bucket", "missing_text_units", "protocol_impact", "note"],
    )
    memo = [
        "# G0.2 Stratified Annotation Sample",
        "",
        "## Purpose",
        "",
        "Build the blind annotation sample and closed-environment visible packages from admitted STINT 1 units.",
        "",
        "## Sampling Rules Applied",
        "",
        f"- Sample by `sampling_unit_key`.",
        f"- Cap per `source_unit_key`: `{MAX_SOURCE_UNIT_SHARE:.0%}` of each target sample.",
        "- Stratify by path, stratum, and anchor source where row-level metadata is available.",
        "- Use admitted units only; G1 candidate pools remain excluded.",
        f"- Two annotators with `{OVERLAP_RATE:.0%}` target-level overlap.",
        "",
        "## Outputs",
        "",
        "- Versioned sanitized manifest: `g02_annotation_sample_manifest_sanitized.csv`.",
        "- Versioned availability audit: `g02_sampling_frame_availability_sanitized.csv`.",
        "- Versioned text-recovery blockers: `g02_text_recovery_blockers_sanitized.csv`.",
        "- Closed visible packages: `g0_independent_evaluation/internal/g02_annotation_packages/` with permissions 600.",
        "",
        "## Text Recovery Limitation",
        "",
        "Rows without recoverable visible text are excluded from the visible annotation packages. This affects B2 workbook snapshot paths and must be resolved before those units can be annotated.",
        "",
        "No visible text is written to versioned outputs.",
    ]
    (G0_OUT / "g02_sampling_memo.md").write_text("\n".join(memo) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
