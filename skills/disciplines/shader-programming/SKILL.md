---
name: shader-programming
description: >
  Engine-neutral shader technique in GLSL with HLSL equivalents: how dissolve, outline, fresnel
  rim and post effects work, and porting GLSL to HLSL. Use when the math of an effect is the
  question, or for specks or mobile shimmer. To write a shader in one engine, its skill alone is
  enough (`godot-shaders`, `threejs-materials-lighting`, `pixijs-rendering`). Not for particles
  (`unreal-niagara`).
---

# Shader programming (cross-engine)

Shaders run per vertex and per pixel on the GPU. The pipeline, coordinate spaces, UV tricks and
the maths behind common effects port across engines; only the dialect and built-in names
change. This skill owns that technique in GLSL with HLSL equivalents. Load the engine skill
(`godot-shaders`, `threejs-materials-lighting`, `pixijs-rendering`) as well for the syntax,
built-ins and how the material is wired.

## When to use

- Designing or debugging an effect's maths: tint, scroll, dissolve, outline, rim, vignette,
  grading.
- Reasoning about stages, spaces, interpolation and precision.
- Porting a shader between GLSL and HLSL, or between engines.

**Not this skill:** Godot shading language syntax and pipeline (`godot-shaders`), three.js
`ShaderMaterial` vs TSL (`threejs-materials-lighting`), PixiJS filters (`pixijs-rendering`),
particle systems (`unreal-niagara`), post-process stack settings (the engine's renderer docs),
per-pixel cost in a profiler (`performance-optimization`).

## Core workflow

1. **Name the stage.** The vertex stage moves vertices to clip space and passes data on; the
   fragment stage runs per pixel and outputs a colour. Most game effects are fragment work.
2. **Pick one space** for lighting maths (world or view) and convert every vector into it.
3. **Drive effects with UVs, uniforms and time.** UVs are 0..1; uniforms are constant per draw;
   varyings are interpolated from vertex to fragment.
4. **Prefer `mix`, `step`, `smoothstep` and `clamp` to branches** on per-pixel values: pixels run
   in lockstep, so a branch that differs between neighbours runs both sides. A branch on a
   uniform is cheap.
5. **Keep texture samples few**; they are usually the main cost.
6. **Compile before looking** (see "Check it").
7. **Ask for a visual check on the target device** with specific questions.

## Patterns

GLSL fragment snippets for desktop `#version 330`; each compiles with `glslangValidator` under
that header. For GLSL ES 3.00 (WebGL 2, three.js `ShaderMaterial`, PixiJS filters) add
`precision highp float;` and set uniform defaults from code: ES rejects `uniform float edge =
0.05;` with "cannot initialize this type of qualifier", while Godot's shading language accepts
it. HLSL forms and the longer effects are in `references/effects.md`.

### 1. Sample, tint, combine

```glsl
uniform sampler2D tex;
uniform vec4 tint;          // multiply tints without clipping; (1,1,1,1) is unchanged
in vec2 uv;
out vec4 frag;
void main() {
    vec4 c = texture(tex, uv);   // HLSL: tex.Sample(samp, uv)
    frag = c * tint;
}
```

### 2. Scrolling UVs, frame-rate independent

```glsl
uniform sampler2D tex;
uniform float time;          // seconds since start, supplied by the engine
uniform vec2 scroll_speed;   // UV units per second
in vec2 uv;
out vec4 frag;
void main() {
    vec2 scrolled = fract(uv + scroll_speed * time);  // HLSL: frac(...)
    frag = texture(tex, scrolled);
}
// Drive with an absolute time uniform, not a per-frame accumulator. With mipmaps, fract()
// leaves a thin seam where the UV jumps from 1 to 0; prefer a repeat sampler and drop fract().
```

### 3. Dissolve with a glowing edge

```glsl
// Hide pixels where noise < threshold; tint a thin band at the boundary.
uniform sampler2D tex;
uniform sampler2D noise_tex;     // grayscale noise, 0..1
uniform float amount;            // 0 = fully visible, 1 = fully dissolved
uniform float edge = 0.05;       // width of the glowing edge band
uniform vec4 edge_color;
in vec2 uv;
out vec4 frag;
void main() {
    vec4 c = texture(tex, uv);
    float n = texture(noise_tex, uv).r;
    float cut = amount * (1.0 + edge) - edge;  // edge band starts below 0 -> none at amount 0
    if (n <= cut) discard;                     // cut away dissolved pixels (all of them at 1)
    float e = smoothstep(cut, cut + edge, n);  // 0 at the edge -> 1 inside; keep edge > 0
    frag = mix(edge_color, c, e);              // HLSL: lerp(edge_color, c, e)
}
// WRONG: thresholding at `amount` directly — at amount 0 every pixel with
// n < edge is still tinted, so the "fully visible" sprite shows glowing specks.
```

### 4. Fresnel rim light

```glsl
in vec3 world_normal;        // world space, interpolated from the vertex stage
in vec3 view_dir;            // surface -> camera, world space
uniform float power = 3.0;
uniform vec3 rim_color;
out vec4 frag;
void main() {
    // Interpolation does not preserve unit length, even with normalized vertex outputs.
    vec3 normal = normalize(world_normal);
    vec3 view = normalize(view_dir);
    float f = pow(1.0 - clamp(dot(normal, view), 0.0, 1.0), power);
    frag = vec4(rim_color * f, 1.0);   // add to lighting; f peaks at the silhouette
}
```

## Check it

1. **Compile every GLSL file** with `glslangValidator path/to/effect.frag` (the stage comes from
   the suffix: `.vert`, `.frag`). Compile the ES variant too when it ships to the web: put
   `#version 300 es` and `precision highp float;` at the top. For WGSL run
   `naga path/to/shader.wgsl`. For Godot `.gdshader` files use the headless compile check in
   `godot-shaders`.
2. **Check the endpoints numerically** where the effect has parameters: dissolve at `amount` 0
   shows no edge colour and at 1 discards everything; a vignette at `strength` 0 leaves the image
   unchanged. Read the maths off the code, or render a test quad in the engine and read pixels
   back.
3. **Ask the user to look on the target hardware** and report specific things: "Does the dissolve
   show specks at 0? Is the outline cut off at the sprite edge? Does the effect shimmer or band on
   your phone? Is the texture upside down?" Desktop drivers forgive things mobile GPUs do not.

## Gotchas

- **Mixed coordinate spaces** (a world-space normal lit by a view-space light) give subtly wrong
  shading. Convert everything into one space.
- **Unnormalized interpolated vectors** shorten between vertices, so `dot()` drifts. Normalize in
  the fragment stage.
- **V flipped between engines or APIs.** Texture and framebuffer origins differ; a ported
  effect can appear upside down or mirrored.
- **Reversed `smoothstep` edges.** The GLSL spec leaves `smoothstep(e0, e1, x)` undefined when
  `e0 >= e1`, so `smoothstep(1.0, 0.5, d)` may work on one GPU and not another. Write
  `1.0 - smoothstep(0.5, 1.0, d)`.
- **`discard` disables early depth testing** and can cost more on tiled mobile GPUs; use alpha
  blending where the effect allows it.
- **Precision on mobile.** `mediump` time or large UVs shimmer and step. Use `highp` for
  coordinates and time, and wrap time in the engine before it grows large.
- **GLSL is not HLSL.** `mix`/`lerp`, `fract`/`frac`, `texture()`/`.Sample()`, `vec2`/`float2`,
  `M * v`/`mul(M, v)`, and `mod` vs `fmod`, which differ for negative numbers. Keep the source
  engine's multiply order rather than swapping operands by reflex.
- **Outline clipped at the quad edge**: the sprite needs a transparent margin as wide as the
  outline, and atlas frames need UV clamping or neighbours bleed in.
- **A GLSL `ShaderMaterial` renders nothing under three.js `WebGPURenderer`**: that renderer only
  runs node materials (TSL) on both of its backends. Keep `WebGLRenderer` for raw GLSL or port the
  effect to TSL.
- **A PixiJS 8 GL filter given only a fragment shader**: `GlProgram` options need a `vertex`
  string as well. Pass Pixi's default filter vertex shader (exported as `defaultFilterVert`) or
  your own.

## References

- `references/effects.md`: read when you need the GLSL-to-HLSL mapping table, clip-space and
  matrix-order notes for porting, the full 2D outline, vignette and colour-grading shaders,
  per-engine notes (Godot, Unity URP, Unreal, three.js, PixiJS), or the performance checklist.

## Related skills

- `godot-shaders`: Godot shading language, built-ins, render modes and a compile check.
- `threejs-materials-lighting`, `pixijs-rendering`: web material and filter wiring.
- `procedural-gen`: the noise that drives dissolve and procedural textures.
- `performance-optimization`: measuring what an effect costs per frame.

## Version notes

Last verified: 2026-11-11.

- All seven GLSL blocks in this skill and its reference compile with glslangValidator 16.6.0
  under `#version 330`, and under `#version 300 es` once uniform initializers are removed; with
  initializers the ES compile fails with "cannot initialize this type of qualifier"
  (https://github.com/KhronosGroup/glslang/releases/tag/16.6.0).
- three.js r187 (npm 0.187.0): `WebGPURenderer` runs node materials only.
- PixiJS 8.22.0: `Filter.from` passes `gl` to `GlProgram.from`, whose options type requires
  `vertex` and `fragment`; `defaultFilterVert` is exported from `src/filters/index.ts`
  (https://github.com/pixijs/pixijs/tree/v8.22.0/src/filters).
- WebGPU in browsers (gpuweb implementation status): Chrome and Edge 113+ on Windows x64, macOS
  and ChromeOS; Chrome 121+ on Android 12+ (ARM, Qualcomm, Intel) and 139+ for Imagination on
  Android 16+; Chrome on Linux 144+ for Intel Gen12+ and 147+ for NVIDIA on Wayland, others
  behind a flag; Safari 26 on macOS, iOS, iPadOS and visionOS; Firefox 141+ on Windows, 145+ on
  macOS 26 and 147+ on all Apple Silicon macOS; Firefox on Linux and Android not yet in stable
  (https://github.com/gpuweb/gpuweb/wiki/Implementation-Status). Keep a WebGL 2 path for a web
  game.
