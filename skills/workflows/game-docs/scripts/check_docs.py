#!/usr/bin/env python3
"""Check a game docs folder: a GDD with a feature index and features/<slug>/ folders.

Each feature folder holds design.md, and implementation.md plus testing.md once
the feature has code. The checker reads every Markdown file under DOCS_DIR and
reports what is broken or out of step. It never writes anything, never opens
the network and never runs other programs.

Errors (the docs are broken or contradict themselves):
  broken-link            a relative link or image points at a file that does not exist
  design-missing         a feature folder has no design.md
  design-no-status       design.md has no "**Status:** ..." in its header
  index-folder-missing   a GDD index row links a feature folder that does not exist
  status-mismatch        the GDD index and design.md give a feature different statuses

Warnings (worth a look, may be fine):
  feature-doc-missing    a feature with code (in progress, implemented, changed — code
                         pending) has no implementation.md or testing.md
  anchor-not-found, absolute-link, unknown-status, folder-not-indexed,
  row-no-folder, ticked-no-proof, slug-not-kebab, gdd-missing, not-utf8,
  unreadable, old-line-missing, old-number-missing

Notes (never change the exit code):
  gdd-no-index           the GDD has no feature index table, so index checks were
                         skipped (normal for a GDD that is not in this layout)
  feature-summary        status, criteria proven and open assumptions per feature
  old-all-found          every line of an --old file was found in the new docs

The GDD is GDD.md in DOCS_DIR (any letter case) unless --gdd names another file.
Folders starting with '.' and vendored folders (node_modules, addons, vendor,
Library, Packages) are skipped. Anchors follow GitHub's heading slugs.

Exit codes: 0 no errors, 1 errors (or warnings with --strict), 2 usage problem:
DOCS_DIR or an --old/--gdd file is missing, or DOCS_DIR has no GDD and no
features/ folder.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote

TOOL = "check_docs"
SCHEMA = 1

STATUSES = ("idea", "designed", "in progress", "implemented", "changed — code pending", "cut")
HAS_CODE = ("in progress", "implemented", "changed — code pending")
CODE_DOCS = ("implementation.md", "testing.md")
# Vendored or engine-owned folders, skipped when the docs folder is the repo root.
# Names like build/ or dist/ are left in: they could be real feature slugs.
SKIP_DIRS = {"node_modules", "addons", "vendor", "Library", "Packages"}

LINK_RE = re.compile(r"\[(?:[^\]\\]|\\.)*\]\(\s*(<[^>]*>|[^)\s]+)(?:\s+(?:\"[^\"]*\"|'[^']*'))?\s*\)")
SCHEME_RE = re.compile(r"^[a-z][a-z0-9+.-]*:", re.I)
STATUS_RE = re.compile(r"\*\*Status:\*\*\s*([^·|\n]+)")
CRIT_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+\[([ xX])\]\s+(.*)$")
PROOF_RE = re.compile(r"\(.+\)[\s*_.]*$")
FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
ATX_RE = re.compile(r"^ {0,3}#{1,6}(?:[ \t]+(.*?))?(?:[ \t]+#+)?[ \t]*$")
SETEXT_RE = re.compile(r"^ {0,3}(=+|-+)[ \t]*$")
HTML_ID_RE = re.compile(r"<a\s[^>]*\b(?:id|name)\s*=\s*[\"']([^\"']+)[\"']", re.I)
SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)?")


@dataclass
class Issue:
    level: str  # ERROR, WARNING or NOTE
    code: str
    file: str
    line: int | None
    message: str
    fix: str

    def as_json(self) -> dict[str, object]:
        return {"code": self.code, "file": self.file, "line": self.line, "message": self.message, "fix": self.fix}


class UsageProblem(Exception):
    pass


# --------------------------------------------------------------------------
# Markdown helpers
# --------------------------------------------------------------------------


def outside_fences(lines: list[str]) -> list[bool]:
    """For each line, True when it is ordinary Markdown (not inside or on a code fence)."""
    flags: list[bool] = []
    fence: str | None = None
    for line in lines:
        m = FENCE_RE.match(line)
        if fence is None:
            if m and not (m.group(1)[0] == "`" and "`" in m.group(2)):
                fence = m.group(1)
                flags.append(False)
            else:
                flags.append(True)
        else:
            # CommonMark: a fence closes only on the same character, at least as long.
            if m and m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence) and not m.group(2).strip():
                fence = None
            flags.append(False)
    return flags


def strip_inline_code(line: str) -> str:
    return re.sub(r"(`+)(?:(?!\1).)+?\1", "", line)


def heading_text(heading: str) -> str:
    """The plain text GitHub renders for a heading's Markdown source."""
    text = heading.strip()
    code: list[str] = []

    def keep_code(m: re.Match[str]) -> str:
        code.append(m.group(2).strip())
        return f"\0{len(code) - 1}\0"

    text = re.sub(r"(`+)(.+?)\1", keep_code, text)  # code spans keep _ and * as typed
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", text)  # links and images -> their text
    text = re.sub(r"<[^>]+>", "", text)  # inline HTML
    text = text.replace("*", "").replace("~", "")
    # Paired _emphasis_ loses its underscores; MAX_SPEED and _private_field keep theirs.
    text = re.sub(r"(?<![^\W_])(_+)(?=\S)(.+?)(?<=\S)\1(?![^\W_])", r"\2", text)
    return re.sub(r"\0(\d+)\0", lambda m: code[int(m.group(1))], text)


def github_slug(heading: str) -> str:
    """github-slugger's rule: lower case, keep letters, marks, digits, '_', '-' and spaces."""
    def keep(c: str) -> bool:
        cat = unicodedata.category(c)
        return c in " -" or cat[0] in "LM" or cat in ("Nd", "Nl", "Pc")

    return "".join(c for c in heading_text(heading).lower() if keep(c)).replace(" ", "-")


def anchors_of(text: str) -> set[str]:
    lines = text.split("\n")
    plain = outside_fences(lines)
    out: set[str] = set()
    occurrences: dict[str, int] = {}

    def add(heading: str) -> None:
        # github-slugger: on a clash, bump the base slug's counter until the result is unused.
        base = slug = github_slug(heading)
        while slug in occurrences:
            occurrences[base] += 1
            slug = f"{base}-{occurrences[base]}"
        occurrences[slug] = 0
        out.add(slug)

    for i, line in enumerate(lines):
        if not plain[i]:
            continue
        out.update(a.lower() for a in HTML_ID_RE.findall(line))
        m = ATX_RE.match(line)
        if m:
            add(m.group(1) or "")
            continue
        prev = lines[i - 1] if i > 0 else ""
        if (SETEXT_RE.match(line) and i > 0 and plain[i - 1] and prev.strip()
                and not prev.lstrip().startswith(("|", "-", "*", "+", ">", "#"))
                and not SETEXT_RE.match(prev)):
            add(prev)
    return out


def norm_status(text: str) -> str:
    s = text.strip().strip("*_` ").lower()
    for dash in (" -- ", " – ", " - "):
        s = s.replace(dash, " — ")
    return re.sub(r"\s+", " ", s)


def normalize_for_compare(text: str) -> str:
    # Internal doc links and section refs change on migration ("§6.10" -> "[combo](...)"),
    # so both are dropped; external links keep their text.
    text = re.sub(r"\[[^\]]*\]\((?![a-z][a-z0-9+.-]*:)[^)]*\)", "", text, flags=re.I)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"§\s*\d+(?:\.\d+)*(?:\s*[–-]\s*\d+(?:\.\d+)*)?", "", text)
    text = re.sub(r"[*_`>#|]", " ", text)
    text = re.sub(r"^\s*([-+]|\d+\.)\s+(\[[ xX]\]\s+)?", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def number_key(s: str) -> float:
    try:
        return float(s.replace(",", "."))
    except ValueError:
        return float("inf")


def is_regular_file(path: Path) -> bool:
    try:
        return stat.S_ISREG(path.stat().st_mode)
    except OSError:
        return False


# --------------------------------------------------------------------------
# Checker
# --------------------------------------------------------------------------


class Checker:
    def __init__(self, root: Path, gdd_name: str | None, old: list[Path]) -> None:
        self.root = Path(os.path.normpath(str(root.resolve())))
        self.gdd_name = gdd_name
        self.old = [Path(os.path.normpath(str(p.resolve()))) for p in old]
        self.issues: list[Issue] = []
        self.files_checked = 0
        self._text: dict[Path, str | None] = {}
        self._anchors: dict[Path, set[str] | None] = {}

    # -- reporting -----------------------------------------------------------

    def show(self, path: Path) -> str:
        try:
            return Path(os.path.relpath(path, self.root)).as_posix()
        except ValueError:  # another drive on Windows
            return path.as_posix()

    def add(self, level: str, code: str, path: Path, line: int | None, message: str, fix: str) -> None:
        self.issues.append(Issue(level, code, self.show(path), line, message, fix))

    def error(self, code: str, path: Path, line: int | None, message: str, fix: str) -> None:
        self.add("ERROR", code, path, line, message, fix)

    def warn(self, code: str, path: Path, line: int | None, message: str, fix: str) -> None:
        self.add("WARNING", code, path, line, message, fix)

    def note(self, code: str, path: Path, line: int | None, message: str) -> None:
        self.add("NOTE", code, path, line, message, "No action needed.")

    # -- reading -------------------------------------------------------------

    def read(self, path: Path, report: bool = True) -> str | None:
        """Text of a regular file, or None when it can't be read. Never raises, never blocks."""
        if path in self._text:
            return self._text[path]
        text: str | None = None
        problem = None
        if not is_regular_file(path):  # dangling symlink, FIFO, device: opening could fail or hang
            problem = "not a regular file"
        else:
            try:
                raw = path.read_bytes()
            except OSError as exc:
                problem = str(exc.strerror or exc)
            else:
                try:
                    text = raw.decode("utf-8-sig")
                except UnicodeDecodeError as exc:
                    text = raw.decode("utf-8-sig", errors="replace")
                    if report:
                        line = raw[: exc.start].count(b"\n") + 1
                        self.warn("not-utf8", path, line, "file is not valid UTF-8; bad bytes were read as '\ufffd'",
                                  "Re-save the file as UTF-8 so non-ASCII text shows correctly on GitHub and in editors.")
                text = text.replace("\r\n", "\n").replace("\r", "\n")
        if problem and report:
            self.warn("unreadable", path, None, f"cannot read file ({problem})",
                      "Check that it is a regular file you can read, or move it out of the docs folder.")
        self._text[path] = text
        return text

    def anchors(self, path: Path) -> set[str] | None:
        if path not in self._anchors:
            text = self.read(path, report=False) if is_regular_file(path) else None
            self._anchors[path] = anchors_of(text) if text is not None else None
        return self._anchors[path]

    # -- discovery -----------------------------------------------------------

    def find_root_file(self, name: str) -> Path | None:
        try:
            entries = list(self.root.iterdir())
        except OSError:
            return None
        for entry in entries:
            if entry.name.lower() == name.lower() and entry.is_file():
                return entry
        return None

    def markdown_files(self) -> list[Path]:
        found: list[Path] = []
        for dirpath, dirnames, filenames in os.walk(self.root):
            dirnames[:] = sorted(d for d in dirnames if not d.startswith(".") and d not in SKIP_DIRS)
            for name in sorted(filenames):
                if name.lower().endswith(".md"):
                    path = Path(os.path.normpath(os.path.join(dirpath, name)))
                    if path not in self.old:
                        found.append(path)
        return found

    # -- checks --------------------------------------------------------------

    def run(self) -> None:
        if not self.root.is_dir():
            raise UsageProblem(f"{self.root}: not a folder")
        for old in self.old:
            if not old.is_file():
                raise UsageProblem(f"--old {old}: file not found")

        if self.gdd_name:
            gdd: Path | None = Path(os.path.normpath(str(self.root / self.gdd_name)))
            if not gdd.is_file():
                raise UsageProblem(f"--gdd {self.gdd_name}: no such file in {self.root}")
        else:
            gdd = self.find_root_file("GDD.md")
        features_dir = self.root / "features"
        if gdd is None and not features_dir.is_dir():
            raise UsageProblem(
                f"{self.root}: no GDD.md and no features/ folder; pass the docs folder, or name the GDD with --gdd")

        md_files = self.markdown_files()
        for path in md_files:
            self.read(path)
        self.files_checked = len(md_files)

        self.check_links(md_files)

        if gdd is None:
            self.warn("gdd-missing", self.root, None, "no GDD.md in the docs folder",
                      "Create the GDD from references/gdd-template.md, or pass its file name with --gdd.")

        folders = self.feature_folders(features_dir)
        statuses = {slug: self.check_feature(features_dir / slug, slug) for slug in folders}

        if gdd is not None:
            self.check_index(gdd, folders, statuses)

        if self.old:
            self.check_old(md_files)

    def check_links(self, md_files: list[Path]) -> None:
        for path in md_files:
            text = self._text.get(path)
            if text is None:
                continue
            lines = text.split("\n")
            plain = outside_fences(lines)
            for lineno, line in enumerate(lines, 1):
                if not plain[lineno - 1]:
                    continue
                for m in LINK_RE.finditer(strip_inline_code(line)):
                    target = m.group(1)
                    if target.startswith("<"):
                        target = target[1:-1].strip()
                    if not target or SCHEME_RE.match(target):  # http:, mailto:, ...
                        continue
                    file_part, _, anchor = target.partition("#")
                    file_part = unquote(file_part.split("?", 1)[0])
                    anchor = unquote(anchor)
                    if file_part.startswith("/"):
                        self.warn("absolute-link", path, lineno, f"absolute link -> {target}",
                                  "Use a relative link (../GDD.md) so it works on GitHub, in editors and offline.")
                        continue
                    dest = path if not file_part else Path(os.path.normpath(str(path.parent / file_part)))
                    if not dest.exists():
                        self.error("broken-link", path, lineno, f"broken link -> {target}",
                                   "Fix the path (relative to this file) or create the missing file.")
                        continue
                    if anchor and dest.suffix.lower() == ".md":
                        found = self.anchors(dest)
                        if found is not None and anchor.lower() not in found:
                            self.warn("anchor-not-found", path, lineno, f"anchor not found -> {target}",
                                      "Match the heading's GitHub anchor: lower case, punctuation dropped,"
                                      " spaces as '-' (\"## 3. Feature index\" is #3-feature-index).")

    def feature_folders(self, features_dir: Path) -> list[str]:
        if not features_dir.is_dir():
            return []
        try:
            entries = sorted(features_dir.iterdir())
        except OSError:
            return []
        folders = [e.name for e in entries if e.is_dir() and not e.name.startswith(".")]
        for slug in folders:
            if not SLUG_RE.match(slug):
                self.warn("slug-not-kebab", features_dir / slug, None, f"slug '{slug}' is not lowercase kebab-case",
                          "Use a short kebab-case noun for new features; don't rename existing ones (links depend on them).")
        return folders

    def check_feature(self, fdir: Path, slug: str) -> str | None:
        parts: list[str] = []
        status: str | None = None
        design = fdir / "design.md"
        design_text = self.read(design) if design.is_file() else None
        if not design.is_file():
            self.error("design-missing", fdir, None, f"features/{slug}/ has no design.md",
                       "Create design.md from references/feature-templates.md; it holds the feature's status.")
        elif design_text is not None:
            m = STATUS_RE.search(design_text)
            if m:
                status = norm_status(m.group(1))
            else:
                self.error("design-no-status", design, 1, "no '**Status:** ...' in the header",
                           "Add '**Status:** <status>' to the header line, matching the GDD index.")
        if status in HAS_CODE:
            for doc in CODE_DOCS:
                if not (fdir / doc).is_file():
                    self.warn("feature-doc-missing", fdir, None, f"features/{slug}/ is '{status}' but has no {doc}",
                              f"Write {doc} from references/feature-templates.md against the real code,"
                              " or tell the user the project keeps design notes only.")
        testing = fdir / "testing.md"
        testing_text = self.read(testing) if testing.is_file() else None
        if testing_text is not None:
            total = proven = 0
            lines = testing_text.split("\n")
            plain = outside_fences(lines)
            for lineno, line in enumerate(lines, 1):
                m = CRIT_RE.match(line)
                if not m or not plain[lineno - 1]:
                    continue
                total += 1
                if m.group(1) in "xX":
                    proven += 1
                    if not PROOF_RE.search(m.group(2)):
                        self.warn("ticked-no-proof", testing, lineno, "ticked criterion has no proof in (...)",
                                  "Name the test or dated check in parentheses at the end, or untick it.")
            parts.append(f"{proven}/{total} criteria proven")
        assumptions = 0
        for doc in ("design.md", *CODE_DOCS):
            text = self._text.get(Path(os.path.normpath(str(fdir / doc))))
            if text:
                assumptions += text.count("[ASSUMPTION]")
        if assumptions:
            parts.append(f"{assumptions} [ASSUMPTION]")
        summary = " · ".join([status or "no status"] + parts)
        self.note("feature-summary", fdir, None, f"{slug}: {summary}")
        return status

    def parse_index(self, text: str) -> list[dict[str, object]] | None:
        """Rows of the first table whose header has Feature and Status columns."""
        lines = text.split("\n")
        plain = outside_fences(lines)
        for i, line in enumerate(lines):
            if not plain[i] or not line.strip().startswith("|"):
                continue
            cells = [c.strip().lower() for c in line.strip().strip("|").split("|")]
            if not ("feature" in cells and "status" in cells and i + 1 < len(lines)
                    and re.match(r"^\s*\|?\s*:?-", lines[i + 1])):
                continue
            fi, si = cells.index("feature"), cells.index("status")
            di = cells.index("docs") if "docs" in cells else None  # summaries may link other features
            rows: list[dict[str, object]] = []
            for j in range(i + 2, len(lines)):
                row = lines[j].strip()
                if not row.startswith("|"):
                    break
                rc = [c.strip() for c in row.strip("|").split("|")]
                if len(rc) <= max(fi, si):
                    continue
                where = rc[di] if di is not None and di < len(rc) else row
                slugs = set(re.findall(r"features/([^/)\s#]+)/", where))
                rows.append({"line": j + 1, "feature": rc[fi], "status": norm_status(rc[si]), "slugs": slugs,
                             "linked": "](" in where})
            return rows
        return None

    def check_index(self, gdd: Path, folders: list[str], statuses: dict[str, str | None]) -> None:
        text = self.read(gdd)
        if text is None:
            return
        index = self.parse_index(text)
        if index is None:
            self.note("gdd-no-index", gdd, None,
                      "no feature index table (Feature and Status columns); index checks skipped."
                      " Normal for a GDD that is not in this layout: edit it in place")
            return
        indexed: set[str] = set()
        for row in index:
            line, feature, status = int(row["line"]), row["feature"], str(row["status"])
            slugs = sorted(row["slugs"])  # type: ignore[arg-type]
            if status not in STATUSES:
                self.warn("unknown-status", gdd, line, f"'{feature}' has unknown status '{status}'",
                          "Use one of: " + ", ".join(STATUSES) + ".")
            # A row that links other docs (spec-kit or Kiro specs) is documented elsewhere.
            if not slugs and not row["linked"] and status not in ("idea", "cut"):
                self.warn("row-no-folder", gdd, line, f"'{feature}' is '{status}' but links no feature docs",
                          "Link its features/<slug>/design.md, or set the status to idea if no folder exists yet.")
            for slug in slugs:
                indexed.add(slug)
                if slug not in folders:
                    self.error("index-folder-missing", gdd, line, f"'{feature}' links features/{slug}/, which doesn't exist",
                               "Create the feature folder, or fix the slug in the link.")
                elif statuses.get(slug) and statuses[slug] != status:
                    self.error("status-mismatch", gdd, line,
                               f"'{feature}': GDD index says '{status}', features/{slug}/design.md says '{statuses[slug]}'",
                               "Set the same status in both places.")
        for slug in folders:
            if slug not in indexed:
                self.warn("folder-not-indexed", self.root / "features" / slug, None,
                          f"features/{slug}/ is not in the GDD feature index",
                          "Add a row for it to the GDD's feature index, linking its design.md.")

    def check_old(self, md_files: list[Path]) -> None:
        # Originals parked in archive/ must not count as "found", or a lost line would hide there.
        current = [p for p in md_files if p.relative_to(self.root).parts[0] != "archive"]
        new_lines = [normalize_for_compare(line) for p in current for line in (self._text.get(p) or "").split("\n")]
        new_blob = " ".join(new_lines)
        new_numbers = set(NUMBER_RE.findall(new_blob))
        for old in self.old:
            text = self.read(old)
            if text is None:
                continue
            missing_lines = 0
            missing_nums: set[str] = set()
            for lineno, line in enumerate(text.split("\n"), 1):
                if re.match(r"^\s*(#|```|~~~|\|?\s*:?-{3})", line):
                    continue
                # table rows are compared cell by cell; prose line by line
                chunks = line.strip().strip("|").split("|") if line.strip().startswith("|") else [line]
                for chunk in chunks:
                    n = normalize_for_compare(chunk)
                    if len(n) < 20:
                        continue
                    if n not in new_blob:
                        missing_lines += 1
                        self.warn("old-line-missing", old, lineno, f"not found verbatim in the new docs: {chunk.strip()[:110]}",
                                  "Check it was moved (reworded is fine) and put it back if it was lost.")
                    missing_nums.update(x for x in NUMBER_RE.findall(n) if x not in new_numbers)
            if missing_nums:
                nums = ", ".join(sorted(missing_nums, key=number_key))
                self.warn("old-number-missing", old, None, f"numbers that appear nowhere in the new docs: {nums}",
                          "Find each number's old line; a lost number is usually a lost rule or tuning value.")
            if not missing_lines and not missing_nums:
                self.note("old-all-found", old, None, "all content found in the new docs")


# --------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------


def split_issues(issues: list[Issue]) -> tuple[list[Issue], list[Issue], list[Issue]]:
    def key(i: Issue) -> tuple[str, int]:
        return (i.file, i.line or 0)

    by = {lvl: sorted((i for i in issues if i.level == lvl), key=key) for lvl in ("ERROR", "WARNING", "NOTE")}
    return by["ERROR"], by["WARNING"], by["NOTE"]


def limit(checker: Checker, max_issues: int) -> tuple[list[Issue], list[Issue], list[Issue], int]:
    errors, warnings, notes = split_issues(checker.issues)
    if max_issues <= 0:
        return errors, warnings, notes, 0
    e = errors[:max_issues]
    w = warnings[: max(0, max_issues - len(e))]
    n = notes[: max(0, max_issues - len(e) - len(w))]
    return e, w, n, len(errors) + len(warnings) + len(notes) - len(e) - len(w) - len(n)


def render_text(checker: Checker, max_issues: int) -> str:
    errors, warnings, notes = split_issues(checker.issues)
    e, w, n, omitted = limit(checker, max_issues)
    lines: list[str] = []
    for issue in e + w + n:
        where = f"{issue.file}:{issue.line}" if issue.line is not None else issue.file
        lines.append(f"{issue.level} {where}: {issue.message}")
        if issue.level != "NOTE":
            lines.append(f"  fix: {issue.fix}")
    if omitted:
        lines.append(f"... and {omitted} more (rerun with --max-issues 0 to see all)")
    lines.append(f"Summary: {len(errors)} errors, {len(warnings)} warnings in {checker.files_checked} files checked")
    if notes:
        lines.append(f"Notes: {len(notes)} informational findings (do not affect --strict)")
    return "\n".join(lines)


def render_json(checker: Checker, max_issues: int) -> str:
    errors, warnings, notes = split_issues(checker.issues)
    e, w, n, omitted = limit(checker, max_issues)
    payload = {
        "tool": TOOL,
        "schema": SCHEMA,
        "root": checker.root.as_posix(),
        "files_checked": checker.files_checked,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "note_count": len(notes),
        "errors": [i.as_json() for i in e],
        "warnings": [i.as_json() for i in w],
        "notes": [i.as_json() for i in n],
        "truncated": omitted > 0,
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="check_docs.py",
        description=__doc__,
        epilog=(
            "examples:\n"
            "  python scripts/check_docs.py docs\n"
            "  python scripts/check_docs.py design --gdd game-design.md\n"
            "  python scripts/check_docs.py docs --old ../scratch/old-GDD.md --max-issues 0\n"
            "  python scripts/check_docs.py docs --json --strict"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("docs_dir", metavar="DOCS_DIR", help="the docs folder that holds the GDD and features/")
    parser.add_argument("--gdd", metavar="FILE", help="GDD file name inside DOCS_DIR (default: GDD.md, any case)")
    parser.add_argument("--old", action="append", default=[], metavar="FILE",
                        help="pre-migration doc to compare against; repeat for several (keep them outside DOCS_DIR)")
    parser.add_argument("--json", action="store_true", help="print one JSON object instead of text")
    parser.add_argument("--strict", action="store_true", help="exit 1 on warnings too")
    parser.add_argument("--max-issues", type=int, default=50, metavar="N",
                        help="print at most N issues (default 50, 0 = no limit); totals are unchanged")
    return parser


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.max_issues < 0:
        parser.error("--max-issues must be 0 or more")
    target = Path(args.docs_dir)
    if not target.is_dir():
        print(f"{TOOL}: {target}: folder not found", file=sys.stderr)
        return 2
    checker = Checker(target, args.gdd, [Path(p) for p in args.old])
    try:
        checker.run()
    except UsageProblem as exc:
        print(f"{TOOL}: {exc}", file=sys.stderr)
        return 2
    print(render_json(checker, args.max_issues) if args.json else render_text(checker, args.max_issues))
    errors, warnings, _ = split_issues(checker.issues)
    if errors or (args.strict and warnings):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
