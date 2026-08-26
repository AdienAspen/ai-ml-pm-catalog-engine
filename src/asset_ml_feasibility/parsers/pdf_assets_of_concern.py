"""Safe structural parser for PDF Assets of Concern tables.

The parser uses the PDF text layer only to reconstruct table rows. It does not
emit raw operational values to versioned outputs.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import pandas as pd
import pdfplumber


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data"
REPORTS_DIR = PROJECT_ROOT / "reports"
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
INTERNAL_REPORTS_DIR = REPORTS_DIR / "internal"
INTERNAL_ARTIFACTS_DIR = ARTIFACTS_DIR / "internal"

PARSER_VERSION = "pdf_assets_of_concern_v1"
SECTION_NAME = "ASSETS OF CONCERN"
SECTION_BOUNDARIES = (
    "PLANNED WORK",
    "NOTES",
    "ASSET STATUS",
    "WEATHER",
    "SUMMARY",
)

STATE_CODES = {"T", "I", "S", "R", "M", "NC"}
EVENT_WORDS = {"Tripped", "Impacted", "Stopped", "Repair", "Maintenance", "No Communication"}


@dataclass(frozen=True)
class ParsedRow:
    relative_path: str
    file_name: str
    path_hash: str
    file_hash: str
    report_year_hint: str
    section: str
    asset: str
    state: str
    site_text: str
    fault_code: str
    event: str
    duration: str
    extraction_status: str


@dataclass(frozen=True)
class FileStatus:
    relative_path: str
    file_name: str
    path_hash: str
    file_hash: str
    report_year_hint: str
    read_status: str
    section_status: str
    page_count: int
    row_count: int
    non_empty_fault_code_rows: int
    distinct_fault_code_count: int
    event_present_rows: int
    duration_present_rows: int
    error_type: str
    raw_operational_values_emitted: bool = False


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_hash(value: str, length: int = 16) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="ignore")).hexdigest()[:length]


def relative_to_project(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        return path.name


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()[:16]


def infer_year(path: Path) -> str:
    match = re.search(r"(20\d{2})", path.as_posix())
    return match.group(1) if match else "unknown"


def list_pdf_files() -> list[Path]:
    if not DATA_DIR.exists():
        return []
    return sorted(DATA_DIR.rglob("*.pdf"))


def extract_pages(path: Path) -> tuple[list[str], int]:
    pages: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text(x_tolerance=1, y_tolerance=3) or ""
            pages.append(text)
        page_count = len(pdf.pages)
    return pages, page_count


def detect_sections(full_text: str) -> dict[str, bool]:
    upper = full_text.upper()
    return {
        "asset_status": "ASSET STATUS" in upper,
        "notes": "NOTES" in upper,
        "assets_of_concern": SECTION_NAME in upper,
        "planned_work": "PLANNED WORK" in upper,
        "fault_code": "FAULT CODE" in upper,
    }


def extract_assets_section(full_text: str) -> str:
    upper = full_text.upper()
    start = upper.find(SECTION_NAME)
    if start < 0:
        return ""

    section = full_text[start:]
    section_upper = section.upper()
    end_positions = [
        section_upper.find(boundary)
        for boundary in SECTION_BOUNDARIES
        if boundary != SECTION_NAME and section_upper.find(boundary) > 0
    ]
    if end_positions:
        section = section[: min(end_positions)]
    return section


def is_noise_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return True
    upper = stripped.upper()
    if upper == SECTION_NAME:
        return True
    if "ASSET STATE SITE FAULT CODE EVENT DURATION" in upper:
        return True
    if "UTC" in upper and "TRIPPED" in upper and "REPAIR" in upper:
        return True
    if "NO DATA AVAILABLE" in upper:
        return True
    return False


def parse_duration_suffix(value: str) -> tuple[str, str]:
    patterns = [
        r"(?P<duration>\d+d\s+\d+h)$",
        r"(?P<duration>\d+d\s+\d+m)$",
        r"(?P<duration>\d+h\s+\d+m)$",
        r"(?P<duration>\d+d)$",
        r"(?P<duration>\d+h)$",
        r"(?P<duration>\d+m)$",
    ]
    stripped = value.strip()
    for pattern in patterns:
        match = re.search(pattern, stripped)
        if match:
            duration = match.group("duration").strip()
            prefix = stripped[: match.start()].strip()
            return prefix, duration
    return stripped, ""


def split_structured_row(line: str) -> dict[str, str] | None:
    line = re.sub(r"\s+", " ", line.strip())
    match = re.match(r"^(?P<asset>\d+)\s+(?P<state>[A-Z]{1,2})\s+(?P<body>.+)$", line)
    if not match:
        return None
    state = match.group("state")
    if state not in STATE_CODES:
        return None

    body_without_duration, duration = parse_duration_suffix(match.group("body"))
    tokens = body_without_duration.split()
    code_index: int | None = None
    for index, token in enumerate(tokens):
        if token == "-" or re.fullmatch(r"\d{2,5}", token):
            code_index = index
            break
    if code_index is None or code_index == 0:
        return None

    site_text = " ".join(tokens[:code_index]).strip()
    fault_code = tokens[code_index].strip()
    event = " ".join(tokens[code_index + 1 :]).strip()

    return {
        "asset": match.group("asset"),
        "state": state,
        "site_text": site_text,
        "fault_code": fault_code,
        "event": event,
        "duration": duration,
    }


def merge_event_parts(parts: Iterable[str]) -> str:
    clean_parts = [re.sub(r"\s+", " ", part).strip(" -") for part in parts if part and part.strip(" -")]
    if not clean_parts:
        return "-"
    return " ".join(clean_parts).strip()


def parse_assets_section(section_text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    pending_event_lines: list[str] = []

    for raw_line in section_text.splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        if is_noise_line(line):
            continue

        parsed = split_structured_row(line)
        if parsed:
            parsed["event"] = merge_event_parts([*pending_event_lines, parsed.get("event", "")])
            pending_event_lines = []
            rows.append(parsed)
            continue

        if rows and not pending_event_lines:
            # Hold ambiguous wrapped text until the next row. If no next row appears,
            # it will be attached to the last parsed row after the loop.
            pending_event_lines.append(line)
        else:
            pending_event_lines.append(line)

    if rows and pending_event_lines:
        rows[-1]["event"] = merge_event_parts([rows[-1].get("event", ""), *pending_event_lines])

    return rows


def clean_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    cleaned: list[dict[str, str]] = []
    for row in rows:
        fault_code = str(row.get("fault_code", "")).strip()
        if not (fault_code == "-" or re.fullmatch(r"\d{2,5}", fault_code)):
            continue
        cleaned.append(
            {
                "asset": str(row.get("asset", "")).strip(),
                "state": str(row.get("state", "")).strip(),
                "site_text": str(row.get("site_text", "")).strip(),
                "fault_code": fault_code,
                "event": str(row.get("event", "")).strip() or "-",
                "duration": str(row.get("duration", "")).strip() or "-",
            }
        )
    return cleaned


def parse_pdf(path: Path) -> tuple[list[ParsedRow], FileStatus]:
    rel_path = relative_to_project(path)
    path_digest = stable_hash(rel_path)
    file_digest = file_hash(path)
    year_hint = infer_year(path)

    try:
        pages, page_count = extract_pages(path)
    except Exception as exc:  # noqa: BLE001 - recorded as status, not raised across batch
        status = FileStatus(
            relative_path=rel_path,
            file_name=path.name,
            path_hash=path_digest,
            file_hash=file_digest,
            report_year_hint=year_hint,
            read_status="read_error",
            section_status="not_read",
            page_count=0,
            row_count=0,
            non_empty_fault_code_rows=0,
            distinct_fault_code_count=0,
            event_present_rows=0,
            duration_present_rows=0,
            error_type=type(exc).__name__,
        )
        return [], status

    full_text = "\n".join(pages)
    section_flags = detect_sections(full_text)
    section_text = extract_assets_section(full_text)
    if not section_text:
        status = FileStatus(
            relative_path=rel_path,
            file_name=path.name,
            path_hash=path_digest,
            file_hash=file_digest,
            report_year_hint=year_hint,
            read_status="read_ok",
            section_status="section_missing",
            page_count=page_count,
            row_count=0,
            non_empty_fault_code_rows=0,
            distinct_fault_code_count=0,
            event_present_rows=0,
            duration_present_rows=0,
            error_type="",
        )
        return [], status

    parsed_rows = clean_rows(parse_assets_section(section_text))
    section_status = "ok" if parsed_rows else "empty_section"

    output_rows = [
        ParsedRow(
            relative_path=rel_path,
            file_name=path.name,
            path_hash=path_digest,
            file_hash=file_digest,
            report_year_hint=year_hint,
            section=SECTION_NAME,
            asset=row["asset"],
            state=row["state"],
            site_text=row["site_text"],
            fault_code=row["fault_code"],
            event=row["event"],
            duration=row["duration"],
            extraction_status="ok",
        )
        for row in parsed_rows
    ]

    non_empty_codes = [row["fault_code"] for row in parsed_rows if row["fault_code"] != "-"]
    status = FileStatus(
        relative_path=rel_path,
        file_name=path.name,
        path_hash=path_digest,
        file_hash=file_digest,
        report_year_hint=year_hint,
        read_status="read_ok",
        section_status=section_status,
        page_count=page_count,
        row_count=len(parsed_rows),
        non_empty_fault_code_rows=len(non_empty_codes),
        distinct_fault_code_count=len(set(non_empty_codes)),
        event_present_rows=sum(1 for row in parsed_rows if row["event"] != "-"),
        duration_present_rows=sum(1 for row in parsed_rows if row["duration"] != "-"),
        error_type="" if section_flags.get("assets_of_concern") else "assets_section_not_detected",
    )
    return output_rows, status


def select_validation_pdf(pdf_files: list[Path]) -> Path | None:
    for path in pdf_files:
        try:
            pages, _ = extract_pages(path)
        except Exception:
            continue
        full_text = "\n".join(pages).upper()
        if SECTION_NAME in full_text and "FAULT CODE" in full_text:
            rows = clean_rows(parse_assets_section(extract_assets_section("\n".join(pages))))
            if rows and any(row["fault_code"] != "-" for row in rows):
                return path
    return None


def validate_parser(pdf_path: Path) -> dict[str, object]:
    rows, status = parse_pdf(pdf_path)
    fault_codes = [row.fault_code for row in rows]
    invalid_codes = [
        code
        for code in fault_codes
        if code != "-" and not re.fullmatch(r"\d{2,5}", code)
    ]
    passed = (
        status.read_status == "read_ok"
        and status.section_status == "ok"
        and len(rows) > 0
        and status.non_empty_fault_code_rows > 0
        and not invalid_codes
    )
    return {
        "validation_passed": passed,
        "validation_file_hash": status.file_hash,
        "validation_path_hash": status.path_hash,
        "row_count": len(rows),
        "non_empty_fault_code_rows": status.non_empty_fault_code_rows,
        "invalid_fault_code_count": len(invalid_codes),
        "raw_operational_values_emitted": False,
    }


def build_internal_rows(rows: list[ParsedRow]) -> pd.DataFrame:
    return pd.DataFrame([row.__dict__ | {"raw_operational_values_emitted": True} for row in rows])


def build_internal_status(statuses: list[FileStatus]) -> pd.DataFrame:
    return pd.DataFrame([status.__dict__ for status in statuses])


def build_sanitized_file_profile(statuses: list[FileStatus]) -> pd.DataFrame:
    rows = []
    for status in statuses:
        rows.append(
            {
                "path_hash": status.path_hash,
                "file_hash": status.file_hash,
                "report_year_hint": status.report_year_hint,
                "read_status": status.read_status,
                "section_status": status.section_status,
                "page_count": status.page_count,
                "row_count": status.row_count,
                "non_empty_fault_code_rows": status.non_empty_fault_code_rows,
                "distinct_fault_code_count": status.distinct_fault_code_count,
                "event_present_rows": status.event_present_rows,
                "duration_present_rows": status.duration_present_rows,
                "error_type": status.error_type,
                "raw_operational_values_emitted": False,
            }
        )
    return pd.DataFrame(rows)


def build_internal_fault_profile(rows: list[ParsedRow]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=["fault_code", "frequency", "associated_event_count", "example_event", "example_state"])
    records = [row.__dict__ for row in rows if row.fault_code != "-"]
    if not records:
        return pd.DataFrame(columns=["fault_code", "frequency", "associated_event_count", "example_event", "example_state"])
    df = pd.DataFrame(records)
    grouped = (
        df.groupby("fault_code", dropna=False)
        .agg(
            frequency=("fault_code", "size"),
            associated_event_count=("event", "nunique"),
            example_event=("event", "first"),
            example_state=("state", "first"),
        )
        .reset_index()
        .sort_values(["frequency", "fault_code"], ascending=[False, True])
    )
    return grouped


def build_sanitized_fault_profile(rows: list[ParsedRow]) -> pd.DataFrame:
    internal = build_internal_fault_profile(rows)
    if internal.empty:
        return pd.DataFrame(
            columns=[
                "fault_code_hash",
                "fault_code_length",
                "fault_code_pattern",
                "frequency",
                "associated_event_count",
                "raw_operational_values_emitted",
            ]
        )
    output = internal.copy()
    output["fault_code_hash"] = output["fault_code"].map(stable_hash)
    output["fault_code_length"] = output["fault_code"].astype(str).str.len()
    output["fault_code_pattern"] = output["fault_code"].astype(str).map(
        lambda value: "numeric" if value.isdigit() else "placeholder_or_other"
    )
    output["raw_operational_values_emitted"] = False
    return output[
        [
            "fault_code_hash",
            "fault_code_length",
            "fault_code_pattern",
            "frequency",
            "associated_event_count",
            "raw_operational_values_emitted",
        ]
    ]


def write_outputs(rows: list[ParsedRow], statuses: list[FileStatus], validation: dict[str, object]) -> dict[str, object]:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    INTERNAL_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    INTERNAL_ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    internal_rows_path = INTERNAL_REPORTS_DIR / "pdf_assets_of_concern_rows.csv"
    internal_status_path = INTERNAL_REPORTS_DIR / "pdf_assets_of_concern_file_status.csv"
    internal_fault_profile_path = INTERNAL_REPORTS_DIR / "pdf_assets_of_concern_fault_code_profile.csv"

    sanitized_file_profile_path = REPORTS_DIR / "pdf_assets_of_concern_file_profile_sanitized.csv"
    sanitized_fault_profile_path = REPORTS_DIR / "pdf_assets_of_concern_fault_code_profile_sanitized.csv"
    sanitized_summary_path = ARTIFACTS_DIR / "pdf_assets_of_concern_summary_sanitized.json"
    internal_summary_path = INTERNAL_ARTIFACTS_DIR / "pdf_assets_of_concern_summary.json"

    internal_rows = build_internal_rows(rows)
    internal_status = build_internal_status(statuses)
    internal_fault_profile = build_internal_fault_profile(rows)
    sanitized_file_profile = build_sanitized_file_profile(statuses)
    sanitized_fault_profile = build_sanitized_fault_profile(rows)

    internal_rows.to_csv(internal_rows_path, index=False)
    internal_status.to_csv(internal_status_path, index=False)
    internal_fault_profile.to_csv(internal_fault_profile_path, index=False)
    sanitized_file_profile.to_csv(sanitized_file_profile_path, index=False)
    sanitized_fault_profile.to_csv(sanitized_fault_profile_path, index=False)

    read_ok = sum(1 for status in statuses if status.read_status == "read_ok")
    files_failed = len(statuses) - read_ok
    section_ok = sum(1 for status in statuses if status.section_status == "ok")
    section_missing = sum(1 for status in statuses if status.section_status == "section_missing")
    empty_sections = sum(1 for status in statuses if status.section_status == "empty_section")
    non_empty_code_rows = sum(status.non_empty_fault_code_rows for status in statuses)

    summary = {
        "created_at_utc": utc_now(),
        "parser_version": PARSER_VERSION,
        "files_listed": len(statuses),
        "files_read_ok": read_ok,
        "files_failed": files_failed,
        "assets_of_concern_ok_files": section_ok,
        "assets_of_concern_missing_files": section_missing,
        "assets_of_concern_empty_section_files": empty_sections,
        "extraction_rows": len(rows),
        "fault_code_non_empty_rows": non_empty_code_rows,
        "distinct_fault_code_count": int(internal_fault_profile.shape[0]),
        "validation": validation,
        "outputs": {
            "sanitized_file_profile_csv": str(sanitized_file_profile_path),
            "sanitized_fault_profile_csv": str(sanitized_fault_profile_path),
            "internal_rows_csv": str(internal_rows_path),
            "internal_file_status_csv": str(internal_status_path),
            "internal_fault_profile_csv": str(internal_fault_profile_path),
        },
        "raw_operational_values_emitted_in_versioned_outputs": False,
    }

    internal_summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    sanitized_summary = {
        key: value
        for key, value in summary.items()
        if key not in {"outputs"}
    }
    sanitized_summary["outputs"] = {
        "sanitized_file_profile_csv": str(sanitized_file_profile_path),
        "sanitized_fault_profile_csv": str(sanitized_fault_profile_path),
    }
    sanitized_summary_path.write_text(json.dumps(sanitized_summary, indent=2), encoding="utf-8")
    return summary


def run(limit: int | None = None, verify_only: bool = False) -> dict[str, object]:
    pdf_files = list_pdf_files()
    validation_pdf = select_validation_pdf(pdf_files)
    if validation_pdf is None:
        raise RuntimeError("No PDF with a parsable Assets of Concern section was found.")

    validation = validate_parser(validation_pdf)
    if not validation["validation_passed"]:
        INTERNAL_ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
        validation_path = INTERNAL_ARTIFACTS_DIR / "pdf_assets_of_concern_validation_failed.json"
        validation_path.write_text(json.dumps(validation, indent=2), encoding="utf-8")
        raise RuntimeError("PDF parser validation failed. Batch parsing is blocked.")

    if verify_only:
        return {
            "created_at_utc": utc_now(),
            "parser_version": PARSER_VERSION,
            "verification_only": True,
            "validation": validation,
            "raw_operational_values_emitted": False,
        }

    if limit is not None:
        pdf_files = pdf_files[:limit]

    all_rows: list[ParsedRow] = []
    statuses: list[FileStatus] = []
    for path in pdf_files:
        rows, status = parse_pdf(path)
        all_rows.extend(rows)
        statuses.append(status)

    return write_outputs(all_rows, statuses, validation)
