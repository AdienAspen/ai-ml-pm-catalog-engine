# F4.0 XLSX Characterization Memo

## What These Documents Are

The sampled XLSX family behaves primarily as daily/status-style operational workbooks rather than atomic event records. The evidence is structural: repeated dated files, compact sheet sets, status/code-like columns, identifier-like columns, and free-text columns that appear as contextual fields rather than as normalized target labels. This is a characterization of four selected files only; it does not extrapolate to the full corpus.

## Structure

| sample_id | sheets | columns_profiled | rows_sampled | truncated | template_signature |
| --- | ---: | ---: | ---: | --- | --- |
| F40-XLSX-SAMPLE-001 | 2 | 4 | 25 | False | TPL-6954111df89f |
| F40-XLSX-SAMPLE-002 | 2 | 5 | 26 | False | TPL-ef9b45929aa7 |
| F40-XLSX-SAMPLE-003 | 2 | 5 | 26 | False | TPL-a109242b409c |
| F40-XLSX-SAMPLE-004 | 2 | 5 | 26 | False | TPL-1991fb7cd5af |

Positive controls passed before missing values were interpreted: `True`.

## Where The Signal Is

- Free-text columns observed: `11`.
- Column classes observed: `{'unknown': 7, 'code': 1, 'free_text': 11}`.
- Text language categories observed: `{'english_like': 1, 'undetermined': 10}`.
- Planned/reactive candidate columns observed: `0`. These are candidate locations only; no maintenance-type derivation was performed.
- Status/code-like columns observed: `1`. These require downstream state-vs-description review before any mapping work.

## Red Flags

- Repetition risk: `0` repeated identifier/code/status value hashes were observed in the bounded sample. This does not prove absence of repetition beyond the sample.
- Template variation: `4` template signatures were observed across `4` files: `{'TPL-6954111df89f': 1, 'TPL-ef9b45929aa7': 1, 'TPL-a109242b409c': 1, 'TPL-1991fb7cd5af': 1}`.
- Text outside obvious routing: `7` sheets had free-text-like columns not clearly identified by routed text-column names.
- PII locations: `10` column locations were flagged. Values were not emitted.
- Truncated files: `0`.

## Implications For The Pipeline

F4 should start with document-family routing and template-aware sheet handling before any extraction or weak supervision. The sample supports a snapshot/repetition risk check similar to Path A: rows should not be treated as events until a stable event or physical-record key is defined. Status/code-like columns must be separated from failure-description evidence before target scoring, and free-text fields must preserve `source_text_field` for DELTA-0003.

## Coverage Note

This pass inspected `4` files, at most `10` sheets per file, `40` columns per sheet, and `15` data rows per sheet, using `openpyxl` with `read_only=True` and `data_only=True`. Embedded objects were ignored except for yes/no presence. No raw operational values, raw file names, raw paths, site names, contractor names, asset identifiers, personal data, or raw prose were emitted.
