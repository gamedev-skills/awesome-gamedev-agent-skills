# Shader effects and GLSL↔HLSL mapping

Contents: GLSL-to-HLSL quick reference (with matrix order and clip-space notes);
2D sprite outline; vignette; colour grading; per-engine notes (Godot, Unity URP,
Unreal, three.js, PixiJS, WGSL in browsers); performance checklist.

## GLSL ↔ HLSL quick reference

| GLSL | HLSL | Note |
|---|---|---|
| `vec2/3/4`, `mat3/4` | `float2/3/4`, `float3x3/4x4` | vectors and matrices |
| `mix(a, b, t)` | `lerp(a, b, t)` | linear interpolation |
| `fract(x)` | `frac(x)` | fractional part |
| `mod(a, b)` | `a - b * floor(a / b)` | HLSL `fmod` truncates, so it differs for negatives |
| `texture(samp, uv)` | `tex.Sample(samp, uv)` | sampler is a separate object in HLSL |
| `inversesqrt(x)` | `rsqrt(x)` | |
| `atan(y, x)` | `atan2(y, x)` | two-argument arctangent |
| `M * v` | `mul(M, v)` | same maths; `v * M` ↔ `mul(v, M)` |
| `gl_Position` / `out` color | `SV_Position` / `SV_Target` | stage outputs via semantics |
| `dFdx/dFdy` | `ddx/ddy` | screen-space derivatives |

Matrix order is about how the engine builds and uploads its matrices, not the
language: Unity's SRP shader library writes
`mul(GetObjectToWorldMatrix(), float4(positionOS, 1.0))`, the same order as
GLSL's `M * v`. When porting, keep the multiply order the source engine used and
check its constant-buffer packing (`row_major` / `column_major`) rather than
swapping the operands by reflex.

Also watch: clip-space depth range (OpenGL `-1..1`; Direct3D, Vulkan, Metal and
WebGPU `0..1`) and Y orientation (Vulkan's clip-space Y points down; texture and
framebuffer origins differ between APIs) — engines usually normalize this for
you, but it surfaces when porting raw shaders.

## 2D sprite outline (sample the alpha neighborhood)

```glsl
// Draw an outline where a transparent pixel is adjacent to an opaque one.
uniform sampler2D tex;
uniform vec2 texel_size;     // (1/width, 1/height) of the texture
uniform vec4 outline_color;
in vec2 uv;
out vec4 frag;
void main() {
    vec4 c = texture(tex, uv);
    if (c.a > 0.5) { frag = c; return; }          // inside the sprite: unchanged
    // sample 4 neighbors; if any is opaque, this empty pixel is on the border
    float a = max(max(texture(tex, uv + vec2( texel_size.x, 0)).a,
                      texture(tex, uv + vec2(-texel_size.x, 0)).a),
                  max(texture(tex, uv + vec2(0,  texel_size.y)).a,
                      texture(tex, uv + vec2(0, -texel_size.y)).a));
    frag = (a > 0.5) ? outline_color : vec4(0.0);  // border pixel -> outline
}
```

For thicker or smoother outlines, sample 8 neighbors (include diagonals) or do a
small distance-field pass. Two traps: the outline can only be drawn inside the
sprite's quad, so the texture needs a transparent margin at least as wide as the
outline (or the engine must pad the quad); and on an atlas, neighbour samples at
the frame edge read the next sprite, so clamp the UV to the frame. In Godot,
`TEXTURE_PIXEL_SIZE` gives `texel_size` directly; in a PixiJS filter, clamp with
the provided `uInputClamp`. In 3D, outlines are usually done differently: render
back-faces scaled outward along normals, or detect edges from depth/normal
discontinuities in a post-process.

## Vignette (darken the screen edges) — post-process

```glsl
// Darken pixels by distance from screen center. screen_uv is 0..1 across the view.
uniform sampler2D screen_tex;
uniform float strength = 0.6;   // 0 = none, 1 = strong
uniform float radius = 0.75;    // full darkness at this distance
in vec2 screen_uv;
out vec4 frag;
void main() {
    vec3 c = texture(screen_tex, screen_uv).rgb;
    float d = distance(screen_uv, vec2(0.5));      // 0 center .. ~0.707 corner
    float v = 1.0 - smoothstep(radius * 0.5, radius, d); // 1 in center, ->0 at edges
    frag = vec4(c * mix(1.0 - strength, 1.0, v), 1.0);
}
// smoothstep needs edge0 < edge1; smoothstep(radius, radius * 0.5, d) is undefined.
```

## Color grading via a curve (brightness/contrast/saturation)

```glsl
// Order matters: contrast around 0.5, then saturation, then brightness.
uniform sampler2D screen_tex;
uniform float brightness = 0.0;   // additive
uniform float contrast   = 1.0;   // multiplicative around mid-gray
uniform float saturation = 1.0;
in vec2 screen_uv;
out vec4 frag;
void main() {
    vec3 c = texture(screen_tex, screen_uv).rgb;
    c = (c - 0.5) * contrast + 0.5;                       // contrast
    float luma = dot(c, vec3(0.2126, 0.7152, 0.0722));    // Rec.709 luminance
    c = mix(vec3(luma), c, saturation);                   // saturation
    c += brightness;                                      // brightness
    frag = vec4(clamp(c, 0.0, 1.0), 1.0);
}
```

The luminance weights `(0.2126, 0.7152, 0.0722)` are the Rec.709 coefficients —
green dominates perceived brightness. For LUT-based grading, sample a color
lookup texture indexed by the pixel's RGB instead.

## Per-engine notes

- **Godot (4.x) — `gdshader`.** Godot's shading language is GLSL-like with a
  `shader_type` (`canvas_item` for 2D, `spatial` for 3D). It provides built-ins:
  `UV`, `COLOR`, `TIME`, `TEXTURE`, `TEXTURE_PIXEL_SIZE` (2D), `NORMAL`, `VIEW`
  (3D). The screen is not a built-in since 4.0 (`SCREEN_TEXTURE` was removed):
  declare `uniform sampler2D screen_tex : hint_screen_texture, filter_linear_mipmap;`
  and sample it with `SCREEN_UV`. Write `fragment()` / `vertex()` functions. Map
  the GLSL examples here onto those built-ins. See `godot-shaders`.
- **Unity 6.3 — ShaderLab + HLSL.** Shaders live in `.shader` files (ShaderLab
  blocks) or Shader Graph. Code is HLSL: `float4`, `lerp`, `SV_Target`. In URP,
  include `Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl`,
  declare `TEXTURE2D(_BaseMap); SAMPLER(sampler_BaseMap);`, sample with
  `SAMPLE_TEXTURE2D(_BaseMap, sampler_BaseMap, uv)` and put every material
  property in one `CBUFFER_START(UnityPerMaterial)` block so the SRP Batcher can
  batch it. `tex2D`/`sampler2D` belong to Built-in Render Pipeline shaders.
- **Unreal 5.8 — Material Editor (node graph) + HLSL.** Most authoring is visual
  nodes; Custom nodes embed HLSL. Concepts (UVs, fresnel via a Fresnel node,
  panner for UV scroll) map directly to the patterns here.
- **three.js r187.** `WebGLRenderer` runs GLSL through `ShaderMaterial`
  (three.js prepends its uniforms and attributes such as `projectionMatrix`,
  `position`, `uv`; compiled as GLSL ES 3.00 on WebGL 2) or `RawShaderMaterial`
  (you declare everything). `WebGPURenderer` (`three/webgpu`) only runs node
  materials: write the effect in TSL (`three/tsl`), which it compiles to WGSL on
  WebGPU and to GLSL on its WebGL 2 fallback.
- **PixiJS 8 filters.** `Filter.from({ gl: { vertex, fragment }, resources })`
  takes a GLSL ES 3.00 fragment shader (`in vec2 vTextureCoord; uniform sampler2D
  uTexture; out vec4 finalColor;`) plus a vertex shader for the WebGL renderer;
  Pixi's own is exported as `defaultFilterVert`. The WebGPU renderer needs a WGSL
  program passed as `gpu`. `vTextureCoord` is **not** 0..1 over
  the sprite: it covers the filter's input texture, so for sprite-relative
  effects (vignette, dissolve by UV) compute
  `vTextureCoord * uInputSize.xy / uOutputFrame.zw` (declare both as
  `uniform vec4`; the filter system fills them).
- **WGSL / WebGPU in browsers.** Support is on by default in current Chrome,
  Edge, Safari, and Firefox on Windows and Apple Silicon Macs, but still patchy on Linux and Android;
  the per-browser versions are in the SKILL.md Version notes. Keep a WebGL 2 path
  for a web game.

## Performance checklist

- Minimize texture samples; they are the dominant cost. Reuse a sample instead of
  re-reading.
- Prefer math (`smoothstep`, `mix`) to branches and `discard`.
- Compute heavy values per vertex (then interpolate) when per-pixel precision
  isn't required.
- Use appropriate precision on mobile (`mediump` for color, higher for UV/time).
- Avoid dependent texture reads (sampling using a value read from another texture)
  on low-end GPUs where possible.
