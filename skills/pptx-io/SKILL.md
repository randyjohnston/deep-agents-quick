---
name: pptx-io
description: Create and inspect Microsoft PowerPoint .pptx presentations. Use for slide-based briefings, pitches, and presentations.
license: MIT
---

# PPTX Input and Output

Use `write_pptx(filename, deck)` for presentations and `read_pptx(path,
max_slides=100)` to inspect supplied decks. Pass typed structure rather than
markdown: `deck` has an optional title slide plus `slides`, each with a title
and concise bullet points.

`write_pptx` also accepts `theme={"name": "acme"}` or bounded inline colors,
fonts, and a logo. Pass `template="acme.potx"` to inherit an organization's
real slide masters and layouts. Themes resolve under `OFFICE_THEME_DIR`;
logos and templates must be under `OFFICE_INPUT_DIR`.

Choose PPTX only when the material will be presented. Prefer DOCX for sustained
narrative and XLSX for tabular analysis. Give each slide one idea, use short
titles that state the takeaway, and keep bullets brief enough to scan while
speaking. Reads and writes are confined to `OFFICE_INPUT_DIR` and
`OFFICE_OUTPUT_DIR`; report the absolute output path returned by the tool.
`read_pptx` returns visible slide text, including tables and grouped shapes;
speaker notes are not returned.
