---
name: docx-io
description: Create and inspect Microsoft Word .docx documents. Use for polished narrative deliverables with headings, paragraphs, and bullet lists.
license: MIT
---

# DOCX Input and Output

Use `write_docx(filename, document)` for Word deliverables and `read_docx(path,
max_blocks=500)` to inspect supplied documents. Pass typed structure rather
than markdown: `document` contains `title`, `subtitle`, and `sections`; each
section contains an optional `heading`, `paragraphs`, and `bullets`.

Choose DOCX for reports, briefs, memos, and other narrative documents intended
for editing or formal distribution. Prefer Markdown when the user only needs
chat-readable text, and PPTX when the content is meant to be presented.

Keep paragraphs focused, use headings to make the document navigable, and use
bullets for genuinely scannable lists rather than every sentence. Reads and
writes are confined to `OFFICE_INPUT_DIR` and `OFFICE_OUTPUT_DIR`; report the
absolute output path returned by the tool.
