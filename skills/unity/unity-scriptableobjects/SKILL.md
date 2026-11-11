---
name: unity-scriptableobjects
description: >
  Unity 6.3 LTS data and decoupling with ScriptableObjects: CreateAssetMenu config assets, shared
  runtime variables, event channels and .asset files made from code. Use for replacing singletons,
  data-driven items or cards, or values that persist after leaving Play mode. Not for saving
  progress (`save-systems`) or Godot Resources (`godot-resources`).
---

# Unity ScriptableObject Architecture

Use `ScriptableObject` assets in Unity 6.3 LTS (6000.3) for shared data and for decoupling
systems: configuration, event channels and registries that live as project assets instead of
scene singletons. An SO asset is a YAML file you can read and check without the Editor.

## When to use

- Designer-editable config (weapon stats, level data), one value shared by unrelated
  systems, senders and listeners that should not reference each other, a live registry of
  active objects without scene scans.
- The project has `*.asset` files backed by `: ScriptableObject` classes.

**When not to use:** state that differs per GameObject belongs on a MonoBehaviour, since an SO
asset is shared by everyone who references it; saving progress → `save-systems`; plain data
that never needs to be an asset can be a `[System.Serializable]` class.

## Workflow

1. **Define the class** deriving from `ScriptableObject`, in a file with the same name, with
   `[CreateAssetMenu]` so designers can create instances.
2. **Create the assets.** Designers use the Assets > Create menu. From code, use an editor
   script (pattern 3) so Unity writes the `.asset` and its `.meta` with a valid GUID. Do not
   hand-write a new `.asset` file: the `m_Script` GUID must match the script's `.meta`.
3. **Reference, do not copy.** MonoBehaviours hold a `[SerializeField]` reference; every
   consumer sees the same data.
4. **Keep mutable runtime state out of serialized fields** (`[System.NonSerialized]`) and
   reset it when Play mode starts (pattern 2), because Play-mode edits to an asset persist in
   the Editor.
5. **Make sure builds include the asset.** Only assets referenced from a scene in the build,
   from another included asset, from a `Resources` folder or from Addressables ship in the
   player.
6. **Verify** with the checks below.

## Patterns

### 1. Config asset

```csharp
using UnityEngine;

[CreateAssetMenu(fileName = "WeaponData", menuName = "Game/Weapon Data")]
public class WeaponData : ScriptableObject
{
    public string displayName = "Pistol";
    public int damage = 10;
    public float fireRate = 0.25f;
    public GameObject projectilePrefab;
}
```

### 2. Shared runtime variable that resets on Play

```csharp
using UnityEngine;

[CreateAssetMenu(menuName = "Game/Float Variable")]
public class FloatVariable : ScriptableObject
{
    [SerializeField] private float initialValue;
    [System.NonSerialized] public float runtimeValue;   // never saved to the asset

    private void OnEnable()
    {
        runtimeValue = initialValue;
#if UNITY_EDITOR
        // With Reload Domain off, OnEnable does not run again on Play, so also reset there.
        UnityEditor.EditorApplication.playModeStateChanged -= ResetOnPlay;
        UnityEditor.EditorApplication.playModeStateChanged += ResetOnPlay;
#endif
    }

#if UNITY_EDITOR
    private void OnDisable() => UnityEditor.EditorApplication.playModeStateChanged -= ResetOnPlay;

    private void ResetOnPlay(UnityEditor.PlayModeStateChange change)
    {
        if (change == UnityEditor.PlayModeStateChange.ExitingEditMode) runtimeValue = initialValue;
    }
#endif
}
```

### 3. Create assets from editor code

Put this in an `Editor` folder. Run it from the menu, from the Unity CLI with
`unity command script eval --code 'WeaponAssets.CreateDefaults();'`, or in batch mode with
`-executeMethod WeaponAssets.CreateDefaults`.

```csharp
using UnityEditor;
using UnityEngine;

public static class WeaponAssets
{
    [MenuItem("Tools/Create Default Weapons")]
    public static void CreateDefaults()
    {
        if (!AssetDatabase.IsValidFolder("Assets/Data"))
            AssetDatabase.CreateFolder("Assets", "Data");

        var pistol = ScriptableObject.CreateInstance<WeaponData>();
        pistol.displayName = "Pistol";
        pistol.damage = 10;
        AssetDatabase.CreateAsset(pistol, "Assets/Data/Pistol.asset");   // writes .asset and .meta
        AssetDatabase.SaveAssets();
    }
}
```

To change an existing asset from editor code, load it with
`AssetDatabase.LoadAssetAtPath<WeaponData>(path)`, set the fields, call
`EditorUtility.SetDirty(asset)` and then `AssetDatabase.SaveAssets()`; without `SetDirty` the
change is lost on the next reload.

## Verify

- **No Editor needed:** an SO asset is YAML. Each `.asset` has a `MonoBehaviour:` document
  with `m_Script: {fileID: 11500000, guid: ..., type: 3}`, `m_Name`, and one line per
  serialized field (`damage: 10`). Grep the values, and run `unity-csharp-scripting`'s
  `check_unity_project.py` to confirm every `m_Script` GUID resolves to a script.
- **Unity CLI with a ready Editor:** read the loaded value back:
  `unity command script eval --code 'return AssetDatabase.LoadAssetAtPath<WeaponData>("Assets/Data/Pistol.asset").damage;'`
- **Tests:** an EditMode test can load the asset with `AssetDatabase.LoadAssetAtPath` and
  assert its values, or exercise an event channel with `ScriptableObject.CreateInstance`
  (setup in `unity-csharp-scripting`).
- **Play-mode reset:** ask the user to enter and leave Play mode twice and report whether the
  values shown on the asset in the Inspector changed.

## Gotchas

- **Values changed after leaving Play mode.** Play-mode edits to an SO asset persist in the
  Editor (not across launches of a build). Keep mutable state in `[NonSerialized]` fields and
  reset it.
- **The `OnEnable` reset stopped working.** With Enter Play Mode Options on and Reload Domain
  off, loaded SOs are not recreated on Play, so `OnEnable` does not run. Also reset on
  `EditorApplication.playModeStateChanged` (pattern 2) or from a static
  `[RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]` method.
- **Renaming a field wipes the data in every asset.** Add
  `[UnityEngine.Serialization.FormerlySerializedAs("oldName")]` when you rename.
- **"The associated script can not be loaded" on an asset.** The class name differs from the
  file name, the script has a compile error, or the script's `.meta` GUID changed.
- **Expecting per-object state.** Two enemies referencing one SO share its values. Keep
  current HP on the MonoBehaviour.
- **Missing in a build, fine in the Editor.** Nothing included in the build references the
  asset, so it was stripped. Reference it from a scene or a referenced asset, or load it
  through `Resources` or Addressables.
- **No `Update`.** SOs get `OnEnable`, `OnDisable`, `OnDestroy` and `OnValidate`, not frame
  callbacks.
- **Leaking `CreateInstance` objects.** Runtime-created instances are Unity objects; `Destroy`
  them when done.

## References

- Read `references/event-channels.md` when adding an event channel (a `GameEvent` SO with
  listeners, typed payloads) or a runtime set that replaces `FindObjectsByType` scans.

## Related skills

- `unity-csharp-scripting`: the MonoBehaviours that use these assets, tests and the `.meta`
  checker.
- `save-systems`: writing progress to disk.
- `card-game`, `rpg`, `survival-crafting`: genres built on SO data.

## Version notes

Last verified: 2026-11-11, against Unity 6000.3.28f1.

- Manual: "ScriptableObject" and "Enter Play mode with domain reload disabled"
  (https://docs.unity.com/en-us/engine/6000.3/manual), Scripting API `ScriptableObject`,
  `CreateAssetMenuAttribute`, `AssetDatabase.CreateAsset`, `EditorUtility.SetDirty`,
  `Serialization.FormerlySerializedAsAttribute`.
- `script eval` is a `com.unity.pipeline` 1.0.0-pre.1 command (pre-release):
  https://docs.unity3d.com/Packages/com.unity.pipeline@1.0/manual/index.html
