---
name: unity-physics
description: >
  Set up 3D physics in Unity 6.3 LTS: Rigidbody movement and forces, colliders, triggers vs
  collisions, layer-based collision, raycasts, and joints. Use when adding a Rigidbody,
  handling OnCollisionEnter/OnTriggerEnter, tuning collision layers, casting rays, or when
  the user mentions Unity physics, AddForce, isKinematic, or linearVelocity.
---

# Unity Physics (Rigidbody / PhysX)

Make objects move, collide, and detect each other with Unity 6.3 LTS's built-in 3D physics
(PhysX). Get the `FixedUpdate` discipline, trigger-vs-collision rules, and collision layers
right. Targets **Unity 6.3 LTS (6000.3)**.

> **Unity 6 renames:** `Rigidbody.velocity` → **`linearVelocity`**, `drag` → **`linearDamping`**,
> `angularDrag` → **`angularDamping`**. The old names still compile in 6.3 LTS but are obsolete
> (warnings; the API Updater offers the rename), so write the new names. `PhysicMaterial` →
> **`PhysicsMaterial`** is a hard compile error in old code.

## When to use

- Use when giving an object physical motion (forces, velocity, gravity), responding to
  collisions or triggers, setting up collision layers/masks, raycasting for ground checks or
  line-of-sight, or connecting bodies with joints.
- Use when scenes/prefabs contain `Rigidbody` + `Collider` components.

**When *not* to use:** 2D physics (`Rigidbody2D`, `Collider2D`) is a separate API — adapt the
concepts but the types differ. Unity 6.3 also has a separate low-level 2D API
(`UnityEngine.LowLevelPhysics2D`: `PhysicsWorld`, `PhysicsBody`) with its own isolated worlds;
it is not the `Rigidbody2D` system. Unity 6.5 renamed it Physics Core 2D, namespace
`Unity.U2D.Physics` (the API Updater rewrites old scripts). Cross-engine *feel* tuning
(timestep, jitter, tunnelling) → `physics-tuning`. Reading input that drives movement →
`unity-input-system`.

## Core workflow

1. **Add a `Rigidbody`** to anything that should be simulated; add a `Collider` to anything
   that should be hit. `OnCollision*` messages need a Collider on both and at least one
   **dynamic** (non-kinematic) Rigidbody: with the default Contact Pairs Mode, kinematic vs
   kinematic and kinematic vs static send no collision messages.
2. **Do all physics in `FixedUpdate`.** Read input in `Update`, store intent, then apply
   forces / set `linearVelocity` / call `MovePosition` in `FixedUpdate`.
3. **Move bodies through the physics API, not the Transform.** Use `AddForce`,
   `linearVelocity`, or `MovePosition` — never assign `transform.position` to a non-kinematic
   Rigidbody (it teleports and breaks collision resolution).
4. **Pick collision vs trigger.** A solid collision blocks and calls `OnCollisionEnter`; a
   `Collider` with `Is Trigger` checked passes through and calls `OnTriggerEnter`.
5. **Organise interactions with layers.** Put objects on layers and edit the Layer Collision
   Matrix (Project Settings → Physics) so unrelated things don't test against each other.
6. **Verify** with the Physics Debugger (Window → Analysis → Physics Debugger) and by watching
   for jitter; if fast objects pass through walls, raise Collision Detection mode.

## Patterns

### 1. Force-based movement in `FixedUpdate` (with a speed clamp)

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
        // Unity 6.3 LTS: linearVelocity (was 'velocity'). Clamp horizontal speed.
        Vector3 flat = new(_rb.linearVelocity.x, 0, _rb.linearVelocity.z);
        if (flat.magnitude > maxSpeed)
        {
            flat = flat.normalized * maxSpeed;
            _rb.linearVelocity = new Vector3(flat.x, _rb.linearVelocity.y, flat.z);
        }
    }
}
```

`ForceMode`: `Force` (continuous, mass-scaled), `Acceleration` (continuous, ignores mass),
`Impulse` (instant, mass-scaled — jumps), `VelocityChange` (instant, ignores mass).

### 2. Collision vs trigger callbacks

```csharp
// Solid hit: both have colliders, at least one has a dynamic (non-kinematic) Rigidbody.
private void OnCollisionEnter(Collision col)
{
    // GetContact avoids the garbage that the col.contacts array allocates.
    Debug.Log($"Hit {col.gameObject.name} at {col.GetContact(0).point}");
}

// Overlap: one collider has 'Is Trigger' = true, and at least one party has a Rigidbody
// (or a Rigidbody carries the trigger). Two static colliders never report.
private void OnTriggerEnter(Collider other)
{
    if (other.CompareTag("Pickup")) Destroy(other.gameObject);
}
```

### 3. Ground check with a layer-masked raycast

```csharp
[SerializeField] private LayerMask groundMask;   // set to your "Ground" layer in the Inspector

private bool IsGrounded()
{
    // Cast a short ray down; only test colliders on groundMask.
    return Physics.Raycast(transform.position, Vector3.down, out RaycastHit hit,
                           1.1f, groundMask);
}
```

### 4. Kinematic platform that still pushes bodies

```csharp
// isKinematic Rigidbody: not driven by forces, but MovePosition interpolates and carries
// resting bodies correctly (unlike moving the Transform directly).
private void FixedUpdate() => _rb.MovePosition(_rb.position + Vector3.right * (2f * Time.fixedDeltaTime));
```

## Pitfalls

- **Obsolete warnings on `velocity` / `drag` / `angularDrag`** — Unity 6 renamed them to
  `linearVelocity`, `linearDamping` and `angularDamping` (`angularVelocity` is unchanged). Let
  the API Updater rename them or edit by hand; `PhysicMaterial` must become `PhysicsMaterial`.
- **Setting `transform.position` on a dynamic Rigidbody** — teleports it, skips collision.
  Use `MovePosition` (kinematic/interpolated) or apply forces. If you *do* write the transform,
  physics queries (`Raycast`, `OverlapSphere`) see the old position until the next physics step
  — call `Physics.SyncTransforms()` once before a same-frame query, never every frame.
- **`OnCollisionEnter` never fires on a `CharacterController`** — `CharacterController.Move`
  bypasses the Rigidbody system; it reports hits via `OnControllerColliderHit(ControllerColliderHit)`
  instead. Don't add a Rigidbody to "fix" it — the two are mutually exclusive movement modes.
- **A ground or line-of-sight ray stops on a trigger volume** — `Physics.Raycast` hits trigger
  colliders by default (Project Settings → Physics → Queries Hit Triggers is on, i.e.
  `Physics.queriesHitTriggers == true`). Pass `QueryTriggerInteraction.Ignore` to skip them in
  one query, or turn the global setting off. A ray also returns `false` for a collider its
  origin starts *inside*.
- **A resting Rigidbody stays put after you move or disable what it rests on** — below the
  Sleep Threshold a body goes to sleep. Collisions and `AddForce` wake it automatically, but
  moving a *static* collider (no Rigidbody) via its Transform may not, so the crate hangs in
  mid-air when the floor slides away. Call `Rigidbody.WakeUp()` on the affected bodies.
- **Applying forces in `Update`** — frame-rate-dependent and jittery. Physics goes in
  `FixedUpdate`.
- **`OnCollisionEnter` never fires between two kinematic bodies** (or kinematic vs static) —
  with the default Contact Pairs Mode, Unity only sends collision messages when at least one
  body is dynamic. Make one dynamic, use a trigger, or set Project Settings → Physics →
  Contact Pairs Mode to enable kinematic pairs (more contact work every step).
- **Trigger callbacks never fire** — triggers need a `Rigidbody` on at least one of the two
  colliders, and both colliders enabled; two static triggers don't report overlaps.
- **Fast objects pass through walls (tunnelling)** — raise the Rigidbody's Collision Detection
  from `Discrete`. Note `Continuous` sweeps against **static colliders only** (it falls back to
  Discrete against other dynamic bodies); `Continuous Dynamic` also sweeps against other
  continuous dynamic bodies; `Continuous Speculative` works against everything and is cheaper.
  For bullets, also consider a `SphereCast`/`Raycast` along the trajectory instead of a collider.
- **Non-uniform-scaled `MeshCollider`s or scaled colliders** misbehave; prefer primitive
  colliders and keep scale uniform.
- **A concave `MeshCollider` on a moving body** — Mesh colliders are concave by default, and
  concave ones can only be static or kinematic; two concave colliders never collide at all.
  For a dynamic Rigidbody enable **Convex** on the MeshCollider, or build a compound collider
  from primitives.
- **Part of a compound body drifts off on its own** — a compound collider should have exactly
  one Rigidbody, on the root. An extra Rigidbody on a child makes that child a separate body.
- **Nothing moves and no callbacks fire, but raycasts still hit** — `Time.timeScale = 0` stops
  `FixedUpdate` and the simulation; queries read collider geometry and keep working. Restore
  a positive `timeScale` when the pause ends.
- **Everything collides with everything** — wasted cost; assign layers and prune the Layer
  Collision Matrix.

## References

- For raycast variants (`SphereCast`, `RaycastAll`, `OverlapSphere`, `LayerMask` bit math) and
  joints (`FixedJoint`, `HingeJoint`, `ConfigurableJoint`, breakable joints), read
  `references/raycasting-and-joints.md`.
- Primary docs: Unity Manual "Physics" section and `ScriptReference/Rigidbody`,
  `ScriptReference/Physics.Raycast`. For the added gotchas: `ScriptReference/CollisionDetectionMode`,
  `ScriptReference/Physics-queriesHitTriggers`, `ScriptReference/MonoBehaviour.OnControllerColliderHit`,
  `ScriptReference/Physics.SyncTransforms`, `ScriptReference/Rigidbody.WakeUp`, and the Manual
  pages "Physics settings" (Queries Hit Triggers, Contact Pairs Mode), "Introduction to rigid
  body physics" (sleeping), "Introduction to compound colliders" and "Introduction to Mesh
  colliders" (concave vs convex).

## Related skills

- `physics-tuning` — engine-agnostic feel: fixed timestep, mass/drag, CCD, stability.
- `unity-csharp-scripting` — the `FixedUpdate`/`Update` split these patterns rely on.
- `unity-navmesh` — agent movement that is *not* force-driven.
