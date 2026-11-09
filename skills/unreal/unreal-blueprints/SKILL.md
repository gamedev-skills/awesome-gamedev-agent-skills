---
name: unreal-blueprints
description: >
  Build Unreal Engine 5 gameplay with Blueprint visual scripting: Blueprint Classes, the
  Event Graph and Construction Script, variables/functions/macros, and Blueprint
  communication (Cast, Interfaces, Event Dispatchers). Use when working in Blueprints, wiring
  an event graph, deciding how Blueprints talk to each other, or when the user mentions
  Blueprint, BP, event graph, construction script, or a Blueprint .uasset.
---

# Unreal Blueprints (Visual Scripting)

Structure gameplay logic in Unreal Engine 5 Blueprints: pick the right graph, expose data
cleanly, and choose a communication method that doesn't create hard-reference spaghetti.
Targets **UE 5.8**. (Blueprints are node graphs; the snippets below describe node flows.)

## When to use

- Use when authoring a Blueprint Class, wiring the Event Graph (BeginPlay/Tick/overlap),
  using the Construction Script, creating variables/functions/macros, or choosing how two
  Blueprints communicate (Cast, Interface, or Event Dispatcher).
- Use when the project has `*.uproject` and Blueprint `*.uasset` files, and the user works
  visually rather than in C++.

**When *not* to use:** performance-critical systems, large data structures, or anything that
benefits from source control diffs and unit tests → `unreal-cpp-gameplay`. Player input
mapping → `unreal-enhanced-input`. AI logic → `unreal-behavior-trees`.

## Core workflow

1. **Choose the Blueprint type.** A **Blueprint Class** (derived from Actor/Pawn/Character/
   ActorComponent) defines a reusable object. The **Level Blueprint** is a per-level graph for
   level-specific scripting only — don't put reusable logic there.
2. **Use the Construction Script for instance setup** (procedural placement, configuring
   components from variables). It can rerun when actors are placed/edited and also runs for
   dynamically spawned Blueprint instances during play. Placed actors can use their cooked
   construction results on load. Keep construction repeatable; use `BeginPlay` for gameplay init.
3. **Use the Event Graph for runtime logic.** `Event BeginPlay` for init, input/overlap events
   for reactions. Avoid `Event Tick` unless you truly need per-frame work.
4. **Expose data with variables**; click the eye icon to make a variable Instance Editable, and
   group related ones with categories. Mark **pure** functions (no exec pin) for getters.
5. **Pick a communication method by coupling** (see Patterns): direct **Cast** for things you
   own, **Blueprint Interface** to call across types without hard references, **Event
   Dispatcher** to broadcast one-to-many.
6. **Verify** with the Blueprint debugger: drop breakpoints on nodes, watch variable values,
   and use Print String to confirm execution paths during Play In Editor (PIE).

## Patterns

### 1. Reactive Event Graph (no Tick)

```text
Event BeginPlay
  -> Set 'StartLocation' = GetActorLocation
  -> Bind Event to OnComponentBeginOverlap (TriggerVolume) [calls custom event OnEnterZone]

OnEnterZone (Other Actor)
  -> Branch: Other Actor == Player?
       True  -> Open Door (Timeline drives the rotation)   // event-driven, runs once
```

Prefer events (overlaps, timers, dispatchers) and Timelines over polling in Tick.

### 2. Direct reference + Cast (tight coupling, use sparingly)

```text
Overlapped Actor (Actor ref)
  -> Cast To BP_Player
       Cast Failed -> (do nothing)
       Success     -> call BP_Player.ApplyDamage(10)
```

`Cast To` creates a hard reference to that class (it loads with this Blueprint). Fine when the
caller genuinely depends on that type; otherwise prefer an Interface.

### 3. Blueprint Interface (decoupled call)

```text
// 1. Create BPI_Interactable with function 'Interact(Instigator)'.
// 2. Add the interface to BP_Door, BP_Chest, BP_Lever and implement 'Interact' in each.
// 3. Caller, with any Actor ref:
Player presses Use
  -> Does Object Implement Interface (BPI_Interactable)?  // safe check, no Cast/hard ref
       True -> Interact (Message) on Target Actor
```

### 4. Event Dispatcher (one-to-many broadcast)

```text
// In BP_Player: declare Event Dispatcher 'OnHealthChanged (float NewHealth)'.
TakeDamage -> Set Health -> Call 'OnHealthChanged' (Health)   // broadcast

// In WBP_HUD BeginPlay: Bind Event to 'OnHealthChanged' -> update health bar.
// Many listeners can bind; the player never references them.
```

## Pitfalls

- **Cast spaghetti / long load times** — chains of `Cast To` create hard references that pull
  whole asset trees into memory. Decouple with Interfaces or Dispatchers.
- **Logic in the Level Blueprint that should be reusable** — it can't be reused across levels.
  Put it in a Blueprint Class.
- **`Event Tick` overuse** — every-frame nodes add up fast. Use events, Timers
  (`Set Timer by Event`), and Timelines instead.
- **Construction Script doing gameplay** — it runs in the editor on edit/placement; spawning
  gameplay actors or starting logic there causes editor-only artifacts. Init in BeginPlay.
- **Variable not visible on the instance** — toggle Instance Editable (the eye); to edit before
  spawn via Spawn node, also mark "Expose on Spawn".
- **Interface call did nothing** — the target doesn't implement the interface; use "Does
  Implement Interface" before calling, or use the Message version which is safe on non-implementers.
- **Local variable picks up an unexpected default value** — it shares its name with a member
  variable, and one can inherit the other's default. UE 5.8 refuses such names for new local
  variables, but older Blueprints keep existing collisions; rename one of the two by hand.

## References

- For a decision guide on **Cast vs Interface vs Event Dispatcher** and step-by-step dispatcher
  binding, read `references/communication.md`.
- Primary docs: "Blueprints Visual Scripting"
  (`https://dev.epicgames.com/documentation/en-us/unreal-engine/overview-of-blueprints-visual-scripting-in-unreal-engine`).

## Related skills

- `unreal-cpp-gameplay` — when to drop to C++; how BP and C++ classes interoperate.
- `unreal-enhanced-input` — the modern way to feed input events into these graphs.
- `unreal-behavior-trees` — AI decision logic that Blueprints trigger.
