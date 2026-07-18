---
name: unity-scriptableobjects
description: >
  Architect Unity 6 data and decoupling with ScriptableObjects: config/data assets, shared
  runtime variables, event channels, and runtime sets/registries. Use when designing
  data-driven systems, replacing singletons/managers, creating .asset data with
  CreateAssetMenu, or when the user mentions ScriptableObject, SO architecture, or data assets.
license: Apache-2.0
compatibility: Unity 6 (6000.0 LTS); UnityEngine.ScriptableObject
metadata:
  engine: unity
  category: unity
  difficulty: intermediate
---

# Unity ScriptableObject Architecture

Use `ScriptableObject` assets to store shared data and decouple systems in Unity 6 —
configuration, event channels, and registries that live as project assets instead of being
hard-wired into scenes or singletons. Targets **Unity 6 (6000.0 LTS)**.

## When to use

- Use when you need designer-editable config (weapon stats, level data), to share one value
  between unrelated systems, to decouple senders from listeners via event channels, or to
  build a runtime registry of active objects — without a `static`/singleton manager.
- Use when the project has `*.asset` data files backed by `: ScriptableObject` classes.

**When _not_ to use:** per-instance runtime state that differs per GameObject (that belongs on
a MonoBehaviour) — a ScriptableObject asset is _shared_ by everyone who references it. Saving
player progress to disk → `save-systems`. Plain DTOs that never need to be an asset can just be
`[System.Serializable]` classes.

## Core workflow

1. **Define the class** deriving from `ScriptableObject` and tag it with `[CreateAssetMenu]` so
   designers can create instances from the Assets menu.
2. **Create one or more `.asset` instances** in the Project window; each is a shared, named
   piece of data referenced by `[SerializeField]` fields.
3. **Reference, don't copy.** MonoBehaviours hold a reference to the asset; they all see the
   same data, so changing the asset changes every consumer.
4. **For decoupling**, model _signals_ and _shared variables_ as ScriptableObjects: a
   "FloatVariable" the HUD reads and the player writes; an "event channel" the player raises
   and many systems listen to. Neither side references the other.
5. **Reset runtime mutations** in `OnEnable` if the asset is mutated during play, because edits
   made in the Editor at runtime persist on the asset (a frequent source of "my values
   changed after I played").
6. **Verify** by inspecting the asset values during Play mode and confirming consumers react.

## Patterns

### 1. Config/data asset

```csharp
using UnityEngine;

[CreateAssetMenu(fileName = "WeaponData", menuName = "Game/Weapon Data", order = 0)]
public class WeaponData : ScriptableObject
{
    public string displayName = "Pistol";
    public int    damage = 10;
    public float  fireRate = 0.25f;
    public GameObject projectilePrefab;
}
```

```csharp
public class Weapon : MonoBehaviour
{
    [SerializeField] private WeaponData data;   // assign the shared asset in the Inspector
    private void Fire() => Debug.Log($"{data.displayName} for {data.damage}");
}
```

### 2. Shared runtime variable (decouples producer from consumer)

```csharp
[CreateAssetMenu(menuName = "Game/Float Variable")]
public class FloatVariable : ScriptableObject
{
    [SerializeField] private float initialValue;
    [System.NonSerialized] public float runtimeValue;   // not saved to the asset

    private void OnEnable() => runtimeValue = initialValue;  // reset each play session
}
// Player writes playerHealth.runtimeValue; the HUD reads it — neither references the other.
```

### 3. Creating an instance at runtime (not an asset on disk)

```csharp
// For transient SO data you build in code (e.g. a generated config).
var temp = ScriptableObject.CreateInstance<WeaponData>();
temp.damage = 25;
// ...use temp...  Destroy(temp);   // clean up runtime-created instances
```

## Pitfalls

- **Editing an SO at runtime persists in the Editor** — values you change during Play stay
  changed on the asset after you stop. Keep mutable runtime state in `[NonSerialized]` fields
  reset in `OnEnable`, or it will surprise you. (In a _build_, asset edits do not persist
  across launches.)
- **Disabled Domain Reload skips your `OnEnable` reset** — with **Enter Play Mode Options**
  enabled and **Reload Domain** off (a Unity 6 fast-iteration setting), already-loaded SOs are
  _not_ re-created when you press Play, so `OnEnable` never fires and `runtimeValue` keeps its
  value from the previous session. Reset explicitly from an `ISerializationCallbackReceiver` or
  a scene-load hook instead of relying on `OnEnable` alone.
- **Expecting per-object state** — every reference points to the _same_ asset. If two enemies
  need different current HP, store HP on the MonoBehaviour, not the shared SO.
- **No frame lifecycle** — ScriptableObjects have `OnEnable`/`OnDisable`/`OnDestroy` but no
  `Update`. Don't expect per-frame callbacks.
- **Using SOs as a save file** — they're authoring assets, not runtime persistence; write
  progress with `save-systems` instead.
- **Leaking `CreateInstance` objects** — runtime-created instances are not garbage-collected
  like plain C# objects; `Destroy` them when done.

## References

- For the **event-channel** pattern (a `GameEvent` SO + listeners, type-safe payloads) and
  **runtime sets/registries** (a shared list of active enemies), read
  `references/event-channels.md`.
- Primary docs: Unity Manual "ScriptableObject" (`/Manual/class-ScriptableObject.html`) and
  `ScriptReference/ScriptableObject`, `ScriptReference/CreateAssetMenuAttribute`.

## Related skills

- `unity-csharp-scripting` — the MonoBehaviours that consume these assets.
- `save-systems` — persisting state to disk (what SOs are _not_ for).
- `card-game` / `rpg` / `survival-crafting` — genres that lean on SO-driven data.
