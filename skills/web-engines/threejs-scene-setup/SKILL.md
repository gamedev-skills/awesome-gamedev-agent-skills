---
name: threejs-scene-setup
description: >
  Sets up and debugs a plain three.js r187 game or 3D scene: import maps, Scene, PerspectiveCamera
  and WebGLRenderer, setAnimationLoop with Timer, resize, OrbitControls and WebGPURenderer. Use on
  "Failed to resolve module specifier three", a black canvas or nothing animating. Not for GLB
  loading (`threejs-gltf-loading`), materials (`threejs-materials-lighting`) or React Three Fiber.
---

# three.js scene setup

Builds the base every three.js game needs: module loading, the scene, camera and renderer,
one render loop, resize handling, and a resolution budget. Patterns target **r187**. Read
the installed `three` version first; addons, defaults and deprecations move every release.

## When to use

- Bootstrapping a three.js scene, fixing a black or blank canvas, making the canvas
  responsive, setting up the loop, adding `OrbitControls`, or choosing between
  `WebGLRenderer` and `WebGPURenderer`.
- `package.json` depends on `three`, or code does `import * as THREE from 'three'`.
- Not for models and animation (`threejs-gltf-loading`), surface look, lights and shadows
  (`threejs-materials-lighting`), or React Three Fiber (`@react-three/fiber`) components,
  whose `<Canvas>` owns the renderer and loop. For 2D, use `pixijs-rendering` or Phaser.

## Workflow

1. **Read `three` from `package.json` or the import map.** An existing project keeps its
   release unless the user asks to upgrade.
2. **Resolve `three` and `three/addons/`** with a bundler or an import map; addons live under
   `three/addons/...`.
3. **Create the scene, camera and renderer**, with the camera moved back from the origin and
   the pixel ratio capped (Pattern 2).
4. **Prove the pipeline with an unlit mesh first** (`MeshNormalMaterial`). Only then switch
   to lit materials and add lights.
5. **Drive everything from `renderer.setAnimationLoop`** with a `Timer` and a clamped delta.
   Keep game state in plain objects and copy it onto meshes each frame. Meshes then stay a
   view, and state can be saved and tested without a GPU.
6. **Handle resize** (aspect, projection matrix, renderer size) and add `OrbitControls`
   while developing.
7. **Verify** with [Verify](#verify).

## Patterns

### 1. Import map (no bundler)

```html
<canvas id="c"></canvas>
<script type="importmap">
{
  "imports": {
    "three": "https://cdn.jsdelivr.net/npm/three@0.187.0/build/three.module.js",
    "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.187.0/examples/jsm/"
  }
}
</script>
<script type="module" src="./main.js"></script>
```

With Vite or webpack, `npm i three` and the same imports resolve without a map.

### 2. Scene, camera and renderer

```js
import * as THREE from 'three';

const canvas = document.querySelector('#c');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5)); // starting budget; profile on target hardware
renderer.setSize(window.innerWidth, window.innerHeight);

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x101018);

const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 100);
camera.position.set(3, 2, 5);
camera.lookAt(0, 0, 0);

const cube = new THREE.Mesh(new THREE.BoxGeometry(1, 1, 1), new THREE.MeshNormalMaterial());
scene.add(cube);

Object.assign(window, { renderer, scene }); // for the smoke check and console debugging
```

### 3. Render loop with Timer

```js
const timer = new THREE.Timer();        // replaces the deprecated THREE.Clock (r183+)
timer.connect(document);                // optional: no huge delta after a hidden tab

renderer.setAnimationLoop(() => {
  timer.update();                      // use performance.now(), like visibility reset
  const dt = Math.min(Math.max(timer.getDelta(), 0), 0.1); // seconds; bound stalls and negative deltas
  cube.rotation.x += dt;                // frame-rate independent
  cube.rotation.y += dt * 0.7;
  renderer.render(scene, camera);
});
// renderer.setAnimationLoop(null); // stop the loop
// timer.dispose();                 // remove visibility listener when tearing down
```

Call `update()` with no argument when the timer is connected. Visibility reset samples
`performance.now()`, so passing the loop's timestamp can produce a negative delta right after
a hidden tab returns. The clamp also protects a fixed-step accumulator; the 0.1 s upper bound
drops time after a stall on purpose, so tune it to the game's catch-up policy.

### 4. Resize

```js
window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();      // required after changing aspect
  renderer.setSize(window.innerWidth, window.innerHeight);
});
```

### 5. OrbitControls

```js
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
// In the loop, before render: controls.update(); (required every frame with damping)
```

### 6. WebGPURenderer, only when needed

Stay on `WebGLRenderer` by default. Switch when the project needs TSL node materials or
compute shaders; `WebGPURenderer` falls back to a WebGL 2 backend where WebGPU is missing.

```js
// Official WebGPU examples map both "three" and "three/webgpu" to
// build/three.webgpu.js, plus "three/tsl" to build/three.tsl.js.
import * as THREE from 'three/webgpu';

const renderer = new THREE.WebGPURenderer({ antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5)); // starting budget; profile on target hardware
renderer.setSize(window.innerWidth, window.innerHeight);
document.body.appendChild(renderer.domElement);
await renderer.init();                  // required before direct render()/compute()

renderer.setAnimationLoop(() => renderer.render(scene, camera));
```

Scenes, cameras, built-in `Mesh*Material`s and most addons carry over. Custom GLSL
(`ShaderMaterial`, `onBeforeCompile`) does not.

## Verify

1. `npm run build` (or `npx tsc --noEmit` with `@types/three` matching the `three` version)
   passes.
2. Smoke-test in a headless browser. With the dev server running and `window.renderer`
   exposed (Pattern 2), run `node smoke.mjs <url>` after `npm i -D playwright` and
   `npx playwright install chromium`. Without browser automation, ask the user to open the
   page, then report the console output and whether the cube is visible and turning.

```js
// smoke.mjs: fails on page errors; checks that frames are drawn and survive a context loss.
import { chromium } from 'playwright';

const browser = await chromium.launch();
const page = await browser.newPage();
const errors = [];
page.on('pageerror', (e) => errors.push(e.message));
page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
await page.goto(process.argv[2]);
await page.waitForFunction(() => window.renderer?.info.render.calls > 0, null, { timeout: 15000 });
const state = await page.evaluate(() => ({
  drawCalls: window.renderer.info.render.calls,
  triangles: window.renderer.info.render.triangles,
  geometries: window.renderer.info.memory.geometries,
  canvas: [window.renderer.domElement.width, window.renderer.domElement.height],
}));
await page.screenshot({ path: 'smoke.png' });
await page.evaluate(async () => {           // WebGLRenderer only: lose and restore the context
  if (!window.renderer.forceContextLoss) return;
  window.renderer.forceContextLoss();
  await new Promise((r) => setTimeout(r, 200));
  window.renderer.forceContextRestore();
  await new Promise((r) => setTimeout(r, 500));
});
await page.screenshot({ path: 'smoke-restored.png' });
await browser.close();
console.log(JSON.stringify({ ...state, errors }, null, 2));
process.exit(errors.length ? 1 : 0);
```

Expect `drawCalls` above 0, a canvas size other than 0 × 0, and no errors. Open both
screenshots: the second must still show the scene, or something holds GPU objects that the
restore did not rebuild.

## Gotchas

- **`Failed to resolve module specifier "three"`** → no import map or bundler. Map both
  `"three"` and `"three/addons/"`; the addons entry must end with `/`.
- **Black canvas, no errors** → the camera sits inside or behind the object, or a lit
  material has no light. Move the camera back and test with `MeshNormalMaterial`.
- **Stretched view after resize** → the renderer was resized but `camera.aspect` and
  `updateProjectionMatrix()` were not updated.
- **Slow or hot on HiDPI and phones** → a pixel ratio of 2 draws four times the pixels of 1,
  so a cap of 2 does nothing on a 2× screen. Start at 1.25 to 1.5 and offer a resolution
  setting; adaptive resolution is in the reference.
- **Simulation freezes after the tab returns** → in r186 and r187 a loop timestamp passed to
  `timer.update(time)` can precede the visibility reset and give a negative delta. Call
  `update()` with no argument and clamp as in Pattern 3.
- **`THREE.Clock: This module has been deprecated`** → since r183; use `THREE.Timer`.
- **Old tutorials use `<script src="three.min.js">` or `examples/js/...`** → `examples/js` was
  removed in r148 and `build/three.min.js` in r161. Use modules and an import map.
- **OrbitControls feel dead** → with `enableDamping` on, `controls.update()` must run every
  frame.
- **Canvas goes black after a GPU reset or many tabs** → the WebGL context was lost.
  `WebGLRenderer` handles `webglcontextlost` and rebuilds its own state on restore; code that
  keeps raw GL objects or skips the loop while lost does not recover. Test with
  `forceContextLoss()` / `forceContextRestore()` as in Verify.
- **`.render() called before the backend is initialized`** (WebGPURenderer) → `await
  renderer.init()` before a direct `render()`/`compute()`, or render only from
  `setAnimationLoop`, which initialises first.
- **`Material "ShaderMaterial" is not compatible`, or `onBeforeCompile` is ignored**
  (WebGPURenderer) → it renders node materials only. Port the effect to TSL or stay on
  `WebGLRenderer`.

## References

- Read [`references/scene-graph.md`](references/scene-graph.md) for coordinate conventions,
  parenting with `Group`, `OrthographicCamera` for 2.5D, disposing geometries, materials and
  textures between levels, stopping the loop, render-on-demand, and adaptive resolution.

## Related skills

- `threejs-materials-lighting`: lights, shadows, PBR and environment maps.
- `threejs-gltf-loading`: loading models and playing their animations.
- `camera-systems`: follow, orbit and first-person camera design.
- `fps-shooter`: a 3D genre that builds on these skills.

## Version notes

Last verified: 2026-11-11 against three r187 (npm `three@0.187.0`, published 2026-10-30;
`@types/three@0.187.0`).

- `Timer.update()` is unchanged between r186 and r187, so the negative-delta note holds.
- The r187 WebGPU examples still map `three` and `three/webgpu` to `build/three.webgpu.js`.
- Sources: [r187 release notes](https://github.com/mrdoob/three.js/releases/tag/r187),
  [Migration Guide](https://github.com/mrdoob/three.js/wiki/Migration-Guide),
  [r187 Timer.js](https://github.com/mrdoob/three.js/blob/r187/src/core/Timer.js),
  [r187 responsive rendering manual](https://github.com/mrdoob/three.js/blob/r187/manual/pages/responsive.html),
  [WebGLRenderer.js context handling](https://github.com/mrdoob/three.js/blob/r187/src/renderers/WebGLRenderer.js).
