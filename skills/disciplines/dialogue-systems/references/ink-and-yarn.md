# Ink and Yarn Spinner: syntax cheat sheet

Contents:
1. Side-by-side syntax table
2. Ink essentials (includes, sticky choices, gathers, read counts, alternatives, functions)
3. Yarn Spinner essentials (declare, options, commands, Yarn 3 additions)
4. Integration notes (runtime loop, presenters, localization, variable bridging)

Pick **Ink** for prose-first, heavily branching writing; pick **Yarn Spinner** for node-graph
dialogue with explicit engine commands. This sheet covers the constructs you reach for most;
consult the official docs for the full language.

## Side-by-side

| Concept | Ink (inkle) | Yarn Spinner 3.x |
|---|---|---|
| Unit of content | **knot** `=== name ===` (sub-units = stitches `= name`) | **node** with `title:` header, body between `---` and `===` |
| Plain line | bare text | bare text, optional `Speaker:` prefix |
| Choice / option | `*` once-only, `+` sticky | `->` option, with indented body |
| Move flow | divert `-> name`, end `-> END` / `-> DONE` | `<<jump NodeName>>` |
| Declare variable | `VAR gold = 0` (global), `~ temp x = 0` | `<<declare $gold = 0>>` |
| Set variable | `~ gold = gold - 5` | `<<set $gold = $gold - 5>>` |
| Show variable | `{gold}` | `{$gold}` |
| Condition on choice | `* {gold >= 50} [Bribe] ...` | `-> Bribe <<if $gold >= 50>>` |
| Conditional text | `{flag: yes text\|no text}` | `<<if $flag>>...<<else>>...<<endif>>` |
| Constants | `CONST MAX = 3` | (use a declared variable) |
| Comments | `// line` and `/* block */` | `// line` |

## Ink essentials

```ink
INCLUDE characters.ink              // split content across files (top of file)
VAR gold = 60                       // global variables
VAR met_guard = false
CONST GATE_COST = 50

-> tavern                           // content outside a knot runs first; divert in

=== tavern ===
The tavern is warm and loud.
+ [Talk to the guard] -> guard      // sticky: still offered when you come back
* [Leave] -> END

=== guard ===
{ met_guard: "You again." | "Who are you?" }   // conditional text: read the flag first
~ met_guard = true                  // '~' marks a logic line (assignment / call)
+ {gold >= GATE_COST} [Pay {GATE_COST} gold]    // sticky choice, gated, interpolated
    ~ gold = gold - GATE_COST
    -> END
+ [Never mind] -> tavern            // sticky so the menu can loop
```

Useful Ink behaviors:

- **Square brackets in a choice** split what the player sees from what prints:
  `* "Yes[."]," I said.` offers the option `"Yes."` and prints `"Yes," I said.`
- **Gathers** (`-`) rejoin branches without naming a knot — the core of "weave".
- **Read counts**: any knot/stitch name used in a condition is the number of
  times it has been visited (`{seen_clue > 2}`), so flags are often free.
- **Alternatives** vary text on revisits: `{a|b|c}` sequence, `{&a|b}` cycle,
  `{!a|b}` once-only, `{~a|b}` shuffle.
- **Randomness**: `RANDOM(1, 6)` (inclusive); `SEED_RANDOM(n)` for repeatable tests.
- **Functions**: `=== function name(args) ===` with `~ return value`.

## Yarn Spinner essentials

```yarn
title: Tavern
---
<<declare $gold = 60>>
<<declare $met_guard = false>>
The tavern is warm and loud.
-> Talk to the guard
    <<jump Guard>>
-> Leave
    Narrator: You step back into the night.
===

title: Guard
---
<<if $met_guard>>
    Guard: You again.
<<else>>
    Guard: Who are you?
<<endif>>
<<set $met_guard to true>>
-> Pay 50 gold <<if $gold >= 50>>
    <<set $gold = $gold - 50>>
    Guard: ...go on through. You have {$gold} left.
-> Never mind
    <<jump Tavern>>
===
```

Useful Yarn behaviors:

- **Variables** start with `$`, hold number/string/bool, and must keep their
  type. `<<declare>>` them up front (often in a setup node).
- **Operators** have word and symbol forms: `is`/`==`, `and`/`&&`, `or`/`||`,
  `not`/`!`, plus `<`, `>`, `<=`, `>=`.
- **Commands** (`<<...>>`) that aren't built in are dispatched to your game code,
  e.g. `<<playSound door_open>>` calls a registered command handler.
- **Functions** (`visited("Node")`, custom registered functions) return values
  usable in `<<if>>` and `{ }` interpolation.
- **Yarn Spinner 3 additions** (need Yarn language version 3; an older project
  fails with "requires version 3 or later"): `<<once>>` … `<<endonce>>` runs a block only
  the first time; `<<detour Node>>` visits a node and returns, where `<<jump>>`
  never comes back; several nodes sharing one `title:` with `when:` headers form
  a node group, and the runner picks one whose condition passes (for barks and
  storylets).

## Integration notes

- **Ink**: compile `.ink` to JSON, then step the runtime: loop
  `Continue()` while `canContinue`, show `currentChoices`, call
  `ChooseChoiceIndex(i)`, and then `Continue()` again; the chosen branch does not
  print until you do. Integrations: Unity (official, inkle), web (inkjs), Godot
  (community C# and GDScript ports). The Unity integration 2.0 no longer writes a
  `.json` beside each `.ink`: it imports an `InkFile` asset, so build the story with
  `new Story(inkFile.storyJson)` (1.x projects referenced the generated `TextAsset`).
- **Yarn Spinner** (3.x): a `DialogueRunner` steps `.yarn` nodes and hands lines
  and options to **Dialogue Presenters** (`DialoguePresenterBase` subclasses; 3.0
  replaced 2.x Dialogue Views), while commands go to registered handlers. Official
  integrations exist for Unity, Godot (C# and GDScript editions) and Unreal; only the
  Unity one is a stable release (status per engine is in the skill's Version notes).
- **Localization**: Yarn Spinner tags every line with a `#line:` ID and exports
  string tables per locale. Ink has no built-in line-ID localization: either
  translate whole `.ink` files per locale, or tag lines (`#id:guard_01`) and look the
  text up in your own tables by tag. Either way, ship per-locale data rather than
  editing the script in place.
- **Variable bridging**: expose game state to the script (gold, flags, quest
  stage) via variable storage / external functions so dialogue reacts to play,
  and persist that state through `save-systems`.

Originality note: the snippets above are minimal originals written to illustrate
each construct, verified against the official Ink and Yarn Spinner documentation.
