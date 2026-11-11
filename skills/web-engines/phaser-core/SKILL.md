---
name: phaser-core
description: >
  Sets up and debugs Phaser 4 games (and pinned Phaser 3.90): Game config, Scene lifecycle, the
  loader, scene transitions and Phaser 3 to 4 migration. Use when code imports phaser, or on a
  black screen, assets undefined in create, or a HUD scene behind the game. Not for colliders
  (`phaser-arcade-physics`), HUD layout (`game-ui-ux`) or PixiJS (`pixijs-rendering`).
---

# Phaser 4 core

Builds the foundation of a Phaser game: one `Phaser.Game`, a scene per screen, assets loaded
per scene into a global cache, and a clear split between game rules and the scenes that draw
them. New projects target **Phaser 4.2**. A project pinned to Phaser 3.90 stays on 3.x unless
the user asks for a migration.

## When to use

- Starting a Phaser game, structuring scenes, loading assets, wiring cameras, passing data
  between scenes, or porting Phaser 3 code to Phaser 4.
- The project has `phaser` in `package.json`, `import Phaser from 'phaser'`, or classes that
  extend `Phaser.Scene`.
- Not for bodies, colliders and movement (`phaser-arcade-physics`), Matter.js physics, or
  engine-neutral menu and HUD design (`game-ui-ux`; load it next to this skill for UI work).

## Workflow

1. **Read the installed major.** Check `package.json` and the lockfile. Phaser 3 and 4 share
   the scene model but not the renderer, so a v3 snippet can run and still look wrong in v4.
2. **Keep rules out of scenes.** Put state and rules (score, turns, inventory, AI) in plain
   modules with no Phaser import. A scene reads that state, draws it, and sends input actions
   back. The rules then run under `node --test` without a browser, and a restart is just new
   state.
3. **Create one game from a config** with `type: Phaser.AUTO`, a size, a `scale` mode and a
   `scene` array. The first scene in the array (and any with `active: true`) starts on boot.
4. **One `Scene` subclass per screen** with a unique key. Reset run state in `init()`, queue
   assets in `preload()`, build objects in `create()`, step in `update(time, delta)`.
5. **Move between screens with the right verb** (`start`, `launch`, `run`, `switch`, `sleep`;
   see Patterns 4) and share data through `this.registry` or a scene's `events`.
6. **Pick where UI lives.** A score or health readout fits a parallel HUD scene. Text-heavy
   menus and settings work better as HTML over the canvas (`this.add.dom` or a plain overlay).
7. **Verify** with the build and the headless smoke check in [Verify](#verify).

## Patterns

### 1. Game config and boot

```js
// main.js: one Game owns the renderer, loop, cache and Scene Manager.
import Phaser from 'phaser';
import BootScene from './scenes/BootScene.js';
import PlayScene from './scenes/PlayScene.js';
import HudScene from './scenes/HudScene.js';

const config = {
  type: Phaser.AUTO,               // WebGL, Canvas only as a fallback
  parent: 'game',                  // id of the element that holds the canvas
  width: 800,
  height: 600,
  backgroundColor: '#1d1d28',
  scale: { mode: Phaser.Scale.FIT, autoCenter: Phaser.Scale.CENTER_BOTH },
  dom: { createContainer: true },  // only if you use this.add.dom(); needs `parent`
  scene: [BootScene, PlayScene, HudScene], // later in the list = drawn on top
};

const game = new Phaser.Game(config);
Object.assign(window, { game }); // for the smoke check and console debugging (TS-safe)
```

### 2. A scene with the full lifecycle

```js
// scenes/PlayScene.js
import Phaser from 'phaser';
import { createRun, stepRun } from '../rules/run.js'; // plain module, no Phaser import

export default class PlayScene extends Phaser.Scene {
  constructor() {
    super('play');
  }

  init(data) {
    this.run = createRun({ level: data.level ?? 1 }); // runs on every (re)start
  }

  preload() {
    this.load.image('player', 'assets/player.png');
    this.load.spritesheet('coin', 'assets/coin.png', { frameWidth: 16, frameHeight: 16 });
  }

  create() {
    this.player = this.add.sprite(400, 300, 'player');
    this.cursors = this.input.keyboard.createCursorKeys();
    if (!this.scene.isActive('hud')) this.scene.launch('hud');
  }

  update(time, delta) {
    const dir = (this.cursors.right.isDown ? 1 : 0) - (this.cursors.left.isDown ? 1 : 0);
    stepRun(this.run, { dir }, delta / 1000); // delta is milliseconds
    this.player.x = this.run.playerX;
    this.registry.set('score', this.run.score);
  }
}
```

### 3. Cross-scene data and events

```js
// HUD scene: react to registry changes instead of polling every frame.
create() {
  this.scoreText = this.add.text(10, 10, 'Score: 0', { fontSize: '20px', color: '#fff' });
  const onScore = (_parent, value) => this.scoreText.setText(`Score: ${value}`);
  this.registry.events.on('changedata-score', onScore);
  // The registry outlives scenes: remove the listener or it stacks on every restart.
  this.events.once('shutdown', () => this.registry.events.off('changedata-score', onScore));
}

// Talk to another running scene directly through its event emitter.
this.scene.get('hud').events.emit('show-message', 'Level cleared!');
```

### 4. Scene transitions

```js
this.scene.start('gameover', { score }); // stop this scene, start the target
this.scene.launch('hud');                // run in parallel; restarts it if already running
this.scene.run('hud');                   // wake if asleep, resume if paused, else start
this.scene.switch('menu');               // sleep this scene, start or wake the target
this.scene.pause();                      // stop updating, keep drawing (modal menus)
this.scene.sleep();                      // stop updating and drawing, keep state
this.scene.bringToTop('hud');            // draw order follows the scene list
```

### 5. HTML over the canvas

```js
// Requires dom.createContainer and parent in the game config (Pattern 1).
const panel = this.add.dom(400, 300).createFromHTML(`
  <form class="settings"><label>Volume <input name="vol" type="range"></label></form>`);
panel.addListener('input');
panel.on('input', (event) => this.sound.setVolume(event.target.value / 100));
```

### 6. Camera follow

```js
this.cameras.main.setBounds(0, 0, 1600, 1200);
this.cameras.main.startFollow(this.player, true, 0.1, 0.1); // lerp follow
```

## Verify

1. Build or type-check first: `npm run build` (or `npx tsc --noEmit` in a TypeScript project)
   must pass.
2. Test the rules modules with `node --test` when step 2 of the workflow was followed.
3. Smoke-test the running game in a headless browser. With the dev server running and
   `window.game` exposed (Pattern 1), save and run this with `node smoke.mjs <url>`. It needs
   `npm i -D playwright` and `npx playwright install chromium`; if the user does not want
   that, ask them to open the page and report the console output and what they see.

```js
// smoke.mjs: fails on any page error; prints renderer, running scenes and a screenshot path.
import { chromium } from 'playwright';

const browser = await chromium.launch();
const page = await browser.newPage();
const errors = [];
page.on('pageerror', (e) => errors.push(e.message));
page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
await page.goto(process.argv[2]);
await page.waitForFunction(() => window.game?.isRunning, null, { timeout: 15000 });
await page.waitForTimeout(1500); // let the first scenes finish preload
const state = await page.evaluate(() => ({
  renderer: window.game.config.renderType === 2 ? 'webgl' : 'canvas', // Phaser.WEBGL = 2
  scenes: window.game.scene.getScenes(true).map((s) => s.sys.settings.key),
}));
await page.screenshot({ path: 'smoke.png' });
await browser.close();
console.log(JSON.stringify({ ...state, errors }, null, 2));
process.exit(errors.length ? 1 : 0);
```

Expect `renderer: "webgl"`, the scene keys you meant to be running (for example `["play",
"hud"]`), and an empty `errors` list. Open `smoke.png` and confirm the playfield and HUD are
drawn; DOM checks alone miss a canvas that renders nothing.

## Gotchas

- **Assets are `undefined` in `create`** → they were not queued in `preload`, or the key is
  wrong. The loader runs between `preload` and `create`. A failed file shows as a 404 in the
  console, and sprites using that key draw Phaser's placeholder "missing" texture.
- **State leaks across a restart** → fields set in the constructor. A scene instance is reused,
  so reset run state in `init()` and clear collections on `shutdown`.
- **HUD hidden, reset, or drawn underneath** → `start` stopped the gameplay scene; use
  `launch`. A second `launch` or `run` on a running scene restarts it, so guard with
  `isActive`. Scenes draw in scene-list order; call `bringToTop('hud')` if it was listed first.
- **Scene state read right after `start`/`launch` is stale** → scene operations are queued and
  run at the start of the next game step.
- **`No DOM Container set in game config`** from `this.add.dom()` → add
  `dom: { createContainer: true }` and a `parent` element to the game config.
- **Keys stay down after release, or Left + Right cancel out** → Phaser 4.2.1 skips keyboard
  events that are already `defaultPrevented`, so a host-page listener that cancels `keyup`
  leaves the key held. Check host listeners and extensions before touching movement code
  (diagnosis in the reference).
- **A Phaser 3 snippet runs but looks wrong in Phaser 4** → `preFX`/`postFX` and `BitmapMask`
  became filters (`obj.enableFilters()`, then `obj.filters.internal` / `.external`);
  `setPipeline('Light2D')` became `setLighting(true)`; `setTintFill(c)` only logs an error,
  use `setTint(c).setTintMode(Phaser.TintModes.FILL)`; `Phaser.Math.TAU` is now 2π (use
  `Phaser.Math.PI_OVER_2` where v3 code meant π/2); `Geom.Point` is gone (use
  `Phaser.Math.Vector2`).
- **Phaser 3 custom pipelines or renderer plugins fail in Phaser 4** → the renderer was
  rebuilt and the old pipeline extension points are gone. Port them against the v4 migration
  guide instead of copying renderer internals. Canvas rendering still works but is deprecated.
- **Pixel art is blurry or shimmers** → set `pixelArt: true`; it turns off antialiasing and
  turns on `roundPixels`, which defaults to `false` in Phaser 4.
- **Black screen with no error** → no scene started, or the canvas has no size. Run
  `game.scene.dump()` in the console to list scene states.
- **Two canvases after hot reload or a React/Vue remount** → a second `new Phaser.Game` ran
  while the first was alive. Keep one instance and call `game.destroy(true)` on unmount; the
  teardown finishes on the next frame. Leave `noReturn` false or no new game can start.

## References

- Read [`references/scene-flow.md`](references/scene-flow.md) when a transition behaves
  unexpectedly (pause vs sleep vs stop), listeners stack up after restarts, a scene key must be
  replaced, or keys stay stuck down.

## Related skills

- `phaser-arcade-physics`: velocity, gravity, colliders, overlaps and groups.
- `game-ui-ux`: HUD and menu layout, scaling and focus rules.
- `input-systems`: rebindable, multi-device input architecture.
- `platformer`, `puzzle`, `tower-defense`: genre skills that build on Phaser.

## Version notes

Last verified: 2026-11-11.

- npm `latest` is Phaser 4.2.1 (published 2026-07-09). The newest 3.x on npm is 3.90.0.
- The keyboard `defaultPrevented` behaviour and `game.destroy(removeCanvas, noReturn)` were
  checked in the v4.2.1 source; recheck the keyboard diagnosis on other versions.
- Sources: `npm view phaser dist-tags`,
  [Phaser 4 migration guide](https://github.com/phaserjs/phaser/blob/v4.0.0/changelog/v4/4.0/MIGRATION-GUIDE.md),
  [Phaser 3 to 4 article](https://phaser.io/news/2026/04/migrating-from-phaser-3-to-phaser-4-what-you-need-to-know),
  [v4.2.1 source](https://github.com/phaserjs/phaser/tree/v4.2.1/src).
