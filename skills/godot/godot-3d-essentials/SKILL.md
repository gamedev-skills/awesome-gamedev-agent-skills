---
name: godot-3d-essentials
description: >
  Godot 4.7 3D scene setup: Camera3D, lights, WorldEnvironment (sky, ambient, tonemap, fog),
  StandardMaterial3D, GridMap and local vs global transforms, with a headless scene check. Use
  when a 3D scene renders black or washed out, a mesh is invisible, or a child rotates on the
  wrong axis. Not for spatial shaders (`godot-shaders`), bodies and raycasts (`godot-physics`) or
  camera feel (`camera-systems`).
---

# Godot 3D Essentials (4.x)

Assemble a 3D scene that shows what it should in the running game: a current camera, real
lights, an environment, materials and GridMap blockouts. Targets **Godot 4.7**; read
`config/features` and `rendering/renderer/rendering_method` in `project.godot` first,
because Forward+, Mobile and Compatibility differ in what they draw.

## Workflow

1. **Check the renderer** (`rendering/renderer/rendering_method`: `forward_plus`, `mobile`
   or `gl_compatibility`). Mobile and Compatibility (web, low-end) have no SDFGI, SSIL,
   screen-space reflections or volumetric fog, and Mobile also has no SSAO, so do not build
   the look on them for those targets. The reference has the renderer table.
2. **One current `Camera3D` per viewport.** Set `current = true` on the one you want.
   Godot's convention is -Z forward, +Y up.
3. **Light the scene in the scene itself.** The editor viewport's preview sun and preview
   environment (toolbar toggles) do not exist at runtime. Add a `DirectionalLight3D` and a
   `WorldEnvironment` to the main scene, or set
   `rendering/environment/defaults/default_environment`.
4. **Configure the `Environment`:** background (sky or colour), ambient source, tonemapper,
   then post effects. Pick the tonemapper before tuning light energy or glow.
5. **Materials:** `StandardMaterial3D` on `MeshInstance3D.material_override` (all surfaces)
   or `set_surface_override_material(i, mat)`; `ShaderMaterial` for custom looks.
6. **Block out with `GridMap`** and a `MeshLibrary`.
7. **Verify before you finish** (paths are relative to this skill's folder):
   - If `godot-nodes-scenes` is installed, run `python3 ../godot-nodes-scenes/scripts/check_godot_project.py <project>`
     and fix every `ERROR`.
   - Run `godot --headless --path <project> --script <this skill>/assets/check_3d_scene.gd -- res://level.tscn`
     (no scene argument means the main scene). It needs no GPU and exits 1 when there is no
     current camera, nothing lights the meshes, a sky background has no `Sky`, or a mesh is
     hidden by the camera's `cull_mask`, behind the camera or past `far`.
   - To see a frame without a GPU, render one in software with Movie Maker:
     `xvfb-run -a godot --path <project> --rendering-driver opengl3 --write-movie shots/f.png --quit-after 3 res://level.tscn`
     writes `shots/f00000000.png` and up, which you can open and inspect. This draws with
     the Compatibility renderer, so judge Forward+ looks by asking the user for a screenshot.

## Patterns

### 1. Sun and environment from code

```gdscript
func _ready() -> void:
    var sun := DirectionalLight3D.new()
    sun.rotation_degrees = Vector3(-50, -30, 0)   # pointing down: -X tilt
    sun.shadow_enabled = true
    add_child(sun)

    var env := Environment.new()
    env.background_mode = Environment.BG_SKY
    env.sky = Sky.new()
    env.sky.sky_material = ProceduralSkyMaterial.new()
    env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
    env.tonemap_mode = Environment.TONE_MAPPER_AGX
    var world_env := WorldEnvironment.new()
    world_env.environment = env
    add_child(world_env)
```

Only one `WorldEnvironment` applies per world: the first one keeps control and a later one
is ignored without a runtime message (the editor shows a node warning).

### 2. A material from code

```gdscript
func tint(mesh: MeshInstance3D, color: Color) -> void:
    var mat := StandardMaterial3D.new()
    mat.albedo_color = color
    mat.roughness = 0.6
    mesh.material_override = mat   # wins over surface and mesh materials
```

### 3. Fill a GridMap from code

```gdscript
@onready var grid: GridMap = $GridMap   # mesh_library and cell_size set on the node

func build_floor(width: int, depth: int, item_id: int) -> void:
    for x in width:
        for z in depth:
            grid.set_cell_item(Vector3i(x, 0, z), item_id)   # -1 clears a cell
```

## Gotchas

- **Fine in the editor, dark or flat in the game** → the editor preview sun and environment
  were doing the lighting. Put a light and a `WorldEnvironment` in the scene.
- **Meshes are black** → nothing lights them. With no `Environment`, Forward+ and Mobile still
  add flat ambient from `rendering/environment/defaults/default_clear_color`, but
  Compatibility adds none, so the same scene is dim grey on desktop and black on web. An
  `Environment` with ambient `Disabled` or a black colour background does the same.
- **Plain grey screen** → no current camera, so you only see the clear colour; or the camera
  sits inside a mesh, whose back faces are culled.
- **Wrong camera renders** → a camera in an instanced sub-scene also has `current = true`.
  Keep `current` on one camera, or call `make_current()` after the scene loads.
- **A mesh is missing** → its `layers` do not overlap the camera's `cull_mask`, it is past
  `far`, or an imported mesh has flipped normals (try `cull_mode = CULL_DISABLED` to test).
- **`look_at()` errors and does nothing** → the target equals the node's position, the up
  vector is parallel to the view direction (looking straight down with `Vector3.UP`), or the
  node is not in the tree yet; use `look_at_from_position()` before `add_child()`.
- **Local vs global mix-ups** → `position`/`rotation` are parent-relative; `look_at()` and
  `global_position` are world space.
- **Non-uniform scale distorts collision and lights** → scale the mesh resource or use uniform
  scale on bodies.
- **Washed-out or blown highlights** → the tonemapper is `Linear` (no tonemapping) or glow
  thresholds are low; switch to AgX or Filmic and lower `glow_intensity`.
- **GridMap places nothing** → no `MeshLibrary` assigned, or the item id is not in it.

## References

- Read `references/scene-and-environment.md` for Transform3D math, camera projection and
  picking, the light table (including AreaLight3D costs), every Environment option, material
  fields, building a `MeshLibrary`, and baked or real-time GI.
- `assets/check_3d_scene.gd` is the headless check used in step 7.

## Related skills

- `camera-systems`: orbit, follow and first-person camera feel.
- `godot-physics`: 3D bodies, CharacterBody3D, areas and raycasts.
- `godot-shaders`: spatial shaders.
- `godot-animation`: AnimationTree for 3D characters.
- `performance-optimization`: draw calls, lights, LOD and frame budget.
- `fps-shooter`: a full 3D game on top of these pieces.

## Version notes

Last verified: 2026-11-11 against the Godot 4.7.2 class reference, renderer source and a
4.7.2 headless and Movie Maker run.

- Godot 4.7.2 (August 2026) is the current stable release; 4.8 is in beta.
- `AreaLight3D` and the dedicated MeshLibrary editor are new in 4.7.
- The AgX tonemapper exists since 4.4.
- No-environment ambient: Forward+/Mobile fall back to the default clear colour
  (`render_scene_data_rd.cpp`); Compatibility has no fallback (`rasterizer_scene_gles3.cpp`).
- Sources: [Godot releases](https://github.com/godotengine/godot/releases),
  [Godot 4.7 release page](https://godotengine.org/releases/4.7),
  [Environment and post-processing](https://docs.godotengine.org/en/stable/tutorials/3d/environment_and_post_processing.html),
  [render_scene_data_rd.cpp @ 4.7.2](https://github.com/godotengine/godot/blob/4.7.2-stable/servers/rendering/renderer_rd/storage_rd/render_scene_data_rd.cpp),
  [rasterizer_scene_gles3.cpp @ 4.7.2](https://github.com/godotengine/godot/blob/4.7.2-stable/drivers/gles3/rasterizer_scene_gles3.cpp).
