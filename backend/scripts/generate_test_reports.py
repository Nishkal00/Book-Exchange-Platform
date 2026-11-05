"""Run the unit tests and write the Markdown test reports into ../docs.

Usage (from the backend folder):  python scripts/generate_test_reports.py

Writes docs/unit-test-report.md, docs/coverage-report.md and docs/branch-coverage-report.md.
Re-run it after the last merge so the reports match the final commit.
"""

from __future__ import annotations

import json
import platform
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
DOCS = BACKEND.parent / "docs"
GATE = 70


def git(*args: str) -> str:
    try:
        return subprocess.run(
            ["git", *args], cwd=BACKEND, capture_output=True, text=True, check=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def run_tests(junit: Path, cov_json: Path) -> int:
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "-p",
        "no:cacheprovider",
        f"--junitxml={junit}",
        f"--cov-report=json:{cov_json}",
    ]
    return subprocess.run(cmd, cwd=BACKEND).returncode


def header(title: str, commit: str) -> list[str]:
    return [
        f"# {title}",
        "",
        "| Item | Value |",
        "| :--- | :--- |",
        f"| Generated | {datetime.now().strftime('%d %b %Y %H:%M')} |",
        f"| Commit | `{commit}` |",
        f"| Python | {platform.python_version()} on {platform.system()} |",
        "| Command | `python scripts/generate_test_reports.py` (runs `pytest` in `backend/`) |",
        "",
    ]


def unit_report(junit: Path, commit: str) -> str:
    root = ET.parse(junit).getroot()
    suite = root if root.tag == "testsuite" else root.find("testsuite")
    cases = list(suite.iter("testcase"))
    per_file: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    failures = []
    for case in cases:
        module = case.get("classname", "").split(".")
        name = "/".join(module[:-1] if module and module[-1][:1].isupper() else module)
        status = "passed"
        if case.find("failure") is not None or case.find("error") is not None:
            status = "failed"
            failures.append(f"{case.get('classname')}::{case.get('name')}")
        elif case.find("skipped") is not None:
            status = "skipped"
        per_file[name][status] += 1
        per_file[name]["total"] += 1

    total = len(cases)
    failed = sum(v["failed"] for v in per_file.values())
    skipped = sum(v["skipped"] for v in per_file.values())
    passed = total - failed - skipped
    out = header("Unit Test Report (backend)", commit)
    out += [
        "## Summary",
        "",
        "| Total | Passed | Failed | Skipped | Duration |",
        "| ---: | ---: | ---: | ---: | ---: |",
        f"| {total} | {passed} | {failed} | {skipped} | {float(suite.get('time', 0)):.1f} s |",
        "",
        "Database: in-memory SQLite for unit tests. PostgreSQL-only behaviour is exercised by the",
        "CI migration step against a real PostgreSQL service.",
        "",
        "## Results by test file",
        "",
        "| Test file | Tests | Passed | Failed | Skipped |",
        "| :--- | ---: | ---: | ---: | ---: |",
    ]
    for name in sorted(per_file):
        v = per_file[name]
        done = v["total"] - v["failed"] - v["skipped"]
        out.append(
            f"| `{name.replace('.', '/')}.py` | {v['total']} | {done} | "
            f"{v['failed']} | {v['skipped']} |"
        )
    out += ["", "## Failures", ""]
    out += [f"- `{f}`" for f in failures] or ["None."]
    out.append("")
    return "\n".join(out)


def coverage_tables(cov: dict, commit: str) -> tuple[str, str]:
    files = cov["files"]
    totals = cov["totals"]
    line_rows, branch_rows = [], []
    for path in sorted(files):
        s = files[path]["summary"]
        short = path.replace("\\", "/")
        if s["num_statements"] == 0:
            continue
        line_rows.append(
            f"| `{short}` | {s['num_statements']} | {s['missing_lines']} | "
            f"{100 * s['covered_lines'] / s['num_statements']:.0f}% |"
        )
        if s["num_branches"]:
            branch_rows.append(
                f"| `{short}` | {s['num_branches']} | {s['covered_branches']} | "
                f"{s['missing_branches']} | "
                f"{100 * s['covered_branches'] / s['num_branches']:.0f}% |"
            )
    stmts = totals["num_statements"]
    line_pct = 100 * totals["covered_lines"] / stmts
    br = totals["num_branches"]
    br_pct = 100 * totals["covered_branches"] / br if br else 100

    line = header("Code Coverage Report (statement coverage)", commit) + [
        "## Summary",
        "",
        "| Statements | Missed | Statement coverage | CI gate |",
        "| ---: | ---: | ---: | :--- |",
        f"| {stmts} | {totals['missing_lines']} | **{line_pct:.1f}%** | >= {GATE}% "
        f"({'met' if totals['percent_covered'] >= GATE else 'NOT met'}) |",
        "",
        "The CI gate (`--cov-fail-under=70`) uses the combined statement and branch figure, "
        f"currently {totals['percent_covered']:.1f}%.",
        "",
        "## Coverage by file",
        "",
        "| File | Statements | Missed | Coverage |",
        "| :--- | ---: | ---: | ---: |",
        *line_rows,
        "",
    ]
    branch = header("Branch Coverage Report", commit) + [
        "## Summary",
        "",
        "| Branches | Covered | Partially or not covered | Branch coverage |",
        "| ---: | ---: | ---: | ---: |",
        f"| {br} | {totals['covered_branches']} | {totals['missing_branches']} | "
        f"**{br_pct:.1f}%** |",
        "",
        "Branch coverage is switched on with `branch = true` in `backend/pyproject.toml`.",
        "",
        "## Branch coverage by file",
        "",
        "| File | Branches | Covered | Missed | Coverage |",
        "| :--- | ---: | ---: | ---: | ---: |",
        *branch_rows,
        "",
    ]
    return "\n".join(line), "\n".join(branch)


def main() -> int:
    commit = git("rev-parse", "--short", "HEAD")
    dirty = git("status", "--porcelain", "--", ".")
    if dirty and dirty != "unknown":
        commit += " (+ uncommitted changes)"
    with tempfile.TemporaryDirectory() as tmp:
        junit, cov_json = Path(tmp) / "junit.xml", Path(tmp) / "cov.json"
        code = run_tests(junit, cov_json)
        if not junit.exists() or not cov_json.exists():
            print("Tests did not produce reports.")
            return code or 1
        DOCS.mkdir(exist_ok=True)
        (DOCS / "unit-test-report.md").write_text(unit_report(junit, commit), encoding="utf-8")
        line, branch = coverage_tables(json.loads(cov_json.read_text()), commit)
        (DOCS / "coverage-report.md").write_text(line, encoding="utf-8")
        (DOCS / "branch-coverage-report.md").write_text(branch, encoding="utf-8")
    print("Wrote docs/unit-test-report.md, docs/coverage-report.md, docs/branch-coverage-report.md")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
