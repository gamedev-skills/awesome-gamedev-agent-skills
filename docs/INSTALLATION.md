# Installation

How to install these skills into any supported agent. The compatibility details (per-agent paths,
triggers, and optional fields) live in [`COMPATIBILITY.md`](COMPATIBILITY.md); this page is the
practical how-to. The fastest route for every agent is the
[universal `skills` CLI](#universal-installer-any-agent).

## The one rule

Skills are stored here as:

```
skills/<category>/<name>/SKILL.md
```

The `<name>/` folder — the direct parent of `SKILL.md` — **is** the skill, and its name equals
the skill's `name`. To install a skill, copy that `<name>/` folder (with its `references/`,
`scripts/`, `assets/` if present) into the agent's skills directory. Skill names are unique
across this repository, so installing every skill into one flat directory is safe.

**Install the router too.** The [`router/`](../router) folder is itself a skill (its `SKILL.md`
is the dispatcher). Copy it in alongside the others so the agent can route requests:
`cp -R router <agent-skills-dir>/router`. The bulk-install snippets below copy everything under
`skills/`; add the router with the extra line shown for Claude Code.

> The examples below use one skill (`godot-tilemap`) and POSIX shell. On Windows PowerShell,
> replace `cp -R src dest` with `Copy-Item -Recurse src dest` and `mkdir -p` with `mkdir`.

## Universal installer (any agent)

The [`skills` CLI](https://www.npmjs.com/package/skills) is the package manager for the Agent
Skills ecosystem. It detects the agents installed on your machine and copies the skills (the
router plus all 62) into each one's skills directory — no clone required:

```bash
# install into whatever agent(s) you have
npx skills add AbhishekBarali/awesome-gamedev-agent-skills

# preview the skill list without installing anything
npx skills add AbhishekBarali/awesome-gamedev-agent-skills --list

# target one agent · install globally for all projects · grab a subset
npx skills add AbhishekBarali/awesome-gamedev-agent-skills -a cursor
npx skills add AbhishekBarali/awesome-gamedev-agent-skills -g
npx skills add AbhishekBarali/awesome-gamedev-agent-skills -s godot-tilemap -s platformer
```

Companions: `npx skills list` (what's installed), `npx skills update` (pull latest), and
`npx skills remove` (uninstall). This is the recommended path for Cursor, Windsurf, Cline, Codex,
Gemini CLI, GitHub Copilot, Kiro, and most other agents. The sections below cover each agent's
native or manual route if you'd rather not use the CLI.

## Claude Code (plugin — recommended)

This repo is a Claude Code plugin marketplace (see [`.claude-plugin/marketplace.json`](../.claude-plugin/marketplace.json)),
so you can install it without cloning or copying files. Add the marketplace once:

```bash
claude plugin marketplace add AbhishekBarali/awesome-gamedev-agent-skills
```

Easiest — install the router and all 62 skills in one command:

```bash
claude plugin install gamedev@awesome-gamedev-agent-skills
```

Or install just what you use (each engine and category is its own plugin):

```bash
claude plugin install router@awesome-gamedev-agent-skills        # always install this
claude plugin install godot@awesome-gamedev-agent-skills         # engine: godot | unity | unreal | web-engines | other-engines
claude plugin install disciplines@awesome-gamedev-agent-skills   # cross-engine concepts
claude plugin install genres@awesome-gamedev-agent-skills        # genre templates
claude plugin install workflows@awesome-gamedev-agent-skills     # jam / prototype / shipping
```

Verify with `/plugin` or `/skills` inside Claude Code.

## Claude Code (manual copy)

Prefer to copy files instead of using the plugin system:

```bash
# project-local
mkdir -p .claude/skills
cp -R skills/godot/godot-tilemap .claude/skills/

# …or every skill (names are globally unique, so flattening is safe)
find skills -name SKILL.md -type f -exec dirname {} \; | while read -r d; do
  cp -R "$d" .claude/skills/
done
cp -R router .claude/skills/router   # the dispatcher — install it too
```

For all projects, copy into `~/.claude/skills/` instead. Claude Code auto-triggers a skill from
its `description`; `/skills` opens an interactive menu.

## Kiro

```bash
mkdir -p .kiro/skills          # or ~/.kiro/skills for global
cp -R skills/godot/godot-tilemap .kiro/skills/
```

The default agent auto-loads skills from both locations. A **custom** agent must opt in via its
`resources`:

```json
{ "name": "my-agent",
  "resources": ["skill://.kiro/skills/*/SKILL.md", "skill://~/.kiro/skills/*/SKILL.md"] }
```

Trigger automatically by description match, or explicitly with `/skill-name`.

## Gemini CLI & Codex CLI (shared location)

Both read `.agents/skills/`, so one copy serves both:

```bash
mkdir -p .agents/skills        # repo-local; or ~/.agents/skills for user-global
cp -R skills/godot/godot-tilemap .agents/skills/
```

Gemini CLI and Codex can also be targeted by the universal CLI, no clone needed:

```bash
npx skills add AbhishekBarali/awesome-gamedev-agent-skills -a gemini-cli   # or: -a codex
```

- **Gemini CLI:** manage and verify with `/skills`; activation prompts for consent.
- **Codex CLI:** list with `/skills`, or mention `$godot-tilemap`; implicit activation by
  description also works.

## Claude Agent SDK (Python)

Skills are filesystem artifacts under `.claude/skills/`; load them by setting
`setting_sources`:

```python
from claude_agent_sdk import ClaudeAgentOptions

options = ClaudeAgentOptions(
    cwd="/path/to/project",                 # contains .claude/skills/
    setting_sources=["user", "project"],    # REQUIRED, or no skills are discovered
    skills="all",                           # or ["godot-tilemap", ...]
    allowed_tools=["Read", "Write", "Bash", "Skill"],
)
```

## Claude.ai

1. Settings → Capabilities → enable **Code execution**.
2. Zip the skill folder so that the folder (named exactly like `name`) is the zip root and
   `SKILL.md` sits inside it.
3. Customize → Skills → **Upload**.

Keep `description` ≤ 200 characters so it is not truncated by the upload UI.

## Cursor / Windsurf / Cline (native skills)

These editors read `SKILL.md` natively — there is no rule-file conversion. The simplest install is
the universal CLI (`npx skills add AbhishekBarali/awesome-gamedev-agent-skills -a cursor`; swap in
`windsurf` or `cline`). To place files by hand:

```bash
# Cursor — project; use ~/.cursor/skills for global. Cursor also reads .agents/skills and .claude/skills
mkdir -p .cursor/skills && cp -R skills/godot/godot-tilemap .cursor/skills/

# Windsurf (Cascade) — global lives at ~/.codeium/windsurf/skills/
mkdir -p .windsurf/skills && cp -R skills/godot/godot-tilemap .windsurf/skills/

# Cline — also reads .claude/skills/ ; enable via Settings → Features → Enable Skills
mkdir -p .cline/skills && cp -R skills/godot/godot-tilemap .cline/skills/
```

Copy `router` into the same directory so the agent can route requests. Each editor surfaces skills
by description and via `/skill-name`; the per-agent paths are in
[`COMPATIBILITY.md`](COMPATIBILITY.md).

## Verify after installing

Open your agent and confirm the skill is listed (e.g. `/skills` in Claude Code, Kiro, Codex, or
Gemini). Then ask a question that should trigger it — for `godot-tilemap`, something like
"set up a tilemap with autotiling in Godot" — and confirm the skill activates.
