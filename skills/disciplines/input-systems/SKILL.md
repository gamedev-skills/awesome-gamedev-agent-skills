---
name: input-systems
description: >
  Engine-neutral input architecture with Godot InputMap code: named actions, stick deadzones,
  buffered presses and rebinding with conflict checks. Use for controller support or a rebind
  menu, or a drifting stick, WASD on AZERTY, or a dropped press. Not for coyote time
  (`platformer`) or Unity and Unreal input assets (`unity-input-system`, `unreal-enhanced-input`).
---

# Input systems

Gameplay reads named **actions** (`jump`, `attack`, `move`); bindings from keys, buttons and
touch to those actions are data. Rebinding, multi-device support and most input accessibility
fall out of that one indirection. This skill is the engine-neutral architecture with Godot 4.7
code. For the engine's own input assets use `unity-input-system` or `unreal-enhanced-input`;
Godot's `InputMap` is covered here.

## When to use

- Designing an input layer: actions, per-device bindings, device detection and prompts.
- Stick handling: deadzones, response curves, sensitivity.
- Buffering discrete presses (attack during recovery, dodge, combo links, menu confirm).
- A rebinding screen with conflict handling, saved bindings and reset to defaults.
- Accessible controls: full remap, toggle vs hold, no required chords, adjustable windows.

**Not this skill:** coyote time, jump buffering and variable jump height belong to
`platformer`, which owns the jump controller. Hit-stop and other juice that interact with
buffers are `game-feel`. Writing the bindings file is `save-systems`. Menu focus and
navigation rules are `game-ui-ux`.

## Core workflow

1. **Inventory before editing.** List the existing actions (Godot: the `[input]` section of
   `project.godot`; Unity: the `.inputactions` file; Unreal: `IA_`/`IMC_` assets) and grep
   gameplay code for raw key reads (`is_key_pressed`, `KEY_`, `Input.GetKey`). Raw reads are
   the first thing to replace.
2. **Name actions by intent**, not by key, and give each one a keyboard and a gamepad binding.
   Touch routes through the same actions.
3. **Match the read to the action.** Edge (pressed this frame or tick) for discrete actions,
   held or axis for continuous ones.
4. **Filter analog input** with a radial deadzone and a separate response curve.
5. **Buffer discrete presses** that arrive a little before they are legal, measured in game
   time and consumed when they fire.
6. **Rebinding:** capture the next input, bind the physical key, reject or swap conflicts,
   save, and offer reset to defaults. Keep a way back to the pause menu that cannot be unbound.
7. **Check it yourself, then ask for the device test** (see "Check it" below).

## Patterns

### 1. Actions over raw keys; edge vs held

```gdscript
if Input.is_action_just_pressed("jump"):      # edge: true on the press frame or tick only
    try_jump()
var dir := Input.get_vector("move_left", "move_right", "move_up", "move_down")
# get_vector applies a radial deadzone, rescales past it and caps length at 1,
# so diagonals are not faster. Use get_axis for a single axis.
# WRONG: Input.is_key_pressed(KEY_SPACE): unrebindable, keyboard-only, and a held
# check, so jump re-fires every frame.
```

Engine equivalents: Unity Input System `InputAction` and action maps; Unreal Enhanced Input
Actions plus Mapping Contexts.

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

Keep the response curve (exponent) separate from sensitivity (a gain on the result, usually a
camera turn rate) and expose both in settings. Invalid settings report an error and return zero
movement. Godot's `get_vector` already does this deadzone and rescale, using the average of the
four actions' deadzones (0.2 per action by default) unless you pass one.

### 3. Action buffer for discrete presses

```gdscript
# action_buffer.gd: remember discrete presses briefly so an early press still fires.
extends RefCounted

var window := 0.15                        # seconds; 0.1-0.2 suits attacks and dodges
var _pressed_at := {}                     # action -> game time of its latest press

func press(action: StringName, now: float) -> void:
    _pressed_at[action] = now

func consume(action: StringName, now: float) -> bool:
    if not _pressed_at.has(action) or now - _pressed_at[action] > window:
        return false
    _pressed_at.erase(action)             # one press fires one action
    return true

func clear() -> void:                     # on death, pause, cutscene, scene change
    _pressed_at.clear()
```

Feed it from the input read (`if Input.is_action_just_pressed("attack"): buffer.press(&"attack",
clock)`) and call `consume` where the action becomes legal, such as the first frame after attack
recovery. `clock` is game time you advance in `_physics_process`, so the window freezes during
pause and hit-stop. When two buffered actions become legal on the same tick, choose by a fixed
priority, not by dictionary order. Jump buffering and coyote time use the same idea but belong to
`platformer`.

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
```

Keyboard bindings use `physical_keycode` with `keycode` left at 0, which makes Godot match by key
position, so WASD stays in place on AZERTY or Dvorak. Show the player's own label with
`DisplayServer.keyboard_get_label_from_physical`. Reset to defaults with
`InputMap.load_from_project_settings()`. Unity: `PerformInteractiveRebinding()` and
`SaveBindingOverridesAsJson()`/`LoadBindingOverridesFromJson()`. Unreal: Enhanced Input User
Settings with player-mappable keys.

### 5. Binding audit (headless, exits 1 on problems)

```gdscript
# tools/audit_bindings.gd: godot --headless --path . --script res://tools/audit_bindings.gd
extends SceneTree

const KEYBOARD_ONLY := [&"toggle_console"]   # actions allowed to have no gamepad binding

func _initialize() -> void:
    var problems := PackedStringArray()
    var actions := InputMap.get_actions().filter(func(a): return not String(a).begins_with("ui_"))
    for i in actions.size():
        var action: StringName = actions[i]
        var events := InputMap.action_get_events(action)
        if not events.any(func(e): return e is InputEventKey or e is InputEventMouseButton):
            problems.append("%s: no keyboard or mouse binding" % action)
        if action not in KEYBOARD_ONLY and not events.any(
                func(e): return e is InputEventJoypadButton or e is InputEventJoypadMotion):
            problems.append("%s: no gamepad binding" % action)
        for other in actions.slice(i + 1):
            for e in events:
                for o in InputMap.action_get_events(other):
                    if e.is_match(o, true):       # exact: axis direction and modifiers count
                        problems.append("%s and %s share %s" % [action, other, e.as_text()])
    for p in problems:
        printerr("BINDING: ", p)
    print("Checked %d actions, %d problems" % [actions.size(), problems.size()])
    quit(1 if problems.size() > 0 else 0)
```

It reads the project's `[input]` section. Exact matching matters: with the default loose match,
`move_left` and `move_right` on the two directions of one stick axis would count as a conflict.
Two actions that are never active at the same time (a menu action and a gameplay action) may
share a key; list such pairs instead of deleting the check.

## Check it

1. Run the binding audit and fix every line it prints. In Unity or Unreal, do the same review on
   the `.inputactions` JSON or by listing mapping-context keys.
2. Unit-test the pure parts headless with fixed inputs: deadzone outputs at 0, at the deadzone
   edge and on a diagonal; a buffered press fires once and expires after the window. Follow
   `godot-gdscript-headless-testing` for the runner and exit codes.
3. Grep gameplay code for raw key reads again; the count should be zero outside debug tools.
4. Ask the user to plug in a gamepad, rebind one action to a face button, restart the game and
   report whether the new binding still works, whether prompts switch between keyboard and pad
   glyphs, and whether a second pad can use the rebound button. You cannot press buttons
   yourself, so do not report device behaviour you have not had confirmed.

## Gotchas

- **Edge vs held confusion.** A held check for jump re-fires every frame; an edge check for
  movement drops held input.
- **Per-axis deadzones** clip diagonals and snap movement to the axes. Use a radial deadzone.
- **A buffered press fires twice** because `consume` never clears it, or it fires after a
  respawn because nothing calls `clear()`.
- **A buffer that expires during hit-stop or pause** is counting wall-clock time
  (`Time.get_ticks_msec`). Use game time from the physics step.
- **Rebinding without conflict handling** lets two actions share a key, or strands the player
  by unbinding the menu. Detect conflicts and keep an unbindable way back.
- **WASD in the wrong place on AZERTY or QWERTZ**: bindings stored by key letter follow the
  layout. Store physical positions and show the layout's label.
- **A rebound gamepad button works only for player 1**: the captured event kept pad 0's device
  ID. Store bindings for all devices (Godot `device = -1`) unless pads are assigned on purpose.
- **Comparing InputEvents with `==`** is always false for two separate objects. Use
  `action_has_event` or `is_match`.
- **"Press Space" shown to a gamepad player.** Track the last device that sent input and swap
  glyphs on every change, without a restart.
- **Steam Input reports every pad as Xbox** when it is on for that controller, so name and ID
  checks pick the wrong glyphs. Ask Steam for the real type (details in the reference).
- **Hold-only actions, required chords and fixed sensitivity** block some players. Offer
  toggle vs hold, single-input alternatives and sensitivity settings.

## References

- `references/buffering-and-accessibility.md`: read when tuning buffer windows, choosing button
  glyphs per controller family (SDL3 positions, Steam Input), building touch controls, or
  reviewing an accessibility checklist for controls.

## Related skills

- `platformer`: coyote time, jump buffering, variable jump height and jump feel.
- `unity-input-system`, `unreal-enhanced-input`: engine input assets and APIs.
- `save-systems`: persisting bindings and input settings.
- `game-ui-ux`: menu focus and navigation; `camera-systems`: look sensitivity and invert.

## Version notes

Last verified: 2026-11-11.

- Godot 4.7: `Input.is_action_just_pressed` is true on the frame or physics tick of the press;
  `InputEvent.is_match(event, exact_match = true)`; `get_joy_info()` fills `raw_name`,
  `vendor_id` and `product_id` on Windows, Linux, macOS and iOS, and `steam_input_index` on
  desktop only (https://github.com/godotengine/godot/blob/4.7-stable/doc/classes/Input.xml).
- The binding audit and action buffer above were run on Godot 4.7.2 headless.
