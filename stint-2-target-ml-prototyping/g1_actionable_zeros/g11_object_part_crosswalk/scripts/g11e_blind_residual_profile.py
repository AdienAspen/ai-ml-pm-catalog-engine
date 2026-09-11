from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path("/home/adien-i7-remote/workspace/fsa_bridge_ml_feasibility")
STINT2_ROOT = PROJECT_ROOT / "stint-2-target-ml-prototyping"
G11_ROOT = STINT2_ROOT / "g1_actionable_zeros" / "g11_object_part_crosswalk"
OUT = G11_ROOT / "outputs"
INTERNAL_OUT = G11_ROOT / "internal"

SERVICE_ORDERS_JSON = (
    PROJECT_ROOT
    / "data/interim/extracted_source/package_001_37cac7fe/Data/Vestas/api_service_v1_service-orders.json"
)
ITEM_ROWS = OUT / "g11_item_signal_rows_sanitized.csv"
CROSSWALK = OUT / "g11_material_to_catalog_b_crosswalk_sanitized.csv"
INTERNAL_CROSSWALK = INTERNAL_OUT / "g11_material_to_catalog_b_crosswalk_internal_review.csv"
G11C_ORDER_PROFILE = OUT / "g11c_no_item_signal_order_profile_sanitized.csv"
CANONICAL_VOCAB = (
    PROJECT_ROOT
    / "stint-1-evidence-ground-truth/phase_1_lexical/outputs/canonical_vocabulary/"
    / "canonical_vocabulary_v1_working.csv"
)


CONSUMABLE_PATTERNS = [
    r"\bgrease\b",
    r"\boil\b",
    r"\bfluid\b",
    r"\blubric",
    r"\bclean",
    r"\bcleaner\b",
    r"\bcloth\b",
    r"\bwipe",
    r"\brag\b",
    r"\btowel\b",
    r"\bsolvent\b",
    r"\bdegreaser\b",
    r"\bpaint\b",
    r"\blabel\b",
    r"\bdecal\b",
    r"\btape\b",
    r"\bsealant\b",
    r"\badhesive\b",
    r"\bglove",
    r"\bsafety\b",
    r"\bppe\b",
    r"\bwater\b",
]

GENERIC_HARDWARE_PATTERNS = [
    r"\bnut\b",
    r"\bnuts\b",
    r"\bbolt\b",
    r"\bbolts\b",
    r"\bscrew",
    r"\bwasher",
    r"\bshim",
    r"\bspacer",
    r"\brivet",
    r"\bpin\b",
    r"\bclip\b",
    r"\bclamp\b",
    r"\bbracket\b",
    r"\bplate\b",
    r"\bsheet\b",
    r"\bfastener",
    r"\btie\b",
    r"\bcable tie\b",
]

LIKELY_COMPONENT_PATTERNS = [
    r"\bconnector\b",
    r"\bbattery\b",
    r"\bstack\b",
    r"\bsensor\b",
    r"\bswitch\b",
    r"\bvalve\b",
    r"\brelay\b",
    r"\bcontactor\b",
    r"\bmotor\b",
    r"\bcable\b",
    r"\bhose\b",
    r"\bpump\b",
    r"\bfan\b",
    r"\bheater\b",
    r"\bbearing\b",
    r"\bfilter\b",
    r"\bmodule\b",
    r"\bconverter\b",
    r"\bcontroller\b",
    r"\bboard\b",
    r"\bpcb\b",
    r"\bterminal\b",
    r"\btransducer\b",
    r"\bencoder\b",
    r"\bactuator\b",
    r"\bseal\b",
    r"\bo[- ]?ring\b",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_hash(value: object, length: int = 16) -> str:
    raw = "" if value is None else str(value)
    return hashlib.sha256(raw.encode("utf-8", errors="ignore")).hexdigest()[:length]


def prefixed_hash(prefix: str, value: object, length: int = 16) -> str:
    return f"{prefix}-{stable_hash(value, length)}"


def normalize_text(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def word_count(value: object) -> int:
    return len(re.findall(r"[A-Za-z0-9]+", str(value or "")))


def read_json_records(path: Path) -> pd.DataFrame:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise RuntimeError(f"Expected list payload: {path}")
    return pd.DataFrame(payload)


def match_any(patterns: list[str], text: str) -> bool:
    return any(re.search(pattern, text) for pattern in patterns)


def classify_item_concept(description: object) -> str:
    text = str(description or "").lower()
    if match_any(CONSUMABLE_PATTERNS, text):
        return "consumable_or_non_component"
    if match_any(GENERIC_HARDWARE_PATTERNS, text):
        return "generic_hardware"
    if match_any(LIKELY_COMPONENT_PATTERNS, text):
        return "likely_component_no_code"
    return "undetermined"


def count_bins(series: pd.Series, group_name: str, field: str = "combined_text") -> pd.DataFrame:
    bins = [-1, 0, 5, 20, 50, 100, 200, 500, 1000, 10**9]
    labels = ["0", "1-5", "6-20", "21-50", "51-100", "101-200", "201-500", "501-1000", ">1000"]
    binned = pd.cut(series, bins=bins, labels=labels)
    rows = binned.value_counts(sort=False).rename_axis("word_count_bin").reset_index(name="orders")
    rows.insert(0, "group", group_name)
    rows.insert(1, "text_field", field)
    rows["share_of_group"] = (rows["orders"] / len(series) * 100).round(6)
    return rows


def frequency_bins(series: pd.Series) -> pd.DataFrame:
    bins = [0, 1, 2, 5, 10, 25, 50, 100, 250, 500, 10**9]
    labels = ["1", "2", "3-5", "6-10", "11-25", "26-50", "51-100", "101-250", "251-500", ">500"]
    binned = pd.cut(series, bins=bins, labels=labels)
    rows = binned.value_counts(sort=False).rename_axis("orders_per_concept_bin").reset_index(name="concepts")
    rows["share_of_concepts"] = (rows["concepts"] / len(series) * 100).round(6)
    return rows


def object_part_vocab_terms() -> pd.DataFrame:
    vocab = pd.read_csv(CANONICAL_VOCAB)
    vocab = vocab[(vocab["target"].astype(str) == "Object Part") & vocab["canonical_concept"].notna()].copy()
    vocab["normalized_concept"] = vocab["canonical_concept"].map(normalize_text)
    vocab = vocab[vocab["normalized_concept"] != ""]
    return vocab[["canonical_concept_key", "normalized_concept"]].drop_duplicates()


def count_existing_vocab_matches(text: object, terms: pd.DataFrame) -> int:
    padded = f" {normalize_text(text)} "
    count = 0
    for phrase in terms["normalized_concept"]:
        if f" {phrase} " in padded:
            count += 1
    return count


def build_group_a() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    item_rows = pd.read_csv(ITEM_ROWS)
    crosswalk = pd.read_csv(CROSSWALK)
    internal = pd.read_csv(INTERNAL_CROSSWALK)

    strong_concepts = set(
        crosswalk.loc[crosswalk["crosswalk_status"] == "auto_candidate_strong", "source_item_concept_key"]
    )
    strong_orders = set(
        item_rows.loc[item_rows["source_item_concept_key"].isin(strong_concepts), "order_id_hash"]
    )
    item_orders = set(item_rows["order_id_hash"])
    group_a_orders = item_orders - strong_orders

    residual_rows = item_rows[
        item_rows["order_id_hash"].isin(group_a_orders)
        & ~item_rows["source_item_concept_key"].isin(strong_concepts)
    ].copy()

    concept_profile = (
        residual_rows.groupby("source_item_concept_key", dropna=False)
        .agg(
            item_rows_in_group_a=("order_id_hash", "size"),
            orders_in_group_a=("order_id_hash", "nunique"),
        )
        .reset_index()
        .merge(
            crosswalk[
                [
                    "source_item_concept_key",
                    "item_id_hash",
                    "item_description_hash",
                    "crosswalk_status",
                    "match_score",
                    "catalog",
                    "catalog_b_code_group",
                    "catalog_b_code",
                ]
            ],
            on="source_item_concept_key",
            how="left",
            validate="one_to_one",
        )
        .merge(
            internal[["source_item_concept_key", "item_id", "item_description", "material_head"]],
            on="source_item_concept_key",
            how="left",
            validate="one_to_one",
        )
    )
    concept_profile["blind_profile_class"] = concept_profile["item_description"].map(classify_item_concept)
    concept_profile = concept_profile.sort_values(
        ["orders_in_group_a", "source_item_concept_key"], ascending=[False, True]
    )

    sanitized = concept_profile.drop(columns=["item_id", "item_description", "material_head"]).copy()
    return concept_profile, sanitized, pd.DataFrame({"order_id_hash": sorted(group_a_orders)})


def build_group_b() -> tuple[pd.DataFrame, pd.DataFrame]:
    g11c = pd.read_csv(G11C_ORDER_PROFILE)
    group_b = g11c[
        (~g11c["has_high_band_object_part_anchor"])
        & (g11c["combined_text_word_count"] > 0)
    ].copy()
    anchored = g11c[g11c["has_high_band_object_part_anchor"]].copy()
    return group_b, anchored


def write_internal_sample(path: Path, rows: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    clean = rows.copy()
    object_columns = clean.select_dtypes(include=["object"]).columns
    for column in object_columns:
        clean[column] = clean[column].map(
            lambda value: re.sub(r"\s+", " ", str(value)).strip() if pd.notna(value) else ""
        )
    clean.to_csv(path, index=False)
    os.chmod(path, 0o600)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    INTERNAL_OUT.mkdir(parents=True, exist_ok=True)
    os.chmod(INTERNAL_OUT, 0o700)

    group_a_visible, group_a_sanitized, group_a_orders = build_group_a()
    group_b, group_b_anchored = build_group_b()

    group_a_sanitized.to_csv(OUT / "g11e_group_a_unresolved_item_concept_profile_sanitized.csv", index=False)
    class_breakdown = (
        group_a_sanitized.groupby(["blind_profile_class"], dropna=False)
        .agg(
            distinct_item_concepts=("source_item_concept_key", "nunique"),
            orders_covered=("orders_in_group_a", "sum"),
            item_rows=("item_rows_in_group_a", "sum"),
        )
        .reset_index()
        .sort_values(["distinct_item_concepts", "blind_profile_class"], ascending=[False, True])
    )
    class_breakdown["share_of_distinct_concepts"] = (
        class_breakdown["distinct_item_concepts"] / len(group_a_sanitized) * 100
    ).round(6)
    class_breakdown.to_csv(OUT / "g11e_group_a_class_breakdown_sanitized.csv", index=False)

    frequency_bins(group_a_sanitized["orders_in_group_a"]).to_csv(
        OUT / "g11e_group_a_concept_frequency_distribution_sanitized.csv", index=False
    )

    status_breakdown = (
        group_a_sanitized.groupby(["crosswalk_status", "blind_profile_class"], dropna=False)
        .agg(
            distinct_item_concepts=("source_item_concept_key", "nunique"),
            orders_covered=("orders_in_group_a", "sum"),
        )
        .reset_index()
        .sort_values(["crosswalk_status", "distinct_item_concepts"], ascending=[True, False])
    )
    status_breakdown.to_csv(OUT / "g11e_group_a_status_class_breakdown_sanitized.csv", index=False)

    group_a_sample = (
        group_a_visible.groupby("blind_profile_class", group_keys=False)
        .apply(lambda df: df.sort_values(["orders_in_group_a", "source_item_concept_key"], ascending=[False, True]).head(5))
        .head(20)
        .copy()
    )
    write_internal_sample(
        INTERNAL_OUT / "g11e_group_a_blind_concept_sample_internal.csv",
        group_a_sample[
            [
                "source_item_concept_key",
                "item_id",
                "item_description",
                "material_head",
                "crosswalk_status",
                "match_score",
                "orders_in_group_a",
                "item_rows_in_group_a",
                "blind_profile_class",
            ]
        ],
    )

    activity_compare = pd.concat(
        [
            group_b.assign(group="no_high_band_anchor_with_text"),
            group_b_anchored.assign(group="high_band_anchor"),
        ],
        ignore_index=True,
    )
    activity_rows = (
        activity_compare.groupby(["group", "resource_activity_bucket", "unlikely_component_activity_bucket"], dropna=False)
        .size()
        .reset_index(name="orders")
    )
    group_sizes = activity_compare.groupby("group").size().to_dict()
    activity_rows["share_of_group"] = activity_rows.apply(
        lambda row: round(row["orders"] / group_sizes[row["group"]] * 100, 6), axis=1
    )
    activity_rows = activity_rows.sort_values(["group", "orders"], ascending=[True, False])
    activity_rows.to_csv(OUT / "g11e_group_b_activity_comparison_sanitized.csv", index=False)

    word_rows = pd.concat(
        [
            count_bins(group_b["combined_text_word_count"], "no_high_band_anchor_with_text"),
            count_bins(group_b_anchored["combined_text_word_count"], "high_band_anchor"),
        ],
        ignore_index=True,
    )
    word_rows.to_csv(OUT / "g11e_group_b_word_count_comparison_sanitized.csv", index=False)

    quantile_rows = []
    for name, frame in [
        ("no_high_band_anchor_with_text", group_b),
        ("high_band_anchor", group_b_anchored),
    ]:
        s = frame["combined_text_word_count"]
        for stat, value in {
            "min": s.min(),
            "p25": s.quantile(0.25),
            "median": s.quantile(0.50),
            "p75": s.quantile(0.75),
            "p90": s.quantile(0.90),
            "p95": s.quantile(0.95),
            "max": s.max(),
        }.items():
            quantile_rows.append({"group": name, "statistic": stat, "combined_text_word_count": float(value)})
    pd.DataFrame(quantile_rows).to_csv(OUT / "g11e_group_b_word_count_quantiles_sanitized.csv", index=False)

    service_orders = read_json_records(SERVICE_ORDERS_JSON)
    service_orders["order_id_hash"] = service_orders["id"].map(lambda value: prefixed_hash("ORDER", value))
    sample_orders = (
        group_b.sort_values(["combined_text_word_count", "order_id_hash"], ascending=[False, True])
        .sample(n=min(20, len(group_b)), random_state=1105)
        .sort_values("order_id_hash")
        .merge(
            service_orders[
                [
                    "order_id_hash",
                    "id",
                    "description",
                    "descriptionExtended",
                    "reason",
                    "activityType",
                    "type",
                    "assetType",
                ]
            ],
            on="order_id_hash",
            how="left",
            validate="one_to_one",
            suffixes=("_profile", "_visible"),
        )
    )
    vocab_terms = object_part_vocab_terms()
    sample_orders["existing_object_part_vocab_phrase_matches"] = (
        sample_orders["descriptionExtended"].fillna("").astype(str)
        + " "
        + sample_orders["reason"].fillna("").astype(str)
    ).map(lambda text: count_existing_vocab_matches(text, vocab_terms))
    sample_orders["physical_component_mention_existing_vocab"] = sample_orders[
        "existing_object_part_vocab_phrase_matches"
    ].map(lambda count: "yes" if count > 0 else "no")
    sample_orders["physical_component_mention_blind_review"] = ""
    write_internal_sample(
        INTERNAL_OUT / "g11e_group_b_blind_order_sample_internal.csv",
        sample_orders[
            [
                "order_id_hash",
                "id",
                "description",
                "descriptionExtended",
                "reason",
                "activityType_visible",
                "type_visible",
                "assetType_visible",
                "resource_activity_bucket",
                "combined_text_word_count",
                "existing_object_part_vocab_phrase_matches",
                "physical_component_mention_existing_vocab",
                "physical_component_mention_blind_review",
            ]
        ],
    )

    summary = {
        "task": "G1.1e_blind_residual_profile",
        "created_at_utc": utc_now(),
        "group_a_definition": "Item-bearing B1 orders with no auto_candidate_strong material concept.",
        "group_a_orders": int(len(group_a_orders)),
        "group_a_distinct_unresolved_item_concepts": int(len(group_a_sanitized)),
        "group_a_class_breakdown": class_breakdown.to_dict(orient="records"),
        "group_b_definition": "No-item B1 orders with non-empty combined text and zero high-band Object Part anchor.",
        "group_b_orders_exact": int(len(group_b)),
        "group_b_high_band_anchor_comparator_orders": int(len(group_b_anchored)),
        "group_b_no_anchor_including_empty_text": int((~pd.read_csv(G11C_ORDER_PROFILE)["has_high_band_object_part_anchor"]).sum()),
        "group_b_empty_text_no_anchor": int(
            (
                (~pd.read_csv(G11C_ORDER_PROFILE)["has_high_band_object_part_anchor"])
                & (pd.read_csv(G11C_ORDER_PROFILE)["combined_text_word_count"] == 0)
            ).sum()
        ),
        "candidate_promotion_performed": False,
        "denominator_change_performed": False,
        "visible_text_samples": {
            "group_a": "internal/g11e_group_a_blind_concept_sample_internal.csv",
            "group_b": "internal/g11e_group_b_blind_order_sample_internal.csv",
            "file_mode": "600",
            "directory_mode": "700",
        },
        "versioned_raw_text_emitted": False,
        "tooling_note": "pandas over existing artefacts; classification is rule-based blind profiling, not candidate emission.",
    }
    (OUT / "g11e_blind_residual_profile_summary_sanitized.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )

    memo = f"""# G1.1e Blind Residual Profile Memo

G1.1e profiles the two Object Part B1 residual groups before G2 scope is set.

## Group A

Group A is defined as item-bearing B1 orders with no `auto_candidate_strong` material concept.

- Orders: {len(group_a_orders):,}
- Distinct unresolved item concepts: {len(group_a_sanitized):,}

The concept classification is a blind rule-based profile over visible material descriptions in the closed environment. It is not a candidate promotion.

## Group B

Group B is defined as no-item B1 orders with non-empty combined text and zero high-band Object Part anchor.

- Exact count with text and no high-band anchor: {len(group_b):,}
- Comparator with high-band anchor: {len(group_b_anchored):,}

## Governance

- No candidate emitted.
- No denominator changed.
- Versioned outputs are sanitized.
- Visible-text samples are internal only, mode 600.
"""
    (OUT / "g11e_blind_residual_profile_memo.md").write_text(memo, encoding="utf-8")


if __name__ == "__main__":
    main()
