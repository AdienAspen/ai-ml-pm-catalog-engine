from __future__ import annotations

import hashlib
import importlib.util
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import g20c_neutral_ngram_extraction as extraction
import pandas as pd
from g20c_lexical_safety import TERMS_FILE, assert_safe_terms

ROOT = extraction.STINT2_ROOT
OUT = extraction.OUT
TARGETS = ("Activity", "Object Part")
FULL = "descriptive_full_corpus"
ELIGIBLE = "model_eligible_construction_corpus"
G11 = ROOT / "g1_actionable_zeros/g11_object_part_crosswalk"
G12 = ROOT / "g1_actionable_zeros/g12_floc_alignment/outputs"


def checksum(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_legacy():
    path = G11 / "scripts/g11d_anchor_source_breakdown.py"
    spec = importlib.util.spec_from_file_location("g11d", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def add_phrase(index, phrase, key):
    tokens = tuple(phrase.split())
    if tokens:
        index[len(tokens)][tokens].add(key)


def phrase_index():
    return defaultdict(lambda: defaultdict(set))


def match_segments(segments, index):
    hits = set()
    for tokens in segments:
        for length, phrases in index.items():
            for start in range(len(tokens) - length + 1):
                hits.update(phrases.get(tuple(tokens[start : start + length]), ()))
    return hits


def bucket(domain, catalogue):
    if domain and catalogue:
        return "both"
    if domain:
        return "domain_vocabulary_only"
    if catalogue:
        return "sap_catalog_only"
    return "no_anchor"


def concept_summary(frame, source, universe, target, path, n, anchored):
    counts = Counter()
    for ids in frame[source]:
        counts.update(ids)
    rows = []
    for concept_id, count in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
        rows.append(
            dict(
                universe=universe,
                target=target,
                path_bucket=path,
                anchor_source=source,
                concept_id=concept_id,
                units=count,
                path_units=n,
                anchored_units=anchored,
                share_of_anchored_units=count / anchored,
                share_of_path_units=count / n,
                concentration_above_30pct=count / anchored > 0.30,
            )
        )
    return rows


def summarize(frame, universe):
    summaries, concepts = [], []
    for (target, path), group in frame.groupby(["target", "path_bucket"], sort=True):
        n = len(group)
        counts = Counter(group.anchor_bucket)
        domain_n = counts["domain_vocabulary_only"] + counts["both"]
        sap_n = counts["sap_catalog_only"] + counts["both"]
        assert sum(counts.values()) == n
        sources = {}
        for source, anchored in [("domain_vocabulary", domain_n), ("sap_catalog", sap_n)]:
            rows = concept_summary(group, source, universe, target, path, n, anchored)
            concepts.extend(rows)
            top = rows[0] if rows else {}
            sources.update(
                {
                    source + "_distinct_concepts_matched": len(rows),
                    source + "_top_concept_id": top.get("concept_id", ""),
                    source + "_top_concept_units": top.get("units", 0),
                    source + "_top_concept_share": top.get("share_of_anchored_units"),
                    source + "_concentration_above_30pct": top.get(
                        "concentration_above_30pct", False
                    ),
                }
            )
        summaries.append(
            dict(
                universe=universe,
                target=target,
                path_bucket=path,
                path_units=n,
                units_with_domain_anchor=domain_n,
                units_with_sap_anchor=sap_n,
                domain_vocabulary_only=counts["domain_vocabulary_only"],
                both=counts["both"],
                sap_catalog_only=counts["sap_catalog_only"],
                no_anchor=counts["no_anchor"],
                domain_coverage=domain_n / n,
                sap_coverage=sap_n / n,
                coverage_difference_units=domain_n - sap_n,
                units_touching_reviewed_concepts=int(group.reviewed_concept_exposure.sum()),
                evaluation_set_type="not_evaluation_descriptive_coverage",
                threshold="exact_frozen_phrase_match_no_score_threshold",
                normalisation_pipeline=extraction.NORMALISATION_VERSION,
                source_registry="g20c_step5_anchor_registry_sanitized.csv",
                **sources,
            )
        )
    return summaries, concepts


def run():
    legacy = load_legacy()
    vocab_path = OUT / "g20c_domain_vocabulary_step3b_sanitized.csv"
    members_path = OUT / "g20c_concept_members_step3b_sanitized.csv"
    reviewed_path = OUT / "g20c_step3b_construction_exclusions_sanitized.csv"
    audit_path = OUT / "g20c_step1_normalization_audit_sanitized.csv"
    universe_path = OUT / "g20c_step1_universe_register_sanitized.csv"
    b1_path = (
        extraction.STINT1_ROOT
        / "phase_4_path_b_xlsx/outputs/b1_silver_labels"
        / "b1_silver_labels_textual_residue_sanitized.csv"
    )
    old_obj_path = G11 / "outputs/g11d_anchor_source_order_profile_sanitized.csv"
    old_top_path = G12 / "g12c_anchor_source_top10_concepts_sanitized.csv"
    inputs = {
        TERMS_FILE,
        Path(__file__).with_name("g20c_lexical_safety.py"),
        vocab_path,
        members_path,
        reviewed_path,
        audit_path,
        universe_path,
        legacy.LEXICAL_HIGH,
        legacy.CANONICAL_VOCAB,
        legacy.CONSUMPTION_JSON,
        b1_path,
        old_obj_path,
        old_top_path,
        Path(__file__),
        Path(extraction.__file__),
        Path(legacy.__file__),
        extraction.SERVICE_ORDERS_JSON,
        extraction.PATH_A_EVENTS,
        extraction.PATH_A_ASSIGNMENTS,
        extraction.PATH_A_PDF_ROWS,
        extraction.PATH_A_NOTES,
        extraction.B25_SCRIPT,
        extraction.EVAL_V1_EXCLUSIONS,
        extraction.LEAKAGE_REGEX_CATALOG,
        extraction.LEAKAGE_MASKING_MANIFEST,
        extraction.G02_SAMPLE_MANIFEST,
        *extraction.G02_VISIBLE_PACKAGES,
    }
    inputs.update(ROOT.rglob("*split_manifest*.csv"))
    for root in extraction.B2_SOURCE_ROOTS:
        inputs.update(root.rglob("*.xls*"))
    # Upstream artefacts, including Step 4 mapping and evaluation, remain immutable.
    inputs.update(
        p
        for p in OUT.iterdir()
        if p.is_file()
        and not p.name.startswith("g20c_step5_")
        and p.name not in {"g20c_coverage_contrast_sanitized.csv", "g20c_memo.md"}
    )
    inputs.update(p for p in (ROOT / "artifacts/evaluation_sets").rglob("*") if p.is_file())
    initial_hashes = {path: checksum(path) for path in sorted(inputs)}
    vocab = pd.read_csv(vocab_path).fillna("")
    members = pd.read_csv(members_path).fillna("")
    assert_safe_terms(members.candidate_term)
    reviewed = set(pd.read_csv(reviewed_path).concept_id)
    assert len(reviewed) == 13
    assert vocab.concept_id.is_unique
    target_by_id = vocab.set_index("concept_id").target.to_dict()
    assert all(row.target == target_by_id[row.concept_id] for row in members.itertuples())
    assigned = vocab[vocab.target.isin(TARGETS)]
    assert assigned.groupby("target").size().to_dict() == {"Activity": 24, "Object Part": 43}
    domain_index, sap_index, member_index = phrase_index(), phrase_index(), phrase_index()
    registry = []
    for row in members.itertuples():
        add_phrase(member_index, row.candidate_term, (row.concept_id, row.candidate_term))
        if row.target in TARGETS:
            add_phrase(domain_index, row.candidate_term, (row.target, row.concept_id))
            registry.append(
                dict(
                    target=row.target,
                    anchor_source="domain_vocabulary",
                    concept_id=row.concept_id,
                    term_hash=row.term_hash,
                    provenance="frozen_step3b_members",
                    origin_path=row.path_bucket,
                    source_concept_id=row.concept_id,
                    anchor_source_originally_populated=True,
                )
            )
    lexical = pd.read_csv(legacy.LEXICAL_HIGH).fillna("")
    canonical = pd.read_csv(legacy.CANONICAL_VOCAB).fillna("")
    canonical = canonical[canonical.target.isin(TARGETS)]
    assert canonical.concept_id.is_unique
    selected = lexical[
        lexical.target.isin(TARGETS)
        & lexical.score_band.eq("high")
        & lexical.status.eq("semantic_anchor_high")
        & lexical.can_support_proxy_denominator.astype(str).str.lower().eq("true")
    ]
    selected = selected[["target", "canonical_concept_id"]].drop_duplicates()
    catalog = selected.merge(
        canonical,
        left_on="canonical_concept_id",
        right_on="concept_id",
        suffixes=("", "_canonical"),
        how="left",
        validate="many_to_one",
    )
    assert catalog.concept_id.notna().all()
    assert catalog.target.eq(catalog.target_canonical).all()
    source_counts = Counter()
    for row in catalog.itertuples():
        source = legacy.vocabulary_owner_to_anchor_source(
            row.vocabulary_owner, row.source, row.namespace
        )
        source_counts[(row.target, source)] += 1
        if source != "sap_catalog":
            continue
        tokens, _ = extraction.normalise_text(row.canonical_concept)
        phrase = " ".join(tokens)
        assert phrase, "Empty catalogue concept after normalization"
        add_phrase(sap_index, phrase, (row.target, row.canonical_concept_key))
        registry.append(
            dict(
                target=row.target,
                anchor_source="sap_catalog",
                concept_id=row.canonical_concept_key,
                term_hash=extraction.prefixed_hash("TERM", phrase, 16),
                provenance="lexical_layer_v2_high_join_canonical_vocabulary",
                origin_path="frozen_reference",
                source_concept_id=row.concept_id,
                anchor_source_originally_populated=False,
            )
        )

    print("Frozen dictionaries loaded; reconstructing masked corpus", flush=True)
    extraction.LEAKAGE_PATTERNS = extraction.load_leakage_patterns()
    units = extraction.load_b1_units() + extraction.load_path_a_units() + extraction.load_b2_units()
    assert len({unit["unit_key"] for unit in units}) == len(units)
    assert Counter(unit["path_bucket"] for unit in units) == {
        "B1_RELATIONAL": 10749,
        "PATH_A": 362,
        "B2_WORKBOOKS": 1857,
    }
    exclusions = extraction.load_exclusions()
    eligible_audit = pd.read_csv(audit_path)
    frozen_eligible = set(eligible_audit.unit_key_hash)
    frozen_tokens = eligible_audit.set_index("unit_key_hash").normalised_token_count.to_dict()
    observed_eligible, masked_keys, member_counts = set(), set(), Counter()
    records, hits = [], []
    for unit in units:
        key, path = unit["unit_key"], unit["path_bucket"]
        key_hash = extraction.prefixed_hash("UNIT", key, 12)
        reason = extraction.exclusion_reason(unit, *exclusions[:4])
        eligible = not reason
        if eligible:
            observed_eligible.add(key_hash)
        segments, mask_count = [], 0
        for _, text in unit["segments"]:
            masked, count, _ = extraction.apply_leakage_mask(text, extraction.LEAKAGE_PATTERNS)
            tokens, _ = extraction.normalise_text(masked)
            segments.append(tokens)
            mask_count += count
        if mask_count:
            masked_keys.add(unit["source_unit_key"])
        if eligible:
            assert sum(map(len, segments)) == frozen_tokens.get(key_hash), (
                "Construction token drift"
            )
        all_members = match_segments(segments, member_index)
        if eligible:
            member_counts.update((path, term) for term in {term for _, term in all_members})
        exposure = {concept for concept, _ in all_members} & reviewed
        domain = match_segments(segments, domain_index)
        sap = match_segments(segments, sap_index)
        for target in TARGETS:
            d = {cid for t, cid in domain if t == target}
            s = {cid for t, cid in sap if t == target}
            records.append(
                dict(
                    unit_key_hash=key_hash,
                    target=target,
                    path_bucket=path,
                    construction_eligible=eligible,
                    construction_exclusion=reason,
                    domain_vocabulary=d,
                    sap_catalog=s,
                    anchor_bucket=bucket(d, s),
                    leakage_mask_applied=bool(mask_count),
                    reviewed_concept_exposure=bool(exposure),
                    reviewed_concept_ids="|".join(sorted(exposure)),
                    future_evaluation_status="excluded_instrument_construction"
                    if exposure
                    else "not_assessed_by_step5",
                )
            )
            for source, ids in [("domain_vocabulary", d), ("sap_catalog", s)]:
                for cid in sorted(ids):
                    hits.append(
                        dict(
                            unit_key_hash=key_hash,
                            target=target,
                            path_bucket=path,
                            anchor_source=source,
                            concept_id=cid,
                            construction_eligible=eligible,
                        )
                    )
    assert observed_eligible == frozen_eligible, (
        "Evaluation/heldout exclusion drift: do not rebuild silently"
    )
    expected_masked = set(pd.read_csv(extraction.LEAKAGE_MASKING_MANIFEST).source_unit_key)
    assert masked_keys == expected_masked and len(masked_keys) == 13
    frequency_audit = []
    for row in members.itertuples():
        actual = member_counts[(row.path_bucket, row.candidate_term)]
        assert actual == row.units_with_term, (row.term_hash, actual, row.units_with_term)
        frequency_audit.append(
            dict(
                path_bucket=row.path_bucket,
                term_hash=row.term_hash,
                concept_id=row.concept_id,
                frozen_units=row.units_with_term,
                reconstructed_units=actual,
                matches=True,
            )
        )
    frame = pd.DataFrame(records)
    hit_frame = pd.DataFrame(hits)
    assert not frame.duplicated(["unit_key_hash", "target", "path_bucket"]).any()
    assert not hit_frame.duplicated(
        ["unit_key_hash", "target", "path_bucket", "anchor_source", "concept_id"]
    ).any()
    register = pd.read_csv(universe_path)
    summaries, concepts = [], []
    for universe, subset in [(FULL, frame), (ELIGIBLE, frame[frame.construction_eligible])]:
        summary, concept_rows = summarize(subset, universe)
        for row in summary:
            expected = register[
                (register.universe == universe) & (register.path_bucket == row["path_bucket"])
            ].units.item()
            assert row["path_units"] == expected
        summaries.extend(summary)
        concepts.extend(concept_rows)

    # Historical anchors are retained as observed membership, not rerun or relabelled.
    old_activity = pd.read_csv(b1_path)
    old_activity = old_activity[
        old_activity.target.eq("Activity") & old_activity.status.str.contains("converged")
    ]
    activity_keys = {
        extraction.prefixed_hash("UNIT", key, 12) for key in old_activity.physical_record_id
    }
    activity_top = old_activity.groupby("canonical_concept_key").physical_record_id.nunique().max()
    assert len(activity_keys) == 1215 and activity_top == 832
    no_item = legacy.load_no_item_text()
    assert len(no_item) == 6670
    order_to_unit = {
        legacy.prefixed_hash("ORDER", row.order_id): extraction.prefixed_hash(
            "UNIT", extraction.physical_record_id(row.order_id), 12
        )
        for row in no_item.itertuples()
    }
    old_object = set(pd.read_csv(old_obj_path).order_id_hash)
    assert old_object <= set(order_to_unit) and len(old_object) == 3737
    object_keys = {order_to_unit[key] for key in old_object}
    no_item_keys = set(order_to_unit.values())
    historical = []
    residual_summaries, residual_concepts = summarize(
        frame[frame.unit_key_hash.isin(no_item_keys) & frame.target.eq("Object Part")],
        "descriptive_B1_no_item_signal_subset",
    )
    for target, keys, subset_keys, old_n, old_top_n in [
        (
            "Activity",
            activity_keys,
            set(frame[frame.path_bucket.eq("B1_RELATIONAL")].unit_key_hash),
            1215,
            832,
        ),
        ("Object Part", object_keys, no_item_keys, 3737, 738),
    ]:
        group = frame[frame.target.eq(target) & frame.unit_key_hash.isin(subset_keys)]
        domain_keys = set(group[group.domain_vocabulary.map(bool)].unit_key_hash)
        both = keys & domain_keys
        historical.append(
            dict(
                target=target,
                path_bucket="B1_RELATIONAL",
                universe_units=len(group),
                historical_catalogue_units=old_n,
                current_domain_units=len(domain_keys),
                both=len(both),
                historical_catalogue_only=len(keys - domain_keys),
                domain_only=len(domain_keys - keys),
                neither=len(subset_keys - keys - domain_keys),
                historical_top_concept_units=old_top_n,
                historical_top_concept_share=old_top_n / old_n,
                historical_method="b1_semantic_converged"
                if target == "Activity"
                else "g11d_legacy_exact_high_band_no_item",
                current_method="semantic_normalisation_v2_exact_step3b_surface_variants",
                directly_comparable_detector_methods=False,
                interpretation="descriptive_membership_contrast_not_quality_or_admission",
            )
        )
    old_top = pd.read_csv(old_top_path)
    mixed = old_top[old_top.target.eq("Activity")].iloc[0]
    assert mixed.unit_count == 858

    assert all(checksum(path) == digest for path, digest in initial_hashes.items()), (
        "Upstream input changed"
    )
    serialized = frame.copy()
    for column in ("domain_vocabulary", "sap_catalog"):
        serialized[column] = serialized[column].map(lambda ids: "|".join(sorted(ids)))
    outputs = {
        "g20c_coverage_contrast_sanitized.csv": pd.DataFrame(summaries),
        "g20c_step5_concept_coverage_sanitized.csv": pd.DataFrame(concepts),
        "g20c_step5_unit_coverage_sanitized.csv": serialized,
        "g20c_step5_unit_concept_hits_sanitized.csv": hit_frame,
        "g20c_step5_anchor_registry_sanitized.csv": pd.DataFrame(registry).drop_duplicates(),
        "g20c_step5_member_frequency_audit_sanitized.csv": pd.DataFrame(frequency_audit),
        "g20c_step5_historical_contrast_sanitized.csv": pd.DataFrame(historical),
        "g20c_step5_no_item_subset_sanitized.csv": pd.DataFrame(residual_summaries),
        "g20c_step5_no_item_concepts_sanitized.csv": pd.DataFrame(residual_concepts),
        "g20c_step5_input_hashes_sanitized.csv": pd.DataFrame(
            [
                dict(
                    source_file_key=extraction.prefixed_hash(
                        "FILE", str(p.relative_to(extraction.PROJECT_ROOT)), 24
                    ),
                    sha256=digest,
                    unchanged=True,
                )
                for p, digest in initial_hashes.items()
            ]
        ),
    }
    for name, table in outputs.items():
        table["raw_operational_values_emitted"] = False
        table.to_csv(OUT / name, index=False)
        reread = pd.read_csv(OUT / name, keep_default_na=False)
        assert len(reread) == len(table) and list(reread.columns) == list(table.columns)
    full_rows = [row for row in summaries if row["universe"] == FULL]
    flags = [
        dict(
            target=row["target"],
            path_bucket=row["path_bucket"],
            share=row["domain_vocabulary_top_concept_share"],
        )
        for row in full_rows
        if row["domain_vocabulary_concentration_above_30pct"]
    ]
    manifest = dict(
        created_at=datetime.now(timezone.utc).isoformat(),
        step="G2.0c Step 5",
        status="completed_with_concentration_flags" if flags else "completed",
        domain_concepts=67,
        unassigned_and_ambiguous_concepts_not_used=189,
        domain_matcher="exact_contiguous_1_to_3_token_surface_variants_frozen_step3b",
        catalogue_matcher="exact_contiguous_canonical_phrases_from_frozen_lexical_v2_high_sap_owned",
        matching_scope="shared_frozen_lexicon_across_paths_separate_unit_counts_per_path",
        segment_policy="no_phrase_matches_across_original_source_segment_boundaries",
        catalogue_mapping_step4_used_as_detector=False,
        normalisation_pipeline=extraction.NORMALISATION_VERSION,
        catalogue_anchor_source="derived_from_frozen_owner_source_namespace_not_original_field",
        top_concept_share_denominator="distinct_units_with_at_least_one_anchor_from_same_source_target_path_universe",
        gate_rule="flag_strictly_above_0.30_no_retuning",
        concentration_flags=flags,
        measurement="descriptive_lexical_coverage_not_accuracy_or_admission",
        reviewed_concepts_excluded_from_future_evaluation=sorted(reviewed),
        masks_verified=13,
        construction_membership_verified=10900,
        frozen_member_frequencies_verified=len(frequency_audit),
        labels_read=False,
        training_run=False,
        denominator_changed=False,
        heldout_statistics_used_to_retune=False,
        reference_or_upstream_files_changed=False,
        historical_activity_correction=dict(
            mixed_path_top=858, mixed_path_denominator=1628, b1_top=832, b1_denominator=1215
        ),
        outputs={name: checksum(OUT / name) for name in outputs},
        limitations=[
            "Exact phrase coverage is not semantic validation of every cluster member.",
            "Historical semantic Activity detector differs from this exact phrase comparator.",
            "Object Part historical 3737 has denominator 6670, not 10749.",
            "Excluded texts enter full-corpus statistics only; no vocabulary changes.",
            "Unseen surface variants can be missed, especially B2 and Path A.",
            "Future heldout additions require rechecking construction exclusions before reuse.",
        ],
    )
    (OUT / "g20c_step5_coverage_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        "# G2.0c - Step 5 coverage report",
        "",
        "Descriptive lexical coverage only. No accuracy, admission, F6 change, or training.",
        "",
        "## Method",
        "",
        "Frozen Step 3b surface variants are matched exactly after G2.0b masking and "
        "semantic_normalisation_v2. The same frozen global lexicon is applied to each path, "
        "with no cross-path count aggregation. Source segment boundaries are preserved. "
        "Each concept counts at most once per unit and target. All 67 assigned concepts "
        "participate, including concepts without a Step 4 catalogue match.",
        "",
        "The paired SAP comparator uses frozen high-band SAP-owned canonical phrases with "
        "the same normalization and units. This is a lexical comparator, not a replay of "
        "the historical semantic admission mechanism. anchor_source is explicit; for SAP "
        "it is derived from frozen ownership, not originally populated evidence.",
        "",
        "Top share is concept units / units anchored by the same source, target and path. "
        "Multi-concept hits are allowed; concept counts must not be summed into a denominator. "
        "A flag is not proof that a concept "
        "is semantically generic, but requires review before using coverage to scope modelling.",
        "",
        "## Full corpus, statistics only",
        "",
        "| Target | Path | Units | Domain (including both) | Both | SAP only | Neither "
        "| Domain concepts | Top share | Gate |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in full_rows:
        top_share = row["domain_vocabulary_top_concept_share"]
        share_display = f"{top_share:.2%}" if top_share is not None else "undefined"
        gate = "FLAG" if row["domain_vocabulary_concentration_above_30pct"] else "within limit"
        lines.append(
            f"| {row['target']} | {row['path_bucket']} | {row['path_units']} "
            f"| {row['units_with_domain_anchor']} | {row['both']} "
            f"| {row['sap_catalog_only']} | {row['no_anchor']} "
            f"| {row['domain_vocabulary_distinct_concepts_matched']} "
            f"| {share_display} | {gate} |"
        )
    lines += [
        "",
        "## Historical reconciliation",
        "",
        "The plan's Activity 52.7% was 858/1628 across paths. B1 alone is 832/1215 = 68.48%. "
        "This report corrects the comparison without rewriting frozen G1.2c evidence. "
        "Object Part 3737 is restricted to 6670 no-item orders. A separate same-subset file "
        "retains that scope. Historical membership contrasts are descriptive, "
        "not a claim of equivalent detector methods.",
        "",
        "## Integrity and limitations",
        "",
        f"The 13 masked units match G2.0b exactly. The 10900 eligible keys and all {len(members)} "
        "frozen member frequencies reconcile. Current evaluation and heldout manifests "
        "were rechecked; any drift aborts the run. The 13 reviewed-concept exclusions "
        "are retained and their unit exposure is explicit for both targets. No response "
        "labels were read. No reviewed concept becomes eligible for evaluation here.",
        "",
        "Path A construction uses only 159 units. B2 coverage may miss surface forms "
        "excluded with evaluation text. Exact lexical hits, cluster coherence, component "
        "presence and SAP coding correctness are different "
        "questions. The measured coverage does not validate the latter three.",
        "",
        "Only hashed unit/concept identifiers, counts and metadata are emitted. "
        "No source text or new visible-text sample is written. Upstream files and "
        "evaluation artifacts are verified unchanged by SHA-256.",
        "",
        "Step 5 is executed; concentration flags remain open findings. "
        "No model training or G2 closure is implied.",
    ]
    (OUT / "g20c_memo.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        pd.DataFrame(full_rows)[
            [
                "target",
                "path_bucket",
                "path_units",
                "units_with_domain_anchor",
                "both",
                "sap_catalog_only",
                "no_anchor",
                "domain_vocabulary_top_concept_share",
            ]
        ].to_string(index=False)
    )
    print(
        json.dumps(
            {
                "status": manifest["status"],
                "flags": flags,
                "upstream_inputs_unchanged": len(initial_hashes),
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    run()
