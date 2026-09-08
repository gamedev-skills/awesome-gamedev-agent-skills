# Responsive Roblox UI

Read this when a screen must adapt across viewport sizes or when layout defects appear outside the
author's primary monitor. This reference targets Roblox's rolling platform APIs.

## Choose structure before coordinates

1. Identify persistent regions: HUD edge groups, header, primary content, secondary detail,
   footer/action row, modal layer.
2. Decide what changes on narrow screens. Reflow or collapse secondary regions; do not only scale
   the desktop composition down.
3. Anchor edge-owned regions to their edge (`AnchorPoint` must match `Position`). Put siblings in
   layouts instead of manually positioning each child.
4. Use offsets for bounded component dimensions and spacing; use scale for proportional placement
   and flexible region size. Inspect `AbsoluteSize`, not device names, for layout breakpoints.

## Roblox layout primitives

| Need | Primitive | Check |
|---|---|---|
| vertical/horizontal flow | `UIListLayout` | `Padding`, alignment, flex behavior, content size |
| uniform collection | `UIGridLayout` | cell size at narrow/wide bounds; scroll canvas |
| true rows and columns | `UITableLayout` | headers and cell alignment; avoid for card collections |
| inner spacing | `UIPadding` | use one spacing scale; include it in width calculations |
| content-driven object | `AutomaticSize` | localization, wrapping, and circular dependencies |
| content-driven scrolling | `AutomaticCanvasSize` | scrolling direction and bottom reachability |
| proportional shape/media | `UIAspectRatioConstraint` | avoid constraining text-heavy containers |
| min/max component size | `UISizeConstraint` | test both limits, not only preferred width |
| bounded text scaling | `UITextSizeConstraint` | still test localization and TV distance |
| deliberate subtree zoom | `UIScale` | avoid using one scale as the entire responsive system |

## Safe areas and reserved controls

For interactive `ScreenGui` content, retain `ScreenInsets = CoreUISafeInsets` unless the design
has a measured reason not to. Decorative backgrounds may intentionally bleed into `None`, but put
interactive descendants in a separate inset-aware `ScreenGui` or safe root.
`GuiService:GetInsetArea(Enum.ScreenInsets.CoreUISafeInsets)` returns the actual inset rectangle when
custom positioning needs it — the `ScreenInsets` argument is required, and which inset set you ask
for is the point of the call. `GuiService.TopbarInset` gives the topbar rectangle on its own.

Mobile tests must include the bottom-left movement control and bottom-right jump/action region.
Console tests must consider viewing distance and overscan, not just a desktop window enlarged to TV
resolution.

Do not choose breakpoints from device labels. Choose them where the composition loses usable width:
for example, a sidebar + grid + detail view must switch to a horizontal category strip, full-width
grid, and separate detail state before any region becomes token-width. On touch, relocate bottom
actions away from reserved controls and remove irrelevant controller hint rows.

## Density and visual rhythm

Derive a small spacing scale from the existing game (for example 4/8/12/16/24, not a mandated
universal scale). Reuse it for padding, gaps, icon-to-label space, and section separation. A larger
gap signals a stronger grouping boundary. Choose text roles (title, section, body, metadata) and
keep role sizes/weights stable. Use consistent icon boxes even when source art has different bounds.

## Required verification matrix

| Configuration | Inspect |
|---|---|
| desktop, mouse + keyboard | hover/pressed, resizing, ultrawide or tall extreme |
| narrow mobile portrait | reflow, touch reach, wrapping, scrolling, safe cutouts |
| mobile landscape | reserved controls, low vertical space, modal height |
| tablet-like | density and excessive empty space |
| console/gamepad | initial focus, every directional edge, back action, TV readability |

For every configuration, exercise open/close, content-empty/content-full, long localized-like text,
disabled and error states, scrolling to both ends, and character respawn. Record observed defects
and the exact change that fixed them.

## Bundled Instance fixture

`../assets/inventory-quality-test.project.json` maps the adjacent Rojo JSON model into `StarterGui`.
Build it with `rojo build assets/inventory-quality-test.project.json -o inventory-test.rbxlx` from
the skill directory. The result contains a real `ScreenGui` hierarchy—not a procedural UI script.
Inspect it in Explorer, then use it only to exercise the matrix above. It deliberately uses
restrained geometry and a clear category/grid/detail hierarchy; adaptation logic, interaction
behavior, data population, and project styling remain work for the test scenario. Do not ship the
fixture unchanged.

## Primary references

- `https://create.roblox.com/docs/ui/on-screen-containers`
- `https://create.roblox.com/docs/ui/position-and-size`
- `https://create.roblox.com/docs/ui/size-modifiers`
- `https://create.roblox.com/docs/production/publishing/adaptive-design`
