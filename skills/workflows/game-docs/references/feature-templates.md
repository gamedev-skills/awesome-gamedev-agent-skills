# Feature templates

One folder per feature, `features/<slug>/` in the docs folder. `design.md` comes first and is often all a feature has. `implementation.md` and `testing.md` are added when the feature first gets code (or when the user asks). Text in *italics* is guidance; don't copy it. Leave out any section that doesn't apply.

- `references/design.md`(#designmd-the-feature-note)
- `references/implementation.md`(#implementationmd-once-code-exists)
- `references/testing.md`(#testingmd-once-code-exists)

## design.md: the feature note

*Describes the **current** design; edit it in place and keep the past in History. It owns the feature's numbers; other docs name or test them, never copy them. Keep `**Status:** <status>` in the header exactly in this form: the checker reads it and compares it with the GDD index. A small feature's note is 15 to 30 lines.*

~~~markdown
# <Feature name>

**Status:** designed · **Updated:** <YYYY-MM-DD> · [GDD](../../GDD.md)

<One paragraph: what the player does and feels, and how it changes play. Name the pillar it serves.>

## Rules
*Numbered, precise, testable: what triggers what, in what order, and what can't happen.*
1. …

## Numbers
| Name | Value | Unit | What to watch in playtests |
|---|---|---|---|

## Edge cases
- *(pause, death mid-effect, stacking, max values, quitting mid-feature, input spam)*

## Open questions
- [ASSUMPTION] …

## History
- <YYYY-MM-DD>: designed.
~~~

Add these sections only when the feature needs them: **Interactions** (a table of the other features it touches, linked), **Feel and UI** (feedback per event, HUD, onboarding), **Non-goals** (what it deliberately doesn't do). When `implementation.md` and `testing.md` exist, add `· [Implementation](implementation.md) · [Testing](testing.md)` to the header.

## implementation.md: once code exists

*Describes **the code as it is**: read it, and use real paths, names and constants. Shared structure lives in ARCHITECTURE.md; link to it instead of re-describing it. If the user wants a plan before code, start Approach with "**Plan, no code yet.**" and rewrite it when the code lands.*

~~~markdown
# <Feature name>: implementation

**Updated:** <YYYY-MM-DD> · [Design](design.md) · [Testing](testing.md)

## Approach
<A few sentences: the shape of the solution and why. Name a rejected approach if it was a real option.>

## Code map
| File / module | Role in this feature |
|---|---|
| `src/systems/combo.ts` | meter and multiplier state |

## Data and config
- **Config constants:** *(name → the design.md number it holds, e.g. `COMBO_MAX_MULT` = max multiplier)*
- **Persistence:** *(what is saved and the save version, or "none")*

## Deviations from design
*Where the code differs from design.md and why. Each one either updates design.md (and logs a decision) or is a bug to fix. Empty means the code matches the design.*

## History
- <YYYY-MM-DD>: implemented in <commit>.
~~~

Add when it matters: **Flow** (events emitted and consumed, update order, a state diagram), **Performance** (per-frame cost, pooling, asset size), **Risks and TODO**.

## testing.md: once code exists

*Each criterion maps to a rule or number in design.md and ends with its proof, or the reason it has none (proof annotations in `references/doc-rules.md`). Unticked means not proven yet, which is useful information.*

~~~markdown
# <Feature name>: testing

**Updated:** <YYYY-MM-DD> · [Design](design.md) · [Implementation](implementation.md)

## Acceptance criteria
- [x] <Checkable statement, worded as narrowly as its proof>. *(`tests/<file>.test.ts` › <suite>)*
- [x] <Statement>. *(manual check <date>: <device or browser>, <anything stubbed>)*
- [ ] <The part not proven yet>. *(not proven: <no test / the test checks less / needs a device>)*

Covered in [<other feature>](../<slug>/testing.md): <a rule whose criterion lives there>.

## Playtest checks
1. *(steps a person runs, with the expected result and the device)*

## History
- <YYYY-MM-DD>: criteria written.
~~~

Add when it matters: **Metrics to watch** (what to measure in playtests to tune the numbers, e.g. "average multiplier at 800 m, target ×1.5–2") and **Regression risks** (features this could break, and the tests that guard them).
