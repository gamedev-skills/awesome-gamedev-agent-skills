---
name: create-game-assets
description: >
  Plans, generates or sources, and validates consistent game art: style guides, sprites, pixel
  art, tilesets, icons and textures, with QA and licence records. Use when making or AI-generating
  game art, fixing fake transparency, or checking Steam AI disclosure. Not for engine import
  (`godot-tilemap`, `godot-animation`, `unity-tilemap-2d`), UI layout (`game-ui-ux`) or sound
  (`audio-design`).
---

# Create Game Assets

Turn a game's visual intent into a consistent, engine-ready asset set. Treat image generation as
one production tool inside a controlled pipeline, never as proof that an asset is shippable.

## When to use

- Defining or refreshing an art direction, or writing a style guide other contributors follow.
- Producing a family of sprites, tiles, icons, backgrounds or textures that must match.
- Generating art with an image tool, or sourcing licensed packs, and making the result usable.
- Auditing what was generated or licensed before release.

**Not this skill:** importing into the engine (`godot-tilemap`, `unity-tilemap-2d`,
`pixijs-rendering`, `threejs-gltf-loading`), animating the sprites (`godot-animation`,
`unity-animation`), atlas and texture-memory budgets at runtime (`performance-optimization`).

## Core workflow

1. **Inspect before inventing.** Find existing screenshots, concept art, sprites, models, fonts,
   import settings, camera framing, target resolution, and naming conventions. Preserve a coherent
   existing direction unless the user asks for a redesign.
2. **Lock the technical frame.** Record engine, 2D/3D, camera/view, native display size, asset
   dimensions, world scale, transparency, palette, filtering, animation frames, texture budget,
   and target platforms. Use `assets/art-direction-brief.md` as a copyable brief.
3. **Name the visual system.** Define shape language, silhouette priorities, value structure,
   palette roles, materials, lighting, detail density, edge treatment, and motion character. Use
   concrete visual properties; do not substitute a living artist's name for an art direction.
4. **Make an asset manifest.** Copy `assets/asset-manifest.json`, then list every required asset,
   state, variant, size, pivot, collision role, source, license, and approval status. Separate
   production assets from disposable greybox placeholders.
5. **Approve one visual target.** Create or select a representative hero asset or small style
   board before producing a full set. Judge it at actual game scale and against a gameplay
   background. If the user delegated the choice, pick the strongest viable direction and record
   the decision instead of blocking.
6. **Produce related assets as families.** Reuse the approved target as an edit/reference input.
   Keep palette, view, proportions, lighting, outline, and texture density invariant. Generate
   small coherent batches; avoid unrelated one-off prompts that drift.
7. **Normalize deterministically.** Crop, size, anchor, slice, name, compress, and check alpha with
   ordinary image/DCC tools. Never trust generated grids, transparency, seams, pivots, topology,
   or dimensions without inspection. Use the bundled scripts for raster QA and contact sheets.
8. **Import with engine-native settings.** Set filtering, mipmaps, pixels-per-unit/world scale,
   color space, compression, sprite slicing, texture types, materials, and collision deliberately.
   Read the relevant engine skill before editing engine files.
9. **Validate in context.** Inspect a contact sheet and the actual game at native resolution.
   Check silhouette, scale, animation stability, seams, legibility, palette, collision fit, memory,
   and compression artifacts. Iterate on the source asset, not only on runtime compensations.
10. **Record provenance.** Keep the source URL/tool, license or generation note, edit history, and
    restrictions beside the manifest. Preserve embedded provenance metadata when the pipeline can.
11. **Finish with the checks.** Run `scripts/asset_report.py` over every file in the batch with
    the manifest's size, alpha and colour limits and `--json`; it must exit 0. Build a contact
    sheet with `scripts/build_preview_sheet.py` and look at it. Confirm every shipped manifest
    entry has a source, licence and `technical_checks_passed: true`. Then ask the user to view
    the assets in the running game at native resolution and report anything that does not read.

## Choose the production path

| Need | Default path |
|------|--------------|
| Existing asset needs a controlled change | Edit the original/reference; state what must remain unchanged |
| New 2D visual family | Approve seed → generate/source family → normalize → preview → import |
| True pixel art | Use generated work as a draft; enforce grid, palette, clusters, and frames with pixel tools |
| Tileable surface or tileset | Produce a small family; repair seams; test repeated 3×3 before approval |
| UI art or icons | Keep text and interaction code-native; prefer SVG/vector for simple geometric symbols |
| 3D model or material | Use concepts as reference; author/clean in a DCC; validate topology, UVs, scale, pivots, and LODs |
| No generation/edit tool is available | Build the brief and manifest; source licensed assets or keep explicit greybox placeholders |
| Audio asset | Route sound implementation and mixing to `audio-design`; still track source/license in the manifest |

## Image-generation handoff

When a capable image generation or editing tool is installed, use it for live visual creation. If
the workspace exposes an `imagegen` skill, read and follow it for the actual generation/edit call;
this skill owns the game-art brief, constraints, normalization, and acceptance gates. Generation
APIs usually bill per image: tell the user the batch size and ask before large or repeated runs.

Build prompts from these blocks:

```text
ROLE/PURPOSE: production asset for [gameplay role]
SUBJECT: [specific object/character and action]
VIEW: [orthographic/top-down/side/three-quarter], [camera and facing]
ART DIRECTION: [shape language], [palette roles], [materials], [edge treatment]
GAME-SCALE READ: [silhouette and focal details that must survive at WxH]
TECHNICAL OUTPUT: [dimensions/aspect], [transparent or scene background], [frame/slot count]
LOCKS: preserve [identity, proportions, palette, costume, lighting, line weight]
EXCLUDE: text, labels, mockup frames, scenery, duplicate objects, cropped edges, signatures
```

For edits, say both what changes and what stays fixed. Ask for transparent output through the
tool's native transparency option when available, then verify the alpha channel—prompt wording
alone does not guarantee transparency.

## Raster QA recipes

Inspect constraints and emit a machine-readable report. `--require-alpha` also fails an RGBA file
whose every pixel is opaque, which is how a baked background or fake checkerboard shows up:

```bash
python scripts/asset_report.py assets/player-idle.png \
  --expect-size 64x64 --require-alpha --max-colors 48 --json
```

Build a nearest-neighbor contact sheet over a checkerboard:

```bash
python scripts/build_preview_sheet.py output/player/*.png \
  --out output/player-preview.png --columns 4 --cell-size 192
```

Run script paths relative to this skill directory, or resolve the installed skill path first.
Both scripts need Python and Pillow (see Version notes). Install the only dependency with
`python -m pip install -r scripts/requirements.txt` when it is not already available.
`asset_report.py` exits 1 when any explicit constraint fails, so it can gate a build.

## Quality gates

- **Cohesion:** related assets share palette roles, line/edge treatment, view, light direction,
  scale, and detail density.
- **Gameplay read:** silhouettes and state changes remain clear at native resolution, in motion,
  and over real backgrounds.
- **Technical fit:** exact size/frame count, usable alpha, stable anchors/pivots, correct color
  space/filtering, no clipped content, no accidental labels or baked mockup chrome.
- **Animation:** identity, volume, proportions, costume, facing, and baseline do not drift; timing
  and anticipation read in an in-engine preview.
- **Tiles/backgrounds:** required edges tile without seams; repetition is tolerable; parallax
  layers have intentional depth and no baked collision cues.
- **3D:** transforms, scale, pivot, normals, UVs, materials, topology, rig, collision proxies,
  LODs, and runtime format are checked rather than inferred from a render.
- **Rights:** every shipped file has recorded provenance and terms compatible with the project.

Do not call an asset production-ready from a prompt result alone. Approval requires the relevant
technical checks plus an in-engine or native-scale visual inspection.

## Gotchas

- **Fake transparency.** Image models often paint a grey-and-white checkerboard or a flat
  backdrop instead of alpha. `asset_report.py --require-alpha` fails a file with no alpha
  channel or with every pixel opaque; remove the background with a real matte, never by trusting
  the prompt.
- **Halos around cut-outs.** Semi-transparent edges keep the old background colour and show as a
  light or dark fringe in the engine. Bleed edge colour outward into transparent pixels (or
  export premultiplied when the engine expects it) and check over a contrasting background.
- **Pseudo pixel art.** Generated "pixel art" has blended in-between colours, off-grid pixels and
  hundreds of near-duplicates. Downscale to the true grid with nearest-neighbour, quantize to
  the palette, then check `--max-colors`.
- **Mipmaps or linear filtering on pixel art** blur and shimmer it. Nearest filtering, no
  mipmaps, integer camera scale.
- **Sprite sheets that do not slice.** Generated grids drift by a few pixels per cell and frames
  change size. Re-slice onto a fixed canvas with one shared anchor (usually bottom-centre) before
  import.
- **Character drift between frames or batches** (head size, outline width, palette). Edit from
  the approved seed each time instead of from the last output.
- **Texture bleeding at tile and atlas edges** under zoom or mipmaps. Pad or extrude tiles by 1-2
  px and test a 3x3 repeat at the game's camera scale.
- **Block-compression sizes.** BC and ETC2 compress in 4x4 blocks (ASTC in its chosen block
  size); other dimensions get padded, or rejected by stricter paths such as WebGL compressed
  textures. Keep textures at multiples of 4, and powers of two where mipmaps are needed.
- **Normal and data maps imported as sRGB** shade wrongly. Only colour textures are sRGB.
- **Generated text and logos** come out as near-letters and invite trademark trouble. Keep text
  code-native and remove marks before approval.
- **Licences that do not survive packing.** Attribution and terms must follow the asset through
  atlases and renames; record them in the manifest, not in a filename.
- **Undeclared AI content.** Steam's Content Survey asks about AI-generated content that ships
  with the game; answer it from the manifest's `source.kind`, so record generation per asset.

## References

- For visual-system decisions and maintaining consistency, read
  `references/art-direction.md`.
- For sprites, animation strips, tiles, backgrounds, UI art, and engine import settings, read
  `references/raster-pipeline.md`.
- For concept-to-mesh, textures, glTF/GLB, LOD, collision, and runtime validation, read
  `references/three-d-pipeline.md`.
- For licenses, generated-media records, and provenance, read
  `references/provenance.md`.

## Related skills

- `game-ui-ux` for layout, navigation, readability, and accessible interaction.
- `game-feel`, `shader-programming`, and `audio-design` for presentation after the source art fits.
- Engine import/rendering skills such as `godot-tilemap`, `unity-tilemap-2d`,
  `pixijs-rendering`, and `threejs-gltf-loading`.

## Version notes

Last verified: 2026-11-11.

- Scripts: Python 3.10+ with Pillow 10 to 13 (`scripts/requirements.txt` pins `Pillow>=10,<14`).
  Pillow 13.0.0 is the latest release and requires Python 3.11+
  (https://pypi.org/project/pillow/).
- Steam Content Survey: the generative AI section separates pre-generated content (made during
  development and shipped) from live-generated content (made while the game runs, which also
  needs a description of guardrails); AI tools used only for efficiency are not its focus
  (https://partner.steamgames.com/doc/gettingstarted/contentsurvey).
- Engine import settings in `references/raster-pipeline.md` target Godot 4.7 and Unity 6.3 LTS.
