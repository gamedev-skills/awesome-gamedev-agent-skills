---
name: dialogue-systems
description: >
  Builds engine-neutral branching dialogue with Ink, Yarn Spinner or a small JSON graph runner:
  lines, choices, conditions, variables and localization IDs. Use for NPC conversations, dialogue
  trees, barks, .ink or .yarn files, or dialogue that dead-ends. Not for visual-novel backlog and
  skip (`visual-novel`), quests (`rpg`) or text box widgets (`godot-ui-control`, `game-ui-ux`).
---

# Dialogue systems

Model conversations as a graph: nodes hold lines, choices branch, conditions gate options and
a variable store remembers what the player did. The first decision is build or adopt: Ink or
Yarn Spinner when writers need real flow control, a small data-driven runner when lines,
choices and flags are enough. Never build a new scripting language.

## When to use

- Designing branching conversations, choice menus or narrative state that later lines read.
- Choosing between Ink, Yarn Spinner and a custom JSON/resource graph.
- Wiring a dialogue runtime into the game loop: advance, show choices, run commands, persist.

**Not this skill:** VN presentation and flow (`visual-novel`), quest logic (`rpg`), widget
code (`godot-ui-control`, `roblox-ui`) and UI layout rules (`game-ui-ux`), persisting variables
across sessions (`save-systems`).

## Core workflow

1. **Inspect the project**: existing `.ink`/`.yarn`/`.yarnproject` files, an installed
   integration (ink-unity-integration, inkjs, Yarn Spinner for Unity or Godot), or a JSON graph.
   Keep what exists.
2. **Choose the tool.**
   - **Ink**: prose-first, weave and gather flow, read counts as free flags; best for
     dialogue-heavy or choose-your-own-adventure narrative.
   - **Yarn Spinner**: node-based, explicit `<<commands>>` dispatched to game code, built-in
     line IDs for localization; best for game-driven dialogue with many engine hooks.
   - **Custom runner**: a JSON graph plus about 100 lines of interpreter, when you need full
     control or no dependency.
3. **Define the node contract**: a node yields a line (speaker plus line ID), a choice set, a
   command, or an end/jump. The runner hands lines and choices to the UI and waits.
4. **Keep variables outside the UI** in one store the dialogue reads and writes, so cutscenes,
   tests and saves see the same state.
5. **Author line IDs from day one**; display text comes from a per-locale string table.
6. **Apply costs on the transition** (the choice), not on a node the player can revisit.
7. **Validate before handing back:**
   - Ink: `inklecate -o story.json story.ink` exits 1 on compile errors.
   - Yarn: `ysc compile story.yarn` reports errors; `ysc run --auto-advance story.yarn` plays it
     in the terminal.
   - Custom graph: run `validate_graph()` from `references/runner.md`; it must return no
     problems (missing targets, nodes without an exit, undeclared variables, unreachable nodes).
   - Then walk each choice path once with a script that picks choices in order.

## Patterns

### 1. Engine-neutral dialogue graph (data, not code)

```json
{
  "start": "guard_intro",
  "vars": { "gold": 0, "gate_open": false },
  "nodes": {
    "guard_intro": {
      "speaker": "Guard", "line": "DLG_GUARD_001",
      "choices": [
        { "text": "DLG_OPT_BRIBE", "to": "bribe", "if": "gold >= 50",
          "set": { "gold": "gold - 50" } },
        { "text": "DLG_OPT_LEAVE", "to": "end" }
      ]
    },
    "bribe": {
      "speaker": "Guard", "line": "DLG_GUARD_BRIBED",
      "set": { "gate_open": true },
      "next": "end"
    },
    "end": { "end": true }
  }
}
```

`line`/`text` are **string-table IDs** (localization), not literal text. `if`
gates a choice; `set` mutates the variable store. The gold cost sits on the
*choice*, so it is paid once per pick even if the `bribe` node is revisited; the
idempotent `gate_open` write can live on the node. A string `set` value is an
expression, so a literal string needs inner quotes: `"mood": "'angry'"`. The full
interpreter that walks this graph is in `references/runner.md`. Its variable store
starts from `vars`; replace those defaults with the player's saved narrative state
when starting a real conversation. Declare every referenced variable so unknown
names still expose authoring mistakes.

### 2. Runner step (a state machine over the graph)

```gdscript
# Godot 4.7. The runner holds the current node and a variable store. Every line
# waits for the player: the UI calls choose() or the continue callback.
func goto(id: String) -> void:
    current = graph.nodes[id]
    apply_set(current.get("set", {}))
    if current.get("end", false):
        ui.close()
        return
    if current.has("line"):
        ui.show_line(current.get("speaker", ""), localize(current.line))
    if current.has("choices"):
        var shown = current.choices.filter(func(c): return eval_cond(c.get("if", "")))
        ui.show_choices(shown)            # only choices whose condition passes
    elif current.has("next"):
        var next_id: String = current.next
        ui.show_continue(func(): goto(next_id))   # advance when the player continues

func choose(choice: Dictionary) -> void:   # called when the player picks a choice
    apply_set(choice.get("set", {}))       # write on the transition (revisit-safe)
    goto(choice.to)
```

### 3. Ink — branching with knots, choices, and variables (inkle)

```ink
// Ink: '*' = once-only choice, '+' = sticky. [bracketed] text shows only in the
// choice, not the printed result. '->' diverts; '-> END' stops the flow.
VAR gold = 60
-> guard_intro                    // the story starts at the top: divert into a knot

=== guard_intro ===
The guard blocks the gate.
* {gold >= 50} [Offer 50 gold]   "Here, take it."
    ~ gold = gold - 50
    The guard pockets it and steps aside. -> END
* [Leave]   You turn back. -> END
```

Ink tracks how often each knot was seen, so `{visited_knot}` is a built-in
condition. Variables are global (`VAR`) or temporary (`~ temp`).

### 4. Yarn Spinner — nodes, options, and commands (Yarn Spinner 3.x)

```yarn
title: GuardIntro
---
<<declare $gold = 60>>
<<declare $gate_open = false>>
Guard: You can't pass.
-> Offer 50 gold <<if $gold >= 50>>
    <<set $gold = $gold - 50>>
    Guard: ...fine. Go on through.
    <<set $gate_open to true>>
-> Leave
    Guard: Good choice.
===
```

Yarn lines may start with `Speaker:`; options use `->`; `<<set>>`/`<<declare>>`
manage `$variables`; `<<if>>` gates an option; `<<jump NodeName>>` moves between
nodes. Interpolate values in text with `{$gold}`. Declare every variable before first
use: an undeclared one still compiles (Yarn infers its type and a zero/false/empty
start value) with only a warning, which hides typos. These constructs are unchanged from
Yarn Spinner 2.x.

## Gotchas

- **Display strings in the script** instead of line IDs turn localization into a rewrite.
  Yarn tags lines with `#line:` IDs (`ysc tag` adds them); Ink has no line IDs, so tag lines
  yourself (`#id:guard_01`) or translate whole files.
- **A cost on a revisitable node** (`gold - 50` on `bribe`) is paid again on every visit. Put it
  on the choice, or guard it with a seen-flag.
- **Ink `*` versus `+`.** `*` choices vanish after one use, so a looping hub menu built from `*`
  empties itself. Hub menus use sticky `+`.
- **Ink choice text printed twice or not at all.** Text inside `[brackets]` shows only in the
  choice; text before them shows in both; text after only in the output.
- **Ink runtime loop stops after a choice.** After `ChooseChoiceIndex(i)` call `Continue()` (or
  `ContinueMaximally()`) again; the chosen branch prints nothing until you do.
- **Yarn undeclared variables compile with only a warning** and start at 0, false or "", which
  hides typos. `<<declare>>` everything.
- **Yarn 3 syntax in a Yarn 2 project** (`<<once>>`, `<<detour>>`, `when:` node groups) fails
  with "requires version 3 or later". Check the `.yarnproject` language version.
- **Ink Unity integration 2.0** imports `.ink` as an `InkFile` asset; code that loaded the old
  generated `.json` `TextAsset` must switch to `new Story(inkFile.storyJson)`.
- **Dead ends** (a node with no next, choices or end) silently stall the conversation. The
  validation step catches them.
- **`eval()` on dialogue expressions** runs arbitrary code from data files and mods. Use a
  whitelisting evaluator (the runner's `evaluate`).

## References

- `references/ink-and-yarn.md`: read when writing or reviewing `.ink` or `.yarn` (side-by-side
  syntax, Ink weave features, Yarn 3 additions, runtime integration and localization).
- `references/runner.md`: read when building or fixing a custom runner (schema, sandboxed
  `evaluate`, `DialogueRunner`, localization lookup, `validate_graph`).

## Related skills

- `save-systems`: persist narrative variables and seen-flags.
- `godot-resources`, `unity-scriptableobjects`: store dialogue as engine data.
- `godot-ui-control`, `game-ui-ux`: text boxes, portraits and choice buttons.
- `visual-novel`, `rpg`: genres that compose this skill.

## Version notes

Last verified: 2026-11-11.

- Ink 1.2.1 (May 2026) with ink-unity-integration 2.0.0 (July 2026); `inklecate` exits with code
  1 on compile errors and defaults its output to `<name>.ink.json`
  (https://github.com/inkle/ink/releases, inklecate `CommandLineTool.cs`).
- Yarn Spinner 3.2.1 compiler (May 2026), Yarn Spinner for Unity 3.2.8 (August 2026), `ysc`
  3.2.2 with `compile`, `run`, `tag` and `extract`
  (https://github.com/YarnSpinnerTool/YarnSpinner-Console).
- Yarn Spinner engine status: Unity stable; Godot GDScript edition in Early Access (3.3 docs,
  Godot 4.6 or later, not yet recommended for shipping); Godot C# edition marked
  work-in-progress without official support; Unreal listed as a pre-release for UE 5.7 or later
  (https://yarnspinner.dev, https://github.com/YarnSpinnerTool/YarnSpinner-Godot-GDScript,
  https://github.com/YarnSpinnerTool/YarnSpinner-Godot).
