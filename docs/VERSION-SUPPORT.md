# Version support

Checked **2026-09-25** (Bevy row re-checked **2026-10-09** for the 0.20 release). These are
authoring baselines for **new projects**, not forced upgrade
targets. Existing projects keep the version declared by their manifest, lockfile, or engine
metadata unless the user explicitly asks for migration.

| Stack | New-project baseline | Detection / source |
|-------|----------------------|--------------------|
| Godot | 4.7 (current stable patch; 4.7.2 at last check) | `project.godot`; [official archive](https://godotengine.org/download/archive/) and [stable docs](https://docs.godotengine.org/en/stable/) |
| Godot .NET | Godot 4.7 + .NET 8 | `.csproj`; [Godot C# basics](https://docs.godotengine.org/en/stable/tutorials/scripting/c_sharp/c_sharp_basics.html) |
| Unity | Unity 6.3 LTS / 6000.3 | `ProjectSettings/ProjectVersion.txt`; [Unity 6 support](https://unity.com/releases/unity-6/support) |
| Unreal Engine | 5.8 | `*.uproject`; [UE 5.8 release](https://www.unrealengine.com/news/unreal-engine-5-8-is-now-available) and [what's new](https://dev.epicgames.com/documentation/unreal-engine/whats-new) |
| Phaser | 4.2 | `package.json` + lockfile; [Phaser downloads](https://phaser.io/download/phaser4) and [3→4 migration](https://phaser.io/news/2026/04/migrating-from-phaser-3-to-phaser-4-what-you-need-to-know) |
| PixiJS | 8.21 | `package.json` + lockfile; [PixiJS releases](https://pixijs.com/blog) |
| three.js | r186 | `package.json` + lockfile; [three.js releases](https://github.com/mrdoob/three.js/releases) |
| Bevy | 0.20 | `Cargo.toml` + `Cargo.lock`; [Bevy 0.20](https://bevy.org/news/bevy-0-20/) and [migration guide](https://bevy.org/learn/migration-guides/0-19-to-0-20/) |
| pygame-ce | 2.5.8 | Python dependency/lockfile; [pygame-ce releases](https://github.com/pygame-community/pygame-ce/releases) |
| LÖVE | 11.5 | `conf.lua` / `main.lua`; [LÖVE releases](https://love2d.org/wiki/Version_History) |
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
