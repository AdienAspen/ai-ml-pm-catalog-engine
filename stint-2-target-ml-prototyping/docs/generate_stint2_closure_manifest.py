import csv
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TABLE = ROOT / "g1_actionable_zeros/g1_denominator_update/outputs/f6_final_denominators_sanitized.csv"
OUTPUT = ROOT / "docs/stint2_closure_manifest.md"


def rel(path):
    return Path(os.path.relpath(path, ROOT)).as_posix()


def entry(code, purpose, memo, tables, internal, status):
    if memo:
        assert (ROOT / memo).exists(), memo
    for table in tables:
        assert (ROOT / table).exists(), table
    for path in internal:
        assert (ROOT / path).exists(), path
    return (code, purpose, memo or "n/a", "; ".join(tables) or "n/a", "; ".join(internal) or "n/a", status)


def main():
    with TABLE.open(newline="", encoding="utf-8-sig") as handle:
        f6 = list(csv.DictReader(handle))
    assert len(f6) == 83
    sources = sorted({row["source_file"] for row in f6})
    assert all((ROOT / source).exists() for source in sources)
    b = "g2_baseline_models/outputs/"
    rows = [
        entry("STINT1-F3", "Path A estimated-event grouping and 1.66x compression", "../stint-1-evidence-ground-truth/phase_3_path_a_faultcodes/outputs/f354_snapshot_dedup_memo.md", ["../stint-1-evidence-ground-truth/phase_3_path_a_faultcodes/outputs/f354_snapshot_dedup_summary_sanitized.json"], [], "frozen; episode reconstruction contingent"),
        entry("STINT1-F4", "B2 date-sensitive and date-insensitive snapshot grouping", "../stint-1-evidence-ground-truth/phase_4_path_b_xlsx/outputs/b2_snapshot_dedup/b22_snapshot_dedup_memo.md", ["../stint-1-evidence-ground-truth/phase_4_path_b_xlsx/outputs/b2_snapshot_dedup/b22_snapshot_dedup_summary_sanitized.json", "../stint-1-evidence-ground-truth/phase_4_path_b_xlsx/outputs/b25_grouping_refinement/b25_grouping_refinement_summary_sanitized.json"], [], "frozen; episode reconstruction contingent"),
        entry("STINT1-F6", "Original target-by-path denominator matrix", "../stint-1-evidence-ground-truth/phase_6_denominators/outputs/f6_committee_closure_table_memo.md", ["../stint-1-evidence-ground-truth/phase_6_denominators/outputs/f6_committee_closure_denominator_table_sanitized.csv"], [], "frozen"),
        entry("G0.0-G0.2", "Inventory, row recovery, protocol and stratified sample", "g0_independent_evaluation/outputs/annotation_samples/g02_sampling_memo.md", ["g0_independent_evaluation/outputs/annotation_samples/g02_annotation_sample_manifest_sanitized.csv"], ["g0_independent_evaluation/internal"], "closed historical"),
        entry("G0.4", "Three-target evaluation_set_v1 and training exclusion", "artifacts/evaluation_sets/evaluation_set_v1/evaluation_set_v1_limitations.md", ["artifacts/evaluation_sets/evaluation_set_v1/evaluation_set_v1_registration_summary.json", "artifacts/evaluation_sets/evaluation_set_v1/evaluation_set_v1_training_exclusion_keys.csv"], [], "frozen; not amended"),
        entry("G0.4b", "Damage and Activity separate diagnostic evaluation_set_v2", "artifacts/evaluation_sets/evaluation_set_v2/evaluation_set_v2_limitations.md", ["artifacts/evaluation_sets/evaluation_set_v2/evaluation_set_v2_registration_summary.json", "artifacts/evaluation_sets/evaluation_set_v2/evaluation_set_v1_v2_training_exclusion_union.csv", "artifacts/evaluation_sets/evaluation_set_v2/evaluation_set_v2_agreement_register.csv"], ["g2_baseline_models/internal/g20e_g20f_blind_catalogue_code_annotation/responses"], "registered diagnostic; not final held-out"),
        entry("g01-v2", "Operational annotation protocol closure", "g0_independent_evaluation/outputs/annotation_protocol/g01_v2_closure_memo.md", [], ["g2_baseline_models/internal/g20e_g20f_blind_catalogue_code_annotation"], "closed diagnostic"),
        entry("G1.1", "Consumption-to-Catalog B crosswalk", "g1_actionable_zeros/g11_object_part_crosswalk/outputs/g11_coverage_memo.md", [], [], "closed expert inference"),
        entry("G1.1f", "Profile-constrained crosswalk category partition", "g1_actionable_zeros/g11_object_part_crosswalk/outputs/g11f_profile_constrained/g11f_memo.md", ["g1_actionable_zeros/g11_object_part_crosswalk/outputs/g11f_profile_constrained/g11f_order_categories_sanitized.csv", "g1_actionable_zeros/g11_object_part_crosswalk/outputs/g11f_profile_constrained/g11f_pair_categories_sanitized.csv"], [], "closed candidate, not precision"),
        entry("G1.2", "Turbine FLOC alignment", "g1_actionable_zeros/g12_floc_alignment/outputs/g12_floc_alignment_memo.md", [], [], "closed at turbine level"),
        entry("C1/F6", "Final figure-by-metric and source register", "g1_actionable_zeros/g1_denominator_update/outputs/f6_final_memo.md", ["g1_actionable_zeros/g1_denominator_update/outputs/f6_final_denominators_sanitized.csv"], [], "bookkeeping complete"),
        entry("C1b/G2.0k.6", "Order-weighted shared-description shares of component and PMMUWW sets", "g2_baseline_models/outputs/g20k_component_lift/g20k6_memo.md", ["g1_actionable_zeros/g1_denominator_update/outputs/c1b_g20k6_shared_descriptions_sanitized.csv"], ["g2_baseline_models/internal/g20k_component_lift/g20k6_detail.csv"], "diagnostic, derived; no denominator change"),
        entry("C1b/G1.1f", "Profile agreement under chosen-code, identical-description and equal-score tests", "g1_actionable_zeros/g11_object_part_crosswalk/outputs/g11f_profile_constrained/g11f_memo.md", ["g1_actionable_zeros/g1_denominator_update/outputs/c1b_g11f_profile_agreement_sanitized.csv"], ["g1_actionable_zeros/g11_object_part_crosswalk/internal/g11f_profile_constrained/g11f_detail.csv"], "diagnostic, derived; 248/872 cohorts"),
        entry("G2.0", "Corpus-informed prototype baseline and diagnostic calibration", b + "g20_zero_shot_prototype_baseline/g20_zero_shot_baseline_memo.md", [b + "g20_zero_shot_prototype_baseline/g20_object_part_b1_overlap_agreement_summary_sanitized.json"], [], "diagnostic only"),
        entry("G2.0b/C3", "Target-heading leakage count, masking and extracted-span validation", "g0_independent_evaluation/outputs/g20_target_leakage_quantification/g20b_leakage_validation_memo.md", ["g0_independent_evaluation/outputs/g20_target_leakage_quantification/g20b_leakage_validation_sanitized.csv"], ["g0_independent_evaluation/internal/g20_target_leakage_quantification/g20b_leakage_validation_internal.csv"], "13 captured spans terminal; masking retained"),
        entry("G2.0c", "Corpus-native vocabulary construction and source contrast", b + "g20_corpus_native_domain_vocab/g20c_memo.md", [b + "g20_corpus_native_domain_vocab/g20c_coverage_contrast_sanitized.csv"], [], "closed; target exposure limits recorded"),
        entry("G2.0d", "Conservative lexical floor", b + "g20d_catalogue_free_coverage/g20d_memo.md", [], [], "provisional detector floor"),
        entry("G2.0d2", "Broader semantic estimate against frozen external vocabulary", b + "g20d2_semantic_reference_coverage/g20d2_memo.md", [b + "g20d2_semantic_reference_coverage/g20d2_detector_comparison_sanitized.csv"], [], "descriptive; no code accuracy"),
        entry("G2.0d3", "Symptom threshold sweep without threshold selection", b + "g20d3_symptom_threshold_review/g20d3_memo.md", [], [], "diagnostic curve only"),
        entry("G2.0e", "Activity blind catalogue-code round", b + "g20ef_blind_catalogue_code_annotation/g20e_closure_memo.md", [b + "g20ef_blind_catalogue_code_annotation/g20e_activity_agreement_v21_sanitized.csv", b + "g20ef_blind_catalogue_code_annotation/g20e_activity_v21_response_confusion_matrix_sanitized.csv", b + "g20ef_blind_catalogue_code_annotation/g20e_activity_v21_response_per_class_agreement_sanitized.csv"], ["g2_baseline_models/internal/g20e_g20f_blind_catalogue_code_annotation/responses/activity"], "closed diagnostic g01-v2.1"),
        entry("G2.0f", "Damage blind group and code round", b + "g20ef_blind_catalogue_code_annotation/g20f_closure_memo.md", [b + "g20ef_blind_catalogue_code_annotation/g20f_damage_agreement_sanitized.csv", b + "g20ef_blind_catalogue_code_annotation/g20f_damage_group_confusion_matrix_sanitized.csv", b + "g20ef_blind_catalogue_code_annotation/g20f_damage_group_code_confusion_matrix_sanitized.csv", b + "g20ef_blind_catalogue_code_annotation/g20f_damage_group_per_class_agreement_sanitized.csv", b + "g20ef_blind_catalogue_code_annotation/g20f_damage_group_code_per_class_agreement_sanitized.csv"], ["g2_baseline_models/internal/g20e_g20f_blind_catalogue_code_annotation/responses/damage"], "closed diagnostic g01-v2"),
        entry("G2.0h", "Deterministic nearest-ancestor profile inheritance", b + "g20h_profile_inheritance/g20h_memo.md", [b + "g20h_profile_inheritance/g20h_profile_inheritance_sanitized.csv"], [], "closed structural"),
        entry("G2.0i", "Site-aware component-node/profile funnel", b + "g20i_component_resolution/g20i_memo.md", [b + "g20i_component_resolution/g20i_profile_funnel_sanitized.csv"], [], "candidate resolution, circularity declared"),
        entry("G2.0i-consensus", "Shared-profile resolution with ambiguous node", b + "g20i_profile_consensus/g20i_profile_consensus_memo.md", [b + "g20i_profile_consensus/g20i_profile_consensus_by_order_sanitized.csv"], [], "closed profile-only"),
        entry("G2.0j", "Domain presence versus profile/catalogue code reachability", b + "g20j_catalogue_code_coverage/g20j_memo.md", [b + "g20j_catalogue_code_coverage/g20j_noncoverage_partition_sanitized.csv"], [], "descriptive candidate only"),
        entry("G2.0k", "Component lift and first-failing-link partition", b + "g20k_component_lift/g20k3_memo.md", [b + "g20k_component_lift/g20k3_partition_summary_sanitized.csv"], [], "closed diagnostic partition"),
        entry("G2.0k.4-.7", "Tie structure, profile relation, crosswalk membership and implied component", b + "g20k_component_lift/g20k7_memo.md", [b + "g20k_component_lift/g20k4_tie_structure_summary_sanitized.csv", b + "g20k_component_lift/g20k5_profile_identity_sanitized.csv", b + "g20k_component_lift/g20k6_crosswalk_membership_sanitized.csv", b + "g20k_component_lift/g20k7_coverage_sanitized.csv"], [], "closed diagnostic"),
        entry("CHAIN", "Frozen G2.0i scoring, filters and persistence specification", "docs/G2.0i-resolution-chain-code-spec.md", [], [], "frozen method reference"),
    ]
    out = ["# STINT_2 closure manifest", "", "This is the citation index for C1-C4. Figures are cited through the exact `source_file` in the F6 register; the step entries below identify interpretive memos, supporting tables and private material by path only. No private text is reproduced.", "", "## Exact C1 figure sources", ""]
    out += [f"- `{source}`" for source in sources]
    out += ["", "## Step registry", "", "| Step | Purpose | Memo | Sanitised tables | Internal path only | Status |", "|---|---|---|---|---|---|"]
    for row in rows:
        out.append("| " + " | ".join(f"`{cell}`" if index in (2, 3, 4) else cell for index, cell in enumerate(row)) + " |")
    out += ["", "## Use rules", "", "- MAT alone is contractual. All other volumes are structural, diagnostic or proxy as specified in the F6 row.", "- A/B2 source units remain contingent on episode reconstruction; never aggregate across paths or levels.", "- `internal/` entries are location references only. They are not versioned evidence and must not be reproduced in documentation.", "- A cited number must resolve to exactly one F6 `source_file`, metric, unit, universe and condition.", ""]
    OUTPUT.write_text("\n".join(out), encoding="utf-8")
    print({"entries": len(rows), "c1_source_files": len(sources), "output": rel(OUTPUT)})


if __name__ == "__main__":
    main()
