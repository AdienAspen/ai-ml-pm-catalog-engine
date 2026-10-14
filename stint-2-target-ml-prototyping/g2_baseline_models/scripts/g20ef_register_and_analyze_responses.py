"""Register originals, enforce structural gates, and report nominal agreement."""

from __future__ import annotations

import csv
import hashlib
import io
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from sklearn.metrics import cohen_kappa_score

import g20ef_validate_responses as validator

ROOT = validator.ROOT
OUT = ROOT / "g2_baseline_models/outputs/g20ef_blind_catalogue_code_annotation"
PROTOCOL = validator.PRIVATE / "protocol/g01-v2_protocol.md"
MANIFEST = OUT / "g20ef_sample_manifest_sanitized.csv"
ANNOTATORS = ("annotator_01", "annotator_02")
TARGETS = ("activity", "damage")
AC1_SOURCE = "https://pmc.ncbi.nlm.nih.gov/articles/PMC5965565/"
QUALIFIERS = {
    "path": "B1_RELATIONAL",
    "evaluation_set_type": "blind_llm_annotation_g01-v2_non_final",
    "threshold": "not_applicable_annotation_agreement",
    "eligible_for_final_heldout": False,
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def csv_text(rows: list[dict], fields: list[str]) -> str:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()


def save(name: str, content: str) -> None:
    path = OUT / name
    if path.exists():
        raise RuntimeError(f"Refusing to overwrite an existing registration: {path}")
    path.write_text(content, encoding="utf-8")


def read(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def path_for(target: str, annotator: str, kind: str) -> Path:
    stem = f"g20ef_{target}_g01-v2_{annotator}"
    if kind == "response":
        return validator.PRIVATE / "responses" / target / annotator / f"{stem}_response_received.csv"
    return validator.PRIVATE / "packages" / target / annotator / (
        f"{stem}.jsonl" if kind == "package" else f"{stem}_catalogue_codes.csv"
    )


def structural_issues(target: str, rows: list[dict], catalogue: list[dict]) -> list[dict]:
    issues = []
    codes = {row["code"] for row in catalogue}
    pairs = {(row["group"], row["code"]) for row in catalogue}
    groups = {group for group, _ in pairs}
    for position, row in enumerate(rows, start=2):
        reason = ""
        if None in row or any(value is None for value in row.values()):
            reason = "malformed_csv_field_count"
        elif target == "activity":
            if row["response"] not in codes | validator.ACTIVITY_EXITS:
                reason = "invalid_activity_response"
        else:
            group, code = row["group"], row["code"]
            if group in validator.LEVEL_ONE_EXITS:
                if code:
                    reason = "level_one_exit_requires_blank_code"
            elif group not in groups:
                reason = "invalid_damage_group"
            elif code != "abstain" and (group, code) not in pairs:
                reason = "invalid_damage_group_code_pair"
        if reason:
            issues.append({"csv_record_position": position, "annotation_id": row.get("annotation_id", ""), "reason": reason})
    return issues


def nominal_metrics(left: list[str], right: list[str], categories: list[str]) -> tuple[dict, list[dict], list[dict]]:
    assert len(left) == len(right) and left
    assert len(categories) >= 2 and len(set(categories)) == len(categories)
    assert set(left + right) <= set(categories)
    n = len(left)
    ca, cb = Counter(left), Counter(right)
    cells = Counter(zip(left, right))
    matching = sum(a == b for a, b in zip(left, right))
    observed = matching / n
    chance_kappa = sum(ca[c] * cb[c] for c in categories) / n**2
    kappa = (observed - chance_kappa) / (1 - chance_kappa) if chance_kappa < 1 else None
    pooled = [(ca[c] + cb[c]) / (2 * n) for c in categories]
    chance_ac1 = sum(p * (1 - p) for p in pooled) / (len(categories) - 1)
    ac1 = (observed - chance_ac1) / (1 - chance_ac1)
    if kappa is not None:
        reference = cohen_kappa_score(left, right, labels=categories)
        assert abs(reference - kappa) < 1e-12
    per_class = []
    for category in categories:
        a, b, common = ca[category], cb[category], cells[(category, category)]
        per_class.append({
            "category": category,
            "annotator_01_count": a,
            "annotator_02_count": b,
            "both_same_class": common,
            "specific_agreement": 2 * common / (a + b) if a + b else "",
            "status": "observed" if a + b else "unobserved_not_estimable",
        })
    matrix = [{"annotator_01_response": a, "annotator_02_response": b, "count": cells[(a, b)]}
              for a in categories for b in categories]
    result = {
        "n": n, "matching": matching, "disagreements": n - matching,
        "raw_agreement": observed, "cohen_kappa": kappa,
        "gwet_ac1": ac1, "ac1_category_count": len(categories),
        "kappa_chance_agreement": chance_kappa, "ac1_chance_agreement": chance_ac1,
    }
    return result, per_class, matrix


def main() -> None:
    protected = [PROTOCOL, MANIFEST]
    protected.extend(path_for(t, a, k) for t in TARGETS for a in ANNOTATORS
                     for k in ("response", "package", "catalogue"))
    before = {str(path.relative_to(ROOT)): digest(path) for path in protected}
    manifests = read(MANIFEST)
    registrations, defects, distributions, agreements = [], [], [], []
    batch_rows, statuses, overlap_details = {}, {}, {}
    for target in TARGETS:
        expected_shared = {row["annotation_id"] for row in manifests
                           if row["target"] == target and row["overlap_record"] == "True"}
        assert len(expected_shared) == 75
        for annotator in ANNOTATORS:
            path = path_for(target, annotator, "response")
            rows = read(path)
            package = [json.loads(line) for line in path_for(target, annotator, "package").read_text(encoding="utf-8").splitlines()]
            ids = [row.get("annotation_id", "") for row in rows]
            expected = {row["annotation_id"] for row in package}
            catalogue = read(path_for(target, annotator, "catalogue"))
            issues = structural_issues(target, rows, catalogue)
            try:
                result = validator.validate(target, annotator, path)
                status, reason = "valid", ""
            except (ValueError, AssertionError) as exc:
                result = {}
                status, reason = "rejected", str(exc)
            statuses[(target, annotator)] = status
            registrations.append({
                "target": target, "annotator_id": annotator,
                "response_file": str(path.relative_to(ROOT)), "sha256": digest(path),
                "received_via": "user_supplied_chat_csv", "protocol_version": "g01-v2",
                "rows": len(rows), "expected_rows": len(package),
                "duplicate_ids": len(ids) - len(set(ids)),
                "missing_ids": len(expected - set(ids)), "extra_ids": len(set(ids) - expected),
                "defective_rows": len(issues), "validation_status": status, "reason": reason,
                "annotation_date": "not_supplied", "original_patched": False,
                "raw_text_emitted": False,
            })
            for issue in issues:
                defects.append({"target": target, "annotator_id": annotator, **issue})
            batch_rows[(target, annotator)] = {row["annotation_id"]: row for row in rows}
            if status == "valid":
                label_counts = Counter(row["response"] if target == "activity" else row["group"] for row in rows)
                for label, count in sorted(label_counts.items()):
                    distributions.append({
                        **QUALIFIERS,
                        "target": target, "annotator_id": annotator, "level": "response" if target == "activity" else "group",
                        "category": label, "count": count, "n": len(rows), "fraction": count / len(rows),
                        "above_40pct": count / len(rows) > 0.40,
                        "abstention_rate": label_counts["abstain"] / len(rows),
                        "scope": "assigned_annotation_sample_not_population",
                    })
        a, b = (batch_rows[(target, annotator)] for annotator in ANNOTATORS)
        shared = set(a) & set(b)
        assert shared == expected_shared, "Overlap drift"
        overlap_details[target] = {"shared_ids_present": len(shared), "matches_sample_manifest": True}
        if any(statuses[(target, annotator)] != "valid" for annotator in ANNOTATORS):
            for level in ("group", "group_code") if target == "damage" else ("response",):
                agreements.append({"target": target, "level": level, "status": "blocked_invalid_batch",
                                   "n": "", "raw_agreement": "", "cohen_kappa": "", "gwet_ac1": "",
                                   "matching": "", "disagreements": "", "ac1_category_count": ""})
            continue
        assert target == "activity", "Damage needs separate two-level logic after both batches are valid"
        shared = sorted(shared)
        left = [a[key]["response"] for key in shared]
        right = [b[key]["response"] for key in shared]
        catalogue = read(path_for(target, ANNOTATORS[0], "catalogue"))
        categories = sorted({row["code"] for row in catalogue} | validator.ACTIVITY_EXITS)
        metric, classes, matrix = nominal_metrics(left, right, categories)
        assert "TEST" not in left + right, "Update the memo: TEST occurs in the overlap"
        classes = [{**QUALIFIERS, "n": len(shared), **row} for row in classes]
        matrix = [{**QUALIFIERS, "n": len(shared), **row} for row in matrix]
        agreements.append({"target": target, "level": "response", "status": "valid", **metric})
        save("g20ef_activity_per_class_agreement_sanitized.csv", csv_text(classes, list(classes[0])))
        save("g20ef_activity_confusion_matrix_sanitized.csv", csv_text(matrix, list(matrix[0])))
        paired = [{"annotation_id": key, "annotator_01_response": a[key]["response"],
                   "annotator_02_response": b[key]["response"], "agreement": a[key]["response"] == b[key]["response"]}
                  for key in shared]
        save("g20ef_activity_overlap_responses_sanitized.csv", csv_text(paired, list(paired[0])))

    agreement_fields = ["target", "level", "status", "n", "matching", "disagreements", "raw_agreement",
                        "cohen_kappa", "gwet_ac1", "ac1_category_count", "kappa_chance_agreement", "ac1_chance_agreement",
                        *QUALIFIERS]
    agreements = [{field: {**QUALIFIERS, **row}.get(field, "") for field in agreement_fields} for row in agreements]
    save("g20ef_response_receipt_register_sanitized.csv", csv_text(registrations, list(registrations[0])))
    save("g20ef_response_validation_defects_sanitized.csv", csv_text(defects, list(defects[0])))
    save("g20ef_class_distribution_sanitized.csv", csv_text(distributions, list(distributions[0])))
    save("g20ef_agreement_sanitized.csv", csv_text(agreements, agreement_fields))
    assert all(digest(ROOT / name) == value for name, value in before.items())
    run = {"registered_at_utc": datetime.now(timezone.utc).isoformat(),
           "inputs_sha256": before, "originals_unchanged": True,
           "overlap_integrity": overlap_details, "metrics": agreements,
           "evaluation_set_type": "blind_llm_annotation_g01-v2_non_final",
           "path": "B1_RELATIONAL", "threshold": "not_applicable_annotation_agreement",
           "eligible_for_final_heldout": False, "activity_frame_units": 1234,
           "ac1_method": "nominal_unweighted_fixed_complete_controlled_vocabulary",
           "ac1_formula_source": AC1_SOURCE,
           "annotator_models": "actual_round_model_identity_not_verified_from_csv",
           "annotation_process_compliance": "cannot_be_proven_from_csv_alone"}
    save("g20ef_response_analysis_run_manifest.json", json.dumps(run, indent=2, sort_keys=True) + "\n")
    activity = next(row for row in agreements if row["target"] == "activity")
    memo = f"""# G2.0e/G2.0f response registration and agreement

Four original user-supplied CSV batches are preserved unchanged in the private
responses tree (mode 600), separately from empty templates. No responses were
assigned, corrected, normalized, merged, or adjudicated by DevOps.

## Structural gate

Activity 01 and 02 are valid (187/188 rows). Damage 01 is rejected: 141 level-1
none_applicable outcomes have a nonempty code. Damage 02 is rejected: the last
record G20EF-DAMAGE-0293 has two CSV fields rather than three. Its intended code
is not inferred. All four batches have the package ID sets and the declared 75
shared IDs per target. Damage agreement at both levels is blocked, not zero.
Corrected whole-file resubmissions must come from the annotators; originals
remain available for provenance.

## Activity agreement

On the 75 shared physical units: {activity['matching']}/75 match;
raw agreement {activity['raw_agreement']:.6f}, Cohen kappa
{activity['cohen_kappa']:.6f}, Gwet AC1 {activity['gwet_ac1']:.6f}.
Full confusion and per-class specific agreement are separate sanitized files.
Specific agreement is 2*diagonal/(row marginal + column marginal); unobserved
classes are not estimable. AC1 uses all nine prespecified nominal categories,
not only categories observed in the overlap. Formula reference: {AC1_SOURCE}

Both Activity batches have zero abstentions; this is a process-review flag, not
proof of mechanical annotation. Activity 01 assigns TEST once, outside the
overlap; Activity 02 assigns no catalogue code. The 375 annotation responses
are not 375 unique units (300 unique units, including 75 shared). There is no
paired evidence to assess agreement on an assigned catalogue code.

Rates are annotation-sample summaries, not corpus-wide code-coverage estimates.
Activity was sampled only from the 1,234-unit frame left after exclusions. Every
metric is B1_RELATIONAL, g01-v2 blind-LLM non-final evaluation, n=75 for agreement,
with no classifier threshold. eligible_for_final_heldout remains false.
No SAP correctness, final-heldout performance, or definitive absence of corpus
signal follows from these agreement statistics. Damage conclusions await valid
resubmissions. Actual model identity and no-script compliance cannot be verified
from response values alone. No denominator or frozen evaluation set is changed.
"""
    save("g20ef_response_analysis_memo.md", memo)
    print(json.dumps({"receipt_statuses": registrations, "agreement": agreements}, indent=2))


if __name__ == "__main__":
    main()
