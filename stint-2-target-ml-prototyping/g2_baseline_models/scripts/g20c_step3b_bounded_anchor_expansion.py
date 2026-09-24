from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
from g20c_step3_semantic_grouping import (
    ACTION_TOKENS,
    ACTIVITY_SCORE_THRESHOLD,
    COMPONENT_TOKENS,
    OBJECT_PART_SCORE_THRESHOLD,
    TARGET_MARGIN,
    target_for_cluster,
)

ROOT = Path(
    "/home/adien-i7-remote/workspace/fsa_bridge_ml_feasibility/"
    "stint-2-target-ml-prototyping"
)
OUT = ROOT / "g2_baseline_models/outputs/g20_corpus_native_domain_vocab"

STEP3_VOCAB = OUT / "g20c_domain_vocabulary_sanitized.csv"
STEP3_MEMBERS = OUT / "g20c_concept_members_sanitized.csv"
STEP3_SUMMARY = OUT / "g20c_step3_grouping_summary_sanitized.csv"
DIAGNOSTIC_SAMPLE = OUT / "g20c_step3_unassigned_diagnostic_sample_sanitized.csv"

EXPANSION_SOURCE = (
    "g2_baseline_models/outputs/g20_corpus_native_domain_vocab/"
    "g20c_step3_unassigned_diagnostic_sample_sanitized.csv"
)
CONSTRUCTION_METHOD = "derived_from_corpus_inspection"
EVALUATION_EXCLUSION = "instrument_construction_g20c_step3b"

EXPANSION_FAMILIES = {
    "G20C-CONCEPT-c6d168b839ef9d": {
        "target": "Activity",
        "family": "acknowledgement_verification",
        "tokens": {"acknowledge", "acknowledged", "agreed", "ensure"},
    },
    "G20C-CONCEPT-3581c591dd5afd": {
        "target": "Activity",
        "family": "configuration_setting",
        "tokens": {"configuration", "configured", "setting", "settings"},
    },
    "G20C-CONCEPT-171ae89bfd2d21": {
        "target": "Activity",
        "family": "assessment_review",
        "tokens": {"analyzing", "assess", "assessment", "assessments", "review"},
    },
    "G20C-CONCEPT-bfd6f5fca3d412": {
        "target": "Object Part",
        "family": "locking_hardware",
        "tokens": {
            "bolts",
            "cyl",
            "door",
            "interlock",
            "lock",
            "locked",
            "locknut",
            "locks",
            "nut",
            "nuts",
            "pins",
            "shackle",
        },
    },
}

STEP3B_QA_REVIEWED = [
    {
        "concept_id": "G20C-CONCEPT-5ca42a7492f5d9",
        "canonical_label": "screws",
        "diagnostic_class": "step3b_false_promotion_review",
        "suggested_target": "",
        "disposition": "remain_unassigned",
    },
    {
        "concept_id": "G20C-CONCEPT-d6f2c241a892d6",
        "canonical_label": "bolts cim",
        "diagnostic_class": "step3b_promotion_quality_review",
        "suggested_target": "Object Part",
        "disposition": "accepted_step3b",
    },
    {
        "concept_id": "G20C-CONCEPT-f1679004e1686e",
        "canonical_label": "box",
        "diagnostic_class": "step3b_promotion_quality_review",
        "suggested_target": "Object Part",
        "disposition": "accepted_step3b",
    },
]


def stable_id(prefix: str, value: str, length: int = 14) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:length]
    return f"{prefix}-{digest}"


def token_set(term: object) -> set[str]:
    return set(str(term).lower().split())


def member_share(group: pd.DataFrame, vocabulary: set[str]) -> float:
    matches = group["candidate_term"].map(
        lambda value: bool(token_set(value) & vocabulary)
    )
    return float(matches.mean())


def expansion_register() -> pd.DataFrame:
    rows = []
    for source_concept_id, family in EXPANSION_FAMILIES.items():
        target = str(family["target"])
        for token in sorted(family["tokens"]):
            rows.append(
                {
                    "anchor_id": stable_id("G20C-STEP3B-ANCHOR", f"{target}|{token}"),
                    "target": target,
                    "anchor_kind": (
                        "corpus_inspection_action_token"
                        if target == "Activity"
                        else "corpus_inspection_component_head_token"
                    ),
                    "anchor_text": token,
                    "anchor_family": family["family"],
                    "source_concept_id": source_concept_id,
                    "source_artifact": EXPANSION_SOURCE,
                    "evidence_type": "expert_inference",
                    "construction_method": CONSTRUCTION_METHOD,
                    "evaluation_exclusion": EVALUATION_EXCLUSION,
                    "externally_transcribed": False,
                    "evaluation_text_used": False,
                    "g20_prototype_reused": False,
                }
            )
    return pd.DataFrame(rows)


def construction_exclusions(sample: pd.DataFrame) -> pd.DataFrame:
    result = sample[
        [
            "concept_id",
            "canonical_label",
            "diagnostic_class",
            "suggested_target",
            "disposition",
        ]
    ].copy()
    result = pd.concat(
        [result, pd.DataFrame(STEP3B_QA_REVIEWED)], ignore_index=True
    )
    result["excluded_from_future_evaluation_targets"] = "Activity|Object Part"
    result["eligible_for_future_evaluation"] = False
    result["evaluation_exclusion"] = EVALUATION_EXCLUSION
    result["exclusion_basis"] = (
        "concept_reviewed_for_target_support_and_threshold_decision"
    )
    result["construction_method"] = CONSTRUCTION_METHOD
    return result


def concentration_tables(
    members: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    for (target, path), group in members.groupby(["target", "path_bucket"]):
        by_concept = group.groupby("concept_id").agg(
            member_rows=("candidate_term", "size"),
            unit_mention_weight=("units_with_term", "sum"),
        )
        member_total = int(by_concept["member_rows"].sum())
        weight_total = int(by_concept["unit_mention_weight"].sum())
        for concept_id, row in by_concept.iterrows():
            surface_share = float(row["member_rows"] / member_total)
            weight_share = (
                float(row["unit_mention_weight"] / weight_total)
                if weight_total
                else 0.0
            )
            rows.append(
                {
                    "target": target,
                    "path_bucket": path,
                    "concept_id": concept_id,
                    "concept_count_in_target_path": len(by_concept),
                    "surface_variant_share": round(surface_share, 6),
                    "unit_mention_weight_share": round(weight_share, 6),
                    "surface_concentration_over_30pct": surface_share > 0.30,
                    "unit_mention_weight_over_30pct_warning": weight_share > 0.30,
                    "metric_scope": (
                        "surface_variant_share_is_step3b_gate;"
                        "unit_mention_weight_is_non_deduplicated_diagnostic;"
                        "exact_physical_unit_coverage_deferred_to_step5"
                    ),
                }
            )
    concentration = pd.DataFrame(rows)

    summary_rows = []
    for path in sorted(members["path_bucket"].unique()):
        for target in ["Activity", "Object Part", "ambiguous", "unassigned"]:
            subset = members[
                members["path_bucket"].eq(path) & members["target"].eq(target)
            ]
            c = concentration[
                concentration["path_bucket"].eq(path)
                & concentration["target"].eq(target)
            ]
            gate_applies = target in {"Activity", "Object Part"}
            summary_rows.append(
                {
                    "path_bucket": path,
                    "target": target,
                    "concepts": subset["concept_id"].nunique(),
                    "member_rows": len(subset),
                    "max_surface_variant_share": round(
                        float(c["surface_variant_share"].max()), 6
                    )
                    if not c.empty
                    else 0.0,
                    "max_unit_mention_weight_share": round(
                        float(c["unit_mention_weight_share"].max()), 6
                    )
                    if not c.empty
                    else 0.0,
                    "surface_concentration_gate_applies": gate_applies,
                    "surface_concentration_gate_pass": bool(
                        not gate_applies
                        or c.empty
                        or not c["surface_concentration_over_30pct"].any()
                    ),
                    "unit_mention_weight_over_30pct_warning": bool(
                        not c.empty
                        and c["unit_mention_weight_over_30pct_warning"].any()
                    ),
                }
            )
    return concentration, pd.DataFrame(summary_rows)


def counts_frame(vocab: pd.DataFrame, stage: str) -> pd.DataFrame:
    targets = ["Activity", "Object Part", "ambiguous", "unassigned"]
    counts = vocab["target"].value_counts()
    return pd.DataFrame(
        {
            "stage": stage,
            "target": targets,
            "concepts": [int(counts.get(target, 0)) for target in targets],
        }
    )


def main() -> None:
    vocab = pd.read_csv(STEP3_VOCAB).fillna("")
    members = pd.read_csv(STEP3_MEMBERS).fillna("")
    before_summary = pd.read_csv(STEP3_SUMMARY).fillna("")
    sample = pd.read_csv(DIAGNOSTIC_SAMPLE).fillna("")

    if len(vocab) != 256 or not vocab["concept_id"].is_unique:
        raise RuntimeError("Step 3 vocabulary integrity failed")
    expected_before = {
        "Activity": 21,
        "Object Part": 40,
        "ambiguous": 4,
        "unassigned": 191,
    }
    if vocab["target"].value_counts().to_dict() != expected_before:
        raise RuntimeError("Unexpected pre-expansion target counts")
    if len(sample) != 10 or not sample["concept_id"].is_unique:
        raise RuntimeError("Diagnostic construction sample integrity failed")

    anchors = expansion_register()
    activity_expansion = set(
        anchors.loc[anchors["target"].eq("Activity"), "anchor_text"]
    )
    object_expansion = set(
        anchors.loc[anchors["target"].eq("Object Part"), "anchor_text"]
    )
    all_action_tokens = set(ACTION_TOKENS) | activity_expansion
    all_component_tokens = set(COMPONENT_TOKENS) | object_expansion

    updated_rows = []
    target_map = {}
    for _, row in vocab.iterrows():
        concept_id = str(row["concept_id"])
        group = members[members["concept_id"].eq(concept_id)]
        action_share = member_share(group, all_action_tokens)
        component_share = member_share(group, all_component_tokens)
        target_before = str(row["target"])
        reason_before = str(row["target_assignment_reason"])
        matched_sources = sorted(
            {
                str(anchor.source_concept_id)
                for anchor in anchors.itertuples()
                if any(
                    anchor.anchor_text in token_set(term)
                    for term in group["candidate_term"]
                )
            }
        )
        if target_before == "unassigned":
            target_after, reason_after = target_for_cluster(
                float(row["activity_anchor_score"]),
                float(row["object_part_anchor_score"]),
                action_share,
                component_share,
            )
            if target_after != target_before:
                reason_after = f"step3b_corpus_inspection_{reason_after}"
        else:
            target_after = target_before
            reason_after = reason_before

        target_map[concept_id] = target_after
        result = row.to_dict()
        result.update(
            {
                "target_step3": target_before,
                "target": target_after,
                "target_assignment_reason_step3": reason_before,
                "target_assignment_reason": reason_after,
                "action_member_share_step3": row["action_member_share"],
                "action_member_share": round(action_share, 6),
                "component_head_member_share_step3": row[
                    "component_head_member_share"
                ],
                "component_head_member_share": round(component_share, 6),
                "assignment_changed_step3b": target_after != target_before,
                "step3b_construction_method": (
                    CONSTRUCTION_METHOD
                    if target_after != target_before
                    else "retained_step3_assignment"
                ),
                "step3b_source_concept_ids": "|".join(matched_sources),
            }
        )
        updated_rows.append(result)

    updated_vocab = pd.DataFrame(updated_rows)
    updated_members = members.copy()
    updated_members["target_step3"] = updated_members["target"]
    updated_members["target"] = updated_members["concept_id"].map(target_map)
    updated_members["assignment_changed_step3b"] = updated_members[
        "target"
    ].ne(updated_members["target_step3"])

    concentration, after_summary = concentration_tables(updated_members)
    exclusions = construction_exclusions(sample)

    before_counts = counts_frame(vocab, "before_step3b")
    after_counts = counts_frame(updated_vocab, "after_step3b")
    counts_comparison = before_counts.merge(
        after_counts, on="target", suffixes=("_before", "_after")
    )
    counts_comparison = counts_comparison.drop(
        columns=["stage_before", "stage_after"]
    )
    counts_comparison["delta"] = (
        counts_comparison["concepts_after"]
        - counts_comparison["concepts_before"]
    )
    assigned_total = pd.DataFrame(
        [
            {
                "target": "assigned_total",
                "concepts_before": int(
                    counts_comparison.loc[
                        counts_comparison["target"].isin(["Activity", "Object Part"]),
                        "concepts_before",
                    ].sum()
                ),
                "concepts_after": int(
                    counts_comparison.loc[
                        counts_comparison["target"].isin(["Activity", "Object Part"]),
                        "concepts_after",
                    ].sum()
                ),
            }
        ]
    )
    assigned_total["delta"] = (
        assigned_total["concepts_after"] - assigned_total["concepts_before"]
    )
    counts_comparison = pd.concat(
        [counts_comparison, assigned_total], ignore_index=True
    )

    gate_columns = [
        "path_bucket",
        "target",
        "max_surface_variant_share",
        "max_unit_mention_weight_share",
        "surface_concentration_gate_pass",
        "unit_mention_weight_over_30pct_warning",
    ]
    before_gates = before_summary[
        before_summary["surface_concentration_gate_applies"].astype(bool)
    ][gate_columns]
    after_gates = after_summary[
        after_summary["surface_concentration_gate_applies"].astype(bool)
    ][gate_columns]
    gate_comparison = before_gates.merge(
        after_gates,
        on=["path_bucket", "target"],
        suffixes=("_before", "_after"),
    )

    reviewed = set(sample["concept_id"]) | {
        str(row["concept_id"]) for row in STEP3B_QA_REVIEWED
    }
    if set(exclusions["concept_id"]) != reviewed:
        raise RuntimeError("Construction exclusion register is incomplete")
    if exclusions["eligible_for_future_evaluation"].any():
        raise RuntimeError("Reviewed concept remains evaluation-eligible")
    if set(anchors["construction_method"]) != {CONSTRUCTION_METHOD}:
        raise RuntimeError("Corpus-inspection anchors have mixed provenance")
    if anchors["externally_transcribed"].any():
        raise RuntimeError("Corpus-inspection anchors mixed with external anchors")
    if not after_summary.loc[
        after_summary["surface_concentration_gate_applies"],
        "surface_concentration_gate_pass",
    ].all():
        raise RuntimeError("Step 3b surface concentration gate failed")
    if not updated_vocab.loc[
        updated_vocab["target_step3"].ne("unassigned"),
        "assignment_changed_step3b",
    ].eq(False).all():
        raise RuntimeError("Step 3b changed a previously assigned concept")

    updated_vocab.sort_values(["target", "canonical_label"]).to_csv(
        OUT / "g20c_domain_vocabulary_step3b_sanitized.csv",
        index=False,
        lineterminator="\n",
    )
    updated_members.sort_values(
        ["target", "concept_id", "path_bucket", "candidate_term"]
    ).to_csv(
        OUT / "g20c_concept_members_step3b_sanitized.csv",
        index=False,
        lineterminator="\n",
    )
    anchors.to_csv(
        OUT / "g20c_step3b_anchor_expansion_sanitized.csv",
        index=False,
        lineterminator="\n",
    )
    exclusions.to_csv(
        OUT / "g20c_step3b_construction_exclusions_sanitized.csv",
        index=False,
        lineterminator="\n",
    )
    concentration.sort_values(["target", "path_bucket", "concept_id"]).to_csv(
        OUT / "g20c_step3b_concentration_by_target_path_sanitized.csv",
        index=False,
        lineterminator="\n",
    )
    after_summary.to_csv(
        OUT / "g20c_step3b_grouping_summary_sanitized.csv",
        index=False,
        lineterminator="\n",
    )
    counts_comparison.to_csv(
        OUT / "g20c_step3b_before_after_target_counts_sanitized.csv",
        index=False,
        lineterminator="\n",
    )
    gate_comparison.to_csv(
        OUT / "g20c_step3b_before_after_concentration_sanitized.csv",
        index=False,
        lineterminator="\n",
    )

    changed = updated_vocab[updated_vocab["assignment_changed_step3b"]]
    changed[
        [
            "concept_id",
            "canonical_label",
            "target_step3",
            "target",
            "target_assignment_reason",
            "activity_anchor_score",
            "object_part_anchor_score",
            "action_member_share_step3",
            "action_member_share",
            "component_head_member_share_step3",
            "component_head_member_share",
            "step3b_source_concept_ids",
            "step3b_construction_method",
        ]
    ].sort_values(["target", "canonical_label"]).to_csv(
        OUT / "g20c_step3b_assignment_changes_sanitized.csv",
        index=False,
        lineterminator="\n",
    )
    result = {
        "clusters_regrouped": False,
        "thresholds_lowered": False,
        "activity_score_threshold": ACTIVITY_SCORE_THRESHOLD,
        "object_part_score_threshold": OBJECT_PART_SCORE_THRESHOLD,
        "target_margin": TARGET_MARGIN,
        "new_anchor_construction_method": CONSTRUCTION_METHOD,
        "diagnostic_sample_concepts_excluded": len(sample),
        "step3b_qa_concepts_excluded": len(STEP3B_QA_REVIEWED),
        "reviewed_concepts_excluded_from_future_evaluation": len(exclusions),
        "concept_assignments_changed": len(changed),
        "assigned_concepts_before": int(assigned_total["concepts_before"].iloc[0]),
        "assigned_concepts_after": int(assigned_total["concepts_after"].iloc[0]),
        "before_counts": vocab["target"].value_counts().to_dict(),
        "after_counts": updated_vocab["target"].value_counts().to_dict(),
        "max_surface_concentration_before": round(
            float(before_gates["max_surface_variant_share"].max()), 6
        ),
        "max_surface_concentration_after": round(
            float(after_gates["max_surface_variant_share"].max()), 6
        ),
        "all_surface_concentration_gates_pass": True,
    }
    (OUT / "g20c_step3b_summary_sanitized.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )

    memo = f"""# G2.0c Step 3b - Bounded Anchor Expansion

Step 3 grouping remained frozen at 256 concepts. No cluster was rebuilt and no
threshold was lowered. Only concepts that were `unassigned` in Step 3 were
re-evaluated with the bounded corpus-inspection anchor families.

All {len(anchors)} new lexical anchors carry
`construction_method={CONSTRUCTION_METHOD}` and remain separate from externally
transcribed anchors. The 10 diagnostic concepts plus the 3 additional concepts
inspected during Step 3b QA are registered with
`eligible_for_future_evaluation=false` for Activity and Object Part.

```
before  {vocab['target'].value_counts().to_dict()}
after   {updated_vocab['target'].value_counts().to_dict()}
changed {len(changed)} concept assignments
```

The maximum target-by-path surface concentration changed from
{before_gates['max_surface_variant_share'].max():.2%} to
{after_gates['max_surface_variant_share'].max():.2%}. All six blocking surface
concentration gates remain at or below 30%. Non-deduplicated unit-mention weights
remain diagnostic only; exact physical-unit concentration is deferred to Step 5.
"""
    (OUT / "g20c_step3b_bounded_anchor_expansion_memo.md").write_text(
        memo, encoding="utf-8"
    )

    print(counts_comparison.to_string(index=False))
    print(gate_comparison.to_string(index=False))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
