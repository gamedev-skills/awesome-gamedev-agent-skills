---
name: studio-qa-plan
description: Plan risk-focused quality assurance for game features and pipelines, covering platforms, assets, regression tests and traceable acceptance evidence.
---

# Studio QA Plan

Own structured test coverage and evidence. Load engine testing skills to execute the tests; planning alone is not proof of passing.

## Procedure

1. Read requested behavior, user story, applicable art/architecture contracts, code, active bugs and known platform constraints.
2. Build a risk matrix: player-facing severity × failure probability × detectability; prioritize high-impact/high-change boundaries.
3. Separate deterministic automated checks (schemas, save migration, sprites, frame counts, builds) from manual gameplay checks (readability, feel, timing, comfort, UI).
4. Design a test matrix of feature × state × platform × control scheme × resolution × character gear combination as relevant.
5. Include positive, negative, interrupted, persistence, performance, accessibility, input and visual-regression cases.
6. Provide reproducible test data/seed, environment, expected result, observed result, logs/captures and defect severity.
7. Run available checks only when tools/environment permit; report skipped/blocked tests and confidence honestly.
8. Define release blockers and regression suites, then hand off to implementers with exact reproduction cases.

## Output

Risk register; test cases; environments/fixtures; regression suite; acceptance mapping; evidence log; pass/fail/blocked; actionable next fixes.

## Coverage examples

For modular pixel-art characters, test eight facing directions, idle/movement/attack/death, helmet/weapon/armor combinations, occlusion/y-sort, alt palettes, pivot jitter and equipment clipping against real maps.
