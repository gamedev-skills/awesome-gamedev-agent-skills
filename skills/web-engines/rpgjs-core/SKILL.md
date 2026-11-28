---
name: rpgjs-core
description: >
  Builds and debugs RPGJS v5 games (the TypeScript RPG and MMORPG framework, `@rpgjs/*`):
  starter setup, client/server/standalone entry points, providers, modules and hooks, player
  spawn, spritesheets and synchronized `props`. Use when package.json has `@rpgjs/server`, or on
  "RPG.js", `defineModule`, `onConnected`, `provideTiledMap`, player stats missing on the client.
  Not for events and maps (`rpgjs-events-maps`), tests (`rpgjs-testing`) or Phaser (`phaser-core`).
---

# RPGJS v5 core

Sets up and extends an RPGJS v5 game: a Vite project where a **server** (rules, maps, players) and a
**client** (rendering, GUI) are wired together through providers and modules. The same code runs as a
single-player game (`standalone.ts`, server inside the browser) or as an MMORPG (`client.ts` plus a
separate `server.ts`). New projects start from the `v5` starter. A project pinned to RPGJS 4 keeps its
v4 APIs unless the user asks for a migration.

## When to use

- Creating an RPGJS project, adding a module, spawning the player, registering a spritesheet,
  choosing standalone or MMORPG, adding synchronized player state.
- `package.json` lists `@rpgjs/server`, `@rpgjs/client` or `@rpgjs/tiledmap`; files named
  `client.ts`, `server.ts`, `standalone.ts`, `config/config.client.ts`.
- Not for NPCs, chests, maps and Tiled work (`rpgjs-events-maps`), Vitest suites
  (`rpgjs-testing`), engine-neutral save design (`save-systems`).

## Workflow

1. **Prove it is RPGJS v5.** Run `grep -n '"@rpgjs/' package.json` and read the resolved versions in
   the lockfile. No match means no project yet: scaffold, do not hand-build the folders.
   ```bash
   npx degit rpgjs/starter#v5 my-rpg-game && cd my-rpg-game && npm install
   ```
2. **Read the live docs for the task.** `https://v5.rpgjs.dev/llms.txt` is the index; each page is
   also served as Markdown (for example `https://v5.rpgjs.dev/guide/structure.md`). The API moves
   between betas, so prefer these pages over memory.
3. **Find the entry point in use.** `standalone.ts` means single player, `client.ts` plus
   `server.ts` means MMORPG. `RPG_TYPE=mmorpg npm run dev` switches the starter to MMORPG mode.
4. **Put code on the right side.** Server hooks go in `modules/server.ts`, visuals in
   `modules/client.ts`, each installed with `provideServerModules` or `provideClientModules`.
   Never import the server module from client code: in MMORPG mode it would ship into the browser.
5. **Implement** with the patterns below, matching the neighbouring files.
6. **Check.** Run `npm run build` (type errors and bad imports fail here), then `npm run dev` and read
   the terminal and browser console for errors. Ask the user to open `http://localhost:5173`, walk
   the hero around and report what they see.

## Patterns

### Server module and player spawn

```ts
import { defineModule, type RpgServer, type RpgPlayer } from "@rpgjs/server";

export default defineModule<RpgServer>({
  maps: [{ id: "simplemap" }],
  player: {
    onConnected(player: RpgPlayer) {
      player.initializeDefaultStats();
      player.changeMap("simplemap");
      player.name = "Hero";
      player.setGraphic("hero");
    },
  },
});
```

`changeMap` puts the player on the Tiled point named `start` when the map has one.

### Client spritesheet

```ts
import { provideClientModules, Presets } from "@rpgjs/client";

provideClientModules([
  {
    spritesheets: [
      { id: "hero", image: "spritesheets/hero.png", ...Presets.RMSpritesheet(3, 4) },
    ],
  },
]);
```

The image path is relative to `public/`. `setGraphic("hero")` on the server must match this `id`.

### Synchronized custom state

```ts
declare module "@rpgjs/server" {
  export interface RpgPlayer {
    wood: RpgWritableSignal<number>;
  }
}

export const player: RpgPlayerHooks = {
  props: { wood: Number },
  onConnected(player) {
    player.wood.set(0);
  },
};
```

Use `props` for state that must reach the client and survive map changes and snapshots. Use
`map.broadcast(type, data)` for one-off messages and `player.on(key, cb)` for data the client sends.

## Gotchas

- **Stats or position look wrong right after `changeMap`** → code kept running in `onConnected`
  before the player joined the room; move it to `onJoinMap`.
- **HP and `maxHp` are 0 on the client** → `initializeDefaultStats()` was never called. Do not call
  it after restoring a save or database row: it overwrites the loaded values.
- **Title screen never starts the game** → initialization sits in `onConnected`; with a title GUI
  put it in `onStart`, which fires after the GUI returns `id === 'start'`.
- **Hero is invisible** → the `setGraphic` id is not in `spritesheets`, or the image is outside
  `public/`.
- **Custom field is `undefined` on the client or lost on map change** → it is a plain property, not
  a `props` entry; declare it in `props` and write it with `.set()`.
- **Server code or secrets appear in the browser bundle** → standalone mode bundles everything
  `server.ts` imports; keep credentials out of standalone games, or switch to MMORPG mode.
- **Map not found** → no map provider is registered. Add `provideTiledMap()` on both server and
  client (or a custom `provideLoadMap`), and keep the map id equal to the `.tmx` file name.

## Resources

- Read `https://v5.rpgjs.dev/guide/synchronization.md` before changing replicated or persisted state.
- Read `https://canvasengine.net/llms.txt` before touching any `.ce` GUI component: they use
  CanvasEngine syntax, not React or Vue.
- Read `https://raw.githubusercontent.com/RSamaium/RPG-JS/refs/heads/v5/packages/physic/README.md`
  before changing collisions, hitboxes or movement rules.

## Related skills

- `rpgjs-events-maps`: NPCs, chests, Tiled maps, variables, database items.
- `rpgjs-testing`: Vitest fixtures for modules and hooks.
- `save-systems`: engine-neutral save and slot design.

## Version notes

Last verified 2026-11-28.

- Baseline: RPGJS v5 (starter `v5` installs `@rpgjs/server` 5.4.2 and `@rpgjs/client` 5.5.2);
  docs at `v5.rpgjs.dev`. The module, spritesheet, `props` and event snippets type-check against these. The `v4` branch of the starter is a different, incompatible API.
- Packages publish frequently; check the installed versions before copying a documented API.
