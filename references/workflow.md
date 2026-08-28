# Workflow and Gates

This workflow begins after the research task, core method, and experiment
package are substantially fixed. Reuse established project files when they
already serve the same purpose.

## Stage 0: INTAKE

Collect the active project rules, paper sources, evidence artifacts,
bibliography, figures/tables, build instructions, target venue, and current
rendered PDF. Record missing inputs and distinguish user-supplied metadata from
scientific gaps.

For a LaTeX conference paper, create or map `venue-profile.json` using current
official author instructions and the exact official kit. Record venue, year,
track, mode, page-limit semantics, template files/hashes, anonymity, PDF
requirements, required sections/checklists, and official source URLs. Do not
derive a new-year profile from conference-family defaults alone.

Gate `G0 INPUT_READY`:

- active manuscript and evidence sources are identified;
- target venue and paper type are known or explicitly unresolved;
- exposed, exploratory, negative, and non-comparable evidence is labeled;
- no ambiguity exists about which draft is canonical.
- venue/page-budget assumptions have a sourced profile or are explicitly
  unresolved and blocked from compliance claims.

## Stage 1: WAITING_FOR_STORY_APPROVAL -> STORY_LOCKED

Build the editorial contract before rewriting prose:

- one-sentence thesis;
- problem -> gap -> mechanism -> evidence -> boundary argument chain;
- at most a small set of headline contributions;
- explicit non-claims;
- claim-evidence matrix;
- terminology ledger grounded in benchmark definitions and primary literature;
- main table/figure roles;
- main-text/appendix allocation;
- venue and page-budget assumptions.

The story architect produces a Story Approval Packet and stops. The packet must
contain the one-sentence thesis, argument chain, contributions, non-claims,
claim-evidence summary, terminology choices, main table/figure plan, venue/page
assumptions, and unresolved paper-level decisions.

Set the workflow to `WAITING_FOR_STORY_APPROVAL`. Present the packet to the
user/PI and request an explicit decision. No writer may draft or rewrite the
manuscript while this state is active. Read-only evidence checks and venue-rule
verification may continue, but they cannot alter the proposed story.

Only a direct user/PI instruction such as "通过", "按这个写", or an equally
unambiguous approval of the identified packet advances the workflow. The
integrator cannot approve on the user's behalf. Silence, timeout, approval of an
older packet, or permission to continue unrelated work is not approval.

Gate `G1 STORY_LOCKED`:

- every headline claim maps to specific evidence;
- core scientific terms have authoritative sources and stable meanings;
- no invented field jargon is carrying the novelty argument;
- central adverse evidence appears in the argument or limitations;
- tables and figures have argumentative jobs, not decorative jobs;
- the user/PI has explicitly approved the exact Story Approval Packet;
- the approval record contains approver, timestamp, verbatim approval evidence,
  and packet SHA-256;
- the approved packet has not changed since approval.

If the thesis, contribution hierarchy, core mechanism, explicit non-claims, or
main evidence interpretation changes later, invalidate G1 and return to
`WAITING_FOR_STORY_APPROVAL`.
`invalidate-story` archives the prior story packet, panel, reports, ledgers,
build/table/readiness records, and state under `archive/story-cycle-*`; it then
starts a clean active cycle. Historical requests do not leak into the new story.

## Stage 2: DRAFTING

When the approved Story Approval Packet assigns a central method figure, begin
Stage 2 by loading `$paper-main-figure`. Create `MAIN_FIGURE_CONTRACT.md` and
`FIGURE_FACTS.md`, bind both to the approved packet SHA-256, and lock the
scientific node/edge topology before drafting prose around the figure. Produce
an editable vector master, caption, venue-sized render, and QA record. The
figure may compress labels and visual grouping, but it may not change the
approved thesis, mechanism, contribution order, non-claims, or evidence
interpretation. If it would, invalidate G1 and return to story approval.

This figure step does not add a routine human gate. Continue through visual
iteration while the approved story remains unchanged. User confirmation is
required only when the project explicitly requests a visual approval gate or
when the proposed figure would materially change the story.

Draft in dependency order:

1. task/data/evaluation and method definitions;
2. results and analysis from verified tables;
3. limitations and ethics;
4. introduction, related work, abstract, and conclusion after the evidence
   story is stable.

Write with calibrated confidence. Lead paragraphs with the scientific point,
then give the most relevant evidence. State a scope condition where it affects
interpretation, but avoid repeating the same defensive disclaimer throughout
the paper.

Parallel section drafting is allowed only for disjoint sidecar files with the
same frozen fact pack and terminology. The canonical writer or integrator
performs the merge.

Gate `G2 COMPLETE_DRAFT`:

- all required sections exist;
- no unsupported numbers or citations were introduced;
- placeholders are enumerated;
- every table/figure is cited and has a source;
- terminology and claim strength are consistent.
- when a central method figure is planned, its contract cites the approved
  story hash and its editable master, caption, and placement-size render exist.

## Stage 3: ASSEMBLING -> REVIEWABLE

Convert or synchronize the manuscript into the venue source format. Build the
PDF, check errors and unresolved references, and render representative pages.
Do this before substantive review so reviewers see the artifact a real reviewer
would receive.

For LaTeX compilation or layout repair, load `$paper-compile-layout-qa` and
follow its contract: identify the exact venue/year/track/mode, prefer the
repository-native build, preserve the official template, render before
diagnosing, make the smallest owning-layer fix, and verify every changed page.
Current official author instructions or the official local kit control format;
project checklists are useful but cannot override them.

When the controller was initialized with `--venue-profile`, run the compile
skill's `conference_format_audit.py` on the built PDF and write the mapped
`format-audit.json`. The audit must bind the exact profile, canonical source,
and rendered PDF. Record both hashes in `BUILD_RECEIPT.md`. A source-only,
stale, failed, or warning-only audit does not satisfy the enforced handoff.

Gate `G3 REVIEWABLE_ARTIFACT`:

- the source builds successfully;
- `BUILD_RECEIPT.md` records the exact source, bibliography, and PDF hashes,
  compiler dependency-manifest hash (`.fls` or Tectonic `.mk`/`.d`) for LaTeX,
  discovered dependency-bundle hash,
  repository-native command, page count, log findings, and rendered inspection;
- source and PDF correspond to the same recorded build;
- the PDF is readable enough for substantive review;
- page count and anonymization state are known.
- when enabled, the venue profile and format audit pass and are bound to the
  exact reviewable source/PDF.

Run an initial table/font preflight here so reviewers do not receive a broken
or unreadable artifact. This is not the final `TABLE_QA.md` sign-off: later
revision can change table geometry, font size, and downstream pagination.

## Stage 4: REVIEWABLE -> REVIEWING (standard) or approval gate (custom)

First freeze the reviewable source/bibliography/PDF identity. Run the field-analysis phase of
`$academic-paper-reviewer` to produce `REVIEW_PANEL.md` with five roles: EIC,
methodology, domain, perspective, and Devil's Advocate.

Use `Configuration type: STANDARD_FIVE_ROLE` when the roster and responsibilities
follow the fixed `STANDARD_FIVE_ROLE_V1` responsibility IDs. Field-specific
persona/expertise may vary. Validate the card, freeze its hash together with the
source, bibliography, PDF, and build-receipt hashes, and enter `REVIEWING`
directly. Do not pause for confirmation.

Use `Configuration type: CUSTOM` only when a role is added, removed, merged, or
given a materially different responsibility, or an extra reviewer is added.
Complete `Special configuration rationale`, enter
`WAITING_FOR_REVIEW_PANEL_APPROVAL`, and stop. Review may begin
only after the user/PI approves that exact custom card. A supplementary methods
reviewer is therefore `CUSTOM`; a non-review venue/compliance QA pass is not.
The custom card must include `Required report files`, a two-column Role/Output
file table. Each row names a matching role section with completed persona and
responsibility ID. Only safe Markdown basenames are accepted; every declared
report is required and undeclared review reports are rejected.

Then run independent, read-only review. Every review subagent loads
`$academic-paper-reviewer`:

- `full` mode supplies the required five-role editorial panel;
- the methodology role inside `full` applies the methodology criteria when
  design, statistics, or reproducibility are central; do not invoke the
  separate `methodology-focus` mode, which creates a reduced two-person panel;
- any additional independent methods reviewer changes the panel and requires a
  `CUSTOM` configuration;
- a venue/compliance pass may run in parallel but does not replace peer review.

Do not reveal other reviewers' reports until each independent report is
complete. Require exact locations and actionable fixes. Any experiment request
must use an Experiment Request Card.

The current installed reviewer package may describe sprint-contract assets that
are not present locally. Run the workflow preflight. If those schema/template/
validator files are missing, use **five-role compatibility mode**: retain the
five frozen personas and the review skill's substantive rubrics, but do not
claim machine-enforced sprint-contract review. Never silently shrink the panel
to the older four-role editorial template.

For the standard panel, write the five reports separately as `EIC.md`, `METHODOLOGY.md`, `DOMAIN.md`,
`PERSPECTIVE.md`, and `DEVILS_ADVOCATE.md`, plus `EDITORIAL_DECISION.md`. Every
report records the frozen source/bibliography/PDF SHA-256 and an `Experiment requirement:`
marker. A non-`NONE` marker requires a complete `EXP-REQ` card. It also records
`Revision requirement: NONE` or one or more stable `REV-REQ-*` identifiers.
For a custom panel, use exactly its declared report files plus the editorial
decision.
Every required heading and machine-control field occurs exactly once. Duplicate
requirement, status, hash, or readiness lines invalidate the artifact.

Gate `G4 REVIEW_COMPLETE`:

- independent reports and editorial synthesis exist;
- disagreements are preserved rather than averaged away;
- every proposed experiment has a complete request card;
- every roster-declared independent report matches the frozen
  source/bibliography/PDF hashes;
- the editorial decision accounts for the Devil's Advocate rather than using a
  stale four-reviewer template;
- reviewers have not edited the manuscript;
- no two independent reviewer reports are byte-for-byte duplicates;
- every report contains the required recommendation, strengths, major/minor
  concerns, required revisions, experiment-request, and confidence sections;
- editorial synthesis records consensus, disagreements, Devil's Advocate
  disposition, and the prioritized roadmap.

Entering `TRIAGE` freezes SHA-256 values for the frozen panel and every declared
report plus `EDITORIAL_DECISION.md`. Later revision may change the manuscript,
but it must not rewrite the historical review record. Entering `SUBMISSION_QA`
likewise freezes `RE_REVIEW.md`.

## Stage 5: TRIAGE

The scheduler deduplicates findings into revision tickets. Separate:

- definite factual or validity defects;
- claim/evidence mismatches;
- readability and organization improvements;
- venue/compliance defects;
- experiment requests;
- optional taste or polish.

For experiment requests, report `GO`, `CONDITIONAL GO`, or `NO-GO` as an agent
recommendation, then preserve the user's decision separately. When the project
has declared experiments complete, prefer claim narrowing or limitations unless
the request is a genuine P0/P1 validity blocker.

Copy every frozen `EXP-REQ` identifier into `EXPERIMENT_REQUESTS.md`. Each row
records resolution, authority/evidence, concrete action, and status. A new run
requires explicit user/PI evidence or an exact project-policy authority. The
controller will not enter `REVISING` while a request lacks a decision.
Copy every reviewer `REV-REQ-*` identifier into `REVISION_LEDGER.md`.
`NO_REQUIRED_REVISIONS` is valid only when no reviewer emitted a revision ID.

Gate `G5 REVISION_PLAN_ACCEPTED`:

- every P0/P1 concern has a planned resolution, explicit user deferral, or
  documented blocker;
- experiment requests are not confused with approved work;
- revision ownership and target files are unambiguous.

## Stage 6: REVISING

Apply accepted tickets in controlled passes:

1. factual and claim corrections;
2. structure and argument;
3. tables, figures, captions, appendix, and citations;
4. style and compression;
5. source-format synchronization.

Complete all conference-format, table, font, figure, and pagination edits here.
Rebuild and refresh `BUILD_RECEIPT.md` after the final edit. Every experiment
request must be completed/applied/verified before entering re-review.
Every required revision ticket must have a closed status and completed
verification; a `pending` ticket cannot enter re-review.

Maintain a change ledger. Do not delete adverse evidence or inflate claims to
answer a reviewer. Use the smallest scientifically adequate change.

Gate `G6 REVISION_COMPLETE`:

- accepted tickets map to actual edits;
- rejected/deferred tickets have reasons;
- generated and source representations are synchronized;
- the revised artifact builds.

## Stage 7: RE_REVIEW

Give a fresh review subagent the original reports, revision ledger, and revised
snapshot. It loads `$academic-paper-reviewer` in `re-review` mode and verifies
each concern against the manuscript. It may identify new issues but cannot close
items merely because the response letter says they are fixed.

This snapshot is the exact final candidate: canonical source, bibliography,
rendered PDF, and build receipt. The report must declare `Scientific signoff:
PASS`, `Revision requirement: NONE`, and either `Experiment requirement: NONE`
or a complete request card. A new re-review experiment request is persisted in
workflow state before QA is allowed to fail. It must receive a recorded
decision and closed status after `reopen-revision`; replacing the report cannot
erase the request.
New re-review `REV-REQ-*` identifiers are persisted and must be closed in the
revision ledger. Entering re-review freezes both the revision and experiment
decision ledgers; changing either invalidates re-review and final QA.

Gate `G7 SCIENTIFIC_SIGNOFF`:

- no unresolved P0/P1 scientific or claim blocker remains, or the user has
  explicitly accepted a documented residual risk;
- each closed ticket has verification evidence;
- any new experiment request has been triaged.

## Stage 8: SUBMISSION_QA

Run read-only final checks on the exact re-reviewed candidate package:

- title/abstract/contributions/conclusion consistency;
- terminology ledger compliance and removal of unsupported coined jargon;
- direct, non-apologetic prose with proportionate limitations;
- all numbers, captions, tables, and appendix cross-references;
- citation-key completeness, reference authenticity, and local citation fit;
- template, page limits, anonymity, fonts, figures, tables, and accessibility;
- main-figure placement uses its declared physical width without hidden
  downscaling; editable/vector text, embedded fonts, grayscale meaning, and
  caption/source synchronization remain valid;
- one-column tables aligned to `\columnwidth`, two-column tables aligned to
  `\textwidth`, and documented exceptions rather than accidental natural width;
- venue-compatible three-line tables (`booktabs` by default), no vertical rules,
  consistent document fonts, and no `tiny` text used to force fit;
- build errors, overflows, missing assets, and source/PDF synchronization;
- rendered visual inspection of dense or transition pages;
- ethics, limitations, data/code availability, conflicts, funding, author
  contributions, acknowledgments, and AI-disclosure fields as applicable;
- supplementary/archive/reproducibility manifest as required by the venue.

The exact final candidate must receive a `$paper-compile-layout-qa` final gate.
A successful TeX exit is not sufficient: compile logs, page count, fonts,
figures/tables, column/page layout, and the rendered PDF must all be checked
against the current conference requirements.
If the venue-format contract is enabled, rerun its strict audit after the last
revision and before re-review; the frozen profile/audit hashes must remain
unchanged through read-only `SUBMISSION_QA`.

Before rendering, run `scripts/tex_table_audit.py` on the real LaTeX source.
Treat it as a structural preflight, not a substitute for PDF inspection. Follow
[conference-format-qa.md](conference-format-qa.md) for the acceptance contract.
Rebuild `TABLE_QA.md` on this exact final candidate, include every main and
appendix table, and record the final PDF path/hash. An earlier reviewable-draft
table check cannot be reused as final sign-off without revalidation.

Do not edit source, bibliography, PDF, or build receipt in this stage. If any
defect requires a change, run `reopen-revision`, apply the fix, rebuild, and
re-review the resulting candidate. There is no "layout-only" exemption.

Gate `G8 PACKAGE_SIGNOFF`:

- the exact PDF has been rendered and inspected;
- no unresolved references, missing assets, or critical layout defects remain;
- external/user-supplied blockers are explicit;
- the final status is `SUBMISSION_READY`, `CONDITIONALLY_READY`, or
  `NOT_READY`.
- every status report binds the exact source, bibliography, and PDF hashes,
  records the build/render inspection, gives three explicit PASS/FAIL verdicts,
  and states blockers, residual risks, and the next action. A non-ready status
  cannot be represented by a one-line label.
- `CONDITIONALLY_READY` specifically means scientific PASS, manuscript PASS,
  and submission-package FAIL. Any scientific or manuscript FAIL is
  `NOT_READY`.

## Stop conditions

Stop and request a user decision when a proposed action would change the venue,
headline claim, core scientific story, frozen evidence boundary, or experiment
scope; incur meaningful cost; or submit material externally.

Do not stop for ordinary prose repair, citation cross-checking, reproducible
local builds, read-only review, or bounded layout correction within the accepted
paper plan.
