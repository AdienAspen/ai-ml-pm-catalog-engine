# F4.0 XLSX Characterization Workspace

This directory contains the controlled workspace for `F4.0` XLSX document-family characterization.

## Scope

`F4.0` characterizes a small sample of productive XLSX files before any extraction, parser, candidate mapping, or weak-supervision pass is allowed.

The task answers what the XLSX family is, where usable text and codes live, whether template variation exists, and whether the current routing would miss relevant evidence.

## Routing

The sub-agent must use only the paths provided by the orchestrator. It must not create ad hoc output directories.

Prompt:

- `prompts/f40_xlsx_characterization_prompt.md`

Required output directory:

- `outputs/f40_xlsx_characterization/`

Allowed outputs:

- `f40_xlsx_characterization_memo.md`
- `f40_xlsx_file_sample_manifest_sanitized.csv`
- `f40_xlsx_sheet_inventory_sanitized.csv`
- `f40_xlsx_column_profile_sanitized.csv`
- `f40_xlsx_positive_control_check_sanitized.csv`

## Controls

- Characterization only; no parser, no extraction pipeline, no target candidates.
- Streaming reads only for XLSX inspection.
- No raw operational values in versionable outputs.
- Positive known controls must be defined before interpreting missing values.
- Sample files must span distinct contractor paths and separated dates where available.
- If a file exceeds the prompt budget caps, mark it `truncated: true` and stop reading that file.

## Status

Initialized for sub-agent execution. No F4.0 characterization outputs have been accepted yet.
