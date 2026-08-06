---
name: pptx-io
description: >
  Create and inspect Microsoft PowerPoint .pptx presentations. Use for
  slide-based briefings, pitches, and presentations.
license: MIT
---

# PPTX Input and Output

Use `write_pptx(filename, deck)` for presentations and `read_pptx(path,
max_slides=100)` to inspect supplied decks. Pass typed structure rather than
markdown. Simple slides still accept `title` plus concise `bullets`. For a
designed 16:9 deck, select one bounded archetype per slide:

- `cover`: title (70 chars), subtitle (160), kicker (50), meta (80), optional image and notes.
- `stats`: headline (75), optional deck (160), and 2-4 stats with value (18),
  label (45), caption (120).
- `cards`: headline (75), optional deck (160), and 2-4 cards with title (48),
  metric (45), body (120), and optional image.
- `statement`: statement (140), optional kicker (50), attribution (90), and notes.

The writer owns every coordinate; never invent coordinate or raw-OOXML fields.
Stay within schema budgets because server-side font metrics are unavailable.
Cover/card images are confined PNG/JPEG paths under `OFFICE_INPUT_DIR`, cropped
to fill without distortion, and degrade to a deliberate solid panel when absent.
To use remote images, call `internet_search(..., include_images=True)` to discover
candidates, call `fetch_images` with up to 12 selected HTTPS URLs, then pass each
returned `image` path into the archetype. The fetcher rejects redirects
and non-public network peers, streams into a fixed byte ceiling, downsizes and
normalizes to JPEG, and returns `source_url` for provenance. Treat that source
as a citation and use images only when their licensing permits reuse.
Each URL returns independently: use entries containing `image` and inspect
entries containing `error` rather than retrying the entire batch.
`OFFICE_IMAGE_DOMAINS` optionally narrows eligible hostnames; when it is unset,
any public HTTPS hostname is eligible.

`write_pptx` also accepts `theme={"name": "acme"}` or bounded inline colors,
fonts, six-role PPTX palette, bounded type scale (including statement size),
and a logo. Pass `template="acme.potx"` to inherit an organization's
real slide masters and layouts. Themes resolve under `OFFICE_THEME_DIR`;
logos and templates must be under `OFFICE_INPUT_DIR`.

Choose PPTX only when the material will be presented. Prefer DOCX for sustained
narrative and XLSX for tabular analysis. Give each slide one idea, use short
titles that state the takeaway, and keep bullets brief enough to scan while
speaking. Reads and writes are confined to `OFFICE_INPUT_DIR` and
`OFFICE_OUTPUT_DIR`; report the absolute output path returned by the tool.
`read_pptx` returns visible slide text, including tables and grouped shapes;
speaker notes are written for designed archetypes but are not returned by reads.
