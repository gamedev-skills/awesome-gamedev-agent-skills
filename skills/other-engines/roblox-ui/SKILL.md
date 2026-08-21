---
name: roblox-ui
description: >
  Build production Roblox interfaces with ScreenGui/PlayerGui lifecycle, responsive UDim2
  layouts, safe insets, reusable editable Instances, cross-device input and selection, restrained
  motion, cleanup, and multi-viewport verification. Use for Roblox HUDs, inventories, shops,
  settings, ability bars, ScrollingFrames, AutomaticSize, GuiService, gamepad focus, touch UI, or
  UI that clips, resets on respawn, looks generic, or was generated as one giant LocalScript.
---

# Roblox UI

Implement deliberate, editable Roblox UI that preserves the experience's visual language and
works across supported devices. Targets Roblox's rolling platform APIs. Pair with `game-ui-ux`
for engine-neutral information architecture and UX; this skill owns Roblox Instances and APIs.

## When to use

- Use for authored `ScreenGui` interfaces, Roblox layout/constraint APIs, UI lifecycle, input,
  focus, animation, performance, or responsive/device fixes.
- Use to replace brittle pixel layouts, runtime-created Instance tangles, mouse-only menus, or
  generic generated styling with a maintainable hierarchy.

**When not to use:** general UX flow and accessibility principles belong to `game-ui-ux`; raw
gameplay action mapping belongs to `input-systems`; server trust belongs to `roblox-networking`.

## Workflow

1. **Inspect before designing.** In Explorer, inventory existing `ScreenGui`s, UI modules,
   fonts, colors, icon family, spacing, corners, strokes, animation timing, naming, and reusable
   components. Capture representative screenshots at two viewports. Extend that language.
2. **Define ownership and lifecycle.** `StarterGui` is the authored template; Roblox clones it
   into each player's `PlayerGui`. Decide whether each `ScreenGui` should persist across respawn
   with `ResetOnSpawn = false`; never keep stale references to a destroyed clone.
3. **Author a readable hierarchy.** Prefer meaningful editable Instances and small behavior
   modules. A normal screen should be understandable in Explorer; procedural generation is for
   genuinely data-driven repetition, not the whole shell.
4. **Build responsive structure.** Combine `UDim2` scale for placement with bounded offsets,
   correct `AnchorPoint`s, layouts, padding, content sizing, and constraints. Choose explicit
   narrow/wide arrangements instead of shrinking a desktop panel until it technically fits.
5. **Handle platform obstructions.** Keep interactive UI in `CoreUISafeInsets` (the recommended
   `ScreenGui.ScreenInsets` default), and account for touch controls and TV distance/overscan.
6. **Wire state and input.** Render from a small view state; update on events. Use `Activated` for
   `GuiButton`s, explicit selected states, and reachable gamepad navigation. Bind non-widget
   actions with `ContextActionService` only while the screen owns them.
7. **Polish with restraint.** Implement hover, pressed, selected, and disabled states. Animate
   state changes, not decoration; honor `GuiService.ReducedMotionEnabled` and clean up tweens and
   connections when the screen closes or is replaced.
8. **Verify the real interface.** Use Device Emulator and Controller Emulator. Test desktop,
   narrow portrait, mobile landscape, tablet-like, and console/gamepad; then respawn. Record
   clipping, overlap, text, scroll, safe-area, focus path, touch target, and lifecycle results.

## Production structure

```text
StarterGui
└── InventoryGui (ScreenGui; ResetOnSpawn = false)
    ├── Root (Frame)
    │   ├── Header
    │   ├── Content
    │   │   ├── CategoryList
    │   │   ├── ItemGrid (ScrollingFrame)
    │   │   └── DetailsPanel
    │   └── Footer
    └── InventoryController (LocalScript)
ReplicatedStorage
└── UI
    ├── Components
    └── Theme
```

Names describe roles, not colors or temporary positions. Keep repeated item cells as templates or
components, but keep the authored shell visible in Explorer.

## Patterns

### Layout that survives content and viewport changes

```lua
-- Authored properties on ItemGrid (ScrollingFrame):
--   AutomaticCanvasSize = Enum.AutomaticSize.Y
--   CanvasSize = UDim2.fromOffset(0, 0)
-- Children: UIPadding + UIGridLayout
local grid = itemGrid.UIGridLayout
local projectBreakpoint = 700 -- derive from where this composition stops being usable

local function applyComposition()
    local narrow = root.AbsoluteSize.X < projectBreakpoint
    categoryList.UIListLayout.FillDirection = if narrow
        then Enum.FillDirection.Horizontal
        else Enum.FillDirection.Vertical
    categoryList.Size = if narrow
        then UDim2.new(1, 0, 0, 40)
        else UDim2.new(0, 148, 1, 0)
    itemGrid.Position = if narrow then UDim2.fromOffset(0, 52) else UDim2.fromOffset(164, 0)
    itemGrid.Size = if narrow
        then UDim2.new(1, 0, 1, -52)
        else UDim2.new(0.58, -164, 1, 0)
    detailsPanel.Visible = not narrow -- open details as a separate narrow-screen state

    local width = itemGrid.AbsoluteSize.X
    local columns = if width < 520 then 2 elseif width < 820 then 3 else 4
    local gap = 12
    local usable = width - itemGrid.UIPadding.PaddingLeft.Offset
        - itemGrid.UIPadding.PaddingRight.Offset - gap * (columns - 1)
    grid.CellSize = UDim2.fromOffset(math.floor(usable / columns), 112)
    grid.CellPadding = UDim2.fromOffset(gap, gap)
end

root:GetPropertyChangedSignal("AbsoluteSize"):Connect(applyComposition)
applyComposition()
```

Use `UIListLayout` for one-dimensional flow, `UIGridLayout` for uniform cells, and
`UITableLayout` only when row/column alignment is truly tabular. `AutomaticSize` fits content;
`AutomaticCanvasSize` fits scroll content. Bound extremes with `UISizeConstraint`,
`UIAspectRatioConstraint`, or `UITextSizeConstraint` rather than one global `UIScale` guess.

### One activation path and explicit gamepad entry

```lua
local GuiService = game:GetService("GuiService")
local RunService = game:GetService("RunService")
local UserInputService = game:GetService("UserInputService")

local function openInventory()
    root.Visible = true
    task.spawn(function()
        RunService.RenderStepped:Wait() -- selection must be rendered and selectable
        if root.Visible and (UserInputService.GamepadEnabled
            or (UserInputService.KeyboardEnabled and not UserInputService.TouchEnabled)) then
            GuiService.SelectedObject = firstItemButton
        end
    end)
end

local function closeInventory()
    GuiService.SelectedObject = nil
    root.Visible = false
end

firstItemButton.Activated:Connect(function()
    selectItem(firstItemButton:GetAttribute("ItemId"))
end)
```

Prefer `Activated` over separate mouse/touch handlers. Set `NextSelectionUp/Down/Left/Right`
when automatic navigation is ambiguous, especially around grids, sidebars, and modals. A modal
must trap focus inside itself and restore a sensible selection when it closes.

Inspect Roblox's default selection adornment in context. If it overwhelms the interface, assign a
project-owned `SelectionImageObject` or selected-state treatment; keep it visible, valid, and
restrained rather than disabling focus feedback.

### State transition without animation noise

```lua
local TweenService = game:GetService("TweenService")
local GuiService = game:GetService("GuiService")
local fade = TweenInfo.new(0.14, Enum.EasingStyle.Quad, Enum.EasingDirection.Out)

local function setPanelVisible(visible: boolean)
    panel.Visible = true -- panel is a CanvasGroup
    if GuiService.ReducedMotionEnabled then
        panel.GroupTransparency = if visible then 0 else 1
    else
        TweenService:Create(panel, fade, {
            GroupTransparency = if visible then 0 else 1,
        }):Play()
    end
    if not visible then
        task.delay(fade.Time, function()
            if panel.GroupTransparency == 1 then panel.Visible = false end
        end)
    end
end
```

Animate a panel or state boundary once. Do not independently bounce every descendant.

## Visual quality gates

- Establish hierarchy through size, weight, contrast, grouping, and whitespace before adding
  decoration. Use a small spacing scale and align to it.
- Preserve the game's fonts, palette, icons, radii, and strokes. If none exist, define a compact
  token module; do not improvise per component.
- Use corners where the material/form calls for them, not on every nested `Frame`. Avoid nested
  card-on-card shells, universal pills, arbitrary gradients/glows/shadows, neon outlines,
  excessive transparency/blur, oversized headings, meaningless icons, and huge empty panels.
- Buttons with different importance should not look identical. Define primary, secondary,
  quiet, destructive, selected, pressed, hover, and disabled treatment only as needed.
- Motion communicates open/close, focus, confirmation, or spatial relationship. Keep it short,
  interruptible, and subtle; avoid perpetual motion and decorative tween chains.
- On touch devices, reserve the default movement/jump corners. Move or recompose bottom actions
  that overlap them, and hide keyboard/gamepad hints when those inputs are not active.

## Common failures

| Symptom | Likely cause | Remedy |
|---|---|---|
| UI disappears or duplicates after respawn | wrong `ResetOnSpawn` policy or stale clone | choose policy; reacquire from `PlayerGui`; clean old bindings |
| Phone layout clips | desktop offsets/global scale used as layout | add narrow composition, layouts, bounds, and Device Emulator checks |
| Content hidden under topbar/notch | insets ignored or `ScreenInsets = None` | use `CoreUISafeInsets` for interactive UI; inspect intentional bleed |
| Scroll ends early | fixed `CanvasSize` | use `AutomaticCanvasSize` or layout `AbsoluteContentSize` |
| Controller gets stuck | no entry selection or bad neighbor graph | set initial `SelectedObject`; define and test focus edges/modal trap |
| UI looks generated | decoration substituted for hierarchy | remove effects; align, reduce nesting, fix density and component roles |
| Explorer contains only one script | entire authored interface is procedural | author the shell as named Instances; generate repeated content only |
| Increasing connection/tween count | screen rebinds without cleanup | own connections per screen lifecycle; disconnect/cancel on teardown |

## Resources

- Read `references/responsive-layout.md` for layout decisions, inset policy, density, and the
  required viewport matrix.
- Read `references/input-navigation.md` when implementing gamepad/touch focus, modal behavior,
  action binding, or motion preferences.
- Build `assets/inventory-quality-test.project.json` with Rojo (it maps the adjacent JSON model)
  for an editable Instance fixture used in visual/layout review; it is a test baseline, not a style
  template for a shipping game.

## Related skills

- `game-ui-ux` — information hierarchy, screen flow, accessibility, and UX validation.
- `input-systems` — gameplay action mapping and device switching.
- `roblox-networking` — server-authoritative requests initiated by UI.
- `roblox-studio-workflow` — Explorer-first editing and Studio verification.

## Primary references

- Roblox Creator Hub: `https://create.roblox.com/docs/ui/on-screen-containers`
- Roblox Creator Hub: `https://create.roblox.com/docs/ui/position-and-size`
- Roblox Creator Hub: `https://create.roblox.com/docs/ui/size-modifiers`
- Roblox Creator Hub: `https://create.roblox.com/docs/studio/testing-modes`
