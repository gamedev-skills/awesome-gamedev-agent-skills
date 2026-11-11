# Defold file formats (1.14.1)

Every file below comes from one small project that Bob 1.14.1 built (`--variant headless`) and
the 1.14.1 headless engine ran: a player that moves and fires bullets from a factory, a loader
that spawns a wave with a collection factory and loads a level through a collection proxy.
Copy these shapes when you must write editor files by hand; when the editor is available,
let it write them.

## Contents

- [game.project](#gameproject) and [.input_binding](#input_binding)
- [.collection](#collection): instances, embedded instances, nested collections, children,
  proxy-loaded collections
- [.go](#go): file and embedded components, factories, proxies
- [.atlas](#atlas) and [Scripts](#scripts)
- [Where build errors point](#where-build-errors-point): tracing generated-file errors

The editor files are protobuf text format. Fields not shown keep their defaults, `#` starts a
comment, and the field order the editor writes does not matter to Bob. The schemas are the
`*_ddf.proto` files in the Defold engine source.

```text
game.project
input/game.input_binding
main/main.collection      main/player.go   main/player.script
main/main.atlas           main/bullet.go   main/bullet.script
main/loader.go            main/loader.script        main/check.script
main/wave.collection      main/enemy.go
levels/level1.collection  levels/level.script
```

## game.project

INI file, required, in the project root, named exactly `game.project`. Paths name the compiled
file (trailing `c`). Without the `[bootstrap]` key Defold looks for `/logic/main.collectionc`;
without `[input]` it uses `/input/game.input_bindingc`.

```ini
[project]
title = Defold Core Example

[bootstrap]
main_collection = /main/main.collectionc

[input]
game_binding = /input/game.input_bindingc

[physics]
use_fixed_timestep = 1

[engine]
fixed_update_frequency = 60
```

Library dependencies are listed as `dependencies#0 = https://…/archive.zip`, `dependencies#1 =
…`; Bob's `resolve` command fetches them into `.internal/lib/`. Read any setting at run time
with `sys.get_config_string("project.title")`.

## .input_binding

```text
key_trigger {
  input: KEY_LEFT
  action: "left"
}
key_trigger {
  input: KEY_RIGHT
  action: "right"
}
key_trigger {
  input: KEY_SPACE
  action: "fire"
}
mouse_trigger {
  input: MOUSE_BUTTON_LEFT
  action: "touch"
}
```

`/builtins/input/all.input_binding` exists for quick tests; a game should own its bindings.

## .collection

Instances of game object files, an embedded instance, a nested collection and a per-instance
script property override. `name` becomes the socket when the collection is loaded through a
proxy, so every proxied collection needs a unique name.

```text
name: "main"
instances {
  id: "player"
  prototype: "/main/player.go"
  position {
    x: 480.0
    y: 120.0
  }
  component_properties {
    id: "player"                 # id of the script component inside player.go
    properties { id: "speed" value: "250.0" type: PROPERTY_TYPE_NUMBER }
  }
}
instances {
  id: "loader"
  prototype: "/main/loader.go"
}
embedded_instances {
  id: "check"                    # a game object defined inline; here it holds one script
  data: "components {\n  id: \"check\"\n  component: \"/main/check.script\"\n}\n"
}
collection_instances {
  id: "decor"
  collection: "/main/wave.collection"
  position {
    x: 100.0
    y: 400.0
  }
}
scale_along_z: 0
```

Ids inside a nested collection are prefixed with its id: the `leader` object in `decor` is
`/decor/leader`. A child is attached with `children: "child_id"` on the parent instance:

```text
name: "wave"
instances {
  id: "leader"
  prototype: "/main/enemy.go"
  children: "wingman"
}
instances {
  id: "wingman"
  prototype: "/main/enemy.go"
  position {
    x: 64.0
  }
}
scale_along_z: 0
```

A collection that only holds embedded instances, as loaded by a proxy:

```text
name: "level1"
embedded_instances {
  id: "level"
  data: "components {\n"
  "  id: \"level\"\n"
  "  component: \"/levels/level.script\"\n"
  "}\n"
  ""
}
scale_along_z: 0
```

## .go

`components` reference component files (a script here); `embedded_components` carry the
component's own file as an escaped string, split across adjacent quoted lines.

```text
components {
  id: "player"
  component: "/main/player.script"
}
embedded_components {
  id: "sprite"
  type: "sprite"
  data: "default_animation: \"blob\"\n"
  "material: \"/builtins/materials/sprite.material\"\n"
  "textures {\n"
  "  sampler: \"texture_sampler\"\n"
  "  texture: \"/main/main.atlas\"\n"
  "}\n"
  ""
}
embedded_components {
  id: "bulletfactory"
  type: "factory"
  data: "prototype: \"/main/bullet.go\"\n"
  ""
}
```

The loader object holds the other two spawning components:

```text
components {
  id: "loader"
  component: "/main/loader.script"
}
embedded_components {
  id: "levelproxy"
  type: "collectionproxy"
  data: "collection: \"/levels/level1.collection\"\n"
  ""
}
embedded_components {
  id: "wavefactory"
  type: "collectionfactory"
  data: "prototype: \"/main/wave.collection\"\n"
  ""
}
```

Older sprite data uses `tile_set: "/main/main.atlas"` instead of the `textures` block; keep
whichever form the project already uses.

## .atlas

```text
images {
  image: "/builtins/graphics/particle_blob.png"
}
animations {
  id: "blob"
  images {
    image: "/builtins/graphics/particle_blob.png"
  }
  playback: PLAYBACK_LOOP_FORWARD
  fps: 8
}
```

A sprite's `default_animation` names an image (file name without extension) or an animation
id in its atlas.

## Scripts

`bullet.script`, spawned by the player's factory with a `velocity` override:

```lua
go.property("velocity", vmath.vector3(0, 400, 0))
go.property("lifetime", 1.5)

function update(self, dt)
	go.set_position(go.get_position() + self.velocity * dt)
	self.lifetime = self.lifetime - dt
	if self.lifetime <= 0 then
		go.delete()                         -- deletes this game object at the end of the frame
	end
end
```

`level.script`, inside the proxy-loaded world, reporting back to the main world:

```lua
local LEVEL_DONE = hash("level_done")

function init(self)
	self.time = 0
	print("level init", msg.url())          -- url: [level1:/level#level]
end

function update(self, dt)
	self.time = self.time + dt
	if self.time >= 0.5 and not self.reported then
		self.reported = true
		msg.post("main:/loader#loader", LEVEL_DONE, { seconds = self.time })
	end
end
```

Shared code goes in `.lua` modules, loaded with a dotted path from the project root:
`local util = require "modules.util"` loads `/modules/util.lua`.

The run printed, in order: `wave leader hash: [/collection0/leader]`,
`level init url: [level1:/level#level]`, `level done after 0.5…`, `level unloaded`.

## Where build errors point

Bob names the source file and line 0 for most reference errors:

```text
ERROR: game.project:0: '…the bootstrap.main_collection '/main/main.collectio' can't be found'
ERROR: main/probe.script:0: '…the Lua module '/modules/nothere.lua' can't be found'
ERROR main/main.atlas:0 Resource 'main/images/missing.png' is not created
```

For an embedded component, Bob reports a generated file instead of the `.go` that holds it:

```text
ERROR: build/default/_generated_c1d664c47a440ab4.factory:0: '…the prototype '/main/missing.go' can't be found'
```

The generated name does not exist in the sources. Search them for the quoted path in the
message (`"/main/missing.go"`, written as `\"/main/missing.go\"` inside embedded data) or run
`scripts/check_defold_project.py`, which reports the `.go` file and line.

A missing resource property (`go.property("art", resource.atlas("/main/nope.atlas"))`) appears
only in the `SEVERE` stack trace lines: `Resource '/main/nope.atlas' referenced from script
resource property 'art' does not exist`.
