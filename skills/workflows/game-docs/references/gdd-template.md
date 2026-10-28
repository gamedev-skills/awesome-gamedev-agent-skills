# GDD template

Copy this structure into `docs/GDD.md`. The GDD is the game **as a whole**: why it exists, what it feels like, the rules every feature follows, and a map of the features. Detailed rules and numbers for one feature belong in that feature's `design.md`. The GDD gives a one-line summary and links there.

Drop a section that truly doesn't apply (e.g. Narrative for an abstract puzzle game), but say so in one line instead of silently leaving it out. Text in *italics* is guidance for you; don't copy it into the doc.

~~~markdown
# <Title> — Game Design Document

**Version:** 0.1 · **Updated:** <YYYY-MM-DD> · [Architecture](ARCHITECTURE.md) · [Features](#feature-index) · [Change log](#change-log)

**Working title:** <title> · **Code name:** <short name>

---

## 1. Summary
<2–4 sentence pitch: who you are, what you do, what makes it fun, how you win.>

| | |
|---|---|
| Genre | |
| Perspective / camera | |
| Audience | <age, skill, casual/core> |
| Platforms | |
| Input | |
| Orientation / resolution | |
| Session | <length of one run/level, total playtime> |
| Language(s) | |
| Engine / tech | <one line; details in ARCHITECTURE.md> |
| Asset pipeline | <hand-drawn, generated, procedural, store-bought, placeholder> |
| Scope | <jam / prototype / small release, deadline> |
| References | <games/films this feels like, and what's taken from each> |

### Design pillars
*3–5 pillars. Each is a short bold statement plus one sentence on how it shapes decisions. Pillars settle design arguments, and every feature's design.md says how it serves them.*
1. **<Pillar>.** <How it shapes decisions.>

## 2. Core loop
```
<ASCII loop diagram: action → reward → growth → harder challenge → back>
```
- **Moment-to-moment (seconds):** *(name the features involved, linked)*
- **Recurring events (~minute):**
- **Session arc:**
- **Meta / between sessions (if any):**

## 3. Feature index
*Every feature, one row each. This table is the map of the game. Keep it in sync with features/ (the checker enforces this). Post-MVP ideas get a row with status `idea` and no link until a folder exists.*

| Feature | Status | Scope | Summary | Docs |
|---|---|---|---|---|
| Lane movement | implemented | MVP | Swipe to change between 3 lanes, jump and duck | [design](features/lane-movement/design.md) · [impl](features/lane-movement/implementation.md) · [tests](features/lane-movement/testing.md) |
| Combo | designed | post-MVP | Stunts fill a meter; ×1–×5 gear multiplier; a hit resets it | [design](features/combo/design.md) · [impl](features/combo/implementation.md) · [tests](features/combo/testing.md) |
| Online leaderboard | idea | later | Weekly distance board | — |

*Statuses: idea · designed · in progress · implemented · changed — code pending · cut*

## 4. Screens and flow
```
Boot → Title → <Select> → Game ⇄ Pause → End (win/lose) → Title
```
*One line per screen: what it's for, linked to the feature that owns it.*

## 5. Global direction
*Rules every feature follows. Feature-specific art/audio/feel goes in that feature's design.md.*
### 5.1 Narrative and tone
*Setting, premise, voice, how story is delivered (or "none, tone only"). Text style and length limits.*
### 5.2 Art direction
*Style, palette, line weight or poly budget, sizes, readability rules (silhouettes, color coding of danger and safety), references.*
### 5.3 Audio direction
*Music mood and adaptive approach, SFX style, mixing priorities.*
### 5.4 Game feel
*The feedback language: what a hit, a reward, a near miss and a failure feel like across the game.*
### 5.5 Accessibility and localization
*Text size, colorblind-safe cues, remapping, reduced motion, pause anywhere, language handling.*
### 5.6 Monetization and distribution
*Free / paid / none; where it ships.*

## 6. Scope and milestones
| MVP (must ship) | Nice-to-have | Cut / later |
|---|---|---|
| *(feature names, linked)* | | |

*Ordered milestones, each ending in something playable or visible. M1 = greybox core loop.*
1. **M1, greybox core loop:** <features> · done when: <checkable statement>
2. **M2 …**

## 7. Game-level acceptance
*Only criteria that span features (e.g. "a first-time player finishes a run in under 60 s without reading text"; "60 fps on <device>"). Per-feature criteria live in each testing.md.*
- [ ] …

## 8. Decisions
*Decisions that will matter later. IDs run in sequence and are never reused. A superseded decision stays, with "→ superseded by D-n" added.*

| ID | Date | Decision | Alternatives considered | Why | Affects |
|---|---|---|---|---|---|
| D-001 | <date> | | | | |

## 9. Risks and open questions
- **Risks:** *(design: "is X fun?"; tech; scope), each with a mitigation.*
- **Assumptions:** *(every [ASSUMPTION] in the GDD, listed for confirmation)*
- **Open questions:**

## Change log
**0.1 (<date>):** first draft.
*Later: "**0.2 (<date>):** combo designed ([combo](features/combo/design.md)); D-003 logged." Keep it to one line per version; the details live in the linked docs.*
~~~
