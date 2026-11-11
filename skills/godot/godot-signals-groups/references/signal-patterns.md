# Signal & group patterns reference (Godot 4.7)

Depth companion to `godot-signals-groups`.

Contents: connection flags · bind vs unbind · custom signals with typed arguments ·
awaiting a signal with a timeout · disconnecting safely · groups API · signals vs direct
calls · global event bus (autoload)

## Connection flags

`Object.connect` / `Signal.connect` accept a flags bitmask:

- `CONNECT_ONE_SHOT` — disconnect automatically after the first emission.
- `CONNECT_DEFERRED` — invoke the callback at idle time (end of frame) instead of
  immediately. Useful when the handler modifies the tree during physics.
- `CONNECT_PERSIST` — the connection is saved with the scene (editor-made connections).
- `CONNECT_REFERENCE_COUNTED` — multiple identical connections are reference-counted so
  the matching number of disconnects is required.

```gdscript
sig.connect(cb, CONNECT_ONE_SHOT | CONNECT_DEFERRED)
```

## bind vs unbind

- `cb.bind(a, b)` — appends `a, b` to the end of the argument list when called.
- `cb.unbind(n)` — drops the last `n` signal arguments. Handy when the handler ignores
  the signal's payload: `sig.connect(_refresh.unbind(sig_arg_count))`.

## Custom signals with typed arguments

```gdscript
signal stat_changed(stat_name: String, old_value: int, new_value: int)

var stats: Dictionary[String, int] = {}

func set_stat(stat: String, value: int) -> void:
    var old: int = stats.get(stat, 0)   # get() returns Variant, so type the variable
    stats[stat] = value
    stat_changed.emit(stat, old, value)
```

Typed parameters are documentation and let the editor's connection dialog show argument
names. `emit()` does not check them against the declaration; a mismatch shows up as an
error when a connected handler is called with the wrong number of arguments.

## Awaiting a signal with a timeout

`await` has no built-in timeout. Race the signal against a timer by having both finish one
helper signal, and await that:

```gdscript
signal _race_finished(signal_won: bool)

## Returns true if `sig` fired within `seconds`, false on timeout.
func await_signal_or_timeout(sig: Signal, seconds: float) -> bool:
    var on_signal := func(..._args: Array) -> void: _race_finished.emit(true)
    var on_timeout := func() -> void: _race_finished.emit(false)
    var timer := get_tree().create_timer(seconds)
    sig.connect(on_signal, CONNECT_ONE_SHOT)
    timer.timeout.connect(on_timeout, CONNECT_ONE_SHOT)
    var won: bool = await _race_finished
    if sig.is_connected(on_signal):          # the loser is still connected
        sig.disconnect(on_signal)
    if timer.timeout.is_connected(on_timeout):
        timer.timeout.disconnect(on_timeout)
    return won

# Usage: if not await await_signal_or_timeout($Door.opened, 2.0): print("door stuck")
```

The `..._args` rest parameter (Godot 4.5+) lets one helper accept signals with any number
of arguments. Run one race at a time per node; two overlapping calls share
`_race_finished`.

For most gameplay, awaiting `animation_finished`, `timeout`, or `tween_finished`
directly is cleaner.

## Disconnecting safely

```gdscript
if sig.is_connected(cb):
    sig.disconnect(cb)
```

A connection is removed automatically when the emitter or the object that owns the
Callable is freed. A **lambda** is owned by the object whose script created it, not by the
nodes it captures: if a captured node is freed, the lambda stays connected and errors
("Lambda capture at index 0 was freed") the next time the signal fires. Each `func():`
expression is also a new Callable, so `is_connected()` cannot spot a repeat and every
re-connect stacks another call. Keep the lambda in a variable so you can disconnect it, or
connect a method on the listener instead.

## Groups: full API

```gdscript
add_to_group("saveable")                       # optional 2nd arg: persistent
remove_from_group("saveable")
is_in_group("saveable")
get_tree().get_nodes_in_group("saveable")      # Array[Node]
get_tree().get_first_node_in_group("player")   # first match or null
get_tree().call_group("enemies", "method", arg)
get_tree().set_group("enemies", "modulate", Color.RED)  # set a property on all
```

`call_group` has flag variants (`call_group_flags`) for deferred/unique-only calls.

## Signals vs direct calls — when to use which

- **Signal** when the emitter should not know or care who listens (reusable scenes,
  one-to-many, decoupling UI from logic).
- **Direct call** when there is a clear owner→owned relationship and coupling is fine
  (a controller calling a method on a component it created). Over-using signals for
  tightly coupled code adds indirection without benefit.

## Global event bus (autoload)

For events that cross scenes, declare signals on an autoload and have any scene emit or
connect:

```gdscript
# Events.gd (autoload). Emit: Events.player_died.emit(). Listen: Events.player_died.connect(...)
extends Node
signal player_died
signal level_completed(level_id: int)
```
