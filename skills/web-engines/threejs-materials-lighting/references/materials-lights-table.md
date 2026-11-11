# three.js materials, lights & IBL reference (r155+)

Lookup tables and detail behind the materials & lighting skill.

Contents:

- Material cheat-sheet and PBR intuition
- Light types, starting intensities, shadow camera by light type
- Transparency & sorting
- IBL without an HDR file: PMREM + RoomEnvironment, tone mapping, `OutputPass`

## Material cheat-sheet

| Material | Lit? | Use for | Key params |
|----------|:----:|---------|-----------|
| `MeshBasicMaterial` | no | UI, flat color, billboards, debug | `color`, `map`, `wireframe` |
| `MeshStandardMaterial` | yes (PBR) | most realistic surfaces | `roughness`, `metalness`, `map`, `normalMap`, `roughnessMap`, `metalnessMap`, `aoMap`, `emissive` |
| `MeshPhysicalMaterial` | yes (PBR+) | car paint, glass, coatings | adds `clearcoat`, `transmission`, `ior`, `sheen` |
| `MeshPhongMaterial` | yes (legacy) | cheap shiny look, older tutorials | `shininess`, `specular` |
| `MeshLambertMaterial` | yes (legacy) | cheap matte | `color`, `map` |
| `MeshNormalMaterial` | no | debug orientation (no light needed) | — |
| `MeshDepthMaterial` | no | debug depth / custom depth | — |
| `MeshToonMaterial` | yes | cel-shaded look | `gradientMap` |

Default to `MeshStandardMaterial`. It responds to lights **and** `scene.environment`,
matches glTF's PBR model, and is the safe choice for imported assets.

### Common PBR intuition

- `metalness`: 0 for non-metals (plastic, wood, skin), 1 for bare metal. Avoid
  in-between values except for transitions (rust, wear).
- `roughness`: 0 = sharp mirror reflection, 1 = fully diffuse. Most real surfaces
  sit 0.3–0.8.
- Metals get their color from the albedo (`color`/`map`); dielectrics reflect the
  environment near-white.

## Light types

| Light | Direction/shape | Casts shadows | Notes |
|-------|-----------------|:-------------:|-------|
| `AmbientLight(color, intensity)` | uniform, everywhere | no | flat fill; no form |
| `HemisphereLight(sky, ground, intensity)` | sky-to-ground gradient | no | great cheap outdoor fill |
| `DirectionalLight(color, intensity)` | parallel rays (sun) | yes (orthographic) | the usual key/shadow light |
| `PointLight(color, intensity, distance, decay)` | omni from a point | yes (6× cost) | bulbs, torches |
| `SpotLight(color, intensity, distance, angle, penumbra, decay)` | cone | yes (perspective) | flashlights, stage |
| `RectAreaLight(color, intensity, w, h)` | soft rectangle | no | softboxes, screens (needs init helper) |

Since r155 physically correct lighting is the default; the old switch
(`physicallyCorrectLights`, later `useLegacyLights`) no longer exists in current
releases, so old tutorial intensities look too dark. Practical starting
intensities: key `DirectionalLight` 2–3,
`HemisphereLight`/`AmbientLight` fill ≈ 0.5–1.5. `PointLight`/`SpotLight` use
inverse-square `decay` (default 2), so they fall off fast — increase intensity or
reduce `decay` if a lamp seems too dim.

### Shadow camera by light type

- `DirectionalLight` → `OrthographicCamera`; you set `left/right/top/bottom/near/far`.
  Fit it tightly; oversized frustums waste shadow-map resolution.
- `SpotLight` → `PerspectiveCamera`; `fov` follows the spot `angle`, aspect is
  automatic.
- `PointLight` → 6 renders (cube faces); only `near`/`far` matter, and it's the
  most expensive shadow.

Tuning knobs: `light.shadow.mapSize` (default 512×512; raise to 1024/2048 for
crisper edges at memory cost), `light.shadow.bias` (small negative to fix acne),
`light.shadow.normalBias`, and `renderer.shadowMap.type` (`BasicShadowMap`,
`PCFShadowMap`, `VSMShadowMap`). `PCFShadowMap` has been soft since r182, and
`PCFSoftShadowMap` now just falls back to it with a console warning. Visualise the
frustum with
`new THREE.CameraHelper(light.shadow.camera)`.

## Transparency & sorting

- Set `material.transparent = true` and `material.opacity` for blended transparency;
  three.js sorts transparent objects back-to-front, which can still mis-order
  intersecting geometry.
- For binary cutouts (foliage, chain-link), prefer `material.alphaTest = 0.5` with
  `transparent = false` — it writes depth and avoids sort artifacts.
- `material.side` = `FrontSide` (default), `BackSide` (interiors/skyboxes), or
  `DoubleSide` (planes, leaves).
- `depthWrite = false` on overlapping additive/transparent effects (particles) so
  they don't occlude each other.

## IBL without an HDR file: PMREM + RoomEnvironment

When you don't have an `.hdr`, generate a neutral studio environment procedurally:

```js
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';

const pmrem = new THREE.PMREMGenerator(renderer);
const room = new RoomEnvironment();
scene.environment = pmrem.fromScene(room, 0.04).texture;
room.dispose();   // the room's own geometry/materials are no longer needed
pmrem.dispose();  // the generated texture stays valid
```

`RoomEnvironment` was repositioned in r183, so a project upgraded across that
release lights slightly differently; re-check exposure and `scene.environmentIntensity`.
r187 rebuilt PMREMs on cube render targets and removed `CubeUVReflectionMapping`, so
IBL also shifts slightly when upgrading across r187; the code above is unchanged.

`PMREMGenerator` pre-filters any environment (HDR, RoomEnvironment, or a rendered
scene) into the mip-mapped format PBR materials sample for reflections at varying
roughness. Assigning the result to `scene.environment` lights every
`MeshStandardMaterial`/`MeshPhysicalMaterial` without adding explicit lights (with
`WebGLRenderer`, `MeshLambertMaterial` and `MeshPhongMaterial` also pick it up
since r183).

Pair IBL with tone mapping for a filmic result: set `renderer.toneMapping` to
`THREE.ACESFilmicToneMapping`, `THREE.AgXToneMapping`, or
`THREE.NeutralToneMapping` (the Khronos 3D Commerce curve, meant to keep product
colors close to their authored values) and adjust `renderer.toneMappingExposure`.
The default is `NoToneMapping`.

The renderer applies `toneMapping` and the sRGB output conversion only when it
draws straight to the canvas. With `EffectComposer` post-processing, add
`OutputPass` (from `three/addons/postprocessing/OutputPass.js`) at the end of the
chain (passes that need sRGB input, such as FXAA, go after it), or the image comes
out too dark and untoned.

Scale all IBL at once with `scene.environmentIntensity` (r163+);
`material.envMapIntensity` only scales a material's own `envMap`.
