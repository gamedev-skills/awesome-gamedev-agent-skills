---
name: threejs-materials-lighting
description: >
  Lights and shades three.js r187 scenes: standard, physical and unlit materials, lights, shadows,
  HDR environment lighting and tone mapping. Use when a mesh renders black or washed out, shadows
  are missing or full of acne, or EffectComposer darkens the image. Not for renderer setup
  (`threejs-scene-setup`), model loading (`threejs-gltf-loading`) or custom shaders
  (`shader-programming`).
---

# three.js materials and lighting

Makes three.js surfaces read correctly: the right material, a light rig, working shadows and
image-based lighting (IBL). Patterns target **r187**. Lighting has been physically based
since r155, so intensities from older tutorials look far too dark.

## When to use

- A mesh renders black or flat, a material choice is needed, lights or shadows are being
  added, or environment reflections (IBL) are being set up.
- Code constructs `MeshStandardMaterial`, `DirectionalLight` and similar, or sets
  `renderer.shadowMap.enabled`, `scene.environment` or `renderer.toneMapping`.
- Not for the renderer, camera and loop (`threejs-scene-setup`), loading models
  (`threejs-gltf-loading`), or custom GLSL and node shaders (`shader-programming` for the
  technique).

## Workflow

1. **Rule out geometry first.** Swap the material for `MeshNormalMaterial`. If the mesh is
   still missing, the problem is the camera, scale or loading, not lighting.
2. **Default to `MeshStandardMaterial`.** It reacts to lights and `scene.environment` and
   matches glTF's PBR model. Use `MeshPhysicalMaterial` only for clearcoat, transmission or
   sheen, and `MeshBasicMaterial` for unlit UI, sprites and flat colour.
3. **Light the scene**: an environment map or a hemisphere fill, plus one directional key
   light. Start the key at about 2 to 3.
4. **Turn on shadows in three places**: the renderer, the light, and each mesh's
   `castShadow` / `receiveShadow`. Then fit the light's shadow camera to the play area.
5. **Tag colour textures sRGB** and leave data maps (normal, roughness, metalness) linear.
6. **Choose a tone mapping curve** once, and finish any post-processing chain with
   `OutputPass`.
7. **Verify** with [Verify](#verify).

## Patterns

### 1. PBR material under a key and fill

```js
import * as THREE from 'three';

const material = new THREE.MeshStandardMaterial({
  color: 0xcc4444,
  roughness: 0.5, // 0 = mirror, 1 = matte
  metalness: 0.0, // 0 = plastic, wood, skin; 1 = bare metal
});
scene.add(new THREE.Mesh(new THREE.SphereGeometry(1, 32, 16), material));

scene.add(new THREE.HemisphereLight(0xbbddff, 0x443322, 1.0)); // sky, ground, intensity
const key = new THREE.DirectionalLight(0xffffff, 2.5);
key.position.set(5, 10, 7);
scene.add(key);
```

### 2. Unlit material with a colour texture

```js
const tex = new THREE.TextureLoader().load('assets/logo.png');
tex.colorSpace = THREE.SRGBColorSpace; // colour maps are sRGB
const logo = new THREE.MeshBasicMaterial({ map: tex, transparent: true }); // ignores lights
```

### 3. Shadows with a fitted shadow camera

```js
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFShadowMap;      // soft since r182

const sun = new THREE.DirectionalLight(0xffffff, 3);
sun.position.set(8, 12, 6);
sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048);                // default 512
const cam = sun.shadow.camera;                     // orthographic for a DirectionalLight
cam.near = 1; cam.far = 40;
cam.left = -15; cam.right = 15; cam.top = 15; cam.bottom = -15;
scene.add(sun);
// scene.add(new THREE.CameraHelper(cam));         // draw the frustum while tuning

mesh.castShadow = true;
ground.receiveShadow = true;
```

For a level larger than the shadow frustum, move the light and its `target` with the player
each frame instead of growing the frustum, which spreads the same map over more ground. Add
the target to the scene (`scene.add(sun.target)`) so its world matrix updates.

### 4. PBR texture set

```js
const loader = new THREE.TextureLoader();
const colorMap = loader.load('assets/brick_color.jpg');
colorMap.colorSpace = THREE.SRGBColorSpace;
const brick = new THREE.MeshStandardMaterial({
  map: colorMap,
  normalMap: loader.load('assets/brick_normal.jpg'),   // data maps stay linear
  roughnessMap: loader.load('assets/brick_rough.jpg'),
  metalness: 0,
});
```

### 5. Image-based lighting from an HDR file

```js
import { HDRLoader } from 'three/addons/loaders/HDRLoader.js'; // RGBELoader before r180

new HDRLoader().load('assets/studio.hdr', (hdr) => {
  hdr.mapping = THREE.EquirectangularReflectionMapping;
  scene.environment = hdr; // lights and reflects every PBR material
  scene.background = hdr;  // optional backdrop
});
renderer.toneMapping = THREE.ACESFilmicToneMapping; // default is NoToneMapping
renderer.toneMappingExposure = 1.0;
```

No HDR file? The reference shows `RoomEnvironment` through `PMREMGenerator`.

## Verify

1. `npm run build` (or `npx tsc --noEmit`) passes.
2. Probe the lighting state in the running page. Expose `renderer` and `scene` on `window`
   (`Object.assign(window, { renderer, scene })`). Then pass this expression to Playwright's
   `page.evaluate` as a string, so it runs in the page and not in Node (the smoke script in
   `threejs-scene-setup` works), or ask the user to paste it into the browser console and
   report the output:

```js
(() => {
  const lights = [], casters = [], srgbMissing = [];
  window.scene.traverse((o) => {
    if (o.isLight) lights.push(`${o.type}:${o.intensity}${o.castShadow ? ':shadow' : ''}`);
    if (o.isMesh && o.castShadow) casters.push(o.name || o.type);
    for (const m of [].concat(o.material ?? [])) {
      if (m.map && m.map.colorSpace !== 'srgb') srgbMissing.push(m.name || m.type);
    }
  });
  return {
    lights,
    environment: !!window.scene.environment,
    shadowMap: window.renderer.shadowMap.enabled,
    shadowCasters: casters.length,
    toneMapping: window.renderer.toneMapping, // 0 = NoToneMapping
    colorMapsNotSRGB: srgbMissing,
  };
})();
```

   Expect at least one light or an environment, `shadowMap: true` with a `:shadow` light and
   at least one caster when shadows are wanted, and an empty `colorMapsNotSRGB`. Then take a screenshot and check that highlights face the
   key light and shadows land under objects.

## Gotchas

- **Mesh is pure black** → a lit material with no light and no `scene.environment`. Add one;
  confirm the geometry with `MeshNormalMaterial`.
- **Too dark even with lights** → intensities from pre-r155 tutorials. Raise the key light to
  about 2 to 3 or add an environment map.
- **No shadows** → one of the three switches is missing: `renderer.shadowMap.enabled`,
  `light.castShadow`, or mesh `castShadow` / `receiveShadow`.
- **Shadows cut off or blocky** → the directional light's orthographic shadow camera does not
  cover the scene, or covers far too much. Fit `left/right/top/bottom/near/far`, raise
  `shadow.mapSize`, and view it with `CameraHelper`.
- **Shadow acne or floating shadows** → tune `shadow.bias` (small negative) and
  `shadow.normalBias`.
- **Colours washed out or too bright** → colour textures you load yourself need
  `colorSpace = THREE.SRGBColorSpace`; data maps stay linear. `GLTFLoader` already tags glTF
  textures.
- **Dark and untoned once post-processing is added** → tone mapping and the sRGB conversion
  run only when rendering straight to the canvas. End the `EffectComposer` chain with
  `OutputPass`.
- **Environment light too strong or weak** → scale it with `scene.environmentIntensity`;
  `material.envMapIntensity` only affects a material's own `envMap`.
- **`PCFSoftShadowMap` logs a warning** → since r182 `PCFShadowMap` is already soft and
  `PCFSoftShadowMap` falls back to it.
- **Point-light shadows tank the frame rate** → each renders the scene six times. Keep one
  shadow-casting directional light and fake the rest.

## References

- Read [`references/materials-lights-table.md`](references/materials-lights-table.md) when
  choosing among materials, looking up light parameters and units, fixing transparency
  sorting or `alphaTest` cutouts, building IBL from `RoomEnvironment` without an HDR file, or
  choosing a tone mapping curve with post-processing.

## Related skills

- `threejs-scene-setup`: renderer, camera and loop.
- `threejs-gltf-loading`: models arrive with PBR materials this skill tunes.
- `shader-programming`: custom shader effects as a technique.

## Version notes

Last verified: 2026-11-11 against three r187 (npm `three@0.187.0`, published 2026-10-30).

- r155 made physically based lighting the default; r163 added `scene.environmentIntensity`;
  r180 deprecated `RGBELoader` in favour of `HDRLoader`; r182 made `PCFShadowMap` soft; r183 repositioned
  `RoomEnvironment`; r187 rebuilt PMREMs on cube render targets and removed
  `CubeUVReflectionMapping`, so IBL looks slightly different after an upgrade.
- Shadow `mapSize` still defaults to 512 in r187.
- Sources: [r187 release notes](https://github.com/mrdoob/three.js/releases/tag/r187),
  [Migration Guide 186→187](https://github.com/mrdoob/three.js/wiki/Migration-Guide#186--187),
  [r187 source](https://github.com/mrdoob/three.js/tree/r187/src).
