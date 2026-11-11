# Godot Shading Language reference (Godot 4.7)

Depth companion to `godot-shaders`. The language is GLSL-like with engine built-ins.

Contents: shader types and processor functions · common built-ins · uniform hints ·
render modes · varying · vertex() displacement · custom light() · 2D normal maps ·
visual shaders · performance notes

## Shader types and processor functions

| `shader_type` | Used by | Main functions | Key output writes |
|---------------|---------|----------------|-------------------|
| `canvas_item` | 2D `CanvasItem` materials | `vertex`, `fragment`, `light` | `COLOR` |
| `spatial` | 3D `Mesh`/surface materials | `vertex`, `fragment`, `light` | `ALBEDO`, `EMISSION`, `ALPHA`, `ROUGHNESS`, `METALLIC`, `NORMAL_MAP` |
| `particles` | `GPUParticles` process | `start`, `process` | `VELOCITY`, `TRANSFORM`, `COLOR` |
| `sky` | `Sky` material | `sky` | `COLOR` |
| `fog` | `FogVolume` | `fog` | `DENSITY`, `ALBEDO`, `EMISSION` |

## Common built-ins

canvas_item: `UV`, `COLOR`, `TEXTURE`, `TEXTURE_PIXEL_SIZE`, `SCREEN_UV`,
`SCREEN_PIXEL_SIZE`, `VERTEX`, `TIME`, `POINT_COORD`, and in `vertex()` `MODEL_MATRIX`,
`CANVAS_MATRIX`, `SCREEN_MATRIX` (3.x's `MODELVIEW_MATRIX` no longer exists).

spatial: `VERTEX` (model/local), `NORMAL`, `TANGENT`, `UV`, `UV2`, `VIEW`, `ALBEDO`,
`ALPHA`, `EMISSION`, `ROUGHNESS`, `METALLIC`, `SPECULAR`, `NORMAL_MAP`, `TIME`,
`CAMERA_POSITION_WORLD`, `MODEL_MATRIX`, `VIEW_MATRIX`, `PROJECTION_MATRIX`, `FRAGCOORD`.

## Uniform hints (4.x)

```glsl
uniform float speed : hint_range(0.0, 1.0) = 0.5;
uniform float gain  : hint_range(0.0, 2.0, 0.01);     // min, max, step
uniform vec4 col    : source_color = vec4(1.0);       // sRGB color picker
uniform sampler2D tex : source_color, filter_linear_mipmap, repeat_enable;
uniform sampler2D screen_tex : hint_screen_texture, filter_linear_mipmap;
uniform sampler2D depth_tex  : hint_depth_texture;
uniform sampler2D normal_rough : hint_normal_roughness_texture;
group_uniforms Movement;                               // Inspector grouping
uniform float amplitude = 1.0;
```

Sampler filter/repeat qualifiers: `filter_nearest`, `filter_linear`,
`filter_nearest_mipmap`, `filter_linear_mipmap`, `repeat_enable`, `repeat_disable`.

Set from code: `material.set_shader_parameter("name", value)`;
read with `get_shader_parameter("name")`.

## Render modes

First-line modifiers after the type, comma-separated:

- spatial: `unshaded`, `cull_disabled`, `cull_front`, `depth_draw_opaque`,
  `depth_test_disabled`, `blend_add`, `blend_mul`, `diffuse_toon`, `specular_toon`,
  `world_vertex_coords`, `vertex_lighting`, `shadows_disabled`, `ambient_light_disabled`.
- canvas_item: `blend_mix` (default), `blend_add`, `blend_sub`, `blend_mul`,
  `blend_premul_alpha`, `unshaded`, `light_only`.

```glsl
shader_type spatial;
render_mode unshaded, cull_disabled;
```

## varying (pass data vertex -> fragment)

```glsl
varying vec3 world_pos;
void vertex()   { world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz; }
void fragment() { ALBEDO = fract(world_pos); }
```

## vertex() displacement

```glsl
void vertex() {
    VERTEX.y += sin(VERTEX.x * 4.0 + TIME * 2.0) * 0.1;   // wave the mesh
}
```

## Custom light() (toon ramp example, spatial)

```glsl
void light() {
    float ndl = dot(NORMAL, LIGHT);
    float ramp = step(0.0, ndl);                 // hard two-tone
    DIFFUSE_LIGHT += ALBEDO * LIGHT_COLOR.rgb * ramp * ATTENUATION;
}
```

## 2D normal maps

For lit 2D, write `NORMAL_MAP` in a `canvas_item` fragment (or assign a normal map on the
node) and add a `Light2D`/`PointLight2D` to the scene; `light()` controls the response.

## Visual shaders

`VisualShader` lets you build the same graphs node-by-node and exports to this language.
Useful for iteration; the generated code is standard Godot Shading Language. Convert to a
text `.gdshader` when you need precise control or version it in source.

## Performance notes

- Texture fetches and `discard` are the most expensive common operations; minimize both.
- Branch on uniforms (constant per draw) is cheap; branch on per-pixel values can be slow.
- Precompute in `vertex()` and pass via `varying` when a value is linear across a triangle.
- Prefer `mix()`, `step()`, `smoothstep()`, `clamp()` over `if` for per-pixel selection.
