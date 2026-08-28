# Operational Runbook

Use `scripts/workflow_ctl.py` for every multi-stage execution. The Markdown
references explain judgment; the controller enforces recoverable state and hard
gates.

Resolve the installed skill once per PowerShell session. This works whether
`CODEX_HOME` is set explicitly or Codex uses its default user-profile location:

```powershell
$codexRoot = if ($env:CODEX_HOME) {
  $env:CODEX_HOME
} else {
  Join-Path ([Environment]::GetFolderPath("UserProfile")) ".codex"
}
$orchestratorSkill = Join-Path $codexRoot "skills\paper-submission-orchestrator"
$compileSkill = Join-Path $codexRoot "skills\paper-compile-layout-qa"
$workflowCtl = Join-Path $orchestratorSkill "scripts\workflow_ctl.py"
$tableAudit = Join-Path $orchestratorSkill "scripts\tex_table_audit.py"
$fontAudit = Join-Path $orchestratorSkill "scripts\pdf_font_audit.py"
$smokeTest = Join-Path $orchestratorSkill "scripts\smoke_test.py"
$formatAudit = Join-Path $compileSkill "scripts\conference_format_audit.py"
```

## 1. Initialize

Run from the project root so relative paper paths are unambiguous:

```powershell
python $workflowCtl init `
  --project-root . `
  --venue ACL `
  --year 2026 `
  --track main `
  --mode review `
  --source docs/paper/main.tex `
  --bibliography docs/paper/references.bib `
  --pdf output/pdf/local_build/main.pdf `
  --dependency-manifest output/pdf/local_build/main.mk `
  --venue-profile docs/paper/venue-profile.json `
  --format-audit .paper-workflow/format-audit.json `
  --build-command "powershell -File scripts/build_paper_local.ps1 -MainTex docs/paper/main.tex -OutDir output/pdf/local_build"
```

The command, PDF and manifest must describe one real build. The repository's
Tectonic helper emits `<stem>.mk`; a latexmk-based project may instead map its
actual `.fls` recorder.

Create `docs/paper/venue-profile.json` first with
`$paper-compile-layout-qa` from current official author instructions and the
exact official kit. The compile skill ships
`assets/venue-profile.template.json`. `--venue-profile` enables the enforced
handoff; `--format-audit` maps the JSON produced after the build. Both options
may be omitted only for a legacy compatibility workflow, which must not claim
machine-enforced venue-profile compliance.

This creates `.paper-workflow/state.json`, ledgers, approval packets, and a
review directory. It refuses to overwrite an existing state file. Existing
project-native artifacts may remain canonical; map them in `state.json` or use
the generated files as sidecars.

Run preflight:

```powershell
python $workflowCtl validate `
  --state .paper-workflow
```

Warnings are not silent passes. In particular, if
`academic-paper-reviewer` declares sprint-contract files that are absent, use
the documented five-role compatibility mode and do not claim hard-contract
enforcement.

## 2. Story approval hard gate

The story architect completes `STORY_APPROVAL_PACKET.md`. Then:

```powershell
python $workflowCtl submit-story `
  --state .paper-workflow
```

The controller moves to `WAITING_FOR_STORY_APPROVAL`. Present the exact packet
and its SHA-256 to the user. Do not draft.

Only after an explicit user/PI approval message, record that evidence:

```powershell
python $workflowCtl approve-story `
  --state .paper-workflow `
  --by USER `
  --evidence "通过，按这个写"
```

The command is an audit record, not a substitute for approval. If the packet is
edited after approval, validation and drafting transitions fail. Submit the new
packet and obtain approval again.

After approval:

```powershell
python $workflowCtl advance `
  --state .paper-workflow --to DRAFTING
```

If the approved thesis, contribution hierarchy, non-claims, or main evidence
interpretation changes, do not edit through the old approval. Run:

```powershell
python $workflowCtl invalidate-story `
  --state .paper-workflow --reason "main evidence interpretation changed"
```

The command preserves the old cycle under `.paper-workflow/archive/`, clears
its active review/request state, resets claim/terminology and QA sidecars, and
requires submission and explicit approval of the current story packet again.

## 3. Build a reviewable artifact

Advance through `ASSEMBLING` after the draft is complete. Use
`$paper-compile-layout-qa` to compile and visually inspect the real venue PDF,
then update the mapped PDF path if needed and advance to `REVIEWABLE`.

For LaTeX papers, run the source preflight before visual inspection:

```powershell
python $tableAudit `
  docs/paper/main.tex --strict --output .paper-workflow/tex_table_audit.json
python $fontAudit `
  output/pdf/local_build/main.pdf --output .paper-workflow/pdf_font_audit.json
python $formatAudit `
  --profile docs/paper/venue-profile.json --project-root . `
  --tex docs/paper/main.tex --pdf output/pdf/local_build/main.pdf `
  --strict --output .paper-workflow/format-audit.json
```

The venue audit must declare `PASS` and bind the exact profile, main source,
and PDF hashes. It checks pinned kit files, source mode signatures, page size,
mechanically knowable page limits, PDF metadata, embedded fonts, and Type 3
fonts. It does not replace manual inspection of reference/appendix boundaries,
figures, tables, density, or aesthetics. Record the profile and audit SHA-256
values in `BUILD_RECEIPT.md`.

Strict mode enforces explicit column/text width, a complete booktabs three-line
hierarchy, no vertical/grid rules, and no `tiny` table font. Record justified
natural-width exceptions immediately before the table as
`% paper-qa: natural-width-ok; reason=<rendered justification>`. Strict mode
keeps this as a visible warning rather than an error. Do not use the annotation
before rendered inspection.
The PDF font audit blocks unembedded and Type 3 fonts and reports rendered text
below 6.5 pt for mandatory visual inspection.

Use this pass to identify table defects before review and, if useful, populate
provisional rows in `.paper-workflow/TABLE_QA.md`. Do not declare final PASS at
this stage: the review and revision loop can change table geometry, font size,
and downstream pagination.
For final QA, copy `tables_scanned=N` from the strict JSON result, create exactly
N ledger rows, bind both JSON SHA-256 values, and bind the font result as
`pdf_sha256=<exact PDF hash>`. The controller rechecks the canonical source,
every scanned TeX input, and PDF hashes stored inside those JSON files.

The controller requires source, bibliography, and PDF files before it accepts
`REVIEWABLE`. It also requires `BUILD_RECEIPT.md` with `Status: PASS`, exact
source/bibliography/PDF hashes, a compiler dependency-manifest hash for LaTeX,
the dependency-bundle hash from
`workflow_ctl.py fingerprint`, the real build command, page count, log counts,
and rendered-inspection evidence.

With latexmk/pdflatex, enable recorder output and pass the resulting `.fls`.
With Tectonic, use `--makefile-rules <outdir>/<stem>.mk` and pass that `.mk`.
The repository's `scripts/build_paper_local.ps1` now emits this Tectonic rule.
The controller treats compiler-reported inputs as the primary inventory and
unions them with source preflight discovery. A LaTeX candidate cannot become
`REVIEWABLE` without one of these manifests. `.fls` requires a valid `PWD`, the
canonical source plus another existing `INPUT`, no missing inputs, and the exact
PDF `OUTPUT`; Tectonic `.mk`/`.d` requires the exact PDF target and resolvable
local inputs after output-directory projection is mapped to the source tree.

`Status: PASS` is structural: page count matches the PDF; undefined references,
citations, and missing files are zero; rendered inspection uses
`PASS; pages=ALL|<pages>; evidence=<completed evidence>`; and nonzero overfull
boxes use `; REVIEWED: <visual disposition and reason>`. Use
`workflow_ctl.py check-build --state .paper-workflow` to test
the build evidence without advancing the story state.

## 4. Configure and freeze the review panel

Run `$academic-paper-reviewer` Phase 0 only. It writes `REVIEW_PANEL.md` and
declares `Configuration type: STANDARD_FIVE_ROLE` or `CUSTOM`.

For the unchanged standard five-role roster and duties, validate and freeze it
without a user pause:

```powershell
python $workflowCtl advance `
  --state .paper-workflow --to REVIEWING
```

This records `STANDARD_AUTO_FROZEN` and freezes the fixed standard
responsibility IDs plus panel, canonical source, bibliography, rendered PDF,
and build-receipt hashes. Dynamic persona expertise is allowed; changing a
responsibility ID requires `CUSTOM`.

Only when a role or required responsibility is specially adjusted, or an extra
reviewer is added, mark the
card `CUSTOM`, complete `Special configuration rationale`, and submit it for
approval:

Also add `## Required report files` with a two-column Role/Output file table.
Every row must have a matching role section containing completed persona and
responsibility ID. The controller requires every declared report and rejects
undeclared reviewer reports.

```powershell
python $workflowCtl advance `
  --state .paper-workflow --to WAITING_FOR_REVIEW_PANEL_APPROVAL
```

After explicit user/PI approval of that exact custom card:

```powershell
python $workflowCtl approve-review-panel `
  --state .paper-workflow `
  --by USER `
  --evidence "审稿组通过"
```

The controller rejects a standard card sent to the custom approval state and a
custom card sent directly to `REVIEWING`. While custom approval is pending, it
also checks all discovered TeX inputs, figures, bibliography, and local
class/style dependencies against the submitted bundle. Changing any protected
artifact or dependency after either freeze path makes approval or validation
fail.

## 5. Review output adapter

The full review execution produces:

```text
.paper-workflow/reviews/
  EIC.md
  METHODOLOGY.md
  DOMAIN.md
  PERSPECTIVE.md
  DEVILS_ADVOCATE.md
  EDITORIAL_DECISION.md
```

Each standard report, or each custom roster-declared report, contains:

- the exact frozen source, bibliography, and PDF SHA-256;
- `Experiment requirement: NONE` or the relevant EXP-REQ identifiers;
- `Revision requirement: NONE` or the relevant `REV-REQ-*` identifiers;
- a complete Experiment Request Card for every non-`NONE` request.
- the required substantive sections: recommendation/scope, strengths,
  major/minor concerns, required revisions, experiment requests, and
  confidence/assumptions.

The controller rejects the transition to `TRIAGE` if a declared role is missing, a
snapshot hash is absent, or an experiment is requested without a card.
It also rejects byte-for-byte duplicate reviewer reports as non-independent.
Required headings and machine-control fields must each occur exactly once;
duplicate requirement, hash, status, or readiness lines are rejected.
On successful transition it freezes hashes for the frozen panel, every declared
reports, and `EDITORIAL_DECISION.md`; subsequent edits invalidate validation.

## 6. Revision and re-review

After review artifacts pass, advance to `TRIAGE`. Complete
`REVISION_LEDGER.md`; use a data row for each decision, or write
`NO_REQUIRED_REVISIONS` when the editorial decision genuinely requires none.
The controller will not enter `REVISING` on an empty template, and it rejects
`NO_REQUIRED_REVISIONS` or a ledger that omits any reviewer `REV-REQ-*` ID.

If any review report contains an EXP-REQ, complete one corresponding row in
`EXPERIMENT_REQUESTS.md`. Record resolution, exact user/PI or project-policy
authority, the concrete action, and status. Revision cannot begin until every
request has a decision; re-review cannot begin until every request is
`COMPLETED`, `APPLIED`, or `VERIFIED`.
Every required revision ticket must also be in a closed status with completed
verification before re-review.

Complete all content and layout work, rebuild, visually inspect, and refresh
`format-audit.json` plus `BUILD_RECEIPT.md` before advancing to `RE_REVIEW`.
This freezes the exact final source, bibliography, venue profile, format audit,
PDF, and receipt. The re-review subagent writes
`reviews/RE_REVIEW.md` containing all frozen SHA-256 values, the verification
sections, `Scientific signoff: PASS`, and `Experiment requirement: NONE`. A
file that merely says “fixed” does not unlock `SUBMISSION_QA`.
It also declares `Revision requirement: NONE`. If re-review emits a new
EXP-REQ, the controller persists that ID before QA fails; `reopen-revision`
cannot erase it, and re-review remains blocked until its decision is recorded
and closed.
The same persistence applies to a new re-review REV-REQ. Entering re-review
freezes both decision ledgers, and the re-review report records their exact
SHA-256 values.

## 7. Final status

`SUBMISSION_QA` is read-only. Re-run the strict TeX table audit, PDF font audit,
and conference format audit on the exact re-reviewed candidate, then rebuild
`TABLE_QA.md` for every
main and appendix table. Its rows record intended width, semantic rule
hierarchy, column/row alignment, minimum rendered font, visual evidence, and
every page changed before the frozen re-review candidate. Record audit commands
and results plus the exact final PDF hash, and declare `Overall table QA: PASS`
only after rendered inspection.

If final QA finds a defect that requires any source/PDF change:

```powershell
python $workflowCtl reopen-revision `
  --state .paper-workflow --reason "final QA requires a candidate change"
```

Then fix, rebuild, refresh the receipt, and re-review. Do not edit in place and
reuse the old scientific signoff.

Complete `SUBMISSION_READINESS.md`, then record one terminal status:

```powershell
python $workflowCtl set-readiness `
  --state .paper-workflow --status SUBMISSION_READY
```

`SUBMISSION_READY` is rejected if the canonical source still contains common
unresolved markers, the PDF is missing, or final `TABLE_QA.md` does not declare
PASS. `CONDITIONALLY_READY` and `NOT_READY` remain available for explicit
metadata/external blockers or substantive failures.
All three statuses require exact source/bibliography/PDF hashes, three explicit
PASS/FAIL verdicts, build/render evidence, blockers, risks, and next action.
A one-line non-ready label is invalid.
`CONDITIONALLY_READY` requires scientific PASS, manuscript PASS, and package
FAIL. Scientific or manuscript failure must be recorded as `NOT_READY`.

## 8. Resume and diagnose

```powershell
python $workflowCtl status `
  --state .paper-workflow
python $workflowCtl validate `
  --state .paper-workflow
```

`status` reports the current stage, last passed G0--G8 gate, frozen review and
re-review snapshots, and the commands currently allowed as next actions.

On Windows, execute `test_workflow_ctl.py` directly. Running `python -m
unittest C:\...` from another drive can fail before discovery because Python
tries to compute a cross-drive relative path.

Skill regression and real-project smoke commands:

```powershell
python (Join-Path $orchestratorSkill "scripts\test_workflow_ctl.py") -v
python (Join-Path $orchestratorSkill "scripts\test_tex_table_audit.py") -v
python $smokeTest `
  --project-root . --source docs/paper/main.tex `
  --bibliography docs/paper/references.bib --pdf output/pdf/local_build/main.pdf `
  --main-tex docs/paper/main.tex --build-script scripts/build_paper_local.ps1 `
  --venue-profile docs/paper/venue-profile.json `
  --venue ACL --year 2026 --track main --mode review
```

This smoke is intentionally strict: it requires a real repository build,
compiler dependency manifest, exact render diff, strict table audit, font audit,
and the read-only build-evidence gate. It fails on table/font/build defects; it
does not substitute for story approval or final `TABLE_QA.md` visual sign-off.
