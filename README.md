<!-- markdownlint-disable MD033 MD041 -->

# awesome-gamedev-agent-skills

**Game-development expertise for AI coding agents — install once, and a router loads the
right skill for whatever you're building.**

[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)
[![Skills](https://img.shields.io/badge/skills-62%20%2B%20router-brightgreen)](skills/)
[![Format](https://img.shields.io/badge/format-Agent%20Skills-informational)](docs/SKILL-FORMAT.md)
[![Last commit](https://img.shields.io/github/last-commit/AbhishekBarali/awesome-gamedev-agent-skills)](https://github.com/AbhishekBarali/awesome-gamedev-agent-skills/commits/main)

[Agent Skills](docs/SKILL-FORMAT.md) are small capability files an AI agent loads only when it
needs them. This repo gives your agent **62 game-dev skills** and a **router** that picks the
right ones for you. You describe what you're building; the agent loads the matching engine and
task skills before it writes code.

- **Cross-engine.** Godot, Unity, Unreal, Phaser, PixiJS, three.js, Bevy, pygame, LÖVE, Roblox.
- **You don't pick skills.** The router detects your engine and task and loads only what fits.
- **Built to trust.** Every skill is written from primary docs, version-pinned to a stated
  engine release, and checked by a [validator](scripts/validate-skills.py). Nothing is copied
  from other skill collections.

## Contents

- [Quick start](#quick-start)
- [What you can ask](#what-you-can-ask)
- [How the router picks skills](#how-the-router-picks-skills)
- [Catalog](#catalog)
- [Agent compatibility](#agent-compatibility)
- [Contributing](#contributing)

## Quick start

**One command, any agent.** The [`skills`](https://www.npmjs.com/package/skills) CLI detects the
coding agent you already use and installs the router plus all 62 skills into the right place:

```bash
npx skills add AbhishekBarali/awesome-gamedev-agent-skills
```

Add `--list` to preview first, `-g` to install for every project, or `-a <agent>` to target a
specific tool (`-a cursor`, `-a claude-code`, `-a gemini-cli`, …). The same `SKILL.md` files load
natively in Claude Code, Cursor, Windsurf, Cline, Codex, Gemini CLI, GitHub Copilot, Kiro, and
[dozens more](docs/COMPATIBILITY.md) — there's nothing to convert.

**Claude Code plugin (alternative).** This repo is also a Claude Code plugin marketplace, so you
can install it with Claude's own commands:

```bash
claude plugin marketplace add AbhishekBarali/awesome-gamedev-agent-skills
claude plugin install gamedev@awesome-gamedev-agent-skills
```

Building in only one engine? Install a smaller bundle — `router` plus your engine:

```bash
claude plugin install router@awesome-gamedev-agent-skills
claude plugin install godot@awesome-gamedev-agent-skills    # or: unity · unreal · web-engines · other-engines
```

Prefer to copy the files by hand, or want the exact per-tool paths? See
**[`docs/INSTALLATION.md`](docs/INSTALLATION.md)**.

Then just talk to your agent — see below.

## What you can ask

Describe the task in plain language. The router figures out the skills:

| You say | Skills it loads for you |
|---------|-------------------------|
| "add a double jump to my Godot player" | `godot-2d-movement` + `platformer` |
| "make an inventory for my Unity RPG" | `unity-scriptableobjects` + `rpg` + `save-systems` |
| "procedural dungeon roguelike in Godot" | `godot-tilemap` + `procedural-gen` + `roguelike` |
| "how should I design save slots?" | `save-systems` |
| "publish my game on itch with butler" | `itch-publish` |

You never type the skill names on the right. That's the router's job.

## How the router picks skills

You never name a skill. On each request the router does three things:

1. **Detects your engine** from project files — a `project.godot` means Godot, a `*.uproject`
   means Unreal, and so on. If it can't tell, it just asks.
2. **Reads your request** for the task — a concept (AI, shaders, saving), a genre (platformer,
   roguelike), or a shipping step (game jam, Steam).
3. **Loads only the matching skills**, in order: engine basics first, then the concept, then any
   genre glue. It re-routes if you switch to something new.

That's why "add a double jump to my Godot player" loads `godot-2d-movement` + `platformer` and
nothing else.

<details>
<summary>The exact detection signals and routing table</summary>

The full algorithm — every engine fingerprint, the task-to-skill table, and how engine,
discipline, genre, and workflow skills compose — lives in the router skill itself:
[`router/SKILL.md`](router/SKILL.md). In short: engine selection is exclusive (exactly one
engine), while disciplines, genres, and workflows are additive on top.

</details>

## Catalog

62 skills across 8 categories — each links to its `SKILL.md` below.

### Engines

#### Godot — 15 ([`skills/godot/`](skills/godot/)) · Godot 4.x

| Skill | Scope |
|-------|-------|
| [`godot-gdscript`](skills/godot/godot-gdscript/SKILL.md) | GDScript language: typing, lifecycle, `@export`, signals, idioms |
| [`godot-nodes-scenes`](skills/godot/godot-nodes-scenes/SKILL.md) | Scene tree, node composition, instancing, autoloads, `PackedScene` |
| [`godot-signals-groups`](skills/godot/godot-signals-groups/SKILL.md) | Event-driven design with signals + groups |
| [`godot-2d-movement`](skills/godot/godot-2d-movement/SKILL.md) | `CharacterBody2D` kinematic movement, `move_and_slide`, slopes |
| [`godot-tilemap`](skills/godot/godot-tilemap/SKILL.md) | `TileMapLayer`/`TileSet`: autotiling, terrain, collision/nav layers |
| [`godot-physics`](skills/godot/godot-physics/SKILL.md) | Rigid/Area/Static bodies (2D+3D), collision layers, raycasts |
| [`godot-ui-control`](skills/godot/godot-ui-control/SKILL.md) | `Control` nodes: anchors, containers, themes, focus nav |
| [`godot-animation`](skills/godot/godot-animation/SKILL.md) | `AnimationPlayer`, `AnimationTree`, `Tween` |
| [`godot-shaders`](skills/godot/godot-shaders/SKILL.md) | Godot shading language: 2D `canvas_item` + 3D `spatial` shaders |
| [`godot-3d-essentials`](skills/godot/godot-3d-essentials/SKILL.md) | 3D nodes, cameras, lighting, environment/post, `GridMap` |
| [`godot-resources`](skills/godot/godot-resources/SKILL.md) | Custom `Resource` classes, `.tres`, data-driven design |
| [`godot-audio`](skills/godot/godot-audio/SKILL.md) | `AudioStreamPlayer`, buses, effects, sync-to-beat |
| [`godot-multiplayer`](skills/godot/godot-multiplayer/SKILL.md) | High-level multiplayer: `MultiplayerAPI`, RPCs, spawner/sync |
| [`godot-export`](skills/godot/godot-export/SKILL.md) | Export presets/templates, platform builds, headless CLI export |
| [`godot-csharp`](skills/godot/godot-csharp/SKILL.md) | C#/.NET in Godot: bindings, signals as events, GDScript interop |

#### Unity — 8 ([`skills/unity/`](skills/unity/)) · Unity 6 (6000.0 LTS)

| Skill | Scope |
|-------|-------|
| [`unity-csharp-scripting`](skills/unity/unity-csharp-scripting/SKILL.md) | `MonoBehaviour` lifecycle, component model, coroutines, serialization |
| [`unity-input-system`](skills/unity/unity-input-system/SKILL.md) | New Input System: actions, bindings, action maps, devices |
| [`unity-physics`](skills/unity/unity-physics/SKILL.md) | Rigidbody, colliders, layers, joints |
| [`unity-animation`](skills/unity/unity-animation/SKILL.md) | Animator Controllers, state machines, blend trees, humanoid IK |
| [`unity-scriptableobjects`](skills/unity/unity-scriptableobjects/SKILL.md) | Data architecture with `ScriptableObject` |
| [`unity-tilemap-2d`](skills/unity/unity-tilemap-2d/SKILL.md) | 2D Tilemap/Tile Palette, rule tiles, tilemap colliders |
| [`unity-navmesh`](skills/unity/unity-navmesh/SKILL.md) | AI navigation: NavMesh bake, `NavMeshAgent` |
| [`unity-build-pipeline`](skills/unity/unity-build-pipeline/SKILL.md) | Build/player/quality settings, code stripping, Addressables |

#### Unreal — 6 ([`skills/unreal/`](skills/unreal/)) · Unreal Engine 5.4+

| Skill | Scope |
|-------|-------|
| [`unreal-blueprints`](skills/unreal/unreal-blueprints/SKILL.md) | Blueprint visual scripting: classes, graphs, comms, common nodes |
| [`unreal-cpp-gameplay`](skills/unreal/unreal-cpp-gameplay/SKILL.md) | C++ gameplay + Gameplay Framework (GameMode, Pawn, Controller) |
| [`unreal-enhanced-input`](skills/unreal/unreal-enhanced-input/SKILL.md) | Enhanced Input: Input Actions, Mapping Contexts, Modifiers, Triggers |
| [`unreal-behavior-trees`](skills/unreal/unreal-behavior-trees/SKILL.md) | AI Behavior Trees + Blackboard, tasks/decorators/services |
| [`unreal-niagara`](skills/unreal/unreal-niagara/SKILL.md) | Niagara VFX: systems, emitters, modules, parameters |
| [`unreal-packaging`](skills/unreal/unreal-packaging/SKILL.md) | Packaging/cooking projects, build configs, shipping builds |

#### Web engines — 6 ([`skills/web-engines/`](skills/web-engines/)) · Phaser 3 · PixiJS v8 · three.js r165+

| Skill | Scope |
|-------|-------|
| [`phaser-core`](skills/web-engines/phaser-core/SKILL.md) | Phaser 3 game config, Scene lifecycle, loader, cameras |
| [`phaser-arcade-physics`](skills/web-engines/phaser-arcade-physics/SKILL.md) | Arcade Physics: bodies, velocity, colliders/overlap, groups |
| [`pixijs-rendering`](skills/web-engines/pixijs-rendering/SKILL.md) | PixiJS v8 scene graph: `Application`, `Container`, `Sprite`, events |
| [`threejs-scene-setup`](skills/web-engines/threejs-scene-setup/SKILL.md) | Three.js scene/camera/renderer/animation-loop, resizing, controls |
| [`threejs-gltf-loading`](skills/web-engines/threejs-gltf-loading/SKILL.md) | Loading glTF/GLB + skinned animation (`GLTFLoader`/`AnimationMixer`) |
| [`threejs-materials-lighting`](skills/web-engines/threejs-materials-lighting/SKILL.md) | Materials (PBR), lights, shadows, environment maps |

#### Other engines — 5 ([`skills/other-engines/`](skills/other-engines/)) · Bevy · pygame · LÖVE · Roblox

| Skill | Scope |
|-------|-------|
| [`bevy-ecs`](skills/other-engines/bevy-ecs/SKILL.md) | Bevy app + ECS: components, systems, queries, resources, plugins (Bevy 0.16+) |
| [`pygame-core`](skills/other-engines/pygame-core/SKILL.md) | pygame loop, `Surface`/`Rect`, sprites/groups, events (pygame 2.6) |
| [`love2d-core`](skills/other-engines/love2d-core/SKILL.md) | LÖVE `load/update/draw` loop, dt-driven motion, input, states (LÖVE 11.5) |
| [`roblox-luau`](skills/other-engines/roblox-luau/SKILL.md) | Roblox Luau scripting: services, instances, client/server model |
| [`roblox-datastores`](skills/other-engines/roblox-datastores/SKILL.md) | Persistent data with `DataStoreService`: sessions, limits, ordered stores |

### Disciplines — 9 ([`skills/disciplines/`](skills/disciplines/))

Cross-engine concepts that load alongside the detected engine skill.

| Skill | Scope |
|-------|-------|
| [`game-ai`](skills/disciplines/game-ai/SKILL.md) | NPC decision-making: FSMs, behavior trees, steering, pathfinding |
| [`procedural-gen`](skills/disciplines/procedural-gen/SKILL.md) | Noise, RNG, seeds, grid/dungeon/terrain generation |
| [`dialogue-systems`](skills/disciplines/dialogue-systems/SKILL.md) | Branching dialogue/narrative: nodes, conditions, variables (Yarn/Ink) |
| [`save-systems`](skills/disciplines/save-systems/SKILL.md) | Serialize/restore game state: formats, slots, versioning, autosave |
| [`audio-design`](skills/disciplines/audio-design/SKILL.md) | Buses/mixing, adaptive music, SFX, ducking |
| [`shader-programming`](skills/disciplines/shader-programming/SKILL.md) | Cross-engine shader concepts: vertex/fragment, UVs, common effects |
| [`physics-tuning`](skills/disciplines/physics-tuning/SKILL.md) | Tuning feel: fixed timestep, mass/drag, CCD, stability, layers |
| [`level-design`](skills/disciplines/level-design/SKILL.md) | Whitebox/blockout structure, tile/grid layout, pacing |
| [`input-systems`](skills/disciplines/input-systems/SKILL.md) | Input architecture: action mapping, rebinding, multi-device, buffering |

### Genres — 9 ([`skills/genres/`](skills/genres/))

Compositional templates that orchestrate engine + discipline skills; they never re-teach
primitives.

| Skill | Scope |
|-------|-------|
| [`platformer`](skills/genres/platformer/SKILL.md) | 2D platformer: run/jump/coyote-time, tiled levels, hazards, goals |
| [`roguelike`](skills/genres/roguelike/SKILL.md) | Grid/turn movement, procedural dungeons, permadeath, FOV, loot |
| [`rpg`](skills/genres/rpg/SKILL.md) | Stats/leveling, inventory, quests, dialogue, save/load, combat |
| [`fps-shooter`](skills/genres/fps-shooter/SKILL.md) | First-person controller, camera, shooting/hitscan, enemy AI |
| [`tower-defense`](skills/genres/tower-defense/SKILL.md) | Wave spawning, lane pathing, towers/targeting, economy |
| [`card-game`](skills/genres/card-game/SKILL.md) | Card data, deck/hand/discard zones, play rules, turn structure |
| [`visual-novel`](skills/genres/visual-novel/SKILL.md) | Branching script, character/bg display, text box + choices, backlog |
| [`survival-crafting`](skills/genres/survival-crafting/SKILL.md) | Resource gathering, inventory, crafting, needs, base building |
| [`puzzle`](skills/genres/puzzle/SKILL.md) | Grid/board state, match/rule resolution, undo, level progression |

### Workflows — 4 ([`skills/workflows/`](skills/workflows/))

| Skill | Scope |
|-------|-------|
| [`game-jam`](skills/workflows/game-jam/SKILL.md) | Scope/plan/execute a jam build under time limits; submit |
| [`prototype-fast`](skills/workflows/prototype-fast/SKILL.md) | Greybox a playable vertical slice quickly; cut scope; validate the fun |
| [`steam-publish`](skills/workflows/steam-publish/SKILL.md) | Steamworks onboarding: app/depots, store page, builds, release checklist |
| [`itch-publish`](skills/workflows/itch-publish/SKILL.md) | Publish/update on itch.io: project page, channels, `butler` uploads |

## Agent compatibility

Every skill here is a plain `SKILL.md` folder in the [Agent Skills](https://agentskills.io) open
standard — metadata plus a Markdown playbook the agent reads on demand. The same file loads
**natively** in Claude Code, Claude, Cursor, Windsurf, Cline, OpenAI Codex, Gemini CLI, GitHub
Copilot, Kiro, VS Code, and [many more](https://agentskills.io/clients). There are no
editor-specific rule files to maintain and nothing to convert.

The easiest install is the universal CLI, which detects your agent and writes the skills to its
skills directory:

```bash
npx skills add AbhishekBarali/awesome-gamedev-agent-skills
```

Or drop a skill's `<name>/` folder into your agent's skills directory yourself — commonly
`.claude/skills/`, `.agents/skills/` (the shared path Codex, Gemini, Copilot, and Cursor all read),
`.cursor/skills/`, `.windsurf/skills/`, `.cline/skills/`, or `.kiro/skills/`. The exact per-agent
paths, triggers, and the handful of optional fields that vary by agent are in
[`docs/COMPATIBILITY.md`](docs/COMPATIBILITY.md).

## Demo

<!-- TODO: record a short terminal capture of the router resolving a prompt and replace the
     line below with: ![router demo](docs/assets/router-demo.gif)
     Suggested clip: in a Godot project, prompt "add a double jump to my player" and show the
     router selecting godot-2d-movement + platformer before editing code. Keep it under ~15s. -->

_A short router demo GIF will live here. To record one: open a project an agent can see, ask a
plain-language game-dev question, and capture the router announcing which skills it loads and
why._

## Repository layout

```
skills/        62 specialized skills, grouped by engine / discipline / genre / workflow
router/        the master router skill (+ references/)
docs/          authoring standard, installation, compatibility
templates/     SKILL.md template
scripts/       validate-skills.py and tooling
```

## Contributing

Contributions are welcome. Read [`CONTRIBUTING.md`](CONTRIBUTING.md) and the authoring standard
in [`docs/SKILL-FORMAT.md`](docs/SKILL-FORMAT.md). Every skill must pass the validator and the
rubric before merge:

```bash
python scripts/validate-skills.py
```

## License

[Apache-2.0](LICENSE). See [`NOTICE`](NOTICE) for attribution and trademark notes.
