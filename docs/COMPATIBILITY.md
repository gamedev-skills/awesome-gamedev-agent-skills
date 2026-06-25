# Compatibility

Every skill in this repository is a plain `SKILL.md` folder in the
[Agent Skills](https://agentskills.io) open standard: YAML frontmatter (`name` + `description`)
followed by a Markdown playbook, with optional `references/`, `scripts/`, and `assets/`. The
standard was created by Anthropic and released as an open format; it is now read **natively** by a
large and growing set of AI coding agents and IDEs. There is no editor-specific rule file to
maintain and nothing to convert — the same file installs everywhere.

For step-by-step install commands, see [`INSTALLATION.md`](INSTALLATION.md).

## TL;DR

- **A skill is just a folder with a `SKILL.md`.** Agents preload only `name` + `description`, then
  read the body when a request matches, then read bundled files on demand (progressive disclosure).
- **It's broadly supported.** Claude Code, Claude, Cursor, Windsurf, Cline, OpenAI Codex, Gemini
  CLI, GitHub Copilot, Kiro, VS Code, Roo Code, Junie, Trae, Factory, Tabnine, OpenCode, Goose and
  [many others](https://agentskills.io/clients) load the standard directly.
- **One installer covers all of them.** `npx skills add AbhishekBarali/awesome-gamedev-agent-skills`
  detects the agents you have installed and copies the skills (router included) to the right place.
- **The skills here use only the portable core**, so a single tree works in every agent — no
  per-tool variants.

## Install in one line

The [`skills` CLI](https://www.npmjs.com/package/skills) is the package manager for the Agent
Skills ecosystem. It auto-detects your agent(s) and writes skills to each one's directory:

```bash
# install the router + all 62 skills into whatever agent(s) you have
npx skills add AbhishekBarali/awesome-gamedev-agent-skills

# preview without installing
npx skills add AbhishekBarali/awesome-gamedev-agent-skills --list

# target a specific agent, and/or install globally for every project
npx skills add AbhishekBarali/awesome-gamedev-agent-skills -a cursor -g
```

This repo ships a `.claude-plugin/marketplace.json`, which the CLI also reads, so the master
[`router/`](../router) skill is discovered alongside the catalog under `skills/`. Claude Code users
can alternatively use the native plugin commands (see [`INSTALLATION.md`](INSTALLATION.md)).

## Where each agent looks for skills

Skills install per-project (committed with your repo) or globally (every project). Paths can change
as tools evolve, so the `skills` CLI is the most reliable installer; the table below lists the
documented project locations and how each agent triggers a skill. Each row links to that agent's
own skills documentation.

| Agent | Project skills directory | How it triggers | Docs |
|-------|--------------------------|-----------------|------|
| **Claude Code** | `.claude/skills/` | auto by description · `/skills` | [docs](https://code.claude.com/docs/en/skills) |
| **Claude** (claude.ai) | upload the skill as a `.zip` | auto in chat | [docs](https://support.claude.com/) |
| **Cursor** | `.agents/skills/` or `.cursor/skills/` | auto by description · `/skill-name` | [docs](https://cursor.com/docs/skills) |
| **Windsurf** (Cascade) | `.windsurf/skills/` | auto by description · `/skill-name` | [docs](https://docs.windsurf.com/) |
| **Cline** | `.cline/skills/` (also reads `.claude/skills/`) | auto (`use_skill`) · `/skill-name` · *enable in Settings* | [docs](https://docs.cline.bot/customization/skills) |
| **OpenAI Codex** | `.agents/skills/` | `$skill` · `/skills` · implicit | [docs](https://developers.openai.com/codex/skills) |
| **Gemini CLI** | `.agents/skills/` or `.gemini/skills/` | activation + consent · `/skills` | [docs](https://geminicli.com/docs/cli/skills/) |
| **GitHub Copilot** | `.agents/skills/` | auto by description | [docs](https://docs.github.com/en/copilot/concepts/agents/about-agent-skills) |
| **Kiro** | `.kiro/skills/` (+ `~/.kiro/skills/`) | auto by description · `/skill-name` | [docs](https://kiro.dev/docs/cli/skills/) |
| **Others** (VS Code, Roo Code, Junie, Trae, Factory, Tabnine, OpenCode, Goose, …) | see each tool | varies | [client list](https://agentskills.io/clients) |

`.agents/skills/` is the shared, cross-agent convention that many tools read, which is why one copy
there can serve several agents at once. The `skills` CLI maps each agent to its correct location
automatically, so you rarely need to track these by hand.

> **Kiro note.** The default Kiro agent auto-loads skills from `.kiro/skills/` and
> `~/.kiro/skills/` with no extra setup. A **custom** agent must opt in via its `resources`, e.g.
> `"resources": ["skill://.kiro/skills/**/SKILL.md"]`.

> **Cline note.** Skills are an experimental feature — enable them under
> **Settings → Features → Enable Skills** before they appear.

## The only real "compatibility" wrinkle: optional fields

A **basic skill** — `name`, `description`, a Markdown body, and optional `scripts/`/`references/`/
`assets/` — works in every skills-compatible agent. The differences between agents live entirely in
a few **optional, advanced** frontmatter fields:

| Optional field | Honored by | Notes |
|----------------|-----------|-------|
| `allowed-tools` | most agents (e.g. Claude Code, Codex, Cursor, Cline) | **not** honored by Kiro; ignored where unsupported |
| `hooks` | Claude Code, Cline, Kiro | per-agent lifecycle hooks |
| `context: fork` | Claude Code only | runs the skill in a forked context |

Because these are optional, an agent that doesn't support one simply ignores it — it does not break
the skill. **Every committed skill in this repo deliberately uses only the portable core** (below),
so the same file is valid and useful in every agent, and the validator (`scripts/validate-skills.py`)
keeps it that way.

## What's in a committed `SKILL.md` (the portable core)

- **Frontmatter:** `name` (1–64 chars; lowercase, digits, hyphens; equals the folder name) and
  `description` (≤1024 chars; says *what it does* **and** *when to use it*). Optionally `license`,
  `compatibility`, and a flat `metadata` map (we use `engine` / `category` / `difficulty`).
- **Body:** the open-standard playbook — when-to-use, workflow, patterns, pitfalls, references —
  kept under ~500 lines, with depth pushed into `references/`.

The validator rejects agent-specific frontmatter keys (`allowed-tools`, `paths`,
`disable-model-invocation`, `globs`, `alwaysApply`, `trigger`, `hooks`, `model`, …). Some agents
(e.g. Cursor) accept several of these, but keeping them out of the source is what lets one file run
unchanged in all of them; an agent-specific field is set at install time, never baked into the
shared skill.

## Verify after installing

1. List installed skills — `npx skills list`, or `/skills` inside agents that expose it.
2. Ask a prompt that should route — e.g. *"set up a tilemap with autotiling in Godot"* — and
   confirm the router loads the matching skill(s) before it edits code.

## Why this is portable

The standard formalizes two things: **progressive disclosure** (metadata → body → resources) and a
tiny required frontmatter contract (`name` + `description`). Any agent that implements the standard
can load any compliant skill, so a correct `SKILL.md` is portable by construction — the broad
adoption above is what turns "write it once" into "runs everywhere."

---

*Sources (checked 2026-06-25): the Agent Skills [specification](https://agentskills.io/specification)
and [client list](https://agentskills.io/clients); the [`skills` CLI](https://www.npmjs.com/package/skills);
and the official skills docs for [Cursor](https://cursor.com/docs/skills),
[Cline](https://docs.cline.bot/customization/skills), [Codex](https://developers.openai.com/codex/skills),
and [Kiro](https://kiro.dev/docs/cli/skills/). Content was rephrased for compliance with licensing
restrictions.*
