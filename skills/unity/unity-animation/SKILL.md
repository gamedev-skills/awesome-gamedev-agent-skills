---
name: unity-animation
description: >
  Drive Unity 6.3 LTS character animation with Animator Controllers: states, transitions,
  parameters, blend trees, animation layers, and humanoid Avatar IK. Use when wiring an
  Animator, setting parameters from script (SetFloat/SetBool/SetTrigger), building blend
  trees, or when the user mentions Animator, Mecanim, state machine, blend tree, or .controller.
---

# Unity Animation (Animator / Mecanim)

Control animation state with Unity 6.3 LTS's `Animator` and Animator Controllers: parameters,
transitions, blend trees, layers, and humanoid IK. Targets **Unity 6.3 LTS (6000.3)**.

## When to use

- Use when connecting animation clips into a state machine, driving them from script via
  parameters, blending locomotion (idle→walk→run), layering an upper-body action over
  movement, or adding foot/hand IK on a humanoid rig.
- Use when the project has `*.controller` (Animator Controller) and `*.anim` assets, or a
  rigged model with an Avatar.

**When *not* to use:** simple non-skeletal value tweens (UI fades, position lerps) are better
done with a tween/coroutine — see `unity-csharp-scripting`. Timeline cutscenes are a separate
tool. 2D sprite frame animation also uses the Animator but with sprite keyframes.

## Core workflow

1. **Add an `Animator`** to the model and assign an Animator Controller; for a humanoid model,
   set its rig to **Humanoid** so it has an Avatar (enables retargeting and IK).
2. **Define parameters** on the controller — `Float` (Speed), `Bool` (IsGrounded), `Int`,
   `Trigger` (Jump) — and states with transitions whose *conditions* read those parameters.
3. **Drive ordinary locomotion with parameters**: `SetFloat`, `SetBool`, `SetInteger`,
   `SetTrigger`. Let controller conditions resolve transitions; use `CrossFade`/`Play` when
   an explicit scripted transition is intended (see the pattern below).
4. **Blend continuous motion with a Blend Tree** (one `Float` like Speed drives idle↔walk↔run)
   instead of many discrete states + transitions.
5. **Layer additive/override motion** (e.g. an upper-body "aim" layer with an Avatar Mask) and
   control its `layerWeight`.
6. **Verify** in the Animator window during Play mode — the live state highlights and parameter
   values update, so you can see exactly which transition fired (or didn't).

## Patterns

### 1. Drive locomotion + a one-shot action from script

```csharp
using UnityEngine;

[RequireComponent(typeof(Animator))]
public class CharacterAnim : MonoBehaviour
{
    private Animator _anim;
    // Cache parameter hashes — faster and typo-proof vs string lookups every frame.
    private static readonly int Speed     = Animator.StringToHash("Speed");
    private static readonly int IsGrounded= Animator.StringToHash("IsGrounded");
    private static readonly int Jump      = Animator.StringToHash("Jump");

    private void Awake() => _anim = GetComponent<Animator>();

    public void Tick(float planarSpeed, bool grounded)
    {
        _anim.SetFloat(Speed, planarSpeed);     // drives a 1D blend tree (idle/walk/run)
        _anim.SetBool(IsGrounded, grounded);    // gates a falling/landing transition
    }

    public void DoJump() => _anim.SetTrigger(Jump);  // fire-and-forget; auto-resets after use
}
```

### 2. Smooth a noisy input into a blend parameter

```csharp
// dampTime smooths Speed so the blend tree doesn't snap; great for analog sticks.
_anim.SetFloat(Speed, targetSpeed, 0.1f /* dampTime */, Time.deltaTime);
```

### 3. Play / cross-fade a state directly (bypassing parameter conditions)

```csharp
// Useful for hit reactions where you want an immediate, explicit transition.
_anim.CrossFade("Hit", 0.1f);                    // 0.1 = 10% of the state's length, not seconds
_anim.CrossFadeInFixedTime("Hit", 0.15f);        // duration in seconds
// Or jump instantly:  _anim.Play("Hit");
```

### 4. Wait until the current state finishes

```csharp
private System.Collections.IEnumerator AfterAttack()
{
    yield return null;                                 // let the Animator start the transition
    // During a transition the "current" state is the one being left; read the next one.
    var info = _anim.IsInTransition(0)
        ? _anim.GetNextAnimatorStateInfo(0)
        : _anim.GetCurrentAnimatorStateInfo(0);        // layer 0
    yield return new WaitForSeconds(info.length);      // seconds; approximate, varies in blend trees
    // ...follow-up logic
}
```

## Pitfalls

- **`SetTrigger` missed or "sticks"** — triggers are consumed by the next satisfied transition
  and auto-reset; if no transition consumes it, it can fire later unexpectedly. Use
  `ResetTrigger` to clear, or prefer a `Bool` when the condition is a sustained state.
- **String parameter typos fail silently** — a misspelled name just does nothing. Use
  `Animator.StringToHash` and cache the int hashes.
- **Transition feels laggy** — `Has Exit Time` makes the transition wait for the clip to reach
  a normalized time. Uncheck it for responsive, condition-driven transitions (jump, hit).
- **Character slides or won't move** — `Apply Root Motion` is on but your code also moves the
  transform (or vice versa). Decide: root motion *or* scripted movement, not both.
- **Upper-body layer overrides the whole body** — set the layer's Blend mode (Override vs
  Additive), assign an Avatar Mask, and tune `layerWeight` (0–1).
- **A cross-fade is much slower or faster than expected** — `CrossFade`'s duration is
  *normalized* to the state's length. Use `CrossFadeInFixedTime` to give the
  duration in seconds.
- **IK does nothing** — IK only applies inside `OnAnimatorIK`, requires "IK Pass" enabled on
  the layer, and needs a Humanoid Avatar.

## References

- For **blend trees** (1D vs 2D Freeform/Directional), **animation layers + Avatar Masks**,
  and **humanoid IK** (`OnAnimatorIK`, `SetIKPositionWeight`, `SetIKPosition`, look-at), read
  `references/blend-trees-and-ik.md`.
- Primary docs: Unity Manual "Animation" section and `ScriptReference/Animator`.

## Related skills

- `unity-csharp-scripting` — the MonoBehaviour and coroutine timing used above.
- `unity-physics` — moving the body that the animation visualises.
- `game-ai` — deciding *when* to play which animation state.
