---
name: studio-asset-spec
description: Specify a game asset or cohesive asset family with technical dimensions, animation states, modular attachment points, references, and acceptance criteria before production.
---

# Studio Asset Specification

Own the **contract for one asset or family**. Use `create-game-assets` to perform creation, normalization, and engine integration.

## Workflow

1. Name gameplay purpose, in-game context, visual owner, approved reference, and priority.
2. Fix technical output: sprite canvas, occupied bounds, alpha, palette, number of frames, direction labels, texture filtering, naming convention, pivots, collision role, and source/rights.
3. Describe identity invariants across states and variants: anatomy, scale, silhouette, material palette, shading direction and source seed.
4. For modular equipment, define shared skeleton or pose contract, layer ordering by direction, anchors for hands/head/back, render order, coverage masks and clipping rules; specify behavior during attacking, hurt, roll and death.
5. List all gameplay states and animation events. Specify how visual and gameplay hit windows align, without mistaking generated sequences for validated rigged animations.
6. Include test matrix: native-scale view, each direction, idle/move/attack, equip/unequip, overlap, baseline jitter, transparency, palette consistency and actual background readability.
7. Write `design/assets/<asset-id>.md` or the existing asset manifest. Mark unknowns and approval owner.

## Example acceptance checks

- All expected files and directional/state variants exist and pass dimensions and alpha checks.
- Root/pivot/attachment positions remain stable across the same animation frames.
- Equipped helmet, torso, boots and weapon track the base body's poses and swap without redraw of every combination.
- Provenance and distribution rights are recorded.
- An in-engine preview shows no clipping, scale mismatch, silhouette loss or animation discontinuity.

## Output

Asset ID, purpose, asset family, locked constraints, file naming and folder plan, variants/states matrix, modular hooks, acceptance tests, risks, source references, and verification evidence.
