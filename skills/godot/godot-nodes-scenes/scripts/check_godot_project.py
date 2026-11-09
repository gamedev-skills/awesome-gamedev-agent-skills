#!/usr/bin/env python3
"""Check a Godot 4.x project for broken file references. Read-only.

Run it after creating, moving or renaming scenes, resources or scripts. It
reads the project's text files and reports references that Godot will fail
to load. It never edits anything and needs no Godot binary.

What it checks:

* ``[ext_resource]`` entries in ``.tscn``/``.tres`` files. Godot loads the
  ``uid`` first and falls back to ``path`` when the uid is unknown, so:
  uid resolves -> OK (a stale or different ``path`` is only a warning);
  uid unknown and ``path`` missing -> error; ``path`` exists but the uid is
  unknown -> warning (Godot prints "invalid UID" and fixes it on save).
  Uids are read from text headers, ``.import``/``.uid`` files and
  uncompressed binary resources; compressed ``.scn``/``.res`` files hide
  theirs, so a uid that might belong to one is only a warning.
* ``res://`` paths whose letter case differs from the file on disk. This
  works in the editor on Windows and macOS but breaks on Linux and in
  exported ``.pck`` files, which are case-sensitive.
* ``ExtResource("id")`` / ``SubResource("id")`` uses with no matching
  declaration, sub-resources used before they are declared, malformed
  ``[ext_resource]`` headers and duplicate ids in one file.
* The same uid claimed by two files (``.tscn``/``.tres`` headers,
  ``.import`` files and ``.uid`` sidecar files).
* Scene trees: exactly one root node, every ``parent=`` path declared
  earlier in the scene, and every ``[connection]`` ``from``/``to`` node.
  Nodes inside instanced or inherited scenes are followed through their
  ``.tscn`` files; paths inside scenes that cannot be read (imported
  ``.glb``/``.blend`` models, binary ``.scn``) are skipped, not guessed.
  A stale path that Godot 4.6+ can recover through ``parent_id_path`` /
  ``from_uid_path`` / ``to_uid_path`` is a warning.
* ``project.godot``: ``application/run/main_scene`` (``res://`` or
  ``uid://``), ``[autoload]`` entries and other ``res://`` setting values.
* ``.gd`` scripts: string-literal paths in ``preload()``, ``load()``,
  ``change_scene_to_file()`` and ``extends "..."`` (warnings).
* ``.uid`` and ``.import`` files left behind after their source file was
  moved or deleted (warnings).

Folders Godot does not scan are skipped the same way: the project data
folder (``.godot/``), hidden files and folders, folders containing a
``.gdignore`` file and folders containing another ``project.godot``.
Addons are ordinary project files and are checked.

Exit codes: 0 no errors, 1 errors (or warnings with --strict),
2 usage problem or no project.godot found.
"""

from __future__ import annotations

import argparse
import json
import os
import posixpath
import re
import struct
import sys
from dataclasses import dataclass, field
from pathlib import Path

TOOL = "check_godot_project"
SCHEMA = 1

TEXT_RESOURCE_EXTS = {".tscn", ".tres"}
SCRIPT_CALL_RE = re.compile(
    r"""\b(preload|load|load_threaded_request|change_scene_to_file)\s*\(\s*(["'])((?:res|uid)://[^"'\n]*)\2\s*\)"""
)
EXTENDS_RE = re.compile(r"""^\s*extends\s+(["'])((?:res|uid)://[^"'\n]*)\1""")
TOKEN_RE = re.compile(r'"|\n|[\[\](){}]|\b(?:ExtResource|SubResource)\b')
REF_RE = re.compile(r'(ExtResource|SubResource)\s*\(\s*(?:"((?:[^"\\]|\\.)*)"|(\d+))\s*\)')
PROJECT_STRING_RE = re.compile(r'"((?:res|uid)://(?:[^"\\]|\\.)*)"')


@dataclass
class Issue:
    severity: str  # "error" or "warning"
    code: str
    file: str
    line: int | None
    message: str
    fix: str

    def as_dict(self) -> dict:
        return {
            "code": self.code,
            "file": self.file,
            "line": self.line,
            "message": self.message,
            "fix": self.fix,
        }


# ---------------------------------------------------------------- text helpers


def display_text(value: str) -> str:
    """Keep source-controlled strings inside one terminal line; JSON keeps raw values."""
    escapes = {"\n": "\\n", "\r": "\\r", "\t": "\\t",
               "\u2028": "\\u2028", "\u2029": "\\u2029"}
    return "".join(
        escapes.get(ch, f"\\x{ord(ch):02x}")
        if ch in escapes or ord(ch) < 0x20 or 0x7f <= ord(ch) <= 0x9f else ch
        for ch in value
    )


def read_text(path: Path) -> str:
    """Read a text file, tolerating a UTF-8 BOM, CRLF line endings and bad bytes."""
    data = path.read_bytes()
    text = data.decode("utf-8", errors="replace")
    if text.startswith("\ufeff"):
        text = text[1:]
    return text.replace("\r\n", "\n").replace("\r", "\n")


def unescape(value: str) -> str:
    out = []
    i = 0
    while i < len(value):
        ch = value[i]
        if ch == "\\" and i + 1 < len(value):
            nxt = value[i + 1]
            out.append({"n": "\n", "t": "\t", "r": "\r"}.get(nxt, nxt))
            i += 2
        else:
            out.append(ch)
            i += 1
    return "".join(out)


def parse_header(line: str) -> tuple[str, dict[str, str]]:
    """Parse ``[tag key=value ...]`` into a tag name and raw attribute values.

    Quoted values are unescaped; other values (``ExtResource("1")``,
    ``PackedStringArray(...)``, numbers) are kept as written.
    """
    body = line.strip()
    if body.startswith("["):
        body = body[1:]
    if body.endswith("]"):
        body = body[:-1]
    i = 0
    n = len(body)
    while i < n and not body[i].isspace():
        i += 1
    tag = body[:i]
    attrs: dict[str, str] = {}
    while i < n:
        while i < n and body[i].isspace():
            i += 1
        start = i
        while i < n and body[i] not in "= \t":
            i += 1
        key = body[start:i]
        if i >= n or body[i] != "=":
            break
        i += 1
        if i < n and body[i] == '"':
            j = i + 1
            while j < n and body[j] != '"':
                j += 2 if body[j] == "\\" else 1
            attrs[key] = unescape(body[i + 1 : j])
            i = j + 1
            continue
        start = i
        depth = 0
        while i < n:
            ch = body[i]
            if ch == '"':
                i += 1
                while i < n and body[i] != '"':
                    i += 2 if body[i] == "\\" else 1
            elif ch in "([{":
                depth += 1
            elif ch in ")]}":
                depth -= 1
            elif ch.isspace() and depth <= 0:
                break
            i += 1
        attrs[key] = body[start:i]
    return tag, attrs


def ref_id(raw: str | None) -> str | None:
    """Return the id inside ``ExtResource("id")`` / ``SubResource("id")``."""
    if not raw:
        return None
    m = REF_RE.match(raw.strip())
    if not m:
        return None
    return unescape(m.group(2)) if m.group(2) is not None else m.group(3)


@dataclass
class Section:
    tag: str
    attrs: dict[str, str]
    line: int
    offset: int


@dataclass
class Ref:
    kind: str  # ExtResource or SubResource
    rid: str
    line: int
    offset: int


@dataclass
class ParsedResource:
    sections: list[Section] = field(default_factory=list)
    refs: list[Ref] = field(default_factory=list)


def string_end(text: str, pos: int) -> int:
    """Index just past the closing quote of a string whose body starts at ``pos``.

    Uses plain ``find`` instead of a regex so multi-megabyte strings (built-in
    scripts, shader code) are scanned quickly and without extra memory.
    """
    while True:
        quote = text.find('"', pos)
        if quote == -1:
            return len(text)
        backslashes = 0
        k = quote - 1
        while k >= pos and text[k] == "\\":
            backslashes += 1
            k -= 1
        if backslashes % 2 == 0:
            return quote + 1
        pos = quote + 1


def parse_text_resource(text: str) -> ParsedResource:
    """Split a .tscn/.tres file into section headers and resource references.

    String literals (including multi-line built-in script sources) are
    skipped, so text inside strings is never mistaken for a header or a
    reference. A header is a ``[`` at the start of a line while no bracket
    is open.
    """
    result = ParsedResource()
    line = 1
    depth = 0
    pos = 0
    at_line_start = True
    n = len(text)
    while pos < n:
        if at_line_start and depth == 0:
            stripped = pos
            while stripped < n and text[stripped] in " \t":
                stripped += 1
            if stripped < n and text[stripped] == "[":
                end = text.find("\n", stripped)
                end = n if end == -1 else end
                tag, attrs = parse_header(text[stripped:end])
                result.sections.append(Section(tag, attrs, line, stripped))
            elif stripped < n and text[stripped] == ";":
                end = text.find("\n", stripped)
                pos = n if end == -1 else end
                at_line_start = False
                continue
        at_line_start = False
        m = TOKEN_RE.search(text, pos)
        if not m:
            break
        tok = m.group(0)
        start = m.start()
        if tok == '"':
            end = string_end(text, start + 1)
            line += text.count("\n", start, end)
            pos = end
        elif tok == "\n":
            line += 1
            pos = m.end()
            at_line_start = True
        elif tok in "([{":
            depth += 1
            pos = m.end()
        elif tok in ")]}":
            depth = max(0, depth - 1)
            pos = m.end()
        else:
            rm = REF_RE.match(text, start)
            if rm:
                rid = unescape(rm.group(2)) if rm.group(2) is not None else rm.group(3)
                result.refs.append(Ref(rm.group(1), rid, line, start))
                line += text.count("\n", start, rm.end())
                pos = rm.end()
            else:
                pos = m.end()
    return result


UID_CHARS = "abcdefghijklmnopqrstuvwxy012345678"  # Godot's uid alphabet ('z' and '9' are never used)


def uid_to_text(value: int) -> str:
    digits = ""
    while True:
        digits = UID_CHARS[value % len(UID_CHARS)] + digits
        value //= len(UID_CHARS)
        if not value:
            return "uid://" + digits


def read_binary_uid(path: Path) -> str | None:
    """Return the uid stored in a binary resource (.res, .scn, ...).

    Returns ``"compressed"`` for compressed binary resources (magic ``RSCC``),
    whose header this tool cannot read, and None when the file is not a binary
    resource or has no uid.
    """
    try:
        with open(path, "rb") as handle:
            head = handle.read(4096)
    except OSError:
        return None
    if head[:4] == b"RSCC":
        return "compressed"
    if head[:4] != b"RSRC" or len(head) < 28:
        return None
    try:
        order = ">" if struct.unpack_from("<I", head, 4)[0] else "<"
        (type_len,) = struct.unpack_from(order + "I", head, 24)
        _metadata_offset, flags, uid = struct.unpack_from(order + "QIQ", head, 28 + type_len)
    except struct.error:
        return None
    if not flags & 2 or uid >= 1 << 63:  # 2 = FORMAT_FLAG_UIDS; larger values mean "no uid"
        return None
    return uid_to_text(uid)


def strip_comment(code_line: str) -> str:
    """Drop a GDScript ``#`` comment that is not inside a string."""
    quote = None
    i = 0
    while i < len(code_line):
        ch = code_line[i]
        if quote:
            if ch == "\\":
                i += 1
            elif ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
        elif ch == "#":
            return code_line[:i]
        i += 1
    return code_line


# ------------------------------------------------------------------- project


@dataclass
class PathStatus:
    status: str  # ok, case, missing, ignored, unknown
    actual: str | None = None  # project-relative path found on disk


class Project:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.data_dir = ".godot"
        self.files: list[str] = []  # scanned, project-relative posix paths
        self.file_set: set[str] = set()
        self.by_name: dict[str, list[str]] = {}
        self._listing: dict[str, dict[str, bool]] = {}
        self._skip_cache: dict[str, bool] = {}
        self.issues: list[Issue] = []
        self.files_checked = 0
        self.uid_to_files: dict[str, list[tuple[str, int | None]]] = {}
        self.file_uid: dict[str, str] = {}
        self.orphan_uids: dict[str, str] = {}  # uid -> orphaned sidecar file
        self._uid_owner_file: dict[tuple[str, str], str] = {}  # (uid, source) -> file holding the uid
        self.generated: set[str] = set()  # files listed as importer output in .import files
        # Compressed binary resources (.scn/.res saved by the editor) keep their uid in
        # zstd-compressed data this tool cannot read, so an unknown uid may belong to one.
        self.hidden_uid_files: list[str] = []
        self.parsed: dict[str, ParsedResource] = {}
        self.unreadable: set[str] = set()  # files that exist but could not be read
        self.unlistable: set[str] = set()  # directories that exist but could not be listed
        self._trees: dict[str, tuple[set[str], set[str]] | None] = {}
        self._tree_busy: set[str] = set()

    # -- reporting

    def add(self, severity: str, code: str, file: str, line: int | None, message: str, fix: str) -> None:
        self.issues.append(Issue(severity, code, file, line, message, fix))

    def add_unreadable(self, rel: str) -> None:
        self.add("warning", "file-unreadable", rel, None, "File could not be read, so it was not checked.",
                 "Check the file's permissions (on Windows, also whether the path is longer than 260 characters).")

    # -- filesystem

    def listing(self, rel_dir: str) -> dict[str, bool]:
        """Names in a project directory mapped to whether each is a directory.

        Only call it for directories. Broken symlinks and special files are left out,
        so a reference to one counts as missing. A directory that exists but cannot be
        listed (permissions, a path too long for Windows) is recorded in ``unlistable``.
        """
        if rel_dir not in self._listing:
            entries: dict[str, bool] = {}
            try:
                with os.scandir(self.root / rel_dir if rel_dir else self.root) as it:
                    for entry in it:
                        try:
                            if entry.is_dir():
                                entries[entry.name] = True
                            elif entry.is_file():
                                entries[entry.name] = False
                        except OSError:
                            pass
            except OSError:
                self.unlistable.add(rel_dir)
            self._listing[rel_dir] = entries
        return self._listing[rel_dir]

    def skipped_dir(self, rel_dir: str) -> bool:
        """True when Godot's file scan skips this directory (and so everything in it)."""
        if rel_dir in self._skip_cache:
            return self._skip_cache[rel_dir]
        skip = False
        if rel_dir:
            name = rel_dir.rsplit("/", 1)[-1]
            parent = rel_dir.rsplit("/", 1)[0] if "/" in rel_dir else ""
            if name.startswith(".") or rel_dir == self.data_dir or self.skipped_dir(parent):
                skip = True
            else:
                names = self.listing(rel_dir)
                skip = ".gdignore" in names or "project.godot" in names
        self._skip_cache[rel_dir] = skip
        return skip

    def scan(self) -> None:
        # Each stack entry carries the identities of the folders above it, so a symlink
        # that points back up the tree is entered once instead of looping forever.
        stack: list[tuple[str, tuple]] = [("", ())]
        while stack:
            rel_dir, ancestors = stack.pop()
            try:
                info = os.stat(self.root / rel_dir if rel_dir else self.root)
                # Some file systems (FAT on Windows) report inode 0 for everything.
                identity = (info.st_dev, info.st_ino) if info.st_ino else None
            except OSError:
                identity = None
            if identity is not None:
                if identity in ancestors:
                    continue
                ancestors = ancestors + (identity,)
            for name, is_dir in sorted(self.listing(rel_dir).items()):
                rel = f"{rel_dir}/{name}" if rel_dir else name
                if is_dir:
                    if not self.skipped_dir(rel):
                        stack.append((rel, ancestors))
                elif not name.startswith("."):
                    self.files.append(rel)
            if rel_dir in self.unlistable:
                self.add(
                    "warning",
                    "dir-unreadable",
                    rel_dir,
                    None,
                    "Folder could not be read, so files in it were not checked and references "
                    "into it are not verified.",
                    "Check the folder's permissions (on Windows, also whether the path is longer than 260 characters).",
                )
        self.files.sort()
        self.file_set = set(self.files)
        for rel in self.files:
            self.by_name.setdefault(rel.rsplit("/", 1)[-1].casefold(), []).append(rel)

    def resolve(self, raw: str, base_dir: str = "") -> PathStatus:
        """Look up a ``res://`` (or file-relative) path on disk, case-sensitively.

        Backslashes and repeated slashes are normalized the way Godot's
        ``simplify_path()`` does, so ``res://art\\icon.png`` finds ``art/icon.png``.
        """
        path = raw.split("::", 1)[0].replace("\\", "/")
        if path.startswith("res://"):
            path = path[len("res://") :].lstrip("/")
        elif "://" in path:
            return PathStatus("unknown")
        else:
            path = posixpath.join(base_dir, path) if base_dir else path
        path = posixpath.normpath(path) if path else ""
        if path in ("", "."):
            return PathStatus("ok", "")
        if path.startswith("../") or path == "..":
            return PathStatus("missing")
        if path == self.data_dir or path.startswith(self.data_dir + "/"):
            return PathStatus("unknown")
        if path in self.generated:
            return PathStatus("unknown")
        parts = path.split("/")
        current = ""
        case_differs = False
        for index, part in enumerate(parts):
            if current in self.unlistable:
                return PathStatus("unknown")
            names = self.listing(current)
            if part in names:
                actual = part
            else:
                matches = [n for n in names if n.casefold() == part.casefold()]
                if len(matches) != 1:
                    return PathStatus("missing")
                actual = matches[0]
                case_differs = True
            if index < len(parts) - 1 and not names[actual]:
                return PathStatus("missing")  # a file used as a folder
            current = f"{current}/{actual}" if current else actual
        if case_differs:
            return PathStatus("case", current)
        parent = current.rsplit("/", 1)[0] if "/" in current else ""
        name = current.rsplit("/", 1)[-1]
        if self.skipped_dir(parent) or name.startswith(".") or (
            self.listing(parent).get(name) and self.skipped_dir(current)
        ):
            return PathStatus("ignored", current)
        return PathStatus("ok", current)

    def similar(self, raw: str) -> list[str]:
        name = raw.split("::", 1)[0].replace("\\", "/").rstrip("/").rsplit("/", 1)[-1].casefold()
        return self.by_name.get(name, [])[:3]

    def missing_fix(self, raw: str, what: str) -> str:
        candidates = self.similar(raw)
        if candidates:
            listed = ", ".join(f"res://{c}" for c in candidates)
            return f"A file with that name exists at {listed}; point {what} there, or restore the file."
        return f"Create the file, or point {what} at the file's current location."

    # -- uids

    def uid_target(self, uid: str) -> str | None:
        entries = self.uid_to_files.get(uid)
        return entries[0][0] if entries else None

    def index_uids(self) -> None:
        for rel in self.files:
            lower = rel.lower()
            if lower.endswith(".import"):
                source = rel[: -len(".import")]
                text = self.load(rel)
                m = re.search(r'^uid="(uid://[^"]+)"', text, re.M)
                if source not in self.file_set:
                    self.add(
                        "warning",
                        "import-file-orphaned",
                        rel,
                        None,
                        f"Import settings file has no source file res://{source}.",
                        "If the asset was moved, move this .import file with it; if it was deleted, delete this file.",
                    )
                    if m:
                        self.orphan_uids.setdefault(m.group(1), rel)
                    continue
                if m:
                    line = text.count("\n", 0, m.start()) + 1
                    self._claim_uid(m.group(1), source, rel, line)
                # Files the importer writes (for example .translation files from a CSV).
                dest = re.search(r"^dest_files=\[(.*)\]\s*$", text, re.M)
                if dest:
                    for out in re.findall(r'"res://([^"]+)"', dest.group(1)):
                        self.generated.add(out)
            elif lower.endswith(".uid"):
                source = rel[: -len(".uid")]
                uid = self.load(rel).strip().split("\n", 1)[0].strip()
                if source not in self.file_set:
                    self.add(
                        "warning",
                        "uid-file-orphaned",
                        rel,
                        1,
                        f"UID file has no source file res://{source}.",
                        "If the script/shader was moved, move this .uid file next to it; if it was deleted, delete this file.",
                    )
                    if uid.startswith("uid://"):
                        self.orphan_uids.setdefault(uid, rel)
                    continue
                if uid.startswith("uid://") and source not in self.file_uid:
                    self._claim_uid(uid, source, rel, 1)
            elif Path(rel).suffix.lower() in TEXT_RESOURCE_EXTS:
                parsed = self.parse(rel)
                if parsed.sections:
                    head = parsed.sections[0]
                    uid = head.attrs.get("uid", "")
                    if head.tag in ("gd_scene", "gd_resource") and uid.startswith("uid://"):
                        self._claim_uid(uid, rel, rel, head.line)
            elif f"{rel}.import" not in self.file_set and f"{rel}.uid" not in self.file_set \
                    and Path(rel).suffix.lower() != ".gd":
                uid = read_binary_uid(self.root / rel)
                if uid == "compressed":
                    self.hidden_uid_files.append(rel)
                elif uid:
                    self._claim_uid(uid, rel, rel, None)
        for uid, entries in self.uid_to_files.items():
            if len(entries) < 2:
                continue
            first_source = entries[0][0]
            for source, line in entries[1:]:
                owner = self._uid_owner_file.get((uid, source), source)
                self.add(
                    "error",
                    "uid-duplicate",
                    owner,
                    line,
                    f"{uid} is also used by res://{first_source}; references by uid load only one of them.",
                    "Give one file a new uid: delete the uid=\"...\" attribute (or the .uid/.import file) of the copy "
                    "and open the project in the Godot editor so it assigns a fresh one, then re-save scenes that use it.",
                )

    def _claim_uid(self, uid: str, source: str, owner_file: str, line: int | None) -> None:
        if source in self.file_uid:
            return
        self.file_uid[source] = uid
        self.uid_to_files.setdefault(uid, []).append((source, line))
        self._uid_owner_file[(uid, source)] = owner_file

    def uid_knowable(self, rel: str) -> bool:
        """True when this tool can see the file's uid: a text resource header, a .import or a .uid file.

        Binary resources (.res, .scn, .mesh, ...) keep their uid inside the binary data; it is
        read from uncompressed ones, while compressed ones are not reported.
        """
        return (
            Path(rel).suffix.lower() in TEXT_RESOURCE_EXTS
            or rel in self.file_uid
            or f"{rel}.import" in self.file_set
            or f"{rel}.uid" in self.file_set
        )

    # -- file cache

    def load(self, rel: str) -> str:
        """Read a project file. Not cached: each file is read once, and big projects hold
        gigabytes of .tres text that should not stay in memory."""
        try:
            return read_text(self.root / rel)
        except OSError:
            self.unreadable.add(rel)
            return ""

    def parse(self, rel: str) -> ParsedResource:
        if rel not in self.parsed:
            self.parsed[rel] = parse_text_resource(self.load(rel))
        return self.parsed[rel]

    # -- ext_resource resolution

    def ext_target(self, rel: str, attrs: dict[str, str]) -> str | None:
        """The file Godot actually loads for an ``[ext_resource]``, or None."""
        uid = attrs.get("uid", "")
        target = self.uid_target(uid) if uid.startswith("uid://") else None
        if target:
            return target
        path = attrs.get("path")
        if path is None:
            return None
        st = self.resolve(path, posixpath.dirname(rel))
        return st.actual if st.status == "ok" else None

    # -- scene trees

    def scene_tree(self, rel: str) -> tuple[set[str], set[str]] | None:
        """Node paths (relative to the root, root excluded) and opaque prefixes of a scene.

        Returns None when the scene cannot be read as a text scene. An opaque
        prefix is a node whose children come from a scene this tool cannot read;
        ``"."`` means the whole tree is opaque.
        """
        if Path(rel).suffix.lower() != ".tscn" or rel not in self.file_set:
            return None
        if rel in self._trees:
            return self._trees[rel]
        if rel in self._tree_busy:
            return None
        self.parse(rel)
        if rel in self.unreadable:
            return None
        self._tree_busy.add(rel)
        try:
            tree = self._walk_scene(rel, report=False)
        finally:
            self._tree_busy.discard(rel)
        self._trees[rel] = tree
        return tree

    def _walk_scene(self, rel: str, report: bool) -> tuple[set[str], set[str]]:
        parsed = self.parse(rel)
        ext = {
            s.attrs.get("id"): s.attrs
            for s in parsed.sections
            if s.tag == "ext_resource" and s.attrs.get("id") is not None
        }
        known: set[str] = set()
        opaque: set[str] = set()
        roots: list[Section] = []
        broken: set[str] = set()  # names of nodes whose parent= is wrong

        def merge(prefix: str, raw_instance: str | None) -> None:
            rid = ref_id(raw_instance)
            target = self.ext_target(rel, ext[rid]) if rid in ext else None
            sub = self.scene_tree(target) if target else None
            if sub is None:
                opaque.add(prefix or ".")
                return
            sub_known, sub_opaque = sub
            for p in sub_known:
                known.add(f"{prefix}/{p}" if prefix else p)
            for p in sub_opaque:
                if p == ".":
                    opaque.add(prefix or ".")
                else:
                    opaque.add(f"{prefix}/{p}" if prefix else p)

        for sec in parsed.sections:
            if sec.tag == "node":
                name = sec.attrs.get("name")
                parent = sec.attrs.get("parent")
                if parent is None:
                    roots.append(sec)
                    if report and len(roots) == 2:
                        self.add(
                            "error",
                            "scene-multiple-roots",
                            rel,
                            sec.line,
                            f'Node "{name}" has no parent= but the scene already has a root node '
                            f'"{roots[0].attrs.get("name")}" (line {roots[0].line}).',
                            'Give this node a parent= path (use parent="." for a child of the root); '
                            "a scene must have exactly one root.",
                        )
                    if len(roots) == 1 and "instance" in sec.attrs:
                        merge("", sec.attrs.get("instance"))
                    continue
                ppath = self._norm_node_path(parent)
                if ppath is not None and ppath != "" and ppath not in known and self._verifiable(ppath, opaque):
                    # Keep going as if the parent existed, so one bad parent= is reported once
                    # instead of again for every child and connection of this node.
                    if name:
                        broken.add(name)
                    if report and "parent_id_path" in sec.attrs:
                        # Godot 4.6+ finds a renamed parent by its unique ids when the path fails.
                        self.add(
                            "warning",
                            "node-parent-missing",
                            rel,
                            sec.line,
                            f'Node "{name}" has parent="{parent}", which no longer exists; Godot looks the '
                            "parent up by parent_id_path instead, which works while the base scene keeps its node ids.",
                            "Open and re-save this scene in the Godot editor so it writes the current parent= path.",
                        )
                    elif report:
                        self.add(
                            "error",
                            "node-parent-missing",
                            rel,
                            sec.line,
                            f'Node "{name}" has parent="{parent}", but no node at that path is declared above it.',
                            "Fix the parent= path (relative to the root, without the root's name; "
                            'use "." for direct children) or declare the parent node earlier in the file.',
                        )
                if name is None or ppath is None:
                    continue
                full = f"{ppath}/{name}" if ppath else name
                known.add(full)
                if "instance" in sec.attrs:
                    merge(full, sec.attrs.get("instance"))
                elif "instance_placeholder" in sec.attrs:
                    opaque.add(full)
            elif sec.tag == "connection" and report:
                for key in ("from", "to"):
                    value = sec.attrs.get(key)
                    if value is None:
                        continue
                    npath = self._norm_node_path(value)
                    if npath is None or npath == "" or npath in known or not self._verifiable(npath, opaque):
                        continue
                    if broken.intersection(npath.split("/")):
                        continue  # already reported as node-parent-missing
                    if f"{key}_uid_path" in sec.attrs:
                        # Godot 4.6+ finds a renamed node by its unique ids when the path fails.
                        self.add(
                            "warning",
                            "connection-node-missing",
                            rel,
                            sec.line,
                            f'Signal connection {key}="{value}" names a node path that no longer exists; Godot '
                            f"looks the node up by {key}_uid_path instead, which works while the node ids stay the same.",
                            "Open and re-save this scene in the Godot editor so it writes the current node path.",
                        )
                        continue
                    self.add(
                        "error",
                        "connection-node-missing",
                        rel,
                        sec.line,
                        f'Signal connection {key}="{value}" names a node that does not exist in this scene; '
                        "Godot drops the connection.",
                        f"Update {key}= to the node's current path (relative to the root, \".\" for the root), "
                        "or remove the [connection] line.",
                    )
        if report and not roots:
            self.add(
                "error",
                "scene-root-missing",
                rel,
                parsed.sections[0].line if parsed.sections else None,
                "Scene has no root node (every [node] needs a parent, or there are no nodes).",
                "Add one [node] without parent= as the first node; all other nodes use parent= paths below it.",
            )
        return known, opaque

    @staticmethod
    def _norm_node_path(value: str) -> str | None:
        """Normalize a scene-relative node path; None when it cannot be checked."""
        value = value.strip()
        if value in (".", ""):
            return ""
        if ".." in value.split("/") or value.startswith("/") or "%" in value or ":" in value:
            return None
        if value.startswith("./"):
            value = value[2:]
        return value.strip("/")

    @staticmethod
    def _verifiable(path: str, opaque: set[str]) -> bool:
        if "." in opaque:
            return False
        return not any(path.startswith(o + "/") for o in opaque)

    # ----------------------------------------------------------- the checks

    def check_text_resource(self, rel: str) -> None:
        self.files_checked += 1
        parsed = self.parse(rel)
        base_dir = posixpath.dirname(rel)
        sections = parsed.sections
        if rel in self.unreadable:
            self.add_unreadable(rel)
            return
        if not sections or sections[0].tag not in ("gd_scene", "gd_resource"):
            self.add(
                "error",
                "header-missing",
                rel,
                sections[0].line if sections else 1,
                "File does not start with a [gd_scene ...] or [gd_resource ...] header, so Godot cannot load it.",
                'Start the file with [gd_scene format=3] (scenes) or [gd_resource type="..." format=3] (resources).',
            )
            return
        ext_ids: dict[str, int] = {}
        sub_ids: dict[str, tuple[int, int]] = {}
        for sec in sections:
            if sec.tag == "ext_resource":
                missing = [k for k in ("path", "type", "id") if k not in sec.attrs]
                if missing:
                    self.add(
                        "error",
                        "ext-resource-malformed",
                        rel,
                        sec.line,
                        f"[ext_resource] is missing {', '.join(missing)}; Godot refuses to load the file.",
                        'Write it as [ext_resource type="Type" uid="uid://..." path="res://file" id="1_abc"].',
                    )
                rid = sec.attrs.get("id")
                if rid is not None:
                    if rid in ext_ids:
                        self.add(
                            "error",
                            "resource-id-duplicate",
                            rel,
                            sec.line,
                            f'ext_resource id "{rid}" is already declared on line {ext_ids[rid]}.',
                            "Give each [ext_resource] a unique id and update the ExtResource(...) uses.",
                        )
                    else:
                        ext_ids[rid] = sec.line
                if "path" in sec.attrs:
                    self._check_ext_resource(rel, base_dir, sec)
            elif sec.tag == "sub_resource":
                rid = sec.attrs.get("id")
                missing = [k for k in ("type", "id") if k not in sec.attrs]
                if missing:
                    self.add(
                        "error",
                        "sub-resource-malformed",
                        rel,
                        sec.line,
                        f"[sub_resource] is missing {', '.join(missing)}; Godot refuses to load the file.",
                        'Write it as [sub_resource type="Type" id="Type_abc12"].',
                    )
                if rid is not None and rid in sub_ids:
                    self.add(
                        "error",
                        "resource-id-duplicate",
                        rel,
                        sec.line,
                        f'sub_resource id "{rid}" is already declared on line {sub_ids[rid][0]}.',
                        "Give each [sub_resource] a unique id and update the SubResource(...) uses.",
                    )
                elif rid is not None:
                    sub_ids[rid] = (sec.line, sec.offset)
            elif sec.tag == "node" and "instance_placeholder" in sec.attrs:
                raw = sec.attrs["instance_placeholder"]
                self._check_plain_path(rel, sec.line, raw, base_dir, "error", "placeholder-path-missing",
                                       "instance_placeholder=")
        for ref in parsed.refs:
            if ref.kind == "ExtResource":
                if ref.rid not in ext_ids:
                    self.add(
                        "error",
                        "ext-resource-id-undeclared",
                        rel,
                        ref.line,
                        f'ExtResource("{ref.rid}") is used but no [ext_resource] has id="{ref.rid}".',
                        "Add the matching [ext_resource] near the top of the file, or change the id to a declared one.",
                    )
            else:
                decl = sub_ids.get(ref.rid)
                if decl is None:
                    self.add(
                        "error",
                        "sub-resource-id-undeclared",
                        rel,
                        ref.line,
                        f'SubResource("{ref.rid}") is used but no [sub_resource] has id="{ref.rid}".',
                        "Add the matching [sub_resource] above this line, or change the id to a declared one.",
                    )
                elif decl[1] > ref.offset:
                    self.add(
                        "error",
                        "sub-resource-used-before-declared",
                        rel,
                        ref.line,
                        f'SubResource("{ref.rid}") is used before its [sub_resource] on line {decl[0]}.',
                        "Move that [sub_resource] block above the first place that uses it.",
                    )
        if sections[0].tag == "gd_scene":
            self._walk_scene(rel, report=True)

    def _check_ext_resource(self, rel: str, base_dir: str, sec: Section) -> None:
        path = sec.attrs["path"]
        uid = sec.attrs.get("uid", "")
        has_uid = uid.startswith("uid://")
        target = self.uid_target(uid) if has_uid else None
        st = self.resolve(path, base_dir)
        if st.status == "unknown":
            return
        if target:
            if st.status == "ok" and st.actual == target:
                return
            if st.status == "ok":
                self.add(
                    "warning",
                    "uid-path-mismatch",
                    rel,
                    sec.line,
                    f'ext_resource uid {uid} belongs to res://{target}, but path="{path}" names a different file. '
                    f"Godot loads res://{target}.",
                    f'If res://{target} is right, set path="res://{target}". Otherwise set uid= to '
                    f"{self.file_uid.get(st.actual or '', 'the uid of the intended file')} "
                    "or delete the uid= attribute.",
                )
            else:
                self.add(
                    "warning",
                    "ext-resource-path-stale",
                    rel,
                    sec.line,
                    f'path="{path}" is out of date; Godot finds the file by uid at res://{target}.',
                    f'Set path="res://{target}" (the editor also fixes it when the scene is re-saved).',
                )
            return
        if st.status == "ok":
            if has_uid and st.actual and (self.uid_knowable(st.actual) or uid in self.orphan_uids):
                actual_uid = self.file_uid.get(st.actual)
                orphan = self.orphan_uids.get(uid)
                if orphan:
                    fix = (f"The uid is in the orphaned file {orphan}; move it next to res://{st.actual} "
                           f"(as {Path(st.actual).name}{Path(orphan).suffix}) or set uid= to the file's own uid.")
                elif actual_uid:
                    fix = f'Set uid="{actual_uid}" (the uid of res://{st.actual}).'
                else:
                    fix = ("Delete the uid= attribute, or open the project in the Godot editor and re-save this "
                           "file so it writes the correct uid.")
                self.add(
                    "warning",
                    "ext-resource-uid-unknown",
                    rel,
                    sec.line,
                    f"uid {uid} is not assigned to any file; Godot warns and falls back to path=\"{path}\".",
                    fix,
                )
            return
        if st.status == "case":
            self.add(
                "error",
                "path-case-mismatch",
                rel,
                sec.line,
                f'path="{path}" differs in letter case from the file on disk (res://{st.actual}). '
                "It works on Windows/macOS but breaks on Linux and in exported games.",
                f'Set path="res://{st.actual}".',
            )
            return
        if st.status == "ignored":
            self.add(
                "warning",
                "path-in-ignored-dir",
                rel,
                sec.line,
                f'path="{path}" points into a folder Godot does not scan (.gdignore, hidden or nested project); '
                "it is not imported or exported.",
                "Move the file into a scanned folder, or remove the .gdignore file.",
            )
            return
        hint = ""
        if has_uid and uid in self.orphan_uids:
            hint = f" Its uid is in the orphaned file {self.orphan_uids[uid]}."
        suffix = Path(path).suffix.lower()
        hidden = [f for f in self.hidden_uid_files if Path(f).suffix.lower() == suffix] if has_uid else []
        if hidden:
            # The file may have been moved: Godot would still find it by uid, which is
            # stored inside compressed binary files this tool cannot read.
            listed = ", ".join(f"res://{f}" for f in hidden[:3]) + (" ..." if len(hidden) > 3 else "")
            self.add(
                "warning",
                "ext-resource-missing",
                rel,
                sec.line,
                f'ext_resource path="{path}" does not exist. Godot still loads it if uid {uid} belongs to '
                f"one of the compressed binary files whose uid this tool cannot read ({listed}).",
                "If the Godot editor reports no missing dependency for this file, re-save it there to update "
                "path=. Otherwise: " + self.missing_fix(path, "path="),
            )
            return
        self.add(
            "error",
            "ext-resource-missing",
            rel,
            sec.line,
            f'ext_resource path="{path}" does not exist'
            + (f" and uid {uid} matches no file" if has_uid else "")
            + "; the resource fails to load."
            + hint,
            self.missing_fix(path, "path="),
        )

    def _check_plain_path(self, rel: str, line: int | None, raw: str, base_dir: str, severity: str,
                          code: str, what: str, case_severity: str = "error") -> None:
        """Check one res:// or uid:// value that is not an [ext_resource]."""
        if raw.startswith("uid://"):
            if raw not in self.uid_to_files:
                hint = f" (it is in the orphaned file {self.orphan_uids[raw]})" if raw in self.orphan_uids else ""
                if self.hidden_uid_files and not hint:
                    self.add("warning", code, rel, line,
                             f"{what} {raw} matches no file this tool can read; it may belong to one of the "
                             f"{len(self.hidden_uid_files)} compressed binary files (.scn/.res) whose uid is unreadable.",
                             "Check in the Godot editor that this uid opens the intended file, or use the file's "
                             "res:// path instead.")
                    return
                self.add(severity, code, rel, line, f"{what} {raw} matches no file in the project{hint}.",
                         "Use the res:// path of the file, or the uid shown in the Godot editor for it.")
            return
        st = self.resolve(raw, base_dir)
        if st.status == "missing" and ":" in raw.rsplit("/", 1)[-1]:
            # Translation remaps store "res://file.ext:locale".
            raw = raw.rsplit(":", 1)[0]
            st = self.resolve(raw, base_dir)
        if st.status in ("ok", "unknown"):
            return
        if st.status == "case":
            self.add(case_severity, "path-case-mismatch", rel, line,
                     f'{what} "{raw}" differs in letter case from the file on disk (res://{st.actual}). '
                     "It works on Windows/macOS but breaks on Linux and in exported games.",
                     f'Use "res://{st.actual}".')
        elif st.status == "ignored":
            self.add("warning", "path-in-ignored-dir", rel, line,
                     f'{what} "{raw}" points into a folder Godot does not scan (.gdignore, hidden or nested project).',
                     "Move the file into a scanned folder, or remove the .gdignore file.")
        else:
            self.add(severity, code, rel, line, f'{what} "{raw}" does not exist.', self.missing_fix(raw, what))

    def check_project_file(self) -> None:
        rel = "project.godot"
        self.files_checked += 1
        text = self.load(rel)
        section = ""
        setting = ""  # the setting whose (possibly multi-line) value this line belongs to
        main_scene_seen = False
        for lineno, line in enumerate(text.split("\n"), start=1):
            stripped = line.strip()
            if re.fullmatch(r"\[[A-Za-z0-9_./-]+\]", stripped):
                section = stripped[1:-1]
                setting = ""
                continue
            if section == "locale":
                # Left over from Godot 3; Godot 4 reads internationalization/locale/* instead.
                continue
            m = re.match(r'^([A-Za-z0-9_./"-][^=]*?)=(.*)$', line)
            key = ""
            value = ""
            if m and not line.startswith(('"', " ", "\t")):
                key = m.group(1).strip()
                value = m.group(2).strip()
                setting = f"{section}/{key}" if section else key
            string_value = re.fullmatch(r'"((?:[^"\\]|\\.)*)"', value) if key else None
            if section == "application" and re.fullmatch(r"run/main_scene(\.[\w.]+)?", key):
                scene = unescape(string_value.group(1)) if string_value else ""
                if key == "run/main_scene" and scene:
                    main_scene_seen = True
                if scene:
                    self._check_plain_path(rel, lineno, scene, "", "error", "main-scene-missing",
                                           f"application/{key}")
                continue
            if section == "autoload" and key:
                if string_value:
                    target = unescape(string_value.group(1)).lstrip("*")
                    self._check_plain_path(rel, lineno, target, "", "error", "autoload-missing",
                                           f"autoload {key}")
                continue
            if string_value and string_value.group(1).startswith("uid://"):
                # A uid is only checked when it is the whole value of a setting.
                self._check_plain_path(rel, lineno, unescape(string_value.group(1)), "", "warning",
                                       "project-path-missing", f"setting {setting}")
                continue
            for sm in PROJECT_STRING_RE.finditer(line):
                raw = unescape(sm.group(1))
                if raw.startswith("res://"):
                    self._check_plain_path(rel, lineno, raw, "", "warning", "project-path-missing",
                                           f"setting {setting}", case_severity="warning")
        if not main_scene_seen:
            self.add("warning", "main-scene-not-set", rel, None,
                     "application/run/main_scene is not set; the exported game has no scene to start.",
                     "Set it in Project Settings > Application > Run > Main Scene "
                     '(run/main_scene="res://main.tscn" under [application]).')

    def check_script(self, rel: str) -> None:
        self.files_checked += 1
        text = self.load(rel)
        base_dir = posixpath.dirname(rel)
        if rel in self.unreadable:
            self.add_unreadable(rel)
            return
        for lineno, line in enumerate(text.split("\n"), start=1):
            if "://" not in line:
                continue
            code = strip_comment(line)
            m = EXTENDS_RE.match(code)
            if m:
                self._check_plain_path(rel, lineno, m.group(2), base_dir, "warning", "script-path-missing",
                                       "extends")
            for m in SCRIPT_CALL_RE.finditer(code):
                self._check_plain_path(rel, lineno, m.group(3), base_dir, "warning", "script-path-missing",
                                       f"{m.group(1)}()")

    def read_project_settings(self) -> None:
        text = self.load("project.godot")
        if re.search(r"^config/use_hidden_project_data_directory\s*=\s*false\s*$", text, re.M):
            self.data_dir = "godot"

    def run(self) -> None:
        self.read_project_settings()
        self.scan()
        self.index_uids()
        self.check_project_file()
        for rel in self.files:
            suffix = Path(rel).suffix.lower()
            if suffix in TEXT_RESOURCE_EXTS:
                self.check_text_resource(rel)
            elif suffix == ".gd":
                self.check_script(rel)
            elif suffix in (".import", ".uid"):
                self.files_checked += 1


# ----------------------------------------------------------------------- CLI


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="check_godot_project.py",
        description=(
            "Read-only check of a Godot 4.x project for broken references: missing or "
            "wrong-case res:// paths, unknown or duplicate uids, undeclared ExtResource/SubResource "
            "ids, broken scene trees and signal connections, project.godot main scene and "
            "autoloads, and literal preload()/load() paths in .gd scripts."
        ),
        epilog=(
            "example:\n"
            "  python scripts/check_godot_project.py path/to/my_game\n"
            "  python scripts/check_godot_project.py . --json --max-issues 20\n\n"
            "exit codes: 0 no errors, 1 errors found (or warnings with --strict), "
            "2 usage problem or no project.godot"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("project_dir", nargs="?", default=".", metavar="PROJECT_DIR",
                        help="folder that contains project.godot (default: current folder)")
    parser.add_argument("--json", action="store_true", help="print one JSON object instead of text")
    parser.add_argument("--strict", action="store_true", help="exit 1 when there are warnings too")
    parser.add_argument("--max-issues", type=int, default=50, metavar="N",
                        help="print at most N issues, errors first (default: 50; 0 = no limit)")
    return parser


def main(argv: list[str] | None = None) -> int:
    # A console or pipe that cannot encode a file name (Windows code pages) must not crash the report.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="backslashreplace")
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.max_issues < 0:
        parser.error("--max-issues must be 0 or more")
    root = Path(args.project_dir).expanduser()
    if not root.is_dir():
        print(f"error: {display_text(args.project_dir)} is not a folder", file=sys.stderr)
        return 2
    if not (root / "project.godot").is_file():
        print(f"error: {display_text(args.project_dir)} is not a Godot project (no project.godot found there)",
              file=sys.stderr)
        return 2
    root = root.resolve()
    project = Project(root)
    project.run()

    def sort_key(issue: Issue) -> tuple:
        return (issue.file, issue.line or 0, issue.code, issue.message)

    errors = sorted((i for i in project.issues if i.severity == "error"), key=sort_key)
    warnings = sorted((i for i in project.issues if i.severity == "warning"), key=sort_key)
    ordered = errors + warnings
    shown = ordered[: args.max_issues] if args.max_issues else ordered
    truncated = len(ordered) > len(shown)

    if args.json:
        payload = {
            "tool": TOOL,
            "schema": SCHEMA,
            "root": root.as_posix(),
            "files_checked": project.files_checked,
            "error_count": len(errors),
            "warning_count": len(warnings),
            "errors": [i.as_dict() for i in shown if i.severity == "error"],
            "warnings": [i.as_dict() for i in shown if i.severity == "warning"],
            "truncated": truncated,
        }
        print(json.dumps(payload, indent=2))
    else:
        for issue in shown:
            where = f"{issue.file}:{issue.line}" if issue.line else issue.file
            print(f"{issue.severity.upper()} {display_text(where)}: {display_text(issue.message)}")
            print(f"  fix: {display_text(issue.fix)}")
        if truncated:
            print(f"... and {len(ordered) - len(shown)} more")
        print(f"Summary: {len(errors)} errors, {len(warnings)} warnings in {project.files_checked} files checked")

    if errors or (args.strict and warnings):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
