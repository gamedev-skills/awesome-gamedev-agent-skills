# Doc rules

Where each fact lives and how the docs are written. Read this before writing or syncing any doc.

## One fact, one home

Each fact lives in one place, and everything else links to it. A tuning number lives in its feature's `design.md`; the GDD index gives a one-line summary and a link, `implementation.md` names the config constant that holds the number, and `testing.md` tests it. When you are tempted to copy something, link to it.

| Kind of content | Home |
|---|---|
| Pitch, audience, platform, pillars, core loop, tone, art and audio *direction* | GDD |
| Rules, numbers, UX, feel, art or audio *specific to one feature* | `features/<slug>/design.md` |
| Which files a feature touches, its data, events, persistence, deviations | `features/<slug>/implementation.md` |
| Acceptance criteria and their proof, playtest steps, metrics to watch | `features/<slug>/testing.md` |
| Engine, scene flow, event bus, save format, config conventions, perf budget | ARCHITECTURE (once that code exists) |
| Decisions that matter beyond today | GDD §Decisions |
| What changed when | GDD §Change log, and each feature doc's History line |

## What counts as a feature

Anything you can design, build, ship and test as a unit: a mechanic (combo, jump), a system (save, difficulty curve), a screen or flow (garage, tutorial), a content set (biomes, vehicle roster), or a platform concern (controls, PWA). Global direction (pillars, art style) is not a feature. Slugs are short kebab-case nouns (`combo`, `day-night`, `first-run-tutorial`) and never change once created, because other docs link to them.

## Decision row

| ID | Date | Decision | Alternatives considered | Why | Affects |
|---|---|---|---|---|---|
| D-014 | 2026-11-02 | Combo cap ×6 | keep ×5; uncapped | playtests: skilled runs flatline at ×5 by 2 km | combo (a relative link to `features/combo/design.md`) |

IDs run in sequence and are never reused. A superseded decision stays in the table, with "→ superseded by D-021" added to its Decision cell. "Why" names the evidence (a playtest, a measurement, a constraint), so a later reader can tell whether it still holds.

## Proof annotations

Every criterion in `testing.md` ends with its proof, or the reason it has none, in parentheses. The checker warns about a ticked line with no `(…)`.

```text
- [x] Multiplier rises on each stunt  *(tests/combo.test.ts › stunts)*
- [x] Share card renders  *(browser check 2026-10-27: headless Chrome, 390×844 touch, Web Share API stubbed)*
- [ ] The iOS share sheet receives the card  *(not proven: needs a device)*
```

A criterion that belongs to another feature is not ticked here: write a plain "Covered in" line that links to that feature's `testing.md`.

## Testing pitfalls

A ticked box that isn't true is worse than an unticked one, because nobody checks it again.

- **A test's name is not proof; its assertions are.** A test called "oil locks lane changes for 0.8 s" may only check the lane right after the slick, and a unit test of `Combo.update(held)` doesn't prove a real run passes `held`. Read the test body. When the proof covers less than the criterion, split it: tick the proven part, worded as narrowly as the test, and leave the rest unticked with its reason.
- **A new test that can't fail proves nothing.** Before ticking on it, break the value it guards for a moment (a config number, a data flag), see the test fail, and restore the file.
- **A stubbed browser check is not "works on device".** Name the date, browser, viewport and stubs in the check, and keep a separate unticked line for the real device.
- **A check that surprises you is suspect first.** Rule out the check itself (reading a label after it already reset) before blaming the environment, then get the real error. Code that swallows errors into a quiet fallback hides bugs this way.

## Writing rules

- **Numbers for every tunable**, with units: speeds, timers, sizes, HP, rates, prices. First guesses are fine; mark them.
- **Acceptance criteria are checkable statements** with a number or an observable result ("a hit drops the multiplier to ×1 in the same frame"), not wishes ("combo feels good").
- **Proportionate length.** A small feature's note can be 15 lines. Leave out a section that doesn't apply; no "n/a" padding.
- **Keep the language** of the existing docs; new docs are in English unless the user asks otherwise. In-game strings stay in the game's language.
- **Skimmable beats complete.** Short paragraphs, bullets and tables; a diagram or table where it replaces a paragraph.
