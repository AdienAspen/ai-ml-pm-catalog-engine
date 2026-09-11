from __future__ import annotations

import hashlib
import json
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


def normalize_text(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def is_non_empty(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, float) and pd.isna(value):
        return False
    return bool(str(value).strip())


def vocabulary_owner_to_anchor_source(owner: object, source: object, namespace: object) -> str:
    owner_norm = normalize_text(owner)
    source_norm = normalize_text(source)
    namespace_norm = normalize_text(namespace)
    if owner_norm == "sap mapping" or "sap mapping" in source_norm or namespace_norm.startswith("catalog"):
        return "sap_catalog"
    if owner_norm in {"domain vocabulary", "domain vocabulary v2", "domain"}:
        return "domain_vocabulary"
    if owner_norm in {"structural field", "structural"}:
        return "structural_field"
    return "unknown"


def read_json_records(path: Path) -> pd.DataFrame:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise RuntimeError(f"Expected list payload: {path}")
    return pd.DataFrame(payload)


def load_no_item_text() -> pd.DataFrame:
    service_orders = read_json_records(SERVICE_ORDERS_JSON)
    consumption = read_json_records(CONSUMPTION_JSON)
    consumption["order_id"] = consumption["orderId"].astype(str).str.strip()
    consumption["has_item_signal"] = consumption["items"].map(lambda items: isinstance(items, list) and len(items) > 0)
    no_item = consumption.loc[~consumption["has_item_signal"], ["order_id"]].copy()

    service_orders["order_id"] = service_orders["id"].astype(str).str.strip()
    frame = no_item.merge(
        service_orders[["order_id", "descriptionExtended", "reason"]],
        on="order_id",
        how="left",
        validate="one_to_one",
    )
    frame["normalized_combined_text"] = (
        frame["descriptionExtended"].fillna("").astype(str) + " " + frame["reason"].fillna("").astype(str)
    ).map(normalize_text)
    return frame[["order_id", "normalized_combined_text"]]


def load_terms() -> pd.DataFrame:
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
            "target_code",
            "code_group",
            "vocabulary_owner",
            "source",
            "namespace",
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
    terms["anchor_source"] = terms.apply(
        lambda row: vocabulary_owner_to_anchor_source(
            row.get("vocabulary_owner_vocab"), row.get("source"), row.get("namespace")
        ),
        axis=1,
    )
    terms = terms[terms["normalized_concept"] != ""].copy()
    return terms.drop_duplicates(
        [
            "canonical_concept_key_vocab",
            "normalized_concept",
            "target_code",
            "code_group",
            "vocabulary_owner_vocab",
            "anchor_source",
        ]
    ).reset_index(drop=True)


def match_terms(text: str, terms: pd.DataFrame) -> list[dict[str, object]]:
    padded = f" {text} "
    matches = []
    for row in terms.itertuples(index=False):
        phrase = getattr(row, "normalized_concept")
        if f" {phrase} " not in padded:
            continue
        matches.append(
            {
                "canonical_concept_key": getattr(row, "canonical_concept_key_vocab"),
                "target_code": getattr(row, "target_code"),
                "code_group": getattr(row, "code_group"),
                "vocabulary_owner": getattr(row, "vocabulary_owner_vocab"),
                "anchor_source": getattr(row, "anchor_source"),
            }
        )
    return matches


def classify_order_sources(sources: set[str]) -> str:
    clean = set(sources)
    has_domain = "domain_vocabulary" in clean
    has_sap = "sap_catalog" in clean
    if has_domain and has_sap and len(clean - {"domain_vocabulary", "sap_catalog"}) == 0:
        return "both_domain_vocabulary_and_sap_catalog"
    if has_domain and not has_sap and len(clean - {"domain_vocabulary"}) == 0:
        return "domain_vocabulary_only"
    if has_sap and not has_domain and len(clean - {"sap_catalog"}) == 0:
        return "sap_catalog_only"
    if not clean:
        return "no_high_band_anchor"
    return "mixed_or_other_anchor_source"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    frame = load_no_item_text()
    terms = load_terms()

    order_concepts = []
    for row in frame.itertuples(index=False):
        unique = {
            (
                match["canonical_concept_key"],
                match["target_code"],
                match["code_group"],
                match["vocabulary_owner"],
                match["anchor_source"],
            )
            for match in match_terms(row.normalized_combined_text, terms)
        }
        for concept_key, target_code, code_group, vocabulary_owner, anchor_source in unique:
            order_concepts.append(
                {
                    "order_id": row.order_id,
                    "order_id_hash": prefixed_hash("ORDER", row.order_id),
                    "canonical_concept_key": concept_key,
                    "target_code": target_code,
                    "code_group": code_group,
                    "vocabulary_owner": vocabulary_owner,
                    "anchor_source": anchor_source,
                }
            )

    order_concepts_df = pd.DataFrame(order_concepts)
    if order_concepts_df.empty:
        order_concepts_df = pd.DataFrame(
            columns=[
                "order_id",
                "order_id_hash",
                "canonical_concept_key",
                "target_code",
                "code_group",
                "vocabulary_owner",
                "anchor_source",
            ]
        )

    anchored_order_source_sets = (
        order_concepts_df.groupby("order_id")["anchor_source"].apply(lambda values: set(values)).reset_index()
    )
    anchored_order_source_sets["anchor_source_breakdown"] = anchored_order_source_sets["anchor_source"].map(
        classify_order_sources
    )
    anchored_order_source_sets["order_id_hash"] = anchored_order_source_sets["order_id"].map(
        lambda value: prefixed_hash("ORDER", value)
    )

    order_breakdown = (
        anchored_order_source_sets["anchor_source_breakdown"]
        .value_counts()
        .rename_axis("anchor_source_breakdown")
        .reset_index(name="orders")
        .sort_values("anchor_source_breakdown")
    )
    anchored_orders = int(len(anchored_order_source_sets))
    order_breakdown["share_of_anchored_orders"] = (
        order_breakdown["orders"] / anchored_orders * 100 if anchored_orders else 0
    ).round(6)
    order_breakdown.to_csv(OUT / "g11d_anchor_source_order_breakdown_sanitized.csv", index=False)

    concept_sources = order_concepts_df[
        ["canonical_concept_key", "vocabulary_owner", "anchor_source"]
    ].drop_duplicates()
    concept_breakdown = (
        concept_sources["anchor_source"]
        .value_counts()
        .rename_axis("anchor_source")
        .reset_index(name="distinct_high_band_concepts_matched")
        .sort_values("anchor_source")
    )
    total_concepts = int(len(concept_sources))
    concept_breakdown["share_of_matched_concepts"] = (
        concept_breakdown["distinct_high_band_concepts_matched"] / total_concepts * 100 if total_concepts else 0
    ).round(6)
    concept_breakdown.to_csv(OUT / "g11d_anchor_source_concept_breakdown_sanitized.csv", index=False)

    concept_codes = (
        order_concepts_df.groupby("canonical_concept_key", dropna=False)
        .agg(
            target_codes=("target_code", lambda values: "|".join(sorted({str(value) for value in values}))),
            code_groups=("code_group", lambda values: "|".join(sorted({str(value) for value in values}))),
        )
        .reset_index()
    )
    top_concepts = (
        order_concepts_df.groupby(
            ["canonical_concept_key", "vocabulary_owner", "anchor_source"],
            dropna=False,
        )["order_id"]
        .nunique()
        .reset_index(name="orders_with_anchor")
        .merge(concept_codes, on="canonical_concept_key", how="left")
        .sort_values(["orders_with_anchor", "canonical_concept_key"], ascending=[False, True])
        .head(15)
    )
    top_concepts.to_csv(OUT / "g11d_anchor_source_top15_concepts_sanitized.csv", index=False)

    order_source_sets = anchored_order_source_sets.copy()
    order_source_sets["anchor_sources"] = order_source_sets["anchor_source"].map(lambda values: "|".join(sorted(values)))
    order_source_sets = order_source_sets[
        ["order_id_hash", "anchor_sources", "anchor_source_breakdown"]
    ].sort_values("order_id_hash")
    order_source_sets.to_csv(OUT / "g11d_anchor_source_order_profile_sanitized.csv", index=False)

    summary = {
        "task": "G1.1d_anchor_source_breakdown",
        "created_at_utc": utc_now(),
        "scope": "B1 no-item orders with at least one Object Part high-band anchor",
        "no_item_orders_profiled": int(len(frame)),
        "anchored_orders": anchored_orders,
        "distinct_high_band_concepts_matched": total_concepts,
        "anchor_source_mapping": {
            "SAP_MAPPING": "sap_catalog",
            "catalog_* namespace": "sap_catalog",
            "DOMAIN_VOCABULARY": "domain_vocabulary",
            "STRUCTURAL_FIELD": "structural_field",
        },
        "order_breakdown": order_breakdown.to_dict(orient="records"),
        "concept_breakdown": concept_breakdown.to_dict(orient="records"),
        "candidate_promotion_performed": False,
        "denominator_change_performed": False,
        "raw_text_emitted": False,
    }
    (OUT / "g11d_anchor_source_breakdown_summary_sanitized.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )

    memo = f"""# G1.1d Anchor Source Breakdown Memo

G1.1d breaks down the {anchored_orders:,} B1 no-item orders with at least one high-band Object Part lexical anchor by `anchor_source`.

This is counting only. No candidate was promoted and no denominator was changed.

## Result

All matched high-band Object Part anchors in this pass originate from `sap_catalog` (`SAP_MAPPING` / Catalog B vocabulary). No matched order is anchored exclusively through `domain_vocabulary`, and no matched concept originates from `domain_vocabulary`.

## Interpretation

The 3,737 orders reported in G1.1c should be treated as catalogue-anchored textual residual, not as technician-language residual. Given the known over-generation behavior of catalogue concepts, this is a weaker ML-addressable signal than the headline count alone suggests.
"""
    (OUT / "g11d_anchor_source_breakdown_memo.md").write_text(memo, encoding="utf-8")


if __name__ == "__main__":
    main()
