"""Prune restricted variants from frozen clusters, then reconcile downstream runs."""

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd
from g20c_lexical_safety import POLICY, assert_safe_terms, restricted_match
from g20c_step3_semantic_grouping import has_action_token, has_component_token
from g20c_step3b_bounded_anchor_expansion import concentration_tables

ROOT = Path(__file__).resolve().parents[2]
REL = Path("g2_baseline_models/outputs/g20_corpus_native_domain_vocab")
OUT = ROOT / REL
BACKUP = ROOT / "g2_baseline_models/internal/g20c_pre_release_v083"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(name, old=False):
    return pd.read_csv((BACKUP / REL if old else OUT) / name).fillna("")


def save(frame, name):
    frame.to_csv(OUT / name, index=False)
    assert len(read(name)) == len(frame)


def prune():
    original = read("g20c_candidate_terms_sanitized.csv", old=True)
    current = read("g20c_candidate_terms_sanitized.csv")
    expected = original[~original.candidate_term.map(restricted_match)]
    key = ["path_bucket", "term_hash"]
    pd.testing.assert_frame_equal(
        expected[current.columns.intersection(original.columns)].reset_index(drop=True),
        current[current.columns.intersection(original.columns)].reset_index(drop=True),
        check_dtype=False,
    )
    assert len(original) - len(current) == 39 and len(current) == 79330
    for name in [
        "g20c_step1_normalization_audit_sanitized.csv",
        "g20c_step1_universe_register_sanitized.csv",
    ]:
        pd.testing.assert_frame_equal(read(name, True), read(name), check_dtype=False)
    filtered = read("g20c_filtered_terms_sanitized.csv")
    allowed = set(map(tuple, filtered[key].to_numpy()))
    members = read("g20c_concept_members_sanitized.csv", True)
    retained = members.apply(lambda row: (row.path_bucket, row.term_hash) in allowed, axis=1)
    removed = members[~retained]
    assert len(removed) == 16 and removed.candidate_term.map(restricted_match).all()
    members = members[retained].copy()
    assert len(members) == 24405 and len(filtered) == 24825
    decisions = read("g20c_step3_grouping_decisions_sanitized.csv", True)
    decisions = decisions[
        decisions.apply(lambda row: (row.path_bucket, row.term_hash) in allowed, axis=1)
    ].copy()
    assert len(decisions) == len(filtered)
    vocab = read("g20c_domain_vocabulary_sanitized.csv", True)
    assert set(members.concept_id) == set(vocab.concept_id)
    for idx, concept in vocab.iterrows():
        group = members[members.concept_id.eq(concept.concept_id)]
        assert concept.canonical_label in set(group.candidate_term)
        variants = (
            group.sort_values(
                ["units_with_term", "member_centroid_similarity", "candidate_term"],
                ascending=[False, False, True],
            )
            .candidate_term.drop_duplicates()
            .head(20)
        )
        for column, value in {
            "member_rows": len(group),
            "distinct_surface_variants": group.candidate_term.nunique(),
            "paths_present": "|".join(sorted(set(group.path_bucket))),
            "top_surface_variants": "|".join(variants),
            "action_member_share": round(group.candidate_term.map(has_action_token).mean(), 6),
            "component_head_member_share": round(
                group.candidate_term.map(has_component_token).mean(), 6
            ),
            "mean_member_centroid_similarity": round(group.member_centroid_similarity.mean(), 6),
            "minimum_member_centroid_similarity": round(group.member_centroid_similarity.min(), 6),
        }.items():
            vocab.at[idx, column] = value
    for frame in (members, decisions, vocab):
        frame["release_sanitization_policy"] = POLICY
        frame["cluster_fit_scope"] = "historical_pre_release_fit_no_reclustering"
        frame["concept_id_policy"] = "stable_original_ids_after_member_pruning"
    assert_safe_terms(members.candidate_term)
    assert_safe_terms(vocab.canonical_label)
    assert_safe_terms(vocab.top_surface_variants)
    concentration, summary = concentration_tables(members)
    concentration.metric_scope = concentration.metric_scope.str.replace("step3b_gate", "step3_gate")
    for frame in (concentration, summary):
        frame["release_sanitization_policy"] = POLICY
    save(vocab, "g20c_domain_vocabulary_sanitized.csv")
    save(members, "g20c_concept_members_sanitized.csv")
    save(decisions, "g20c_step3_grouping_decisions_sanitized.csv")
    save(concentration, "g20c_step3_concentration_by_target_path_sanitized.csv")
    save(summary, "g20c_step3_grouping_summary_sanitized.csv")
    selection = read("g20c_step3_cluster_selection_sanitized.csv", True)
    selection["measurement_scope"] = "historical_pre_release_fit_not_recomputed"
    save(selection, "g20c_step3_cluster_selection_sanitized.csv")
    summary_path = OUT / "g20c_step3_grouping_summary_sanitized.json"
    data = json.loads((BACKUP / REL / summary_path.name).read_text())
    data.update(
        input_terms=len(filtered),
        grouped_member_rows=len(members),
        release_sanitization_policy=POLICY,
        removed_member_rows=16,
        original_fit_input_terms=24841,
        cluster_refitted=False,
        centroid_similarity_scope="original_fit_centroids_retained",
        target_assignment_scope="original_assignments_retained_step3b_revalidated",
    )
    summary_path.write_text(json.dumps(data, indent=2) + "\n")
    dropped = original[original.candidate_term.map(restricted_match)][
        ["path_bucket", "term_hash", "ngram_length", "units_with_term"]
    ].copy()
    dropped = dropped.merge(
        removed[key + ["concept_id", "target"]], on=key, how="left", validate="one_to_one"
    ).fillna("")
    dropped["reason"] = "restricted_lexical_content_removed_no_raw_value_emitted"
    dropped["lexical_safety_policy"] = POLICY
    dropped["raw_operational_values_emitted"] = False
    save(dropped, "g20c_release_removed_terms_sanitized.csv")
    note = (
        "\n## Release sanitization correction\n\n"
        "The original six-token guard was incomplete. The broader local restricted-term "
        "policy removes 39 path-term candidates and 16 clustered variants. Current counts "
        "are 79,330 candidates, 24,825 filtered rows and 24,405 members. All 256 concept IDs "
        "and canonical labels remain stable. Member statistics and concentration are "
        "recomputed; original fitted centers, silhouette and target scores are historical, "
        "not a claim of a fresh clean fit. No restricted variant remains usable as an anchor. "
        "Step 3b, mapping and unit coverage are rerun separately. See the release "
        "reconciliation report for current results.\n"
    )
    for name in [
        "g20c_step3_semantic_grouping_memo.md",
        "g20c_step3_unassigned_diagnostic_memo.md",
    ]:
        (OUT / name).write_text((BACKUP / REL / name).read_text() + note)
    print("PRUNED: 39 candidates; 16 members; 256 stable IDs; unchanged exclusions")


def finalize():
    old_vocab = read("g20c_domain_vocabulary_step3b_sanitized.csv", True)
    vocab = read("g20c_domain_vocabulary_step3b_sanitized.csv")
    pd.testing.assert_frame_equal(
        old_vocab[["concept_id", "canonical_label", "target"]]
        .sort_values("concept_id")
        .reset_index(drop=True),
        vocab[["concept_id", "canonical_label", "target"]]
        .sort_values("concept_id")
        .reset_index(drop=True),
    )
    name = "g20c_step3b_construction_exclusions_sanitized.csv"
    pd.testing.assert_frame_equal(read(name, True), read(name))
    for name in [
        "g20c_vocabulary_to_catalogue_map_sanitized.csv",
        "g20c_catalogue_gaps_sanitized.csv",
        "g20c_step4_mapping_summary_sanitized.csv",
    ]:
        pd.testing.assert_frame_equal(read(name, True), read(name), check_exact=False, atol=1e-6)
    keys = ["universe", "target", "path_bucket"]
    old = read("g20c_coverage_contrast_sanitized.csv", True).set_index(keys)
    new = read("g20c_coverage_contrast_sanitized.csv").set_index(keys)
    unit_keys = ["unit_key_hash", "target", "path_bucket"]
    old_units = read("g20c_step5_unit_coverage_sanitized.csv", True)
    new_units = read("g20c_step5_unit_coverage_sanitized.csv")
    exposure = old_units[old_units.reviewed_concept_exposure][
        unit_keys + ["reviewed_concept_ids"]
    ].merge(
        new_units[unit_keys + ["reviewed_concept_exposure"]], on=unit_keys, validate="one_to_one"
    )
    preserved = exposure[~exposure.reviewed_concept_exposure].copy()
    preserved["eligible_for_future_evaluation"] = False
    preserved["exclusion_basis"] = "historical_instrument_exposure_not_revoked_by_sanitization"
    preserved["raw_operational_values_emitted"] = False
    save(preserved, "g20c_release_preserved_evaluation_exclusions_sanitized.csv")
    rows = []
    for index, row in new.iterrows():
        result = dict(zip(keys, index))
        for metric in [
            "units_with_domain_anchor",
            "sap_catalog_only",
            "no_anchor",
            "domain_vocabulary_top_concept_share",
            "units_touching_reviewed_concepts",
        ]:
            result[metric + "_before"] = old.loc[index, metric]
            result[metric + "_after"] = row[metric]
            result[metric + "_delta"] = row[metric] - old.loc[index, metric]
        result["raw_operational_values_emitted"] = False
        result = {
            key: value.item() if hasattr(value, "item") else value for key, value in result.items()
        }
        rows.append(result)
    save(pd.DataFrame(rows), "g20c_release_coverage_reconciliation_sanitized.csv")
    count_rows = []
    for name in [
        "g20c_candidate_terms_sanitized.csv",
        "g20c_filtered_terms_sanitized.csv",
        "g20c_concept_members_sanitized.csv",
        "g20c_concept_members_step3b_sanitized.csv",
    ]:
        for path, group in read(name).groupby("path_bucket"):
            before = int(read(name, True).path_bucket.eq(path).sum())
            count_rows.append(
                dict(
                    artifact=name,
                    path_bucket=path,
                    before=before,
                    after=len(group),
                    delta=len(group) - before,
                    raw_operational_values_emitted=False,
                )
            )
    save(pd.DataFrame(count_rows), "g20c_release_count_reconciliation_sanitized.csv")
    provenance = []
    for path in sorted(OUT.iterdir()):
        before = BACKUP / REL / path.name
        if before.is_file():
            provenance.append(
                dict(
                    artifact=path.name,
                    before_sha256=sha(before),
                    after_sha256=sha(path),
                    changed=sha(before) != sha(path),
                )
            )
    save(pd.DataFrame(provenance), "g20c_release_hash_reconciliation_sanitized.csv")
    summary = dict(
        policy=POLICY,
        candidates_before=79369,
        candidates_after=79330,
        filtered_before=24841,
        filtered_after=24825,
        members_before=24421,
        members_after=24405,
        concepts=256,
        assigned_concepts=67,
        concept_ids_and_targets_unchanged=True,
        construction_exclusions_unchanged=True,
        catalogue_mapping_unchanged=True,
        clean_refit_performed=False,
        normalization_unchanged=True,
        limitation="Historical clustering geometry is retained; this is member pruning, not a clean refit.",
        repaired_raw_value_cells=142,
        affected_original_files=6,
        excluded_variant_candidate_emission_prevented=True,
        evaluation_set_modified=False,
        f6_modified=False,
        g2_closed=False,
        original_backups="ignored_internal_directory_700_files_600",
        historical_exposure_exceptions_preserved=len(preserved),
        historical_exposure_units_preserved=preserved.unit_key_hash.nunique(),
        coverage_comparison=rows,
    )
    (OUT / "g20c_release_sanitization_manifest.json").write_text(
        json.dumps(summary, indent=2) + "\n"
    )
    memo = [
        "# G2.0c release sanitization and reconciliation",
        "",
        "The pre-push gate found restricted operational names in six CSVs (142 repeated "
        "cells, representing 39 path-term candidates). They are removed, not renamed or "
        "turned into new vocabulary. The local restricted-term policy also catches "
        "substrings inside compounds; ambiguous matches are conservatively excluded.",
        "",
        "## Current state",
        "",
        "- Candidates: 79,369 -> 79,330. Filtered rows: 24,841 -> 24,825.",
        "- Cluster members: 24,421 -> 24,405; 256 stable IDs and 67 assigned concepts.",
        "- Normalization and evaluation/heldout exclusion universes are unchanged.",
        "- Step 3b assignments and 13 reviewed-concept exclusions reconcile exactly.",
        "- Step 4 mapping reconciles; input hashes reflect the corrected artefacts.",
        "- Step 5 is recomputed from the masked corpus with corrected dictionaries.",
        "",
        "## Method limitation",
        "",
        "This is post-fit member pruning with stable concept IDs, not re-clustering. "
        "Original centers, similarity scores and silhouette describe the historical fit. "
        "Member summaries and concentration are recomputed. Restricted terms can no "
        "longer be emitted as candidates or matched as vocabulary anchors, but this "
        "does not claim removal of their prior influence on fitted geometry.",
        "",
        "Pre-correction counts in earlier notes are historical; this report and the "
        "release count/coverage ledgers are authoritative for publication. Full original "
        "artefacts are retained only in ignored internal storage (700/600).",
        "",
        "One Path A unit no longer matches a reviewed concept after pruning. Its historical "
        "instrument-exposure exclusion remains in the preserved-evaluation-exclusions ledger "
        "for both targets. A reduction in current lexical matches never restores evaluation "
        "eligibility; future evaluation must union that ledger with the existing exclusions.",
        "",
        "No model training, F6 update, evaluation-label change, or G2 closure occurred.",
    ]
    (OUT / "g20c_release_sanitization_memo.md").write_text("\n".join(memo) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=["prune", "finalize"])
    args = parser.parse_args()
    prune() if args.phase == "prune" else finalize()
