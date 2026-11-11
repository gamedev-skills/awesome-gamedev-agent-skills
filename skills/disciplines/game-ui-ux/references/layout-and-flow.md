# Layout, scaling and flow

Contents:
1. Scaling modes per engine
2. Safe-area maths
3. Focus navigation (full pattern, modal focus trap)
4. Screen/menu stack
5. Diegetic vs non-diegetic UI
6. Accessibility
7. Localization-ready layout

Snippets target Godot 4.7 and Unity 6.3 LTS.

## 1. Scaling modes per engine

**Godot 4.7** (Project Settings → Display → Window → Stretch):

| Setting | Choose | Effect |
|---------|--------|--------|
| Mode | `canvas_items` | UI scales with the window (vs `viewport` = pixel-exact, `disabled` = none) |
| Aspect | `expand` | shows more world/UI space on odd ratios; `keep` letterboxes |
| Scale | `1.0`+ | global UI multiplier |
| Scale Mode | `fractional` / `integer` | `integer` keeps pixel-art UI crisp by scaling in whole steps |

Anchor HUD corners so `expand` puts the extra space where you want it. `keep_width`/`keep_height`
pin one axis for hard 16:9 designs.

**Unity 6.3 LTS** (`CanvasScaler` on each Canvas):

- `UI Scale Mode = Scale With Screen Size`.
- `Reference Resolution = 1920×1080` (or your art's design size).
- `Screen Match Mode = Match Width Or Height`, `Match = 0.5` (blend). Use `1.0` if vertical
  layout must never clip, `0.0` if horizontal must not.
- `Reference Pixels Per Unit = 100` for sprite-based UI.

## 2. Safe-area math

The OS reports a safe rectangle inside the screen (excludes notch, rounded corners, and — on TVs
— overscan margins). Inset only **critical** UI (health, timers, prompts); decorative art can
bleed to the edge.

```text
# Normalized anchors from a pixel safe rect (engine-neutral):
anchorMin = (safe.x / screenW,                 safe.y / screenH)
anchorMax = ((safe.x + safe.w) / screenW,       (safe.y + safe.h) / screenH)
# Re-apply on resolution change / orientation change, not once at startup.
```

- **Godot:** `DisplayServer.get_display_safe_area()` → `Rect2i` in pixels; reapply on
  `size_changed`.
- **Unity:** `Screen.safeArea` → `Rect` in pixels; recompute when `Screen.width/height` or
  `Screen.orientation` changes (cache the last applied rect to avoid per-frame work).

## 3. Focus navigation (full pattern)

Requirements for controller/keyboard usability:

1. **Initial focus** on every screen open (`grab_focus()` / `EventSystem.SetSelectedGameObject`).
2. **Explicit neighbors** for predictable movement (Godot `focus_neighbor_*`; Unity `Navigation`
   = Explicit with up/down/left/right, or Automatic for simple grids).
3. **Visible focus style** distinct from hover (theme focus stylebox / Unity Selectable
   transition). Never rely on color alone (see accessibility).
4. **Wrap or stop** intentionally at list ends; trap focus inside modal dialogs.
5. **Device coexistence:** moving the mouse can update selection; a gamepad press acts on the
   focused control. Don't clear focus when the mouse moves.

```gdscript
# Godot 4.7: trap focus inside a modal so the stick can't escape to the menu behind it.
var _prev_focus: Control

func open_modal() -> void:
    _prev_focus = get_viewport().gui_get_focus_owner()
    $Menu.focus_behavior_recursive = Control.FOCUS_BEHAVIOR_DISABLED   # Godot 4.5+
    $Menu.mouse_behavior_recursive = Control.MOUSE_BEHAVIOR_DISABLED
    $Modal.show()
    $Modal/OK.grab_focus()

func close_modal() -> void:
    $Modal.hide()
    $Menu.focus_behavior_recursive = Control.FOCUS_BEHAVIOR_INHERITED
    $Menu.mouse_behavior_recursive = Control.MOUSE_BEHAVIOR_INHERITED
    if is_instance_valid(_prev_focus): _prev_focus.grab_focus()
```

Showing the modal and focusing its button is not a trap on its own: Godot's neighbor search
still reaches visible controls behind it. The two `*_behavior_recursive` switches turn a whole
subtree off without touching each button.

## 4. Screen/menu stack

Model screens as a stack of UI states; the top owns input and is visible. Push for overlays,
pop for "back". This generalizes pause, settings-over-pause, and confirm dialogs.

```gdscript
# Godot 4.7 sketch: screens are Controls under one CanvasLayer; only the top one is interactive.
# Each screen scene marks its default control with the unique name %DefaultFocus.
var _stack: Array[Control] = []

func push(screen: Control) -> void:
    if not _stack.is_empty():
        _set_interactive(_stack.back(), false)
    _stack.append(screen)
    add_child(screen)
    screen.get_node("%DefaultFocus").grab_focus()

func pop() -> void:
    var top: Control = _stack.pop_back()
    top.queue_free()
    if not _stack.is_empty():
        var below: Control = _stack.back()
        _set_interactive(below, true)
        below.get_node("%DefaultFocus").grab_focus()

func _set_interactive(screen: Control, on: bool) -> void:
    # Godot 4.5+. set_process_input(false) would not do this: buttons get GUI input, not _input.
    screen.focus_behavior_recursive = Control.FOCUS_BEHAVIOR_INHERITED if on else Control.FOCUS_BEHAVIOR_DISABLED
    screen.mouse_behavior_recursive = Control.MOUSE_BEHAVIOR_INHERITED if on else Control.MOUSE_BEHAVIOR_DISABLED
# Pause overlay: get_tree().paused = true and set the overlay's process_mode = PROCESS_MODE_ALWAYS.
```

## 5. Diegetic vs non-diegetic UI

- **Non-diegetic:** drawn on the screen plane, outside the fiction (most HUDs). Cheapest, clearest.
- **Diegetic:** UI that exists in the world (ammo counter on the gun, health on the suit). More
  immersive, more work, can hurt readability. Use for key elements, keep a non-diegetic fallback.
- **Spatial/world-space:** floating health bars, damage numbers — anchor to world position,
  clamp to screen edges when off-screen, and scale with distance (3D).

## 6. Accessibility (bake in, don't bolt on)

- **Text size option** and never hardcode tiny fonts; size to a percentage of reference height.
  Xbox Accessibility Guideline 101 floors: 26 px at 1080p (52 px at 4K) on console/TV, 18 px at
  1080p on PC, and player scaling up to 200% without clipping or lost meaning.
- **Contrast & color independence:** text that carries gameplay information needs at least
  4.5:1 contrast with its background, large text and key visual elements at least 3:1 (Xbox
  Accessibility Guideline 102). Don't encode state in color alone — add icon/shape/text.
  Provide colorblind-safe palettes.
- **Scalable hit targets** for touch (≥ ~9 mm); padding around small buttons.
- **Reduce-motion / reduce-flashing** toggles (coordinate with `game-feel`).
- **Full keyboard + gamepad** reachability (section 3); don't gate actions behind mouse-only.

## 7. Localization-ready layout

- Externalize strings (Godot `tr()` + translation CSV/PO; Unity Localization package). Never bake
  display text into layout logic.
- Let containers **size to content** so longer translations (German is ~30% longer) don't clip.
  Avoid fixed-width buttons sized to English.
- Leave room for RTL mirroring and different number/date formats.
- Keep icons separate from text so only strings need translating.

## Primary sources

- [Godot 4.7: Multiple resolutions](https://docs.godotengine.org/en/4.7/tutorials/rendering/multiple_resolutions.html)
- [Unity Input System: UI support](https://docs.unity3d.com/Packages/com.unity.inputsystem@1.19/manual/UISupport.html)
- [Xbox Accessibility Guideline 101: Text display](https://learn.microsoft.com/en-us/xbox/accessibility/xbox-accessibility-guidelines/101)
- [Xbox Accessibility Guideline 102: Contrast](https://learn.microsoft.com/en-us/xbox/accessibility/xbox-accessibility-guidelines/102)
- [Game Accessibility Guidelines](https://gameaccessibilityguidelines.com/)
