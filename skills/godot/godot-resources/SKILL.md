---
name: godot-resources
description: >
  Godot 4.7 data-driven design with custom Resources: class_name and @export fields, .tres files,
  shared references vs duplicate_deep(), uids and threaded loading. Use for items, stats or enemy
  configs as data, or when editing one enemy changes every enemy or a .tres stops loading. Not for
  save slots (`save-systems`) or the C# version (`godot-csharp`).
---

# Godot Resources (4.x)

Model game data as `Resource` objects saved as `.tres`/`.res`, share them safely, and
load them without hitches. Targets **Godot 4.7** (see Version notes).

## When to use

- Items, stats, enemy configs, dialogue lines or level metadata as data files; custom
  `Resource` subclasses; `ResourceLoader`/`ResourceSaver` code.

**When *not* to use:** scene structure → `godot-nodes-scenes`; the player's runtime
progress, slots and migration → `save-systems`; C# → `godot-csharp`.

## Core workflow

1. **Subclass `Resource`** with `class_name` and typed `@export` fields (Pattern 1). The
   `class_name` is what lets the editor offer it in "New Resource" and as an export type.
2. **Create instances as text `.tres` files.** You can write them directly (Pattern 2)
   instead of clicking through the FileSystem dock and Inspector; use binary `.res` only for
   large generated data.
3. **Reference resources from nodes** with `@export var data: ItemResource` or
   `@export var loot: Array[ItemResource]`, or load them by path in code.
4. **Load** with `preload` (constant path) or `load` (variable path); use
   `ResourceLoader.load_threaded_request` for large scenes (see the reference).
5. **Duplicate before mutating** a shared resource at runtime (Pattern 3); every node that
   loaded the same path holds the same object.
6. **Check before you finish.**
   - After adding or moving `.tres`/`.gd` files, run the `godot-nodes-scenes` skill's
     `scripts/check_godot_project.py <project-dir>` to catch broken `ext_resource` paths,
     uids and ids. Fix every `ERROR`.
   - Prove the data loads and copies correctly with a headless test (Pattern 4):
     `godot --headless --path . --import` once on a fresh checkout (so `class_name` types
     resolve), then `godot --headless --path . --script res://tests/test_items.gd`, and
     read the exit code. With no Godot binary (`godot`, `godot4` or `$GODOT_BIN`), ask the
     user to run both lines and paste the output.

## Patterns

### 1. A custom data resource

```gdscript
# res://items/item.gd
extends Resource
class_name ItemResource

@export var id: StringName = &""
@export var display_name: String = "Item"
@export_multiline var description: String = ""
@export var icon: Texture2D
@export var max_stack: int = 99
@export var value: int = 0
```

### 2. The same item as a hand-written `.tres`

```ini
[gd_resource type="Resource" script_class="ItemResource" format=3]

[ext_resource type="Script" path="res://items/item.gd" id="1_item"]

[resource]
script = ExtResource("1_item")
id = &"sword"
display_name = "Sword"
max_stack = 1
value = 50
```

Leave out the `uid=` attributes; Godot adds them the next time the file is saved. Fields
left out keep the script defaults.

### 3. Duplicate before mutating shared data

```gdscript
func give_unique_copy(template: ItemResource) -> ItemResource:
    # true = deep: copies nested arrays/dictionaries and *embedded* sub-resources, but
    # sub-resources saved in their own .tres stay shared. Use
    # template.duplicate_deep(Resource.DEEP_DUPLICATE_ALL) to copy those as well.
    var copy: ItemResource = template.duplicate(true)
    copy.value += 5                # mutating the copy won't touch the template .tres
    return copy
```

### 4. Headless check: the file loads as its class and copies are independent

```gdscript
# res://tests/test_items.gd
extends SceneTree

func _initialize() -> void:
    var failed := 0
    var sword := load("res://items/sword.tres") as ItemResource
    if sword == null:
        failed += 1
        push_error("sword.tres did not load as ItemResource")
    else:
        var copy: ItemResource = sword.duplicate(true)
        copy.value += 1
        if copy.value == sword.value:
            failed += 1
            push_error("duplicate(true) shares state with the template")
    print("Results: %d failed" % failed)
    quit(1 if failed > 0 else 0)
```

## Gotchas

- **Resources are shared by reference.** Every `load()` of one path returns the same cached
  object, so mutating it changes every user (and re-saving writes the change into the
  file). Duplicate for per-instance state, or set `resource_local_to_scene = true` for a
  copy per scene instance.
- **A deep copy still changes the original's sub-resource** → `duplicate(true)` only copies
  sub-resources embedded in the file; one saved as its own `.tres` (e.g. a shared
  `stats.tres` inside `goblin.tres`) stays the same object. Use
  `duplicate_deep(Resource.DEEP_DUPLICATE_ALL)` when those must be copied too.
- **`class_name` is required for editor and typed use.** Without it the class is missing
  from "New Resource" and cannot be an `@export` type.
- **`class_name` "not declared" only in headless or CI runs** → the global class cache in
  `.godot/` is missing on a fresh checkout. Run `godot --headless --path . --import` first.
- **`res://` is read-only in exported games.** Write runtime data to `user://`.
  `ResourceSaver.save` to `res://` works only while running from the project folder.
- **Moving a `.gd` or `.tres` outside the editor breaks `ext_resource` paths.** Move the
  `.uid` sidecar with scripts, then run the checker; a uid that still resolves keeps the
  link working.
- **Nodes stored in a Resource don't serialize.** Resources hold data; reference scenes as
  `PackedScene`, not node instances.
- **Cyclic references** (A holds B holds A) can fail to save or load cleanly; keep data
  graphs acyclic or link by id.
- **`preload` vs `load`.** `preload` needs a constant path and loads with the script;
  `load` takes a runtime path. Check `ResourceLoader.exists()` first for optional files.
- **`.tres` files ship as readable text** inside the export, so keep secrets out of them.

## References

- Read `references/resource-patterns.md` when you need threaded loading with progress,
  `resource_local_to_scene`, `@tool` resources, a custom `ResourceFormatLoader`/`Saver`
  for a new file type, uid handling, or a registry layout for many data files.

## Related skills

- `godot-gdscript` for the `@export` annotations that define resource fields.
- `godot-nodes-scenes` for instancing scenes vs sharing resource data, and the checker.
- `save-systems` for persisting runtime progress (separate from static data).
- `godot-gdscript-headless-testing` to keep data tests in CI.
- `unity-scriptableobjects` for the equivalent Unity pattern.

## Version notes

Last verified: 2026-11-11 against Godot 4.7.2-stable (released 2026-08-18).

- `Resource.duplicate_deep()` and `DEEP_DUPLICATE_ALL` exist since 4.5.
- `.uid` sidecar files for scripts and shaders exist since 4.4; commit them.
- The text format writes `script_class` in the `[gd_resource]` header; since 4.6 it no
  longer writes or reads `load_steps`, so older files that carry it still load.

Sources: [Resource @ 4.7.2-stable](https://github.com/godotengine/godot/blob/4.7.2-stable/doc/classes/Resource.xml),
[resource_format_text.cpp @ 4.7.2-stable](https://github.com/godotengine/godot/blob/4.7.2-stable/scene/resources/resource_format_text.cpp),
[Resources](https://docs.godotengine.org/en/stable/tutorials/scripting/resources.html),
[File paths in Godot projects](https://docs.godotengine.org/en/stable/tutorials/io/data_paths.html).
