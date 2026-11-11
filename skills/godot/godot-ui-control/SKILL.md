---
name: godot-ui-control
description: >
  Godot 4.7 Control-node API for menus and HUDs: anchors, Containers, Theme and StyleBox, focus
  neighbours and stretch settings, with a headless layout check. Use when Godot UI overlaps or
  drifts on resize, buttons ignore the gamepad, or an invisible panel swallows clicks. Not for
  engine-neutral UI rules (`game-ui-ux`; load both) or rebinding (`input-systems`).
---

# Godot UI / Control nodes (4.x)

Lay out responsive UI with `Control` anchors and `Container` nodes, style it with a
`Theme`, make it navigable by keyboard and gamepad, and prove the layout holds at more
than one screen size. Targets **Godot 4.7** (see Version notes). Design rules (what a good
HUD or menu needs) live in `game-ui-ux`; load both for engine UI work.

## When to use

- HUDs, menus, inventories, dialog boxes or settings screens built from `Control` nodes;
  UI that must adapt to window size; theming; focus navigation for controller/keyboard.

**When *not* to use:** in-world `Node2D`/sprites → `godot-nodes-scenes`; UI tweens →
`godot-animation`; rebinding → `input-systems`; card hands and VN text boxes →
`card-game` / `visual-novel`.

## Core workflow

1. **Read the stretch settings first.** `project.godot` `[display]` holds
   `window/size/viewport_width`/`viewport_height` (base size, default 1152x648),
   `window/stretch/mode` (`canvas_items` is the usual choice for UI-heavy games) and
   `window/stretch/aspect` (`expand` lets UI use extra width or height). Layout bugs on
   other screens usually start here.
2. **Use `Control` nodes for UI**, not `Node2D`, and put HUDs under a `CanvasLayer` so the
   game camera does not move them.
3. **Anchor top-level panels; let Containers place their children.** Outside containers,
   set anchors with presets (`set_anchors_and_offsets_preset()`). Inside a `VBoxContainer`,
   `HBoxContainer`, `GridContainer` or `MarginContainer`, the container owns position and
   size; steer it with `size_flags_*`. In a `.tscn`, a Full Rect panel reads:

   ```ini
   [node name="PauseMenu" type="Control"]
   anchors_preset = 15
   anchor_right = 1.0
   anchor_bottom = 1.0
   grow_horizontal = 2
   grow_vertical = 2
   ```

   Keep whatever `layout_mode` line Godot wrote; it records whether anchors or a parent
   container drive the node.
4. **Style with one `Theme`.** Set a project-wide theme with `gui/theme/custom="res://ui/theme.tres"`
   in `project.godot`, or assign `theme` on the top Control; children inherit it. Use
   per-node `add_theme_*_override` only for exceptions.
5. **Wire focus.** Give the first button focus when a menu opens (`grab_focus()`), keep
   `focus_mode = FOCUS_ALL` on anything a gamepad must reach, and set
   `focus_neighbor_*` only where the automatic geometry guess is wrong.
6. **Connect signals** (`pressed`, `toggled`, `text_submitted`, `value_changed`).
7. **Check before you finish.**
   - Run the layout test (Pattern 4) headless:
     `godot --headless --path . --script res://tests/test_ui_layout.gd` and read the exit
     code. It flags controls pushed off-screen and menus with nothing focused, at each size.
   - Run the `godot-nodes-scenes` skill's `scripts/check_godot_project.py <project-dir>` if you edited
     `.tscn`/`.tres` files (themes, StyleBoxes, fonts).
   - For a picture, on a machine with a GPU (not `--headless`), capture frames and look
     at them: `godot --path . --resolution 2560x1080 --write-movie $OUT/menu.png --quit-after 3 --scene res://ui/main_menu.tscn`
     writes numbered PNGs next to that path. Repeat at 1280x720.
   - With no Godot binary (`godot`, `godot4` or `$GODOT_BIN`), ask the user to run these
     and paste the output or screenshots. Ask the user to try the menu with a gamepad
     and report any button that cannot be reached.

## Patterns

### 1. Full Rect from code (anchors *and* offsets)

```gdscript
extends Control

func _ready() -> void:
    # Setting only anchors (or `anchors_preset`) keeps the old offsets, so the rect
    # would not snap to the preset. This moves anchors AND resets offsets.
    set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
```

### 2. A menu from containers, with initial focus

```gdscript
extends VBoxContainer    # children stack vertically, auto-sized

func _ready() -> void:
    for child in get_children():
        if child is Button:
            child.pressed.connect(_on_button_pressed.bind(child.name))
    # Give the first button focus so a gamepad can navigate immediately.
    if get_child_count() > 0:
        (get_child(0) as Control).grab_focus()

func _on_button_pressed(which: StringName) -> void:
    match which:
        "PlayButton":  get_tree().change_scene_to_file("res://game.tscn")
        "QuitButton":  get_tree().quit()
```

### 3. One child takes the leftover space

```gdscript
func _ready() -> void:
    $Label.size_flags_horizontal = Control.SIZE_SHRINK_BEGIN
    $Spacer.size_flags_horizontal = Control.SIZE_EXPAND_FILL   # grows to fill
```

### 4. Headless layout test at several sizes

```gdscript
# res://tests/test_ui_layout.gd
extends SceneTree

# The sizes the UI really gets. With stretch mode canvas_items and aspect "expand",
# a 2560x1080 window on a 1152x648 base gives the UI 1536x648, not 2560x1080.
const SIZES: Array[Vector2i] = [Vector2i(1152, 648), Vector2i(1536, 648), Vector2i(1152, 864)]

func _initialize() -> void:
    var failed := 0
    for size in SIZES:
        var vp := SubViewport.new()
        vp.size = size
        root.add_child(vp)
        var ui: Control = load("res://ui/main_menu.tscn").instantiate()
        vp.add_child(ui)
        await process_frame
        await process_frame                      # containers re-sort a frame later
        var screen := Rect2(Vector2.ZERO, Vector2(size))
        for node in ui.find_children("*", "Control", true, false):
            var c := node as Control
            if c.is_visible_in_tree() and not screen.encloses(c.get_global_rect()):
                failed += 1
                push_error("%s off-screen at %s: %s" % [ui.get_path_to(c), size, c.get_global_rect()])
        if vp.gui_get_focus_owner() == null:
            failed += 1
            push_error("nothing has focus at %s, so a gamepad cannot navigate" % size)
        vp.free()
    print("Results: %d failed" % failed)
    quit(1 if failed > 0 else 0)
```

Children of a `ScrollContainer` are meant to extend past it; skip them (or check only the
container) when the menu scrolls.

## Gotchas

- **Mixing manual position with Containers.** A container child cannot keep its own
  position or anchors; the container overwrites them on every sort. To nudge, rotate or
  scale one (a hover pop), set `offset_transform_enabled = true` and use
  `offset_transform_position`/`_rotation`/`_scale`, which the container leaves alone.
- **Anchors vs offsets.** Anchors are fractions of the parent; offsets are pixels from the
  anchored point. Positioning with anchors at 0 makes UI ignore window size.
- **UI under a `Node2D`** doesn't theme, anchor or take focus correctly. Keep UI in a
  `Control` subtree, under a `CanvasLayer` for HUDs.
- **Gamepad does nothing** → nothing has focus. Call `grab_focus()` when the screen opens;
  plain `Control`s default to `FOCUS_NONE`, `FOCUS_CLICK` is mouse-only, and
  `grab_focus()` on a `FOCUS_NONE` control only prints a warning.
- **Invisible full-rect panel swallows clicks** → its `mouse_filter` is `STOP`. Set
  `MOUSE_FILTER_IGNORE` on decorative panels and HUD roots.
- **Looks right in the editor, cramped or off-screen on ultrawide or 4:3** → stretch
  `aspect` is `keep` (black bars) or the panel is anchored to a corner instead of the
  edge it should follow. Test the sizes the UI actually gets (Pattern 4).
- **Theme vs override.** Per-node `add_theme_*_override` calls beat the inherited `Theme`;
  many of them defeat central theming and make restyling slow.
- **`rect_*` properties are renamed.** Godot 3's `rect_size`/`rect_position`/`rect_min_size`
  are now `size`/`position`/`custom_minimum_size`.

## References

- Read `references/layout-and-theming.md` when you need the anchor/offset maths, every
  Container type, size-flag values, building a Theme and StyleBox in code, focus neighbour
  wiring, offset transforms, the built-in `VirtualJoystick`, or common Control signals.

## Related skills

- `game-ui-ux` for engine-neutral rules: scaling, safe areas, focus flow, screen stack.
- `godot-animation` for Tween-based UI transitions.
- `godot-signals-groups` for wiring UI events to game logic.
- `input-systems` for rebindable input and multi-device focus.
- `card-game` / `visual-novel` for UI-heavy genre templates.

## Version notes

Last verified: 2026-11-11 against Godot 4.7.2-stable (released 2026-08-18).

- `Control.offset_transform_*` and the `VirtualJoystick` node are new in 4.7.
- Default base size is 1152x648 and default stretch mode is `disabled`, aspect `keep`.
- `--write-movie` with a `.png` path writes an image sequence; `--resolution` requests the
  window size.

Sources: [Control @ 4.7.2-stable](https://github.com/godotengine/godot/blob/4.7.2-stable/doc/classes/Control.xml),
[ProjectSettings @ 4.7.2-stable](https://github.com/godotengine/godot/blob/4.7.2-stable/doc/classes/ProjectSettings.xml),
[main.cpp @ 4.7.2-stable](https://github.com/godotengine/godot/blob/4.7.2-stable/main/main.cpp),
[Multiple resolutions](https://docs.godotengine.org/en/stable/tutorials/rendering/multiple_resolutions.html),
[Godot 4.7 release](https://godotengine.org/releases/4.7).
