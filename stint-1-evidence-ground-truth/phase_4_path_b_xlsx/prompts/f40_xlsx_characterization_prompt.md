Prompt F4.0 — Caracterización XLSX
Versión optimizada · agente interno · presupuesto controlado

ROLE

You are characterising a document family before it enters a data
pipeline. You are not extracting data, building a parser, or
producing candidates.

Your job is to read a small sample AS DOCUMENTS and report what
they are.

WHY THIS EXISTS

A parallel document family (PDFs) was parsed as tables and it cost
us a full phase. The files turned out to be daily status snapshots,
not maintenance events; two codes we treated as fault codes were
actually application status values; and the richest text lived in a
prose block the parser discarded entirely.

We are not repeating that with the XLSX family.

═══════════════════════════════════════════════════════════════
DATA HANDLING — NON-NEGOTIABLE
═══════════════════════════════════════════════════════════════

This is client operational data from an energy utility. It stays
inside the project perimeter.

- Never write raw operational values into your reasoning, logs, or
  final report. Work with shapes, counts, distributions.
- Text examples in the report: maximum 3 per column, maximum 12
  words each, with any personal data redacted.
- Personal data means: names, phone numbers, emails, worker IDs,
  signatures, badge numbers. If you encounter it, report the
  LOCATION only — sheet and column — never the values.
- Do not copy file contents into scratch files, temp outputs, or
  anywhere outside the working directory.
- If you are unsure whether something is sensitive, treat it as
  sensitive and report its shape, not its content.

═══════════════════════════════════════════════════════════════
BUDGET CAPS — HARD LIMITS
═══════════════════════════════════════════════════════════════

Exceeding any cap means SAMPLE AND FLAG AS TRUNCATED. It never
means read more.

  Files                    max 4, spanning contractors and sites
  Sheets inspected/file    max 10
  Columns inspected/sheet  max 40
  Data rows read/sheet     max 15
  Text examples/column     max 3, max 12 words each

If a file exceeds a cap, inspect the first N by position, note
what was skipped, and mark that file `truncated: true` in your
report. Do not attempt to compensate by reading more elsewhere.

═══════════════════════════════════════════════════════════════
READ METHOD — FOLLOW EXACTLY
═══════════════════════════════════════════════════════════════

Step 1 — Size before opening. Always.

    stat -c '%s bytes' <file>

    < 20 MB   → normal read is fine
    ≥ 20 MB   → streaming mode is MANDATORY

Step 2 — Sheet inventory, cheap, without loading data:

    from openpyxl import load_workbook
    wb = load_workbook(path, read_only=True, data_only=True)
    print(wb.sheetnames)

    read_only=True is required, not optional. Without it openpyxl
    loads the entire workbook into memory and will break on large
    files.

    Do not trust ws.max_row in read_only mode — many writers omit
    the dimension record and it returns None or a wrong value.

Step 3 — Headers and sample rows, streaming:

    ws = wb[sheet_name]
    for i, row in enumerate(ws.iter_rows(max_row=16, values_only=True)):
        if i > 15: break
        # row 0 is headers

    Do NOT rely on pandas.read_excel(nrows=N) to limit cost. With
    the openpyxl engine it often parses the full sheet internally
    before truncating — you save tokens in the report but not time
    or memory on read.

Step 4 — Ignore embedded objects entirely.

    Images, charts, pivot tables, conditional formatting, defined
    names, macros. Do not load, inspect, or report them beyond
    noting "embedded objects present: yes/no".

Step 5 — Abort condition.

    If a single file takes more than ~2 minutes to inventory, stop
    on that file, report what you got, mark it `read_incomplete`,
    and move to the next. A partial characterisation of 4 files
    beats a complete one of 1.

═══════════════════════════════════════════════════════════════
QUESTIONS TO ANSWER
═══════════════════════════════════════════════════════════════

1. WHAT IS THIS DOCUMENT? An event record, a daily status
   snapshot, a work order log, a schedule, something else?
   State your evidence.

2. REPETITION ACROSS FILES. If the same asset or event appears
   in consecutive dated files, row count is not event count.
   Check explicitly. This is the single most expensive thing to
   discover late.

3. SHEET INVENTORY. What sheets exist, what does each hold, and
   are any currently ignored by our field routing?

4. COLUMN INVENTORY per sheet: name, dtype, null rate, and
   classification — free text, code, identifier, date, metadata.

5. WHERE IS THE FREE TEXT? Which columns carry technician prose?
   Report typical word count distribution.

6. STATE vs DESCRIPTION columns. In the PDFs, two values we read
   as fault codes mirrored application status categories instead
   of describing failures. Check for the same pattern: does any
   code column's value set match a status vocabulary rather than
   a failure vocabulary?

7. TEXT OUTSIDE THE ROUTED COLUMNS. Notes, comments, remarks,
   observations, free-form fields, merged header cells, anything
   the current routing does not touch.

8. LANGUAGE per text column: Spanish, English, mixed?

9. PLANNED vs REACTIVE. Is there a field distinguishing
   maintenance type? What values, what coverage?

10. TEMPLATE VARIATION. Do the sampled files share the same sheet
    and column structure, or does it change across dates or
    contractors? The PDF family changed template at least once
    mid-range and it broke position-based extraction silently.

11. PERSONAL DATA. Present anywhere? Report sheet and column
    location only. Never the values.

═══════════════════════════════════════════════════════════════
OUTPUT — UNDER ONE PAGE
═══════════════════════════════════════════════════════════════

  WHAT THESE DOCUMENTS ARE
  One paragraph. The single most important finding.

  STRUCTURE
  Compact table: file · sheets · columns · rows · truncated?

  WHERE THE SIGNAL IS
  Which columns carry usable semantics, which do not.

  RED FLAGS
  Snapshot repetition · state-vs-description columns · ignored
  text blocks · template variation · PII locations.

  IMPLICATIONS FOR THE PIPELINE
  What our current field routing gets right, and what it misses.

  COVERAGE NOTE
  What you read, what you skipped, what was truncated.

═══════════════════════════════════════════════════════════════
RULES
═══════════════════════════════════════════════════════════════

- If a question cannot be answered from the sample, say so. Never
  extrapolate from 4 files to the corpus.
- Prefer "observed in 3 of 4 sampled files" over confident
  generalisation.
- Do not build a parser, write extraction code, or produce
  candidate mappings. Characterisation only.
- A truncated honest report beats a complete one that burned the
  budget or leaked data.
