---
name: game-ai
description: >
  Designs engine-neutral enemy and NPC AI: picks FSM, behavior tree, utility or GOAP, and builds
  perception, steering and A* pathfinding. Use for patrol and chase, "find a path to the player",
  agents stuck on corners or AI that sees through walls. Not for BT or utility code
  (`ai-behavior-trees-utility-ai`), Unreal AI (`unreal-behavior-trees`) or Unity NavMesh
  (`unity-navmesh`).
---

# Game AI architecture

Split every agent into layers that pass one small value to the next: **perceive** (facts on a
Blackboard) → **decide** (an intent such as "go to X", "attack Y") → **path** (waypoints) →
**steer** (a velocity) → **animate**. Most "dumb AI" bugs are a layer doing another layer's job:
a state that raycasts, a pathfinder called every frame, steering that ignores the path.

## When to use

- Choose a decision model, or fix one that has grown into flag soup.
- Build or debug an FSM, perception, steering, A* on a grid or graph, or a flow field.
- Diagnose agents that get stuck, oscillate, react unfairly fast or see through walls.

**Not this skill:** BT and utility runtimes go to `ai-behavior-trees-utility-ai`; Unreal
`BehaviorTree`, EQS and StateTree go to `unreal-behavior-trees`; Unity `NavMeshSurface` and
`NavMeshAgent` go to `unity-navmesh`. Movement and collision feel go to `physics-tuning`.

## Pick the decision model

| Situation | Default |
|---|---|
| 2-6 states, transitions obvious (door, turret, simple guard) | FSM |
| Several states share exits (stunned, dead, alerted from anywhere) | Hierarchical FSM: a parent state owns the shared exits |
| Many prioritized, interruptible behaviors, reused across enemy types | Behavior tree, built with `ai-behavior-trees-utility-ai` |
| Graded trade-offs (which target, heal or attack, needs) | Utility scoring, same skill; usually inside a BT branch |
| Multi-step plans with preconditions the designers want to emerge | GOAP; only if a BT cannot express it, because plans are hard to debug |

Common shipping mix: an FSM for the top mode (Idle, Combat, Dead) with a BT inside Combat.
Start with the FSM; promote a state to a BT when its transitions stop fitting on one screen.

## Workflow

1. **Read the project first.** Engine, existing AI code, navigation (navmesh, `AStarGrid2D`,
   a tile grid), and how enemies find the player today. Extend what exists.
2. **Write perception once.** One sensor per agent writes `target`, `last_known_pos`,
   `can_see`, `heard_at` to a Blackboard on a timer (5-10 Hz). Decisions read those facts; they
   never raycast.
3. **Pick the model** from the table and keep transitions inside states (or a table), not in
   scattered `if state == ...` checks.
4. **Path on the coarsest graph that works** (waypoints or a nav grid beats a dense pixel grid),
   cache the path, and follow the next waypoint with steering.
5. **Add stuck and fairness guards** (see Gotchas) before tuning numbers.
6. **Verify with runnable checks**, not just by watching:
   - A* admissibility: on 50 random grids, the path cost from A* equals Dijkstra's (`h = 0`)
     cost. Any mismatch means the heuristic or step costs are wrong.
   - State flicker: log transitions with timestamps during a scripted run; more than about 2
     transitions per second for one agent means missing hysteresis.
   - Stuck: run agents through the level headless and fail if any makes less than 0.5 units of
     progress toward its waypoint in 2 s.
   Then watch it with the path, current state and sight cone drawn on screen.

## Gotchas

**FSM**
- **The initial state's `enter()` never runs** when the agent assigns `current = Patrol.new()`
  without calling it. Route the first state through the same `change_state()` as every other.
- **Changing state from inside `enter()`/`exit()`** re-enters the machine and runs exits twice.
  Queue the next state and apply it after `update()` returns.
- **Threshold flicker.** Chase at 10 m and give up at 10 m, and the agent toggles every frame
  at the boundary. Use separate enter and exit thresholds (chase at 10, give up at 14) and a
  minimum time in state of about 0.3-0.5 s.

**Perception**
- **Check cheap to expensive:** squared distance, then the view cone (`dot(forward, dir) >
  cos(half_angle)`), then one raycast. Only survivors pay for the ray; stagger rays across frames.
- **One ray to the target's origin** fails behind low cover (origin at the feet) or passes through
  a gap at the waist. Cast to two or three points (head, chest) and accept any hit.
- **Omniscient AI feels like cheating.** Chase the last-known position, then search, instead of
  reading the player's live position after sight is lost. Delay the first reaction by roughly
  0.2-0.5 s, or fill an awareness meter faster at close range, so players can react.

**Steering**
- **Weighted sums cancel.** Seek plus avoid pointing opposite ways sums to zero and the agent
  freezes at the wall. Use priority truncation: apply avoidance first and spend the remaining
  force budget on lower behaviors.
- **Waypoint radius smaller than one tick of travel** (`speed * dt`) makes agents overshoot and
  orbit the point. Advance when within `max(radius, speed * dt)`.
- **Separation over every pair** is O(n²); bucket agents in a spatial hash with cells about the
  neighbor radius.
- **Steering and an engine nav agent both moving the body** jitter. Let the agent compute the
  path and feed its desired velocity into your steering (Godot: `NavigationAgent2D/3D`
  `velocity` and `velocity_computed` when avoidance is on; Unity: see `unity-navmesh`).

**Pathfinding**
- **Inadmissible heuristic** returns fast but longer paths: octile assumes diagonal steps cost
  √2; if diagonals cost 1 use Chebyshev; terrain weights below 1 break every grid heuristic.
- **Diagonal corner cutting** through wall corners: only allow a diagonal when both orthogonal
  neighbors are open. Godot `AStarGrid2D` defaults to `DIAGONAL_MODE_ALWAYS`, which cuts
  corners; set `DIAGONAL_MODE_ONLY_IF_NO_OBSTACLES` (or `NEVER` for 4-way with Manhattan).
- **Godot `AStarGrid2D.update()` clears every solid point and weight.** Call it after setting
  `region`/`cell_size`/`offset`, then mark walls. `jumping_enabled` ignores weight scales.
- **Unreachable goal floods the whole map.** Label connected regions with a flood fill once and
  reject cross-region requests, or cap node expansions per search.
- **Repathing every frame.** Repath when the target moves more than a cell (or 1-2 m), or every
  0.25-0.5 s, staggered, with a per-frame budget of searches. Many agents to one goal: one flow
  field (Dijkstra from the goal) instead of A* per agent.
- **Stuck forever.** If progress toward the next waypoint stalls for about 2 s, repath; after two
  failed repaths, change state (give up, teleport off-screen, or pick a new goal).

## References

- `references/pathfinding.md`: read when writing A* or a grid adapter by hand, choosing a
  heuristic, or deciding between hand-rolled A*, `AStarGrid2D` and an engine navmesh.
- `references/fsm-perception-steering.md`: read when implementing a hierarchical FSM, a
  sight/hearing sensor or priority-truncated steering.

## Related skills

- `ai-behavior-trees-utility-ai`: BT and utility runtimes once the model is chosen.
- `unity-navmesh`, `unreal-behavior-trees`: engine navigation and AI assets.
- `physics-tuning`: agent radius, movement and collision response.
- `procedural-gen`: the level graph the AI navigates.

## Version notes

Last verified: 2026-11-11.

- Godot 4.7 `AStarGrid2D`: default `diagonal_mode` is `DIAGONAL_MODE_ALWAYS`, `update()` clears
  point data, and `jumping_enabled` disables weight scaling
  (https://docs.godotengine.org/en/4.7/classes/class_astargrid2d.html).
- Godot 4.7 `NavigationAgent2D`: `avoidance_enabled`, `velocity`, `velocity_computed`
  (https://docs.godotengine.org/en/4.7/classes/class_navigationagent2d.html).
