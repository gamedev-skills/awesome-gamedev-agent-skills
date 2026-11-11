#!/usr/bin/env python3
"""Validate skills, resources, routing, catalogs, and plugin manifests.

The script intentionally uses only the Python standard library so the same check
runs locally and in CI.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MD_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
CODE_PATH_RE = re.compile(r"`((?:references|scripts|assets)/[^`\s]+)`")
HTML_SRC_RE = re.compile(r"\bsrc=[\"']([^\"']+)[\"']")
YAML_VALUE_RE = re.compile(r'^\s{2}([a-z_]+):\s*["\'](.*)["\']\s*$')
NOT_FOR_RE = re.compile(r"\bnot for\b", re.IGNORECASE)
GOTCHAS_RE = re.compile(r"^##\s+Gotchas\s*$", re.MULTILINE)
# "## Contents", "**Contents**", "Contents: a · b · c" or "Table of contents".
CONTENTS_HEADING_RE = re.compile(
    r"^(?:#{1,6}\s*(?:table of )?contents\s*$|\*\*(?:table of )?contents:?\*\*|(?:table of )?contents:)",
    re.IGNORECASE,
)
ANCHOR_ITEM_RE = re.compile(r"^\s*(?:[-*+]|\d+\.)\s+\[[^\]]+\]\(#[^)]+\)")

MAX_NAME = 64
MAX_DESCRIPTION = 1024
MAX_LINES = 500
LONG_REFERENCE_LINES = 100
CONTENTS_WINDOW = 30
ALLOWED_FRONTMATTER = frozenset({"name", "description"})
ALLOWED_SKILL_ENTRIES = frozenset({"SKILL.md", "agents", "assets", "references", "scripts"})
REPO_ROOT = Path(__file__).resolve().parent.parent

# Directories the repository-wide Markdown walk must never enter: version-control
# internals, vendored packages, build output, and the paths .gitignore keeps local.
# Without this the link check reports failures for third-party README files that
# are not part of the project, and only passes on a clean checkout.
EXCLUDED_DIRS = frozenset(
    {
        ".git",
        ".kiro",
        ".cache",
        ".tmp",
        ".venv",
        "venv",
        "__pycache__",
        "_site",
        "node_modules",
        "site-packages",
        "dist",
        "build",
        "scratch",
        "plan",
        "progress",
    }
)


def find_skill_files() -> list[Path]:
    files = sorted((REPO_ROOT / "skills").rglob("SKILL.md"))
    router = REPO_ROOT / "router" / "SKILL.md"
    if router.is_file():
        files.append(router)
    return files


def split_frontmatter(text: str) -> tuple[dict[str, str] | None, int]:
    """Parse the flat fields and folded scalars used by this repository."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, 0

    end = next((i for i, line in enumerate(lines[1:], 1) if line.strip() == "---"), None)
    if end is None:
        return None, 0

    fields: dict[str, str] = {}
    key_re = re.compile(r"^([A-Za-z0-9_-]+):\s*(.*)$")
    i = 1
    while i < end:
        raw = lines[i]
        if not raw.strip() or raw.lstrip().startswith("#") or raw[:1] in (" ", "\t"):
            i += 1
            continue
        match = key_re.match(raw)
        if not match:
            i += 1
            continue
        key, inline = match.group(1), match.group(2).strip()
        if key in fields:
            fields[f"__duplicate__{key}"] = ""
        if inline in {">", "|", ">-", "|-", ">+", "|+"}:
            block: list[str] = []
            i += 1
            while i < end and (not lines[i].strip() or lines[i][:1] in (" ", "\t")):
                if lines[i].strip():
                    block.append(lines[i].strip())
                i += 1
            fields[key] = " ".join(block).strip()
            continue
        fields[key] = inline.strip('"\'')
        i += 1
    return fields, end + 1


def _display(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _local_link_target(target: str) -> str | None:
    link = target.strip().strip("<>").split("#", 1)[0].split("?", 1)[0]
    if not link or link.startswith(("http://", "https://", "mailto:", "#")):
        return None
    # Ignore code that only happens to look like Markdown, such as [v](data).
    if "/" not in link and not link.startswith(".") and Path(link).suffix == "":
        return None
    return link


def validate_openai_yaml(skill_dir: Path, skill_name: str) -> list[str]:
    path = skill_dir / "agents" / "openai.yaml"
    if not path.exists():
        return []
    rel = _display(path)
    text = path.read_text(encoding="utf-8")
    if not text.startswith("interface:\n"):
        return [f"{rel}: must start with 'interface:'"]

    values = {match.group(1): match.group(2) for match in map(YAML_VALUE_RE.match, text.splitlines()) if match}
    errors: list[str] = []
    required = {"display_name", "short_description", "default_prompt"}
    missing = sorted(required - values.keys())
    if missing:
        errors.append(f"missing interface field(s): {', '.join(missing)}")
    short = values.get("short_description", "")
    if short and not 25 <= len(short) <= 64:
        errors.append(f"short_description is {len(short)} chars (must be 25–64)")
    prompt = values.get("default_prompt", "")
    if prompt and f"${skill_name}" not in prompt:
        errors.append(f"default_prompt must mention ${skill_name}")
    return [f"{rel}: {error}" for error in errors]


def validate_file(path: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    rel = _display(path)
    text = path.read_text(encoding="utf-8")

    line_count = len(text.splitlines())
    if line_count >= MAX_LINES:
        errors.append(f"file is {line_count} lines (must be < {MAX_LINES})")

    fields, _ = split_frontmatter(text)
    if fields is None:
        return [f"{rel}: missing or malformed YAML frontmatter"], []

    duplicates = sorted(key.removeprefix("__duplicate__") for key in fields if key.startswith("__duplicate__"))
    for key in duplicates:
        errors.append(f"duplicate frontmatter key: {key!r}")
    actual_keys = {key for key in fields if not key.startswith("__duplicate__")}
    extra = sorted(actual_keys - ALLOWED_FRONTMATTER)
    missing = sorted(ALLOWED_FRONTMATTER - actual_keys)
    if extra:
        errors.append(f"non-portable frontmatter field(s): {', '.join(extra)}")
    if missing:
        errors.append(f"missing frontmatter field(s): {', '.join(missing)}")

    name = fields.get("name", "")
    if name:
        if len(name) > MAX_NAME:
            errors.append(f"'name' is {len(name)} chars (max {MAX_NAME})")
        if not NAME_RE.fullmatch(name):
            errors.append("'name' must use lowercase letters, digits, and single hyphens")
        if name != path.parent.name:
            errors.append(f"'name' = {name!r} must equal folder name {path.parent.name!r}")

    description = fields.get("description", "")
    if not description:
        errors.append("'description' is missing or empty")
    elif len(description) > MAX_DESCRIPTION:
        errors.append(f"'description' is {len(description)} chars (max {MAX_DESCRIPTION})")
    elif "<" in description or ">" in description:
        errors.append("'description' must not contain angle brackets")

    unexpected = sorted(entry.name for entry in path.parent.iterdir() if entry.name not in ALLOWED_SKILL_ENTRIES)
    if unexpected:
        errors.append(f"unexpected skill-root entry/entries: {', '.join(unexpected)}")

    # Code such as Lua's `t[k](args)` looks like a Markdown link, so match links outside code fences.
    targets = set(MD_LINK_RE.findall(_without_fenced_code(text))) | set(CODE_PATH_RE.findall(text))
    for target in sorted(targets):
        link = _local_link_target(target)
        if link is None:
            continue
        resolved = (path.parent / link).resolve()
        if not resolved.exists():
            errors.append(f"local resource link does not resolve: {target!r}")

    errors.extend(error.removeprefix(f"{rel}: ") for error in validate_openai_yaml(path.parent, name))
    warnings = skill_warnings(path, text, description)
    return [f"{rel}: {error}" for error in errors], warnings


def _has_contents_list(text: str) -> bool:
    """True when a contents heading or a list of in-page anchor links opens the file."""
    head = text.splitlines()[:CONTENTS_WINDOW]
    if any(CONTENTS_HEADING_RE.match(line.strip()) for line in head):
        return True
    return sum(1 for line in head if ANCHOR_ITEM_RE.match(line)) >= 3


def skill_warnings(path: Path, text: str, description: str) -> list[str]:
    """Authoring-guide checks that warn instead of failing (unless --strict)."""
    rel = _display(path)
    warnings: list[str] = []
    # The router is the entry point for every game-dev request, so it has no neighbour to
    # name in a "Not for" clause; its boundaries live in its body.
    is_router = path.resolve() == (REPO_ROOT / "router" / "SKILL.md").resolve()
    if description and not is_router and not NOT_FOR_RE.search(description):
        warnings.append(f"{rel}: description has no 'Not for ...' clause naming the neighbouring skill")
    if not GOTCHAS_RE.search(_without_fenced_code(text)):
        warnings.append(f"{rel}: no '## Gotchas' heading")

    references = path.parent / "references"
    if not references.is_dir():
        return warnings
    for ref in sorted(references.rglob("*.md")):
        ref_rel = _display(ref)
        ref_text = ref.read_text(encoding="utf-8")
        line_count = len(ref_text.splitlines())
        if line_count > LONG_REFERENCE_LINES and not _has_contents_list(ref_text):
            warnings.append(
                f"{ref_rel}: {line_count} lines but no contents list in the first {CONTENTS_WINDOW} lines"
            )
        linked: set[str] = set()
        for target in MD_LINK_RE.findall(_without_fenced_code(ref_text)):
            link = _local_link_target(target)
            if link is None:
                continue
            resolved = (ref.parent / link).resolve()
            if resolved == ref.resolve() or resolved.suffix != ".md" or not resolved.exists():
                continue  # self links, non-Markdown files and template placeholders
            if resolved.is_relative_to(references.resolve()):
                linked.add(_display(resolved))
        for other in sorted(linked):
            warnings.append(f"{ref_rel}: links to another reference ({other}); link both from SKILL.md instead")
    return warnings


def validate_unique_names(files: list[Path]) -> list[str]:
    paths_by_name: dict[str, list[Path]] = {}
    for path in files:
        fields, _ = split_frontmatter(path.read_text(encoding="utf-8"))
        if fields and fields.get("name"):
            paths_by_name.setdefault(fields["name"], []).append(path)
    errors: list[str] = []
    for name, paths in sorted(paths_by_name.items()):
        if len(paths) > 1:
            locations = ", ".join(_display(path) for path in paths)
            errors.append(f"duplicate skill name {name!r}: {locations}")
    return errors


def validate_json_assets() -> list[str]:
    errors: list[str] = []
    for path in sorted((REPO_ROOT / "skills").rglob("assets/*.json")):
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{_display(path)}: invalid JSON: {exc}")
    return errors


def _without_fenced_code(text: str) -> str:
    kept: list[str] = []
    fence: str | None = None
    for line in text.splitlines():
        stripped = line.lstrip()
        marker = "```" if stripped.startswith("```") else "~~~" if stripped.startswith("~~~") else None
        if marker:
            fence = None if fence == marker else marker if fence is None else fence
            continue
        if fence is None:
            kept.append(line)
    return "\n".join(kept)


def validate_markdown_links() -> list[str]:
    """Check repository-local Markdown and HTML image targets outside code fences."""
    errors: list[str] = []
    for path in sorted(REPO_ROOT.rglob("*.md")):
        # Only look at folders inside the repo: a checkout that itself lives under
        # an excluded name (for example ~/.kiro/...) must still be checked.
        if any(part in EXCLUDED_DIRS for part in path.relative_to(REPO_ROOT).parts):
            continue
        text = _without_fenced_code(path.read_text(encoding="utf-8"))
        text = re.sub(r"`[^`]*`", "", text)
        targets = set(MD_LINK_RE.findall(text)) | set(HTML_SRC_RE.findall(text))
        for target in sorted(targets):
            link = _local_link_target(target)
            if link is None:
                continue
            resolved = (path.parent / link).resolve()
            if not resolved.exists():
                errors.append(f"{_display(path)}: local link does not resolve: {target!r}")
    return errors


def validate_marketplace(files: list[Path]) -> list[str]:
    path = REPO_ROOT / ".claude-plugin" / "marketplace.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"{_display(path)}: cannot load manifest: {exc}"]

    errors: list[str] = []
    plugins = data.get("plugins")
    if not isinstance(plugins, list):
        return [f"{_display(path)}: 'plugins' must be a list"]

    by_name: dict[str, set[str]] = {}
    for plugin in plugins:
        plugin_name = plugin.get("name", "<unnamed>")
        if plugin.get("source") == "./" and plugin.get("strict") is not False:
            errors.append(f"{_display(path)}: plugin {plugin_name!r} must set strict=false for explicit skill paths")
        skill_paths = plugin.get("skills", [])
        if len(skill_paths) != len(set(skill_paths)):
            errors.append(f"{_display(path)}: plugin {plugin_name!r} contains duplicate skill paths")
        by_name[plugin_name] = set(skill_paths)
        for skill_path in skill_paths:
            target = (REPO_ROOT / skill_path).resolve()
            if not (target / "SKILL.md").is_file():
                errors.append(f"{_display(path)}: plugin {plugin_name!r} points to missing skill {skill_path!r}")

    expected_all = {f"./{path.parent.relative_to(REPO_ROOT).as_posix()}" for path in files}
    if by_name.get("gamedev") != expected_all:
        missing = sorted(expected_all - by_name.get("gamedev", set()))
        extra = sorted(by_name.get("gamedev", set()) - expected_all)
        errors.append(f"{_display(path)}: 'gamedev' bundle mismatch; missing={missing}, extra={extra}")

    category_plugins = {
        "godot": "godot",
        "unity": "unity",
        "unreal": "unreal",
        "ebitengine": "ebitengine",
        "web-engines": "web-engines",
        "other-engines": "other-engines",
        "disciplines": "disciplines",
        "genres": "genres",
        "workflows": "workflows",
    }
    for plugin_name, category in category_plugins.items():
        expected = {
            f"./{skill.parent.relative_to(REPO_ROOT).as_posix()}"
            for skill in files
            # Compare the path under the repo root, not the grandparent folder name:
            # router/SKILL.md's grandparent is the checkout folder itself, which may
            # share a category's name.
            if skill.parent.parent.relative_to(REPO_ROOT).as_posix() == f"skills/{category}"
        }
        if by_name.get(plugin_name) != expected:
            errors.append(f"{_display(path)}: bundle {plugin_name!r} does not exactly match skills/{category}")
    if by_name.get("router") != {"./router"}:
        errors.append(f"{_display(path)}: 'router' bundle must contain only ./router")
    return errors


def validate_router_and_catalog(files: list[Path]) -> list[str]:
    errors: list[str] = []
    table_path = REPO_ROOT / "router" / "references" / "routing-table.md"
    table = table_path.read_text(encoding="utf-8")
    for path in files:
        if path.parent.name == "router":
            continue
        name = path.parent.name
        if f"`{name}`" not in table:
            errors.append(f"{_display(table_path)}: missing routed skill `{name}`")

    count = len(files) - 1
    readme_path = REPO_ROOT / "README.md"
    readme = readme_path.read_text(encoding="utf-8")
    if f"{count} skills" not in readme:
        errors.append(f"{_display(readme_path)}: catalog must state the current count ({count} skills)")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate skills, resources, routing, catalogs and plugin manifests.")
    parser.add_argument("--strict", action="store_true", help="fail when there are warnings too")
    args = parser.parse_args(argv)

    files = find_skill_files()
    if not files:
        print("No SKILL.md files found.")
        return 1

    errors: list[str] = []
    warnings: list[str] = []
    for path in files:
        file_errors, file_warnings = validate_file(path)
        errors.extend(file_errors)
        warnings.extend(file_warnings)
    errors.extend(validate_unique_names(files))
    errors.extend(validate_json_assets())
    errors.extend(validate_markdown_links())
    errors.extend(validate_marketplace(files))
    errors.extend(validate_router_and_catalog(files))

    print(f"Validated {len(files)} skill file(s) and repository wiring.")
    if warnings:
        print()
        for warning in warnings:
            print(f"WARNING: {warning}")
        print(f"{len(warnings)} warning(s)." + ("" if args.strict else " Run with --strict to fail on them."))
    if errors:
        print(f"\nFAILED — {len(errors)} problem(s):")
        for error in errors:
            print(f"  - {error}")
        return 1
    if warnings and args.strict:
        print("\nFAILED — warnings are errors with --strict.")
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
