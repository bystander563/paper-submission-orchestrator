#!/usr/bin/env python3
"""Audit font embedding and rendered text sizes in a conference-paper PDF.

The audit uses PyMuPDF because ``pdffonts`` is not available in every Codex
runtime.  It is intentionally conservative: unembedded and Type 3 fonts are
errors; very small rendered text is a warning that must be inspected in the
PDF rather than an automatic rejection.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path


SUBSET_PREFIX = re.compile(r"^[A-Z]{6}\+")


def clean_font_name(name: str) -> str:
    return SUBSET_PREFIX.sub("", name or "UNKNOWN")


def audit_pdf(pdf_path: Path, min_readable_pt: float) -> dict[str, object]:
    try:
        import fitz  # type: ignore
    except ImportError as exc:  # pragma: no cover - environment failure path
        raise RuntimeError(
            "PyMuPDF is required for PDF font auditing; install pymupdf or use "
            "a runtime that provides it."
        ) from exc

    document = fitz.open(pdf_path)
    fonts: dict[int, dict[str, object]] = {}
    font_pages: dict[int, set[int]] = defaultdict(set)
    size_counts: Counter[float] = Counter()
    small_examples: list[dict[str, object]] = []

    for page_number, page in enumerate(document, start=1):
        for row in page.get_fonts(full=True):
            xref = int(row[0])
            font_pages[xref].add(page_number)
            if xref not in fonts:
                extracted = document.extract_font(xref)
                content = extracted[3] if len(extracted) >= 4 else b""
                fonts[xref] = {
                    "xref": xref,
                    "extension": str(row[1]),
                    "type": str(row[2]),
                    "basefont": clean_font_name(str(row[3])),
                    "resource_name": str(row[4]),
                    "encoding": str(row[5]),
                    "embedded": bool(content),
                    "embedded_bytes": len(content or b""),
                }

        text_dict = page.get_text("dict")
        for block in text_dict.get("blocks", []):
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = str(span.get("text", "")).strip()
                    if not text:
                        continue
                    size = round(float(span.get("size", 0.0)), 2)
                    size_counts[size] += len(text)
                    if size < min_readable_pt and len(small_examples) < 20:
                        small_examples.append(
                            {
                                "page": page_number,
                                "size_pt": size,
                                "font": clean_font_name(str(span.get("font", "UNKNOWN"))),
                                "text": text[:80],
                            }
                        )

    errors: list[dict[str, object]] = []
    warnings: list[dict[str, object]] = []
    font_rows = []
    for xref in sorted(fonts):
        entry = fonts[xref]
        entry["pages"] = sorted(font_pages[xref])
        font_rows.append(entry)
        if not entry["embedded"]:
            errors.append(
                {
                    "code": "FONT_NOT_EMBEDDED",
                    "font": entry["basefont"],
                    "pages": entry["pages"],
                }
            )
        if "Type3" in str(entry["type"]):
            errors.append(
                {
                    "code": "TYPE3_FONT",
                    "font": entry["basefont"],
                    "pages": entry["pages"],
                }
            )

    if small_examples:
        warnings.append(
            {
                "code": "TEXT_BELOW_READABILITY_THRESHOLD",
                "threshold_pt": min_readable_pt,
                "counted_examples": len(small_examples),
                "examples": small_examples,
                "message": "Inspect at 100% print scale; formulas and superscripts may be legitimate.",
            }
        )

    return {
        "pdf": str(pdf_path),
        "pdf_sha256": hashlib.sha256(pdf_path.read_bytes()).hexdigest(),
        "pages": document.page_count,
        "font_count": len(font_rows),
        "fonts": font_rows,
        "rendered_text_size_character_counts": {
            f"{size:.2f}": count for size, count in sorted(size_counts.items())
        },
        "errors": errors,
        "warnings": warnings,
        "status": "PASS" if not errors else "FAIL",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    parser.add_argument(
        "--min-readable-pt",
        type=float,
        default=6.5,
        help="Rendered text below this size is reported for visual inspection (default: 6.5).",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    pdf = args.pdf.expanduser().resolve()
    if not pdf.is_file():
        parser.error(f"PDF not found: {pdf}")
    if args.min_readable_pt <= 0:
        parser.error("--min-readable-pt must be positive")
    try:
        result = audit_pdf(pdf, args.min_readable_pt)
    except Exception as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}, indent=2), file=sys.stderr)
        return 2
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        output = args.output.expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
