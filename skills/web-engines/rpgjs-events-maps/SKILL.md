---
name: rpgjs-events-maps
description: >
  RPGJS v5 events and maps: NPCs, chests and triggers with `onAction`, `onChanges` and
  `onPlayerTouch`, per-player variables, Tiled `.tmx` maps and start points, and registering items in
  the database. Use for `EventDefinition`, `setVariable`, `showText`, `provideTiledMap`, "NPC does
  nothing", "chest reopens". Not for project setup and player hooks (`rpgjs-core`) or tests
  (`rpgjs-testing`).
---

# RPGJS v5 events and maps

Adds interactive objects to RPGJS v5 maps. An event is a hook object placed on a map; its state
belongs in **player variables**, so it persists, survives map changes and re-triggers the event's
change detection. Maps come from Tiled: the `.tmx` file name is the map id.

## When to use

- Writing an NPC, chest, switch, enemy or trigger; placing it on a map; making it react to progress.
- Adding a Tiled map, a `start` point, event points; registering items or other database entries.
- Not for the project skeleton, player spawn or `props` (`rpgjs-core`), Vitest (`rpgjs-testing`),
  or engine-neutral design topics.

## Workflow

1. **Read the neighbours.** Open an existing event under the project's `modules/` and the server
   module's `maps` array; copy their layout and naming.
2. **Model state as variables.** Name them per object (`chest-1-opened`). Read with
   `player.getVariable`, write with `player.setVariable`.
3. **Write the event** as a function returning `EventDefinition`, then **place it** in
   `maps[].events` with `id`, `x`, `y`. Placement fields belong to the wrapper, not the definition.
4. **Add the map** by dropping `src/tiled/<id>.tmx` (map id equals the file name) and listing
   `{ id: "<id>" }` in the server module. Add a Tiled point named `start` for the default spawn.
5. **Check.** Run `npm run build`. Then `grep -rn "onChanges" <events dir>` and confirm every event
   whose look depends on a variable has one. Ask the user to talk to the NPC or open the chest, then
   reload and report whether the state held.

## Patterns

### Chest driven by a variable

```ts
import { RpgPlayer, type EventDefinition } from "@rpgjs/server";

export function ChestEvent(): EventDefinition {
  return {
    onInit() {
      this.setGraphic("chest-closed");
    },
    onChanges(player: RpgPlayer) {
      const opened = player.getVariable("chest-1-opened");
      this.setGraphic(opened ? "chest-opened" : "chest-closed");
    },
    async onAction(player: RpgPlayer) {
      if (player.getVariable("chest-1-opened")) {
        await player.showText("The chest is already open.");
        return;
      }
      player.setVariable("chest-1-opened", true);
      player.addItem("Potion", 1);
      await player.showText("You found a potion.");
    },
  };
}
```

### Place it and register data

```ts
import { defineModule, type RpgServer } from "@rpgjs/server";

export default defineModule<RpgServer>({
  maps: [
    { id: "simplemap", events: [{ id: "chest-1", x: 200, y: 120, event: ChestEvent() }] },
  ],
  database: { Potion },
});
```

With Tiled you may drop `x` and `y` and add a point object named like the event id (`chest-1`).

## Gotchas

- **Chest looks open for everyone, or closed again after reload** → state kept in a closure or event
  field instead of a player variable; use `setVariable`.
- **Graphic never updates after the variable changes** → only `onInit` sets it; mirror the logic in
  `onChanges(player)`, or call `player.syncChanges()`.
- **`this.setGraphic` is a type error** → the hooks were written as arrow functions; `this` is typed
  only in object-method syntax.
- **Event never fires `onAction`** → custom actions (`projectile:shoot`) go to `player.onInput`;
  only the default action key triggers `onAction`.
- **Player pushes the crate, or cannot** → events block without being pushed by default; set
  `pushable: true` and tune `mass`.
- **MMORPG patrol freezes** → events far from every player are paused; set
  `this.alwaysSimulated = true` in `onInit`.
- **Every player shares one NPC's progress** → mode is shared; use scenario mode for per-player
  progression (docs: `guide/event-modes`).
- **`addItem("Potion")` does nothing** → the id is not in `database`; register it or use
  `map.addInDatabase`.
- **Map is blank or missing** → file name and map id differ in case or spelling, or `provideTiledMap`
  is missing on one side.

## Resources

- Read `https://v5.rpgjs.dev/guide/create-event.md` and `https://v5.rpgjs.dev/guide/event-modes.md`
  for the full hook list and shared versus scenario behaviour.
- Read `https://v5.rpgjs.dev/guide/create-your-first-map.md` for the Tiled providers.

## Related skills

- `rpgjs-core`: entry points, modules, player spawn, `props`.
- `rpgjs-testing`: assert event and hook behaviour in Vitest.

## Version notes

Last verified 2026-11-28.

- Targets RPGJS v5 (`@rpgjs/server` 5.4.2); the chest and placement snippets type-check there. Hook names and `EventDefinition` come from the v5 guide;
  v4 events were classes with decorators and are not interchangeable.
