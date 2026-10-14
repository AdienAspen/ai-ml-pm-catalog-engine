"""G2.0k.6: exact-description overlap and strong-crosswalk profile membership."""

import argparse
import csv
import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from openpyxl import load_workbook

import g20i_component_resolution as base
import g20k5_component_profile_comparison as k5

OUT = k5.OUT
PRIVATE = k5.PRIVATE
PLAN = base.STINT2 / "docs/PLAN-G2.0k.6—semantic-disjunct-crosswalk-membership.md"
K5_DETAIL = PRIVATE / "g20k5_codeset_detail.csv"
K5_COUNTS = OUT / "g20k5_codeset_comparison_sanitized.csv"
K5_MANIFEST = OUT / "g20k5_run_manifest.json"
SEMANTIC_OUT = OUT / "g20k6_semantic_overlap_sanitized.csv"
MEMBERSHIP_OUT = OUT / "g20k6_crosswalk_membership_sanitized.csv"
DETAIL_OUT = PRIVATE / "g20k6_detail.csv"
MEMO_OUT = OUT / "g20k6_memo.md"
RUN_MANIFEST = OUT / "g20k6_run_manifest.json"
MEMBER_CLASSES = (
    "in_component_profile", "in_pmmuww", "in_other_profile",
    "in_no_profile", "not_in_catalog",
)


def normalized_description(value):
    return re.sub(r"\s+", " ", str(value).strip().lower())


def row_pairs(value):
    return set(value.split("|")) if value else set()


def catalog_with_descriptions():
    workbook = load_workbook(base.SOURCES[2], read_only=True, data_only=True)
    allowed = defaultdict(set)
    descriptions = {}
    multigroup = {}
    facts = {}
    try:
        profile_sheet = workbook["Catalog Profile and Code Groups"]
        profile_header = next(profile_sheet.values)
        if profile_header[:4] != (
            "Catalog Profile", "Description", "Catalog", "Code Group Search Pattern"
        ):
            raise ValueError("Q1 profile sheet columns differ")
        wildcard_count = 0
        for row in list(profile_sheet.values)[1:]:
            if not (row[0] and row[2] and row[3]):
                continue
            profile, typ, group = (str(row[i]).strip() for i in (0, 2, 3))
            wildcard_count += any(char in group for char in "*?%")
            allowed[(profile, typ)].add(group)
        facts["Q1"] = {
            "state": "confirmed" if wildcard_count == 0 else "differs",
            "source": "Wind Catalog Group and Codes Final v4.xlsx: Catalog Profile and Code Groups, columns A/C/D; g20k5_component_profile_comparison.py:catalogue/code_set",
            "profile_group_associations": sum(map(len, allowed.values())),
            "wildcard_rows": wildcard_count,
            "expansion": "exact group membership; no wildcard expansion" if wildcard_count == 0 else "not established",
        }
        for typ in k5.TYPES:
            sheet = workbook[f"Catalog. {typ} - Group and Code"]
            header = next(sheet.values)
            if header[:4] != ("Catalog", "Code Group", "Code", "Short Text for Code"):
                raise ValueError(f"Q2 sheet columns differ for {typ}")
            by_code = defaultdict(set)
            blank = 0
            conflicting = 0
            for row in list(sheet.values)[1:]:
                if str(row[0]).strip() != typ or not row[1] or not row[2]:
                    continue
                group, code = str(row[1]).strip(), str(row[2]).strip()
                desc = "" if row[3] is None else str(row[3]).strip()
                blank += not bool(desc)
                pair = (typ, group, code)
                if pair in descriptions and descriptions[pair] != desc:
                    conflicting += 1
                descriptions[pair] = desc
                by_code[code].add(group)
            multigroup[typ] = sum(len(groups) > 1 for groups in by_code.values())
            facts[f"Q5_{typ}"] = {
                "state": "confirmed", "distinct_codes_in_multiple_groups": multigroup[typ],
                "source": f"same workbook: Catalog. {typ} - Group and Code, columns B/C",
            }
            facts[f"Q2_{typ}"] = {"blank_descriptions": blank, "conflicting_pair_descriptions": conflicting}
    finally:
        workbook.close()
    q2_ok = all(facts[f"Q2_{typ}"]["blank_descriptions"] == 0 and
                facts[f"Q2_{typ}"]["conflicting_pair_descriptions"] == 0
                for typ in k5.TYPES)
    facts["Q2"] = {
        "state": "confirmed" if q2_ok else "differs",
        "source": "Wind Catalog Group and Codes Final v4.xlsx: Catalog. S/B/C/5/A - Group and Code, column D Short Text for Code",
        "language": "English text in one untagged description column; no locale field",
        "per_type": {typ: facts.pop(f"Q2_{typ}") for typ in k5.TYPES},
    }
    facts["Q5"] = {
        "state": "confirmed", "source": "same workbook, columns B/C grouped within catalogue type",
        "distinct_code_values_in_multiple_groups": multigroup,
    }
    return allowed, descriptions, facts


def preflight():
    k5.verify()
    if not PLAN.exists():
        raise FileNotFoundError(PLAN)
    allowed, descriptions, facts = catalog_with_descriptions()
    detail = k5.read_csv(K5_DETAIL)
    expected = {(row["target"], row["category"]): int(row["orders"])
                for row in k5.read_csv(K5_COUNTS)}
    actual = Counter()
    profile_sets = {}
    for row in detail:
        typ = row["catalogue_type"]
        target = k5.TYPES[typ]
        component = row_pairs(row["component_group_code_pairs"])
        turbine = row_pairs(row["turbine_group_code_pairs"])
        actual[(target, k5.classify(component, turbine))] += 1
        profile = row["component_rbnr"]
        key = (profile, typ)
        if key in profile_sets and profile_sets[key] != component:
            raise ValueError("Persisted sets differ within same RBNR")
        profile_sets[key] = component
        if row["turbine_rbnr"] != "PMMUWW":
            raise ValueError("Q3 persisted turbine profile differs")
    q3_ok = actual == Counter(expected) and len(detail) == 3217 * len(k5.TYPES)
    facts["Q3"] = {
        "state": "confirmed" if q3_ok else "differs",
        "source": "g20k5_codeset_detail.csv + g20k5_codeset_comparison_sanitized.csv; g20k5_run_manifest.json",
        "different_rbnr_orders": len(detail) // len(k5.TYPES),
        "distinct_component_rbnrs": len({r["component_rbnr"] for r in detail}),
        "category_replay_identical": q3_ok,
    }
    strong = k5.strong_crosswalk()
    profiles = k5.resolved_profiles()
    overlap = set(strong) & set(profiles)
    full_pairs = sum(len(pairs) for pairs in strong.values())
    overlap_pairs = sum(len(strong[key]) for key in overlap)
    q4_ok = (len(strong), len(overlap), full_pairs, overlap_pairs) == (3013, 1189, 5778, 1313)
    facts["Q4"] = {
        "state": "confirmed" if q4_ok else "differs",
        "source": "g11_item_signal_rows_sanitized.csv joined to g11_material_to_catalog_b_crosswalk_sanitized.csv; g20k5_component_profile_comparison.py:strong_crosswalk",
        "catalogue_type": "B", "strong_orders": len(strong),
        "full_pairs": full_pairs, "overlap_orders": len(overlap),
        "overlap_pairs": overlap_pairs,
    }
    if any(facts[q]["state"] != "confirmed" for q in ("Q1", "Q2", "Q3", "Q4", "Q5")):
        raise ValueError("G2.0k.6 pre-flight differs: " + json.dumps(facts, sort_keys=True))
    return allowed, descriptions, detail, profile_sets, strong, profiles, facts


def add_summary(rows, target, unit, view, counts, denominator):
    if sum(counts.values()) != denominator:
        raise ValueError(f"Semantic sum drift for {target}/{unit}/{view}")
    for category in k5.CLASSES:
        rows.append({
            "record_type": "summary", "target": target, "unit": unit,
            "view": view, "profile_id": "", "category": category,
            "count": counts[category], "denominator": denominator,
            "order_weight": "", "shared_code_values": "",
            "code_values_with_differing_descriptions": "",
            "code_values_with_no_shared_description": "",
            "sum_valid": True,
        })


def semantic_analysis(detail, descriptions):
    by_profile = defaultdict(list)
    for row in detail:
        by_profile[(row["component_rbnr"], row["catalogue_type"])].append(row)
    rows, private = [], []
    for typ, target in k5.TYPES.items():
        profiles = sorted(profile for profile, cat in by_profile if cat == typ)
        weights = {profile: len(by_profile[(profile, typ)]) for profile in profiles}
        if sum(weights.values()) != 3217:
            raise ValueError("Distinct RBNR weights do not sum to 3217")
        summary = {(unit, view): Counter() for unit in ("code_value", "description")
                   for view in ("distinct_rbnr", "order_weighted")}
        collision_unique = Counter()
        collision_weighted = Counter()
        for profile in profiles:
            entries = by_profile[(profile, typ)]
            representative = entries[0]
            cpairs = row_pairs(representative["component_group_code_pairs"])
            tpairs = row_pairs(representative["turbine_group_code_pairs"])
            for entry in entries[1:]:
                if row_pairs(entry["component_group_code_pairs"]) != cpairs or row_pairs(entry["turbine_group_code_pairs"]) != tpairs:
                    raise ValueError("Per-RBNR enabled sets not stable")
            def decode(pair):
                group, code = pair.split(":", 1)
                if (typ, group, code) not in descriptions:
                    raise ValueError("Persisted pair absent from catalogue descriptions")
                return group, code
            cdecoded = {decode(pair) for pair in cpairs}
            tdecoded = {decode(pair) for pair in tpairs}
            cdesc = {normalized_description(descriptions[(typ, g, c)]) for g, c in cdecoded}
            tdesc = {normalized_description(descriptions[(typ, g, c)]) for g, c in tdecoded}
            ccode = {code for _, code in cdecoded}
            tcode = {code for _, code in tdecoded}
            cdescription_by_code = defaultdict(set)
            tdescription_by_code = defaultdict(set)
            for group, code in cdecoded:
                cdescription_by_code[code].add(normalized_description(descriptions[(typ, group, code)]))
            for group, code in tdecoded:
                tdescription_by_code[code].add(normalized_description(descriptions[(typ, group, code)]))
            shared = ccode & tcode
            differing = sum(cdescription_by_code[code] != tdescription_by_code[code] for code in shared)
            no_shared = sum(not(cdescription_by_code[code] & tdescription_by_code[code]) for code in shared)
            weight = weights[profile]
            collision_unique.update({"shared": len(shared), "differing": differing, "no_shared": no_shared})
            collision_weighted.update({"shared": len(shared) * weight, "differing": differing * weight, "no_shared": no_shared * weight})
            safe_id = base.short_hash("RBNR", profile)
            for unit, cset, tset in (("code_value", ccode, tcode), ("description", cdesc, tdesc)):
                category = k5.classify(cset, tset)
                summary[(unit, "distinct_rbnr")][category] += 1
                summary[(unit, "order_weighted")][category] += weight
                rows.append({
                    "record_type": "rbnr", "target": target, "unit": unit,
                    "view": "distinct_rbnr", "profile_id": safe_id,
                    "category": category, "count": 1, "denominator": len(profiles),
                    "order_weight": weight, "shared_code_values": len(shared),
                    "code_values_with_differing_descriptions": differing,
                    "code_values_with_no_shared_description": no_shared,
                    "sum_valid": True,
                })
            for group, code in sorted(cdecoded | tdecoded):
                private.append({
                    "analysis": "semantic_rbnr", "population": "",
                    "order_id_hash": "",
                    "component_rbnr": profile, "target": target,
                    "catalogue_type": typ, "group": group, "code": code,
                    "description": descriptions[(typ, group, code)],
                    "in_component_profile": (group, code) in cdecoded,
                    "in_pmmuww": (group, code) in tdecoded,
                    "membership_category": "",
                    "other_enabling_rbnrs": "",
                })
        for (unit, view), counts in summary.items():
            add_summary(rows, target, unit, view, counts, len(profiles) if view == "distinct_rbnr" else 3217)
        for view, counts in (("distinct_rbnr", collision_unique), ("order_weighted", collision_weighted)):
            rows.append({
                "record_type": "code_description_control", "target": target,
                "unit": "code_value", "view": view, "profile_id": "",
                "category": "shared_code_value_description_comparison",
                "count": counts["shared"], "denominator": counts["shared"],
                "order_weight": "", "shared_code_values": counts["shared"],
                "code_values_with_differing_descriptions": counts["differing"],
                "code_values_with_no_shared_description": counts["no_shared"],
                "sum_valid": True,
            })
    return rows, private


def membership_analysis(allowed, descriptions, strong, profiles):
    all_profile_pairs = defaultdict(set)
    pair_enablers = defaultdict(set)
    for (profile, typ), groups in allowed.items():
        if typ != "B":
            continue
        for group, code in ((g, c) for cat, g, c in descriptions if cat == "B" and g in groups):
            all_profile_pairs[profile].add((group, code))
            pair_enablers[(group, code)].add(profile)
    pmmuww = all_profile_pairs["PMMUWW"]
    category_counts = defaultdict(Counter)
    multi_counts = Counter()
    mixed_counts = Counter()
    other_pair_profiles = defaultdict(list)
    private = []
    for population, keys in (("overlap", sorted(set(strong) & set(profiles))),
                             ("full", sorted(strong))):
        if len(keys) != (1189 if population == "overlap" else 3013):
            raise ValueError("Population order count drift")
        for key in keys:
            component = profiles.get(key)
            if len(strong[key]) > 1:
                multi_counts[population] += 1
            categories = set()
            for group, code in sorted(strong[key]):
                pair = (group, code)
                if component and pair in all_profile_pairs[component]:
                    category = "in_component_profile"
                elif pair in pmmuww:
                    category = "in_pmmuww"
                elif pair in pair_enablers:
                    category = "in_other_profile"
                    other_pair_profiles[population].append(pair_enablers[pair])
                elif ("B", group, code) in descriptions:
                    category = "in_no_profile"
                else:
                    category = "not_in_catalog"
                categories.add(category)
                category_counts[(population, "pair")][category] += 1
                private.append({
                    "analysis": "crosswalk_membership", "population": population,
                    "order_id_hash": key,
                    "component_rbnr": component or "", "target": "Object Part",
                    "catalogue_type": "B", "group": group, "code": code,
                    "description": descriptions.get(("B", group, code), ""),
                    "in_component_profile": bool(component and pair in all_profile_pairs[component]),
                    "in_pmmuww": pair in pmmuww,
                    "membership_category": category,
                    "other_enabling_rbnrs": "|".join(sorted(pair_enablers[pair])) if category == "in_other_profile" else "",
                })
            category_counts[(population, "order")][min(categories, key=MEMBER_CLASSES.index)] += 1
            mixed_counts[population] += len(categories) > 1
    expected = {"overlap": {"pair": 1313, "order": 1189},
                "full": {"pair": 5778, "order": 3013}}
    if multi_counts != Counter({"overlap": 97, "full": 821}) or mixed_counts["overlap"] > 97:
        raise ValueError("Multi-pair or mixed-membership count drift")
    rows = []
    for population in ("overlap", "full"):
        for unit in ("pair", "order"):
            counts = category_counts[(population, unit)]
            total = expected[population][unit]
            if sum(counts.values()) != total:
                raise ValueError(f"Membership sum drift: {population}/{unit}")
            for category in MEMBER_CLASSES:
                rows.append({
                    "population": population, "unit": unit,
                    "record_type": "category", "category": category,
                    "count": counts[category], "denominator": total,
                    "multi_pair_orders": multi_counts[population],
                    "mixed_membership_orders": mixed_counts[population],
                    "distinct_enabling_rbnrs": "", "top5_enabler_pair_share": "",
                    "sum_valid": True,
                })
        enabling = Counter()
        for enablers in other_pair_profiles[population]:
            for profile in enablers:
                enabling[profile] += 1
        top5 = [p for p, _ in enabling.most_common(5)]
        top5_covered = sum(bool(set(top5) & enablers) for enablers in other_pair_profiles[population])
        other_count = category_counts[(population, "pair")]["in_other_profile"]
        if len(other_pair_profiles[population]) != other_count:
            raise ValueError("Other-profile enabler accounting drift")
        rows.append({
            "population": population, "unit": "pair",
            "record_type": "other_profile_control", "category": "in_other_profile",
            "count": other_count, "denominator": expected[population]["pair"],
            "multi_pair_orders": multi_counts[population],
            "mixed_membership_orders": mixed_counts[population],
            "distinct_enabling_rbnrs": len(enabling),
            "top5_enabler_pair_share": round(top5_covered / other_count, 6) if other_count else "",
            "sum_valid": True,
        })
        for profile in top5:
            rows.append({
                "population": population, "unit": "pair",
                "record_type": "other_profile_top5",
                "category": base.short_hash("RBNR", profile),
                "count": enabling[profile], "denominator": other_count,
                "multi_pair_orders": multi_counts[population],
                "mixed_membership_orders": mixed_counts[population],
                "distinct_enabling_rbnrs": len(enabling),
                "top5_enabler_pair_share": round(top5_covered / other_count, 6) if other_count else "",
                "sum_valid": True,
            })
    return rows, private


def write_csv(path, rows):
    with path.open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    if len(k5.read_csv(path)) != len(rows):
        raise ValueError("Output round-trip row-count drift: " + str(path))


def run():
    allowed, descriptions, detail, _, strong, profiles, facts = preflight()
    targets = (SEMANTIC_OUT, MEMBERSHIP_OUT, DETAIL_OUT, MEMO_OUT, RUN_MANIFEST)
    if any(path.exists() for path in targets):
        raise FileExistsError("G2.0k.6 output already exists")
    semantic, semantic_detail = semantic_analysis(detail, descriptions)
    membership, membership_detail = membership_analysis(allowed, descriptions, strong, profiles)
    if not PRIVATE.is_dir() or PRIVATE.stat().st_mode & 0o777 != 0o700:
        raise PermissionError("Private directory mode is not 700")
    write_csv(DETAIL_OUT, semantic_detail + membership_detail)
    os.chmod(DETAIL_OUT, 0o600)
    write_csv(SEMANTIC_OUT, semantic)
    write_csv(MEMBERSHIP_OUT, membership)
    memo = [
        "# G2.0k.6 - semantic disjunction and crosswalk membership",
        "", "Diagnostic only; B1 only. Exact normalized description match is a conservative semantic proxy, not proof of equivalent meaning.",
        "", "## Pre-flight",
    ]
    for q in ("Q1", "Q2", "Q3", "Q4", "Q5"):
        memo += [f"- **{q}: {facts[q]['state']}** — {facts[q]['source']}. {json.dumps({key: value for key, value in facts[q].items() if key not in ('state', 'source')}, sort_keys=True)}"]
    memo += [
        "", "## Accounting",
        "- Distinct RBNR view: 17 component RBNRs per target; order-weighted view: 3,217 different-RBNR orders per target.",
        "- Crosswalk pair view: 1,313 overlap pairs and 5,778 full-set pairs.",
        "- Crosswalk order view: 1,189 overlap orders and 3,013 full-set orders. An order takes its highest-precedence pair category.",
        "- Multi-pair orders: 97 overlap; 821 full set. Mixed-membership counts are in the membership CSV, not a sixth category.",
        "- Shared code values are controls only; their descriptions may differ. See code_description_control rows.",
        "- Description-unit order-weighted categories: " + "; ".join(
            target + " " + ", ".join(
                row["category"] + "=" + str(row["count"])
                for row in semantic if row["record_type"] == "summary" and
                row["target"] == target and row["unit"] == "description" and
                row["view"] == "order_weighted" and int(row["count"]) > 0
            ) for target in k5.TYPES.values()
        ) + ".",
        "- Strong crosswalk full-set pair categories: " + ", ".join(
            row["category"] + "=" + str(row["count"])
            for row in membership if row["population"] == "full" and
            row["unit"] == "pair" and row["record_type"] == "category"
        ) + ". Top-five other-profile IDs and counts are anonymized in the membership CSV.",
        "- G1 crosswalk pairs are deterministic inference, not independent SAP assignments; membership is not correctness.",
        "- No order text, scoring, model replay, mapping promotion, or F6 denominator change.",
    ]
    MEMO_OUT.write_text("\n".join(memo) + "\n", encoding="utf-8")
    manifest = {
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "B1_diagnostic_only", "no_order_text_read": True,
        "no_replay_or_scoring": True, "promotion": False,
        "denominator_changed": False,
        "source_sha256": {str(p.relative_to(base.ROOT)): base.sha(p)
                          for p in (PLAN, K5_DETAIL, K5_COUNTS, K5_MANIFEST, base.SOURCES[2], k5.CROSSWALK, k5.ITEMS)},
        "output_sha256": {p.name: base.sha(p) for p in (SEMANTIC_OUT, MEMBERSHIP_OUT, MEMO_OUT)},
        "private_detail_sha256": base.sha(DETAIL_OUT),
        "private_file_mode": oct(DETAIL_OUT.stat().st_mode & 0o777),
        "private_directory_mode": oct(PRIVATE.stat().st_mode & 0o777),
    }
    RUN_MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"preflight": {q: facts[q]["state"] for q in ("Q1", "Q2", "Q3", "Q4", "Q5")},
                      "semantic_rows": len(semantic), "membership_rows": len(membership),
                      "private_rows": len(semantic_detail) + len(membership_detail)}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("preflight", "run"))
    args = parser.parse_args()
    if args.mode == "preflight":
        print(json.dumps(preflight()[-1], indent=2, sort_keys=True))
    else:
        run()
