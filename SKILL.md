---
name: awesome-gamedev-agent-skills
description: >
  66 game-development Agent Skills + a master router for AI coding agents.
  Covers Godot, Unity, Unreal, Phaser, PixiJS, three.js, Bevy, pygame, LÖVE,
  and Roblox — plus cross-engine disciplines (game AI, procedural gen, shaders,
  save systems, game-feel, camera, performance, and more), genre templates
  (platformer, roguelike, RPG, FPS, tower-defense, card game, visual novel,
  survival-crafting, puzzle), and shipping workflows (game jam, Steam, itch.io).
  Install once; the router detects your engine and task from your project files
  and loads only the skills you need. Every skill is written from primary docs,
  version-pinned, and validated. Use when building any kind of game with an AI
  coding agent.
license: Apache-2.0
---

# awesome-gamedev-agent-skills

An open collection of **66 game-development Agent Skills** plus a **master
router** (67 `SKILL.md` files total) for AI coding agents.

## How it works

1. You install the collection once.
2. You ask your agent a game-dev question in plain English.
3. The **router** detects your engine from the project files, classifies the
   task, and loads only the skills that match — not all 66.

Example: *"add a double jump to my Godot player"* → the router loads
`godot-2d-movement` + `platformer`. Nothing else touches your context.

## What's inside

| Category | Count | Examples |
|----------|:-----:|---------|
| Engines | 40 | Godot (15), Unity (8), Unreal (6), web (6), others (5) |
| Disciplines | 13 | game-ai, procedural-gen, shaders, save-systems, game-feel, camera, performance |
| Genres | 9 | platformer, roguelike, rpg, fps, tower-defense, card-game, visual-novel, survival, puzzle |
| Workflows | 4 | game-jam, prototype-fast, steam-publish, itch-publish |

Every skill is written from primary documentation, version-pinned (Godot 4.x,
Unity 6, UE 5.4+, Phaser 3, PixiJS v8, three.js r176+, Bevy 0.16+, pygame 2.6,
LÖVE 11.5, Roblox), and checked by `scripts/validate-skills.py`.

## Install

```bash
npx skills add AbhishekBarali/awesome-gamedev-agent-skills
```

Works with Claude Code, Cursor, Windsurf, Cline, OpenAI Codex, Gemini CLI,
GitHub Copilot, Kiro, Antigravity, and any agent that reads the `SKILL.md`
format. See `docs/INSTALLATION.md` for per-agent paths.

## Links

- Repository: https://github.com/AbhishekBarali/awesome-gamedev-agent-skills
- Router logic: `router/SKILL.md`
- Full catalog: `skills/` (8 subcategories)
- Compatibility: `docs/COMPATIBILITY.md`
