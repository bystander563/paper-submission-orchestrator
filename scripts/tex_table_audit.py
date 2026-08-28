#!/usr/bin/env python3
"""Audit LaTeX tables for width, booktabs rules, and readable font choices."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


TABLE_RE = re.compile(
    r"\\begin\s*\{(?P<env>table\*?)\}(?P<body>.*?)\\end\s*\{(?P=env)\}",
    re.DOTALL,
)
UNSUPPORTED_TABLE_RE = re.compile(
    r"\\begin\s*\{(?P<env>longtable|sidewaystable\*?)\}(?P<body>.*?)"
    r"\\end\s*\{(?P=env)\}",
    re.DOTALL,
)
INPUT_RE = re.compile(r"\\(?:input|include)\s*\{([^}]+)\}")


def strip_tex_comments(text: str) -> str:
    """Remove TeX comments while preserving line/character positions.

    The paper-qa exception annotation is intentionally retained because it is
    an input to the width policy. Escaped percent signs are not comments.
    """
    rendered: list[str] = []
    for line in text.splitlines(keepends=True):
        comment_at = None
        for index, char in enumerate(line):
            if char != "%":
                continue
            backslashes = 0
            cursor = index - 1
            while cursor >= 0 and line[cursor] == "\\":
                backslashes += 1
                cursor -= 1
            if backslashes % 2 == 0:
                comment_at = index
                break
        if comment_at is None or re.match(
            r"%\s*paper-qa:\s*natural-width-ok\b",
            line[comment_at:],
            re.IGNORECASE,
        ):
            rendered.append(line)
            continue
        ending = "\n" if line.endswith("\n") else ""
        content_end = len(line) - len(ending)
        rendered.append(
            line[:comment_at] + " " * (content_end - comment_at) + ending
        )
    return "".join(rendered)


def resolve_include(owner: Path, raw: str) -> Path:
    candidate = (owner.parent / raw).resolve()
    if candidate.suffix == "":
        candidate = candidate.with_suffix(".tex")
    return candidate


def collect_tex(path: Path, seen: set[Path] | None = None) -> list[tuple[Path, str]]:
    resolved = path.expanduser().resolve()
    if seen is None:
        seen = set()
    if resolved in seen:
        return []
    if not resolved.is_file():
        raise FileNotFoundError(f"TeX source not found: {resolved}")
    seen.add(resolved)
    text = strip_tex_comments(resolved.read_text(encoding="utf-8", errors="replace"))
    files = [(resolved, text)]
    for match in INPUT_RE.finditer(text):
        included = resolve_include(resolved, match.group(1).strip())
        if included.is_file():
            files.extend(collect_tex(included, seen))
    return files


def finding(
    severity: str,
    code: str,
    path: Path,
    line: int,
    environment: str,
    message: str,
) -> dict[str, Any]:
    return {
        "severity": severity,
        "code": code,
        "file": str(path),
        "line": line,
        "environment": environment,
        "message": message,
    }


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_braced(text: str, start: int) -> tuple[str, int] | None:
    index = start
    while index < len(text) and text[index].isspace():
        index += 1
    if index >= len(text) or text[index] != "{":
        return None
    depth = 0
    content_start = index + 1
    for cursor in range(index, len(text)):
        char = text[cursor]
        if char == "{" and (cursor == 0 or text[cursor - 1] != "\\"):
            depth += 1
        elif char == "}" and (cursor == 0 or text[cursor - 1] != "\\"):
            depth -= 1
            if depth == 0:
                return text[content_start:cursor], cursor + 1
    return None


def parse_tabular(body: str) -> tuple[bool, str, str] | None:
    star_match = re.search(r"\\begin\s*\{tabular\*\}", body)
    normal_match = re.search(r"\\begin\s*\{tabular\}", body)
    if star_match and (not normal_match or star_match.start() < normal_match.start()):
        first = parse_braced(body, star_match.end())
        if not first:
            return None
        width, next_index = first
        second = parse_braced(body, next_index)
        if not second:
            return None
        columns, _ = second
        return True, width.strip(), columns
    if normal_match:
        first = parse_braced(body, normal_match.end())
        if not first:
            return None
        columns, _ = first
        return False, "", columns
    tabularx_match = re.search(r"\\begin\s*\{tabularx\}", body)
    if tabularx_match:
        first = parse_braced(body, tabularx_match.end())
        if not first:
            return None
        width, next_index = first
        second = parse_braced(body, next_index)
        if not second:
            return None
        columns, _ = second
        return True, width.strip(), columns
    return None


def promoted(strict: bool, default: str = "warning") -> str:
    return "error" if strict else default


def exact_frame_width(value: str, expected: str, alternate: str) -> bool:
    normalized = re.sub(r"\s+", "", value)
    return normalized in {expected, alternate}


def audit_table(path: Path, text: str, match: re.Match[str], strict: bool) -> list[dict[str, Any]]:
    env = match.group("env")
    body = match.group("body")
    line = text.count("\n", 0, match.start()) + 1
    findings: list[dict[str, Any]] = []
    expected = r"\textwidth" if env == "table*" else r"\columnwidth"
    alternate = r"\linewidth"
    wrong = r"\columnwidth" if env == "table*" else r"\textwidth"
    nearby_prefix = "\n".join(text[: match.start()].splitlines()[-5:])
    natural_width_exception = re.search(
        r"^\s*%\s*paper-qa:\s*natural-width-ok\s*;\s*reason=(\S.*?)\s*$",
        nearby_prefix,
        re.MULTILINE | re.IGNORECASE,
    )

    width_evidence = False
    tabular = parse_tabular(body)
    if tabular:
        is_star, width, columns = tabular
        if is_star and exact_frame_width(width, expected, alternate):
            width_evidence = True
        if "|" in columns:
            findings.append(
                finding("error", "VERTICAL_RULE", path, line, env, "tabular column specification contains a vertical rule")
            )
    else:
        findings.append(
            finding("warning", "TABULAR_UNPARSED", path, line, env, "could not parse a tabular/tabular* column specification")
        )

    resize = re.search(r"\\resizebox\{([^}]+)\}", body)
    if resize:
        target = resize.group(1).strip()
        if exact_frame_width(target, expected, alternate):
            width_evidence = True
        findings.append(
            finding("warning", "RESIZEBOX_TEXT_SCALING", path, line, env, "resizebox may scale table text; verify rendered font size")
        )

    adjust = re.search(r"\\begin\{adjustbox\}\{([^}]+)\}", body)
    if adjust:
        settings = adjust.group(1)
        exact_width = any(
            re.fullmatch(
                r"width\s*=\s*(?:" + re.escape(expected) + "|" + re.escape(alternate) + r")",
                item.strip(),
            )
            for item in settings.split(",")
        )
        if exact_width:
            width_evidence = True
        if re.search(
            r"max\s+width\s*=\s*(?:" + re.escape(expected) + "|" + re.escape(alternate) + r")",
            settings,
        ):
            findings.append(
                finding(
                    "warning",
                    "MAX_WIDTH_ONLY",
                    path,
                    line,
                    env,
                    "adjustbox max width prevents overflow but does not make a narrow table equal to the text frame",
                )
            )

    if wrong in body and expected not in body and alternate not in body:
        findings.append(
            finding("error", "WRONG_WIDTH_SCOPE", path, line, env, f"{env} uses {wrong}; expected {expected} or {alternate}")
        )
    if not width_evidence:
        if natural_width_exception:
            findings.append(
                finding(
                    "warning",
                    "NATURAL_WIDTH_EXCEPTION_ACCEPTED",
                    path,
                    line,
                    env,
                    "strict width exception recorded: " + natural_width_exception.group(1).strip(),
                )
            )
        else:
            findings.append(
                finding(
                    promoted(strict),
                    "WIDTH_NOT_EXPLICIT",
                    path,
                    line,
                    env,
                    f"outer table width is not explicitly aligned to {expected}; add a justified paper-qa natural-width annotation only after rendered inspection",
                )
            )

    has_top = r"\toprule" in body
    has_middle = r"\midrule" in body or r"\cmidrule" in body
    has_bottom = r"\bottomrule" in body
    if not (has_top and has_middle and has_bottom):
        findings.append(
            finding(
                promoted(strict),
                "THREE_LINE_INCOMPLETE",
                path,
                line,
                env,
                "table lacks a complete booktabs top/mid-or-cmid/bottom rule hierarchy",
            )
        )
    if r"\hline" in body:
        findings.append(
            finding(promoted(strict), "HLINE_GRID", path, line, env, "table uses hline; prefer booktabs rules unless the venue requires a grid")
        )
    if body.count(r"\midrule") > 1:
        findings.append(
            finding(
                "warning",
                "MULTIPLE_FULL_MIDRULES",
                path,
                line,
                env,
                "multiple full-width midrules need distinct protocol-level meanings; use trimmed cmidrule or whitespace for subordinate groups",
            )
        )
    for multirow in re.finditer(r"\\multirow\s*(?:\[([^\]]+)\])?", body):
        alignment = multirow.group(1)
        if alignment != "c":
            findings.append(
                finding(
                    "warning",
                    "MULTIROW_ALIGNMENT_UNSPECIFIED",
                    path,
                    line,
                    env,
                    "multirow group label does not explicitly request centered vertical alignment; verify the rendered row group",
                )
            )
            break
    if r"\multirow" in body and r"\raisebox" in body:
        findings.append(
            finding(
                "warning",
                "MANUAL_MULTIROW_NUDGE",
                path,
                line,
                env,
                "manual multirow vertical adjustment is fragile; record rendered evidence and recheck after row-height or font changes",
            )
        )
    if tabular:
        _, _, columns = tabular
        has_p = bool(re.search(r"(?:^|[^A-Za-z])p\s*\{", columns))
        has_m = bool(re.search(r"(?:^|[^A-Za-z])m\s*\{", columns))
        if has_p and has_m:
            findings.append(
                finding(
                    "warning",
                    "MIXED_PARAGRAPH_VERTICAL_ALIGNMENT",
                    path,
                    line,
                    env,
                    "column specification mixes top-aligned p{} and centered m{} paragraph cells; verify row-wise vertical alignment",
                )
            )
    if re.search(r"\\tiny\b", body):
        findings.append(
            finding("error", "TINY_FONT", path, line, env, "table uses tiny font to fit content")
        )
    if re.search(r"\\scriptsize\b", body):
        findings.append(
            finding("warning", "SCRIPTSIZE_FONT", path, line, env, "scriptsize requires a documented exception and rendered readability proof")
        )
    if re.search(r"\\(?:fontfamily|fontsize)\b", body):
        findings.append(
            finding("warning", "LOCAL_FONT_OVERRIDE", path, line, env, "table locally overrides the document font; verify venue compliance")
        )
    if r"\caption" not in body:
        findings.append(finding("error", "MISSING_CAPTION", path, line, env, "table has no caption"))
    if r"\label" not in body:
        findings.append(finding("warning", "MISSING_LABEL", path, line, env, "table has no label for cross-reference"))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("main_tex", type=Path)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    try:
        files = collect_tex(args.main_tex)
    except FileNotFoundError as exc:
        parser.error(str(exc))

    findings: list[dict[str, Any]] = []
    tables = 0
    table_inventory: list[dict[str, Any]] = []
    combined = "\n".join(text for _, text in files)
    for path, text in files:
        for match in TABLE_RE.finditer(text):
            tables += 1
            body = match.group("body")
            line = text.count("\n", 0, match.start()) + 1
            label_match = re.search(r"\\label\s*\{([^}]+)\}", body)
            table_inventory.append(
                {
                    "id": label_match.group(1).strip() if label_match else f"{path.name}:{line}",
                    "file": str(path),
                    "line": line,
                    "environment": match.group("env"),
                }
            )
            findings.extend(audit_table(path, text, match, args.strict))
        for match in UNSUPPORTED_TABLE_RE.finditer(text):
            tables += 1
            body = match.group("body")
            line = text.count("\n", 0, match.start()) + 1
            label_match = re.search(r"\\label\s*\{([^}]+)\}", body)
            table_inventory.append(
                {
                    "id": label_match.group(1).strip() if label_match else f"{path.name}:{line}",
                    "file": str(path),
                    "line": line,
                    "environment": match.group("env"),
                }
            )
            findings.append(
                finding(
                    promoted(args.strict),
                    "UNSUPPORTED_TABLE_ENVIRONMENT",
                    path,
                    line,
                    match.group("env"),
                    "table environment requires an explicit venue-specific extension of the width/rule audit; it cannot pass as NO_TABLES",
                )
            )

    if tables and not re.search(
        r"\\usepackage\s*(?:\[[^\]]*\]\s*)?\{[^}]*\bbooktabs\b[^}]*\}",
        combined,
    ):
        findings.append(
            finding("warning", "BOOKTABS_PACKAGE_UNSEEN", files[0][0], 1, "document", "booktabs package declaration was not found in the reachable TeX sources")
        )
    if re.search(r"\\captionsetup\{[^}]*font\s*=", combined):
        findings.append(
            finding("warning", "GLOBAL_CAPTION_FONT_OVERRIDE", files[0][0], 1, "document", "caption font is overridden; verify the official style permits it")
        )
    if re.search(r"\\setlength\s*\{\\(?:heavy|light|cmid)rulewidth\}", combined):
        findings.append(
            finding(
                "warning",
                "BOOKTABS_RULE_WIDTH_OVERRIDE",
                files[0][0],
                1,
                "document",
                "booktabs rule width is overridden; verify this is venue-wide and not a screenshot-zoom correction",
            )
        )

    errors = [item for item in findings if item["severity"] == "error"]
    result = {
        "ok": not errors,
        "strict": args.strict,
        "main_tex": str(args.main_tex.expanduser().resolve()),
        "main_tex_sha256": file_sha256(args.main_tex.expanduser().resolve()),
        "files_scanned": [str(path) for path, _ in files],
        "files_sha256": {str(path): file_sha256(path) for path, _ in files},
        "tables_scanned": tables,
        "tables": table_inventory,
        "error_count": len(errors),
        "warning_count": sum(item["severity"] == "warning" for item in findings),
        "findings": findings,
    }
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        output = args.output.expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
