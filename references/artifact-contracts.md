# Artifact Contracts

Use project-native filenames when equivalents already exist. These schemas
define information, not mandatory file names.

## Paper state

Record:

- canonical manuscript source and revision identity;
- target venue, paper type, deadline source, and template revision;
- current workflow stage and last passed gate;
- one-sentence thesis and explicit non-claims;
- active evidence ledger and bibliography paths;
- current review snapshot and latest rendered PDF;
- unresolved P0/P1 blockers;
- user decisions pending.

## Story Approval Packet

The story architect must produce one reviewable packet before drafting:

```markdown
# Story Approval Packet

- Packet ID:

## One-sentence thesis

## Target venue and paper type

## Argument chain
Problem -> gap -> mechanism -> evidence -> boundary.

## Headline contributions

## Explicit non-claims

## Main claim-evidence mapping

## Authoritative terminology decisions

## Main tables and figures

## Main-text and appendix allocation

## Remaining paper-level decisions

## Agent recommendation
```

The approval record is separate from the packet and contains:

- status: `PENDING` or `APPROVED`;
- approver: user/PI identity or label;
- timestamp;
- verbatim approval evidence;
- SHA-256 of the approved packet.

Agents must not infer approval. A material packet edit invalidates the recorded
approval and returns the workflow to `WAITING_FOR_STORY_APPROVAL`.

## Main Figure Contract

Create this artifact after story approval when the packet plans a central
method figure. It is downstream of the story packet and never substitutes for
story approval.

```markdown
# Main Figure Contract

- Story packet path/SHA-256:
- Figure role in the paper:
- Three-second message:
- Target venue and exact placement width:
- Editable master path:
- Vector export path:
- Preview path:

## Required scientific entities

## Canonical node and edge map

## Training-only and inference-time boundary

## Edge semantics

## Authoritative labels and notation

## Forbidden content and claims

## Final-size typography and palette contract

## Caption and alt text paths

## QA record path
```

The QA record binds the vector master and export hashes and reports one of
`DRAFT_ONLY`, `PAPER_READY`, or `CAMERA_READY`. `CAMERA_READY` requires the
exact manuscript placement size, editable text and shapes, embedded valid
fonts, no unsupported scientific element, no clipped label, accessible color
semantics, and a rendered inspection of the export used by the manuscript.

The figure contract becomes stale if the approved story packet changes. A
post-review change to the vector, caption, or placement is a candidate change:
rebuild and re-review before final package QA.

## Reviewer Configuration Card

The card must contain:

```markdown
# Reviewer Configuration Card

- Configuration type: STANDARD_FIVE_ROLE

## Editor-in-Chief
- Persona and expertise: completed field-specific persona
- Responsibility ID: EIC_STANDARD_V1

## Methodology Reviewer
- Persona and expertise: completed methodology persona
- Responsibility ID: METHODOLOGY_STANDARD_V1

## Domain Reviewer
- Persona and expertise: completed domain persona
- Responsibility ID: DOMAIN_STANDARD_V1

## Perspective Reviewer
- Persona and expertise: completed complementary persona
- Responsibility ID: PERSPECTIVE_STANDARD_V1

## Devil's Advocate
- Persona and expertise: completed adversarial persona
- Responsibility ID: DEVILS_ADVOCATE_STANDARD_V1

## Review mode and venue calibration
Completed mode, venue, track, and calibration details.

## Special configuration rationale
Not applicable for STANDARD_FIVE_ROLE.
```

`STANDARD_FIVE_ROLE` means the five required roles are preserved with their
fixed `STANDARD_FIVE_ROLE_V1` responsibility IDs. The controller validates and
freezes this card, source, bibliography, PDF, and build receipt directly; no
user approval record is required. Its approval status is
`STANDARD_AUTO_FROZEN`.

Use `CUSTOM` when a required role is added, removed, merged, or assigned a
materially non-standard responsibility. In that case, `Special configuration
rationale` must identify the exact change and its purpose. The custom card must
be submitted to `WAITING_FOR_REVIEW_PANEL_APPROVAL`; its separate approval
record contains user/PI identity, timestamp, verbatim evidence, and card
SHA-256. Neither configuration may change after its review snapshot is frozen.
The custom card additionally contains:

```markdown
## Required report files

| Role | Output file |
|---|---|
| Reproducibility Reviewer | REPRODUCIBILITY.md |
```

Every role in this table has a matching `##` section with `Persona and
expertise` and `Responsibility ID`. Filenames are safe Markdown basenames.
Every declared report is mandatory, and undeclared review files are rejected.

The standard responsibility IDs mean:

- `EIC_STANDARD_V1`: venue fit, originality, significance, and overall decision;
- `METHODOLOGY_STANDARD_V1`: design, statistics, leakage, uncertainty, and reproducibility;
- `DOMAIN_STANDARD_V1`: literature, task definitions, terminology, and field contribution;
- `PERSPECTIVE_STANDARD_V1`: complementary assumptions, impact, ethics, and transfer limits;
- `DEVILS_ADVOCATE_STANDARD_V1`: strongest counter-argument, alternative explanations, cherry-picking, and overgeneralization.

An extra reviewer is a custom roster. The separate reviewer Skill's
`methodology-focus` mode is not the standard methodology role; it is a reduced
EIC-plus-methodology panel.

## Claim-evidence row

For every material claim, record:

| Field | Meaning |
|---|---|
| Claim ID | Stable identifier |
| Manuscript claim | Exact or normalized wording |
| Evidence | Result card, table, figure, analysis, or citation |
| Protocol | Dataset/split/revision/seed/metric identity |
| Evidence status | Confirmed, exploratory, exposed, negative, non-comparable, or unverified |
| Allowed wording | Strongest defensible formulation |
| Forbidden wording | Known overclaim or category error |
| Location | Planned/current manuscript location |

## Terminology ledger

Record every central task, method-family, evaluation, and mechanism term:

| Field | Meaning |
|---|---|
| Term | Exact manuscript form |
| Status | Established field term, benchmark-defined term, method name, or avoid |
| Authority | Primary paper, benchmark specification, or official standard |
| Accepted meaning | What the source actually means |
| Paper usage | Where and how the manuscript uses it |
| Collision risk | Conflicting meaning in nearby literature |

Rules:

- Do not promote an internal implementation nickname into a scientific concept.
- Do not replace a standard field term with a more dramatic synonym merely to
  sound novel.
- A new method name should describe the actual mechanism, remain distinct from
  established terms, and be introduced as this paper's name rather than as
  community terminology.
- If no authoritative source supports a proposed general concept label, use
  plain descriptive language.

## Review finding

Each finding contains:

- stable ID and reviewer;
- severity: `P0`, `P1`, `P2`, or `P3`;
- category: fact, claim, method, experiment, citation, structure, writing,
  terminology, reproducibility, ethics, or venue;
- exact location and quoted/paraphrased target;
- what is wrong and why it matters;
- evidence supporting the concern;
- smallest acceptable repair;
- whether an Experiment Request Card is attached.

Severity meanings:

- `P0`: invalidates the central result, violates protocol/ethics, or makes the
  submission materially misleading.
- `P1`: likely rejection or desk-reject blocker; must be fixed, explicitly
  accepted by the user, or clearly disclosed before submission.
- `P2`: material quality or score improvement that does not invalidate the
  paper.
- `P3`: optional polish or reviewer preference.

Each standard reviewer file, and every custom roster-declared reviewer file,
must contain these `##` sections:

- `Recommendation and scope`;
- `Evidence-grounded strengths`;
- `Major concerns`;
- `Minor concerns`;
- `Required revisions`;
- `Experiment requests`;
- `Confidence and assumptions`.

`DEVILS_ADVOCATE.md` additionally requires `## Strongest counter-argument`.
`EDITORIAL_DECISION.md` requires `Decision`, `Cross-reviewer consensus`,
`Disagreements and arbitration`, `Devil's Advocate disposition`, `Prioritized
revision roadmap`, and `Experiment request summary`.
Each reviewer file also contains `Revision requirement: NONE` or one or more
stable `REV-REQ-*` identifiers. Every non-`NONE` identifier must be represented
by a revision-ledger row; prose severity alone is not a machine-readable
replacement for the marker.
Independent reviewer files must not be byte-for-byte duplicates; identical
SHA-256 values are a contract failure.
Every required heading and every machine-control field occurs exactly once.
Duplicate requirement, status, hash, or readiness fields are rejected.

## Experiment Request Card

Every reviewer-proposed experiment must use this complete schema:

```markdown
### EXP-REQ-<id>: <short title>

- Reviewer question:
- Manuscript claim at risk:
- Why current evidence is insufficient:
- Priority recommendation: REQUIRED_BEFORE_SUBMISSION | HIGH_VALUE_OPTIONAL |
  CLAIM_NARROWING_PREFERRED | OUT_OF_SCOPE
- Minimum discriminating experiment:
- Hypothesis and falsifier:
- Data, split, revision, and exposure status:
- Comparator(s) and control(s):
- Frozen training/selection/evaluation protocol:
- Metrics, uncertainty, seeds, and reporting unit:
- Positive-result interpretation:
- Negative-result interpretation:
- Null/ambiguous-result interpretation:
- Estimated compute, wall time, and implementation risk:
- Claim unlocked if successful:
- Best no-new-experiment repair:
- Can the current paper remain defensible without it? Why:
- Reviewer confidence and assumptions:
```

Rules:

- Ask the minimum experiment that distinguishes the reviewer concern from a
  plausible alternative explanation; do not request a broad benchmark shopping
  list.
- Specify what a negative or null result would mean before execution.
- Do not prescribe post-result tuning, favorable-seed selection, or a changed
  metric merely to obtain a pass.
- Distinguish validation of the current paper from a new research direction.
- The scheduler may merge duplicates but must preserve material disagreements.

## Experiment decision ledger

Every frozen EXP-REQ must appear in `EXPERIMENT_REQUESTS.md`:

```markdown
| Request ID | Resolution | Authority/evidence | Manuscript or experiment action | Status |
|---|---|---|---|---|
```

Allowed resolutions are `RUN_AUTHORIZED`, `CLAIM_NARROWED`,
`DECLINED_WITH_RATIONALE`, and `OUT_OF_SCOPE`. A run authorization must cite
`USER`, `PI`, or an exact `PROJECT_POLICY`. Before re-review, status must be
`COMPLETED`, `APPLIED`, or `VERIFIED`.

## Revision ticket

Each accepted review item becomes a ticket:

| Field | Meaning |
|---|---|
| Ticket ID | Stable ID linked to review finding(s) |
| Decision | Accept, modify, defer, reject, or needs user decision |
| Rationale | Evidence-based reason |
| Target | File and location |
| Planned change | Minimal concrete edit |
| Owner | Integrator, writer, figure/table agent, citation agent, or user |
| Status | `PENDING`, `APPLIED`, `VERIFIED`, `DEFERRED`, or `REJECTED` |
| Verification | Re-review evidence and verifier |

Ticket IDs use the matching `REV-REQ-*` identifier. The exact standalone line
`NO_REQUIRED_REVISIONS` is permitted only if every reviewer declared
`Revision requirement: NONE`.
Before entering re-review, each required ticket has a closed status (`APPLIED`,
`VERIFIED`, `DEFERRED`, or `REJECTED`) and completed verification evidence.
`BLOCKED` belongs in the decision/rationale while work remains open; it is not
a closed controller status.

## Re-review report

`reviews/RE_REVIEW.md` must identify the exact frozen revised-source,
bibliography, and PDF SHA-256, verify the original tickets against those
artifacts, and contain
`Experiment requirement: NONE` or the relevant EXP-REQ identifiers with full
Experiment Request Cards. It also requires `Verification decision`,
`Ticket-by-ticket verification`, `Residual issues`, `New issues`, `Experiment
requests`, and `Confidence and assumptions`, with `Scientific signoff: PASS`.
File existence alone is not verification.
It also declares `Revision requirement: NONE`. New re-review experiment IDs
are persisted in workflow state before QA can fail and remain open across
`reopen-revision` or report replacement until the decision ledger closes them.
New re-review revision IDs are persisted under the same rule. The re-review
report records the exact revision-ledger and experiment-ledger SHA-256 values;
both ledgers are frozen with the final candidate.

## Build receipt

`BUILD_RECEIPT.md` binds every reviewable and final candidate:

```markdown
# Build Receipt

- Status: PASS
- Command:
- Source SHA-256:
- Bibliography SHA-256:
- Dependency manifest SHA-256:
- Dependency bundle SHA-256:
- Venue profile SHA-256:
- Format audit SHA-256:
- Output PDF SHA-256:
- Page count:
- Undefined references/citations:
- Missing files:
- Overfull boxes:
- Rendered inspection:
```

Refresh it after every source, bibliography, or layout change and before
entering re-review. Generate the dependency bundle with `workflow_ctl.py
fingerprint`; it includes discovered local TeX inputs, bibliography files,
figures, and local class/style files.
When the controller's venue-format contract is enabled, the two additional
hashes are mandatory. The mapped audit must declare `PASS`, bind the exact
venue-profile SHA-256, and bind the exact canonical-source and PDF SHA-256.
`Status: PASS` requires a positive integer page count that matches the PDF,
zero unresolved references/citations, zero missing files, and
`Rendered inspection: PASS; pages=ALL|<pages>; evidence=<completed evidence>`.
A nonzero overfull-box count needs `; REVIEWED: <visual disposition and reason>`.
When `init --build-command` was supplied, the receipt
must reproduce that exact command. Run `workflow_ctl.py check-build` for a
read-only validation of these fields and hashes.
Figure discovery follows declared `\graphicspath` directories as well as paths
relative to each TeX file.
Supported TeX dependency commands remain discoverable when legal whitespace
appears before their braced arguments, such as `\input {body}`.
For LaTeX, a compiler dependency manifest is mandatory and primary. Initialize
with `--dependency-manifest <main.fls>` for latexmk/pdflatex recorder output or
`--dependency-manifest <main.mk>` for Tectonic `--makefile-rules` output. The
bundle includes the manifest and resolved local inputs, preventing dependency
coverage from relying on source regexes alone. `.fls` validation requires a
valid `PWD`, the canonical source plus another existing `INPUT`, no missing
inputs, and the exact PDF as an `OUTPUT`. Tectonic `.mk`/`.d` validation requires
the exact PDF target and the canonical source plus another resolvable input;
output-directory projections are mapped back to the canonical source tree.

## Submission-readiness report

Lead with one status and three independent verdicts:

```markdown
# Submission Readiness

- Overall: SUBMISSION_READY | CONDITIONALLY_READY | NOT_READY
- Scientific readiness: PASS | FAIL
- Manuscript readiness: PASS | FAIL
- Submission-package readiness: PASS | FAIL
- Exact source revision:
- Exact bibliography path/hash:
- Exact PDF path/hash:
- Venue profile path/hash:
- Format audit path/hash:
- Build command/result:
- Final rendered-PDF inspection evidence:
- Remaining P0/P1 blockers:
- User-supplied or external blockers:
- Residual non-blocking risks:
- Recommended next action:
```

Scientific sign-off must not be used as a substitute for author metadata,
ethics, venue-template, deadline, or whole-PDF verification.
When venue-format enforcement is enabled, the readiness report must bind the
exact profile and audit artifacts. Their hashes are frozen with terminal
sign-off.

## Venue profile and format audit

`venue-profile.json` is the project-level conference contract produced from
current official instructions. It records exact venue/year/track/mode,
official sources and supported rules, template files/hashes, page semantics,
PDF requirements, anonymity, required sections, and venue-checker evidence.

`format-audit.json` is produced by `$paper-compile-layout-qa`. It contains:

- `status: PASS | PASS_WITH_WARNINGS | FAIL`;
- exact profile path/SHA-256 and venue identity;
- canonical main-source path/SHA-256 and discovered TeX inputs;
- official template file existence and actual hashes;
- exact PDF path/SHA-256, page information, and font findings;
- structured findings with severity, code, message, and evidence.

The orchestrator accepts only `PASS` at enforced workflow gates. Visual QA and
semantic page-boundary evidence remain in the build receipt; audit JSON is not
a substitute for rendering.
Every terminal status requires every listed field, including exact hashes and
completed evidence/blocker/risk/action lines. `SUBMISSION_READY` requires all
three verdicts to be `PASS`; `CONDITIONALLY_READY` and `NOT_READY` require at
least one explicit `FAIL` and cannot use a one-line shortcut.
More specifically, `CONDITIONALLY_READY` requires scientific PASS, manuscript
PASS, and submission-package FAIL. Any scientific or manuscript FAIL is
`NOT_READY`.

## Table QA ledger

`SUBMISSION_READY` requires a `TABLE_QA.md` tied to the exact candidate PDF:

```markdown
# Table QA

- Overall table QA: PASS | FAIL
- Exact PDF path/SHA-256:
- TeX table audit command/result:
- TeX table audit output SHA-256:
- TeX tables scanned:
- PDF font audit command/result:
- PDF font audit output SHA-256:

| Table | Page | Intended frame | Rule semantics | Column and row alignment | Minimum rendered font | Visual evidence | Changed pages | Status |
|---|---:|---|---|---|---:|---|---|---|
```

One row is required for every main and appendix table. `Rule semantics` states
why each full or partial separator exists. `Changed pages` records the complete
render-diff footprint, not only the page containing the table. A sparse table
that intentionally uses a fractional or natural width records that exception
under `Intended frame`. A ledger populated on the reviewable draft is
provisional. Final PASS requires re-running the source, font, and rendered PDF
checks on the exact submission candidate and recording that PDF's hash.
`TeX tables scanned` is copied from the strict source audit. Its integer must
equal the ledger row count; zero is valid only with `NO_TABLES: CONFIRMED` and
no rows. This prevents a visually inspected subset from masquerading as full
table coverage.
Use the audit JSON `tables[].id` (normally the LaTeX label, otherwise
`file:line`) in the ledger's `Table` column so main and appendix coverage is
traceable rather than inferred from row order.
Run both tools with `--output` into the mapped workflow JSON files. The TeX
evidence line records `--strict`, `PASS`, and `tables_scanned=<same integer>`;
its output-hash field binds the exact JSON, whose canonical-source and every
scanned TeX-file hash must still match. The font evidence line records `PASS`
and `pdf_sha256=<exact candidate hash>`; its output-hash field binds JSON that
also records that PDF hash. A generic command name is not sign-off.

A justified natural-width table places
`% paper-qa: natural-width-ok; reason=<rendered justification>` immediately
before its table environment. The annotation converts only the strict width
finding to a recorded warning; it does not waive font, rules, fit, or visual QA.
