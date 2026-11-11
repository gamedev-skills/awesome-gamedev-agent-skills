---
name: threejs-gltf-loading
description: >
  Loads glTF/GLB models into three.js r187 and plays their animations: GLTFLoader, DRACO, Meshopt
  and KTX2 decoders, AnimationMixer cross-fades and SkeletonUtils clones. Use when a model is
  invisible or tiny, decoder files 404, animations never play, or clones share one skeleton. Not
  for scene setup (`threejs-scene-setup`) or lighting (`threejs-materials-lighting`).
---

# three.js glTF loading

Loads `.gltf` / `.glb` models, including compressed geometry (DRACO, Meshopt) and textures
(KTX2), and plays their animation clips. Patterns target **r187**; an existing project keeps
its pinned release unless the user asks to upgrade. glTF is the runtime format to default
to: OBJ has no scene graph or animation, and FBX is heavy to parse in a browser.

## When to use

- Importing a model or character, inspecting its node hierarchy, playing or blending clips,
  spawning many copies of an animated enemy, or fixing a model that does not appear.
- Files are `.gltf` / `.glb`, or code imports `GLTFLoader`, `DRACOLoader` or `KTX2Loader`
  from `three/addons/loaders/...`.
- Not for the renderer, camera and loop (`threejs-scene-setup`), the model's lighting and
  materials (`threejs-materials-lighting`), or modelling and export settings in a DCC tool.

## Workflow

1. **Inspect the file before writing loader code** when `gltf-transform` is available:
   `npx @gltf-transform/cli inspect model.glb` lists meshes, extensions (for example
   `KHR_draco_mesh_compression`, `EXT_meshopt_compression`, `KHR_texture_basisu`), clips and
   texture sizes. Each listed compression extension needs its decoder attached.
2. **Load with `GLTFLoader`** (`loadAsync` in async code). The result has `gltf.scene`, the
   root `Object3D`, and `gltf.animations`, an `AnimationClip[]`.
3. **Add `gltf.scene` and frame it.** glTF units are metres; log names and bounds to find
   the parts code will control.
4. **One `AnimationMixer` per animated root**, actions from `mixer.clipAction(clip)`, and
   `mixer.update(seconds)` every frame.
5. **Attach decoders** for the extensions found in step 1. Since r185 `DRACOLoader` and
   `KTX2Loader` find their bundled decoder files without a path.
6. **Verify** with [Verify](#verify).

## Patterns

### 1. Load and frame a model

```js
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

const gltf = await new GLTFLoader().loadAsync('assets/robot.glb');
const root = gltf.scene;
scene.add(root);

const box = new THREE.Box3().setFromObject(root);
console.log('size (m):', box.getSize(new THREE.Vector3()).toArray());
console.log('clips:', gltf.animations.map((c) => c.name));
```

### 2. Play a clip

```js
const timer = new THREE.Timer();            // THREE.Clock is deprecated since r183
const mixer = new THREE.AnimationMixer(gltf.scene);
const run = THREE.AnimationClip.findByName(gltf.animations, 'Run') ?? gltf.animations[0];
mixer.clipAction(run).play();

renderer.setAnimationLoop(() => {
  timer.update();
  mixer.update(timer.getDelta());           // seconds, not milliseconds
  renderer.render(scene, camera);
});
```

### 3. Cross-fade between clips

```js
const actions = Object.fromEntries(gltf.animations.map((c) => [c.name, mixer.clipAction(c)]));
let current = actions.Idle;
current.play();

function transitionTo(name, duration = 0.3) {
  const next = actions[name];
  if (!next || next === current) return;
  next.reset().play();                      // rewind and clear an old fade
  current.crossFadeTo(next, duration, false);
  current = next;
}
```

### 4. Compressed geometry and textures

```js
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { DRACOLoader, DRACO_GLTF_CONFIG } from 'three/addons/loaders/DRACOLoader.js';
import { KTX2Loader } from 'three/addons/loaders/KTX2Loader.js';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';

const loader = new GLTFLoader()
  .setDRACOLoader(new DRACOLoader().setDecoderPath(DRACO_GLTF_CONFIG)) // glTF-only WASM build (r185+)
  .setKTX2Loader(new KTX2Loader().detectSupport(renderer))             // needs the renderer
  .setMeshoptDecoder(MeshoptDecoder);
// Share this one loader for every model so decoders and workers are created once.
```

On releases before r185, or when the host does not serve the bundled files, copy
`examples/jsm/libs/draco/` and `libs/basis/` from the installed `three` and pass those folders
to `setDecoderPath` / `setTranscoderPath`.

### 5. Find a named part

```js
const wheels = [];
gltf.scene.traverse((node) => {
  if (node.name.startsWith('Wheel')) wheels.push(node);
});
// In the loop: for (const w of wheels) w.rotation.x += dt * 4;
```

### 6. Shrink a model without losing the parts code needs

```bash
# Meshopt compression, WebP textures at most 1024 px, keep named nodes and the hierarchy.
npx @gltf-transform/cli optimize in.glb out.glb \
  --compress meshopt --texture-compress webp --texture-size 1024 \
  --flatten false --join-named false
npx @gltf-transform/cli validate out.glb
```

`optimize` flattens the hierarchy and joins meshes, named ones included, by default. That
cuts draw calls, but code that looks up `Wheel_FL` or animates a door node then finds
nothing. Keep the two flags above for any model that code reaches into. The output needs
`setMeshoptDecoder` (Pattern 4).

## Verify

1. **File check**: `npx @gltf-transform/cli validate model.glb` for each new or changed
   file; fix reported errors before debugging loader code.
2. **Build**: `npm run build` (or `npx tsc --noEmit`) passes.
3. **Runtime probe**: expose `scene` and the mixer on `window`
   (`Object.assign(window, { scene, mixer })`). Pass this expression to Playwright's
   `page.evaluate` as a string, so it runs in the page and not in Node (the smoke script in
   `threejs-scene-setup` works), or ask the user to paste it into the browser console with
   `await` in front and report the output:

```js
(async () => {
  const before = window.mixer?.time ?? null;
  await new Promise((r) => setTimeout(r, 500));
  const meshes = [];
  window.scene.traverse((o) => { if (o.isMesh) meshes.push(o.name || o.type); });
  return { meshes: meshes.length, mixerAdvanced: before !== null && window.mixer.time > before };
})();
```

   Expect a non-zero mesh count and `mixerAdvanced: true`, then check a screenshot for
   scale and orientation.

## Gotchas

- **Model loads but nothing shows** → PBR materials with no light or environment (see
  `threejs-materials-lighting`), or the scale is off by 100 (a centimetre export). Log the
  bounding box from Pattern 1.
- **`gltf` is undefined outside the callback** → `load` is asynchronous. Use `loadAsync`,
  or assign shared references inside the callback.
- **Animation never moves** → `mixer.update` is not called each frame, it is given
  milliseconds, or `play()` was never called.
- **404 for `draco_*` or `basis_*` files, or a decode error** → the decoder files are not
  served, or come from another three.js release. Serve the copies from the installed
  `three` and point the loader at them.
- **`setKTX2Loader must be called before loading KTX2 textures`** or **`setMeshoptDecoder
  must be called before loading compressed files`** → the file uses `KHR_texture_basisu` or
  meshopt compression; attach the decoder (Pattern 4).
- **`.hasFeature() called before the backend is initialized`** → `KTX2Loader.detectSupport`
  ran on a `WebGPURenderer` before `await renderer.init()` finished.
- **Adding the same model twice moves it** → an `Object3D` has one parent. Clone it, and use
  `SkeletonUtils.clone` for skinned meshes (see the reference).
- **Clones animate together, or only one moves** → a plain `.clone()` shares the skeleton;
  use `SkeletonUtils.clone` and a separate mixer per clone.
- **Named parts vanish after `gltf-transform optimize`** → the default flatten and join
  merged them. Re-run with `--flatten false --join-named false`.
- **Baked offsets fight runtime control** → exporters can bake scale or rotation into child
  nodes. Dump names and local transforms first; re-parent a part under a fresh `Object3D`
  for a clean pivot, or ask for a re-export with applied transforms.

## References

- Read [`references/loaders-and-animation.md`](references/loaders-and-animation.md) for a
  `LoadingManager` progress bar across many loaders, spawning many animated enemies with
  `SkeletonUtils.clone`, `AnimationAction` looping and blending detail, decoder hosting
  notes, and exporter checklists to hand to an artist.

## Related skills

- `threejs-scene-setup`: renderer, camera and loop.
- `threejs-materials-lighting`: lighting and environment so PBR models look right.
- `create-game-assets`: briefing, sourcing and checking the 3D assets themselves.
- `fps-shooter`: a 3D genre that builds on these skills.

## Version notes

Last verified: 2026-11-11 against three r187 (npm `three@0.187.0`, published 2026-10-30) and
`@gltf-transform/cli` 4.5.1.

- r185: `DRACOLoader` and `KTX2Loader` default to their bundled decoder folders;
  `DRACO_GLTF_CONFIG` added; `DRACOLoader.setDecoderConfig()` deprecated (removal planned
  for r194). r183: `KHR_meshopt_compression` supported next to `EXT_meshopt_compression`.
  r181: `KTX2Loader.detectSupportAsync()` deprecated.
- gltf-transform 4.5.1 `optimize` defaults: `--compress meshopt`, `--flatten true`,
  `--join true`, `--join-named true`, `--simplify true`, `--texture-compress auto`.
  `--texture-compress ktx2` needs the `ktx` command from KTX-Software 4.4.0 or newer on
  `PATH`.
- Sources: [r187 release notes](https://github.com/mrdoob/three.js/releases/tag/r187),
  [r187 DRACOLoader.js](https://github.com/mrdoob/three.js/blob/r187/examples/jsm/loaders/DRACOLoader.js),
  [r187 GLTFLoader.js](https://github.com/mrdoob/three.js/blob/r187/examples/jsm/loaders/GLTFLoader.js),
  [glTF Transform CLI](https://gltf-transform.dev/cli), `npx @gltf-transform/cli optimize --help`.
