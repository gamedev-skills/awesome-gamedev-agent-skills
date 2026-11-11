# Control layout & theming reference (Godot 4.7)

Depth companion to `godot-ui-control`.

Contents: anchors and offsets · container types · size flags · Theme and StyleBox ·
focus navigation · offset transforms (4.7+) · touch joystick (4.7+) · HUDs over the game ·
common signals

## Anchors and offsets

A `Control` has four anchors (`anchor_left/top/right/bottom`), each a fraction `0.0–1.0`
of the parent's rect, and four offsets (`offset_left/top/right/bottom`) in pixels from the
anchored point.

- Anchors at `(0,0,0,0)` → the control's edges all track the parent's top-left; size is
  driven entirely by offsets (fixed pixel size, top-left aligned).
- Anchors at `(0,0,1,1)` (Full Rect) → edges track each corner; the control resizes with
  the parent. Offsets become margins.
- Center presets set anchors to `0.5` and use offsets relative to the center.

Use the editor's Layout toolbar, or in code
`set_anchors_and_offsets_preset(Control.PRESET_*)` (CENTER, FULL_RECT, TOP_WIDE,
BOTTOM_RIGHT, ...), which sets anchors and offsets together. Assigning `anchor_*` or
`anchors_preset` alone keeps the existing offsets, so the rect does not snap to the preset.

## Container types

| Container | Arranges children |
|-----------|-------------------|
| `VBoxContainer` / `HBoxContainer` | Stacked vertically / horizontally |
| `GridContainer` | Grid with `columns` |
| `MarginContainer` | Adds margins (theme constants `margin_*`) |
| `CenterContainer` | Centers a single child at its min size |
| `PanelContainer` | Draws a panel stylebox behind one child |
| `ScrollContainer` | Scrolls oversized content |
| `TabContainer` | Tabbed pages |
| `AspectRatioContainer` | Keeps child aspect ratio |
| `SplitContainer` (H/V) | Draggable splitter between two children |
| `FlowContainer` (H/V) | Wraps children like text |

Containers ignore child anchors/positions and instead use **size flags**.

## Size flags

```gdscript
size_flags_horizontal / size_flags_vertical:
  SIZE_FILL            # fill assigned space
  SIZE_EXPAND          # claim extra space (combine with FILL: SIZE_EXPAND_FILL)
  SIZE_SHRINK_BEGIN    # shrink to min, align to start
  SIZE_SHRINK_CENTER   # shrink to min, centered
  SIZE_SHRINK_END      # shrink to min, align to end
size_flags_stretch_ratio = 2.0   # relative share of expand space among siblings
```

## Theme and StyleBox

A `Theme` resource maps (control type, property name) → value. Property kinds: `color`,
`constant`, `font`, `font_size`, `icon`, `stylebox`.

```gdscript
var theme := Theme.new()
theme.set_color("font_color", "Button", Color.WHITE)
theme.set_font_size("font_size", "Button", 18)
var sb := StyleBoxFlat.new()
sb.bg_color = Color(0.1, 0.1, 0.15)
sb.set_corner_radius_all(8)
sb.set_content_margin_all(12)
theme.set_stylebox("normal", "Button", sb)
control.theme = theme        # inherited by the whole subtree
```

Per-node overrides (win over the inherited Theme):

```gdscript
add_theme_color_override("font_color", Color.RED)
add_theme_font_size_override("font_size", 24)
add_theme_stylebox_override("panel", my_stylebox)
add_theme_constant_override("separation", 16)   # e.g. VBox spacing
remove_theme_color_override("font_color")
```

`StyleBoxFlat` (solid color, borders, corners, shadows), `StyleBoxTexture` (9-patch
texture), and `StyleBoxEmpty` cover most needs.

## Focus navigation (keyboard / gamepad)

```gdscript
control.focus_mode = Control.FOCUS_ALL        # also FOCUS_NONE, FOCUS_CLICK (mouse only),
                                              # FOCUS_ACCESSIBILITY (screen readers only)
control.grab_focus()
# Explicit neighbors (NodePaths) override automatic geometry-based neighbor finding:
control.focus_neighbor_bottom = next_button.get_path()
control.focus_next = other.get_path()         # Tab order
```

The default UI input actions (`ui_up/down/left/right/accept/cancel/focus_next`) drive
focus movement; they map to arrow keys, Enter, and the gamepad D-pad/face buttons out of
the box.

## Offset transforms (4.7+)

Containers overwrite their children's `position`, `rotation` and `scale` on every re-sort.
For animation inside a container, enable `offset_transform_enabled` and tween
`offset_transform_position` / `_rotation` / `_scale` (pivot: `offset_transform_pivot_ratio`,
centre by default). With `offset_transform_visual_only = true` (default) input still hits
the untransformed rect.

## Touch joystick (4.7+)

`VirtualJoystick` is a built-in `Control` for touchscreens. Set `joystick_mode`
(`JOYSTICK_FIXED`, `JOYSTICK_DYNAMIC`, `JOYSTICK_FOLLOWING`) and the `action_left/right/up/down`
input actions it presses, then read movement with `Input.get_vector()` as for a gamepad.

## HUDs over the game

Put HUD UI under a `CanvasLayer` so it renders on top of and independent from the moving
game camera. A `Control` set to Full Rect inside the CanvasLayer fills the viewport
regardless of world scrolling.

## Common signals

- `Button.pressed`, `Button.toggled(toggled_on)`, `Button.button_down/up`.
- `LineEdit.text_submitted(text)`, `text_changed(text)`.
- `Slider/SpinBox.value_changed(value)`.
- `ItemList.item_selected(index)`, `OptionButton.item_selected(index)`.
- `Control.gui_input(event)` for custom click/drag handling.
