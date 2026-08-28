from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("tex_table_audit.py")


class TexTableAuditTests(unittest.TestCase):
    def run_audit(self, tex: str, strict: bool = True) -> tuple[subprocess.CompletedProcess[str], dict]:
        with tempfile.TemporaryDirectory(prefix="tex_table_audit_") as temporary:
            source = Path(temporary) / "main.tex"
            source.write_text(tex, encoding="utf-8")
            command = [sys.executable, str(SCRIPT), str(source)]
            if strict:
                command.append("--strict")
            result = subprocess.run(command, text=True, capture_output=True, check=False)
            return result, json.loads(result.stdout)

    def test_booktabs_exact_width_table_passes(self) -> None:
        tex = r"""
\documentclass{article}
\usepackage{booktabs}
\begin{document}
\begin{table}
\centering
\small
\caption{Matched comparison.}
\label{tab:main}
\begin{tabular*}{\columnwidth}{@{\extracolsep{\fill}}lrr}
\toprule
Method & A & B \\
\midrule
Base & 1 & 2 \\
\bottomrule
\end{tabular*}
\end{table}
\end{document}
"""
        result, payload = self.run_audit(tex)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["tables_scanned"], 1)

    def test_grid_tiny_natural_width_table_fails_strict(self) -> None:
        tex = r"""
\documentclass{article}
\begin{document}
\begin{table}
\tiny
\begin{tabular}{|l|r|}
\hline
A & 1 \\
\hline
\end{tabular}
\end{table}
\end{document}
"""
        result, payload = self.run_audit(tex)
        self.assertEqual(result.returncode, 1)
        codes = {item["code"] for item in payload["findings"] if item["severity"] == "error"}
        self.assertTrue({"VERTICAL_RULE", "TINY_FONT", "WIDTH_NOT_EXPLICIT", "THREE_LINE_INCOMPLETE"}.issubset(codes))

    def test_table_star_rejects_columnwidth(self) -> None:
        tex = r"""
\documentclass{article}
\usepackage{booktabs}
\begin{document}
\begin{table*}
\caption{Wide table.}\label{tab:wide}
\begin{tabular*}{\columnwidth}{lrr}
\toprule A & B & C \\ \midrule X & 1 & 2 \\ \bottomrule
\end{tabular*}
\end{table*}
\end{document}
"""
        result, payload = self.run_audit(tex)
        self.assertEqual(result.returncode, 1)
        self.assertIn("WRONG_WIDTH_SCOPE", {item["code"] for item in payload["findings"]})

    def test_justified_natural_width_exception_passes_strict(self) -> None:
        tex = r"""
\documentclass{article}
\usepackage{booktabs}
\begin{document}
% paper-qa: natural-width-ok; reason=sparse two-column semantic table inspected at print scale
\begin{table}
\centering
\caption{Compact semantic table.}\label{tab:compact}
\begin{tabular}{lr}
\toprule Item & Value \\
\midrule A & 1 \\
\bottomrule
\end{tabular}
\end{table}
\end{document}
"""
        result, payload = self.run_audit(tex)
        self.assertEqual(result.returncode, 0, result.stderr)
        codes = {item["code"] for item in payload["findings"]}
        self.assertIn("NATURAL_WIDTH_EXCEPTION_ACCEPTED", codes)

    def test_semantic_grouping_and_vertical_alignment_warnings(self) -> None:
        tex = r"""
\documentclass{article}
\usepackage{booktabs}
\usepackage{multirow}
\begin{document}
\begin{table*}
\caption{Grouped controls.}\label{tab:groups}
\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}}p{.2\textwidth}m{.3\textwidth}rr}
\toprule Group & Method & A & B \\
\midrule
\multirow{2}{*}{Control} & X & 1 & 2 \\
& Y & 3 & 4 \\
\midrule
Other & Z & 5 & 6 \\
\bottomrule
\end{tabular*}
\end{table*}
\end{document}
"""
        result, payload = self.run_audit(tex)
        self.assertEqual(result.returncode, 0, result.stderr)
        codes = {item["code"] for item in payload["findings"]}
        self.assertTrue(
            {
                "MULTIPLE_FULL_MIDRULES",
                "MULTIROW_ALIGNMENT_UNSPECIFIED",
                "MIXED_PARAGRAPH_VERTICAL_ALIGNMENT",
            }.issubset(codes)
        )

    def test_manual_multirow_nudge_and_rule_width_override_warn(self) -> None:
        tex = r"""
\documentclass{article}
\usepackage{booktabs}
\usepackage{multirow}
\setlength{\lightrulewidth}{0.4pt}
\begin{document}
\begin{table}
\caption{Ablation.}\label{tab:ablation}
\begin{tabular*}{\columnwidth}{@{\extracolsep{\fill}}lr}
\toprule Group & Score \\
\midrule
\multirow[c]{2}{*}{\raisebox{-1ex}{Ablation}} & 1 \\
& 2 \\
\bottomrule
\end{tabular*}
\end{table}
\end{document}
"""
        result, payload = self.run_audit(tex)
        self.assertEqual(result.returncode, 0, result.stderr)
        codes = {item["code"] for item in payload["findings"]}
        self.assertIn("MANUAL_MULTIROW_NUDGE", codes)
        self.assertIn("BOOKTABS_RULE_WIDTH_OVERRIDE", codes)

    def test_input_with_whitespace_is_scanned_and_comments_are_ignored(self) -> None:
        with tempfile.TemporaryDirectory(prefix="tex_table_audit_include_") as temporary:
            root = Path(temporary)
            (root / "main.tex").write_text(
                r"""\documentclass{article}
\usepackage{booktabs,adjustbox}
% \begin{table}\tiny\begin{tabular}{|l|}\hline X\\\hline\end{tabular}\end{table}
\begin{document}
\input {body}
\end{document}
""",
                encoding="utf-8",
            )
            (root / "body.tex").write_text(
                r"""\begin{table}
\caption{Included table.}\label{tab:included}
\begin{tabular}{|l|}\hline X\\\hline\end{tabular}
\end{table}
""",
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(root / "main.tex"), "--strict"],
                text=True,
                capture_output=True,
                check=False,
            )
            payload = json.loads(result.stdout)
            self.assertEqual(payload["tables_scanned"], 1)
            self.assertEqual(result.returncode, 1)
            self.assertNotIn(
                "BOOKTABS_PACKAGE_UNSEEN",
                {item["code"] for item in payload["findings"]},
            )

    def test_adjustbox_max_width_is_not_exact_width_evidence(self) -> None:
        tex = r"""
\documentclass{article}
\usepackage{booktabs,adjustbox}
\begin{document}
\begin{table}
\caption{Sparse table.}\label{tab:sparse}
\begin{adjustbox}{max width=\columnwidth}
\begin{tabular}{lr}
\toprule A & B \\ \midrule X & 1 \\ \bottomrule
\end{tabular}
\end{adjustbox}
\end{table}
\end{document}
"""
        result, payload = self.run_audit(tex)
        self.assertEqual(result.returncode, 1)
        codes = {item["code"] for item in payload["findings"]}
        self.assertIn("MAX_WIDTH_ONLY", codes)
        self.assertIn("WIDTH_NOT_EXPLICIT", codes)

    def test_tabularx_exact_width_passes(self) -> None:
        tex = r"""
\documentclass{article}
\usepackage{booktabs,tabularx}
\begin{document}
\begin{table*}
\caption{Wide table.}\label{tab:wide-x}
\begin{tabularx}{\textwidth}{Xrr}
\toprule A & B & C \\ \midrule X & 1 & 2 \\ \bottomrule
\end{tabularx}
\end{table*}
\end{document}
"""
        result, payload = self.run_audit(tex)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(payload["ok"])

    def test_whitespace_before_environment_braces_is_supported(self) -> None:
        tex = r"""
\documentclass{article}
\usepackage {booktabs}
\begin{document}
\begin {table}
\caption{Whitespace form.}\label{tab:space}
\begin {tabular*}{\columnwidth}{lr}
\toprule A & B \\ \midrule X & 1 \\ \bottomrule
\end {tabular*}
\end {table}
\end{document}
"""
        result, payload = self.run_audit(tex)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(payload["tables_scanned"], 1)

    def test_fractional_width_is_not_full_frame_evidence(self) -> None:
        tex = r"""
\documentclass{article}
\usepackage{booktabs,tabularx}
\begin{document}
\begin{table*}
\caption{Fractional table.}\label{tab:fractional}
\begin{tabularx}{0.5\textwidth}{Xr}
\toprule A & B \\ \midrule X & 1 \\ \bottomrule
\end{tabularx}
\end{table*}
\end{document}
"""
        result, payload = self.run_audit(tex)
        self.assertEqual(result.returncode, 1)
        self.assertIn("WIDTH_NOT_EXPLICIT", {item["code"] for item in payload["findings"]})

    def test_longtable_cannot_disappear_as_no_tables(self) -> None:
        tex = r"""
\documentclass{article}
\usepackage{longtable}
\begin{document}
\begin{longtable}{|l|r|}
\caption{Long table.}\label{tab:long}\\
\hline A & B \\ \hline
\end{longtable}
\end{document}
"""
        result, payload = self.run_audit(tex)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(payload["tables_scanned"], 1)
        self.assertEqual(payload["tables"][0]["id"], "tab:long")
        self.assertIn(
            "UNSUPPORTED_TABLE_ENVIRONMENT",
            {item["code"] for item in payload["findings"]},
        )


if __name__ == "__main__":
    unittest.main()
