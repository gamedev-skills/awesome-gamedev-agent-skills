# Visual novel script model and flow (depth)

Detail behind `SKILL.md`. Engine-neutral pseudocode. Covers the branching data model, route
structures, and the save/backlog/skip data a VN needs. For the branching-script runtime
(Ink/Yarn) defer to `dialogue-systems`; this file is the VN-specific glue.

Contents:
1. The script data model
2. Route structures
3. Flags and variables
4. Save-anywhere data (Ink, Yarn Spinner, Ren'Py)
5. Backlog, skip and auto
6. Presentation conventions
7. Localization

## 1. The script data model

A VN script is a graph of nodes. Whether authored in Ink, Yarn, or your own format, the engine
walks it node by node:

- **Line:** `speaker`, `text`, optional portrait/expression, optional voice clip.
- **Choice:** a set of options, each with display text, an optional `condition` (flag check),
  a `target` to jump to, and optional flags to `set`.
- **Command:** show/hide character, change background, play music/SFX, set a variable, jump/call.
- **Label / knot:** a named entry point you can jump to.

Keep **content** (lines, choices, conditions) separate from **direction** (which sprite, what
transition). Direction can live as lightweight commands in the script, but the *rendering* of
those commands belongs in the engine layer so writers don't touch code.

## 2. Route structures

| Structure | Shape | Cost | Use |
|-----------|-------|------|-----|
| Linear | one path, no branches | low | Kinetic novels (story-first). |
| Branch-and-merge | branches that reconverge | medium | Most VNs; choices vary the trip, not the destination. |
| Gauntlet / routes | distinct routes per choice/character | high | Dating sims, route-based stories. |
| Flag-driven (state) | endings/lines computed from accumulated flags | medium | Reactive stories; "affection" systems. |

Branch-and-merge gives the *feeling* of choice at a fraction of the writing/art cost of fully
distinct routes. Reserve full routes for the moments that matter (e.g. character endings).

## 3. Flags and variables

- **Booleans** for one-off decisions (`helped_npc`).
- **Counters** for accumulated state (`affection_alice`, `corruption`), compared with thresholds
  to pick lines or endings.
- Evaluate conditions when presenting a choice (to gate/hide options) and when branching (to pick
  a target). Keep all of this in the dialogue runtime's variable store so it saves cleanly.

```python
# Pseudocode. Ending selection from accumulated state.
def pick_ending(flags):
    if flags["affection_alice"] >= 5 and flags["helped_npc"]: return "alice_good"
    if flags["affection_alice"] >= 5:                          return "alice_neutral"
    return "solo"
```

## 4. Save-anywhere data

A VN save must let the player resume the **exact** line. Persist:

```python
save = {
    "version": 1,
    "script_position": script.serialize_position(),   # knot + line index (from the runtime)
    "variables": dict(flags),                          # all story flags/counters
    "seen_text": list(seen_line_ids),                  # for skip-read-only + completion %
    "history": recent_backlog[-200:],                  # optional: restore the backlog
    "scene": {"bg": current_bg, "chars": visible_chars, "music": current_track},
}
```

What the runtime can restore decides how precise "save anywhere" can be:

- **Ink:** `story.state.ToJson()` / `story.state.LoadJson(json)` captures the exact position
  and all variables, so a load resumes the same line.
- **Yarn Spinner:** you can save the variables and the current node name
  (`DialogueRunner.Dialogue.CurrentNode` in Yarn Spinner for Unity 3.x; 2.x had
  `DialogueRunner.CurrentNodeName`) and restart that node, but its FAQ states that the
  specific line inside a node cannot be saved or restored. Keep nodes short, put a node boundary
  wherever a save may happen, or record the last line ID and fast-forward to it on load.
- **Ren'Py:** saving and loading at any line is built in (a save records the start of the
  current statement). Declare story flags with `default`, which is always saved; `define` is for
  constants.

Add a `version` and a migration path so old saves survive script edits (see `save-systems`).
Editing a line that a save points at is the usual way old saves break; give lines stable IDs.

## 5. Backlog, skip, and auto

- **Backlog/history:** append each completed line (speaker + text, and voice handle if any) to a
  ring buffer; a backlog screen scrolls it and can replay voice. Cap length (e.g. 100–200 lines).
- **Skip:** fast-forwards text. Default to skipping **only seen** lines (track `seen_text`);
  optionally allow "skip all" as a setting. Skipping must stop at unseen text and at choices.
- **Auto-advance:** after a line fully reveals, wait `auto_delay` (scaled to text length) then
  advance; pause at choices and cancel on any input.

## 6. Presentation conventions

- **Character positions:** discrete slots (left/center/right); show/hide with a fade or slide.
- **Expressions:** swap a portrait layer rather than reloading the whole sprite.
- **Transitions:** dissolve between backgrounds; a brief fade-to-black marks scene/time changes.
- **Text reveal:** typewriter at a configurable rate; first advance completes the line, second
  advances. Never trap the player in a non-skippable reveal.

## 7. Localization

Keep every player-facing string in data keyed by id (not inline in code/branch logic), so a
translation is a swap of the string table. Allow text expansion (some languages are longer) in
the text box layout, and avoid baking text into images where possible.
