---
name: godot-tilemap
description: >
  Godot 4.7 tile maps with TileMapLayer and TileSet: atlas sources, data layers, terrain
  autotiling and set_cell or local_to_map at runtime. Use for 2D tile levels in Godot, tiles with
  no collision, a click on the wrong cell or porting a deprecated TileMap. Not for Unity
  (`unity-tilemap-2d`), tile art (`create-game-assets`) or generation (`procedural-gen`).
---

# Godot TileMap (4.7 TileMapLayer)

Author tile levels with `TileMapLayer` + `TileSet`, attach per-tile collision and data,
autotile with terrains, and edit cells at runtime. Targets **Godot 4.7**, where
`TileMapLayer` replaces the deprecated `TileMap` node (see Version notes).

## When to use

- 2D levels on a tile grid, configuring a `TileSet` (collision, navigation, custom data,
  terrains), or reading/writing tiles from code.
- Migrating a `TileMap` node (one node, many layers) to `TileMapLayer` nodes.

**When *not* to use:** moving the player across tiles → `godot-2d-movement`; general
bodies and raycasts → `godot-physics`; generation algorithms → `procedural-gen`; level
design practice → `level-design`; 3D grids → `godot-3d-essentials` (GridMap).

## Core workflow

1. **One `TileMapLayer` per layer** (background, walls, foreground), grouped under a
   `Node2D`. All layers share one `TileSet` saved as an external `.tres`.
2. **Build the TileSet.** The TileSet editor is click-only, so when you cannot drive the
   editor, generate the `.tres` with a headless tool script (Pattern 1) and keep that
   script in the repo. Otherwise, ask the user to make the change in the editor and
   report the source id, atlas coordinates and layer names.
3. **Add data layers on the TileSet**: physics layers (collision polygons plus their
   collision layer/mask bits), navigation layers, occlusion, and typed custom data layers
   (`damage: int`, `is_ladder: bool`).
4. **Place tiles from code** with `set_cell`, `set_cells_terrain_connect` or
   `set_cells_terrain_path`. The cells in a `.tscn` are an encoded `tile_map_data`
   byte array, so never edit them by hand; write a generator script or ask the user to
   paint in the editor.
5. **Turn on per-layer collision/navigation** with `collision_enabled` /
   `navigation_enabled` on each `TileMapLayer`.
6. **Check before you finish.**
   - Run the `godot-nodes-scenes` skill's `scripts/check_godot_project.py <project-dir>`
     to catch a TileSet `.tres` whose texture or script path is broken.
   - Prove the tiles behave with a headless test (Pattern 4): on a fresh checkout run
     `godot --headless --path . --import` first so the tile texture is imported, then
     `godot --headless --path . --script res://tests/test_tiles.gd`, and read the exit
     code. With no Godot binary (`godot`, `godot4` or `$GODOT_BIN`), ask the user to run
     it and paste the output. For a visual check, ask the user to run
     `godot --path . --debug-collisions` and report whether walls show shapes.

## Patterns

### 1. Generate a TileSet `.tres` in code

```gdscript
# res://tools/make_tileset.gd
# Run: godot --headless --path . --script res://tools/make_tileset.gd
extends SceneTree

func _initialize() -> void:
    var tile_set := TileSet.new()
    tile_set.tile_size = Vector2i(16, 16)
    tile_set.add_physics_layer()
    tile_set.set_physics_layer_collision_layer(0, 1 << 1)   # bit 2 ("walls")
    tile_set.add_custom_data_layer()
    tile_set.set_custom_data_layer_name(0, "damage")
    tile_set.set_custom_data_layer_type(0, TYPE_INT)

    var atlas := TileSetAtlasSource.new()
    atlas.texture = load("res://art/tiles.png")
    atlas.texture_region_size = Vector2i(16, 16)
    tile_set.add_source(atlas, 0)                  # add before creating tiles
    atlas.create_tile(Vector2i(2, 1))              # column 2, row 1 of the texture
    var wall := atlas.get_tile_data(Vector2i(2, 1), 0)
    wall.add_collision_polygon(0)
    wall.set_collision_polygon_points(0, 0, PackedVector2Array([
        Vector2(-8, -8), Vector2(8, -8), Vector2(8, 8), Vector2(-8, 8)]))  # cell-centred
    wall.set_custom_data("damage", 0)

    var err := ResourceSaver.save(tile_set, "res://tiles/world_tileset.tres")
    print("saved tileset: ", error_string(err))
    quit(0 if err == OK else 1)
```

Add the source to the TileSet before `create_tile`, so the tile's data knows the TileSet's
physics and custom data layers. Polygon points are relative to the cell centre.

### 2. Mouse position to a cell, then read custom data

```gdscript
extends TileMapLayer

func _unhandled_input(event: InputEvent) -> void:
    if event is InputEventMouseButton and event.pressed:
        # event.position is in viewport pixels and ignores Camera2D scroll/zoom.
        var local_event := make_input_local(event) as InputEventMouseButton
        var cell := local_to_map(local_event.position)
        var data := get_cell_tile_data(cell)       # TileData or null
        if data:
            var dmg: int = data.get_custom_data("damage")
            print("Cell %s deals %d damage" % [cell, dmg])
```

### 3. Place, erase and autotile at runtime

```gdscript
func place_wall(cell: Vector2i) -> void:
    set_cell(cell, 0, Vector2i(2, 1))     # source 0, atlas tile at column 2, row 1

func dig(cell: Vector2i) -> void:
    erase_cell(cell)                      # same as set_cell(cell, -1)

func fill_with_grass(cells: Array[Vector2i]) -> void:
    set_cells_terrain_connect(cells, 0, 0, true)   # terrain set 0, terrain 0
```

### 4. Headless test: a placed wall has collision and data

```gdscript
# res://tests/test_tiles.gd
extends SceneTree

func _initialize() -> void:
    var layer := TileMapLayer.new()
    layer.tile_set = load("res://tiles/world_tileset.tres")
    root.add_child(layer)
    layer.set_cell(Vector2i(0, 0), 0, Vector2i(2, 1))
    var data := layer.get_cell_tile_data(Vector2i(0, 0))
    var failed := 0
    if data == null:
        failed += 1
        push_error("wall tile missing: wrong source id or atlas coords?")
    elif data.get_collision_polygons_count(0) == 0:
        failed += 1
        push_error("wall tile has no collision polygon on physics layer 0")
    print("Results: %d failed" % failed)
    quit(1 if failed > 0 else 0)
```

## Gotchas

- **`TileMap` node is deprecated since 4.3.** Use one `TileMapLayer` per layer. Old calls
  with a leading `layer` argument (`set_cell(layer, ...)`) do not apply to `TileMapLayer`.
- **`local_to_map` needs layer-local coordinates.** Convert a world position with
  `to_local(...)` first. A mouse event's `position` is in viewport pixels, so it breaks as
  soon as a `Camera2D` scrolls or zooms; use `make_input_local(event)` or
  `get_local_mouse_position()`.
- **`get_cell_tile_data` returns `null`** for empty cells and non-atlas sources; check
  before `get_custom_data`.
- **Custom data is typed and named.** Reading a layer name that doesn't exist errors;
  define the layer on the TileSet first.
- **"Cannot create tile. The tile is outside the texture..."** → the atlas has no texture
  yet, the coordinates fall outside it, or a tile already covers that space. Set
  `texture` and `texture_region_size` before `create_tile`.
- **Terrains need every combination defined.** `set_cells_terrain_connect` places odd or
  placeholder tiles when the TileSet's peering bits are incomplete.
- **Runtime edits are batched** to the end of the frame. Call `update_internals()` only if
  you must read updated internals immediately (expensive in loops).
- **Collision not working?** Check `collision_enabled` on the layer, that the tile has a
  polygon on a physics layer, and that the physics layer's bits match your bodies' masks.

## References

- Read `references/tileset-and-terrains.md` when you need atlas vs scene-collection
  sources, the per-tile data layer types, terrain set modes and painting, coordinate
  helpers, Y-sorting, runtime tile-data overrides, or the TileMap-to-TileMapLayer
  migration steps.

## Related skills

- `godot-2d-movement` for characters that walk on these tiles.
- `godot-physics` for the collision layers/masks tile collisions take part in.
- `procedural-gen` for generating the cell layout.
- `create-game-assets` for drawing the tile sheet.
- `level-design` / `roguelike` for design practice and grid-based genres.

## Version notes

Last verified: 2026-11-11 against Godot 4.7.2-stable (released 2026-08-18).

- `TileMap` has been deprecated in favor of `TileMapLayer` since 4.3.
- `TileMapLayer.tile_map_data` is stored as a `PackedByteArray` in scenes.

Sources: [TileMapLayer @ 4.7.2-stable](https://github.com/godotengine/godot/blob/4.7.2-stable/doc/classes/TileMapLayer.xml),
[TileSet @ 4.7.2-stable](https://github.com/godotengine/godot/blob/4.7.2-stable/doc/classes/TileSet.xml),
[TileSetAtlasSource @ 4.7.2-stable](https://github.com/godotengine/godot/blob/4.7.2-stable/doc/classes/TileSetAtlasSource.xml),
[tile_map_layer.cpp @ 4.7.2-stable](https://github.com/godotengine/godot/blob/4.7.2-stable/scene/2d/tile_map_layer.cpp),
[Using TileMaps](https://docs.godotengine.org/en/stable/tutorials/2d/using_tilemaps.html).
