# Engine detection — full project fingerprint

The router body carries the primary signal per engine; this file holds the **complete**
fingerprint table, the disambiguation rules, and the secondary signals. Detection is
**exclusive**: identify one engine for the target project. A custom/proprietary engine can be
known without a catalog skill; use the router's custom-engine fallback in that case.

Scan for the highest-confidence signal and stop at the first match in this precedence order.

| # | Engine | Primary signal (project files) | Secondary signals | Skill set root |
|:-:|--------|--------------------------------|-------------------|----------------|
| 1 | Godot | `project.godot` | `*.tscn`, `*.gd`, `*.gdshader`, `*.tres`, `export_presets.cfg` | `skills/godot/` |
| 2 | Unreal | `*.uproject` | `Source/**/*.Build.cs`, `Config/Default*.ini`, `*.uasset`, `Content/` | `skills/unreal/` |
| 3 | Unity | `Assets/` **and** `ProjectSettings/ProjectVersion.txt` | `*.unity`, `*.prefab`, `*.asmdef`, `Packages/manifest.json` | `skills/unity/` |
| 4 | Ebitengine | `go.mod` requiring `github.com/hajimehoshi/ebiten/v2` | Go imports of that module, `ebiten.RunGame`, `*.kage` | `skills/ebitengine/` |
| 5 | Bevy | `Cargo.toml` with a `bevy` dependency | `*.rs` with `App::new()` / `use bevy::prelude` | `skills/other-engines/bevy-ecs/` |
| 6 | Phaser | `package.json` dep `phaser` | `import Phaser`, `new Phaser.Game` | `skills/web-engines/phaser-core`, `skills/web-engines/phaser-arcade-physics` |
| 7 | PixiJS | `package.json` dep `pixi.js` | `import * as PIXI`, `new PIXI.Application` | `skills/web-engines/pixijs-rendering/` |
| 8 | three.js | `package.json` dep `three` | `import * as THREE`, `*.gltf` / `*.glb` | `skills/web-engines/threejs-scene-setup`, `threejs-gltf-loading`, `threejs-materials-lighting` |
| 9 | Defold | `game.project` | `*.collection`, `*.go`, `*.script`, `*.gui_script`, `*.atlas`, `*.input_binding`, `/builtins/` paths | `skills/other-engines/defold-core/` |
| 10 | LÖVE | `conf.lua`, or `main.lua` calling `love.*` | `*.love` | `skills/other-engines/love2d-core/` |
| 11 | pygame | `*.py` with `import pygame` | `pygame.init()`, `pygame.display.set_mode` | `skills/other-engines/pygame-core/` |
| 12 | Roblox | `*.rbxl` / `*.rbxlx`, or `*.project.json` (Rojo) | `*.luau`, `DataStoreService`, `game:GetService` | `skills/other-engines/roblox-*` (`roblox-luau` first, then the focused Roblox skill) |
| 13 | RPGJS | `package.json` dep `@rpgjs/server` or `@rpgjs/client` | `client.ts`, `server.ts`, `standalone.ts`, `*.ce` files | `skills/web-engines/rpgjs-core`, `rpgjs-events-maps`, `rpgjs-testing` |

## Detect the installed version

Engine identity is not enough. Read the version source before using version-sensitive APIs:

| Stack | Version source |
|-------|----------------|
| Godot | feature tags in `project.godot`, then the project's documented toolchain or `godot --version` when available |
| Unity | `ProjectSettings/ProjectVersion.txt` plus package versions in `Packages/manifest.json` / `packages-lock.json` |
| Unreal | `EngineAssociation` in `*.uproject`, project documentation, or the selected installed engine |
| Ebitengine | `go.mod` module version, `replace` directives and `go.work`; inspect the replacement checkout when a local replacement is active |
| Phaser / PixiJS / three.js | `package.json` **and the resolved lockfile**, not a tutorial's version |
| Bevy | `Cargo.toml` and the resolved `Cargo.lock` entry |
| pygame-ce | `pyproject.toml`, requirements/lock files, then the active environment |
| Defold | `game.project` has no engine version key: use the editor or `bob.jar` version the project is built with (a release or sha1 pinned in CI or docs; `java -jar bob.jar --version`), and `library.defold_min_version` when present |
| LÖVE | `conf.lua` version when declared, then the installed runtime |
| Roblox | platform APIs are rolling; inspect current Creator Hub documentation for unstable APIs |

For a new project use the baseline stated in the engine skill (the catalog-wide table is
`docs/VERSION-SUPPORT.md` in the source repository). For an existing project,
preserve the detected version unless the user explicitly requests migration.

## Disambiguation rules (must-handle ambiguities)

- **Godot C# vs Unity vs Bevy** — all may contain a `.csproj` or `Cargo.toml`. The presence of
  `project.godot` means **Godot** (route `godot-csharp` for C# work) even when a `.csproj`
  exists. Unity requires the `Assets/` + `ProjectSettings/` pair, not just any `.cs`. Bevy
  requires a `bevy` dependency, not just any Rust crate.
- **Ebitengine vs unrelated Go code** — a generic `go.mod` is not an engine signal. Require
  the Ebitengine v2 dependency or imports and confirm the requested package is the game;
  an editor/tool or another engine's project can use the dependency without being an
  Ebitengine game. Browser launch scaffolding does not change a Go game's engine to a
  JavaScript renderer.
- **Defold vs LÖVE vs plain Lua** — all three are Lua. A `game.project` file in the project
  root means **Defold**, even if a `main.lua` module is present; Defold code lives in
  `.script`/`.gui_script` files and `require`d modules and never calls `love.*`. LÖVE
  needs `conf.lua` or a `main.lua` calling `love.*`. Lua files or a `.rockspec` with
  neither signal are not an engine project: use the unknown-engine fallback. Roblox Luau is
  detected by its place/Rojo files, not by `.lua`.
- **Multiple web deps** — a `package.json` may list more than one of `phaser` / `pixi.js` /
  `three`. Prefer the library actually imported in the file under discussion; if unclear, ask
  which renderer the task targets before loading a web-engine skill.
- **Monorepo / multiple engines** — if more than one engine fingerprint is present, route by the
  file or subdirectory the request is about. If still ambiguous, ask one targeted question.
- **No engine files at all** — go to the unknown-engine fallback (router body §6). Many
  discipline / genre / workflow tasks need no engine at all.
- **Custom/proprietary engine** — inspect the named engine's build files, runtime entry point,
  local SDK/docs and examples. A generic CMake project, `.csproj`, Lua file, or bundled renderer
  alone does not establish a catalog engine. Preserve the existing engine; record its revision
  from build metadata or local documentation and use `custom-engines.md` for API bindings.

## Plain-text engine mentions

If there are no project files but the request names an engine in prose ("in Unity", "using
Phaser", "a Godot game"), adopt that engine. Never load an engine skill on a guess when neither
a file signal nor a named engine is present.

## Confidence boosters from task files

Some non-project files raise confidence about the *task* (not the engine):

- `*.yarn` / `*.ink` → `dialogue-systems` (and `visual-novel` if the whole game is one).
- `steam_appid.txt` / Steamworks SDK → `steam-publish`.
- `.itch.toml` / `butler` usage → `itch-publish`.
- `*.inputactions` → `unity-input-system`; `IA_`/`IMC_` assets → `unreal-enhanced-input`.
- `NavMesh.asset` / baked navmesh → `unity-navmesh`; `BT_`/`BB_` assets → `unreal-behavior-trees`.
