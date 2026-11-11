# Version support

Checked **2026-10-24**: every row below was re-checked against the latest stable release, and
the skills were reviewed against it. These are
authoring baselines for **new projects**, not forced upgrade
targets. Existing projects keep the version declared by their manifest, lockfile, or engine
metadata unless the user explicitly asks for migration.

| Stack | New-project baseline | Detection / source |
|-------|----------------------|--------------------|
| Godot | 4.7 (current stable patch; 4.7.2 at last check) | `project.godot`; [official archive](https://godotengine.org/download/archive/) and [stable docs](https://docs.godotengine.org/en/stable/) |
| Godot .NET | Godot 4.7 + .NET 8 (Android exports target .NET 9) | `.csproj`; [Godot C# basics](https://docs.godotengine.org/en/stable/tutorials/scripting/c_sharp/c_sharp_basics.html) |
| Unity | Unity 6.3 LTS / 6000.3 (6000.3.28f1 at last check) | `ProjectSettings/ProjectVersion.txt`; [Unity 6 support](https://unity.com/releases/unity-6/support) |
| Unreal Engine | 5.8 (5.8.4 hotfix at last check) | `*.uproject`; [UE 5.8 release](https://www.unrealengine.com/news/unreal-engine-5-8-is-now-available) and [what's new](https://dev.epicgames.com/documentation/unreal-engine/whats-new) |
| Ebitengine | v2.10.5 / Go 1.25+ (pinned examples; checked 2026-10-23) | `go.mod`, `go.work` and `replace` directives; [v2.10.5 source and toolchain requirement](https://github.com/hajimehoshi/ebiten/blob/v2.10.5/go.mod) and [API reference](https://pkg.go.dev/github.com/hajimehoshi/ebiten/v2@v2.10.5) |
| Phaser | 4.2 (4.2.1 at last check) | `package.json` + lockfile; [Phaser downloads](https://phaser.io/download/phaser4) and [3→4 migration](https://phaser.io/news/2026/04/migrating-from-phaser-3-to-phaser-4-what-you-need-to-know) |
| PixiJS | 8.22 | `package.json` + lockfile; [PixiJS releases](https://pixijs.com/blog) |
| three.js | r187 (npm 0.187.0 at last check) | `package.json` + lockfile; [three.js releases](https://github.com/mrdoob/three.js/releases) |
| Bevy | 0.20 | `Cargo.toml` + `Cargo.lock`; [Bevy 0.20](https://bevy.org/news/bevy-0-20/) and [migration guide](https://bevy.org/learn/migration-guides/0-19-to-0-20/) |
| pygame-ce | 2.5.8 | Python dependency/lockfile; [pygame-ce releases](https://github.com/pygame-community/pygame-ce/releases) |
| LÖVE | 11.5 (12.0 not yet released) | `conf.lua` / `main.lua`; [LÖVE releases](https://love2d.org/wiki/Version_History) |
| Defold | 1.14.0 (examples built with Bob 1.14.0 and run on the 1.14.0 headless engine; checked 2026-10-23) | `game.project` has no version key: the editor/`bob.jar` version the project is built with, `library.defold_min_version`; [stable release info](https://d.defold.com/stable/info.json), [1.14.0 release](https://github.com/defold/defold/releases/tag/1.14.0) and [Bob manual](https://defold.com/manuals/bob/) |
| Roblox | rolling platform APIs | Rojo project / place files; [Creator Hub](https://create.roblox.com/docs) |

## Rules for version-sensitive work

1. Read the project version before proposing APIs.
2. Preserve the installed version and its package lock.
3. Never combine snippets from different engine majors or Bevy minor releases.
4. If migration is requested, read every intervening official migration guide and isolate the
   migration from unrelated feature work.
5. Run the engine/compiler/browser build that matches the project and verify the real output.

## Maintenance cadence

Review this table and search all skills for old baselines at least quarterly and whenever a covered
stack ships a stable/LTS release. A baseline update must include code review, routing/catalog
updates, primary-source links, and validator/tests—not a version-string-only change.
