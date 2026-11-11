---
name: unity-tilemap-2d
description: >
  Build and script 2D tilemaps in Unity 6.3 LTS: the Grid + Tilemap components, the Tile Palette,
  tilemap colliders, rule tiles, and runtime SetTile/GetTile painting. Use when painting tile
  levels, adding a TilemapCollider2D, using rule or animated tiles, generating tilemaps from
  code, or when the user mentions Unity tilemap, tile palette, rule tile, or Grid.
---

# Unity 2D Tilemap

Author and script tile-based 2D levels in Unity 6.3 LTS with the `Grid`/`Tilemap` system, the Tile
Palette, colliders, and runtime painting. Targets **Unity 6.3 LTS (6000.3)**.

> **Package note:** the Tilemap runtime types (`Grid`, `Tilemap`, `Tile`, `TilemapCollider2D`)
> are built in. The Tile Palette and its default brush come from the **2D Tilemap Editor** core
> package (`com.unity.2d.tilemap`): the 2D template includes it, other projects add it in Package
> Manager. **Rule Tiles, Animated Tiles, and the extra brushes (Random, Line, GameObject,
> Group) live in the separate "2D Tilemap Extras" package (`com.unity.2d.tilemap.extras`,
> 6.0.x for Unity 6.3)** — install it via Package Manager before using `RuleTile`.

## When to use

- Use when laying out a 2D level by painting tiles, setting up a `Grid` + `Tilemap`, adding
  collision to the map, using auto-tiling Rule Tiles, or generating/editing tiles from script.
- Use when scenes contain a `Grid` with `Tilemap` children, or `*.asset` tile/palette files.

**When _not_ to use:** level _design_ practice (pacing, blockout, layout principles) →
`level-design`. 3D tile/grid placement → Unity's own 3D tooling (ProBuilder / grid brushes; no dedicated skill here). The platformer character that
moves over the tiles → `platformer` / `unity-physics`.

## Core workflow

1. **Create the grid:** GameObject → 2D Object → Tilemap → Rectangular (the `Grid`'s **Cell
   Layout** also offers Hexagonal and Isometric for hex/iso levels). This makes a `Grid`
   with a child `Tilemap` (+ `TilemapRenderer`). Use one Tilemap per layer (background,
   ground, foreground) and set each renderer's sorting.
2. **Open the Tile Palette** (Window → 2D → Tile Palette), drag in a sliced sprite sheet to
   create `Tile` assets, then paint with the brush tools.
3. **Add collision** to the solid layer: `TilemapCollider2D`. For one merged collider (far
   cheaper and gap-free), also add `CompositeCollider2D` (+ a `Rigidbody2D` set to **Static**)
   and set the tilemap collider's **Composite Operation** to **Merge**.
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
  static `Rigidbody2D` and set Composite Operation to **Merge** to merge the whole layer into
  one smooth shape.
- **No "Used By Composite" checkbox, or an obsolete warning on `usedByComposite`** — Unity 6
  replaced it with **Composite Operation** (`Collider2D.compositeOperation`). Old
  `usedByComposite = true` maps to `CompositeOperation.Merge`; write that instead.
- **Small gaps remain between merged tiles** — raise the Tilemap Collider 2D's **Extrusion
  Factor** so neighbouring tile shapes fall within the Composite Collider 2D's Vertex Distance.
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

- Primary docs: Unity Manual "Tilemap component reference"
  (`https://docs.unity.com/en-us/engine/6000.3/manual/unity2d/tilemaps/reference/tilemap`),
  `ScriptReference/Tilemaps.Tilemap`, `ScriptReference/Collider2D-compositeOperation`, the
  Manual "Tilemap Collider 2D component reference", and the 2D Tilemap Extras package manual
  (`https://docs.unity3d.com/Packages/com.unity.2d.tilemap.extras@6.0/manual/index.html`) for
  Rule Tiles. (`@6.0` is the version that ships with Unity 6.3 LTS; the old `@1.6` docs are
  for Unity 2021-era projects.)

## Related skills

- `level-design` — engine-agnostic blockout, pacing, and tile layout practice.
- `procedural-gen` — generating the tile data (noise, RNG, dungeons) you feed to `SetTilesBlock`.
- `platformer` / `roguelike` — genres that compose this skill with movement and generation.
