---
name: studio-art-bible
description: Define or maintain a durable game visual identity and art bible, including palette, silhouettes, perspective, sprite sizing, animation style, and asset acceptance rules.
---

# Studio Art Bible

## Ownership and handoff

Own **persistent visual direction**, not asset generation or engine import. Pair with `create-game-assets` when images or sprites are being produced, and with the engine import skill for runtime tests. Do not silently redesign approved art or overwrite existing style documents.

## Workflow

1. Inspect game references, existing assets, screenshots, palette files, camera projection, native canvas, platform and display targets. Record observed evidence separately from proposals.
2. State the intended player experience and visual pillars, including what the game's art must *not* resemble.
3. Define form language and silhouette tiers for player, enemies, bosses, props, and UI. Specify value grouping, focal detail budgets, material response, edge treatment, texture frequency, and palette roles.
4. Lock camera/view convention and scale: orientation, foreshortening, sprite canvas vs occupied bounds, pixels-per-world-unit, zoom/filter mode, pivots, baseline, occlusion and y-sort.
5. Define animation rules: directional views, key poses, motion arcs, timing, frame anchors, limb/gear compatibility, anticipation/recovery, and shadow handling.
6. Define *asset families* and a reference hierarchy: approved originals > style sheets > written prompts. Keep variant rules (helmets, gear tiers, monsters) separate from invariant character rig and shared palette constraints.
7. Specify evaluation at game scale, accessibility/contrast, implementation constraints, and a review process before mass generation.
8. Publish a versioned art bible at `design/art-bible.md` (or existing canonical location). Link the asset manifest, example contact sheets, and superseded decisions.

## Output contract

Provide visual pillars; palette roles; shape/silhouette rules; camera/scale; characters and modular gear; animation; environments; UI/VFX; asset checklist; do/don't examples; acceptance tests; known risks; changed files and evidence.

## Verification gates

- A fresh contributor can create a compatible player, enemy and equipment set using the written spec.
- Rules are measurable: dimensions, facing, palette budgets, pivots and outline treatment, not just adjectives.
- Style is recognizable when rendered over an actual game background at intended zoom.
- Remaining subjective decisions are visibly flagged for art-direction approval.

## Relationship to other skills

`create-game-assets` produces and normalizes artwork; `studio-asset-spec` scopes one asset; `studio-asset-audit` checks the catalog. If asset generation is asked for, load the production skill too.
