---
name: unreal-blueprints
description: >
  Unreal Engine 5 (UE 5.8) Blueprint visual scripting: Blueprint Classes vs the Level Blueprint,
  Event Graph, and Cast, Interfaces and Event Dispatchers. Use for BP graphs, how one Blueprint
  calls another, "cast failed", slow Event Tick or Blueprint compile errors. Not for C++
  (`unreal-cpp-gameplay`), input assets (`unreal-enhanced-input`) or AI trees
  (`unreal-behavior-trees`).
---

# Unreal Blueprints

Structure UE5 gameplay in Blueprints: put logic in the right graph, expose data cleanly, and
connect Blueprints without a web of hard references. Targets **UE 5.8**.

## When to use

- Authoring a Blueprint Class, wiring the Event Graph, using the Construction Script, adding
  variables, functions, macros or Event Dispatchers.
- Choosing how two Blueprints communicate, or untangling slow loads caused by casts.
- Diagnosing Blueprint compile errors and runtime "Accessed None" errors.

**When *not* to use:** hot loops, large data, or code that needs diffs and unit tests →
`unreal-cpp-gameplay`. Input assets and bindings → `unreal-enhanced-input`. AI decisions →
`unreal-behavior-trees`.

## Workflow

1. **Read the project.** Check `EngineAssociation` in the `.uproject`, and whether a `Source/`
   folder exists (C++ base classes may already provide what the Blueprint needs). Blueprints are
   binary `.uasset` files: you cannot edit or grep them as text. Default: write the change as an
   exact node-by-node recipe the user applies, and verify it with the checks below. Escape
   hatches: Epic's `unreal-mcp` skill can create and edit graphs in a running editor, and UE 5.9
   adds Python and Editor Utility functions that edit Blueprints from scripts.
2. **Pick the container.** Reusable behavior goes in a Blueprint Class (Actor, Pawn, Character
   or Actor Component). The Level Blueprint is only for one-off level scripting, because
   nothing else can reach it.
3. **Construction Script for setup, BeginPlay for gameplay.** The Construction Script reruns
   whenever the actor is placed, moved or edited in the editor, so it must be repeatable and
   must not spawn gameplay actors or start timers.
4. **Prefer events to Tick.** Overlaps, timers (`Set Timer by Event`), Timelines and Event
   Dispatchers instead of polling every frame.
5. **Choose communication by coupling.** Default: an Interface call for "do this to whatever I
   hit" and an Event Dispatcher for "tell anyone who cares". Cast only to a class the caller
   already depends on, because the cast loads that class with the caller.
6. **Expose data deliberately.** Instance Editable for per-instance values, Expose on Spawn for
   values set by `Spawn Actor`, categories for anything designers touch. Getters with no side
   effects can be Pure.
7. **Check it (see Verify).**

## Patterns

### Event-driven door (no Tick)

```text
BeginPlay
  -> Bind Event to OnComponentBeginOverlap (TriggerBox)  [custom event OnEnterZone]

OnEnterZone (Other Actor)
  -> Does Object Implement Interface (BPI_CanOpenDoors)?
       True -> Play Timeline 'DoorOpen' -> Set Relative Rotation (Lerp 0..90 by Alpha)
```

### Interface call (decoupled)

```text
// BPI_Interactable: function Interact(Instigator: Actor)
// BP_Door, BP_Chest: Class Settings -> Implemented Interfaces -> BPI_Interactable
Player Use pressed -> Line Trace -> Hit Actor -> Interact (Message) [Target = Hit Actor]
// The Message node does nothing on actors that don't implement it, so no Cast is needed.
```

### Dispatcher broadcast (one to many)

```text
BP_Player: Event Dispatcher OnHealthChanged(NewHealth: float)
ApplyDamage -> Set Health -> Call OnHealthChanged(Health)
WBP_HUD Construct -> Get Player Pawn -> Cast To BP_Player -> Bind Event to OnHealthChanged
```

## Verify

Say which of these you ran; describing a graph is not a test.

1. **Compile every Blueprint headless:**
   `UnrealEditor-Cmd <Project>.uproject -run=CompileAllBlueprints -unattended -nullrhi`
   (`UnrealEditor-Cmd.exe` on Windows). Read the summary at the end of the log and every
   `Error` or `Warning` line that names your assets; don't rely on the exit code alone.
2. **Validate assets:** `UnrealEditor-Cmd <Project>.uproject -run=DataValidation -unattended`.
3. **Behavior:** if the project has functional tests or automation tests for this feature, run
   `UnrealEditor-Cmd <Project>.uproject -ExecCmds="Automation RunTest <Filter>;Quit" -unattended -nullrhi -ReportExportPath="<dir>"`
   and read the report. Otherwise ask the user to run PIE with a breakpoint (F9) on the node
   in question, and report whether it hit and the values in the Watch window. Print String on
   each branch is the quick fallback.
4. **Optional:** with Epic's `unreal-mcp` connected, compile the edited Blueprint and read its
   messages through the Blueprints toolset.

## Gotchas

- **Slow loads and huge memory from a small Blueprint:** chains of `Cast To` and hard object
  references pull whole asset trees in with it. Use the Reference Viewer (or Size Map) to see
  what loads, then switch to Interfaces, Dispatchers or soft references.
- **"Accessed None" at runtime:** a reference variable was never set, or the actor it pointed
  to was destroyed. Guard with `Is Valid` where the target can legitimately vanish.
- **Variable missing on the placed instance:** Instance Editable is off; for `Spawn Actor`
  pins also tick Expose on Spawn.
- **Construction Script side effects in the editor:** it runs on every edit, so spawned actors
  pile up and timers misbehave. Move gameplay init to BeginPlay.
- **Interface call does nothing:** the target does not implement it, or you called the
  non-Message version on the wrong type.
- **Dispatcher listener fires after it was destroyed or hidden:** unbind on EndPlay or Destruct.
- **Local variable picks up an unrelated default:** it shares a name with a member variable.
  5.8 refuses such names for new locals, but older Blueprints keep the collision until you
  rename one of them.
- **Blueprint Nativization is gone in UE5:** move hot logic to C++ instead.

## References

- Read `references/communication.md` when choosing between Cast, Interface and Event
  Dispatcher, or when wiring and unbinding a dispatcher and handling soft references.
- Epic docs: [Blueprints Visual Scripting](https://dev.epicgames.com/documentation/unreal-engine/overview-of-blueprints-visual-scripting-in-unreal-engine).

## Related skills

- `unreal-cpp-gameplay`: C++ base classes for Blueprints and when to move logic to C++.
- `unreal-enhanced-input`: input events that feed these graphs.
- `unreal-behavior-trees`: AI decisions that Blueprints trigger.

## Version notes

Last verified: 2026-11-11.

- Current release: UE 5.8 (5.8.4 hotfix, October 2026); UE 5.9 is in Preview.
- 5.8: local variables can no longer reuse a member variable's name; existing collisions must
  be renamed by hand.
- 5.9 Preview: new Python and Editor Utility Blueprint functions create and edit Blueprints,
  graphs, nodes and variables from scripts, and the editor MCP gains a Blueprints toolset.
- Sources: [UE 5.8 release notes](https://dev.epicgames.com/documentation/unreal-engine/unreal-engine-5-8-release-notes),
  [UE 5.9 Preview release notes](https://dev.epicgames.com/documentation/unreal-engine/unreal-engine-5-9-release-notes),
  [Epic unreal-mcp plugin](https://github.com/EpicGames/unreal-engine-skills-for-claude-code-plugin).
