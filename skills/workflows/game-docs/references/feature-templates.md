# Feature doc templates

One folder per feature: `docs/features/<slug>/` with `design.md`, `implementation.md`, `testing.md`. Each doc opens with a header line for navigation. The feature's **status lives in `design.md`'s header** (and in the GDD index; `scripts/check_docs.py` checks the two agree). Keep `**Status:** <status>` exactly in this form there. The other two docs carry only the updated date and links.

Scale to the feature: a small feature's docs can be a few lines per section, and "n/a" is a fine answer. Text in *italics* is guidance; don't copy it.

---

## design.md: what and why

*Always describes the **current** design. Edit it in place, and keep the history in the History section. Owns the feature's numbers. Other docs refer to them, not copy them.*

~~~markdown
# <Feature name>: design

**Status:** designed · **Updated:** <YYYY-MM-DD> · [GDD](../../GDD.md) · Design · [Implementation](implementation.md) · [Testing](testing.md)

## In one paragraph
<What the player experiences, and how the feature changes play.>

**Player-facing pitch:** *"<one line you could put in a store listing or tutorial>"*

## Why
| Goal | How this feature achieves it |
|---|---|
| | |

**Pillars served:** <pillar name: how>. *(If it strains a pillar, say which and why that's accepted; link the decision.)*
**Non-goals:** <what this deliberately doesn't do>

## Rules
*Numbered, precise, testable. What triggers what, in what order, and what can't happen.*
1. …

## Numbers
*Every tunable, with units. First guesses are fine; mark them.*
| Name | Value | Unit | Notes / what to watch in playtests |
|---|---|---|---|

## Player experience
- **UI / HUD:** *(what appears, where, when; touch target sizes)*
- **Feedback and feel:** *(sound, particles, shake, tween, hit-stop per event)*
- **Onboarding:** *(how a new player learns it)*
- **Art / audio specifics:** *(only what's specific to this feature; global direction is in the GDD)*

## Interactions
| Other feature | Interaction |
|---|---|
| [<name>](../<slug>/design.md) | |

## Edge cases
- *(pause, death mid-effect, stacking, max values, save/quit mid-feature, input spam, …)*

## Open questions
- [ASSUMPTION] …

## History
- <YYYY-MM-DD>: designed (GDD <version>). *(Later: "2026-11-02: cap ×5 → ×6 after playtest, D-014.")*
~~~

---

## implementation.md: how it's built

*Before code exists: the plan (start the Approach with "**Plan, no code yet.**"). After: describes **the code as it is**. Read the code and use the real paths, names and constants. Shared, game-wide structure is in ARCHITECTURE.md; link to it instead of re-describing it.*

~~~markdown
# <Feature name>: implementation

**Updated:** <YYYY-MM-DD> · [GDD](../../GDD.md) · [Design](design.md) · Implementation · [Testing](testing.md) · [Architecture](../../ARCHITECTURE.md)

## Approach
<A few sentences: the shape of the solution and why this shape. Mention rejected approaches if they were real options.>

## Code map
| File / module | Role in this feature | New / changed |
|---|---|---|
| `src/systems/combo.ts` | meter + multiplier state machine | new |

## Data and config
- **Config constants:** *(name → design.md number, e.g. `COMBO_MAX_MULT` = "max multiplier")*
- **Data files / content tables:**
- **Persistence:** *(what is saved, save-version bump and migration, or "none")*

## Flow
*Events emitted/consumed, update order, state machine. A small diagram helps for anything with states.*
```
<diagram>
```

## Dependencies
- **Uses:** *(other features' modules, shared systems from ARCHITECTURE)*
- **Used by:**

## Performance
*Per-frame cost, pooling, allocations, draw calls, asset size; or "negligible" with a reason.*

## Deviations from design
*Where the code differs from design.md, and why: either design.md gets updated (and the decision logged) or the deviation is a bug to fix. Empty = code matches design.*

## Risks and TODO
- …

## History
- <YYYY-MM-DD>: plan written. *(Later: "2026-11-05: implemented in 6b4fe1b.")*
~~~

---

## testing.md: how we know it works

*Acceptance criteria are checkable statements with numbers or observable results. Tick one only when a named test or a dated manual check proves it, and write the proof next to it. Unticked means not proven yet.*

~~~markdown
# <Feature name>: testing

**Updated:** <YYYY-MM-DD> · [GDD](../../GDD.md) · [Design](design.md) · [Implementation](implementation.md) · Testing

## Acceptance criteria
*Group by rule or area. Each one maps to a rule or number in design.md. Tick only what a test's assertions or a dated check prove; split a criterion when the proof covers part of it (see SKILL.md, "Proof annotations" and "Pitfalls").*
Ticked = proven by the named test or check. Unticked = not proven yet.

- [x] <Checkable statement, worded as narrowly as its proof>. *(`tests/<file>.test.ts` › <suite>)*
- [x] <Statement>. *(browser check <date>: <browser>, <viewport>, <anything stubbed>)*
- [ ] <The part not proven yet>. *(not proven: <no test / the test checks less / needs a device>)*

Covered in [<other feature>](../<slug>/testing.md): <a rule whose criterion lives there>.

## Automated tests
| Test file / suite | Covers |
|---|---|

## Manual / playtest checks
*Steps a person runs, with the expected result. Note which devices or inputs.*
1. …

## Metrics to watch
*What to measure in playtests or bot runs to tune the numbers (e.g. "average multiplier at 800 m, target ×1.5–2").*

## Regression risks
*Other features this could break, and the tests that guard them.*

## History
- <YYYY-MM-DD>: criteria written.
~~~
