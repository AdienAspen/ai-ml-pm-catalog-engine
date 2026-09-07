from __future__ import annotations

import csv
import importlib.util
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from openpyxl import load_workbook
from sentence_transformers import SentenceTransformer


PROJECT_ROOT = Path("/home/adien-i7-remote/workspace/fsa_bridge_ml_feasibility")
STINT_ROOT = PROJECT_ROOT / "stint-1-evidence-ground-truth"
OUTPUT_DIR = STINT_ROOT / "phase_5_symptom/outputs/f51_symptom_thread_resolution"
PATH_A_NOTES_INTERNAL = PROJECT_ROOT / "reports/internal/path_a_repair/f353_notes_semantics_internal.csv"
PATH_A_NOTES_SANITIZED = STINT_ROOT / "phase_3_path_a_faultcodes/outputs/f353_notes_semantics_sanitized.csv"
PATH_A_CONCERN = PROJECT_ROOT / "reports/internal/pdf_assets_of_concern_rows.csv"
B21_SCRIPT = STINT_ROOT / "phase_4_path_b_xlsx/scripts/b21_snapshot_characterization.py"
CLASSIFIER_SCRIPT = STINT_ROOT / "phase_5_symptom/scripts/t51b2x_reason_semantic_classification_normalized.py"
PATTERN_VERDICT = OUTPUT_DIR / "t51b24_other_path_oem_pattern_verdict_sanitized.csv"

THRESHOLD = 0.50

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


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def clean_text(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value).strip())


def iter_path_a_notes() -> list[dict[str, str]]:
    internal = pd.read_csv(PATH_A_NOTES_INTERNAL, dtype=str).fillna("")
    sanitized = pd.read_csv(PATH_A_NOTES_SANITIZED, dtype=str).fillna("")
    signal_keys = set(sanitized.loc[sanitized["has_semantic_signal"].str.lower().eq("true"), "note_line_key"])
    rows = []
    for row in internal.to_dict("records"):
        key = clean_text(row.get("note_line_key"))
        text = clean_text(row.get("note_line_text"))
        if key not in signal_keys or not text:
            continue
        rows.append(
            {
                "path_bucket": "PATH_A_NOTES",
                "source_text_field": "pdf_notes_region.note_line_text",
                "record_hash": key,
                "text": text,
            }
        )
    return rows


def iter_path_a_concern() -> list[dict[str, str]]:
    df = pd.read_csv(PATH_A_CONCERN, dtype=str).fillna("")
    rows = []
    for idx, row in enumerate(df.to_dict("records")):
        text = clean_text(row.get("event"))
        if not text:
            continue
        rows.append(
            {
                "path_bucket": "PATH_A_CONCERN_TABLE",
                "source_text_field": "pdf_assets_of_concern.event",
                "record_hash": f"AOC-{row.get('file_hash','')}-{idx}",
                "text": text,
            }
        )
    return rows


def iter_b2_workbook_text() -> list[dict[str, str]]:
    b21 = load_module(B21_SCRIPT, "b21_snapshot_characterization")
    files: list[Path] = []
    for root in b21.SOURCE_GLOBS:
        files.extend(sorted(root.rglob("*.xls*")))
    rows_out: list[dict[str, str]] = []
    for path in sorted(files):
        family, _doc_type = b21.family_for_path(path)
        file_key = b21.short_hash(str(path.relative_to(PROJECT_ROOT)), "B2FILE")
        try:
            wb = load_workbook(path, read_only=True, data_only=True)
        except Exception:
            continue
        for sheet_index, ws in enumerate(wb.worksheets, start=1):
            sample_rows = []
            for row in ws.iter_rows(min_row=1, max_row=min(ws.max_row or 1, 30), max_col=min(ws.max_column or 1, 30), values_only=True):
                sample_rows.append([b21.clean_text(v) for v in row])
            header_row, headers = b21.likely_header_row(sample_rows)
            if not header_row or not headers:
                continue
            categories = [b21.categorize_header(h) for h in headers]
            text_positions = [i + 1 for i, c in enumerate(categories) if c in {"notes_text", "work_text", "issue_text"}]
            if not text_positions:
                continue
            max_col = max(len(headers), max(text_positions))
            for row_number, row in enumerate(ws.iter_rows(min_row=header_row + 1, max_col=max_col, values_only=True), start=header_row + 1):
                row_values = [b21.clean_text(v) for v in row]
                for pos in text_positions:
                    text = row_values[pos - 1] if pos - 1 < len(row_values) else ""
                    if len(text) < 8:
                        continue
                    rows_out.append(
                        {
                            "path_bucket": "B2_WORKBOOKS",
                            "source_text_field": f"xlsx_snapshot.{categories[pos - 1]}",
                            "record_hash": b21.short_hash(f"{file_key}|{sheet_index}|{row_number}|{pos}", "B2TXT"),
                            "text": text,
                            "family": family,
                        }
                    )
        wb.close()
    return rows_out


def pct(count: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round(100 * count / denominator, 2)


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
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    classifier = load_module(CLASSIFIER_SCRIPT, "t51b2x_reason_semantic_classification_normalized")
    text_rows = iter_path_a_notes() + iter_path_a_concern() + iter_b2_workbook_text()
    model = SentenceTransformer(classifier.MODEL_NAME)
    prototype_labels, prototype_texts, proto_emb = classifier.prototype_vectors(model)
    normalised_texts = [classifier.normalise_telegram_text(row["text"]) for row in text_rows]
    embeddings = np.asarray(model.encode(normalised_texts, normalize_embeddings=True, show_progress_bar=False, batch_size=128))
    matches = classifier.best_matches(classifier.cosine_matrix(embeddings, proto_emb), prototype_labels, prototype_texts)
    predictions = classifier.apply_threshold(matches, THRESHOLD)

    class_rows = []
    for row, match, prediction in zip(text_rows, matches, predictions, strict=True):
        class_rows.append(
            {
                "path_bucket": row["path_bucket"],
                "source_text_field": row["source_text_field"],
                "record_hash": row["record_hash"],
                "predicted_class": prediction,
                "confidence": round(float(match["best_score"]), 6),
                "anchor_prototype_hash": match["anchor_hash"],
                "abstained": prediction == "abstained",
                "evidence_type": "expert_inference",
                "tier": "silver-medium",
                "status": "candidate_not_promoted",
                "label_generation_method": "semantic_prototype_matching_v1_normalized_fixed_threshold_0_50",
                "embedding_model": classifier.MODEL_NAME,
                "evaluation_independence": "derived_from_rules",
                "raw_operational_values_emitted": False,
            }
        )

    distribution_rows = []
    for path_bucket in ["PATH_A_NOTES", "PATH_A_CONCERN_TABLE", "B2_WORKBOOKS"]:
        scoped = [row for row in class_rows if row["path_bucket"] == path_bucket]
        counts = Counter(row["predicted_class"] for row in scoped)
        for klass in ["observed_condition", "dispatch_motive", "ambiguous", "not_interpretable", "abstained"]:
            distribution_rows.append(
                {
                    "path_bucket": path_bucket,
                    "predicted_class": klass,
                    "row_count": counts.get(klass, 0),
                    "pct_of_path_rows": pct(counts.get(klass, 0), len(scoped)),
                    "raw_operational_values_emitted": False,
                }
            )

    pattern_df = pd.read_csv(PATTERN_VERDICT, dtype=str).fillna("") if PATTERN_VERDICT.exists() else pd.DataFrame()
    contrast_rows = []
    for path_bucket in ["PATH_A_NOTES", "PATH_A_CONCERN_TABLE", "B2_WORKBOOKS"]:
        scoped = [row for row in class_rows if row["path_bucket"] == path_bucket]
        counts = Counter(row["predicted_class"] for row in scoped)
        oem_rows = 0
        oem_pct = 0.0
        if not pattern_df.empty:
            match = pattern_df[pattern_df["path_bucket"].eq(path_bucket)]
            if not match.empty:
                oem_rows = int(float(match.iloc[0]["rows_with_oem_pattern"]))
                oem_pct = float(match.iloc[0]["pct_rows_with_oem_pattern"])
        observed = counts.get("observed_condition", 0)
        contrast_rows.append(
            {
                "path_bucket": path_bucket,
                "text_rows_evaluated": len(scoped),
                "oem_pattern_rows": oem_rows,
                "oem_pattern_pct": oem_pct,
                "semantic_observed_condition_rows": observed,
                "semantic_observed_condition_pct": pct(observed, len(scoped)),
                "semantic_non_abstained_rows": len(scoped) - counts.get("abstained", 0),
                "semantic_coverage_pct": pct(len(scoped) - counts.get("abstained", 0), len(scoped)),
                "verdict": (
                    "signal_present_beyond_oem_pattern"
                    if observed > max(oem_rows, 0)
                    else ("signal_marginal_or_oem_bound" if observed else "no_semantic_signal_observed")
                ),
                "raw_operational_values_emitted": False,
            }
        )

    summary = {
        "created_at_utc": utc_now(),
        "pass_id": "T5.1b2.4b",
        "task_type": "semantic_classification_other_paths_fixed_threshold",
        "threshold": THRESHOLD,
        "threshold_source": "T5.1b2X-normalized reason calibration; not recalibrated here",
        "path_summary": {
            row["path_bucket"]: {
                "text_rows_evaluated": row["text_rows_evaluated"],
                "oem_pattern_rows": row["oem_pattern_rows"],
                "semantic_observed_condition_rows": row["semantic_observed_condition_rows"],
                "semantic_coverage_pct": row["semantic_coverage_pct"],
                "verdict": row["verdict"],
            }
            for row in contrast_rows
        },
        "classification_action": "semantic_crosscheck_only_no_denominator_promotion",
        "raw_operational_values_emitted_to_versioned_artifacts": False,
    }

    class_path = OUTPUT_DIR / "t51b24b_semantic_other_paths.csv"
    dist_path = OUTPUT_DIR / "t51b24b_semantic_other_paths_distribution_sanitized.csv"
    contrast_path = OUTPUT_DIR / "t51b24b_oem_vs_semantic_contrast_sanitized.csv"
    summary_path = OUTPUT_DIR / "t51b24b_semantic_other_paths_summary_sanitized.json"
    memo_path = OUTPUT_DIR / "t51b24b_memo.md"

    write_csv(
        class_path,
        class_rows,
        [
            "path_bucket",
            "source_text_field",
            "record_hash",
            "predicted_class",
            "confidence",
            "anchor_prototype_hash",
            "abstained",
            "evidence_type",
            "tier",
            "status",
            "label_generation_method",
            "embedding_model",
            "evaluation_independence",
            "raw_operational_values_emitted",
        ],
    )
    write_csv(dist_path, distribution_rows, ["path_bucket", "predicted_class", "row_count", "pct_of_path_rows", "raw_operational_values_emitted"])
    write_csv(
        contrast_path,
        contrast_rows,
        [
            "path_bucket",
            "text_rows_evaluated",
            "oem_pattern_rows",
            "oem_pattern_pct",
            "semantic_observed_condition_rows",
            "semantic_observed_condition_pct",
            "semantic_non_abstained_rows",
            "semantic_coverage_pct",
            "verdict",
            "raw_operational_values_emitted",
        ],
    )
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    memo_lines = [
        "# T5.1b2.4b - Semantic Classification In Path A and B2",
        "",
        "## Purpose",
        "",
        "Apply the normalized semantic classifier from `T5.1b2X-normalized` to Path A and B2 text sources using the fixed threshold `0.50`. The threshold is not recalibrated on these sources.",
        "",
        "## OEM Pattern vs Semantic Classifier",
        "",
        "| Source | Rows | OEM pattern rows | Semantic observed_condition | Semantic coverage | Verdict |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in contrast_rows:
        memo_lines.append(
            f"| `{row['path_bucket']}` | {row['text_rows_evaluated']} | {row['oem_pattern_rows']} ({row['oem_pattern_pct']}%) | {row['semantic_observed_condition_rows']} ({row['semantic_observed_condition_pct']}%) | {row['semantic_coverage_pct']}% | `{row['verdict']}` |"
        )
    memo_lines.extend(
        [
            "",
            "## Guardrail",
            "",
            "This pass is a semantic cross-check only. It does not map to SAP, does not promote Symptom evidence to a denominator, and keeps `evaluation_independence = derived_from_rules`.",
        ]
    )
    memo_path.write_text("\n".join(memo_lines) + "\n", encoding="utf-8")

    assert_sanitized([class_path, dist_path, contrast_path, summary_path, memo_path])
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
