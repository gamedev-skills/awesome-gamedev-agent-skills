---
name: godot-shaders
description: >
  Godot 4.7 Shading Language syntax and pipeline: canvas_item, spatial and particle shaders,
  built-ins, ShaderMaterial wiring, a headless compile check and 3.x porting. Use for a .gdshader,
  a SHADER ERROR, shader parameters set from GDScript, or an effect that looks washed out or sorts
  wrong. Not for effect maths such as dissolve or outline (`shader-programming`).
---

# Godot Shaders (4.x)

Write `.gdshader` files in the Godot Shading Language, wire them to materials, and prove
they compile. Targets **Godot 4.7** (see Version notes). The effect technique (the maths
of a dissolve, outline, toon ramp) lives in `shader-programming`; this skill covers
Godot's syntax, built-ins and pipeline.

## When to use

- Writing or porting `.gdshader` code, fixing a `SHADER ERROR`, wiring a
  `ShaderMaterial`, picking render modes, or setting uniforms from code.

**When *not* to use:** cross-engine shading technique → `shader-programming`;
`StandardMaterial3D`, lights and environment → `godot-3d-essentials`. `GPUParticles`
node properties (as opposed to a `particles` shader) are outside this skill.

## Core workflow

1. **Pick the shader type** on the first line: `shader_type canvas_item;` for anything
   `CanvasItem` (Sprite2D, TextureRect, Control) or `shader_type spatial;` for 3D meshes.
   `particles`, `sky` and `fog` exist too.
2. **Write the output the type expects:** `COLOR` in `canvas_item`; `ALBEDO`, `EMISSION`,
   `ROUGHNESS`, `METALLIC` in `spatial`. `vertex()` moves geometry; `light()` replaces
   lighting.
3. **Expose tunables as `uniform`s** with hints (`source_color` for colors, `hint_range`
   for sliders) so they show in the Inspector and are color-managed.
4. **Wire the material.** In a `.tscn` this is plain text, so no Inspector clicks are
   needed:

   ```ini
   [ext_resource type="Shader" path="res://fx/scroll.gdshader" id="1_fx"]

   [sub_resource type="ShaderMaterial" id="ShaderMaterial_fx"]
   shader = ExtResource("1_fx")
   shader_parameter/scroll_speed = 0.5

   [node name="Water" type="Sprite2D" parent="."]
   material = SubResource("ShaderMaterial_fx")
   ```

   From code: `material.set_shader_parameter("scroll_speed", 0.5)`.
5. **Check before you finish.**
   - Compile every shader headless with Pattern 4, then grep the log:

     ```bash
     godot --headless --path . --script res://tests/compile_shaders.gd > shaders.log 2>&1
     grep -nE "SHADER ERROR|Shader compilation failed" shaders.log   # no output = pass
     ```

     Headless uses a dummy renderer that still runs Godot's shader compiler, so syntax,
     unknown built-ins, wrong output variables and bad hints all show up. It does not run
     the GPU driver, so ask the user to open the scene with the project's renderer
     (Forward+, Mobile or Compatibility) and report how it looks and any errors in the
     Output panel.
   - If you wired a material in a `.tscn`, also run the `godot-nodes-scenes` skill's
     `scripts/check_godot_project.py <project-dir>` to confirm the `ext_resource` path.
   - With no Godot binary (`godot`, `godot4` or `$GODOT_BIN`), ask the user to run the
     command above and paste `shaders.log`.

## Patterns

### 1. canvas_item: tint and scrolling UV

```glsl
shader_type canvas_item;

uniform vec4 tint : source_color = vec4(1.0);
uniform float scroll_speed : hint_range(0.0, 2.0) = 0.3;

void fragment() {
    vec2 uv = UV + vec2(TIME * scroll_speed, 0.0);
    COLOR = texture(TEXTURE, uv) * tint;          // TEXTURE = the node's own texture
}
```

The node's texture must repeat for the scroll to wrap: set `texture_repeat` on the
CanvasItem, or sample your own `uniform sampler2D tex : repeat_enable;`.

### 2. spatial: emissive rim on an opaque material

```glsl
shader_type spatial;

uniform vec4 base_color : source_color = vec4(0.2, 0.5, 1.0, 1.0);
uniform vec3 rim_color : source_color = vec3(0.6, 0.8, 1.0);
uniform float rim_power : hint_range(0.5, 8.0) = 3.0;

void fragment() {
    ALBEDO = base_color.rgb;
    float rim = pow(1.0 - clamp(dot(NORMAL, VIEW), 0.0, 1.0), rim_power);  // view space
    EMISSION = rim_color * rim;                   // no ALPHA write: stays opaque
}
```

### 3. Screen-reading post effect (4.x hint, not SCREEN_TEXTURE)

```glsl
shader_type canvas_item;

uniform sampler2D screen_tex : hint_screen_texture, filter_linear_mipmap;
uniform float blur : hint_range(0.0, 4.0) = 1.0;

void fragment() {
    vec2 px = SCREEN_PIXEL_SIZE * blur;
    vec4 c = texture(screen_tex, SCREEN_UV);
    c += texture(screen_tex, SCREEN_UV + vec2(px.x, 0.0));
    c += texture(screen_tex, SCREEN_UV - vec2(px.x, 0.0));
    COLOR = c / 3.0;
}
```

### 4. Headless compile check for every `.gdshader`

```gdscript
# res://tests/compile_shaders.gd
extends SceneTree

func _initialize() -> void:
    var paths := _find("res://", "gdshader")
    for path in paths:
        print("compiling ", path)                 # a SHADER ERROR prints right after this
        var shader := load(path) as Shader
        shader.get_shader_uniform_list()         # forces the compile; load() alone is lazy
    print("Compiled %d shaders" % paths.size())
    quit(0)

func _find(dir: String, ext: String) -> PackedStringArray:
    var found := PackedStringArray()
    for file in DirAccess.get_files_at(dir):
        if file.get_extension() == ext:
            found.append(dir.path_join(file))
    for sub in DirAccess.get_directories_at(dir):
        if not sub.begins_with("."):             # skips .godot/ and other hidden folders
            found.append_array(_find(dir.path_join(sub), ext))
    return found
```

Shaders embedded in a `.tscn` (`[sub_resource type="Shader"]`) are not files; cover them
by smoke-running that scene (`--scene res://... --quit-after 10`) and grepping the same way.

## Gotchas

- **3.x → 4.x renames.** `SCREEN_TEXTURE` and `DEPTH_TEXTURE` are removed; declare
  `uniform sampler2D x : hint_screen_texture;` (or `hint_depth_texture`) and sample with
  `SCREEN_UV`. Forward+ also offers `hint_normal_roughness_texture`. `hint_color`/`hint_albedo`
  → `source_color`; `hint_white`/`hint_black` → `hint_default_white`/`hint_default_black`.
  In `canvas_item` `vertex()`, 3.x's `MODELVIEW_MATRIX` is now `MODEL_MATRIX` /
  `CANVAS_MATRIX` / `SCREEN_MATRIX`.
- **Wrong output variable.** In a spatial `fragment()`, `COLOR` is the read-only vertex
  color, so assigning to it is a compile error; write `ALBEDO`.
- **Color uniforms without `source_color`** are treated as raw linear values and look
  washed out or dark.
- **Object drawn in the wrong order, casts no shadow, or skips SSAO (3D)** → the spatial
  shader reads or writes `ALPHA`, which moves the whole material to the transparent
  pipeline even if the value is always `1.0`. For hard cut-outs set
  `ALPHA_SCISSOR_THRESHOLD`, which stays in the opaque pass.
- **Sampling outside [0,1] UV clamps** unless the sampler uniform has `repeat_enable` (or,
  for `TEXTURE`, the node's `texture_repeat` is on).
- **Effect jumps once an hour** → `TIME` wraps at `rendering/limits/time/time_rollover_secs`
  (3600 by default). Pick periods that divide the rollover, or feed your own time uniform.
- **`load()` alone does not compile a shader.** The `Shader` creates its GPU-side object on
  first use, which is why Pattern 4 calls `get_shader_uniform_list()`.
- **`discard` breaks early depth testing** and costs more on some GPUs; prefer alpha where
  the blend mode allows.

## References

- Read `references/shading-language.md` when you need the built-ins per shader type,
  render-mode names, sampler filter/repeat qualifiers, `varying`, `vertex()`
  displacement, a custom `light()` function, 2D normal maps, or performance rules.

## Related skills

- `shader-programming` for the effect technique (dissolve, outline, fresnel, vignette).
- `godot-3d-essentials` for materials, environment and where spatial shaders live.
- `godot-ui-control` for applying shaders to UI.
- `godot-gdscript-headless-testing` to run Pattern 4 in CI.

## Version notes

Last verified: 2026-11-11 against Godot 4.7.2-stable (released 2026-08-18).

- The headless (dummy) renderer compiles shaders with the engine's shader compiler and
  prints `SHADER ERROR:` lines; a `Shader` resource compiles lazily on first use.
- The render modes and built-ins listed in the reference exist in 4.7.2's
  `shader_types.cpp`.

Sources: [dummy material_storage.cpp @ 4.7.2-stable](https://github.com/godotengine/godot/blob/4.7.2-stable/servers/rendering/dummy/storage/material_storage.cpp),
[shader.cpp @ 4.7.2-stable](https://github.com/godotengine/godot/blob/4.7.2-stable/scene/resources/shader.cpp),
[shader_types.cpp @ 4.7.2-stable](https://github.com/godotengine/godot/blob/4.7.2-stable/servers/rendering/shader_types.cpp),
[Shading language](https://docs.godotengine.org/en/stable/tutorials/shaders/shader_reference/shading_language.html),
[Upgrading from Godot 3 to 4](https://docs.godotengine.org/en/stable/tutorials/migrating/upgrading_to_godot_4.html).
