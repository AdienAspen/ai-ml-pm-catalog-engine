"""Prepare blind g01-v2 Activity and Damage annotation packages."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import random
import re
import sys
from collections import Counter
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "g2_baseline_models/scripts"))
sys.path.insert(0, str(ROOT / "g0_independent_evaluation/scripts"))

import g20c_neutral_ngram_extraction as corpus  # noqa: E402
from g02_build_stratified_annotation_packages import redact_pii  # noqa: E402
from g20c_lexical_safety import restricted_terms  # noqa: E402

PRIVATE = ROOT / "g2_baseline_models/internal/g20e_g20f_blind_catalogue_code_annotation"
PUBLIC = ROOT / "g2_baseline_models/outputs/g20ef_blind_catalogue_code_annotation"
PROTOCOL = PRIVATE / "protocol/g01-v2_protocol.md"
COVERAGE = ROOT / (
    "g2_baseline_models/outputs/g20_corpus_native_domain_vocab/"
    "g20c_step5_unit_coverage_sanitized.csv"
)
EVAL_KEYS = ROOT / (
    "artifacts/evaluation_sets/evaluation_set_v1/"
    "evaluation_set_v1_training_exclusion_keys.csv"
)
LEAK_MANIFEST = ROOT / (
    "g2_baseline_models/outputs/g20_target_leakage_quantification/"
    "g20b_masking_manifest_sanitized.csv"
)
CATALOGUE = corpus.PROJECT_ROOT / (
    "data/interim/extracted_source/package_001_37cac7fe/Data/References/"
    "Wind Catalog Group and Codes Final v4.xlsx"
)
SEED = "STINT2-G20EF-g01-v2-simple-random-20260926"
TARGETS = ("activity", "damage")
ANNOTATORS = ("annotator_01", "annotator_02")
SAMPLE_SIZE = 300
OVERLAP = 75


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def private_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    os.chmod(path, 0o700)


def write_private(path: Path, content: str) -> None:
    private_dir(path.parent)
    if path.exists():
        raise RuntimeError(f"Refusing to overwrite an existing annotation artefact: {path}")
    path.write_text(content, encoding="utf-8")
    os.chmod(path, 0o600)


def read_catalogue() -> dict[str, list[tuple[str, str, str]]]:
    book = load_workbook(CATALOGUE, read_only=True, data_only=True)
    associations = {
        (str(row[2]).strip(), str(row[3]).strip())
        for row in list(book["Catalog Profile and Code Groups"].values)[1:]
        if row[0] == "PMMUWW"
    }
    result = {}
    for target, typ, sheet in (
        ("activity", "A", "Catalog. A - Group and Code"),
        ("damage", "C", "Catalog. C - Group and Code"),
    ):
        allowed = {group for t, group in associations if t == typ}
        records = {
            (str(row[1]).strip(), str(row[2]).strip(), str(row[3]).strip())
            for row in list(book[sheet].values)[1:]
            if str(row[0]).strip() == typ and str(row[1]).strip() in allowed
        }
        result[target] = sorted(records)
    assert len(result["activity"]) == 5
    assert len(result["damage"]) == 94
    assert len({row[0] for row in result["damage"]}) == 9
    return result


def sanitize(text: str, patterns: list, restricted: tuple[str, ...]) -> str:
    masked, _, _ = corpus.apply_leakage_mask(text, patterns)
    value = redact_pii(masked)
    value = re.sub(
        r"\b(?:SITE|WTG|TURBINE|ASSET|EQUIPMENT|SERIAL)[-_\s]*\d+[A-Za-z0-9_-]*\b",
        "<ASSET_REF>",
        value,
        flags=re.I,
    )
    value = re.sub(
        r"\b(?:technician|employee|contact|performed by|created by|reported by)"
        r"\s*[:=-]?\s*[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2}",
        "<PERSON_REF>",
        value,
        flags=re.I,
    )
    for term in restricted:
        value = re.sub(
            re.escape(term),
            "<REDACTED_ENTITY>",
            value,
            flags=re.I,
        )
    for name in ("latigo", "pioneer", "takkion", "vestas"):
        value = re.sub(rf"\b{name}\b", "<REDACTED_ENTITY>", value, flags=re.I)
    if any(pattern.search(value) for pattern, _, _ in patterns):
        raise RuntimeError("Catalogue assignment survived G2.0b masking")
    if re.search(r"https?://|www\.|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", value, re.I):
        raise RuntimeError("Direct PII survived redaction")
    if any(term in value.casefold() for term in restricted):
        raise RuntimeError("Restricted operational term survived redaction")
    return value


def visible_text(unit: dict, patterns: list, restricted: tuple[str, ...]) -> str:
    parts = []
    for field, raw in unit["segments"]:
        if raw:
            parts.append(f"{field}: {sanitize(raw, patterns, restricted)}")
    return "\n".join(parts).strip()


def make_csv(rows: list[dict], fields: list[str]) -> str:
    import io

    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()


def make_packages() -> dict:
    protocol = PROTOCOL.read_text(encoding="utf-8")
    for required in ("A1", "A2", "A3", "D1", "D2", "D3", "D4",
                     "no_applicable_code", "ambiguous_multi_process",
                     "annotation_id,group,code"):
        if required not in protocol:
            raise RuntimeError(f"Protocol is incomplete: {required}")
    if "PENDING COMMITTEE CONTENT" in protocol:
        raise RuntimeError("The g01-v2 protocol is still a placeholder")

    catalogue = read_catalogue()
    coverage = pd.read_csv(COVERAGE)
    coverage = coverage[
        coverage.path_bucket.eq("B1_RELATIONAL") & coverage.target.eq("Activity")
    ].set_index("unit_key_hash")
    assert len(coverage) == 10749 and coverage.index.is_unique
    eval_keys = set(pd.read_csv(EVAL_KEYS).source_unit_key.astype(str))
    expected_masked = set(pd.read_csv(LEAK_MANIFEST).source_unit_key.astype(str))
    assert len(expected_masked) == 13
    units = corpus.load_b1_units()
    assert len(units) == 10749 and len({u["source_unit_key"] for u in units}) == 10749
    patterns = corpus.load_leakage_patterns()
    corpus.LEAKAGE_PATTERNS = patterns
    restricted = tuple(restricted_terms())

    frames = {target: [] for target in TARGETS}
    counts = {target: Counter() for target in TARGETS}
    observed_masked = set()
    for unit in units:
        key = unit["source_unit_key"]
        key_hash = corpus.prefixed_hash("UNIT", key, 12)
        record = coverage.loc[key_hash]
        assert key not in eval_keys or not bool(record.construction_eligible)
        if any(corpus.apply_leakage_mask(raw, patterns)[1] for _, raw in unit["segments"]):
            observed_masked.add(key)
        if not bool(record.construction_eligible):
            for target in TARGETS:
                counts[target]["frozen_construction_exclusion"] += 1
            continue
        text = visible_text(unit, patterns, restricted)
        if not text:
            for target in TARGETS:
                counts[target]["empty_text"] += 1
            continue
        for target in TARGETS:
            if target == "activity" and bool(record.reviewed_concept_exposure):
                counts[target]["g20c_reviewed_concept_exposure"] += 1
                continue
            frames[target].append((key, text))
    assert observed_masked == expected_masked

    PUBLIC.mkdir(parents=True, exist_ok=True)
    manifest = []
    summary = {
        "protocol_sha256": sha256(PROTOCOL.read_bytes()),
        "catalogue_sha256": sha256(CATALOGUE.read_bytes()),
        "seed": SEED,
        "sampling_design": "simple_random_with_declared_exclusions",
        "evaluation_independence": "independent",
        "label_generation_method": "blind_llm_annotation",
        "evaluation_role": "evaluation",
        "eligible_for_final_heldout": False,
        "heldout_reason": "source corpus participated in prior instrument construction; final eligibility not established",
        "targets": {},
    }
    for target in TARGETS:
        frame = sorted(frames[target], key=lambda row: row[0])
        if len(frame) < SAMPLE_SIZE:
            raise RuntimeError(f"Insufficient {target} eligible units: {len(frame)}")
        chosen = random.Random(f"{SEED}|{target}|units").sample(frame, SAMPLE_SIZE)
        ids = {
            key: f"G20EF-{target.upper()}-{idx:04d}"
            for idx, (key, _) in enumerate(chosen, start=1)
        }
        common = set(random.Random(f"{SEED}|{target}|overlap").sample(list(ids), OVERLAP))
        remainder = [key for key in ids if key not in common]
        random.Random(f"{SEED}|{target}|partition").shuffle(remainder)
        assignments = {
            ANNOTATORS[0]: common | set(remainder[:112]),
            ANNOTATORS[1]: common | set(remainder[112:]),
        }
        assert [len(assignments[a]) for a in ANNOTATORS] == [187, 188]
        assert len(assignments[ANNOTATORS[0]] & assignments[ANNOTATORS[1]]) == OVERLAP
        text_by_key = dict(chosen)
        for annotator in ANNOTATORS:
            keys = sorted(
                assignments[annotator],
                key=lambda key: sha256(f"{SEED}|{target}|{annotator}|{key}".encode()),
            )
            package = [{"annotation_id": ids[key], "text": text_by_key[key]} for key in keys]
            assert len(package) == len({row["annotation_id"] for row in package})
            package_text = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in package)
            reread = [json.loads(line) for line in package_text.splitlines()]
            assert reread == package and all(set(row) == {"annotation_id", "text"} for row in reread)
            stem = f"g20ef_{target}_g01-v2_{annotator}"
            package_path = PRIVATE / "packages" / target / annotator / f"{stem}.jsonl"
            write_private(package_path, package_text)
            response_fields = ["annotation_id", "response"] if target == "activity" else [
                "annotation_id", "group", "code"
            ]
            template = [{field: row["annotation_id"] if field == "annotation_id" else ""
                         for field in response_fields} for row in package]
            template_path = PRIVATE / "responses" / target / annotator / f"{stem}_response_template.csv"
            write_private(template_path, make_csv(template, response_fields))
            with template_path.open(newline="", encoding="utf-8") as handle:
                parsed = list(csv.DictReader(handle))
            assert len(parsed) == len(package)
            assert [row["annotation_id"] for row in parsed] == [row["annotation_id"] for row in package]
            allowed_path = PRIVATE / "packages" / target / annotator / f"{stem}_catalogue_codes.csv"
            write_private(
                allowed_path,
                make_csv(
                    [{"group": group, "code": code, "description": desc}
                     for group, code, desc in catalogue[target]],
                    ["group", "code", "description"],
                ),
            )
        for key, text in chosen:
            manifest.append({
                "annotation_id": ids[key],
                "target": target,
                "path": "B1_RELATIONAL",
                "source_unit_key": key,
                "text_sha256": sha256(text.encode("utf-8")),
                "overlap_record": key in common,
                "assigned_annotators": "|".join(a for a in ANNOTATORS if key in assignments[a]),
                "protocol_version": "g01-v2",
                "evaluation_independence": "independent",
                "label_generation_method": "blind_llm_annotation",
                "evaluation_role": "evaluation",
                "sampling_design": "simple_random",
                "eligible_for_final_heldout": False,
                "raw_text_emitted": False,
            })
        summary["targets"][target] = {
            "frame_units": len(frame),
            "exclusions": dict(counts[target]),
            "unique_sampled": SAMPLE_SIZE,
            "overlap": OVERLAP,
            "annotator_01_rows": 187,
            "annotator_02_rows": 188,
            "total_responses_expected": 375,
        }

    manifest_path = PUBLIC / "g20ef_sample_manifest_sanitized.csv"
    summary_path = PUBLIC / "g20ef_sampling_summary_sanitized.json"
    if manifest_path.exists() or summary_path.exists():
        raise RuntimeError("Refusing to overwrite existing sample registration")
    manifest_path.write_text(make_csv(manifest, list(manifest[0])), encoding="utf-8")
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with manifest_path.open(newline="", encoding="utf-8") as handle:
        reread_manifest = list(csv.DictReader(handle))
    assert len(reread_manifest) == 600
    assert all(row["raw_text_emitted"] == "False" for row in reread_manifest)
    return summary


if __name__ == "__main__":
    result = make_packages()
    print(json.dumps(result["targets"], indent=2, sort_keys=True))
