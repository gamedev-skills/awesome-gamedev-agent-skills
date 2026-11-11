---
name: godot-signals-groups
description: >
  Godot 4.7 signals and node groups: typed signals, connect() with Callables, one-shot and
  deferred connections, event-bus autoloads and call_group broadcasts. Use when nodes must talk
  without hard references, a handler fires twice or never, or the log says "already connected".
  Not for GDScript syntax (`godot-gdscript`) or autoload setup (`godot-nodes-scenes`).
---

# Godot Signals & Groups (4.x)

Decouple nodes with signals and act on many nodes at once with groups, instead of
hard-coding references between scenes. Targets **Godot 4.7** (see Version notes).

## When to use

- A node must announce "something happened" (player died, item picked up, wave
  cleared) without holding references to its listeners.
- A whole category of nodes needs one call ("pause all enemies", "save every
  checkpoint").

**When *not* to use:** general GDScript syntax → `godot-gdscript`; scene structure and
autoload registration → `godot-nodes-scenes`.

## Core workflow

1. **Decide the direction.** A child or sub-scene *emits* upward; the parent *connects*.
   The child stays reusable and ignorant of who listens. Calling down into a child you own
   is a plain method call, not a signal.
2. **Declare typed signals** on the emitter and `emit()` exactly the declared arguments.
3. **Connect with a Callable** (`sig.connect(_on_sig)`). Use `CONNECT_ONE_SHOT` for
   fire-once and `bind()` to pass extra context.
4. **Editor connections and groups are plain text in the `.tscn`**, so you can read and
   write them without the Node dock:

   ```ini
   [node name="Goblin" type="CharacterBody2D" parent="Enemies" groups=["enemies"]]

   [connection signal="pressed" from="UI/StartButton" to="." method="_on_start_pressed"]
   ```

   `from`/`to` are paths relative to the scene root, and the `method` must exist on the
   `to` node's script.
5. **Use groups for broadcast**: `add_to_group()`, then `get_tree().call_group(...)` or
   iterate `get_nodes_in_group(...)`.
6. **For cross-scene events, put signals on an autoload** (event bus, see the reference).
7. **Check before you finish.**
   - If you edited `.tscn` connections, run the `godot-nodes-scenes` skill's
     `scripts/check_godot_project.py <project-dir>`; it reports `[connection]` entries
     whose `from`/`to` node does not exist. It does not check method names.
   - Prove the wiring at runtime with a headless test (Pattern 4), or smoke-run the scene
     and grep the log:

     ```bash
     godot --headless --path . --fixed-fps 60 --quit-after 300 --scene res://level.tscn > run.log 2>&1
     grep -nE "^ *(SCRIPT ERROR|ERROR):" run.log   # signal errors print as ERROR: lines
     ```

     With no Godot binary (`godot`, `godot4` or `$GODOT_BIN`), ask the user to run it and
     paste `run.log`.

## Patterns

### 1. Emit upward, connect from the parent

```gdscript
# coin.gd (reusable pickup; knows nothing about the player or HUD)
extends Area2D
signal collected(value: int)

func _ready() -> void:
    body_entered.connect(_on_body_entered)

func _on_body_entered(body: Node2D) -> void:
    if body.is_in_group("player"):
        collected.emit(10)
        queue_free()
```

```gdscript
# level.gd (the parent wires coins to game state)
func _ready() -> void:
    for coin in get_tree().get_nodes_in_group("coins"):
        coin.collected.connect(_on_coin_collected)

func _on_coin_collected(value: int) -> void:
    GameState.add_score(value)
```

### 2. One-shot and bound arguments

```gdscript
func _ready() -> void:
    $Door.opened.connect(_on_door_opened, CONNECT_ONE_SHOT)   # auto-disconnects
    # bind() appends its arguments after the signal's own arguments.
    $RedButton.pressed.connect(_on_button.bind("red"))

func _on_button(color: String) -> void:
    print("Pressed the %s button" % color)
```

### 3. Groups: broadcast to many nodes

```gdscript
func pause_all_enemies() -> void:
    get_tree().call_group("enemies", "set_paused", true)   # skips nodes without the method
```

### 4. Headless test that a signal reaches its handler once

```gdscript
# res://tests/test_signals.gd
extends SceneTree

func _initialize() -> void:
    var level: Node = load("res://level.tscn").instantiate()
    root.add_child(level)                          # parent _ready() connects the coins
    await process_frame
    var coin: Node = get_first_node_in_group("coins")
    var failed := 0
    if coin == null or coin.collected.get_connections().size() != 1:
        failed += 1
        push_error("coin.collected should have exactly one connection")
    print("Results: %d failed" % failed)
    quit(1 if failed > 0 else 0)
```

Run it with `godot --headless --path . --script res://tests/test_signals.gd` and read the
exit code. To check the handler's effect, emit the signal in the test and assert on the
state it should change.

## Gotchas

- **3.x connect signature is gone.** `connect("died", self, "_on_died")` →
  `died.connect(_on_died)`. `Object.connect("died", Callable(self, "_on_died"))` still
  works; the method-name string form does not. Prefer `died.emit()` over
  `emit_signal("died")`: a misspelled signal name is then a parse error, not a runtime one.
- **Connecting the same method twice** prints "Signal '...' is already connected to given
  callable" and keeps one connection. A new lambda each time is a *different* Callable, so
  it stacks silently and the handler fires once per connect. Keep the lambda in a variable,
  or guard with `if not sig.is_connected(cb):`.
- **A lambda outlives the nodes it captures.** Godot removes a connection when the emitter
  or the Callable's owner is freed, but a lambda belongs to the script that created it; one
  that captures a node freed later keeps firing and errors. Connect listener methods, or
  disconnect stored lambdas yourself.
- **Argument mismatch fails at emit time.** `emit()` does not validate arguments against
  the `signal` declaration; a handler with a different count logs "Error calling from
  signal ... Method expected N argument(s)". Declare typed params and emit exactly those.
- **Groups are global to the SceneTree**, not per scene. Two levels using the same group
  name share membership; namespace names if that matters.
- **`call_group` silently ignores nodes lacking the method**, so a typo fails quietly.
  Prefer a typed signal when the contract matters.
- **`[connection]` to a method that doesn't exist** is not caught by the checker; Godot
  prints a "Cannot connect" error when the scene is instantiated, so the smoke run catches
  it.
- **Handlers that change the tree during physics** ("flushing queries" errors) → connect
  with `CONNECT_DEFERRED` or `call_deferred` the change.

## References

- Read `references/signal-patterns.md` when you need every connection flag, `unbind()`,
  awaiting a signal with a timeout, safe disconnection and lambda lifetime, the full
  groups API, an autoload event bus, or a signals-vs-direct-calls decision.

## Related skills

- `godot-gdscript` for signal and `await` syntax.
- `godot-nodes-scenes` for autoloads used as global event buses, and the checker.
- `godot-gdscript-headless-testing` to keep Pattern 4 in CI.
- `game-ai` for state machines that drive and consume these events.

## Version notes

Last verified: 2026-11-11 against Godot 4.7.2-stable (released 2026-08-18).

- Variadic rest parameters (`..._args`), used by the reference's timeout helper, exist
  since GDScript 4.5.
- The "already connected" and "Method expected N argument(s)" messages match 4.7.2's
  `object.cpp` and `variant.cpp`.

Sources: [object.cpp @ 4.7.2-stable](https://github.com/godotengine/godot/blob/4.7.2-stable/core/object/object.cpp),
[variant.cpp @ 4.7.2-stable](https://github.com/godotengine/godot/blob/4.7.2-stable/core/variant/variant.cpp),
[Signal @ 4.7.2-stable](https://github.com/godotengine/godot/blob/4.7.2-stable/doc/classes/Signal.xml),
[Using signals](https://docs.godotengine.org/en/stable/getting_started/step_by_step/signals.html).
