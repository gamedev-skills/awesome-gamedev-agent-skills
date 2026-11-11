---
name: unity-build-pipeline
description: >
  Builds and ships Unity 6.3 LTS players: Build Profiles, IL2CPP vs Mono, managed stripping with
  link.xml, scripted BuildPlayer, Addressables and CI or headless builds. Use when automating a
  Unity build or MissingMethodException appears only in the player. Not for a build that is too
  big (`unity-build-size`) or store uploads (`steam-publish`, `itch-publish`).
---

# Unity Build Pipeline

Configure, script, and automate Unity 6.3 LTS player builds: scenes, platform target, scripting
backend, stripping, and headless/CI builds. Targets **Unity 6.3 LTS (6000.3)**.

## When to use

- Use when setting up Build Settings/Profiles, choosing a platform and scripting backend
  (Mono vs IL2CPP), reducing build size with managed stripping, scripting a repeatable build
  with `BuildPipeline.BuildPlayer`, or wiring a CI/headless build.
- Use when the project has `ProjectSettings/EditorBuildSettings.asset` or a CI build script.

**When *not* to use:** authoring a CI service config end-to-end is DevOps; this skill covers
the Unity-side build API and settings. Console/platform certification specifics are
platform-NDA territory. Storefront submission → `steam-publish` / `itch-publish`. A build, APK
or Web build that is too large (assets, compression, per-platform size settings) →
`unity-build-size`, which sends stripping work back here.

## Core workflow

1. **List the scenes to build** (File → Build Profiles → Scene List, or
   `EditorBuildSettings.scenes`). Only listed, enabled scenes ship; scene 0 is the start scene.
   A Build Profile asset can carry its own Scene List (Add Settings → Scene List); when it
   does, that profile builds its list, not the global one.
2. **Pick the platform target** and switch the active build target if needed
   (`BuildTarget` / `EditorUserBuildSettings`). In batch mode, pass `-buildTarget <name>` on
   the command line instead: `SwitchActiveBuildTarget` is not available there.
3. **Choose the scripting backend** (Player Settings): **Mono** (fast iteration, desktop) vs
   **IL2CPP** (AOT C++; required for many platforms, better perf, harder to reverse). IL2CPP
   needs the platform's C++ toolchain installed. (Forward note: Unity is developing a
   **CoreCLR** backend as a modern .NET runtime successor to Mono, but in the Unity 6.7 beta
   it is still *experimental*, desktop-only, and documented as not suitable for production —
   so for 6.3 LTS the choice stays Mono vs IL2CPP.)
4. **Tune size/perf:** set Managed Stripping Level (Disabled → Minimal → Low → Medium → High)
   and protect reflection-only code with a `link.xml`. Set Quality Settings per platform.
5. **Script the build** with `BuildPipeline.BuildPlayer(BuildPlayerOptions)` and **inspect the
   returned `BuildReport`** — a non-`Succeeded` result must fail your pipeline.
6. **Run headless** for CI with `-batchmode -quit -executeMethod`, and check the exit code.
7. **Verify** the actual output runs (launch the player), not just that the build returned
   without throwing.

## Patterns

### 1. Scripted build with a result check

```csharp
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEngine;

public static class BuildScript
{
    [MenuItem("Build/Windows x64")]
    public static void BuildWindows()
    {
        var options = new BuildPlayerOptions
        {
            scenes = new[] { "Assets/Scenes/Main.unity", "Assets/Scenes/Level1.unity" },
            locationPathName = "Builds/Windows/Game.exe",
            target = BuildTarget.StandaloneWindows64,
            options = BuildOptions.None,            // add BuildOptions.Development for a dev build
        };

        BuildReport report = BuildPipeline.BuildPlayer(options);
        BuildSummary summary = report.summary;

        if (summary.result != BuildResult.Succeeded)
            throw new System.Exception($"Build failed: {summary.totalErrors} errors");
        Debug.Log($"Build OK: {summary.totalSize} bytes in {summary.totalTime}");
    }
}
```

### 2. Headless / CI invocation

```bash
# Exit code is 0 on success; -quit ensures the editor closes; -nographics for build servers.
# -buildTarget makes the Editor start on that platform, so scripts compile with its defines.
Unity -batchmode -quit -nographics \
  -projectPath "/path/to/Project" \
  -buildTarget win64 \
  -executeMethod BuildScript.BuildWindows \
  -logFile -
```

### 3. Build a saved Build Profile

```csharp
using UnityEditor;
using UnityEditor.Build.Profile;
using UnityEditor.Build.Reporting;

public static class ProfileBuild
{
    [MenuItem("Build/Windows Release Profile")]
    public static void Build()
    {
        var profile = AssetDatabase.LoadAssetAtPath<BuildProfile>(
            "Assets/Settings/Build Profiles/WindowsRelease.asset");
        var options = new BuildPlayerWithProfileOptions
        {
            buildProfile = profile,                 // platform, scene list, defines from the asset
            locationPathName = "Builds/Windows/Game.exe",
            options = BuildOptions.None,
        };
        BuildReport report = BuildPipeline.BuildPlayer(options);
        if (report.summary.result != BuildResult.Succeeded)
            throw new System.Exception($"Build failed: {report.summary.totalErrors} errors");
    }
}
```

### 4. Protect stripped code with `link.xml`

```xml
<!-- Assets/link.xml — keep types the linker can't see are used (reflection, JSON, plugins). -->
<linker>
  <assembly fullname="MyGameRuntime" preserve="all"/>
</linker>
```

## Gotchas

- **A scene loads in the Editor but is missing in the build** — it isn't in the scene list
  (File → Build Profiles → Scene List, or the built profile's own list) or is disabled.
  `SceneManager.LoadScene` only sees listed scenes.
- **IL2CPP build fails on a fresh machine** — the platform C++ toolchain (e.g. Windows build
  tools, Android NDK) isn't installed. Mono has no such requirement.
- **`MissingMethodException`/`TypeLoadException` only in the build** — managed stripping removed
  reflection-only code. Lower the stripping level or add a `link.xml` preserve entry.
- **Treating "BuildPlayer returned" as success** — always check `BuildReport.summary.result`;
  it can return with errors.
- **Addressables content is stale/missing** — Addressables (`com.unity.addressables`) content
  is built by Build → Addressables or by `AddressableAssetSettings.BuildPlayerContent`. The
  **Build Addressables on Player Build** setting can do it during a player build, but when it
  is left at "Use global Settings" the result depends on each machine's Preferences — call the
  content build explicitly in CI, and check the profile's load path.
- **The build platform's code didn't compile in** — a scripted `BuildPlayer` for a target
  other than the active one keeps the active platform's `UNITY_*` defines, and define changes
  only apply after a domain reload. Switch platform first (in the Editor) or launch with
  `-buildTarget` (batch mode).
- **Build ignores scenes you added to the global list** — the Build Profile you build has its
  own Scene List. Edit that list; a profile without a Scene List uses the global one.
- **Shipping a Development build** — `BuildOptions.Development` enables the profiler/debugging
  and is slower; use `BuildOptions.None` for release.

## References

- For a complete **multi-platform CI build script** (`-buildTarget` per platform, version
  stamping, argument parsing, exit codes), building a Build Profile from the command line, and
  an Addressables content-build call, read `references/ci-build-script.md`.
- Primary docs: `ScriptReference/BuildPipeline.BuildPlayer`, `ScriptReference/BuildPlayerWithProfileOptions`,
  the Manual pages "Editor command line arguments" and "Manage scenes in a build", and Unity
  Manual build sections (player settings, managed code stripping). For the forward-looking
  CoreCLR backend, see the experimental note at
  `https://docs.unity.com/en-us/engine/6000.7/manual/programming-environment/scripting-backends/coreclr`.

## Related skills

- `steam-publish` / `itch-publish` — distributing the player you just built.
- `unity-csharp-scripting` — editor scripting conventions used by build scripts.
- `unity-build-size` — finding and shrinking what makes a build, APK or Web build large.
