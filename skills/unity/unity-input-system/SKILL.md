---
name: unity-input-system
description: >
  Wire player input in Unity 6.3 LTS with the Input System package: Input Actions, action maps,
  the PlayerInput component, and reading values via callbacks or polling. Use when the
  project has a .inputactions asset or com.unity.inputsystem, or when the user mentions the
  Unity Input System, InputAction, action maps, PlayerInput, control schemes, or rebinding.
---

# Unity Input System (new)

Read input through Unity's **Input System package** (`com.unity.inputsystem` 1.x; Unity 6.3 LTS
ships 1.20) — action-based, device-agnostic, rebindable. Targets **Unity 6.3 LTS**. This is the modern
replacement for the legacy `Input.GetAxis`/`Input.GetKey` Input Manager.

## When to use

- Use when setting up movement/jump/fire input, defining an `.inputactions` asset with
  action maps and control schemes, wiring a `PlayerInput` component, reading a `Vector2`
  stick/WASD value, or handling gamepad + keyboard + touch from one set of actions.
- Use when `Packages/manifest.json` contains `com.unity.inputsystem` or the project has an
  `*.inputactions` asset.

**When *not* to use:** rebindable-control *architecture* across engines → `input-systems`
(this skill is the Unity-specific API). Moving the character once you have the input vector
→ `unity-physics` / `unity-csharp-scripting`.

## Core workflow

1. **Check Active Input Handling** (Project Settings → Player). The package only receives
   input when this is `Input System Package (New)` or `Both`. `Both` is required if any old
   `Input.GetAxis` code remains.
2. **Find or create the `.inputactions` asset.** New Unity 6 projects usually already have one
   assigned as the **project-wide actions** (Project Settings → Input System Package; the
   template file is `InputSystem_Actions.inputactions`) — reuse it rather than adding a
   second asset. Add an *action map* (e.g. `Gameplay`), add *actions*
   (`Move` = Value/Vector2, `Jump` = Button, `Fire` = Button), and bind them to controls and
   composite bindings (WASD = 2D Vector composite).
3. **Choose how to read it:**
   - **`PlayerInput` component** (designer-friendly) — drop it on the player, point it at the
     asset, pick a *Behavior* (Send Messages / Broadcast / Invoke Unity Events / Invoke C#
     Events). Best for single/local-coop players.
   - **Project-wide actions in code** (`InputSystem.actions.FindAction("Move")`) — no asset
     reference to wire up, and the actions are already enabled.
   - **Direct in code** (`InputActionReference` / `InputActionAsset`) — most control; you
     `Enable()` actions and read them. Best for systems and tools.
4. **Enable the actions/maps you read.** `PlayerInput` enables its default map automatically
   and project-wide actions start enabled; actions from any other asset must be `.Enable()`d
   (and disabled on teardown).
5. **Switch action maps** for context (gameplay ↔ UI/menu) instead of guarding every handler.
6. **Verify** with the Input Debugger (Window → Analysis → Input Debugger) to confirm devices
   and that actions fire.

## Patterns

### 1. `PlayerInput` with "Send Messages" (handlers on the same GameObject)

```csharp
using UnityEngine;
using UnityEngine.InputSystem;

// PlayerInput (Behavior = Send Messages) calls On<ActionName>(InputValue) by name.
public class PlayerInputReceiver : MonoBehaviour
{
    private Vector2 _move;

    private void OnMove(InputValue value) => _move = value.Get<Vector2>();   // Move action
    private void OnJump(InputValue value) { if (value.isPressed) Jump(); }   // Button action

    private void Update() { /* drive movement from _move */ }
    private void Jump() { }
}
```

### 2. Reading an action directly in code (polling a value)

```csharp
using UnityEngine;
using UnityEngine.InputSystem;

public class DirectMover : MonoBehaviour
{
    [SerializeField] private InputActionReference moveAction;  // assign the Move action

    private void OnEnable()  => moveAction.action.Enable();    // REQUIRED or it reads zero
    private void OnDisable() => moveAction.action.Disable();

    private void Update()
    {
        Vector2 move = moveAction.action.ReadValue<Vector2>(); // continuous value
        transform.Translate(new Vector3(move.x, 0, move.y) * (5f * Time.deltaTime));
    }
}
```

### 3. Project-wide actions (no asset reference)

```csharp
using UnityEngine;
using UnityEngine.InputSystem;

public class ProjectWideMover : MonoBehaviour
{
    private InputAction _move, _jump;

    private void Awake()
    {
        // Looked up once; project-wide actions are preloaded and enabled by default.
        _move = InputSystem.actions.FindAction("Move");
        _jump = InputSystem.actions.FindAction("Jump");
    }

    private void Update()
    {
        Vector2 move = _move.ReadValue<Vector2>();
        if (_jump.WasPressedThisFrame()) { /* jump */ }
    }
}
```

### 4. Event callbacks + switching action maps (gameplay ↔ UI)

```csharp
[SerializeField] private InputActionAsset actions;

private void OnEnable()
{
    actions.FindAction("Gameplay/Fire").performed += OnFire;  // edge event: fires once
    actions.FindActionMap("Gameplay").Enable();
}
private void OnDisable() => actions.FindAction("Gameplay/Fire").performed -= OnFire;

private void OnFire(InputAction.CallbackContext ctx) => Shoot();  // ctx.ReadValue<T>() if needed

private void OpenPauseMenu()                       // change context, don't sprinkle if-checks
{
    actions.FindActionMap("Gameplay").Disable();
    actions.FindActionMap("UI").Enable();
}
private void Shoot() { }
```

## Pitfalls

- **No input at all** → either Active Input Handling is still `Input Manager (Old)`, or you
  forgot to `Enable()` the action/map. `PlayerInput` and project-wide actions start enabled;
  actions from other assets do not.
- **Gameplay actions fire while a menu is open** → project-wide actions enable *every* action
  map at startup, including when `PlayerInput` uses that asset. In `Start`, disable the maps
  you do not want (`InputSystem.actions.FindActionMap("UI").Disable()`) and enable only the
  current one.
- **`FindAction` returns null** → the name (or `Map/Action` path) does not exist in that
  asset. Check the spelling in the Actions Editor; with project-wide actions, make sure the
  asset you edited is the one assigned in Project Settings → Input System Package.
- **`InvalidOperationException` about the old input backend** → some script still calls
  `Input.GetAxis`/`Input.GetKey` while Active Input Handling is `New`. Port it or set `Both`.
- **Buttons read as 0 with `ReadValue`** → button *presses* are edge events; use the
  `performed` callback (or `WasPressedThisFrame()`), not per-frame `ReadValue` for triggers.
- **`Send Messages` handlers never fire** → the receiving script must be on the *same*
  GameObject as the `PlayerInput`; `Broadcast Messages` reaches children too.
- **Leaking subscriptions** → unsubscribe (`-=`) in `OnDisable`; re-subscribing in `OnEnable`
  without unsubscribing doubles up handlers.
- **Touch/gamepad not detected** → enable the matching control scheme and confirm the device
  in the Input Debugger; the Vector2 composite needs all four bindings set.

## References

- For interactive control **rebinding** (`PerformInteractiveRebinding`), saving/loading
  bindings as JSON, and **local multiplayer** with `PlayerInputManager`, read
  `references/rebinding.md`.
- Primary docs: Unity Manual "Input System"
  (`https://docs.unity.com/en-us/engine/6000.3/manual/packages-list/packages-all/pack-safe/com-unity-inputsystem`) and the package manual
  (`https://docs.unity3d.com/Packages/com.unity.inputsystem@1.20/manual/index.html`),
  including "About project-wide actions".

## Related skills

- `input-systems` — engine-agnostic input architecture (rebinding, buffering, multi-device).
- `unity-csharp-scripting` — the MonoBehaviour these handlers live in.
- `unity-physics` — applying the input vector to a Rigidbody.
