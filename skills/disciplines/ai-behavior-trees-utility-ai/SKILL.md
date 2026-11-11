---
name: ai-behavior-trees-utility-ai
description: >
  Engine-neutral behavior tree and utility AI code for NPCs in any language: Blackboard, reactive
  composites, decorators and response-curve scoring. Use when an enemy keeps chasing after losing
  sight, restarts its action every frame or flip-flops between choices. Not for FSMs, steering or
  pathfinding (`game-ai`) or Unreal BT, EQS and StateTree (`unreal-behavior-trees`).
---

# Behavior trees and Utility AI

A behavior tree (BT) gives an agent ordered, interruptible priorities; Utility AI scores every
option and picks the most wanted one. The code is plain C# so it ports to any engine; the
non-obvious part is the lifecycle contract (who resets what, and when), which is where almost
every BT bug lives.

## When to use

- Build or fix a reusable BT runtime: Blackboard, leaves, composites, decorators.
- Build a utility decider: curves, considerations, a selector with hysteresis.
- Combine them: a BT branch that hands a graded choice (which attack, which target) to utility.

**Not this skill:** choosing FSM vs BT, steering, A*, flow fields and perception belong to
`game-ai`. Unreal's `BehaviorTree`/`Blackboard` assets, `BTTask`/`BTService`, EQS and StateTree
belong to `unreal-behavior-trees`. The agent that physically moves (`NavMeshAgent`,
`NavigationAgent3D`) belongs to the engine navigation skill.

## Workflow

1. **Read what exists.** Find the current AI code, its tick site and how it reads the world. If
   the project already ships a BT plugin (Godot LimboAI or Beehave, Unity Behavior, NodeCanvas),
   extend it instead of adding a second runtime.
2. **Pick the default shape: BT outside, utility inside.** The BT decides engage, flee or patrol;
   a utility node inside the engage branch picks how. Use utility at the top only when every
   top-level behavior is a graded trade-off (needs-driven villagers), because it is harder to
   debug and prone to thrashing.
3. **Design the Blackboard first.** Perception writes facts (`targetPos`, `health01`,
   `distToPlayer`); leaves read them. Nodes never hold references to each other.
4. **Choose memory or reactive per composite.** Priority selectors at the top are reactive so
   a higher branch can preempt; a `Sequence` whose first child is a guard condition must be a
   `ReactiveSequence`, or the guard stops being checked once the action runs.
5. **Normalize every utility input to 0..1** through a curve before combining; multiply with
   compensation so a 0 still vetoes.
6. **Tick on a decision cadence** (5-15 Hz for most NPCs) from an accumulator, staggered across
   agents. Movement and animation still run every frame.
7. **Prove it with a headless tick test** (below): script the Blackboard, tick N times and
   assert the status sequence and reset counts. Then draw the running leaf and per-action
   scores on screen while tuning.

## The lifecycle contract

Every node returns `Success`, `Failure` or `Running`. Parents reset a child as soon as it returns
a terminal status and when they abandon it while `Running`; the tree resets a terminal root.
`Reset()` must be idempotent and must clear only execution-local state (timers, reservations),
never persistent state such as a cooldown deadline.

```csharp
// Selector = fallback/OR: return the first child that is not Failure.
// `Current` (from Composite) remembers a Running child so the next tick resumes there.
public sealed class Selector : Composite
{
    public override Status Tick(Blackboard bb, float dt)
    {
        for (; Current < Children.Count; Current++)
        {
            var s = Children[Current].Tick(bb, dt);
            if (s == Status.Running) return Status.Running;            // resume here next tick
            Children[Current].Reset();                                // terminal child can re-enter cleanly
            if (s == Status.Success) { Current = 0; return Status.Success; }
        }
        Current = 0;
        return Status.Failure;                                         // every child failed
    }
}
```

This is the memory variant: it cannot be preempted. `Sequence`, `ReactiveSelector`,
`ReactiveSequence`, `Parallel`, the decorators and `BehaviorTree` follow the same contract in
`references/behavior-tree-core.md`.

## Utility scoring in one snippet

```csharp
// A consideration maps one raw fact to 0..1 through a response curve.
float Score(Blackboard bb)
{
    float distance01 = Curves.InverseLerp01(bb.Get<float>("distToPlayer"), 20f, 2f); // near = 1
    float health01   = Curves.Sigmoid(bb.Get<float>("health01"), k: 8f, mid: 0.4f);  // hurt = low
    // A 0 in any factor still vetoes the action; compensation stops each extra
    // consideration from dragging every score toward 0. No allocation per call.
    return Curves.Compensate(distance01 * health01, count: 2);
}
```

Selection: argmax with an inertia bonus of about 0.05 for the running action is the default;
softmax (temperature about 0.2) when designers want variety without silly picks.

## Headless tick test

Run this shape in the project's test runner (Unity Test Framework, GdUnit4, xUnit) before
tuning by eye; `Assert` stands for the framework's assertion. A probe leaf counts ticks and
resets, so lifecycle bugs show up as numbers.

```csharp
sealed class Probe : Leaf
{
    public int Ticks, Resets; readonly int _after; readonly Status _end;
    public Probe(int after, Status end = Status.Success) { _after = after; _end = end; }
    public override Status Tick(Blackboard bb, float dt) => ++Ticks >= _after ? _end : Status.Running;
    public override void Reset() { Ticks = 0; Resets++; }
}
// Guard lost mid-action: the running action must be aborted, not resumed.
var bb = new Blackboard(); var chase = new Probe(after: 3);
var seq = new ReactiveSequence().Add(new Condition(b => b.Get<bool>("sees"))).Add(chase);
bb.Set("sees", true);  Assert(seq.Tick(bb, 0.1f) == Status.Running);
bb.Set("sees", false); Assert(seq.Tick(bb, 0.1f) == Status.Failure && chase.Ticks == 0);
```

Cover at least: a `Wait` that runs twice in a row takes full time both runs; a lost guard
aborts its action; a cooldown still blocks after its branch is aborted; utility returns `null`
(and the caller copes) when every action scores 0.

## Gotchas

- **Guard not re-checked.** A memory `Sequence` resumes at its running child, so
  `[CanSeePlayer?, Chase]` chases forever after sight is lost. Use `ReactiveSequence`, or make
  the action fail when its Blackboard input disappears.
- **Priority never preempts.** A memory `Selector` at the root keeps resuming a running Patrol
  and never re-asks Attack. Top-level priority selectors are reactive, and they must `Reset()`
  the branch they abandon or its move or animation keeps running.
- **Timed actions finish instantly the second time.** `Wait`/`Repeat` accumulators were not
  cleared because the parent skipped `Reset()` on a terminal child.
- **Cooldown bypass.** A `Cooldown` that clears its ready-time in `Reset()` lets an agent attack
  every time it flickers between branches. Keep the deadline across resets.
- **`Parallel` restarts finished children.** Re-ticking a child that already succeeded restarts
  it, and `RequireAll` then never sees all children succeed on one tick. Store per-child results.
- **Cooldown inside a `Sequence` makes the agent step back to patrol** for a tick each time it is
  blocked. Wrap it in `ForceSuccess` when "wait for the cooldown" should hold the branch.
- **Mixed ranges.** One consideration in 0..100 next to others in 0..1 dominates and makes
  weights meaningless. Clamp every curve output to 0..1.
- **Plain products sink with more considerations.** Five factors of 0.8 give 0.33. Apply the
  compensation factor (`Curves.Compensate`), which keeps an exact 0 as a veto.
- **Inertia revives a vetoed action.** Add the hysteresis bonus only to positive raw scores.
- **Softmax overflows** at small temperatures (`exp(score / 0.01)` is infinity in float). Subtract
  the best score before `exp`.
- **GC spikes.** Build the tree once at spawn; `Tick` allocates nothing (no LINQ, no closures
  capturing locals, no boxing in hot Blackboards). Use a fields class instead of a
  `Dictionary<string, object>` for agents that tick often.
- **Cost lives in the leaves.** Raycasts and path queries inside conditions dominate CPU; let
  perception cache facts on the Blackboard and pathfind on a timer.

## References

- `references/behavior-tree-core.md`: read when writing or reviewing the runtime itself
  (Blackboard, base classes, every composite including the reactive ones, `Parallel`,
  decorators, `BehaviorTree`).
- `references/utility-ai-system.md`: read when building the scorer (curve library,
  compensation, `Consideration`, `UtilityAction`, argmax and softmax selection).
- `references/practical-examples.md`: read when you need a full agent to adapt (guard
  Patrol/Combat BT, needs-driven villager, hybrid `UtilitySelectorNode`).
- `references/best-practices-and-pitfalls.md`: read when scaling to many agents or debugging
  (time-slicing, AI LOD, event-driven aborts, debug overlays, reproducible randomness).

## Related skills

- `game-ai`: decision-model choice, FSMs, steering, pathfinding, perception.
- `unreal-behavior-trees`: Unreal's asset-based BT, Blackboard, EQS and StateTree.
- `unity-navmesh`: the `NavMeshAgent` that carries out "move to" intents.

## Version notes

Last verified: 2026-11-11.

- The C# compiles with no engine types. Example leaves use Unity 6 `Vector2` member names
  (`magnitude`, `normalized`, `sqrMagnitude`); Godot 4 C# uses `Length()`, `Normalized()`,
  `LengthSquared()`; `System.Numerics.Vector2` uses `Length()` and `Vector2.Normalize(v)`.
- The repository test `tests/test_ai_examples.py` compiles the published blocks with the .NET 10
  SDK and runs the lifecycle scenarios.
- BT plugins worth extending instead of replacing (latest releases at check): Unity Behavior
  `com.unity.behavior` 1.0.17, LimboAI 1.8.1 and Beehave 2.9.3 for Godot.
- Sources: compensation factor from Dave Mark and Mike Lewis, "Building a Better Centaur: AI at
  Massive Scale", GDC 2015 AI Summit (https://www.gdcvault.com/play/1021848); Unity package
  registry (https://packages.unity.com/com.unity.behavior); GitHub releases of
  limbonaut/limboai and bitbrain/beehave.
