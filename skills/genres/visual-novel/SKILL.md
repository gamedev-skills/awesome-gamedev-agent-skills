---
name: visual-novel
description: >
  Builds visual novels and choice-driven stories in Ren'Py or any engine: routes and endings,
  save-anywhere, backlog, skip-read-only and typewriter text. Use for a VN or dating sim, or loads
  at the wrong line, skip running through unread text or an unreachable ending. Not for dialogue
  in a larger game or Ink and Yarn (`dialogue-systems`) or text box widgets (`godot-ui-control`).
---

# Visual novel

Owns the shape of a branching story and the reading conveniences players expect. The script
runtime (Ren'Py, Ink, Yarn Spinner) does the stepping; this skill decides routes, flags,
saves and the reader-facing systems, and checks them.

## When to use

- The game is mostly reading text with character art, backgrounds and choices.
- Planning routes and endings, affection systems, save behaviour, backlog, skip and auto, or
  checking that every ending can be reached.

**When not to use:** NPC conversations inside another genre (`dialogue-systems`, with `rpg`
for quests); Ink or Yarn integration code (`dialogue-systems`); the text box and choice menu
widgets (`godot-ui-control`, `game-ui-ux`).

## Workflow

1. **Find the engine.** In Ren'Py (`game/*.rpy`), the engine already has save-anywhere,
   rollback, history, skip, auto-forward and text speed: restyle its screens and preferences,
   and spend the effort on routes and flags. Elsewhere, build those systems from refs §4-5.
2. **Draw the route map** before writing: common route, the lock-in point (often about a
   third of the way through), each route's endings, and a true ending gated on finishing
   others if wanted. Write the flags and the thresholds each ending needs next to it.
3. **Size the script.** Readers average roughly 200-250 words per minute, so 1,000 words is
   about 4-5 minutes; a 2-hour VN is about 25,000-30,000 words. Give a meaningful choice or
   reaction every 5-15 minutes of reading, and make at least one later line visibly react to
   each important choice.
4. **Track state** as booleans for one-off decisions and counters for affection. For each
   route, add up the maximum affection the choices can give and set the ending threshold
   below it, with some slack for missed choices.
5. **Saves resume the exact line** with all flags, and seen-text data lives in a persistent
   store shared by all saves (refs §4).
6. **Check it.** Run what applies and report the output:
   - Ren'Py: `./renpy.sh <project> lint --error-code` (exit 1 on lint errors), and
     `./renpy.sh <project> test` for scripted test cases;
   - Ink: `inklecate -o story.json story.ink` (exit 1 on compile errors; `-s` prints word
     counts), then a breadth-first walk with inkjs: `Continue()` while `canContinue`, save
     `state.ToJson()` at each choice, `LoadJson()` and `ChooseChoiceIndex(i)` for each branch,
     and collect `currentTags` at each end. Tag ending lines (for example `# ending:
     alice_good`) and assert every planned ending appears. Cap the depth and dedupe states
     for big scripts;
   - any engine: save at a choice, quit, load, and confirm the same line and choices appear;
     enable skip on a fresh profile and confirm it stops at the first unseen line.

## Reader systems

| System | Default | Notes |
|--------|---------|-------|
| Text speed | instant or fast by default, with a slider | Ren'Py's own default is instant (`preferences.text_cps = 0`) |
| Skip | read text only; stops at choices and unseen lines | Ren'Py: `preferences.skip_unseen = False` |
| Auto-forward | delay scaled by line length; pauses at choices | Ren'Py: `preferences.afm_time = 15` |
| Backlog | 100-200 lines, with voice replay | rollback in Ren'Py doubles as backlog |
| Saves | many slots with thumbnail, date and chapter, plus quick save | autosave at chapter starts and before choices |
| Galleries | CG, music and ending lists unlocked across all saves | Ren'Py `persistent` data |

## Pattern 1: typewriter reveal that does not jump

```python
# Set the full text once, then reveal by visible-character count.
def show_line(speaker, text):
    name_label.text = speaker
    body.text = text                         # wrapping decided once, on the full text
    shown = 0.0
    while shown < visible_length(body) and not advance_pressed():
        shown += cps * frame_dt()
        body.visible_characters = int(shown)
        wait_frame()
    body.visible_characters = -1             # first press completes the line
    backlog.append((speaker, text)); seen.add(line_id)
    wait_for_advance()                       # second press moves on
```

Godot 4.7: `RichTextLabel.visible_characters` with `visible_characters_behavior =
TextServer.VC_CHARS_AFTER_SHAPING` (the default leaves hidden text out of line breaking, so
words still jump). Unity 6.3: `TMP_Text.maxVisibleCharacters`.

## Gotchas

- **Load resumes at the start of a scene** → only a checkpoint or node name is saved. Ink saves
  the exact position with `state.ToJson()`; Yarn Spinner restores only the node (refs §4).
- **Old saves break after an update** → lines moved or edited under a save. Give lines stable
  IDs, keep released labels, and test loading saves from the previous build.
- **Ren'Py flag not saved or reset on load** → declared with `define` (meant for constants)
  instead of `default`. Story state uses `default`.
- **Skip runs through new text** → seen-text stored per save, or skip set to "all". Store seen
  line IDs in persistent data shared by all saves.
- **An ending is unreachable** → thresholds above the maximum the choices can give, or a flag
  set on one branch and read on another. Run the reachability walk (step 6).
- **Choices feel fake** → branches merge back immediately with no reaction. Pay each choice
  off with at least one later line, sprite or option.
- **Text jumps between lines or shows raw tags** → the reveal slices the string (Pattern 1).
- **Branch explosion** → fully separate trees for every choice. Branch and merge, with flags
  that vary lines, and reserve full routes for the big decisions.
- **Text baked into code or images** → no translation path. Keep strings in the script or a
  table keyed by line ID, and leave room for 30% longer text in the box.

## References

- `references/script-and-flow.md`: read when designing the script data model, choosing a
  route structure, picking ending logic from flags, writing save-anywhere data (Ink, Yarn
  Spinner and Ren'Py specifics), backlog, skip and auto behaviour, staging conventions or
  localisation.

Related: `dialogue-systems` (Ink and Yarn runtimes), `save-systems` (slots, versioning),
`game-ui-ux` with `godot-ui-control` (text box, choices, backlog screen), `audio-design`
(music, voice), `prototype-fast` (test the branch map in plain text first).

## Version notes

Last verified: 2026-11-11.

- Ren'Py 8.5.3 is the current stable release (8.6.0 is a prerelease, updated 2026-11-01):
  https://www.renpy.org/latest.html. Preference defaults (`text_cps = 0`, `afm_time = 15`,
  `skip_unseen = False`): https://www.renpy.org/doc/html/preferences.html. `lint
  --error-code` and `test`: https://www.renpy.org/doc/html/cli.html.
- inklecate exits 1 on compile errors and `-s` prints story stats
  (inklecate/CommandLineTool.cs in https://github.com/inkle/ink, ink 1.2.1).
- inkjs 2.4.0 typings: `Continue()`, `canContinue`, `currentChoices`, `currentTags`,
  `ChooseChoiceIndex()`, `state.ToJson()`, `state.LoadJson()`.
- Yarn Spinner for Unity 3.2.8 is the latest release (GitHub releases).
- Reading speed and words-per-hour figures are rough design estimates.
