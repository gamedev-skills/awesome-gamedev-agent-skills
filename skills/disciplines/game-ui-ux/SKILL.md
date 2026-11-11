---
name: game-ui-ux
description: >
  Design and build game UI/UX — HUDs, menus, and overlays — that survive every screen: anchor-
  based responsive layout, resolution/aspect scaling and safe areas, keyboard/gamepad focus
  navigation, a screen/menu state stack, and event-driven (not polled) HUD updates. Engine-
  neutral patterns that pair with the detected engine's UI skill. Use when the user mentions
  HUD, health bar, main menu, pause menu, settings screen, UI layout, anchors, UI scaling,
  aspect ratio, safe area, controller/keyboard menu navigation, or wiring UI to game state.
---

# Game UI/UX

Build HUDs and menus that stay correct on a phone, an ultrawide monitor, and a TV across a
gamepad and a mouse. This skill owns the engine-neutral UI architecture — responsive layout,
scaling, focus navigation, screen flow, and how UI talks to game state — and defers the
concrete widget API to the engine UI skill.

## When to use

- Use when building a HUD (health/ammo/score), a menu (main/pause/settings), an inventory or
  shop screen, or any overlay, and you want it to scale and navigate correctly.
- Use to fix UI that breaks at other resolutions/aspect ratios, ignores notches/safe areas,
  can't be used with a controller, or is wired to game state by per-frame polling.
- Use to structure screen flow (title → game → pause → settings) as a stack, not flag soup.

**When *not* to use:** for the engine's concrete UI nodes/components and styling, use
`godot-ui-control` or Unity UI (UGUI/UI Toolkit). For *visual* punch (button pop, damage
numbers, shake) use `game-feel`. For branching conversation UI use `dialogue-systems`. For
translating UI strings, that is localization (see `references/` and `input-systems` for
rebinding screens). For card/board layout specifics, the `card-game` genre composes this skill.

## Core workflow

1. **Pick a layout model: anchors + containers, never absolute pixels.** Anchor elements to
   edges/corners/center and let containers (rows, columns, grids) flow children. Absolute
   `(x, y)` positions break at the first new resolution.
2. **Choose a scaling strategy** for the whole UI: a reference resolution that scales to fit
   (most games), plus a policy for extra width/height on other aspect ratios (letterbox,
   expand, or anchor HUD corners outward).
3. **Respect the safe area.** Inset critical UI from screen edges so notches, rounded corners,
   and TV overscan don't clip it.
4. **Make every screen keyboard/gamepad navigable.** Set an initial focused control per screen,
   define focus order/neighbors, and show a clear focus highlight. Mouse and focus must coexist.
5. **Model screens as a stack.** Push (pause over game), pop (resume), with input + visibility
   handed to the top screen. This makes overlays and "back" trivial.
6. **Drive the HUD from events, not polling.** The HUD subscribes to `health_changed`,
   `score_changed`, etc. and updates only when they fire — it does not read game state every
   frame.
7. **Verify across screens and devices.** Resize the window, switch aspect ratios, unplug the
   mouse and navigate by gamepad only, and confirm focus, scaling, and safe-area insets. Report
   what you actually observed at which resolutions.

## Patterns

### 1. Anchors + containers, not absolute coordinates

```gdscript
# Godot 4.7. Anchor a HUD label to the TOP-LEFT; let a container flow a row of hearts.
func _ready() -> void:
    $Score.set_anchors_preset(Control.PRESET_TOP_LEFT)   # sticks to the corner at any size
    # An HBoxContainer auto-lays-out children left-to-right; never position hearts by hand.
    for i in lives:
        $Hearts.add_child(make_heart())                   # HBoxContainer spaces them for you
# Unity 6.3 LTS uGUI: set RectTransform anchors to the corner; use a HorizontalLayoutGroup.
# RIGHT: anchors + layout groups. WRONG: rect.anchoredPosition = new Vector2(640, 360) (1080p-only).
```

### 2. Scale to a reference resolution (one UI, many screens)

```text
# Godot 4.7 — Project Settings > Display > Window > Stretch:
#   Mode = "canvas_items", Aspect = "expand", reference size e.g. 1920x1080.
#   UI scales to the window; "expand" reveals extra space you anchor HUD corners into.
# Unity 6.3 LTS — Canvas > CanvasScaler:
#   UI Scale Mode = "Scale With Screen Size", Reference Resolution = 1920x1080,
#   Match = 0.5 (blend width/height) — pick 1.0 if your HUD is height-critical.
# Unity 6.3 LTS — UI Toolkit: the same three settings live on the PanelSettings asset
#   (Scale Mode = Scale With Screen Size, Reference Resolution, Screen Match Mode/Match).
```

### 3. Safe-area inset for notches / overscan

```gdscript
# Godot 4.7. Inset a MarginContainer to the OS safe rect. Only Android and iOS report a real
# safe area; elsewhere Godot returns the screen's usable rect, so desktop margins are ~0.
func _apply_safe_area() -> void:
    var safe := Rect2(DisplayServer.get_display_safe_area())           # screen pixels
    var win := Rect2(Rect2i(DisplayServer.window_get_position(), DisplayServer.window_get_size()))
    var inner := safe.intersection(win)
    var to_ui := get_viewport_rect().size / win.size    # window pixels -> UI units under stretch
    $Margin.add_theme_constant_override("margin_left", int((inner.position.x - win.position.x) * to_ui.x))
    $Margin.add_theme_constant_override("margin_top", int((inner.position.y - win.position.y) * to_ui.y))
    $Margin.add_theme_constant_override("margin_right", int((win.end.x - inner.end.x) * to_ui.x))
    $Margin.add_theme_constant_override("margin_bottom", int((win.end.y - inner.end.y) * to_ui.y))
# Unity 6.3 LTS: read Screen.safeArea (Rect in pixels) and set a panel's anchorMin/anchorMax to
# safeArea.position / (position+size) normalized by Screen.width/height.
```

### 4. Gamepad/keyboard focus (UI is unusable on a controller without it)

```gdscript
# Godot 4.7. Give each screen a default focus; Godot guesses neighbors from layout, so set
# them only where its guess is wrong (grids, wrap-around, skipping a disabled row).
func _on_screen_shown() -> void:
    $PlayButton.grab_focus()                               # always focus SOMETHING on open
    $PlayButton.focus_neighbor_bottom = $SettingsButton.get_path()
    $SettingsButton.focus_neighbor_top = $PlayButton.get_path()
# Unity 6.3 LTS uGUI: EventSystem.SetSelectedGameObject(playButton) on enable; set each Selectable's
# Navigation (Explicit or Automatic). With the Input System package, the EventSystem needs an
# InputSystemUIInputModule, not the old StandaloneInputModule. UI Toolkit: call Focus() on the
# first focusable element. RIGHT: a control is focused on open. WRONG: nothing
# selected → the gamepad does nothing and the player is stuck.
```

### 5. Event-driven HUD (decouple UI from game logic)

```gdscript
# RIGHT: HUD reacts to a signal; it updates only when health actually changes.
func _ready() -> void:
    player.health_changed.connect(_on_health_changed)     # emitted by gameplay
    _on_health_changed(player.hp, player.max_hp)           # signals do not replay initial state
func _on_health_changed(current: int, max_health: int) -> void:
    # ratio maps 0..1 to the bar's configured range (default value range is 0..100).
    $HealthBar.ratio = clampf(float(current) / max_health, 0.0, 1.0) if max_health > 0 else 0.0
# WRONG: func _process(dt): $HealthBar.value = player.hp / player.max_hp  # polls every frame,
# couples UI to the player's internals, and runs work even when nothing changed.
```

## Pitfalls

- **Absolute pixel positions / a single design resolution.** Looks right on your monitor, broken
  everywhere else. Anchor to edges/center and flow with containers.
- **No aspect-ratio policy.** 16:9-only layouts crop or letterbox badly on ultrawide and phones.
  Decide expand vs letterbox and anchor HUD to corners that move outward.
- **Ignoring the safe area.** HUD under a notch or lost to TV overscan. Inset critical elements.
- **No initial focus / no focus neighbors.** The game is unplayable on a gamepad; players land
  on a menu with nothing selected. Always focus one control and define navigation.
- **Polling game state in `_process`/`Update`.** Couples UI to internals and wastes work. Push
  updates via signals/events.
- **Tiny fixed font sizes.** Unreadable on a TV-at-distance or a small phone. Scale text with the
  UI and offer a text-size option. Xbox Accessibility Guideline 101 sets floors of 26 px at 1080p
  on console/TV and 18 px at 1080p on PC, and asks for scaling up to 200% without losing content.
- **Menu flow as boolean flags** (`isPaused`, `inSettings`, …) becomes unmanageable. Use a
  screen stack with push/pop.
- **Hardcoded English strings baked into layout.** Translations overflow buttons. Externalize
  strings and let containers size to content (see `references/`).
- **Mouse-only or focus-only.** Support both; switching input device should not strand the user.
- **Unity uGUI menu ignores the gamepad or throws on start** after switching Active Input
  Handling to the Input System: the scene still has a `StandaloneInputModule`. Replace it with
  `InputSystemUIInputModule` (the Inspector offers a one-click swap). UI Toolkit in Unity 6 reads
  the project-wide UI actions directly and needs no module.
- **A corner-anchored uGUI element grows off-screen** when its size changes (longer translated
  text, a bigger text-size setting): its pivot was left at (0.5, 0.5), so it grows in every
  direction. Set the pivot to the anchored corner or edge as well.

## References

- For stretch/scale modes per engine, the safe-area math, a complete focus-navigation and
  screen-stack pattern, diegetic vs non-diegetic UI, accessibility (text size, contrast,
  colorblind-safe state), and localization-ready layout, read `references/layout-and-flow.md`.

## Related skills

- `godot-ui-control`, Unity UI (UGUI/UI Toolkit) — the concrete widgets, themes, and styling.
- `game-feel` — button pops, transitions, and HUD juice that ride on top of this layout.
- `dialogue-systems` — conversation/choice UI that lives inside this UI shell.
- `input-systems` — device switching, rebinding screens, and accessible controls.
- `rpg`, `card-game`, `tower-defense`, `visual-novel` — UI-heavy genres that compose this skill.
