# Doc rules

Where each fact lives and how the docs are written. Read this before writing or syncing any doc. The mode steps are in [workflow-modes.md](workflow-modes.md).

## One fact, one home

**Each fact lives in exactly one place, and everything else links to it.** A tuning number lives in its feature's `design.md`. The GDD index gives a one-line summary and a link, `implementation.md` names the config constant that holds the number, and `testing.md` tests it. When you are tempted to copy something, link to it.

| Kind of content | Home |
|---|---|
| Pitch, audience, platform, pillars, core loop, tone, art/audio *direction* (the style everyone follows) | GDD |
| Rules, numbers, UX, HUD, feel, audio/art *specific to one feature* | `features/<slug>/design.md` |
| Engine, scene/state machine, event bus, save format, config conventions, folder layout, perf budget | ARCHITECTURE |
| Which modules/files a feature touches, its data, events, persistence, perf cost | `features/<slug>/implementation.md` |
| Acceptance criteria, test files, manual playtest steps, metrics to watch | `features/<slug>/testing.md` |
| Decisions that matter beyond today (chosen option, alternatives, why) | GDD §Decisions |
| What changed when | GDD §Change log (game level) and each feature doc's History line |

## What counts as a feature

A feature is anything you can design, build, ship and test as a unit:
- a mechanic (combo, jump);
- a system (save, difficulty curve, procedural track);
- a screen or flow (garage, tutorial, sharing);
- a content set (biomes, vehicle roster);
- a platform concern (PWA, controls).

If it has its own rules *and* its own code *and* its own tests, it gets a folder. Global direction (pillars, art style) is not a feature.

Slugs are short kebab-case nouns (`combo`, `day-night`, `first-run-tutorial`). They never change once created, because other docs link to them.

## Decision row

| ID | Date | Decision | Alternatives considered | Why | Affects |
|---|---|---|---|---|---|
| D-014 | 2026-11-02 | Combo cap ×6 | keep ×5; uncapped | playtests: skilled runs flatline at ×5 by 2 km | combo (a relative link to `features/combo/design.md`) |

IDs run in sequence and are never reused. A superseded decision stays in the table, with "→ superseded by D-021" added to its Decision cell.

## Proof annotations

Every criterion in `testing.md` carries its proof, or the reason it has none, in parentheses at the end of the line. The checker warns about a ticked line with no `(…)`.

```text
- [x] Multiplier rises on each stunt  *(tests/combo.test.ts › stunts)*
- [x] Share card renders  *(browser check 2026-10-27: headless Chrome, 390×844 touch, Web Share API stubbed)*
- [ ] The iOS share sheet receives the card  *(not proven: needs a device)*
- [ ] Combo survives breathers in a real run  *(not proven: no test)*
```

A criterion that belongs to another feature is not ticked here. Write a plain "Covered in" line that links to that feature's `testing.md` (template in [feature-templates.md](feature-templates.md)).

## Testing pitfalls

A ticked box that isn't true is worse than an unticked one, because nobody checks it again.

- **Ticked criterion the test doesn't fully prove** → a test's name is not proof; its assertions are. Names drift and promise more than the code checks: a test called "oil locks lane changes for 0.8 s" may only check the lane right after the slick, and a unit test of `Combo.update(held)` doesn't prove a real run passes `held` inside breathers. Read the test body. When the proof covers less than the criterion, split it:
  - tick the proven part, worded as narrowly as the test (a truck, not "any tall obstacle"; three screen sizes, not "every aspect");
  - keep the rest unticked, with its reason.

  Don't leave a true, proven part unticked because the rest isn't.
- **The same rule as a checkbox in two features** → copies drift and the counts double. Keep it in its home feature and point to it in a plain line (head-on crashes belong to damage, the fast drop to controls).
- **A new test that can't fail** → it proves nothing. Before ticking on it, break the value it guards for a moment (a config number, a data flag), run the test, see it fail, and restore the file from a backup. Say so when a test is a guard the current code can't break.
- **Stubbed browser check ticked as "works on device"** → a stub proves the game's own logic, not the platform. Name the date, browser, viewport and stubs in the check, and keep a separate unticked line for the real device.
- **A check fails or surprises you and the environment gets blamed** → first rule out the check itself (reading a label after a 5 s wait sees it already reset). Then get the real error, e.g. by calling the module directly in the page; code that swallows errors into a quiet fallback hides real bugs this way. Fix the bug or report it, and record it in that feature's implementation History.

## Writing rules

- **Be concrete.** Use numbers for every tunable: speeds, timers, sizes, HP, rates, counts, prices, with units. First guesses are fine: write them down and say they're first guesses.
- **Acceptance criteria are checkable statements** with a number or an observable result ("A hit costing HP drops the multiplier to ×1 within the same frame"), not wishes ("combo feels good").
- **Keep length proportionate.** A small feature's three docs can be 20 lines each. Don't pad sections: write "n/a: no persistence" in one line and move on.
- **Keep the language.** Use the language the existing docs use; for new docs, English unless the user asks otherwise. In-game strings stay in the game's language.
- **Keep it skimmable.** Short paragraphs, bullets and tables. Skimmable beats complete.
