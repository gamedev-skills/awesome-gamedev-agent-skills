# Session 07 — Author: Unity + Unreal Skills

> Public build-log entry. Value-focused only. No growth/marketing/strategy language.

- **Session:** S07
- **Wave:** 3 (authoring; runs in parallel with S06, S08–S11)
- **Date (UTC):** 2026-06-24
- **Depends on:** S05 (frozen standard, catalog, golden skill)
- **Status:** complete
- **Branch / commits:** `session/S07-unity-unreal` → `213ac22` (Unity), `0867674` (Unreal)

## Objective
Author the Unity and Unreal skill sets from the frozen catalog — 8 Unity skills (Unity 6 /
6000.0 LTS) and 6 Unreal skills (UE 5.4+) — each verified against primary documentation, built
to `docs/SKILL-FORMAT.md`, and shaped after the golden `love2d-core` skill.

## What was produced
All 14 catalog skills (none were `golden-done`), each a `SKILL.md` with a routing-rule
description, when-to-use boundary, core workflow, ≥2 version-pinned patterns, pitfalls, and a
References + Related-skills section. Ten carry a `references/` file for progressive disclosure.

**Unity (8) — Unity 6 (6000.0 LTS), `UnityEngine`/`UnityEditor`:**
- `unity-csharp-scripting` — MonoBehaviour lifecycle, component access, serialization,
  coroutines (+ `references/lifecycle-and-coroutines.md`).
- `unity-input-system` — Input System package 1.x: actions, maps, `PlayerInput`, reading values
  (+ `references/rebinding.md`).
- `unity-physics` — Rigidbody/forces, collisions vs triggers, layers, raycasts
  (+ `references/raycasting-and-joints.md`).
- `unity-animation` — Animator/Mecanim parameters, blend trees, layers, IK
  (+ `references/blend-trees-and-ik.md`).
- `unity-scriptableobjects` — data assets, shared variables, event channels
  (+ `references/event-channels.md`).
- `unity-tilemap-2d` — Grid/Tilemap, colliders, Rule Tiles, runtime painting.
- `unity-navmesh` — AI Navigation package baking + `NavMeshAgent` runtime.
- `unity-build-pipeline` — build settings, scripting backend, stripping, scripted builds
  (+ `references/ci-build-script.md`).

**Unreal (6) — UE 5.4+:**
- `unreal-blueprints` — Blueprint Classes, graphs, and communication
  (+ `references/communication.md`).
- `unreal-cpp-gameplay` — reflection macros + Gameplay Framework
  (+ `references/components-and-gc.md`).
- `unreal-enhanced-input` — Input Actions/Mapping Contexts, binding by `ETriggerEvent`
  (+ `references/cpp-setup.md`).
- `unreal-behavior-trees` — Behavior Tree + Blackboard AI
  (+ `references/custom-bttask.md`).
- `unreal-niagara` — VFX systems/emitters and runtime control.
- `unreal-packaging` — cooking, build configurations, and packaging.
- This progress entry.

## Key decisions
- **Catalog names are authoritative.** The session brief listed a "typical set" of placeholder
  names (e.g. `unity-core`, `unreal-cpp`); the frozen catalog's exact names were used instead,
  since the catalog is the single source of truth (and the router routes from it).
- **Verify, then pin.** Every load-bearing API was checked against primary docs before writing;
  patterns state the target version and call out the major-version traps that break copied code
  (below). No APIs were invented.
- **Progressive disclosure where depth earns it.** Ten skills push deep material (full lifecycle
  tables, interactive rebinding, IK, SO event channels, CI build scripts, C++ setups, custom
  BTTask) into a one-level-deep `references/` file so each `SKILL.md` stays lean (≤151 lines).
- **Discipline/engine split honored.** Engine skills teach the engine API and defer the portable
  concept to the discipline sibling: `unity-navmesh`/`unreal-behavior-trees` → `game-ai`,
  `unity-input-system`/`unreal-enhanced-input` → `input-systems`, `unity-tilemap-2d` →
  `level-design`, `unity-physics` → `physics-tuning`.
- **Blueprint skill represents node graphs as text.** Since Blueprints are visual, recipes are
  written as annotated node-flow blocks rather than fictional code.

## Verification
- **Validator:** `python scripts/validate-skills.py` → "Validated 31 skill file(s). All checks
  passed." (exit 0), covering all 14 skills authored here.
- **Sizes/format:** every `SKILL.md` is well under the 500-line limit (Unity 125–151; Unreal
  113–150); all `references/` links resolve; folder names equal `name`; no forbidden frontmatter
  keys. Skills authored: 14; all meet the rubric in `docs/SKILL-FORMAT.md`: yes.
- **Version traps confirmed against primary docs and documented in-skill:**
  - Unity `Rigidbody.velocity` → **`linearVelocity`** (Unity 6 rename).
  - Unity high-level NavMesh baking moved from the legacy Navigation window to the **AI
    Navigation package** (`com.unity.ai.navigation` 2.x) via the `NavMeshSurface` component;
    `NavMeshAgent` stays in built-in `UnityEngine.AI`.
  - Unity `RuleTile`/`AnimatedTile` live in the **2D Tilemap Extras** package
    (`com.unity.2d.tilemap.extras`), not the built-in Tilemap.
  - UE5 **Enhanced Input** is the default (legacy axis/action mappings deprecated); Blueprint
    **nativization was removed** in UE5; Niagara supersedes Cascade.

## Sources consulted (primary docs)
- Unity Manual — Event execution order (`/Manual/execution-order.html`), Input System
  (`/Manual/com.unity.inputsystem.html`), Tilemap reference, Animation state machines; Scripting
  API — `MonoBehaviour`, `Rigidbody`, `Tilemaps.Tilemap`, `AI.NavMeshAgent`,
  `BuildPipeline.BuildPlayer`, `CreateAssetMenuAttribute`.
- Unity AI Navigation package manual (`com.unity.ai.navigation@2.0`) and 2D Tilemap Extras
  package manual (`com.unity.2d.tilemap.extras`).
- Unreal docs — Blueprints Visual Scripting overview, Gameplay Framework, C++ Quick Start,
  Enhanced Input, Behavior Trees, Overview of Niagara Effects, Packaging Your Project.

## Handoff to next sessions
- **S12 (router):** the 14 Unity/Unreal names match the catalog exactly and can be routed.
  Detection signals used in descriptions: Unity `*.cs`+`ProjectSettings/`, `*.inputactions`,
  `*.unity`/`*.prefab`, `*.controller`, `*.asset`, `Tilemap`, `NavMeshSurface`; Unreal
  `*.uproject`, `Source/**/*.cpp` with `UCLASS`, `*.Build.cs`, `IA_/IMC_`, `BT_/BB_`, `NS_/NE_`.
- **S13 (QA):** two non-blocking catalog source-URL drifts found and worked around (see below);
  flagging for the QA pass to reconcile in the catalog if desired.
- Cross-references to disciplines/genres (`game-ai`, `input-systems`, `level-design`,
  `physics-tuning`, `fps-shooter`, `tower-defense`, `card-game`, `rpg`, `survival-crafting`) are
  in place for the router to compose.

## Notes for QA (catalog source-URL drift; catalog left unedited per scope)
- The catalog's Unity navigation source `/Manual/nav-NavigationSystem.html` now **404s** in the
  Unity 6 docs (navigation restructured). Current authority used instead: the AI Navigation
  package manual (`com.unity.ai.navigation@2.0`) plus `ScriptReference/AI.NavMeshAgent`.
- The Unreal packaging page resolves at `/packaging-your-project` (the catalog slug is correct);
  the Epic docs currently render under the 5.8 path while the APIs cited are stable for 5.4+.

## If partial — remaining work
- None. All 14 catalog skills are authored, validated, and committed on
  `session/S07-unity-unreal`.
