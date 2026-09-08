# Roblox UI input, selection, and motion

Read this for gamepad navigation, touch/mouse parity, modal focus, `ContextActionService`, or UI
motion. Targets Roblox's rolling platform APIs.

## Control contract

- Prefer `GuiButton.Activated` for the primary action because it unifies mouse, touch, and gamepad.
- Give every interactive state a visual response: hover where a pointer exists, pressed, selected,
  disabled, and busy if an operation can take time. Do not communicate state with color alone.
- Make touch targets comfortably hittable and separated; do not add invisible hit zones that overlap
  neighboring controls.
- Show input prompts that match the active device, but never hide the only explanation of an action
  during device switching.

## Selection graph

On screen open, select the most likely safe action—not a destructive action. Use
`GuiService.SelectedObject`. Let automatic selection handle simple lists; assign
`NextSelectionLeft/Right/Up/Down` where layout geometry is ambiguous. Test every edge and a full
round trip through the graph.

Set initial selection only after the control is rendered and only for keyboard/gamepad navigation.
Device emulation can expose keyboard capability while touch controls are active, so prefer the
active input policy used by the project; do not force a selected object on a touch-first screen.
Inspect the default adornment. A custom `SelectionImageObject` must remain a valid visible
`GuiObject` (it can live offscreen as the reusable template) and should match the interface's focus
treatment instead of adding a large glow.

When a modal opens:

1. remember the prior selected object if it still belongs to the underlying screen;
2. prevent interaction with the screen beneath it;
3. select the modal's first safe control;
4. keep directional navigation inside the modal;
5. on close, restore the prior object or a stable fallback.

To keep directional navigation inside the modal, set `GuiBase2d.SelectionGroup = true` on the modal
root and set its `SelectionBehaviorUp`/`Down`/`Left`/`Right` to `Enum.SelectionBehavior.Stop`. The
older `GuiService:AddSelectionParent()`/`AddSelectionTuple()`/`RemoveSelectionGroup()` methods are
all deprecated — do not use them in new work.

## Context actions

Use `ContextActionService:BindAction()` for screen-level actions such as close/back, tab change, or
an ability-bar shortcut that is not already owned by a button. Bind on screen activation and
`UnbindAction()` on close. Return `Enum.ContextActionResult.Sink` only when the UI intentionally
consumes the action; otherwise allow gameplay to receive it.

Do not create a second input system inside a menu. Coordinate screen actions with `input-systems`
and preserve the project's existing action names and bindings.

## Motion lifecycle

- Read `GuiService.ReducedMotionEnabled`; replace spatial movement with an instant state or short
  opacity change when reduced motion is requested.
- Reuse a small timing/easing vocabulary. Typical state transitions should be quick enough not to
  delay interaction.
- Cancel or supersede an in-flight tween when the target state changes. Do not queue contradictory
  open/close animations.
- Animate a stable parent (`CanvasGroup` is useful for group transparency) instead of spawning a
  tween for every descendant.
- The logical state changes immediately; animation visualizes it. Never make server-critical state
  depend on tween completion.

## Controller verification

Use Studio's Controller Emulator and also a real controller when available. Verify initial focus,
all directions, activation, back/cancel, tab/shoulder navigation if used, scroll-following selected
items, focus restoration, and mouse-to-gamepad switching. Controller emulation proves mapping and
navigation, not TV legibility; use Device Emulator/console sizing for that.

## Primary references

- `https://create.roblox.com/docs/reference/engine/classes/GuiService`
- `https://create.roblox.com/docs/studio/testing-modes`
- `https://create.roblox.com/docs/production/publishing/console-guidelines`
