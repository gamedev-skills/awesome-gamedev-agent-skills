---
name: studio-architecture
description: Design coherent technical architecture for a game project, including module boundaries, data ownership, engine integration, testing and migration choices.
---

# Studio Game Architecture

Use for multi-system design. For a single significant choice, pair with `studio-architecture-decision`.

## Procedure

1. Inspect repository structure, build pipeline, engine/version, platforms, test setup, and existing diagrams. Name evidence sources.
2. Map game domains: input, movement, simulation, combat, inventory, quests, UI, animation, assets, save/load, content pipeline and platform services as applicable.
3. Diagram ownership, dependencies, synchronous/event boundaries and data lifecycles. Keep scene/prefab/entity coupling intentional.
4. Define contracts between systems, plugin interfaces, test seams, resource ownership, persistence boundaries and thread/async concerns.
5. Compare a minimal change against larger options; account for startup complexity, build size, performance, developer tooling and iteration cost.
6. Define migration steps with versioning, adapter layers, verification and rollback. Preserve the existing engine and public interfaces unless changing them is explicitly in scope.
7. Publish architecture notes under `docs/architecture/` (or established path), with explicit non-goals and prioritized decisions.

## Verification

Record build and test commands actually executed; unresolved risks; proof from a small vertical implementation; known assumptions requiring a spike.

## Output

System context; components; data ownership; engine-specific binding points; critical flows; tradeoffs; migration; tests and acceptance gates; changed files and review risks.
