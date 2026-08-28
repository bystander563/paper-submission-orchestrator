---
name: paper-submission-orchestrator
description: Coordinate an evidence-grounded multi-agent workflow from a substantially fixed research direction and completed experiment package to a submission-ready manuscript. Use for story locking, drafting, independent review, revision, re-review, and final source/PDF/venue QA. Do not use for open-ended method search or early experiment exploration.
---

# Paper Submission Orchestrator

Turn finished research into a coherent, defensible, submission-ready paper. The
workflow is a controlled editorial loop, not a collection of agents writing into
one file.

Project instructions, `AGENTS.md`, frozen protocols, venue rules, and the
user's latest decisions override this skill.

## At a glance

Use this skill only after the research question, core method, and main
experiment package are substantially fixed. Success means three things pass on
the same artifact: scientific claims, manuscript quality, and the actual
submission package.

The shortest operational flow is:

`evidence intake -> story packet -> USER STORY APPROVAL -> drafting/assembly -> standard five-role panel auto-freeze (custom panel: USER APPROVAL) -> independent review -> triage -> revision and final layout -> re-review exact candidate -> read-only package QA -> readiness decision`

Mandatory human decision points:

1. The user/PI approves the exact Story Approval Packet before drafting.
2. The standard five-role reviewer configuration is validated and frozen
   automatically. User/PI approval is required only when a role is added,
   removed, merged, or given materially non-standard responsibilities.
3. A reviewer request for a new experiment is triaged first; execution needs
   user authorization unless existing project policy already grants it.
4. External submission, upload, publication, or sending always needs explicit
   user authorization.

Use these files by purpose:

| Need | Read or run |
|---|---|
| Decide the current stage and gate | [references/workflow.md](references/workflow.md) |
| Execute or resume the workflow | [references/operational-runbook.md](references/operational-runbook.md) and `scripts/workflow_ctl.py` |
| Delegate a bounded role | [references/agent-prompts.md](references/agent-prompts.md) |
| Create or validate an artifact | [references/artifact-contracts.md](references/artifact-contracts.md) |
| Audit wording and field terminology | [references/writing-and-terminology.md](references/writing-and-terminology.md) |
| Audit conference tables, fonts, and rendered layout | [references/conference-format-qa.md](references/conference-format-qa.md) |

Runtime skill dependencies are `$academic-paper-reviewer` and
`$paper-compile-layout-qa`. The `paper-submission-suite` plugin installs all
three together. If either dependency is absent, stop before its stage and
report the missing skill instead of silently substituting a weaker workflow.

## Authority and invariants

- The user or PI owns the target venue, headline claim, scientific positioning,
  authorization for new experiments, and external submission.
- The user or PI must explicitly approve the Story Approval Packet before any
  manuscript drafting begins. The integrator cannot self-approve it. Silence,
  timeout, or approval of a different artifact grants no authority.
- The scheduler/integrator owns workflow state and the canonical manuscript.
- The exact standard five-role panel is a frozen default, not a human decision
  gate. A custom role roster or materially altered responsibility must be
  labeled `CUSTOM`, justified, and approved by the user/PI before review.
- Standard review responsibilities use the fixed `STANDARD_FIVE_ROLE_V1`
  charter. Field-specific personas may vary; changing a responsibility ID or
  adding a reviewer makes the configuration `CUSTOM`.
- A `CUSTOM` card must enumerate every reviewer in `Required report files`.
  The controller requires exactly those declared reports and rejects undeclared
  reviewer outputs, so added, removed, or merged roles cannot disappear at
  triage.
- Reviewers are read-only. They produce review artifacts and never edit the
  submitted manuscript.
- Keep one writer for the canonical manuscript at a time. Parallel writers may
  draft disjoint sidecar files after the story is locked; the integrator merges
  them.
- Never invent metrics, citations, protocols, statistical significance,
  experiment status, or venue metadata. Preserve negative, exposed,
  exploratory, and non-comparable evidence labels.
- Use established field terminology from authoritative primary literature,
  benchmark/task definitions, or official venue guidance. Do not coin new task
  labels, mechanism categories, metrics, or scientific jargon for rhetorical
  novelty. A new method name is allowed only when it accurately describes the
  mechanism and does not misrepresent an established term.
- Claim discipline must not turn the prose defensive. State the contribution
  and result directly; place necessary scope conditions where they matter and
  consolidate broader caveats in limitations instead of repeating apologies.
- A reviewer request is not an authorized experiment. Record and triage it;
  do not launch it unless the user has authorized that experiment or an
  existing project policy clearly grants that authority.
- Do not improve a failed scientific claim by silently changing its protocol,
  comparator, seed roster, threshold, or evaluation population.

## Intake and routing

Before writing, identify the current equivalents of:

1. project brief and active instructions;
2. paper facts or evidence ledger, including adverse results and exposure
   boundaries;
3. innovation direction, one-sentence thesis, explicit non-claims, and venue;
4. active manuscript source, bibliography, figures/tables, build path, and
   latest rendered PDF;
5. existing review reports, decision log, and unresolved placeholders.

Also build a small terminology ledger for the paper's central scientific terms:
term, authoritative source, accepted meaning, and intended manuscript usage.
Resolve terminology drift before story lock.

If these are incomplete, create or update lightweight equivalents before
drafting. Do not replace a project's established artifact names merely to match
this skill.

Use this skill when the task, dataset, core method, and main experiment package
are already substantially fixed. If the work still needs problem selection,
method search, or broad experimental iteration, route to a research workflow
instead.

## Agent topology

The main agent is the scheduler/integrator. Delegate only bounded work with a
clear input snapshot and output file or report:

- **Evidence auditor:** builds the fact/claim/evidence ledger and flags
  contradictions. It does not choose the story.
- **Story architect:** proposes the argument chain, contribution hierarchy,
  table/figure plan, and limitations from the ledger. The user/PI approves the
  exact packet; the integrator only records and enforces that decision.
- **Writer:** drafts claim-safe prose from the frozen story and evidence.
- **Review subagents:** must load `$academic-paper-reviewer`. For the first
  serious review, use `full` mode for the frozen five-role panel. The
  methodology role inside that full panel applies the methodology rubric;
  do not invoke the separate `methodology-focus` mode, which is a reduced
  EIC-plus-methodology panel. An extra reviewer is a `CUSTOM` configuration.
  After all content and layout edits, use `re-review` mode on the exact final
  candidate snapshot.
- **Reviser:** converts accepted review items into minimal manuscript edits. It
  cannot declare its own fixes verified.
- **Submission QA:** checks citations, template compliance, anonymization,
  build logs, rendered pages, source/PDF synchronization, and author-supplied
  metadata blockers. It must load `$paper-compile-layout-qa` for LaTeX build and
  rendered-layout work.

When delegation is unavailable or not authorized, perform the same roles
sequentially and keep their artifacts logically separate.

Parallelize read-only work on the same frozen snapshot. Serialize story
decisions, canonical manuscript edits, and final merge operations.

## State machine

Run the stages and gates in [references/workflow.md](references/workflow.md):

`INTAKE -> WAITING_FOR_STORY_APPROVAL -> STORY_LOCKED -> DRAFTING -> ASSEMBLING -> REVIEWABLE -> REVIEWING -> TRIAGE -> REVISING -> RE_REVIEW -> SUBMISSION_QA -> SUBMISSION_READY | CONDITIONALLY_READY | NOT_READY`

Only a `CUSTOM` reviewer configuration inserts
`REVIEWABLE -> WAITING_FOR_REVIEW_PANEL_APPROVAL -> REVIEWING`. The
`STANDARD_FIVE_ROLE` path freezes the panel, source, and PDF and enters review
directly.

`SUBMISSION_QA` is read-only. The re-review snapshot freezes the final source,
bibliography, PDF, and build receipt. If any frozen artifact changes, use
`reopen-revision`, rebuild, and re-review the new exact candidate before a
readiness decision.

Every initial reviewer must emit `Revision requirement: NONE` or stable
`REV-REQ-*` identifiers. Every requested identifier must appear in the revision
ledger; `NO_REQUIRED_REVISIONS` is invalid when any reviewer requested a
revision. Re-review `EXP-REQ-*` identifiers are persisted into workflow state
before QA can fail, and remain subject to explicit decision and closure even if
the re-review report is later replaced.
Re-review `REV-REQ-*` identifiers are persisted the same way. Before re-review,
every required revision ticket must be closed and have completed verification.
The revision and experiment-decision ledgers are part of the re-review snapshot
and cannot change during re-review or final QA.
Machine-control fields and required headings are single-valued: each must occur
exactly once. Duplicate requirement, status, hash, or readiness fields are a
hard failure rather than a first-match override.

`STORY_LOCKED` requires a recorded user approval and the SHA-256 of the exact
Story Approval Packet. If that packet changes materially, invalidate the
approval and return to `WAITING_FOR_STORY_APPROVAL`.

For a real project, use `scripts/workflow_ctl.py` as the durable control plane.
It initializes the workflow artifacts, records approvals, freezes source/PDF
hashes for review, rejects illegal transitions, detects post-approval story
changes, validates required review outputs, and records the terminal readiness
status. The script records authority; it does not create it. Call
`approve-story` only after explicit approval of the identified story packet.
Call `approve-review-panel` only for a `CUSTOM` configuration after explicit
user/PI approval; the standard panel uses `advance --to REVIEWING`.

Read [references/operational-runbook.md](references/operational-runbook.md)
before starting or resuming a multi-stage run. Resume from `state.json`; do not
reconstruct approval or review state from chat memory.

Do not skip from a readable draft directly to a terminal readiness state. A
successful scientific review does not prove that citations, author metadata,
anonymity, venue format, or the actual rendered PDF are submission-ready.

## Review hard contract

Every review report must contain an editorial recommendation, evidence-grounded
major/minor concerns, exact manuscript locations where possible, and a
prioritized revision roadmap. Review subagents must use
`$academic-paper-reviewer` and remain read-only.

The controller validates substantive report sections, not only filenames and
hashes. The editorial synthesis must preserve consensus, disagreements, the
Devil's Advocate disposition, and a prioritized roadmap.

If a reviewer believes an experiment is needed, it must not write only "add
more experiments." It must emit an **Experiment Request Card** for each request
using [references/artifact-contracts.md](references/artifact-contracts.md). The
card must specify the reviewer question, why current evidence is insufficient,
the minimum discriminating experiment, protocol and comparators, metrics and
reporting, positive/negative/null interpretation, cost, claim impact, and the
best no-new-experiment alternative.

The integrator deduplicates the cards and labels each request:

- `REQUIRED_BEFORE_SUBMISSION`: unresolved validity or headline-claim blocker;
- `HIGH_VALUE_OPTIONAL`: likely score gain, but the paper remains defensible
  without it;
- `CLAIM_NARROWING_PREFERRED`: cost or scope is disproportionate; narrow the
  claim or strengthen limitations;
- `OUT_OF_SCOPE`: unrelated wishlist or a new research direction.

Present the experiment queue to the user with a recommendation. Keep reviewer
requests distinct from user-approved experiments.
Before revision, every EXP-REQ identifier must have a recorded resolution,
authority/evidence, action, and status. Before re-review, every request must be
completed, applied, or verified; unresolved requests cannot silently disappear.

## Revision and verification

- Convert accepted concerns into traceable revision tickets: concern, evidence,
  file/location, edit, owner, status, and verification result.
- Apply the smallest edit that resolves the issue. If evidence cannot support
  the original wording, narrow the claim and update limitations.
- Keep prose, tables, captions, appendix, bibliography, and generated LaTeX in
  sync.
- During prose revision, preserve an assertive scientific register: lead with
  the supported finding, state the relevant boundary once, and avoid strings of
  defensive qualifiers that obscure the contribution.
- Re-review against the original concern list. A concern closes only after an
  independent verifier checks the revised artifact; an author's response alone
  is not verification.
- New concerns found during re-review enter the same triage process. Avoid an
  endless polish loop: only unresolved validity, claim, reproducibility, or
  venue blockers prevent finalization.

## Final decision

Report three separate dimensions before handoff:

1. **Scientific readiness:** claims follow from evidence and limitations are
   explicit.
2. **Manuscript readiness:** the story is coherent, complete, cited, and
   internally consistent.
3. **Submission-package readiness:** the correct template builds, the rendered
   PDF passes visual QA, and required metadata/checklists are complete.

Submission-package QA must also apply the table/font contract in
[references/conference-format-qa.md](references/conference-format-qa.md). Run
`scripts/tex_table_audit.py` for source-level table checks and
`scripts/pdf_font_audit.py` for embedded-font and rendered-size checks, then
use `$paper-compile-layout-qa` for rendered confirmation. Source lint cannot
prove visual width or readability by itself, and a size warning still requires
human inspection of the affected page. Complete the generated `TABLE_QA.md`
for every main and appendix table; `SUBMISSION_READY` is blocked until that
ledger passes on the exact candidate PDF.

`BUILD_RECEIPT.md` must bind the exact final source, bibliography, discovered
local TeX inputs/figures/styles, and PDF to a successful repository-native
build and rendered inspection. Use `workflow_ctl.py fingerprint` to generate
the dependency-bundle hash. The final
readiness report repeats those hashes and audit evidence. Any post-re-review
edit invalidates scientific signoff.
Figure discovery includes `\graphicspath` search directories, not only images
written relative to the current TeX file.
Dependency parsing accepts legal whitespace between supported TeX commands and
their braced arguments (for example, `\input {body}` and
`\graphicspath {{figures/}}`).
For LaTeX candidates, require compiler dependency output via
`init --dependency-manifest`: use recorder `.fls` for latexmk/pdflatex or a
Tectonic `--makefile-rules` `.mk`/`.d` file. Compiler-reported inputs are the
primary dependency inventory, and source parsing is a supplementary preflight.
An `.fls` must contain a valid `PWD`, the canonical source plus another existing
`INPUT`, no missing inputs, and the exact PDF as an `OUTPUT`. A Tectonic rule
must target the exact PDF and resolve the canonical source plus another local
input after output-directory projection is mapped back to the source tree.

Use one terminal status:

- `SUBMISSION_READY`: all three dimensions pass and no P0/P1 blockers remain.
- `CONDITIONALLY_READY`: scientific/manuscript review passes, but user-supplied
  metadata or a bounded external requirement remains.
- `NOT_READY`: a scientific, manuscript, build, or venue blocker remains.

All three terminal statuses require the exact source, bibliography, and PDF
hashes; explicit scientific, manuscript, and package PASS/FAIL verdicts; build
and rendered-inspection evidence; blockers/risks; and a concrete next action.
Only `SUBMISSION_READY` additionally requires all three verdicts to pass and the
strict table/source marker gates to pass.
`CONDITIONALLY_READY` is encoded specifically as scientific PASS, manuscript
PASS, and submission-package FAIL; scientific or manuscript failure is
`NOT_READY`.

Never submit, upload, publish, or send the paper without explicit user
authorization.
