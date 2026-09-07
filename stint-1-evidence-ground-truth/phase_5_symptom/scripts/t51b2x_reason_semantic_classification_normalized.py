from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer


PROJECT_ROOT = Path("/home/adien-i7-remote/workspace/fsa_bridge_ml_feasibility")
OUTPUT_DIR = PROJECT_ROOT / "stint-1-evidence-ground-truth/phase_5_symptom/outputs/f51_symptom_thread_resolution"
INTERNAL_MANIFEST = PROJECT_ROOT / "reports/internal/f40b_contractor_path_001_relational_model/f40b_contractor_path_001_entity_manifest_internal.csv"
VALIDATION_FILES = [
    ("complete_reason_universe", PROJECT_ROOT / "reports/internal/f51b2_reason_blind_review_unbiased/f51b2_reason_blind_review_unbiased_visible_internal.csv", PROJECT_ROOT / "reports/internal/f51b2_reason_blind_review_unbiased/f51b2_reason_blind_review_unbiased_responses_only.csv"),
    ("residual_after_pattern_passes", PROJECT_ROOT / "reports/internal/f51b2_2f_residual_unique_and_oem_space/f51b2_2f_residual_unique_blind_review_visible_internal.csv", PROJECT_ROOT / "reports/internal/f51b2_2f_residual_unique_and_oem_space/f51b2_2f_residual_unique_blind_review_responses_only.csv"),
]

ENTITY = "api_service_v1_service-orders"
CONTRACTOR_PATH = "CONTRACTOR_PATH_001"
MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
LABEL_METHOD = "semantic_prototype_matching_v2_normalised_telegram_text"
ALLOWED_LABELS = {"observed_condition", "dispatch_motive", "ambiguous", "not_interpretable"}
CLASS_ORDER = ["observed_condition", "dispatch_motive", "ambiguous", "not_interpretable", "abstained"]
PROTOTYPES = {
    "observed_condition": [
        "high temperature alarm", "low fluid level", "low water level", "oil leak", "hydraulic oil leak",
        "sensor error", "low pressure", "high vibration", "damaged bearing", "alarm detected",
        "no communication", "converter cooling error", "generator lubrication error", "ambient high temperature",
    ],
    "dispatch_motive": [
        "component replacement", "filter replacement", "brush replacement", "scheduled inspection",
        "checklist", "audit", "upgrade", "troubleshooting", "health check", "testing",
        "planned maintenance", "routine service", "fill lubricators", "annual maintenance",
    ],
    "ambiguous": [
        "component name only", "component reference without failure", "equipment item only",
        "bearing", "converter", "filter", "hydraulic system",
    ],
    "not_interpretable": [
        "inventory adjustment", "hours allocation", "quotation", "log string",
        "administrative fragment", "unreadable code fragment",
    ],
}
RAW_PATTERNS = [
    re.compile(r"contractor_path_001", re.I), re.compile(r"site_path_001", re.I), re.compile(r"site_path_002", re.I),
    re.compile(r"site_path_003", re.I), re.compile(r"site_path_004", re.I), re.compile(r"client_entity", re.I),
    re.compile(r"oem_entity_001", re.I), re.compile(r"\bge\b", re.I),
    re.compile(r"/home/adien", re.I), re.compile(r"data/interim/extracted_source", re.I),
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


def normalise_telegram_text(text: str) -> str:
    value = str(text)
    value = re.sub(r"https?://\S+|www\.\S+", " ", value, flags=re.I)
    value = re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", " ", value)
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
    value = re.sub(r"\s+", " ", value).strip().lower()
    return value


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
    return Path(manifest.loc[manifest["entity_label"].eq(ENTITY), "json_path"].iloc[0])


def physical_record_id(record: Mapping[str, object], fallback_index: int) -> str:
    record_key = as_text(record.get("id")) or str(fallback_index)
    return prefixed_hash(f"{CONTRACTOR_PATH}|{ENTITY}|{record_key}", "PHY", 16)


def read_validation_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for subset_name, visible_path, response_path in VALIDATION_FILES:
        if not visible_path.exists() or not response_path.exists():
            continue
        visible = pd.read_csv(visible_path).fillna("")
        responses = pd.read_csv(response_path).fillna("")
        merged = visible.merge(
            responses[["reason_hash", "reviewer_response", "reviewer", "review_round"]],
            on="reason_hash",
            how="left",
            suffixes=("", "_response"),
        )
        for row in merged.to_dict("records"):
            label = as_text(row.get("reviewer_response_response") or row.get("reviewer_response"))
            text = as_text(row.get("reason_text_pii_redacted"))
            if label in ALLOWED_LABELS and text:
                rows.append(
                    {
                        "subset": subset_name,
                        "reason_hash": as_text(row.get("reason_hash")),
                        "text": text,
                        "normalised_text": normalise_telegram_text(text),
                        "label": label,
                        "reviewer": as_text(row.get("reviewer")),
                        "review_round": as_text(row.get("review_round")),
                    }
                )
    unique: dict[str, dict[str, str]] = {}
    for row in rows:
        unique.setdefault(row["reason_hash"], row)
    return list(unique.values())


def cosine_matrix(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return a @ b.T


def prototype_vectors(model: SentenceTransformer) -> tuple[list[str], list[str], np.ndarray]:
    labels, texts = [], []
    for label, phrases in PROTOTYPES.items():
        for phrase in phrases:
            labels.append(label)
            texts.append(normalise_telegram_text(phrase))
    embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return labels, texts, np.asarray(embeddings)


def best_matches(scores: np.ndarray, prototype_labels: list[str], prototype_texts: list[str]) -> list[dict[str, Any]]:
    best_idx = scores.argmax(axis=1)
    out = []
    for i, idx in enumerate(best_idx):
        sorted_scores = np.sort(scores[i])[::-1]
        out.append(
            {
                "best_label": prototype_labels[int(idx)],
                "best_score": float(scores[i, idx]),
                "anchor_hash": prefixed_hash(prototype_texts[int(idx)], "PROTO", 10),
                "margin": float(sorted_scores[0] - sorted_scores[1]) if len(sorted_scores) > 1 else np.nan,
            }
        )
    return out


def apply_threshold(matches: list[dict[str, Any]], threshold: float) -> list[str]:
    return [m["best_label"] if m["best_score"] >= threshold else "abstained" for m in matches]


def evaluate(labels: list[str], preds: list[str]) -> tuple[int, int, float, float, float]:
    covered = [i for i, pred in enumerate(preds) if pred != "abstained"]
    correct = sum(1 for i in covered if preds[i] == labels[i])
    precision = correct / len(covered) if covered else 0.0
    recall_proxy = correct / len(labels) if labels else 0.0
    coverage = len(covered) / len(labels) if labels else 0.0
    f1 = 2 * precision * recall_proxy / (precision + recall_proxy) if precision + recall_proxy else 0.0
    return len(covered), correct, precision, coverage, f1


def calibrate(labels: list[str], matches: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    curve = []
    for threshold in [round(x, 2) for x in np.arange(0.30, 0.82, 0.02)]:
        preds = apply_threshold(matches, threshold)
        covered, correct, precision, coverage, f1 = evaluate(labels, preds)
        curve.append(
            {
                "threshold": threshold,
                "covered_rows": covered,
                "correct_rows": correct,
                "precision_on_covered": round(precision, 4),
                "coverage": round(coverage, 4),
                "f1_proxy": round(f1, 4),
                "raw_operational_values_emitted": False,
            }
        )
    eligible = [row for row in curve if row["precision_on_covered"] >= 0.8 and row["covered_rows"] > 0]
    if eligible:
        best = max(eligible, key=lambda row: (row["f1_proxy"], row["coverage"], row["precision_on_covered"], -row["threshold"]))
    else:
        best = max(curve, key=lambda row: (row["precision_on_covered"], row["coverage"], -row["threshold"]))
    return best, curve


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
    validation_rows = read_validation_rows()
    if len(validation_rows) < 80:
        raise RuntimeError(f"Expected 80 validation labels, found {len(validation_rows)}")

    model = SentenceTransformer(MODEL_NAME)
    prototype_labels, prototype_texts, proto_emb = prototype_vectors(model)
    labels = [r["label"] for r in validation_rows]
    val_texts = [r["normalised_text"] for r in validation_rows]
    val_emb = np.asarray(model.encode(val_texts, normalize_embeddings=True, show_progress_bar=False))
    val_matches = best_matches(cosine_matrix(val_emb, proto_emb), prototype_labels, prototype_texts)
    selected_threshold, curve_rows = calibrate(labels, val_matches)
    threshold = float(selected_threshold["threshold"])
    val_preds = apply_threshold(val_matches, threshold)

    records = load_json_records(service_orders_path())
    reason_records = []
    for idx, record in enumerate(records):
        reason = as_text(record.get("reason"))
        if reason:
            reason_records.append(
                {
                    "physical_record_id": physical_record_id(record, idx),
                    "reason_hash": prefixed_hash(reason.lower(), "REASON", 12),
                    "normalised_text": normalise_telegram_text(reason),
                }
            )

    reason_emb = np.asarray(model.encode([r["normalised_text"] for r in reason_records], normalize_embeddings=True, show_progress_bar=False, batch_size=128))
    reason_matches = best_matches(cosine_matrix(reason_emb, proto_emb), prototype_labels, prototype_texts)
    reason_preds = apply_threshold(reason_matches, threshold)

    class_rows = []
    for row, match, pred in zip(reason_records, reason_matches, reason_preds, strict=True):
        class_rows.append(
            {
                "reason_hash": row["reason_hash"],
                "predicted_class": pred,
                "confidence": round(match["best_score"], 6),
                "anchor_prototype_hash": match["anchor_hash"],
                "abstained": pred == "abstained",
                "evidence_type": "expert_inference",
                "tier": "silver-medium",
                "status": "candidate_not_promoted",
                "label_generation_method": LABEL_METHOD,
                "embedding_model": MODEL_NAME,
                "evaluation_independence": "derived_from_rules",
                "raw_operational_values_emitted": False,
            }
        )

    dist = Counter(row["predicted_class"] for row in class_rows)
    distribution_rows = [
        {
            "predicted_class": klass,
            "row_count": dist.get(klass, 0),
            "pct_of_reason_non_empty": round(100 * dist.get(klass, 0) / len(class_rows), 2),
            "raw_operational_values_emitted": False,
        }
        for klass in CLASS_ORDER
    ]

    confusion_counter = Counter((row["label"], pred, row["subset"]) for row, pred in zip(validation_rows, val_preds, strict=True))
    confusion_rows = [
        {
            "actual_class": actual,
            "predicted_class": pred,
            "validation_subset": subset,
            "row_count": count,
            "raw_operational_values_emitted": False,
        }
        for (actual, pred, subset), count in sorted(confusion_counter.items())
    ]
    subset_rows = []
    for subset in sorted({r["subset"] for r in validation_rows}):
        idxs = [i for i, r in enumerate(validation_rows) if r["subset"] == subset]
        covered, correct, precision, coverage, f1 = evaluate([labels[i] for i in idxs], [val_preds[i] for i in idxs])
        subset_rows.append(
            {
                "validation_subset": subset,
                "validation_rows": len(idxs),
                "covered_rows": covered,
                "correct_rows": correct,
                "precision_on_covered": round(precision, 4),
                "coverage": round(coverage, 4),
                "f1_proxy": round(f1, 4),
                "raw_operational_values_emitted": False,
            }
        )

    summary = {
        "created_at_utc": utc_now(),
        "pass_id": "T5.1b2X-normalized",
        "status": "completed_no_target_promotion",
        "reason_non_empty_rows": len(class_rows),
        "validation_rows": len(validation_rows),
        "normalisation": "strip_numeric_codes_separators_placeholders_split_camel_case",
        "threshold_selection": "maximise_f1_proxy_among_thresholds_with_precision_at_least_0_8",
        "threshold": threshold,
        "covered_validation_rows": selected_threshold["covered_rows"],
        "correct_validation_rows": selected_threshold["correct_rows"],
        "precision_on_covered_validation_rows": selected_threshold["precision_on_covered"],
        "coverage_on_validation_rows": selected_threshold["coverage"],
        "f1_proxy": selected_threshold["f1_proxy"],
        "predicted_class_distribution": dict(dist),
        "observed_condition_candidate_rows": dist.get("observed_condition", 0),
        "label_generation_method": LABEL_METHOD,
        "embedding_model": MODEL_NAME,
        "evaluation_independence": "derived_from_rules",
        "control_of_circularity": "model_blind_review rows calibrate this rule; they are not independent held-out data for STINT_2 if the same mechanism is used",
        "raw_operational_values_emitted_to_versioned_artifacts": False,
    }

    classification_path = OUTPUT_DIR / "t51b2x_reason_semantic_classification_normalized.csv"
    distribution_path = OUTPUT_DIR / "t51b2x_class_distribution_normalized.csv"
    confusion_path = OUTPUT_DIR / "t51b2x_confusion_matrix_normalized_sanitized.csv"
    subset_path = OUTPUT_DIR / "t51b2x_validation_by_subset_normalized_sanitized.csv"
    curve_path = OUTPUT_DIR / "t51b2x_threshold_curve_normalized_sanitized.csv"
    summary_path = OUTPUT_DIR / "t51b2x_reason_semantic_classification_normalized_summary_sanitized.json"
    memo_path = OUTPUT_DIR / "t51b2x_reason_semantic_classification_normalized_memo.md"

    write_csv(
        classification_path,
        class_rows,
        [
            "reason_hash", "predicted_class", "confidence", "anchor_prototype_hash", "abstained",
            "evidence_type", "tier", "status", "label_generation_method", "embedding_model",
            "evaluation_independence", "raw_operational_values_emitted",
        ],
    )
    write_csv(distribution_path, distribution_rows, ["predicted_class", "row_count", "pct_of_reason_non_empty", "raw_operational_values_emitted"])
    write_csv(confusion_path, confusion_rows, ["actual_class", "predicted_class", "validation_subset", "row_count", "raw_operational_values_emitted"])
    write_csv(subset_path, subset_rows, ["validation_subset", "validation_rows", "covered_rows", "correct_rows", "precision_on_covered", "coverage", "f1_proxy", "raw_operational_values_emitted"])
    write_csv(curve_path, curve_rows, ["threshold", "covered_rows", "correct_rows", "precision_on_covered", "coverage", "f1_proxy", "raw_operational_values_emitted"])
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    memo_path.write_text(
        "# T5.1b2X - Normalized Reason Semantic Classification\n\n"
        "## Method\n\n"
        f"This rerun applies telegram-style text normalisation before embedding with `{MODEL_NAME}`. "
        "It strips leading numeric codes and placeholders, expands separators, and splits CamelCase before prototype matching.\n\n"
        "## Calibration\n\n"
        f"- Validation rows: `{len(validation_rows)}`.\n"
        f"- Threshold: `{threshold}`.\n"
        f"- Covered validation rows: `{selected_threshold['covered_rows']}`.\n"
        f"- Correct covered validation rows: `{selected_threshold['correct_rows']}`.\n"
        f"- Precision on covered rows: `{selected_threshold['precision_on_covered']}`.\n"
        f"- Coverage on validation rows: `{selected_threshold['coverage']}`.\n"
        f"- Proxy F1: `{selected_threshold['f1_proxy']}`.\n\n"
        "## Guardrail\n\n"
        "This pass remains `expert_inference`, `silver-medium`, and `derived_from_rules`. It emits Symptom candidates for downstream assessment only; nothing is promoted to a denominator here.\n",
        encoding="utf-8",
    )
    assert_sanitized([classification_path, distribution_path, confusion_path, subset_path, curve_path, summary_path, memo_path])
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
