#!/usr/bin/env python3
"""Generate a static documentation site from the committed ``SKILL.md`` files.

Every page is built from skill frontmatter, so the site cannot drift from the
skills themselves. Unlike a ``blob`` view on github.com, each generated page
carries its own ``<title>``, meta description and canonical URL.

Output is written to ``_site/`` (git-ignored) and is deployed by
``.github/workflows/pages.yml``. Nothing here mutates the skills.

Usage:
    python scripts/generate-site.py [--out _site] [--base-url URL]

No third-party dependencies.
"""

from __future__ import annotations

import argparse
import html
import re
import shutil
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = REPO_ROOT / "_site"
DEFAULT_BASE_URL = "https://gamedev-skills.github.io/awesome-gamedev-agent-skills"
REPO_SLUG = "gamedev-skills/awesome-gamedev-agent-skills"
GITHUB_BLOB = f"https://github.com/{REPO_SLUG}/blob/main"
INSTALL_CMD = f"npx skills add {REPO_SLUG}"

MAX_META_DESCRIPTION = 155

# Category slug -> (page heading, lead paragraph). Engine groups first.
CATEGORIES: dict[str, tuple[str, str]] = {
    "godot": (
        "Godot Agent Skills",
        "Skills that teach an AI coding agent the Godot 4.x API surface — GDScript, "
        "the scene tree, TileMapLayer, physics, shaders and exporting.",
    ),
    "unity": (
        "Unity Agent Skills",
        "Skills covering Unity 6 (6000.0 LTS) — MonoBehaviour scripting, the Input "
        "System, physics, Animator controllers, ScriptableObjects and builds.",
    ),
    "unreal": (
        "Unreal Engine Agent Skills",
        "Skills for Unreal Engine 5.4+ — Blueprints, C++ gameplay framework, "
        "Enhanced Input, Behavior Trees, Niagara and packaging.",
    ),
    "web-engines": (
        "Web Game Engine Agent Skills",
        "Skills for browser game engines — Phaser 3, PixiJS v8 and three.js r165+.",
    ),
    "other-engines": (
        "Bevy, pygame, LÖVE and Roblox Agent Skills",
        "Skills for Bevy ECS, pygame, LÖVE and Roblox Luau, including DataStore "
        "persistence.",
    ),
    "disciplines": (
        "Game Development Discipline Skills",
        "Cross-engine concepts that load alongside whichever engine skill applies — "
        "AI, procedural generation, save systems, shaders, game feel and more.",
    ),
    "genres": (
        "Game Genre Skills",
        "Compositional templates that orchestrate engine and discipline skills for a "
        "specific genre, from platformers to card games.",
    ),
    "workflows": (
        "Game Development Workflow Skills",
        "Skills for shipping — game jams, fast prototyping, and publishing to Steam "
        "or itch.io.",
    ),
}

# Agent slug -> (display name, skills directory, note)
AGENTS: dict[str, tuple[str, str, str]] = {
    "claude-code": ("Claude Code", ".claude/skills/", "Also installable as a Claude Code plugin marketplace."),
    "cursor": ("Cursor", ".cursor/skills/", "Cursor also reads the shared .agents/skills/ path."),
    "kiro": ("Kiro", ".kiro/skills/", "Kiro ignores the optional allowed-tools field; the skills here do not use it."),
    "codex": ("OpenAI Codex", ".agents/skills/", "Shared path used by several agents."),
    "gemini-cli": ("Gemini CLI", ".agents/skills/", "Shared path used by several agents."),
    "github-copilot": ("GitHub Copilot", ".agents/skills/", "Shared path used by several agents."),
    "windsurf": ("Windsurf", ".windsurf/skills/", ""),
    "cline": ("Cline", ".cline/skills/", "Skills are experimental; enable them under Settings -> Features."),
    "omp": ("Oh My Pi", ".omp/skills/", "Also reads the shared .agents/skills/ path; user-global skills live in ~/.omp/agent/skills/."),
}


# --------------------------------------------------------------------------- #
# Frontmatter parsing (stdlib only; handles nested `metadata:` unlike the
# validator's minimal parser, which only needs top-level keys).
# --------------------------------------------------------------------------- #

def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Return (frontmatter, body). Frontmatter values are str or dict[str, str]."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text

    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return {}, text

    fm: dict = {}
    key_re = re.compile(r"^([A-Za-z0-9_-]+):\s*(.*)$")
    i = 1
    while i < end:
        raw = lines[i]
        if not raw.strip() or raw.lstrip().startswith("#") or raw[:1] in (" ", "\t"):
            i += 1
            continue
        m = key_re.match(raw)
        if not m:
            i += 1
            continue
        key, inline = m.group(1), m.group(2).strip()

        if inline in (">", "|", ">-", "|-", ">+", "|+"):
            block: list[str] = []
            j = i + 1
            while j < end and (not lines[j].strip() or lines[j][:1] in (" ", "\t")):
                block.append(lines[j].strip())
                j += 1
            fm[key] = " ".join(part for part in block if part)
            i = j
            continue

        if inline == "":
            # Possibly a nested map (e.g. `metadata:`).
            nested: dict[str, str] = {}
            j = i + 1
            while j < end and (lines[j][:1] in (" ", "\t")) and lines[j].strip():
                sub = key_re.match(lines[j].strip())
                if sub:
                    nested[sub.group(1)] = sub.group(2).strip()
                j += 1
            fm[key] = nested if nested else ""
            i = j
            continue

        fm[key] = inline
        i += 1

    return fm, "\n".join(lines[end + 1:])


def first_heading(body: str) -> str:
    for line in body.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return ""


def meta_description(text: str, limit: int = MAX_META_DESCRIPTION) -> str:
    """Trim to `limit` chars on a word boundary without cutting mid-word."""
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0].rstrip(" ,.;:—-")
    return f"{cut}…"


# --------------------------------------------------------------------------- #
# Skill model
# --------------------------------------------------------------------------- #

class Skill:
    def __init__(self, path: Path) -> None:
        fm, body = parse_frontmatter(path.read_text(encoding="utf-8"))
        meta = fm.get("metadata") or {}
        if not isinstance(meta, dict):
            meta = {}

        self.path = path
        self.name: str = str(fm.get("name", path.parent.name))
        self.description: str = str(fm.get("description", ""))
        self.compatibility: str = str(fm.get("compatibility", ""))
        self.engine: str = meta.get("engine", "")
        self.difficulty: str = meta.get("difficulty", "")
        self.heading: str = first_heading(body) or self.name
        self.category: str = meta.get("category", "") or path.parent.parent.name
        self.rel_source: str = path.relative_to(REPO_ROOT).as_posix()

    @property
    def url_path(self) -> str:
        return f"{self.category}/{self.name}/"


def collect_skills() -> list[Skill]:
    skills_dir = REPO_ROOT / "skills"
    files = sorted(skills_dir.rglob("SKILL.md")) if skills_dir.is_dir() else []
    return [Skill(p) for p in files]


# --------------------------------------------------------------------------- #
# HTML rendering
# --------------------------------------------------------------------------- #

STYLES = """\
:root{--bg:#0d1117;--fg:#e6edf3;--muted:#9198a1;--accent:#7ee787;--line:#30363d;
--code:#161b22}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
font:16px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif}
.skip{position:absolute;left:-9999px}
.skip:focus{left:8px;top:8px;padding:8px 12px;background:var(--code);z-index:10}
.wrap{max-width:56rem;margin:0 auto;padding:2rem 1.25rem 4rem}
header nav{border-bottom:1px solid var(--line);padding:.9rem 0;margin-bottom:2rem}
header nav a{margin-right:1rem}
a{color:var(--accent)}
a:focus-visible,button:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
h1{font-size:1.9rem;line-height:1.25;margin:0 0 .6rem}
h2{font-size:1.3rem;margin:2.2rem 0 .6rem}
.lead{color:var(--muted);font-size:1.05rem;margin:0 0 1.6rem}
pre{background:var(--code);border:1px solid var(--line);border-radius:6px;
padding:.85rem 1rem;overflow-x:auto}
code{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:.9em}
table{border-collapse:collapse;width:100%;margin:1rem 0}
th,td{border:1px solid var(--line);padding:.55rem .7rem;text-align:left;
vertical-align:top}
th{background:var(--code)}
ul.cards{list-style:none;padding:0;display:grid;gap:.9rem}
ul.cards li{border:1px solid var(--line);border-radius:6px;padding:.9rem 1.1rem}
ul.cards p{margin:.35rem 0 0;color:var(--muted);font-size:.94rem}
dl.facts{display:grid;grid-template-columns:auto 1fr;gap:.35rem 1rem;margin:1.2rem 0}
dt{color:var(--muted)}
dd{margin:0}
footer{border-top:1px solid var(--line);margin-top:3rem;padding-top:1.2rem;
color:var(--muted);font-size:.9rem}
"""


def page(
    *,
    title: str,
    description: str,
    canonical: str,
    body: str,
    depth: int,
    base_url: str,
) -> str:
    root = "../" * depth if depth else ""
    esc = html.escape
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<link rel="canonical" href="{esc(canonical)}">
<meta property="og:type" content="website">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:url" content="{esc(canonical)}">
<link rel="stylesheet" href="{root}styles.css">
</head>
<body>
<a class="skip" href="#main">Skip to main content</a>
<div class="wrap">
<header>
<nav aria-label="Primary">
<a href="{root}">Catalog</a>
<a href="{root}install/">Install</a>
<a href="https://github.com/{REPO_SLUG}">Source on GitHub</a>
</nav>
</header>
<main id="main">
{body}
</main>
<footer>
<p>Generated from the committed <code>SKILL.md</code> files by
<code>scripts/generate-site.py</code>. Apache-2.0.</p>
</footer>
</div>
</body>
</html>
"""


def install_block(extra: str = "") -> str:
    return (
        "<h2>Install</h2>\n"
        f"<pre><code>{html.escape(INSTALL_CMD)}</code></pre>\n"
        f"{extra}"
    )


def skill_cards(skills: list[Skill], depth: int) -> str:
    root = "../" * depth if depth else ""
    items = []
    for s in skills:
        href = f"{root}{s.url_path}"
        items.append(
            f'<li><a href="{html.escape(href)}"><code>{html.escape(s.name)}</code></a>'
            f"<p>{html.escape(meta_description(s.description, 180))}</p></li>"
        )
    return '<ul class="cards">\n' + "\n".join(items) + "\n</ul>"


# --------------------------------------------------------------------------- #
# Page builders
# --------------------------------------------------------------------------- #

def write(out: Path, rel: str, content: str) -> None:
    target = out / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def build_index(out: Path, skills: list[Skill], base_url: str) -> None:
    by_cat: dict[str, list[Skill]] = {}
    for s in skills:
        by_cat.setdefault(s.category, []).append(s)

    sections = []
    for slug, (heading, lead) in CATEGORIES.items():
        group = by_cat.get(slug, [])
        if not group:
            continue
        sections.append(
            f'<h2><a href="{slug}/">{html.escape(heading)}</a> '
            f"<span class=\"muted\">({len(group)})</span></h2>\n"
            f"<p>{html.escape(lead)}</p>"
        )

    body = (
        "<h1>Game Development Agent Skills</h1>\n"
        f'<p class="lead">{len(skills)} version-pinned Agent Skills plus a router, in the '
        "portable <code>SKILL.md</code> format. An AI coding agent loads only the skills "
        "that match the engine and task at hand.</p>\n"
        + install_block(
            '<p>Or copy any skill folder into your agent\'s skills directory — see '
            '<a href="install/">install paths per agent</a>.</p>'
        )
        + "\n<h2>Catalog</h2>\n"
        + "\n".join(sections)
    )
    write(
        out,
        "index.html",
        page(
            title="Game Development Agent Skills for AI Coding Agents",
            description=meta_description(
                f"{len(skills)} game dev agent skills for AI coding agents across Godot, "
                "Unity, Unreal, Phaser, three.js, Bevy, pygame, LÖVE and Roblox."
            ),
            canonical=f"{base_url}/",
            body=body,
            depth=0,
            base_url=base_url,
        ),
    )


def build_category(out: Path, slug: str, skills: list[Skill], base_url: str) -> None:
    heading, lead = CATEGORIES[slug]
    body = (
        f"<h1>{html.escape(heading)}</h1>\n"
        f'<p class="lead">{html.escape(lead)}</p>\n'
        + install_block()
        + f"\n<h2>{len(skills)} skills</h2>\n"
        + skill_cards(skills, depth=1)
    )
    write(
        out,
        f"{slug}/index.html",
        page(
            title=f"{heading} — {len(skills)} skills for AI coding agents",
            description=meta_description(lead),
            canonical=f"{base_url}/{slug}/",
            body=body,
            depth=1,
            base_url=base_url,
        ),
    )


def build_skill(out: Path, skill: Skill, siblings: list[Skill], base_url: str) -> None:
    facts = [("Skill name", f"<code>{html.escape(skill.name)}</code>")]
    if skill.compatibility:
        facts.append(("Targets", html.escape(skill.compatibility)))
    if skill.engine:
        facts.append(("Engine", html.escape(skill.engine)))
    if skill.difficulty:
        facts.append(("Level", html.escape(skill.difficulty)))
    facts_html = "\n".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in facts)

    related = [s for s in siblings if s.name != skill.name][:8]
    related_html = ""
    if related:
        links = ", ".join(
            f'<a href="../{html.escape(s.name)}/"><code>{html.escape(s.name)}</code></a>'
            for s in related
        )
        related_html = f"<h2>Related skills</h2>\n<p>{links}</p>\n"

    source = f"{GITHUB_BLOB}/{skill.rel_source}"
    body = (
        f"<h1>{html.escape(skill.heading)}</h1>\n"
        f'<p class="lead">{html.escape(skill.description)}</p>\n'
        f'<dl class="facts">\n{facts_html}\n</dl>\n'
        + install_block(
            f'<p>Installs every skill in the collection; the router loads '
            f"<code>{html.escape(skill.name)}</code> when your request matches it.</p>"
        )
        + f'\n<h2>Skill source</h2>\n<p>Read the full playbook in '
        f'<a href="{html.escape(source)}">{html.escape(skill.rel_source)}</a>.</p>\n'
        + related_html
    )
    write(
        out,
        f"{skill.url_path}index.html",
        page(
            title=f"{skill.heading} — Agent Skill",
            description=meta_description(skill.description),
            canonical=f"{base_url}/{skill.url_path}",
            body=body,
            depth=2,
            base_url=base_url,
        ),
    )


def build_install_pages(out: Path, skills: list[Skill], base_url: str) -> None:
    rows = "\n".join(
        f'<tr><td><a href="{slug}/">{html.escape(nameinfo[0])}</a></td>'
        f"<td><code>{html.escape(nameinfo[1])}</code></td></tr>"
        for slug, nameinfo in AGENTS.items()
    )
    body = (
        "<h1>Install game dev agent skills</h1>\n"
        '<p class="lead">One command detects the coding agent you already use and writes '
        "the router plus every skill to the right directory.</p>\n"
        + install_block()
        + "\n<h2>Skills directory per agent</h2>\n"
        f"<table>\n<thead><tr><th>Agent</th><th>Skills directory</th></tr></thead>\n"
        f"<tbody>\n{rows}\n</tbody>\n</table>"
    )
    write(
        out,
        "install/index.html",
        page(
            title="Install game dev agent skills in any AI coding agent",
            description=meta_description(
                "Install game development agent skills into Claude Code, Cursor, Kiro, "
                "Codex, Gemini CLI, Copilot, Windsurf or Cline with one command."
            ),
            canonical=f"{base_url}/install/",
            body=body,
            depth=1,
            base_url=base_url,
        ),
    )

    for slug, (display, directory, note) in AGENTS.items():
        note_html = f"<p>{html.escape(note)}</p>\n" if note else ""
        body = (
            f"<h1>Install game dev agent skills in {html.escape(display)}</h1>\n"
            f'<p class="lead">Add {len(skills)} version-pinned game development skills '
            f"and a router to {html.escape(display)}. The router detects your engine from "
            "the project files and loads only the skills that fit the request.</p>\n"
            + install_block(
                f'<p>The CLI writes to <code>{html.escape(directory)}</code>. '
                f"To install by hand, copy a skill's folder into that directory.</p>\n"
                + note_html
            )
            + '\n<h2>Browse the skills</h2>\n<p>'
            + ", ".join(
                f'<a href="../../{slug2}/">{html.escape(CATEGORIES[slug2][0])}</a>'
                for slug2 in CATEGORIES
            )
            + "</p>"
        )
        write(
            out,
            f"install/{slug}/index.html",
            page(
                title=f"Game dev agent skills for {display} — install guide",
                description=meta_description(
                    f"Install {len(skills)} game development agent skills in {display}. "
                    f"Skills live in {directory} and cover Godot, Unity, Unreal and web engines."
                ),
                canonical=f"{base_url}/install/{slug}/",
                body=body,
                depth=2,
                base_url=base_url,
            ),
        )


def build_sitemap(out: Path, urls: list[str], base_url: str) -> None:
    today = date.today().isoformat()
    entries = "\n".join(
        f"  <url><loc>{html.escape(u)}</loc><lastmod>{today}</lastmod></url>" for u in urls
    )
    write(
        out,
        "sitemap.xml",
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{entries}\n</urlset>\n",
    )
    write(
        out,
        "robots.txt",
        f"User-agent: *\nAllow: /\n\nSitemap: {base_url}/sitemap.xml\n",
    )


# --------------------------------------------------------------------------- #

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(DEFAULT_OUT), help="output directory")
    ap.add_argument("--base-url", default=DEFAULT_BASE_URL, help="canonical base URL")
    args = ap.parse_args()

    base_url = args.base_url.rstrip("/")
    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    skills = collect_skills()
    if not skills:
        print("No SKILL.md files found under skills/.")
        return 1

    by_cat: dict[str, list[Skill]] = {}
    for s in skills:
        by_cat.setdefault(s.category, []).append(s)

    unknown = sorted(set(by_cat) - set(CATEGORIES))
    if unknown:
        print(f"FAILED — skills use unknown category values: {', '.join(unknown)}")
        return 1

    urls = [f"{base_url}/", f"{base_url}/install/"]

    build_index(out, skills, base_url)
    build_install_pages(out, skills, base_url)
    urls += [f"{base_url}/install/{slug}/" for slug in AGENTS]

    for slug, group in by_cat.items():
        build_category(out, slug, group, base_url)
        urls.append(f"{base_url}/{slug}/")
        for skill in group:
            build_skill(out, skill, group, base_url)
            urls.append(f"{base_url}/{skill.url_path}")

    write(out, "styles.css", STYLES)
    build_sitemap(out, urls, base_url)

    print(f"Generated {len(urls)} pages for {len(skills)} skills into {out}/")
    print(f"Categories: {', '.join(f'{k}={len(v)}' for k, v in sorted(by_cat.items()))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
