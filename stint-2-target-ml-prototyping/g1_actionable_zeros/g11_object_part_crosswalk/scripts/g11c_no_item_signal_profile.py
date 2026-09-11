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
OUT = STINT2_ROOT / "g1_actionable_zeros" / "g11_object_part_crosswalk" / "outputs"

SERVICE_ORDERS_JSON = (
    PROJECT_ROOT
    / "data/interim/extracted_source/package_001_37cac7fe/Data/Vestas/api_service_v1_service-orders.json"
)
CONSUMPTION_JSON = (
    PROJECT_ROOT
    / "data/interim/extracted_source/package_001_37cac7fe/Data/Vestas/api_service_v1_service-orders_consumption.json"
)
LEXICAL_HIGH = (
    PROJECT_ROOT
    / "stint-1-evidence-ground-truth/phase_1_lexical/outputs/lexical_layer_v2/"
    / "lexical_layer_v2_high_confidence_candidates_sanitized.csv"
)
CANONICAL_VOCAB = (
    PROJECT_ROOT
    / "stint-1-evidence-ground-truth/phase_1_lexical/outputs/canonical_vocabulary/"
    / "canonical_vocabulary_v1_working.csv"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_hash(value: object, length: int = 16) -> str:
    raw = "" if value is None else str(value)
    return hashlib.sha256(raw.encode("utf-8", errors="ignore")).hexdigest()[:length]


def prefixed_hash(prefix: str, value: object, length: int = 16) -> str:
    return f"{prefix}-{stable_hash(value, length)}"


def is_non_empty(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, float) and pd.isna(value):
        return False
    return bool(str(value).strip())


def normalize_text(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def word_count(value: object) -> int:
    return len(re.findall(r"[A-Za-z0-9]+", str(value or "")))


def read_json_records(path: Path) -> pd.DataFrame:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise RuntimeError(f"Expected list payload: {path}")
    return pd.DataFrame(payload)


def resource_activity_bucket(resources: object) -> str:
    if not isinstance(resources, list) or not resources:
        return "no_resource_activity"
    labels = sorted(
        {
            normalize_text(resource.get("activityTypeId") or resource.get("activityType") or "unknown_activity")
            for resource in resources
            if isinstance(resource, dict)
        }
    )
    return "|".join(labels) if labels else "no_resource_activity"


def unlikely_component_bucket(activity_bucket: str) -> str:
    pieces = set(activity_bucket.split("|"))
    if pieces and pieces <= {"travel to from turbine", "mob de mob"}:
        return "travel_or_mob_only"
    if pieces & {"travel to from turbine", "mob de mob"}:
        return "mixed_with_travel_or_mob"
    if pieces == {"no_resource_activity"}:
        return "no_resource_activity"
    return "work_or_other_activity"


def load_object_part_high_band_terms() -> pd.DataFrame:
    lexical = pd.read_csv(LEXICAL_HIGH)
    lexical = lexical[
        (lexical["target"].astype(str) == "Object Part")
        & (lexical["score_band"].astype(str).str.lower() == "high")
        & (lexical["status"].astype(str) == "semantic_anchor_high")
        & (lexical["can_support_proxy_denominator"].astype(str).str.lower() == "true")
    ].copy()

    vocab = pd.read_csv(CANONICAL_VOCAB)
    vocab = vocab[
        [
            "concept_id",
            "canonical_concept_key",
            "canonical_concept",
            "target",
            "target_code",
            "code_group",
            "vocabulary_owner",
        ]
    ].copy()
    terms = lexical.merge(
        vocab,
        left_on="canonical_concept_id",
        right_on="concept_id",
        how="left",
        suffixes=("_lexical", "_vocab"),
    )
    terms = terms[terms["canonical_concept"].map(is_non_empty)].copy()
    terms["normalized_concept"] = terms["canonical_concept"].map(normalize_text)
    terms["token_count"] = terms["normalized_concept"].str.split().map(len)
    terms = terms[(terms["normalized_concept"] != "") & (terms["token_count"] > 0)].copy()
    return terms.drop_duplicates(
        ["canonical_concept_key_vocab", "normalized_concept", "target_code", "code_group"]
    ).reset_index(drop=True)


def match_high_band_concepts(text: str, terms: pd.DataFrame) -> list[dict[str, object]]:
    padded = f" {text} "
    matches: list[dict[str, object]] = []
    for row in terms.itertuples(index=False):
        phrase = getattr(row, "normalized_concept")
        if f" {phrase} " in padded:
            matches.append(
                {
                    "canonical_concept_key": getattr(row, "canonical_concept_key_vocab"),
                    "target_code": getattr(row, "target_code"),
                    "code_group": getattr(row, "code_group"),
                    "vocabulary_owner": getattr(row, "vocabulary_owner_vocab"),
                }
            )
    return matches


def count_bins(series: pd.Series, field: str) -> pd.DataFrame:
    bins = [-1, 0, 5, 20, 50, 100, 200, 500, 1000, 10**9]
    labels = ["0", "1-5", "6-20", "21-50", "51-100", "101-200", "201-500", "501-1000", ">1000"]
    binned = pd.cut(series, bins=bins, labels=labels)
    rows = binned.value_counts(sort=False).rename_axis("word_count_bin").reset_index(name="orders")
    rows.insert(0, "text_field", field)
    rows["share_of_no_item_orders"] = (rows["orders"] / len(series) * 100).round(6)
    return rows


def quantile_rows(series: pd.Series, field: str) -> list[dict[str, object]]:
    quantiles = {
        "min": float(series.min()),
        "p25": float(series.quantile(0.25)),
        "median": float(series.quantile(0.50)),
        "p75": float(series.quantile(0.75)),
        "p90": float(series.quantile(0.90)),
        "p95": float(series.quantile(0.95)),
        "max": float(series.max()),
    }
    return [{"text_field": field, "statistic": name, "word_count": value} for name, value in quantiles.items()]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    service_orders = read_json_records(SERVICE_ORDERS_JSON)
    consumption = read_json_records(CONSUMPTION_JSON)

    consumption["order_id"] = consumption["orderId"].astype(str).str.strip()
    consumption["has_item_signal"] = consumption["items"].map(lambda items: isinstance(items, list) and len(items) > 0)
    consumption["resource_activity_bucket"] = consumption["resources"].map(resource_activity_bucket)
    consumption["unlikely_component_activity_bucket"] = consumption["resource_activity_bucket"].map(unlikely_component_bucket)

    no_item_orders = consumption[~consumption["has_item_signal"]].copy()

    service_orders["order_id"] = service_orders["id"].astype(str).str.strip()
    frame = no_item_orders[
        ["order_id", "resource_activity_bucket", "unlikely_component_activity_bucket"]
    ].merge(
        service_orders[
            [
                "order_id",
                "descriptionExtended",
                "reason",
                "activityType",
                "type",
                "assetType",
            ]
        ],
        on="order_id",
        how="left",
        validate="one_to_one",
    )

    for field in ["descriptionExtended", "reason"]:
        frame[f"has_{field}"] = frame[field].map(is_non_empty)
        frame[f"{field}_word_count"] = frame[field].map(word_count)
    frame["combined_text"] = (
        frame["descriptionExtended"].fillna("").astype(str) + " " + frame["reason"].fillna("").astype(str)
    )
    frame["combined_text_word_count"] = frame["combined_text"].map(word_count)
    frame["normalized_combined_text"] = frame["combined_text"].map(normalize_text)

    terms = load_object_part_high_band_terms()
    concept_counts: dict[tuple[str, str, str, str], set[str]] = {}
    anchor_counts: list[int] = []

    for row in frame[["order_id", "normalized_combined_text"]].itertuples(index=False):
        matches = match_high_band_concepts(row.normalized_combined_text, terms)
        unique = {
            (
                str(match["canonical_concept_key"]),
                str(match["target_code"]),
                str(match["code_group"]),
                str(match["vocabulary_owner"]),
            )
            for match in matches
        }
        anchor_counts.append(len(unique))
        for key in unique:
            concept_counts.setdefault(key, set()).add(row.order_id)

    frame["high_band_object_part_anchor_count"] = anchor_counts
    frame["has_high_band_object_part_anchor"] = frame["high_band_object_part_anchor_count"] > 0

    order_profile = frame[
        [
            "order_id",
            "has_descriptionExtended",
            "has_reason",
            "descriptionExtended_word_count",
            "reason_word_count",
            "combined_text_word_count",
            "resource_activity_bucket",
            "unlikely_component_activity_bucket",
            "activityType",
            "type",
            "assetType",
            "high_band_object_part_anchor_count",
            "has_high_band_object_part_anchor",
        ]
    ].copy()
    order_profile.insert(0, "order_id_hash", order_profile["order_id"].map(lambda value: prefixed_hash("ORDER", value)))
    order_profile = order_profile.drop(columns=["order_id"])
    order_profile.to_csv(OUT / "g11c_no_item_signal_order_profile_sanitized.csv", index=False)

    resource_activity = (
        frame.groupby(["resource_activity_bucket", "unlikely_component_activity_bucket"], dropna=False)
        .size()
        .reset_index(name="orders")
        .sort_values(["orders", "resource_activity_bucket"], ascending=[False, True])
    )
    resource_activity["share_of_no_item_orders"] = (resource_activity["orders"] / len(frame) * 100).round(6)
    resource_activity.to_csv(OUT / "g11c_no_item_signal_resource_activity_sanitized.csv", index=False)

    service_activity = (
        frame.groupby(["activityType"], dropna=False)
        .size()
        .reset_index(name="orders")
        .sort_values(["orders", "activityType"], ascending=[False, True])
    )
    service_activity["share_of_no_item_orders"] = (service_activity["orders"] / len(frame) * 100).round(6)
    service_activity.to_csv(OUT / "g11c_no_item_signal_service_activity_type_sanitized.csv", index=False)

    word_bins = pd.concat(
        [
            count_bins(frame["descriptionExtended_word_count"], "descriptionExtended"),
            count_bins(frame["reason_word_count"], "reason"),
            count_bins(frame["combined_text_word_count"], "combined_text"),
        ],
        ignore_index=True,
    )
    word_bins.to_csv(OUT / "g11c_no_item_signal_word_count_bins_sanitized.csv", index=False)

    word_quantiles = pd.DataFrame(
        [
            *quantile_rows(frame["descriptionExtended_word_count"], "descriptionExtended"),
            *quantile_rows(frame["reason_word_count"], "reason"),
            *quantile_rows(frame["combined_text_word_count"], "combined_text"),
        ]
    )
    word_quantiles.to_csv(OUT / "g11c_no_item_signal_word_count_quantiles_sanitized.csv", index=False)

    anchor_distribution = (
        frame["high_band_object_part_anchor_count"]
        .value_counts()
        .rename_axis("high_band_object_part_anchor_count")
        .reset_index(name="orders")
        .sort_values("high_band_object_part_anchor_count")
    )
    anchor_distribution["share_of_no_item_orders"] = (anchor_distribution["orders"] / len(frame) * 100).round(6)
    anchor_distribution.to_csv(OUT / "g11c_no_item_signal_anchor_count_distribution_sanitized.csv", index=False)

    concept_rows = []
    for (concept_key, target_code, code_group, vocabulary_owner), order_ids in concept_counts.items():
        concept_rows.append(
            {
                "canonical_concept_key": concept_key,
                "target_code": target_code,
                "code_group": code_group,
                "vocabulary_owner": vocabulary_owner,
                "orders_with_anchor": len(order_ids),
                "share_of_anchored_orders": 0.0,
            }
        )
    concept_profile = pd.DataFrame(concept_rows)
    if concept_profile.empty:
        concept_profile = pd.DataFrame(
            columns=[
                "canonical_concept_key",
                "target_code",
                "code_group",
                "vocabulary_owner",
                "orders_with_anchor",
                "share_of_anchored_orders",
            ]
        )
    else:
        anchored_orders = int(frame["has_high_band_object_part_anchor"].sum())
        concept_profile["share_of_anchored_orders"] = (
            concept_profile["orders_with_anchor"] / anchored_orders * 100
        ).round(6)
        concept_profile = concept_profile.sort_values(
            ["orders_with_anchor", "canonical_concept_key"], ascending=[False, True]
        )
    concept_profile.to_csv(OUT / "g11c_no_item_signal_lexical_anchor_concepts_sanitized.csv", index=False)

    summary = {
        "task": "G1.1c_no_item_signal_profile",
        "created_at_utc": utc_now(),
        "scope": "B1 orders without consumption item signal only",
        "service_order_universe": int(len(service_orders)),
        "orders_with_item_signal": int(consumption["has_item_signal"].sum()),
        "orders_without_item_signal": int(len(frame)),
        "descriptionExtended_non_empty": int(frame["has_descriptionExtended"].sum()),
        "descriptionExtended_non_empty_percent": round(float(frame["has_descriptionExtended"].mean() * 100), 6),
        "reason_non_empty": int(frame["has_reason"].sum()),
        "reason_non_empty_percent": round(float(frame["has_reason"].mean() * 100), 6),
        "combined_text_non_empty": int((frame["combined_text_word_count"] > 0).sum()),
        "combined_text_non_empty_percent": round(float((frame["combined_text_word_count"] > 0).mean() * 100), 6),
        "object_part_high_band_canonical_concepts_loaded": int(terms["canonical_concept_key_vocab"].nunique()),
        "orders_with_at_least_one_object_part_high_band_anchor": int(
            frame["has_high_band_object_part_anchor"].sum()
        ),
        "orders_with_at_least_one_object_part_high_band_anchor_percent": round(
            float(frame["has_high_band_object_part_anchor"].mean() * 100), 6
        ),
        "unique_object_part_high_band_concepts_matched": int(
            concept_profile["canonical_concept_key"].nunique() if not concept_profile.empty else 0
        ),
        "unversioned_visible_text_emitted": False,
        "candidate_promotion_performed": False,
        "denominator_change_performed": False,
        "lexical_anchor_rule": "Object Part lexical_layer_v2 high band only; canonical concepts phrase-matched to descriptionExtended + reason for profiling counts only.",
        "sanitization": "Versioned outputs contain hashes, counts, metadata, and controlled vocabulary keys; no raw service-order text is emitted.",
    }
    (OUT / "g11c_no_item_signal_profile_summary_sanitized.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )

    memo = f"""# G1.1c No-Item Signal Profile Memo

G1.1c profiles the {len(frame):,} B1 service orders without consumption item signal. This is a scope audit only: it does not promote candidates and does not alter the Object Part denominator.

## Text Availability

- Non-empty `descriptionExtended`: {int(frame["has_descriptionExtended"].sum()):,} ({frame["has_descriptionExtended"].mean() * 100:.2f}%)
- Non-empty `reason`: {int(frame["has_reason"].sum()):,} ({frame["has_reason"].mean() * 100:.2f}%)
- Non-empty combined text: {int((frame["combined_text_word_count"] > 0).sum()):,} ({(frame["combined_text_word_count"] > 0).mean() * 100:.2f}%)

## Lexical High-Band Anchor

Object Part lexical_layer_v2 high-band canonical concepts were phrase-matched against `descriptionExtended + reason` for profiling only.

- High-band Object Part canonical concepts loaded: {int(terms["canonical_concept_key_vocab"].nunique()):,}
- Orders with at least one high-band Object Part anchor: {int(frame["has_high_band_object_part_anchor"].sum()):,} ({frame["has_high_band_object_part_anchor"].mean() * 100:.2f}%)
- Unique high-band concepts matched: {int(concept_profile["canonical_concept_key"].nunique() if not concept_profile.empty else 0):,}

## Governance

- No parser was introduced.
- No candidate was promoted.
- No denominator was changed.
- Versioned outputs do not emit raw order text.
"""
    (OUT / "g11c_no_item_signal_profile_memo.md").write_text(memo, encoding="utf-8")


if __name__ == "__main__":
    main()
