---
name: input-systems
description: >
  Architect game input — action mapping (abstracting keys into named actions),
  rebinding with conflict detection and persistence, multi-device support
  (keyboard, gamepad, touch), analog deadzones, and feel features like input
  buffering and coyote time, plus accessibility. Engine-neutral. Use when the
  user mentions input mapping, rebind controls, gamepad support, deadzone, input
  buffering, coyote time, or accessible controls.
---

# Input systems

Never wire gameplay to raw keys. Map physical inputs (a key, a button, a touch)
to named **actions** (`jump`, `interact`, `move`), and let gameplay read actions.
That one indirection gives you rebinding, multi-device support, and accessibility
almost for free. This skill is the engine-neutral architecture; bind it to
`unity-input-system`, `unreal-enhanced-input`, or Godot's `InputMap`.

## When to use

- Use to design an input layer: actions, bindings, multiple devices, and a
  rebinding UI with conflict detection and saved bindings.
- Use to add analog handling (deadzones, sensitivity) and game-feel features
  (input buffering, coyote time).
- Use to make controls accessible (full remapping, hold-vs-toggle, sensitivity,
  no required simultaneous presses).

**When *not* to use:** for an engine's concrete input package/API, use
`unity-input-system`, `unreal-enhanced-input`, or Godot's InputMap. For the
movement/jump *physics* the buffer feeds, see `physics-tuning` and the engine
movement skill. Persisting bindings to disk is `save-systems`.

## Core workflow

1. **Define actions, not keys.** Gameplay asks "is `jump` pressed?", never "is
   Space pressed?". Actions are the stable contract; bindings are data.
2. **Bind per device.** Each action holds bindings for keyboard, gamepad, and
   touch. The active device is whichever last sent input; swap UI prompts to match.
3. **Read the right edge.** Use *pressed-this-frame* (edge) for discrete actions
   (jump, interact) and *held* (level) for continuous ones (move, aim). Confusing
   the two causes double-fires or missed presses.
4. **Filter analog input.** Apply a deadzone to sticks/triggers so resting drift
   reads as zero, and scale sensitivity/curve to taste.
5. **Buffer for feel.** Remember a pressed action for a short window so a slightly
   early press still fires (input buffering); allow a jump shortly after leaving a
   ledge (coyote time).
6. **Make rebinding first-class.** A UI that captures the next input, detects
   conflicts, and persists bindings — and a reset-to-default. Save via
   `save-systems`.
7. **Verify on every device** and with rebinds: keyboard, gamepad, touch; rebind
   an action mid-game and confirm gameplay and prompts follow.

## Patterns

### 1. Actions over raw keys; edge vs held

```gdscript
# Gameplay reads ACTIONS. The mapping from key/button to action lives in data.
# Discrete (edge): fire once on the press frame.
if Input.is_action_just_pressed("jump"):
    try_jump()
# Continuous (held): read every frame as an axis.
var move := Input.get_axis("move_left", "move_right")   # -1..1, one axis
player.velocity.x = move * RUN_SPEED
# Two axes (stick or WASD): get_vector applies a circular deadzone, rescales
# past it and caps the length at 1, so diagonals are not faster.
var dir := Input.get_vector("move_left", "move_right", "move_up", "move_down")
# RIGHT: name actions ("jump"); rebinding/devices just change the binding data.
# WRONG: `if Input.is_key_pressed(KEY_SPACE)` — unrebindable, keyboard-only,
# and `is_key_pressed` is a held check that would re-fire jump every frame.
```

Engine equivalents (Godot 4.7, Unity 6.3 LTS, Unreal 5.8): Godot `InputMap` +
`Input.is_action_just_pressed` (valid in `_process` and `_physics_process`);
Unity Input System `InputAction` / action maps; Unreal Enhanced Input `Input
Actions` + `Input Mapping Contexts`.

### 2. Analog deadzone and sensitivity

```gdscript
# Raw sticks never rest at exactly zero. Apply a RADIAL deadzone (on the vector
# length), not per-axis, so diagonals aren't clipped into the axes.
func apply_deadzone(stick: Vector2, dead := 0.2, curve := 1.0) -> Vector2:
    # dead == 1 cannot be rescaled; report invalid settings before stopping movement.
    if not (dead >= 0.0 and dead < 1.0 and curve > 0.0):
        push_error("apply_deadzone requires 0 <= dead < 1 and curve > 0.")
        return Vector2.ZERO
    var mag := stick.length()
    if mag <= dead:
        return Vector2.ZERO                      # inside deadzone -> no movement
    # Rescale so motion ramps from 0 at the edge of the deadzone, not from `dead`.
    var scaled := minf((mag - dead) / (1.0 - dead), 1.0)  # some pads report > 1 on diagonals
    return stick / mag * pow(scaled, curve)      # curve > 1 = finer aim near center
# WRONG: clamping each axis separately — it carves a square hole and snaps to axes.
```

Keep the response curve (exponent) separate from sensitivity (a plain gain on
the result, usually a camera turn rate) and expose both. Settings require
`0 <= dead < 1` and `curve > 0`; invalid settings report an error and return zero movement.
Godot's `get_vector`
already does the deadzone and rescale above, using the average of the four
actions' deadzones (0.2 by default per action) unless you pass one.

### 3. Input buffering + coyote time (forgiving, responsive feel)

```gdscript
# Buffer: a jump pressed slightly BEFORE landing still triggers on touchdown.
# Coyote: a jump pressed slightly AFTER walking off a ledge still works.
const BUFFER := 0.12   # seconds an early press stays "remembered"
const COYOTE := 0.10   # seconds after leaving ground you can still jump
var _buffer_timer := 0.0
var _coyote_timer := 0.0

func _physics_process(dt):
    _buffer_timer -= dt
    _coyote_timer = COYOTE if is_on_floor() else _coyote_timer - dt
    if Input.is_action_just_pressed("jump"):
        _buffer_timer = BUFFER                  # remember the press
    if _buffer_timer > 0.0 and _coyote_timer > 0.0:
        velocity.y = JUMP_VELOCITY
        _buffer_timer = 0.0; _coyote_timer = 0.0  # consume both so it fires once
```

### 4. Rebinding with conflict detection

```gdscript
# Godot 4.7. Capture the next physical input, reject conflicts, then persist.
var _waiting_for: StringName = &""               # set by the "press a key for Jump" button

func _unhandled_input(event: InputEvent) -> void:
    if _waiting_for != &"" and _is_bindable(event):
        get_viewport().set_input_as_handled()
        if not rebind(_waiting_for, event):
            show_conflict_warning(event)         # offer swap or cancel
        _waiting_for = &""

func _is_bindable(e: InputEvent) -> bool:
    if e is InputEventKey or e is InputEventJoypadButton or e is InputEventMouseButton:
        return e.pressed and not e.is_echo()     # ignore releases and key repeat
    return e is InputEventJoypadMotion and absf(e.axis_value) > 0.5  # ignore stick noise

func rebind(action: StringName, captured: InputEvent) -> bool:
    var event := _to_binding(captured)
    for other in InputMap.get_actions():
        if other != action and not String(other).begins_with("ui_") \
                and InputMap.action_has_event(other, event):
            return false                         # already used -> let UI warn/swap
    for old in InputMap.action_get_events(action):
        if old.get_class() == event.get_class():  # replace only this device kind's binding
            InputMap.action_erase_event(action, old)
    InputMap.action_add_event(action, event)
    save_bindings()                              # persist (see save-systems)
    return true

func _to_binding(e: InputEvent) -> InputEvent:
    if e is InputEventKey:                       # bind the physical key, not the layout's letter
        var k := InputEventKey.new()
        k.physical_keycode = e.physical_keycode
        return k
    var b := e.duplicate() as InputEvent
    b.device = -1                                # all devices: a pad binding must not stick to pad 0
    if b is InputEventJoypadMotion:
        b.axis_value = signf(b.axis_value)       # keep the direction only
    return b
# Compare bindings with action_has_event() / InputEvent.is_match(), never `==`:
# two InputEvents with the same key are different objects, so `==` is false.
# Always provide "reset to defaults" (InputMap.load_from_project_settings()), and
# never let the player unbind a key they need to reach the menu without an alternative.
```

Keyboard bindings use the **physical** key (`physical_keycode`, with `keycode`
left at 0, which is what makes Godot match by position), so WASD stays in the
same place on AZERTY or Dvorak; show the label for the player's layout with
`DisplayServer.keyboard_get_label_from_physical`. Unity Input System `action.PerformInteractiveRebinding()` and
`SaveBindingOverridesAsJson()` / `LoadBindingOverridesFromJson()`; Unreal
Enhanced Input **User Settings** (enable under Project Settings ▸ Enhanced Input)
with player-mappable keys on the mapping context.

## Pitfalls

- **Hardcoding keys** in gameplay blocks rebinding, locks out gamepad/touch, and
  scatters input logic. Read named actions only.
- **Edge vs held confusion**: using a held check for jump re-fires every frame;
  using an edge check for movement drops held input. Match the check to the action.
- **Per-axis deadzones** clip diagonal stick input and snap movement to the axes.
  Use a radial deadzone on the vector magnitude.
- **No buffering/coyote time** makes tight platformers feel unfair even when the
  physics are correct — players "clearly pressed jump". Add small windows.
- **Rebinding without conflict handling** lets two actions share a key, or strands
  the player by unbinding menu access. Detect conflicts; guarantee a way back.
- **WASD lands in the wrong place on AZERTY/QWERTZ**: bindings stored by key
  *letter* follow the layout. Store physical key positions and display the
  layout's label.
- **A rebound gamepad button works only for player 1**: the captured event
  carried pad 0's device ID. Store bindings for all devices (Godot `device = -1`)
  unless the game assigns pads to players on purpose.
- **Not swapping prompts on device change** shows "Press Space" to a gamepad
  player. Track the last-used device and switch glyphs.
- **Ignoring accessibility**: required simultaneous presses, no remap, fixed
  sensitivity, hold-only actions. Offer remap, toggle-vs-hold, and sensitivity.
- **Reading input in the wrong loop**: poll held state in the physics step for
  consistent movement; capture discrete presses so none are missed between frames.

## References

- `references/buffering-and-accessibility.md` — buffering/coyote tuning, jump feel
  (variable height, apex), device detection and prompt swapping, touch controls,
  and an accessibility checklist (remap, toggle/hold, sensitivity, latency).

## Related skills

- `unity-input-system`, `unreal-enhanced-input` — concrete engine input APIs
  (Godot uses `InputMap` + the `Input` singleton).
- `save-systems` — persist custom key bindings and input settings.
- `physics-tuning` — the movement the buffer/coyote windows feed into.
- `platformer`, `fps-shooter` — genres whose feel depends on input handling.
