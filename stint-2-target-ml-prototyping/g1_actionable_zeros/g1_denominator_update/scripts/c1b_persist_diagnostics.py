"""Persist C1b aggregates from existing private diagnostics, without promotion."""

import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "g1_actionable_zeros/g1_denominator_update/outputs"
PRIVATE_K6 = ROOT / "g2_baseline_models/internal/g20k_component_lift"
PRIVATE_F = ROOT / "g1_actionable_zeros/g11_object_part_crosswalk/internal/g11f_profile_constrained/g11f_detail.csv"
G20I = ROOT / "g2_baseline_models/outputs/g20i_profile_consensus/g20i_profile_consensus_by_order_sanitized.csv"


def records(path):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write(path, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)
    assert len(records(path)) == len(rows)


def normalized(value):
    return " ".join(value.strip().lower().split())


def k6_shares():
    detail = records(PRIVATE_K6 / "g20k6_detail.csv")
    k5 = records(PRIVATE_K6 / "g20k5_codeset_detail.csv")
    by_profile = defaultdict(lambda: (set(), set()))
    for row in detail:
        if row["analysis"] != "semantic_rbnr":
            continue
        component, turbine = by_profile[(row["target"], row["component_rbnr"])]
        description = normalized(row["description"])
        if row["in_component_profile"] == "True":
            component.add(description)
        if row["in_pmmuww"] == "True":
            turbine.add(description)
    targets = {"Symptom": ("S", 9.52, 41.61), "Object Part": ("B", 0.0, 0.0),
               "Damage": ("C", 48.43, 20.62), "Cause": ("5", 14.47, 43.76),
               "Activity": ("A", 22.76, 26.68)}
    rows = []
    for target, (typ, expected_component, expected_turbine) in targets.items():
        weights = Counter(r["component_rbnr"] for r in k5 if r["catalogue_type"] == typ)
        assert sum(weights.values()) == 3217 and len(weights) == 17
        shared = component_total = turbine_total = 0
        for profile, weight in weights.items():
            component, turbine = by_profile[(target, profile)]
            shared += weight * len(component & turbine)
            component_total += weight * len(component)
            turbine_total += weight * len(turbine)
        for metric, denominator, expected in [
            ("partition_share_component_description", component_total, expected_component),
            ("partition_share_pmmuww_description", turbine_total, expected_turbine),
        ]:
            figure = round(100 * shared / denominator, 2) if denominator else 0.0
            assert figure == expected, (target, metric, figure, expected)
            rows.append(dict(target=target, metric_id=metric, numerator=shared,
                             denominator=denominator, figure_percent=f"{figure:.2f}",
                             order_weighted_population=3217, distinct_component_profiles=17,
                             evidence_level="diagnostic, derived"))
    return rows


def g11f_agreement():
    sys.path.insert(0, str(ROOT / "g1_actionable_zeros/g11_object_part_crosswalk/scripts"))
    sys.path.insert(0, str(ROOT / "g2_baseline_models/scripts"))
    import g11_material_to_catalog_b_crosswalk as g11
    import g20k6_semantic_crosswalk_membership as k6

    by_order = defaultdict(list)
    for row in records(PRIVATE_F):
        by_order[row["order_id_hash"]].append(row)
    assert sum(map(len, by_order.values())) == 5778 and len(by_order) == 3013
    profiles = {r["order_id_hash"]: r["resolved_rbnr"] for r in records(G20I)
                if r["resolved_rbnr"]}
    old_pairs = {(r["order_id_hash"], r["crosswalk_group"], r["crosswalk_code"]): r
                 for r in records(PRIVATE_K6 / "g20k7_detail.csv")}
    assert len(old_pairs) == 5778
    allowed, _, _ = k6.catalog_with_descriptions()
    catalog = {(r["Code Group"], r["Code"]): r for r in g11.read_catalog_b()}
    enabled = {p: {pair for pair in catalog if pair[0] in groups}
               for (p, typ), groups in allowed.items() if typ == "B"}
    precedence = ["no_turbine_subtree", "original_code_available", "exact_equivalent",
                  "restricted_strong", "restricted_medium_weak", "no_enabled_codes_under_subtree",
                  "enabled_codes_no_score"]
    counts = Counter()
    for order, parts in by_order.items():
        if order not in profiles:
            continue
        candidates = sorted((r for r in parts if r["category"] in precedence[1:5]),
                            key=lambda r: (precedence.index(r["category"]), r["original_group"], r["original_code"]))
        if not candidates:
            continue
        winner = candidates[0]
        cohort = "prior_implied_none" if winner["prior_order_category"] == "implied_none" else "prior_implied_node"
        profile = profiles[order]
        counts[(cohort, "orders")] += 1
        if winner["category"] == "original_code_available":
            old = old_pairs[(order, winner["original_group"], winner["original_code"])]
            implied = set(old["implied_rbnrs"].split("|")) if old["implied_rbnrs"] else set()
            chosen_agrees = profile in implied
        else:
            chosen_agrees = winner["g20i_profile_agreement"] == "same_rbnr"
        counts[(cohort, "agreement_chosen_code")] += chosen_agrees
        selected_description = normalized(winner["selected_description"])
        selected_score = float(winner["selected_score"])
        profile_codes = enabled[profile]
        counts[(cohort, "agreement_identical_description")] += any(
            normalized(catalog[pair]["Short Text for Code"]) == selected_description
            for pair in profile_codes)
        counts[(cohort, "agreement_equal_score")] += any(
            g11.score_candidate(winner["material_description"], catalog[pair]["Short Text for Code"]) == selected_score
            for pair in profile_codes)
    assert counts[("prior_implied_node", "orders")] == 248
    assert counts[("prior_implied_none", "orders")] == 872
    expected = {"agreement_chosen_code": 54, "agreement_identical_description": 138,
                "agreement_equal_score": 143}
    assert all(sum(counts[(cohort, metric)] for cohort in ("prior_implied_node", "prior_implied_none")) == value
               for metric, value in expected.items())
    rows = []
    for cohort in ("prior_implied_node", "prior_implied_none", "all_comparable"):
        denominator = (sum(counts[(c, "orders")] for c in ("prior_implied_node", "prior_implied_none"))
                       if cohort == "all_comparable" else counts[(cohort, "orders")])
        for metric in expected:
            numerator = (sum(counts[(c, metric)] for c in ("prior_implied_node", "prior_implied_none"))
                         if cohort == "all_comparable" else counts[(cohort, metric)])
            rows.append(dict(target="Object Part", cohort=cohort, metric_id=metric,
                             numerator=numerator, denominator=denominator,
                             figure_percent=f"{100 * numerator / denominator:.2f}",
                             evidence_level="diagnostic, derived"))
    return rows


def main():
    shares = k6_shares()
    agreement = g11f_agreement()
    OUT.mkdir(parents=True, exist_ok=True)
    write(OUT / "c1b_g20k6_shared_descriptions_sanitized.csv", shares)
    write(OUT / "c1b_g11f_profile_agreement_sanitized.csv", agreement)
    print({"shared_description_rows": len(shares), "agreement_rows": len(agreement),
           "agreement_by_cohort": agreement})


if __name__ == "__main__":
    main()
