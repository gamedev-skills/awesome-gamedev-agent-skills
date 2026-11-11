---
name: unreal-behavior-trees
description: >
  Unreal Engine 5 (UE 5.8) NPC AI with Behavior Trees, Blackboards, EQS and StateTree: decorators
  with Observer Aborts, C++ BTTask nodes and running trees from an AIController. Use for UE enemy
  AI, BT_, BB_ or EQS_ assets, "my AI just stands there" or "MoveTo fails". Not for engine-neutral
  BT or utility code (`ai-behavior-trees-utility-ai`) or choosing FSM vs BT (`game-ai`).
---

# Unreal Behavior Trees, EQS and StateTree

Author NPC decision-making in UE5: a Behavior Tree reads a Blackboard, decorators gate
branches, services keep keys fresh, EQS picks locations or targets, and an AIController runs
it all. StateTree is the alternative for mode-based AI. Targets **UE 5.8**.

## When to use

- Creating or fixing `BT_`/`BB_` assets, decorators, services, custom `BTTask`/`BTService`/
  `BTDecorator` C++ nodes, or the AIController that runs the tree.
- Writing or debugging EQS queries (`EQS_` assets, Run EQS Query, the EQS Testing Pawn).
- Building AI with StateTree (`ST_` assets, `UStateTreeAIComponent`) or mixing it with a BT.

**When *not* to use:** writing your own behavior-tree or utility-AI runtime, outside Unreal's
assets → `ai-behavior-trees-utility-ai`. Choosing an AI architecture or engine-neutral
steering and pathfinding → `game-ai`. The pawn and controller classes themselves →
`unreal-cpp-gameplay`.

## Behavior Tree or StateTree?

Both ship in UE 5.8 and Behavior Trees are not deprecated. Default: **keep whatever the
project already uses**. For a new AI, pick StateTree when the behavior is a set of modes with
explicit transitions (patrol, alert, combat), and a Behavior Tree when it is a priority list
that must re-evaluate when Blackboard values change. They also combine: the BT task
`Run State Tree` (`UBTTask_RunStateTree`) runs a StateTree inside a branch, and StateTree has
its own Run Env Query task for EQS. StateTree on an AI needs the **StateTree** and
**GameplayStateTree** plugins and a `UStateTreeAIComponent` on the AIController, with an asset
that uses the StateTree AI Component schema. Ask before adding a second system beside the
first.

## Workflow

1. **Read the project first.** Check `EngineAssociation` in the `.uproject` (this skill targets
   5.8). List existing AI assets and classes so you extend them instead of duplicating:
   `find Content -name "BT_*" -o -name "BB_*" -o -name "EQS_*" -o -name "ST_*"` and
   `grep -rn "AAIController\|RunBehaviorTree\|UStateTreeAIComponent" Source`. C++ AI code needs
   `"AIModule"` in the module's `*.Build.cs`.
2. **Blackboard (`BB_`) first.** One typed key per fact the AI remembers (`TargetActor`,
   `LastKnownLocation`, `bIsInvestigating`). The tree references this asset.
3. **Run it from the controller.** The pawn's AIController calls `RunBehaviorTree(BT)` in
   `OnPossess`; that also initializes the Blackboard. Set the pawn's *Auto Possess AI* to
   "Placed in World or Spawned" and its *AI Controller Class*.
4. **Shape the tree.** Root Selector for priorities (combat, else investigate, else patrol);
   Sequences for steps that must all succeed. Put a Blackboard decorator on each priority
   branch and set **Observer Aborts** so a key change interrupts the running branch.
5. **Keep keys fresh with services** on the branch that needs them (perception, distance
   checks). A service ticks only while its branch is active.
6. **Use EQS for "where" and "which" questions** (cover point, nearest pickup): add a **Run EQS
   Query** task, set its Query Template and the Blackboard key that receives the best item, and
   pass parameters through Query Config.
7. **Write custom nodes in C++ only when the built-ins can't do it**; read the reference below.
8. **Check it (see Verify).**

## Patterns

### AIController that runs the tree (C++)

```cpp
void AEnemyAIController::OnPossess(APawn* InPawn)
{
    Super::OnPossess(InPawn);
    if (BehaviorTree)                  // UPROPERTY(EditAnywhere) TObjectPtr<UBehaviorTree>
    {
        RunBehaviorTree(BehaviorTree); // also initializes the Blackboard the BT references
    }
}

void AEnemyAIController::SetTarget(AActor* Target)
{
    if (UBlackboardComponent* BB = GetBlackboardComponent())
    {
        BB->SetValueAsObject(TEXT("TargetActor"), Target); // must match the BB key name
    }
}
// BB->ClearValue(TEXT("TargetActor")) drops the tree back to a lower-priority branch.
```

### A reactive priority tree

```text
ROOT
└── Selector
    ├── Sequence   [Blackboard: TargetActor Is Set, Observer Aborts: Both]
    │     ├── MoveTo (TargetActor)
    │     └── Attack
    ├── Sequence   [Blackboard: LastKnownLocation Is Set, Observer Aborts: Lower Priority]
    │     ├── MoveTo (LastKnownLocation)
    │     └── Wait 3s, then clear the key
    └── Sequence   (patrol)
          ├── Run EQS Query (EQS_NextPatrolPoint -> PatrolLocation)
          └── MoveTo (PatrolLocation)
```

`Both` on the combat branch means: start combat the moment `TargetActor` is set, and leave it
the moment it is cleared.

## Verify

Say which of these you actually ran; reading the assets is not a test.

1. **Compile** the module (Windows: `Engine/Build/BatchFiles/Build.bat <Project>Editor Win64
   Development -Project="<path>.uproject" -WaitMutex`; Linux and macOS use
   `Engine/Build/BatchFiles/Linux/Build.sh` or `Mac/Build.sh` with the matching platform) and
   fix every error and warning in your files.
2. **Validate assets:** `UnrealEditor-Cmd <Project>.uproject -run=DataValidation -unattended`
   runs the project's asset validators; fix every error it reports.
3. **Prove behavior with a functional test.** In a small test map, place the NPC, a target and
   a Functional Test actor whose test waits a few seconds and then checks the Blackboard key or
   the NPC's distance to the target before calling `FinishTest`. Run it headless and read the
   exit status and report:
   `UnrealEditor-Cmd <Project>.uproject -ExecCmds="Automation RunTest Project.Functional Tests;Quit" -unattended -nullrhi -ReportExportPath="<dir>"`.
   Run `-ExecCmds="Automation List;Quit"` first if the test path is unclear. The **Functional
   Testing Editor** plugin must be enabled. If the map won't run without a renderer, swap
   `-nullrhi` for `-RenderOffscreen` (needs a GPU).
4. **When a run in the editor is needed, ask the user** to start PIE, press the apostrophe key
   for the Gameplay Debugger (or open the Behavior Tree editor while PIE runs), and report which
   branch is highlighted and the live Blackboard values. EQS results also show in the Visual
   Logger.
5. **Optional:** if Epic's `unreal-mcp` skill is installed and the editor's MCP server is
   running, you can inspect the BT and StateTree assets live through it. The checks above do
   not need it.

## Gotchas

- **AI never starts:** the pawn isn't possessed by your AIController (Auto Possess AI, AI
  Controller Class), or `RunBehaviorTree` never ran.
- **`MoveTo` fails instantly:** no navmesh (add a Nav Mesh Bounds Volume and rebuild paths), or
  the goal is off the navmesh.
- **The tree ignores a key change:** the decorator's Observer Aborts is `None`. `Self` aborts
  its own branch when the condition fails, `Lower Priority` lets it interrupt branches to its
  right, `Both` does both.
- **A task hangs the tree:** it returned `InProgress` and never called `FinishLatentTask`, or
  its abort path never finishes.
- **Bugs appear only with several NPCs:** a custom task keeps run state in member variables.
  Non-instanced nodes are shared by every AI using the asset; keep per-AI state in node memory.
- **Blackboard key typo:** `SetValueAsObject("Taget", ...)` does nothing, silently. Use a
  `FBlackboardKeySelector` or one shared constant for the key name.
- **Sequence vs Selector swapped:** Sequence stops at the first failure (AND), Selector stops
  at the first success (OR).
- **EQS returns odd results:** only the left-most generator connected to the root runs. Debug
  with an EQS Testing Pawn in the level before blaming the tree.
- **EQS missing on clients:** EQS is server-side AI. In 5.8 a query asset can be stripped from
  client builds (`bStripFromClientBuilds`), so client code must not run it.
- **StateTree edits don't show in PIE:** 5.8 compiles StateTrees through a queue and the editor
  marks out-of-date trees; recompile the asset before testing.

## References

- Read `references/custom-bttask.md` before writing a C++ `UBTTaskNode`: instant and latent
  tasks, per-AI node memory, `AbortTask`, typed Blackboard access, key selectors, and the base
  classes for custom services and decorators.
- Epic docs: [Behavior Trees](https://dev.epicgames.com/documentation/unreal-engine/behavior-trees-in-unreal-engine),
  [EQS user guide](https://dev.epicgames.com/documentation/unreal-engine/environment-query-system-user-guide-in-unreal-engine),
  [StateTree](https://dev.epicgames.com/documentation/unreal-engine/state-tree-in-unreal-engine),
  [Functional Testing](https://dev.epicgames.com/documentation/unreal-engine/functional-testing-in-unreal-engine).

## Related skills

- `ai-behavior-trees-utility-ai`: hand-written BT and utility AI runtimes, any engine.
- `game-ai`: choosing FSM, BT, steering or pathfinding.
- `unreal-cpp-gameplay`: the AIController and pawn classes, module setup.
- `fps-shooter`, `tower-defense`: genres that compose enemy AI.

## Version notes

Last verified: 2026-11-11.

- Current release: UE 5.8 (5.8.4 hotfix, October 2026). UE 5.9 is in Preview (the MegaJam
  Preview, November 2026); do not move a project to it without a copy.
- 5.8: StateTree gained starting states, a compiler manager with queued compilation, and
  out-of-date tracking; `UEnvQuery` gained `bStripFromClientBuilds`.
- 5.9 Preview: StateTrees can be edited from Blueprint or Python scripts; the navmesh can build
  progressively.
- Sources: [UE 5.8 release notes](https://dev.epicgames.com/documentation/unreal-engine/unreal-engine-5-8-release-notes),
  [UE 5.9 Preview release notes](https://dev.epicgames.com/documentation/unreal-engine/unreal-engine-5-9-release-notes),
  [GameplayStateTreeModule API](https://dev.epicgames.com/documentation/unreal-engine/API/Plugins/GameplayStateTreeModule),
  [Run Automation Tests](https://dev.epicgames.com/documentation/unreal-engine/run-automation-tests-in-unreal-engine).
