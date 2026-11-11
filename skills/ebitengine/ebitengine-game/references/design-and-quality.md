# Design and finish a game

Use for a new game or substantial redesign. A tiny arcade game can be finished
through a few deliberate passes. Repeated internal testing is part of one
delivery; no skill guarantees the first untested implementation will be fun.

## Contents

- [Establish the product before choosing systems](#establish-the-product-before-choosing-systems)
- [Choose structure from the game](#choose-structure-from-the-game)
- [Iterate on a representative slice](#iterate-on-a-representative-slice)
- [Calibrate content to capabilities](#calibrate-content-to-capabilities)
- [Finish the presentation in context](#finish-the-presentation-in-context)
- [Verify a complete session](#verify-a-complete-session)

## Establish the product before choosing systems

Record a short brief in the project with concrete answers:

- **Player experience:** the repeated decision, information available and visible
  consequence. A theme or list of engine features is not the core loop.
- **Complete scope:** how play starts, what progress means, what ends/sustains a
  session and how to retry/continue. State the content promised in this build.
- **Presentation:** visual language, scale, focal point, motion and sound character.
  Use a coherent palette, typography and shape/sprite language tied to the game.
  Quality need not mean detailed assets or expensive effects.
- **Delivery:** platform, viewport, controls, language, persistence and relevant
  accessibility needs. Keep unknown assumptions visible.
- **Acceptance:** observable criteria for this game: a new player understands the
  first goal, a legal move has immediate feedback, failure permits a clean retry,
  text fits and the requested build launches. Add genre-specific criteria.

If genre/content is open, pick a focused concept and proceed. Keep scope small
enough to finish; a coherent game benefits more from refinement than from an
unfinished extra system.

## Choose structure from the game

| Game need | Useful implementation | Check in play |
| --- | --- | --- |
| Timing, aiming, movement | fixed-step motion, intentional input forgiveness, clear hit/hurt rules | latency, collision visibility, recovery |
| Puzzle, cards, board decisions | legal moves, explicit turn/state transitions, undo/hints if appropriate | unambiguous interaction, solvability, no unintended deadlock |
| Strategy or simulation | commands, selection, resource/progression model, bounded simulation work | dense-state readability, visible priorities, speed/pause behavior |
| Exploration or narrative | interaction state, authored pacing, dialogue/progress | where to go next, readable text, interruption/resume |
| Sandbox or endless play | sustainable loop, reset/pause, progression or player-created goals | continued agency and recovery rather than a forced win screen |

These are examples, not required genres. Let a tile grid, ECS, physics engine,
level editor or procedural generator earn its place. The starter demonstrates
engine wiring; replace its platformer rules when the brief calls for another game.

## Iterate on a representative slice

Build enough of the real experience to judge: the intended control, meaningful
opposition/constraint, feedback and a consequence. Include the visual direction
early so mechanics and presentation are evaluated together. Exercise it before
multiplying levels, cards or enemies.

For each pass, observe a specific problem, change its cause and repeat the same
interaction. Examples: near-edge jump ignored → inspect input/collision timing;
puzzle move appears ignored → show selection, legal targets and result; enemies
blend into scenery → fix silhouette/value separation before adding particles.
Avoid applying every game-feel effect to every game.

Work backwards from the desired experience: predict which rule makes the player
choose a particular behavior, then observe whether the slice produces it. For
example, limited ammunition may encourage positioning or may merely add waiting;
check which occurs before adding more weapons. Mechanics, resulting player
behavior and felt experience are different claims. Effects cannot establish
that a decision is interesting. This is a practical use of the
[MDA framing](https://github.com/pluginagentmarketplace/custom-plugin-game-developer/blob/aa7edfe267b34eac63d888f60b13e08aca7850ed/skills/game-design-theory/SKILL.md),
not a formula that guarantees enjoyment.

## Calibrate content to capabilities

Before producing many encounters, establish the measurements they depend on:
jump reach and recovery, attack/range limits, movement per turn, obtainable
resources, time to complete a route, or readable choices on one screen. Make
representative content with comfortable and demanding margins, then verify both.
If a capability changes, identify and recheck the content whose assumptions changed.

Test **reachability**, not just absence of crashes: a gap must be traversable, a
required purchase must be affordable from reachable resources, a target score
must be attainable, and a puzzle needs a legal solution. A known solution proves
existence, not uniqueness or a good difficulty curve. Introduce a pattern in a
readable situation before combining it with another demand; a tutorial label is
not evidence the player learned it. These checks adapt the capability/content
relationship in [Higgsfield's design system](https://github.com/higgsfield-ai/skills/blob/f83af0bc1d937c8119099a11f8ebbf5e6fb99819/higgsfield-websites/references/game-design-system.md).

Where randomness matters, inspect both typical outcomes and damaging streaks;
equal averages can produce different play. Where resources compound, examine
whether an early advantage removes later decisions or a catch-up rule erases
good play. Change the rule that produces the behavior, then replay the same
scenario. Do not add currency, rewards or dynamic difficulty merely to fill a
design checklist.

## Finish the presentation in context

- Make the player, interactable object and immediate threat/goal identifiable at
  play scale. Decorative detail must not obscure information.
- Use consistent spacing, alignment and text hierarchy across play, pause and
  outcomes. Check real strings, small windows and promised languages. Title and
  settings screens should serve the game rather than add mandatory ceremony.
- Give actions a response on the next presented state. Match anticipation,
  impact and recovery to the action. Distinguish idle and selected states.
- Use music/effects when they improve the requested experience. Check volume,
  overlap, abrupt loops and meaningful visual alternatives for audio cues.
  Follow project-specific audio/asset rules; preserve provenance and licences.
- Choose AA/filtering deliberately: clean edges for smooth geometry and stable
  alignment for pixel art. Inspect motion for shimmer, seams and unreadable FX.
- Introduce demands in a learnable order. Tune the first encounter and at least
  one later/high-pressure case; identical repeated content is not progression.
  Use fixed seeds or authored scenarios to reproduce difficult situations.

## Verify a complete session

Use the same action layer for scripted and real input. For short games, exercise
a whole session; for longer games, a representative route and important
progression/save boundaries.

| Evidence | Establishes | Does not establish |
| --- | --- | --- |
| Rules/transition tests | legal outcomes, reset, scoring, seeded reproduction where required | feel and clarity |
| Scripted rendered run | reachability, visual states, reproducible failures | human input timing/comprehension |
| Inspected screenshots | layout, contrast, missing art/glyphs | motion, frame pacing, audio |
| Real play with audio | responsiveness, difficulty, sound balance and loops | other devices/platforms not exercised |
| Cross-build | compile/link success for those flags | installation, SDK services, runtime behavior |

Exercise new start, normal play, an invalid action, failure/retry and completion
or sustained play. Include focus loss, resize and disconnect where relevant.
For saves, test restart/load and malformed/old data; for generation, test seeds
that stress the rules. Do not require a gamepad for a mouse/touch game or forced
failure for a creative sandbox.

If direct play/audio/device testing is unavailable, use the strongest available
checks, inspect actual renders and state the gap accurately. Do not turn a PNG
or test pass into a claim that the game is fun, balanced or listened to. Fix
material observed problems before delivery. Keep a concise scenario/change/result
record so the artifact and conclusions are reproducible.
