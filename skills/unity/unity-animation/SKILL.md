---
name: unity-animation
description: >
  Unity 6.3 LTS character animation with the Animator (Mecanim): states and transitions, blend
  trees, Avatar Mask layers, root motion and humanoid IK. Use for SetTrigger wiring, a transition
  that lags or never fires, sliding root motion, or an upper-body layer overriding the legs. Not
  for AI state machines (`game-ai`), juice (`game-feel`) or Godot (`godot-animation`).
---

# Unity Animation (Animator / Mecanim)

Control animation state with the `Animator` and Animator Controllers in Unity 6.3 LTS
(6000.3): parameters, transitions, blend trees, layers and humanoid IK. A `.controller` file is
text YAML, so you can read its parameters and states without the Editor, and build one from
editor code instead of the Animator window.

## When to use

- Connecting clips into a state machine, driving it from script, blending locomotion
  (idle, walk, run), layering an upper-body action over movement, foot or hand IK.
- The project has `*.controller` and `*.anim` assets, or a rigged model with an Avatar.

**When not to use:** simple value tweens (UI fades, position lerps) → a coroutine in
`unity-csharp-scripting`; when an NPC should attack or flee → `game-ai`; Timeline cutscenes
have no skill here. 2D sprite frame animation uses the same Animator with sprite keyframes.

## Workflow

1. **Read the controller before writing code.** In the `.controller` YAML,
   `m_AnimatorParameters` lists each parameter's `m_Name` and `m_Type` (1 Float, 3 Int,
   4 Bool, 9 Trigger), and each `AnimatorState` document has its `m_Name`. Your script's
   strings must match these exactly.
2. **Set the rig.** Humanoid IK and retargeting need the model imported as Humanoid
   (`animationType: 3` in the model's `.meta`); ask before changing a model's rig, since it
   rebuilds the Avatar.
3. **Drive locomotion with parameters** (`SetFloat`, `SetBool`, `SetInteger`, `SetTrigger`)
   through cached `Animator.StringToHash` ids, and let transitions resolve. Use
   `CrossFadeInFixedTime` only for deliberate scripted cuts such as hit reactions.
4. **Blend continuous motion with a blend tree** driven by one `Float` (or two for 2D
   directional) instead of many states and transitions.
5. **Layer upper-body actions** with an Avatar Mask and `SetLayerWeight`.
6. **Create or change controllers from code** when the Editor UI is not available
   (pattern 3), then re-read the YAML to confirm.
7. **Verify** with the checks below.

## Patterns

### 1. Parameters from script with cached hashes

```csharp
using UnityEngine;

[RequireComponent(typeof(Animator))]
public class CharacterAnim : MonoBehaviour
{
    private static readonly int Speed = Animator.StringToHash("Speed");
    private static readonly int IsGrounded = Animator.StringToHash("IsGrounded");
    private static readonly int Jump = Animator.StringToHash("Jump");
    private Animator _anim;

    private void Awake() => _anim = GetComponent<Animator>();

    public void Tick(float planarSpeed, bool grounded)
    {
        _anim.SetFloat(Speed, planarSpeed, 0.1f, Time.deltaTime);  // damped: no snapping
        _anim.SetBool(IsGrounded, grounded);
    }

    public void DoJump() => _anim.SetTrigger(Jump);   // consumed by the next matching transition
}
```

### 2. Wait for the state you just triggered

```csharp
private System.Collections.IEnumerator AfterAttack()
{
    yield return null;   // let the Animator start the transition
    // During a transition the current state is the one being left; read the next one.
    AnimatorStateInfo info = _anim.IsInTransition(0)
        ? _anim.GetNextAnimatorStateInfo(0)
        : _anim.GetCurrentAnimatorStateInfo(0);
    yield return new WaitForSeconds(info.length);   // approximate inside blend trees
}
```

### 3. Build a controller from editor code

Put this in an `Editor` folder. Run it from a menu item, from the Unity CLI with
`unity command script eval --code 'BuildLocomotionController.Build();'`, or in batch mode with
`-executeMethod BuildLocomotionController.Build`.

```csharp
using UnityEditor;
using UnityEditor.Animations;
using UnityEngine;

public static class BuildLocomotionController
{
    [MenuItem("Tools/Build Locomotion Controller")]
    public static void Build()
    {
        if (!AssetDatabase.IsValidFolder("Assets/Animation"))
            AssetDatabase.CreateFolder("Assets", "Animation");

        var controller = AnimatorController.CreateAnimatorControllerAtPath("Assets/Animation/Player.controller");
        controller.AddParameter("Speed", AnimatorControllerParameterType.Float);
        controller.AddParameter("Jump", AnimatorControllerParameterType.Trigger);

        AnimatorStateMachine sm = controller.layers[0].stateMachine;
        AnimatorState locomotion = sm.AddState("Locomotion");   // assign a clip or blend tree as its motion
        AnimatorState jump = sm.AddState("Jump");
        sm.defaultState = locomotion;

        AnimatorStateTransition toJump = locomotion.AddTransition(jump);
        toJump.hasExitTime = false;   // react to the trigger at once
        toJump.duration = 0.1f;
        toJump.AddCondition(AnimatorConditionMode.If, 0f, "Jump");

        AnimatorStateTransition back = jump.AddTransition(locomotion);
        back.hasExitTime = true;      // return when the jump clip nearly ends
        back.exitTime = 0.9f;

        AssetDatabase.SaveAssets();
    }
}
```

## Verify

- **No Editor needed:** grep the `.controller` for `m_AnimatorParameters` and the state
  names, and compare them with every string or `StringToHash` argument in the scripts. A typo
  does nothing at runtime, so this catches the most common bug for free.
- **Unity CLI with a ready Editor:** `unity command animation.animator get_controller` reads a
  controller's full structure (find its flags with `--help`). In Play mode, read live state:
  `unity command script eval --code 'var a = GameObject.Find("Player").GetComponent<Animator>(); return a.GetCurrentAnimatorStateInfo(0).IsName("Locomotion") + " speed=" + a.GetFloat("Speed");'`
- **No CLI:** a PlayMode test can instantiate the character prefab, set a parameter, wait a
  few frames and assert `GetCurrentAnimatorStateInfo(0).IsName(...)`; see
  `unity-csharp-scripting` for the test setup.
- **Visual quality** (foot sliding, pops): ask the user to watch the Animator window in Play
  mode and report which transition fired and whether the feet slide.

## Gotchas

- **A trigger fires late or "sticks".** A trigger stays set until a transition consumes it.
  If none can consume it now, it fires later at a surprising moment. `ResetTrigger` when the
  moment passes, or use a `Bool` for sustained states.
- **Misspelled parameter names do nothing.** No exception is thrown. Cache hashes and compare
  against the controller YAML (Verify).
- **Transition feels laggy.** `Has Exit Time` waits for the clip to reach its exit time.
  Turn it off for condition-driven transitions (jump, hit).
- **Character slides or will not move.** `Apply Root Motion` is on while code also moves the
  Transform, or the other way round. Choose root motion or scripted movement per character.
- **Upper-body layer overrides the whole body.** Assign an Avatar Mask, pick Override or
  Additive, and set the layer weight.
- **`CrossFade` takes far longer than expected.** Its duration is normalized to the state's
  length. `CrossFadeInFixedTime` takes seconds.
- **IK does nothing.** IK only applies inside `OnAnimatorIK`, needs IK Pass on the layer, and
  needs a Humanoid Avatar.
- **A re-enabled character restarts its animation.** Deactivating the GameObject resets
  its Animator; on re-enable it starts again in the default state with default parameters.
  Set `animator.keepAnimatorStateOnDisable = true` when that is not wanted, or reset the
  parameters yourself when you take the object from the pool.

## References

- Read `references/blend-trees-and-ik.md` when setting up 1D or 2D blend trees, layers with
  Avatar Masks, humanoid IK (`OnAnimatorIK`, look-at, foot IK), or additive reference poses.

## Related skills

- `unity-csharp-scripting`: the MonoBehaviour and coroutine timing used above, and tests.
- `unity-physics`: moving the body that the animation shows.
- `game-ai`: deciding when to play which state.

## Version notes

Last verified: 2026-11-11, against Unity 6000.3.28f1.

- `AnimatorControllerParameterType` values (Float 1, Int 3, Bool 4, Trigger 9) and the editor
  API in pattern 3 (`CreateAnimatorControllerAtPath`, `AddParameter`, `AddState`,
  `AddTransition`, `AddCondition`, `hasExitTime`, `exitTime`, `duration`), the model `.meta`
  `animationType` values (Human is 3) and `Animator.keepAnimatorStateOnDisable` were checked in the
  Unity C# reference source at tag 6000.3.28f1 (`Modules/Animation/ScriptBindings/`,
  `Editor/Mono/Animation/`, `Editor/Mono/StateMachine.bindings.cs`).
- `animation.animator get_controller` is a `com.unity.pipeline` 1.0.0-pre.1 command
  (pre-release): https://docs.unity3d.com/Packages/com.unity.pipeline@1.0/manual/index.html
- Manual: https://docs.unity.com/en-us/engine/6000.3/manual and Scripting API `Animator`.
