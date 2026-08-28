# Cross-skill rule ownership

Use one canonical owner for each enforceable rule. Copies in the suite plugin
are release mirrors and must remain byte-identical to their canonical skill.

| Rule family | Canonical owner | Orchestrator responsibility |
|---|---|---|
| Story approval, state transitions, snapshots, review and readiness gates | `paper-submission-orchestrator` | Enforce and persist |
| Five-role sprint outputs, phase lint, fatal flags, majority arithmetic, synthesis receipt | `academic-paper-reviewer` | Require and freeze the PASS receipt |
| Main-figure topology, visual QA, verdict, artifact manifest | `paper-main-figure` | Require `PAPER_READY` before drafting and `CAMERA_READY` before final re-review |
| Venue profile, compile log, format audit, rendered layout | `paper-compile-layout-qa` | Bind the exact PASS audit and keep final QA read-only |
| Plugin packaging and copied skill files | `paper-submission-suite` plugin | Mirror canonical owners; do not redefine behavior |

When a rule changes, update its canonical owner first, add or update executable
tests there, then update the orchestrator handoff and plugin mirror. Do not fix
drift by adding a competing rule to a downstream skill.
