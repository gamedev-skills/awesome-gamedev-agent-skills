---
name: threejs-scene-setup
description: >
  Stand up a three.js scene: import maps and the three/addons path, the
  Scene/PerspectiveCamera/WebGLRenderer trio, the setAnimationLoop render loop,
  responsive resize, OrbitControls, and opting into WebGPURenderer. Use when
  starting or debugging a three.js app — when the user mentions three.js,
  THREE.Scene, WebGLRenderer, WebGPURenderer, PerspectiveCamera, the render loop,
  resizing, or OrbitControls. For models use
  threejs-gltf-loading; for materials/lights use threejs-materials-lighting.
---

# three.js Scene Setup

Create the foundation of a three.js app: module loading, the
scene/camera/renderer trio, the render loop, responsive resizing, and camera
controls. Patterns target **r187**. Read the installed `three` version before
changing an existing project because examples and addons move across releases.

## When to use

- Use when bootstrapping a three.js scene, fixing a blank/black canvas, making the
  canvas responsive, setting up the animation loop, or adding `OrbitControls`.
- Use when `package.json` depends on `three` and code does `import * as THREE from
  'three'`.

**When *not* to use:** loading `.gltf`/`.glb` models or skinned animation →
`threejs-gltf-loading`. Materials, lights, shadows, environment maps →
`threejs-materials-lighting`. 2D rendering → `pixijs-rendering`.

## Core workflow

1. **Load three.js as an ES module with an import map.** Since r137 the bare
   specifier `'three'` must be resolved by an import map (in HTML) or a bundler;
   map `'three/addons/'` too. Addons (controls, loaders) live under
   `three/addons/...`.
2. **Create the trio.** A `Scene` (root of the graph), a `PerspectiveCamera(fov,
   aspect, near, far)` moved back from the origin, and a `WebGLRenderer` whose
   `domElement` is in the DOM. Set size and `pixelRatio`.
3. **Add a mesh.** `new Mesh(geometry, material)` and `scene.add(mesh)`. With a
   lit material you also need a light (see `threejs-materials-lighting`).
4. **Drive a render loop with `renderer.setAnimationLoop(fn)`.** It's the modern,
   WebXR-/WebGPU-safe replacement for hand-rolled `requestAnimationFrame`. Use a
   `Timer` for delta time (`Clock` is deprecated since r183).
5. **Handle resize** so the camera aspect and renderer match the canvas; update
   `camera.aspect`, call `updateProjectionMatrix()`, and `renderer.setSize(...)`.
6. **Add `OrbitControls`** for orbit/pan/zoom while developing. Confirm something
   actually renders (a lit cube, the controls responding) before assuming success.

## Patterns

### 1. HTML import map + module entry (no bundler)

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

With a bundler (Vite/webpack), skip the import map and just
`npm i three`; the same `import` statements resolve.

### 2. Scene + camera + renderer

```js
// main.js
import * as THREE from 'three';

const canvas = document.querySelector('#c');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5)); // starting budget; profile on target hardware
renderer.setSize(window.innerWidth, window.innerHeight);

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x101018);

const camera = new THREE.PerspectiveCamera(
  60,                                   // vertical field of view (degrees)
  window.innerWidth / window.innerHeight, // aspect
  0.1,                                  // near
  100                                   // far
);
camera.position.set(3, 2, 5);
camera.lookAt(0, 0, 0);

const cube = new THREE.Mesh(
  new THREE.BoxGeometry(1, 1, 1),
  new THREE.MeshNormalMaterial()        // unlit; shows orientation without a light
);
scene.add(cube);
```

### 3. The render loop (setAnimationLoop + Timer)

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

In r187 (unchanged from r186), visibility reset samples `performance.now()`. A
supplied animation-frame timestamp can precede that reset and produce a negative delta. Using `update()`
keeps the clock source consistent; the lower clamp also protects a fixed-step
accumulator. Feed the bounded `dt` into simulation, not raw `getDelta()`.
The 0.1-second upper bound deliberately drops excess time after a stall; tune it
to the game's catch-up policy rather than using it for real-world deadlines.

### 4. Responsive resize

```js
function onResize() {
  const w = window.innerWidth, h = window.innerHeight;
  camera.aspect = w / h;
  camera.updateProjectionMatrix();      // required after changing aspect
  renderer.setSize(w, h);
}
window.addEventListener('resize', onResize);
```

### 5. OrbitControls (orbit / pan / zoom)

```js
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;          // inertial feel
controls.target.set(0, 0, 0);

renderer.setAnimationLoop(() => {
  controls.update();                    // needed every frame when damping is on
  renderer.render(scene, camera);
});
```

### 6. Opting into WebGPURenderer (only when you need it)

`WebGLRenderer` stays the default choice for compatibility. Switch to
`WebGPURenderer` when the project needs TSL node materials or compute shaders; it
falls back to a WebGL 2 backend where WebGPU is unavailable.

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

Scenes, cameras, built-in `Mesh*Material`s, and most addons carry over; custom
GLSL (`ShaderMaterial`, `onBeforeCompile`) does not.

### 7. Resolution is a performance budget

A ratio of 2 draws four times as many pixels as 1 at the same CSS size. A cap
of 2 does nothing on a 2× display. Start games around 1.25–1.5, expose a resolution
setting, and profile the target device; these are tuning defaults, not an FPS guarantee.
Lower resolution helps fill-rate bottlenecks, not CPU-bound simulation.

For adaptive resolution, measure several seconds of frame time after assets and
shader warm-up. Ignore hidden-tab intervals and loading stalls. If sustained
GPU/fill-rate pressure exceeds the budget, lower the ratio in 0.25 steps to a
chosen floor (for example 1), never above the device ratio or user setting.
Use a cooldown and a separate recovery threshold before raising it again to avoid
oscillation. Reapply the chosen ratio on display/DPR changes and resize render
targets or postprocessing buffers consistently with the renderer.

## Pitfalls

- **`Failed to resolve module specifier "three"`** → missing import map (or bundler
  config). Map both `"three"` and `"three/addons/"`; addon paths must end with `/`.
- **Black canvas, no errors** → camera is at the origin (inside/behind the object),
  or you used a lit material (`MeshStandardMaterial`) with no light. Move the camera
  back; use `MeshNormalMaterial`/`MeshBasicMaterial` to verify geometry first.
- **Nothing animates** → you never called `renderer.render` inside the loop, or you
  call `setAnimationLoop` but render outside it.
- **Stretched / squashed view on resize** → you resized the renderer but didn't
  update `camera.aspect` + `updateProjectionMatrix()`.
- **Blurry or slow on HiDPI** → balance sharpness against fill rate with a resolution
  setting. Start around 1.25–1.5; a cap of 2 still renders 4× the pixels of 1×.
- **Simulation freezes after restoring a tab** → r186 and r187 can mix a frame timestamp
  with visibility-reset time. Use `timer.update()` and clamp simulation delta to
  `[0, 0.1]` as above so a negative delta cannot drain the fixed-step accumulator.
- **OrbitControls feel dead** → with `enableDamping = true` you must call
  `controls.update()` every frame.
- **Old tutorials use `<script src="three.min.js">` or `examples/js/...`** →
  `examples/js` was removed in r148 and `build/three.min.js` in r161; use
  `type="module"` + import maps.
- **`.render() called before the backend is initialized`** (WebGPURenderer) → call
  `await renderer.init()` before any direct `render()`/`compute()`, or render only
  from `setAnimationLoop`, which initializes first.
- **`Material "ShaderMaterial" is not compatible`, or an `onBeforeCompile` patch is
  ignored** (WebGPURenderer) → it renders node materials only; port the effect to
  TSL, or stay on `WebGLRenderer`.

## References

- Primary sources: [r187 Timer implementation](https://github.com/mrdoob/three.js/blob/r187/src/core/Timer.js)
  and [r187 responsive rendering manual](https://github.com/mrdoob/three.js/blob/r187/manual/pages/responsive.html).

- For coordinate conventions, the scene-graph (`Group`, parent/child transforms,
  `Object3D` add/remove), `OrthographicCamera` for 2.5D, and disposing of
  geometries/materials/textures to avoid leaks, read `references/scene-graph.md`.

## Related skills

- `threejs-materials-lighting` — give surfaces a lit look (lights, shadows, PBR).
- `threejs-gltf-loading` — load 3D models and play their animations.
- `pixijs-rendering` — 2D rendering in the browser.
- `fps-shooter` — a 3D genre template that composes three.js skills.
