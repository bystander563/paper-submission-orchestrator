# Paper Submission Orchestrator

A Codex skill that turns a substantially fixed research project and completed
experiment package into a submission-ready manuscript through explicit story
approval, controlled drafting, independent review, revision, exact-candidate
re-review, and read-only venue/package QA.

## Recommended installation

Install the complete plugin, which includes this skill plus its reviewer and
LaTeX/PDF layout dependencies:

<https://github.com/bystander563/paper-submission-suite>

For standalone installation, clone this repository as
`$CODEX_HOME/skills/paper-submission-orchestrator` (or under the default
`.codex/skills` directory in the user profile), and install these sibling
skills as well:

- `academic-paper-reviewer`
- `paper-compile-layout-qa`

Start a new Codex task after installation so skill discovery refreshes.

## Entry point

Codex loads [`SKILL.md`](SKILL.md). Operational commands and recovery steps are
in [`references/operational-runbook.md`](references/operational-runbook.md).

## Validation

```powershell
python scripts/test_workflow_ctl.py -q
python scripts/test_tex_table_audit.py -q
```

The real-project smoke test additionally requires a LaTeX project, its native
build script, Poppler, and a baseline PDF.

## License

MIT. See [`LICENSE`](LICENSE).
