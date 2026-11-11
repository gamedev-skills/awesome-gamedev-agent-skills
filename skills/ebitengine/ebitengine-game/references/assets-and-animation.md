# Assets that belong to one game

Read when producing/importing sprites, backgrounds, UI art or animation. These
are asset-integration checks, not a requirement to generate images or build a
large asset pipeline for a small game.

## Establish shared visual rules and integration data

Describe the rendering/line language, viewing angle, lighting and palette **by
role**: world, player/interactable, threat, reward and UI. A shared list of colors
can make everything blend together; shared style should preserve distinctions
needed for play. A side-view character and top-down environment will not agree
merely because their colors match. Reuse a compact style description across art
requests, but verify actual results; identical prompt text cannot ensure cohesion.

For a set of assets, keep enough metadata to assemble it reliably: stable ID,
role, file/source and licence, intended world/logical size, anchor/pivot, facing,
animation layout and timing. A table or small data file is sufficient; no fixed
CSV schema is necessary. Separate source-image resolution from in-game scale.
Compare important objects in common world units and against the intended
background at play size, rather than approving isolated full-resolution images.

This adapts the role palette, scale comparison and asset-contract ideas in
[Higgsfield's stylization reference](https://github.com/higgsfield-ai/skills/blob/f83af0bc1d937c8119099a11f8ebbf5e6fb99819/higgsfield-websites/references/game-stylization.md).
Use the current asset tool's actual capabilities for transparency and output
formats; do not inherit a provider-specific claim that all models require chroma key.

## Keep animation registration stable

- Give frames consistent cell dimensions and a stable pivot appropriate to the
  action, such as a ground-contact point. Independently trimming every frame and
  centering the remaining pixels introduces jitter. A union of occupied bounds
  across the sequence can preserve registration **when the source frames were
  already aligned**; it cannot repair a drifting camera or a moving subject.
- Reserve bounds for the largest pose/effect. Check the full motion, thin parts,
  alpha edges on light and dark backgrounds, and transitions between clips.
  A good first frame does not establish a good sheet.
- Inspect a loop's seam and timing. Remove a terminal frame only when it repeats
  the start pose/timing unnecessarily; do not assume an exported/generated loop
  has identical endpoints. One-shot attack/recovery poses have different needs.
- Store actual frame count, grid dimensions and duration/markers. A partial final
  row must not animate through empty cells. For a grid sheet, cell coordinates
  come from `column = i % columns`, `row = i / columns`; the simple `NewAnim`
  example in the rendering reference assumes a horizontal strip.
- Choose sheet dimensions and frame count from motion/readability and target
  memory/texture constraints. A long strip can exceed the target's limits; split
  clips or pack a grid as needed. More nearly identical frames can add cost or
  shimmer without improving motion.

These checks adapt the registration and loop-assembly lessons in
[Higgsfield's 2D animation pipeline](https://github.com/higgsfield-ai/skills/blob/f83af0bc1d937c8119099a11f8ebbf5e6fb99819/higgsfield-websites/references/game-2d-animation.md).
Its provider commands, mandatory frame counts and fixed size limits are not
Ebitengine requirements.

## Connect art to rules deliberately

Keep the collision body and visual transform distinct. A squashed sprite or
shifted pivot should not silently change hit detection. If an attack's contact
occurs at an animation marker, process that marker in the simulation/update
timeline and emit the event once; a frame selected in `Draw` must not cause
damage. Verify pose, hitbox, particle location and sound onset together. Changing
clip speed must not accidentally duplicate or skip a gameplay event.

Inspect a small contact sheet at the intended relative sizes, then the assets
in motion in the game. This catches mismatched outlines/perspective, invisible
threats, sliding feet, cropped attacks and different anchors between clips.
Preserve the source and integration metadata needed to reproduce a later fix.
