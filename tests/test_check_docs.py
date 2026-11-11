"""End-to-end tests for the game-docs documentation checker."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import unicodedata
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "workflows" / "game-docs"
CHECKER = SKILL / "scripts" / "check_docs.py"

HEADER = "**Updated:** 2026-11-09 · [GDD](../../GDD.md) · [Design](design.md) · [Implementation](implementation.md) · [Testing](testing.md)"

GDD = """# Snake — Game Design Document

**Version:** 0.2 · [Architecture](ARCHITECTURE.md) · [Features](#3-feature-index) · [Tuning](#max_speed)

## 3. Feature index

| Feature | Status | Scope | Summary | Docs |
|---|---|---|---|---|
| Movement | implemented | MVP | Grid steps every 120 ms | [design](features/movement/design.md) |
| Growth | designed | MVP | Eating grows the tail by 1; see [movement](features/movement/design.md) | [design](features/growth/design.md) |
| Leaderboard | idea | later | Weekly board | — |

## MAX_SPEED

Cap is 8 cells/s.

## Change log
**0.2:** growth designed.
"""

ARCH = "# Snake — Architecture\n\n**Status:** current · [GDD](GDD.md)\n"


def design(status: str, header: str = HEADER) -> str:
    return f"# Feature: design\n\n**Status:** {status} · {header}\n\n## Rules\n1. Step every 120 ms.\n"


def implementation() -> str:
    return f"# Feature: implementation\n\n{HEADER} · [Architecture](../../ARCHITECTURE.md)\n\n## Approach\nA timer.\n"


def testing(criteria: str = "- [x] Steps every 120 ms. *(tests/move.test.ts › step)*\n- [ ] Feels fair. *(not proven: no test)*\n") -> str:
    return f"# Feature: testing\n\n{HEADER}\n\n## Acceptance criteria\n{criteria}"


def clean_docs() -> dict[str, str | bytes]:
    """An implemented feature with all three docs, and a designed one with only its note."""
    return {
        "GDD.md": GDD,
        "ARCHITECTURE.md": ARCH,
        "features/movement/design.md": design("implemented"),
        "features/movement/implementation.md": implementation(),
        "features/movement/testing.md": testing(),
        "features/growth/design.md": design("designed", "**Updated:** 2026-11-09 · [GDD](../../GDD.md)")
        + "\n## Open questions\n- [ASSUMPTION] tail +1.\n",
    }


def template_block(name: str, index: int = 0) -> str:
    text = (SKILL / "references" / name).read_text(encoding="utf-8")
    blocks = re.findall(r"^~~~markdown\n(.*?)^~~~$", text, re.M | re.S)
    return blocks[index]


class CheckDocsTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)
        self.docs = self.base / "docs"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def write(self, files: dict[str, str | bytes], root: Path | None = None) -> None:
        root = root or self.docs
        for rel, content in files.items():
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))

    def run_checker(self, *args: str, target: Path | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(CHECKER), str(target or self.docs), *args],
            capture_output=True, text=True, encoding="utf-8", timeout=60,
        )

    def report(self, *args: str, target: Path | None = None) -> tuple[int, dict]:
        proc = self.run_checker("--json", "--max-issues", "0", *args, target=target)
        self.assertIn(proc.returncode, (0, 1), proc.stderr)
        return proc.returncode, json.loads(proc.stdout)

    def codes(self, data: dict, level: str) -> list[str]:
        return [i["code"] for i in data[level]]

    # -- clean input ---------------------------------------------------------

    def test_clean_docs_pass(self) -> None:
        self.write(clean_docs())
        code, data = self.report("--strict")
        self.assertEqual(code, 0, data)
        self.assertEqual(data["errors"], [])
        self.assertEqual(data["warnings"], [])
        self.assertEqual(data["files_checked"], 6)
        summaries = {n["message"] for n in data["notes"] if n["code"] == "feature-summary"}
        self.assertIn("movement: implemented · 1/2 criteria proven", summaries)
        self.assertIn("growth: designed · 1 [ASSUMPTION]", summaries)

    def test_gdd_alone_is_clean(self) -> None:
        # Mode A's default output: one GDD page, no ARCHITECTURE.md, no feature folders yet.
        gdd = GDD.replace("[Architecture](ARCHITECTURE.md) · ", "").replace("| implemented |", "| idea |")
        gdd = re.sub(r"\[design\]\(features/\w+/design\.md\)", "—", gdd).replace("; see [movement](features/movement/design.md)", "")
        gdd = gdd.replace("| Growth | designed", "| Growth | idea")
        self.write({"GDD.md": gdd})
        code, data = self.report("--strict")
        self.assertEqual((code, data["errors"], data["warnings"]), (0, [], []))

    def test_filled_templates_are_clean(self) -> None:
        gdd = template_block("gdd-template.md").replace("| Combo | designed", "| Combo | implemented")
        gdd = gdd.replace("[Change log](#change-log)", "[Change log](#change-log) · [Architecture](ARCHITECTURE.md)")
        files: dict[str, str | bytes] = {"GDD.md": gdd, "ARCHITECTURE.md": template_block("architecture-template.md")}
        for slug in ("lane-movement", "combo"):
            files[f"features/{slug}/design.md"] = template_block("feature-templates.md", 0).replace(
                "**Status:** designed", "**Status:** implemented")
            files[f"features/{slug}/implementation.md"] = template_block("feature-templates.md", 1)
            files[f"features/{slug}/testing.md"] = template_block("feature-templates.md", 2).replace("<slug>", "combo")
        self.write(files)
        code, data = self.report("--strict")
        self.assertEqual(data["errors"], [])
        self.assertEqual(data["warnings"], [])
        self.assertEqual(code, 0)

    def test_text_output_format(self) -> None:
        files = clean_docs()
        files["GDD.md"] = GDD.replace("(ARCHITECTURE.md)", "(ARCH.md)")
        self.write(files)
        proc = self.run_checker()
        self.assertEqual(proc.returncode, 1)
        lines = proc.stdout.splitlines()
        self.assertEqual(lines[0], "ERROR GDD.md:3: broken link -> ARCH.md")
        self.assertTrue(lines[1].startswith("  fix: "))
        self.assertRegex(lines[-2], r"^Summary: 1 errors, 0 warnings in 6 files checked$")
        self.assertTrue(lines[-1].startswith("Notes: "))

    def test_help_lists_options_and_codes(self) -> None:
        proc = subprocess.run([sys.executable, str(CHECKER), "--help"], capture_output=True, text=True,
                              encoding="utf-8", timeout=60)
        self.assertEqual(proc.returncode, 0)
        for text in ("--json", "--strict", "--max-issues", "--old", "--gdd", "Exit codes",
                     "broken-link", "feature-doc-missing", "gdd-no-index"):
            self.assertIn(text, proc.stdout)

    # -- errors --------------------------------------------------------------

    def test_error_codes(self) -> None:
        files = clean_docs()
        files["GDD.md"] = (GDD.replace("[design](features/growth/design.md)", "[design](features/grow/design.md)")
                           .replace("| Movement | implemented", "| Movement | in progress"))
        files["features/growth/design.md"] = "# Growth\n\n[gone](nowhere.md) ![art](img/missing.png)\n"
        files["features/orphan/implementation.md"] = "# Orphan\n"
        self.write(files)
        code, data = self.report()
        self.assertEqual(code, 1)
        self.assertEqual(sorted(set(self.codes(data, "errors"))), sorted([
            "broken-link", "design-missing", "design-no-status", "index-folder-missing", "status-mismatch",
        ]))
        broken = sorted((e["file"], e["message"]) for e in data["errors"] if e["code"] == "broken-link")
        self.assertEqual(broken, [
            ("GDD.md", "broken link -> features/grow/design.md"),
            ("features/growth/design.md", "broken link -> img/missing.png"),
            ("features/growth/design.md", "broken link -> nowhere.md"),
        ])
        self.assertIn("folder-not-indexed", self.codes(data, "warnings"))

    # -- a GDD that is not in this layout ------------------------------------

    def test_plain_gdd_is_a_note_not_an_error(self) -> None:
        self.write({"GDD.md": "# My game\n\n## Dash\nDash lasts 0.2 s. See [combat](#combat).\n\n## Combat\nHits.\n"})
        code, data = self.report("--strict")
        self.assertEqual((code, data["errors"], data["warnings"]), (0, [], []))
        self.assertEqual(self.codes(data, "notes"), ["gdd-no-index"])

    def test_plain_gdd_in_repo_root_skips_vendored_folders(self) -> None:
        repo = self.base / "repo"
        self.write({
            "GDD.md": "# My game\n\nSee [the readme](README.md).\n",
            "README.md": "# Game\n",
            "node_modules/pkg/README.md": "[x](missing.md)\n",
            "addons/plugin/README.md": "[x](missing.md)\n",
            ".git/notes.md": "[x](missing.md)\n",
        }, repo)
        code, data = self.report(target=repo)
        self.assertEqual((code, data["errors"], data["files_checked"]), (0, [], 2))

    def test_spec_tool_links_count_as_feature_docs(self) -> None:
        gdd = GDD.replace("[design](features/growth/design.md)", "[spec](../specs/002-growth/spec.md)")
        self.write({"GDD.md": gdd, "ARCHITECTURE.md": ARCH, **{k: v for k, v in clean_docs().items()
                                                                if not k.startswith(("GDD", "features/growth"))}})
        self.write({"specs/002-growth/spec.md": "# Growth spec\n"}, self.base)
        code, data = self.report("--strict")
        self.assertEqual((code, data["errors"], data["warnings"]), (0, [], []))

    # -- warnings ------------------------------------------------------------

    def test_warning_codes(self) -> None:
        files = clean_docs()
        files["GDD.md"] = (GDD.replace("| Leaderboard | idea", "| Leaderboard | designed")
                           .replace("[Tuning](#max_speed)", "[Tuning](#nope) · [Abs](/docs/GDD.md)")
                           .replace("| Leaderboard |", "| Sound | someday | later | Music | — |\n| Leaderboard |"))
        files["features/movement/testing.md"] = testing("- [x] Steps every 120 ms.\n1. [x] Wraps at the edge.\n").replace(
            " · [Implementation](implementation.md)", "")
        del files["features/movement/implementation.md"]
        files["features/movement/design.md"] = design("implemented").replace(" · [Implementation](implementation.md)", "")
        files["features/Bad_Slug/design.md"] = design("idea", "[GDD](../../GDD.md)")
        self.write(files)
        code, data = self.report()
        self.assertEqual(data["errors"], [], data["errors"])
        self.assertEqual(code, 0)
        self.assertEqual(sorted(set(self.codes(data, "warnings"))), sorted([
            "absolute-link", "anchor-not-found", "feature-doc-missing", "folder-not-indexed",
            "row-no-folder", "slug-not-kebab", "ticked-no-proof", "unknown-status",
        ]))
        missing = [w["message"] for w in data["warnings"] if w["code"] == "feature-doc-missing"]
        self.assertEqual(missing, ["features/movement/ is 'implemented' but has no implementation.md"])
        unproven = [w["line"] for w in data["warnings"] if w["code"] == "ticked-no-proof"]
        self.assertEqual(unproven, [6, 7])  # numbered criteria count too
        self.assertEqual(self.run_checker("--strict").returncode, 1)

    def test_features_without_gdd_warns(self) -> None:
        files = clean_docs()
        del files["GDD.md"]
        self.write(files)
        _, data = self.report()
        self.assertIn("gdd-missing", self.codes(data, "warnings"))

    # -- anchors -------------------------------------------------------------

    def test_github_anchor_rules(self) -> None:
        files = clean_docs()
        files["GDD.md"] = GDD + (
            "\n## _Emphasis_ and `code` & Stuff!\n## Repeat\n## Repeat\nSetext title\n------------\n"
            '<a id="custom-spot"></a>\n'
            "[a](#emphasis-and-code--stuff) [b](#repeat-1) [c](#setext-title) [d](#custom-spot)"
            " [e](#MAX_SPEED) [f](features/movement/design.md#rules) [g](<features/movement/design.md#rules>)\n"
            "```\n## Not A Heading\n[ignored](missing.md)\n```\n[h](#not-a-heading)\n"
        )
        self.write(files)
        _, data = self.report()
        anchor_warnings = [w["message"] for w in data["warnings"] if w["code"] == "anchor-not-found"]
        self.assertEqual(anchor_warnings, ["anchor not found -> #not-a-heading"])
        self.assertEqual(data["errors"], [])

    def test_anchors_match_github_slugger(self) -> None:
        # Expected slugs computed with github-slugger 2.0.0 from the text GitHub renders.
        headings = {
            "`_ready()` callback": "_ready-callback",
            "`__init__` method": "__init__-method",
            "_private_field": "_private_field",
            "MAX_SPEED tuning": "max_speed-tuning",
            "गेम डिज़ाइन": "गेम-डिज़ाइन",
            unicodedata.normalize("NFD", "café rules"): unicodedata.normalize("NFD", "café-rules"),
            "Price ½ off": "price--off",
        }
        body = "".join(f"## {h}\n" for h in headings) + "## Rules\n## Rules\n## Rules\n## Rules 1\n"
        links = list(headings.values()) + ["rules", "rules-1", "rules-2", "rules-1-1", "%C3%BCber-uns"]
        body += "## Über uns\n" + " ".join(f"[x](#{a})" for a in links) + "\n"
        files = clean_docs()
        files["notes.md"] = body
        self.write(files)
        _, data = self.report()
        self.assertEqual([w["message"] for w in data["warnings"]], [])

    def test_bom_and_crlf(self) -> None:
        files = clean_docs()
        files["GDD.md"] = b"\xef\xbb\xbf" + GDD.replace("\n", "\r\n").encode("utf-8")
        self.write(files)
        code, data = self.report("--strict")
        self.assertEqual((code, data["errors"], data["warnings"]), (0, [], []))

    # -- odd files -----------------------------------------------------------

    def test_non_utf8_file_is_a_warning_not_a_crash(self) -> None:
        files = clean_docs()
        files["notes.md"] = b"# Notes\n\nCaf\xe9 \x93quoted\x94 \xff\n"
        self.write(files)
        code, data = self.report()
        self.assertEqual(code, 0)
        warning = next(w for w in data["warnings"] if w["code"] == "not-utf8")
        self.assertEqual((warning["file"], warning["line"]), ("notes.md", 3))

    def test_folder_named_md_and_empty_file(self) -> None:
        files = clean_docs()
        files["empty.md"] = ""
        files["GDD.md"] = GDD + "\n[odd](odd.md#top) [empty](empty.md#x)\n"
        self.write(files)
        (self.docs / "odd.md").mkdir()
        code, data = self.report()
        self.assertEqual(data["errors"], [])
        self.assertEqual([w["message"] for w in data["warnings"]], ["anchor not found -> empty.md#x"])
        self.assertEqual(code, 0)

    @unittest.skipUnless(hasattr(os, "mkfifo"), "needs named pipes")
    def test_fifo_and_dangling_symlink_do_not_hang(self) -> None:
        self.write(clean_docs())
        os.mkfifo(self.docs / "pipe.md")
        os.symlink(self.docs / "gone.md", self.docs / "dangling.md")
        code, data = self.report()  # run_checker's timeout fails the test on a hang
        self.assertEqual(code, 0)
        self.assertEqual(sorted(w["file"] for w in data["warnings"] if w["code"] == "unreadable"),
                         ["dangling.md", "pipe.md"])

    # -- --old ---------------------------------------------------------------

    def test_old_reports_lost_lines_and_numbers(self) -> None:
        self.write(clean_docs())
        old = self.base / "old-GDD.md"
        old.write_text(
            "# Old GDD\n\n## 6.1 Movement\nGrid steps every 120 ms\n"
            "The snake wraps around the edges of a 24 by 24 board.\n", encoding="utf-8")
        code, data = self.report("--old", str(old))
        self.assertEqual(code, 0)
        warnings = {w["code"]: w for w in data["warnings"]}
        self.assertEqual(warnings["old-line-missing"]["line"], 5)
        self.assertIn("24", warnings["old-number-missing"]["message"])
        self.assertNotIn("120", warnings["old-number-missing"]["message"])

    def test_old_ignores_the_archive_copy(self) -> None:
        old_text = "# Old GDD\n\nThe snake wraps around the edges of a 24 by 24 board.\n"
        files = clean_docs()
        files["archive/old-GDD.md"] = old_text
        self.write(files)
        old = self.base / "old-GDD.md"
        old.write_text(old_text, encoding="utf-8")
        _, data = self.report("--old", str(old))
        self.assertIn("old-line-missing", self.codes(data, "warnings"))
        self.assertIn("old-number-missing", self.codes(data, "warnings"))

    def test_old_all_found_and_repeatable(self) -> None:
        self.write(clean_docs())
        first, second = self.base / "old.md", self.base / "side.md"
        first.write_text("# Old\n\nGrid steps every 120 ms\n", encoding="utf-8")
        second.write_text("# Side\n\nCap is 8 cells/s.\n", encoding="utf-8")
        code, data = self.report("--old", str(first), "--old", str(second))
        self.assertEqual(code, 0)
        self.assertEqual(self.codes(data, "notes").count("old-all-found"), 2)

    def test_old_file_inside_docs_is_excluded(self) -> None:
        files = clean_docs()
        files["old-GDD.md"] = "# Old\n\n[gone](gone.md)\nA long line that only the old copy of the GDD has.\n"
        self.write(files)
        _, data = self.report("--old", str(self.docs / "old-GDD.md"))
        self.assertEqual(data["errors"], [])
        self.assertIn("old-line-missing", self.codes(data, "warnings"))

    # -- other docs folders and GDD names ------------------------------------

    def test_custom_folder_and_gdd_name(self) -> None:
        files = clean_docs()
        files["game-design.md"] = files.pop("GDD.md")
        for rel in list(files):
            files[rel] = re.sub(r"\(((?:\.\./)*)GDD\.md\)", r"(\1game-design.md)", str(files[rel]))
        design_dir = self.base / "design"
        self.write(files, design_dir)
        proc = self.run_checker("--json", "--strict", "--gdd", "game-design.md", target=design_dir)
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertEqual(self.run_checker("--gdd", "missing.md", target=design_dir).returncode, 2)

    def test_gdd_name_is_case_insensitive(self) -> None:
        files = clean_docs()
        files["gdd.md"] = files.pop("GDD.md")
        self.write(files)
        _, data = self.report()
        self.assertNotIn("gdd-missing", self.codes(data, "warnings"))

    # -- usage problems ------------------------------------------------------

    def test_exit_2_cases(self) -> None:
        self.assertEqual(self.run_checker(target=self.base / "nope").returncode, 2)
        self.write({"GDD.md": GDD})
        self.assertEqual(self.run_checker(target=self.docs / "GDD.md").returncode, 2)
        self.assertEqual(self.run_checker("--old", str(self.base / "missing.md")).returncode, 2)
        self.assertEqual(self.run_checker("--old", str(self.base)).returncode, 2)
        self.assertEqual(self.run_checker("--max-issues", "-1").returncode, 2)
        plain = self.base / "src"
        self.write({"README.md": "# Not docs\n"}, plain)
        proc = self.run_checker(target=plain)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("no GDD.md and no features/", proc.stderr)

    # -- output limits -------------------------------------------------------

    def test_max_issues_truncates_without_changing_totals(self) -> None:
        files = clean_docs()
        files["GDD.md"] = GDD + "".join(f"\n[l{i}](missing{i}.md)" for i in range(5))
        self.write(files)
        proc = self.run_checker("--json", "--max-issues", "2")
        data = json.loads(proc.stdout)
        self.assertEqual(proc.returncode, 1)
        self.assertEqual((data["error_count"], len(data["errors"]), data["truncated"]), (5, 2, True))
        self.assertEqual(data["warnings"], [])
        self.assertEqual(data["notes"], [])
        for key in ("tool", "schema", "root", "files_checked", "warning_count", "note_count"):
            self.assertIn(key, data)
        self.assertEqual(data["tool"], "check_docs")
        text = self.run_checker("--max-issues", "2").stdout
        self.assertIn("... and ", text)
        self.assertIn("Summary: 5 errors", text)


if __name__ == "__main__":
    unittest.main()
