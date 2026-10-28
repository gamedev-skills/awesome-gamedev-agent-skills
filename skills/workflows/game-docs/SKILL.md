---
name: game-docs
description: >
  Build and maintain the full documentation set for a game project: a Game Design
  Document (GDD) that links to an ARCHITECTURE.md and to per-feature folders
  (design.md, implementation.md, testing.md), kept in sync with the code. Use
  whenever work starts on a new game ("let's make a game", "new game idea", "I want
  to build a game about…", "draft a GDD", "design doc", after a planning session),
  whenever a feature is proposed, designed, changed, built or cut ("design the combo
  system", "write up this feature", "add a feature doc", "spec out X"), after
  implementing or refactoring game code so the docs match the code ("update the
  docs", "sync docs", "the docs are out of date"), when recording a design decision,
  and when an existing GDD or loose design notes need splitting into this structure.
  Use it even when the user only says "document this" in a game project, and before
  writing game code for a feature that has no design doc yet.
---

# Game docs

Give every fact about the game one home (GDD, ARCHITECTURE or a feature folder) and keep those docs true to the code for the whole life of the project. Keep an existing project's docs folder, doc language and conventions; use the defaults below only for new docs.

Game projects drift: the design changes in playtests, the code changes faster, and one big GDD ends up 1000 lines long, mixing vision with file paths and test notes, and nobody trusts it. The structure in [Patterns](#patterns) prevents that.

## When to use

- Use when work starts on a new game, or right after a planning session or brainstorm.
- Use when a feature is proposed, designed, changed, built or cut.
- Use after implementing or refactoring game code, so the docs match the code.
- Use when a design decision is made that someone will later ask "why?" about.
- Use when an existing GDD or loose design notes need splitting into this structure.
- Use before writing game code for a feature that has no design doc yet.

**When not to use:** writing the game code itself goes to the engine and genre skills (`$router` picks them); level layouts to `$level-design`; jam scoping to `$game-jam`; READMEs, API references and code comments are not game design docs.

## Workflow

1. **Inspect.** Look before writing anything:
   - Find existing docs: `docs/`, `GDD.md`, `*design*`, `*spec*`, `README.md`, `CHANGELOG.md`. Note the docs folder, the doc language and the conventions already in use, and keep them.
   - Read the repo: engine, language, `package.json` / project files, folder layout, test setup. Never ask the user what the repo already answers.
   - Read the conversation: if there was a planning session or brainstorm earlier, it is your main source. Pull every decision, number and name out of it.
   - If an existing doc would be overwritten, stop and ask. Never silently replace a doc the user wrote.
2. **Choose.** Pick the mode:

   | Situation | Mode |
   |---|---|
   | No GDD yet (new game, or idea + planning session) | **A. Start the docs** |
   | GDD in this structure exists; a new feature is proposed or designed | **B. New feature** |
   | An existing feature's design changes (playtest, tuning, rework, cut) | **C. Change a feature** |
   | Code was written or changed; docs need to match | **D. Sync after coding** |
   | A GDD/notes exist but not in this structure | **E. Migrate** |
   | A decision was just made | **F. Record a decision** (also happens inside every other mode) |

   Several modes can apply in one request (e.g. migrate, then add a feature). Do them in that order.
3. **Implement.** Follow the mode's steps below, using the [Patterns](#patterns) for layout, headers, statuses and writing rules.
4. **Verify.** Run the checker. It finds broken links, missing feature files, index rows without folders (and the reverse), and mismatched statuses:
   ```bash
   python3 <this-skill-dir>/scripts/check_docs.py <project>/docs
   python3 <this-skill-dir>/scripts/check_docs.py <project>/docs --old <old-GDD-copy.md>   # migration only
   ```
   Use `python` instead of `python3` where only that exists (common on Windows). (For a migration, keep a copy of the old GDD outside `docs/`, e.g. via `git show HEAD:docs/GDD.md > <scratch>/old-GDD.md`, or a plain file copy made before you start if there is no git.) Fix what it reports, or tell the user why a warning doesn't apply.
5. **Handoff.** Reply briefly with:
   - which docs were created or changed (as links);
   - a 2 to 4 line summary of the substance (for mode A: pitch, pillars, MVP features);
   - the `[ASSUMPTION]`s and open questions the user should answer;
   - decisions logged, and statuses changed;
   - the suggested next step.

   Don't commit unless the user asks you to.

### Mode A: Start the docs

**1. Extract, then interview.** Take every answer you can from the pitch, the planning session and the repo. Ask only for what is missing *and* matters, with `AskUserQuestion` (at most 4 questions per call, 2 to 4 options each, recommended option first and marked "(Recommended)"). Ask in rounds, most fundamental first, and stop once the essentials are covered:

- *Round 1, essentials:* core fantasy (what the player does and feels), genre and camera, target audience, platforms and input (and orientation).
- *Round 2, shape of play:* session length and structure, win/lose and how harsh failure is, progression within and across sessions, main sources of challenge.
- *Round 3, presentation and scope, if not obvious:* art style and mood (reference games are fine), audio, narrative amount, text language(s), scope (jam / prototype / small release, deadline), engine/tech if the repo doesn't decide it.

Never invent the core fantasy, the audience or the platform; those come from the user. Fill other gaps with sensible defaults marked `[ASSUMPTION]`.

**2. Cut the game into features.** List the MVP features (usually 4 to 10) and the likely post-MVP ones. Show the list to the user in one line each before writing them up if the cut isn't obvious from the planning session; feature boundaries are hard to change later because slugs and links depend on them.

**3. Write the docs:**
- `docs/GDD.md` from [references/gdd-template.md](references/gdd-template.md).
- `docs/ARCHITECTURE.md` from [references/architecture-template.md](references/architecture-template.md). If the tech isn't decided yet, write what is known, put the choices in §Open questions, and keep it short.
- For each **MVP** feature, a folder with all three docs from [references/feature-templates.md](references/feature-templates.md). Before code exists, `implementation.md` is a *plan* (its Approach starts with "**Plan, no code yet.**"): the intended approach, modules and risks. `testing.md` holds the acceptance criteria, all unticked.
- Post-MVP features get a row in the GDD index with status `idea`, and no folder yet. A folder appears when someone starts designing the feature (mode B).

**4. Verify and hand off** (workflow steps 4–5). Suggest the next step, usually milestone 1, a greybox of the core loop. Don't start implementing the game in the same turn unless the user asked for it. For engine and genre skills, `$router` picks the right ones.

### Mode B: New feature

1. Read the GDD (pillars, core loop, feature index), ARCHITECTURE and the design docs of the features this one touches. A new feature must fit the pillars. If it fights one, say so, and log the decision either way.
2. If the idea is rough, interview briefly (same `AskUserQuestion` rules) about what's missing: the player-facing goal, how it interacts with existing systems, numbers, failure and edge cases. Offer 2 or 3 concrete options with a recommendation instead of open questions.
3. Create `docs/features/<slug>/` with all three docs. Fill `design.md` fully. Write `implementation.md` against the real code: name the actual modules and files it will touch, the existing events and config it reuses, and what is new. Write `testing.md` with acceptance criteria and the planned tests (named files where the repo's test layout makes that obvious).
4. Add the feature to the GDD index (status `designed`), bump the GDD minor version, and add a change-log line. If it changes game-wide tech (a new event type, a save-format change), update ARCHITECTURE too.

### Mode C: Change a feature

1. Edit `design.md` in place so it always describes **the current design**, not the history of how it got there. Add a dated line to its History section ("2026-11-02: multiplier cap ×5 → ×6 after playtest, D-014").
2. Follow the change through: does `implementation.md` still match? (If the code isn't updated yet, set the status to `changed — code pending` in `design.md`'s header and in the GDD index.) Does `testing.md` still test the right numbers? Do other features' docs that link here still hold?
3. Log the decision (mode F) if it reverses or changes a previous decision, or if someone will later ask "why is it like this?".
4. Cutting a feature: set the status to `cut`, keep the folder, and add a short note at the top of `design.md` explaining why. Cut ideas come back, and the reasoning is the valuable part.

### Mode D: Sync after coding

The goal: someone reading the docs tomorrow can trust that they describe the code as it is.

1. Find what changed: `git log` / `git diff` since the docs were last touched (`git log -1 --format=%cs -- docs/features/<slug>`), or the work done in this conversation. Without git, compare file modification dates against the docs' "Updated" dates, or ask the user what changed.
2. **Read the code.** Don't trust memory or the plan. Then update `implementation.md` so it matches the code: real file paths, module and function names, config constant names, events, the save-data shape. Put anything that was built differently from `design.md` in `implementation.md` §Deviations, then either change `design.md` to match (if the change is now the design; log it) or flag it as a bug to fix.
3. Update `testing.md`: tick an acceptance criterion **only when a named test or a dated manual check proves it**, and write the proof next to it (see [Proof annotations](#proof-annotations)). Unticked means "not proven yet", which is useful information, not a failure, so give the reason next to it. Add new tests to the test list. Run the tests if you can, and report the real result. A ticked box that isn't true is worse than an unticked one, because nobody checks it again; the first five [Pitfalls](#pitfalls) are the ways that happens.
4. Set the status (`in progress` → `implemented`) in `design.md`'s header and the GDD index, and add a History line to `implementation.md` naming the commit if there is one. Update ARCHITECTURE if cross-cutting structure changed (new module, new event, folder move, save version bump).
5. Code in a feature folder that the docs never mention means that part of the docs is missing. Write it.

### Mode E: Migrate existing docs

Moving content must never lose any. Plan first, then move, then check.

1. Read the old docs completely (the GDD and any side files: proposals, design notes, reviews).
2. Build a **mapping table**: every old section (or side file) → its new home (GDD / ARCHITECTURE / `features/<slug>/design|implementation|testing`). Mixed sections get split: a section's rules go to `design.md`, its "tech notes" go to `implementation.md`, its acceptance criteria go to `testing.md`. Present the feature list and the mapping to the user and get a yes before moving anything. This is the step where mistakes are cheap.
3. Move the text **close to verbatim**. Migration is not the time to rewrite. Fix only what the new location forces: headings, links, and "see §6.10" references, which become links to the new docs. Keep numbers, tables and tick marks exactly as they were.
4. Keep the history: the old change log stays in the GDD. Dated side docs (`DESIGN-combo-2026-10.md`) are merged into their feature folder, and the original moves to `docs/archive/` with a link from the feature's History section. Proposals and reviews that aren't one feature go to `docs/archive/` and are linked from the GDD.
5. Run the checker with `--old` (workflow step 4) and go through every line it reports as missing. Either the content landed somewhere in reworded form (fine), or it was lost (put it back).
6. Bump the GDD version and add a change-log line: "Docs split into GDD + ARCHITECTURE + features/".

### Mode F: Record a decision

Log a decision when it will matter later: it picks between real alternatives, reverses an earlier choice, or will make someone ask "why?". Don't log trivia. Add a row to GDD §Decisions (format in [Decision row](#decision-row)). Feature docs mention the IDs in their History lines; they don't copy the reasoning.

## Patterns

### Doc layout

```
docs/
  GDD.md                    the game as a whole: vision, pillars, core loop, global
                            direction, FEATURE INDEX, scope, decisions, change log
  ARCHITECTURE.md           game-wide tech: engine, module map, data flow, conventions,
                            file layout, performance budget, test tooling, build
  features/<slug>/
    design.md               what the feature is and why: rules, numbers, edge cases
    implementation.md       how it is built: modules, files, data, events, deviations
    testing.md              how we know it works: acceptance criteria, tests, playtests
```

`docs/` is the default location. If the project already keeps its docs in another folder (`documentation/`, `design/`, a wiki submodule), use that folder instead, and read every `docs/` in this skill as that folder.

### One fact, one home

**The one rule that makes this work: each fact lives in exactly one place, and everything else links to it.** A tuning number lives in that feature's `design.md`; the GDD index gives a one-line summary and a link; `implementation.md` names the config constant that holds it; `testing.md` tests it. When you are tempted to copy something, link to it.

| Kind of content | Home |
|---|---|
| Pitch, audience, platform, pillars, core loop, tone, art/audio *direction* (the style everyone follows) | GDD |
| Rules, numbers, UX, HUD, feel, audio/art *specific to one feature* | `features/<slug>/design.md` |
| Engine, scene/state machine, event bus, save format, config conventions, folder layout, perf budget | ARCHITECTURE |
| Which modules/files a feature touches, its data, events, persistence, perf cost | `features/<slug>/implementation.md` |
| Acceptance criteria, test files, manual playtest steps, metrics to watch | `features/<slug>/testing.md` |
| Decisions that matter beyond today (chosen option, alternatives, why) | GDD §Decisions |
| What changed when | GDD §Change log (game level) and each feature doc's History line |

### What counts as a feature

Anything you can design, build, ship and test as a unit: a mechanic (combo, jump), a system (save, difficulty curve, procedural track), a screen or flow (garage, tutorial, sharing), a content set (biomes, vehicle roster), a platform concern (PWA, controls). If it has its own rules *and* its own code *and* its own tests, it gets a folder. Global direction (pillars, art style) is not a feature. Slugs are short kebab-case nouns (`combo`, `day-night`, `first-run-tutorial`) and never change once created, because other docs link to them.

### Header, status and links

- **Every doc starts with a header line** that has its last-updated date and links back to the GDD and to its two siblings. The feature's status is in `design.md`'s header and in the GDD index, nowhere else.
- **Statuses:** `idea` → `designed` → `in progress` → `implemented`, plus `changed — code pending` and `cut`. They are the same words everywhere, so the index can be scanned and grepped.
- **Relative links only** (`../../GDD.md`, `../combo/design.md`), so the docs work on GitHub, in an editor and offline.
- `[ASSUMPTION]` marks anything you guessed. Collect these in that doc's Open questions.

### Decision row

| ID | Date | Decision | Alternatives considered | Why | Affects |
|---|---|---|---|---|---|
| D-014 | 2026-11-02 | Combo cap ×6 | keep ×5; uncapped | playtests: skilled runs flatline at ×5 by 2 km | combo (a relative link to `features/combo/design.md`) |

IDs run in sequence and are never reused. A superseded decision stays in the table, with "→ superseded by D-021" added to its Decision cell.

### Proof annotations

Every criterion in `testing.md` carries its proof or the reason it has none:

```text
- [x] Multiplier rises on each stunt  *(tests/combo.test.ts › stunts)*
- [x] Share card renders  *(browser check 2026-10-27: headless Chrome, 390×844 touch, Web Share API stubbed)*
- [ ] The iOS share sheet receives the card  *(not proven: needs a device)*
- [ ] Combo survives breathers in a real run  *(not proven: no test)*
```

A criterion that belongs to another feature is not ticked here: write a plain "Covered in" line that links to that feature's `testing.md` (template in [references/feature-templates.md](references/feature-templates.md)).

### Writing rules

- **Be concrete.** Use numbers for every tunable: speeds, timers, sizes, HP, rates, counts, prices, with units. First guesses are fine: write them down and say they're first guesses.
- **Acceptance criteria are checkable statements** with a number or an observable result ("A hit costing HP drops the multiplier to ×1 within the same frame"), not wishes ("combo feels good").
- **Proportionate length.** A small feature's three docs can be 20 lines each. Don't pad sections: write "n/a: no persistence" in one line and move on.
- Use the language the existing docs use; for new docs, English unless the user asks otherwise. In-game strings stay in the game's language.
- Short paragraphs, bullets and tables. Skimmable beats complete.

## Pitfalls

- **Ticked criterion the test doesn't fully prove** → a test's name is not proof; its assertions are, and names drift and promise more than the code checks (a test called "oil locks lane changes for 0.8 s" may only check the lane right after the slick; a unit test of `Combo.update(held)` doesn't prove a real run passes `held` inside breathers). Read the test body; when the proof covers less than the criterion, split it: tick the proven part, worded as narrowly as the test (a truck, not "any tall obstacle"; three screen sizes, not "every aspect"), and keep the rest unticked with its reason. Don't leave a true, proven part unticked because the rest isn't.
- **The same rule as a checkbox in two features** → copies drift and the counts double. Keep it in its home feature and point to it in a plain line (head-on crashes belong to damage, the fast drop to controls).
- **A new test that can't fail** → it proves nothing. Before ticking on it, break the value it guards for a moment (a config number, a data flag), run it, see it fail, and restore the file from a backup. Say so when a test is a guard the current code can't break.
- **Stubbed browser check ticked as "works on device"** → a stub proves the game's own logic, not the platform. Name date, browser, viewport and stubs in the check, and keep a separate unticked line for the real device.
- **A check fails or surprises you and the environment gets blamed** → first rule out the check itself (reading a label after a 5 s wait sees it already reset), then get the real error, e.g. by calling the module directly in the page. Code that swallows errors into a quiet fallback hides real bugs this way. Fix the bug or report it, and record it in that feature's implementation History.
- **Two docs disagree on a number** → a fact was copied, and one copy went stale. Keep it in its home and replace the copy with a link.
- **A GDD section grows past a screen of detail** → feature detail leaked into the GDD. Move it to that feature's docs and leave a one-line summary and link.
- **Links break after a rename** → slugs never change once created; rename the feature's title, not its folder.
- **Content vanishes in a migration** → it was rewritten or skipped. Map every old section first, move close to verbatim, and go through every `--old` checker line.
- **Existing docs use another folder, structure or language** → keep the folder and language; migrate the structure (mode E) only with the user's yes.

## Resources

- Read [references/gdd-template.md](references/gdd-template.md) when writing or migrating a GDD.
- Read [references/architecture-template.md](references/architecture-template.md) when writing or migrating ARCHITECTURE.md.
- Read [references/feature-templates.md](references/feature-templates.md) when creating a feature folder.
- Run `scripts/check_docs.py --help` before using the checker (workflow step 4).

## Related skills

- `$router` — picks the engine and genre skills that build what the docs describe.
- `$level-design` — layouts, pacing and encounters for individual levels.
- `$prototype-fast` — answering "is it fun?" before a feature earns full docs.
- `$game-jam` — scoping and scheduling under a deadline; keep jam docs to the GDD and MVP features.
