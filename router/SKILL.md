---
name: router
description: >
  Routes any game-development request to the right specialized skill(s): it detects the engine
  (Godot, Unity, Unreal, Bevy, Phaser, PixiJS, three.js, LÖVE, pygame, Roblox) and the task, then
  reads the chosen skill before acting. Use to make a game or to decide which skill applies — for
  players, levels, enemies, shaders, art direction, sprites, tiles, textures, 3D assets, UI/UX,
  cameras, game feel, physics, input, audio, saving, multiplayer, AI, dialogue, procedural
  generation, or performance, for genres (platformer,
  roguelike, RPG, FPS, tower-defense, card game, visual novel, survival-crafting, puzzle), and for
  shipping (game jam, Steam, itch). Start here
  when unsure which gamedev skill to use.
---

# Master Router — Game-Development Skill Dispatcher

The entry point for game-development work. It fingerprints the project to pick **one** engine,
classifies the task from the request, names the **minimal** set of specialized skills, and tells
you to read them before acting. It **dispatches and composes** — it does not re-teach engine APIs.

## When to use

- Use at the **start of any game-development request** — building or debugging a game, level,
  player, enemy, shader, UI, save system, multiplayer, input, audio, AI, dialogue, procedural
  content, or visual asset set — to decide which skill(s) to load.
- Use when the user names an engine or genre, says "make a game", or asks "which skill should I
  use?".

**When *not* to use:** once the right skill is loaded and the task is squarely inside it, work
from that skill — don't re-run the router every turn. Re-route only when the task **pivots** to a
new engine or concern (router step 6).

## Routing algorithm

1. **Detect engine and version** — project fingerprint → at most one engine skill set (or
   "unknown"), then read the project's version source. §1.
2. **Classify task** — phrasing → discipline(s) + at most one genre + workflow(s). §2.
3. **Resolve** — the minimal set: engine skill(s) + discipline(s) + genre + workflow(s). §3.
4. **Read (disclosure)** — open only the chosen `SKILL.md` bodies; `references/` only on demand. §4.
5. **Compose** — order: engine fundamentals → discipline concept → genre glue → workflow. §5.
6. **Fallback** — engine unknown or no skill fits → ask or default to Godot; state any gap. §6.

---

## 1. Engine detection (project fingerprint)

Scan for the highest-confidence signal; **choose exactly one** engine. Stop at the first match.

| # | Engine | Primary signal | Skill set root |
|:-:|--------|----------------|----------------|
| 1 | Godot | `project.godot` | `skills/godot/` |
| 2 | Unreal | `*.uproject` | `skills/unreal/` |
| 3 | Unity | `Assets/` **and** `ProjectSettings/ProjectVersion.txt` | `skills/unity/` |
| 4 | Bevy | `Cargo.toml` with a `bevy` dependency | `skills/other-engines/bevy-ecs/` |
| 5 | Phaser | `package.json` dep `phaser` | `skills/web-engines/phaser-*` |
| 6 | PixiJS | `package.json` dep `pixi.js` | `skills/web-engines/pixijs-rendering/` |
| 7 | three.js | `package.json` dep `three` | `skills/web-engines/threejs-*` |
| 8 | LÖVE | `conf.lua` / `main.lua` calling `love.*` | `skills/other-engines/love2d-core/` |
| 9 | pygame | `*.py` with `import pygame` | `skills/other-engines/pygame-core/` |
| 10 | Roblox | `*.rbxl(x)` / `*.project.json` (Rojo) | `skills/other-engines/roblox-*` |

For secondary signals, the Godot-C#/Unity/Bevy and multi-web disambiguation rules, monorepos,
and plain-text engine mentions, read `references/engine-detection.md`.

After identifying the engine, read its version from project metadata or dependency locks before
choosing APIs. Existing projects keep their pinned version unless migration is requested; the
catalog baseline is only for new projects. The exact version sources are in the detection reference
and `../docs/VERSION-SUPPORT.md`.

## 2. Task classification (phrasing → category)

After the engine, read the request for task signals (three **additive** categories):

- **disciplines** (cross-engine concepts): `create-game-assets`, `game-ai`, `ai-behavior-trees-utility-ai`, `procedural-gen`, `dialogue-systems`,
  `save-systems`, `audio-design`, `shader-programming`, `physics-tuning`, `level-design`,
  `input-systems`, `game-feel`, `camera-systems`, `game-ui-ux`, `performance-optimization`.
  Triggered by concept words ("sprite sheet", "art direction", "texture", "pathfinding",
  "save slots", "fragment shader", "screen shake", "camera follow", "HUD/menu",
  "optimize/low FPS").
- **genres** (whole-game templates): `platformer`, `roguelike`, `rpg`, `fps-shooter`,
  `tower-defense`, `card-game`, `visual-novel`, `survival-crafting`, `puzzle`. Triggered by genre
  words ("make a roguelike", "deckbuilder").
- **workflows** (process/shipping): `game-jam`, `prototype-fast`, `steam-publish`,
  `itch-publish`. Triggered by process words ("publish on Steam", "vertical slice").

File signals sharpen this: `*.yarn`/`*.ink` → `dialogue-systems`/`visual-novel`; `steam_appid.txt`
→ `steam-publish`; `*.inputactions` → `unity-input-system`.

## 3. Routing table (task → category → skill)

### 3a. Engine skills — read the one matching the detected engine + sub-task

- **Godot** (`skills/godot/`): language `godot-gdscript` / `godot-csharp`; structure
  `godot-nodes-scenes`, `godot-signals-groups`; 2D `godot-2d-movement`, `godot-tilemap`; 3D
  `godot-3d-essentials`; physics `godot-physics`; UI `godot-ui-control`; animation
  `godot-animation`; shaders `godot-shaders`; data `godot-resources`; audio `godot-audio`;
  netcode `godot-multiplayer`; ship `godot-export`.
- **Unity** (`skills/unity/`): scripting `unity-csharp-scripting`; input `unity-input-system`;
  physics `unity-physics`; animation `unity-animation`; data `unity-scriptableobjects`; 2D
  `unity-tilemap-2d`; AI nav `unity-navmesh`; ship `unity-build-pipeline`.
- **Unreal** (`skills/unreal/`): visual scripting `unreal-blueprints`; C++ gameplay
  `unreal-cpp-gameplay`; input `unreal-enhanced-input`; AI `unreal-behavior-trees`; VFX
  `unreal-niagara`; ship `unreal-packaging`.
- **Web** (`skills/web-engines/`): `phaser-core`, `phaser-arcade-physics`; `pixijs-rendering`;
  `threejs-scene-setup`, `threejs-gltf-loading`, `threejs-materials-lighting`.
- **Other** (`skills/other-engines/`): `bevy-ecs`, `pygame-core`, `love2d-core`, `roblox-luau`,
  `roblox-datastores`.

### 3b. Disciplines — load **with** the engine skill (concept ↔ engine API)

| Concept (`says:`) | Discipline skill | Pairs with (engine API) |
|-------------------|------------------|-------------------------|
| art direction, game assets, sprites, tilesets, textures, icons, 3D props | `create-game-assets` | engine importer/rendering skill; `imagegen` when available |
| enemy AI, behavior tree, pathfinding, steering | `game-ai` | `unity-navmesh` / `unreal-behavior-trees` / Godot nav |
| BT runtime, blackboard, decorator, selector/sequence, utility AI, response curve, consideration | `ai-behavior-trees-utility-ai` | `game-ai` (model choice) / `unreal-behavior-trees` (engine assets) |
| procedural, noise, seed, dungeon generator | `procedural-gen` | engine tilemap/grid skill |
| dialogue, Yarn, Ink, conversation tree | `dialogue-systems` | engine UI skill |
| save/load, slots, persistence | `save-systems` | `roblox-datastores` / engine IO |
| adaptive music, mixer, ducking, SFX | `audio-design` | `godot-audio` / Unity AudioMixer |
| shader, fragment, dissolve/outline | `shader-programming` | `godot-shaders` / engine material |
| jitter, tunneling, fixed timestep | `physics-tuning` | `godot-physics` / `unity-physics` |
| whitebox, blockout, tile layout, pacing | `level-design` | `godot-tilemap` / `unity-tilemap-2d` |
| rebind, gamepad, input buffering | `input-systems` | `unity-input-system` / `unreal-enhanced-input` / Godot InputMap |
| screen shake, hit-stop, juice, squash & stretch, "make it punchy" | `game-feel` | engine animation/tween + `camera-systems` (shake) |
| camera follow, deadzone, look-ahead, orbit, first-person | `camera-systems` | `godot-2d-movement` / `godot-3d-essentials` / Cinemachine |
| HUD, menu, UI layout, scaling, safe area, focus nav | `game-ui-ux` | `godot-ui-control` / Unity UI (UGUI/UI Toolkit) |
| low FPS, optimize, draw calls, GC spike, pooling, profiler | `performance-optimization` | engine profiler + `physics-tuning` |

### 3c. Genres — **compose** engine + disciplines (bind `*` to the detected engine)

| Genre (`says:`) | composes |
|-----------------|----------|
| platformer, jump, double jump | `godot-2d-movement` (or engine physics) + `godot-tilemap`/`unity-tilemap-2d` + `level-design` + `camera-systems` + `game-feel` |
| roguelike, procedural dungeon, permadeath | `procedural-gen` + `godot-tilemap`/`unity-tilemap-2d` + `game-ai` + `save-systems` + `game-feel` |
| RPG, stats, inventory, quests | `godot-resources`/`unity-scriptableobjects` + `dialogue-systems` + `save-systems` + `game-ui-ux` |
| FPS, first-person, hitscan | `godot-3d-essentials`/`unreal-cpp-gameplay` + `input-systems` + `game-ai` + `camera-systems` + `game-feel` |
| tower defense, waves, lanes | `game-ai` + engine movement + `level-design` + `game-ui-ux` |
| card game, deckbuilder, TCG | `godot-resources`/`unity-scriptableobjects` + `game-ui-ux` (+ engine UI) |
| visual novel, branching story | `dialogue-systems` + `save-systems` + `game-ui-ux` |
| survival, crafting, gathering | `save-systems` + `godot-resources`/`unity-scriptableobjects` + `procedural-gen` + `game-ui-ux` |
| puzzle, match-3, grid logic | `godot-tilemap`/`unity-tilemap-2d` + `level-design` + `game-feel` |

### 3d. Workflows — engine-independent process & shipping

`game-jam` (jam, 48-hour, Ludum Dare/GMTK) · `prototype-fast` (vertical slice, MVP, greybox) ·
`steam-publish` (Steam, Steamworks, depot; `steam_appid.txt`) · `itch-publish` (itch.io, butler;
`.itch.toml`).

For the exhaustive per-skill trigger list and every engine binding, read
`references/routing-table.md`.

## 4. Read protocol (progressive disclosure)

1. **Preloaded:** only each skill's `name` + `description` are in context. Decide from those plus
   the fingerprint — do **not** pre-read bodies.
2. **On selection:** read the body of **each chosen** `skills/<category>/<name>/SKILL.md` — and
   only those. Never bulk-load a whole category.
3. **On demand:** read a skill's bundled `references/` files only when the subtask needs that
   depth (the skill body says when).
4. **Re-route on pivot:** if the task changes (movement → saving), select and read the newly
   relevant skill instead of keeping everything loaded.

Announce what you load and why, e.g.: *"Detected Godot (`project.godot`). Loading
`godot-2d-movement` for the controller and `platformer` for jump feel; will open the platformer
skill's `feel-tuning.md` reference if you want coyote-time/buffering."*

## 5. Composition rules

- **One engine set, additive concepts.** Exactly one engine skill set; add the disciplines the
  task needs and usually **at most one** genre. Workflows attach independently.
- **Order:** engine fundamentals → discipline concept → genre orchestration → workflow. For asset
  production, approve the visual target before generating a family, then finish with the engine
  import settings and an in-context capture.
- **Ownership on overlap:** the **engine** skill owns API/syntax; the **discipline** skill owns
  the portable concept/algorithm and defers to the engine skill for code; the **genre** skill owns
  structure/glue and links out instead of re-teaching a primitive.
- **Hand-offs:** when a genre's `composes` names a slot like `*-2d-movement`, bind it to the
  detected engine. If that engine lacks the exact skill, see §6 and `references/routing-table.md`
  ("Binding gaps").

## 6. Unknown-engine & no-skill fallback

**Engine unknown** (no fingerprint, no engine named):

1. Check the request for a plain-text engine name ("in Unity", "using Phaser"). If found, adopt it.
2. If the task is a pure concept/genre/workflow question, route straight to the engine-agnostic
   discipline/genre/workflow skill — no engine needed ("what's a good save format?" → `save-systems`).
3. Only if engine choice actually blocks the answer, ask **one** targeted question ("Which engine —
   Godot, Unity, Unreal, or a web/other engine?"). If the user has no preference and one is needed,
   **default to Godot** (the most fully covered engine here) and say so.
4. Never invent an engine or load an engine skill on a guess.

**Engine known but no skill covers the subtask:** load the closest engine skill plus the relevant
discipline and **state the gap** plainly (e.g. "no dedicated Unity 2D-movement skill; using
`unity-csharp-scripting` + `unity-physics`"). Never fabricate a skill name.

**Conflicting/multiple genres:** pick the dominant genre from the phrasing; mention the secondary
and offer to load it if the user confirms.

## Worked examples

| Request | Detected engine | Skills loaded (in order) |
|---------|-----------------|--------------------------|
| "add a double jump to my Godot player" | Godot (`project.godot`) | `godot-2d-movement` → `platformer` |
| "make an inventory for my Unity RPG" | Unity (`Assets/`+`ProjectSettings/`) | `unity-scriptableobjects` → `rpg` → `save-systems` |
| "procedural dungeon roguelike in Godot" | Godot | `godot-tilemap` → `procedural-gen` → `roguelike` |
| "branching dialogue from a `.yarn` file" | (none required) | `dialogue-systems` (+ engine UI skill if an engine is detected) |
| "how do I design save slots with migration?" | (none) | `save-systems` only |
| "publish my game on itch with butler" | (any/none) | `itch-publish` only |
| "I want to make a game but don't know what to use" | unknown → ask, default Godot | router asks once; then e.g. `godot-nodes-scenes` |
| "make hits feel punchy in my Godot game" | Godot (`project.godot`) | `game-feel` (+ `camera-systems` for shake) |
| "the camera should follow my player smoothly" | (detected engine) | `camera-systems` (+ engine movement skill) |
| "my Unity game drops to 30 FPS, optimize it" | Unity (`Assets/`+`ProjectSettings/`) | `performance-optimization` (profile first) → engine skill |
| "make a cohesive pixel-art player and enemy set" | (detected engine) | `create-game-assets` → relevant engine import/rendering skill |

## References

- Full engine fingerprints, secondary signals, and disambiguation: `references/engine-detection.md`.
- Exhaustive per-skill trigger words, engine bindings, and binding gaps: `references/routing-table.md`.
