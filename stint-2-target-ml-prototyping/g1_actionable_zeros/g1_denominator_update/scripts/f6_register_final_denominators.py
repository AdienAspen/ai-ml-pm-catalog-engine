import csv
import os
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "g1_actionable_zeros/g1_denominator_update/outputs"
F6 = OUT / "f6_g20_committee_closure_denominator_table_sanitized.csv"
G11 = ROOT / "g1_actionable_zeros/g11_object_part_crosswalk/outputs/g11f_profile_constrained/g11f_order_categories_sanitized.csv"
G20C = ROOT / "g2_baseline_models/outputs/g20_corpus_native_domain_vocab/g20c_coverage_contrast_sanitized.csv"
G20D2 = ROOT / "g2_baseline_models/outputs/g20d2_semantic_reference_coverage/g20d2_detector_comparison_sanitized.csv"
G20J = ROOT / "g2_baseline_models/outputs/g20j_catalogue_code_coverage/g20j_noncoverage_partition_sanitized.csv"
G20K3 = ROOT / "g2_baseline_models/outputs/g20k_component_lift/g20k3_partition_summary_sanitized.csv"
G20K7 = ROOT / "g2_baseline_models/outputs/g20k_component_lift/g20k7_memo.md"
G20I = ROOT / "g2_baseline_models/outputs/g20i_component_resolution/g20i_profile_funnel_sanitized.csv"
G20EF = ROOT / "g2_baseline_models/outputs/g20ef_blind_catalogue_code_annotation"
G20OBJ = ROOT / "g2_baseline_models/outputs/g20_zero_shot_prototype_baseline/g20_object_part_b1_overlap_agreement_summary_sanitized.json"
C1B_K6 = OUT / "c1b_g20k6_shared_descriptions_sanitized.csv"
C1B_G11F = OUT / "c1b_g11f_profile_agreement_sanitized.csv"


def records(path):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def rel(path):
    assert path.exists(), path
    return Path(os.path.relpath(path, ROOT)).as_posix()


def main():
    rows = []

    def add(target, path, level, metric_id, unit, figure, source, evidence, layer, universe, condition, denominator="proxy_poc"):
        assert isinstance(figure, (int, float))
        rows.append(dict(target=target, path=path, level=level, metric_id=metric_id, unit=unit,
                         figure=figure, source_file=rel(source), evidence_level=evidence,
                         layer=layer, universe=universe, denominator_type=denominator, conditions=condition))

    f6 = records(F6)
    def f6row(target, path, dtype="proxy_poc"):
        matches = [r for r in f6 if (r["target"], r["path"], r["denominator_type"]) == (target, path, dtype)]
        assert len(matches) == 1, (target, path, dtype)
        return matches[0]

    b1 = "B1_RELATIONAL_TEXTUAL"
    bs = "B1_RELATIONAL_STRUCTURED"
    add("MAT", bs, "n/a", "volume_contractual", "order", int(f6row("Activity Type / MAT", bs, "contractual")["admitted_denominator_units"]), F6,
        "observed_structural_label", "deterministic", "full_b1_10749", "contractual denominator; direct field", "contractual")
    add("FLOC", bs, "turbine", "volume_structural_match", "order", int(f6row("FLOC turbine", bs)["admitted_denominator_units"]), F6,
        "structural", "deterministic", "full_b1_10749", "turbine granularity only; 50 out of scope")
    add("FLOC", bs, "component", "volume_frozen_zero", "order", int(f6row("FLOC leaf", bs)["admitted_denominator_units"]), F6,
        "structural", "operator decision", "full_b1_10749", "leaf not admitted; component profile is separate candidate evidence")

    g20i = records(G20I)
    op = [r for r in g20i if r["target"] == "Object Part" and r["turbine_rbnr"] == "PMMUWW"]
    assert op and {r["turbine_code_pair_count"] for r in op} == {"1"}
    add("Object Part", bs, "turbine", "enabled_codes_pmmuww", "pair", 1, G20I,
        "structural", "deterministic", "PMMUWW_profile", "one group-code pair enabled; answer space, not classified orders")

    shares = records(C1B_K6)
    assert len(shares) == 10 and {r["target"] for r in shares} == {"Symptom", "Object Part", "Damage", "Cause", "Activity"}
    for r in shares:
        assert r["evidence_level"] == "diagnostic, derived" and int(r["order_weighted_population"]) == 3217
        assert r["metric_id"] in {"partition_share_component_description", "partition_share_pmmuww_description"}
        add(r["target"], b1, "component", r["metric_id"], "percent_order_weighted_description_set",
            float(r["figure_percent"]), C1B_K6, "diagnostic, derived", "profile answer-space comparison",
            "g20k6_different_rbnr_orders_3217",
            f"{r['numerator']} shared description occurrences / {r['denominator']} denominator occurrences; "
            "each profile set weighted by its comparable order count; not a per-order hit rate")

    profile_agreement = records(C1B_G11F)
    assert len(profile_agreement) == 9
    for r in profile_agreement:
        assert r["evidence_level"] == "diagnostic, derived"
        assert r["metric_id"] in {"agreement_chosen_code", "agreement_identical_description", "agreement_equal_score"}
        assert r["cohort"] in {"all_comparable", "prior_implied_node", "prior_implied_none"}
        add("Object Part", b1, "component", f"{r['metric_id']}_{r['cohort']}", "order",
            int(r["numerator"]), C1B_G11F, "diagnostic, derived", "cross-signal agreement",
            f"g11f_{r['cohort']}_{r['denominator']}",
            f"{r['numerator']} / {r['denominator']} orders; profile membership/equivalence diagnostic, not precision")
    for cohort, expected in [("prior_implied_node", 248), ("prior_implied_none", 872)]:
        assert {int(r["denominator"]) for r in profile_agreement if r["cohort"] == cohort} == {expected}
        add("Object Part", b1, "component", f"volume_profile_agreement_cohort_{cohort}", "order",
            expected, C1B_G11F, "diagnostic, derived", "cross-signal agreement",
            "g11f_comparable_1120", "cohort count; restricted candidate and resolved G2.0i profile; no precision claim")

    c = [r for r in records(G20C) if r["universe"] == "descriptive_full_corpus" and r["path_bucket"] == "B1_RELATIONAL"]
    assert len(c) == 2
    for target, expected in [("Object Part", 7668), ("Activity", 7606)]:
        r = next(r for r in c if r["target"] == target)
        assert int(r["path_units"]) == 10749 and int(r["units_with_domain_anchor"]) == expected
        add(target, b1, "component" if target == "Object Part" else "n/a", "volume_corpus_anchor", "order", expected, G20C,
            "semantic_candidate", "ML-addressable", "descriptive_full_corpus_10749", "not a validated code; vocabulary exact-match detector")

    import json
    op_agree = json.loads(G20OBJ.read_text(encoding="utf-8"))
    def find_kappa(obj):
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key in {"cohen_kappa", "kappa"} and isinstance(value, (int, float)):
                    return value
                result = find_kappa(value)
                if result is not None:
                    return result
        if isinstance(obj, list):
            for value in obj:
                result = find_kappa(value)
                if result is not None:
                    return result
        return None
    k = find_kappa(op_agree)
    assert k is not None and round(k, 3) == .671
    add("Object Part", b1, "component", "kappa_g20_diagnostic", "order", k, G20OBJ,
        "annotated agreement", "operator decision", "g20_diagnostic_overlap_75", "independent LLM annotation; not final held-out")

    add("Object Part", b1, "component", "volume_prior_f6_proxy", "order", int(f6row("Object Part", b1)["admitted_denominator_units"]), F6,
        "expert_inference", "ML-addressable", "full_b1_10749", "historical threshold-0.30 proxy; not interchangeable with corpus anchor volume")
    g11 = [r for r in records(G11) if r["population"] == "full"]
    cats = {r["category"]: int(r["orders"]) for r in g11}
    assert sum(cats.values()) == 3013 and cats["original_code_available"] == 1207
    pair_source = ROOT / "g1_actionable_zeros/g11_object_part_crosswalk/outputs/g11f_profile_constrained/g11f_pair_categories_sanitized.csv"
    pair_rows = records(pair_source)
    assert sum(int(r["pairs"]) for r in pair_rows) == 5778
    for metric, fig, unit, condition in [
        ("volume_crosswalk_orders", 3013, "order", "as built; orders with at least one strong pair"),
        ("volume_crosswalk_pairs", 5778, "pair", "as built; distinct order x group-code pairs"),
    ]:
        source = G11 if unit == "order" else pair_source
        add("Object Part", b1, "component", metric, unit, fig, source, "expert_inference", "deterministic", "crosswalk_strong_b1", condition)
    for category, fig in cats.items():
        add("Object Part", b1, "component", f"volume_crosswalk_{category}", "order", fig, G11,
            "semantic_candidate", "deterministic", "crosswalk_strong_3013", "profile-constrained first-match category; not validated precision")
    candidate = sum(cats[x] for x in ["original_code_available", "exact_equivalent", "restricted_strong", "restricted_medium_weak"])
    assert candidate == 2868
    add("Object Part", b1, "component", "volume_profile_constrained_candidate", "order", candidate, G11,
        "semantic_candidate", "deterministic", "crosswalk_strong_3013", "sum of four candidate categories; derived from same source; precision unvalidated")

    k3 = {r["category"]: int(r["orders"]) for r in records(G20K3)}
    assert sum(k3.values()) == 10749 and k3["resolved"] == 3935
    for category, fig in k3.items():
        add("FLOC", b1, "component", f"volume_component_{category}", "order", fig, G20K3,
            "semantic_candidate", "ML-addressable", "full_b1_10749", "first-failing-link partition; node/profile resolution, not code accuracy")
    assert '"unique_node_all": 2400' in G20K7.read_text(encoding="utf-8") and '"profile_only_all": 1535' in G20K7.read_text(encoding="utf-8")
    for metric, fig in [("volume_unique_node", 2400), ("volume_profile_consensus_ambiguous_node", 1535)]:
        add("FLOC", b1, "component", metric, "order", fig, G20K7,
            "semantic_candidate", "ML-addressable", "component_resolved_3935", "subdivision of resolved profile; no code-classification claim")

    activity = records(G20EF / "g20e_activity_agreement_v21_sanitized.csv")[0]
    for metric, field in [("kappa_g01_v21", "cohen_kappa"), ("ac1_g01_v21", "gwet_ac1"), ("agreement_raw_g01_v21", "raw_agreement")]:
        add("Activity", b1, "n/a", metric, "order", float(activity[field]), G20EF / "g20e_activity_agreement_v21_sanitized.csv",
            "annotated agreement", "operator decision", "g01_v21_overlap_75", "diagnostic; 1234 eligible sampling frame; final held-out false")
    overlap = records(G20EF / "g20e_activity_v21_overlap_responses_sanitized.csv")
    both_gap = sum(r["annotator_01_response"] == r["annotator_02_response"] == "no_applicable_code" for r in overlap)
    assert len(overlap) == 75 and both_gap == 39
    add("Activity", b1, "n/a", "volume_overlap_work_no_code", "order", both_gap, G20EF / "g20e_activity_v21_overlap_responses_sanitized.csv",
        "annotated agreement", "operator decision", "g01_v21_overlap_75", "39 of 75; shared diagnostic units, not population rate")
    damage = records(G20EF / "g20f_damage_agreement_sanitized.csv")
    for d in damage:
        if d["level"] == "both_assigned_group_code":
            continue
        assert d["level"] in {"group", "group_code"}
        add("Damage", b1, "n/a", f"kappa_g01_v2_{d['level']}", "order", float(d["cohen_kappa"]), G20EF / "g20f_damage_agreement_sanitized.csv",
            "annotated agreement", "operator decision", "g01_v2_overlap_75", "diagnostic; final held-out false")

    d2 = records(G20D2)
    j = records(G20J)
    for target, expected in [("Damage", 3078), ("Symptom", 104), ("Cause", 289)]:
        match = [r for r in d2 if r["target"] == target and r["path_bucket"] == "B1_RELATIONAL" and r["universe"] == "model_eligible_construction_corpus"]
        assert len(match) == 1 and int(match[0]["path_units"]) == 9263
        assert int(match[0]["broader_semantic_estimate"]) == expected
        add(target, b1, "n/a", "volume_external_semantic_d2", "order", expected, G20D2,
            "semantic_candidate", "ML-addressable", "model_eligible_9263", "128-token limit; external prototypes; presence only, no code accuracy")
    for target in ["Activity", "Cause", "Damage"]:
        add(target, b1, "n/a", "volume_prior_f6_proxy", "order", int(f6row(target, b1)["admitted_denominator_units"]), F6,
            "expert_inference", "ML-addressable", "frozen_stint1_b1", "historical catalogue-influenced proxy; do not equate with new domain-supported volume")
    symptom_prior = int(f6row("Symptom", "RELATIONAL_REASON")["admitted_denominator_units"])
    assert symptom_prior == 1827
    add("Symptom", "RELATIONAL_REASON", "n/a", "volume_prior_f6_proxy", "candidate_text_row_or_hash", symptom_prior, F6,
        "expert_inference", "ML-addressable", "frozen_stint1_relational_reason", "historical semantic proxy; different presence definition from G2.0d2/G2.0j")
    for target, expected, parts in [("Symptom", 106, (14, 86, 6)), ("Cause", 135, (14, 104, 17))]:
        scoped = [r for r in j if r["target"] == target and r["path_bucket"] == "B1_RELATIONAL" and
                  r["universe"] == "model_eligible_construction_corpus" and r["class_space"] == "profile_scoped"]
        wide = [r for r in j if r["target"] == target and r["path_bucket"] == "B1_RELATIONAL" and
                r["universe"] == "model_eligible_construction_corpus" and r["class_space"] == "catalogue_wide"]
        subset = {r["partition"]: int(r["units"]) for r in scoped}
        wider = {r["partition"]: int(r["units"]) for r in wide}
        assert sum(subset.values()) == sum(wider.values()) == 9263
        assert (subset["catalogue_and_domain"], subset["no_catalogue_code"] - wider["no_catalogue_code"], wider["no_catalogue_code"]) == parts
        add(target, b1, "n/a", "volume_domain_anchor_j", "order", expected, G20J,
            "semantic_candidate", "ML-addressable", "model_eligible_9263", "128-token limit; different presence prototypes from G2.0d2; do not subtract")
        for category, fig in [("candidate_under_pmmuww", parts[0]), ("candidate_catalogue_wide_only", parts[1]), ("no_catalogue_code", parts[2])]:
            add(target, b1, "n/a", f"volume_domain_{category}", "order", fig, G20J,
                "semantic_candidate", "ML-addressable", "model_eligible_9263", "profile-scoped partition; precision unvalidated")

    for old in f6:
        path = old["path"]
        if old["denominator_type"] != "proxy_poc" or path.startswith("DECLARED_") or path == "LEXICAL_LAYER_V2_HIGH_BAND":
            continue
        if path in {b1, bs}:
            continue
        if not (path.startswith("PATH_A") or path.startswith("B2_") or path == "RELATIONAL_REASON"):
            continue
        target = old["target"]
        if target == "Symptom" and path == "RELATIONAL_REASON":
            continue
        unit = {"physical_record_id": "order", "estimated_event": "estimated_event_key",
                "estimated_event_key_with_snapshot_date": "estimated_event_key",
                "candidate_text_row_or_hash": "candidate_text_row_or_hash"}.get(old["count_unit"], old["count_unit"])
        layer = "data preparation" if path.startswith(("PATH_A", "B2_")) else "ML-addressable"
        add(target, path, "n/a", "volume_frozen_f6", unit, int(old["admitted_denominator_units"]), F6,
            "provisional grouping", layer, "frozen_stint1_path_specific", "contingent on episode reconstruction; frozen F6 unit; no cross-path aggregation")

    path_a = ROOT / "../stint-1-evidence-ground-truth/phase_3_path_a_faultcodes/outputs/f354_snapshot_dedup_summary_sanitized.json"
    b25 = ROOT / "../stint-1-evidence-ground-truth/phase_4_path_b_xlsx/outputs/b25_grouping_refinement/b25_grouping_refinement_summary_sanitized.json"
    b22 = ROOT / "../stint-1-evidence-ground-truth/phase_4_path_b_xlsx/outputs/b2_snapshot_dedup/b22_snapshot_dedup_summary_sanitized.json"
    pa = json.loads(path_a.read_text(encoding="utf-8"))
    bd = json.loads(b25.read_text(encoding="utf-8"))
    bn = json.loads(b22.read_text(encoding="utf-8"))
    assert pa["snapshot_rows_evaluated"] == 602 and pa["estimated_events"] == 362
    assert bd["snapshot_text_rows"] == 1988 and bd["refined_events"] == 1857
    assert bn["snapshot_rows"] == 1988 and bn["estimated_events"] == 460
    add("Episode grouping", "PATH_A_PDF_EVENTS", "n/a", "compression_path_a", "event", float(pa["overall_compression_ratio"]), path_a,
        "provisional grouping", "data preparation", "stint1_path_a_602_rows", "602 rows / 362 estimated events; contingent on episode reconstruction")
    add("Episode grouping", "B2_WORKBOOK_SNAPSHOTS", "n/a", "compression_b2_with_date", "estimated_event_key", round(1988 / 1857, 2), b25,
        "provisional grouping", "data preparation", "stint1_b2_1988_rows", "1.07x rounded from persisted counts; date-sensitive grouping; contingent on episode reconstruction")
    add("Episode grouping", "B2_WORKBOOK_SNAPSHOTS", "n/a", "compression_b2_without_date", "estimated_event_key", float(bn["overall_compression_ratio"]), b22,
        "provisional grouping", "data preparation", "stint1_b2_1988_rows", "1988 rows / 460 estimated events without date; contingent on episode reconstruction")

    key = [(r["target"], r["path"], r["level"], r["metric_id"]) for r in rows]
    assert len(key) == len(set(key)), [x for x, n in Counter(key).items() if n > 1]
    assert all(r["unit"] and r["source_file"] and r["evidence_level"] and r["conditions"] for r in rows)
    output = OUT / "f6_final_denominators_sanitized.csv"
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, list(rows[0]))
        writer.writeheader()
        writer.writerows(sorted(rows, key=lambda r: (r["target"], r["path"], r["level"], r["metric_id"])))
    print({"rows": len(rows), "metric_ids": len({r["metric_id"] for r in rows}), "crosswalk_candidate": candidate})


if __name__ == "__main__":
    main()
