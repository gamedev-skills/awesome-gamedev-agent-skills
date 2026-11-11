---
name: unity-physics
description: >
  Unity 6.3 LTS physics in 3D and 2D: Rigidbody and Rigidbody2D, forces and linearVelocity, the
  layer collision matrix and raycasts. Use when an object falls through the floor, OnTriggerEnter
  never fires, or a ground ray hits the player. Not for engine-neutral tunnelling tuning
  (`physics-tuning`), tilemap colliders (`unity-tilemap-2d`) or NavMesh (`unity-navmesh`).
---

# Unity Physics (3D PhysX and 2D)

Make objects move, collide and detect each other in Unity 6.3 LTS (6000.3). Unity has two
separate physics engines: 3D (`Rigidbody`, `Collider`, `Physics`) and 2D (`Rigidbody2D`,
`Collider2D`, `Physics2D`). They never interact: a `Rigidbody2D` falls straight through a
`BoxCollider`, and 3D callbacks never fire on 2D objects.

## When to use

- Giving an object physical motion, responding to collisions or triggers, setting up layers,
  ray or shape casts for ground checks and line of sight, joints, kinematic movers.
- The project's scenes or prefabs contain `Rigidbody`/`Collider` or `Rigidbody2D`/`Collider2D`.

**When not to use:** cross-engine feel (fixed timestep choice, jitter strategy, tunnelling
trade-offs) → `physics-tuning`; Tilemap Collider 2D and composite merging →
`unity-tilemap-2d`; pathfinding agents → `unity-navmesh`; reading the input that drives
movement → `unity-input-system`. If Unity's official `fix-3d-physics-collisions` or
`create-2d-physics` skill is installed and an Editor is connected, it can drive the Editor for
scene setup; this skill still owns the API and the code.

## Workflow

1. **Find out which engine the object uses before touching code.** Grep the scene or prefab
   YAML for a `Rigidbody2D:` or `Rigidbody:` document header (and `BoxCollider2D:` vs
   `BoxCollider:`). Mixed 2D and 3D components on interacting objects are a bug, not a design.
2. **Read the physics settings as text, not through the Inspector.** 3D settings live in
   `ProjectSettings/DynamicsManager.asset` (`m_QueriesHitTriggers`, `m_ContactPairsMode`,
   `m_LayerCollisionMatrix`), 2D settings in `ProjectSettings/Physics2DSettings.asset`
   (`m_QueriesHitTriggers`, `m_QueriesStartInColliders`, `m_SimulationMode`,
   `m_LayerCollisionMatrix`). The matrix is a hex bitfield: read and change it with
   `Physics.GetIgnoreLayerCollision`/`IgnoreLayerCollision` (2D: the `Physics2D` versions)
   rather than editing the hex.
3. **Do physics in `FixedUpdate`.** Read input in `Update`, store intent, apply forces or set
   `linearVelocity` or call `MovePosition` in `FixedUpdate`. Both engines step after
   `FixedUpdate` by default.
4. **Move bodies through the physics API, not the Transform.** `AddForce`, `linearVelocity`,
   `MovePosition`. Writing `transform.position` on a dynamic body teleports it and skips
   collision resolution.
5. **Pick collision vs trigger.** A solid collider blocks and calls `OnCollisionEnter`
   (`OnCollisionEnter2D`); `isTrigger` passes through and calls `OnTriggerEnter`
   (`OnTriggerEnter2D`). At least one of the pair needs a rigidbody.
6. **Prune layer pairs** that never need to touch. A runtime `IgnoreLayerCollision` call is
   not saved; for a lasting change ask the user to untick the pair in Project Settings >
   Physics (or Physics 2D) > Layer Collision Matrix, or for 3D use the Unity CLI's
   `settings.physics set` command, which asks for confirmation.
7. **Verify** with one of the checks below, then remove any temporary logging.

## Patterns

### 1. Force-based movement in `FixedUpdate` with a speed clamp (3D)

```csharp
using UnityEngine;

[RequireComponent(typeof(Rigidbody))]
public class Mover : MonoBehaviour
{
    [SerializeField] private float accel = 30f, maxSpeed = 8f;
    private Rigidbody _rb;
    private Vector3 _input;   // set from Update / input system

    private void Awake() => _rb = GetComponent<Rigidbody>();

    private void FixedUpdate()
    {
        _rb.AddForce(_input * accel, ForceMode.Acceleration);     // mass-independent accel
        Vector3 flat = new(_rb.linearVelocity.x, 0, _rb.linearVelocity.z);
        if (flat.magnitude > maxSpeed)
        {
            flat = flat.normalized * maxSpeed;
            _rb.linearVelocity = new Vector3(flat.x, _rb.linearVelocity.y, flat.z);
        }
    }
}
```

`ForceMode`: `Force` and `Acceleration` are continuous (mass-scaled vs not); `Impulse` and
`VelocityChange` are instant (mass-scaled vs not; use them for jumps).

### 2. Ground check that ignores triggers (3D)

```csharp
[SerializeField] private LayerMask groundMask;   // only the Ground layer

private bool IsGrounded() =>
    Physics.Raycast(transform.position, Vector3.down, out RaycastHit _, 1.1f,
                    groundMask, QueryTriggerInteraction.Ignore);
```

### 3. Kinematic platform that carries resting bodies (3D)

```csharp
// isKinematic Rigidbody: MovePosition moves it through the solver, so bodies on top ride along.
private void FixedUpdate() =>
    _rb.MovePosition(_rb.position + Vector3.right * (2f * Time.fixedDeltaTime));
```

## 2D physics (Rigidbody2D)

Same rules, different types. The traps a 3D habit walks into:

| 3D | 2D equivalent | Difference that bites |
|---|---|---|
| `Rigidbody.isKinematic` | `Rigidbody2D.bodyType` (`Dynamic`, `Kinematic`, `Static`) | `Rigidbody2D.isKinematic` is obsolete; set `bodyType` |
| `OnCollisionEnter(Collision)` | `OnCollisionEnter2D(Collision2D)` | a 3D-named method on a 2D object never runs, with no error |
| `OnTriggerEnter(Collider)` | `OnTriggerEnter2D(Collider2D)` | same |
| `Physics.Raycast` → `bool` + `out RaycastHit` | `Physics2D.Raycast` → `RaycastHit2D` | test `if (hit)` or `hit.collider != null` |
| ray starting inside a collider misses it | `Physics2D.queriesStartInColliders` is on by default | a ground ray cast from the player's centre hits the player itself |
| `RaycastNonAlloc` | `Physics2D.Raycast(origin, dir, contactFilter, results, distance)` | the 2D `*NonAlloc` methods are deprecated in Unity 6 |
| `Vector3 angularVelocity` (rad/s) | `float angularVelocity` (degrees/s) | unit change |

For a kinematic 2D character, `Rigidbody2D.Slide` moves the body along surfaces with gravity
and slope limits, which saves writing your own cast-and-slide loop. Patterns for the ground
check with a `ContactFilter2D`, one-way platforms and `Slide` are in
`references/physics-2d.md`.

## Verify

Pick the first path that is available and say which one you used.

- **Unity CLI with a ready Editor** (`unity status --project-path <project>` reports
  `ready`): run `unity recompile --project-path <project>` for compile errors, then read the
  state back instead of eyeballing it, for example
  `unity command script eval --code 'return Physics2D.GetIgnoreLayerCollision(LayerMask.NameToLayer("Player"), LayerMask.NameToLayer("Enemy"));'`
  or a body's `bodyType`, `collisionDetectionMode` and `linearVelocity` after a few seconds of
  Play mode (`unity command editor.playmode start`). Commands change between CLI releases:
  find the current name with `unity command --query <word>` and its flags with `--help`.
- **PlayMode test, with or without the CLI:** build the case in code (a floor, a falling
  body, `yield return new WaitForSeconds(1f)`, assert the body rests above the floor or the
  callback count is 1). Run it with `unity test <project> --mode PlayMode`, or without the
  CLI in batch mode: `-batchmode -projectPath <project> -runTests -testPlatform PlayMode
  -testResults <file>` (no `-quit`; the test runner exits by itself). Read the NUnit XML, not
  just the exit code. Test-assembly setup is in `unity-csharp-scripting`.
- **Feel or visual only:** ask the user to enter Play mode and report a number (does the
  crate rest at y ≈ 1, how many `OnCollisionEnter` logs per hit).

## Gotchas

- **`OnCollisionEnter` never fires on a `CharacterController`.** `Move` bypasses the
  rigidbody system and reports through `OnControllerColliderHit`. Adding a Rigidbody does not
  fix it; the two are separate movement modes.
- **Trigger callbacks never fire.** One of the two colliders needs a rigidbody (2D: a
  `Rigidbody2D`, and `simulated` on), and both colliders must be enabled. Two static colliders
  never report.
- **No collision messages between two kinematic bodies, or kinematic vs static.** With the
  default 3D Contact Pairs Mode Unity only reports when one body is dynamic. Make one dynamic,
  use a trigger, or change Contact Pairs Mode. In 2D, turn on `useFullKinematicContacts` on
  the kinematic `Rigidbody2D`.
- **A ground or line-of-sight ray stops on a trigger volume.** Queries hit triggers by
  default in both engines. Pass `QueryTriggerInteraction.Ignore` (3D) or a `ContactFilter2D`
  with `useTriggers = false` (2D), or turn off Queries Hit Triggers.
- **2D ground check is always true.** The ray starts inside the player's own collider and
  `queriesStartInColliders` returns it. Exclude the player's layer from the mask, or start the
  ray just below the collider.
- **Obsolete warnings on `velocity`, `drag`, `angularDrag`.** Unity 6 renamed them
  `linearVelocity`, `linearDamping`, `angularDamping` in both 3D and 2D (2D also has
  `linearVelocityX`/`Y`). They still compile with warnings; `PhysicMaterial` →
  `PhysicsMaterial` is a hard error.
- **Setting `transform.position` on a dynamic body.** It teleports and skips collision. If
  you do write the Transform, queries see the old position until the next step; call
  `Physics.SyncTransforms()` (2D: `Physics2D.SyncTransforms()`) once before a same-frame query.
- **A resting body hangs in mid-air after its floor moves.** Sleeping bodies wake on
  collisions and forces, but a static collider moved by its Transform may not wake them. Call
  `WakeUp()`. A collider that moves every frame should get a kinematic rigidbody instead of
  staying static.
- **Fast objects pass through walls.** Raise Collision Detection from `Discrete`. 3D
  `Continuous` sweeps only against static colliders; `Continuous Dynamic` also against other
  continuous dynamic bodies; `Continuous Speculative` against everything and cheaper. 2D has
  `CollisionDetectionMode2D.Continuous`. For bullets, a cast along the path is often better.
- **A concave `MeshCollider` on a moving body.** Concave mesh colliders can only be static or
  kinematic, and two concave colliders never collide. Enable Convex or build a compound
  collider from primitives, and keep scale uniform.
- **Part of a compound body drifts away.** A compound collider has one rigidbody, on the root.
  An extra rigidbody on a child makes it a separate body.
- **Nothing moves, raycasts still hit.** `Time.timeScale = 0` stops the simulation; queries
  still read collider geometry. In 2D also check `Physics2D.simulationMode`: with `Script`,
  nothing moves until you call `Physics2D.Simulate`.

## References

- Read `references/physics-2d.md` when writing 2D movement, ground checks, one-way platforms
  or kinematic `Slide` controllers.
- Read `references/raycasting-and-joints.md` when you need 3D cast variants (`SphereCast`,
  `RaycastAll`, `OverlapSphere`, non-allocating buffers), `LayerMask` bit math or 3D joints.

## Related skills

- `physics-tuning`: engine-neutral feel, timestep, mass ratios, stability.
- `unity-csharp-scripting`: the `FixedUpdate`/`Update` split, test assemblies, the `.meta`
  checker.
- `unity-tilemap-2d`: tilemap colliders and composite colliders.
- `unity-navmesh`: agent movement that is not force-driven.

## Version notes

Last verified: 2026-11-11, against Unity 6000.3.28f1 (latest 6.3 LTS patch).

- Unity 6 renames (3D and 2D `velocity`/`drag`/`angularDrag`, `Rigidbody2D.isKinematic`,
  the 2D `*NonAlloc` queries, `Physics2D.OverlapCollider` → `Overlap`) are obsolete warnings
  with an API Updater path in 6.3; `PhysicMaterial` is an error. Source: Unity C# reference
  source at tag 6000.3.28f1, `Modules/Physics/ScriptBindings/*.deprecated.cs` and
  `Modules/Physics2D/ScriptBindings/Physics2D.deprecated.cs`
  (https://github.com/Unity-Technologies/UnityCsReference/tree/6000.3.28f1).
- Unity 6.3 also ships a separate low-level 2D API, `UnityEngine.LowLevelPhysics2D`
  (`PhysicsWorld`, `PhysicsBody`), with its own worlds; it is not the `Rigidbody2D` system.
  Unity 6.5 renamed it Physics Core 2D, namespace `Unity.U2D.Physics`. Use it only when the
  project already does.
- Unity CLI 1.0.0-beta.17 (2026-11-05) and the `com.unity.pipeline` package
  1.0.0-pre.1 (2026-11-10) are pre-release; command names can change.
  https://docs.unity.com/en-us/unity-cli and
  https://docs.unity3d.com/Packages/com.unity.pipeline@1.0/manual/index.html
- Manual: https://docs.unity.com/en-us/engine/6000.3/manual/unity-editor/editor-settings-reference/comp-manager-group/class-physics2dsettings
  and Scripting API pages for `Rigidbody2D`, `Physics2D`, `Rigidbody`, `Physics`.
