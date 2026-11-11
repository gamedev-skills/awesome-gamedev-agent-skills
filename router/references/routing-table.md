# Full routing table — every authored skill

## Contents

- [Engine skills](#engine-skills): [Godot](#godot-skillsgodot-target-godot-47--read-after-projectgodot-is-detected) ·
  [Unity](#unity-skillsunity-target-unity-63-lts--60003) ·
  [Unreal](#unreal-skillsunreal-target-ue-58) ·
  [Ebitengine](#ebitengine-skillsebitengine-target-v2106--go-125) ·
  [Web engines](#web-engines-skillsweb-engines--detected-from-packagejson--imports) ·
  [Other engines](#other-engines-skillsother-engines)
- [Disciplines](#disciplines-skillsdisciplines--cross-engine-concepts-load-with-the-engine-skill)
- [Genres](#genres-skillsgenres--whole-game-templates-load-with-the-engine-skill)
- [Workflows](#workflows-skillsworkflows--process--shipping-engine-independent)
- [Keyword traps with no owner](#keyword-traps-with-no-owner)
- [Binding gaps](#binding-gaps-be-honest-do-not-fabricate-a-skill)

The exhaustive `task → category → skill` lookup the router body summarizes. Every name here is
a real folder at `skills/<category>/<name>/SKILL.md`. Trigger words (`says:`) and file signals
(`files:`) are the cues that should select each skill. `*` in a binding is filled with the
**detected** engine (router body §1); where an engine lacks the exact skill, see "Binding gaps".
When two skills both match, the router's ownership table (§3c) decides who leads.

## Engine skills

### Godot (`skills/godot/`, target Godot 4.7) — read after `project.godot` is detected

| Skill | Pick it when the request says / file signal |
|-------|---------------------------------------------|
| `godot-gdscript` | "GDScript", static typing, "Cannot infer the type", `@export`/`@onready`, `await`, porting 3.x code; `*.gd` |
| `godot-nodes-scenes` | "scene", "instance a scene", spawning bullets/enemies, autoloads, "Node not found", "previously freed instance", broken `res://` paths or uids; `*.tscn` |
| `godot-signals-groups` | "signal", "emit", "connect", "already connected", handler fires twice, groups, `call_group`, event bus, porting `connect("sig", self, "method")` |
| `godot-2d-movement` | "2D movement", `CharacterBody2D`, `move_and_slide`, top-down 8-direction, slopes, one-way platforms, `is_on_floor()` always false |
| `godot-tilemap` | "tilemap", "tileset", terrain autotiling, `TileMapLayer`, "TileSet in code", `tile_map_data`, `set_cell`/`local_to_map`, porting `TileMap`; tileset `*.tres` |
| `godot-physics` | "RigidBody", "Area2D", `body_entered` never fires, "collision layer/mask", "raycast hits itself", Jolt (2D + 3D) |
| `godot-ui-control` | Godot UI, "Control node", anchors, Containers, Theme/StyleBox, focus neighbours, panel swallows clicks (load `game-ui-ux` too) |
| `godot-animation` | `AnimationPlayer`, `AnimationTree`, `travel()` does nothing, `AnimatedSprite2D`, `Tween`, "Animation not found" |
| `godot-shaders` | "Godot shader", "gdshader", `SHADER ERROR`, "headless shader compile", ShaderMaterial uniforms from GDScript; `*.gdshader` |
| `godot-3d-essentials` | "3D", `Camera3D`, `WorldEnvironment`, scene renders black or washed out, invisible mesh, `GridMap`; `Node3D` |
| `godot-resources` | "custom Resource", items/stats as data, `.tres`, editing one enemy changes all (`duplicate_deep()`), `ResourceLoader` |
| `godot-audio` | Godot audio, `AudioStreamPlayer`, audio bus, volume slider in Godot, sound silent/cut off/not looping |
| `godot-multiplayer` | "multiplayer", ENet host/join, `@rpc`, `rpc_id()`, `MultiplayerSpawner`/`MultiplayerSynchronizer`, state not syncing |
| `godot-export` | "export Godot", export presets, "No export template found", blank web build, `SharedArrayBuffer`, export in CI; `export_presets.cfg` |
| `godot-csharp` | "Godot C#", "GodotSharp", `[Export]`/`[Signal]`, porting GDScript to C#; `*.cs` + `*.csproj` in a Godot project |
| `godot-gdscript-headless-testing` | "headless test", Godot tests in CI, GitHub Actions for `.gd` tests, `godot --headless --script`, run exits 0 despite `SCRIPT ERROR` |

### Unity (`skills/unity/`, target Unity 6.3 LTS / 6000.3)

| Skill | Pick it when |
|-------|--------------|
| `unity-csharp-scripting` | "Unity script", `MonoBehaviour`, lifecycle, "Missing script", field missing from Inspector, `.meta`/GUID, command-line compile and tests; `*.cs` + `*.asmdef` |
| `unity-input-system` | "Input System", `.inputactions`, action map, `PlayerInput`, `FindAction` returns null, porting `Input.GetAxis` |
| `unity-physics` | "Unity physics", `Rigidbody`, `Rigidbody2D`, `Physics2D`, "2D physics", `OnTriggerEnter`/`OnTriggerEnter2D` never fires, `linearVelocity`, layer collision matrix, raycasts, joints |
| `unity-animation` | "Animator", "Mecanim", transitions, blend tree, Avatar Mask, root motion, humanoid IK; `*.controller` |
| `unity-scriptableobjects` | `ScriptableObject`, `CreateAssetMenu`, event channels, replacing singletons, values persist after Play mode |
| `unity-tilemap-2d` | "Unity tilemap", Tile Palette, Rule Tile, `SetTile`, Tilemap Collider 2D seams, hex/isometric grid |
| `unity-navmesh` | `NavMeshSurface`, `NavMeshAgent`, `NavMeshLink`, "pathfinding in Unity", agent won't move, Bake tab missing |
| `unity-build-pipeline` | "build Unity", Build Profiles, player settings, IL2CPP vs Mono, code stripping, `BuildPipeline.BuildPlayer`, CI/headless builds, Addressables |
| `unity-build-size` | "build too big", "reduce build size", "size limit", APK/AAB/IPA or WebGL build too large, itch/Steam download size, huge `sharedassets*.assets.resS`, glTF/GLB textures in a build |

### Unreal (`skills/unreal/`, target UE 5.8)

| Skill | Pick it when |
|-------|--------------|
| `unreal-blueprints` | "Blueprint", Event Graph, Cast, Interfaces, Event Dispatchers, "cast failed", slow Event Tick, Blueprint compile errors |
| `unreal-cpp-gameplay` | "Unreal C++", `UCLASS`/`UPROPERTY`, `GENERATED_BODY`, Live Coding, "unresolved external symbol", UHT errors; `Source/**/*.cpp` + `*.Build.cs` |
| `unreal-enhanced-input` | "Enhanced Input", Input Mapping Context, `ETriggerEvent`, rebind menu, input stops after respawn; `IA_`/`IMC_` |
| `unreal-behavior-trees` | UE Behavior Tree, Blackboard, Observer Aborts, `BTTask`, EQS, StateTree, `UStateTreeAIComponent`, "my AI just stands there", "MoveTo fails"; `BT_`/`BB_`/`EQS_`/`ST_` |
| `unreal-niagara` | "Niagara", Unreal particles, muzzle flash, User parameters, effect vanishes at screen edge (bounds); `NS_`/`NE_` |
| `unreal-packaging` | "package Unreal", Shipping build, cook, pak/IoStore, `RunUAT BuildCookRun`, "black screen in packaged build", "BUILD FAILED", map missing in build |

### Ebitengine (`skills/ebitengine/`, target v2.10.6 / Go 1.25+)

| Skill | Pick it when |
|-------|--------------|
| `ebitengine-game` | "Ebitengine", "Ebiten", "2D game in Go", `Update`/`Draw`/`Layout`, blurry pixel art, missed key presses, stutter after a long frame, text, audio, WASM or mobile builds; `go.mod` requiring `github.com/hajimehoshi/ebiten/v2` plus game imports |

### Web engines (`skills/web-engines/`) — detected from `package.json` + imports

| Skill | Pick it when |
|-------|--------------|
| `phaser-core` | "Phaser", Game config, Scene lifecycle, loader, assets undefined in `create`, black screen, HUD scene behind the game, Phaser 3 → 4 migration; dep `phaser` |
| `phaser-arcade-physics` | "Arcade Physics", collider vs overlap, `onFloor()` always false, bullet pools, Phaser platformer or top-down controller |
| `pixijs-rendering` | PixiJS **game or playable ad**, async `Application.init`, `Assets`, blank canvas, clicks not firing, drag stops at the sprite edge, v7 → v8 migration; dep `pixi.js`. Not for dashboards or charts. |
| `threejs-scene-setup` | plain three.js, import maps, "Failed to resolve module specifier three", black canvas, `setAnimationLoop`, `OrbitControls`, `WebGPURenderer`, DOM overlay; dep `three` |
| `threejs-gltf-loading` | `GLTFLoader`, DRACO/Meshopt/KTX2 decoder 404, model invisible or tiny, `AnimationMixer`, cloned skeletons, `gltf-transform optimize`; `*.gltf`/`*.glb` |
| `threejs-materials-lighting` | `MeshStandardMaterial`, lights, shadows or shadow acne, HDR environment, tone mapping, EffectComposer darkens the image, context loss |

### Other engines (`skills/other-engines/`)

| Skill | Pick it when |
|-------|--------------|
| `bevy-ecs` | "Bevy", ECS components/systems/`Query`/`Commands`, schedules, States, observers, B0001 query conflict, pre-0.20 code (`EventReader`, `SpriteBundle`); `Cargo.toml` dep `bevy` |
| `pygame-core` | "pygame", pygame-ce, event-update-draw loop, delta time, Sprite groups, "not responding" window, pygame vs pygame-ce conflict; `import pygame` |
| `love2d-core` | "LÖVE", "love2d", `love.update(dt)`, `conf.lua`, blue error screen, blurry pixel art, speed tied to frame rate; `main.lua`/`conf.lua`/`*.love` |
| `defold-core` | "Defold", collection/game object, `msg.post`, `on_input` never fires, `acquire_input_focus`, `factory.create`, collection proxy never loads, "could not be found when dispatching message", `bob.jar`; `game.project` + `*.collection`/`*.go`/`*.script` (target Defold 1.14.1) |
| `roblox-luau` | "Roblox", "Luau", services, Script vs LocalScript vs ModuleScript, LocalScript does not run, `task` library, replacing `wait()`, typed Luau, selene/luau-lsp; `*.luau` + `*.rbxl(x)` / Rojo |
| `roblox-datastores` | "DataStore", lost player data, `UpdateAsync` vs `SetAsync`, session locking, items duplicate after teleport, "too many requests", `OrderedDataStore` leaderboard |
| `roblox-ui` | Roblox HUD/shop/settings menu, `ScreenGui`, `PlayerGui`, `ResetOnSpawn`, `UDim2`, UI clips on phones, StyleSheet, gamepad selection, touch controls (load `game-ui-ux` too) |
| `roblox-networking` | Roblox remotes, replication, server authority, hit validation, hitreg, `RemoteEvent`/`RemoteFunction`/`UnreliableRemoteEvent`, exploiters spam remotes or gain items, rate limits |
| `roblox-characters` | Roblox character, `CharacterAdded`, respawn breaks a script, `Humanoid`, R6/R15, `Animator`, animations not replicating, Tools, sprint fights the Humanoid |
| `roblox-physics` | Roblox assemblies, constraints, collision groups, `Raycast`/`Shapecast` API, ray hits the shooter, unreliable `Touched`, network ownership, replacing BodyMovers |
| `roblox-studio-workflow` | edit/inspect/test an existing place or Rojo project, Studio MCP (`execute_luau`), Server & Clients test, report what was tested. Studio MCP setup or "tools missing" → Roblox's official `roblox-get-started` |
| `roblox-simulator-economy` | Roblox simulator/tycoon/clicker/idle economy, upgrade cost curve, `baseCost`, buy max, income per second, rebirth pacing, offline earnings, big-number suffixes, "1000K" display bug, unearned currency, paid eggs/crates odds; pairs with `roblox-networking` + `roblox-datastores` |

## Disciplines (`skills/disciplines/`) — cross-engine concepts, load **with** the engine skill

| Concept skill | `says:` triggers | Pairs with (engine API skill) |
|---------------|------------------|-------------------------------|
| `create-game-assets` | art direction, style guide, sprite/sprite sheet, pixel art, tileset art, texture, icon, AI-generated art, fake transparency, Steam AI disclosure | engine importer/rendering skill; installed `imagegen` for raster generation when available |
| `game-ai` | enemy/NPC AI, FSM/state machine, patrol and chase, steering, A* pathfinding, perception ("sees through walls"), stuck on corners, FSM vs BT vs utility vs GOAP choice | `unity-navmesh` / `unreal-behavior-trees` / Godot nav (`godot-nodes-scenes` + `godot-physics`) |
| `ai-behavior-trees-utility-ai` | behavior tree code (engine-neutral), blackboard, reactive composites, selector/sequence/parallel, decorator, utility AI, response curve, consideration, AI restarts its action every frame or flip-flops | `game-ai` (model choice) / `unreal-behavior-trees` (UE BT, EQS, StateTree assets) |
| `procedural-gen` | procedural generation, seeded RNG, dungeon generator, rooms and corridors, BSP, cellular caves, wave function collapse (WFC), Perlin/simplex noise terrain, loot tables, same seed gives different maps | engine tilemap/grid: `godot-tilemap` / `unity-tilemap-2d` / `godot-3d-essentials` |
| `dialogue-systems` | dialogue system, branching dialogue, Yarn Spinner, Ink, conversation tree, barks, dialogue dead-ends; `*.yarn`/`*.ink` | engine UI: `godot-ui-control` / Unity UI |
| `save-systems` | save/load (route here first), save slots, continue button, autosave, atomic writes, corrupt saves after a crash, saves broken after a patch, versioned migration; `save*.json`/`*.sav` | `roblox-datastores` / Godot IO / engine serialization |
| `audio-design` | mixing, bus layout, volume sliders in decibels, loudness, ducking, adaptive music, repetitive footsteps, beat sync design, mix clips or pumps | `godot-audio` / Unity AudioMixer / FMOD/Wwise |
| `shader-programming` | how an effect works (dissolve, outline, fresnel rim, post effects), GLSL ↔ HLSL porting, specks or mobile shimmer; `*.shader`/`*.hlsl`. One-engine shader work needs only the engine skill. | `godot-shaders` / `threejs-materials-lighting` / `pixijs-rendering` |
| `physics-tuning` | jitter, tunnelling, "objects pass through walls", fixed timestep and interpolation, CCD, damping, solver iterations, collision layer matrix, floaty physics | the engine physics skill: `godot-physics` / `unity-physics` / `roblox-physics` / `phaser-arcade-physics` |
| `level-design` | level layout, greybox/blockout a level, player metrics, key and ability gating, soft-lock check, metroidvania gates, pacing, players get lost | `godot-tilemap` / `unity-tilemap-2d` / `godot-3d-essentials` (GridMap) |
| `input-systems` | input mapping, named actions, rebind menu with conflict checks, controller support, stick deadzone/drift, WASD on AZERTY, dropped press, generic input buffering | `unity-input-system` / `unreal-enhanced-input` / Godot InputMap |
| `game-feel` | game feel, juice, trauma screen shake, hit-stop, eased tweens, squash & stretch, knockback, "flat", "weightless", "make it punchy" | engine animation/tween (`godot-animation`/`unity-animation`) + `camera-systems` (follow) + `audio-design` |
| `camera-systems` | camera follow, deadzone, look-ahead, camera bounds, third-person orbit, first-person look, split-screen, Cinemachine 3, camera lag/jitter, clips through walls | `godot-2d-movement`/`godot-3d-essentials` / Unity Cinemachine 3 / Godot `Camera2D`/`Camera3D` |
| `game-ui-ux` | HUD, health bar, main/pause/settings menu, inventory screen layout, anchors, UI scaling, ultrawide/phone breakage, safe area, gamepad focus, event-driven HUD, accessibility minimums | `godot-ui-control` / `roblox-ui` / Unity UI (UGUI/UI Toolkit); load both |
| `performance-optimization` | low/dropping FPS, stutter, "stutter the first time an effect appears", "phone slows after minutes", CPU- vs GPU-bound, draw calls, pooling, GC spikes, profile | engine profiler (Godot Monitors / Unity Profiler / Unreal `stat unit` / Roblox MicroProfiler) + `physics-tuning` |

## Genres (`skills/genres/`) — whole-game templates, load **with** the engine skill

| Genre skill | `says:` triggers | composes (bind `*` to the detected engine) |
|-------------|------------------|---------------------------------------------|
| `platformer` | platformer, Mario- or Celeste-like, jump feel, **coyote time, jump buffer, variable jump height** (owner), fall gravity, corner correction, wall jump, one-way platforms, checkpoints, "floaty" or "laggy" jump | engine movement (`godot-2d-movement` / `phaser-arcade-physics` / `unity-physics`) + `level-design` + `camera-systems` + `game-feel` |
| `roguelike` | roguelike, roguelite, NetHack- or Hades-style, run structure, permadeath, meta-progression, seeded/daily runs, turn order, field of view, runs feel cheap | `procedural-gen` (generation and loot tables) + `godot-tilemap`/`unity-tilemap-2d` + `game-ai` + `save-systems` (run vs meta saves) |
| `rpg` | RPG, JRPG, Diablo-style looter, stats with modifiers, XP curve, damage formula, items, equipment slots, rarity, affixes, quests, stats wrong after unequipping | `godot-resources`/`unity-scriptableobjects` + `dialogue-systems` + `save-systems` + `game-ui-ux` |
| `fps-shooter` | FPS, Doom- or Counter-Strike-like, hitscan vs projectiles, time-to-kill, damage falloff, recoil, ADS sensitivity, lag-compensated hits, guns feel weak, shots not registering | `godot-3d-essentials`/`unreal-cpp-gameplay` + `input-systems` + `game-ai` + `camera-systems` + `game-feel` |
| `tower-defense` | tower defense, Bloons- or Kingdom Rush-like, lane/maze pathing, wave pacing, targeting priority, armoured/flying counters, gold economy, late waves impossible or trivial | `game-ai` + `godot-2d-movement`/engine movement + `level-design` + `game-ui-ux` |
| `card-game` | card game, deckbuilder, **roguelike deckbuilder** (owner), Slay the Spire- or Balatro-like, TCG, effect interpreter, trigger stack, seeded shuffle, cards duplicate | `godot-resources`/`unity-scriptableobjects` + `game-ui-ux` + `godot-ui-control` (engine UI) |
| `visual-novel` | visual novel, VN, dating sim, routes and endings, save-anywhere, backlog, skip read-only, typewriter text, Ren'Py; `*.rpy` | `dialogue-systems` + `save-systems` + `game-ui-ux` |
| `survival-crafting` | survival game, Minecraft-, Valheim- or Don't Starve-like, gathering, crafting recipes, tech tree, carry weight, spoilage, hunger, temperature, base building | `save-systems` + `godot-resources`/`unity-scriptableobjects` + `procedural-gen` + `game-ui-ux` |
| `puzzle` | puzzle game, match-3 cascades, Sokoban, nonogram/Picross, Sudoku, unique solution, exact undo, solver-checked levels, unsolvable level | `godot-tilemap`/`unity-tilemap-2d` + `level-design` + `game-feel` |

Plain "inventory" belongs to neither genre alone: items, equipment and rarity go to `rpg`;
gathering, stacks, weight, spoilage and recipes go to `survival-crafting`. Ask if the request
gives no detail.

## Workflows (`skills/workflows/`) — process & shipping, engine-independent

| Workflow skill | `says:` / `files:` triggers |
|----------------|------------------------------|
| `game-jam` | game jam, 48-hour game, Ludum Dare, GMTK, Global Game Jam, Brackeys, itch.io jam, jam rules, "we're behind, what do we cut" |
| `prototype-fast` | "prototype this", "just get something playable", "rough it in", "is this fun", greybox a mechanic, keep or kill the prototype |
| `steam-publish` | publish on Steam, SteamPipe, depots, `app_build` `.vdf`, `steamcmd` upload, ContentBuilder, beta branch, SetLive, store review, Coming Soon, Steam Deck Verified, "Failed to get application info"; `steam_appid.txt` |
| `itch-publish` | upload to itch, `butler push`, channels, HTML5 game downloads instead of playing, blank or 403 web build, "invalid target", `--userversion`; `.itch.toml` |
| `game-docs` | GDD, game design doc, spec out / write up a feature, update or sync the GDD or design docs, record a design decision, split a GDD into features; an existing GDD (`GDD.md`, `features/*/design.md`). Only when asked for docs or a GDD already exists, never for a plain "make a game" |

## Keyword traps with no owner

Answer with a one-line pointer and say there is no skill; do not route to a near match.

- **Steamworks SDK in game code** (`SteamAPI_Init`, achievements, stats, overlay, lobbies, Steam
  Input): use the engine binding — GodotSteam, Steamworks.NET or Facepunch.Steamworks,
  Unreal's Online Subsystem Steam. `steam-publish` covers uploads only.
- **Unity VFX Graph:** no owner. Do not load `unreal-niagara`; use `shader-programming` only for
  shader maths and Unity's own documentation for the graph.
- **Building Unreal from source:** out of scope for `unreal-cpp-gameplay`; point to Epic's
  source-build documentation.
- **React Three Fiber:** no skill; `threejs-scene-setup` covers plain three.js only. OpenAI's
  `game-studio` plugin has a React Three Fiber skill if the user has it installed.

## Binding gaps (be honest; do not fabricate a skill)

For a **custom, proprietary, in-house, or unsupported engine**, keep the engine and use the
router's `custom-engines.md` reference. Load the relevant genre/discipline skills; replace
catalog engine bindings with verified project APIs. Engine-specific names in composition
tables are examples, not mandatory dependencies for portable genre systems.

The collection does not yet have a skill for every engine × concept. Several cross-cutting
concerns are now covered **engine-neutrally** by disciplines that pair with any detected engine —
camera work (`camera-systems`), HUD/menus (`game-ui-ux`), juice/feedback (`game-feel`), and
performance (`performance-optimization`) — so those are no longer gaps; bind them on top of the
engine. The remaining true gaps are engine-specific primitives. When a genre binding names a slot
the detected engine lacks, load the closest skill(s) and **state the gap** plainly:

- **No `*-2d-movement` for Unity / Unreal / web.** `unity-physics` now covers Rigidbody2D
  movement, ground checks and one-way platforms (its `physics-2d.md` reference), so a Unity
  platformer binds movement to `unity-physics` + `unity-csharp-scripting`; it is still not a
  dedicated 2D-movement skill. For Phaser, use `phaser-arcade-physics`.
- **No dedicated 3D-essentials for Unity.** For a Unity FPS, use `unity-csharp-scripting` +
  `unity-physics` + `unity-navmesh`; only Godot has `godot-3d-essentials` and Unreal has
  `unreal-cpp-gameplay`.
- **No `*-tilemap` for web / Bevy / pygame / Roblox / LÖVE / Defold.** Use `level-design` for the concept
  and the engine's rendering skill for drawing; note the missing engine tilemap skill.
- **No engine-specific save skill except Roblox.** `save-systems` owns the concept and cites
  Godot IO; `roblox-datastores` is the one engine-specific persistence skill.
- **No Godot particles skill.** `GPUParticles2D/3D` node setup is not covered; `godot-shaders`
  covers particle shaders only.
- **No Roblox profiling skill.** Roblox Studio's built-in `rbx-perf-profiling` and
  `rbx-scene-analysis` skills (through Studio MCP) supply the data; `performance-optimization`
  supplies the method.
- **Ebitengine uses one engine skill with focused references.** Bind engine movement,
  collision, rendering/camera, UI, audio, data/save and build slots to `ebitengine-game`;
  open only the matching reference. A puzzle/card request does not require a platformer
  scaffold. The Tiled loader is deliberately constrained, not a complete editor importer.
  Networking guidance does not supply transport/matchmaking; native 3D is outside this
  2D skill. Never substitute another engine's API to hide one of these gaps.
- **Defold has one core skill.** Bind movement, input, spawning, level loading and build slots
  to `defold-core`. There is no Defold GUI, sprite/tilemap or collision skill yet: use
  `defold-core` (its build reference links the official manuals for those subsystems) plus
  `game-ui-ux` / `level-design` / `physics-tuning`, and state the gap.
