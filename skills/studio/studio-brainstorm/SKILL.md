---
name: studio-brainstorm
description: Explore and compare game concepts, gameplay loops, player fantasy, constraints, and scope tiers before committing to production.
---

# Studio Brainstorm

Use for exploratory creative decisions **before** implementation. Avoid treating a brainstorm as an instruction to change production code.

## Workflow

1. Inspect current game identity, target audience, existing design decisions, technology constraints, recent playtest evidence and budget.
2. Define the player's core fantasy, primary verbs, emotional pacing, opposition, progression, and what makes the game distinct.
3. Generate 3 genuinely different options when choices are open. Include a conservative option that preserves existing systems.
4. For each option evaluate implementation burden, art/animation requirements, balance implications, player readability, technical risks, and testable novelty.
5. Rank against the user's stated priorities; explicitly distinguish evidence, assumptions and taste.
6. Select one direction only when requested or delegated, and define a one-sprint experimental proof with a reversible exit.
7. Record decided/rejected/deferred ideas in `design/` or the project's existing design log, without overwriting canonical decisions.

## Deliverable

Core fantasy, gameplay loop, pillars, option comparison, scope tiers (minimum/target/stretch), risks, experiment and success metrics, open decisions.

## Boundaries

Route code to engine/discipline skills, system rules to `studio-system-design`, and polished vertical-slice validation to `studio-vertical-slice`. Creativity is additive; preserve the project's actual engine and architecture unless migration is explicitly requested.
