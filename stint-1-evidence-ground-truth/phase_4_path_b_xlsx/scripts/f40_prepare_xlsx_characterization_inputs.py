"""Prepare controlled inputs for F4.0 XLSX characterization.

This is not a parser and does not emit candidate evidence. It creates a
sanitized sample manifest and positive-control hashes for a bounded XLSX
document-family characterization pass.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from openpyxl import load_workbook


PROJECT_ROOT = Path(__file__).resolve().parents[3]
STINT_ROOT = PROJECT_ROOT / "stint-1-evidence-ground-truth"
PATH_B_DIR = STINT_ROOT / "phase_4_path_b_xlsx"
OUTPUT_DIR = PATH_B_DIR / "outputs" / "f40_xlsx_characterization"
INTERNAL_DIR = PROJECT_ROOT / "reports" / "internal" / "f40_xlsx_characterization"
DATA_ROOT = PROJECT_ROOT / "data"

MAX_SAMPLE_FILES = 4
MAX_SHEETS_FOR_CONTROL = 10
MAX_ROWS_FOR_CONTROL = 16


@dataclass(frozen=True)
class WorkbookCandidate:
    path: Path
    package_key: str
    family_key: str
    date_sort_key: str
    file_size_bytes: int


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_hash(value: object, length: int = 16) -> str:
    raw = "" if value is None else str(value)
    return hashlib.sha256(raw.encode("utf-8", errors="ignore")).hexdigest()[:length]


def prefixed_hash(value: object, prefix: str, length: int = 12) -> str:
    return f"{prefix}-{stable_hash(value, length)}"


def as_text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def path_is_reference(path: Path) -> bool:
    lowered = "/".join(part.lower() for part in path.parts)
    reference_markers = [
        "/references/",
        "/mapping/",
        "catalog",
        "canonical_field_matrix",
        "ih06",
        "ih08",
        "historical orders",
    ]
    return any(marker in lowered for marker in reference_markers)


def package_key(path: Path) -> str:
    for part in path.parts:
        if part.startswith("package_"):
            return prefixed_hash(part, "PKG", 10)
    return "PKG-unclassified"


def family_key(path: Path) -> str:
    parts = list(path.parts)
    package_index = next((i for i, part in enumerate(parts) if part.startswith("package_")), None)
    if package_index is None:
        seed = "/".join(parts[-4:-1])
    else:
        after_package = [part for part in parts[package_index + 1 : -1] if part.lower() not in {"data", "latest"}]
        seed = "/".join(after_package[:2] or after_package[:1] or [parts[package_index]])
    return prefixed_hash(seed, "FAM", 10)


def date_sort_key(path: Path) -> str:
    text = "/".join(path.parts)
    patterns = [
        r"(20\d{2})[-_ .](\d{1,2})[-_ .](\d{1,2})",
        r"(\d{1,2})[-_ .](\d{1,2})[-_ .](20\d{2})",
        r"(20\d{2})\s+(\d{1,2})\s+(\d{1,2})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        groups = [int(value) for value in match.groups()]
        if groups[0] > 1900:
            year, month, day = groups
        elif groups[2] > 1900:
            month, day, year = groups
        else:
            continue
        return f"{year:04d}-{month:02d}-{day:02d}"
    return "9999-99-99"


def discover_candidates() -> list[WorkbookCandidate]:
    candidates: list[WorkbookCandidate] = []
    for path in sorted(DATA_ROOT.rglob("*")):
        if path.suffix.lower() not in {".xlsx", ".xlsm", ".xls"}:
            continue
        if path_is_reference(path):
            continue
        try:
            size = path.stat().st_size
        except OSError:
            continue
        candidates.append(
            WorkbookCandidate(
                path=path,
                package_key=package_key(path),
                family_key=family_key(path),
                date_sort_key=date_sort_key(path),
                file_size_bytes=size,
            )
        )
    return candidates


def choose_sample(candidates: list[WorkbookCandidate]) -> list[WorkbookCandidate]:
    by_family: dict[str, list[WorkbookCandidate]] = {}
    for candidate in candidates:
        by_family.setdefault(candidate.family_key, []).append(candidate)

    selected: list[WorkbookCandidate] = []
    ranked_families = sorted(
        by_family.items(),
        key=lambda item: (-len(item[1]), item[0]),
    )
    for _, family_candidates in ranked_families:
        ordered = sorted(family_candidates, key=lambda item: (item.date_sort_key, item.path.name))
        selected.append(ordered[len(ordered) // 2])
        if len(selected) >= MAX_SAMPLE_FILES:
            break
    return selected


def size_band(size: int) -> str:
    if size < 1_000_000:
        return "lt_1mb"
    if size < 20_000_000:
        return "lt_20mb"
    return "gte_20mb_streaming_required"


def inspect_positive_control(path: Path) -> dict[str, object]:
    control: dict[str, object] = {
        "read_status": "not_started",
        "sheet_count": 0,
        "sheet_index": None,
        "sheet_name": "",
        "header_row_index": None,
        "header_hashes": [],
        "text_marker_hash": "",
        "text_marker_word_count": 0,
        "error_type": "",
    }
    try:
        wb = load_workbook(path, read_only=True, data_only=True)
        control["read_status"] = "opened"
        sheet_names = wb.sheetnames[:MAX_SHEETS_FOR_CONTROL]
        control["sheet_count"] = len(wb.sheetnames)
        if not sheet_names:
            control["read_status"] = "no_sheets"
            return control

        ws = wb[sheet_names[0]]
        control["sheet_index"] = 0
        control["sheet_name"] = sheet_names[0]
        rows = []
        for idx, row in enumerate(ws.iter_rows(max_row=MAX_ROWS_FOR_CONTROL, values_only=True)):
            rows.append((idx, [as_text(value) for value in row]))

        header_idx = None
        header_values: list[str] = []
        for idx, values in rows:
            non_empty = [value for value in values if value]
            if len(non_empty) >= 2:
                header_idx = idx
                header_values = non_empty[:40]
                break
        control["header_row_index"] = header_idx
        control["header_hashes"] = [prefixed_hash(value.lower(), "HDR", 10) for value in header_values]

        marker = ""
        if header_idx is not None:
            for idx, values in rows:
                if idx <= header_idx:
                    continue
                for value in values[:40]:
                    words = re.findall(r"[A-Za-z0-9]+", value)
                    if len(words) >= 2:
                        marker = value
                        break
                if marker:
                    break
        if marker:
            control["text_marker_hash"] = prefixed_hash(marker.lower(), "TXT", 12)
            control["text_marker_word_count"] = len(re.findall(r"[A-Za-z0-9]+", marker))
        control["read_status"] = "control_ready"
        wb.close()
    except Exception as exc:  # noqa: BLE001 - report type only, not raw data.
        control["read_status"] = "read_failed"
        control["error_type"] = type(exc).__name__
    return control


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    INTERNAL_DIR.mkdir(parents=True, exist_ok=True)

    candidates = discover_candidates()
    sample = choose_sample(candidates)

    sanitized_rows: list[dict[str, object]] = []
    internal_rows: list[dict[str, object]] = []
    positive_rows: list[dict[str, object]] = []
    for index, candidate in enumerate(sample, start=1):
        sample_id = f"F40-XLSX-SAMPLE-{index:03d}"
        path_hash = prefixed_hash(candidate.path.as_posix(), "PATH", 12)
        control = inspect_positive_control(candidate.path)
        temporal_rank = sorted({item.date_sort_key for item in candidates if item.family_key == candidate.family_key}).index(
            candidate.date_sort_key
        )

        sanitized_rows.append(
            {
                "sample_id": sample_id,
                "path_hash": path_hash,
                "package_key": candidate.package_key,
                "family_key": candidate.family_key,
                "extension": candidate.path.suffix.lower(),
                "file_size_bytes": candidate.file_size_bytes,
                "size_band": size_band(candidate.file_size_bytes),
                "family_temporal_rank": temporal_rank,
                "selection_reason": "one_file_per_productive_xlsx_family_spread_by_family",
                "raw_operational_values_emitted": False,
            }
        )
        internal_rows.append(
            {
                "sample_id": sample_id,
                "path_hash": path_hash,
                "raw_path": str(candidate.path),
                "package_key": candidate.package_key,
                "family_key": candidate.family_key,
                "date_sort_key": candidate.date_sort_key,
                "sheet_name_for_control": control["sheet_name"],
            }
        )
        positive_rows.append(
            {
                "sample_id": sample_id,
                "path_hash": path_hash,
                "read_status": control["read_status"],
                "sheet_count": control["sheet_count"],
                "control_sheet_index": control["sheet_index"],
                "header_row_index": control["header_row_index"],
                "header_hash_count": len(control["header_hashes"]),
                "first_header_hash": control["header_hashes"][0] if control["header_hashes"] else "",
                "text_marker_hash": control["text_marker_hash"],
                "text_marker_word_count": control["text_marker_word_count"],
                "error_type": control["error_type"],
                "raw_operational_values_emitted": False,
            }
        )

    write_csv(
        OUTPUT_DIR / "f40_xlsx_file_sample_manifest_sanitized.csv",
        sanitized_rows,
        [
            "sample_id",
            "path_hash",
            "package_key",
            "family_key",
            "extension",
            "file_size_bytes",
            "size_band",
            "family_temporal_rank",
            "selection_reason",
            "raw_operational_values_emitted",
        ],
    )
    write_csv(
        INTERNAL_DIR / "f40_xlsx_file_sample_manifest_internal.csv",
        internal_rows,
        [
            "sample_id",
            "path_hash",
            "raw_path",
            "package_key",
            "family_key",
            "date_sort_key",
            "sheet_name_for_control",
        ],
    )
    write_csv(
        OUTPUT_DIR / "f40_xlsx_positive_control_check_sanitized.csv",
        positive_rows,
        [
            "sample_id",
            "path_hash",
            "read_status",
            "sheet_count",
            "control_sheet_index",
            "header_row_index",
            "header_hash_count",
            "first_header_hash",
            "text_marker_hash",
            "text_marker_word_count",
            "error_type",
            "raw_operational_values_emitted",
        ],
    )

    summary = {
        "created_at_utc": utc_now(),
        "pass_id": "F4.0-preflight",
        "productive_xlsx_candidates": len(candidates),
        "sample_files_selected": len(sample),
        "sample_family_count": len({item.family_key for item in sample}),
        "positive_controls_ready": sum(row["read_status"] == "control_ready" for row in positive_rows),
        "raw_operational_values_emitted": False,
        "outputs": {
            "sanitized_manifest": str(OUTPUT_DIR / "f40_xlsx_file_sample_manifest_sanitized.csv"),
            "sanitized_positive_controls": str(OUTPUT_DIR / "f40_xlsx_positive_control_check_sanitized.csv"),
            "internal_manifest": str(INTERNAL_DIR / "f40_xlsx_file_sample_manifest_internal.csv"),
        },
    }
    (OUTPUT_DIR / "f40_xlsx_preflight_summary_sanitized.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
