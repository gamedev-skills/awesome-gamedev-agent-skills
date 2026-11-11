# Workflow modes

Steps for each mode in SKILL.md's workflow. Read only the section you need. "The docs folder" is the folder the project already uses, or `docs/` when there is none. Where each fact lives, decision rows and proof rules are in `references/doc-rules.md`. The question rules and the "what to write, and when" table are in SKILL.md.

**A GDD not in this layout** (one long file, a wiki page): run modes B, C, D and F against the GDD's own sections, in its own format. Make the smallest edit that keeps the doc true, in the user's own style: change the line that holds the old value and, if the doc keeps notes or a change log, record old → new there. Create no index, folders or headers, and don't suggest restructuring unless the user asks.

- [Mode A: Draft the GDD](#mode-a-draft-the-gdd)
- [Mode B: New feature](#mode-b-new-feature)
- [Mode C: Change a feature](#mode-c-change-a-feature)
- [Mode D: Sync after coding](#mode-d-sync-after-coding)
- [Mode E: Migrate existing docs](#mode-e-migrate-existing-docs)
- [Mode F: Record a decision](#mode-f-record-a-decision)

## Mode A: Draft the GDD

1. **Gather.** Take every answer you can from the pitch, the planning chat and the repo. Then ask the one round of questions SKILL.md allows, or none.
2. **Cut the game into features.** List the MVP features (usually 4 to 10) and the likely later ones as rows in the GDD index. Name each with a short noun slug (`combo`, `day-night`); slugs never change once a folder exists.
3. **Write `GDD.md`** from `references/gdd-template.md` in the docs folder. Aim for one page, around 100 lines: if a section grows past a screen, that detail belongs in a feature note. The summary, pillars and core loop must state the actual design in concrete words (what the player spends, does, risks and wins), not placeholders.
4. **Design the core; don't hand back a template.** A draft the user can react to beats an empty form. For the 2 or 3 features the core loop needs (the ones milestone 1 builds), write `features/<slug>/design.md` from `references/feature-templates.md` with a concrete first proposal: rules, starting numbers, how a fight or level is won and lost. Mark every value the user didn't give `[ASSUMPTION]` so they can change it. Set those rows to `designed`. Every other row stays `idea`, with a one-line summary and no folder.
   - **The game already has code:** features that are built get status `implemented` and a note whose numbers are read from the code. Don't write their `implementation.md` or `testing.md` in this pass; offer them as the next step. The checker's `feature-doc-missing` warnings for those features are expected then, and say so in the handoff.
5. **Verify and hand off.** Say which values are assumptions, and name one next step only if it isn't obvious (usually prototyping the core loop with `$prototype-fast`). Don't start coding in the same turn unless the user asked.

## Mode B: New feature

1. Read the GDD (pillars, core loop, feature index) and the notes of features this one touches. If the feature fights a pillar, say so plainly; log the decision either way.
2. If the idea is rough, ask one short round about what's missing: the player-facing goal, interactions with existing systems, numbers, failure and edge cases. Offer options with a recommendation instead of open questions.
3. Write `features/<slug>/design.md`. Add the index row (status `designed`) and a change-log line.
4. If code for it already exists, or the user asks, also write `implementation.md` and `testing.md` against the real code (mode D, steps 2 and 3).

## Mode C: Change a feature

1. **Find the new values first.** Check `git diff`, `git log -p` on config or tuning files, and the conversation. Playtest tuning often lands in code before the docs, and a number in the diff is not a question for the user.
2. **Edit `design.md` in place** so it describes the current design, not its history. Add a dated History line with the old and new value and the reason ("2026-11-02: multiplier cap ×5 → ×6 after playtest, D-014"). Playtest notes earn their place here: what was seen and what changed. Don't write to-dos or follow-ups into the user's doc unless they asked; put open questions in your reply instead.
3. **Follow it through.** If the code already has the change, update the numbers in `implementation.md` and `testing.md` (when they exist). If the code doesn't have the change yet, set `changed — code pending` in `design.md` and the GDD index. Check the notes of other features that link here.
4. **Log a decision** (mode F) if the change reverses an earlier choice or picks between real alternatives.
5. **Cutting:** set the status to `cut`, keep the folder, and add a short note at the top of `design.md` saying why. Cut ideas come back, and the reasoning is the valuable part.

## Mode D: Sync after coding

Goal: someone reading the docs tomorrow can trust them to describe the code as it is.

1. **Find what changed:** `git diff`, or `git log` since the docs were last touched (`git log -1 --format=%cs -- <docs>/features/<slug>`), or the work done in this conversation.
2. **Read the code**, not the plan or your memory. When a feature first gets code, set it to `in progress` and create its `implementation.md` from the template, short: real file paths, config constant names, events, save data. Anything built differently from `design.md` goes under Deviations; then either update `design.md` (and log it) or report it as a bug.
3. **Update `testing.md`** (create it with `implementation.md`). Tick a criterion only when a named test or a dated manual check proves it, with the proof next to it (proof annotations in `references/doc-rules.md`). Run the tests if you can and report the real result.
4. **Set the status** (`in progress` → `implemented` when the feature works end to end) in `design.md` and the GDD index, and add a History line naming the commit if there is one.
5. **Shared structure:** when code several features depend on appears or changes (a save version, an event, a scene flow, a folder move), write or update `ARCHITECTURE.md` from `references/architecture-template.md`.

## Mode E: Migrate existing docs

Only when the user asked for it. Moving content must not lose any of it: plan, move, then check.

1. Read the old docs completely: the GDD and any side files (proposals, design notes, reviews).
2. Save a copy of the old GDD **outside** the docs folder for the checker, e.g. `git show HEAD:docs/GDD.md > <scratch>/old-GDD.md`, or a plain copy made before you start.
3. Build a **mapping table**: every old section or side file → its new home (GDD or `features/<slug>/design|implementation|testing`). Split mixed sections: rules to `design.md`, tech notes to `implementation.md`, acceptance criteria to `testing.md`. A feature gets `implementation.md` or `testing.md` only if the old docs had that content or the code exists. Show the mapping and get one yes before moving anything; this is where mistakes are cheap.
4. Move text **close to verbatim**. Fix only what the new location forces: headings, links, and "see §6.10" references, which become links. Keep numbers, tables and tick marks exactly as they were.
5. Keep the history: the old change log stays in the GDD. Merge dated side docs into their feature, move the originals to `archive/` in the docs folder and link them from the feature's History. The checker ignores `archive/` when comparing.
6. Run `python3 scripts/check_docs.py <docs> --old <scratch>/old-GDD.md --max-issues 0` (repeat `--old` for each side file). For every line and number it reports, either the content landed in reworded form (fine) or it was lost (put it back).
7. Add a change-log line: "Docs split into GDD + features/".

## Mode F: Record a decision

Log a decision when it will matter later: it picks between real alternatives, reverses an earlier choice, or someone will ask "why is it like this?". Skip trivia.

- **GDD in this layout:** add a row to GDD §Decisions (decision row in `references/doc-rules.md`). Feature notes mention the ID in their History line; they don't copy the reasoning.
- **GDD in another form:** add it to the GDD's own decisions or change-log section; if it has neither, append a short "Decisions" table at the end and say so in the handoff.
- **No GDD:** add it where the project keeps decisions or notes (`docs/adr/`, `decisions.md`, `NOTES.md`). If there is no such place, create `docs/decisions.md` holding only the decision table and this row. Don't start a GDD; offer one in a line. The checker needs a GDD, so skip it here and reread the row instead.
