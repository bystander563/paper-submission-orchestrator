#!/usr/bin/env python3
"""Durable state and hard gates for the paper submission workflow."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 2
STATE_FILE = "state.json"
LATEX_SOURCE_SUFFIXES = {".tex", ".ltx"}

STAGES = (
    "INTAKE",
    "WAITING_FOR_STORY_APPROVAL",
    "STORY_LOCKED",
    "DRAFTING",
    "ASSEMBLING",
    "REVIEWABLE",
    "WAITING_FOR_REVIEW_PANEL_APPROVAL",
    "REVIEWING",
    "TRIAGE",
    "REVISING",
    "RE_REVIEW",
    "SUBMISSION_QA",
    "SUBMISSION_READY",
    "CONDITIONALLY_READY",
    "NOT_READY",
)

ORDINARY_TRANSITIONS = {
    "STORY_LOCKED": {"DRAFTING"},
    "DRAFTING": {"ASSEMBLING"},
    "ASSEMBLING": {"REVIEWABLE"},
    "REVIEWABLE": {"REVIEWING", "WAITING_FOR_REVIEW_PANEL_APPROVAL"},
    "REVIEWING": {"TRIAGE"},
    "TRIAGE": {"REVISING"},
    "REVISING": {"RE_REVIEW"},
    "RE_REVIEW": {"SUBMISSION_QA"},
}

PASSED_GATE_BY_TARGET = {
    "ASSEMBLING": "G2_COMPLETE_DRAFT",
    "REVIEWABLE": "G3_REVIEWABLE_ARTIFACT",
    "TRIAGE": "G4_REVIEW_COMPLETE",
    "REVISING": "G5_REVISION_PLAN_ACCEPTED",
    "RE_REVIEW": "G6_REVISION_COMPLETE",
    "SUBMISSION_QA": "G7_SCIENTIFIC_SIGNOFF",
}

POST_STORY_STAGES = set(STAGES[2:])
REVIEW_SNAPSHOT_STAGES = {"REVIEWING", "TRIAGE"}
TERMINAL_STAGES = {"SUBMISSION_READY", "CONDITIONALLY_READY", "NOT_READY"}
POST_REVIEW_PANEL_STAGES = set(STAGES[STAGES.index("REVIEWING") :])
POST_REVIEW_OUTPUT_STAGES = set(STAGES[STAGES.index("TRIAGE") :])
POST_REREVIEW_OUTPUT_STAGES = set(STAGES[STAGES.index("SUBMISSION_QA") :])
POST_REREVIEW_SNAPSHOT_STAGES = set(STAGES[STAGES.index("RE_REVIEW") :])

FORBIDDEN_APPROVER_LABELS = {
    "AGENT",
    "ASSISTANT",
    "CODEX",
    "INTEGRATOR",
    "SCHEDULER",
    "SYSTEM",
}

REQUIRED_STORY_SECTIONS = (
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

REQUIRED_PANEL_SECTIONS = (
    "Editor-in-Chief",
    "Methodology Reviewer",
    "Domain Reviewer",
    "Perspective Reviewer",
    "Devil's Advocate",
    "Review mode and venue calibration",
)

CUSTOM_REQUIRED_PANEL_SECTIONS = (
    "Review mode and venue calibration",
    "Special configuration rationale",
    "Required report files",
)

REVIEW_PANEL_TYPES = {"STANDARD_FIVE_ROLE", "CUSTOM"}

STANDARD_RESPONSIBILITY_IDS = {
    "Editor-in-Chief": "EIC_STANDARD_V1",
    "Methodology Reviewer": "METHODOLOGY_STANDARD_V1",
    "Domain Reviewer": "DOMAIN_STANDARD_V1",
    "Perspective Reviewer": "PERSPECTIVE_STANDARD_V1",
    "Devil's Advocate": "DEVILS_ADVOCATE_STANDARD_V1",
}

STANDARD_REPORT_FILES = {
    "Editor-in-Chief": "EIC.md",
    "Methodology Reviewer": "METHODOLOGY.md",
    "Domain Reviewer": "DOMAIN.md",
    "Perspective Reviewer": "PERSPECTIVE.md",
    "Devil's Advocate": "DEVILS_ADVOCATE.md",
}

REQUIRED_REVIEW_SECTIONS = (
    "Recommendation and scope",
    "Evidence-grounded strengths",
    "Major concerns",
    "Minor concerns",
    "Required revisions",
    "Experiment requests",
    "Confidence and assumptions",
)

REQUIRED_EDITORIAL_SECTIONS = (
    "Decision",
    "Cross-reviewer consensus",
    "Disagreements and arbitration",
    "Devil's Advocate disposition",
    "Prioritized revision roadmap",
    "Experiment request summary",
)

REQUIRED_REREVIEW_SECTIONS = (
    "Verification decision",
    "Ticket-by-ticket verification",
    "Residual issues",
    "New issues",
    "Experiment requests",
    "Confidence and assumptions",
)

EXPERIMENT_RESOLUTIONS = {
    "RUN_AUTHORIZED",
    "CLAIM_NARROWED",
    "DECLINED_WITH_RATIONALE",
    "OUT_OF_SCOPE",
}
EXPERIMENT_CLOSED_STATUSES = {"COMPLETED", "APPLIED", "VERIFIED"}

REQUIRED_EXPERIMENT_FIELDS = (
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

UNRESOLVED_RE = re.compile(
    r"\[(?:TBD|TODO|CHECK|CITE|USER|PLACEHOLDER)(?::|\])|\bPLACEHOLDER\b|\bTODO\b|\bTBD\b",
    re.IGNORECASE,
)
UNRESOLVED_SINGLETONS = {
    "TBC",
    "UNKNOWN",
    "TO BE DETERMINED",
    "TO BE CONFIRMED",
    "PENDING",
}


STORY_TEMPLATE = """# Story Approval Packet

- Packet ID: STORY-001

## One-sentence thesis

[TBD]

## Target venue and paper type

[TBD]

## Argument chain

Problem -> gap -> mechanism -> evidence -> boundary.

[TBD]

## Headline contributions

[TBD]

## Explicit non-claims

[TBD]

## Main claim-evidence mapping

[TBD]

## Authoritative terminology decisions

[TBD]

## Main tables and figures

[TBD]

## Main-text and appendix allocation

[TBD]

## Remaining paper-level decisions

[TBD]

## Agent recommendation

[TBD]
"""


PANEL_TEMPLATE = """# Reviewer Configuration Card

This card is generated from the frozen review snapshot. All five reviewers are
read-only and must review independently.

- Configuration type: STANDARD_FIVE_ROLE

## Editor-in-Chief

- Persona and expertise: [TBD]
- Responsibility ID: EIC_STANDARD_V1

## Methodology Reviewer

- Persona and expertise: [TBD]
- Responsibility ID: METHODOLOGY_STANDARD_V1

## Domain Reviewer

- Persona and expertise: [TBD]
- Responsibility ID: DOMAIN_STANDARD_V1

## Perspective Reviewer

- Persona and expertise: [TBD]
- Responsibility ID: PERSPECTIVE_STANDARD_V1

## Devil's Advocate

- Persona and expertise: [TBD]
- Responsibility ID: DEVILS_ADVOCATE_STANDARD_V1

## Review mode and venue calibration

[TBD]

## Special configuration rationale

Not applicable for STANDARD_FIVE_ROLE.
"""


CLAIM_TEMPLATE = """# Claim-Evidence Matrix

| Claim ID | Manuscript claim | Evidence | Protocol | Evidence status | Allowed wording | Forbidden wording | Location |
|---|---|---|---|---|---|---|---|
"""


TERM_TEMPLATE = """# Terminology Ledger

| Term | Status | Authority | Accepted meaning | Paper usage | Collision risk |
|---|---|---|---|---|---|
"""


EXPERIMENT_TEMPLATE = """# Experiment Requests

Reviewer requests are proposals, not approved experiments. Copy each frozen
EXP-REQ identifier into this decision ledger before revision begins.

| Request ID | Resolution | Authority/evidence | Manuscript or experiment action | Status |
|---|---|---|---|---|
"""


REVISION_TEMPLATE = """# Revision Ledger

| Ticket ID | Review finding | Decision | Rationale | Target | Planned change | Owner | Status | Verification |
|---|---|---|---|---|---|---|---|---|
"""


READINESS_TEMPLATE = """# Submission Readiness

- Overall: NOT_READY
- Scientific readiness: FAIL
- Manuscript readiness: FAIL
- Submission-package readiness: FAIL
- Exact source revision:
- Exact bibliography path/hash:
- Exact PDF path/hash:
- Build command/result:
- Final rendered-PDF inspection evidence:
- Remaining P0/P1 blockers:
- User-supplied or external blockers:
- Residual non-blocking risks:
- Recommended next action:
"""


TABLE_QA_TEMPLATE = """# Table QA

- Overall table QA: NOT_RUN
- Exact PDF path/SHA-256:
- TeX table audit command/result:
- TeX table audit output SHA-256:
- TeX tables scanned:
- PDF font audit command/result:
- PDF font audit output SHA-256:

| Table | Page | Intended frame | Rule semantics | Column and row alignment | Minimum rendered font | Visual evidence | Changed pages | Status |
|---|---:|---|---|---|---:|---|---|---|
"""


BUILD_RECEIPT_TEMPLATE = """# Build Receipt

- Status: NOT_RUN
- Command:
- Source SHA-256:
- Bibliography SHA-256:
- Dependency manifest SHA-256:
- Dependency bundle SHA-256:
- Output PDF SHA-256:
- Page count:
- Undefined references/citations:
- Missing files:
- Overfull boxes:
- Rendered inspection:
"""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def pdf_page_count(path: Path) -> int:
    try:
        from pypdf import PdfReader
        return len(PdfReader(str(path)).pages)
    except ImportError:
        try:
            import fitz

            with fitz.open(path) as document:
                return document.page_count
        except ImportError as exc:
            raise ValueError(
                "pypdf or PyMuPDF is required to verify BUILD_RECEIPT page count"
            ) from exc
        except Exception as exc:
            raise ValueError(f"cannot read rendered PDF page count: {path}: {exc}") from exc
    except Exception as exc:
        raise ValueError(f"cannot read rendered PDF page count: {path}: {exc}") from exc


def write_new(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(content)


def portable_path(path: Path, root: Path) -> str:
    resolved = path.expanduser().resolve()
    try:
        return resolved.relative_to(root).as_posix()
    except ValueError:
        return str(resolved)


def resolve_input_path(path: Path, root: Path) -> Path:
    return path.expanduser().resolve() if path.is_absolute() else (root / path).resolve()


def resolve_artifact(state: dict[str, Any], value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    return (Path(state["project_root"]) / path).resolve()


def strip_tex_comments(text: str) -> str:
    return re.sub(r"(?<!\\)%[^\r\n]*", "", text)


def collect_text_dependencies(path: Path, seen: set[Path] | None = None) -> list[Path]:
    resolved = path.resolve()
    if seen is None:
        seen = set()
    if resolved in seen or not resolved.is_file():
        return []
    seen.add(resolved)
    files = [resolved]
    if resolved.suffix.lower() not in LATEX_SOURCE_SUFFIXES:
        return files
    text = strip_tex_comments(resolved.read_text(encoding="utf-8", errors="replace"))
    for match in re.finditer(r"\\(?:input|include)\s*\{([^}]+)\}", text):
        included = (resolved.parent / match.group(1).strip()).resolve()
        if included.suffix == "":
            included = included.with_suffix(".tex")
        files.extend(collect_text_dependencies(included, seen))
    return files


def resolve_local_reference(
    owner: Path,
    raw: str,
    extensions: tuple[str, ...],
    extra_bases: tuple[Path, ...] = (),
) -> Path | None:
    for base in (owner.parent,) + extra_bases:
        candidate = (base / raw.strip()).resolve()
        candidates = [candidate] if candidate.suffix else [candidate.with_suffix(ext) for ext in extensions]
        resolved = next((path for path in candidates if path.is_file()), None)
        if resolved:
            return resolved
    return None


def manifest_input_records(state: dict[str, Any]) -> tuple[Path | None, list[Path], list[str]]:
    value = state.get("artifacts", {}).get("dependency_manifest", "")
    if not value:
        return None, [], []
    manifest = resolve_artifact(state, value)
    if not manifest.is_file():
        return manifest, [], []
    if manifest.suffix.lower() in {".mk", ".d"}:
        _, inputs, missing = makefile_manifest_records(state, manifest)
        return manifest, inputs, missing
    inputs: list[Path] = []
    missing: list[str] = []
    working_directory = manifest.parent.resolve()
    for line in manifest.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("PWD "):
            candidate = Path(line[4:].strip()).expanduser()
            if candidate.is_dir():
                working_directory = candidate.resolve()
            continue
        if not line.startswith("INPUT "):
            continue
        raw = line[6:].strip().strip('"')
        candidate = Path(raw).expanduser()
        if not candidate.is_absolute():
            candidate = (working_directory / candidate).resolve()
        else:
            candidate = candidate.resolve()
        if candidate.is_file():
            inputs.append(candidate)
        else:
            missing.append(raw)
    return manifest, sorted(set(inputs)), missing


def makefile_manifest_records(
    state: dict[str, Any], manifest: Path
) -> tuple[list[Path], list[Path], list[str]]:
    lines = manifest.read_text(encoding="utf-8", errors="replace").splitlines()
    rule_index = next(
        (
            index
            for index, line in enumerate(lines)
            if line.strip() and not line.lstrip().startswith("#") and re.search(r"\s:\s", line)
        ),
        None,
    )
    if rule_index is None:
        return [], [], ["manifest has no Makefile dependency rule"]
    target_text, first_dependency = re.split(
        r"\s+:\s+", lines[rule_index].strip(), maxsplit=1
    )
    dependency_records: list[str] = []
    current = first_dependency.strip()
    cursor = rule_index
    while True:
        continues = current.endswith("\\")
        record_text = current[:-1].rstrip() if continues else current
        if record_text:
            dependency_records.append(record_text)
        if not continues:
            break
        cursor += 1
        if cursor >= len(lines):
            return [], [], ["Makefile dependency rule ends with an incomplete continuation"]
        current = lines[cursor].strip()
    source = resolve_artifact(state, state["artifacts"]["canonical_source"])
    rendered_pdf = resolve_artifact(state, state["artifacts"]["rendered_pdf"])
    root = Path(state["project_root"]).resolve()

    def path_is_recorded(fragment: str, path: Path) -> bool:
        spellings = {str(path.resolve()), path.resolve().as_posix()}
        try:
            relative = path.resolve().relative_to(root)
            spellings.update({str(relative), relative.as_posix()})
        except ValueError:
            pass
        return any(spelling in fragment for spelling in spellings)

    targets = [rendered_pdf.resolve()] if path_is_recorded(target_text, rendered_pdf) else []
    inputs: set[Path] = set()
    missing: list[str] = []
    for raw in dependency_records:
        candidate = Path(raw).expanduser()
        if not candidate.is_absolute():
            candidate = (root / candidate).resolve()
        else:
            candidate = candidate.resolve()
        if path_is_recorded(target_text, candidate):
            continue
        if candidate.is_file():
            inputs.add(candidate)
            continue
        try:
            projection = Path(os.path.relpath(candidate, rendered_pdf.parent.resolve()))
            source_candidate = (source.parent / projection).resolve()
        except ValueError:
            source_candidate = candidate
        if source_candidate.is_file():
            inputs.add(source_candidate)
        else:
            missing.append(raw)
    return sorted(set(targets)), sorted(path for path in inputs if path.is_file()), missing


def manifest_dependencies(state: dict[str, Any]) -> list[Path]:
    manifest, inputs, _ = manifest_input_records(state)
    dependencies = set(inputs)
    if manifest and manifest.is_file():
        dependencies.add(manifest.resolve())
    return sorted(dependencies)


def dependency_manifest_errors(state: dict[str, Any]) -> list[str]:
    source = resolve_artifact(state, state["artifacts"]["canonical_source"])
    if source.suffix.lower() not in LATEX_SOURCE_SUFFIXES:
        return []
    manifest, inputs, missing = manifest_input_records(state)
    errors: list[str] = []
    if manifest is None or not manifest.is_file():
        return [
            "LaTeX candidates require a compiler dependency manifest "
            "(.fls or Tectonic --makefile-rules .mk/.d)"
        ]
    if manifest.suffix.lower() not in {".fls", ".mk", ".d"}:
        errors.append(
            f"LaTeX dependency manifest must be .fls, .mk, or .d: {manifest}"
        )
    if len(inputs) < 2:
        errors.append(
            f"dependency manifest must contain the canonical source and at least one "
            f"additional existing INPUT record: {manifest}"
        )
    if source.resolve() not in set(inputs):
        errors.append(f"dependency manifest does not include the canonical source INPUT: {source}")
    if missing:
        sample = "; ".join(missing[:5])
        errors.append(f"dependency manifest references missing INPUT files: {sample}")
    rendered_pdf = resolve_artifact(state, state["artifacts"]["rendered_pdf"])
    outputs: set[Path] = set()
    if manifest.suffix.lower() == ".fls":
        working_directory = manifest.parent.resolve()
        has_pwd = False
        for line in manifest.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("PWD "):
                candidate = Path(line[4:].strip()).expanduser()
                if candidate.is_dir():
                    working_directory = candidate.resolve()
                    has_pwd = True
            elif line.startswith("OUTPUT "):
                raw = line[7:].strip().strip('"')
                candidate = Path(raw).expanduser()
                outputs.add(
                    candidate.resolve()
                    if candidate.is_absolute()
                    else (working_directory / candidate).resolve()
                )
        if not has_pwd:
            errors.append(f"dependency manifest lacks a valid PWD recorder line: {manifest}")
    else:
        targets, _, _ = makefile_manifest_records(state, manifest)
        outputs.update(targets)
    if rendered_pdf.resolve() not in outputs:
        errors.append(f"dependency manifest does not record the rendered PDF OUTPUT: {rendered_pdf}")
    return errors


def submission_dependencies(state: dict[str, Any]) -> list[Path]:
    source = resolve_artifact(state, state["artifacts"]["canonical_source"])
    bibliography = resolve_artifact(state, state["artifacts"]["bibliography"])
    dependencies = set(collect_text_dependencies(source))
    dependencies.add(bibliography.resolve())
    dependencies.update(manifest_dependencies(state))
    tex_owners = [path for path in dependencies if path.suffix.lower() == ".tex" and path.is_file()]
    graphic_bases: list[Path] = []
    for owner in tex_owners:
        text = strip_tex_comments(owner.read_text(encoding="utf-8", errors="replace"))
        for declaration in re.findall(
            r"\\graphicspath\s*\{((?:\s*\{[^{}]*\}\s*)+)\}", text
        ):
            for raw_base in re.findall(r"\{([^{}]+)\}", declaration):
                graphic_bases.append((owner.parent / raw_base.strip()).resolve())
    extra_graphic_bases = tuple(dict.fromkeys(graphic_bases))
    for owner in list(dependencies):
        if owner.suffix.lower() not in LATEX_SOURCE_SUFFIXES or not owner.is_file():
            continue
        text = strip_tex_comments(owner.read_text(encoding="utf-8", errors="replace"))
        for raw in re.findall(
            r"\\includegraphics\s*\*?\s*(?:\[[^\]]*\]\s*)?\{([^}]+)\}", text
        ):
            resolved = resolve_local_reference(
                owner,
                raw,
                (".pdf", ".png", ".jpg", ".jpeg", ".eps", ".svg"),
                extra_graphic_bases,
            )
            if resolved:
                dependencies.add(resolved)
        for raw in re.findall(r"\\addbibresource\s*\{([^}]+)\}", text):
            resolved = resolve_local_reference(owner, raw, (".bib",))
            if resolved:
                dependencies.add(resolved)
        for group in re.findall(r"\\bibliography\s*\{([^}]+)\}", text):
            for raw in group.split(","):
                resolved = resolve_local_reference(owner, raw, (".bib",))
                if resolved:
                    dependencies.add(resolved)
        for raw in re.findall(
            r"\\documentclass\s*(?:\[[^\]]*\]\s*)?\{([^}]+)\}", text
        ):
            resolved = resolve_local_reference(owner, raw, (".cls",))
            if resolved:
                dependencies.add(resolved)
        for group in re.findall(
            r"\\usepackage\s*(?:\[[^\]]*\]\s*)?\{([^}]+)\}", text
        ):
            for raw in group.split(","):
                resolved = resolve_local_reference(owner, raw, (".sty",))
                if resolved:
                    dependencies.add(resolved)
    return sorted(path for path in dependencies if path.is_file())


def dependency_hashes(state: dict[str, Any]) -> dict[str, str]:
    root = Path(state["project_root"])
    return {portable_path(path, root): sha256(path) for path in submission_dependencies(state)}


def dependency_bundle_sha256(state: dict[str, Any]) -> str:
    digest = hashlib.sha256()
    for path, file_hash in sorted(dependency_hashes(state).items()):
        digest.update(path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(file_hash.encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def dependency_snapshot_errors(state: dict[str, Any], snapshot: dict[str, Any], label: str) -> list[str]:
    expected = snapshot.get("submission_dependency_hashes") or {}
    current = dependency_hashes(state)
    if current != expected:
        return [f"submission dependency bundle changed after the {label} snapshot was frozen"]
    return []


def unresolved_marker_errors(source: Path, bibliography: Path) -> list[str]:
    errors: list[str] = []
    for path in collect_text_dependencies(source) + collect_text_dependencies(bibliography):
        if UNRESOLVED_RE.search(path.read_text(encoding="utf-8", errors="replace")):
            errors.append(f"submission source contains unresolved markers: {path}")
    return errors


def state_path(value: str | Path) -> Path:
    path = Path(value).expanduser().resolve()
    return path / STATE_FILE if path.is_dir() else path


def load_state(value: str | Path) -> tuple[Path, dict[str, Any]]:
    path = state_path(value)
    if not path.is_file():
        raise FileNotFoundError(f"workflow state not found: {path}")
    with path.open("r", encoding="utf-8") as stream:
        state = json.load(stream)
    if state.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(
            f"unsupported schema_version: {state.get('schema_version')}; "
            f"expected {SCHEMA_VERSION}. Start a new state directory or migrate explicitly."
        )
    return path, state


def save_state(path: Path, state: dict[str, Any]) -> None:
    temporary = path.with_suffix(".json.tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(state, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    temporary.replace(path)


def record(state: dict[str, Any], event: str, **details: Any) -> None:
    state.setdefault("history", []).append(
        {"at": utc_now(), "event": event, "details": details}
    )


def markdown_sections(text: str) -> dict[str, str]:
    matches = list(re.finditer(r"^##\s+(.+?)\s*$", text, re.MULTILINE))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[match.group(1).strip()] = text[match.end() : end].strip()
    return sections


def unresolved_evidence(value: str) -> bool:
    normalized = re.sub(r"\s+", " ", value).strip()
    normalized = normalized.strip("*_`~[]()<>\"' ")
    normalized = normalized.strip(" :;,.!?").upper()
    punctuation_free = normalized.replace(".", "")
    compact = re.sub(r"[^A-Z0-9]+", "", normalized)
    unresolved_compact = {
        "TBD",
        "TBC",
        "TODO",
        "UNKNOWN",
        "TOBEDETERMINED",
        "TOBECONFIRMED",
        "PENDING",
    }
    return (
        bool(UNRESOLVED_RE.search(value))
        or normalized in UNRESOLVED_SINGLETONS
        or punctuation_free in (UNRESOLVED_SINGLETONS | {"TBD", "TODO"})
        or compact in unresolved_compact
    )


def markdown_structural_records(text: str) -> list[tuple[str, bool]]:
    """Return non-code lines and whether quote/list containers were removed."""
    structural: list[tuple[str, bool]] = []
    fence_char: str | None = None
    fence_length = 0
    for raw_line in text.splitlines():
        line = raw_line
        had_container = False
        while True:
            unquoted = re.sub(r"^[ \t]{0,3}>[ \t]?", "", line, count=1)
            if unquoted != line:
                line = unquoted
                had_container = True
                continue
            unlisted = re.sub(
                r"^[ \t]{0,3}(?:[-+*]|\d+[.)])[ \t]+", "", line, count=1
            )
            if unlisted != line:
                line = unlisted
                had_container = True
                continue
            break
        if fence_char is not None:
            if re.match(
                rf"^[ \t]{{0,3}}{re.escape(fence_char)}{{{fence_length},}}[ \t]*$",
                line,
            ):
                fence_char = None
                fence_length = 0
            continue
        opening = re.match(r"^[ \t]{0,3}(`{3,}|~{3,})(?:[^\r\n]*)$", line)
        if opening:
            fence_char = opening.group(1)[0]
            fence_length = len(opening.group(1))
            continue
        structural.append((line, had_container))
    return structural


def validate_packet(path: Path, required: tuple[str, ...]) -> list[str]:
    if not path.is_file():
        return [f"missing packet: {path}"]
    text = path.read_text(encoding="utf-8")
    sections = markdown_sections(text)
    errors: list[str] = []
    if required == REQUIRED_STORY_SECTIONS:
        packet_ids = re.findall(
            r"^-\s*Packet ID:\s*([A-Za-z0-9][A-Za-z0-9_.-]*)\s*$",
            text,
            re.MULTILINE,
        )
        if len(packet_ids) != 1:
            errors.append(f"story packet must contain exactly one safe Packet ID: {path}")
    for heading in required:
        occurrences = re.findall(rf"^##\s+{re.escape(heading)}\s*$", text, re.MULTILINE)
        if len(occurrences) != 1:
            errors.append(f"section '{heading}' must occur exactly once in {path}")
            continue
        content = sections.get(heading, "")
        if not content:
            errors.append(f"missing or empty section '{heading}' in {path}")
        elif UNRESOLVED_RE.search(content):
            errors.append(f"unresolved marker in section '{heading}' of {path}")
    return errors


def review_panel_type(path: Path) -> str | None:
    if not path.is_file():
        return None
    matches = re.findall(
        r"^-\s*Configuration type:\s*([A-Z0-9_]+)\s*$",
        path.read_text(encoding="utf-8"),
        re.MULTILINE | re.IGNORECASE,
    )
    return matches[0].upper() if len(matches) == 1 else None


def custom_report_specs(path: Path) -> tuple[list[tuple[str, str]], list[str]]:
    if not path.is_file():
        return [], [f"missing reviewer configuration: {path}"]
    sections = markdown_sections(path.read_text(encoding="utf-8"))
    roster = sections.get("Required report files", "")
    rows = [line for line in roster.splitlines() if line.startswith("|")]
    data_rows = rows[2:] if len(rows) >= 2 else []
    specs: list[tuple[str, str]] = []
    errors: list[str] = []
    seen_roles: set[str] = set()
    seen_files: set[str] = set()
    for row in data_rows:
        cells = [cell.strip() for cell in row.strip().strip("|").split("|")]
        if len(cells) != 2 or any(not cell for cell in cells):
            errors.append(f"malformed custom reviewer output row: {row}")
            continue
        role, filename = cells
        if role in seen_roles:
            errors.append(f"duplicate custom reviewer role: {role}")
        if filename.lower() in seen_files:
            errors.append(f"duplicate custom reviewer output file: {filename}")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*\.md", filename):
            errors.append(f"unsafe custom reviewer output filename: {filename}")
        if filename.upper() in {"EDITORIAL_DECISION.MD", "RE_REVIEW.MD"}:
            errors.append(f"reserved custom reviewer output filename: {filename}")
        content = sections.get(role, "")
        if not content:
            errors.append(f"custom reviewer role lacks a matching section: {role}")
        else:
            for label in ("Persona and expertise", "Responsibility ID"):
                match = re.search(
                    rf"^-\s*{re.escape(label)}:\s*(.+?)\s*$", content, re.MULTILINE
                )
                if not match or UNRESOLVED_RE.search(match.group(1)):
                    errors.append(f"custom reviewer role '{role}' lacks a completed {label}")
        seen_roles.add(role)
        seen_files.add(filename.lower())
        specs.append((role, filename))
    if not specs:
        errors.append("CUSTOM review panel requires at least one reviewer output row")
    return specs, errors


def panel_report_specs(path: Path) -> tuple[list[tuple[str, str]], list[str]]:
    panel_type = review_panel_type(path)
    if panel_type == "STANDARD_FIVE_ROLE":
        return list(STANDARD_REPORT_FILES.items()), []
    if panel_type == "CUSTOM":
        return custom_report_specs(path)
    return [], ["review panel configuration type is invalid"]


def review_panel_errors(path: Path) -> list[str]:
    if not path.is_file():
        return [f"missing packet: {path}"]
    panel_type = review_panel_type(path)
    errors: list[str] = []
    if panel_type not in REVIEW_PANEL_TYPES:
        errors.append(
            "review panel must declare '- Configuration type: "
            "STANDARD_FIVE_ROLE' or 'CUSTOM'"
        )
        return errors
    if panel_type == "STANDARD_FIVE_ROLE":
        errors.extend(validate_packet(path, REQUIRED_PANEL_SECTIONS))
        panel_text = path.read_text(encoding="utf-8")
        sections = markdown_sections(panel_text)
        if "Required report files" in sections:
            errors.append(
                "STANDARD_FIVE_ROLE must not declare a custom report roster; "
                "declare CUSTOM and obtain approval"
            )
        allowed_sections = set(REQUIRED_PANEL_SECTIONS) | {"Special configuration rationale"}
        structural_records = markdown_structural_records(panel_text)
        structural_lines = [line for line, _ in structural_records]
        heading_rows: list[tuple[str, str]] = []
        for line in structural_lines:
            match = re.match(r"^[ \t]{0,3}(#{1,6})[ \t]+(.+?)[ \t]*$", line)
            if match:
                heading_rows.append((match.group(1), match.group(2)))
        for marker, heading in heading_rows:
            heading = heading.strip()
            if marker == "#" and heading == "Reviewer Configuration Card":
                continue
            if marker == "##" and heading in allowed_sections:
                continue
            errors.append(
                f"STANDARD_FIVE_ROLE contains an undeclared heading '{heading}'; "
                "declare CUSTOM and obtain approval for any additional reviewer or duty"
            )
        for heading in allowed_sections:
            if sum(1 for marker, candidate in heading_rows if marker == "##" and candidate.strip() == heading) > 1:
                errors.append(f"STANDARD_FIVE_ROLE repeats section '{heading}'")
        if sum(1 for marker, heading in heading_rows if marker == "#" and heading.strip() == "Reviewer Configuration Card") != 1:
            errors.append("STANDARD_FIVE_ROLE must contain exactly one canonical title")
        for index, line in enumerate(structural_lines[1:], start=1):
            if re.match(r"^[ ]{0,3}(?:=+|-+)[ \t]*$", line) and structural_lines[index - 1].strip():
                errors.append(
                    "STANDARD_FIVE_ROLE contains an undeclared Setext heading "
                    f"'{structural_lines[index - 1].strip()}'; use only the fixed "
                    "level-2 sections or declare CUSTOM"
                )
        for line in structural_lines:
            plain_role = re.match(
                r"^[ \t]{0,3}([^|:\r\n]*\b(?:reviewer|editor|advocate))\s*:\s*\S",
                line,
                re.IGNORECASE,
            )
            if plain_role:
                errors.append(
                    f"STANDARD_FIVE_ROLE contains an undeclared role label '{plain_role.group(1).strip()}'; "
                    "declare CUSTOM and obtain approval"
                )
        for line, had_container in structural_records:
            if not had_container:
                continue
            bare_role = re.match(
                r"^[ \t]{0,3}([^|:\r\n]*\b(?:reviewer|editor|advocate))\s*:?[ \t]*$",
                line,
                re.IGNORECASE,
            )
            if bare_role:
                errors.append(
                    f"STANDARD_FIVE_ROLE contains an undeclared container role label '{bare_role.group(1).strip()}'; "
                    "declare CUSTOM and obtain approval"
                )
        for index, line in enumerate(structural_lines[:-1]):
            if "|" in line and re.match(
                r"^[ \t]*\|?(?:[ \t]*:?-{3,}:?[ \t]*\|)+[ \t]*:?-{3,}:?[ \t]*\|?[ \t]*$",
                structural_lines[index + 1],
            ):
                errors.append(
                    "STANDARD_FIVE_ROLE must not contain a Markdown roster table; "
                    "declare CUSTOM and obtain approval"
                )
        for line in structural_lines:
            bold_match = re.match(
                r"^[ \t]{0,3}(?:\*\*([^*\n]+)\*\*|__([^_\n]+)__)(?:\s*:?[ \t]*.*)?$",
                line,
            )
            if bold_match:
                bold_heading = bold_match.group(1) or bold_match.group(2)
                if re.search(
                    r"\b(?:reviewer|editor|advocate)\s*:?[ \t]*$",
                    bold_heading,
                    re.IGNORECASE,
                ):
                    errors.append(
                        f"STANDARD_FIVE_ROLE contains an undeclared role-like label '{bold_heading.strip()}'; "
                        "declare CUSTOM and obtain approval"
                    )
            html_role = re.match(
                r"^[ \t]{0,3}<(?:h[1-6]|strong|b)>\s*(.+?)\s*</(?:h[1-6]|strong|b)>",
                line,
                re.IGNORECASE,
            )
            if html_role and re.search(
                r"\b(?:reviewer|editor|advocate)\s*:?[ \t]*$",
                html_role.group(1),
                re.IGNORECASE,
            ):
                errors.append(
                    f"STANDARD_FIVE_ROLE contains an undeclared HTML role label '{html_role.group(1).strip()}'; "
                    "declare CUSTOM and obtain approval"
                )
        for role, responsibility_id in STANDARD_RESPONSIBILITY_IDS.items():
            content = sections.get(role, "")
            persona = re.search(
                r"^-\s*Persona and expertise:\s*(.+?)\s*$",
                content,
                re.MULTILINE,
            )
            if not persona or UNRESOLVED_RE.search(persona.group(1)):
                errors.append(f"standard role '{role}' lacks a completed persona")
            if not re.search(
                rf"^-\s*Responsibility ID:\s*{re.escape(responsibility_id)}\s*$",
                content,
                re.MULTILINE,
            ):
                errors.append(
                    f"standard role '{role}' must retain Responsibility ID: "
                    f"{responsibility_id}; otherwise declare CUSTOM"
                )
    if panel_type == "CUSTOM":
        errors.extend(validate_packet(path, CUSTOM_REQUIRED_PANEL_SECTIONS))
        sections = markdown_sections(path.read_text(encoding="utf-8"))
        rationale = sections.get(
            "Special configuration rationale", ""
        )
        normalized = re.sub(r"\s+", " ", rationale.strip()).lower().rstrip(".")
        if (
            not rationale
            or UNRESOLVED_RE.search(rationale)
            or normalized in {"n/a", "na", "none", "not applicable"}
            or normalized.startswith("not applicable for ")
        ):
            errors.append(
                "CUSTOM review panel requires a completed "
                "'Special configuration rationale' section"
            )
        _, roster_errors = custom_report_specs(path)
        errors.extend(roster_errors)
    return errors


def freeze_review_snapshot(
    state: dict[str, Any], panel: Path, approval: dict[str, Any]
) -> None:
    source = resolve_artifact(state, state["artifacts"]["canonical_source"])
    bibliography = resolve_artifact(state, state["artifacts"]["bibliography"])
    pdf = resolve_artifact(state, state["artifacts"]["rendered_pdf"])
    build_receipt = resolve_artifact(state, state["artifacts"]["build_receipt"])
    if not source.is_file() or not bibliography.is_file() or not pdf.is_file():
        raise ValueError("review snapshot requires existing source, bibliography, and PDF")
    frozen_at = utc_now()
    state["approvals"]["review_panel"] = approval | {
        "frozen_at": frozen_at,
        "packet_sha256": sha256(panel),
    }
    state["review_snapshot"] = {
        "frozen_at": frozen_at,
        "canonical_source_sha256": sha256(source),
        "bibliography_sha256": sha256(bibliography),
        "rendered_pdf_sha256": sha256(pdf),
        "build_receipt_sha256": sha256(build_receipt),
        "submission_dependency_hashes": dependency_hashes(state),
        "panel_sha256": sha256(panel),
    }


def validate_human_approver(value: str) -> str:
    approver = value.strip()
    if not approver:
        raise ValueError("user/PI approver identity is required")
    if approver.upper() in FORBIDDEN_APPROVER_LABELS:
        raise ValueError(f"approver must identify the user/PI, not {approver}")
    return approver


def story_integrity_errors(state: dict[str, Any]) -> list[str]:
    if state.get("stage") not in POST_STORY_STAGES:
        return []
    approval = state.get("approvals", {}).get("story", {})
    packet = resolve_artifact(state, state["artifacts"]["story_packet"])
    errors: list[str] = []
    if approval.get("status") != "APPROVED":
        errors.append("story is not explicitly approved")
        return errors
    if not packet.is_file():
        errors.append(f"approved story packet missing: {packet}")
        return errors
    current_hash = sha256(packet)
    if current_hash != approval.get("packet_sha256"):
        errors.append("story packet changed after approval; approval is invalid")
    if not approval.get("by") or not approval.get("evidence"):
        errors.append("story approval lacks approver or verbatim evidence")
    return errors


def pending_story_errors(state: dict[str, Any]) -> list[str]:
    if state.get("stage") != "WAITING_FOR_STORY_APPROVAL":
        return []
    pending = state.get("approvals", {}).get("story", {})
    packet = resolve_artifact(state, state["artifacts"]["story_packet"])
    if not packet.is_file():
        return [f"pending story packet is missing: {packet}"]
    if sha256(packet) != pending.get("proposed_sha256"):
        return ["story packet changed after submission for approval; resubmit it"]
    return []


def pending_review_panel_errors(state: dict[str, Any]) -> list[str]:
    if state.get("stage") != "WAITING_FOR_REVIEW_PANEL_APPROVAL":
        return []
    pending = state.get("approvals", {}).get("review_panel", {})
    checks = (
        ("review panel", "review_panel", "proposed_sha256"),
        ("canonical source", "canonical_source", "proposed_source_sha256"),
        ("bibliography", "bibliography", "proposed_bibliography_sha256"),
        ("rendered PDF", "rendered_pdf", "proposed_pdf_sha256"),
        ("build receipt", "build_receipt", "proposed_build_receipt_sha256"),
    )
    errors: list[str] = []
    for label, artifact_key, hash_key in checks:
        artifact = resolve_artifact(state, state["artifacts"][artifact_key])
        if not artifact.is_file():
            errors.append(f"pending {label} artifact is missing: {artifact}")
        elif sha256(artifact) != pending.get(hash_key):
            errors.append(f"{label} changed after review-panel submission for approval")
    errors.extend(dependency_snapshot_errors(state, pending, "pending review-panel"))
    errors.extend(build_receipt_errors(state))
    return errors


def review_snapshot_errors(state: dict[str, Any]) -> list[str]:
    if state.get("stage") not in REVIEW_SNAPSHOT_STAGES:
        return []
    snapshot = state.get("review_snapshot") or {}
    if not snapshot:
        return ["review snapshot is missing"]
    errors: list[str] = []
    for key in ("canonical_source", "bibliography", "rendered_pdf"):
        path = resolve_artifact(state, state["artifacts"][key])
        if not path.is_file():
            errors.append(f"review snapshot artifact missing: {path}")
            continue
        expected = snapshot.get(f"{key}_sha256")
        if sha256(path) != expected:
            errors.append(f"{key} changed after the review snapshot was frozen")
    receipt = resolve_artifact(state, state["artifacts"]["build_receipt"])
    if not receipt.is_file() or sha256(receipt) != snapshot.get("build_receipt_sha256"):
        errors.append("build receipt changed after the review snapshot was frozen")
    errors.extend(dependency_snapshot_errors(state, snapshot, "review"))
    return errors


def review_panel_integrity_errors(state: dict[str, Any]) -> list[str]:
    if state.get("stage") not in POST_REVIEW_PANEL_STAGES:
        return []
    snapshot = state.get("review_snapshot") or {}
    panel = resolve_artifact(state, state["artifacts"]["review_panel"])
    if not panel.is_file():
        return [f"frozen review panel is missing: {panel}"]
    if sha256(panel) != snapshot.get("panel_sha256"):
        return ["REVIEW_PANEL.md changed after freeze"]
    return []


def review_reports_integrity_errors(state: dict[str, Any]) -> list[str]:
    if state.get("stage") not in POST_REVIEW_OUTPUT_STAGES:
        return []
    snapshot = state.get("review_reports_snapshot") or {}
    if not snapshot:
        return ["review reports snapshot is missing"]
    reviews_dir = resolve_artifact(state, state["artifacts"]["reviews_dir"])
    errors: list[str] = []
    for name, expected in snapshot.items():
        report = reviews_dir / name
        if not report.is_file():
            errors.append(f"frozen review report is missing: {report}")
        elif sha256(report) != expected:
            errors.append(f"frozen review report changed after TRIAGE: {report}")
    return errors


def rereview_snapshot_errors(state: dict[str, Any]) -> list[str]:
    if state.get("stage") not in POST_REREVIEW_SNAPSHOT_STAGES:
        return []
    snapshot = state.get("rereview_snapshot") or {}
    if not snapshot:
        return ["re-review snapshot is missing"]
    errors: list[str] = []
    for key in ("canonical_source", "bibliography", "rendered_pdf"):
        path = resolve_artifact(state, state["artifacts"][key])
        if not path.is_file():
            errors.append(f"re-review snapshot artifact missing: {path}")
        elif sha256(path) != snapshot.get(f"{key}_sha256"):
            errors.append(f"{key} changed after the re-review snapshot was frozen")
    receipt = resolve_artifact(state, state["artifacts"]["build_receipt"])
    if not receipt.is_file() or sha256(receipt) != snapshot.get("build_receipt_sha256"):
        errors.append("build receipt changed after the re-review snapshot was frozen")
    for artifact_key, snapshot_key, label in (
        ("revision_ledger", "revision_ledger_sha256", "revision ledger"),
        ("experiment_requests", "experiment_requests_sha256", "experiment decision ledger"),
    ):
        artifact = resolve_artifact(state, state["artifacts"][artifact_key])
        if not artifact.is_file() or sha256(artifact) != snapshot.get(snapshot_key):
            errors.append(f"{label} changed after the re-review snapshot was frozen")
    errors.extend(dependency_snapshot_errors(state, snapshot, "re-review"))
    return errors


def rereview_report_integrity_errors(state: dict[str, Any]) -> list[str]:
    if state.get("stage") not in POST_REREVIEW_OUTPUT_STAGES:
        return []
    snapshot = state.get("rereview_snapshot") or {}
    expected = snapshot.get("report_sha256")
    report = resolve_artifact(state, state["artifacts"]["reviews_dir"]) / "RE_REVIEW.md"
    if not expected:
        return ["re-review report snapshot is missing"]
    if not report.is_file():
        return [f"frozen re-review report is missing: {report}"]
    if sha256(report) != expected:
        return ["RE_REVIEW.md changed after SUBMISSION_QA sign-off"]
    return []


def required_section_errors(text: str, required: tuple[str, ...], label: Path) -> list[str]:
    sections = markdown_sections(text)
    errors: list[str] = []
    for heading in required:
        occurrences = re.findall(rf"^##\s+{re.escape(heading)}\s*$", text, re.MULTILINE)
        if len(occurrences) != 1:
            errors.append(
                f"required section '{heading}' must occur exactly once: {label}"
            )
            continue
        content = sections.get(heading, "")
        if not content:
            errors.append(f"required section '{heading}' is missing or empty: {label}")
        elif UNRESOLVED_RE.search(content):
            errors.append(f"required section '{heading}' contains an unresolved marker: {label}")
    return errors


def line_marker_values(text: str, label: str) -> list[str]:
    return [
        value.strip()
        for value in re.findall(
            rf"^{re.escape(label)}:\s*(.+?)\s*$", text, re.MULTILINE | re.IGNORECASE
        )
    ]


def bullet_field_values(text: str, label: str) -> list[str]:
    return [
        value.strip()
        for value in re.findall(
            rf"^-\s*{re.escape(label)}:\s*(.+?)\s*$", text, re.MULTILINE
        )
    ]


def exact_line_hash_errors(
    text: str, label: str, expected: str, artifact: Path
) -> list[str]:
    values = line_marker_values(text, label)
    if len(values) != 1:
        return [f"hash field '{label}' must occur exactly once: {artifact}"]
    hashes = re.findall(r"\b[0-9a-fA-F]{64}\b", values[0])
    if len(hashes) != 1 or hashes[0].lower() != expected.lower():
        return [f"hash field '{label}' does not identify the exact frozen hash: {artifact}"]
    return []


def review_output_errors(state: dict[str, Any]) -> list[str]:
    reviews_dir = resolve_artifact(state, state["artifacts"]["reviews_dir"])
    panel = resolve_artifact(state, state["artifacts"]["review_panel"])
    specs, spec_errors = panel_report_specs(panel)
    reviewer_reports = tuple(reviews_dir / filename for _, filename in specs)
    report_roles = {filename: role for role, filename in specs}
    editorial = reviews_dir / "EDITORIAL_DECISION.md"
    required = reviewer_reports + (editorial,)
    errors = list(spec_errors)
    errors.extend(f"required review artifact missing: {path}" for path in required if not path.is_file())
    allowed_names = {path.name.lower() for path in required}
    for report in reviews_dir.glob("*.md"):
        if report.name.lower() not in allowed_names:
            errors.append(f"unregistered review artifact is present: {report}")
    report_hashes: dict[str, str] = {}
    for report in reviewer_reports:
        if not report.is_file():
            continue
        digest = sha256(report)
        if digest in report_hashes:
            errors.append(
                f"independent reviewer reports are exact duplicates: "
                f"{report_hashes[digest]} and {report}"
            )
        report_hashes[digest] = str(report)
    snapshot = state.get("review_snapshot") or {}
    source_hash = snapshot.get("canonical_source_sha256", "")
    bibliography_hash = snapshot.get("bibliography_sha256", "")
    pdf_hash = snapshot.get("rendered_pdf_sha256", "")
    for report in required:
        if not report.is_file():
            continue
        text = report.read_text(encoding="utf-8")
        for label, expected in (
            ("Source snapshot SHA-256", source_hash),
            ("Bibliography snapshot SHA-256", bibliography_hash),
            ("PDF snapshot SHA-256", pdf_hash),
        ):
            errors.extend(exact_line_hash_errors(text, label, expected, report))
        if report == editorial:
            errors.extend(required_section_errors(text, REQUIRED_EDITORIAL_SECTIONS, report))
            continue
        errors.extend(required_section_errors(text, REQUIRED_REVIEW_SECTIONS, report))
        if report_roles.get(report.name) == "Devil's Advocate":
            errors.extend(required_section_errors(text, ("Strongest counter-argument",), report))
        marker_values = line_marker_values(text, "Experiment requirement")
        if len(marker_values) != 1:
            errors.append(
                f"review report must contain exactly one 'Experiment requirement:' marker: {report}"
            )
        elif marker_values[0].upper() != "NONE":
            errors.extend(experiment_card_errors(text, marker_values[0], report))
        revision_values = line_marker_values(text, "Revision requirement")
        if len(revision_values) != 1:
            errors.append(
                f"review report must contain exactly one 'Revision requirement:' marker: {report}"
            )
        elif revision_values[0].upper() != "NONE" and not re.findall(
            r"REV-REQ-[A-Za-z0-9_-]+", revision_values[0], re.IGNORECASE
        ):
            errors.append(f"review revision marker has no REV-REQ identifier: {report}")
    return errors


def requested_experiment_ids(state: dict[str, Any]) -> set[str]:
    reviews_dir = resolve_artifact(state, state["artifacts"]["reviews_dir"])
    requested: set[str] = {
        item.upper() for item in state.get("pending_experiment_request_ids", [])
    }
    panel = resolve_artifact(state, state["artifacts"]["review_panel"])
    specs, _ = panel_report_specs(panel)
    for _, name in specs:
        report = reviews_dir / name
        if not report.is_file():
            continue
        text = report.read_text(encoding="utf-8")
        for marker in line_marker_values(text, "Experiment requirement"):
            if marker.upper() != "NONE":
                requested.update(
                    item.upper()
                    for item in re.findall(r"EXP-REQ-[A-Za-z0-9_-]+", marker, re.IGNORECASE)
                )
    return requested


def requested_revision_ids(state: dict[str, Any]) -> set[str]:
    reviews_dir = resolve_artifact(state, state["artifacts"]["reviews_dir"])
    panel = resolve_artifact(state, state["artifacts"]["review_panel"])
    specs, _ = panel_report_specs(panel)
    requested: set[str] = {
        item.upper() for item in state.get("pending_revision_request_ids", [])
    }
    for _, name in specs:
        report = reviews_dir / name
        if not report.is_file():
            continue
        for marker in line_marker_values(
            report.read_text(encoding="utf-8"), "Revision requirement"
        ):
            if marker.upper() != "NONE":
                requested.update(
                    item.upper()
                    for item in re.findall(r"REV-REQ-[A-Za-z0-9_-]+", marker, re.IGNORECASE)
                )
    return requested


def rereview_experiment_ids(state: dict[str, Any]) -> set[str]:
    report = resolve_artifact(state, state["artifacts"]["reviews_dir"]) / "RE_REVIEW.md"
    if not report.is_file():
        return set()
    requested: set[str] = set()
    for marker in line_marker_values(
        report.read_text(encoding="utf-8"), "Experiment requirement"
    ):
        if marker.upper() != "NONE":
            requested.update(
                item.upper()
                for item in re.findall(r"EXP-REQ-[A-Za-z0-9_-]+", marker, re.IGNORECASE)
            )
    return requested


def rereview_revision_ids(state: dict[str, Any]) -> set[str]:
    report = resolve_artifact(state, state["artifacts"]["reviews_dir"]) / "RE_REVIEW.md"
    if not report.is_file():
        return set()
    requested: set[str] = set()
    for marker in line_marker_values(
        report.read_text(encoding="utf-8"), "Revision requirement"
    ):
        if marker.upper() != "NONE":
            requested.update(
                item.upper()
                for item in re.findall(r"REV-REQ-[A-Za-z0-9_-]+", marker, re.IGNORECASE)
            )
    return requested


def markdown_table_rows(path: Path) -> list[list[str]]:
    if not path.is_file():
        return []
    rows = [line for line in path.read_text(encoding="utf-8").splitlines() if line.startswith("|")]
    data_rows = rows[2:] if len(rows) >= 2 else []
    return [[cell.strip() for cell in row.strip().strip("|").split("|")] for row in data_rows]


def experiment_decision_errors(state: dict[str, Any], require_closed: bool) -> list[str]:
    requested = requested_experiment_ids(state)
    if not requested:
        return []
    ledger = resolve_artifact(state, state["artifacts"]["experiment_requests"])
    rows = markdown_table_rows(ledger)
    decisions: dict[str, list[str]] = {}
    errors: list[str] = []
    for cells in rows:
        if len(cells) != 5 or not cells[0].upper().startswith("EXP-REQ-"):
            errors.append(f"malformed experiment decision row: {' | '.join(cells)}")
            continue
        request_id = cells[0].upper()
        if request_id in decisions:
            errors.append(f"duplicate experiment decision row: {request_id}")
        decisions[request_id] = cells
    for request_id in sorted(requested):
        cells = decisions.get(request_id)
        if cells is None:
            errors.append(f"experiment request lacks a triage decision: {request_id}")
            continue
        _, resolution, authority, action, status = cells
        resolution = resolution.upper()
        status = status.upper()
        if resolution not in EXPERIMENT_RESOLUTIONS:
            errors.append(f"{request_id} has invalid resolution: {resolution}")
        if not authority or UNRESOLVED_RE.search(authority):
            errors.append(f"{request_id} lacks authority/evidence")
        if not action or UNRESOLVED_RE.search(action):
            errors.append(f"{request_id} lacks a concrete manuscript or experiment action")
        if resolution == "RUN_AUTHORIZED" and not re.search(
            r"\b(USER|PI|PROJECT_POLICY)\b", authority, re.IGNORECASE
        ):
            errors.append(
                f"{request_id} RUN_AUTHORIZED lacks USER, PI, or PROJECT_POLICY authority"
            )
        if require_closed and status not in EXPERIMENT_CLOSED_STATUSES:
            errors.append(f"{request_id} is not closed before re-review: {status or 'EMPTY'}")
    return errors


def experiment_card_errors(text: str, marker: str, report: Path) -> list[str]:
    errors: list[str] = []
    requested = {item.upper() for item in re.findall(r"EXP-REQ-[A-Za-z0-9_-]+", marker)}
    if not requested:
        return [f"review experiment marker has no EXP-REQ identifier: {report}"]
    headings = list(
        re.finditer(
            r"^###\s+(EXP-REQ-[A-Za-z0-9_-]+)(?::[^\n]*)?\s*$",
            text,
            re.MULTILINE | re.IGNORECASE,
        )
    )
    cards: dict[str, str] = {}
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        cards[heading.group(1).upper()] = text[heading.end() : end]
    for request_id in sorted(requested):
        card = cards.get(request_id)
        if card is None:
            errors.append(f"review requests {request_id} without a matching card: {report}")
            continue
        for field in REQUIRED_EXPERIMENT_FIELDS:
            match = re.search(
                rf"^-\s+{re.escape(field)}:\s*(.+?)\s*$",
                card,
                re.MULTILINE,
            )
            if not match or not match.group(1).strip() or UNRESOLVED_RE.search(match.group(1)):
                errors.append(f"{request_id} is missing a completed '{field}' field: {report}")
    return errors


def rereview_output_errors(state: dict[str, Any]) -> list[str]:
    reviews_dir = resolve_artifact(state, state["artifacts"]["reviews_dir"])
    report = reviews_dir / "RE_REVIEW.md"
    if not report.is_file():
        return [f"required re-review artifact missing: {report}"]
    snapshot = state.get("rereview_snapshot") or {}
    source_hash = snapshot.get("canonical_source_sha256", "")
    bibliography_hash = snapshot.get("bibliography_sha256", "")
    pdf_hash = snapshot.get("rendered_pdf_sha256", "")
    build_receipt_hash = snapshot.get("build_receipt_sha256", "")
    revision_ledger_hash = snapshot.get("revision_ledger_sha256", "")
    experiment_ledger_hash = snapshot.get("experiment_requests_sha256", "")
    text = report.read_text(encoding="utf-8")
    errors: list[str] = []
    for label, expected in (
        ("Source snapshot SHA-256", source_hash),
        ("Bibliography snapshot SHA-256", bibliography_hash),
        ("PDF snapshot SHA-256", pdf_hash),
        ("Build receipt SHA-256", build_receipt_hash),
        ("Revision ledger SHA-256", revision_ledger_hash),
        ("Experiment ledger SHA-256", experiment_ledger_hash),
    ):
        errors.extend(exact_line_hash_errors(text, label, expected, report))
    errors.extend(required_section_errors(text, REQUIRED_REREVIEW_SECTIONS, report))
    if bullet_field_values(text, "Scientific signoff") != ["PASS"]:
        errors.append("re-review report does not declare Scientific signoff: PASS")
    marker_values = line_marker_values(text, "Experiment requirement")
    if len(marker_values) != 1:
        errors.append(
            f"re-review report must contain exactly one 'Experiment requirement:' marker: {report}"
        )
    elif marker_values[0].upper() != "NONE":
        errors.extend(experiment_card_errors(text, marker_values[0], report))
        errors.append(
            "re-review introduced an experiment request; reopen revision, triage it, "
            "and re-review the resulting final candidate"
        )
    revision_values = line_marker_values(text, "Revision requirement")
    if len(revision_values) != 1:
        errors.append(
            f"re-review report must contain exactly one 'Revision requirement:' marker: {report}"
        )
    elif revision_values[0].upper() != "NONE":
        errors.append(
            "re-review introduced a revision requirement; reopen revision and re-review "
            "the resulting final candidate"
        )
    return errors


def exact_pdf_hash_in(text: str, label: str) -> str | None:
    values = bullet_field_values(text, label)
    if len(values) != 1:
        return None
    hashes = re.findall(r"\b[0-9a-fA-F]{64}\b", values[0])
    return hashes[0].lower() if len(hashes) == 1 else None


def build_receipt_errors(state: dict[str, Any]) -> list[str]:
    receipt = resolve_artifact(state, state["artifacts"]["build_receipt"])
    if not receipt.is_file():
        return [f"build receipt is missing: {receipt}"]
    text = receipt.read_text(encoding="utf-8")
    errors: list[str] = []
    if bullet_field_values(text, "Status") != ["PASS"]:
        errors.append("BUILD_RECEIPT.md does not declare Status: PASS")
    source = resolve_artifact(state, state["artifacts"]["canonical_source"])
    bibliography = resolve_artifact(state, state["artifacts"]["bibliography"])
    pdf = resolve_artifact(state, state["artifacts"]["rendered_pdf"])
    for label, artifact in (
        ("Source SHA-256", source),
        ("Bibliography SHA-256", bibliography),
        ("Output PDF SHA-256", pdf),
    ):
        if not artifact.is_file() or exact_pdf_hash_in(text, label) != sha256(artifact).lower():
            errors.append(f"BUILD_RECEIPT.md does not identify the exact {label}")
    if source.suffix.lower() in LATEX_SOURCE_SUFFIXES:
        errors.extend(dependency_manifest_errors(state))
        manifest_value = state.get("artifacts", {}).get("dependency_manifest", "")
        manifest = resolve_artifact(state, manifest_value) if manifest_value else None
        if manifest is not None and manifest.is_file() and exact_pdf_hash_in(
            text, "Dependency manifest SHA-256"
        ) != sha256(manifest):
            errors.append("BUILD_RECEIPT.md does not identify the exact dependency manifest SHA-256")
    if exact_pdf_hash_in(text, "Dependency bundle SHA-256") != dependency_bundle_sha256(state):
        errors.append("BUILD_RECEIPT.md does not identify the exact dependency bundle SHA-256")
    for label in ("Command",):
        values = bullet_field_values(text, label)
        if len(values) != 1 or not values[0] or UNRESOLVED_RE.search(values[0]):
            errors.append(f"BUILD_RECEIPT.md lacks completed '{label}' evidence")
    expected_command = state.get("build_command", "").strip()
    recorded_commands = bullet_field_values(text, "Command")
    if expected_command and recorded_commands != [expected_command]:
        errors.append("BUILD_RECEIPT.md Command does not match the initialized repository build command")
    integer_fields: dict[str, int | None] = {}
    for label in (
        "Page count",
        "Undefined references/citations",
        "Missing files",
        "Overfull boxes",
    ):
        values = bullet_field_values(text, label)
        match = re.fullmatch(r"(\d+)(?:\s*;\s*(.+))?", values[0]) if len(values) == 1 else None
        if not match:
            errors.append(
                f"BUILD_RECEIPT.md '{label}' must start with one non-negative integer"
            )
            integer_fields[label] = None
            continue
        integer_fields[label] = int(match.group(1))
        if label == "Page count" and integer_fields[label] <= 0:
            errors.append("BUILD_RECEIPT.md Page count must be a positive integer")
        if label in {"Undefined references/citations", "Missing files"} and integer_fields[label] != 0:
            errors.append(f"BUILD_RECEIPT.md cannot PASS with nonzero {label}")
        if label == "Overfull boxes" and integer_fields[label] > 0:
            disposition = (match.group(2) or "").strip()
            if not re.fullmatch(r"REVIEWED:\s*\S.+", disposition, re.IGNORECASE):
                errors.append(
                    "nonzero overfull boxes require '; REVIEWED: <visual disposition and reason>'"
                )
    if pdf.is_file() and integer_fields.get("Page count") is not None:
        try:
            actual_pages = pdf_page_count(pdf)
            if integer_fields["Page count"] != actual_pages:
                errors.append(
                    f"BUILD_RECEIPT.md Page count does not match the rendered PDF ({actual_pages})"
                )
        except ValueError as exc:
            errors.append(str(exc))
    rendered = bullet_field_values(text, "Rendered inspection")
    if len(rendered) != 1 or not re.fullmatch(
        r"PASS;\s*pages=(?:ALL|[0-9][0-9, -]*);\s*evidence=\S.+",
        rendered[0],
        re.IGNORECASE,
    ):
        errors.append(
            "BUILD_RECEIPT.md Rendered inspection must use "
            "'PASS; pages=ALL|<pages>; evidence=<completed evidence>'"
        )
    return errors


def table_qa_errors(state: dict[str, Any]) -> list[str]:
    table_qa = resolve_artifact(state, state["artifacts"]["table_qa"])
    pdf = resolve_artifact(state, state["artifacts"]["rendered_pdf"])
    source = resolve_artifact(state, state["artifacts"]["canonical_source"])
    tex_audit = resolve_artifact(state, state["artifacts"]["tex_table_audit"])
    font_audit = resolve_artifact(state, state["artifacts"]["pdf_font_audit"])
    if not table_qa.is_file():
        return [f"final table QA ledger is missing: {table_qa}"]
    text = table_qa.read_text(encoding="utf-8")
    errors: list[str] = []
    if bullet_field_values(text, "Overall table QA") != ["PASS"]:
        errors.append("TABLE_QA.md does not declare Overall table QA: PASS")
    recorded = exact_pdf_hash_in(text, "Exact PDF path/SHA-256")
    actual = sha256(pdf).lower()
    if recorded != actual:
        errors.append("TABLE_QA.md does not identify the exact final PDF SHA-256")
    tex_payload: dict[str, Any] = {}
    font_payload: dict[str, Any] = {}
    if not tex_audit.is_file():
        errors.append(f"strict TeX table audit JSON is missing: {tex_audit}")
    else:
        if exact_pdf_hash_in(text, "TeX table audit output SHA-256") != sha256(tex_audit):
            errors.append("TABLE_QA.md does not bind the exact TeX table audit JSON hash")
        try:
            tex_payload = json.loads(tex_audit.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            errors.append(f"strict TeX table audit JSON is invalid: {tex_audit}")
    if not font_audit.is_file():
        errors.append(f"PDF font audit JSON is missing: {font_audit}")
    else:
        if exact_pdf_hash_in(text, "PDF font audit output SHA-256") != sha256(font_audit):
            errors.append("TABLE_QA.md does not bind the exact PDF font audit JSON hash")
        try:
            font_payload = json.loads(font_audit.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            errors.append(f"PDF font audit JSON is invalid: {font_audit}")
    if tex_payload:
        if tex_payload.get("ok") is not True or tex_payload.get("strict") is not True:
            errors.append("TeX table audit JSON must record strict=true and ok=true")
        recorded_main = Path(str(tex_payload.get("main_tex", ""))).expanduser()
        if not recorded_main.is_absolute() or recorded_main.resolve() != source.resolve():
            errors.append("TeX table audit JSON does not identify the exact canonical source")
        if tex_payload.get("main_tex_sha256") != sha256(source):
            errors.append("TeX table audit JSON does not bind the current canonical source hash")
        files_sha = tex_payload.get("files_sha256")
        if not isinstance(files_sha, dict) or not files_sha:
            errors.append("TeX table audit JSON lacks the scanned-file hash inventory")
        else:
            for raw_path, expected_hash in files_sha.items():
                scanned_path = Path(str(raw_path)).expanduser()
                if (
                    not scanned_path.is_absolute()
                    or not scanned_path.is_file()
                    or sha256(scanned_path.resolve()) != expected_hash
                ):
                    errors.append(
                        f"TeX table audit scanned file changed or is missing: {raw_path}"
                    )
    if font_payload:
        recorded_pdf = Path(str(font_payload.get("pdf", ""))).expanduser()
        if (
            font_payload.get("status") != "PASS"
            or font_payload.get("errors") not in ([], None)
            or font_payload.get("pdf_sha256") != sha256(pdf)
            or not recorded_pdf.is_absolute()
            or recorded_pdf.resolve() != pdf.resolve()
        ):
            errors.append("PDF font audit JSON does not PASS on the exact candidate PDF")
    tex_evidence = bullet_field_values(text, "TeX table audit command/result")
    if (
        len(tex_evidence) != 1
        or UNRESOLVED_RE.search(tex_evidence[0])
        or "--strict" not in tex_evidence[0]
        or not re.search(r"\bPASS\b", tex_evidence[0], re.IGNORECASE)
    ):
        errors.append(
            "TABLE_QA.md TeX audit evidence must record --strict and PASS"
        )
    font_evidence = bullet_field_values(text, "PDF font audit command/result")
    expected_font_binding = f"pdf_sha256={sha256(pdf).lower()}"
    if (
        len(font_evidence) != 1
        or UNRESOLVED_RE.search(font_evidence[0])
        or not re.search(r"\bPASS\b", font_evidence[0], re.IGNORECASE)
        or expected_font_binding not in font_evidence[0].lower()
    ):
        errors.append(
            "TABLE_QA.md PDF font evidence must record PASS and the exact pdf_sha256"
        )
    scanned_values = bullet_field_values(text, "TeX tables scanned")
    scanned = None
    if len(scanned_values) != 1 or not re.fullmatch(r"\d+", scanned_values[0]):
        errors.append("TABLE_QA.md must declare one integer 'TeX tables scanned' value")
    else:
        scanned = int(scanned_values[0])
        if len(tex_evidence) == 1 and not re.search(
            rf"\btables_scanned\s*=\s*{scanned}\b", tex_evidence[0], re.IGNORECASE
        ):
            errors.append(
                "TABLE_QA.md TeX audit evidence does not bind the declared tables_scanned count"
            )
        if tex_payload and tex_payload.get("tables_scanned") != scanned:
            errors.append(
                "TABLE_QA.md TeX tables scanned does not match the bound strict audit JSON"
            )
    inventory = tex_payload.get("tables", []) if isinstance(tex_payload, dict) else []
    if tex_payload and (
        not isinstance(inventory, list)
        or len(inventory) != tex_payload.get("tables_scanned")
        or any(not isinstance(item, dict) or not item.get("id") for item in inventory)
    ):
        errors.append("TeX table audit JSON has an invalid or incomplete table inventory")
        inventory = []
    inventory_ids = [str(item["id"]) for item in inventory]
    if len(inventory_ids) != len(set(inventory_ids)):
        errors.append("TeX table audit JSON contains duplicate table IDs")
    rows = [line for line in text.splitlines() if line.startswith("|")]
    data_rows = rows[2:] if len(rows) >= 2 else []
    no_tables = bool(re.search(r"^-\s*NO_TABLES:\s*CONFIRMED\s*$", text, re.MULTILINE))
    if not data_rows and not no_tables:
        errors.append("TABLE_QA.md has no table rows and no NO_TABLES declaration")
    if scanned is not None:
        if scanned == 0 and (data_rows or not no_tables):
            errors.append(
                "TABLE_QA.md with zero scanned tables requires NO_TABLES and no table rows"
            )
        if scanned > 0 and (no_tables or len(data_rows) != scanned):
            errors.append(
                f"TABLE_QA.md row count ({len(data_rows)}) does not match TeX tables scanned ({scanned})"
            )
    ledger_ids: list[str] = []
    for row in data_rows:
        cells = [cell.strip() for cell in row.strip().strip("|").split("|")]
        if len(cells) != 9 or any(not cell for cell in cells):
            errors.append(f"TABLE_QA.md contains an incomplete or malformed table row: {row}")
            continue
        ledger_ids.append(cells[0])
        if cells[-1].upper() != "PASS":
            errors.append(f"TABLE_QA.md contains a non-PASS table row: {row}")
        try:
            if float(cells[5]) <= 0:
                raise ValueError
        except ValueError:
            errors.append(f"TABLE_QA.md has an invalid minimum rendered font value: {row}")
    if inventory_ids and set(ledger_ids) != set(inventory_ids):
        errors.append("TABLE_QA.md table IDs do not exactly cover the bound strict audit inventory")
    return errors


def revision_ledger_errors(
    path: Path, required_ids: set[str], require_closed: bool = False
) -> list[str]:
    if not path.is_file():
        return [f"revision ledger is missing: {path}"]
    text = path.read_text(encoding="utf-8")
    if re.search(r"^NO_REQUIRED_REVISIONS\s*$", text, re.MULTILINE):
        return (
            ["revision ledger declares NO_REQUIRED_REVISIONS despite reviewer REV-REQ tickets"]
            if required_ids
            else []
        )
    rows = markdown_table_rows(path)
    if not rows:
        return ["revision ledger has no actionable row or NO_REQUIRED_REVISIONS marker"]
    errors: list[str] = []
    recorded_ids: set[str] = set()
    for cells in rows:
        if len(cells) != 9 or any(not cell for cell in cells):
            errors.append(f"revision ledger contains an incomplete or malformed row: {' | '.join(cells)}")
        elif any(UNRESOLVED_RE.search(cell) for cell in cells):
            errors.append(f"revision ledger contains an unresolved marker: {' | '.join(cells)}")
        elif not re.fullmatch(r"REV-REQ-[A-Za-z0-9_-]+", cells[0], re.IGNORECASE):
            errors.append(f"revision ledger ticket ID is not a REV-REQ identifier: {cells[0]}")
        else:
            recorded_ids.add(cells[0].upper())
            if require_closed:
                status = cells[7].strip().upper()
                verification = cells[8].strip()
                if status not in {"APPLIED", "VERIFIED", "DEFERRED", "REJECTED"}:
                    errors.append(
                        f"revision ticket is not closed before re-review: {cells[0]} ({status})"
                    )
                if UNRESOLVED_RE.search(verification) or re.search(
                    r"\b(?:PENDING|TODO|NOT VERIFIED|UNVERIFIED)\b", verification, re.IGNORECASE
                ):
                    errors.append(
                        f"revision ticket lacks completed verification before re-review: {cells[0]}"
                    )
    for request_id in sorted(required_ids - recorded_ids):
        errors.append(f"reviewer revision request lacks a ledger row: {request_id}")
    return errors


def dependency_findings(codex_home: Path | None) -> tuple[list[str], list[str]]:
    if codex_home is None:
        codex_home = Path.home() / ".codex"
    skills = codex_home.expanduser().resolve() / "skills"
    errors: list[str] = []
    warnings: list[str] = []
    reviewer = skills / "academic-paper-reviewer"
    compiler = skills / "paper-compile-layout-qa"
    for name, folder in (
        ("academic-paper-reviewer", reviewer),
        ("paper-compile-layout-qa", compiler),
    ):
        if not (folder / "SKILL.md").is_file():
            errors.append(f"required skill is not installed: {name}")
    hard_contract_assets = (
        reviewer / "shared" / "sprint_contract.schema.json",
        reviewer / "shared" / "contracts" / "reviewer" / "full.json",
        reviewer / "shared" / "contracts" / "reviewer" / "methodology_focus.json",
        reviewer / "scripts" / "check_sprint_contract.py",
    )
    missing = [str(path) for path in hard_contract_assets if not path.is_file()]
    if reviewer.is_dir() and missing:
        warnings.append(
            "academic-paper-reviewer sprint-contract assets are incomplete; "
            "use five-role compatibility mode and do not claim machine-enforced "
            "sprint-contract review. Missing: " + "; ".join(missing)
        )
    return errors, warnings


def full_validation(state: dict[str, Any], codex_home: Path | None) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if state.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"unsupported schema_version: {state.get('schema_version')}")
    if state.get("stage") not in STAGES:
        errors.append(f"unknown stage: {state.get('stage')}")
    root = Path(state.get("project_root", ""))
    if not root.is_dir():
        errors.append(f"project_root is not a directory: {root}")
    for key in ("canonical_source", "bibliography"):
        value = state.get("artifacts", {}).get(key)
        if not value:
            errors.append(f"missing artifact mapping: {key}")
        elif not resolve_artifact(state, value).is_file():
            errors.append(f"artifact not found ({key}): {resolve_artifact(state, value)}")
    errors.extend(story_integrity_errors(state))
    errors.extend(pending_story_errors(state))
    errors.extend(pending_review_panel_errors(state))
    errors.extend(review_snapshot_errors(state))
    errors.extend(review_panel_integrity_errors(state))
    errors.extend(review_reports_integrity_errors(state))
    errors.extend(rereview_snapshot_errors(state))
    errors.extend(rereview_report_integrity_errors(state))
    dep_errors, dep_warnings = dependency_findings(codex_home)
    errors.extend(dep_errors)
    warnings.extend(dep_warnings)
    if state.get("stage") in TERMINAL_STAGES:
        source = resolve_artifact(state, state["artifacts"]["canonical_source"])
        bibliography = resolve_artifact(state, state["artifacts"]["bibliography"])
        pdf = resolve_artifact(state, state["artifacts"].get("rendered_pdf", ""))
        report = resolve_artifact(state, state["artifacts"]["submission_readiness"])
        readiness = state.get("readiness") or {}
        if readiness.get("status") != state.get("stage"):
            errors.append("terminal state does not match the recorded readiness status")
        if not report.is_file():
            errors.append("submission readiness report is missing after terminal signoff")
        elif sha256(report) != readiness.get("report_sha256"):
            errors.append("submission readiness report changed after terminal signoff")
        if not source.is_file():
            errors.append("canonical source is missing after terminal signoff")
        elif sha256(source) != readiness.get("canonical_source_sha256"):
            errors.append("canonical source changed after terminal signoff")
        if not bibliography.is_file():
            errors.append("bibliography is missing after terminal signoff")
        elif sha256(bibliography) != readiness.get("bibliography_sha256"):
            errors.append("bibliography changed after terminal signoff")
        if readiness.get("rendered_pdf_sha256") and not pdf.is_file():
            errors.append("rendered PDF is missing after terminal signoff")
        elif pdf.is_file() and sha256(pdf) != readiness.get("rendered_pdf_sha256"):
            errors.append("rendered PDF changed after terminal signoff")
        table_qa_value = state["artifacts"].get("table_qa")
        table_qa = (
            resolve_artifact(state, table_qa_value)
            if table_qa_value
            else Path(state["workflow_dir"]) / "TABLE_QA.md"
        )
        expected_table_qa = readiness.get("table_qa_sha256")
        if expected_table_qa and not table_qa.is_file():
            errors.append("TABLE_QA.md is missing after terminal signoff")
        elif expected_table_qa and sha256(table_qa) != expected_table_qa:
            errors.append("TABLE_QA.md changed after terminal signoff")
        for artifact_key, readiness_key, label in (
            ("tex_table_audit", "tex_table_audit_sha256", "TeX table audit JSON"),
            ("pdf_font_audit", "pdf_font_audit_sha256", "PDF font audit JSON"),
        ):
            expected = readiness.get(readiness_key)
            artifact = resolve_artifact(state, state["artifacts"].get(artifact_key, ""))
            if expected and not artifact.is_file():
                errors.append(f"{label} is missing after terminal signoff")
            elif expected and sha256(artifact) != expected:
                errors.append(f"{label} changed after terminal signoff")
        if state.get("stage") == "SUBMISSION_READY":
            if not pdf.is_file():
                errors.append("SUBMISSION_READY requires a rendered PDF")
            if source.is_file() and bibliography.is_file():
                errors.extend(unresolved_marker_errors(source, bibliography))
            if pdf.is_file():
                errors.extend(table_qa_errors(state))
    return {
        "ok": not errors,
        "stage": state.get("stage"),
        "errors": errors,
        "warnings": warnings,
    }


def command_init(args: argparse.Namespace) -> int:
    root = args.project_root.expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"project root not found: {root}")
    workflow_dir = (
        args.state_dir.expanduser().resolve()
        if args.state_dir
        else root / ".paper-workflow"
    )
    state_file = workflow_dir / STATE_FILE
    if state_file.exists():
        raise FileExistsError(f"workflow already initialized: {state_file}")
    source = resolve_input_path(args.source, root)
    bibliography = resolve_input_path(args.bibliography, root)
    pdf = resolve_input_path(args.pdf, root) if args.pdf else None
    for label, artifact in (("source", source), ("bibliography", bibliography)):
        if not artifact.is_file():
            raise FileNotFoundError(f"{label} not found: {artifact}")
    if source.suffix.lower() in LATEX_SOURCE_SUFFIXES and not (args.build_command or "").strip():
        raise ValueError("LaTeX workflows require --build-command with the repository-native command")
    if workflow_dir.exists() and any(workflow_dir.iterdir()):
        raise FileExistsError(f"workflow directory is not empty: {workflow_dir}")
    workflow_dir.mkdir(parents=True, exist_ok=True)
    artifacts = {
        "canonical_source": portable_path(source, root),
        "bibliography": portable_path(bibliography, root),
        "rendered_pdf": portable_path(pdf, root) if pdf else "",
        "dependency_manifest": (
            portable_path(resolve_input_path(args.dependency_manifest, root), root)
            if args.dependency_manifest
            else ""
        ),
        "story_packet": portable_path(workflow_dir / "STORY_APPROVAL_PACKET.md", root),
        "review_panel": portable_path(workflow_dir / "REVIEW_PANEL.md", root),
        "claim_evidence_matrix": portable_path(workflow_dir / "CLAIM_EVIDENCE_MATRIX.md", root),
        "terminology_ledger": portable_path(workflow_dir / "TERMINOLOGY_LEDGER.md", root),
        "experiment_requests": portable_path(workflow_dir / "EXPERIMENT_REQUESTS.md", root),
        "revision_ledger": portable_path(workflow_dir / "REVISION_LEDGER.md", root),
        "build_receipt": portable_path(workflow_dir / "BUILD_RECEIPT.md", root),
        "table_qa": portable_path(workflow_dir / "TABLE_QA.md", root),
        "tex_table_audit": portable_path(workflow_dir / "tex_table_audit.json", root),
        "pdf_font_audit": portable_path(workflow_dir / "pdf_font_audit.json", root),
        "submission_readiness": portable_path(workflow_dir / "SUBMISSION_READINESS.md", root),
        "reviews_dir": portable_path(workflow_dir / "reviews", root),
    }
    state = {
        "schema_version": SCHEMA_VERSION,
        "project_root": str(root),
        "workflow_dir": str(workflow_dir),
        "stage": "INTAKE",
        "last_passed_gate": None,
        "venue": {
            "name": args.venue,
            "year": args.year,
            "track": args.track,
            "mode": args.mode,
        },
        "build_command": args.build_command or "",
        "artifacts": artifacts,
        "approvals": {
            "story": {"status": "PENDING"},
            "review_panel": {"status": "PENDING"},
        },
        "review_snapshot": None,
        "review_reports_snapshot": None,
        "rereview_snapshot": None,
        "readiness": None,
        "pending_experiment_request_ids": [],
        "pending_revision_request_ids": [],
        "story_cycle": 1,
        "history": [],
    }
    record(state, "initialized")
    write_new(workflow_dir / "STORY_APPROVAL_PACKET.md", STORY_TEMPLATE)
    write_new(workflow_dir / "REVIEW_PANEL.md", PANEL_TEMPLATE)
    write_new(workflow_dir / "CLAIM_EVIDENCE_MATRIX.md", CLAIM_TEMPLATE)
    write_new(workflow_dir / "TERMINOLOGY_LEDGER.md", TERM_TEMPLATE)
    write_new(workflow_dir / "EXPERIMENT_REQUESTS.md", EXPERIMENT_TEMPLATE)
    write_new(workflow_dir / "REVISION_LEDGER.md", REVISION_TEMPLATE)
    write_new(workflow_dir / "BUILD_RECEIPT.md", BUILD_RECEIPT_TEMPLATE)
    write_new(workflow_dir / "TABLE_QA.md", TABLE_QA_TEMPLATE)
    write_new(workflow_dir / "SUBMISSION_READINESS.md", READINESS_TEMPLATE)
    (workflow_dir / "reviews").mkdir(exist_ok=True)
    save_state(state_file, state)
    print(state_file)
    return 0


def command_submit_story(args: argparse.Namespace) -> int:
    path, state = load_state(args.state)
    if state.get("stage") not in {"INTAKE", "WAITING_FOR_STORY_APPROVAL"}:
        raise ValueError("submit-story is allowed only from INTAKE or WAITING_FOR_STORY_APPROVAL")
    packet = resolve_artifact(state, state["artifacts"]["story_packet"])
    errors = validate_packet(packet, REQUIRED_STORY_SECTIONS)
    if errors:
        raise ValueError("; ".join(errors))
    packet_hash = sha256(packet)
    state["stage"] = "WAITING_FOR_STORY_APPROVAL"
    state["approvals"]["story"] = {
        "status": "PENDING",
        "proposed_sha256": packet_hash,
        "submitted_at": utc_now(),
    }
    state["last_passed_gate"] = "G0_INPUT_READY"
    record(state, "story_submitted", packet_sha256=packet_hash)
    save_state(path, state)
    print(json.dumps({"stage": state["stage"], "packet_sha256": packet_hash}, indent=2))
    return 0


def command_approve_story(args: argparse.Namespace) -> int:
    path, state = load_state(args.state)
    if state.get("stage") != "WAITING_FOR_STORY_APPROVAL":
        raise ValueError("story approval is allowed only while waiting for approval")
    pending = state["approvals"]["story"]
    packet = resolve_artifact(state, state["artifacts"]["story_packet"])
    current_hash = sha256(packet)
    if current_hash != pending.get("proposed_sha256"):
        raise ValueError("story packet changed after it was submitted for approval")
    if not args.evidence.strip():
        raise ValueError("verbatim user/PI approval evidence is required")
    approver = validate_human_approver(args.by)
    state["approvals"]["story"] = {
        "status": "APPROVED",
        "by": approver,
        "approved_at": utc_now(),
        "evidence": args.evidence.strip(),
        "packet_sha256": current_hash,
    }
    state["stage"] = "STORY_LOCKED"
    state["last_passed_gate"] = "G1_STORY_LOCKED"
    record(state, "story_approved", by=approver, packet_sha256=current_hash)
    save_state(path, state)
    print(json.dumps({"stage": state["stage"], "packet_sha256": current_hash}, indent=2))
    return 0


def command_invalidate_story(args: argparse.Namespace) -> int:
    path, state = load_state(args.state)
    if state.get("stage") not in POST_STORY_STAGES:
        raise ValueError("invalidate-story is allowed only after the story has been approved")
    reason = args.reason.strip()
    if not reason:
        raise ValueError("invalidate-story requires a non-empty reason")
    workflow_dir = Path(state["workflow_dir"]).resolve()
    cycle = int(state.get("story_cycle", 1))
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    archive = workflow_dir / "archive" / f"story-cycle-{cycle:03d}-{stamp}"
    archive.mkdir(parents=True, exist_ok=False)
    shutil.copy2(path, archive / STATE_FILE)
    for name in (
        "STORY_APPROVAL_PACKET.md",
        "REVIEW_PANEL.md",
        "CLAIM_EVIDENCE_MATRIX.md",
        "TERMINOLOGY_LEDGER.md",
        "EXPERIMENT_REQUESTS.md",
        "REVISION_LEDGER.md",
        "BUILD_RECEIPT.md",
        "TABLE_QA.md",
        "SUBMISSION_READINESS.md",
        "tex_table_audit.json",
        "pdf_font_audit.json",
    ):
        artifact = workflow_dir / name
        if artifact.is_file():
            shutil.copy2(artifact, archive / name)
    reviews = workflow_dir / "reviews"
    if reviews.is_dir():
        shutil.move(str(reviews), str(archive / "reviews"))
    reviews.mkdir(exist_ok=False)
    (workflow_dir / "REVIEW_PANEL.md").write_text(PANEL_TEMPLATE, encoding="utf-8")
    (workflow_dir / "CLAIM_EVIDENCE_MATRIX.md").write_text(CLAIM_TEMPLATE, encoding="utf-8")
    (workflow_dir / "TERMINOLOGY_LEDGER.md").write_text(TERM_TEMPLATE, encoding="utf-8")
    (workflow_dir / "EXPERIMENT_REQUESTS.md").write_text(
        EXPERIMENT_TEMPLATE, encoding="utf-8"
    )
    (workflow_dir / "REVISION_LEDGER.md").write_text(REVISION_TEMPLATE, encoding="utf-8")
    (workflow_dir / "BUILD_RECEIPT.md").write_text(BUILD_RECEIPT_TEMPLATE, encoding="utf-8")
    (workflow_dir / "TABLE_QA.md").write_text(TABLE_QA_TEMPLATE, encoding="utf-8")
    (workflow_dir / "SUBMISSION_READINESS.md").write_text(
        READINESS_TEMPLATE, encoding="utf-8"
    )
    for name in ("tex_table_audit.json", "pdf_font_audit.json"):
        active_audit = workflow_dir / name
        if active_audit.is_file():
            active_audit.unlink()
    state["stage"] = "WAITING_FOR_STORY_APPROVAL"
    state["approvals"]["story"] = {"status": "PENDING", "invalidated_at": utc_now()}
    state["approvals"]["review_panel"] = {"status": "PENDING", "invalidated_at": utc_now()}
    state["review_snapshot"] = None
    state["review_reports_snapshot"] = None
    state["rereview_snapshot"] = None
    state["readiness"] = None
    state["pending_experiment_request_ids"] = []
    state["pending_revision_request_ids"] = []
    state["story_cycle"] = cycle + 1
    state["last_passed_gate"] = None
    record(
        state,
        "story_invalidated",
        reason=reason,
        archived_cycle=cycle,
        archive_path=portable_path(archive, Path(state["project_root"])),
    )
    save_state(path, state)
    print(
        json.dumps(
            {"stage": state["stage"], "reason": reason, "archive": str(archive)},
            indent=2,
        )
    )
    return 0


def command_advance(args: argparse.Namespace) -> int:
    path, state = load_state(args.state)
    current = state.get("stage")
    target = args.to
    if target not in ORDINARY_TRANSITIONS.get(current, set()):
        raise ValueError(f"transition not allowed: {current} -> {target}")
    story_errors = story_integrity_errors(state)
    if story_errors:
        raise ValueError("; ".join(story_errors))
    snapshot_errors = (
        review_snapshot_errors(state)
        + review_panel_integrity_errors(state)
        + review_reports_integrity_errors(state)
        + rereview_snapshot_errors(state)
        + rereview_report_integrity_errors(state)
    )
    if snapshot_errors:
        raise ValueError("; ".join(snapshot_errors))
    if target == "REVIEWABLE":
        for key in ("canonical_source", "bibliography", "rendered_pdf"):
            value = state["artifacts"].get(key, "")
            artifact = resolve_artifact(state, value) if value else None
            if artifact is None or not artifact.is_file():
                raise ValueError(f"REVIEWABLE requires existing artifact: {key}")
        errors = build_receipt_errors(state)
        if errors:
            raise ValueError("; ".join(errors))
    if target == "WAITING_FOR_REVIEW_PANEL_APPROVAL":
        panel = resolve_artifact(state, state["artifacts"]["review_panel"])
        errors = review_panel_errors(panel) + build_receipt_errors(state)
        if errors:
            raise ValueError("; ".join(errors))
        if review_panel_type(panel) != "CUSTOM":
            raise ValueError(
                "STANDARD_FIVE_ROLE panels must be frozen directly with "
                "'advance --to REVIEWING'; manual approval is only for CUSTOM panels"
            )
        source = resolve_artifact(state, state["artifacts"]["canonical_source"])
        bibliography = resolve_artifact(state, state["artifacts"]["bibliography"])
        pdf = resolve_artifact(state, state["artifacts"]["rendered_pdf"])
        build_receipt = resolve_artifact(state, state["artifacts"]["build_receipt"])
        state["approvals"]["review_panel"] = {
            "status": "PENDING",
            "configuration_type": "CUSTOM",
            "proposed_sha256": sha256(panel),
            "proposed_source_sha256": sha256(source),
            "proposed_bibliography_sha256": sha256(bibliography),
            "proposed_pdf_sha256": sha256(pdf),
            "proposed_build_receipt_sha256": sha256(build_receipt),
            "submission_dependency_hashes": dependency_hashes(state),
            "submitted_at": utc_now(),
        }
    if target == "REVIEWING":
        panel = resolve_artifact(state, state["artifacts"]["review_panel"])
        errors = review_panel_errors(panel) + build_receipt_errors(state)
        if errors:
            raise ValueError("; ".join(errors))
        if review_panel_type(panel) != "STANDARD_FIVE_ROLE":
            raise ValueError(
                "CUSTOM review panels require explicit user/PI approval via "
                "WAITING_FOR_REVIEW_PANEL_APPROVAL"
            )
        freeze_review_snapshot(
            state,
            panel,
            {
                "status": "STANDARD_AUTO_FROZEN",
                "configuration_type": "STANDARD_FIVE_ROLE",
                "policy": "standard-five-role",
            },
        )
        record(state, "standard_review_panel_and_snapshot_frozen")
    if target == "TRIAGE":
        errors = review_output_errors(state)
        if errors:
            raise ValueError("; ".join(errors))
        reviews_dir = resolve_artifact(state, state["artifacts"]["reviews_dir"])
        panel = resolve_artifact(state, state["artifacts"]["review_panel"])
        specs, _ = panel_report_specs(panel)
        state["review_reports_snapshot"] = {
            name: sha256(reviews_dir / name)
            for name in tuple(filename for _, filename in specs) + ("EDITORIAL_DECISION.md",)
        }
    if target == "REVISING":
        ledger = resolve_artifact(state, state["artifacts"]["revision_ledger"])
        errors = revision_ledger_errors(ledger, requested_revision_ids(state))
        if errors:
            raise ValueError("; ".join(errors))
        errors = experiment_decision_errors(state, require_closed=False)
        if errors:
            raise ValueError("; ".join(errors))
    if target == "RE_REVIEW":
        errors = experiment_decision_errors(state, require_closed=True)
        ledger = resolve_artifact(state, state["artifacts"]["revision_ledger"])
        errors.extend(
            revision_ledger_errors(ledger, requested_revision_ids(state), require_closed=True)
        )
        if errors:
            raise ValueError("; ".join(errors))
        source = resolve_artifact(state, state["artifacts"]["canonical_source"])
        bibliography = resolve_artifact(state, state["artifacts"]["bibliography"])
        pdf = resolve_artifact(state, state["artifacts"]["rendered_pdf"])
        if not source.is_file() or not bibliography.is_file() or not pdf.is_file():
            raise ValueError("re-review requires final source, bibliography, and rendered PDF")
        errors = build_receipt_errors(state)
        if errors:
            raise ValueError("; ".join(errors))
        build_receipt = resolve_artifact(state, state["artifacts"]["build_receipt"])
        state["rereview_snapshot"] = {
            "frozen_at": utc_now(),
            "canonical_source_sha256": sha256(source),
            "bibliography_sha256": sha256(bibliography),
            "rendered_pdf_sha256": sha256(pdf),
            "build_receipt_sha256": sha256(build_receipt),
            "revision_ledger_sha256": sha256(ledger),
            "experiment_requests_sha256": sha256(
                resolve_artifact(state, state["artifacts"]["experiment_requests"])
            ),
            "submission_dependency_hashes": dependency_hashes(state),
        }
    if target == "SUBMISSION_QA":
        new_requests = rereview_experiment_ids(state)
        if new_requests:
            pending = set(state.get("pending_experiment_request_ids", [])) | new_requests
            state["pending_experiment_request_ids"] = sorted(pending)
            record(state, "rereview_experiment_requests_captured", request_ids=sorted(new_requests))
            save_state(path, state)
        new_revisions = rereview_revision_ids(state)
        if new_revisions:
            pending = set(state.get("pending_revision_request_ids", [])) | new_revisions
            state["pending_revision_request_ids"] = sorted(pending)
            record(state, "rereview_revision_requests_captured", request_ids=sorted(new_revisions))
            save_state(path, state)
        errors = rereview_output_errors(state)
        if errors:
            raise ValueError("; ".join(errors))
        rereview = resolve_artifact(state, state["artifacts"]["reviews_dir"]) / "RE_REVIEW.md"
        state["rereview_snapshot"]["report_sha256"] = sha256(rereview)
    state["stage"] = target
    if target in PASSED_GATE_BY_TARGET:
        state["last_passed_gate"] = PASSED_GATE_BY_TARGET[target]
    record(state, "stage_advanced", previous=current, current=target)
    save_state(path, state)
    print(json.dumps({"stage": target}, indent=2))
    return 0


def command_approve_review_panel(args: argparse.Namespace) -> int:
    path, state = load_state(args.state)
    if state.get("stage") != "WAITING_FOR_REVIEW_PANEL_APPROVAL":
        raise ValueError("review panel approval is allowed only while waiting")
    if story_integrity_errors(state):
        raise ValueError("story approval is invalid")
    pending = state["approvals"]["review_panel"]
    pending_errors = pending_review_panel_errors(state)
    if pending_errors:
        raise ValueError("; ".join(pending_errors))
    panel = resolve_artifact(state, state["artifacts"]["review_panel"])
    errors = review_panel_errors(panel)
    if errors:
        raise ValueError("; ".join(errors))
    if review_panel_type(panel) != "CUSTOM":
        raise ValueError("manual review-panel approval is allowed only for CUSTOM panels")
    panel_hash = sha256(panel)
    if panel_hash != pending.get("proposed_sha256"):
        raise ValueError("review panel changed after submission for approval")
    source = resolve_artifact(state, state["artifacts"]["canonical_source"])
    bibliography = resolve_artifact(state, state["artifacts"]["bibliography"])
    pdf = resolve_artifact(state, state["artifacts"]["rendered_pdf"])
    build_receipt = resolve_artifact(state, state["artifacts"]["build_receipt"])
    if not source.is_file() or not bibliography.is_file() or not pdf.is_file():
        raise ValueError("review snapshot requires existing source, bibliography, and PDF")
    if sha256(source) != pending.get("proposed_source_sha256"):
        raise ValueError("canonical source changed after review panel submission")
    if sha256(bibliography) != pending.get("proposed_bibliography_sha256"):
        raise ValueError("bibliography changed after review panel submission")
    if sha256(pdf) != pending.get("proposed_pdf_sha256"):
        raise ValueError("rendered PDF changed after review panel submission")
    if sha256(build_receipt) != pending.get("proposed_build_receipt_sha256"):
        raise ValueError("build receipt changed after review panel submission")
    if not args.evidence.strip():
        raise ValueError("verbatim user/PI review-panel approval evidence is required")
    approver = validate_human_approver(args.by)
    freeze_review_snapshot(
        state,
        panel,
        {
            "status": "APPROVED",
            "configuration_type": "CUSTOM",
            "by": approver,
            "approved_at": utc_now(),
            "evidence": args.evidence.strip(),
        },
    )
    state["stage"] = "REVIEWING"
    record(state, "review_panel_approved_and_snapshot_frozen", by=approver)
    save_state(path, state)
    print(json.dumps({"stage": state["stage"], "snapshot": state["review_snapshot"]}, indent=2))
    return 0


def command_set_readiness(args: argparse.Namespace) -> int:
    path, state = load_state(args.state)
    if state.get("stage") != "SUBMISSION_QA":
        raise ValueError("readiness can be set only from SUBMISSION_QA")
    integrity_errors = (
        story_integrity_errors(state)
        + review_panel_integrity_errors(state)
        + review_reports_integrity_errors(state)
        + rereview_snapshot_errors(state)
        + rereview_report_integrity_errors(state)
    )
    if integrity_errors:
        raise ValueError("; ".join(integrity_errors))
    status = args.status
    report = resolve_artifact(state, state["artifacts"]["submission_readiness"])
    if not report.is_file():
        raise ValueError("submission readiness report is missing")
    report_text = report.read_text(encoding="utf-8")
    if bullet_field_values(report_text, "Overall") != [status]:
        raise ValueError(f"readiness report does not declare {status}")
    source = resolve_artifact(state, state["artifacts"]["canonical_source"])
    bibliography = resolve_artifact(state, state["artifacts"]["bibliography"])
    pdf = resolve_artifact(state, state["artifacts"]["rendered_pdf"])
    table_qa_value = state["artifacts"].get("table_qa")
    table_qa = (
        resolve_artifact(state, table_qa_value)
        if table_qa_value
        else Path(state["workflow_dir"]) / "TABLE_QA.md"
    )
    if not source.is_file() or not bibliography.is_file() or not pdf.is_file():
        raise ValueError("readiness sign-off requires exact source, bibliography, and rendered PDF")
    exact_hash_fields = (
        ("Exact source revision", source, "source"),
        ("Exact bibliography path/hash", bibliography, "bibliography"),
        ("Exact PDF path/hash", pdf, "PDF"),
    )
    for label, artifact, artifact_name in exact_hash_fields:
        if exact_pdf_hash_in(report_text, label) != sha256(artifact).lower():
            raise ValueError(
                f"submission readiness report does not identify the exact final {artifact_name} SHA-256"
            )
    evidence_labels = (
        "Build command/result",
        "Final rendered-PDF inspection evidence",
        "Remaining P0/P1 blockers",
        "User-supplied or external blockers",
        "Residual non-blocking risks",
        "Recommended next action",
    )
    for label in evidence_labels:
        values = bullet_field_values(report_text, label)
        if len(values) != 1 or not values[0] or unresolved_evidence(values[0]):
            raise ValueError(f"readiness report lacks completed '{label}' evidence")
    verdicts: dict[str, str] = {}
    for label in ("Scientific readiness", "Manuscript readiness", "Submission-package readiness"):
        values = bullet_field_values(report_text, label)
        if len(values) != 1 or values[0] not in {"PASS", "FAIL"}:
            raise ValueError(f"readiness report lacks an explicit PASS/FAIL '{label}' verdict")
        verdicts[label] = values[0]
    blocker_values = bullet_field_values(report_text, "Remaining P0/P1 blockers")
    external_values = bullet_field_values(report_text, "User-supplied or external blockers")
    normalized_none = {"NONE", "NO", "0", "N/A", "NOT APPLICABLE"}
    no_p01_blockers = (
        len(blocker_values) == 1 and blocker_values[0].strip().upper().rstrip(".") in normalized_none
    )
    no_external_blockers = (
        len(external_values) == 1 and external_values[0].strip().upper().rstrip(".") in normalized_none
    )
    if status == "SUBMISSION_READY":
        if any(value != "PASS" for value in verdicts.values()):
            raise ValueError("SUBMISSION_READY requires all three readiness verdicts to PASS")
        if not no_p01_blockers or not no_external_blockers:
            raise ValueError(
                "SUBMISSION_READY requires Remaining P0/P1 blockers and "
                "User-supplied or external blockers to be NONE"
            )
        table_errors = table_qa_errors(state)
        if table_errors:
            raise ValueError("; ".join(table_errors))
        marker_errors = unresolved_marker_errors(source, bibliography)
        if marker_errors:
            raise ValueError("; ".join(marker_errors))
    elif status == "CONDITIONALLY_READY":
        expected = {
            "Scientific readiness": "PASS",
            "Manuscript readiness": "PASS",
            "Submission-package readiness": "FAIL",
        }
        if verdicts != expected:
            raise ValueError(
                "CONDITIONALLY_READY requires scientific/manuscript PASS and "
                "submission-package FAIL"
            )
        if not no_p01_blockers:
            raise ValueError("CONDITIONALLY_READY requires no remaining scientific/manuscript P0/P1 blockers")
        if no_external_blockers:
            raise ValueError("CONDITIONALLY_READY requires a concrete user-supplied or external blocker")
    else:
        if all(value == "PASS" for value in verdicts.values()):
            raise ValueError("NOT_READY must identify at least one failed readiness dimension")
        if no_p01_blockers and no_external_blockers:
            raise ValueError(
                "NOT_READY requires at least one concrete remaining P0/P1 blocker "
                "or user-supplied/external blocker"
            )
    state["stage"] = status
    state["last_passed_gate"] = "G8_PACKAGE_SIGNOFF"
    state["readiness"] = {
        "status": status,
        "set_at": utc_now(),
        "report_sha256": sha256(report),
        "table_qa_sha256": sha256(table_qa) if table_qa.is_file() else None,
        "tex_table_audit_sha256": sha256(
            resolve_artifact(state, state["artifacts"]["tex_table_audit"])
        )
        if resolve_artifact(state, state["artifacts"]["tex_table_audit"]).is_file()
        else None,
        "pdf_font_audit_sha256": sha256(
            resolve_artifact(state, state["artifacts"]["pdf_font_audit"])
        )
        if resolve_artifact(state, state["artifacts"]["pdf_font_audit"]).is_file()
        else None,
        "canonical_source_sha256": sha256(source),
        "bibliography_sha256": sha256(bibliography),
        "rendered_pdf_sha256": sha256(pdf) if pdf.is_file() else None,
    }
    record(state, "readiness_set", status=status)
    save_state(path, state)
    print(json.dumps(state["readiness"], indent=2))
    return 0


def command_reopen_revision(args: argparse.Namespace) -> int:
    path, state = load_state(args.state)
    if state.get("stage") not in POST_REREVIEW_SNAPSHOT_STAGES:
        raise ValueError("reopen-revision is allowed only from RE_REVIEW or a later stage")
    reason = args.reason.strip()
    if not reason:
        raise ValueError("reopen-revision requires a non-empty reason")
    new_requests = rereview_experiment_ids(state)
    if new_requests:
        pending = set(state.get("pending_experiment_request_ids", [])) | new_requests
        state["pending_experiment_request_ids"] = sorted(pending)
    new_revisions = rereview_revision_ids(state)
    if new_revisions:
        pending = set(state.get("pending_revision_request_ids", [])) | new_revisions
        state["pending_revision_request_ids"] = sorted(pending)
    state["stage"] = "REVISING"
    state["last_passed_gate"] = "G5_REVISION_PLAN_ACCEPTED"
    state["rereview_snapshot"] = None
    state["readiness"] = None
    record(
        state,
        "revision_reopened_after_final_snapshot",
        reason=reason,
        captured_experiment_requests=sorted(new_requests),
        captured_revision_requests=sorted(new_revisions),
    )
    save_state(path, state)
    print(json.dumps({"stage": state["stage"], "reason": reason}, indent=2))
    return 0


def command_validate(args: argparse.Namespace) -> int:
    _, state = load_state(args.state)
    result = full_validation(state, args.codex_home)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


def command_fingerprint(args: argparse.Namespace) -> int:
    _, state = load_state(args.state)
    manifest_value = state.get("artifacts", {}).get("dependency_manifest", "")
    manifest = resolve_artifact(state, manifest_value) if manifest_value else None
    payload = {
        "canonical_source_sha256": sha256(
            resolve_artifact(state, state["artifacts"]["canonical_source"])
        ),
        "bibliography_sha256": sha256(
            resolve_artifact(state, state["artifacts"]["bibliography"])
        ),
        "rendered_pdf_sha256": sha256(
            resolve_artifact(state, state["artifacts"]["rendered_pdf"])
        ),
        "dependency_bundle_sha256": dependency_bundle_sha256(state),
        "dependency_manifest_sha256": sha256(manifest) if manifest and manifest.is_file() else None,
        "submission_dependencies": dependency_hashes(state),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def command_check_build(args: argparse.Namespace) -> int:
    _, state = load_state(args.state)
    errors = build_receipt_errors(state)
    payload = {"ok": not errors, "errors": errors}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


def command_status(args: argparse.Namespace) -> int:
    path, state = load_state(args.state)
    result = {
        "state_file": str(path),
        "stage": state.get("stage"),
        "last_passed_gate": state.get("last_passed_gate"),
        "story_approval": state.get("approvals", {}).get("story"),
        "review_panel_approval": state.get("approvals", {}).get("review_panel"),
        "review_snapshot": state.get("review_snapshot"),
        "rereview_snapshot": state.get("rereview_snapshot"),
        "readiness": state.get("readiness"),
        "allowed_next_actions": allowed_next_actions(state),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def allowed_next_actions(state: dict[str, Any]) -> list[str]:
    stage = state.get("stage")
    actions = [f"advance --to {target}" for target in sorted(ORDINARY_TRANSITIONS.get(stage, set()))]
    if stage == "INTAKE":
        actions.append("submit-story")
    elif stage == "WAITING_FOR_STORY_APPROVAL":
        actions.extend(("approve-story", "submit-story"))
    elif stage == "WAITING_FOR_REVIEW_PANEL_APPROVAL":
        actions.append("approve-review-panel")
    elif stage == "SUBMISSION_QA":
        actions.append("set-readiness")
    if stage in POST_REREVIEW_SNAPSHOT_STAGES:
        actions.append("reopen-revision")
    if stage in POST_STORY_STAGES:
        actions.append("invalidate-story")
    return actions


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init", help="initialize a durable workflow workspace")
    init.add_argument("--project-root", type=Path, required=True)
    init.add_argument("--state-dir", type=Path)
    init.add_argument("--venue", required=True)
    init.add_argument("--year", required=True)
    init.add_argument("--track", required=True)
    init.add_argument("--mode", choices=("review", "final", "preprint"), required=True)
    init.add_argument("--source", type=Path, required=True)
    init.add_argument("--bibliography", type=Path, required=True)
    init.add_argument("--pdf", type=Path)
    init.add_argument("--dependency-manifest", type=Path)
    init.add_argument("--build-command")
    init.set_defaults(func=command_init)

    for name, func in (
        ("submit-story", command_submit_story),
        ("status", command_status),
        ("validate", command_validate),
        ("fingerprint", command_fingerprint),
        ("check-build", command_check_build),
    ):
        command = subparsers.add_parser(name)
        command.add_argument("--state", required=True)
        if name == "validate":
            command.add_argument("--codex-home", type=Path)
        command.set_defaults(func=func)

    approve_story = subparsers.add_parser("approve-story")
    approve_story.add_argument("--state", required=True)
    approve_story.add_argument("--by", required=True)
    approve_story.add_argument("--evidence", required=True)
    approve_story.set_defaults(func=command_approve_story)

    invalidate = subparsers.add_parser("invalidate-story")
    invalidate.add_argument("--state", required=True)
    invalidate.add_argument("--reason", required=True)
    invalidate.set_defaults(func=command_invalidate_story)

    advance = subparsers.add_parser("advance")
    advance.add_argument("--state", required=True)
    advance.add_argument("--to", choices=STAGES, required=True)
    advance.set_defaults(func=command_advance)

    approve_panel = subparsers.add_parser("approve-review-panel")
    approve_panel.add_argument("--state", required=True)
    approve_panel.add_argument("--by", required=True)
    approve_panel.add_argument("--evidence", required=True)
    approve_panel.set_defaults(func=command_approve_review_panel)

    reopen = subparsers.add_parser("reopen-revision")
    reopen.add_argument("--state", required=True)
    reopen.add_argument("--reason", required=True)
    reopen.set_defaults(func=command_reopen_revision)

    readiness = subparsers.add_parser("set-readiness")
    readiness.add_argument("--state", required=True)
    readiness.add_argument(
        "--status",
        choices=("SUBMISSION_READY", "CONDITIONALLY_READY", "NOT_READY"),
        required=True,
    )
    readiness.set_defaults(func=command_set_readiness)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (FileNotFoundError, FileExistsError, KeyError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
