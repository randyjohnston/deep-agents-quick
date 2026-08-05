---
name: xlsx-io
description: Read and write Excel .xlsx workbooks for data preparation and knowledge management. Use when the user asks for spreadsheet or Excel output instead of CSV or text, needs multiple tabs, or supplies a workbook to inspect or transform.
license: MIT
---

# XLSX Input and Output

Two tools handle spreadsheets directly, with no sandbox or shell involved:

- `write_xlsx(filename, sheets, freeze_header=True, autofilter=True)` — create a workbook
- `read_xlsx(path, sheet=None, max_rows=200)` — inspect an existing workbook

An `.xlsx` file is a ZIP of Office Open XML parts. Both tools serialize and
parse it in memory, so **do not** try to build a workbook by writing a script
and calling `execute`. That path does not work here: the agent's filesystem
backend is not a sandbox, so `execute` returns an error.

## Choosing XLSX over CSV

Prefer `write_xlsx` when any of these hold:

- The user says "Excel", "spreadsheet", "xlsx", or "workbook"
- The deliverable needs **more than one tab** — CSV is single-table by definition
- Types matter: dates should sort as dates, numbers should aggregate
- The recipient will open it by hand and benefits from frozen headers and filters

Stay with CSV or Markdown when the output is a single small table headed for a
pipeline, a diff, or the chat itself. A workbook the user never opens is worse
than a table they can read inline.

## Writing a workbook

Pass one entry per tab. `columns` becomes the bold, frozen, filterable header
row; `rows` is a list of row lists.

```python
write_xlsx(
    filename="q3-pipeline.xlsx",
    sheets=[
        {
            "name": "Summary",
            "columns": ["Metric", "Value"],
            "rows": [["Total accounts", 412], ["Closed won", 57]],
        },
        {
            "name": "Accounts",
            "columns": ["Account", "Owner", "Signed", "ARR"],
            "rows": [
                ["Acme Corp", "R. Johnston", "2026-03-14", 84000],
                ["Globex", "A. Patel", "2026-05-02", 121500],
            ],
        },
    ],
)
```

Conventions that make a workbook usable:

- **One tab per entity.** Do not stack unrelated tables on one sheet.
- **Lead with a Summary tab** when there is more than one data tab.
- **Send real types, not strings.** `84000`, not `"84000"`; `"2026-03-14"`, not
  `"March 14, 2026"`. Numbers passed as strings cannot be summed, and only
  strict `YYYY-MM-DD` / `YYYY-MM-DD HH:MM[:SS]` become real Excel dates.
- **Keep headers short** — they set the column width.
- **Use `null` for missing values**, not `"N/A"` or `""`, so the cell stays
  genuinely empty.

## Reading a workbook

```python
read_xlsx("customers.xlsx")              # every sheet, 200 rows each
read_xlsx("customers.xlsx", sheet="Q3")  # one sheet
read_xlsx("customers.xlsx", max_rows=50) # tighter cap
```

Read before you transform, so column names and types come from the file rather
than a guess. Formula cells return their **last cached value**, not the
formula — a workbook never opened in Excel may return empty cells for them.
Raise `max_rows` deliberately; each row consumes context.

## Where files live

- Writes go to `OFFICE_OUTPUT_DIR` (default `./output`), basename only — a path
  like `../report.xlsx` is rejected rather than escaping the directory.
- Reads resolve under `OFFICE_INPUT_DIR` (default `./input`) and the output
  directory, so a file just written can be read straight back.

Report the returned absolute path to the user; that is how they retrieve the
file. On a deployed server the path is container-local and does not survive a
restart, so mention that when it applies.

The legacy `XLSX_INPUT_DIR` and `XLSX_OUTPUT_DIR` settings remain fallbacks.

## Limits

- Excel caps a sheet at 1,048,576 rows and 16,384 columns; the tool raises
  before producing a corrupt file. Split across tabs when you approach this.
- Tab names are truncated to 31 characters, `[ ] : * ? / \` become `-`, and
  duplicates get a `_2` suffix.
- Text beginning with `=`, `+`, `-`, or `@` is stored as literal text rather
  than a formula, so untrusted content cannot execute on open.
