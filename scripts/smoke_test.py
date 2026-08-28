#!/usr/bin/env python3
"""Read-only integration smoke test for a real paper project."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
WORKFLOW_CTL = HERE / "workflow_ctl.py"


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, text=True, capture_output=True, check=False)


def require_file(path: Path, label: str) -> Path:
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"{label} not found: {resolved}")
    return resolved


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pdf_page_count(path: Path) -> int:
    try:
        from pypdf import PdfReader

        return len(PdfReader(str(path)).pages)
    except ImportError:
        pass
    pdfinfo = shutil.which("pdfinfo")
    if not pdfinfo:
        raise FileNotFoundError("pdfinfo is required for the real-project smoke test")
    result = run([pdfinfo, str(path)])
    if result.returncode != 0:
        raise RuntimeError(f"pdfinfo failed: {result.stderr.strip()}")
    for line in result.stdout.splitlines():
        if line.startswith("Pages:"):
            return int(line.split(":", 1)[1].strip())
    raise RuntimeError("pdfinfo did not report a page count")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--bibliography", type=Path, required=True)
    parser.add_argument("--pdf", type=Path, required=True)
    parser.add_argument("--main-tex", type=Path, required=True)
    parser.add_argument("--build-script", type=Path, required=True)
    parser.add_argument("--venue-profile", type=Path, required=True)
    parser.add_argument("--venue", required=True)
    parser.add_argument("--year", required=True)
    parser.add_argument("--track", required=True)
    parser.add_argument("--mode", choices=("review", "final", "preprint"), required=True)
    parser.add_argument("--codex-home", type=Path, default=Path.home() / ".codex")
    parser.add_argument("--dpi", type=int, default=72)
    args = parser.parse_args()

    root = args.project_root.expanduser().resolve()
    if not root.is_dir():
        parser.error(f"project root not found: {root}")

    def project_path(value: Path) -> Path:
        return value.expanduser().resolve() if value.is_absolute() else (root / value).resolve()

    source = require_file(project_path(args.source), "source")
    bibliography = require_file(project_path(args.bibliography), "bibliography")
    pdf = require_file(project_path(args.pdf), "PDF")
    main_tex = require_file(project_path(args.main_tex), "main TeX") if args.main_tex else None
    build_script = require_file(project_path(args.build_script), "build script") if args.build_script else None
    venue_profile = require_file(project_path(args.venue_profile), "venue profile")
    if source != main_tex:
        parser.error("real LaTeX smoke requires --source and --main-tex to identify the same canonical file")
    diff_script = (
        args.codex_home.expanduser().resolve()
        / "skills"
        / "paper-compile-layout-qa"
        / "scripts"
        / "pdf_render_diff.py"
    )
    require_file(diff_script, "paper-compile-layout-qa render-diff script")
    format_audit_script = diff_script.with_name("conference_format_audit.py")
    require_file(format_audit_script, "paper-compile-layout-qa conference-format audit script")

    results: dict[str, object] = {}
    build_pdf_exists = False
    with tempfile.TemporaryDirectory(prefix="paper_orchestrator_smoke_") as temporary:
        temp = Path(temporary)
        build_out = temp / "build"
        comparison_pdf = build_out / f"{main_tex.stem}.pdf"
        dependency_manifest = build_out / f"{main_tex.stem}.mk"
        build_command = (
            f"powershell -File {build_script} -MainTex {main_tex} -OutDir {build_out}"
        )
        init = run(
            [
                sys.executable,
                str(WORKFLOW_CTL),
                "init",
                "--project-root",
                str(root),
                "--state-dir",
                str(temp / "state"),
                "--venue",
                args.venue,
                "--year",
                args.year,
                "--track",
                args.track,
                "--mode",
                args.mode,
                "--source",
                str(source),
                "--bibliography",
                str(bibliography),
                "--pdf",
                str(comparison_pdf),
                "--dependency-manifest",
                str(dependency_manifest),
                "--venue-profile",
                str(venue_profile),
                "--format-audit",
                str(temp / "state" / "format-audit.json"),
                "--build-command",
                build_command,
            ]
        )
        results["init"] = {
            "returncode": init.returncode,
            "stdout": init.stdout.strip(),
            "stderr": init.stderr.strip(),
        }
        if init.returncode != 0:
            print(json.dumps(results, ensure_ascii=False, indent=2))
            return 1

        validate = run(
            [
                sys.executable,
                str(WORKFLOW_CTL),
                "validate",
                "--state",
                str(temp / "state"),
                "--codex-home",
                str(args.codex_home.expanduser().resolve()),
            ]
        )
        try:
            validation_payload = json.loads(validate.stdout)
        except json.JSONDecodeError:
            validation_payload = {"raw_stdout": validate.stdout.strip()}
        results["preflight"] = {
            "returncode": validate.returncode,
            "result": validation_payload,
            "stderr": validate.stderr.strip(),
        }

        powershell = shutil.which("powershell") or shutil.which("pwsh")
        if not powershell:
            parser.error("PowerShell was not found for the repository build script")
        build = run(
            [
                powershell,
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(build_script),
                "-MainTex",
                str(main_tex),
                "-OutDir",
                str(build_out),
            ]
        )
        build_pdf_exists = comparison_pdf.is_file()
        manifest_exists = dependency_manifest.is_file()
        results["repository_build"] = {
            "returncode": build.returncode,
            "pdf_exists": build_pdf_exists,
            "dependency_manifest_exists": manifest_exists,
            "stdout": build.stdout.strip(),
            "stderr": build.stderr.strip(),
        }

        diff = run(
            [
                sys.executable,
                str(diff_script),
                str(pdf),
                str(comparison_pdf),
                "--dpi",
                str(args.dpi),
                "--output-dir",
                str(temp / "pdf_diff"),
            ]
        )
        results["pdf_render_diff"] = {
            "returncode": diff.returncode,
            "stdout": diff.stdout.strip(),
            "stderr": diff.stderr.strip(),
        }
        font_audit = run(
            [
                sys.executable,
                str(HERE / "pdf_font_audit.py"),
                str(comparison_pdf),
                "--output",
                str(temp / "state" / "pdf_font_audit.json"),
            ]
        )
        try:
            font_payload = json.loads(font_audit.stdout)
        except json.JSONDecodeError:
            font_payload = {"raw_stdout": font_audit.stdout.strip()}
        results["pdf_font_audit"] = {
            "returncode": font_audit.returncode,
            "result": font_payload,
            "stderr": font_audit.stderr.strip(),
        }
        table_audit = None
        if main_tex:
            table_audit = run(
                [
                    sys.executable,
                    str(HERE / "tex_table_audit.py"),
                    str(main_tex),
                    "--strict",
                    "--output",
                    str(temp / "state" / "tex_table_audit.json"),
                ]
            )
            try:
                table_payload = json.loads(table_audit.stdout)
            except json.JSONDecodeError:
                table_payload = {"raw_stdout": table_audit.stdout.strip()}
            results["tex_table_audit"] = {
                "returncode": table_audit.returncode,
                "result": table_payload,
                "stderr": table_audit.stderr.strip(),
            }

        format_audit = run(
            [
                sys.executable,
                str(format_audit_script),
                "--profile",
                str(venue_profile),
                "--project-root",
                str(root),
                "--tex",
                str(main_tex),
                "--pdf",
                str(comparison_pdf),
                "--strict",
                "--output",
                str(temp / "state" / "format-audit.json"),
            ]
        )
        results["conference_format_audit"] = {
            "returncode": format_audit.returncode,
            "stdout": format_audit.stdout.strip(),
            "stderr": format_audit.stderr.strip(),
        }

        build_evidence = None
        rendered_audits_pass = (
            diff.returncode == 0
            and "changed_pages=none" in diff.stdout
            and font_audit.returncode == 0
            and table_audit is not None
            and table_audit.returncode == 0
            and format_audit.returncode == 0
        )
        if build.returncode == 0 and build_pdf_exists and manifest_exists and rendered_audits_pass:
            fingerprint = run(
                [
                    sys.executable,
                    str(WORKFLOW_CTL),
                    "fingerprint",
                    "--state",
                    str(temp / "state"),
                ]
            )
            fingerprint_payload = json.loads(fingerprint.stdout)
            combined_build = build.stdout + "\n" + build.stderr
            def summary_count(label: str, fallback_pattern: str) -> int:
                match = re.search(rf"\b{re.escape(label)}=(\d+)\b", combined_build)
                return int(match.group(1)) if match else len(re.findall(fallback_pattern, combined_build, re.IGNORECASE))
            undefined_count = summary_count(
                "undefined", r"undefined (?:reference|citation)"
            )
            missing_count = summary_count(
                "missing-files", r"(?:file .* not found|could not open .* file)"
            )
            overfull_count = summary_count("overfull", r"Overfull \\hbox")
            receipt = temp / "state" / "BUILD_RECEIPT.md"
            receipt.write_text(
                "# Build Receipt\n\n"
                "- Status: PASS\n"
                f"- Command: {build_command}\n"
                f"- Source SHA-256: {file_sha256(main_tex)}\n"
                f"- Bibliography SHA-256: {file_sha256(bibliography)}\n"
                f"- Dependency manifest SHA-256: {file_sha256(dependency_manifest)}\n"
                f"- Dependency bundle SHA-256: {fingerprint_payload['dependency_bundle_sha256']}\n"
                f"- Venue profile SHA-256: {file_sha256(venue_profile)}\n"
                f"- Format audit SHA-256: {file_sha256(temp / 'state' / 'format-audit.json')}\n"
                f"- Output PDF SHA-256: {file_sha256(comparison_pdf)}\n"
                f"- Page count: {pdf_page_count(comparison_pdf)}\n"
                f"- Undefined references/citations: {undefined_count}\n"
                f"- Missing files: {missing_count}\n"
                f"- Overfull boxes: {overfull_count}\n"
                "- Rendered inspection: PASS; pages=ALL; evidence=exact PDF render-diff and rendered audits completed\n",
                encoding="utf-8",
            )
            build_evidence = run(
                [
                    sys.executable,
                    str(WORKFLOW_CTL),
                    "check-build",
                    "--state",
                    str(temp / "state"),
                ]
            )
            results["build_evidence_gate"] = {
                "returncode": build_evidence.returncode,
                "result": json.loads(build_evidence.stdout),
                "stderr": build_evidence.stderr.strip(),
            }
        elif build.returncode == 0 and build_pdf_exists and manifest_exists:
            results["build_evidence_gate"] = {
                "returncode": None,
                "result": "SKIPPED: rendered diff/font/strict-table audits did not all pass",
                "stderr": "",
            }

    print(json.dumps(results, ensure_ascii=False, indent=2))
    preflight_ok = validate.returncode == 0
    build_ok = build.returncode == 0 and build_pdf_exists and manifest_exists
    diff_ok = diff.returncode == 0 and "changed_pages=none" in diff.stdout
    font_ok = font_audit.returncode == 0
    table_ok = table_audit is None or table_audit.returncode == 0
    format_ok = format_audit.returncode == 0
    build_evidence_ok = build_evidence is not None and build_evidence.returncode == 0
    return 0 if preflight_ok and build_ok and diff_ok and font_ok and table_ok and format_ok and build_evidence_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
