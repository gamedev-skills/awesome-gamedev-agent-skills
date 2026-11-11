# GDScript annotations & typing reference (Godot 4.7)

Depth companion to `godot-gdscript`. All annotations start with `@` in GDScript 2.0.

## Common export annotations

```gdscript
@export var title: String = "Level 1"
@export var enabled := true
@export_range(0, 100, 1) var percent: int = 50          # min, max, step
@export_range(0.0, 1.0, 0.01, "or_greater") var gain := 1.0
@export_enum("Idle", "Walk", "Run") var state: int       # int-backed dropdown
@export_enum("Sword", "Bow") var weapon: String          # string-backed dropdown
@export_flags("Fire", "Water", "Earth") var resist: int  # bitmask
@export_file("*.json") var data_path: String             # file picker
@export_dir var folder: String
@export_multiline var description: String                 # multi-line text box
@export_color_no_alpha var tint: Color
@export_node_path("Camera2D") var cam_path: NodePath
@export_group("Movement")                                 # groups Inspector fields
@export var speed := 200.0
@export_subgroup("Air")
@export var air_control := 0.4
```

Export a typed array of resources (great for data-driven design):

```gdscript
@export var waves: Array[PackedScene] = []
@export var loot: Array[ItemResource] = []
```

## Other annotations

- `@onready var x = $Child` — assign when the node enters the tree.
- `@tool` — run the script in the editor (top of file). Guard editor-only code with
  `if Engine.is_editor_hint():`.
- `@icon("res://icon.svg")` — custom Inspector icon for a `class_name` type.
- `@rpc("any_peer", "call_local", "reliable")` — mark a networked method (see
  `godot-multiplayer`).
- `@warning_ignore("unused_variable")` — silence a specific parser warning.
- `@static_unload` — allow a script's static variables to unload.
- `@export_tool_button("Rebuild") var rebuild_action := rebuild` — an Inspector button
  that calls a `Callable` (4.4+; the script must also be `@tool`).
- `@export_storage var cache: Array` — saved with the scene/resource but hidden from the
  Inspector.
- `@abstract` (4.5+) — on a class (before `class_name`) it cannot be instantiated; on a
  bodiless method, every concrete subclass must implement it.

## Static typing details

```gdscript
var a: int = 3                 # explicit type
var b := 3                     # inferred int via :=
var c: float                   # typed, defaults to 0.0
var nodes: Array[Node2D] = []  # typed array (element type enforced)
var scores: Dictionary[String, int] = {}  # typed dictionary (Godot 4.4+)
var any_data: Dictionary = {}  # untyped: keys and values can be anything

func clamp_hp(hp: int) -> int:
    return clampi(hp, 0, 100)  # clampi/clampf are typed variants

func best_score(name: String) -> int:
    var s: int = scores.get(name, 0)  # get() returns Variant even on a typed dictionary,
    return s                          # so `var s := scores.get(...)` fails to parse
```

Typed code is faster because the VM can skip runtime type checks, and the editor can
autocomplete and flag mismatches before you run.

## Lifecycle callbacks (order)

1. `_init()` — object constructed (no tree, no children resolved).
2. `_enter_tree()` — node added to the tree (children may not be ready).
3. `_ready()` — node and all children are in the tree (runs once). `@onready` vars are
   assigned just before this.
4. `_process(delta)` — every rendered frame (skip with `set_process(false)`).
5. `_physics_process(delta)` — every fixed physics tick (default 60 Hz).
6. `_exit_tree()` — node removed from the tree.
7. `_notification(what)` — low-level catch-all (e.g. `NOTIFICATION_WM_CLOSE_REQUEST`).

## Idioms

- Prefer `is_instance_valid(node)` before touching a node that may have been freed.
- Use `queue_free()` (deferred) over `free()` to delete a node safely during a frame.
- `match` is GDScript's switch: supports values, arrays `[1, var x]`, and `_` default.
- String formatting: `"%s scored %d" % [name, score]`.
- Use `assert(cond, "msg")` for debug-only invariants (stripped in release builds).
