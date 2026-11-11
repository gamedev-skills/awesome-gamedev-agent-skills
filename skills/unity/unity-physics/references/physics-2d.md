# 2D physics patterns (Unity 6.3 LTS, Rigidbody2D)

Depth for `unity-physics`. All types are in `UnityEngine`. Checked against the 6000.3
Scripting API (`Rigidbody2D`, `Physics2D`, `ContactFilter2D`, `PlatformEffector2D`) and the
C# reference source at tag 6000.3.28f1.

## Contents

- Pick the body type
- 1. Dynamic platformer mover
- 2. Ground check with a contact filter
- 3. Kinematic character with `Slide`
- 4. One-way platform
- 5. Layers and simulation settings in code
- Read-back checks

## Pick the body type

| `bodyType` | Moved by | Use for |
|---|---|---|
| `Dynamic` | forces, gravity, collisions | players and props that react physically |
| `Kinematic` | your code (`MovePosition`, `linearVelocity`, `Slide`) | moving platforms, scripted characters |
| `Static` | never | level geometry (a `Collider2D` with no `Rigidbody2D` is also static) |

A collider that moves every frame should sit on a `Kinematic` body rather than be static:
moving a static collider forces the engine to rebuild it.

## 1. Dynamic platformer mover

```csharp
using UnityEngine;

[RequireComponent(typeof(Rigidbody2D))]
public class Runner2D : MonoBehaviour
{
    [SerializeField] private float speed = 6f, jumpSpeed = 12f;
    private Rigidbody2D _rb;
    private float _moveX;        // set from input in Update
    private bool _jumpQueued;    // set from input in Update, consumed once

    private void Awake()
    {
        _rb = GetComponent<Rigidbody2D>();
        _rb.interpolation = RigidbodyInterpolation2D.Interpolate;  // smooth under a following camera
        _rb.freezeRotation = true;                                 // no tipping over
    }

    private void FixedUpdate()
    {
        _rb.linearVelocityX = _moveX * speed;   // keep Y so gravity still applies
        if (_jumpQueued)
        {
            _rb.linearVelocityY = jumpSpeed;
            _jumpQueued = false;
        }
    }
}
```

## 2. Ground check with a contact filter

`IsTouching` reads contacts the solver already found, so it has no ray to start inside the
player's own collider. The normal-angle range keeps walls and ceilings out.

```csharp
[SerializeField] private LayerMask groundMask;
private ContactFilter2D _groundFilter;

private void Start()
{
    _groundFilter = new ContactFilter2D { useTriggers = false };
    _groundFilter.SetLayerMask(groundMask);
    _groundFilter.SetNormalAngle(45f, 135f);   // surface normals pointing roughly up
}

private bool IsGrounded() => _rb.IsTouching(_groundFilter);
```

A cast that reuses one buffer (the 2D `*NonAlloc` methods are deprecated in Unity 6):

```csharp
private readonly RaycastHit2D[] _hits = new RaycastHit2D[4];

private bool GroundBelow(float distance) =>
    Physics2D.Raycast(transform.position, Vector2.down, _groundFilter, _hits, distance) > 0;
```

## 3. Kinematic character with `Slide`

`Rigidbody2D.Slide` moves the body along surfaces, applies the `SlideMovement.gravity` it is
given and stops on slopes steeper than `surfaceSlideAngle`. Unity's own example calls it from
`Update` with `Time.deltaTime`; it returns the hits and the remaining velocity.

```csharp
[SerializeField] private Rigidbody2D.SlideMovement slide = new Rigidbody2D.SlideMovement();
private Rigidbody2D _rb;

private void Awake()
{
    _rb = GetComponent<Rigidbody2D>();
    _rb.bodyType = RigidbodyType2D.Kinematic;
}

// Call from Update; returns true when the body is standing on a surface.
public bool Move(float moveX, float speed)
{
    Rigidbody2D.SlideResults r = _rb.Slide(new Vector2(moveX * speed, 0f), Time.deltaTime, slide);
    return r.surfaceHit;   // RaycastHit2D converts to bool
}
```

## 4. One-way platform

Add a `PlatformEffector2D` to the platform, set `useOneWay = true` and `surfaceArc` (180 is the
top half), and tick **Used By Effector** on its collider (`collider.usedByEffector = true` in
code). Without that tick the effector does nothing. To drop through, briefly ignore the pair:
`Physics2D.IgnoreCollision(playerCollider, platformCollider, true)`, then set it back.

## 5. Layers and simulation settings in code

```csharp
int player = LayerMask.NameToLayer("Player"), enemy = LayerMask.NameToLayer("Enemy");
Physics2D.IgnoreLayerCollision(player, enemy, true);           // separate from the 3D matrix
bool ignored = Physics2D.GetIgnoreLayerCollision(player, enemy);
```

`Physics2D.simulationMode` is `FixedUpdate` by default. `Update` steps once per frame;
`Script` never steps until you call `Physics2D.Simulate(deltaTime)`. A project that "has no
gravity" often has `m_SimulationMode` changed in `ProjectSettings/Physics2DSettings.asset`.

## Read-back checks

With the Unity CLI and a ready Editor, in Play mode:

```bash
unity command script eval --code 'var rb = Object.FindAnyObjectByType<Rigidbody2D>(); return rb.name + " " + rb.bodyType + " v=" + rb.linearVelocity + " sim=" + rb.simulated;'
```

Without it, put the same values in a PlayMode test assertion or a one-off `Debug.Log` and read
the Editor log.
