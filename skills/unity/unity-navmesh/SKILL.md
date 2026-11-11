---
name: unity-navmesh
description: >
  Unity 6.3 LTS pathfinding with the AI Navigation package: NavMeshSurface baking, NavMeshAgent,
  NavMeshLink jumps and runtime rebakes. Use when a Unity enemy should chase or patrol, an agent
  will not move or warps, a path is partial, or the Bake tab is missing. Not for deciding when
  NPCs move (`game-ai`, `ai-behavior-trees-utility-ai`) or force-driven movement
  (`unity-physics`).
---

# Unity NavMesh (AI Navigation)

Give NPCs pathfinding in Unity 6.3 LTS (6000.3) with the AI Navigation package 2.0: bake
walkable surfaces, move agents around obstacles, and prove the mesh and paths exist by reading
them back.

> **Version trap:** the old built-in Navigation window (Object and Bake tabs, the "Navigation
> Static" flag) is gone. Baking is component-based: a `NavMeshSurface`
> (`Unity.AI.Navigation`, package `com.unity.ai.navigation`) holds the bake settings and the
> baked data. The package's **Window > AI > Navigation** only edits agent types and areas.
> The runtime API (`NavMeshAgent`, `NavMesh`, `NavMeshObstacle`) stays in `UnityEngine.AI`.

## When to use

- An agent needs to walk, chase or patrol to a target; a level needs a baked surface;
  doors or crates should block paths at runtime; you need to know whether a target is
  reachable.
- The project has `com.unity.ai.navigation`, a `NavMeshSurface`, or scripts using
  `UnityEngine.AI`.

**When not to use:** the decision of when and where to move → `game-ai` or
`ai-behavior-trees-utility-ai`; force-driven or kinematic movement that is not pathfinding →
`unity-physics`. If Unity's official `initialize-ai-navigation` skill is installed and an
Editor is connected, it can add and bake the components for you; this skill still owns the
agent code and the checks.

## Workflow

1. **Gate on the package.** Look for `com.unity.ai.navigation` in
   `Packages/packages-lock.json`, not only `manifest.json`: a package the Editor has not
   resolved yet produces the same "type not found" errors as one that was never added. If it
   is missing, ask before adding it to `manifest.json`.
2. **Take inventory before adding anything.** Grep the scenes for `NavMeshSurface`,
   `NavMeshAgent`, `NavMeshObstacle`, `NavMeshLink` and the deprecated `OffMeshLink`. Agent
   types (radius, height, step, slope) and area names live in
   `ProjectSettings/NavMeshAreas.asset` (`m_Settings`, `areas`).
3. **Bake the surface.** Pick one path:
   - Unity CLI with a ready Editor: `unity command navmesh bake_surfaces` (the plain
     `navmesh bake` command is the old built-in bake, not `NavMeshSurface`).
   - Procedural or streamed levels: call `surface.BuildNavMesh()` after the geometry exists
     (pattern 3). Nothing is saved to disk.
   - Otherwise ask the user to select the GameObject with the `NavMeshSurface` and press
     **Bake**, then confirm from the file (step 6).
   Re-bake whenever geometry, `NavMeshModifier`s or agent settings change.
4. **Add a `NavMeshAgent`** whose agent type matches the baked one, spawned on the mesh.
   Drive it with `SetDestination`; detect arrival with `pathPending` and `remainingDistance`.
5. **Block paths at runtime** with `NavMeshObstacle` and `carving = true` instead of a rebake.
   Bridge separate islands (ledges, gaps) with a `NavMeshLink`.
6. **Verify** with the checks below.

## Patterns

### 1. Chase with a re-path timer

```csharp
using UnityEngine;
using UnityEngine.AI;

[RequireComponent(typeof(NavMeshAgent))]
public class Chaser : MonoBehaviour
{
    [SerializeField] private Transform target;
    [SerializeField] private float repathInterval = 0.2f;
    private NavMeshAgent _agent;
    private float _nextRepath;

    private void Awake() => _agent = GetComponent<NavMeshAgent>();

    private void Update()
    {
        if (!target || Time.time < _nextRepath) return;
        _nextRepath = Time.time + repathInterval;
        _agent.SetDestination(target.position);
    }

    // pathPending guards the frames before the first path exists.
    public bool HasArrived() =>
        !_agent.pathPending && _agent.remainingDistance <= _agent.stoppingDistance;
}
```

### 2. Check reachability before committing

```csharp
public static bool CanReach(NavMeshAgent agent, Vector3 destination)
{
    var path = new NavMeshPath();
    agent.CalculatePath(destination, path);
    return path.status == NavMeshPathStatus.PathComplete;   // Partial means another island
}
```

### 3. Bake at runtime and bridge a gap

```csharp
using Unity.AI.Navigation;
using UnityEngine;

public class LevelNav : MonoBehaviour
{
    [SerializeField] private NavMeshSurface surface;

    // Call after spawning the level geometry.
    public void Rebuild() => surface.BuildNavMesh();

    // One-way drop from a ledge to the floor below.
    public NavMeshLink AddDrop(Vector3 ledge, Vector3 landing)
    {
        var link = gameObject.AddComponent<NavMeshLink>();
        // Points are local to this GameObject; the link ignores its scale.
        Quaternion toLocal = Quaternion.Inverse(transform.rotation);
        link.startPoint = toLocal * (ledge - transform.position);
        link.endPoint = toLocal * (landing - transform.position);
        link.width = 1f;
        link.bidirectional = false;
        return link;
    }
}
```

## Verify

Say which path you used.

- **Unity CLI with a ready Editor:** after the bake, read the mesh and a real path back:

  ```bash
  unity command script eval --code 'var t = UnityEngine.AI.NavMesh.CalculateTriangulation(); return "triangles=" + t.indices.Length / 3;'
  unity command script eval --code 'var p = new UnityEngine.AI.NavMeshPath(); UnityEngine.AI.NavMesh.CalculatePath(GameObject.Find("Enemy").transform.position, GameObject.Find("Player").transform.position, UnityEngine.AI.NavMesh.AllAreas, p); return p.status.ToString();'
  ```

  Zero triangles means nothing is baked or loaded. In Play mode, also read
  `agent.isOnNavMesh` and `agent.pathStatus` for each agent. Find current command names with
  `unity command --query navmesh`.
- **No CLI:** a baked surface stores a reference in the scene file. Grep the `.unity` for the
  surface's `m_NavMeshData:` line; `{fileID: 0}` means it was never baked or was cleared, and a
  `guid:` means baked data exists (check that asset file is present). Then write a PlayMode
  test that loads the scene, calls `NavMesh.CalculatePath` between two known points and
  asserts `PathComplete`; run it as described in `unity-csharp-scripting`.
- **Behavior you cannot assert:** ask the user to press Play and report whether each agent
  reaches the target and roughly how long it takes.

## Gotchas

- **Looking for the Bake tab or Navigation Static.** Removed with AI Navigation 2.0. Bake
  from a `NavMeshSurface`.
- **Agent does not move or warps to the origin.** It is not on the baked mesh, or no surface
  is baked or enabled (only enabled surfaces on active GameObjects load their data). Snap the
  spawn with `NavMesh.SamplePosition` and move it with `agent.Warp`, not the Transform.
- **`PathPartial`.** The target is on another island. Add a `NavMeshLink` or extend the
  geometry so one surface covers both; a partial path only reaches the near edge.
- **Agents ignore new geometry.** The mesh is baked data. Runtime props need a carving
  `NavMeshObstacle` or a `BuildNavMesh()`.
- **An NPC with a Rigidbody jitters or drifts.** The agent and a non-kinematic `Rigidbody`
  both move the Transform. Make the body kinematic while the agent is in control.
- **An agent with a `NavMeshObstacle` on the same GameObject spins or slides.** It avoids
  itself. Enable only one at a time, for example switch the agent off and the obstacle on
  when the NPC stops for good.
- **Agent size does not match the baked agent type.** It gets stuck in gaps or floats. Keep
  the agent's type, radius and height consistent with the surface's agent type.
- **`OffMeshLink` in old scenes.** Deprecated in AI Navigation 2.0 and gone from the Add
  Component menu. Replace it with `NavMeshLink`, which adds Transform endpoints and an
  `activated` flag.
- **`SetDestination` every frame for many agents.** Wasted path queries; re-path on a timer
  (pattern 1) or when the target moved more than a threshold.
- **Agents jitter against each other.** Tune `avoidancePriority` and the obstacle avoidance
  quality, or use an obstacle for blockers that never move.

## References

- AI Navigation manual: https://docs.unity3d.com/Packages/com.unity.ai.navigation@2.0/manual/index.html
  (read the `NavMeshSurface`, `NavMeshLink` and "Use NavMesh Agent with other components"
  pages when changing bake settings or mixing agents with physics).

## Related skills

- `game-ai`: engine-neutral decisions (FSM, steering, perception) that use this movement.
- `unity-csharp-scripting`: the MonoBehaviour around the agent, test assemblies and the
  `.meta` checker.
- `tower-defense`, `fps-shooter`: genres that combine pathfinding with gameplay.

## Version notes

Last verified: 2026-11-11.

- AI Navigation 2.0.16 (released 2026-10-07) is the latest 2.0 package for Unity 6000.0 and
  later, per the Unity package registry (https://packages.unity.com/com.unity.ai.navigation).
  `NavMeshSurface.m_NavMeshData`, `NavMeshLink` properties and `BuildNavMesh` were checked in
  the 2.0.16 package source.
- `OffMeshLink` deprecation: https://docs.unity3d.com/Packages/com.unity.ai.navigation@2.0/manual/whats-new.html
- `navmesh bake_surfaces` is a `com.unity.pipeline` 1.0.0-pre.1 command (pre-release):
  https://docs.unity3d.com/Packages/com.unity.pipeline@1.0/manual/index.html
- Runtime API checked in the Unity C# reference source at tag 6000.3.28f1,
  `Modules/AI/` (`NavMesh.CalculateTriangulation`, `CalculatePath`, `SamplePosition`,
  `NavMeshAgent.isOnNavMesh`).
