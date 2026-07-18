---
name: godot-nodes-scenes
description: >
  Structure a Godot 4.x project with the scene tree and node composition: build
  reusable scenes, instance PackedScenes at runtime, navigate the tree safely,
  and register autoload singletons. Use when designing .tscn scenes, deciding how
  to split nodes, spawning instances with instantiate(), wiring autoloads, or
  fixing "node not found"/freed-node errors in a Godot project.
license: Apache-2.0
compatibility: Godot 4.3+
metadata:
  engine: godot
  category: godot
  difficulty: beginner
---

# Godot Nodes & Scenes (4.x)

Compose games from nodes and scenes, instance them at runtime, and access the tree
without crashing on freed or missing nodes. Targets **Godot 4.3+**.

## When to use

- Use when structuring `.tscn` scenes, choosing how to break a feature into nodes,
  instancing a `PackedScene` (bullets, enemies, UI), or setting up autoload singletons.
- Use when debugging `get_node()` / `$Path` returning `null`, or "Attempt to call on a
  previously freed instance".

**When _not_ to use:** GDScript language/syntax → `godot-gdscript`; signal-based
decoupling → `godot-signals-groups`; physics bodies/collisions → `godot-physics`.

## Core workflow

1. **Model with composition.** A scene is a tree of nodes saved as `.tscn`. Build small,
   single-purpose scenes (Player, Bullet, Enemy) and compose larger scenes from them.
   Favor adding child nodes over deep inheritance.
2. **Make a scene reusable** by giving its root a script and exposing `@export` config.
   Save it; it becomes a `PackedScene` you can instance many times.
3. **Instance at runtime** with `preload`/`load` → `scene.instantiate()` →
   `add_child(instance)`. Set position/state _after_ adding (or before, both work).
4. **Access nodes safely.** Use `@onready var x = $Path` for fixed children; use unique
   names (`%Name`) for nodes deep in the tree; never assume a node still exists.
5. **Use autoloads for global state/services** (game state, audio, scene switching) —
   registered in Project Settings > Globals (Autoload), accessible by name everywhere.
6. **Free nodes with `queue_free()`** and guard later access with `is_instance_valid()`.

## Patterns

### 1. Instance a scene at runtime

```gdscript
extends Node2D

const BULLET := preload("res://bullet.tscn")   # preload: loaded at compile time

func shoot(at: Vector2, dir: Vector2) -> void:
    var bullet := BULLET.instantiate()         # create an instance of the scene
    bullet.global_position = at
    bullet.direction = dir                      # set exported/public state
    add_child(bullet)                           # now it's in the tree and runs
```

### 2. Safe node access: $, get_node_or_null, and unique names

```gdscript
@onready var label: Label = $UI/Label            # $ is sugar for get_node("UI/Label")
@onready var health_bar: ProgressBar = %HealthBar # % = scene-unique name (rename-proof)

func update() -> void:
    var optional := get_node_or_null("Maybe/Missing")  # returns null instead of erroring
    if optional:
        optional.queue_free()
```

### 3. An autoload singleton (global game state)

```gdscript
# game_state.gd — add in Project Settings > Globals > Autoload as "GameState".
extends Node

var score := 0
signal score_changed(value: int)

func add_score(points: int) -> void:
    score += points
    score_changed.emit(score)         # any scene can: GameState.score_changed.connect(...)
```

### 4. Change the running scene

```gdscript
func go_to_level_2() -> void:
    # Swaps the current scene for another. Frees the old scene tree.
    get_tree().change_scene_to_file("res://levels/level_2.tscn")
    # Or, with a preloaded PackedScene:
    # get_tree().change_scene_to_packed(LEVEL_2)
```

## Pitfalls

- **`$Path` / `get_node()` return `null` or error** when the path is wrong or the node
  isn't in the tree yet. Use `@onready`, verify the path matches the scene, or use
  `get_node_or_null()` for optional nodes.
- **Renaming a node breaks `$Path`.** Use **unique names** (`%Name`, set via right-click
  > Access as Unique Name) so deep references survive renames and reparenting.
- **`free()` mid-frame can crash** other code still using the node. Prefer
  `queue_free()` (deletes at end of frame) and check `is_instance_valid(node)`.
- **Setting child state before `add_child()`** is fine, but `_ready()` on the child only
  runs _after_ it enters the tree — don't expect its `@onready` vars before that.
- **Autoload order matters**: autoloads are added before the main scene, in list order.
  An autoload can't depend on the main scene existing yet.
- **`instance()` was renamed** to `instantiate()` in Godot 4. `preload` runs at parse
  time (path must be constant); `load` runs at runtime (path can be a variable).
- **`change_scene_to_file()` is deferred**, not immediate — Godot swaps and frees the old
  scene at the end of the current frame. Any code after the call still runs against the _old_
  tree, and `get_tree().current_scene` isn't the new scene until next frame. Don't read the new
  scene's nodes on the same line; do it from the new scene's `_ready()`.

## References

- For scene inheritance, `owner`/ownership when saving scenes from code, groups vs
  unique names, and node-path edge cases, read `references/tree-and-instancing.md`.

## Related skills

- `godot-gdscript` — language, lifecycle, and `@onready`.
- `godot-signals-groups` — decouple instanced scenes from their spawner.
- `godot-resources` — share data between instances without duplicating it.
- `save-systems` — persist scene/game state across runs.
