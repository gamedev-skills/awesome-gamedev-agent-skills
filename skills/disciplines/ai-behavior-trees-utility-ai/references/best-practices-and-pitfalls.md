# Best practices & pitfalls — performance, memory, hybrid AI

Depth for `ai-behavior-trees-utility-ai`. How to keep a BT/Utility runtime fast, debuggable, and
maintainable at scale (dozens–hundreds of agents), and how to combine the two models well.

## Memory management

- **Build the tree once, at spawn — never per tick.** Node objects, delegates, and consideration
  lists are created during assembly and reused every tick. A tree rebuilt each frame is both a GC
  storm and a correctness bug (it discards `Running` state).
- **Keep `Tick` allocation-free.** No `new`, no LINQ (`Where`/`Select` allocate iterators), no
  closures capturing locals, no boxing. Pre-allocate scratch buffers; iterate with indexed `for`.
- **Prefer a struct-of-fields blackboard** (or `int`/enum keys) over a `Dictionary<string,object>`
  on hot agents — it removes hashing and value-type boxing. Keep the dictionary form for
  designer-authored or serialized boards.
- **Pool agents and their trees.** Reuse a despawned enemy's tree instance on respawn; call
  `Reset()` instead of reallocating.
- **Share immutable data.** Curves and static config are stateless — one instance serves every
  agent. Only per-agent mutable state (the blackboard, `Running` indices) is unique.

## Performance & profiling

- **Profile before optimizing.** Measure AI time in the engine profiler (Unity Profiler, Godot
  Monitors, Unreal `stat game`). The usual cost is not the tree walk — it is what the *leaves* do
  (raycasts, pathfinding, `FindObjectsByType`). Cache perception; pathfind on a timer, not per tick.
- **Tick on a decision cadence, not per frame.** 5–15 Hz is imperceptible for most NPCs and cuts
  cost 4–10×. Drive the tree from an accumulator (see the guard in `practical-examples.md`).
- **Time-slice across frames.** Don't tick every agent on the same frame. Stagger by bucketing
  agents and ticking one bucket per frame, so the cost spreads instead of spiking.

```csharp
// Round-robin: only ~1/N of agents think each frame; the herd cost is flat, not a spike.
_bucket = (_bucket + 1) % Buckets;
for (int i = _bucket; i < agents.Count; i += Buckets)
    agents[i].Think(dt * Buckets);      // scale dt so per-agent cadence is unchanged
```

- **LOD your AI.** Distant or off-screen agents tick slower (or freeze). Tie the cadence to
  distance-from-camera; a guard 200 m away does not need 10 Hz decisions.
- **Utility cost scales with actions × considerations.** Don't score 40 actions × 8 considerations
  every tick. Prune obviously-irrelevant actions first (a cheap gate consideration that early-outs
  at 0), and re-score only when a relevant fact changed.

## Avoiding deep, brittle trees

- **Keep trees shallow and wide.** Deep nesting is hard to read and forces full re-evaluation.
  Factor repeated subtrees into named builder methods and reuse them.
- **Use conditional aborts / a reactive selector** so a high-priority condition (took damage, lost
  the player) interrupts a lower branch, instead of polling a deep tree for the change.
- **Prefer event-driven perception over polling.** Let sensors push `targetPos` onto the blackboard
  when they fire; the tree reads a cached fact instead of raycasting inside a condition every tick.
- **Cache condition results within a tick** if the same expensive check appears in multiple places.

## Combining Utility AI with behavior trees (hybrid)

The two models answer different questions — use each where it is strong:

| Use a **behavior tree** for… | Use **Utility AI** for… |
|---|---|
| Top-level structure & priorities (patrol / engage / flee) | "How much do I want each option right now?" |
| Ordered, interruptible sequences | Target selection, item/ability choice, needs |
| Clear, debuggable, designer-readable flow | Smooth trade-offs with many inputs |

Recommended default: **BT on the outside, Utility on the inside.** The BT decides *engage vs
disengage vs patrol*; a `UtilitySelectorNode` inside the engage branch decides *which target / which
attack* (see `practical-examples.md` §3). Keep the utility set small and local to the branch so
scoring stays cheap, and give the running action hysteresis so the sub-choice doesn't flicker.

Avoid the inverse (utility choosing between whole behavior trees) unless you truly need graded
top-level behavior — it is harder to debug and easy to make thrash.

## Debugging

- **Draw the decision.** Overlay the active BT path (highlight the running leaf) and, for utility,
  a live bar per action score. Most "bad AI" bugs are visible instantly: a stuck `Running` leaf, an
  un-normalized consideration pinning one action to 1.0, or a mis-shaped curve.
- **Log transitions, not ticks.** Print only when the chosen action or active branch *changes*;
  per-tick logs bury the signal.
- **Make randomness reproducible.** Seed the `System.Random` used by softmax/weighted-random per
  agent so a misbehaving agent can be replayed. Never use a shared global RNG across agents.
- **Assert the `Reset()` contract.** A common bug is a `Running` action (`Wait`, `Repeat`, cover
  reservation) that isn't reset when its branch is abandoned. If timed actions "finish instantly"
  after re-entry, a missing `Reset()` is the cause.

## Pitfall quick-reference

- Rebuilding the tree or allocating in `Tick` → GC spikes and lost `Running` state.
- Ticking every agent every frame → CPU spikes; use cadence + time-slicing + LOD.
- Un-normalized considerations (mixed 0..1 and 0..100) → one factor dominates; weights meaningless.
- No hysteresis → jitter on near-ties in both reactive selectors and utility selection.
- Deep trees with polling conditions → wasted work and laggy reactions; use aborts + events.
- Expensive work inside conditions (raycasts, pathfinding) → cache it on the blackboard instead.
