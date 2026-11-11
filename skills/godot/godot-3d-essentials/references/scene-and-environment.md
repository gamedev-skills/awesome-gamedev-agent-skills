# 3D scene & environment reference (Godot 4.7)

Depth companion to `godot-3d-essentials`.

Contents: Transform3D; Camera3D; Lights; Environment & post-processing; Materials; GridMap &
MeshLibrary; Baked lighting & probes.

## Transform3D

A `Node3D` has a `Transform3D` = `Basis` (3x3 rotation/scale) + `origin` (Vector3).

```gdscript
global_position = Vector3(1, 0, 2)
rotate_y(deg_to_rad(90))                 # rotate about local Y
rotation_degrees = Vector3(0, 45, 0)
look_at(target_global_pos, Vector3.UP)   # global-space orientation
transform = transform.translated_local(Vector3.FORWARD * 2.0)  # move along local -Z
basis = basis.orthonormalized()          # fix drift after many rotations
```

Godot 3D convention: **-Z is forward**, +Y is up, +X is right.

## Camera3D

- `projection`: `PROJECTION_PERSPECTIVE` (fov) or `PROJECTION_ORTHOGONAL` (size).
- `fov`, `near`, `far`, `current`, `make_current()`, `clear_current()`.
- `project_ray_origin(screen_pos)` / `project_ray_normal(screen_pos)` for click-to-world
  picking (combine with a physics raycast).
- `unproject_position(world_pos)` → screen position (e.g. floating health bars).
- For follow/orbit, parent the camera to a pivot `Node3D` and rotate the pivot.

## Lights

| Node | Role | Key props |
|------|------|-----------|
| `DirectionalLight3D` | Sun (parallel rays) | `shadow_enabled`, `light_energy`, `directional_shadow_mode` |
| `OmniLight3D` | Point light | `omni_range`, `light_energy`, `shadow_enabled` |
| `SpotLight3D` | Cone | `spot_range`, `spot_angle`, `shadow_enabled` |
| `AreaLight3D` (4.7+) | Rectangle (screens, light panels) | `area_size`, `area_range`, `area_attenuation`, `area_texture` |

Common: `light_color`, `light_energy`, `light_indirect_energy`, shadow bias settings.
Too many shadow-casting lights hurts performance — bake static lighting where possible.
`AreaLight3D` costs more than omni/spot lights: in Forward+ one visible area light adds cost to every
rendered object, and the Compatibility renderer cannot draw its shadows. Keep it for close-ups
and high-end targets.

## Environment & post-processing

`WorldEnvironment.environment` (an `Environment` resource):

- **Background:** `BG_CLEAR_COLOR`, `BG_COLOR`, `BG_SKY` (with a `Sky` +
  `ProceduralSkyMaterial`/`PanoramaSkyMaterial`).
- **Ambient:** `ambient_light_source` (sky/color/disabled), `ambient_light_color`,
  `ambient_light_energy`.
- **Tonemap:** `tonemap_mode` (`TONE_MAPPER_LINEAR`, `_REINHARDT`, `_FILMIC`, `_ACES`,
  `_AGX`), `tonemap_exposure`, `tonemap_white`.
- **Post:** `glow_enabled` (+ bloom/levels), `ssao_enabled`, `ssil_enabled`,
  `sdfgi_enabled` (real-time GI), `fog_enabled`/`volumetric_fog_enabled`,
  `adjustment_enabled` (brightness/contrast/saturation + color correction).

A `CameraAttributes` resource (Practical/Physical) adds DOF, auto-exposure, and exposure
controls, assigned on the camera or environment.

Renderer support (4.7 docs, "Overview of renderers"):

| Feature | Compatibility | Mobile | Forward+ |
|---|---|---|---|
| SSAO | yes | no | yes |
| SSIL, SSR, SDFGI, volumetric fog | no | no | yes |
| Fog, glow, tonemapping, adjustments | yes | yes | yes |

## Materials

`StandardMaterial3D` (PBR) key fields: `albedo_color`/`albedo_texture`, `metallic`,
`roughness`, `normal_enabled`+`normal_texture`, `emission_enabled`+`emission`,
`transparency` (`TRANSPARENCY_ALPHA`/`ALPHA_SCISSOR`), `cull_mode`, `shading_mode`
(`SHADING_MODE_PER_PIXEL` / `UNSHADED`). Apply via `MeshInstance3D.material_override` (all
surfaces) or `set_surface_override_material(i, mat)` (per surface). `ORMMaterial3D` packs
occlusion/roughness/metallic into one texture.

## GridMap & MeshLibrary

1. Build a scene where each child is a mesh + optional collision; export it as a
   `MeshLibrary` (Scene > Export As > MeshLibrary). In 4.7+ a dedicated `MeshLibrary` editor
   (like the 2D `TileSet` editor) makes adding and
   editing items much quicker.
2. Assign the `MeshLibrary` to the `GridMap.mesh_library` and set `cell_size`.
3. Paint in the editor, or from code (below). Orientation comes from
   `GridMap.get_orthogonal_index_from_basis(basis)`.

```gdscript
func gridmap_calls(grid: GridMap, cell: Vector3i, item_id: int, orientation: int) -> void:
    grid.set_cell_item(cell, item_id, orientation)
    print(grid.get_cell_item(cell))          # -1 if empty (GridMap.INVALID_CELL_ITEM)
    print(grid.get_used_cells())
    var centre := grid.map_to_local(cell)    # cell -> local position of its centre
    print(grid.local_to_map(centre) == cell) # position -> cell
    grid.clear()
```

## Baked lighting & probes

- `LightmapGI` — bake static GI into lightmaps for static geometry (mark meshes "bake").
- `ReflectionProbe` — local cubemap reflections for an area.
- `VoxelGI` / `SDFGI` — dynamic GI (heavier). Use baked lightmaps for ship-quality static
  scenes and reserve real-time GI for dynamic needs.
