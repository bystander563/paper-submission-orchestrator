# Conference Format QA

The current official author kit and venue instructions control. These defaults
apply when the kit does not specify a different convention.

For new workflows, create the sourced `venue-profile.json` with
`$paper-compile-layout-qa` and run its `conference_format_audit.py` after each
candidate build. The orchestrator freezes the resulting `format-audit.json` at
review and re-review gates. This table/font contract adds deeper semantic and
visual checks; it does not duplicate or override the venue profile.

## Text and fonts

- Preserve the official class/style file, page geometry, columns, base font,
  line spacing, heading style, and caption style.
- Table and figure text must use the document's font family or an accepted
  matching family. Do not introduce a visually unrelated font.
- Prefer normal document size, `small`, or `footnotesize` for table bodies.
  Do not use `tiny` to make a table fit. `scriptsize` requires a documented
  exception and rendered readability evidence.
- Do not change global font size, margins, line spacing, or caption settings to
  rescue a local table or page.
- Verify embedded fonts and actual print-size readability in the final PDF.
- Run `scripts/pdf_font_audit.py FINAL.pdf` on the exact candidate. Any
  unembedded or Type 3 font blocks readiness. Text below the configured
  readability threshold is a visual-inspection warning, since mathematical
  superscripts can be legitimately smaller than body or table text.

## Table width and placement

- A main one-column table uses `table` and normally aligns its left and right
  edges to `\columnwidth` (or the equivalent local `\linewidth`). A main
  two-column table uses `table*` and normally aligns to `\textwidth`.
- Prefer `tabular*` with controlled inter-column space for exact alignment.
  Use `adjustbox` with `max width` for overflow containment when justified.
  `max width` is not evidence that a narrow table reaches the intended frame;
  pair it with exact `width=...` or record a justified natural-width exception.
  `tabularx{\columnwidth}`/`tabularx{\textwidth}` is valid exact-width evidence.
  Avoid unconditional `\resizebox` that shrinks text without a readability
  check.
- Do not stretch a sparse table merely to touch both margins. A genuinely
  small semantic table may use a deliberate natural or fractional width when
  it is centered and visibly more coherent; record its chosen width and reason
  in submission QA. This is an exception to the main-table frame rule, not an
  accidental width.
- After rendered inspection, record that exception immediately before the
  table as `% paper-qa: natural-width-ok; reason=<rendered justification>`.
  Strict source audit then reports the width as an accepted warning. The
  annotation does not waive booktabs, font, fit, or visual requirements.
- Do not rasterize a table or insert it as a screenshot.

### Column allocation and alignment

- Allocate width by content density, not equally by column count. Give method,
  dataset, diagnostic, or interpretation columns enough width to avoid repeated
  one-word wrapping; reclaim width first from short numeric or categorical
  columns that visibly contain unused space.
- Left-align prose and identifiers, center short categorical fields, and align
  numeric columns consistently (prefer decimal alignment when useful). Header
  alignment should agree with the data column unless a deliberate centered
  header is clearer.
- If one wrapped cell makes a row taller, use vertically centered paragraph
  columns such as `m{...}` when that makes peer cells read as one row. A set of
  top-aligned `p{...}` cells can create the false appearance of blank lines.
- Multi-level headers must be visually centered over their child columns and
  use trimmed `\cmidrule(lr){i-j}` spans. A `\multirow` group label must be
  centered across the rows it names; `\multirow[c]` is the starting point, but
  the rendered PDF decides. A local `\raisebox` adjustment is allowed only
  after visual measurement and must be rechecked whenever row height, font,
  or `\arraystretch` changes.
- Judge row height as a table system. Adjust column widths before adding blank
  rows or global vertical padding. Use `\arraystretch` and `\tabcolsep`
  sparingly and locally.

## Three-line table contract

- Use `booktabs`-style `\toprule`, `\midrule`/`\cmidrule`, and `\bottomrule` by
  default.
- Do not use vertical rules. Avoid repeated `\hline` grids unless the official
  venue style explicitly requires them.
- Keep rule weights and spacing consistent. Do not simulate padding with blank
  rows.
- Use grouped headers, whitespace, `\cmidrule`, and alignment to communicate
  structure.

### Rule hierarchy is semantic

- Use the header `\midrule` once beneath the complete header block.
- Use a full-width `\midrule` inside the body only for a genuine protocol,
  population, or estimand boundary. It should not be used merely because a
  label changes.
- For subgroups inside one experimental system, prefer a trimmed local rule
  such as `\cmidrule(lr){2-8}` that leaves the shared group-label column
  visually open. `\addlinespace` is appropriate when whitespace alone conveys
  the grouping.
- Do not add a full rule after every group; that turns a three-line table into
  a grid in disguise. Conversely, do not remove a meaningful protocol-level
  separator merely to minimize the number of lines.
- Keep `booktabs` rule widths at one source-level convention across tables.
  If nominally identical rules look different in a screenshot, first compare
  the TeX commands and inspect the vector PDF or high-DPI render. Zoom-level
  pixel rounding, antialiasing, a nearby `\cmidrule`, or a two-level header can
  make equal `\midrule`s look unequal. Do not hand-tune line widths to repair a
  screenshot artifact.

## Numerical and semantic formatting

- Keep metric precision consistent with the evidence source and across a
  column. Align decimals when it materially improves comparison.
- State whether arrows mean higher/lower is better and define abbreviations in
  the caption or nearby text.
- Bold best values only when comparisons are fair and the field convention
  supports it. Use second-best styling consistently or omit it.
- Do not merge incompatible protocols into one visual ranking.
- Captions should be self-contained enough to identify data, metric, direction,
  uncertainty, and key protocol boundaries without becoming mini-method
  sections.

## Rendered acceptance evidence

For every main and appendix table, record or verify:

| Check | Evidence |
|---|---|
| Width | Left/right edges align with the intended column or text block |
| Rules | Three-line hierarchy is visible; no accidental grid/vertical rules |
| Font | Family matches the paper; size is readable at print scale |
| Fit | No clipping, overlap, or uncontrolled scaling |
| Semantics | Headers, units, arrows, precision, bolding, and uncertainty are consistent |
| Caption | Correct style, placement, cross-reference, and sufficient context |
| Pagination | Float placement does not create harmful gaps or detach discussion |

For each table, also record:

- intended frame: column, text block, or justified fractional/natural width;
- semantic row groups and the reason for each full or partial separator;
- columns expected to wrap and the chosen horizontal/vertical alignment;
- minimum rendered body/header font size and any `scriptsize` exception;
- page number and crop or screenshot used for visual acceptance;
- pages changed relative to the last accepted PDF.

Inspect at 100% print scale and at a high-DPI render. Confirm that group labels
are vertically centered, header rules are source-consistent, dense prose does
not wrap into isolated words, and short cells do not appear to have trailing
blank lines. After a table edit, compare the full PDF: making a table shorter
or wider can repaginate later prose, figures, equations, and references even
when the table page itself looks correct.

Run the structural linter first, then compile and inspect every rendered table.
The linter can detect likely source defects; only the PDF proves width, font,
line weight, and readability.
