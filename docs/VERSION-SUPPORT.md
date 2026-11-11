# Version support

Last verified **2026-11-11**: every row below was checked against the official release page
linked in it, and the skills were reviewed against that release. These are authoring baselines
for **new projects**, not forced upgrade targets. Existing projects keep the version declared by
their manifest, lockfile, or engine metadata unless the user explicitly asks for migration.

| Stack | New-project baseline | Last verified | Detection / source |
|-------|----------------------|---------------|--------------------|
| Godot | 4.7 (4.7.2 stable) | 2026-11-11 | `project.godot`; [4.7.2-stable release](https://github.com/godotengine/godot/releases/tag/4.7.2-stable), [official archive](https://godotengine.org/download/archive/) and [stable docs](https://docs.godotengine.org/en/stable/) |
| Godot .NET | Godot 4.7 + .NET 8 (Android exports target .NET 9) | 2026-11-11 | `.csproj`; [Godot C# basics](https://docs.godotengine.org/en/stable/tutorials/scripting/c_sharp/c_sharp_basics.html) |
| Unity | Unity 6.3 LTS / 6000.3 (6000.3.28f1, released 2026-11-03) | 2026-11-11 | `ProjectSettings/ProjectVersion.txt`; [6000.3.28f1 release notes](https://unity.com/releases/editor/whats-new/6000.3.28f1) and [Unity 6 support](https://unity.com/releases/unity-6/support) |
| Unreal Engine | 5.8 (5.8.4 hotfix). 5.9 is in Preview since 2026-11-09 and is not a baseline | 2026-11-11 | `*.uproject`; [5.8.4 hotfix](https://forums.unrealengine.com/t/5-8-4-hotfix-released/2842775), [UE 5.8 release notes](https://dev.epicgames.com/documentation/unreal-engine/unreal-engine-5-8-release-notes) and [5.9 MegaJam Preview](https://forums.unrealengine.com/t/unreal-engine-5-9-megajam-preview/2852840) |
| Ebitengine | v2.10.6 / Go 1.25+ | 2026-11-11 | `go.mod`, `go.work` and `replace` directives; [v2.10.6 release](https://github.com/hajimehoshi/ebiten/releases/tag/v2.10.6), [toolchain requirement](https://github.com/hajimehoshi/ebiten/blob/v2.10.6/go.mod) and [API reference](https://pkg.go.dev/github.com/hajimehoshi/ebiten/v2@v2.10.6) |
| Phaser | 4.2 (4.2.1) | 2026-11-11 | `package.json` + lockfile; [v4.2.1 release](https://github.com/phaserjs/phaser/releases/tag/v4.2.1) and [3→4 migration](https://phaser.io/news/2026/04/migrating-from-phaser-3-to-phaser-4-what-you-need-to-know) |
| PixiJS | 8.22 (8.22.0) | 2026-11-11 | `package.json` + lockfile; [v8.22.0 release](https://github.com/pixijs/pixijs/releases/tag/v8.22.0) |
| three.js | r187 (npm 0.187.0) | 2026-11-11 | `package.json` + lockfile; [r187 release](https://github.com/mrdoob/three.js/releases/tag/r187) |
| Bevy | 0.20 (0.20.1) | 2026-11-11 | `Cargo.toml` + `Cargo.lock`; [v0.20.1 release](https://github.com/bevyengine/bevy/releases/tag/v0.20.1), [Bevy 0.20](https://bevy.org/news/bevy-0-20/) and [migration guide](https://bevy.org/learn/migration-guides/0-19-to-0-20/) |
| pygame-ce | 2.5.8 | 2026-11-11 | Python dependency/lockfile; [2.5.8 release](https://github.com/pygame-community/pygame-ce/releases/tag/2.5.8) |
| LÖVE | 11.5 (12.0 not yet released) | 2026-11-11 | `conf.lua` / `main.lua`; [11.5 release](https://github.com/love2d/love/releases/tag/11.5) and [version history](https://love2d.org/wiki/Version_History) |
| Defold | 1.14.1 (examples built with Bob 1.14.1 and run on the 1.14.1 headless engine) | 2026-11-11 | `game.project` has no version key: the editor/`bob.jar` version the project is built with, `library.defold_min_version`; [stable release info](https://d.defold.com/stable/info.json), [1.14.1 release](https://github.com/defold/defold/releases/tag/1.14.1) and [Bob manual](https://defold.com/manuals/bob/) |
| Roblox | rolling platform APIs; skills checked against the Creator Hub on 2026-11-11 with Luau 0.746 | 2026-11-11 | Rojo project / place files; [Creator Hub](https://create.roblox.com/docs) and [Luau 0.746](https://github.com/luau-lang/luau/releases/tag/0.746) |

### Roblox tools

| Tool | Version | Source |
|------|---------|--------|
| Rojo | 7.7.1 | [release](https://github.com/rojo-rbx/rojo/releases/tag/v7.7.1) |
| selene | 0.32.0 | [release](https://github.com/Kampfkarren/selene/releases/tag/0.32.0) |
| luau-lsp | 1.70.1 | [release](https://github.com/JohnnyMorganz/luau-lsp/releases/tag/1.70.1) |
| Lune | 0.11.1 | [release](https://github.com/lune-org/lune/releases/tag/v0.11.1) |

## Rules for version-sensitive work

1. Read the project version before proposing APIs.
2. Preserve the installed version and its package lock.
3. Never combine snippets from different engine majors or Bevy minor releases.
4. If the project is newer than the baseline above, say so and read the engine's release notes
   for the versions in between before trusting a skill's API details.
5. If migration is requested, read every intervening official migration guide and isolate the
   migration from unrelated feature work.
6. Run the engine/compiler/browser build that matches the project and verify the real output.

## Maintenance cadence

Review this table and search all skills for old baselines at least quarterly and whenever a covered
stack ships a stable/LTS release. A baseline update must include code review, routing/catalog
updates, primary-source links, and validator/tests—not a version-string-only change.
