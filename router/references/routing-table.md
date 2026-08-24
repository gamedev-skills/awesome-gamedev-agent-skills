# Full routing table — every authored skill

The exhaustive `task → category → skill` lookup the router body summarizes. Every name here is
a real folder at `skills/<category>/<name>/SKILL.md`. Trigger words (`says:`) and file signals
(`files:`) are the cues that should select each skill. `*` in a binding is filled with the
**detected** engine (router body §1); where an engine lacks the exact skill, see "Binding gaps".

## Engine skills

### Godot (`skills/godot/`, target Godot 4.7) — read after `project.godot` is detected

| Skill | Pick it when the request says / file signal |
|-------|---------------------------------------------|
| `godot-gdscript` | "GDScript", `_ready`/`_process`, typing, `@export`, `await`; `*.gd` |
| `godot-nodes-scenes` | "scene", "node tree", "instance a scene", autoloads, `PackedScene`; `*.tscn` |
| `godot-signals-groups` | "signal", "emit", "connect", "groups", decoupling/observer |
| `godot-2d-movement` | "2D movement", "platformer controller", `CharacterBody2D`, `move_and_slide` |
| `godot-tilemap` | "tilemap", "tileset", "autotile", `TileMapLayer`; tileset `*.tres` |
| `godot-physics` | "rigidbody", "area2d", "collision layer", "raycast" (2D + 3D) |
| `godot-ui-control` | "UI", "Control node", "anchors", "theme", "HUD" |
| `godot-animation` | `AnimationPlayer`, `AnimationTree`, "blend", `Tween` |
| `godot-shaders` | "Godot shader", "gdshader", fragment/vertex, screen-reading; `*.gdshader` |
| `godot-3d-essentials` | "3D", `Camera3D`, `WorldEnvironment`, `GridMap`; `Node3D` |
| `godot-resources` | "custom Resource", "data resource", `.tres`, `ResourceLoader` |
| `godot-audio` | "Godot audio", "audio bus", "play sound/music", sync-to-beat |
| `godot-multiplayer` | "multiplayer", "RPC", "networked", `MultiplayerSpawner`; `@rpc` |
| `godot-export` | "export Godot", "build for web/windows", `export_presets.cfg` |
| `godot-csharp` | "Godot C#", "GodotSharp", "C# signals in Godot"; `*.cs` + `*.csproj` in a Godot project |

### Unity (`skills/unity/`, target Unity 6.3 LTS / 6000.3)

| Skill | Pick it when |
|-------|--------------|
| `unity-csharp-scripting` | "Unity script", `MonoBehaviour`, `Start`/`Update`, coroutines; `*.cs` + `*.asmdef` |
| `unity-input-system` | "Input System", `InputAction`, "action map"; `*.inputactions` |
| `unity-physics` | "Unity physics", `Rigidbody`, "collision layers", "joint" |
| `unity-animation` | "Animator", "state machine", "blend tree", "Mecanim"; `*.controller` |
| `unity-scriptableobjects` | `ScriptableObject`, "SO architecture", "data asset", event channels |
| `unity-tilemap-2d` | "Unity tilemap", "tile palette", "rule tile" |
| `unity-navmesh` | `NavMesh`, `NavMeshAgent`, "pathfinding in Unity" |
| `unity-build-pipeline` | "build Unity", "player settings", "IL2CPP", "Addressables" |

### Unreal (`skills/unreal/`, target UE 5.8)

| Skill | Pick it when |
|-------|--------------|
| `unreal-blueprints` | "Blueprint", "BP graph", "event graph"; Blueprint `*.uasset` |
| `unreal-cpp-gameplay` | "Unreal C++", `GameMode`, `Pawn`, `ACharacter`; `Source/**/*.cpp` + `*.Build.cs` |
| `unreal-enhanced-input` | "Enhanced Input", "Input Mapping Context", `IA_`/`IMC_` |
| `unreal-behavior-trees` | "Behavior Tree", "Blackboard", `AIController`, `BTTask`; `BT_`/`BB_` |
| `unreal-niagara` | "Niagara", "VFX", "particle system"; `NS_`/`NE_` |
| `unreal-packaging` | "package Unreal", "cook content", "shipping build" |

### Web engines (`skills/web-engines/`) — detected from `package.json` + imports

| Skill | Pick it when |
|-------|--------------|
| `phaser-core` | "Phaser", "Phaser scene", `preload`/`create`/`update`; dep `phaser` |
| `phaser-arcade-physics` | "Arcade Physics", "collider", "overlap", world bounds |
| `pixijs-rendering` | "PixiJS", "Pixi sprite", "stage", `Container`; dep `pixi.js` |
| `threejs-scene-setup` | "three.js", `THREE.Scene`, `WebGLRenderer`, render loop; dep `three` |
| `threejs-gltf-loading` | "load gltf", `GLTFLoader`, `AnimationMixer`; `*.gltf`/`*.glb` |
| `threejs-materials-lighting` | `MeshStandardMaterial`, "lighting", "shadows", env maps |

### Other engines (`skills/other-engines/`)

| Skill | Pick it when |
|-------|--------------|
| `bevy-ecs` | "Bevy", "ECS system/query", `Commands`, "Bevy plugin"; `Cargo.toml` dep `bevy` |
| `pygame-core` | "pygame", "blit", "sprite group", game loop; `import pygame` |
| `love2d-core` | "LÖVE", "love2d", `love.draw`, `love.update(dt)`; `main.lua`/`conf.lua`/`*.love` |
| `roblox-luau` | "Roblox", "Luau", `RemoteEvent`, services; `*.luau` + `*.rbxl(x)` / Rojo |
| `roblox-datastores` | "DataStore", "save player data", `GetDataStore`; `DataStoreService` |

## Disciplines (`skills/disciplines/`) — cross-engine concepts, load **with** the engine skill

| Concept skill | `says:` triggers | Pairs with (engine API skill) |
|---------------|------------------|-------------------------------|
| `create-game-assets` | art direction, game assets, sprite/sprite sheet, tileset, texture, icon, concept art, 3D prop, consistent style | engine importer/rendering skill; installed `imagegen` for raster generation when available |
| `game-ai` | enemy AI, behavior tree, state machine, steering, pathfinding | `unity-navmesh` / `unreal-behavior-trees` / Godot nav (`godot-nodes-scenes` + `godot-physics`) |
| `ai-behavior-trees-utility-ai` | behavior tree runtime, blackboard, action/condition node, selector/sequence/parallel, decorator, utility AI, scoring/response curve, consideration, hybrid AI | `game-ai` (FSM/BT/steering choice) / `unreal-behavior-trees` (engine BT/Blackboard assets) |
| `procedural-gen` | procedural generation, perlin/simplex noise, random seed, dungeon generator | engine tilemap/grid: `godot-tilemap` / `unity-tilemap-2d` / `godot-3d-essentials` |
| `dialogue-systems` | dialogue system, branching dialogue, Yarn Spinner, Ink, conversation tree; `*.yarn`/`*.ink` | engine UI: `godot-ui-control` / Unity UI |
| `save-systems` | save system, save/load, persistence, save slots; `save*.json`/`*.sav` | `roblox-datastores` / Godot IO / engine serialization |
| `audio-design` | audio design, adaptive music, audio mixer, ducking, SFX | `godot-audio` / Unity AudioMixer |
| `shader-programming` | shader, fragment shader, dissolve/outline effect, GLSL/HLSL; `*.gdshader`/`*.shader`/`*.hlsl` | `godot-shaders` / engine material docs |
| `physics-tuning` | physics feel, jitter/tunneling, fixed timestep, collision tuning | `godot-physics` / `unity-physics` |
| `level-design` | level design, whitebox/blockout, tilemap layout, pacing | `godot-tilemap` / `unity-tilemap-2d` / `godot-3d-essentials` (GridMap) |
| `input-systems` | input mapping, rebind controls, gamepad support, input buffering; `*.inputactions`/IMC | `unity-input-system` / `unreal-enhanced-input` / Godot InputMap |
| `game-feel` | game feel, juice, screen shake, hit-stop/freeze frame, squash & stretch, knockback, "make it punchy/satisfying" | engine animation/tween (`godot-animation`/`unity-animation`) + `camera-systems` (shake) + `audio-design` |
| `camera-systems` | camera follow, follow camera, deadzone, look-ahead, camera bounds/limits, third-person/orbit camera, first-person look, Cinemachine, camera jitter | `godot-2d-movement`/`godot-3d-essentials` / Unity Cinemachine 3 / Godot `Camera2D`/`Camera3D` |
| `game-ui-ux` | HUD, health bar, main/pause/settings menu, UI layout, anchors, UI scaling, aspect ratio, safe area, controller/keyboard menu nav | `godot-ui-control` / Unity UI (UGUI/UI Toolkit) |
| `performance-optimization` | performance, optimize, low/dropping FPS, frame drops, stutter, lag, frame budget, draw calls, batching, GC spikes, object pooling, profiler | engine profiler (Godot Monitors / Unity Profiler / Unreal `stat unit`) + `physics-tuning` |

## Genres (`skills/genres/`) — whole-game templates, **compose** engine + disciplines

| Genre skill | `says:` triggers | composes (bind `*` to the detected engine) |
|-------------|------------------|---------------------------------------------|
| `platformer` | platformer, jump mechanic, double jump, Mario-like | `godot-2d-movement` (or engine physics) + `godot-tilemap`/`unity-tilemap-2d` + `level-design` + `camera-systems` + `game-feel` |
| `roguelike` | roguelike, procedural dungeon, permadeath, turn-based grid | `procedural-gen` + `godot-tilemap`/`unity-tilemap-2d` + `game-ai` + `save-systems` + `game-feel` |
| `rpg` | RPG, stats/leveling, inventory, quest system | `godot-resources`/`unity-scriptableobjects` + `dialogue-systems` + `save-systems` + `game-ui-ux` |
| `fps-shooter` | FPS, first-person shooter, hitscan, aim/shoot | `godot-3d-essentials`/`unreal-cpp-gameplay` + `input-systems` + `game-ai` + `camera-systems` + `game-feel` |
| `tower-defense` | tower defense, wave spawner, enemy path, tower targeting | `game-ai` + `godot-2d-movement`/engine movement + `level-design` + `game-ui-ux` |
| `card-game` | card game, deckbuilder, hand/deck/discard, TCG | `godot-resources`/`unity-scriptableobjects` + `game-ui-ux` + `godot-ui-control` (engine UI) |
| `visual-novel` | visual novel, VN, branching story, choice menu; `*.ink`/`*.yarn` | `dialogue-systems` + `save-systems` + `game-ui-ux` |
| `survival-crafting` | survival game, crafting system, inventory, resource gathering | `save-systems` + `godot-resources`/`unity-scriptableobjects` + `procedural-gen` + `game-ui-ux` |
| `puzzle` | puzzle game, match-3, grid logic, tile-matching | `godot-tilemap`/`unity-tilemap-2d` + `level-design` + `game-feel` |

## Workflows (`skills/workflows/`) — process & shipping, engine-independent

| Workflow skill | `says:` / `files:` triggers |
|----------------|------------------------------|
| `game-jam` | game jam, 48-hour game, Ludum Dare / GMTK, jam submission |
| `prototype-fast` | prototype fast, vertical slice, MVP game, greybox |
| `steam-publish` | publish on Steam, Steamworks, store page, depot/build upload; `steam_appid.txt` |
| `itch-publish` | publish on itch, itch.io page, `butler push`, upload build; `.itch.toml` |

## Binding gaps (be honest; do not fabricate a skill)

The collection does not yet have a skill for every engine × concept. Several cross-cutting
concerns are now covered **engine-neutrally** by disciplines that pair with any detected engine —
camera work (`camera-systems`), HUD/menus (`game-ui-ux`), juice/feedback (`game-feel`), and
performance (`performance-optimization`) — so those are no longer gaps; bind them on top of the
engine. The remaining true gaps are engine-specific primitives. When a genre binding names a slot
the detected engine lacks, load the closest skill(s) and **state the gap** plainly:

- **No `*-2d-movement` for Unity / Unreal / web.** For a Unity platformer, bind movement to
  `unity-csharp-scripting` + `unity-physics`; for Phaser, `phaser-arcade-physics`. Say there is
  no dedicated `unity-2d-movement` skill.
- **No dedicated 3D-essentials for Unity.** For a Unity FPS, use `unity-csharp-scripting` +
  `unity-physics` + `unity-navmesh`; only Godot has `godot-3d-essentials` and Unreal has
  `unreal-cpp-gameplay`.
- **No `*-tilemap` for web / Bevy / pygame / Roblox / LÖVE.** Use `level-design` for the concept
  and the engine's rendering skill for drawing; note the missing engine tilemap skill.
- **No engine-specific save skill except Roblox.** `save-systems` owns the concept and cites
  Godot IO; `roblox-datastores` is the one engine-specific persistence skill.
