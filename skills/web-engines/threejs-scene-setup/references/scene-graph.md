# three.js scene graph, cameras & cleanup (r150+)

Depth behind the scene-setup skill: coordinate conventions, the `Object3D`
hierarchy, the orthographic camera, resource disposal, and the resolution budget.

Contents:

- Coordinates & conventions
- The Object3D hierarchy
- PerspectiveCamera vs OrthographicCamera
- Disposing of resources (avoiding leaks)
- Stopping and restarting the loop
- Render-on-demand
- Adaptive resolution

## Coordinates & conventions

- Right-handed coordinate system: **+X right, +Y up, +Z toward the viewer**. A fresh
  `PerspectiveCamera` looks down **-Z**.
- Rotations are in **radians** (except `PerspectiveCamera`'s `fov`, which is degrees).
  Use `THREE.MathUtils.degToRad(deg)` when you think in degrees.
- Units are arbitrary but be consistent. glTF models are authored in metres; pick a
  scale and stick to it across the project.

## The Object3D hierarchy

Every visual thing (`Mesh`, `Group`, `Camera`, `Light`) extends `Object3D` and has
`position`, `rotation`, `quaternion`, and `scale`. Children inherit their parent's
transform.

```js
import * as THREE from 'three';

const turret = new THREE.Group();         // empty transform node
turret.add(barrelMesh);                   // child, positioned relative to turret
scene.add(turret);
turret.rotation.y = Math.PI / 4;          // rotates the whole group

barrelMesh.removeFromParent();            // detach (r129+)
scene.add(barrelMesh);                    // re-parent to the scene root
```

Useful traversal/lookup helpers:

```js
scene.getObjectByName('Player');          // first descendant with that .name
root.traverse((obj) => { /* visit every descendant */ });
obj.getWorldPosition(new THREE.Vector3()); // world-space position
```

Avoid scaling parents of physics/gameplay objects: non-unit parent scale compounds
through children and makes world-space math (raycasts, distances) error-prone.

## PerspectiveCamera vs OrthographicCamera

- **PerspectiveCamera(fov, aspect, near, far)** — objects shrink with distance.
  Default for 3D. Keep `near`/`far` as tight as the scene allows; a huge far/near
  ratio wrecks depth precision (z-fighting).
- **OrthographicCamera(left, right, top, bottom, near, far)** — no perspective;
  ideal for 2.5D, isometric, or CAD-like views. Size the frustum to the aspect:

```js
const aspect = window.innerWidth / window.innerHeight;
const d = 5;
const cam = new THREE.OrthographicCamera(-d * aspect, d * aspect, d, -d, 0.1, 100);
// On resize, recompute left/right from the new aspect, then updateProjectionMatrix().
```

After changing any projection property (`aspect`, `fov`, frustum extents, `zoom`)
call `camera.updateProjectionMatrix()`.

## Disposing of resources (avoiding leaks)

three.js cannot garbage-collect GPU memory for you. Removing an object from the
scene frees nothing on the GPU; you must dispose geometries, materials, and
textures explicitly.

```js
// Disposes everything under obj. Skip geometries/materials/textures that other
// objects still share, or they will be re-uploaded (or break) on the next frame.
function disposeObject(obj) {
  obj.traverse((node) => {
    if (node.geometry) node.geometry.dispose();
    const materials = Array.isArray(node.material) ? node.material : [node.material];
    for (const mat of materials) {
      if (!mat) continue;
      for (const key of Object.keys(mat)) {
        const value = mat[key];
        if (value && value.isTexture) value.dispose(); // map, normalMap, etc.
      }
      mat.dispose();
    }
    if (node.isSkinnedMesh) node.skeleton.dispose();    // bone texture
    node.dispose();   // Object3D.dispose() (r186+): shadow maps, instancing buffers
  });
  obj.removeFromParent();
}
```

`Object3D.dispose()` is on every object since r186 (before that only lights,
`InstancedMesh`, and `BatchedMesh` had it — guard with `node.dispose?.()` on older
releases). The base method frees no geometry, materials, or textures; those stay
manual (`BatchedMesh` is the exception: it owns and disposes its own geometry).

Also dispose render targets (`renderTarget.dispose()`) and, on full teardown, the
renderer (`renderer.dispose()`). When swapping levels, dispose the old level's
subtree before loading the next, or memory grows every transition.

## Stopping and restarting the loop

`renderer.setAnimationLoop(fn)` starts the loop; `setAnimationLoop(null)` stops it
(e.g. when the tab is hidden via the Page Visibility API, or a menu is open). This
is also the loop required by WebXR — `requestAnimationFrame` does not drive XR
frames.

## Render-on-demand

For static scenes or editors, you don't need a continuous loop. Render only when
something changes (input, controls' `change` event, a tween step):

```js
let needsRender = true;
controls.addEventListener('change', () => { needsRender = true; });
renderer.setAnimationLoop(() => {
  controls.update();          // keeps damping alive; fires 'change' while moving
  if (!needsRender) return;
  needsRender = false;
  renderer.render(scene, camera);
});
```

This cuts GPU/battery use dramatically for non-animated content.

## Adaptive resolution

Pixel ratio is a fill-rate budget: a ratio of 2 draws four times the pixels of 1 at the same
CSS size. Lowering it helps when the GPU is the bottleneck, not when the simulation is.

To adapt it at runtime:

- Measure several seconds of frame time after assets load and shaders warm up. Ignore
  hidden-tab intervals and loading stalls.
- If sustained GPU pressure exceeds the budget, lower the ratio in 0.25 steps down to a
  chosen floor (for example 1). Never go above the device ratio or the user's setting.
- Wait out a cooldown and use a separate, higher recovery threshold before raising it again,
  or the ratio oscillates.
- Reapply the chosen ratio when the display or `devicePixelRatio` changes, and resize render
  targets and post-processing buffers to match the renderer.
