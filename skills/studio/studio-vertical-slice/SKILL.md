---
name: studio-vertical-slice
description: Plan and evaluate a bounded playable vertical slice demonstrating a complete game loop at representative final quality with evidence-based go/no-go criteria.
---

# Studio Vertical Slice

Unlike `prototype-fast` (rapid greybox), this skill proves **production feasibility and quality** in a complete representative loop.

## Procedure

1. Define one concrete question: does the planned game deliver its core fantasy at the target quality and within feasible production cost?
2. Bound to a small playable start → challenge → resolution loop; prefer approximately 3–5 minutes when appropriate, with no content inflation.
3. Identify the minimum representative player/enemy/art/animation/UI/audio/save/performance systems needed. Explicitly reject unrelated content.
4. Establish a quality bar based on actual native-scale references, interaction latency, enemy readability, asset consistency and stability.
5. Define tasks, dependencies, scope cuts, test commands, owner and completion criteria. Keep a resumable checkpoint in a project-owned tracking document.
6. Build using the appropriate engine and discipline skills; preserve working behavior after each milestone.
7. Run representative playtests, inspect gameplay captures, and record evidence: time to first meaningful action, completion, confusion, combat clarity, FPS, crash rate and asset rework.
8. Conclude PROCEED / PIVOT / STOP with concrete observations, residual risks and next experiment.

## Output

Validation question; slice boundaries; build checklist; representative asset rules; game-loop scenario; measurable acceptance gates; checkpoint; observations; verdict; next owner.

## Composition

Pair with `prototype-fast` only for the early greybox; use `studio-qa-plan` for coverage, `game-feel` for polish, and engine skills for code. Do not claim a slice is validated without a runnable build/playtest.
