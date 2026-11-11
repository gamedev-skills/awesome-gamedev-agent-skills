# MonoBehaviour lifecycle & coroutines (Unity 6.3 LTS)

Depth for the `unity-csharp-scripting` skill: the full execution order and the coroutine
patterns that don't fit in the main playbook. Verified against the Unity Manual
"Event function execution order" page and `ScriptReference/MonoBehaviour`.

## Contents

- Execution order
- Coroutine yield instructions
- `Awaitable` (async/await) instead of a coroutine
- Custom yield instruction
- Gotchas

## Execution order (the parts that matter for gameplay)

Per object, the engine calls these in this order:

| Phase | Callback | Runs | Use for |
|-------|----------|------|---------|
| Load | `Awake` | once, when the object loads — even if the script component is disabled, but not while the GameObject is inactive | cache `GetComponent`, set up self |
| Enable | `OnEnable` | each time the object/script enables | subscribe to events, re-arm coroutines |
| Init | `Start` | once, before first `Update`, after every `Awake` | wiring that depends on other objects |
| Physics | `FixedUpdate` | every fixed step (default 0.02s) | rigidbody forces, `MovePosition` |
| Physics | `OnTriggerXXX` / `OnCollisionXXX` | during the physics step | collision/trigger response |
| Frame | `Update` | once per rendered frame | input polling, non-physics logic |
| Frame | `LateUpdate` | once per frame, after all `Update`s | camera follow, IK fix-up |
| Disable | `OnDisable` | each time the object/script disables | unsubscribe from events |
| Teardown | `OnDestroy` | once, when destroyed | release native handles, save |

Key consequences:

- `FixedUpdate` may run zero, one, or several times per frame depending on frame rate. Never
  read raw "per frame" input there — read it in `Update`, consume it in `FixedUpdate`.
- All `Awake` calls finish before any `Start`. Order *among* `Awake`s (and among `Start`s) is
  undefined unless you set a Script Execution Order in Project Settings.
- `OnEnable` runs after `Awake` on first enable, then again on every re-enable. Pair every
  `OnEnable` subscription with an `OnDisable` unsubscription to avoid duplicate handlers.

## Coroutine yield instructions

```csharp
yield return null;                          // resume at the start of the next frame
yield return new WaitForSeconds(2f);        // wait 2s of scaled game time (affected by Time.timeScale)
yield return new WaitForSecondsRealtime(2f);// wait 2s of real time (ignores timeScale; good for pause menus)
yield return new WaitForFixedUpdate();      // resume after the next physics step
yield return new WaitUntil(() => isReady);  // resume once the predicate is true
yield return new WaitWhile(() => isLoading);// resume once the predicate is false
yield return StartCoroutine(OtherRoutine());// run a nested coroutine to completion first
```

## `Awaitable` (async/await) instead of a coroutine

Unity 6 ships `UnityEngine.Awaitable`, an allocation-light awaitable for `async` methods.
The coroutine waits map directly:

| Coroutine | `Awaitable` |
|-----------|-------------|
| `yield return null` | `await Awaitable.NextFrameAsync()` |
| `yield return new WaitForSeconds(t)` | `await Awaitable.WaitForSecondsAsync(t)` |
| `yield return new WaitForFixedUpdate()` | `await Awaitable.FixedUpdateAsync()` |
| `yield return new WaitForEndOfFrame()` | `await Awaitable.EndOfFrameAsync()` |
| (no equivalent) | `await Awaitable.BackgroundThreadAsync()` / `MainThreadAsync()` |

```csharp
using System;
using UnityEngine;

public class Blinker : MonoBehaviour
{
    [SerializeField] private Renderer target;

    private async void Start()
    {
        try
        {
            while (true)
            {
                target.enabled = !target.enabled;
                // The token cancels the wait when this component is destroyed.
                await Awaitable.WaitForSecondsAsync(0.5f, destroyCancellationToken);
            }
        }
        catch (OperationCanceledException) { /* destroyed: stop quietly */ }
    }
}
```

Rules that differ from coroutines:

- An async method is **not** stopped when its object is disabled or destroyed. Pass
  `destroyCancellationToken` (read it before the object is destroyed) or check state after
  each `await`.
- `Awaitable` instances are pooled: await each one **once**. To await a result twice, store
  the result, not the `Awaitable`.
- After `BackgroundThreadAsync`, most Unity APIs are off-limits until you
  `await Awaitable.MainThreadAsync()`. Background work does not stop when you exit Play mode;
  use `Application.exitCancellationToken` for that.
- Prefer `async Awaitable` over `async void` for methods you call yourself, so callers can
  await them; reserve `async void` for Unity messages such as `Start`.

## Custom yield instruction

When you want a reusable wait condition:

```csharp
public class WaitForAnimationEnd : CustomYieldInstruction
{
    private readonly Animator _a;
    private readonly int _layer;
    public WaitForAnimationEnd(Animator a, int layer = 0) { _a = a; _layer = layer; }
    // keepWaiting == true means "keep yielding"; false resumes the coroutine.
    public override bool keepWaiting => _a.GetCurrentAnimatorStateInfo(_layer).normalizedTime < 1f;
}
```

## Gotchas

- Coroutines are killed when the GameObject is **deactivated** (`SetActive(false)`) or the
  script is destroyed — but *not* when only the script component is disabled while the object
  stays active. Re-arm in `OnEnable` if needed.
- Allocating `new WaitForSeconds(x)` every loop iteration creates garbage; cache the instance.
