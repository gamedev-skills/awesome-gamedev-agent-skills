---
name: unity-csharp-scripting
description: >
  Writes and fixes Unity 6.3 LTS C# gameplay scripts: MonoBehaviour lifecycle, serialization,
  .meta/GUID discipline and command-line tests. Use for new or renamed .cs files, "Missing script"
  or a field missing from the Inspector. Not for physics (`unity-physics`), input
  (`unity-input-system`), data assets (`unity-scriptableobjects`) or builds
  (`unity-build-pipeline`).
---

# Unity C# Scripting (MonoBehaviour)

Write correct gameplay scripts for Unity 6.3 LTS (6000.3), C# 9 on .NET Standard 2.1, keep the
project's `.meta` files intact, and prove the result compiles and behaves without opening the
Editor by hand.

## When to use

- Authoring or fixing a `MonoBehaviour`: lifecycle callbacks, component references,
  serialized fields, coroutines, `async` with `Awaitable`.
- Creating, moving, renaming or deleting scripts and assets from the file system.
- Compiling or testing a Unity project from a terminal or CI, for any Unity skill.
- The project has `Assets/`, `ProjectSettings/` and `*.cs` files.

**When not to use:** rigidbodies and collision response → `unity-physics`; reading player
input → `unity-input-system`; shared data assets and config → `unity-scriptableobjects`;
Animator parameters → `unity-animation`; building players → `unity-build-pipeline`.

## Workflow

1. **Read the project's versions first.** `ProjectSettings/ProjectVersion.txt` gives the
   Editor version; `Packages/manifest.json` the packages; any `*.asmdef` files tell you which
   assembly a new script lands in. Keep the project's version unless asked to upgrade.
2. **Pick the callback by purpose.** `Awake` caches references to its own components;
   `OnEnable`/`OnDisable` subscribe and unsubscribe; `Start` wires things that depend on other
   objects' `Awake`; `FixedUpdate` is physics; `LateUpdate` follows movement (cameras).
3. **Expose tunables with `[SerializeField] private`** so designers can edit them and other
   code cannot. A plain class needs `[System.Serializable]` to show up.
4. **Move every file with its `.meta`.** A `.meta` holds the asset's GUID; a new `.meta` means
   a new GUID and every reference to the old one shows "Missing script". A brand-new file needs
   no `.meta`: Unity writes one on the next import. Keep each `MonoBehaviour` or
   `ScriptableObject` class in a file of the same name.
5. **Run the checker:** `python scripts/check_unity_project.py <project-dir>` (`--json` for
   machine-readable output). Fix every `ERROR` (duplicate or malformed GUIDs, files moved
   without their `.meta`, missing script references) and re-run until it exits 0. Run it from
   this skill's directory or resolve the installed path first; it needs Python 3.10+ only,
   reads text-serialized assets and never writes. `--help` lists the checks and exit codes.
6. **Compile.** With the Unity CLI and a ready Editor, `unity recompile --project-path
   <project>`; otherwise a batch-mode import and `grep -E "error CS[0-9]{4}"` on its log.
7. **Prove the behavior** with an EditMode or PlayMode test, or by reading the value back from
   the running Editor with `unity command script eval`. Read
   `references/agent-checks.md` for the exact commands, the test `.asmdef` and how to read the
   results. Report which checks ran and which could not.

## Patterns

### 1. Serialized fields that survive refactors

```csharp
using UnityEngine;
using UnityEngine.Serialization;

public class Turret : MonoBehaviour
{
    [SerializeField, Range(0.1f, 5f)] private float fireInterval = 0.5f;

    // Renamed from "range": without this attribute every scene and prefab loses the value.
    [FormerlySerializedAs("range")]
    [SerializeField] private float maxRange = 12f;

    [System.Serializable]
    public class Stats { public int hp = 100; public int armor = 0; }

    [SerializeField] private Stats stats = new();
}
```

### 2. A coroutine you can stop exactly

```csharp
private Coroutine _spawnLoop;

private void OnEnable()  => _spawnLoop = StartCoroutine(SpawnLoop());
private void OnDisable() { if (_spawnLoop != null) StopCoroutine(_spawnLoop); }

private System.Collections.IEnumerator SpawnLoop()
{
    var wait = new WaitForSeconds(1f);   // allocate once, reuse
    while (true) { Spawn(); yield return wait; }
}

private void Spawn() { }
```

For `async`/`await` with `Awaitable`, the full execution order and custom yield
instructions, read `references/lifecycle-and-coroutines.md`.

## Gotchas

- **`?.` and `??` on a destroyed object.** Unity overrides `==` so a destroyed object equals
  `null`, but `?.`, `??` and `is null` skip that override and see a live reference. Use
  `if (target)` or `target == null` for anything derived from `UnityEngine.Object`.
- **Renaming a serialized field wipes its saved values.** Add `[FormerlySerializedAs("old")]`
  (namespace `UnityEngine.Serialization`) when you rename.
- **"Missing script" after a refactor.** The `.meta` stayed behind, was regenerated, or the
  class name no longer matches the file name. The checker reports all three.
- **Physics in `Update`.** Forces or `MovePosition` outside `FixedUpdate` jitter and depend on
  frame rate. Read input in `Update`, apply it in `FixedUpdate`.
- **Order between objects.** All `Awake` calls finish before any `Start`, but the order among
  `Awake`s (and among `Start`s) is undefined unless Script Execution Order is set. Do
  cross-object wiring in `Start`.
- **Coroutines stop when the GameObject is deactivated.** `SetActive(false)` kills them;
  setting only the component's `enabled = false` does not. Restart in `OnEnable` if needed.
- **An `async` method keeps running after its object is destroyed.** Pass
  `destroyCancellationToken` to `Awaitable` waits (they then throw
  `OperationCanceledException`), and await each `Awaitable` instance only once: they are
  pooled.
- **Obsolete warnings on `FindObjectOfType`/`FindObjectsOfType`.** Use `FindAnyObjectByType`
  or `FindObjectsByType(FindObjectsSortMode.None)` on 6.3. From 6.4, `FindFirstObjectByType`
  and the `FindObjectsSortMode` overload are obsolete too: use `FindAnyObjectByType` and
  `FindObjectsByType<T>()`. All of them scan the scene; cache the result.
- **Repeated `GetComponent` in hot paths.** Cache stable references in `Awake`, and profile
  before treating an occasional lookup as the bottleneck.
- **The first `Update` can run in the same frame as `Start`.** Guard fields that other objects
  set later.

## References

- Read `references/agent-checks.md` before compiling or testing a project from the command
  line: Unity CLI commands, batch-mode commands, test assembly files, log locations and how to
  read NUnit results.
- Read `references/lifecycle-and-coroutines.md` when ordering matters across callbacks, or
  for coroutine yield instructions, `CustomYieldInstruction` and the `Awaitable` equivalents
  of coroutine waits.
- `scripts/check_unity_project.py`: run it (step 5); treat it as a black box and use `--help`
  instead of reading the source.

## Related skills

- `unity-physics`: `Rigidbody`, collisions and `FixedUpdate` motion.
- `unity-input-system`: reading player input into these scripts.
- `unity-scriptableobjects`: sharing data between scripts without singletons.

## Version notes

Last verified: 2026-11-11, against Unity 6000.3.28f1.

- `FindObjectsOfType` is obsolete in 6.3; `FindFirstObjectByType` and
  `FindObjectsByType(FindObjectsSortMode)` become obsolete in 6.4. Source: Unity C# reference
  source, `Runtime/Export/Scripting/UnityEngineObject.bindings.cs` at tags 6000.3.28f1 and
  6000.4.12f1 (https://github.com/Unity-Technologies/UnityCsReference).
- `?.`/`??` caveat: Scripting API `Object` page
  (https://docs.unity.com/en-us/engine/6000.3/script-reference/unityengine/object).
- Event order: https://docs.unity.com/en-us/engine/6000.3/manual/scripting/managing-update-order/execution-order
- Unity CLI 1.0.0-beta.17 and `com.unity.pipeline` 1.0.0-pre.1 are pre-release. Exit codes:
  https://docs.unity.com/en-us/unity-cli/reference/output-formats. Commands:
  https://docs.unity3d.com/Packages/com.unity.pipeline@1.0/manual/index.html
- Test runner command line (`-runTests` does not support `-quit`):
  https://docs.unity.com/en-us/engine/6000.3/manual/programming-environment/test-framework-introduction/reference-command-line
