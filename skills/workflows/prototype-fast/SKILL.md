---
name: prototype-fast
description: >
  Builds a throwaway playable prototype in about an hour to answer one question, usually "is this
  mechanic fun?": a one-question brief, a greybox, a debug HUD, a playtest and a keep, kill or
  retune call. Use for "prototype this", "just get something playable" or whether to keep
  prototype code. Not for a timed jam (`game-jam`) or level blockouts (`level-design`).
---

# Prototype Fast

Get a mechanic playable fast to learn whether it is worth building. The output is a
**decision** (keep, kill or retune) written down in the repo, not a product. The agent writes
the brief, builds the smallest thing that answers it, instruments it, and asks the user to play;
the user's report decides.

## When to use

- Validating one mechanic or "what if", a quick slice of one interaction, or de-risking an idea
  before committing real time.

**Not for:** a jam with a deadline and submission (`game-jam`); level layout and blockout
(`level-design`); shipping (`steam-publish`, `itch-publish`); the production build of a
validated feature (engine or genre skill).

## Workflow

1. **Write the brief first** to `prototypes/<idea>/BRIEF.md` (Pattern 1) and confirm it with the
   user: one question, the core verb, keep and kill signals, a timebox. Two questions means two
   prototypes; one that tests everything decides nothing.
2. **Default to throwaway.** Hard-code values, one file is fine, no architecture. Choose "keep"
   structure only when the user says the code will grow, because prototypes that pretend to be
   production code rot into the shipping codebase.
3. **Contain it.** Build in `prototypes/<idea>/` (a separate project or folder the main game
   never imports) or on a throwaway branch.
4. **Greybox everything but the verb.** Boxes, circles, capsules, the engine's default font,
   no audio or one debug beep. Spend nothing on what the question does not depend on.
5. **Instrument the question.** Draw a debug HUD with the values being judged (speed, jump
   height, timing window, time to first success) and expose the tuning values as named
   constants at the top of the file, so a retune is a one-line change.
6. **Run it yourself first** (Verify), then **ask the user to play** without explanation and
   report: did they do the core verb unprompted, how long it took, did they replay, what felt
   off. If someone else can play, ask the user to watch them and report the same.
7. **Make the call against the brief** and append it to `BRIEF.md`: keep (schedule a rewrite in
   the real project), kill (one line on what was learned), or retune (change one constant and
   play again).

## Patterns

### 1. `BRIEF.md`

```text
QUESTION:   The one thing this must prove, ideally yes/no.
CORE VERB:  The single action the player repeats.
THROWAWAY:  yes (default) | no, because ...
TIMEBOX:    e.g. 60 min; stop when it ends, even if unfinished.
KEEP IF:    observable signal (see Pattern 3).
KILL IF:    observable signal.
RESULT:     <date> keep | kill | retune - evidence from the playtest
```

### 2. Only the verb is real (engine-neutral pseudocode)

```text
const RUN_SPEED = 8.0, JUMP_VELOCITY = 12.0, GRAB_WINDOW = 0.15   # tune here

on update(dt):
    read_input()
    apply_core_mechanic(dt)                  # the only thing being tested
    draw_box(player)                         # a box, not a sprite
    draw_debug_hud(speed, airtime, window_hits, time_to_first_success)
    # enemies, menus, saves, audio, art: stubbed or absent
```

### 3. Keep, kill or retune

```text
KEEP when, with placeholder art:
  - a fresh player does the core verb on purpose within about 30 s, unprompted, and
  - they replay the loop without being asked.
KILL when:
  - the verb only feels good after it is explained, or
  - making it fun needs systems far beyond the prototype, or
  - art or levels are being added to avoid admitting the verb is flat.
RETUNE when one value is clearly off (too slow, window too tight): change it, play again.
```

## Verify

Run these yourself before handing the prototype to the user:

1. It launches from the command line (the engine's run or headless command, or a local web
   server on `127.0.0.1`) with no errors in the log or console.
2. The loop completes: start, perform the verb, succeed or fail, restart. Drive it with a
   scripted input or a short automated run where the engine allows; otherwise play it once.
3. The debug HUD shows the values named in the brief and they change as expected.
4. `git status` (or a search for imports) shows nothing outside `prototypes/<idea>/` changed
   and the main game does not import it.
5. `BRIEF.md` has a RESULT line after the user's playtest.

## Gotchas

- **Polishing too early.** Art, menus and audio make a flat verb look finished and delay the
  verdict.
- **No kill criteria.** Without a written "kill if", every prototype "has potential" and nothing
  is cut. Decide the signal before anyone is attached to the code.
- **Building systems instead of the mechanic.** Inventory, saves and settings are not the
  question. Stub them.
- **The spike becomes the product.** A keep authorizes a rewrite in the real project, not a
  copy-paste of prototype code and its assumptions.
- **Prototyping inside the real codebase.** It tangles experiments with shipping systems and
  makes the spike expensive to delete.
- **Only the author playtests.** The author knows the controls and the intent. One uncoached
  player reveals more in two minutes than an hour of self-play, so always ask the user for a
  report rather than judging it yourself.

## Related skills

- `game-jam`: the same scope discipline under a deadline with a submission.
- `level-design`: when the question is about a level's layout rather than a mechanic.
- `game-feel`: juice, only after the verb is proven.
- Engine cores (`godot-gdscript`, `phaser-core`, `love2d-core`, `unity-csharp-scripting`, ...)
  for the greybox itself and for the rewrite after a keep.
