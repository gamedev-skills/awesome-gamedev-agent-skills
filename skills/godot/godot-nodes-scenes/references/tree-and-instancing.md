# Scene tree & instancing reference (Godot 4.7)

Depth companion to `godot-nodes-scenes`.

## Node paths

- `$Child`, `$Child/Grandchild` — relative path sugar for `get_node(...)`.
- `$"Node With Spaces"` — quote paths containing spaces or starting with a number.
- `%UniqueName` — a scene-unique node. Mark a node "Access as Unique Name" in the editor;
  the reference survives hierarchy changes within the same scene/owner. It still uses
  the node's name, so update the reference if that name changes.
- `get_node("../Sibling")` — `..` walks up to the parent.
- `get_tree().root` — the `Window` at the very top; the current scene is
  `get_tree().current_scene`.

## Loading and instancing

```gdscript
const SCENE := preload("res://enemy.tscn")   # constant path, loaded with the script
var dynamic := load(path_variable)            # runtime path, may be a variable

var e := SCENE.instantiate()                  # PackedScene -> Node
add_child(e)                                  # enters tree, _ready() fires
# To instance with the editor state of exported sub-resources, instantiate() is enough.
```

`instantiate()` flags: `PackedScene.GEN_EDIT_STATE_DISABLED` (default, runtime) vs
`GEN_EDIT_STATE_INSTANCE`/`GEN_EDIT_STATE_MAIN` (editor tooling only).

## Ownership when saving scenes from code

To build a scene in code and save it, every node you want serialized must have its
`owner` set to the scene root:

```gdscript
func save_built_scene() -> void:
    var root := Node2D.new()
    var child := Sprite2D.new()
    root.add_child(child)
    child.owner = root                 # without this, child is NOT saved
    var packed := PackedScene.new()
    packed.pack(root)
    ResourceSaver.save(packed, "res://generated.tscn")
```

## Scene inheritance

In the editor, "New Inherited Scene" from a base `.tscn` creates a child scene that
inherits the base's nodes and can override properties or add nodes. Useful for variant
enemies sharing a common base. Changes to the base propagate to inherited scenes.

## Groups vs unique names vs autoloads

- **Unique name (`%`)** — reference a specific node *within the same scene*.
- **Group** — tag many nodes and act on all of them; see `godot-signals-groups`.
- **Autoload** — one global instance accessible by name across all scenes; use for
  services and cross-scene state, not for per-level nodes.

## Freeing and validity

```gdscript
node.queue_free()                 # safe: deletes at end of current frame
if is_instance_valid(node):       # guard against use-after-free
    node.do_something()
node.free()                       # immediate; only when you control the timing
```

`get_child_count()`, `get_children()`, `move_child(node, idx)`, and
`reparent(new_parent)` (4.x) manage tree structure at runtime. `reparent` keeps global
transform by default.

## Deferred calls

When adding/removing nodes during physics callbacks or signal handlers, defer to avoid
"flushing queries" errors:

```gdscript
add_child.call_deferred(instance)
node.queue_free()                 # already deferred
```
