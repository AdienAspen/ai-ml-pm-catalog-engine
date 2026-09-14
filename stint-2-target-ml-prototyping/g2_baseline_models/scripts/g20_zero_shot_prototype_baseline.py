from __future__ import annotations

import csv
import argparse
import hashlib
import importlib.util
import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer


PROJECT_ROOT = Path("/home/adien-i7-remote/workspace/fsa_bridge_ml_feasibility")
STINT2_ROOT = PROJECT_ROOT / "stint-2-target-ml-prototyping"
OUT = STINT2_ROOT / "g2_baseline_models" / "outputs" / "g20_zero_shot_prototype_baseline"
SCRIPTS_OUT = STINT2_ROOT / "g2_baseline_models" / "scripts"

SERVICE_ORDERS_JSON = PROJECT_ROOT / "data/interim/extracted_source/package_001_37cac7fe/Data/Vestas/api_service_v1_service-orders.json"
EVAL1 = STINT2_ROOT / "artifacts/evaluation_sets/evaluation_set_v1/evaluation_set_v1_annotator_01.csv"
EVAL2 = STINT2_ROOT / "artifacts/evaluation_sets/evaluation_set_v1/evaluation_set_v1_annotator_02.csv"
G11E_SAMPLE_B = STINT2_ROOT / "g1_actionable_zeros/g11_object_part_crosswalk/internal/g11e_group_b_blind_order_sample_internal.csv"

STINT1 = PROJECT_ROOT / "stint-1-evidence-ground-truth"
PATH_A_EVENTS = STINT1 / "phase_3_path_a_faultcodes/outputs/f354_estimated_events_sanitized.csv"
PATH_A_ASSIGNMENTS = STINT1 / "phase_3_path_a_faultcodes/outputs/f354_snapshot_row_assignments_sanitized.csv"
PATH_A_PDF_ROWS = PROJECT_ROOT / "reports/internal/pdf_assets_of_concern_rows.csv"
PATH_A_NOTES = PROJECT_ROOT / "reports/internal/path_a_repair/f353_notes_semantics_internal.csv"
B25_SCRIPT = STINT1 / "phase_4_path_b_xlsx/scripts/b25_grouping_refinement.py"
B2_SOURCE_ROOTS = [
    PROJECT_ROOT / "data/interim/extracted_source/package_001_37cac7fe/Data/Latigo Wind GE EOD",
    PROJECT_ROOT / "data/interim/extracted_source/package_001_37cac7fe/Data/Pioneer GE Info/Pioneer GE Info",
    PROJECT_ROOT / "data/interim/extracted_source/package_003_19512420/GE Prevailing",
]

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
LABEL_METHOD = "zero_shot_prototype_matching_v1"


PROTOTYPES = {
    "Activity": {
        "replacement": ["replaced component", "new part fitted"],
        "repair": ["repaired", "fixed", "restored"],
        "inspection": ["inspected", "checked", "visual check", "borescope"],
        "lubrication": ["greased", "lubricated", "refilled lubricant"],
        "adjustment": ["adjusted", "calibrated", "reset setting"],
        "cleaning": ["cleaned", "washed", "debris removed"],
        "troubleshooting": ["troubleshoot", "fault finding", "diagnosed"],
        "installation": ["installed", "mounted", "commissioned"],
    },
    "Cause": {
        "high_wind": ["high wind", "storm", "gust"],
        "grid_failure": ["grid outage", "grid failure", "power loss"],
        "lightning": ["lightning strike"],
        "icing": ["ice build up", "icing"],
        "control_malfunction": ["control system malfunction", "software error"],
        "component_wear": ["worn", "wear", "fatigue", "degradation"],
        "loosening": ["loose connection", "bolts loosened"],
        "external_damage": ["external impact", "foreign object"],
        "unknown_cause": ["cause not determined"],
    },
    "Damage": {
        "spalling": ["spalling", "flaking", "surface break up"],
        "cracking": ["crack", "fracture", "fissure"],
        "wear": ["worn", "abrasion", "erosion"],
        "corrosion": ["corroded", "rust", "oxidation"],
        "leaking": ["leaking", "leak from seal", "fluid escaping"],
        "pitting": ["pitting", "micropitting", "macropitting"],
        "deformation": ["bent", "deformed", "plastic deformation"],
        "contamination": ["contaminated", "debris ingress", "dirty oil"],
        "overheating_damage": ["burnt", "scorched", "thermal damage"],
        "breakage": ["broken", "snapped", "sheared"],
    },
    "Object Part": {
        "bearing": ["main bearing", "gearbox bearing", "generator bearing"],
        "seal": ["seal", "o ring", "gasket"],
        "filter": ["filter", "air filter", "oil filter"],
        "valve": ["valve", "pilot valve", "solenoid valve"],
        "sensor": ["sensor", "encoder", "thermocouple", "PT100"],
        "gear": ["gear", "gearbox", "yaw ring", "torque arm bushing"],
        "blade": ["blade", "pitch", "trailing edge"],
        "motor_pump": ["motor", "pump", "fan"],
        "electrical": ["cabinet", "breaker", "contactor", "converter stack"],
        "battery_ups": ["battery", "UPS", "charger"],
        "brake": ["brake", "brake disc", "brake pad"],
        "hatch_cover": ["hatch", "cover", "deck hatch", "bottom cover"],
        "accumulator": ["accumulator", "manifold", "hydraulic accumulator"],
    },
}

PROTOTYPE_META = {
    "Activity": ("zeus_maintenance_measure", "transcribed_from_source", "", "source_transcribed_zero_shot_prototype_baseline"),
    "Cause": ("wmep_causes", "transcribed_from_source", "", "source_transcribed_zero_shot_prototype_baseline"),
    "Damage": ("nrel_grd", "transcribed_from_source", "", "source_transcribed_zero_shot_prototype_baseline"),
    "Object Part": ("g11e_blind_sample", "derived_from_blind_sample", "g11e_group_b_blind_order_sample_internal", "corpus_informed_prototype_baseline"),
}

TARGETS = ["Activity", "Cause", "Damage", "Object Part"]
PATHS = ["B1_RELATIONAL", "PATH_A", "B2_WORKBOOKS"]

CURVE_COLUMNS = [
    "target", "path_bucket", "calibration_subset", "threshold",
    "evaluation_rows", "covered_rows", "correct_rows",
    "precision_on_covered", "coverage_pct",
    "raw_operational_values_emitted",
]

EVAL_PATH_BUCKET = {
    "B1_RELATIONAL_TEXTUAL": "B1_RELATIONAL",
    "RELATIONAL_REASON": "B1_RELATIONAL",
    "PATH_A_PDF_EVENTS": "PATH_A",
    "PATH_A_CONCERN_TABLE": "PATH_A",
    "PATH_A_NOTES": "PATH_A",
    "B2_WORKBOOK_SNAPSHOTS": "B2_WORKBOOKS",
    "B2_WORKBOOKS": "B2_WORKBOOKS",
}

CATALOGUE_BASELINES = {
    ("Activity", "B1_RELATIONAL"): (1215, 52.7, "sap_catalog catalogue-anchor baseline from G1.2c"),
    ("Cause", "B1_RELATIONAL"): (1203, None, "sap_catalog catalogue-anchor baseline from G1.2c"),
    ("Damage", "B1_RELATIONAL"): (1263, None, "815 sap_catalog + 312 domain + 136 both from G1.2c"),
    ("Object Part", "B1_RELATIONAL"): (3737, 19.748461, "high-band Object Part anchors from G1.1d; top concept 738/3737"),
}

RAW_PATTERNS = [
    re.compile(r"contractor_path_001", re.I),
    re.compile(r"site_path_00[1-9]", re.I),
    re.compile(r"oem_entity_001", re.I),
    re.compile(r"data/interim/extracted_source", re.I),
    re.compile(r"/home/adien", re.I),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_hash(value: object, length: int = 16) -> str:
    raw = "" if value is None or pd.isna(value) else str(value)
    return hashlib.sha256(raw.encode("utf-8", errors="ignore")).hexdigest()[:length]


def prefixed_hash(prefix: str, value: object, length: int = 16) -> str:
    return f"{prefix}-{stable_hash(value, length)}"


def as_text(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def normalise_text(text: object) -> str:
    value = as_text(text)
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


def load_json(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise RuntimeError(f"Expected list payload: {path}")
    return [row for row in payload if isinstance(row, dict)]


def physical_record_id(order_id: object) -> str:
    return prefixed_hash("PHY", f"CONTRACTOR_PATH_001|api_service_v1_service-orders|{as_text(order_id)}", 16)


def load_b1_units() -> pd.DataFrame:
    rows = []
    for record in load_json(SERVICE_ORDERS_JSON):
        order_id = as_text(record.get("id"))
        chunks = [
            as_text(record.get("reason")),
            as_text(record.get("description")),
            as_text(record.get("descriptionExtended")),
            as_text(record.get("workPerformed")),
            as_text(record.get("activityType")),
        ]
        text = " ".join(chunk for chunk in chunks if chunk)
        rows.append(
            {
                "unit_key": physical_record_id(order_id),
                "path_bucket": "B1_RELATIONAL",
                "source_unit_key": physical_record_id(order_id),
                "text": text,
                "text_hash": prefixed_hash("TEXT", text, 16),
            }
        )
    return pd.DataFrame(rows)


def load_b25_module():
    spec = importlib.util.spec_from_file_location("b25", B25_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load B25 module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_b2_units() -> pd.DataFrame:
    b25 = load_b25_module()
    files = []
    for root in B2_SOURCE_ROOTS:
        if not root.exists():
            raise RuntimeError(f"B2 source root does not exist: {root}")
        files.extend(sorted(root.rglob("*.xls*")))
    if not files:
        raise RuntimeError("No B2 workbook files found")
    group_rows = []
    for path in files:
        group_rows.extend(b25.iter_groupable_text_rows(path))
    groups: dict[str, list[str]] = defaultdict(list)
    for row in group_rows:
        groups[str(row["refined_event_key"])].append(str(row["normalized_text"]))
    rows = []
    for key, texts in groups.items():
        text = " ".join(texts)
        rows.append(
            {
                "unit_key": key,
                "path_bucket": "B2_WORKBOOKS",
                "source_unit_key": key,
                "text": text,
                "text_hash": prefixed_hash("TEXT", text, 16),
            }
        )
    return pd.DataFrame(rows)


def load_path_a_units() -> pd.DataFrame:
    events = pd.read_csv(PATH_A_EVENTS)
    assignments = pd.read_csv(PATH_A_ASSIGNMENTS)
    pdf = pd.read_csv(PATH_A_PDF_ROWS).fillna("")
    pdf["fault_code_norm"] = pdf["fault_code"].map(as_text)
    pdf["row_key"] = pdf.apply(
        lambda row: "PATHA-SRCROW-"
        + stable_hash(
            "|".join(
                [
                    str(row.get("path_hash", "")),
                    str(row.get("file_hash", "")),
                    prefixed_hash("ASSET", as_text(row.get("asset")), 10),
                    prefixed_hash("CODE", as_text(row.get("fault_code_norm")), 10),
                    str(row.get("duration", "")),
                    str(row.get("event", "")),
                ]
            ),
            12,
        ),
        axis=1,
    )
    event_rows = assignments[["estimated_event_key", "row_key"]].merge(pdf, on="row_key", how="left")
    text_by_event: dict[str, list[str]] = defaultdict(list)
    for row in event_rows.itertuples(index=False):
        text_by_event[str(row.estimated_event_key)].append(
            " ".join([as_text(getattr(row, "event", "")), as_text(getattr(row, "fault_code", "")), as_text(getattr(row, "state", ""))])
        )
    notes = pd.read_csv(PATH_A_NOTES).fillna("")
    if {"file_hash", "note_line_text"}.issubset(notes.columns) and "file_hash" in event_rows.columns:
        event_files = event_rows[["estimated_event_key", "file_hash"]].drop_duplicates()
        note_join = notes.merge(event_files, on="file_hash", how="inner")
        for row in note_join.itertuples(index=False):
            text_by_event[str(row.estimated_event_key)].append(as_text(row.note_line_text))
    rows = []
    for key in events["estimated_event_key"].astype(str):
        text = " ".join(text_by_event.get(key, []))
        rows.append(
            {
                "unit_key": key,
                "path_bucket": "PATH_A",
                "source_unit_key": key,
                "text": text,
                "text_hash": prefixed_hash("TEXT", text, 16),
            }
        )
    return pd.DataFrame(rows)


def prototype_registry() -> pd.DataFrame:
    rows = []
    for target, classes in PROTOTYPES.items():
        source, method, exclusion, baseline_type = PROTOTYPE_META[target]
        for class_name, phrases in classes.items():
            for idx, phrase in enumerate(phrases, start=1):
                rows.append(
                    {
                        "prototype_id": prefixed_hash("PROTO", f"{target}|{class_name}|{phrase}", 12),
                        "target": target,
                        "class_name": class_name,
                        "prototype_text_hash": prefixed_hash("PTEXT", phrase, 12),
                        "prototype_source": source,
                        "construction_method": method,
                        "evaluation_exclusion": exclusion,
                        "prototype_baseline_type": baseline_type,
                        "anchor_source": "prototype_domain_vocabulary",
                        "label_generation_method": LABEL_METHOD,
                        "raw_operational_values_emitted": False,
                    }
                )
    return pd.DataFrame(rows)


def prototype_texts_for_model() -> list[dict[str, str]]:
    rows = []
    for target, classes in PROTOTYPES.items():
        for class_name, phrases in classes.items():
            for phrase in phrases:
                rows.append(
                    {
                        "target": target,
                        "class_name": class_name,
                        "prototype_id": prefixed_hash("PROTO", f"{target}|{class_name}|{phrase}", 12),
                        "text": normalise_text(phrase),
                    }
                )
    return rows


def eval_positive(target: str, response: str) -> bool | None:
    response = as_text(response)
    if target == "Cause":
        if response == "cause_present":
            return True
        if response in {"no_cause_stated", "not_interpretable"}:
            return False
    if target == "Object Part":
        if response == "component_identified":
            return True
        if response in {"no_component", "system_only", "not_interpretable"}:
            return False
    if target == "Symptom":
        if response == "observed_condition":
            return True
        if response in {"dispatch_motive", "ambiguous", "not_interpretable"}:
            return False
    return None


def load_evaluation() -> pd.DataFrame:
    frames = []
    for path in [EVAL1, EVAL2]:
        df = pd.read_csv(path)
        frames.append(df)
    eval_df = pd.concat(frames, ignore_index=True)
    eval_df = eval_df[eval_df["target"].isin(["Cause", "Object Part"])].copy()
    eval_df["path_bucket"] = eval_df["path"].map(EVAL_PATH_BUCKET).fillna("UNMAPPED")
    eval_df["is_positive"] = eval_df.apply(lambda row: eval_positive(row["target"], row["response"]), axis=1)
    eval_df = eval_df[eval_df["is_positive"].notna()].copy()
    eval_df["eval_row_key"] = eval_df.apply(
        lambda row: prefixed_hash("EVAL", f"{row.annotator_id}|{row.sampling_unit_key}|{row.response}", 16),
        axis=1,
    )
    if G11E_SAMPLE_B.exists():
        sample_b = pd.read_csv(G11E_SAMPLE_B)
        excluded = set(sample_b["order_id_hash"].dropna().astype(str))
    else:
        excluded = set()
    eval_df["excluded_by_prototype_governance"] = eval_df.apply(
        lambda row: row["target"] == "Object Part" and row["source_unit_key"] in excluded,
        axis=1,
    )
    eval_df = eval_df[~eval_df["excluded_by_prototype_governance"]].copy()
    eval_df["split_score"] = eval_df["eval_row_key"].map(lambda value: int(stable_hash(value, 8), 16) / 0xFFFFFFFF)
    eval_df["calibration_subset"] = np.where(eval_df["split_score"] < 0.60, "calibration_60", "heldout_40")
    return eval_df


def encode_texts(model: SentenceTransformer, texts: list[str]) -> np.ndarray:
    if not texts:
        return np.zeros((0, 384))
    clipped = [" ".join(str(text).split()[:256]) for text in texts]
    return np.asarray(model.encode(clipped, normalize_embeddings=True, show_progress_bar=True, batch_size=64))


def assign_target(unit_emb: np.ndarray, units: pd.DataFrame, target: str, proto_rows: list[dict[str, str]], proto_emb_by_target: dict[str, np.ndarray]) -> pd.DataFrame:
    target_proto = [p for p in proto_rows if p["target"] == target]
    proto_emb = proto_emb_by_target[target]
    if len(units) == 0:
        return pd.DataFrame()
    scores = unit_emb @ proto_emb.T
    best_idx = scores.argmax(axis=1)
    sorted_scores = np.sort(scores, axis=1)[:, ::-1]
    rows = []
    for source_row, idx, score_row, sorted_row in zip(units.itertuples(index=False), best_idx, scores, sorted_scores, strict=True):
        proto = target_proto[int(idx)]
        rows.append(
            {
                "unit_key": source_row.unit_key,
                "source_unit_key": source_row.source_unit_key,
                "path_bucket": source_row.path_bucket,
                "target": target,
                "best_class": proto["class_name"],
                "best_score": round(float(score_row[int(idx)]), 6),
                "best_prototype_id": proto["prototype_id"],
                "score_margin": round(float(sorted_row[0] - sorted_row[1]), 6) if len(sorted_row) > 1 else np.nan,
                "text_hash": source_row.text_hash,
            }
        )
    return pd.DataFrame(rows)


def precision_curve(preds: pd.DataFrame, eval_df: pd.DataFrame, subset: str) -> pd.DataFrame:
    rows = []
    ev = eval_df[eval_df["calibration_subset"].eq(subset)].copy()
    if ev.empty:
        return pd.DataFrame()
    merged = ev.merge(
        preds[["target", "path_bucket", "source_unit_key", "best_score", "best_class"]],
        on=["target", "path_bucket", "source_unit_key"],
        how="left",
    )
    for threshold in [round(x, 2) for x in np.arange(0.30, 0.82, 0.02)]:
        assigned = merged["best_score"].fillna(-1) >= threshold
        covered = int(assigned.sum())
        correct = int((assigned & merged["is_positive"].astype(bool)).sum())
        precision = correct / covered if covered else 0.0
        coverage = covered / len(merged) if len(merged) else 0.0
        rows.append(
            {
                "target": as_text(merged["target"].iloc[0]) if not merged.empty else "",
                "path_bucket": as_text(merged["path_bucket"].iloc[0]) if not merged.empty and "path_bucket" in merged.columns else "",
                "calibration_subset": subset,
                "threshold": threshold,
                "evaluation_rows": int(len(merged)),
                "covered_rows": covered,
                "correct_rows": correct,
                "precision_on_covered": round(precision, 6),
                "coverage_pct": round(coverage * 100, 6),
                "raw_operational_values_emitted": False,
            }
        )
    return pd.DataFrame(rows)


def select_threshold(curve: pd.DataFrame) -> float | None:
    eligible = curve[(curve["precision_on_covered"] >= 0.80) & (curve["covered_rows"] > 0)]
    if eligible.empty:
        return None
    best = eligible.sort_values(["coverage_pct", "precision_on_covered", "threshold"], ascending=[False, False, True]).iloc[0]
    return float(best["threshold"])


def summarize_assignments(preds: pd.DataFrame, thresholds: dict[tuple[str, str], float | None]) -> pd.DataFrame:
    rows = []
    for (target, path), part in preds.groupby(["target", "path_bucket"]):
        threshold = thresholds.get((target, path))
        if threshold is None:
            assigned = pd.Series([False] * len(part), index=part.index)
        else:
            assigned = part["best_score"] >= threshold
        assigned_part = part[assigned]
        class_counts = assigned_part["best_class"].value_counts().to_dict()
        top_count = max(class_counts.values()) if class_counts else 0
        rows.append(
            {
                "target": target,
                "path_bucket": path,
                "units_evaluated": int(len(part)),
                "assigned_units": int(assigned.sum()),
                "abstained": int(len(part) - assigned.sum()),
                "coverage_pct": round(float(assigned.mean() * 100), 6) if len(part) else 0,
                "threshold_selected": threshold if threshold is not None else "",
                "top_class": max(class_counts, key=class_counts.get) if class_counts else "",
                "top_class_count": int(top_count),
                "top_class_share": round(top_count / int(assigned.sum()) * 100, 6) if int(assigned.sum()) else 0,
                "top_class_gt_30pct": bool((top_count / int(assigned.sum()) * 100) > 30) if int(assigned.sum()) else False,
            }
        )
    return pd.DataFrame(rows)


def assigned_class_distribution(evidence_rows: pd.DataFrame) -> pd.DataFrame:
    assigned = evidence_rows[evidence_rows["assigned"].astype(str).str.lower().eq("true")].copy()
    columns = [
        "target", "path_bucket", "predicted_class", "assigned_units",
        "assigned_class_share_pct", "raw_operational_values_emitted",
    ]
    if assigned.empty:
        return pd.DataFrame(columns=columns)
    dist = assigned.groupby(["target", "path_bucket", "predicted_class"]).size().reset_index(name="assigned_units")
    totals = dist.groupby(["target", "path_bucket"])["assigned_units"].transform("sum")
    dist["assigned_class_share_pct"] = (dist["assigned_units"] / totals * 100).round(6)
    dist["raw_operational_values_emitted"] = False
    return dist[columns].sort_values(
        ["target", "path_bucket", "assigned_units", "predicted_class"],
        ascending=[True, True, False, True],
    )


def pre_abstention_best_class_distribution(preds: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "target", "path_bucket", "best_class", "units", "mean_best_score",
        "median_best_score", "p90_best_score", "max_best_score",
        "best_class_share_pct", "best_class_gt_30pct",
        "raw_operational_values_emitted",
    ]
    if preds.empty:
        return pd.DataFrame(columns=columns)
    dist = (
        preds.groupby(["target", "path_bucket", "best_class"])
        .agg(
            units=("unit_key", "count"),
            mean_best_score=("best_score", "mean"),
            median_best_score=("best_score", "median"),
            p90_best_score=("best_score", lambda s: s.quantile(0.90)),
            max_best_score=("best_score", "max"),
        )
        .reset_index()
    )
    totals = dist.groupby(["target", "path_bucket"])["units"].transform("sum")
    dist["best_class_share_pct"] = (dist["units"] / totals * 100).round(6)
    for col in ["mean_best_score", "median_best_score", "p90_best_score", "max_best_score"]:
        dist[col] = dist[col].round(6)
    dist["best_class_gt_30pct"] = dist["best_class_share_pct"] > 30
    dist["raw_operational_values_emitted"] = False
    return dist[columns].sort_values(
        ["target", "path_bucket", "units", "best_class"],
        ascending=[True, True, False, True],
    )


def score_band_distribution(preds: pd.DataFrame) -> pd.DataFrame:
    columns = ["target", "path_bucket", "score_band", "units", "raw_operational_values_emitted"]
    if preds.empty:
        return pd.DataFrame(columns=columns)
    banded = preds[["target", "path_bucket", "best_score"]].copy()
    banded["score_band"] = pd.cut(
        banded["best_score"],
        bins=[-1, .20, .25, .30, .35, .38, .40, .45, .50, .60, .70, .80, 1.01],
        labels=[
            "<=0.20", "0.20-0.25", "0.25-0.30", "0.30-0.35",
            "0.35-0.38", "0.38-0.40", "0.40-0.45", "0.45-0.50",
            "0.50-0.60", "0.60-0.70", "0.70-0.80", ">0.80",
        ],
    )
    dist = banded.groupby(["target", "path_bucket", "score_band"], observed=False).size().reset_index(name="units")
    dist["raw_operational_values_emitted"] = False
    return dist[columns]


def catalogue_vs_zero_shot_comparison(summary: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for row in summary.itertuples(index=False):
        cat_units, cat_top, note = CATALOGUE_BASELINES.get(
            (row.target, row.path_bucket),
            (None, None, "no catalogue baseline declared for this path in G2.0"),
        )
        rows.append(
            {
                "target": row.target,
                "path_bucket": row.path_bucket,
                "catalogue_anchor_units": "" if cat_units is None else int(cat_units),
                "catalogue_top_concept_share_pct": "" if cat_top is None else round(float(cat_top), 6),
                "zero_shot_assigned_units": int(row.assigned_units),
                "zero_shot_coverage_pct": float(row.coverage_pct),
                "zero_shot_threshold_selected": "" if pd.isna(row.threshold_selected) else row.threshold_selected,
                "zero_shot_top_class": "" if pd.isna(row.top_class) else row.top_class,
                "zero_shot_top_class_share_pct": float(row.top_class_share),
                "zero_shot_top_class_gt_30pct": bool(row.top_class_gt_30pct),
                "comparison_note": note,
                "raw_operational_values_emitted": False,
            }
        )
    return pd.DataFrame(rows)


def write_csv(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, quoting=csv.QUOTE_MINIMAL)


def assert_sanitized(paths: list[Path]) -> None:
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="ignore")
        hits = [p.pattern for p in RAW_PATTERNS if p.search(text)]
        if hits:
            raise RuntimeError(f"Sanitization failed for {path}: {hits}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--paths", default=",".join(PATHS), help="Comma-separated paths: B1_RELATIONAL,PATH_A,B2_WORKBOOKS")
    parser.add_argument("--targets", default=",".join(TARGETS), help="Comma-separated targets")
    parser.add_argument("--suffix", default="", help="Optional output filename suffix, e.g. _b1")
    args = parser.parse_args()
    selected_paths = [item.strip() for item in args.paths.split(",") if item.strip()]
    selected_targets = [item.strip() for item in args.targets.split(",") if item.strip()]
    suffix = args.suffix

    OUT.mkdir(parents=True, exist_ok=True)
    unit_frames = []
    if "B1_RELATIONAL" in selected_paths:
        print("loading B1_RELATIONAL", flush=True)
        unit_frames.append(load_b1_units())
    if "PATH_A" in selected_paths:
        print("loading PATH_A", flush=True)
        unit_frames.append(load_path_a_units())
    if "B2_WORKBOOKS" in selected_paths:
        print("loading B2_WORKBOOKS", flush=True)
        unit_frames.append(load_b2_units())
    units = pd.concat(unit_frames, ignore_index=True)
    units = units[units["text"].fillna("").astype(str).str.len() > 0].copy()
    print(f"units loaded: {len(units)}", flush=True)
    model = SentenceTransformer(MODEL_NAME)
    proto_model_rows = prototype_texts_for_model()
    proto_registry = prototype_registry()
    print("encoding unit texts once", flush=True)
    unit_texts = [normalise_text(t) for t in units["text"].fillna("").astype(str)]
    unit_emb = encode_texts(model, unit_texts)
    proto_emb_by_target = {
        target: encode_texts(model, [p["text"] for p in proto_model_rows if p["target"] == target])
        for target in selected_targets
    }

    predictions = []
    for target in selected_targets:
        print(f"assigning {target}", flush=True)
        predictions.append(assign_target(unit_emb, units, target, proto_model_rows, proto_emb_by_target))
    preds = pd.concat(predictions, ignore_index=True)

    eval_df = load_evaluation()
    curves = []
    heldout_rows = []
    thresholds: dict[tuple[str, str], float | None] = {
        (target, path): None for target in selected_targets for path in selected_paths
    }
    for target in ["Cause", "Object Part"]:
        if target not in selected_targets:
            continue
        for path in selected_paths:
            target_preds = preds[preds["target"].eq(target) & preds["path_bucket"].eq(path)]
            present_units = set(target_preds["source_unit_key"].dropna().astype(str))
            target_eval = eval_df[
                eval_df["target"].eq(target)
                & eval_df["path_bucket"].eq(path)
                & eval_df["source_unit_key"].astype(str).isin(present_units)
            ]
            if target_eval.empty:
                thresholds[(target, path)] = None
                continue
            cal_curve = precision_curve(target_preds, target_eval, "calibration_60")
            held_curve = precision_curve(target_preds, target_eval, "heldout_40")
            curves.extend([cal_curve, held_curve])
            threshold = select_threshold(cal_curve)
            thresholds[(target, path)] = threshold
            if threshold is not None and not held_curve.empty:
                final = held_curve[held_curve["threshold"].eq(threshold)].copy()
                final["threshold_selected_from"] = "calibration_60"
                heldout_rows.append(final)

    curve_parts = [c for c in curves if c is not None and not c.empty]
    curve_df = pd.concat(curve_parts, ignore_index=True) if curve_parts else pd.DataFrame(columns=CURVE_COLUMNS)
    heldout_df = pd.concat(heldout_rows, ignore_index=True) if heldout_rows else pd.DataFrame(
        columns=[*CURVE_COLUMNS, "threshold_selected_from"]
    )
    summary = summarize_assignments(preds, thresholds)
    pre_abstention_dist = pre_abstention_best_class_distribution(preds)
    score_band_dist = score_band_distribution(preds)

    evidence_rows = preds.copy()
    evidence_rows["threshold_selected"] = evidence_rows.apply(
        lambda row: thresholds.get((row["target"], row["path_bucket"])),
        axis=1,
    )
    evidence_rows["assigned"] = evidence_rows.apply(
        lambda row: bool(pd.notna(row["threshold_selected"]) and row["threshold_selected"] != "" and row["best_score"] >= float(row["threshold_selected"])),
        axis=1,
    )
    evidence_rows["predicted_class"] = np.where(evidence_rows["assigned"], evidence_rows["best_class"], "abstained")
    evidence_rows["evidence_type"] = "expert_inference"
    evidence_rows["tier"] = "silver-medium"
    evidence_rows["label_generation_method"] = LABEL_METHOD
    evidence_rows["embedding_model"] = MODEL_NAME
    evidence_rows["evaluation_independence"] = "derived_from_rules"
    evidence_rows["anchor_source"] = "prototype_domain_vocabulary"
    evidence_rows["status"] = "candidate_not_promoted"
    evidence_rows["raw_operational_values_emitted"] = False
    prototype_meta = proto_registry[
        [
            "prototype_id", "prototype_source", "construction_method",
            "evaluation_exclusion", "prototype_baseline_type",
        ]
    ].rename(columns={"prototype_id": "best_prototype_id"})
    evidence_rows = evidence_rows.merge(prototype_meta, on="best_prototype_id", how="left")
    evidence_rows = evidence_rows[
        [
            "unit_key", "source_unit_key", "path_bucket", "target", "predicted_class", "best_score",
            "best_prototype_id", "score_margin", "assigned", "threshold_selected", "text_hash",
            "evidence_type", "tier", "label_generation_method", "embedding_model",
            "evaluation_independence", "anchor_source", "prototype_source",
            "construction_method", "evaluation_exclusion",
            "prototype_baseline_type", "status", "raw_operational_values_emitted",
        ]
    ]

    split_manifest = eval_df[
        [
            "eval_row_key", "sampling_unit_key", "source_unit_key", "target", "annotator_id",
            "path", "path_bucket", "response", "is_positive", "calibration_subset",
            "excluded_by_prototype_governance",
        ]
    ].copy()

    paths = {
        "registry": OUT / f"g20_prototype_registry{suffix}_sanitized.csv",
        "evidence": OUT / f"g20_zero_shot_evidence_rows{suffix}_sanitized.csv",
        "summary": OUT / f"g20_zero_shot_summary_by_target_path{suffix}_sanitized.csv",
        "curve": OUT / f"g20_precision_coverage_curve{suffix}_sanitized.csv",
        "heldout": OUT / f"g20_heldout_precision_at_selected_threshold{suffix}_sanitized.csv",
        "split": OUT / f"g20_evaluation_split_manifest{suffix}_sanitized.csv",
        "class_dist": OUT / f"g20_assigned_class_distribution{suffix}_sanitized.csv",
        "pre_abstention_dist": OUT / f"g20_pre_abstention_best_class_distribution{suffix}_sanitized.csv",
        "score_bands": OUT / f"g20_score_band_distribution{suffix}_sanitized.csv",
    }
    write_csv(paths["registry"], proto_registry)
    write_csv(paths["evidence"], evidence_rows)
    write_csv(paths["summary"], summary)
    write_csv(paths["curve"], curve_df)
    write_csv(paths["heldout"], heldout_df)
    write_csv(paths["split"], split_manifest)
    write_csv(paths["class_dist"], assigned_class_distribution(evidence_rows))
    write_csv(paths["pre_abstention_dist"], pre_abstention_dist)
    write_csv(paths["score_bands"], score_band_dist)

    comparison_path = None
    comparison_memo_path = None
    if suffix == "":
        comparison_path = OUT / "g20_catalogue_vs_zero_shot_comparison_sanitized.csv"
        comparison_memo_path = OUT / "g20_catalogue_vs_zero_shot_comparison.md"
        write_csv(comparison_path, catalogue_vs_zero_shot_comparison(summary))
        comparison_memo_path.write_text(
            "# G2.0 Catalogue vs Zero-Shot Comparison\n\n"
            "This comparison is derived from the sanitized G2.0 full-run summary and the catalogue-anchor baselines established in G1.1d/G1.2c. "
            "It performs no candidate promotion and no denominator change.\n\n"
            "Catalogue baselines are declared only where already measured. Blank catalogue fields mean no comparable catalogue baseline was declared for that target/path in G2.0.\n",
            encoding="utf-8",
        )

    meta = {
        "created_at_utc": utc_now(),
        "task": "G2.0_zero_shot_prototype_baseline",
        "model": MODEL_NAME,
        "label_generation_method": LABEL_METHOD,
        "targets_run": selected_targets,
        "paths_run": selected_paths,
        "units_loaded": int(len(units)),
        "thresholds": {f"{target}|{path}": threshold for (target, path), threshold in thresholds.items()},
        "calibration_rule": "select max coverage subject to precision >= 0.80 on calibration_60; report final on heldout_40",
        "symptom_rerun": False,
        "candidate_promotion_performed": False,
        "denominator_change_performed": False,
        "raw_text_emitted": False,
    }
    (OUT / f"g20_zero_shot_summary{suffix}_sanitized.json").write_text(json.dumps(meta, indent=2, sort_keys=True), encoding="utf-8")
    memo = """# G2.0 Zero-Shot Prototype Baseline

This pass runs prototype-domain zero-shot matching for Activity, Cause, Damage, and Object Part. Symptom is not rerun.

Thresholds are selected only for targets admitted in evaluation_set_v1 and processed in this run: Cause and Object Part. Damage and Activity are reported without selected thresholds pending g01-v2.

No denominator change, no candidate promotion, and no raw text emission.
"""
    (OUT / f"g20_zero_shot_baseline_memo{suffix}.md").write_text(memo, encoding="utf-8")
    sanitized_targets = [*paths.values(), OUT / f"g20_zero_shot_summary{suffix}_sanitized.json", OUT / f"g20_zero_shot_baseline_memo{suffix}.md"]
    if comparison_path is not None and comparison_memo_path is not None:
        sanitized_targets.extend([comparison_path, comparison_memo_path])
    assert_sanitized(sanitized_targets)
    print(json.dumps(meta, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
