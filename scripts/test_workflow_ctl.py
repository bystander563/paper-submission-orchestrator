from __future__ import annotations

import json
import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from pypdf import PdfWriter


SCRIPT = Path(__file__).with_name("workflow_ctl.py")


def completed_story() -> str:
    headings = (
        "One-sentence thesis",
        "Target venue and paper type",
        "Argument chain",
        "Headline contributions",
        "Explicit non-claims",
        "Main claim-evidence mapping",
        "Authoritative terminology decisions",
        "Main tables and figures",
        "Main-text and appendix allocation",
        "Remaining paper-level decisions",
        "Agent recommendation",
    )
    blocks = ["# Story Approval Packet", "", "- Packet ID: STORY-TEST", ""]
    for heading in headings:
        blocks.extend((f"## {heading}", "", f"Completed content for {heading}.", ""))
    return "\n".join(blocks)


def completed_panel(custom: bool = False) -> str:
    roles = {
        "Editor-in-Chief": "EIC_STANDARD_V1",
        "Methodology Reviewer": "METHODOLOGY_STANDARD_V1",
        "Domain Reviewer": "DOMAIN_STANDARD_V1",
        "Perspective Reviewer": "PERSPECTIVE_STANDARD_V1",
        "Devil's Advocate": "DEVILS_ADVOCATE_STANDARD_V1",
    }
    panel_type = "CUSTOM" if custom else "STANDARD_FIVE_ROLE"
    blocks = [
        "# Reviewer Configuration Card",
        "",
        f"- Configuration type: {panel_type}",
        "",
    ]
    for role, responsibility_id in roles.items():
        blocks.extend(
            (
                f"## {role}",
                "",
                f"- Persona and expertise: Independent {role} specialist.",
                f"- Responsibility ID: {'CUSTOM_' + responsibility_id if custom else responsibility_id}",
                "",
            )
        )
    blocks.extend(
        (
            "## Review mode and venue calibration",
            "",
            "Full review calibrated to the declared conference and track.",
            "",
            "## Special configuration rationale",
            "",
            (
                "The domain reviewer receives an additional deployment-safety mandate."
                if custom
                else "Not applicable for STANDARD_FIVE_ROLE."
            ),
            "",
        )
    )
    if custom:
        blocks.extend(
            (
                "## Required report files",
                "",
                "| Role | Output file |",
                "|---|---|",
                "| Editor-in-Chief | EIC.md |",
                "| Methodology Reviewer | METHODOLOGY.md |",
                "| Domain Reviewer | DOMAIN.md |",
                "| Perspective Reviewer | PERSPECTIVE.md |",
                "| Devil's Advocate | DEVILS_ADVOCATE.md |",
                "",
            )
        )
    return "\n".join(blocks)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_minimal_pdf(path: Path, marker: str) -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.add_metadata({"/Subject": marker})
    with path.open("wb") as stream:
        writer.write(stream)


def completed_experiment_card(request_id: str = "EXP-REQ-TEST") -> str:
    fields = (
        "Reviewer question",
        "Manuscript claim at risk",
        "Why current evidence is insufficient",
        "Priority recommendation",
        "Minimum discriminating experiment",
        "Hypothesis and falsifier",
        "Data, split, revision, and exposure status",
        "Comparator(s) and control(s)",
        "Frozen training/selection/evaluation protocol",
        "Metrics, uncertainty, seeds, and reporting unit",
        "Positive-result interpretation",
        "Negative-result interpretation",
        "Null/ambiguous-result interpretation",
        "Estimated compute, wall time, and implementation risk",
        "Claim unlocked if successful",
        "Best no-new-experiment repair",
        "Can the current paper remain defensible without it? Why",
        "Reviewer confidence and assumptions",
    )
    lines = [f"### {request_id}: Minimal discriminating control", ""]
    lines.extend(f"- {field}: Completed value for {field}." for field in fields)
    return "\n".join(lines) + "\n"


class WorkflowCtlTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="paper_workflow_test_")
        self.root = Path(self.temporary.name) / "project"
        (self.root / "paper").mkdir(parents=True)
        (self.root / "paper" / "main.md").write_text("# Paper\n\nVerified draft.\n", encoding="utf-8")
        (self.root / "paper" / "refs.bib").write_text("% bibliography\n", encoding="utf-8")
        write_minimal_pdf(self.root / "paper" / "main.pdf", "initial candidate")
        result = self.run_cli(
            "init",
            "--project-root",
            str(self.root),
            "--venue",
            "ACL",
            "--year",
            "2026",
            "--track",
            "main",
            "--mode",
            "review",
            "--source",
            "paper/main.md",
            "--bibliography",
            "paper/refs.bib",
            "--pdf",
            "paper/main.pdf",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.state_dir = self.root / ".paper-workflow"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            text=True,
            capture_output=True,
            check=False,
        )

    def test_enabled_venue_format_contract_is_bound_and_frozen(self) -> None:
        root = Path(self.temporary.name) / "format-project"
        (root / "paper").mkdir(parents=True)
        source = root / "paper" / "main.md"
        bibliography = root / "paper" / "refs.bib"
        pdf = root / "paper" / "main.pdf"
        profile_path = root / "paper" / "venue-profile.json"
        source.write_text("# Paper\n\nVerified draft.\n", encoding="utf-8")
        bibliography.write_text("% bibliography\n", encoding="utf-8")
        write_minimal_pdf(pdf, "format candidate")
        profile = {
            "profile_version": 1,
            "venue": "ACL",
            "year": 2026,
            "track": "main",
            "mode": "review",
            "verified_at": "2026-08-28",
            "official_sources": [
                {
                    "title": "Official guide",
                    "url": "https://example.org/official",
                    "accessed": "2026-08-28",
                    "supports": ["template", "page_policy", "mode_rules", "pdf"],
                }
            ],
        }
        profile_path.write_text(json.dumps(profile), encoding="utf-8")
        initialized = self.run_cli(
            "init",
            "--project-root",
            str(root),
            "--venue",
            "ACL",
            "--year",
            "2026",
            "--track",
            "main",
            "--mode",
            "review",
            "--source",
            "paper/main.md",
            "--bibliography",
            "paper/refs.bib",
            "--pdf",
            "paper/main.pdf",
            "--venue-profile",
            "paper/venue-profile.json",
        )
        self.assertEqual(initialized.returncode, 0, initialized.stderr)
        state_dir = root / ".paper-workflow"
        (state_dir / "STORY_APPROVAL_PACKET.md").write_text(
            completed_story(), encoding="utf-8"
        )
        self.assertEqual(
            self.run_cli("submit-story", "--state", str(state_dir)).returncode, 0
        )
        self.assertEqual(
            self.run_cli(
                "approve-story",
                "--state",
                str(state_dir),
                "--by",
                "USER",
                "--evidence",
                "通过",
            ).returncode,
            0,
        )
        for stage in ("DRAFTING", "ASSEMBLING"):
            advanced = self.run_cli("advance", "--state", str(state_dir), "--to", stage)
            self.assertEqual(advanced.returncode, 0, advanced.stderr)

        audit_path = state_dir / "format-audit.json"
        audit = {
            "schema_version": 1,
            "status": "PASS",
            "profile": {
                "sha256": file_sha256(profile_path),
                "venue": "ACL",
                "year": 2026,
                "track": "main",
                "mode": "review",
            },
            "tex": {"main_sha256": file_sha256(source)},
            "pdf": {"sha256": file_sha256(pdf)},
            "findings": [],
        }
        audit_path.write_text(json.dumps(audit), encoding="utf-8")
        fingerprint_result = self.run_cli("fingerprint", "--state", str(state_dir))
        self.assertEqual(fingerprint_result.returncode, 0, fingerprint_result.stderr)
        fingerprint = json.loads(fingerprint_result.stdout)
        (state_dir / "BUILD_RECEIPT.md").write_text(
            "# Build Receipt\n\n"
            "- Status: PASS\n"
            "- Command: test-build\n"
            f"- Source SHA-256: {file_sha256(source)}\n"
            f"- Bibliography SHA-256: {file_sha256(bibliography)}\n"
            f"- Dependency bundle SHA-256: {fingerprint['dependency_bundle_sha256']}\n"
            f"- Venue profile SHA-256: {file_sha256(profile_path)}\n"
            f"- Format audit SHA-256: {file_sha256(audit_path)}\n"
            f"- Output PDF SHA-256: {file_sha256(pdf)}\n"
            "- Page count: 1\n"
            "- Undefined references/citations: 0\n"
            "- Missing files: 0\n"
            "- Overfull boxes: 0\n"
            "- Rendered inspection: PASS; pages=ALL; evidence=format fixture inspected\n",
            encoding="utf-8",
        )
        reviewable = self.run_cli(
            "advance", "--state", str(state_dir), "--to", "REVIEWABLE"
        )
        self.assertEqual(reviewable.returncode, 0, reviewable.stderr)
        state = json.loads((state_dir / "state.json").read_text(encoding="utf-8"))
        self.assertTrue(state["format_contract"]["enabled"])

        (state_dir / "REVIEW_PANEL.md").write_text(completed_panel(), encoding="utf-8")
        profile["track"] = "short"
        profile_path.write_text(json.dumps(profile), encoding="utf-8")
        blocked = self.run_cli(
            "advance", "--state", str(state_dir), "--to", "REVIEWING"
        )
        self.assertNotEqual(blocked.returncode, 0)
        self.assertIn("venue profile", blocked.stderr.lower())

    def submit_and_approve_story(self) -> None:
        packet = self.state_dir / "STORY_APPROVAL_PACKET.md"
        packet.write_text(completed_story(), encoding="utf-8")
        self.assertEqual(
            self.run_cli("submit-story", "--state", str(self.state_dir)).returncode,
            0,
        )
        self.assertEqual(
            self.run_cli(
                "approve-story",
                "--state",
                str(self.state_dir),
                "--by",
                "USER",
                "--evidence",
                "通过，按这个写",
            ).returncode,
            0,
        )

    def write_build_receipt(self) -> None:
        source = self.root / "paper" / "main.md"
        bibliography = self.root / "paper" / "refs.bib"
        pdf = self.root / "paper" / "main.pdf"
        fingerprint_result = self.run_cli(
            "fingerprint", "--state", str(self.state_dir)
        )
        self.assertEqual(fingerprint_result.returncode, 0, fingerprint_result.stderr)
        fingerprint = json.loads(fingerprint_result.stdout)
        (self.state_dir / "BUILD_RECEIPT.md").write_text(
            "# Build Receipt\n\n"
            "- Status: PASS\n"
            "- Command: test-build --frozen-inputs\n"
            f"- Source SHA-256: {file_sha256(source)}\n"
            f"- Bibliography SHA-256: {file_sha256(bibliography)}\n"
            f"- Dependency bundle SHA-256: {fingerprint['dependency_bundle_sha256']}\n"
            f"- Output PDF SHA-256: {file_sha256(pdf)}\n"
            "- Page count: 1\n"
            "- Undefined references/citations: 0\n"
            "- Missing files: 0\n"
            "- Overfull boxes: 0\n"
            "- Rendered inspection: PASS; pages=ALL; evidence=test fixture inspected\n",
            encoding="utf-8",
        )

    def advance_to_reviewable(self) -> None:
        for stage in ("DRAFTING", "ASSEMBLING"):
            result = self.run_cli("advance", "--state", str(self.state_dir), "--to", stage)
            self.assertEqual(result.returncode, 0, result.stderr)
        self.write_build_receipt()
        result = self.run_cli(
            "advance", "--state", str(self.state_dir), "--to", "REVIEWABLE"
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def advance_to_reviewing(self) -> dict[str, str]:
        self.submit_and_approve_story()
        self.advance_to_reviewable()
        (self.state_dir / "REVIEW_PANEL.md").write_text(completed_panel(), encoding="utf-8")
        reviewing = self.run_cli(
            "advance", "--state", str(self.state_dir), "--to", "REVIEWING"
        )
        self.assertEqual(reviewing.returncode, 0, reviewing.stderr)
        state = json.loads((self.state_dir / "state.json").read_text(encoding="utf-8"))
        self.assertEqual(
            state["approvals"]["review_panel"]["status"], "STANDARD_AUTO_FROZEN"
        )
        return state["review_snapshot"]

    def write_review_outputs(self, snapshot: dict[str, str], experiment: bool = False) -> None:
        reviews = self.state_dir / "reviews"
        roles = ("EIC", "METHODOLOGY", "DOMAIN", "PERSPECTIVE", "DEVILS_ADVOCATE")
        for index, role in enumerate(roles):
            requirement = "EXP-REQ-TEST" if experiment and index == 0 else "NONE"
            revision_requirement = "REV-REQ-CLARITY" if index == 0 else "NONE"
            card = "\n" + completed_experiment_card() if requirement != "NONE" else ""
            content = (
                f"# {role} Review\n\n"
                f"Source snapshot SHA-256: {snapshot['canonical_source_sha256']}\n\n"
                f"Bibliography snapshot SHA-256: {snapshot['bibliography_sha256']}\n\n"
                f"PDF snapshot SHA-256: {snapshot['rendered_pdf_sha256']}\n\n"
                f"Experiment requirement: {requirement}\n\n"
                f"Revision requirement: {revision_requirement}\n\n"
                "## Recommendation and scope\n\nMinor revision within the frozen scope.\n\n"
                "## Evidence-grounded strengths\n\nVerified strength with an exact location.\n\n"
                "## Major concerns\n\nNONE.\n\n"
                "## Minor concerns\n\nOne bounded clarity issue.\n\n"
                "## Required revisions\n\nApply the bounded clarity repair.\n\n"
                f"## Experiment requests\n\n{('See complete request below.' + card) if card else 'NONE.'}\n\n"
                "## Confidence and assumptions\n\nHigh confidence under the frozen evidence package.\n\n"
                + (
                    "## Strongest counter-argument\n\nThe strongest alternative explanation is bounded.\n"
                    if role == "DEVILS_ADVOCATE"
                    else ""
                )
            )
            (reviews / f"{role}.md").write_text(content, encoding="utf-8")
        (reviews / "EDITORIAL_DECISION.md").write_text(
            "# Editorial Decision\n\n"
            f"Source snapshot SHA-256: {snapshot['canonical_source_sha256']}\n\n"
            f"Bibliography snapshot SHA-256: {snapshot['bibliography_sha256']}\n\n"
            f"PDF snapshot SHA-256: {snapshot['rendered_pdf_sha256']}\n\n"
            "## Decision\n\nMinor Revision.\n\n"
            "## Cross-reviewer consensus\n\nThe five reviewers agree on the bounded repair.\n\n"
            "## Disagreements and arbitration\n\nNONE.\n\n"
            "## Devil's Advocate disposition\n\nThe counter-argument is addressed by scope.\n\n"
            "## Prioritized revision roadmap\n\n1. Apply the bounded repair.\n\n"
            "## Experiment request summary\n\nSee individual reports; NONE unless listed.\n",
            encoding="utf-8",
        )

    def write_revision_ledger(self) -> None:
        (self.state_dir / "REVISION_LEDGER.md").write_text(
            "# Revision Ledger\n\n"
            "| Ticket ID | Review finding | Decision | Rationale | Target | Planned change | Owner | Status | Verification |\n"
            "|---|---|---|---|---|---|---|---|---|\n"
            "| REV-REQ-CLARITY | Minor clarity issue | Accept | Evidence supports repair | paper/main.md | Clarify sentence | writer | applied | verified |\n",
            encoding="utf-8",
        )

    def write_rereview_report(
        self, snapshot: dict[str, str], experiment: bool = False, revision: bool = False
    ) -> str:
        requirement = "EXP-REQ-REREVIEW" if experiment else "NONE"
        revision_requirement = "REV-REQ-REREVIEW" if revision else "NONE"
        card = "\n" + completed_experiment_card("EXP-REQ-REREVIEW") if experiment else ""
        text = (
            "# Verification Review\n\n"
            f"Source snapshot SHA-256: {snapshot['canonical_source_sha256']}\n\n"
            f"Bibliography snapshot SHA-256: {snapshot['bibliography_sha256']}\n\n"
            f"PDF snapshot SHA-256: {snapshot['rendered_pdf_sha256']}\n\n"
            f"Build receipt SHA-256: {snapshot['build_receipt_sha256']}\n\n"
            f"Revision ledger SHA-256: {snapshot['revision_ledger_sha256']}\n\n"
            f"Experiment ledger SHA-256: {snapshot['experiment_requests_sha256']}\n\n"
            f"Experiment requirement: {requirement}\n\n"
            f"Revision requirement: {revision_requirement}\n\n"
            "## Verification decision\n\n- Scientific signoff: PASS\n\n"
            "## Ticket-by-ticket verification\n\nREV-REQ-CLARITY is verified.\n\n"
            "## Residual issues\n\nNONE.\n\n"
            "## New issues\n\nNONE.\n\n"
            f"## Experiment requests\n\n{('See request.' + card) if card else 'NONE.'}\n\n"
            "## Confidence and assumptions\n\nHigh confidence.\n"
        )
        (self.state_dir / "reviews" / "RE_REVIEW.md").write_text(text, encoding="utf-8")
        return text

    def advance_to_rereview(self) -> dict[str, str]:
        snapshot = self.advance_to_reviewing()
        self.write_review_outputs(snapshot)
        self.assertEqual(
            self.run_cli("advance", "--state", str(self.state_dir), "--to", "TRIAGE").returncode,
            0,
        )
        self.write_revision_ledger()
        self.assertEqual(
            self.run_cli("advance", "--state", str(self.state_dir), "--to", "REVISING").returncode,
            0,
        )
        source = self.root / "paper" / "main.md"
        source.write_text("# Paper\n\nRevised candidate.\n", encoding="utf-8")
        write_minimal_pdf(self.root / "paper" / "main.pdf", "revised candidate")
        self.write_build_receipt()
        self.assertEqual(
            self.run_cli("advance", "--state", str(self.state_dir), "--to", "RE_REVIEW").returncode,
            0,
        )
        return json.loads((self.state_dir / "state.json").read_text(encoding="utf-8"))[
            "rereview_snapshot"
        ]

    def advance_to_submission_qa(self) -> None:
        snapshot = self.advance_to_rereview()
        self.write_rereview_report(snapshot)
        result = self.run_cli("advance", "--state", str(self.state_dir), "--to", "SUBMISSION_QA")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_story_gate_blocks_drafting_until_explicit_approval(self) -> None:
        blocked = self.run_cli(
            "advance", "--state", str(self.state_dir), "--to", "DRAFTING"
        )
        self.assertEqual(blocked.returncode, 2)

        unresolved = self.run_cli("submit-story", "--state", str(self.state_dir))
        self.assertEqual(unresolved.returncode, 2)

        packet = self.state_dir / "STORY_APPROVAL_PACKET.md"
        packet.write_text(completed_story(), encoding="utf-8")
        self.assertEqual(
            self.run_cli("submit-story", "--state", str(self.state_dir)).returncode,
            0,
        )
        waiting_status = self.run_cli("status", "--state", str(self.state_dir))
        waiting_payload = json.loads(waiting_status.stdout)
        self.assertEqual(waiting_payload["last_passed_gate"], "G0_INPUT_READY")
        self.assertIn("approve-story", waiting_payload["allowed_next_actions"])
        packet = self.state_dir / "STORY_APPROVAL_PACKET.md"
        submitted_text = packet.read_text(encoding="utf-8")
        packet.write_text(submitted_text + "\npost-submission edit\n", encoding="utf-8")
        pending_invalid = self.run_cli("validate", "--state", str(self.state_dir))
        self.assertEqual(pending_invalid.returncode, 1)
        self.assertIn("resubmit it", pending_invalid.stdout)
        packet.write_text(submitted_text, encoding="utf-8")
        still_blocked = self.run_cli(
            "advance", "--state", str(self.state_dir), "--to", "DRAFTING"
        )
        self.assertEqual(still_blocked.returncode, 2)

        self.assertEqual(
            self.run_cli(
                "approve-story",
                "--state",
                str(self.state_dir),
                "--by",
                "USER",
                "--evidence",
                "通过，按这个写",
            ).returncode,
            0,
        )
        resubmit_locked = self.run_cli("submit-story", "--state", str(self.state_dir))
        self.assertEqual(resubmit_locked.returncode, 2)
        advanced = self.run_cli(
            "advance", "--state", str(self.state_dir), "--to", "DRAFTING"
        )
        self.assertEqual(advanced.returncode, 0, advanced.stderr)

    def test_story_edit_invalidates_approval(self) -> None:
        self.submit_and_approve_story()
        packet = self.state_dir / "STORY_APPROVAL_PACKET.md"
        packet.write_text(packet.read_text(encoding="utf-8") + "\nmaterial edit\n", encoding="utf-8")
        validated = self.run_cli("validate", "--state", str(self.state_dir))
        self.assertEqual(validated.returncode, 1)
        self.assertIn("changed after approval", validated.stdout)
        blocked = self.run_cli(
            "advance", "--state", str(self.state_dir), "--to", "DRAFTING"
        )
        self.assertEqual(blocked.returncode, 2)

    def test_reviewable_requires_exact_build_receipt(self) -> None:
        self.submit_and_approve_story()
        for stage in ("DRAFTING", "ASSEMBLING"):
            result = self.run_cli("advance", "--state", str(self.state_dir), "--to", stage)
            self.assertEqual(result.returncode, 0, result.stderr)
        blocked = self.run_cli(
            "advance", "--state", str(self.state_dir), "--to", "REVIEWABLE"
        )
        self.assertEqual(blocked.returncode, 2)
        self.assertIn("BUILD_RECEIPT.md", blocked.stderr)
        self.write_build_receipt()
        accepted = self.run_cli(
            "advance", "--state", str(self.state_dir), "--to", "REVIEWABLE"
        )
        self.assertEqual(accepted.returncode, 0, accepted.stderr)

    def test_standard_review_panel_skips_manual_approval(self) -> None:
        self.submit_and_approve_story()
        self.advance_to_reviewable()
        (self.state_dir / "REVIEW_PANEL.md").write_text(
            completed_panel(), encoding="utf-8"
        )
        panel = self.state_dir / "REVIEW_PANEL.md"
        panel.write_text(
            completed_panel().replace("METHODOLOGY_STANDARD_V1", "METHODOLOGY_CUSTOM_V1"),
            encoding="utf-8",
        )
        altered_duty = self.run_cli(
            "advance", "--state", str(self.state_dir), "--to", "REVIEWING"
        )
        self.assertEqual(altered_duty.returncode, 2)
        self.assertIn("otherwise declare CUSTOM", altered_duty.stderr)
        panel.write_text(completed_panel(), encoding="utf-8")
        wrong_route = self.run_cli(
            "advance",
            "--state",
            str(self.state_dir),
            "--to",
            "WAITING_FOR_REVIEW_PANEL_APPROVAL",
        )
        self.assertEqual(wrong_route.returncode, 2)
        self.assertIn("STANDARD_FIVE_ROLE panels must be frozen directly", wrong_route.stderr)
        direct = self.run_cli(
            "advance", "--state", str(self.state_dir), "--to", "REVIEWING"
        )
        self.assertEqual(direct.returncode, 0, direct.stderr)
        state = json.loads((self.state_dir / "state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["stage"], "REVIEWING")
        self.assertEqual(
            state["approvals"]["review_panel"]["status"], "STANDARD_AUTO_FROZEN"
        )

    def test_custom_review_panel_requires_approval_and_freezes_exact_snapshot(self) -> None:
        self.submit_and_approve_story()
        self.advance_to_reviewable()

        panel = self.state_dir / "REVIEW_PANEL.md"
        panel.write_text(
            completed_panel().replace("STANDARD_FIVE_ROLE", "CUSTOM"),
            encoding="utf-8",
        )
        missing_rationale = self.run_cli(
            "advance",
            "--state",
            str(self.state_dir),
            "--to",
            "WAITING_FOR_REVIEW_PANEL_APPROVAL",
        )
        self.assertEqual(missing_rationale.returncode, 2)
        self.assertIn("requires a completed", missing_rationale.stderr)
        panel.write_text(completed_panel(custom=True), encoding="utf-8")
        direct = self.run_cli(
            "advance", "--state", str(self.state_dir), "--to", "REVIEWING"
        )
        self.assertEqual(direct.returncode, 2)
        self.assertIn("CUSTOM review panels require explicit", direct.stderr)
        waiting = self.run_cli(
            "advance",
            "--state",
            str(self.state_dir),
            "--to",
            "WAITING_FOR_REVIEW_PANEL_APPROVAL",
        )
        self.assertEqual(waiting.returncode, 0, waiting.stderr)

        source = self.root / "paper" / "main.md"
        original = source.read_text(encoding="utf-8")
        source.write_text(original + "changed before panel approval\n", encoding="utf-8")
        pending_invalid = self.run_cli("validate", "--state", str(self.state_dir))
        self.assertEqual(pending_invalid.returncode, 1)
        self.assertIn("canonical source changed after review-panel submission", pending_invalid.stdout)
        rejected = self.run_cli(
            "approve-review-panel",
            "--state",
            str(self.state_dir),
            "--by",
            "USER",
            "--evidence",
            "审稿组通过",
        )
        self.assertEqual(rejected.returncode, 2)
        source.write_text(original, encoding="utf-8")

        approved = self.run_cli(
            "approve-review-panel",
            "--state",
            str(self.state_dir),
            "--by",
            "USER",
            "--evidence",
            "审稿组通过",
        )
        self.assertEqual(approved.returncode, 0, approved.stderr)
        state = json.loads((self.state_dir / "state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["stage"], "REVIEWING")
        self.assertTrue(state["review_snapshot"]["canonical_source_sha256"])

        source.write_text(original + "changed during review\n", encoding="utf-8")
        validated = self.run_cli("validate", "--state", str(self.state_dir))
        self.assertEqual(validated.returncode, 1)
        self.assertIn("changed after the review snapshot", validated.stdout)
        source.write_text(original, encoding="utf-8")
        panel.write_text(panel.read_text(encoding="utf-8") + "\npost-approval edit\n", encoding="utf-8")
        panel_invalid = self.run_cli("validate", "--state", str(self.state_dir))
        self.assertEqual(panel_invalid.returncode, 1)
        self.assertIn("REVIEW_PANEL.md changed after freeze", panel_invalid.stdout)

    def test_full_positive_path_reaches_submission_ready(self) -> None:
        snapshot = self.advance_to_reviewing()
        self.write_review_outputs(snapshot)
        triage = self.run_cli(
            "advance", "--state", str(self.state_dir), "--to", "TRIAGE"
        )
        self.assertEqual(triage.returncode, 0, triage.stderr)

        ledger = self.state_dir / "REVISION_LEDGER.md"
        ledger.write_text(
            "# Revision Ledger\n\n"
            "| Ticket ID | Review finding | Decision | Rationale | Target | Planned change | Owner | Status | Verification |\n"
            "|---|---|---|---|---|---|---|---|---|\n"
            "| REV-REQ-CLARITY | Minor clarity issue | Accept | Evidence supports repair | paper/main.md | Clarify sentence | writer | verified | verified against source |\n",
            encoding="utf-8",
        )
        revising = self.run_cli(
            "advance", "--state", str(self.state_dir), "--to", "REVISING"
        )
        self.assertEqual(revising.returncode, 0, revising.stderr)

        source = self.root / "paper" / "main.md"
        source.write_text("# Paper\n\nRevised verified draft.\n", encoding="utf-8")
        write_minimal_pdf(self.root / "paper" / "main.pdf", "revised artifact")
        self.write_build_receipt()
        rereview = self.run_cli(
            "advance", "--state", str(self.state_dir), "--to", "RE_REVIEW"
        )
        self.assertEqual(rereview.returncode, 0, rereview.stderr)
        rereview_snapshot = json.loads(
            (self.state_dir / "state.json").read_text(encoding="utf-8")
        )["rereview_snapshot"]
        (self.state_dir / "reviews" / "RE_REVIEW.md").write_text(
            "# Verification Review\n\nAll required revisions verified.\n",
            encoding="utf-8",
        )
        blocked_weak_rereview = self.run_cli(
            "advance", "--state", str(self.state_dir), "--to", "SUBMISSION_QA"
        )
        self.assertEqual(blocked_weak_rereview.returncode, 2)
        self.assertIn("hash field 'Source snapshot SHA-256'", blocked_weak_rereview.stderr)
        rereview_report = self.state_dir / "reviews" / "RE_REVIEW.md"
        rereview_text = (
            "# Verification Review\n\n"
            f"Source snapshot SHA-256: {rereview_snapshot['canonical_source_sha256']}\n\n"
            f"Bibliography snapshot SHA-256: {rereview_snapshot['bibliography_sha256']}\n\n"
            f"PDF snapshot SHA-256: {rereview_snapshot['rendered_pdf_sha256']}\n\n"
            f"Build receipt SHA-256: {rereview_snapshot['build_receipt_sha256']}\n\n"
            f"Revision ledger SHA-256: {rereview_snapshot['revision_ledger_sha256']}\n\n"
            f"Experiment ledger SHA-256: {rereview_snapshot['experiment_requests_sha256']}\n\n"
            "Experiment requirement: NONE\n\n"
            "Revision requirement: NONE\n\n"
            "## Verification decision\n\n- Scientific signoff: PASS\n\n"
            "## Ticket-by-ticket verification\n\nREV-REQ-CLARITY is verified against the final candidate.\n\n"
            "## Residual issues\n\nNONE.\n\n"
            "## New issues\n\nNONE.\n\n"
            "## Experiment requests\n\nNONE.\n\n"
            "## Confidence and assumptions\n\nHigh confidence on the frozen snapshot.\n"
        )
        rereview_report.write_text(rereview_text, encoding="utf-8")
        qa = self.run_cli(
            "advance", "--state", str(self.state_dir), "--to", "SUBMISSION_QA"
        )
        self.assertEqual(qa.returncode, 0, qa.stderr)
        rereview_report.write_text(rereview_text + "\npost-QA edit\n", encoding="utf-8")
        blocked_changed_rereview = self.run_cli(
            "set-readiness",
            "--state",
            str(self.state_dir),
            "--status",
            "SUBMISSION_READY",
        )
        self.assertEqual(blocked_changed_rereview.returncode, 2)
        self.assertIn("RE_REVIEW.md changed", blocked_changed_rereview.stderr)
        rereview_report.write_text(rereview_text, encoding="utf-8")
        final_pdf = self.root / "paper" / "main.pdf"
        final_source_hash = file_sha256(source)
        final_bibliography_hash = file_sha256(self.root / "paper" / "refs.bib")
        final_pdf_hash = file_sha256(final_pdf)
        (self.state_dir / "SUBMISSION_READINESS.md").write_text(
            "# Submission Readiness\n\n- Overall: SUBMISSION_READY\n"
            "- Scientific readiness: PASS\n- Manuscript readiness: PASS\n"
            "- Submission-package readiness: PASS\n"
            f"- Exact source revision: paper/main.md {final_source_hash}\n"
            f"- Exact bibliography path/hash: paper/refs.bib {final_bibliography_hash}\n"
            f"- Exact PDF path/hash: paper/main.pdf {final_pdf_hash}\n"
            "- Build command/result: test-build PASS\n"
            "- Final rendered-PDF inspection evidence: all pages inspected\n"
            "- Remaining P0/P1 blockers: NONE\n"
            "- User-supplied or external blockers: NONE\n"
            "- Residual non-blocking risks: documented warning only\n"
            "- Recommended next action: submit exact frozen package\n",
            encoding="utf-8",
        )
        final_source_text = source.read_text(encoding="utf-8")
        source.write_text(final_source_text + "\npost-review edit\n", encoding="utf-8")
        blocked_stale_rereview = self.run_cli(
            "set-readiness",
            "--state",
            str(self.state_dir),
            "--status",
            "SUBMISSION_READY",
        )
        self.assertEqual(blocked_stale_rereview.returncode, 2)
        self.assertIn("changed after the re-review snapshot", blocked_stale_rereview.stderr)
        source.write_text(final_source_text, encoding="utf-8")
        readiness_path = self.state_dir / "SUBMISSION_READINESS.md"
        readiness_text = readiness_path.read_text(encoding="utf-8")
        readiness_path.write_text(
            readiness_text.replace(
                "- Remaining P0/P1 blockers: NONE",
                "- Remaining P0/P1 blockers: unresolved validity issue",
            ),
            encoding="utf-8",
        )
        blocked_declared_p01 = self.run_cli(
            "set-readiness", "--state", str(self.state_dir), "--status", "SUBMISSION_READY"
        )
        self.assertEqual(blocked_declared_p01.returncode, 2)
        self.assertIn("requires Remaining P0/P1 blockers", blocked_declared_p01.stderr)
        readiness_path.write_text(readiness_text, encoding="utf-8")
        blocked_without_table_qa = self.run_cli(
            "set-readiness",
            "--state",
            str(self.state_dir),
            "--status",
            "SUBMISSION_READY",
        )
        self.assertEqual(blocked_without_table_qa.returncode, 2)
        self.assertIn("TABLE_QA.md", blocked_without_table_qa.stderr)
        tex_audit = self.state_dir / "tex_table_audit.json"
        tex_audit.write_text(
            json.dumps(
                {
                    "ok": True,
                    "strict": True,
                    "main_tex": str(source.resolve()),
                    "main_tex_sha256": file_sha256(source),
                    "files_scanned": [str(source.resolve())],
                    "files_sha256": {str(source.resolve()): file_sha256(source)},
                    "tables_scanned": 1,
                    "tables": [
                        {
                            "id": "T1",
                            "file": str(source.resolve()),
                            "line": 1,
                            "environment": "table",
                        }
                    ],
                    "findings": [],
                }
            ),
            encoding="utf-8",
        )
        font_audit = self.state_dir / "pdf_font_audit.json"
        font_audit.write_text(
            json.dumps(
                {
                    "pdf": str(final_pdf.resolve()),
                    "pdf_sha256": file_sha256(final_pdf),
                    "status": "PASS",
                    "errors": [],
                    "warnings": [],
                }
            ),
            encoding="utf-8",
        )
        tex_audit_hash = file_sha256(tex_audit)
        font_audit_hash = file_sha256(font_audit)
        wrong_hash_table_qa = (
            "# Table QA\n\n- Overall table QA: PASS\n"
            f"- Exact PDF path/SHA-256: paper/main.pdf {'0' * 64}\n"
            "- TeX table audit command/result: tex_table_audit --strict PASS; tables_scanned=1\n"
            f"- TeX table audit output SHA-256: {tex_audit_hash}\n"
            "- TeX tables scanned: 1\n"
            f"- PDF font audit command/result: pdf_font_audit PASS; pdf_sha256={final_pdf_hash}\n\n"
            f"- PDF font audit output SHA-256: {font_audit_hash}\n\n"
            "| Table | Page | Intended frame | Rule semantics | Column and row alignment | Minimum rendered font | Visual evidence | Changed pages | Status |\n"
            "|---|---:|---|---|---|---:|---|---|---|\n"
            "| T1 | 1 | column | semantic | verified | 8.0 | inspected | 1 | PASS |\n"
        )
        (self.state_dir / "TABLE_QA.md").write_text(wrong_hash_table_qa, encoding="utf-8")
        blocked_wrong_hash = self.run_cli(
            "set-readiness",
            "--state",
            str(self.state_dir),
            "--status",
            "SUBMISSION_READY",
        )
        self.assertEqual(blocked_wrong_hash.returncode, 2)
        self.assertIn("exact final PDF SHA-256", blocked_wrong_hash.stderr)
        missing_audit_evidence = (
            "# Table QA\n\n- Overall table QA: PASS\n"
            f"- Exact PDF path/SHA-256: paper/main.pdf {final_pdf_hash}\n\n"
            "| Table | Page | Intended frame | Rule semantics | Column and row alignment | Minimum rendered font | Visual evidence | Changed pages | Status |\n"
            "|---|---:|---|---|---|---:|---|---|---|\n"
            "| T1 | 1 | column | semantic | verified | 8.0 | inspected | 1 | PASS |\n"
        )
        (self.state_dir / "TABLE_QA.md").write_text(
            missing_audit_evidence, encoding="utf-8"
        )
        blocked_missing_evidence = self.run_cli(
            "set-readiness",
            "--state",
            str(self.state_dir),
            "--status",
            "SUBMISSION_READY",
        )
        self.assertEqual(blocked_missing_evidence.returncode, 2)
        self.assertIn("TeX audit evidence", blocked_missing_evidence.stderr)
        table_qa_text = (
            "# Table QA\n\n- Overall table QA: PASS\n"
            f"- Exact PDF path/SHA-256: paper/main.pdf {final_pdf_hash}\n"
            "- TeX table audit command/result: tex_table_audit --strict PASS; tables_scanned=1\n"
            f"- TeX table audit output SHA-256: {tex_audit_hash}\n"
            "- TeX tables scanned: 1\n"
            f"- PDF font audit command/result: pdf_font_audit PASS; pdf_sha256={final_pdf_hash}\n"
            f"- PDF font audit output SHA-256: {font_audit_hash}\n\n"
            "| Table | Page | Intended frame | Rule semantics | Column and row alignment | Minimum rendered font | Visual evidence | Changed pages | Status |\n"
            "|---|---:|---|---|---|---:|---|---|---|\n"
            "| T1 | 1 | column | semantic | verified | 8.0 | inspected | 1 | PASS |\n"
        )
        (self.state_dir / "TABLE_QA.md").write_text(table_qa_text, encoding="utf-8")
        ready = self.run_cli(
            "set-readiness",
            "--state",
            str(self.state_dir),
            "--status",
            "SUBMISSION_READY",
        )
        self.assertEqual(ready.returncode, 0, ready.stderr)
        state = json.loads((self.state_dir / "state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["stage"], "SUBMISSION_READY")
        self.assertEqual(state["last_passed_gate"], "G8_PACKAGE_SIGNOFF")
        table_qa = self.state_dir / "TABLE_QA.md"
        table_qa.write_text(table_qa_text + "\npost-signoff edit\n", encoding="utf-8")
        invalid_table_signoff = self.run_cli("validate", "--state", str(self.state_dir))
        self.assertEqual(invalid_table_signoff.returncode, 1)
        self.assertIn("TABLE_QA.md changed after terminal signoff", invalid_table_signoff.stdout)
        table_qa.write_text(table_qa_text, encoding="utf-8")
        source.write_text("# Paper\n\nChanged after signoff.\n", encoding="utf-8")
        invalidated = self.run_cli("validate", "--state", str(self.state_dir))
        self.assertEqual(invalidated.returncode, 1)
        self.assertIn("changed after terminal signoff", invalidated.stdout)
        reopened = self.run_cli(
            "reopen-revision",
            "--state",
            str(self.state_dir),
            "--reason",
            "final candidate changed",
        )
        self.assertEqual(reopened.returncode, 0, reopened.stderr)
        reopened_state = json.loads(
            (self.state_dir / "state.json").read_text(encoding="utf-8")
        )
        self.assertEqual(reopened_state["stage"], "REVISING")

    def test_experiment_request_without_card_blocks_triage(self) -> None:
        snapshot = self.advance_to_reviewing()
        self.write_review_outputs(snapshot)
        eic = self.state_dir / "reviews" / "EIC.md"
        eic.write_text(
            eic.read_text(encoding="utf-8").replace(
                "Experiment requirement: NONE", "Experiment requirement: EXP-REQ-MISSING"
            ),
            encoding="utf-8",
        )
        blocked = self.run_cli(
            "advance", "--state", str(self.state_dir), "--to", "TRIAGE"
        )
        self.assertEqual(blocked.returncode, 2)
        self.assertIn("without a matching card", blocked.stderr)
        eic.write_text(
            eic.read_text(encoding="utf-8")
            + "\n### EXP-REQ-MISSING: Incomplete card\n\n- Reviewer question: Is the control needed?\n",
            encoding="utf-8",
        )
        incomplete = self.run_cli(
            "advance", "--state", str(self.state_dir), "--to", "TRIAGE"
        )
        self.assertEqual(incomplete.returncode, 2)
        self.assertIn("missing a completed 'Manuscript claim at risk'", incomplete.stderr)

    def test_complete_experiment_card_allows_triage(self) -> None:
        snapshot = self.advance_to_reviewing()
        self.write_review_outputs(snapshot, experiment=True)
        result = self.run_cli("advance", "--state", str(self.state_dir), "--to", "TRIAGE")
        self.assertEqual(result.returncode, 0, result.stderr)
        eic = self.state_dir / "reviews" / "EIC.md"
        eic.write_text(eic.read_text(encoding="utf-8") + "\npost-triage edit\n", encoding="utf-8")
        validation = self.run_cli("validate", "--state", str(self.state_dir))
        self.assertEqual(validation.returncode, 1)
        self.assertIn("frozen review report changed after TRIAGE", validation.stdout)

    def test_experiment_request_must_be_decided_and_closed(self) -> None:
        snapshot = self.advance_to_reviewing()
        self.write_review_outputs(snapshot, experiment=True)
        triage = self.run_cli("advance", "--state", str(self.state_dir), "--to", "TRIAGE")
        self.assertEqual(triage.returncode, 0, triage.stderr)
        (self.state_dir / "REVISION_LEDGER.md").write_text(
            "# Revision Ledger\n\n"
            "| Ticket ID | Review finding | Decision | Rationale | Target | Planned change | Owner | Status | Verification |\n"
            "|---|---|---|---|---|---|---|---|---|\n"
            "| REV-REQ-CLARITY | Experiment request | Accept | Validity check | paper/main.md | Integrate result | writer | verified | verified against source |\n",
            encoding="utf-8",
        )
        missing_decision = self.run_cli(
            "advance", "--state", str(self.state_dir), "--to", "REVISING"
        )
        self.assertEqual(missing_decision.returncode, 2)
        self.assertIn("lacks a triage decision", missing_decision.stderr)
        decision_ledger = self.state_dir / "EXPERIMENT_REQUESTS.md"
        decision_ledger.write_text(
            "# Experiment Requests\n\n"
            "| Request ID | Resolution | Authority/evidence | Manuscript or experiment action | Status |\n"
            "|---|---|---|---|---|\n"
            "| EXP-REQ-TEST | RUN_AUTHORIZED | USER approved exact request | Run frozen control | PENDING |\n",
            encoding="utf-8",
        )
        revising = self.run_cli(
            "advance", "--state", str(self.state_dir), "--to", "REVISING"
        )
        self.assertEqual(revising.returncode, 0, revising.stderr)
        source = self.root / "paper" / "main.md"
        source.write_text("# Paper\n\nExperiment integrated.\n", encoding="utf-8")
        write_minimal_pdf(self.root / "paper" / "main.pdf", "experiment integrated")
        self.write_build_receipt()
        not_closed = self.run_cli(
            "advance", "--state", str(self.state_dir), "--to", "RE_REVIEW"
        )
        self.assertEqual(not_closed.returncode, 2)
        self.assertIn("is not closed before re-review", not_closed.stderr)
        decision_ledger.write_text(
            decision_ledger.read_text(encoding="utf-8").replace("PENDING", "COMPLETED"),
            encoding="utf-8",
        )
        closed = self.run_cli(
            "advance", "--state", str(self.state_dir), "--to", "RE_REVIEW"
        )
        self.assertEqual(closed.returncode, 0, closed.stderr)

    def test_review_report_requires_substantive_sections(self) -> None:
        snapshot = self.advance_to_reviewing()
        self.write_review_outputs(snapshot)
        eic = self.state_dir / "reviews" / "EIC.md"
        eic.write_text(
            eic.read_text(encoding="utf-8").replace(
                "## Required revisions", "## Unstructured notes"
            ),
            encoding="utf-8",
        )
        blocked = self.run_cli("advance", "--state", str(self.state_dir), "--to", "TRIAGE")
        self.assertEqual(blocked.returncode, 2)
        self.assertIn("Required revisions", blocked.stderr)

    def test_revision_requests_cannot_be_discarded_with_none_marker(self) -> None:
        snapshot = self.advance_to_reviewing()
        self.write_review_outputs(snapshot)
        triage = self.run_cli("advance", "--state", str(self.state_dir), "--to", "TRIAGE")
        self.assertEqual(triage.returncode, 0, triage.stderr)
        (self.state_dir / "REVISION_LEDGER.md").write_text(
            "# Revision Ledger\n\nNO_REQUIRED_REVISIONS\n", encoding="utf-8"
        )
        blocked = self.run_cli("advance", "--state", str(self.state_dir), "--to", "REVISING")
        self.assertEqual(blocked.returncode, 2)
        self.assertIn("despite reviewer REV-REQ tickets", blocked.stderr)

    def test_rereview_experiment_request_is_durable_until_closed(self) -> None:
        snapshot = self.advance_to_rereview()
        self.write_rereview_report(snapshot, experiment=True)
        blocked = self.run_cli(
            "advance", "--state", str(self.state_dir), "--to", "SUBMISSION_QA"
        )
        self.assertEqual(blocked.returncode, 2)
        state = json.loads((self.state_dir / "state.json").read_text(encoding="utf-8"))
        self.assertIn("EXP-REQ-REREVIEW", state["pending_experiment_request_ids"])
        reopened = self.run_cli(
            "reopen-revision", "--state", str(self.state_dir), "--reason", "triage re-review request"
        )
        self.assertEqual(reopened.returncode, 0, reopened.stderr)
        still_blocked = self.run_cli(
            "advance", "--state", str(self.state_dir), "--to", "RE_REVIEW"
        )
        self.assertEqual(still_blocked.returncode, 2)
        self.assertIn("lacks a triage decision", still_blocked.stderr)
        (self.state_dir / "EXPERIMENT_REQUESTS.md").write_text(
            "# Experiment Requests\n\n"
            "| Request ID | Resolution | Authority/evidence | Manuscript or experiment action | Status |\n"
            "|---|---|---|---|---|\n"
            "| EXP-REQ-REREVIEW | CLAIM_NARROWED | PI accepted narrower claim | Narrow exact claim | APPLIED |\n",
            encoding="utf-8",
        )
        accepted = self.run_cli("advance", "--state", str(self.state_dir), "--to", "RE_REVIEW")
        self.assertEqual(accepted.returncode, 0, accepted.stderr)
        latest = json.loads((self.state_dir / "state.json").read_text(encoding="utf-8"))[
            "rereview_snapshot"
        ]
        self.write_rereview_report(latest, experiment=False)
        qa = self.run_cli("advance", "--state", str(self.state_dir), "--to", "SUBMISSION_QA")
        self.assertEqual(qa.returncode, 0, qa.stderr)

    def test_rereview_revision_request_is_durable_until_ledger_closes_it(self) -> None:
        snapshot = self.advance_to_rereview()
        self.write_rereview_report(snapshot, revision=True)
        blocked = self.run_cli(
            "advance", "--state", str(self.state_dir), "--to", "SUBMISSION_QA"
        )
        self.assertEqual(blocked.returncode, 2)
        state = json.loads((self.state_dir / "state.json").read_text(encoding="utf-8"))
        self.assertIn("REV-REQ-REREVIEW", state["pending_revision_request_ids"])
        self.assertEqual(
            self.run_cli(
                "reopen-revision", "--state", str(self.state_dir), "--reason", "new revision"
            ).returncode,
            0,
        )
        missing = self.run_cli("advance", "--state", str(self.state_dir), "--to", "RE_REVIEW")
        self.assertEqual(missing.returncode, 2)
        self.assertIn("lacks a ledger row", missing.stderr)
        ledger = self.state_dir / "REVISION_LEDGER.md"
        ledger.write_text(
            ledger.read_text(encoding="utf-8")
            + "| REV-REQ-REREVIEW | New issue | Accept | Valid issue | paper/main.md | Repair | writer | verified | verified against source |\n",
            encoding="utf-8",
        )
        accepted = self.run_cli("advance", "--state", str(self.state_dir), "--to", "RE_REVIEW")
        self.assertEqual(accepted.returncode, 0, accepted.stderr)
        latest = json.loads((self.state_dir / "state.json").read_text(encoding="utf-8"))[
            "rereview_snapshot"
        ]
        self.write_rereview_report(latest)
        qa = self.run_cli("advance", "--state", str(self.state_dir), "--to", "SUBMISSION_QA")
        self.assertEqual(qa.returncode, 0, qa.stderr)

    def test_revision_ticket_must_be_closed_before_rereview(self) -> None:
        snapshot = self.advance_to_reviewing()
        self.write_review_outputs(snapshot)
        self.assertEqual(
            self.run_cli("advance", "--state", str(self.state_dir), "--to", "TRIAGE").returncode,
            0,
        )
        (self.state_dir / "REVISION_LEDGER.md").write_text(
            "# Revision Ledger\n\n"
            "| Ticket ID | Review finding | Decision | Rationale | Target | Planned change | Owner | Status | Verification |\n"
            "|---|---|---|---|---|---|---|---|---|\n"
            "| REV-REQ-CLARITY | Issue | Accept | Valid | paper/main.md | Repair | writer | pending | pending |\n",
            encoding="utf-8",
        )
        self.assertEqual(
            self.run_cli("advance", "--state", str(self.state_dir), "--to", "REVISING").returncode,
            0,
        )
        self.write_build_receipt()
        blocked = self.run_cli("advance", "--state", str(self.state_dir), "--to", "RE_REVIEW")
        self.assertEqual(blocked.returncode, 2)
        self.assertIn("not closed before re-review", blocked.stderr)

    def test_rereview_snapshot_freezes_both_decision_ledgers(self) -> None:
        snapshot = self.advance_to_rereview()
        experiment_ledger = self.state_dir / "EXPERIMENT_REQUESTS.md"
        experiment_ledger.write_text(
            experiment_ledger.read_text(encoding="utf-8") + "\npost-freeze change\n",
            encoding="utf-8",
        )
        self.write_rereview_report(snapshot)
        blocked = self.run_cli(
            "advance", "--state", str(self.state_dir), "--to", "SUBMISSION_QA"
        )
        self.assertEqual(blocked.returncode, 2)
        self.assertIn("experiment decision ledger changed", blocked.stderr)

    def test_duplicate_rereview_markers_are_rejected_and_captured(self) -> None:
        snapshot = self.advance_to_rereview()
        text = self.write_rereview_report(snapshot)
        text += (
            "\nRevision requirement: REV-REQ-HIDDEN\n"
            "Experiment requirement: EXP-REQ-HIDDEN\n"
        )
        (self.state_dir / "reviews" / "RE_REVIEW.md").write_text(text, encoding="utf-8")
        blocked = self.run_cli(
            "advance", "--state", str(self.state_dir), "--to", "SUBMISSION_QA"
        )
        self.assertEqual(blocked.returncode, 2)
        self.assertIn("exactly one 'Experiment requirement:'", blocked.stderr)
        state = json.loads((self.state_dir / "state.json").read_text(encoding="utf-8"))
        self.assertIn("EXP-REQ-HIDDEN", state["pending_experiment_request_ids"])
        self.assertIn("REV-REQ-HIDDEN", state["pending_revision_request_ids"])

    def test_duplicate_rereview_hash_field_is_rejected(self) -> None:
        snapshot = self.advance_to_rereview()
        text = self.write_rereview_report(snapshot)
        text += "\nSource snapshot SHA-256: " + ("0" * 64) + "\n"
        (self.state_dir / "reviews" / "RE_REVIEW.md").write_text(text, encoding="utf-8")
        blocked = self.run_cli(
            "advance", "--state", str(self.state_dir), "--to", "SUBMISSION_QA"
        )
        self.assertEqual(blocked.returncode, 2)
        self.assertIn("must occur exactly once", blocked.stderr)

    def test_exact_duplicate_reviewer_reports_are_rejected(self) -> None:
        snapshot = self.advance_to_reviewing()
        self.write_review_outputs(snapshot)
        eic = (self.state_dir / "reviews" / "EIC.md").read_bytes()
        (self.state_dir / "reviews" / "METHODOLOGY.md").write_bytes(eic)
        blocked = self.run_cli("advance", "--state", str(self.state_dir), "--to", "TRIAGE")
        self.assertEqual(blocked.returncode, 2)
        self.assertIn("exact duplicates", blocked.stderr)

    def test_custom_added_role_requires_its_declared_report(self) -> None:
        self.submit_and_approve_story()
        self.advance_to_reviewable()
        panel_text = completed_panel(custom=True).replace(
            "| Devil's Advocate | DEVILS_ADVOCATE.md |",
            "| Devil's Advocate | DEVILS_ADVOCATE.md |\n| Reproducibility Reviewer | REPRODUCIBILITY.md |",
        )
        panel_text += (
            "\n## Reproducibility Reviewer\n\n"
            "- Persona and expertise: Independent artifact and reproducibility specialist.\n"
            "- Responsibility ID: REPRODUCIBILITY_CUSTOM_V1\n"
        )
        (self.state_dir / "REVIEW_PANEL.md").write_text(panel_text, encoding="utf-8")
        waiting = self.run_cli(
            "advance", "--state", str(self.state_dir), "--to", "WAITING_FOR_REVIEW_PANEL_APPROVAL"
        )
        self.assertEqual(waiting.returncode, 0, waiting.stderr)
        approved = self.run_cli(
            "approve-review-panel", "--state", str(self.state_dir), "--by", "USER",
            "--evidence", "批准增加复现审稿人",
        )
        self.assertEqual(approved.returncode, 0, approved.stderr)
        snapshot = json.loads((self.state_dir / "state.json").read_text(encoding="utf-8"))[
            "review_snapshot"
        ]
        self.write_review_outputs(snapshot)
        missing = self.run_cli("advance", "--state", str(self.state_dir), "--to", "TRIAGE")
        self.assertEqual(missing.returncode, 2)
        self.assertIn("REPRODUCIBILITY.md", missing.stderr)
        eic = (self.state_dir / "reviews" / "EIC.md").read_text(encoding="utf-8")
        reproducibility = eic.replace("# EIC Review", "# Reproducibility Review").replace(
            "Verified strength with an exact location.",
            "Artifact reconstruction and dependency integrity were checked independently.",
        )
        (self.state_dir / "reviews" / "REPRODUCIBILITY.md").write_text(
            reproducibility, encoding="utf-8"
        )
        accepted = self.run_cli("advance", "--state", str(self.state_dir), "--to", "TRIAGE")
        self.assertEqual(accepted.returncode, 0, accepted.stderr)

    def test_custom_removed_role_is_not_silently_required(self) -> None:
        self.submit_and_approve_story()
        self.advance_to_reviewable()
        panel_text = completed_panel(custom=True)
        perspective_block = (
            "## Perspective Reviewer\n\n"
            "- Persona and expertise: Independent Perspective Reviewer specialist.\n"
            "- Responsibility ID: CUSTOM_PERSPECTIVE_STANDARD_V1\n\n"
        )
        panel_text = panel_text.replace(perspective_block, "").replace(
            "| Perspective Reviewer | PERSPECTIVE.md |\n", ""
        )
        (self.state_dir / "REVIEW_PANEL.md").write_text(panel_text, encoding="utf-8")
        self.assertEqual(
            self.run_cli(
                "advance", "--state", str(self.state_dir), "--to", "WAITING_FOR_REVIEW_PANEL_APPROVAL"
            ).returncode,
            0,
        )
        approved = self.run_cli(
            "approve-review-panel", "--state", str(self.state_dir), "--by", "USER",
            "--evidence", "批准合并视角职责",
        )
        self.assertEqual(approved.returncode, 0, approved.stderr)
        snapshot = json.loads((self.state_dir / "state.json").read_text(encoding="utf-8"))[
            "review_snapshot"
        ]
        self.write_review_outputs(snapshot)
        (self.state_dir / "reviews" / "PERSPECTIVE.md").unlink()
        accepted = self.run_cli("advance", "--state", str(self.state_dir), "--to", "TRIAGE")
        self.assertEqual(accepted.returncode, 0, accepted.stderr)

    def test_custom_panel_pending_approval_detects_included_tex_change(self) -> None:
        source = self.root / "paper" / "dep_main.ltx"
        body = self.root / "paper" / "dep_body.tex"
        figure_dir = self.root / "paper" / "figures"
        figure_dir.mkdir()
        figure = figure_dir / "plot.png"
        figure.write_bytes(b"frozen image")
        source.write_text(
            "\\documentclass{article}\n\\usepackage{graphicx}\n"
            "\\graphicspath% path comment\n {{figures/}}\n\\begin{document}\n"
            "\\input% input comment\n {dep_body}\n\\end{document}\n",
            encoding="utf-8",
        )
        body.write_text("\\includegraphics*{plot}\n", encoding="utf-8")
        manifest = self.root / "paper" / "dep_main.fls"
        manifest.write_text(
            f"PWD {self.root}\n"
            "INPUT paper/dep_main.ltx\n"
            "INPUT paper/dep_body.tex\n"
            "INPUT paper/figures/plot.png\n"
            "INPUT paper/refs.bib\n"
            "OUTPUT paper/main.pdf\n",
            encoding="utf-8",
        )
        dep_state = self.root / ".paper-workflow-dep"
        init = self.run_cli(
            "init", "--project-root", str(self.root), "--state-dir", str(dep_state),
            "--venue", "ACL", "--year", "2026", "--track", "main", "--mode", "review",
            "--source", "paper/dep_main.ltx", "--bibliography", "paper/refs.bib",
            "--pdf", "paper/main.pdf", "--dependency-manifest", "paper/dep_main.fls",
            "--build-command", "frozen-build",
        )
        self.assertEqual(init.returncode, 0, init.stderr)
        old_state = self.state_dir
        self.state_dir = dep_state
        try:
            self.submit_and_approve_story()
            for stage in ("DRAFTING", "ASSEMBLING"):
                self.assertEqual(
                    self.run_cli("advance", "--state", str(dep_state), "--to", stage).returncode, 0
                )
            def write_dependency_receipt() -> None:
                fingerprint = json.loads(
                    self.run_cli("fingerprint", "--state", str(dep_state)).stdout
                )
                (dep_state / "BUILD_RECEIPT.md").write_text(
                    "# Build Receipt\n\n- Status: PASS\n- Command: frozen-build\n"
                    f"- Source SHA-256: {file_sha256(source)}\n"
                    f"- Bibliography SHA-256: {file_sha256(self.root / 'paper' / 'refs.bib')}\n"
                    f"- Dependency manifest SHA-256: {file_sha256(manifest)}\n"
                    f"- Dependency bundle SHA-256: {fingerprint['dependency_bundle_sha256']}\n"
                    f"- Output PDF SHA-256: {file_sha256(self.root / 'paper' / 'main.pdf')}\n"
                    "- Page count: 1\n- Undefined references/citations: 0\n- Missing files: 0\n"
                    "- Overfull boxes: 0\n- Rendered inspection: PASS; pages=ALL; evidence=fixture inspected\n",
                    encoding="utf-8",
                )

            valid_manifest = manifest.read_text(encoding="utf-8")
            manifest.write_text("INPUT paper/missing.tex\n", encoding="utf-8")
            write_dependency_receipt()
            invalid_manifest = self.run_cli(
                "advance", "--state", str(dep_state), "--to", "REVIEWABLE"
            )
            self.assertEqual(invalid_manifest.returncode, 2)
            self.assertIn("canonical source and at least one additional", invalid_manifest.stderr)
            manifest.write_text(valid_manifest, encoding="utf-8")
            write_dependency_receipt()
            self.assertEqual(
                self.run_cli("advance", "--state", str(dep_state), "--to", "REVIEWABLE").returncode, 0
            )
            (dep_state / "REVIEW_PANEL.md").write_text(completed_panel(custom=True), encoding="utf-8")
            self.assertEqual(
                self.run_cli(
                    "advance", "--state", str(dep_state), "--to", "WAITING_FOR_REVIEW_PANEL_APPROVAL"
                ).returncode,
                0,
            )
            figure.write_bytes(b"changed image after submission")
            blocked = self.run_cli(
                "approve-review-panel", "--state", str(dep_state), "--by", "USER",
                "--evidence", "批准",
            )
            self.assertEqual(blocked.returncode, 2)
            self.assertIn("dependency bundle changed", blocked.stderr)
        finally:
            self.state_dir = old_state

    def test_tectonic_makefile_manifest_can_reach_reviewable(self) -> None:
        source = self.root / "paper" / "tectonic_main.tex"
        body = self.root / "paper" / "tectonic_body.tex"
        source.write_text(
            "\\documentclass{article}\n\\usepackage{graphicx}\n\\begin{document}\n"
            "\\input{tectonic_body}\n\\includegraphics{tectonic_figure}\n\\end{document}\n",
            encoding="utf-8",
        )
        body.write_text("Compiled body.\n", encoding="utf-8")
        figure = self.root / "paper" / "tectonic_figure.png"
        figure.write_bytes(b"image fixture")
        out = self.root / "tectonic out"
        out.mkdir()
        pdf = out / "tectonic_main.pdf"
        pdf.write_bytes((self.root / "paper" / "main.pdf").read_bytes())
        manifest = out / "tectonic_main.mk"
        root_rel_pdf = pdf.relative_to(self.root)
        root_rel_source = source.relative_to(self.root)
        projected_body = (out / "tectonic_body.tex").relative_to(self.root)
        projected_figure = (out / "tectonic_figure.png").relative_to(self.root)
        projected_bib = (out / "refs.bib").relative_to(self.root)
        manifest.write_text(
            f"{root_rel_pdf} : {root_rel_source} \\\n"
            f"  {projected_body} \\\n"
            f"  {projected_figure} \\\n"
            f"  {projected_bib}\n",
            encoding="utf-8",
        )
        state_dir = self.root / ".paper-workflow-tectonic"
        init = self.run_cli(
            "init", "--project-root", str(self.root), "--state-dir", str(state_dir),
            "--venue", "ACL", "--year", "2026", "--track", "main", "--mode", "review",
            "--source", str(source), "--bibliography", "paper/refs.bib",
            "--pdf", str(pdf), "--dependency-manifest", str(manifest),
            "--build-command", "tectonic --makefile-rules",
        )
        self.assertEqual(init.returncode, 0, init.stderr)
        old_state = self.state_dir
        self.state_dir = state_dir
        try:
            self.submit_and_approve_story()
            for stage in ("DRAFTING", "ASSEMBLING"):
                self.assertEqual(
                    self.run_cli("advance", "--state", str(state_dir), "--to", stage).returncode,
                    0,
                )
            fingerprint = json.loads(
                self.run_cli("fingerprint", "--state", str(state_dir)).stdout
            )
            (state_dir / "BUILD_RECEIPT.md").write_text(
                "# Build Receipt\n\n- Status: PASS\n- Command: tectonic --makefile-rules\n"
                f"- Source SHA-256: {file_sha256(source)}\n"
                f"- Bibliography SHA-256: {file_sha256(self.root / 'paper' / 'refs.bib')}\n"
                f"- Dependency manifest SHA-256: {file_sha256(manifest)}\n"
                f"- Dependency bundle SHA-256: {fingerprint['dependency_bundle_sha256']}\n"
                f"- Output PDF SHA-256: {file_sha256(pdf)}\n"
                "- Page count: 1\n- Undefined references/citations: 0\n"
                "- Missing files: 0\n- Overfull boxes: 0\n"
                "- Rendered inspection: PASS; pages=ALL; evidence=fixture inspected\n",
                encoding="utf-8",
            )
            accepted = self.run_cli(
                "advance", "--state", str(state_dir), "--to", "REVIEWABLE"
            )
            self.assertEqual(accepted.returncode, 0, accepted.stderr)
            figure.unlink()
            missing_dependency = self.run_cli(
                "check-build", "--state", str(state_dir)
            )
            self.assertEqual(missing_dependency.returncode, 1)
            self.assertIn("missing INPUT files", missing_dependency.stdout)
        finally:
            self.state_dir = old_state

    def test_nonready_status_requires_complete_evidence(self) -> None:
        self.advance_to_submission_qa()
        report = self.state_dir / "SUBMISSION_READINESS.md"
        report.write_text("# Submission Readiness\n\n- Overall: CONDITIONALLY_READY\n", encoding="utf-8")
        blocked = self.run_cli(
            "set-readiness", "--state", str(self.state_dir), "--status", "CONDITIONALLY_READY"
        )
        self.assertEqual(blocked.returncode, 2)
        self.assertIn("exact final source", blocked.stderr)
        source = self.root / "paper" / "main.md"
        bibliography = self.root / "paper" / "refs.bib"
        pdf = self.root / "paper" / "main.pdf"
        report.write_text(
            "# Submission Readiness\n\n- Overall: CONDITIONALLY_READY\n"
            "- Scientific readiness: PASS\n- Manuscript readiness: PASS\n"
            "- Submission-package readiness: FAIL\n"
            f"- Exact source revision: paper/main.md {file_sha256(source)}\n"
            f"- Exact bibliography path/hash: paper/refs.bib {file_sha256(bibliography)}\n"
            f"- Exact PDF path/hash: paper/main.pdf {file_sha256(pdf)}\n"
            "- Build command/result: test-build PASS\n"
            "- Final rendered-PDF inspection evidence: all pages inspected\n"
            "- Remaining P0/P1 blockers: NONE\n"
            "- User-supplied or external blockers: author metadata pending\n"
            "- Residual non-blocking risks: NONE\n"
            "- Recommended next action: obtain metadata and reopen QA\n",
            encoding="utf-8",
        )
        invalid_semantics = report.read_text(encoding="utf-8").replace(
            "- Scientific readiness: PASS", "- Scientific readiness: FAIL"
        )
        report.write_text(invalid_semantics, encoding="utf-8")
        wrong_conditional = self.run_cli(
            "set-readiness", "--state", str(self.state_dir), "--status", "CONDITIONALLY_READY"
        )
        self.assertEqual(wrong_conditional.returncode, 2)
        self.assertIn("scientific/manuscript PASS", wrong_conditional.stderr)
        report.write_text(
            invalid_semantics.replace("- Scientific readiness: FAIL", "- Scientific readiness: PASS"),
            encoding="utf-8",
        )
        valid_conditional = report.read_text(encoding="utf-8")
        report.write_text(
            valid_conditional, encoding="utf-8"
        )
        for placeholder in (
            "TBD",
            "TBC",
            "UNKNOWN",
            "TO BE DETERMINED",
            "TO BE CONFIRMED",
            "PENDING",
            "TBC:",
            "**TBC**",
            "T.B.D.",
        ):
            report.write_text(
                valid_conditional.replace("author metadata pending", placeholder),
                encoding="utf-8",
            )
            unresolved_conditional = self.run_cli(
                "set-readiness", "--state", str(self.state_dir), "--status", "CONDITIONALLY_READY"
            )
            self.assertEqual(unresolved_conditional.returncode, 2, placeholder)
            self.assertIn(
                "lacks completed 'User-supplied or external blockers'",
                unresolved_conditional.stderr,
            )
        report.write_text(
            valid_conditional.replace(
                "- Overall: CONDITIONALLY_READY", "- Overall: NOT_READY"
            ).replace(
                "- Scientific readiness: PASS", "- Scientific readiness: FAIL"
            ).replace(
                "- User-supplied or external blockers: author metadata pending",
                "- User-supplied or external blockers: NONE",
            ),
            encoding="utf-8",
        )
        blockerless_not_ready = self.run_cli(
            "set-readiness", "--state", str(self.state_dir), "--status", "NOT_READY"
        )
        self.assertEqual(blockerless_not_ready.returncode, 2)
        self.assertIn("concrete remaining P0/P1 blocker", blockerless_not_ready.stderr)
        report.write_text(
            valid_conditional
            + "\n- Scientific readiness: FAIL\n- Overall: NOT_READY\n"
            + "- Exact source revision: DIFFERENT-CANDIDATE-WITHOUT-HASH\n",
            encoding="utf-8",
        )
        duplicate_fields = self.run_cli(
            "set-readiness", "--state", str(self.state_dir), "--status", "CONDITIONALLY_READY"
        )
        self.assertEqual(duplicate_fields.returncode, 2)
        self.assertIn("does not declare CONDITIONALLY_READY", duplicate_fields.stderr)
        report.write_text(valid_conditional, encoding="utf-8")
        accepted = self.run_cli(
            "set-readiness", "--state", str(self.state_dir), "--status", "CONDITIONALLY_READY"
        )
        self.assertEqual(accepted.returncode, 0, accepted.stderr)
        table_qa = self.state_dir / "TABLE_QA.md"
        table_qa.write_text(table_qa.read_text(encoding="utf-8") + "\nchanged\n", encoding="utf-8")
        invalid = self.run_cli("validate", "--state", str(self.state_dir))
        self.assertEqual(invalid.returncode, 1)
        self.assertIn("TABLE_QA.md changed after terminal signoff", invalid.stdout)

    def test_agent_cannot_be_recorded_as_human_approver(self) -> None:
        packet = self.state_dir / "STORY_APPROVAL_PACKET.md"
        packet.write_text(completed_story(), encoding="utf-8")
        self.assertEqual(
            self.run_cli("submit-story", "--state", str(self.state_dir)).returncode,
            0,
        )
        blocked = self.run_cli(
            "approve-story",
            "--state",
            str(self.state_dir),
            "--by",
            "INTEGRATOR",
            "--evidence",
            "self-approved",
        )
        self.assertEqual(blocked.returncode, 2)
        self.assertIn("user/PI", blocked.stderr)

    def test_standard_panel_cannot_hide_an_extra_reviewer(self) -> None:
        self.submit_and_approve_story()
        self.advance_to_reviewable()
        variants = (
            "\n## Reproducibility Reviewer\n\nPlease inspect reproducibility independently.\n",
            "\n### Reproducibility Reviewer\n\nPlease inspect reproducibility independently.\n",
            "\n   ### Reproducibility Reviewer\n\nPlease inspect reproducibility independently.\n",
            "\nReproducibility Reviewer\n---\n\nPlease inspect reproducibility independently.\n",
            "\n**Reproducibility Reviewer:** Independent sixth reviewer writes REPRODUCIBILITY.md.\n",
            "\n- **Reproducibility Reviewer:** Independent sixth reviewer writes REPRODUCIBILITY.md.\n",
            "\n> ### Reproducibility Reviewer\n> Independent sixth reviewer writes REPRODUCIBILITY.md.\n",
            "\n- ### Reproducibility Reviewer\n",
            "\n# Reproducibility Reviewer\nIndependent sixth reviewer writes REPRODUCIBILITY.md.\n",
            "\n1. **Reproducibility Reviewer:** Independent sixth reviewer writes REPRODUCIBILITY.md.\n",
            "\n__Reproducibility Reviewer:__ Independent sixth reviewer writes REPRODUCIBILITY.md.\n",
            "\n<h3>Reproducibility Reviewer</h3>\n",
            "\n- Reproducibility Reviewer: Independent sixth reviewer writes REPRODUCIBILITY.md.\n",
            "\n- Reproducibility Reviewer\n  - Writes REPRODUCIBILITY.md independently.\n",
            "\n1. Reproducibility Reviewer\n   Writes REPRODUCIBILITY.md independently.\n",
            "\n| Additional role | Output |\n|---|---|\n| Reproducibility Reviewer | REPRODUCIBILITY.md |\n",
        )
        for extra in variants:
            (self.state_dir / "REVIEW_PANEL.md").write_text(
                completed_panel() + extra, encoding="utf-8"
            )
            blocked = self.run_cli(
                "advance", "--state", str(self.state_dir), "--to", "REVIEWING"
            )
            self.assertEqual(blocked.returncode, 2)
            self.assertIn("CUSTOM", blocked.stderr)
        (self.state_dir / "REVIEW_PANEL.md").write_text(
            completed_panel()
            + "\n```markdown\n### Example Reviewer\n- **Example Reviewer:** documentation only\n```\n",
            encoding="utf-8",
        )
        fenced_example = self.run_cli(
            "advance", "--state", str(self.state_dir), "--to", "REVIEWING"
        )
        self.assertEqual(fenced_example.returncode, 0, fenced_example.stderr)

    def test_unsupported_schema_blocks_state_mutation(self) -> None:
        state_file = self.state_dir / "state.json"
        state = json.loads(state_file.read_text(encoding="utf-8"))
        state["schema_version"] = 1
        state_file.write_text(json.dumps(state), encoding="utf-8")
        blocked = self.run_cli("submit-story", "--state", str(self.state_dir))
        self.assertEqual(blocked.returncode, 2)
        self.assertIn("unsupported schema_version", blocked.stderr)

    def test_build_receipt_rejects_failure_counts_and_failed_render(self) -> None:
        self.submit_and_approve_story()
        for stage in ("DRAFTING", "ASSEMBLING"):
            self.assertEqual(
                self.run_cli("advance", "--state", str(self.state_dir), "--to", stage).returncode,
                0,
            )
        self.write_build_receipt()
        receipt = self.state_dir / "BUILD_RECEIPT.md"
        bad = receipt.read_text(encoding="utf-8").replace(
            "- Page count: 1",
            "- Page count: 999",
        ).replace(
            "- Undefined references/citations: 0",
            "- Undefined references/citations: 4",
        ).replace("- Missing files: 0", "- Missing files: 2").replace(
            "- Rendered inspection: PASS; pages=ALL; evidence=test fixture inspected",
            "- Rendered inspection: FAIL unreadable",
        )
        receipt.write_text(bad, encoding="utf-8")
        blocked = self.run_cli(
            "advance", "--state", str(self.state_dir), "--to", "REVIEWABLE"
        )
        self.assertEqual(blocked.returncode, 2)
        self.assertIn("nonzero Undefined references/citations", blocked.stderr)
        self.assertIn("nonzero Missing files", blocked.stderr)
        self.assertIn("Page count does not match", blocked.stderr)
        self.assertIn("Rendered inspection must use", blocked.stderr)

    def test_invalidate_story_archives_and_starts_clean_cycle(self) -> None:
        self.advance_to_submission_qa()
        state_file = self.state_dir / "state.json"
        state = json.loads(state_file.read_text(encoding="utf-8"))
        state["pending_experiment_request_ids"] = ["EXP-REQ-OLD"]
        state["pending_revision_request_ids"] = ["REV-REQ-OLD"]
        state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")
        invalidated = self.run_cli(
            "invalidate-story",
            "--state",
            str(self.state_dir),
            "--reason",
            "headline story changed",
        )
        self.assertEqual(invalidated.returncode, 0, invalidated.stderr)
        state = json.loads(state_file.read_text(encoding="utf-8"))
        self.assertEqual(state["stage"], "WAITING_FOR_STORY_APPROVAL")
        self.assertEqual(state["story_cycle"], 2)
        self.assertEqual(state["pending_experiment_request_ids"], [])
        self.assertEqual(state["pending_revision_request_ids"], [])
        self.assertEqual(list((self.state_dir / "reviews").glob("*.md")), [])
        archives = list((self.state_dir / "archive").glob("story-cycle-001-*"))
        self.assertEqual(len(archives), 1)
        self.assertTrue((archives[0] / "reviews" / "RE_REVIEW.md").is_file())
        self.assertTrue((archives[0] / "CLAIM_EVIDENCE_MATRIX.md").is_file())
        self.assertIn(
            "| Claim ID | Manuscript claim |",
            (self.state_dir / "CLAIM_EVIDENCE_MATRIX.md").read_text(encoding="utf-8"),
        )

        self.assertEqual(
            self.run_cli("submit-story", "--state", str(self.state_dir)).returncode,
            0,
        )
        self.assertEqual(
            self.run_cli(
                "approve-story", "--state", str(self.state_dir), "--by", "USER",
                "--evidence", "重新确认故事包",
            ).returncode,
            0,
        )
        self.advance_to_reviewable()
        (self.state_dir / "REVIEW_PANEL.md").write_text(completed_panel(), encoding="utf-8")
        reviewing = self.run_cli(
            "advance", "--state", str(self.state_dir), "--to", "REVIEWING"
        )
        self.assertEqual(reviewing.returncode, 0, reviewing.stderr)
        snapshot = json.loads(state_file.read_text(encoding="utf-8"))["review_snapshot"]
        self.write_review_outputs(snapshot)
        triage = self.run_cli(
            "advance", "--state", str(self.state_dir), "--to", "TRIAGE"
        )
        self.assertEqual(triage.returncode, 0, triage.stderr)


if __name__ == "__main__":
    unittest.main()
