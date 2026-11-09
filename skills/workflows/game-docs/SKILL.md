---
name: game-docs
description: >
  Write and maintain a game's design docs: a GDD that links to an ARCHITECTURE.md
  and to per-feature folders with design.md, implementation.md and testing.md,
  kept in sync with the code. Use only when the user asks for game docs ("write a
  GDD", "game design doc", "spec out the combo system", "document this feature",
  "update the docs", "record this decision", "split our GDD into features"), or
  when the project already has a GDD and a feature is designed, changed, built or
  cut. A request to build a game or feature is not a request for docs: build it
  with the engine and genre skills, and at most offer to write docs afterwards,
  writing them only if the user agrees.
---

# Game docs

Give every fact about the game one home (the GDD, ARCHITECTURE or a feature folder) and keep those docs true to the code for the life of the project. Keep the project's existing docs folder, file names, language and conventions; the layout below is only the default for a project that has none.

## When to use

This skill runs only when one of these holds:

1. **The user asked for docs**: a GDD, a design doc, a feature spec or write-up, a docs sync, a decision record, or a migration of existing notes.
2. **The project already has a GDD** (in `docs/`, `design/`, `documentation/`, a wiki folder or the repo root), and a feature is being designed, changed, built or cut. Then keep the docs in step with that work.

**When not to use:** building a game or feature in a project with no GDD, unless the user asked for docs. A request to build something goes to the engine and genre skills through `$router` and is built first. You may offer, in one line, to set up docs for it, but write none unless the user says yes. Also not for level layouts (`$level-design`), jam scoping (`$game-jam`), or READMEs, API references and code comments.

## Workflow

1. **Inspect.** Look before writing anything:
   - **Gate:** confirm that one of the two conditions above holds. If neither does, stop and hand back to `$router`.
   - **Find the docs:** search for a GDD and design notes (`GDD.md`, `*design*`, `*spec*`, `docs/`, `design/`, `documentation/`, `README.md`). Note the folder, the file names, the doc language and the conventions, and keep them all.
   - **No docs folder yet?** Propose a location (by default `docs/` with `GDD.md`, `ARCHITECTURE.md` and `features/`) and let the user confirm or choose another before creating files.
   - **Read the repo:** engine, language, project files, folder layout, test setup. Never ask the user what the repo already answers.
   - **Read the conversation:** an earlier planning session or brainstorm is your main source. Pull every decision, number and name out of it.
   - **Existing docs:** if a doc the user wrote would be overwritten or restructured, stop and ask.
2. **Choose the mode** (several can apply; do them in this order):

   | Situation | Mode |
   |---|---|
   | The user asked for docs and there is no GDD yet | **A. Start the docs** |
   | A GDD in this structure exists; a new feature is proposed or designed | **B. New feature** |
   | An existing feature changes (playtest, tuning, rework, cut) | **C. Change a feature** |
   | Code was written or changed; the docs must match | **D. Sync after coding** |
   | A GDD or notes exist but not in this structure, and the user agreed to restructure | **E. Migrate** |
   | A decision was just made | **F. Record a decision** (also inside every other mode) |

3. **Implement.** Read [references/workflow-modes.md](references/workflow-modes.md) for the steps of the chosen mode, and [references/doc-rules.md](references/doc-rules.md) for where each fact lives, decision rows, proof annotations and writing rules. Use the templates listed under [Resources](#resources).
4. **Verify.** Run the checker on the docs folder. Script paths are relative to this skill's folder:
   ```bash
   python3 scripts/check_docs.py <project>/docs
   python3 scripts/check_docs.py <project>/design --gdd game-design.md      # GDD under another name
   python3 scripts/check_docs.py <project>/docs --old <old-GDD-copy.md>      # migration only
   ```
   Use `python` where `python3` doesn't exist (common on Windows). Exit 0 means no errors. Exit 1 means fix each `ERROR` (and each `WARNING` when it is real, or tell the user why it doesn't apply). Exit 2 means the path or `--gdd` name is wrong, or the folder holds no GDD and no `features/`. Add `--json` for machine-readable output.
5. **Handoff.** Reply briefly with:
   - the docs created or changed, as links;
   - a 2 to 4 line summary of the substance (for mode A: pitch, pillars, MVP features);
   - the `[ASSUMPTION]`s and open questions the user should answer;
   - decisions logged and statuses changed;
   - the suggested next step.

   Don't commit unless the user asks.

## Patterns

### Doc layout

```
<docs folder>/              docs/ unless the project already uses another folder
  GDD.md                    the game as a whole: vision, pillars, core loop, global
                            direction, FEATURE INDEX, scope, decisions, change log
  ARCHITECTURE.md           game-wide tech: engine, module map, conventions, file
                            layout, performance budget, test tooling, build
  features/<slug>/
    design.md               what the feature is and why: rules, numbers, edge cases
    implementation.md       how it is built: modules, files, data, events, deviations
    testing.md              how we know it works: acceptance criteria and their proof
```

Keep existing file names (`game-design.md`, `Design.md`) and pass them to the checker with `--gdd`.

### Statuses and headers

- Every doc starts with a header line: its last-updated date and links to the GDD and its siblings.
- A feature's status appears in two places only, `design.md`'s header (`**Status:** designed`) and the GDD index, and the two must agree.
- **Statuses:** `idea` → `designed` → `in progress` → `implemented`, plus `changed — code pending` and `cut`. Use the same words everywhere.
- Use relative links only. Mark guesses `[ASSUMPTION]` and list them in that doc's Open questions.

### Asking the user

Ask the user only for what is missing *and* matters: a few questions at a time, each with 2 to 4 concrete options and your recommendation first. Never invent the core fantasy, the audience or the platform. Fill other gaps with sensible defaults marked `[ASSUMPTION]`.

## Pitfalls

- **Docs written for a request that only asked for code** → the gate was skipped. With no GDD and no request for docs, build the game first; offer docs at most, and write them only on a yes.
- **Docs created in `docs/` beside an existing `design/` folder** → the inspect step was skipped. Use the existing folder and names.
- **A ticked criterion the test doesn't fully prove** → the test's name was trusted instead of its assertions. Read the test body and tick only the proven part (details in [doc-rules.md](references/doc-rules.md#proof-annotations)).
- **Two docs disagree on a number** → a fact was copied. Keep it in its home and link to it.
- **A GDD section grows past a screen of detail** → feature detail leaked into the GDD. Move it to that feature's docs and leave a one-line summary and link.
- **Links break after a rename** → slugs never change once created. Rename the feature's title, not its folder.
- **Content vanishes in a migration** → it was rewritten or skipped. Map every old section first, move it close to verbatim, and review every `--old` line the checker reports.

## Resources

- [references/workflow-modes.md](references/workflow-modes.md): step-by-step for modes A to F. Read it once a mode is chosen.
- [references/doc-rules.md](references/doc-rules.md): one fact, one home; what counts as a feature; decision rows; proof annotations; writing rules; testing pitfalls. Read it before writing or syncing any doc.
- [references/gdd-template.md](references/gdd-template.md): read it when writing or migrating a GDD.
- [references/architecture-template.md](references/architecture-template.md): read it when writing or migrating ARCHITECTURE.md.
- [references/feature-templates.md](references/feature-templates.md): read it when creating a feature folder.
- `scripts/check_docs.py`: read-only checker (workflow step 4). Run it with `--help` for its options and issue codes.

## Related skills

- `$router`: picks the engine and genre skills that build what the docs describe.
- `$level-design`: layouts, pacing and encounters for individual levels.
- `$prototype-fast`: answering "is it fun?" before a feature earns full docs.
- `$game-jam`: scoping under a deadline. Keep jam docs to the GDD and MVP features.
