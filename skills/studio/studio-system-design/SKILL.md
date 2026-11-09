---
name: studio-system-design
description: Write or review a gameplay system design document covering rules, state, data, balancing levers, edge cases, and executable acceptance tests.
---

# Studio System Design

Own a **gameplay system contract** (inventory, loot, combat, skills, AI progression, economy), not the underlying engine API.

## Procedure

1. Read current design docs and implementation; identify authoritative rules and dependencies.
2. Define player-facing problem, goals, exclusions, interactions and success criteria.
3. Model the core loop and state transitions, timing, resources, failure cases and save/load boundaries.
4. Specify data schemas and ownership without coupling a portable concept to one engine prematurely.
5. Include concrete values and formulas only when sourced or clearly marked proposed; list tunable balance levers.
6. Address edge cases: interruption, death, inventory full, reload, multiplayer or offline behavior if relevant, conflicting status effects and invalid inputs.
7. Define telemetry or playtest observations that would disprove the design.
8. Write acceptance tests that can be translated into engine tests and gameplay scenarios; include rollback/migration for existing saves if relevant.

## Output

Objective and player experience; rules and invariants; entities/data; state transitions; integration surfaces; failure states; balance parameters; acceptance tests; alternatives and risks; handoff to the relevant genre/engine skills.

## Review gates

Rules are deterministic enough for implementation; ownership boundaries are explicit; no invented API or implicit save format change; unclear issues are listed rather than silently decided.
