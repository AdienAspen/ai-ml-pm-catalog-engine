import csv
import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "g2_baseline_models/outputs/g20ef_blind_catalogue_code_annotation"
DEST = ROOT / "artifacts/evaluation_sets/evaluation_set_v2"
V1 = ROOT / "artifacts/evaluation_sets/evaluation_set_v1"


def read_csv(path):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv(path, fields, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    manifest = read_csv(SOURCE / "g20ef_sample_manifest_sanitized.csv")
    by_id = {row["annotation_id"]: row for row in manifest}
    assert len(manifest) == len(by_id) == 600
    receipt = read_csv(SOURCE / "g20ef_closing_response_receipt_register_sanitized.csv")
    assert len(receipt) == 4
    outputs = {"annotator_01": [], "annotator_02": []}
    response_maps = {}
    receipt_checks = []
    for item in receipt:
        target, annotator = item["target"], item["annotator_id"]
        assert target in {"activity", "damage"}
        assert annotator in outputs and item["validation_status"] == "valid"
        assert item["protocol_version"] == ("g01-v2.1" if target == "activity" else "g01-v2")
        path = ROOT / item["file"]
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest == item["sha256"], path
        rows = read_csv(path)
        expected = {row["annotation_id"] for row in manifest if row["target"] == target and annotator in row["assigned_annotators"].split("|")}
        ids = [row["annotation_id"] for row in rows]
        assert len(ids) == len(set(ids)) == len(expected) == int(item["rows"])
        assert set(ids) == expected
        response_maps[(target, annotator)] = {row["annotation_id"]: row for row in rows}
        for row in rows:
            source = by_id[row["annotation_id"]]
            if target == "activity":
                group, code, response = "", "", row["response"]
            else:
                group, code = row["group"], row["code"]
                response = group if not code else f"{group}|{code}"
                if group in {"none_applicable", "ambiguous_multi_process", "abstain"}:
                    assert not code
            outputs[annotator].append({
                "annotation_id": row["annotation_id"],
                "sampling_unit_key": f"{target.title()}|B1_RELATIONAL_TEXTUAL|{source['source_unit_key']}",
                "source_unit_key": source["source_unit_key"],
                "target": target.title(),
                "path": "B1_RELATIONAL_TEXTUAL",
                "response": response,
                "group": group,
                "code": code,
                "annotator_id": annotator,
                "annotator_model": "Claude Opus 5" if annotator == "annotator_01" else "GPT 5.6",
                "annotator_effort": "medium" if annotator == "annotator_01" else "not_supplied",
                "model_identity_source": "lead_user_attestation_not_csv",
                "evaluation_independence": "independent",
                "label_generation_method": "blind_llm_annotation",
                "evaluation_role": "diagnostic",
                "sampling_design": "simple_random_from_model_eligible_pool",
                "eligible_for_final_heldout": "false",
                "protocol_version": item["protocol_version"],
                "annotation_date": item["annotation_date"],
                "overlap_record": source["overlap_record"].lower(),
                "text_sha256": source["text_sha256"],
            })
        receipt_checks.append({"target": target, "annotator_id": annotator, "rows": len(rows), "sha256": digest})

    DEST.mkdir(parents=True, exist_ok=True)
    fields = list(outputs["annotator_01"][0])
    for annotator in outputs:
        write_csv(DEST / f"evaluation_set_v2_{annotator}.csv", fields, sorted(outputs[annotator], key=lambda r: r["annotation_id"]))

    overlap = []
    for source in manifest:
        if source["overlap_record"] != "True":
            continue
        target, aid = source["target"], source["annotation_id"]
        a = response_maps[(target, "annotator_01")][aid]
        b = response_maps[(target, "annotator_02")][aid]
        if target == "activity":
            aresponse, bresponse = a["response"], b["response"]
            group_agreement = "not_applicable"
        else:
            aresponse = a["group"] if not a["code"] else f"{a['group']}|{a['code']}"
            bresponse = b["group"] if not b["code"] else f"{b['group']}|{b['code']}"
            group_agreement = str(a["group"] == b["group"]).lower()
        overlap.append({
            "annotation_id": aid,
            "sampling_unit_key": f"{target.title()}|B1_RELATIONAL_TEXTUAL|{source['source_unit_key']}",
            "source_unit_key": source["source_unit_key"],
            "target": target.title(),
            "path": "B1_RELATIONAL_TEXTUAL",
            "annotator_01_response": aresponse,
            "annotator_02_response": bresponse,
            "group_agreement": group_agreement,
            "response_agreement": str(aresponse == bresponse).lower(),
            "protocol_version": "g01-v2.1" if target == "activity" else "g01-v2",
            "evaluation_role": "diagnostic",
            "eligible_for_final_heldout": "false",
        })
    assert len(overlap) == 150
    write_csv(DEST / "evaluation_set_v2_overlap_agreement.csv", list(overlap[0]), sorted(overlap, key=lambda r: r["annotation_id"]))

    v2_keys = [{"sampling_unit_key": f"{row['target'].title()}|B1_RELATIONAL_TEXTUAL|{row['source_unit_key']}",
                "source_unit_key": row["source_unit_key"], "target": row["target"].title(),
                "path": "B1_RELATIONAL_TEXTUAL"} for row in manifest]
    assert len(v2_keys) == len({row["sampling_unit_key"] for row in v2_keys}) == 600
    v1_keys = read_csv(V1 / "evaluation_set_v1_training_exclusion_keys.csv")
    assert len(v1_keys) == len({row["sampling_unit_key"] for row in v1_keys}) == 900
    combined = {row["sampling_unit_key"]: row for row in v1_keys}
    collision = set(combined).intersection(row["sampling_unit_key"] for row in v2_keys)
    combined.update({row["sampling_unit_key"]: row for row in v2_keys})
    write_csv(DEST / "evaluation_set_v2_training_exclusion_keys.csv", list(v2_keys[0]), sorted(v2_keys, key=lambda r: r["sampling_unit_key"]))
    write_csv(DEST / "evaluation_set_v1_v2_training_exclusion_union.csv", list(v2_keys[0]), [combined[k] for k in sorted(combined)])
    counts = Counter((row["target"], row["path"]) for row in v2_keys)
    write_csv(DEST / "evaluation_set_v2_training_exclusion_counts.csv", ["target", "path", "excluded_units"],
              [{"target": t, "path": p, "excluded_units": n} for (t, p), n in sorted(counts.items())])
    write_csv(DEST / "evaluation_set_v2_target_admission_register.csv",
              ["target", "admission_status", "protocol_version", "evaluation_role", "eligible_for_final_heldout", "reason_or_note"],
              [{"target": "Activity", "admission_status": "REGISTER_DIAGNOSTIC", "protocol_version": "g01-v2.1",
                "evaluation_role": "diagnostic", "eligible_for_final_heldout": "false",
                "reason_or_note": "A3 rewrite; 1234-unit eligible pool affected by corpus-vocabulary exposure"},
               {"target": "Damage", "admission_status": "REGISTER_DIAGNOSTIC", "protocol_version": "g01-v2",
                "evaluation_role": "diagnostic", "eligible_for_final_heldout": "false",
                "reason_or_note": "9261-unit eligible pool with construction exclusions; no final held-out claim"}])
    agreement = []
    for target, filename, levels in [
        ("Activity", "g20e_activity_agreement_v21_sanitized.csv", {"response"}),
        ("Damage", "g20f_damage_agreement_sanitized.csv", {"group", "group_code"}),
    ]:
        for row in read_csv(SOURCE / filename):
            if row["level"] not in levels:
                continue
            stem = "g20e_activity_v21_response" if target == "Activity" else f"g20f_damage_{row['level']}"
            for suffix in ["_confusion_matrix_sanitized.csv", "_per_class_agreement_sanitized.csv"]:
                assert (SOURCE / (stem + suffix)).exists()
            agreement.append({"target": target, "level": row["level"], "n_overlap": row["n"],
                              "raw_agreement": row["raw_agreement"], "cohen_kappa": row["cohen_kappa"],
                              "gwet_ac1": row["gwet_ac1"], "source_file": str((SOURCE / filename).relative_to(ROOT)),
                              "confusion_matrix": str((SOURCE / (stem + "_confusion_matrix_sanitized.csv")).relative_to(ROOT)),
                              "per_class_agreement": str((SOURCE / (stem + "_per_class_agreement_sanitized.csv")).relative_to(ROOT)),
                              "evaluation_role": "diagnostic", "eligible_for_final_heldout": "false"})
    assert len(agreement) == 3 and all(int(r["n_overlap"]) == 75 for r in agreement)
    write_csv(DEST / "evaluation_set_v2_agreement_register.csv", list(agreement[0]), agreement)
    summary = {
        "status": "registered_diagnostic_non_final",
        "admitted_targets": ["Activity", "Damage"],
        "protocol_by_target": {"Activity": "g01-v2.1", "Damage": "g01-v2"},
        "evaluation_independence": "independent",
        "label_generation_method": "blind_llm_annotation",
        "evaluation_role": "diagnostic",
        "eligible_for_final_heldout": False,
        "sampled_units_per_target": 300,
        "overlap_units_per_target": 75,
        "responses_per_target": 375,
        "response_receipts": receipt_checks,
        "v1_exclusion_keys": len(v1_keys),
        "v2_exclusion_keys": len(v2_keys),
        "v1_v2_key_overlap": len(collision),
        "v1_v2_exclusion_union": len(combined),
        "training_assertion": len(combined) == len(v1_keys) + len(v2_keys) - len(collision),
        "agreement_register_rows": len(agreement),
        "model_identity": {"annotator_01": "Claude Opus 5", "annotator_02": "GPT 5.6"},
        "model_identity_source": "lead_user_attestation_not_csv",
        "annotator_effort": {"annotator_01": "medium", "annotator_02": "not_supplied"},
        "annotation_date": "not_supplied",
    }
    (DEST / "evaluation_set_v2_registration_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
