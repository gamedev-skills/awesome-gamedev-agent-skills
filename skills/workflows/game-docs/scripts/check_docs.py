#!/usr/bin/env python3
"""Check a game docs folder (GDD.md + ARCHITECTURE.md + features/<slug>/{design,implementation,testing}.md).

Usage:
    python check_docs.py <docs-dir>
    python check_docs.py <docs-dir> --old <old-GDD.md> [<old-notes.md> ...]

Reports:
  ERROR  broken relative links, feature folders missing a doc, GDD index rows
         without folders (and folders without rows), status mismatch between the
         GDD index and design.md
  WARN   unknown statuses, broken #anchors, ticked criteria with no proof,
         missing GDD/ARCHITECTURE
  INFO   per-feature summary: status, criteria proven, open assumptions
With --old: lines and numbers from the old docs that don't appear anywhere in
the new docs (migration safety net; reworded content shows up too, review each).

Exit code 1 if any ERROR.
"""
import argparse
import os
import re
import sys

STATUSES = ["idea", "designed", "in progress", "implemented", "changed — code pending", "cut"]
FEATURE_DOCS = ["design.md", "implementation.md", "testing.md"]

LINK_RE = re.compile(r"(?<!\!)\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
STATUS_RE = re.compile(r"\*\*Status:\*\*\s*([^·|\n]+)")
CRIT_RE = re.compile(r"^\s*[-*]\s+\[([ xX])\]\s+(.*)$")

errors, warns, infos = [], [], []


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def rel(path, root):
    return os.path.relpath(path, root).replace("\\", "/")


def norm_status(s):
    s = s.strip().strip("*_` ").lower()
    s = s.replace(" - ", " — ").replace(" -- ", " — ").replace(" – ", " — ")
    return s


def slugify(heading):
    """GitHub-style anchor."""
    h = heading.strip().lower()
    h = re.sub(r"[`*_~]", "", h)
    h = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", h)
    h = re.sub(r"[^\w\- ]", "", h, flags=re.UNICODE)
    return h.replace(" ", "-")


def anchors_of(text):
    out, seen = set(), {}
    in_code = False
    for line in text.splitlines():
        if line.lstrip().startswith(("```", "~~~")):
            in_code = not in_code
            continue
        if in_code:
            continue
        m = re.match(r"^#{1,6}\s+(.*?)\s*#*\s*$", line)
        if m:
            base = slugify(m.group(1))
            n = seen.get(base, 0)
            seen[base] = n + 1
            out.add(base if n == 0 else "%s-%d" % (base, n))
    return out


def strip_code(text):
    """Blank out fenced code blocks and inline code so templates/examples aren't link-checked."""
    lines, in_code = [], False
    for line in text.splitlines():
        if line.lstrip().startswith(("```", "~~~")):
            in_code = not in_code
            lines.append("")
            continue
        lines.append("" if in_code else re.sub(r"`[^`]*`", "", line))
    return lines


def check_links(md_files, root):
    anchor_cache = {}
    for path in md_files:
        for lineno, line in enumerate(strip_code(read(path)), 1):
            for m in LINK_RE.finditer(line):
                target = m.group(2)
                if re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I):  # http:, mailto:, …
                    continue
                file_part, _, anchor = target.partition("#")
                dest = path if not file_part else os.path.normpath(os.path.join(os.path.dirname(path), file_part))
                where = "%s:%d" % (rel(path, root), lineno)
                if not os.path.exists(dest):
                    errors.append("%s broken link -> %s" % (where, target))
                    continue
                if anchor and dest.endswith(".md"):
                    if dest not in anchor_cache:
                        anchor_cache[dest] = anchors_of(read(dest))
                    if anchor.lower() not in anchor_cache[dest]:
                        warns.append("%s anchor not found -> %s" % (where, target))


def parse_index(gdd_text):
    """Rows of the first table whose header has 'Feature' and 'Status' columns."""
    lines = gdd_text.splitlines()
    for i, line in enumerate(lines):
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip().lower() for c in line.strip().strip("|").split("|")]
        if "feature" in cells and "status" in cells and i + 1 < len(lines) and re.match(r"^\s*\|?\s*:?-", lines[i + 1]):
            fi, si = cells.index("feature"), cells.index("status")
            di = cells.index("docs") if "docs" in cells else None  # summaries may link other features
            rows = []
            for j in range(i + 2, len(lines)):
                row = lines[j].strip()
                if not row.startswith("|"):
                    break
                rc = [c.strip() for c in row.strip("|").split("|")]
                if len(rc) <= max(fi, si):
                    continue
                where = rc[di] if di is not None and di < len(rc) else row
                slugs = set(re.findall(r"features/([^/)\s]+)/", where))
                rows.append({"line": j + 1, "feature": rc[fi], "status": norm_status(rc[si]), "slugs": slugs})
            return rows
    return None


def feature_summary(fdir, slug):
    parts = []
    design = os.path.join(fdir, "design.md")
    status = None
    if os.path.exists(design):
        m = STATUS_RE.search(read(design))
        if m:
            status = norm_status(m.group(1))
        else:
            errors.append("features/%s/design.md has no '**Status:** …' in its header" % slug)
    testing = os.path.join(fdir, "testing.md")
    if os.path.exists(testing):
        total = proven = 0
        for lineno, line in enumerate(read(testing).splitlines(), 1):
            m = CRIT_RE.match(line)
            if not m:
                continue
            total += 1
            if m.group(1) in "xX":
                proven += 1
                if not re.search(r"\(.+\)\s*\**\s*$", m.group(2)):  # greedy: a proof may contain a link
                    warns.append("features/%s/testing.md:%d ticked criterion has no proof in (…)" % (slug, lineno))
        parts.append("%d/%d criteria proven" % (proven, total))
    assumptions = sum(read(os.path.join(fdir, d)).count("[ASSUMPTION]") for d in FEATURE_DOCS if os.path.exists(os.path.join(fdir, d)))
    if assumptions:
        parts.append("%d [ASSUMPTION]" % assumptions)
    return status, parts


def normalize_for_compare(text):
    # Internal doc links and section refs are expected to change on migration ("§6.10" -> "[combo](...)"),
    # so both are dropped; external links keep their text.
    text = re.sub(r"\[[^\]]*\]\((?![a-z][a-z0-9+.-]*:)[^)]*\)", "", text, flags=re.I)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"§\s*\d+(?:\.\d+)*(?:\s*[–-]\s*\d+(?:\.\d+)*)?", "", text)
    text = re.sub(r"[*_`>#|]", " ", text)
    text = re.sub(r"^\s*([-+]|\d+\.)\s+(\[[ xX]\]\s+)?", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def check_old(old_paths, md_files):
    new_blob = " ".join(normalize_for_compare(l) for p in md_files for l in read(p).splitlines())
    new_numbers = set(re.findall(r"\d+(?:[.,]\d+)?", new_blob))
    for old in old_paths:
        missing_lines, missing_nums = [], set()
        for lineno, line in enumerate(read(old).splitlines(), 1):
            if re.match(r"^\s*(#|```|~~~|\|?\s*:?-{3})", line):
                continue
            # table rows are compared cell by cell; prose line by line
            chunks = line.strip().strip("|").split("|") if line.strip().startswith("|") else [line]
            for chunk in chunks:
                n = normalize_for_compare(chunk)
                if len(n) < 20:
                    continue
                if n not in new_blob:
                    missing_lines.append((lineno, chunk.strip()[:110]))
                missing_nums.update(x for x in re.findall(r"\d+(?:[.,]\d+)?", n) if x not in new_numbers)
        name = os.path.basename(old)
        if missing_lines:
            warns.append("--old %s: %d line(s)/cell(s) not found verbatim in new docs:" % (name, len(missing_lines)))
            warns.extend("    %s:%d  %s" % (name, ln, txt) for ln, txt in missing_lines)
        if missing_nums:
            errors.append("--old %s: numbers that appear nowhere in the new docs: %s" % (name, ", ".join(sorted(missing_nums, key=lambda s: float(s.replace(",", "."))))))
        if not missing_lines and not missing_nums:
            infos.append("--old %s: all content found in new docs" % name)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("docs")
    ap.add_argument("--old", nargs="+", default=[], help="pre-migration docs to compare against (keep them outside docs/)")
    args = ap.parse_args()
    root = os.path.abspath(args.docs)
    if not os.path.isdir(root):
        sys.exit("not a directory: %s" % root)

    md_files = []
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if not d.startswith(".")]
        md_files += [os.path.join(dp, f) for f in fn if f.lower().endswith(".md")]
    old_abs = {os.path.abspath(p) for p in args.old}
    md_files = sorted(p for p in md_files if os.path.abspath(p) not in old_abs)

    check_links(md_files, root)

    gdd = os.path.join(root, "GDD.md")
    if not os.path.exists(os.path.join(root, "ARCHITECTURE.md")):
        warns.append("no ARCHITECTURE.md")
    index = None
    if os.path.exists(gdd):
        index = parse_index(read(gdd))
        if index is None:
            errors.append("GDD.md has no feature index table (a table with 'Feature' and 'Status' columns)")
    else:
        warns.append("no GDD.md")

    fdir = os.path.join(root, "features")
    folders = sorted(d for d in os.listdir(fdir) if os.path.isdir(os.path.join(fdir, d))) if os.path.isdir(fdir) else []
    for slug in folders:
        for doc in FEATURE_DOCS:
            if not os.path.exists(os.path.join(fdir, slug, doc)):
                errors.append("features/%s/ is missing %s" % (slug, doc))
        if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", slug):
            warns.append("features/%s: slug should be lowercase kebab-case" % slug)

    statuses = {}
    for slug in folders:
        statuses[slug], parts = feature_summary(os.path.join(fdir, slug), slug)
        infos.append("%-24s %-24s %s" % (slug, statuses[slug] or "?", " · ".join(parts)))

    if index is not None:
        indexed = set()
        for row in index:
            if row["status"] not in STATUSES:
                warns.append("GDD.md:%d '%s' has unknown status '%s' (use: %s)" % (row["line"], row["feature"], row["status"], ", ".join(STATUSES)))
            if not row["slugs"] and row["status"] not in ("idea", "cut"):
                warns.append("GDD.md:%d '%s' is '%s' but links no feature folder" % (row["line"], row["feature"], row["status"]))
            for slug in row["slugs"]:
                indexed.add(slug)
                if slug not in folders:
                    errors.append("GDD.md:%d '%s' links features/%s/ which doesn't exist" % (row["line"], row["feature"], slug))
                elif statuses.get(slug) and statuses[slug] != row["status"]:
                    errors.append("status mismatch for %s: GDD index says '%s', design.md says '%s'" % (slug, row["status"], statuses[slug]))
        for slug in folders:
            if slug not in indexed:
                errors.append("features/%s/ is not in the GDD feature index" % slug)

    if args.old:
        check_old(args.old, md_files)

    for label, items in (("INFO ", infos), ("WARN ", warns), ("ERROR", errors)):
        for item in items:
            print("%s %s" % (label, item))
    print("\n%d file(s), %d feature(s): %d error(s), %d warning(s)" % (len(md_files), len(folders), len(errors), len([w for w in warns if not w.startswith("    ")])))
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
