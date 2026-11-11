# Phaser scene flow (Phaser 4.2; core lifecycle also applies to 3.90)

The Scene Manager runs every scene through a small state machine. Knowing which
transition verb does what prevents the most common Phaser bugs: hidden scenes,
stale state after a restart, and duplicate event listeners.

Contents:

- Lifecycle order
- Transition verbs (table and rules of thumb)
- The restart-state bug
- Duplicate listeners
- Removing or replacing a scene
- Keys stay down after release (Phaser 4.2.1)

## Lifecycle order

A scene is **booted once** (status `INIT`) and can be **started any number of
times**. On each start it runs:

```
start → (loading, if preload queued anything) → create → running
```

- `init(data)` — runs first on every start. **Reset run-specific state here.**
- `preload()` — queue asset downloads. Optional.
- `create(data)` — build game objects; assets queued in `preload` are now ready.
- `update(time, delta)` — called every frame while the scene is `running`.

The same `data` object is passed to `init` and `create`, coming from
`scene.start(key, data)` / `scene.launch(key, data)`.

## Transition verbs

| Method | Effect on target | Effect on caller |
|--------|------------------|------------------|
| `start(key, data)` | start (or restart) | **stop** the caller |
| `launch(key, data)` | start in parallel; **restarts** it if already running | caller keeps running |
| `run(key, data)` | wake if sleeping, resume if paused, otherwise (re)start | caller keeps running |
| `switch(key)` | wake if sleeping, otherwise start (a paused target restarts) | **sleep** the caller |
| `pause(key?)` | stop updating, keep rendering | — |
| `resume(key?)` | resume updating | — |
| `sleep(key?)` | stop updating AND rendering, keep state | — |
| `wake(key?)` | resume a sleeping scene | — |
| `stop(key?)` | shutdown (frees objects) | — |

All of these are queued: the Scene Manager applies them at the start of the next game
step, so the target scene has not started yet on the line after `start`/`launch`.

Rules of thumb:

- **HUD/overlay** → `launch` it once; a second `launch` or `run` while it is running
  restarts it, so guard with `this.scene.isActive('hud')`. Scenes draw in scene-list
  order, so it is on top only if it comes after the gameplay scene in the `scene`
  config array; otherwise call `this.scene.bringToTop('hud')`. Toggle with
  `setVisible()` or `sleep`/`wake`, not `start`.
- **Modal pause menu** → `pause` the gameplay scene and `launch` the menu; `resume`
  on close.
- **Title ⇄ gameplay you revisit** → prefer `sleep`/`wake` (state preserved, starts
  only once) over `stop`/`start` (fresh each time) when re-initialisation is costly.

## The restart-state bug

A Scene is a long-lived instance. Fields set in the constructor are set **once**,
so they keep their last value after a restart:

```js
// WRONG — gameOver stays true forever after the first game over.
export default class Play extends Phaser.Scene {
  constructor() {
    super('play');
    this.gameOver = false;   // runs once, never again
  }
}

// RIGHT — init() runs on every (re)start.
export default class Play extends Phaser.Scene {
  constructor() { super('play'); }
  init() { this.gameOver = false; }
}
```

The same applies to module-level arrays that collect game objects: clear them on
`shutdown`, or they will hold destroyed objects from the previous run.

```js
create() {
  this.enemies = [];
  // Clean up when the scene stops so the next run starts empty.
  this.events.once('shutdown', () => { this.enemies.length = 0; });
}
```

## Duplicate listeners

Listeners added in `create` on a **global** emitter (the registry, the input
manager, another scene) survive scene restarts and stack up. Either:

- add them with `.once(...)`, or
- remove them on `shutdown`:

```js
create() {
  const onChange = (p, v) => this.refresh(v);
  this.registry.events.on('changedata-coins', onChange);
  this.events.once('shutdown', () => {
    this.registry.events.off('changedata-coins', onChange);
  });
}
```

## Removing or replacing a scene

You cannot reuse a scene key until the original is destroyed. To swap an instance
under the same key, remove it after it finishes shutting down:

```js
this.scene.remove('level'); // remove by key
// then later
this.scene.add('level', NewLevelScene, true); // true = autostart
```

A handy alternative to juggling keys is to store the active level key in the
registry and add/remove by that value.

## Keys stay down after release (Phaser 4.2.1)

The keyboard manager skips events already marked `defaultPrevented`. With its
default `window` event target, a host-page listener earlier in propagation can
cancel `keyup` before Phaser handles it. A tracked `Key` then stays `isDown`;
opposing directions can cancel each other and later presses lose their down edge.
Check the installed version's implementation before applying this diagnosis elsewhere.

1. Inspect `keydown` and `keyup` at window capture and at the configured keyboard
   target. Compare `event.code`, `event.defaultPrevented`, and the tracked key state.
2. Temporarily disable host keyboard handlers and test with extensions disabled.
   Remove or narrow the handler that cancels releases for game-owned keys.
3. After removing the interference, call the affected Scene's
   `this.input.keyboard.resetKeys()` once to clear its stale tracked keys.
   Calling it every frame would break held input. Phaser already resets these keys
   on game blur, Scene pause, and Scene sleep; adding another blur reset alone
   does not repair a release cancelled while the game remains focused.

For a local reproduction with the default keyboard target, temporarily register
this listener, press and release an arrow key, and inspect its `isDown` value:

```js
const cancelRelease = (event) => {
  if (event.code === 'ArrowLeft') event.preventDefault();
};
document.addEventListener('keyup', cancelRelease);
// After inspecting the stuck key, remove the diagnostic listener:
// document.removeEventListener('keyup', cancelRelease);
// Then reset the affected Scene's keys once as described above.
```

If the host cannot be changed, replace keyboard handling deliberately: configure
the Game with `input: { keyboard: false }`, remove `createCursorKeys()` and other
keyboard-plugin calls, and own `window` capture listeners for `keydown`/`keyup`.
The replacement reader needs this contract:

- Track held keys by `event.code`; latch press/release edges until a simulation
  tick consumes them so a short tap between ticks is retained. Suppress repeated
  `keydown` edges while a key is held.
- Clear held state and pending edges on blur or document hiding. Clear and suspend
  gameplay input on Scene pause/sleep, resume cleanly on resume/wake, and remove
  DOM and Scene listeners on shutdown so restarts do not duplicate them.
- Limit capture to game-owned keys while gameplay owns focus; leave text fields,
  editable content, and browser shortcuts usable. Process releases for keys already
  held even if focus changed before release.
- Test short taps, opposite directions, key repeat, focus loss, pause/resume,
  sleep/wake, and Scene restart. Capture sees events before later cancellation,
  but cannot recover an event blocked by an earlier `stopImmediatePropagation()`.

Primary sources: Phaser 4.2.1
[KeyboardManager](https://github.com/phaserjs/phaser/blob/v4.2.1/src/input/keyboard/KeyboardManager.js)
and [KeyboardPlugin](https://github.com/phaserjs/phaser/blob/v4.2.1/src/input/keyboard/KeyboardPlugin.js).
