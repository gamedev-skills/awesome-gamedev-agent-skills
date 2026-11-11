---
name: game-docs
description: >
  Writes and maintains a game's design docs: a one-page GDD with a feature index and short feature
  notes, kept true to the code by a link and status checker. Use for "draft a GDD", "spec out this
  mechanic", or updating docs after a playtest or code change. Not for building a game when no
  docs were asked for (`prototype-fast`, `game-jam`), READMEs or level layouts (`level-design`).
---

# Game docs

Keep a game's design written down in as few words as will stay true. The GDD is one page that says what the game is and maps its features; each feature's detail lives in its own short note; and every number in the docs matches the code. Docs nobody keeps current are worse than none, so write less, edit in place, and sync after every change.

## When to use

Run only when the user asked for game design docs, or when the project already has a GDD and a feature is being designed, changed, built or cut. A request to build a game or a feature is not a request for docs: let the engine and genre skills build it (through `$router`) and offer docs in one line at the end. Level layouts go to `$level-design`; READMEs, API docs and code comments are not this skill's job.

## Workflow

1. **Look before writing.**
   - Find the existing docs: `GDD.md`, `*design*`, `*spec*`, `docs/`, `design/`, a wiki folder, `specs/` (GitHub spec-kit) or `.kiro/specs/` (Kiro). Keep their folder, file names, language and format.
   - Read the conversation (a planning chat is your main source) and, when code exists, the repo and `git diff`/`git log`. Never ask what the repo or the chat already answers.
   - Sort the project into one of three cases. This decides everything below:
     - **No GDD.** Only a request for a GDD starts one.
     - **A GDD in this layout** (a feature index plus `features/<slug>/design.md`). Use the modes as written.
     - **A GDD in any other form** (one long file, a wiki page, spec-tool folders). **Edit it in place, in its own format.** Make the smallest edit, in the user's style. Don't add an index, folders or headers to it, and don't suggest restructuring unless the user asks (mode E).
2. **Pick the mode** and read its section in [references/workflow-modes.md](references/workflow-modes.md):

   | The user wants | Mode |
   |---|---|
   | a GDD, and there is none | **A. Draft the GDD** |
   | a new feature written up | **B. New feature** |
   | a feature changed after a playtest, tuning, rework or cut | **C. Change a feature** |
   | the docs to match code that was just written or changed | **D. Sync after coding** |
   | an existing GDD split into this layout (asked for explicitly) | **E. Migrate** |
   | a design decision recorded | **F. Record a decision** (also inside every other mode) |

3. **Write.** Use the template for the doc you are creating and [references/doc-rules.md](references/doc-rules.md) for where each fact lives, decision rows and proof annotations. Change existing docs with small edits to the affected section; don't regenerate a whole doc, because the user's own wording is part of the design.
4. **Verify.** Run the checker on the docs folder (paths are relative to this skill's folder; use `python` where `python3` doesn't exist):
   ```bash
   python3 scripts/check_docs.py <project>/docs
   python3 scripts/check_docs.py <project>/design --gdd game-design.md   # GDD under another name
   ```
   Exit 0: no errors. Exit 1: fix each `ERROR`, and each `WARNING` that is real; say why the others don't apply. Exit 2: wrong folder or `--gdd` name. A `NOTE gdd-no-index` means the GDD is not in this layout; that is fine, so leave its structure alone. Then reread every number you touched against its source (the code, the diff or the user's message).
5. **Hand off** in a few lines: the docs created or changed (as links, or the diff for a small edit), the substance in 2 to 4 lines, the `[ASSUMPTION]`s and the questions that really matter, and decisions logged or statuses changed. Add a next step only if it isn't obvious. No to-dos or offers of more docs unless the user asked. Don't commit unless asked.

## What to write, and when

| Moment | Write |
|---|---|
| The user asks for a GDD | `GDD.md` from the template, about one page, with the real design in it, plus a `design.md` with a concrete first proposal (rules and starting numbers, `[ASSUMPTION]`-marked) for the 2 or 3 features the core loop needs. Other features are index rows with status `idea` |
| A feature is designed | its `features/<slug>/design.md` |
| A feature first gets code (status `in progress`) | its `implementation.md` and `testing.md`, short, written against the real code |
| Code that several features share appears (save format, event bus, scene flow) | `ARCHITECTURE.md`. Until then, one line in the GDD summary names the engine |

Write more only when the user asks for it. A plan for code that doesn't exist yet goes stale before the engine is chosen, so it is not written by default.

**Statuses**, the same words everywhere: `idea` → `designed` → `in progress` (code has started) → `implemented`, plus `changed — code pending` and `cut`. A feature's status lives in two places, the GDD index and `design.md`'s `**Status:**` header, and they must agree.

**Questions.** Ask at most one short round before the first draft, and none when the user said "just draft it" or already gave the answers. Ask only what you must not guess: the core fantasy (what the player does and feels), the audience and the platform, plus anything that blocks the draft. Number the questions, give each 2 to 4 options with your recommendation first, and say shorthand answers are fine ("1b, 2: PC only"). Fill every other gap with a sensible default marked `[ASSUMPTION]` and list the open questions in the handoff, where answering them costs the user nothing.

## Gotchas

- **"Draft a GDD" produced 20+ files.** Writing a design note, an implementation plan and a test plan for every MVP feature, plus an ARCHITECTURE.md, before any code exists. Follow the table above: one GDD page plus notes for the core-loop features only.
- **The GDD came back as an empty template.** Pillars and a feature list with every rule deferred give the user nothing to build or argue with. Propose the core mechanics with starting numbers, mark them `[ASSUMPTION]`, and let the user change them.
- **Unasked extras in the user's doc or reply.** To-dos written into their GDD, offers to restructure, "want me to write more docs?" lines. Edit what was asked; put real open questions in the reply.
- **A plain GDD got restructured.** The user asked to "update the dash in our GDD" and the agent added a feature index or folders, often to clear checker messages. Edit the GDD where it is; the checker's `gdd-no-index` is only a note.
- **"Record this decision" started a doc set.** With no GDD, add the decision where the project keeps notes; mode F says where.
- **Asking for numbers that are already in the code.** Playtest tuning often lands in code before the docs. In modes C and D, read the diff first, and set `changed — code pending` only when the code really lacks the change.
- **The agent stalls on questions.** Three rounds of interview, or a "where should the docs go?" stop. Use `docs/` (or the existing folder), name it in the handoff, and ask one round at most.
- **A ticked criterion the test doesn't prove.** The test's name was trusted, not its assertions. Read the test body and tick only the proven part ([proof annotations](references/doc-rules.md#proof-annotations)).
- **Two docs disagree on a number.** It was copied. Each fact has one home; everything else links to it.
- **Feature docs beside a spec tool.** If the project uses spec-kit (`specs/NNN-name/spec.md`) or Kiro specs (`.kiro/specs/<name>/`), those are the feature docs. Link them from the GDD index instead of writing `features/` copies.
- **Links break after a rename.** Slugs never change once created; rename the feature's title, not its folder.
- **Content vanishes in a migration.** Mode E moves text close to verbatim and checks with `--old <copy> --max-issues 0`, so no reported line is hidden.

## Resources

- [references/workflow-modes.md](references/workflow-modes.md): the steps for modes A to F. Read only the section for the chosen mode.
- [references/doc-rules.md](references/doc-rules.md): one fact, one home; what counts as a feature; decision rows; proof annotations; testing pitfalls; writing rules. Read before writing or syncing any doc.
- [references/gdd-template.md](references/gdd-template.md): read when drafting a GDD (mode A) or migrating one (mode E).
- [references/feature-templates.md](references/feature-templates.md): read when creating a feature's `design.md`, `implementation.md` or `testing.md`.
- [references/architecture-template.md](references/architecture-template.md): read when shared code first needs an ARCHITECTURE.md.
- `scripts/check_docs.py`: read-only checker (workflow step 4). `--help` lists its options and every issue code.

## Related skills

- `$router`: picks the engine and genre skills that build what the docs describe.
- `$prototype-fast`: finding out whether a mechanic is fun; write its feature note once it is kept.
- `$game-jam`: scoping under a deadline. Jam docs are the GDD page and nothing else.
- `$level-design`: layouts, pacing and encounters for individual levels.
