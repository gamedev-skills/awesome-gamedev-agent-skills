---
name: godot-gdscript
description: >
  GDScript 2.0 for Godot 4.7: static typing, @export and @onready, await and coroutines, and
  porting 3.x code. Use for .gd parse errors ("Cannot infer the type"), a coroutine that never
  resumes, a null @onready variable or upgrade breakage. Not for signals (`godot-signals-groups`),
  scenes (`godot-nodes-scenes`), C# (`godot-csharp`) or CI tests
  (`godot-gdscript-headless-testing`).
---

# Godot GDScript (4.x)

Write typed GDScript that parses on the project's Godot version and behaves the way the
engine schedules it, then prove every script compiles. Targets **Godot 4.7**; read
`config/features` in `project.godot` and keep an older project on its own version.

## Workflow

1. **Match the project's version and settings.** Check `config/features` and any
   `debug/gdscript/warnings/*` entries in `project.godot`: a warning set to Error (2) fails the
   parse, and `inference_on_variant` is an error by default.
2. **Type by default.** Annotate members, parameters and returns; use `:=` only when the
   right side has a static type (see Gotchas). Typed code catches mistakes at parse time and
   runs faster.
3. **Put code in the right callback.** `_init()`: no tree, no children. `_ready()`: after
   the children, only the first time the node enters the tree (`request_ready()` re-arms
   it). `_physics_process()`: movement and physics. `_process()`: visuals and UI.
4. **Write coroutines defensively.** Anything after `await` may run frames later, or never.
5. **Verify before you finish** (paths are relative to this skill's folder):
   - On a fresh checkout, import first: `godot --headless --path <project> --import`.
   - Run `godot --headless --path <project> --script <this skill>/assets/check_scripts_compile.gd`.
     It loads every `.gd` with autoloads and `class_name` types registered; exit 1 lists each
     `BROKEN` file under the engine's parse error and line. Fix the first error in a file
     first; later ones are often follow-ons.
   - Run the main scene briefly and read the log, because Godot exits 0 after runtime errors:
     `godot --headless --path <project> --quit-after 300 > run.log 2>&1`, then
     `grep -nE "SCRIPT ERROR|^ERROR:" run.log`.
   - For behaviour, write a test with `godot-gdscript-headless-testing`. If
     `godot-nodes-scenes` is installed,
     `python3 ../godot-nodes-scenes/scripts/check_godot_project.py <project>` catches broken
     `preload()`/`load()` paths.

## Patterns

### 1. A typed node script

```gdscript
class_name Spinner
extends Node2D

@export var speed_deg: float = 90.0
@export_range(0.0, 10.0, 0.5) var wobble := 2.0
@onready var sprite: Sprite2D = $Sprite2D   # resolved just before _ready()

func _ready() -> void:
    sprite.modulate = Color.AQUA

func _process(delta: float) -> void:
    rotation_degrees += speed_deg * delta
```

### 2. Typing values that come back as Variant

```gdscript
var scores: Dictionary[String, int] = {}      # typed dictionary, 4.4+

func best(name: String) -> int:
    var s: int = scores.get(name, 0)          # get() returns Variant: annotate, don't :=
    return s

func label_text() -> String:
    var label := get_node_or_null("UI/Score") as Label   # returns Node: cast to type it
    return label.text if label else ""
```

### 3. A coroutine that survives its node being freed

```gdscript
func flash() -> void:
    modulate = Color.RED
    await get_tree().create_timer(0.2).timeout
    if not is_inside_tree():
        return          # removed while we waited (a freed node never gets here at all)
    modulate = Color.WHITE
```

## Gotchas

- **`Cannot infer the type of "x" variable because the value doesn't have a set type`** →
  `:=` got a Variant: an untyped function's return, an untyped `Dictionary`/`Array`
  subscript, or a member of a value typed as a base class (`get_node("X").position`, since
  `get_node()` returns `Node`). Write the type (`var p: Vector2 = ...`) or cast with `as`.
- **`The variable type is being inferred from a Variant value`** → `max()`, `min()`,
  `clamp()` and `abs()` return Variant, and this warning is an error by default. Use `maxi`,
  `maxf`, `clampf`, `absf` and friends.
- **Code after `await` never runs, with no error** → the object that emits the signal was
  freed first (a `Timer` node, an enemy), or the awaiting node itself was freed. The
  coroutine is dropped silently, so cleanup and `quit()` after it never happen. Await
  `SceneTreeTimer`s for delays and check validity after waking (Pattern 3).
- **`Identifier "X" not declared in the current scope` on a fresh clone or in CI** → the
  `class_name` cache in `.godot/` does not exist yet. Run `--import` once.
- **`--check-only` reports `Identifier not found: SomeAutoload`** → `--check-only` parses one
  file without registering autoloads, so any script that names an autoload fails. Use the
  bundled compile check instead.
- **`Not all code paths return a value` after upgrading to 4.7** → an override now inherits
  the parent method's return type even when it does not declare one. Return on every path.
- **A setter stopped running after upgrading to 4.7** → assigning one element of a packed
  array property (`points[0] = v`) no longer calls that property's setter. Reassign the
  whole array.
- **`@onready` variable is null** → the node path is wrong, or code ran before `_ready()`
  (for example from `_init()` or a setter during scene load). Use `%UniqueName` for deep
  nodes.
- **`5 / 2 == 2`** → integer division truncates; write `5 / 2.0` or `float(a) / b`.
- **3.x scripts do not parse** → `export`, `onready`, `tool` and `yield(obj, "sig")` became
  `@export`, `@onready`, `@tool` and `await obj.sig`; `setget` became `set`/`get` blocks.
  Signal `connect()` changes are in `godot-signals-groups`.

## References

- Read `references/annotations-and-typing.md` for every `@export_*` variant, the other
  annotations (`@tool`, `@icon`, `@rpc`, `@warning_ignore`, `@export_tool_button`,
  `@export_storage`, `@abstract`), typed collections, and the full lifecycle order.
- `assets/check_scripts_compile.gd` is the compile check used in step 5.

## Related skills

- `godot-signals-groups`: signals, Callables and groups.
- `godot-nodes-scenes`: scene trees, instancing, autoloads and node paths.
- `godot-resources`: custom `Resource` classes with `class_name`.
- `godot-gdscript-headless-testing`: test runners and CI.
- `godot-csharp`: the same engine through C#.

## Version notes

Last verified: 2026-11-11 against the Godot 4.7.2 class reference, the 4.7 migration guide
and a 4.7.2 headless run.

- Godot 4.7.2 (August 2026) is the current stable release; 4.8 is in beta.
- Typed dictionaries exist since 4.4; `@abstract` classes and methods since 4.5.
- 4.7 behaviour changes: override return-type inheritance, and packed-array element writes
  no longer calling the property setter.
- Sources: [Godot releases](https://github.com/godotengine/godot/releases),
  [Upgrading to Godot 4.7](https://docs.godotengine.org/en/stable/tutorials/migrating/upgrading_to_godot_4.7.html),
  [Static typing in GDScript](https://docs.godotengine.org/en/stable/tutorials/scripting/gdscript/static_typing.html),
  [GDScript warning settings](https://docs.godotengine.org/en/stable/tutorials/scripting/gdscript/warning_system.html).
