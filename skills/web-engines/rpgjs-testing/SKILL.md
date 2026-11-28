---
name: rpgjs-testing
description: >
  Writes Vitest tests for RPGJS v5 modules with `@rpgjs/testing`: fixtures, fake clients, player
  hooks, variables, items and map changes, without opening a browser. Use for `testing()`,
  `createClient`, `waitForMapChange`, "test my RPGJS module", "vitest WebGL error". Not for
  writing the gameplay itself (`rpgjs-core`, `rpgjs-events-maps`) or engine-neutral test advice.
---

# RPGJS v5 testing

Runs a real RPGJS server and client in Node through `@rpgjs/testing`, so a test can connect a player,
change map, fire hooks and assert on `RpgPlayer` state in milliseconds.

## When to use

- Adding or fixing tests for a server module, player hook, event, item or variable.
- Vitest fails on WebGL, canvas, `Image` or `HTMLMediaElement` in an RPGJS project.
- Not for implementing the feature (`rpgjs-core`, `rpgjs-events-maps`).

## Workflow

1. **Check the setup.** The starter ships no test runner. Install it with
   `npm i -D vitest jsdom @rpgjs/testing`, then create `vitest.config.ts` (the config below was run
   against the v5 starter). The setup file mocks WebGL, images and media.
   ```ts
   import { defineConfig } from "vitest/config";
   import canvasengine from "@canvasengine/compiler";
   export default defineConfig({
     plugins: [canvasengine()],
     test: {
       setupFiles: ["@rpgjs/testing/dist/setup.js"],
       environment: "jsdom",
       environmentOptions: { jsdom: { url: "http://localhost/" } },
       globals: true,
     },
   });
   ```
2. **Build a module under test** with `defineModule` and a `test-map` using `file: ''` so no Tiled
   file is needed.
3. **Create the fixture in `beforeEach`**, a client, then wait for the map. Clean up in `afterEach`.
4. **Assert** on `player` (hp, variables, items) and on server state through `client.server`.
5. **Check.** Run `npx vitest run` and read the summary. Pass means every test is green and none is
   skipped. A hang usually means a missing `fixture.clear()` or a wrong map id.

## Patterns

```ts
import { testing } from "@rpgjs/testing";
import { defineModule, type RpgServer, type RpgPlayer } from "@rpgjs/server";
import type { RpgClient } from "@rpgjs/client";
import { beforeEach, afterEach, test, expect } from "vitest";

const server = defineModule<RpgServer>({
  maps: [{ id: "test-map", file: "" }],
  player: {
    async onConnected(player) {
      player.setVariable("connected", true);
      await player.changeMap("test-map", { x: 100, y: 100 });
    },
  },
});
const mod = [{ server, client: defineModule<RpgClient>({}) }];

let fixture: any;
let player: RpgPlayer;

beforeEach(async () => {
  fixture = await testing(mod);
  const client = await fixture.createClient();
  player = await client.waitForMapChange("test-map");
});
afterEach(async () => {
  await fixture.clear();
});

test("onConnected ran", () => {
  expect(player.getVariable("connected")).toBe(true);
});
```

`testing(modules, clientConfig, serverConfig)` accepts extra providers for each side. Without modules,
`testing()` still gives a default player: `client.player`.

## Gotchas

- **`ReferenceError: window is not defined` from `joypad.js`** → the environment is `node`; use
  `jsdom` as in the config above (the published guide still shows `node`).
- **`WebGL` or `HTMLCanvasElement` errors on import** → the setup file is missing from `setupFiles`.
- **Variable set in `onConnected` reads `undefined`** → it was set after `await changeMap(...)`, so
  the test's player never saw it; set state before `changeMap`.
- **Test hangs after the first case** → `fixture.clear()` was skipped, so the previous server is alive.
- **`player` is undefined or at the wrong place** → the test read it before `changeMap` finished; use
  `waitForMapChange('<id>')`.
- **Map id not found** → the module `maps` entry and the id passed to `changeMap` differ.
- **Movement assertion flaky** → movement runs on the game loop; wait a short time after
  `player.move(...)` before comparing positions.

## Resources

- Read `https://v5.rpgjs.dev/guide/testing.md` for events, GUI and combat test examples.

## Related skills

- `rpgjs-core`: modules, hooks and providers under test.
- `rpgjs-events-maps`: events and variables that tests exercise.

## Version notes

Last verified 2026-11-28.

- Run against the v5 starter with `@rpgjs/testing` 5.x and Vitest 5.1 on 2026-11-28.
