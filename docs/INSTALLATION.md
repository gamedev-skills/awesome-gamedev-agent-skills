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
Skills ecosystem. It detects the agents installed on your machine and installs the skills (the
router plus all 78) into each one's skills directory — no clone required. It needs Node.js 22.20
or later. Interactive runs ask which skills and agents to use; by default each agent directory is
a symlink to one shared copy (add `--copy` for independent copies, `-y` to skip the prompts):

```bash
# install into whatever agent(s) you have
npx skills add gamedev-skills/awesome-gamedev-agent-skills

# preview the skill list without installing anything
npx skills add gamedev-skills/awesome-gamedev-agent-skills --list

# target one agent · install globally for all projects · grab a subset
npx skills add gamedev-skills/awesome-gamedev-agent-skills -a cursor
npx skills add gamedev-skills/awesome-gamedev-agent-skills -g
npx skills add gamedev-skills/awesome-gamedev-agent-skills --skill godot-tilemap --skill platformer
```

Companions: `npx skills list` (what's installed), `npx skills check` (look for updates),
`npx skills update` (pull latest), and `npx skills remove` (uninstall). This is the recommended
path for Cursor, Windsurf, Codex, Gemini CLI, GitHub Copilot, Kiro, and most other agents. For
Cline, check that the skills appear afterwards: the CLI writes Cline installs to `.agents/skills/`,
which Cline's own docs do not list (see [Cline](#cursor--windsurf--cline-native-skills) below).
The sections below cover each agent's native or manual route if you'd rather not use the CLI.

## Claude Code (plugin — recommended)

This repo is a Claude Code plugin marketplace (see [`.claude-plugin/marketplace.json`](../.claude-plugin/marketplace.json)),
so you can install it without cloning or copying files. Add the marketplace once:

```bash
claude plugin marketplace add gamedev-skills/awesome-gamedev-agent-skills
```

Easiest — install the router and all 78 skills in one command:

```bash
claude plugin install gamedev@awesome-gamedev-agent-skills
```

Or install just what you use (each engine and category is its own plugin):

```bash
claude plugin install router@awesome-gamedev-agent-skills        # always install this
claude plugin install godot@awesome-gamedev-agent-skills         # engine: godot | unity | unreal | ebitengine | web-engines | other-engines
claude plugin install disciplines@awesome-gamedev-agent-skills   # cross-engine concepts
claude plugin install genres@awesome-gamedev-agent-skills        # genre templates
claude plugin install workflows@awesome-gamedev-agent-skills     # jam / prototype / shipping
```

Verify with `/plugin` or `/skills` inside Claude Code, or `claude plugin list` in your shell. Plugin
skills are namespaced by plugin, so to invoke one directly type `/<plugin>:<skill>`, for example
`/gamedev:router` or `/godot:godot-tilemap`; automatic selection by description works as usual.

Add `--scope project` to `claude plugin marketplace add` and `claude plugin install` to record
them in the project's settings and share them with your team. To pick up a new release, run
`claude plugin marketplace update awesome-gamedev-agent-skills`, then
`claude plugin update gamedev@awesome-gamedev-agent-skills` (or the plugin you installed).

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

## Oh My Pi (omp)

omp discovers skills natively — no conversion. Copy each skill's `<name>/` folder
(flattened, as above) into the native project or user directory:

```bash
# project-local (committed; omp walks up to find .omp/skills/)
mkdir -p .omp/skills
cp -R skills/godot/godot-tilemap .omp/skills/
cp -R router .omp/skills/router   # the dispatcher — install it too

# …or every skill (names are globally unique, so flattening is safe)
find skills -name SKILL.md -type f -exec dirname {} \; | while read -r d; do
  cp -R "$d" .omp/skills/
done
```

For all projects, copy into `~/.omp/agent/skills/` instead. omp also reads the
shared `.agents/skills/` path, so one copy there serves omp alongside Codex,
Gemini CLI, and Copilot.

Skills trigger automatically by description, or explicitly with `/skill:<name>` when
`skills.enableSkillCommands` is on.

## Gemini CLI & Codex CLI (shared location)

Both read `.agents/skills/`, so one copy serves both:

```bash
mkdir -p .agents/skills        # repo-local; or ~/.agents/skills for user-global
cp -R skills/godot/godot-tilemap .agents/skills/
```

Gemini CLI and Codex can also be targeted by the universal CLI, no clone needed:

```bash
npx skills add gamedev-skills/awesome-gamedev-agent-skills -a gemini-cli   # or: -a codex
```

- **Gemini CLI:** manage and verify with `/skills`; activation prompts for consent.
- **Codex CLI:** list with `/skills`, or mention `$godot-tilemap`; implicit activation by
  description also works.

## Claude Agent SDK (Python)

Skills are filesystem artifacts under `.claude/skills/` (project) or `~/.claude/skills/` (user).
Default `query()` options already load both sources; if you set `setting_sources` yourself, keep
`"user"` and `"project"` in it or no skills are discovered:

```python
from claude_agent_sdk import ClaudeAgentOptions

options = ClaudeAgentOptions(
    cwd="/path/to/project",                 # contains .claude/skills/
    setting_sources=["user", "project"],    # only needed when overriding the default sources
    skills="all",                           # or ["godot-tilemap", ...]; adds the Skill tool for you
    allowed_tools=["Read", "Write", "Bash"],
)
```

## Claude.ai

Skills run in Claude's code sandbox and are available on Pro, Max, Team, and Enterprise plans
([Claude skills docs](https://claude.com/docs/skills/how-to)).

1. Settings → Capabilities → turn on **Code execution and file creation** (on Team and Enterprise,
   an Owner turns it on under Organization settings → Capabilities).
2. Zip the skill folder from its parent directory so that the folder (named exactly like `name`)
   is the zip root and `SKILL.md` sits inside it: `zip -r godot-tilemap.zip godot-tilemap/`.
3. Customize → Skills → upload the ZIP, then turn the skill on.

Upload the complete skill folder so bundled references, scripts, and assets remain available.

## Cursor / Windsurf / Cline (native skills)

These editors read `SKILL.md` natively — there is no rule-file conversion. The simplest install is
the universal CLI (`npx skills add gamedev-skills/awesome-gamedev-agent-skills -a cursor`; swap in
`windsurf` or `cline`). To place files by hand:

```bash
# Cursor — project; use ~/.cursor/skills for global. Cursor also reads .agents/skills and .claude/skills
mkdir -p .cursor/skills && cp -R skills/godot/godot-tilemap .cursor/skills/

# Windsurf / Devin Desktop (Cascade) — .devin/skills is preferred in current releases;
# .windsurf/skills is still read. Global: ~/.codeium/windsurf/skills/ or ~/.config/devin/skills/
mkdir -p .windsurf/skills && cp -R skills/godot/godot-tilemap .windsurf/skills/

# Cline — also reads .clinerules/skills/ and .claude/skills/ ; global: ~/.cline/skills/
mkdir -p .cline/skills && cp -R skills/godot/godot-tilemap .cline/skills/
```

Copy `router` into the same directory so the agent can route requests. Cursor and Cline also
accept `/skill-name`; Cascade uses `@skill-name` to force a skill. The per-agent paths are in
[`COMPATIBILITY.md`](COMPATIBILITY.md).

## GitHub Copilot

Copilot reads project skills from `.github/skills/`, `.claude/skills/`, or `.agents/skills/`, and
personal skills from `~/.copilot/skills/` or `~/.agents/skills/`
([docs](https://docs.github.com/en/copilot/concepts/customizations/agent-skills)). Copy the
skills into one of those directories as above, or use GitHub CLI 2.90.0 or later, whose
`gh skill` command is in public preview:

```bash
gh skill install gamedev-skills/awesome-gamedev-agent-skills --all           # every skill + router
gh skill install gamedev-skills/awesome-gamedev-agent-skills godot-tilemap   # one skill
```

`gh skill` writes source-tracking metadata into each installed `SKILL.md` so `gh skill update`
can find newer versions; `--agent` and `--scope project|user` choose where the files go.

## Verify after installing

Open your agent and confirm the skill is listed (e.g. `/skills` in Claude Code, Kiro, Codex, or
Gemini). Then ask a question that should trigger it — for `godot-tilemap`, something like
"set up a tilemap with autotiling in Godot" — and confirm the skill activates.
