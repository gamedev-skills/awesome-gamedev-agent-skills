---
name: unity-csharp-scripting
description: >
  Write Unity 6.3 LTS C# gameplay scripts: the MonoBehaviour lifecycle
  (Awake/OnEnable/Start/Update/FixedUpdate/LateUpdate), GameObject and component
  access, coroutines, and Inspector serialization. Use when creating or editing .cs
  scripts in a Unity project, or when the user mentions MonoBehaviour, Start/Update,
  GetComponent, SerializeField, coroutines, or "Unity script".
---

# Unity C# Scripting (MonoBehaviour)

Write correct, idiomatic gameplay scripts in Unity 6. Get the lifecycle, component
access, serialization, and coroutines right so behaviour is deterministic and the
Inspector stays useful. Targets **Unity 6.3 LTS (6000.3)**, C# / .NET Standard 2.1.

## When to use

- Use when authoring or fixing a `MonoBehaviour`: choosing the right lifecycle callback,
  reading/caching components, exposing fields to the Inspector, or running timed logic
  with coroutines.
- Use when the project has `*.cs` files, an `Assembly-CSharp` or `*.asmdef`, and a
  `ProjectSettings/` folder.

**When *not* to use:** moving rigidbodies / collision response → `unity-physics`; reading
player input → `unity-input-system`; shared data assets / config → `unity-scriptableobjects`;
Animator parameters → `unity-animation`. This skill owns the *script lifecycle and C#
plumbing*, not those subsystems.

## Core workflow

1. **Pick the callback by purpose, not habit.** `Awake` (cache references, runs once on
   load), `OnEnable` (subscribe to events), `Start` (init that depends on other objects'
   `Awake`), `Update` (per-frame logic/input polling), `FixedUpdate` (physics), `LateUpdate`
   (camera follow after movement), `OnDisable`/`OnDestroy` (unsubscribe/cleanup).
2. **Cache stable component references in `Awake`** when they are reused frequently.
   Judge lookup cost by call frequency, object count and profiler evidence.
3. **Expose tunables with `[SerializeField] private`**, not public fields, so other code
   can't mutate them but designers can edit them in the Inspector.
4. **Scale per-frame values by `Time.deltaTime`** in `Update` (and `Time.fixedDeltaTime`
   semantics are automatic in `FixedUpdate`).
5. **Use coroutines for time-sequenced logic** (delays, tweens, "do X then wait then Y");
   start them with `StartCoroutine` and stop them deterministically.
6. **Verify in Play mode**: check the Console for null-reference exceptions, confirm values
   in the Inspector update as expected, and watch the Profiler if `Update` is hot.
7. **Check `.meta` files before you finish.** When you create, move, rename or delete
   scripts or assets outside the Editor, always move a file together with its `.meta`
   (a new `.meta` means a new GUID and broken references). Then run
   `python scripts/check_unity_project.py <project-dir>` (`--json` for machine-readable
   output), fix every `ERROR` (duplicate or malformed GUIDs, files moved without their
   `.meta`, missing script references) and re-run until it exits 0. A missing `.meta` on a
   brand-new file is only a warning; Unity creates it on the next import. Run the script
   path relative to this skill directory, or resolve the installed skill path first. It
   needs Python 3.10+ and nothing else, reads only text-serialized assets, and does not
   replace opening the project in Unity.

## Patterns

### 1. Lifecycle + cached components (the canonical skeleton)

```csharp
using UnityEngine;

[RequireComponent(typeof(Rigidbody))]      // auto-adds the dependency, prevents null refs
public class PlayerController : MonoBehaviour
{
    [SerializeField] private float moveSpeed = 6f;   // editable in Inspector, private in code
    private Rigidbody _rb;                            // cached, not fetched per frame

    private void Awake() => _rb = GetComponent<Rigidbody>();  // cache once on load

    private void Update()
    {
        // Per-frame, non-physics work. Scale by deltaTime so it is frame-rate independent.
        transform.Rotate(0f, 90f * Time.deltaTime, 0f);
    }

    private void FixedUpdate()
    {
        // Physics work belongs here (fixed timestep). See the unity-physics skill.
        _rb.MovePosition(_rb.position + transform.forward * moveSpeed * Time.fixedDeltaTime);
    }
}
```

### 2. Safe component access with `TryGetComponent`

```csharp
// Avoids allocating a null and is clearer than GetComponent + null check.
if (other.TryGetComponent<Health>(out var health))
    health.Apply(-10);
```

### 3. Serialization that shows up correctly in the Inspector

```csharp
[SerializeField, Range(0f, 1f)] private float volume = 0.8f;  // slider
[SerializeField] private string playerName = "Hero";          // private but serialized

[System.Serializable]                 // REQUIRED for a plain class to serialize/show
public class Stats { public int hp = 100; public int mana = 50; }

[SerializeField] private Stats stats = new();  // nested struct-like data in the Inspector
```

### 4. Coroutines for time-sequenced logic

```csharp
private void Start() => StartCoroutine(FlashThenHide());

private System.Collections.IEnumerator FlashThenHide()
{
    yield return new WaitForSeconds(0.5f);   // wait half a second of game time
    GetComponent<Renderer>().enabled = false;
    yield return null;                       // resume next frame
}
```

## Pitfalls

- **Repeated component lookups in hot paths** — many `GetComponent` calls across many objects
  can add CPU cost. Cache stable references in `Awake`/`Start`; profile before treating an
  occasional lookup as a bottleneck, and refresh the cache if components change at runtime.
- **Physics in `Update`** — moving a `Rigidbody` with forces or `MovePosition` outside
  `FixedUpdate` causes jitter and timestep-dependent behaviour. Read input in `Update`,
  apply physics in `FixedUpdate`.
- **Relying on `Start` order across objects** — `Start` runs after *all* `Awake`s, but order
  among `Start`s is undefined. Do cross-object wiring in `Start`, self-setup in `Awake`.
- **`public` fields just to show them in the Inspector** — that also lets any script mutate
  them. Use `[SerializeField] private` instead.
- **`gameObject.tag == "Enemy"`** allocates a string and is slower; use
  `gameObject.CompareTag("Enemy")`.
- **Coroutines stop when the GameObject is disabled** — a disabled object's coroutines are
  killed; re-`StartCoroutine` in `OnEnable` if it must survive toggling. Setting only the
  script's `enabled = false` does *not* stop them.
- **Obsolete warnings on `FindObjectOfType` / `FindObjectsOfType`** — Unity 6 replaced them.
  Use `FindFirstObjectByType` (old behaviour), `FindAnyObjectByType` (faster, any match) or
  `FindObjectsByType(FindObjectsSortMode.None)`; all are slow, so cache the result.
- **An `async` method keeps running after its object is destroyed** — `await` is not tied to
  the GameObject the way a coroutine is. Pass `destroyCancellationToken` to the
  `Awaitable` waits (they then throw `OperationCanceledException`), and never await the same
  `Awaitable` instance twice: instances are pooled.
- **`Update` never runs before `Start`, but the *first* `Update` can run on the same
  frame as `Start`** — guard against not-yet-initialised fields if you split setup oddly.

## References

- For the full event-execution-order table, advanced coroutine patterns (custom
  `CustomYieldInstruction`, stopping by handle, `WaitUntil`/`WaitWhile`) and the `Awaitable`
  equivalents of coroutine waits, read `references/lifecycle-and-coroutines.md`.
- `scripts/check_unity_project.py` — read-only `.meta`/GUID and missing-script checker;
  `--help` lists every check and the exit codes.
- Primary docs: Unity Manual "Event function execution order"
  (`https://docs.unity3d.com/Manual/execution-order.html`), `ScriptReference/MonoBehaviour`,
  and the Manual page "Asynchronous programming with the Awaitable class".

## Related skills

- `unity-physics` — `Rigidbody`, collisions, and `FixedUpdate` motion.
- `unity-input-system` — reading player input into these scripts.
- `unity-scriptableobjects` — sharing data/config between scripts without singletons.
