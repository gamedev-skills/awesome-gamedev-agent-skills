# Observe interactions, not just screenshots

Use when automating play, reproducing a bug or checking an important multi-step
feature. The idea is a short sequence of actions, controlled advancement,
observation and a focused change, adapted from
[develop-web-game](https://github.com/openai/skills/blob/30444aed500c00c85294d12074f6e3ee794f808a/skills/.curated/develop-web-game/SKILL.md).
Its JavaScript hooks and Playwright client are not Ebitengine APIs.

## Define a scenario with intermediate outcomes

Start from a known state/seed. Use the game's action dispatcher, with explicit
press/hold/release and tick counts. Observe intermediate states before issuing
the next action, so a successful final score does not hide a broken transition.

| Example chain | Observe along the way |
| --- | --- |
| Collect key → open door → reach exit | inventory changes once, locked/unlocked feedback agrees, next level starts with intended state |
| Hit → damage → defeat → reward | one contact event, correct health, target stops acting, one reward |
| Pause → settings → back → resume | underlying play frozen as intended, controls owned by active UI, focus restored, no leaked confirm/action |
| Invalid puzzle move → undo/reset → solve → replay | refusal explained, state/history restored, completion reachable, replay has no stale result |

Choose chains relevant to the requested change. Reset between independent
scenarios: world, RNG, timers, buffered input, pending scene transitions and
cosmetic events may all matter. Reuse the same scenario after the fix; add a
different boundary case only when it addresses an unresolved concern.

## Pair rendered evidence with actual state

For a scripted failure, a compact read-only diagnostic snapshot can include:
game/content version, seed, tick, scene/mode, logical coordinate origin and units,
camera/viewport, relevant positions, resources, timers, active UI/focus and the
last action/event. Derive it from real state; do not build a second simulation
or print expected answers. Keep it local/debug-only, concise, and free of
credentials or other players' secret state.

Capture the state and image for the **same tick/scene**. On a catch-up frame,
logging in every `Update` and later capturing in `Draw` can pair different
moments. Label the drawn capture with its state tick; report if the requested
tick was not drawn. Compare both: a JSON health value can be correct while the
visible meter is stale, and a correct-looking frame can hide a rule failure.

The starter supplies `-demo` and `-shot`; it does **not** supply a state-JSON or
general input-script flag. Add a small project-specific diagnostic when needed,
or use the pinned engine's opt-in VM tooling described in
the architecture-and-testing reference. A scripted action dispatch
tests rules/flow; actual device or VM input also tests the device-to-action path.
Run graphics checks under Xvfb on Linux, not the user's desktop.

## Control time without changing the game being checked

Advance the real fixed-step simulation rather than sleeping for an estimated
number of updates. Keep test stepping separate from the normal scheduling loop
so both cannot advance the same state. A capture-only `SyncWithFPS` mode may
accelerate tick-based rules, but does not measure interactive frame pacing,
audio synchronization or wall-clock services. Never transplant a browser
`advanceTime` hook by calling `Game.Update` concurrently with `RunGame`.

Inspect runtime errors as well as images/state. Fix the first new causal failure
before collecting downstream symptoms. Record the initial state, action/tick
sequence, changed behavior and inspected artifacts. Test only the affected
paths plus relevant regression boundaries; do not rebuild every platform after
each text or color adjustment without a reason.
