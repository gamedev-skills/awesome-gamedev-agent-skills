---
name: defold-core
description: >
  Builds and debugs Defold 1.14 games in Lua: collections, game objects, input focus, msg.post
  messaging, factories, collection proxies and Bob builds. Use for .collection or .script files,
  on_input never firing, a proxy that never loads, or "could not be found when dispatching
  message". Not for LÖVE (`love2d-core`), HUD rules (`game-ui-ux`) or physics feel
  (`physics-tuning`).
---

# Defold Core

Structure, wire and verify a Defold game: editor resource files, the Lua script lifecycle,
addressing and messages, runtime spawning and world loading, and a Bob build-and-run check.
Examples target **Defold 1.14.1**; they were built with Bob 1.14.1 and run on the 1.14.1
headless engine. An existing project keeps its Defold version (see [Version](#version)).

## When to use

- Use when adding or fixing game objects, collections, scripts, input, messages, spawning or
  level loading in a Defold project (`game.project` in the root, `.collection`, `.go`,
  `.script`, `.gui_script` files), or when Bob reports a missing resource.

**When *not* to use:** plain Lua or LÖVE projects (`love2d-core`); GUI layout, sprites,
tilemaps and physics depth beyond the pointers in the references; engine-agnostic design
handled by the related skills below.

## Workflow

1. **Inspect first.** Read `game.project` (`[bootstrap] main_collection`, `[input]
   game_binding`, `[project] dependencies`), the main collection, and the scripts near the
   request. Follow the project's folder layout, id naming and message names; do not
   reorganize. Note which Defold/Bob version CI or the team uses.
2. **Edit the right file type.** Game objects (`.go`) hold components; collections
   (`.collection`) place game objects and other collections; logic goes in `.script`
   (game objects), `.gui_script` (GUI) or shared `.lua` modules. Editor files are
   protobuf text: keep their structure, and copy shapes from
   `references/file-formats.md` instead of guessing fields.
3. **Check references.** Run `python scripts/check_defold_project.py <project-dir>` (path
   relative to this skill folder; Python 3.10+, no Defold install needed). Fix every `ERROR`
   (missing or wrong-case `/paths`, a `game.project` path without the compiled `c` suffix,
   a `require` whose file does not exist). Warnings cover files nothing uses yet, unfetched
   library dependencies and runtime-loaded files. Re-run until it exits 0.
4. **Build with Bob.** `java -jar bob.jar --root . --variant headless --archive resolve
   build` needs JDK 25 and a `bob.jar` matching the project's Defold version. Exit 1 plus
   an `ERROR:` line means a broken reference or a Lua syntax error (with file and line);
   `references/file-formats.md` shows how to trace an error that names a generated file.
5. **Run it.** A build does not prove the game works. Run a headless bundle under a timeout
   (`references/build-and-run.md`) and read the log: `ERROR:SCRIPT:` lines are Lua runtime
   errors, `ERROR:GAMEOBJECT:` lines bad addresses or socket clashes. Require a line your
   test prints when it finishes; the exit code alone proves nothing. The headless engine has
   no keyboard, mouse or screen, so for input, rendering or layout changes ask the user to
   run the game (editor **Project ▸ Build**, or the desktop bundle from the reference) and
   report what they see, and say what you could not verify.

## Patterns

### Project and resource references

`game.project` is an INI file in the project root. Resource paths everywhere are
root-absolute (`/main/player.go`). In `game.project` they name the **compiled** file, so the
source path gets a trailing `c`:

```ini
[bootstrap]
main_collection = /main/main.collectionc

[input]
game_binding = /input/game.input_bindingc
```

Bob builds only what is reachable from `game.project`; `/builtins/...` ships with the engine.

### Collections, game objects, components

A collection places instances and can override script properties per instance; a game object
lists file components and embedded components (escaped `data:` strings). Full verified
files are in `references/file-formats.md`.

```text
# main.collection (excerpt): place player.go and override its script's speed
instances {
  id: "player"
  prototype: "/main/player.go"
  component_properties {
    id: "player"
    properties { id: "speed" value: "250.0" type: PROPERTY_TYPE_NUMBER }
  }
}
```

### Script lifecycle, `self` and properties

```lua
go.property("speed", 200)                   -- top level only, literal default; editable per instance

local LEFT = hash("left")                   -- hash ids once, not every frame
local RIGHT = hash("right")
local FIRE = hash("fire")

function init(self)
	msg.post(".", "acquire_input_focus")    -- no focus, no on_input calls
	self.held = {}                          -- per-instance state lives on self
end

function update(self, dt)
	local dir = (self.held[RIGHT] and 1 or 0) - (self.held[LEFT] and 1 or 0)
	if dir ~= 0 then
		local pos = go.get_position()
		pos.x = pos.x + dir * self.speed * dt    -- dt-scaled: same speed at any frame rate
		go.set_position(pos)
	end
end

function on_input(self, action_id, action)
	if action_id == LEFT or action_id == RIGHT then
		if action.pressed then self.held[action_id] = true
		elseif action.released then self.held[action_id] = nil end
		return true                         -- consumed: listeners lower on the stack skip it
	elseif action_id == FIRE and action.pressed then
		factory.create("#bulletfactory", go.get_position(), nil,
			{ velocity = vmath.vector3(0, 600, 0) })
		return true
	end
end

function final(self)
	msg.post(".", "release_input_focus")
end
```

Callbacks: `init`, `final`, `fixed_update`, `update`, `late_update` (after every `update`,
before render), `on_message`, `on_input`, `on_reload`. Update order between game
objects is unspecified. `fixed_update` runs 0..N times per frame at `[engine]
fixed_update_frequency`; set `[physics] use_fixed_timestep = 1` too so physics steps at the
same rate, and put physics-driven code there. `self` is userdata: store
fields on it, but `pairs(self)` and `pprint(self)` do not work. Property types: number,
boolean, hash, `msg.url`, `vmath.vector3`/`vector4`, `vmath.quat`, resources such as
`resource.atlas("/main/main.atlas")`, and (since 1.13.2) strings.

### Input bindings and the input stack

`.input_binding` maps devices to action names (`key_trigger`, `mouse_trigger`, plus
gamepad, touch and text triggers). Every component that acquired focus sits on an input
stack; the last to acquire is on top and gets input first, and returning `true` from
`on_input` stops it there, which is how pause menus block gameplay input. Key actions report
`pressed` and `released`; track held keys yourself as above. Since 1.14.1, `action.source`
is a hash (`mouse`, `touch`, `keyboard`, `gamepad`, `text` or `accelerometer`), which tells a
real mouse click from one simulated by touch.

### Addressing and messages

A URL is `[socket:][path][#fragment]`: `"."` is this game object, `"#"` this component,
`"#sprite"` a sibling component, `"enemy#ai"` a relative object, `"/manager#controller"` an
absolute one, `"main:/loader#loader"` an object in another world. Collections create naming
scopes, so a string id is resolved relative to the sender's collection; a pre-hashed id is
always absolute.

```lua
msg.post("/manager#controller", "enemy_spotted", { id = go.get_id() })

function on_message(self, message_id, message, sender)
	if message_id == hash("enemy_spotted") then
		print("from", sender, "id", message.id)
	end
end
```

Messages are queued and dispatched later in the frame; the table is capped at 2 KB. A bad
address logs `ERROR:GAMEOBJECT: Instance '/x' could not be found when dispatching message`.

### Factories and collection factories

```lua
-- factory component "#bulletfactory" -> one game object; properties override go.property values
local id = factory.create("#bulletfactory", pos, nil, { velocity = vmath.vector3(0, 600, 0) })

-- collectionfactory component "#wavefactory" -> table of collection ids -> new instance ids
local ids = collectionfactory.create("#wavefactory", vmath.vector3(480, 500, 0))
local leader = ids[hash("/leader")]         -- e.g. hash: [/collection0/leader]
go.delete(ids, true)                        -- later: delete them and their children
```

Position and rotation default to the spawning object's. `go.delete()` takes effect at the
end of the frame. Per-instance properties for a collection factory are keyed by id:
`{ [hash("/leader")] = { hp = 5 } }`.

### Collection proxies (load another world)

```lua
-- excerpt from the loader script; the collection's "#levelproxy" component is a collectionproxy
function init(self)
	msg.post(".", "acquire_input_focus")        -- else the loaded world gets no input
	msg.post("#levelproxy", "async_load")       -- or "load"
end

function on_message(self, message_id, message, sender)
	if message_id == hash("proxy_loaded") then
		msg.post(sender, "init")
		msg.post(sender, "enable")
	elseif message_id == hash("level_done") then
		msg.post("#levelproxy", "unload")       -- disables and finalizes first
	elseif message_id == hash("proxy_unloaded") then
		-- safe to load the next level here
	end
end
```

The loaded world's socket is the **`name:` of the loaded collection file**, so scripts in it
reply with `msg.post("main:/loader#loader", ...)` and its own URLs read
`level1:/level#level`. `set_time_step { factor = 0, mode = 0 }` pauses a proxy world.

## Version

`game.project` has no engine version key. Use the Defold editor or `bob.jar` version the
project is built with (CI often pins a release sha1), and `library.defold_min_version` when the
project is a library. `java -jar bob.jar --version` prints the version and sha1. Keep that
version; do not migrate unless asked.

## Gotchas

- **Bob: `the bootstrap.main_collection '/main/main.collectio' can't be found`** → the
  setting lacks the compiled suffix and Bob stripped the last letter. Write
  `/main/main.collectionc` (same for `input.game_binding` → `.input_bindingc`).
- **Bob: `ERROR: build/default/_generated_….factory:0: the prototype '/main/x.go' can't be
  found`** → an embedded component in some `.go` points at a missing file. Search the
  sources for the quoted path (`/main/x.go`), not the generated name, or run the checker.
- **`on_input` never fires** → the object never sent `acquire_input_focus`, the action name
  differs from the binding, `input.game_binding` points elsewhere, or a listener higher on
  the stack returns `true`.
- **Input dead inside a proxy-loaded level** → the game object holding the collection proxy
  did not acquire input focus.
- **`already a socket with the same name` and the proxy never sends `proxy_loaded`** → the
  loaded collection's `name:` equals an already loaded world (often both are `"main"` or
  `"default"`). Give every proxied collection a unique name.
- **`fixed_update` never runs** → `[engine] fixed_update_frequency` is 0 (default 60). For
  physics also set `[physics] use_fixed_timestep = 1`, as the manual requires both.
- **`module 'modules.util' not found` at run time although Bob succeeded** → a `require` used
  slashes (`require "modules/util"`). Use the dotted path from the project root,
  `require "modules.util"` for `/modules/util.lua`.
- **An HTML5 build shows a black screen or shader errors only on old WebGL 1 devices, after
  moving to 1.14.1** → 1.14.1 stopped compiling GLES 2.0 / WebGL 1 shaders by default. Set
  `[shader] exclude_gles_sm100 = 0` in `game.project` if the game must still run there.
- **Bob fails at once with `UnsupportedClassVersionError … class file version 69.0`** →
  Bob 1.14.x needs Java 25; an older JDK is on the `PATH`.
- **`tostring(id)` prints `hash: [<unknown:…>]`** → hashes keep their source text only in
  debug builds. Compare hashes, never their strings.
- **A second engine logs `Failed to initialize Remotery`, or a test run never ends** → the
  debug engine opens an engine service (port 8001), a log server and a profiler port, and
  waits forever without `sys.exit`. Run one engine at a time and always use a timeout.

## References

- Read `references/file-formats.md` before writing or repairing editor files by hand, or
  when a Bob error names a generated file: verified minimal `game.project`, `.collection`,
  `.go`, `.atlas`, `.input_binding` and script files, and how to trace errors to a source.
- Read `references/build-and-run.md` when you build, bundle or smoke-test: Java and
  `bob.jar` downloads, Bob commands, platforms and variants, the headless smoke test with
  timeout and log checks, ports, and manual pointers for GUI, sprites, tilemaps and
  collision objects.
- Run `scripts/check_defold_project.py` after editing resource files (workflow step 3);
  `--help` lists every check.

## Related skills

- `input-systems` — rebinding, gamepad support and buffering on top of Defold bindings.
- `game-ui-ux` — HUD and menu design to build with GUI scenes and `.gui_script`.
- `physics-tuning` — fixed-timestep and collision tuning for collision objects.
- `camera-systems` — follow/deadzone logic, typically applied in `late_update`.
- `save-systems` — save formats and slots; pair with Defold's `sys.save`/`sys.load`.
- `game-feel` — juice built from `go.animate` and timers.
- `platformer`, `level-design` — genre and layout guidance that binds to this skill.
- `love2d-core` — the other Lua engine in this catalog, for LÖVE projects.

## Version notes

Last verified: 2026-11-11.

- Defold 1.14.1 became the stable release on 2026-11-10 (sha1
  `ee283d4dad9fa451dd6399d83602e1dc25133681`); 1.14.0 was released on 2026-10-12.
- 1.14.1 changes that touch this skill: GLES 2.0 / WebGL 1 shaders are excluded by default
  (`[shader] exclude_gles_sm100` now defaults to 1), `action.source` in `on_input`, and the
  debug and headless engines print an OpenAPI URL for their engine service at startup.
- Bob 1.14.1 needs OpenJDK 25 (its classes are version 69).
- The example project in the references (player, factory, collection factory, proxy-loaded
  level), the smoke bundle and the quoted build and runtime errors were rebuilt with Bob
  1.14.1 and run on the 1.14.1 `dmengine_headless` with Temurin 25.0.5 on Linux x86_64.
  `action.source` was not run (the headless engine has no input); it comes from the
  release notes.
- Sources: [stable info.json](https://d.defold.com/stable/info.json),
  [1.14.1 release](https://github.com/defold/defold/releases/tag/1.14.1),
  [1.14.1 release notes (beta post)](https://forum.defold.com/t/defold-1-14-1-beta/83389),
  [GLES 2.0 default change (PR #13543)](https://github.com/defold/defold/pull/13543),
  [Bob manual](https://defold.com/manuals/bob/).
