---
name: threejs-materials-lighting
description: >
  Light and shade a three.js scene: choose materials (MeshStandardMaterial PBR vs
  unlit MeshBasicMaterial), add ambient/hemisphere/directional/point/spot lights,
  turn on shadow maps, and use an environment map (IBL) for realistic reflections.
  Use when a three.js model looks black, flat, or wrong — when the user mentions
  three.js materials, MeshStandardMaterial, lights, shadows, envMap, or PBR. For
  renderer/loop setup use threejs-scene-setup; for loading models use
  threejs-gltf-loading.
---

# three.js Materials & Lighting

Make three.js surfaces look right: pick the correct material, light the scene,
enable shadows, and add image-based lighting. Patterns target **r187**, verified
against **r187** (lighting is physically based by default since r155).

## When to use

- Use when a mesh renders black or flat, when choosing a material, adding lights,
  enabling shadows, or setting up environment-map reflections (IBL).
- Use when code constructs `MeshStandardMaterial`, `DirectionalLight`, etc., or sets
  `renderer.shadowMap.enabled` or `scene.environment`.

**When *not* to use:** the renderer/camera/loop → `threejs-scene-setup`. Loading
models (whose PBR materials this complements) → `threejs-gltf-loading`. Custom
GLSL/`ShaderMaterial` is its own topic; for the portable concept see
`shader-programming`.

## Core workflow

1. **Pick a material by need.** `MeshStandardMaterial` (PBR: `roughness`,
   `metalness`, reacts to lights/IBL) for realism; `MeshPhysicalMaterial` for
   clearcoat/transmission; `MeshBasicMaterial` (unlit, ignores lights) for UI/flat;
   `MeshNormalMaterial`/`MeshDepthMaterial` for debugging.
2. **Add light, or nothing shows.** Lit materials need a light source and/or
   `scene.environment`. Combine a soft fill (`AmbientLight`/`HemisphereLight`) with a
   key `DirectionalLight`.
3. **Mind light intensity.** Since r155, lighting is physically based; modern
   intensities are higher than old tutorials (a key `DirectionalLight` ≈ 1–3).
4. **Enable shadows in three places.** `renderer.shadowMap.enabled = true`, the
   light's `castShadow = true`, and each mesh's `castShadow`/`receiveShadow`. Then
   fit the light's shadow camera to the scene.
5. **Use an environment map for grounded reflections.** Assign an equirectangular or
   PMREM-processed texture to `scene.environment`; PBR materials pick it up
   automatically.
6. **Verify under real lighting** — confirm the surface responds to the key light
   (highlights move), shadows land where expected, and reflections look plausible.

## Patterns

### 1. PBR material under a 3-light rig

```js
import * as THREE from 'three';

const material = new THREE.MeshStandardMaterial({
  color: 0xcc4444,
  roughness: 0.5,     // 0 = mirror, 1 = fully matte
  metalness: 0.0,     // 0 = dielectric (plastic/wood), 1 = metal
});
const mesh = new THREE.Mesh(new THREE.SphereGeometry(1, 32, 16), material);
scene.add(mesh);

// Soft sky/ground fill + a directional key light.
scene.add(new THREE.HemisphereLight(0xbbddff, 0x443322, 1.0)); // sky, ground, intensity
const key = new THREE.DirectionalLight(0xffffff, 2.5);
key.position.set(5, 10, 7);
scene.add(key);
```

### 2. Unlit material (no light needed)

```js
// MeshBasicMaterial ignores lights — for flat color, UI, or sprites/labels.
const flat = new THREE.MeshBasicMaterial({ color: 0x44aa88 });
// A textured color map should be tagged sRGB so colors aren't washed out:
const tex = new THREE.TextureLoader().load('assets/logo.png');
tex.colorSpace = THREE.SRGBColorSpace;
const logo = new THREE.MeshBasicMaterial({ map: tex, transparent: true });
```

### 3. Shadows (the three required switches + camera fit)

```js
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFShadowMap;         // soft by default since r182

const sun = new THREE.DirectionalLight(0xffffff, 3);
sun.position.set(8, 12, 6);
sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048);                   // default 512; raise for crisp
// DirectionalLight uses an OrthographicCamera — fit it tightly to the scene:
const cam = sun.shadow.camera;
cam.near = 1; cam.far = 40;
cam.left = -15; cam.right = 15; cam.top = 15; cam.bottom = -15;
scene.add(sun);

mesh.castShadow = true;
ground.receiveShadow = true;                          // a plane to catch the shadow
```

### 4. PBR textures on a material

```js
const loader = new THREE.TextureLoader();
const colorMap = loader.load('assets/brick_color.jpg');
colorMap.colorSpace = THREE.SRGBColorSpace;           // color maps are sRGB
const normalMap = loader.load('assets/brick_normal.jpg'); // data maps stay linear
const roughMap  = loader.load('assets/brick_rough.jpg');

const brick = new THREE.MeshStandardMaterial({
  map: colorMap,
  normalMap,
  roughnessMap: roughMap,
  metalness: 0,
});
```

### 5. Image-based lighting from an HDR environment

```js
import { HDRLoader } from 'three/addons/loaders/HDRLoader.js'; // RGBELoader before r180

new HDRLoader().load('assets/studio.hdr', (hdr) => {
  hdr.mapping = THREE.EquirectangularReflectionMapping;
  scene.environment = hdr;     // lights + reflects all PBR materials
  scene.background = hdr;       // optional: show it as the backdrop
});
// Optional tone curve (default is NoToneMapping). AgXToneMapping and
// NeutralToneMapping are the other common choices.
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.0;
```

## Pitfalls

- **Mesh is pure black** → a lit material with no light and no `scene.environment`.
  Add a light or an environment map; to confirm geometry, temporarily swap to
  `MeshBasicMaterial`/`MeshNormalMaterial`.
- **Scene too dark even with lights** → old tutorial intensities. r155+ is physically
  based; raise intensities (key light ≈ 2–3) or add an environment map.
- **Shadows don't appear** → you missed one of the three switches
  (`renderer.shadowMap.enabled`, `light.castShadow`, mesh `castShadow`/
  `receiveShadow`).
- **Shadows are cut off or blocky** → the `DirectionalLight`'s orthographic
  `shadow.camera` frustum is too big/small or doesn't cover the scene; tighten
  `left/right/top/bottom/near/far` and raise `shadow.mapSize`. Visualise it with
  `new THREE.CameraHelper(light.shadow.camera)`.
- **Shadow acne / peter-panning** → adjust `light.shadow.bias` (small negative) and
  `light.shadow.normalBias`.
- **Colors look washed out / too bright** → color (albedo) textures need
  `texture.colorSpace = THREE.SRGBColorSpace`; normal/roughness/metalness maps must
  stay linear (leave them as `NoColorSpace`). `GLTFLoader` already tags glTF
  textures correctly, so this applies to textures you load yourself.
- **Looks right on its own but dark/flat once post-processing is added** → tone
  mapping and the sRGB output conversion only run when rendering straight to the
  canvas; end the `EffectComposer` chain with `OutputPass`.
- **Environment lighting too strong or too weak** → scale it with
  `scene.environmentIntensity` (r163+); `material.envMapIntensity` only affects a
  material's own `envMap`.
- **PointLight shadows tank performance** → a point light renders the scene 6 times
  (cube map). Prefer one shadow-casting `DirectionalLight`; use cheaper fakes
  elsewhere.

## References

- For the material cheat-sheet (which `Mesh*Material` for which look), light types
  and their parameters/units, transparency vs `alphaTest` ordering, the
  `PMREMGenerator`/`RoomEnvironment` route to IBL without an HDR file, and tone
  mapping with post-processing, read `references/materials-lights-table.md`.

## Related skills

- `threejs-scene-setup` — renderer, camera, and loop (set `shadowMap`, tone mapping).
- `threejs-gltf-loading` — models arrive with PBR materials this skill tunes.
- `shader-programming` — custom shader effects (engine-agnostic concept).
