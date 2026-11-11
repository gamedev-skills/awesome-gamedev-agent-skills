# Build and run with Bob (Defold 1.14.1)

Bob (`bob.jar`) is Defold's command-line builder. Everything here was run with Bob 1.14.1
(sha1 `ee283d4dad9fa451dd6399d83602e1dc25133681`) and OpenJDK 25 on Linux x86_64; commands,
flags and the error messages quoted are from those runs or from the official
[Bob manual](https://defold.com/manuals/bob/) and
[automated testing manual](https://defold.com/manuals/automated-testing/).

## Contents

- [Get the tools](#get-the-tools): Java, `bob.jar`, version check
- [Commands](#commands): build, bundle, build report, platforms, variants, `--settings`
- [Smoke test a running game](#smoke-test-a-running-game): test bootstrap, run under a
  timeout, judge the log
- [Ports and parallel runs](#ports-and-parallel-runs)
- [Beyond the core](#beyond-the-core): GUI, sprites, tilemaps, physics manuals

## Get the tools

- **Java:** Bob 1.14.x needs OpenJDK 25. On Java 21 it fails at once with
  `UnsupportedClassVersionError … class file version 69.0`.
- **bob.jar:** use the release the project is built with. Current stable release info is at
  [d.defold.com/stable/info.json](https://d.defold.com/stable/info.json) (version and sha1).
  Download by version from the GitHub release assets
  (`https://github.com/defold/defold/releases/download/1.14.1/bob.jar`) or by sha1
  (`https://d.defold.com/archive/stable/<sha1>/bob/bob.jar`).
- **Check it:** `java -jar bob.jar --version` prints the version, sha1 and channel.

## Commands

Bob runs the listed commands in order: `resolve` (fetch library dependencies into
`.internal/lib/`), `clean`, `distclean`, `build`, `bundle`.

```sh
# Build only: compiles everything reachable from game.project into build/default
java -jar bob.jar --root . --variant headless --archive resolve build

# Desktop bundle (release)
java -jar bob.jar --root . --archive --platform x86_64-linux --variant release \
  --bundle-output ../dist resolve distclean build bundle

# Machine-readable report of what was built
java -jar bob.jar --root . --archive --build-report-json ../report.json resolve build
```

- Platforms: `x86_64-linux`, `arm64-linux`, `x86_64-win32`, `x86_64-macos`, `arm64-macos`,
  `arm64-ios`, `arm64_sim-ios`, `armv7-android`, `wasm-web`.
- Variants: `debug` (default), `release`, `headless` (null graphics device).
- `bundle` needs `--archive` and `--platform`. `--bundle-output` must be **outside** the
  project's `build/` folder, or Bob stops with `Folder '…/build' in the project folder can't
  be used for bundling as this folder is reserved for Defold build system`.
- `--settings file.settings` overlays `game.project` keys (several files apply left to
  right). Use it for test bootstraps instead of editing `game.project`.
- The bundle lands in a folder named after `project.title`, with the executable named after
  the title without spaces (`Defold Core Example/DefoldCoreExample.x86_64`).
- Bob exits 1 on a build error. The useful line starts with `ERROR`; Java stack traces follow
  as `SEVERE` lines. Errors that name a generated file are traced in the file-formats
  reference that `SKILL.md` links.

## Smoke test a running game

A build proves the resources compile, not that scripts run. Give the project a test bootstrap
that loads the real main collection through a proxy, runs it for a while, prints a marker
and exits. These three files and the commands below were run as shown.

`test/smoke.settings`:

```ini
[bootstrap]
main_collection = /test/smoke.collectionc
```

`test/smoke.collection`:

```text
name: "smoke"
embedded_instances {
  id: "smoke"
  data: "components {\n"
  "  id: \"smoke\"\n"
  "  component: \"/test/smoke.script\"\n"
  "}\n"
  "embedded_components {\n"
  "  id: \"game\"\n"
  "  type: \"collectionproxy\"\n"
  "  data: \"collection: \\\"/main/main.collection\\\"\\n\"\n"
  "  \"\"\n"
  "}\n"
  ""
}
scale_along_z: 0
```

`test/smoke.script`:

```lua
-- Smoke-test bootstrap: loads the real main collection, lets it run, then exits.
go.property("seconds", 2)

local PROXY_LOADED = hash("proxy_loaded")

function init(self)
	msg.post(".", "acquire_input_focus")
	msg.post("#game", "load")
	self.time = 0
end

function update(self, dt)
	self.time = self.time + dt
	if self.time >= self.seconds then
		print("SMOKE done")
		sys.exit(0)
	end
end

function on_message(self, message_id, message, sender)
	if message_id == PROXY_LOADED then
		msg.post(sender, "init")
		msg.post(sender, "enable")
	end
end
```

The main collection's `name` must differ from `smoke`, since both worlds are loaded at once.

```sh
java -jar bob.jar --root . --settings test/smoke.settings --platform x86_64-linux \
  --variant headless --archive --bundle-output ../smoke-bundle resolve build bundle
timeout 30 "../smoke-bundle/Defold Core Example/DefoldCoreExample.x86_64" > run.log 2>&1
grep -q "SMOKE done" run.log && ! grep -q "^ERROR:" run.log && echo PASS
```

Judge the run by the log, not only the exit status:

- A Lua error in a callback prints `ERROR:SCRIPT: main/x.script:8: attempt to index …` with a
  traceback and the engine **keeps running**: without a timeout the test hangs, and with
  one it ends with the timeout's status (124 for GNU `timeout`).
- A main collection that cannot be created (for example a `require` that fails at load)
  exits 1 after `ERROR:GAMEOBJECT: Could not instantiate game object from prototype …`.
- Bad message targets and proxy clashes log `ERROR:GAMEOBJECT:` lines but do not stop the
  game, so check for them explicitly.
- For many assertions, print one structured line per result (the automated testing manual
  suggests a prefix such as `TEST {json}`) and fail the run on a missing final line.

Without a bundle, the headless engine binary can run a plain build from the project root
(it loads `build/default/game.dmanifest`). The official manuals do not document this binary;
it is published next to `bob.jar` as
`https://d.defold.com/archive/stable/<sha1>/engine/x86_64-linux/dmengine_headless`. Prefer
the headless bundle above when you need a documented path.

## Ports and parallel runs

A debug or headless engine starts an engine service on port 8001 (since 1.14.1 it logs an
`OpenAPI: http://…:8001/openapi.json` line describing that service), a log server on a
random port and the Remotery profiler (`ws://127.0.0.1:17815`). A second engine started at the same
time logs `ERROR:PROFILER: Failed to initialize Remotery`. Run one engine per test job, always
under a timeout, and make sure it has exited before the next run.

## Beyond the core

The headless engine has no input devices and draws nothing, so for input, rendering and
layout ask the user to run the editor (**Project ▸ Build**) or a debug bundle for their
platform (for example `--platform x86_64-win32 --variant debug`) and report what they see. For the next subsystems, read the
official manuals:

- GUI scenes and `.gui_script`: [GUI](https://defold.com/manuals/gui/) — a GUI script uses
  `gui.*` functions instead of `go.*` and acquires input focus the same way.
- Sprites and flipbooks: [Sprite](https://defold.com/manuals/sprite/) and
  [Atlas](https://defold.com/manuals/atlas/); play an animation with
  `sprite.play_flipbook("#sprite", "run")`.
- Tilemaps: [Tilemap](https://defold.com/manuals/tilemap/) and
  [Tile source](https://defold.com/manuals/tilesource/).
- Collision objects and physics messages: [Physics](https://defold.com/manuals/physics/);
  with a fixed timestep, act on physics in `fixed_update`.
- Engine-agnostic design for these topics: the related skills listed in `SKILL.md`.
