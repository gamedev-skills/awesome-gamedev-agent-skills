---
name: unreal-packaging
description: >
  Packages and ships Unreal Engine 5 (UE 5.8) projects: Shipping builds, cooking, pak/IoStore and
  RunUAT BuildCookRun with UAT and cook log reading. Use for a packaged game with a black screen,
  a map missing in the build, "BUILD FAILED" or an AutomationTool exit code. Not for store uploads
  (`steam-publish`, `itch-publish`) or gameplay compile errors (`unreal-cpp-gameplay`).
---

# Unreal Packaging & Cooking

Turn a UE5 project into a build that starts on the right map and runs on a machine without the
editor, and make that build reproducible from a command line. Targets **UE 5.8**.

## When to use

- Producing a test or release build; choosing Development, Test or Shipping; setting the
  launch map and which content gets cooked.
- Scripting builds for CI with `RunUAT BuildCookRun`, or reading why one failed.
- Understanding where cooked and staged output goes, including the Zen store.

**When *not* to use:** store submission and depots → `steam-publish` / `itch-publish`.
Gameplay C++ compile errors → `unreal-cpp-gameplay`. Building the engine from source is out of
scope.

## Workflow

1. **Read the project and engine.** `EngineAssociation` in the `.uproject` is a version such
   as `5.8` for a Launcher engine and a GUID (or empty) for a source build; console platforms
   need a source build. Check that the platform SDK on the build machine meets the engine's
   minimum (see Version notes).
2. **Set what loads and what cooks.** Project Settings → Maps & Modes → **Game Default Map**
   (stored as `GameDefaultMap` in `Config/DefaultEngine.ini`). Maps that are only opened by
   name at runtime must be listed in Packaging → "List of maps to include in a packaged build"
   or cooked with `-map=`; assets loaded only by path need "Additional Asset Directories to
   Cook".
3. **Validate content:** `UnrealEditor-Cmd <Project>.uproject -run=DataValidation -unattended`
   and fix every error before cooking.
4. **Build with UAT** (default), even when the user packages from the editor, because the
   command line is reproducible:

   ```bash
   # From Engine/Build/BatchFiles (RunUAT.bat on Windows, RunUAT.sh on macOS and Linux)
   RunUAT BuildCookRun -project="<abs path>/MyGame.uproject" -noP4 \
     -platform=Win64 -clientconfig=Development \
     -build -cook -stage -pak -archive -archivedirectory="<abs path>/Builds" \
     -utf8output
   ```

   Swap `-clientconfig=Shipping` for release. Cook a subset with `-map=Start+Level01`.
   The editor path (Platforms → Windows → Package Project) and Project Launcher profiles run
   the same steps; a Launcher profile prints its full UAT command line in the Output Log.
5. **Read the logs on failure.** UAT prints the path of its log (`Log.txt`) and of the cook log
   (`Cook-*.txt`). Search them for `Error:`; the first error is usually the cause and the rest
   follow from it. Launcher engines on Windows write them under
   `%APPDATA%\Unreal Engine\AutomationTool\Logs\<engine path>`, source builds under
   `Engine/Programs/AutomationTool/Saved/Logs`.
6. **Run the packaged build (see Verify).** A finished cook proves the content converted, not
   that the game starts.

## Verify

Say which of these you ran and quote the lines that prove it.

1. **UAT result:** the run ends with `BUILD SUCCESSFUL` and exit code 0, and the archive
   directory contains the executable plus `.pak`/`.utoc`/`.ucas` files under
   `<Project>/Content/Paks`.
2. **Smoke-run a Development build** from the archive with a log file:
   `<archive>/Windows/MyGame.exe -log -unattended -windowed -ResX=1280 -ResY=720 -abslog="<dir>/smoke.log"`
   (on a machine without a GPU, add `-nullrhi`). Let it reach the first map, close it, then
   check the log for the expected `LoadMap(/Game/...)` line and for any `Fatal error`, `Error:`
   or missing-asset warnings.
3. **Shipping builds** strip logging, so smoke-test the same content as Development or Test
   first, then ask the user to launch the Shipping build and report whether it reaches the main
   menu and can quit from the game's own menu.
4. **Optional:** if the project has automation tests, run them on the packaged Development
   build or in the editor as in `unreal-cpp-gameplay` before shipping.

## Gotchas

- **Black screen or empty level in the build:** Game Default Map is unset, or that map (or a
  map it opens by name) wasn't cooked.
- **Asset exists in the editor, missing in the build:** nothing hard-references it, so the
  cooker skipped it. Add its directory to cook, or reference it from a cooked asset.
- **`Saved/Cooked/<Platform>` has no `.uasset` files:** in 5.8 Zen Server is the cooked
  output store by default, so that folder holds only a small `ue.projectstore` marker. Ship
  the staged or archived folder, built with `-pak`. Staging to loose files without `-pak`
  produces a build that streams content from your Zen server and is not distributable.
- **Zen server starts and stops on every CI step:** for team and CI machines Epic recommends
  `LimitProcessLifetime=false` under `[Zen.AutoLaunch]` in `DefaultEngine.ini`; make sure the
  build agent tolerates the long-running `zenserver` process.
- **Shipping-only bug with no log:** Shipping strips `UE_LOG` and the console. Reproduce in a
  Test build, which keeps some tooling with Shipping-like optimizations.
- **No way to quit a Shipping build:** the console `quit` command isn't there. The game needs
  its own exit option.
- **Platform SDK errors early in the build:** the installed Visual Studio, Windows SDK or Xcode
  is older than the engine minimum, or a console platform is used with a Launcher engine.
- **First cook takes very long:** shaders and every asset cook from scratch; later cooks are
  incremental. A slow first cook is not a hang; watch the cook log grow.
- **Expecting Blueprint Nativization:** it was removed in UE5. Profile and move hot logic to
  C++ instead.

## References

- Epic docs: [Packaging Your Project](https://dev.epicgames.com/documentation/unreal-engine/packaging-your-project),
  [Build operations: cooking, packaging, deploying](https://dev.epicgames.com/documentation/unreal-engine/build-operations-cooking-packaging-deploying-and-running-projects-in-unreal-engine),
  [Zenserver as Cooked Output Store](https://dev.epicgames.com/documentation/unreal-engine/using-zen-storage-server-as-cooked-output-store-for-unreal-engine),
  [Unreal Automation Tool overview](https://dev.epicgames.com/documentation/unreal-engine/unreal-automation-tool-overview-for-unreal-engine).

## Related skills

- `steam-publish` / `itch-publish`: uploading the archived build.
- `unreal-cpp-gameplay`: compile errors and automation tests.
- `performance-optimization`: profiling the packaged build.

## Version notes

Last verified: 2026-11-11.

- Current release: UE 5.8 (5.8.4 hotfix, October 2026); UE 5.9 is in Preview and adds an
  experimental WebAssembly target with WebGPU rendering.
- UE 5.8 Windows: Visual Studio 2022 17.14 or newer (2026 recommended), MSVC 14.38 minimum
  (14.50 recommended), Windows SDK 10.0.22621.0 minimum (10.0.26100.0 default). macOS:
  Xcode 15.2 minimum (15.4 or newer recommended). Linux: clang 20.1.8. Other platforms: see the
  release notes' Platform SDK Upgrades table.
- UE 5.8 adds experimental Windows on Arm game builds: `-clientarchitecture=arm64`, or
  `arm64+x64` for side-by-side executables. The editor itself does not run on Arm64 in 5.8.
- UE 5.8 makes Zen Server the default cooked output store; projects that had the Zen store
  turned off keep it off.
- Sources: [UE 5.8 release notes](https://dev.epicgames.com/documentation/unreal-engine/unreal-engine-5-8-release-notes),
  [UE 5.9 Preview release notes](https://dev.epicgames.com/documentation/unreal-engine/unreal-engine-5-9-release-notes),
  [5.8.4 hotfix announcement](https://forums.unrealengine.com/t/5-8-4-hotfix-released/2842775).
