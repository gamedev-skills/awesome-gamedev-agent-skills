---
name: pixijs-rendering
description: >
  Builds and debugs 2D browser game rendering with PixiJS v8: async init, Assets loading, the
  Container and Sprite scene graph, pointer dragging and v7-to-v8 migration. Use when a game or
  playable ad uses pixi.js, or on a blank canvas, clicks not firing, or drag stopping at the
  sprite edge. Not for dashboards or charts, Phaser (`phaser-core`) or 3D (`threejs-scene-setup`).
---

# PixiJS 8 rendering for games

Sets up and structures a PixiJS **8.22** game renderer: the async `Application`, asset
loading through `Assets`, the `Container` scene graph, the ticker loop, pointer events and
render groups. PixiJS draws; it has no scenes, physics or input mapping. A game that wants
those built in is usually better served by Phaser. With PixiJS you write the loop, the
screen manager and the collision code yourself.

## When to use

- Starting a PixiJS v8 game or playable, fixing a blank canvas, structuring the display list,
  loading textures and sprite sheets, animating with the ticker, or handling pointer input.
- `package.json` depends on `pixi.js` 8.x and code imports from `'pixi.js'`.
- Not for dashboards, charts or other non-game UIs, Phaser projects (`phaser-core`) or 3D
  (`threejs-scene-setup`). PixiJS v7 code (`new Application({...})`, `Loader`,
  `beginFill`) must be migrated first; the Gotchas list the renames.

## Workflow

1. **Read the installed version.** v8 changed boot, loading, Graphics and events, so v7
   answers from memory break here.
2. **Create, then `await app.init({...})`.** The v8 constructor takes no options. Append
   `app.canvas` to the page.
3. **Load before you build.** `await Assets.load(...)` or a manifest bundle per screen; the
   returned `Texture` is what `Sprite` takes.
4. **Build the display list from `Container`s**, one per layer (world, effects, HUD). Child
   transforms are relative to the parent; later children draw on top.
5. **Run game logic in one ticker callback** scaled by `ticker.deltaMS / 1000` (seconds) or
   `ticker.deltaTime` (≈1 per 60 Hz frame). Keep rules in plain modules the callback calls.
6. **Turn on input per object** with `eventMode = 'static'`, then `on('pointerdown', ...)`.
7. **Clean up on screen changes**: `destroy()` what you remove and `Assets.unload()` what the
   next screen does not need.
8. **Verify** with [Verify](#verify).

## Patterns

### 1. Async boot

```js
import { Application, Assets, Sprite } from 'pixi.js';

const app = new Application();
await app.init({
  background: '#1099bb',
  resizeTo: window,
  antialias: true,
  // preference: 'webgpu', // a hint; default order is webgl, webgpu, canvas
});
document.body.appendChild(app.canvas);
Object.assign(window, { app }); // for the smoke check and console debugging (TS-safe)

const texture = await Assets.load('assets/bunny.png');
const bunny = new Sprite(texture);
bunny.anchor.set(0.5);
bunny.position.set(app.screen.width / 2, app.screen.height / 2);
app.stage.addChild(bunny);
```

### 2. Layers as containers

```js
import { Container } from 'pixi.js';

const world = new Container();       // camera: move or scale this, not every sprite
const hud = new Container();         // added last, so it draws over the world
app.stage.addChild(world, hud);

world.position.set(-camera.x, -camera.y);
world.scale.set(2);
```

### 3. One game loop on the ticker

```js
app.ticker.add((ticker) => {
  const dt = ticker.deltaMS / 1000;  // seconds since the last frame
  stepGame(state, input, dt);        // rules live in a plain module
  bunny.rotation += 1.5 * dt;
});
```

### 4. Pointer input and dragging

```js
bunny.eventMode = 'static';          // the v8 default 'passive' ignores the object itself
bunny.cursor = 'pointer';
bunny.on('pointerdown', () => { dragging = true; });
bunny.on('pointerup', () => { dragging = false; });
bunny.on('pointerupoutside', () => { dragging = false; });
// pointermove fires only over the object in v8; globalpointermove fires on every move.
bunny.on('globalpointermove', (event) => {
  if (dragging) bunny.position.copyFrom(event.global);
});
```

### 5. Load a screen's assets by name

```js
// addBundle works at any time; Assets.init({ manifest }) only works before the first load.
Assets.addBundle('level-1', [
  { alias: 'hero', src: 'assets/hero.png' },
  { alias: 'atlas', src: 'assets/characters.json' }, // TexturePacker JSON
]);
Assets.addBundle('level-2', [{ alias: 'boss', src: 'assets/boss.png' }]);

const level = await Assets.loadBundle('level-1');
const hero = new Sprite(level.hero);
Assets.backgroundLoadBundle('level-2'); // warm the next screen while this one plays
```

### 6. Render group for a large static layer

```js
const background = new Container({ isRenderGroup: true });
app.stage.addChildAt(background, 0);
// Hundreds of static tiles go in here. Moving `background` stays cheap;
// adding and removing children every frame cancels the benefit.
```

## Verify

1. `npm run build` (or `npx tsc --noEmit`) passes.
2. Smoke-test in a headless browser. With the dev server running and `window.app` exposed
   (Pattern 1), run `node smoke.mjs <url>` after `npm i -D playwright` and
   `npx playwright install chromium`. Without browser automation, ask the user to open the
   page and report the console output and what is drawn.

```js
// smoke.mjs: fails on page errors; prints the backend and the display list size.
import { chromium } from 'playwright';

const browser = await chromium.launch();
const page = await browser.newPage();
const errors = [];
page.on('pageerror', (e) => errors.push(e.message));
page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
await page.goto(process.argv[2]);
await page.waitForFunction(() => window.app?.renderer, null, { timeout: 15000 });
await page.waitForTimeout(1000); // let the first assets load
const state = await page.evaluate(() => ({
  backend: window.app.renderer.name,           // 'webgl', 'webgpu' or 'canvas'
  stageChildren: window.app.stage.children.length,
  tickerRunning: window.app.ticker.started,
  canvasSize: [window.app.canvas.width, window.app.canvas.height],
}));
await page.screenshot({ path: 'smoke.png' });
await browser.close();
console.log(JSON.stringify({ ...state, errors }, null, 2));
process.exit(errors.length ? 1 : 0);
```

Expect a backend name, a non-zero child count, `tickerRunning: true`, a canvas size other
than 0 × 0, and no errors. Open `smoke.png`: a correct display list with missing textures
still renders blank sprites.

## Gotchas

- **Blank canvas, or `TypeError` reading `canvas` or `screen`** → `init()` was not awaited,
  or options went to the constructor. `app.stage` exists at once, but `app.renderer` is
  `undefined` until `init()` resolves.
- **Ticker callback animates nothing (`NaN`)** → the callback's argument is the `Ticker`,
  not a delta number. Read `ticker.deltaTime` or `ticker.deltaMS` from it.
- **Speed changes with frame rate** → movement was not scaled by delta. `deltaTime` is a
  multiplier (≈1 at 60 Hz), not milliseconds.
- **Clicks do nothing** → `eventMode` is still `'passive'`. Use `'static'`, or `'dynamic'`
  for objects that move under a still cursor.
- **Drag stops at the object's edge** → `pointermove` fires only over the object in v8; use
  `globalpointermove`.
- **`AssetManager already initialized` warning, then `loadBundle` returns `undefined`** →
  `Assets.init({ manifest })` ran after an `Assets.load`, so the manifest was ignored. Call
  `init` once before any load, or register bundles with `Assets.addBundle`.
- **`Texture.from(url)` gives a blank texture** → in v8 it only reads the `Assets` cache.
  `await Assets.load(url)` first and use the returned texture.
- **`addChild` on a `Sprite`, `Graphics` or `Text` logs a deprecation warning** → only
  `Container`s should hold children in v8. Put the sprite and its children side by side in a
  `Container`.
- **Right-click opens the browser menu over the game** → listen for `contextmenu` on the
  object and call `event.preventDefault()` (PixiJS 8.22+); cancelling `rightdown` does not
  stop the menu. On older 8.x, add a native `contextmenu` listener to `app.canvas`.
- **Pixel art is blurry or shimmers** → set `TextureStyle.defaultOptions.scaleMode =
  'nearest'` before loading (or `texture.source.scaleMode = 'nearest'` per texture), and pass
  `roundPixels: true` to `init()`.
- **WebGPU-only code fails on some machines** → `preference` is a hint and PixiJS falls back.
  Branch on `app.renderer.name` before using backend-specific features.
- **Memory grows across levels** → `removeChild` frees nothing on the GPU. `destroy()` removed
  objects and `Assets.unload()` assets the next screen does not use.
- **Flicker or corrupt textures after re-creating the app in the same tab** → destroy the old
  one with `app.destroy({ removeView: true, releaseGlobalResources: true })`.
- **Porting v7 code** → `Loader`/`loader.add` became `Assets.load`;
  `new Application({...})` became an empty constructor plus `await app.init({...})`;
  `beginFill()`/`endFill()` became shape-first `.rect(...).fill(...)`; `app.view` became
  `app.canvas`; `interactive = true` became `eventMode = 'static'`; `buttonMode` became
  `cursor = 'pointer'`; `cacheAsBitmap` became `cacheAsTexture()`. The old `app.view`,
  constructor options and `interactive` still work with deprecation warnings.

## References

- Read [`references/assets-and-display.md`](references/assets-and-display.md) when working
  with sprite sheets and animations, background loading and unloading, `Graphics`, `Text`
  and `BitmapText`, `TilingSprite`, `ParticleContainer`, filters, or teardown and context
  loss.

## Related skills

- `phaser-core`: a full 2D game framework with scenes, physics and input.
- `create-game-assets`: making and packing the sprites and atlases PixiJS loads.
- `game-ui-ux`: HUD and menu layout rules for the `hud` layer.
- `prototype-fast`: greyboxing a playable slice.

## Version notes

Last verified: 2026-11-11 against pixi.js 8.22.0 (npm `latest`, released 2026-10-01).

- 8.22 added the federated `contextmenu` event.
- The renderer order `["webgl", "webgpu", "canvas"]`, the deprecation warnings for
  constructor options, `app.view` and leaf `addChild`, and the cache-only `Texture.from` were
  checked in the 8.22.0 build.
- PixiJS's Quick Start still says Vite 6.0.6 and older fail on top-level `await` in the boot
  code; on those versions wrap boot in an async function. Current Vite is 8.x.
- Sources: [v8.22.0 release notes](https://github.com/pixijs/pixijs/releases/tag/v8.22.0),
  [PixiJS v8 migration guide](https://pixijs.com/8.x/guides/migrations/v8),
  [Quick Start](https://pixijs.com/8.x/guides/getting-started/quick-start),
  `npm view pixi.js dist-tags`.
