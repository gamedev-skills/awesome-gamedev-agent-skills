# three.js glTF: loaders, compression & animation detail (r187)

Depth behind the glTF skill: combining decoders, async loading with progress,
cloning skinned meshes, and exporter hygiene. Notes call out where older releases
differ.

## Compression: DRACO, Meshopt, KTX2

A production glTF pipeline often compresses geometry (DRACO or Meshopt) and
textures (KTX2/Basis). Attach the matching loaders to `GLTFLoader`:

```js
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { DRACOLoader, DRACO_GLTF_CONFIG } from 'three/addons/loaders/DRACOLoader.js';
import { KTX2Loader } from 'three/addons/loaders/KTX2Loader.js';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';

// r185+: both loaders default to the decoder files bundled with three
// (examples/jsm/libs/draco/ and examples/jsm/libs/basis/).
const draco = new DRACOLoader().setDecoderPath(DRACO_GLTF_CONFIG); // glTF-only WASM build
const ktx2 = new KTX2Loader().detectSupport(renderer);

const loader = new GLTFLoader()
  .setDRACOLoader(draco)
  .setKTX2Loader(ktx2)
  .setMeshoptDecoder(MeshoptDecoder);   // EXT_ and KHR_meshopt_compression (r183+)

loader.load('assets/scene.glb', (gltf) => scene.add(gltf.scene));
```

Notes:

- If the default files 404 (some bundler/host setups don't serve them), copy
  `examples/jsm/libs/draco/` and `examples/jsm/libs/basis/` from the installed
  `three` into your static assets and call `draco.setDecoderPath('/decoders/draco/')`
  and `ktx2.setTranscoderPath('/decoders/basis/')`. A pinned CDN folder such as
  `https://cdn.jsdelivr.net/npm/three@0.187.0/examples/jsm/libs/basis/` also works;
  on releases before r185 one of these paths is required.
- The decoder/transcoder files must match your three.js version; a mismatch throws
  at load time.
- `ktx2.detectSupport(renderer)` requires the renderer to exist first. With
  `WebGPURenderer`, `await renderer.init()` before calling it
  (`detectSupportAsync()` is deprecated since r181).
- `DRACOLoader.setDecoderConfig()` is deprecated since r185; the loader picks WASM
  or JS itself.
- Compression shrinks downloads but adds CPU/Worker decode time; measure both.

## Async loading with a progress bar

```js
import { LoadingManager } from 'three';

const manager = new LoadingManager();
manager.onProgress = (url, loaded, total) => {
  setBarWidth(`${(loaded / total) * 100}%`);
};
manager.onLoad = () => hideLoadingScreen();

const loader = new GLTFLoader(manager);

// Promise form — clean with async/await and Promise.all for many assets.
const [hero, level] = await Promise.all([
  loader.loadAsync('assets/hero.glb'),
  loader.loadAsync('assets/level.glb'),
]);
scene.add(hero.scene, level.scene);
```

A `LoadingManager` aggregates progress across every loader that shares it, so one
bar can cover models, textures, and audio.

## Reusing a model many times

Adding the same `gltf.scene` to the scene twice does not duplicate it — it moves
it. To place many instances of an animated character, clone with `SkeletonUtils`
so the skinned mesh and its skeleton are cloned correctly (a plain `.clone()` does
not duplicate the skeleton):

```js
import * as THREE from 'three';
import { clone as skeletonClone } from 'three/addons/utils/SkeletonUtils.js';

const enemy = await loader.loadAsync('assets/enemy.glb');
const mixers = [];
for (let i = 0; i < 10; i++) {
  const instance = skeletonClone(enemy.scene);
  instance.position.x = i * 2;
  scene.add(instance);
  const mixer = new THREE.AnimationMixer(instance);   // each clone needs its own mixer
  mixer.clipAction(enemy.animations[0]).play();       // clips can be shared
  mixers.push(mixer);
}
// In the loop: for (const m of mixers) m.update(dt);
```

For static (non-skinned) meshes, prefer `InstancedMesh` for thousands of copies —
it draws them in one call.

## AnimationMixer detail

- One `AnimationMixer` per animated root object; create every `AnimationAction`
  from that mixer (`mixer.clipAction(clip)`).
- `action.play()` starts it; `action.stop()`/`action.reset()` rewind it.
- Looping: `action.setLoop(THREE.LoopRepeat)` (default) or `THREE.LoopOnce` with
  `action.clampWhenFinished = true` to hold the final pose.
- `action.timeScale` speeds/slows a clip; `action.weight` blends two playing
  clips (e.g. walk↔run by speed).
- Blend transitions with `from.crossFadeTo(to, duration, warp)` or
  `to.crossFadeFrom(from, duration, warp)`.
- Listen for completion: `mixer.addEventListener('finished', (e) => {...})`.

Always advance with real time: call `timer.update(time)` then
`mixer.update(timer.getDelta())` inside the loop (`THREE.Timer`; `Clock` is deprecated
since r183).

## Exporter hygiene (Blender → glTF)

Most "model looks wrong" issues are authoring problems, not loader bugs:

- **Apply transforms** before export (Object → Apply → All Transforms) so nodes have
  identity position/rotation/scale; otherwise baked offsets fight runtime control.
- **One clean root.** Aim for a single root `Object3D` with no transform and
  meaningful child names, so you can re-parent parts to the scene cheaply.
- **Author in metres**, real-world scale. Avoid scaling parents.
- **Name your nodes and clips** — you'll look them up by name (`getObjectByName`,
  `AnimationClip.findByName`).
- Prefer `.glb` (single binary file) for the web; it bundles geometry, textures,
  and animation into one request.
