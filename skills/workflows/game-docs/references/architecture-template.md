# ARCHITECTURE template

Copy into `docs/ARCHITECTURE.md`. This is the game-wide technical picture: things more than one feature depends on. A feature's own modules, data and events go in its `implementation.md`, which links back here for the shared parts.

Before code exists, write the intended architecture and mark it `planned`. Once code exists, **describe the code as it is**. Read the repo, and use real paths and names. Text in *italics* is guidance; don't copy it.

~~~markdown
# <Title> — Architecture

**Status:** planned | current · **Updated:** <YYYY-MM-DD> · [GDD](GDD.md)

## 1. Stack
| | |
|---|---|
| Engine / framework | <name + exact version> |
| Language | |
| Build / bundler | |
| Target runtime | <browsers, devices, OS versions> |
| Key libraries | |
| Hosting / distribution | |

## 2. Structure
*Scenes/states and how control moves between them; the main loop (fixed vs variable step); who owns the game state.*
```
<diagram: e.g. Boot → Title → Play ⇄ Pause → Results, or a module dependency sketch>
```

## 3. Module map
| Module / folder | Responsibility | Used by features |
|---|---|---|
| `src/systems/runSim.ts` | one run as pure logic, no rendering | [combo](features/combo/implementation.md), … |

## 4. Cross-cutting conventions
- **Events / messaging:** *(bus or direct calls; the list of shared event names and payloads; who may emit)*
- **Config and tuning:** *(where tunables live, e.g. one `config.ts`; naming; how design.md numbers map to constants)*
- **Data / content:** *(data file formats, where content tables live)*
- **Persistence:** *(save format, storage, current save version, migration rule)*
- **Randomness:** *(seeded RNG? where seeds come from; determinism requirements)*
- **Rendering / UI layering:** *(canvas vs DOM overlay, scaling, safe areas)*
- **Input:** *(abstraction layer, devices)*
- **Assets:** *(pipeline, naming, budgets)*

## 5. File layout
```
<tree with a short note per folder>
```

## 6. Performance budget
*Target and floor FPS on named devices; draw-call, entity, memory and download-size limits; the "no per-frame allocation" kind of rules.*

## 7. Testing and tooling
*Test runner and how to run it; test folder layout; bots / simulations; debug keys and flags; the manual device check routine. Each feature's testing.md points at specific files.*

## 8. Build and release
*Dev server command and port; build command; versioning; deploy target and steps.*

## 9. Open questions and tech risks
~~~
