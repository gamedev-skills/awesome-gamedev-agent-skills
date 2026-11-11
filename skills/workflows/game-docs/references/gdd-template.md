# GDD template

Copy this into `GDD.md` in the docs folder. The GDD is the game as a whole on about one page: why it exists, what it feels like, and a map of its features. A feature's rules and numbers belong in its `design.md`; the GDD gives a one-line summary and a link.

Keep the headings `Feature index`, `Decisions` and `Change log` as written: the header links point at them. Add `· [Architecture](ARCHITECTURE.md)` to the header only once that file exists. Leave out a summary row or optional section that doesn't apply yet, with no note. Text in *italics* is guidance; don't copy it.

~~~markdown
# <Title> — Game Design Document

**Version:** 0.1 · **Updated:** <YYYY-MM-DD> · [Features](#feature-index) · [Decisions](#decisions) · [Change log](#change-log)

## Summary
<2–4 sentences: who the player is, what they do, what makes it fun, how a run or game ends.>

| | |
|---|---|
| Genre and camera | |
| Audience | <age, skill, casual or core> |
| Platforms and input | |
| Session | <one run or level, total playtime> |
| Engine | <one line; mark [ASSUMPTION] if not chosen> |
| Scope | <jam / prototype / small release, deadline> |
| References | <games this feels like, and what's taken from each> |

## Pillars
*3 to 5. A pillar is a short bold statement plus one sentence on the choices it settles. Pillars end design arguments, so a pillar nobody could disagree with ("fun gameplay") is not one.*
1. **<Pillar>.** <What it makes you choose, and what it rules out.>

## Core loop
```
<action → reward → growth → harder challenge → back>
```
- **Seconds:** *(the moment-to-moment features, linked)*
- **Minutes:** *(recurring events)*
- **Session and between sessions:**

## Feature index
*One row per feature; this table is the map of the game and the checker keeps it in step with features/. A row links its design.md once that exists.*

| Feature | Status | Scope | Summary | Docs |
|---|---|---|---|---|
| Lane movement | implemented | MVP | Swipe between 3 lanes; jump and duck | [design](features/lane-movement/design.md) |
| Combo | designed | MVP | Stunts fill a meter for a ×1–×5 multiplier; a hit resets it | [design](features/combo/design.md) |
| Leaderboard | idea | later | Weekly distance board | — |

## Milestones
*Each ends in something playable. M1 is usually a greybox of the core loop.*
1. **M1, greybox core loop:** <features> · done when: <a checkable statement>

## Decisions
*IDs run in sequence and are never reused; a superseded decision stays, marked "→ superseded by D-n".*

| ID | Date | Decision | Alternatives considered | Why | Affects |
|---|---|---|---|---|---|
| D-001 | <date> | | | | |

## Open questions
- **Assumptions to confirm:** *(every [ASSUMPTION] in the GDD)*
- **Risks:** *(design "is X fun?", tech, scope; each with how you'll find out)*

## Change log
**0.1 (<date>):** first draft.
~~~

## Optional sections

Add these to the GDD, after Milestones, when the game needs them:

- **Screens and flow:** `Boot → Title → Game ⇄ Pause → Results → Title`, with one line per screen linked to the feature that owns it.
- **Direction:** the rules every feature follows, one short paragraph each, only for what is decided: tone and narrative, art (style, palette, readability of danger and safety), audio, game feel (what a hit, a reward and a failure feel like), accessibility and localization.
- **Game-level acceptance:** only criteria that span features ("a first-time player finishes a run in under 60 s without reading text"; "60 fps on <device>").

Change-log lines stay one line per version, with the detail in the linked docs: `**0.2 (<date>):** combo designed ([combo](features/combo/design.md)); D-003 logged.`
