# CI / headless build script (Unity 6.3 LTS)

Depth for `unity-build-pipeline`: a reusable editor build script that takes command-line
arguments, stamps a version, and returns a proper exit code. Verified against
`ScriptReference/BuildPipeline.BuildPlayer`, `ScriptReference/EditorUserBuildSettings.SwitchActiveBuildTarget`
and the 6000.3 Manual page "Editor command line arguments".

**Pick the platform with Unity's own `-buildTarget` flag, not from inside the script.**
`EditorUserBuildSettings.SwitchActiveBuildTarget` is not available in batch mode: a platform
switch needs a script recompile, which cannot happen while your `-executeMethod` code runs.
`-buildTarget` makes the Editor start on that platform, so scripts compile with the right
`UNITY_*` defines before your method is called. Its values are lowercase names such as
`win64`, `osxuniversal`, `linux64`, `android`, `ios` and `webgl`.

## A parameterised build method

```csharp
using System;
using System.Linq;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEngine;

public static class CIBuild
{
    // Invoke with: -buildTarget win64 -executeMethod CIBuild.Run -out Builds/Game.exe -appVersion 1.2.3
    public static void Run()
    {
        string[] args = Environment.GetCommandLineArgs();

        if (!HasArg(args, "-buildTarget"))
        {
            // Without it the build silently uses whatever platform the project was last on.
            Debug.LogError("[CIBuild] pass -buildTarget <name> so the Editor starts on that platform");
            EditorApplication.Exit(2);
            return;
        }

        string outPath = ArgValue(args, "-out", "Builds/Game.exe");
        string version = ArgValue(args, "-appVersion", PlayerSettings.bundleVersion);
        bool   dev     = HasArg(args, "-dev");

        // Already switched by -buildTarget at startup, with matching script defines.
        BuildTarget target = EditorUserBuildSettings.activeBuildTarget;

        PlayerSettings.bundleVersion = version;   // stamp the version into the player

        var options = new BuildPlayerOptions
        {
            scenes = EnabledScenes(),
            locationPathName = outPath,
            target = target,
            options = dev ? BuildOptions.Development : BuildOptions.None,
        };

        BuildReport report = BuildPipeline.BuildPlayer(options);
        BuildSummary s = report.summary;

        if (s.result == BuildResult.Succeeded)
        {
            Debug.Log($"[CIBuild] OK {target} {version} -> {outPath} ({s.totalSize} bytes)");
            EditorApplication.Exit(0);            // explicit success exit code for CI
        }
        else
        {
            Debug.LogError($"[CIBuild] FAILED: {s.totalErrors} errors, result={s.result}");
            EditorApplication.Exit(1);            // non-zero fails the pipeline
        }
    }

    private static string[] EnabledScenes() =>
        EditorBuildSettings.scenes.Where(sc => sc.enabled).Select(sc => sc.path).ToArray();

    private static int IndexOf(string[] args, string key) =>
        Array.FindIndex(args, a => string.Equals(a, key, StringComparison.OrdinalIgnoreCase));

    private static bool HasArg(string[] args, string key) => IndexOf(args, key) >= 0;

    private static string ArgValue(string[] args, string key, string fallback)
    {
        int i = IndexOf(args, key);
        return (i >= 0 && i + 1 < args.Length) ? args[i + 1] : fallback;
    }
}
```

## Invoking from CI

```bash
# No -quit needed: the method ends the process itself with EditorApplication.Exit.
Unity -batchmode -nographics \
  -projectPath "$CI_PROJECT_DIR" \
  -buildTarget win64 \
  -executeMethod CIBuild.Run \
  -out "Builds/Win/Game.exe" -appVersion "1.2.$BUILD_NUMBER" \
  -logFile - || exit 1
```

- Pipe `-logFile -` to stdout so the CI captures the Unity log.
- `EditorApplication.Exit(code)` inside the method is the reliable way to set the exit code;
  an uncaught exception also exits with 1, but `-quit` after a `Debug.LogError` returns 0.
- One platform per Editor launch: run the command again with another `-buildTarget` for the
  next platform instead of switching inside the method.
- Activate the Unity license in a separate step before building on a clean runner, using
  the provisioning flow supported by your license type. Unity's credential flags
  (`-username`/`-password`/`-serial`) can expose values through process arguments or logs;
  do not commit literal credentials or paste them into shell history. Limit activation
  secrets to that step and protect any license files the flow creates.

### Building a saved Build Profile with no script

If the team keeps its platform setup in Build Profile assets, Unity can build one directly:

```bash
Unity -batchmode -nographics -quit \
  -projectPath "$CI_PROJECT_DIR" \
  -activeBuildProfile "Assets/Settings/Build Profiles/WindowsRelease.asset" \
  -build "Builds/Win/Game.exe" \
  -logFile -
```

`-activeBuildProfile` takes a path relative to the project root and adds the profile's
scripting defines before compilation (it does not remove existing ones). Combined with
`-executeMethod` instead of `-build`, the defines are compiled in before your method runs; then
build with `BuildPipeline.BuildPlayer(new BuildPlayerWithProfileOptions { buildProfile = ..., locationPathName = ... })`
so the profile's own scene list and settings are used.

## Addressables content build (when used)

```csharp
using UnityEditor.AddressableAssets.Settings;

// Build the Addressables content bundles BEFORE the player build, or runtime loads fail.
public static void BuildContent()
{
    AddressableAssetSettings.BuildPlayerContent(out var result);
    if (!string.IsNullOrEmpty(result.Error))
        throw new System.Exception($"Addressables build failed: {result.Error}");
}
```

Call it explicitly in CI even if the project's **Build Addressables on Player Build** setting
is on: when that setting is left at "Use global Settings", the answer comes from each
machine's Editor Preferences, so a clean runner may skip the content build.

## Gotchas

- Do not call `EditorUserBuildSettings.SwitchActiveBuildTarget` in batch mode; it is not
  available there. Use `-buildTarget` (or `-activeBuildProfile`) on the command line.
- Reading args via `Environment.GetCommandLineArgs()` includes Unity's own flags. Name custom
  keys so they cannot collide with a real Unity argument (`-buildTarget`, `-build`, `-quit`
  and `-version` are all taken; `-version` prints the Editor version and exits without
  building). `-out`, `-appVersion` and `-dev` are free.
- A build server needs the platform module installed (e.g. IL2CPP toolchain, Android SDK/NDK)
  or the build fails late with a toolchain error.
