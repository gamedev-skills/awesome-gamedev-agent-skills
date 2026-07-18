---
name: unity-tilemap-2d
description: >
  Build and script 2D tilemaps in Unity 6: the Grid + Tilemap components, the Tile Palette,
  tilemap colliders, rule tiles, and runtime SetTile/GetTile painting. Use when painting tile
  levels, adding a TilemapCollider2D, using rule or animated tiles, generating tilemaps from
  code, or when the user mentions Unity tilemap, tile palette, rule tile, or Grid.
license: Apache-2.0
compatibility: Unity 6 (6000.0 LTS); UnityEngine.Tilemaps. RuleTile needs the 2D Tilemap Extras package.
metadata:
  engine: unity
  category: unity
  difficulty: intermediate
---

# Unity 2D Tilemap

Author and script tile-based 2D levels in Unity 6 with the `Grid`/`Tilemap` system, the Tile
Palette, colliders, and runtime painting. Targets **Unity 6 (6000.0 LTS)**.

> **Package note:** the core Tilemap (`Grid`, `Tilemap`, `Tile`, `TilemapCollider2D`) is
> built in. **Rule Tiles, Animated Tiles, and Tile Palette brushes live in the separate
> "2D Tilemap Extras" package (`com.unity.2d.tilemap.extras`)** — install it via Package
> Manager before using `RuleTile`.

## When to use

- Use when laying out a 2D level by painting tiles, setting up a `Grid` + `Tilemap`, adding
  collision to the map, using auto-tiling Rule Tiles, or generating/editing tiles from script.
- Use when scenes contain a `Grid` with `Tilemap` children, or `*.asset` tile/palette files.

**When _not_ to use:** level _design_ practice (pacing, blockout, layout principles) →
`level-design`. 3D tile/grid placement → Unity's own 3D tooling (ProBuilder / grid brushes; no dedicated skill here). The platformer character that
moves over the tiles → `platformer` / `unity-physics`.

## Core workflow

1. **Create the grid:** GameObject → 2D Object → Tilemap → Rectangular. This makes a `Grid`
   with a child `Tilemap` (+ `TilemapRenderer`). Use one Tilemap per layer (background,
   ground, foreground) and set each renderer's sorting.
2. **Open the Tile Palette** (Window → 2D → Tile Palette), drag in a sliced sprite sheet to
   create `Tile` assets, then paint with the brush tools.
3. **Add collision** to the solid layer: `TilemapCollider2D`. For one merged collider (far
   cheaper and gap-free), also add `CompositeCollider2D` (+ a `Rigidbody2D` set to **Static**)
   and enable _Used By Composite_ on the tilemap collider.
4. **Auto-tile with Rule Tiles** (2D Tilemap Extras) so edges/corners pick the right sprite
   automatically instead of hand-placing every variant.
5. **Edit at runtime via script** with cell coordinates (`Vector3Int`): `SetTile`, `GetTile`,
   `SetTilesBlock`, converting world↔cell with the `Grid`/`Tilemap`.
6. **Verify** in Play mode: confirm collisions (Physics Debugger), sorting order, and that
   `RefreshAllTiles` ran after bulk edits.

## Patterns

### 1. Painting tiles at runtime (cell coordinates)

```csharp
using UnityEngine;
using UnityEngine.Tilemaps;

public class TilePainter : MonoBehaviour
{
    [SerializeField] private Tilemap tilemap;   // assign the target Tilemap
    [SerializeField] private TileBase groundTile;

    // World position -> cell, then place a tile.
    public void PaintAt(Vector3 worldPos)
    {
        Vector3Int cell = tilemap.WorldToCell(worldPos);
        tilemap.SetTile(cell, groundTile);
    }

    public bool IsSolid(Vector3 worldPos)
        => tilemap.GetTile(tilemap.WorldToCell(worldPos)) != null;
}
```

### 2. Bulk fill a region (faster than per-cell `SetTile`)

```csharp
// SetTilesBlock writes a whole BoundsInt in one call — use it for procedural rooms/floors.
public void FillFloor(Tilemap map, TileBase tile, int width, int height)
{
    var bounds = new BoundsInt(0, 0, 0, width, height, 1);
    var tiles  = new TileBase[width * height];
    for (int i = 0; i < tiles.Length; i++) tiles[i] = tile;
    map.SetTilesBlock(bounds, tiles);
}
```

### 3. Clearing and refreshing

```csharp
tilemap.SetTile(cell, null);   // null erases the tile at that cell
tilemap.RefreshTile(cell);     // re-evaluate just this cell's rule/animated neighbors (cheap)
// RefreshAllTiles() re-evaluates the ENTIRE map — reserve it for full regenerations, not per-edit.
```

## Pitfalls

- **`RuleTile` type not found** — it's not built in. Install the **2D Tilemap Extras** package
  (`com.unity.2d.tilemap.extras`) via Package Manager.
- **A collider per tile tanks performance / leaves seams** — add a `CompositeCollider2D` with a
  static `Rigidbody2D` and _Used By Composite_ to merge the whole layer into one smooth shape.
- **Confusing world and cell coordinates** — `SetTile`/`GetTile` take a `Vector3Int` _cell_,
  not a world position. Always convert with `WorldToCell` / `CellToWorld`.
- **Tiles render behind/in front of sprites unexpectedly** — set each `TilemapRenderer`'s
  Sorting Layer and Order in Layer; multiple tilemaps need explicit ordering.
- **Rule/animated tiles don't update after script edits** — refresh after writes, but prefer
  the targeted `RefreshTile(cell)` for a few edits; `RefreshAllTiles()` re-evaluates every tile
  on the map and stalls large levels. Reserve the full refresh for whole-map regenerations.
- **Painting onto the wrong layer** — the active target Tilemap in the Tile Palette determines
  where paint lands; check the "Active Tilemap" dropdown.

## References

- Primary docs: Unity Manual "Tilemaps"
  (`https://docs.unity3d.com/Manual/tilemaps/work-with-tilemaps/tilemap-reference.html`),
  `ScriptReference/Tilemaps.Tilemap`, and the 2D Tilemap Extras package manual
  (`https://docs.unity3d.com/Packages/com.unity.2d.tilemap.extras@1.6/manual/index.html`) for
  Rule Tiles.

## Related skills

- `level-design` — engine-agnostic blockout, pacing, and tile layout practice.
- `procedural-gen` — generating the tile data (noise, RNG, dungeons) you feed to `SetTilesBlock`.
- `platformer` / `roguelike` — genres that compose this skill with movement and generation.
