# Workflow modes

The step-by-step for each mode in SKILL.md's workflow. "The docs folder" means the folder the project already uses, or the one the user confirmed (by default `docs/`). Where to put each fact, proof rules and writing rules are in [doc-rules.md](doc-rules.md).

## Mode A: Start the docs

Only when the user asked for docs. A request to build a game is not a request for docs.

**1. Pick the location.** If the project has no docs folder, propose `docs/` (with `GDD.md`, `ARCHITECTURE.md` and `features/`) and let the user confirm or choose another folder or file names. If a folder already exists, use it.

**2. Extract, then interview.** Take every answer you can from the pitch, the planning session and the repo. Then ask the user for what is missing *and* matters: a few questions at a time, each with 2 to 4 concrete options and your recommendation first. Ask in rounds, most fundamental first, and stop once the essentials are covered:

- *Round 1, essentials:* core fantasy (what the player does and feels), genre and camera, target audience, platforms and input (and orientation).
- *Round 2, shape of play:* session length and structure, win/lose and how harsh failure is, progression within and across sessions, main sources of challenge.
- *Round 3, presentation and scope, if not obvious:* art style and mood (reference games are fine), audio, narrative amount, text language(s), scope (jam / prototype / small release, deadline), and engine/tech if the repo doesn't decide it.

Never invent the core fantasy, the audience or the platform; those come from the user. Fill other gaps with sensible defaults marked `[ASSUMPTION]`.

**3. Cut the game into features.** List the MVP features (usually 4 to 10) and the likely post-MVP ones. If the cut isn't obvious from the planning session, show the list to the user, one line per feature, before writing them up. Feature boundaries are hard to change later because slugs and links depend on them.

**4. Write the docs:**
- The GDD from [gdd-template.md](gdd-template.md).
- ARCHITECTURE.md from [architecture-template.md](architecture-template.md). If the tech isn't decided yet, write what is known, put the choices in §Open questions, and keep it short.
- For each **MVP** feature, a folder with all three docs from [feature-templates.md](feature-templates.md). Before code exists, `implementation.md` is a *plan*: its Approach starts with "**Plan, no code yet.**" and gives the intended approach, modules and risks. `testing.md` holds the acceptance criteria, all unticked.
- Post-MVP features get a row in the GDD index with status `idea` and no folder yet. A folder appears when someone starts designing the feature (mode B).

**5. Verify and hand off** (workflow steps 4 and 5). Suggest the next step, usually milestone 1, a greybox of the core loop. Don't start implementing the game in the same turn unless the user asked for it; `$router` picks the engine and genre skills.

## Mode B: New feature

1. Read the GDD (pillars, core loop, feature index), ARCHITECTURE and the design docs of the features this one touches. A new feature must fit the pillars. If it fights one, say so, and log the decision either way.
2. If the idea is rough, ask the user briefly about what's missing: the player-facing goal, how it interacts with existing systems, numbers, failure and edge cases. Offer 2 or 3 concrete options with a recommendation instead of open questions.
3. Create `features/<slug>/` with all three docs. Fill `design.md` fully. Write `implementation.md` against the real code: the actual modules and files it will touch, the existing events and config it reuses, and what is new. Write `testing.md` with acceptance criteria and the planned tests (named files where the repo's test layout makes that obvious).
4. Add the feature to the GDD index (status `designed`), bump the GDD minor version, and add a change-log line. If it changes game-wide tech (a new event type, a save-format change), update ARCHITECTURE too.

## Mode C: Change a feature

1. Edit `design.md` in place so it always describes **the current design**, not the history of how it got there. Add a dated line to its History section ("2026-11-02: multiplier cap ×5 → ×6 after playtest, D-014").
2. Follow the change through. Does `implementation.md` still match? If the code isn't updated yet, set the status to `changed — code pending` in `design.md`'s header and in the GDD index. Does `testing.md` still test the right numbers? Do other features' docs that link here still hold?
3. Log the decision (mode F) if it reverses or changes a previous one, or if someone will later ask "why is it like this?".
4. Cutting a feature: set the status to `cut`, keep the folder, and add a short note at the top of `design.md` explaining why. Cut ideas come back, and the reasoning is the valuable part.

## Mode D: Sync after coding

The goal: someone reading the docs tomorrow can trust that they describe the code as it is.

1. Find what changed: `git log` / `git diff` since the docs were last touched (`git log -1 --format=%cs -- <docs>/features/<slug>`), or the work done in this conversation. Without git, compare file modification dates against the docs' "Updated" dates, or ask the user what changed.
2. **Read the code.** Don't trust memory or the plan. Update `implementation.md` to match it: real file paths, module and function names, config constant names, events, the save-data shape. Put anything built differently from `design.md` in `implementation.md` §Deviations. Then either change `design.md` to match (if the change is now the design, and log it) or flag it as a bug to fix.
3. Update `testing.md`. Tick an acceptance criterion **only when a named test or a dated manual check proves it**, and write the proof next to it ([proof annotations](doc-rules.md#proof-annotations)). Unticked means "not proven yet", which is useful information, not a failure, so give the reason next to it. Add new tests to the test list. Run the tests if you can and report the real result.
4. Set the status (`in progress` → `implemented`) in `design.md`'s header and the GDD index, and add a History line to `implementation.md` naming the commit if there is one. Update ARCHITECTURE if cross-cutting structure changed (a new module, a new event, a folder move, a save version bump).
5. If code in a feature's area is never mentioned in its docs, that part of the docs is missing. Write it.

## Mode E: Migrate existing docs

Only with the user's yes. Moving content must never lose any of it: plan first, then move, then check.

1. Read the old docs completely: the GDD and any side files (proposals, design notes, reviews).
2. Keep a copy of the old GDD outside the docs folder for the checker, e.g. `git show HEAD:docs/GDD.md > <scratch>/old-GDD.md`, or a plain file copy made before you start if there is no git.
3. Build a **mapping table**: every old section (or side file) → its new home (GDD / ARCHITECTURE / `features/<slug>/design|implementation|testing`). Split mixed sections: rules go to `design.md`, "tech notes" to `implementation.md`, acceptance criteria to `testing.md`. Show the feature list and the mapping to the user and get a yes before moving anything. This is the step where mistakes are cheap.
4. Move the text **close to verbatim**. Migration is not the time to rewrite. Fix only what the new location forces: headings, links, and "see §6.10" references, which become links to the new docs. Keep numbers, tables and tick marks exactly as they were.
5. Keep the history. The old change log stays in the GDD. Dated side docs (`DESIGN-combo-2026-10.md`) are merged into their feature folder, and the original moves to `archive/` inside the docs folder, linked from the feature's History section. Proposals and reviews that aren't about one feature also go to `archive/`, linked from the GDD.
6. Run the checker with `--old` and go through every line and number it reports as missing. Either the content landed somewhere in reworded form (fine) or it was lost (put it back).
7. Bump the GDD version and add a change-log line: "Docs split into GDD + ARCHITECTURE + features/".

## Mode F: Record a decision

Log a decision when it will matter later: it picks between real alternatives, reverses an earlier choice, or will make someone ask "why?". Don't log trivia. Add a row to GDD §Decisions ([decision row](doc-rules.md#decision-row)). Feature docs mention the IDs in their History lines; they don't copy the reasoning.
