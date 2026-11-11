#!/usr/bin/env python3
"""Summarize the last player Build Report in a Unity Editor log.

After a player build, Unity writes a "Build Report" block to the Editor log: the
uncompressed size per category (Textures, Meshes, Sounds, ...), the complete
build size, and every used asset sorted by uncompressed size. This tool finds the
last such block, prints the categories and the largest assets, and can fail when
the build is over a size budget.

Log locations: macOS ~/Library/Logs/Unity/Editor.log, Windows
%LOCALAPPDATA%\\Unity\\Editor\\Editor.log, Linux ~/.config/unity3d/Editor.log, or
the file passed to -logFile in batch mode.

Sizes are binary: 1 MB here is 1024 * 1024 bytes, as in the Editor log. Store and
host limits are often decimal (1 MB = 1,000,000 bytes).

Standard library only. Read-only: nothing is ever written.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

TOOL = "build_report"
SCHEMA = 1

UNITS = {"b": 1, "kb": 1024, "mb": 1024**2, "gb": 1024**3}
SIZE = r"([0-9]+(?:\.[0-9]+)?) (b|kb|mb|gb)"

REPORT_START = "Build Report"
USER_ASSETS = "Total User Assets"
OLD_COMPLETE = "Complete size"
# Other threads can write to the Editor log while the asset list is printed; allow a few such lines.
MAX_FOREIGN_LINES = 3
CATEGORY_RE = re.compile(rf"^(\S.*?)\s+{SIZE}\s+([0-9.]+)%\s*$")
COMPLETE_RE = re.compile(rf"^Complete build size\s+{SIZE}\s*$")
ASSET_RE = re.compile(rf"^\s*{SIZE}\s+([0-9.]+)%\s+(.+?)\s*$")
END_RE = re.compile(r"^-{20,}\s*$")


def to_bytes(number: str, unit: str) -> int:
    return round(float(number) * UNITS[unit])


@dataclass
class Report:
    start_line: int
    categories: list[dict] = field(default_factory=list)
    user_assets_bytes: int | None = None
    complete_bytes: int | None = None
    assets: list[dict] = field(default_factory=list)

    @property
    def empty(self) -> bool:
        return not (self.categories or self.assets or self.complete_bytes is not None)


def parse_report(lines: list[str], start: int) -> Report:
    report = Report(start_line=start + 1)
    in_assets = False
    foreign = 0
    for line in lines[start + 1 :]:
        if END_RE.match(line) or line.strip() == REPORT_START:
            break
        if line.startswith("Used Assets and files"):
            in_assets = True
            continue
        if in_assets:
            match = ASSET_RE.match(line)
            if not match:
                foreign += 1
                if foreign > MAX_FOREIGN_LINES:
                    break
                continue
            foreign = 0
            number, unit, percent, path = match.groups()
            report.assets.append({"path": path, "bytes": to_bytes(number, unit), "percent": float(percent)})
            continue
        complete = COMPLETE_RE.match(line)
        if complete:
            report.complete_bytes = to_bytes(*complete.groups())
            continue
        category = CATEGORY_RE.match(line)
        if category:
            name, number, unit, percent = category.groups()
            if name == USER_ASSETS:
                report.user_assets_bytes = to_bytes(number, unit)
                continue
            if name == OLD_COMPLETE:  # pre-2022 layout: "Complete size  220.6 mb  100.0%"
                report.complete_bytes = to_bytes(number, unit)
                continue
            report.categories.append({"name": name, "bytes": to_bytes(number, unit), "percent": float(percent)})
    return report


def parse_last_report(lines: list[str]) -> Report | None:
    """The last Build Report block with content; a bare 'Build Report' line alone is skipped."""
    starts = [index for index, line in enumerate(lines) if line.strip() == REPORT_START]
    for start in reversed(starts):
        report = parse_report(lines, start)
        if not report.empty:
            return report
    return None


def human(size: int) -> str:
    for unit, scale in (("GB", 1024**3), ("MB", 1024**2), ("KB", 1024)):
        if size >= scale:
            return f"{size / scale:.1f} {unit}"
    return f"{size} B"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="build_report.py",
        description="Summarize the last player Build Report in a Unity Editor log.",
        epilog=(
            "example:\n"
            "  python scripts/build_report.py ~/Library/Logs/Unity/Editor.log\n"
            "  python scripts/build_report.py build.log --top 30 --budget-mb 200 --json\n\n"
            "sizes: MB means MiB (1024 * 1024 bytes), as in the Editor log; the sizes are\n"
            "       uncompressed, so measure the shipped file for a store or host limit.\n\n"
            "exit codes: 0 report found (and within --budget-mb), 1 no report in the log,\n"
            "            over budget, or --budget-mb set but the report has no complete build size,\n"
            "            2 usage problem or unreadable log"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("log", metavar="EDITOR_LOG", help="Editor log or -logFile output that contains a player build")
    parser.add_argument("--json", action="store_true", help="print one JSON object instead of text")
    parser.add_argument(
        "--top", type=int, default=15, metavar="N", help="largest assets to list (default: 15; 0 = all)"
    )
    parser.add_argument(
        "--budget-mb",
        type=float,
        metavar="MB",
        help="exit 1 when the complete build size (uncompressed) is above this many MiB, "
        "or when the report has no complete build size to compare",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.top < 0:
        parser.error("--top must be 0 or more")
    if args.budget_mb is not None and args.budget_mb <= 0:
        parser.error("--budget-mb must be above 0")

    path = Path(args.log).expanduser()
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as exc:
        print(f"error: cannot read '{args.log}': {exc.strerror or exc}", file=sys.stderr)
        return 2

    report = parse_last_report(lines)
    if report is None:
        print(
            f"error: no 'Build Report' block with sizes in '{args.log}'; build a player first, "
            "and pass the log of the Editor session that built it",
            file=sys.stderr,
        )
        return 1

    top = report.assets if args.top == 0 else report.assets[: args.top]
    budget = None if args.budget_mb is None else round(args.budget_mb * 1024**2)
    unchecked = budget is not None and report.complete_bytes is None
    over = budget is not None and not unchecked and report.complete_bytes > budget

    if args.json:
        print(
            json.dumps(
                {
                    "tool": TOOL,
                    "schema": SCHEMA,
                    "log": path.as_posix(),
                    "report_line": report.start_line,
                    "complete_bytes": report.complete_bytes,
                    "budget_bytes": budget,
                    "over_budget": over,
                    "budget_checked": budget is not None and not unchecked,
                    "categories": report.categories,
                    "user_assets_bytes": report.user_assets_bytes,
                    "asset_count": len(report.assets),
                    "assets": top,
                },
                indent=2,
            )
        )
    else:
        print(f"Build Report at line {report.start_line} of {path.name}")
        for category in report.categories:
            print(f"  {category['name']:<20} {human(category['bytes']):>10}  {category['percent']:5.1f}%")
        if report.user_assets_bytes is not None:
            print(f"Total user assets: {human(report.user_assets_bytes)}")
        if report.complete_bytes is not None:
            print(f"Complete build size (uncompressed): {human(report.complete_bytes)}")
        print(f"Largest {len(top)} of {len(report.assets)} used assets:")
        for asset in top:
            print(f"  {human(asset['bytes']):>10}  {asset['percent']:5.1f}%  {asset['path']}")
        if over:
            print(f"OVER BUDGET: {human(report.complete_bytes)} > {human(budget)}")

    if unchecked:
        print(
            "error: --budget-mb is set but the Build Report has no 'Complete build size' line "
            "(cut-off log or a different layout), so the budget was not checked",
            file=sys.stderr,
        )
    return 1 if over or unchecked else 0


if __name__ == "__main__":
    sys.exit(main())
