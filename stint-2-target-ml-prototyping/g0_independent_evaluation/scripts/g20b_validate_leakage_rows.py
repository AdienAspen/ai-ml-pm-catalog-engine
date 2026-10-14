import csv
import importlib.util
import os
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "g0_independent_evaluation/internal/g20_target_leakage_quantification/g20b_leaked_rows_deterministic_evidence_internal.csv"
INTERNAL = ROOT / "g0_independent_evaluation/internal/g20_target_leakage_quantification/g20b_leakage_validation_internal.csv"
OUTPUT = ROOT / "g0_independent_evaluation/outputs/g20_target_leakage_quantification/g20b_leakage_validation_sanitized.csv"
LOADER = ROOT / "g2_baseline_models/scripts/g20c_neutral_ngram_extraction.py"


def rows(path):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write(path, fields, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fields)
        writer.writeheader()
        writer.writerows(data)


def main():
    sys.path.insert(0, str(LOADER.parent))
    spec = importlib.util.spec_from_file_location("g20c_loader", LOADER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    source_rows = rows(SOURCE)
    assert len(source_rows) == len({r["source_unit_key"] for r in source_rows}) == 13
    keys = {r["source_unit_key"] for r in source_rows}
    texts = {unit["source_unit_key"]: " ".join(text for _, text in unit["segments"])
             for unit in module.load_b1_units() if unit["source_unit_key"] in keys}
    assert set(texts) == keys
    private = []
    public = []
    for item in source_rows:
        key = item["source_unit_key"]
        text = texts[key]
        value = item["leaked_value"]
        exact_match = bool(value) and value in text
        heading_present = bool(re.search(r"\b" + re.escape(item["label_variant"]) + r"\s*:", text, re.I))
        code = item["parsed_catalog_code"]
        code_pattern = bool(code and item["canonical_target"] == "Object Part" and
                            re.search(r"Object Part\s*:[^\r\n]{0,100}?\s-\s" + re.escape(code) + r"\s-\s", text, re.I))
        status = "validated" if exact_match else "rejected"
        public.append({"source_unit_key": key, "validation_status": status})
        private.append({
            "source_unit_key": key,
            "label_variant": item["label_variant"],
            "leaked_value": value,
            "extracted_value_exact_match": str(exact_match).lower(),
            "target_heading_present": str(heading_present).lower(),
            "parsed_code": code,
            "object_part_code_pattern_present": str(code_pattern).lower(),
            "validation_status": status,
        })
    assert len(public) == 13
    write(INTERNAL, list(private[0]), private)
    os.chmod(INTERNAL, 0o600)
    write(OUTPUT, list(public[0]), public)
    print({"rows": len(public), "validated_exact_values": sum(r["validation_status"] == "validated" for r in public),
           "rejected_extracted_spans": sum(r["validation_status"] == "rejected" for r in public),
           "headings_present": sum(r["target_heading_present"] == "true" for r in private),
           "object_part_code_patterns": sum(r["object_part_code_pattern_present"] == "true" for r in private)})


if __name__ == "__main__":
    main()
