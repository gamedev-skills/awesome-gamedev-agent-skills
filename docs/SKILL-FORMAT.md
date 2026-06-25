# Skill Authoring Standard

This is the canonical standard for every skill in this repository. It is the contract
that keeps 60+ skills consistent and high quality. Read it
fully before authoring or reviewing a skill.

> **Status: FROZEN for v1.** This standard is applied as written — do not reinterpret it. If a
> genuine gap or contradiction is found, raise it in review and resolve it there; do not silently
> diverge. The companion files are [`COMPATIBILITY.md`](COMPATIBILITY.md) (where each agent
> looks for skills) and [`INSTALLATION.md`](INSTALLATION.md) (how to install them).

> **Format basis:** the **Agent Skills open standard** (agentskills.io), consumed natively by
> Claude Code, the Claude Agent SDK, Kiro, Gemini CLI, Codex CLI, and compatible agents. The
> portable core is `SKILL.md`; nothing agent-specific ever goes in a committed skill.

---

## 1. What a skill is

A skill is a **directory** containing a `SKILL.md` file and, optionally, supporting folders.
The agent pre-loads only the `name` + `description` of every skill; it reads the body **on
demand**, and reads bundled files **only when needed**. This is *progressive disclosure* —
design for it.

```
skills/<category>/<skill-name>/
├── SKILL.md            # required — the playbook (keep < 500 lines)
├── references/         # optional — deep docs the agent reads on demand (one level deep)
│   └── *.md
├── scripts/            # optional — runnable, deterministic helpers
│   └── *.{py,sh,gd,lua,...}
└── assets/             # optional — templates, configs, sample files
```

`references/`, `scripts/`, and `assets/` are the **only** permitted top-level subfolders.

### Progressive-disclosure budget (design to these numbers)

| Tier | What loads | When | Budget |
|------|-----------|------|--------|
| 1 — Metadata | `name` + `description` | At startup, for **every** skill | ~100 tokens / skill |
| 2 — Instructions | the `SKILL.md` body | when the skill activates | **< 5000 tokens** (and **< 500 lines**) |
| 3 — Resources | `references/`, `scripts/`, `assets/` | read/executed on demand | effectively unbounded |

---

## 2. Frontmatter

Frontmatter is YAML between two `---` fences, and must be the **very first bytes** of the file
(no BOM, no blank line before the opening `---`).

```yaml
---
name: love2d-core                  # REQUIRED. 1–64 chars. lowercase a-z, 0-9, hyphens.
                                   #   No leading/trailing hyphen, no consecutive hyphens.
                                   #   MUST equal the folder name. Unique across the repo.
description: >                     # REQUIRED. 1–1024 chars. Third person.
  Structure a LÖVE (Love2D) game in Lua — the love.load/update/draw loop, delta-time
  movement, input handling, and simple state stacks. Use when building or debugging a
  LÖVE (.love) game, or when the user mentions love2d, love.run, conf.lua, or main.lua.
license: Apache-2.0                # optional
compatibility: LÖVE 11.5 (Lua 5.1 / LuaJIT)   # optional, ≤500 chars (engine/runtime/network)
metadata:                          # optional; a flat string→string map
  engine: love2d
  category: other-engines
  difficulty: beginner
---
```

### 2.1 Field reference (exact limits — from the open standard)

| Field | Required | Limit | Rules |
|-------|:--------:|-------|-------|
| `name` | **Yes** | **1–64 chars** | `^[a-z0-9]+(-[a-z0-9]+)*$` — lowercase/digits/hyphens; no leading/trailing/consecutive hyphen. **Equals the parent folder name. Unique repo-wide.** Must not contain XML tags or the reserved words `anthropic`/`claude`. |
| `description` | **Yes** | **1–1024 chars** | States *what it does* **and** *when to use it*; embeds real trigger words. No XML tags. See §3. |
| `license` | No | short | e.g. `Apache-2.0` (repo default). |
| `compatibility` | No | **1–500 chars** | Runtime/engine/network requirements, e.g. `Godot 4.3+`, `Unity 6 (6000.0 LTS)`. |
| `metadata` | No | — | A flat **string→string** map. This repo uses `engine`, `category`, `difficulty`. No nested/non-string values. |

`version` is **not** a top-level field. If you must record a target version beyond
`compatibility`, put it inside `metadata` — but `compatibility` is the canonical place.

### 2.2 Forbidden frontmatter keys (hard reject)

These are agent-specific keys that must never appear in a committed `SKILL.md`. Some agents
(Cursor, for example) accept a few of them, but keeping them out of the source is exactly what
makes one file portable across every agent. The validator fails the build if any appear:

```
when_to_use   argument-hint   disable-model-invocation   user-invocable   model
paths         hooks           shell                      context          globs
alwaysApply   trigger
```

`allowed-tools` is part of the open standard (experimental, honored by most agents but not all —
Kiro, for instance, ignores it); this repo **omits it by default** and the validator emits a
**warning** if present. Keeping the core free of these keys is exactly what lets one file install
across every agent (see [`COMPATIBILITY.md`](COMPATIBILITY.md)).

### 2.3 Cross-surface portability note (claude.ai)

The hard cap on `description` is **1024 chars**, but **claude.ai's upload UI truncates at
200 chars**. Treat **≤200 chars as a soft target**: lead with the primary use case so the
skill still triggers correctly if the description is clipped. The validator warns above 200.

---

## 3. Writing the `description` (the most important line you write)

The agent decides whether to trigger a skill almost entirely from `name` + `description`.
A weak description = a skill that never fires, or fires on the wrong task.

- **Lead with what it does, then when to use it** ("Use when …"). Put the primary use case
  first — retrieval budgets truncate the tail.
- **Embed the exact trigger vocabulary a user types:** engine name + version, node/class
  names (`CharacterBody2D`, `MonoBehaviour`, `AnimationTree`), file types (`.tscn`, `.gd`,
  `main.lua`), and genre words.
- **Be specific and disambiguating.** A `godot-2d-movement` skill must not fire for a 3D FPS;
  point to the sibling skill that does.
- **Third person, no "I"/"we".** No marketing adjectives (`amazing`, `best`, `powerful`,
  `ultimate`).

---

## 4. Body structure (the `SKILL.md` playbook)

Keep it scannable, imperative, and lean. Choose a **body archetype** on purpose:

- a **knowledge** skill — task-bucketed recipes, code-forward; or
- a **workflow** skill — numbered steps, decision points, pitfalls, anti-pattern call-outs.

Either way, include these sections:

1. **Title + one-line purpose.**
2. **When to use / when not to use** — sharpen the trigger boundary; name the sibling skill
   that owns what this one doesn't.
3. **Core workflow** — numbered, decision-oriented steps the agent follows.
4. **Patterns / recipes** — **≥2** short, correct, **version-pinned** code blocks for the
   most common tasks. Show the right way; name the wrong way to avoid.
5. **Pitfalls & gotchas** — version traps, performance footguns, common bugs.
6. **References** — point to `references/*.md` for depth ("For X, read `references/x.md`").
   Push long tables, API dumps, and rarely-needed detail there.

Principles: **procedural, not encyclopedic**; **decisions first**; **one responsibility per
skill** (if it sprawls, split it and let the router compose); **< 500 lines** (move depth to
`references/`).

---

## 5. Authoring principles (L1–L10) — the distilled standard

These ten principles, derived from studying the ecosystem and the primary specs, are the
heart of the standard. Every rule above and rubric item below traces back to one of them.

- **L1 — Write the description as a routing rule.** What it does, then when to use it, with
  the exact words a developer types (engine + version, class/node names, file types, genre).
  Lead with the primary use case; stay specific; fit the retrieval budget.
- **L2 — Design for progressive disclosure with explicit budgets.** Tiny always-loaded
  metadata; a lean body (**< 500 lines**, well under ~5k tokens) about *how to act*; depth in
  `references/` (one level deep); deterministic helpers in `scripts/`; templates in `assets/`.
- **L3 — One responsibility per skill.** Prefer many sharp, well-named skills over a few broad
  ones; they auto-trigger more accurately. If a skill sprawls, split it.
- **L4 — Choose a body archetype on purpose** (knowledge *or* workflow). Keep it procedural
  and scannable, with a short when-to-use / when-not boundary.
- **L5 — Pin versions and verify against primary docs.** State the engine/runtime version,
  verify every API against official documentation, never invent APIs, and call out changes
  across major versions (e.g. Godot 3→4 idioms).
- **L6 — Bake in verification suited to the medium.** For games: inspect the scene tree,
  validate scenes/scripts, run headless, capture screenshots / playtest — and report only
  what was actually observed, never assumed.
- **L7 — The standard is enforced mechanically.** The validator checks `name` == folder,
  required frontmatter, description quality, size/token budgets, resolved cross-references,
  and forbidden keys. Run it before every commit.
- **L8 — Make composition explicit.** Provide "Related skills" cross-references and clear
  hand-offs between skills used together (player controller → input + state machine +
  animation). The master router composes them; you make composition legible.
- **L9 — Be portable by construction.** Keep the `SKILL.md` core agent-neutral so it loads
  unchanged in every agent; never embed agent-specific keys in the source file.
- **L10 — Treat trust & safety as first-class.** Scope each skill to what it needs, avoid
  undocumented network calls in `scripts/`, prefer bundled references over live fetches where
  staleness matters, ship no secrets, and write everything originally from primary sources.

---

## 6. Code & technical accuracy

- Code must be **correct and idiomatic** for the stated version. Do not invent APIs, signals,
  or methods. When unsure, **verify against primary docs** (official engine documentation) via
  Firecrawl before writing.
- **Pin versions.** State the engine/runtime the patterns target (e.g. "Godot 4.3", "Unity 6
  / 6000.0 LTS", "Unreal 5.4+", "Bevy 0.16+", "LÖVE 11.5"). Note breaking changes between major
  versions where it matters.
- Prefer **minimal, runnable** snippets over large dumps. Each snippet makes one point.
- `scripts/` are for **deterministic** helpers the agent can run (generators, validators,
  converters). Make them self-contained and documented at the top; no undocumented network calls.

---

## 7. Originality & licensing (mandatory)

- **Write from scratch from primary sources.** Other repos/skills may be studied for
  *structure and ideas only*. Never paste their prose or code.
- Cite **primary documentation** (official engine/framework docs) as the source of truth.
- All skills are licensed **Apache-2.0** (repo default). If a pattern is genuinely derived from
  a permissively licensed source, attribute it in [`NOTICE`](../NOTICE).
- **No growth/marketing language** in any committed file (no "stars", launch, or
  competitor-comparison text).

---

## 8. Cross-agent portability (the portable-core rule)

The `SKILL.md` open standard is the portable core. The full per-agent breakdown lives in
[`COMPATIBILITY.md`](COMPATIBILITY.md); the rules an author must internalize:

- **Skills load natively across the ecosystem.** Claude Code (`.claude/skills/`), Claude.ai (zip
  upload), Cursor, Windsurf, Cline, Codex, Gemini CLI, GitHub Copilot, Kiro (`.kiro/skills/`),
  VS Code and many more read `SKILL.md` directly. `.agents/skills/<name>/SKILL.md` is the shared
  directory several CLI agents read.
- **Install with the `skills` CLI** (`npx skills add …`) — it detects the agent and writes to the
  right path. There is no rule-file conversion: nothing to generate, nothing to hand-fork.
- **Keep the body agent-neutral.** A basic skill (name + description + body + optional resources)
  works everywhere; the only cross-agent differences are optional fields (`allowed-tools`, `hooks`,
  `context: fork`), which this repo deliberately omits.

---

## 9. Quality rubric (a skill ships only if every box is true)

This rubric is what the validator and review enforce. `[E]` = checked as a hard error
by `scripts/validate-skills.py`; `[W]` = warning / human-reviewed.

- [ ] **[E]** Folder name = `name`; lowercase/digits/hyphens; ≤64 chars; no leading/trailing/
      consecutive hyphen; **unique repo-wide**.
- [ ] **[E]** `description` present, ≤1024 chars. **[W]** states what + when, contains real
      trigger words, third person, no marketing adjectives, ≤200 chars for claude.ai portability.
- [ ] **[E]** `compatibility` (if present) ≤500 chars.
- [ ] **[E]** No forbidden frontmatter keys (§2.2). **[W]** `allowed-tools` absent.
- [ ] **[E]** `SKILL.md` < 500 lines. **[W]** body < ~5000 tokens.
- [ ] **[W]** Body has: when-to-use, core workflow, **≥2** correct code patterns, pitfalls,
      references.
- [ ] **[W]** All code is version-pinned, idiomatic, and verified against primary docs (no
      invented APIs).
- [ ] **[W]** Original prose & code — no copied content; primary sources cited.
- [ ] **[W]** No growth/marketing language. No secrets. No undocumented network calls in scripts.
- [ ] **[E]** Internal `references/` links resolve. **[W]** references are one level deep;
      only `references/`/`scripts/`/`assets/` subfolders present.
- [ ] **[E]** Passes the validator (`python scripts/validate-skills.py`).

---

## 10. The golden reference skill

[`skills/other-engines/love2d-core/`](../skills/other-engines/love2d-core/) is the **golden
reference**. It demonstrates this standard end-to-end: a routing-rule
description, the six body sections, ≥2 version-pinned patterns, a pitfalls list, and a
`references/` file for progressive disclosure. **Copy its shape.** When in doubt about
structure, open it.

Start every new skill from [`../templates/SKILL.template.md`](../templates/SKILL.template.md).

---

## 11. Validator

```bash
python scripts/validate-skills.py
```

Pure Python, no dependencies. It validates every `skills/**/SKILL.md` and `router/SKILL.md`
against this standard (frontmatter limits, `name` == folder, < 500 lines, resolved
`references/` links) and exits non-zero with a precise report on any failure. Fix every
reported problem before you commit.
