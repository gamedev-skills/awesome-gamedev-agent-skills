---
name: roblox-ui
description: >
  Roblox UI with ScreenGui and PlayerGui: ResetOnSpawn, UDim2 scale and offset, UIListLayout flex,
  safe areas, StyleSheet, gamepad selection and touch controls. Use for Roblox HUDs, shops or
  settings menus, or UI that clips on phones, resets on respawn or loses controller focus. Load
  `game-ui-ux` too. Not for input mapping (`input-systems`) or purchase checks
  (`roblox-networking`).
---

# Roblox UI

Build editable Roblox interfaces that keep the experience's visual language and work on every
supported device. This skill owns the Roblox Instances and APIs; `game-ui-ux` owns the design
rules, so load both for menu and HUD work.

## Workflow

1. **Inspect before designing.** Inventory existing `ScreenGui`s, UI modules, fonts, colors, icon
   family, spacing, corners, strokes, animation timing, naming, and any `StyleSheet`/`StyleLink`
   tokens. Capture two viewports (`screen_capture` over Studio MCP, or ask the user for
   screenshots). Extend that language.
2. **Define ownership and lifecycle.** `StarterGui` is the authored template; Roblox clones it into
   each `PlayerGui`. Decide per `ScreenGui` whether it survives respawn (`ResetOnSpawn = false`) and
   never keep references to a destroyed clone.
3. **Author a readable hierarchy.** Named, editable Instances plus small behavior modules. A screen
   should make sense in Explorer; procedural creation is for data-driven repetition only.
4. **Build responsive structure.** `UDim2` scale for placement, bounded offsets for components,
   matching `AnchorPoint`s, layouts, padding, and size constraints. Design an explicit narrow
   arrangement instead of shrinking the desktop panel.
5. **Handle obstructions.** Keep interactive UI inside `CoreUISafeInsets` (the `ScreenInsets`
   default) and away from the touch movement and jump controls; allow for TV overscan.
6. **Wire state and input.** Render from a small view state. Use `Activated` for buttons, explicit
   selected states, and a reachable gamepad path. Bind screen actions only while the screen owns
   them.
7. **Polish with restraint.** Hover, pressed, selected, disabled. Animate state changes, honor
   `GuiService.ReducedMotionEnabled`, and cancel tweens and connections on close.
8. **Check before reporting.** Build-level: `rojo build <project>.project.json -o out.rbxlx` must
   succeed for Rojo projects. Live, with the Studio MCP server connected: start play, open the
   screen from `execute_luau` on the `Client` datamodel, print `GuiService.SelectedObject` and the
   `AbsoluteSize` of the root and scroll canvas, then `screen_capture`; Studio's built-in
   `rbx-device-simulator-lua` skill (through the `skill` tool) switches device presets for the
   viewport matrix. Without MCP, ask the user to check the matrix in
   `references/responsive-layout.md` with Device Simulator and Controller Emulator and report
   clipping, overlap, focus path, and respawn behavior.

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

Names describe roles, not colors or positions. Repeated cells are templates or components; the
shell stays visible in Explorer.

## Patterns

### Layout that survives content and viewport changes

```lua
-- Authored on ItemGrid (ScrollingFrame):
--   AutomaticCanvasSize = Enum.AutomaticSize.Y, CanvasSize = UDim2.fromOffset(0, 0)
-- Children: UIPadding + UIGridLayout
local grid = itemGrid.UIGridLayout
local projectBreakpoint = 700 -- where this composition stops being usable, not a device name

local function applyComposition()
    local narrow = root.AbsoluteSize.X < projectBreakpoint
    categoryList.UIListLayout.FillDirection = if narrow
        then Enum.FillDirection.Horizontal
        else Enum.FillDirection.Vertical
    categoryList.Size = if narrow then UDim2.new(1, 0, 0, 40) else UDim2.new(0, 148, 1, 0)
    itemGrid.Position = if narrow then UDim2.fromOffset(0, 52) else UDim2.fromOffset(164, 0)
    itemGrid.Size = if narrow then UDim2.new(1, 0, 1, -52) else UDim2.new(0.58, -164, 1, 0)
    detailsPanel.Visible = not narrow -- narrow screens open details as a separate state

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

`UIListLayout` for one-dimensional flow (with flex for shared space), `UIGridLayout` for uniform
cells, `UITableLayout` only for real tables. `AutomaticSize` fits content; `AutomaticCanvasSize`
fits scroll content. Bound extremes with `UISizeConstraint`, `UIAspectRatioConstraint` or
`UITextSizeConstraint` rather than one global `UIScale`. In a styled project, a `StyleQuery` can
switch rules at a size breakpoint without a resize script.

### One activation path and explicit gamepad entry

```lua
local GuiService = game:GetService("GuiService")
local RunService = game:GetService("RunService")
local UserInputService = game:GetService("UserInputService")

local function usesDirectionalFocus(): boolean
    local preferred = UserInputService.PreferredInput
    return preferred == Enum.PreferredInput.Gamepad
        or preferred == Enum.PreferredInput.MicroGamepad
end

local function focusFirstItem()
    task.spawn(function()
        RunService.RenderStepped:Wait() -- the target must be rendered and selectable
        if root.Visible and usesDirectionalFocus() then
            GuiService.SelectedObject = firstItemButton
        end
    end)
end

local function openInventory()
    root.Visible = true
    focusFirstItem()
end

local function closeInventory()
    GuiService.SelectedObject = nil
    root.Visible = false
end

-- Owned by the screen lifecycle; disconnect on teardown.
local inputConnection = UserInputService:GetPropertyChangedSignal("PreferredInput"):Connect(function()
    if root.Visible and GuiService.SelectedObject == nil then focusFirstItem() end
end)

firstItemButton.Activated:Connect(function()
    selectItem(firstItemButton:GetAttribute("ItemId"))
end)
```

Choose input-dependent UI from `UserInputService.PreferredInput`, which follows the player's
primary device. `TouchEnabled` and `GamepadEnabled` are capabilities (a touch laptop reports
touch), and `GetLastInputType()` flips on every stray input. Set `NextSelection*` where automatic
navigation is ambiguous (grids, sidebars, modals). A modal traps focus with
`SelectionGroup = true` plus `SelectionBehavior*` set to `Stop`, and restores a sensible selection
on close. If the default selection adornment overwhelms the design, give it a project-owned
`SelectionImageObject`; do not remove focus feedback.

### State transition without animation noise

```lua
local TweenService = game:GetService("TweenService")
local GuiService = game:GetService("GuiService")
local fade = TweenInfo.new(0.14, Enum.EasingStyle.Quad, Enum.EasingDirection.Out)
local activeTween: Tween? = nil

local function setPanelVisible(visible: boolean)
    if activeTween then activeTween:Cancel(); activeTween = nil end
    local target = if visible then 0 else 1
    panel.Visible = true -- panel is a CanvasGroup
    if GuiService.ReducedMotionEnabled then
        panel.GroupTransparency = target
        panel.Visible = visible
        return
    end
    local tween = TweenService:Create(panel, fade, { GroupTransparency = target })
    activeTween = tween
    tween.Completed:Once(function(state)
        if state == Enum.PlaybackState.Completed and not visible then panel.Visible = false end
    end)
    tween:Play()
end
```

Animate the panel once, not every descendant, and cancel the previous tween so a fast open and
close cannot leave the panel invisible but interactive.

## Visual quality gates

- Build hierarchy with size, weight, contrast, grouping and whitespace before decoration. Use a
  small spacing scale and align to it.
- Keep the game's fonts, palette, icons, radii and strokes. In a styled project, change tokens and
  `StyleRule`s, not per-instance properties. With no system in place, define a compact token set
  (a token `StyleSheet` or module) instead of improvising per component.
- Corners where the form calls for them, not on every nested `Frame`. Avoid card-on-card shells,
  universal pills, arbitrary gradients, glows, neon outlines, heavy transparency or blur, oversized
  headings, meaningless icons, and huge empty panels.
- Buttons of different importance look different: primary, secondary, quiet, destructive, plus
  selected, pressed, hover and disabled states only as needed.
- Motion explains open and close, focus, confirmation, or spatial relationships. Keep it short and
  interruptible; no perpetual motion.
- On touch, keep bottom actions clear of the movement and jump controls, and show hints only for
  the current `PreferredInput`.

## Gotchas

| Symptom | Likely cause | Remedy |
|---|---|---|
| UI disappears or duplicates after respawn | wrong `ResetOnSpawn` policy or stale clone | choose the policy; reacquire from `PlayerGui`; clean old bindings |
| phone layout clips | desktop offsets or one global scale used as layout | narrow composition, layouts, bounds, Device Simulator checks |
| content under the topbar or notch | insets ignored or `ScreenInsets = None` | `CoreUISafeInsets` for interactive UI; bleed only decoration |
| scroll ends early | fixed `CanvasSize` | `AutomaticCanvasSize` or the layout's `AbsoluteContentSize` |
| controller gets stuck or escapes a modal | no entry selection or bad neighbor graph | set `SelectedObject`; define edges; `SelectionGroup` with `Stop` |
| panel invisible but still blocks clicks | interrupted tween left `Visible = true` | cancel the previous tween; hide on `Completed` |
| UI looks generated | decoration substituted for hierarchy | remove effects; align, reduce nesting, fix density and roles |
| Explorer shows only one script | whole interface built at runtime | author the shell as named Instances |
| connection or tween count keeps rising | screen rebinds without cleanup | own connections per screen; disconnect and cancel on teardown |

## Resources

- Read `references/responsive-layout.md` when a screen must adapt across viewports or a layout
  defect appears: layout primitives, flex, insets, density, and the required viewport matrix.
- Read `references/input-navigation.md` when implementing gamepad or touch focus, modals,
  `ContextActionService` or Input Action bindings, or motion preferences.
- Build `assets/inventory-quality-test.project.json` with Rojo when you need an editable Instance
  fixture for layout review: `rojo build assets/inventory-quality-test.project.json -o inventory-test.rbxlx`
  from the skill directory. It is a test baseline, not a style to ship.

## Related skills

- `game-ui-ux`: information hierarchy, screen flow, accessibility, and design rules.
- `input-systems`: gameplay action mapping and device switching.
- `roblox-networking`: server-authoritative requests started from UI.
- `roblox-studio-workflow`: Explorer-first editing and Studio verification.

## Version notes

Last verified: 2026-11-11.

- `StyleQuery` and enhanced styling reached full release in May 2026; styling transitions are also
  fully released.
- `Enum.PreferredInput` values: `KeyboardAndMouse`, `Gamepad`, `Touch`, `MicroGamepad` (a gamepad
  without a thumbstick, such as a TV remote).
- `GuiBase2d.SelectionGroup` and `SelectionBehaviorUp/Down/Left/Right` are the property-based way
  to contain navigation. `GuiService:AddSelectionParent()` and `AddSelectionTuple()` still exist
  and were not marked deprecated in the API reference on the verification date.
- Rojo 7.7.1 builds the bundled fixture.
- To re-check an API: append `.md` to its Creator Hub URL, or start from
  `https://create.roblox.com/docs/llms.txt`.

Sources: `https://create.roblox.com/docs/ui/on-screen-containers`,
`https://create.roblox.com/docs/ui/position-and-size`,
`https://create.roblox.com/docs/ui/size-modifiers`,
`https://create.roblox.com/docs/reference/engine/enums/PreferredInput`,
`https://create.roblox.com/docs/reference/engine/classes/GuiService`,
`https://create.roblox.com/docs/assistant/skills` (built-in Studio skills),
`https://devforum.roblox.com/t/full-release-stylequery-more-styling-features/4566519`.
