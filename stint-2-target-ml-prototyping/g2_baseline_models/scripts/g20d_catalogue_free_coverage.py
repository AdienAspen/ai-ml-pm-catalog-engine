from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

import g20c_neutral_ngram_extraction as extraction
from g20c_lexical_safety import POLICY, TERMS_FILE, restricted_match
from g20c_step5_coverage import add_phrase, bucket, match_segments, phrase_index, summarize

ROOT = extraction.STINT2_ROOT
S1 = extraction.STINT1_ROOT
OUT = ROOT / "g2_baseline_models/outputs/g20d_catalogue_free_coverage"
G20C = extraction.OUT
VOCAB = S1 / "phase_1_lexical/outputs/canonical_vocabulary"
EXTERNAL = VOCAB / "external_failure_vocabulary_v1.csv"
ALIASES = VOCAB / "translation_aliases_es_v1.csv"
CANONICAL = VOCAB / "canonical_vocabulary_v1_working.csv"
LEXICAL = S1 / "phase_1_lexical/outputs/lexical_layer_v2/lexical_layer_v2_high_confidence_candidates_sanitized.csv"
ZEUS = extraction.PROJECT_ROOT / "stint-1.1-reference-layer/reference_layer/semantic_normalisation/zeus_semantic_scaffold_v1.csv"
AUGMENTATION = G20C / "g20c_external_reference_augmentation_sanitized.csv"
F6 = ROOT / "g1_actionable_zeros/g1_denominator_update/outputs/f6_g20_evidence_denominator_matrix_sanitized.csv"
B1 = S1 / "phase_4_path_b_xlsx/outputs/b1_silver_labels/b1_silver_labels_textual_residue_sanitized.csv"
B2 = S1 / "phase_4_path_b_xlsx/outputs/b25_grouping_refinement/b25_grouped_reanchored_evidence_sanitized.csv"
PA = S1 / "phase_3_path_a_faultcodes/outputs/f356_path_a_integrated_crosswalk_sanitized.csv"
SYM = S1 / "phase_5_symptom/outputs/f51_symptom_thread_resolution"
SYM_B1 = SYM / "t51b2x_reason_semantic_classification_normalized.csv"
SYM_OTHER = SYM / "t51b24b_semantic_other_paths.csv"
TARGETS = ("Cause", "Damage", "Symptom")
FULL = "full_cleaned_corpus"
ELIGIBLE = "model_eligible_construction_corpus"
PATHS = {"B1_RELATIONAL_TEXTUAL": "B1_RELATIONAL", "RELATIONAL_REASON": "B1_RELATIONAL",
         "B2_WORKBOOK_SNAPSHOTS": "B2_WORKBOOKS", "B2_WORKBOOKS": "B2_WORKBOOKS",
         "PATH_A_PDF_EVENTS": "PATH_A", "PATH_A_CONCERN_TABLE": "PATH_A", "PATH_A_NOTES": "PATH_A"}
POLICY_CONFIG = dict(
    method="exact_contiguous_frozen_phrases_no_embeddings", normalization="semantic_normalisation_v2",
    lexical_safety=POLICY, phrase_expansion=False, similarity_threshold=None,
    segment_boundaries_preserved=True, positive_source="domain_vocabulary",
    catalogue_role="high_band_sap_owned_companion_not_signal", source_subsystem_gate="not_validated",
    concept_key="target_x_frozen_canonical_key;augmentation_support_sets_group_variants",
    top_share_denominator="units_anchored_by_same_source_target_path_universe", flag_above=0.30,
    output_interpretation="domain_supported_volume_not_ground_truth",
    zeus_container_definitions="inventory_only_not_lexical_anchors",
    aliases="frozen_external_parent_aliases_only;expert_inference_retained",
    f6_policy="same_units_and_universe_or_null_delta;separate_symptom_strata",
    no_training=True, no_f6_change=True, no_g20e=True,
)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return pd.read_csv(path).fillna("")


def relative(path):
    return str(path.relative_to(extraction.PROJECT_ROOT))


def unit_hash(key):
    return extraction.prefixed_hash("UNIT", key, 12)


def corpus_input_hashes():
    paths = {extraction.SERVICE_ORDERS_JSON, extraction.PATH_A_EVENTS,
             extraction.PATH_A_ASSIGNMENTS, extraction.PATH_A_PDF_ROWS,
             extraction.PATH_A_NOTES, extraction.B25_SCRIPT,
             extraction.G02_SAMPLE_MANIFEST, *extraction.G02_VISIBLE_PACKAGES,
             extraction.B25_SCRIPT.with_name("b23_snapshot_weak_supervision.py")}
    for root in extraction.B2_SOURCE_ROOTS:
        paths.update(root.rglob("*.xls*"))
    return {extraction.prefixed_hash("INPUT", relative(p)): sha(p) for p in sorted(paths)}


def save(frame, name):
    frame = frame.copy()
    frame["raw_operational_values_emitted"] = False
    frame.to_csv(OUT / name, index=False)
    assert len(read(OUT / name)) == len(frame)


def freeze():
    OUT.mkdir(parents=True, exist_ok=True)
    manifest_path = OUT / "g20d_freeze_manifest.json"
    if manifest_path.exists():
        raise RuntimeError("Freeze already exists; do not change vocabulary after observing coverage")
    registry = []

    def append(target, concept, entry, term, source, artifact, kind, evidence, tier,
               subsystem="", level="", scope="", caveat="", source_ids=""):
        normalized = " ".join(extraction.normalise_text(term)[0])
        held = not normalized or restricted_match(normalized)
        registry.append(dict(target=target, concept_id=concept, source_entry_id=entry,
                             anchor_text="" if held else normalized,
                             term_hash=extraction.prefixed_hash("TERM", normalized),
                             anchor_source=source, source_artifact=relative(artifact),
                             reference_family=kind, evidence_type=evidence, tier=tier,
                             subsystem=subsystem, semantic_level=level, source_scope=scope,
                             source_caveat=caveat, source_concept_ids=source_ids or entry,
                             status="held_empty_or_restricted" if held else "active",
                             construction_method="transcribed_frozen_reference_no_new_terms"))

    external = read(EXTERNAL)
    assert len(external) == 144 and external.concept_id.is_unique
    for row in external.itertuples():
        append(row.target, row.canonical_concept_key, row.concept_id, row.canonical_concept,
               "domain_vocabulary", EXTERNAL, row.vocabulary_owner, row.evidence_type,
               row.tier, row.subsystem, row.semantic_level, row.coverage_scope, row.source_caveat)
    parents = external.set_index("concept_id")
    aliases = read(ALIASES)
    assert aliases.canonical_concept_id.isin(parents.index).all()
    for row in aliases.itertuples():
        parent = parents.loc[row.canonical_concept_id]
        append(row.target, row.canonical_concept_key, row.alias_id, row.canonical_alias_es,
               "domain_vocabulary", ALIASES, row.vocabulary_owner + "_FROZEN_ES_ALIAS",
               row.evidence_type, row.tier, row.subsystem, row.semantic_level,
               parent.coverage_scope, parent.source_caveat, row.canonical_concept_id)
    for row in read(AUGMENTATION).itertuples():
        key = str(row.reference_concept_keys)
        if "|" in key:
            key = extraction.prefixed_hash("REFSET", key)
        append(row.reference_target, key, row.reference_entry_id, row.reference_term,
               "domain_vocabulary", AUGMENTATION, "G20C_FROZEN_REFERENCE_AUGMENTATION",
               row.evidence_type, "inherited_reference_scope", level="frozen_reference_variant",
               scope=row.semantic_scope, source_ids=row.reference_source_row_ids)
        registry[-1]["construction_method"] = row.construction_method

    lexical = read(LEXICAL)
    selected = lexical[lexical.target.isin(TARGETS) & lexical.score_band.eq("high")
                       & lexical.status.eq("semantic_anchor_high")
                       & lexical.can_support_proxy_denominator.astype(str).str.lower().eq("true")]
    canonical = read(CANONICAL).drop_duplicates()
    assert canonical.concept_id.is_unique
    selected = selected[["target", "canonical_concept_id"]].drop_duplicates().merge(
        canonical, left_on="canonical_concept_id", right_on="concept_id", how="inner",
        validate="many_to_one", suffixes=("", "_canonical"))
    for row in selected[selected.vocabulary_owner.eq("SAP_MAPPING")].itertuples():
        assert row.target == row.target_canonical
        append(row.target, row.canonical_concept_key, row.concept_id, row.canonical_concept,
               "sap_catalog", CANONICAL, "SAP_MAPPING_HIGH_BAND", row.evidence_type, row.tier,
               level="catalogue_description", scope="comparison_only_not_domain_signal")
    frame = pd.DataFrame(registry).drop_duplicates()
    assert frame.target.isin(TARGETS).all()
    save(frame, "g20d_anchor_registry_sanitized.csv")
    inventory = frame.groupby(
        ["target", "anchor_source", "reference_family", "evidence_type", "tier", "semantic_level"],
        dropna=False).agg(source_entries=("source_entry_id", "nunique"),
                         concepts=("concept_id", "nunique"),
                         lexical_forms=("anchor_text", lambda x: x[x.ne("")].nunique()),
                         active_entries=("status", lambda x: x.eq("active").sum())).reset_index()
    save(inventory, "g20d_vocabulary_inventory_sanitized.csv")
    zeus = read(ZEUS)
    zeus = zeus[zeus.zeus_category.isin(
        ["detection_symptom", "failure_mode", "failure_cause", "failure_process"])].copy()
    zeus["g20d_disposition"] = "held_category_definition_not_materialized_lexicon"
    save(zeus, "g20d_zeus_source_disposition_sanitized.csv")
    totals = frame[frame.status.eq("active")].groupby(["target", "anchor_source"]).agg(
        source_entries=("source_entry_id", "nunique"), concepts=("concept_id", "nunique"),
        lexical_forms=("anchor_text", "nunique")).reset_index()
    save(totals, "g20d_vocabulary_totals_sanitized.csv")
    sources = [EXTERNAL, ALIASES, CANONICAL, LEXICAL, ZEUS, AUGMENTATION, F6, B1, B2, PA,
               SYM_B1, SYM_OTHER, TERMS_FILE, extraction.LEAKAGE_REGEX_CATALOG,
               extraction.LEAKAGE_MASKING_MANIFEST, extraction.EVAL_V1_EXCLUSIONS,
               Path(extraction.__file__), Path(__file__).with_name("g20c_lexical_safety.py"),
               Path(__file__).with_name("g20c_step5_coverage.py"),
               G20C / "g20c_step1_normalization_audit_sanitized.csv",
               G20C / "g20c_step1_universe_register_sanitized.csv"]
    sources.extend(ROOT.rglob("*split_manifest*.csv"))
    manifest = dict(frozen_at_utc=datetime.now(timezone.utc).isoformat(), settings=POLICY_CONFIG,
                    source_sha256={relative(p): sha(p) for p in sorted(set(sources))},
                    registry_sha256=sha(OUT / "g20d_anchor_registry_sanitized.csv"),
                    corpus_input_sha256=corpus_input_hashes(),
                    script_sha256_at_freeze=sha(Path(__file__)), corpus_coverage_observed=False)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(totals.to_string(index=False))
    print("Registry/settings frozen BEFORE corpus measurement; ZEUS containers held")


def historical_memberships(units):
    sets = {}
    for artifact, key, path in [(B1, "physical_record_id", "B1_RELATIONAL_TEXTUAL"),
                                (B2, "refined_event_key", "B2_WORKBOOK_SNAPSHOTS"),
                                (PA, "estimated_event_key", "PATH_A_PDF_EVENTS")]:
        data = read(artifact)
        data = data[data.target.isin(("Cause", "Damage"))]
        if artifact == B1:
            data = data[data.status.str.contains("converged", regex=False)]
        for target, group in data.groupby("target"):
            sets[(target, path)] = set(group[key].astype(str))
    orders = extraction.load_json_records(extraction.SERVICE_ORDERS_JSON)
    reason_orders = [o for o in orders if extraction.as_text(o.get("reason"))]
    predictions = read(SYM_B1)
    assert len(reason_orders) == len(predictions), "Symptom B1 row count mismatch"
    symptom_keys = set()
    for order, row in zip(reason_orders, predictions.itertuples(), strict=True):
        expected_hash = extraction.prefixed_hash(
            "REASON", extraction.as_text(order["reason"]).lower(), 12)
        assert row.reason_hash == expected_hash, "Symptom B1 sequence/hash mismatch"
        if row.predicted_class == "observed_condition":
            symptom_keys.add(extraction.physical_record_id(order["id"]))
    assert len(symptom_keys) == 1827
    sets[("Symptom", "RELATIONAL_REASON")] = symptom_keys
    declared = read(F6)
    declared = declared[declared.target.isin(TARGETS) & declared.admitted_denominator_units.gt(0)]
    other = read(SYM_OTHER)
    counts = other[other.predicted_class.eq("observed_condition")].groupby("path_bucket").size()
    for row in declared.itertuples():
        k = (row.target, row.path_bucket)
        if k in sets:
            assert len(sets[k]) == row.admitted_denominator_units, k
        else:
            assert row.target == "Symptom" and counts[row.path_bucket] == row.admitted_denominator_units
    return declared, sets


def measure():
    freeze_path = OUT / "g20d_freeze_manifest.json"
    manifest = json.loads(freeze_path.read_text())
    assert manifest["settings"] == POLICY_CONFIG
    assert manifest["script_sha256_at_freeze"] == sha(Path(__file__))
    assert manifest["corpus_input_sha256"] == corpus_input_hashes()
    for path, digest in manifest["source_sha256"].items():
        assert sha(extraction.PROJECT_ROOT / path) == digest, f"Frozen input changed: {path}"
    assert sha(OUT / "g20d_anchor_registry_sanitized.csv") == manifest["registry_sha256"]
    protected = [p for base in (ROOT / "artifacts/evaluation_sets", G20C, F6.parent)
                 for p in base.rglob("*") if p.is_file()]
    protected_hashes = {p: sha(p) for p in protected}
    registry = read(OUT / "g20d_anchor_registry_sanitized.csv")
    indexes = {source: phrase_index() for source in ("domain_vocabulary", "sap_catalog")}
    for row in registry[registry.status.eq("active")].itertuples():
        assert not restricted_match(row.anchor_text)
        add_phrase(indexes[row.anchor_source], row.anchor_text, (row.target, row.concept_id))
    extraction.LEAKAGE_PATTERNS = extraction.load_leakage_patterns()
    print("Frozen rules verified; reconstructing masked corpus", flush=True)
    units = extraction.load_b1_units() + extraction.load_path_a_units() + extraction.load_b2_units()
    by_key = {unit["unit_key"]: unit for unit in units}
    assert len(by_key) == len(units) == 12968
    exclusions = extraction.load_exclusions()
    frozen_audit = read(G20C / "g20c_step1_normalization_audit_sanitized.csv")
    expected_eligible = set(frozen_audit.unit_key_hash)
    observed_eligible, masked_keys = set(), set()
    reasons, hit_rows, unit_rows = {}, [], []
    for unit in units:
        key, path = unit["unit_key"], unit["path_bucket"]
        hashed = unit_hash(key)
        reason = extraction.exclusion_reason(unit, *exclusions[:4])
        reasons[key] = reason
        if not reason:
            observed_eligible.add(hashed)
        segments, reason_segments, masked_count = [], [], 0
        for field, text in unit["segments"]:
            masked, count, _ = extraction.apply_leakage_mask(text, extraction.LEAKAGE_PATTERNS)
            tokens, _ = extraction.normalise_text(masked)
            segments.append(tokens)
            if field == "reason":
                reason_segments.append(tokens)
            masked_count += count
        if masked_count:
            masked_keys.add(unit["source_unit_key"])
        source_hits = {source: match_segments(segments, index) for source, index in indexes.items()}
        reason_hits = match_segments(reason_segments, indexes["domain_vocabulary"])
        for target in TARGETS:
            domain = {cid for t, cid in source_hits["domain_vocabulary"] if t == target}
            sap = {cid for t, cid in source_hits["sap_catalog"] if t == target}
            unit_rows.append(dict(unit_key_hash=hashed, target=target, path_bucket=path,
                                  construction_eligible=not reason, construction_exclusion=reason,
                                  domain_vocabulary=domain, sap_catalog=sap,
                                  anchor_bucket=bucket(domain, sap), reviewed_concept_exposure=False,
                                  reason_only_domain_hit=any(t == target for t, _ in reason_hits),
                                  leakage_mask_applied=bool(masked_count)))
            for source, ids in [("domain_vocabulary", domain), ("sap_catalog", sap)]:
                for cid in sorted(ids):
                    hit_rows.append(dict(unit_key_hash=hashed, target=target, path_bucket=path,
                                         anchor_source=source, concept_id=cid,
                                         construction_eligible=not reason,
                                         evidence_type="reference_supported_lexical_match_not_sap_truth",
                                         label_generation_method="exact_frozen_reference_phrase_match",
                                         source_registry="g20d_anchor_registry_sanitized.csv",
                                         subsystem_applicability="not_validated"))
    assert observed_eligible == expected_eligible
    assert masked_keys == set(read(extraction.LEAKAGE_MASKING_MANIFEST).source_unit_key)
    assert len(masked_keys) == 13
    frame = pd.DataFrame(unit_rows)
    hits = pd.DataFrame(hit_rows)
    assert not frame.duplicated(["unit_key_hash", "target"]).any()
    assert not hits.duplicated(["unit_key_hash", "target", "anchor_source", "concept_id"]).any()
    summaries, concept_rows = [], []
    for universe, subset in [(FULL, frame), (ELIGIBLE, frame[frame.construction_eligible])]:
        result, concepts = summarize(subset, universe)
        for row in result:
            row["source_registry"] = "g20d_anchor_registry_sanitized.csv"
            row["measure_name"] = "domain_supported_volume"
            row["subsystem_applicability"] = "not_validated_see_source_scopes"
            row.pop("units_touching_reviewed_concepts")
        summaries.extend(result)
        concept_rows.extend(concepts)
    summary = pd.DataFrame(summaries)
    declared, memberships = historical_memberships(by_key)
    contrast, reconciliation, historical_rows = [], [], []
    for row in declared.itertuples():
        hist_key = (row.target, row.path_bucket)
        path = PATHS[row.path_bucket]
        old_keys = memberships.get(hist_key, set())
        missing_keys = old_keys - set(by_key)
        compatible = hist_key in memberships and not missing_keys
        if hist_key not in memberships:
            comparison_status = "blocked_legacy_text_row_vs_event_unit_no_numeric_delta"
        elif missing_keys:
            comparison_status = "blocked_historical_membership_outside_step5_universe"
        else:
            comparison_status = "same_units_descriptive_not_causal_detector_effect"
        reconciliation.append(dict(target=row.target, f6_path=row.path_bucket,
                                    declared_units=row.admitted_denominator_units,
                                    reconstructed_source_rows=row.admitted_denominator_units,
                                    comparable_unit_membership=compatible,
                                    historical_keys_in_step5=len(old_keys-missing_keys)
                                    if hist_key in memberships else None,
                                    historical_keys_outside_step5=len(missing_keys)
                                    if hist_key in memberships else None,
                                    status=comparison_status))
        for key in sorted(old_keys):
            historical_rows.append(dict(target=row.target, f6_path=row.path_bucket,
                                        unit_key_hash=unit_hash(key),
                                        construction_exclusion=reasons.get(key, "outside_step5_universe")))
        for universe in (FULL, ELIGIBLE):
            group = frame[frame.target.eq(row.target) & frame.path_bucket.eq(path)]
            if universe == ELIGIBLE:
                group = group[group.construction_eligible]
            domains = set(group[group.domain_vocabulary.map(bool)].unit_key_hash)
            universe_keys = set(group.unit_key_hash)
            old_hashes = {unit_hash(key) for key in old_keys}
            old_in_universe = old_hashes & universe_keys
            record = dict(target=row.target, path_bucket=path, f6_path=row.path_bucket,
                          universe=universe, universe_units=len(group), f6_count_unit=row.count_unit,
                          f6_declared_full_units=row.admitted_denominator_units,
                          historical_keys_outside_step5=len(missing_keys)
                          if hist_key in memberships else None,
                          f6_same_universe_units=len(old_in_universe) if compatible else None,
                          f6_excluded_for_evaluation_or_heldout=len(old_hashes-universe_keys)
                          if compatible else None,
                          domain_supported_units=len(domains),
                          same_universe_delta=len(domains)-len(old_in_universe) if compatible else None,
                          both=len(domains & old_in_universe) if compatible else None,
                          domain_only=len(domains-old_in_universe) if compatible else None,
                          f6_only=len(old_in_universe-domains) if compatible else None,
                          comparison_status=comparison_status,
                          historical_text_scope="reason_only" if hist_key == ("Symptom", "RELATIONAL_REASON")
                          else "legacy_path_specific_evidence",
                          current_text_scope="g20c_constituted_source_segments",
                          domain_reason_only_units=int(group.reason_only_domain_hit.sum())
                          if hist_key == ("Symptom", "RELATIONAL_REASON") else None,
                          f6_modified=False)
            contrast.append(record)
    exclusion_rows = []
    for path in sorted({u["path_bucket"] for u in units}):
        group_keys = [u["unit_key"] for u in units if u["path_bucket"] == path]
        counts = Counter(reasons[key] for key in group_keys)
        exclusion_rows.append(dict(path_bucket=path, full_cleaned_units=len(group_keys),
                                   model_eligible_units=counts[""],
                                   evaluation_set_v1_excluded=counts["evaluation_set_v1"],
                                   additional_heldout_excluded=counts["additional_heldout"]))
    serial = frame.drop(columns="reviewed_concept_exposure").copy()
    for column in ("domain_vocabulary", "sap_catalog"):
        serial[column] = serial[column].map(lambda x: "|".join(sorted(x)))
    save(summary, "g20d_domain_only_coverage_sanitized.csv")
    save(pd.DataFrame(concept_rows), "g20d_concept_coverage_sanitized.csv")
    save(serial, "g20d_unit_coverage_sanitized.csv")
    save(hits, "g20d_unit_concept_hits_sanitized.csv")
    save(pd.DataFrame(contrast), "g20d_f6_contrast_sanitized.csv")
    save(pd.DataFrame(reconciliation), "g20d_f6_reconciliation_sanitized.csv")
    save(pd.DataFrame(historical_rows), "g20d_f6_unit_membership_sanitized.csv")
    save(pd.DataFrame(exclusion_rows), "g20d_universe_exclusions_sanitized.csv")
    # Source-specific counts preserve heterogeneous reference semantics and subsystem scopes.
    source_hits = hits.merge(registry[["target", "anchor_source", "concept_id", "reference_family",
                                      "subsystem", "semantic_level", "tier"]].drop_duplicates(),
                            on=["target", "anchor_source", "concept_id"], how="left")
    source_counts = []
    for universe, subset in [(FULL, source_hits), (ELIGIBLE, source_hits[source_hits.construction_eligible])]:
        agg = subset.groupby(["target", "path_bucket", "anchor_source", "reference_family",
                              "subsystem", "semantic_level", "tier"], dropna=False).agg(
                                  units=("unit_key_hash", "nunique"), concepts=("concept_id", "nunique")).reset_index()
        agg["universe"] = universe
        agg["interpretation"] = "reference_support_scope_not_verified_subsystem_assignment"
        source_counts.append(agg)
    save(pd.concat(source_counts, ignore_index=True), "g20d_reference_scope_coverage_sanitized.csv")
    for p, digest in protected_hashes.items():
        assert sha(p) == digest, "Protected upstream file changed"
    assert manifest["corpus_input_sha256"] == corpus_input_hashes()
    for path, digest in manifest["source_sha256"].items():
        assert sha(extraction.PROJECT_ROOT / path) == digest, f"Frozen input changed: {path}"
    result = dict(completed_at_utc=datetime.now(timezone.utc).isoformat(),
                  freeze_sha256=sha(freeze_path), script_sha256=sha(Path(__file__)),
                  masked_units=13, construction_membership_reconciled=10900,
                  protected_files_unchanged=len(protected_hashes),
                  f6_source_count_rows_verified=len(reconciliation),
                  f6_unit_rows_reconciled=sum(r["comparable_unit_membership"] for r in reconciliation),
                  f6_strata_delta_unavailable=sum(not r["comparable_unit_membership"] for r in reconciliation),
                  status="provisional_b2_source_identity_and_six_f6_strata_incomparable",
                  outputs={p.name: sha(p) for p in sorted(OUT.glob('*.csv'))},
                  labels_used_for_tuning=False, f6_updated=False, g20e_started=False)
    (OUT / "g20d_run_manifest.json").write_text(json.dumps(result, indent=2)+"\n")
    write_memo(summary, pd.DataFrame(contrast))
    print(summary[["universe", "target", "path_bucket", "path_units", "units_with_domain_anchor",
                   "sap_catalog_only", "no_anchor", "domain_vocabulary_top_concept_share"]].to_string(index=False))


def write_memo(summary, contrast):
    lines = ["# G2.0d - Catalogue-free reference coverage", "",
             "This is domain-supported volume, not SAP ground truth or an evaluation of a model.", "",
             "## Frozen instrument", "",
             "Exact frozen phrases after leakage masking and semantic_normalisation_v2; no embeddings, "
             "new aliases, synonym generation, token stemming or retrospective tuning. Domain evidence "
             "comes from the full 144-entry external reference inventory, frozen translations and the "
             "three prior reference-augmentation entries. Reference scopes, tiers and inference-derived "
             "aliases remain explicit. ZEUS containers are not converted into invented lexical anchors.", "",
             "## Coverage by universe", "",
             "Domain includes both-source units. Domain + SAP-only + neither equals the path universe. "
             "Top share is computed over domain-anchored units, not all units or summed mentions.", "",
             "| Universe | Target | Path | N | Domain | SAP only | Neither | Top share |",
             "|---|---|---|---:|---:|---:|---:|---:|"]
    for row in summary.itertuples():
        share = row.domain_vocabulary_top_concept_share
        display = "undefined" if pd.isna(share) else f"{share:.2%}"
        lines.append(f"| {row.universe} | {row.target} | {row.path_bucket} | {row.path_units} "
                     f"| {row.units_with_domain_anchor} | {row.sap_catalog_only} | {row.no_anchor} "
                     f"| {display} |")
    lines += ["", "## F6 reconciliation", "",
              "Cause and Damage reconcile to physical orders in B1; Cause also reconciles in Path A. "
              "Symptom B1 reconciles all 1,827 reason rows, in sequence and by hash, to distinct physical "
              "orders. The eligible comparison excludes the same order keys as G2.0c, and exclusions "
              "are reported separately. Reason-only domain coverage is also retained to distinguish "
              "field expansion from detector changes.", "",
              "Symptom's 68 concern-table rows, 42 notes and 62 workbook text rows retain their own F6 "
              "strata. These are not one-to-one event denominators. Their source counts are verified, "
              "but neither addition across strata nor subtraction from constituted-event coverage "
              "is performed. Numeric deltas for those three rows remain null in both universes.", "",
              "There are two additional unit-universe defects in the inherited Step 5 loader. "
              "Damage Path A has 48 PATHA-NOTE-EVENT keys outside its constituted event inventory. "
              "B2's imported family_for_path function recognizes sanitized directory tokens rather "
              "than the original input roots, yielding SNAPSHOT_FAMILY_UNKNOWN/unknown. None of the "
              "57 Cause or 110 Damage historical B2 keys matches the reconstructed Step 5 keys. "
              "These are not evaluation exclusions or evidence of signal loss. Their F6 deltas are "
              "also null. B2 coverage is an exact replica of the inherited Step 5 universe, provisional "
              "pending an explicit source-identity repair and a re-audit of grouping and exclusions. "
              "No upstream frozen script or G2.0c membership was silently repaired.", "",
              "## Limits", "",
              "A reference phrase hit is not a confirmed symptom, physical damage mechanism, causal "
              "relation, subsystem assignment or SAP label. Failure modes, fault events and damage "
              "mechanisms remain distinguished in the inventory and source-specific report. Shared "
              "phrases can support several source scopes; source counts must not be summed.", "",
              "Exact matching can miss inflections and unlisted expressions. Full canonical phrases "
              "containing conjunctions or slashes are normalized as whole phrases, not split into "
              "new seeds. Zero matches do not establish zero underlying signal. Historical F6 methods "
              "include semantic detectors; the contrast is descriptive, not an isolated causal estimate "
              "of catalogue over-generation. No expected outcome was used to choose rules.", "",
              "No raw corpus text is emitted. G2.0c outputs, evaluation artifacts and F6 are unchanged. "
              "G2.0e, new annotation, training, promotion and denominator updates were not started."]
    (OUT / "g20d_memo.md").write_text("\n".join(lines)+"\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("freeze", "measure"))
    args = parser.parse_args()
    freeze() if args.phase == "freeze" else measure()
