# Delegation Prompts

Replace bracketed fields with project paths and constraints. Give every agent
the same frozen revision identity. Prefer output to a separate report or
sidecar file.

Do not assume a child agent can resolve a parent skill's relative reference
path. Inline the complete Story Approval, Experiment Request, or readiness
schema into the delegation prompt whenever that schema is required.

## Evidence auditor

```text
Act as the read-only evidence auditor for [paper/project]. Read [project rules],
[fact/result artifacts], [active manuscript], and [bibliography]. Build or audit
the claim-evidence matrix. For every headline or quantitative claim, record its
exact evidence, protocol identity, exposure/evidence status, strongest allowed
wording, and overclaim boundary. Preserve negative and non-comparable results.
Also build a terminology ledger for central task, method-family, mechanism, and
metric terms. Each term must trace to authoritative primary literature,
benchmark definitions, or an official standard; mark unsupported coined jargon
for replacement with plain field-standard language. Do not edit the manuscript
and do not choose a new paper story. Return contradictions, missing provenance,
and P0/P1 blockers with exact paths.
```

## Story architect

```text
Using only [evidence ledger] and [venue contract], propose a submission-level
story blueprint: one-sentence thesis, problem-gap-mechanism-evidence-boundary
argument chain, contribution list, explicit non-claims, section plan, and the
argumentative role of each main table/figure. Provide at most [N] materially
different story options if a real ambiguity exists. Do not write the full paper
and do not invent experiments. Return a complete Story Approval Packet using
the required schema, set the next state to WAITING_FOR_STORY_APPROVAL, and stop.
Flag decisions that belong to the user/PI. Do not draft prose until the user/PI
explicitly approves the exact packet.
```

## Writer

```text
Draft [section or sidecar file] from the frozen [story blueprint], [fact pack],
[claim-evidence matrix], [terminology ledger], [venue contract], and
[bibliography]. Use calibrated, direct academic prose and authoritative field
terminology. Lead with the contribution or finding, use only necessary
qualifiers, and consolidate broad caveats in the appropriate limitations text.
Do not invent scientific terms or turn implementation nicknames into field
concepts. Every quantitative claim must map to the fact pack. Mark unresolved
items explicitly as [CHECK], [CITE], or [USER]. Do not change the scientific
story, experiment interpretation, or canonical main manuscript outside the
assigned file.

Before writing, verify that the workflow state is STORY_LOCKED and that the
current Story Approval Packet hash matches the recorded user approval. If not,
stop without drafting and report WAITING_FOR_STORY_APPROVAL.
```

## Reviewer configuration subagent

```text
[direct-mode] Use $academic-paper-reviewer Phase 0 only on the frozen reviewable manuscript
[source path/hash and PDF path/hash]. Configure exactly five read-only roles:
Editor-in-Chief, methodology reviewer, domain reviewer, perspective reviewer,
and Devil's Advocate. Write the complete configuration to [REVIEW_PANEL.md],
including `Configuration type: STANDARD_FIVE_ROLE` and the ordinary venue
calibration. Preserve the five fixed `STANDARD_FIVE_ROLE_V1` responsibility IDs;
customize only persona and field expertise. If no role or responsibility departs materially from the standard
contract, return the card for immediate controller validation and auto-freeze;
do not request user approval. If a role is added, removed, merged, or given a
materially special duty, declare `Configuration type: CUSTOM`, complete
`Special configuration rationale`, set `WAITING_FOR_REVIEW_PANEL_APPROVAL`,
and stop without reviewing. Do not disguise a custom panel as standard or infer
approval.
```

## Full review execution subagent

```text
[direct-mode] Use $academic-paper-reviewer in full mode with the already
frozen [REVIEW_PANEL.md and hash] to review the frozen manuscript
[source path/hash, bibliography path/hash, and PDF path/hash] for [target venue]. You are read-only: do
not edit the manuscript. Read [project rules], [fact pack], [claim-evidence matrix],
[terminology ledger], [bibliography], and [venue contract]. Check whether the
paper uses authoritative field terminology without invented jargon, and whether
claim caution has become unnecessarily defensive or repetitive. Return the
independent reviewer reports, editorial decision, scores, exact-location
findings, and prioritized revision roadmap. For every concern that genuinely
requires new empirical evidence,
include a complete Experiment Request Card from the schema inlined below. If
the scheduler did not inline that schema, stop and report a contract error. Never write
only "more experiments are needed". Include the minimum discriminating
experiment and the best defensible no-new-experiment alternative.

Treat the frozen `REVIEW_PANEL.md` as the completed Phase 0 configuration.
Do not rerun panel configuration or pause for another confirmation. The standard
five-role card is already auto-frozen; a custom card reaches this prompt only
after its recorded user/PI approval.

For `STANDARD_FIVE_ROLE`, write exactly five independent reports to [reviews/EIC.md],
[reviews/METHODOLOGY.md], [reviews/DOMAIN.md], [reviews/PERSPECTIVE.md], and
[reviews/DEVILS_ADVOCATE.md], plus [reviews/EDITORIAL_DECISION.md]. Every report
must contain the exact source, bibliography, and PDF SHA-256 and `Experiment requirement:
NONE` or the relevant EXP-REQ IDs. If the reviewer's declared sprint-contract
assets are absent, state `REVIEWER_COMPATIBILITY_MODE`; preserve all five roles
but do not claim machine-enforced sprint-contract execution.

For `CUSTOM`, write exactly the reviewer files declared by the approved
`Required report files` table, plus the editorial decision; do not create or
omit reviewer outputs. For both `STANDARD_FIVE_ROLE` and `CUSTOM`, every
reviewer report declares `Revision requirement: NONE` or stable `REV-REQ-*`
identifiers that must map into the revision ledger.
Reports must be independently written; byte-for-byte duplicate reviewer files
are invalid even if their headings pass schema checks.
Write each required heading and machine-control field exactly once. Never append
a second requirement, hash, status, or readiness line to override an earlier
value.

Adapt each report to the orchestrator contract with these `##` sections:
Recommendation and scope; Evidence-grounded strengths; Major concerns; Minor
concerns; Required revisions; Experiment requests; Confidence and assumptions.
The Devil's Advocate also writes `Strongest counter-argument`. The editorial
decision writes Decision; Cross-reviewer consensus; Disagreements and
arbitration; Devil's Advocate disposition; Prioritized revision roadmap; and
Experiment request summary. Record the exact bibliography SHA-256 as well.
```

## Methodology reviewer (required panel role)

```text
[direct-mode] Act as the methodology role already assigned inside the
$academic-paper-reviewer `full` five-role panel on the frozen manuscript
[source/bibliography/PDF revision]. Do not invoke the separate
`methodology-focus` mode, because it creates a reduced EIC-plus-methodology
panel. Remain read-only. Audit design, split integrity,
comparators, seed/reporting completeness, uncertainty, leakage/exposure,
reproducibility, ablation logic, and whether every conclusion follows from the
estimand. Give exact locations. Every proposed experiment must be a complete
Experiment Request Card, including positive/negative/null interpretation,
cost, claim impact, and a no-new-experiment repair. Write the required
[reviews/METHODOLOGY.md] report for the frozen five-role panel. Do not create
a sixth required reviewer or supplementary report unless the scheduler
explicitly assigns a separate independent methods check.
```

## Scheduler triage

```text
Synthesize [review reports] without erasing disagreements or inventing new
criticisms. Deduplicate findings into revision tickets and experiment requests.
Classify each experiment request as REQUIRED_BEFORE_SUBMISSION,
HIGH_VALUE_OPTIONAL, CLAIM_NARROWING_PREFERRED, or OUT_OF_SCOPE. For each,
recommend GO, CONDITIONAL GO, or NO-GO and explain whether the present paper is
defensible without it. Keep reviewer recommendations separate from user/PI
decisions. Produce a bounded revision plan; do not edit yet.
```

## Reviser

```text
Apply only the accepted tickets in [revision plan] to [assigned manuscript
files]. Use [fact pack], [story blueprint], and [claim-evidence matrix] as hard
constraints. Make the smallest sufficient edits; narrow claims or strengthen
limitations when evidence is insufficient. Keep prose, tables, captions,
appendix, bibliography, and generated source synchronized. Update the change
ledger. Preserve authoritative field terms and replace unsupported coined
jargon with standard or plain descriptive language. Keep the prose
scientifically confident: do not turn every paragraph into a disclaimer. Do not
mark your own fixes verified.
```

## Re-review subagent

```text
[direct-mode] Use $academic-paper-reviewer in re-review mode. The frozen
[REVIEW_PANEL.md] is the already completed Phase 0 configuration for this
cycle: reuse it exactly, do not rerun field analysis/persona configuration, and
do not request another panel confirmation. If any role or responsibility must
change, stop and return `CUSTOM_PANEL_REOPEN_REQUIRED` so the orchestrator can
use the custom-panel approval gate. Compare [original review reports],
[revision tickets/change ledger], and [revised manuscript/PDF]. Stay read-only.
Verify each claimed fix against the actual artifact, identify
residual or newly introduced issues, and issue a new editorial decision. Any
new experiment request must use the complete Experiment Request Card. Do not
close an issue solely because the response letter says it was addressed. Write
[reviews/RE_REVIEW.md] with the exact frozen revised-source, bibliography, PDF,
build-receipt, revision-ledger, and experiment-ledger SHA-256. Include Verification decision; Ticket-by-ticket
verification; Residual issues; New issues; Experiment requests; and Confidence
and assumptions. Declare `Scientific signoff: PASS` only if the exact candidate
passes, plus `Experiment requirement: NONE`. A new experiment request must
return the workflow to revision and another re-review.
Also declare `Revision requirement: NONE`. A new EXP-REQ is durable workflow
state: it must receive a recorded decision and closed status, and cannot be
removed by replacing this report.
A new REV-REQ is durable under the same rule. Do not sign off while any required
revision ticket is pending or lacks verification.
```

## Submission QA

```text
Load $paper-compile-layout-qa. Audit the exact submission candidate [source
revision and PDF] against the current official [venue/year/track/mode]
rules/template. Compile from the repository-native root, verify source/PDF
synchronization, page limits, anonymity, fonts, figures/tables, citations and
bibliography, cross-references, build logs, rendered-page readability,
ethics/limitations, data/code statements, and all author-supplied metadata
fields. Inspect the rendered PDF; a successful TeX exit is not enough.
Run the paper orchestrator's `scripts/tex_table_audit.py [main.tex] --strict
--output [workflow-mapped tex_table_audit.json]` on the real source and run
`scripts/pdf_font_audit.py [final.pdf] --output [workflow-mapped
pdf_font_audit.json]`. Both commands must return PASS. Verify their findings
against the rendered PDF. Check that one-column tables align
to column width, two-column tables align to text width, tables use a
venue-compatible three-line/booktabs structure without vertical rules, and
table/figure fonts remain consistent and readable without `tiny` text. For each
table, verify semantic rule hierarchy (`midrule` for real protocol boundaries,
trimmed `cmidrule` or whitespace for subordinate groups), content-aware column
allocation, multi-level headers, multirow vertical centering, and row-wise cell
alignment. If lines appear inconsistent, compare source commands and a
high-DPI/vector render before changing rule widths. Record all pages changed by
a table edit, including downstream pagination.
Rebuild [TABLE_QA.md] on the exact final PDF, record its path/hash, and include
one verified row for every main and appendix table. An earlier reviewable-draft
ledger is provisional and cannot be reused as final PASS without revalidation.
Persist the strict table and font JSON outputs at the workflow-mapped paths.
In [TABLE_QA.md], record the exact PDF path/hash; both audit commands/results;
both output-file SHA-256 values; and `TeX tables scanned`. Create exactly one
PASS row per `tables[].id` from the strict table JSON, with no extra IDs. The
strict JSON must bind the current canonical main-TeX path/hash and current hash
of every scanned include; the font JSON must bind the exact final PDF path/hash.
Distinguish definite defects, optional layout polish, and external/user-supplied
blockers. This stage is read-only even if an edit would normally be authorized:
if any protected artifact must change, return `REOPEN_REVISION_REQUIRED`. Do not
reuse the old re-review signoff. Return SUBMISSION_READY,
CONDITIONALLY_READY, or NOT_READY with the three independent readiness verdicts.
For every status, record exact source/bibliography/PDF hashes, build and render
evidence, blockers, residual risks, and a concrete next action. Use explicit
PASS/FAIL for each readiness dimension; only SUBMISSION_READY may have all
three PASS.
Use CONDITIONALLY_READY only for scientific PASS, manuscript PASS, and package
FAIL; any scientific or manuscript FAIL is NOT_READY.
```
