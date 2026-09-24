"""Scoped publication gate; legacy repository-wide findings are not waived here."""

import csv
import hashlib
import json
import re
from pathlib import Path

from g20c_lexical_safety import TERMS_FILE, restricted_match, restricted_terms

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "g2_baseline_models/outputs/g20_corpus_native_domain_vocab"
REPORT = OUT / "g20c_release_gate_sanitized.json"


def allowed_code_collision(column, value):
    # The local project-name substring is also a valid frozen catalogue code.
    return (column == "code" and value == "MFSA") or (
        column == "catalogue_key" and bool(re.fullmatch(r"[AB]\|[A-Z0-9_]+\|MFSA", value))
    )


def main():
    restricted_terms()
    failures, exceptions, checked = [], [], []
    for path in sorted(OUT.iterdir()):
        if not path.is_file() or path == REPORT:
            continue
        if path.suffix not in {".csv", ".json", ".md"}:
            failures.append(dict(file=path.name, reason="unexpected_artifact_type"))
            continue
        text = path.read_text(encoding="utf-8")
        if re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text):
            failures.append(dict(file=path.name, reason="email_pattern"))
        if path.suffix == ".csv":
            with path.open(newline="", encoding="utf-8") as stream:
                reader = csv.DictReader(stream)
                forbidden = set(reader.fieldnames) & {
                    "text",
                    "text_pii_redacted",
                    "descriptionExtended",
                    "site_name",
                    "asset_identifier",
                    "order_id",
                }
                if forbidden:
                    failures.append(dict(file=path.name, reason="raw_columns"))
                if (
                    "reason" in reader.fieldnames
                    and path.name
                    != ("g20c_external_reference_augmentation_decisions_sanitized.csv")
                    and path.name != "g20c_release_removed_terms_sanitized.csv"
                ):
                    failures.append(dict(file=path.name, reason="unexpected_reason_column"))
                for line, row in enumerate(reader, 2):
                    if None in row or any(value is None for value in row.values()):
                        failures.append(dict(file=path.name, line=line, reason="csv_shape"))
                        continue
                    for column, value in row.items():
                        if restricted_match(value):
                            if allowed_code_collision(column, value):
                                exceptions.append(
                                    dict(
                                        file=path.name,
                                        line=line,
                                        field=column,
                                        reason="exact_frozen_catalogue_code_collision",
                                    )
                                )
                            else:
                                failures.append(
                                    dict(
                                        file=path.name,
                                        line=line,
                                        field=column,
                                        reason="restricted_content_value_withheld",
                                    )
                                )
                        if column in {"raw_operational_values_emitted", "raw_values_emitted"}:
                            if value.casefold() == "true":
                                failures.append(dict(file=path.name, line=line, reason="raw_flag"))
        else:
            if path.suffix == ".json":
                json.loads(text)
            if restricted_match(text):
                failures.append(dict(file=path.name, reason="restricted_content_value_withheld"))
        checked.append(dict(file=path.name, sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    result = dict(
        status="failed" if failures else "passed",
        scope="all_g20c_output_artifacts",
        policy_sha256=hashlib.sha256(TERMS_FILE.read_bytes()).hexdigest(),
        checked_files=checked,
        reviewed_catalogue_code_collisions=exceptions,
        failures=failures,
        repository_wide_checker_passed=False,
        repository_wide_checker_note=(
            "Legacy checker flags pre-existing project titles, source paths and catalogue-code "
            "substrings. This scoped result does not claim a clean legacy repository. "
            "Code source locators and project documentation are separately reviewed before staging."
        ),
        raw_operational_values_emitted=False,
    )
    REPORT.write_text(json.dumps(result, indent=2) + "\n")
    if failures:
        raise RuntimeError(f"Scoped publication gate failed: {failures}")
    print(f"Scoped publication gate PASS: {len(checked)} artefacts, {len(exceptions)} code cells")


if __name__ == "__main__":
    main()
