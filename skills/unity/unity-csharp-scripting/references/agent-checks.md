# Checking a Unity change without clicking (Unity 6.3 LTS)

Depth for `unity-csharp-scripting`, and the setup the other Unity skills point to. Run the
cheapest check that proves the change, and report which one ran.

## Contents

- Order of checks
- Path A: Unity CLI and a connected Editor
- Path B: batch mode, no CLI
- Test assemblies
- Reading results
- When only a person can judge

## Order of checks

1. `python scripts/check_unity_project.py <project>`: `.meta`, GUID and missing-script
   errors. No Unity needed.
2. Compile check: no `error CS` lines.
3. EditMode tests: plain logic, ScriptableObject data, asset contents.
4. PlayMode tests: physics, animation, input, NavMesh, anything that needs frames.
5. Read live state from a running Editor (Path A only).
6. Ask the user to look and report a number.

Read `ProjectSettings/ProjectVersion.txt` first (`m_EditorVersion`) and use that Editor
version. A project opened in a newer Editor gets upgraded, which the user did not ask for.

## Path A: Unity CLI and a connected Editor

Available when `unity --version` works and the project has the `com.unity.pipeline` package
(`Packages/manifest.json`). Both are pre-release and change between versions: find a command
with `unity command --query <word>` and its flags with `<command> --help` instead of
guessing, and add `--format json` when you parse output.

```bash
unity status --project-path <project>                  # is this project's Editor ready?
unity recompile --project-path <project>               # compile errors, no build
unity test <project> --mode EditMode --output editmode.xml
unity command script eval --project-path <project> --code 'return Application.unityVersion;'
unity command console get --project-path <project>     # recent Console output
```

- `script eval` runs C# inside the Editor and returns the value of `return x;` as JSON.
  `UnityEngine`, `UnityEditor`, `System.Linq` and `System.Collections.Generic` are imported
  already. Use it to read state back (a field value, a component's settings, an asset's
  contents); keep project edits in files so they show in version control.
- `unity test` exits 8 when the tests ran and some failed (a retry gives the same result),
  and 6 when the run did not finish: a compile error, no licence, an Editor crash or a
  timeout. Fix the cause of a 6 before you read any results.
- Always pass `--project-path` when more than one Editor may be open. Without it the CLI picks
  the Editor whose project contains the current directory, which may be another checkout.
- An Editor that started with compile errors boots into Safe Mode and cannot take commands;
  `unity status` lists the errors. Fix them in the files, then retry.
- Installing the CLI (`curl -fsSL https://unity.com/install.sh | bash`) or the package
  (`unity pipeline install`) changes the user's machine or project: ask first.

## Path B: batch mode, no CLI

The Editor binary is in the Unity Hub install folder for the version in `ProjectVersion.txt`;
ask the user for the path if it is not obvious. Batch mode cannot open a project that is
already open in an Editor, so ask the user to close it first or use Path A.

```bash
# Compile check: imports the project, compiles scripts, exits.
"$UNITY" -batchmode -nographics -quit -projectPath "$PROJECT" -logFile "$PWD/compile.log"
grep -E "error CS[0-9]{4}" compile.log

# Tests: no -quit, the test runner exits by itself when it finishes.
"$UNITY" -batchmode -nographics -projectPath "$PROJECT" -runTests \
  -testPlatform EditMode -testResults "$PWD/editmode.xml" -logFile "$PWD/tests.log"
```

Use `-testPlatform PlayMode` for PlayMode tests and `-testFilter <regex>` to run a subset.
Give absolute paths for `-testResults` and `-logFile`.

The Editor log of an interactive session is at `~/.config/unity3d/Editor.log` (Linux),
`~/Library/Logs/Unity/Editor.log` (macOS) or `%LOCALAPPDATA%\Unity\Editor\Editor.log`
(Windows). Grep it for `error CS` and for your own `Debug.Log` tags.

## Test assemblies

Tests live in their own assembly definition. Create the folder and file directly; Unity
writes the `.meta` files on the next import.

`Assets/Tests/EditMode/EditModeTests.asmdef`:

```json
{
  "name": "EditModeTests",
  "references": ["UnityEngine.TestRunner", "UnityEditor.TestRunner", "Game"],
  "includePlatforms": ["Editor"],
  "overrideReferences": true,
  "precompiledReferences": ["nunit.framework.dll"],
  "autoReferenced": false,
  "defineConstraints": ["UNITY_INCLUDE_TESTS"]
}
```

For PlayMode tests use a second folder with `"includePlatforms": []` and drop
`UnityEditor.TestRunner` from `references`.

`"Game"` is the project's own runtime assembly. An assembly definition cannot reference the
predefined `Assembly-CSharp`, so if the game scripts have no `.asmdef` yet, either add one
around them (a bigger change: ask first) or keep the test to engine types and objects built
in the test.

A minimal PlayMode test:

```csharp
using System.Collections;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools;

public class SmokeTests
{
    [UnityTest]
    public IEnumerator BoxComesToRestOnFloor()
    {
        var floor = GameObject.CreatePrimitive(PrimitiveType.Cube);   // top face at y = 0.5
        floor.transform.localScale = new Vector3(10f, 1f, 10f);
        var box = GameObject.CreatePrimitive(PrimitiveType.Cube);
        box.transform.position = new Vector3(0f, 5f, 0f);
        box.AddComponent<Rigidbody>();

        yield return new WaitForSeconds(2f);

        Assert.That(box.transform.position.y, Is.EqualTo(1f).Within(0.1f));
    }
}
```

## Reading results

- The results file is NUnit 3 XML. The root `test-run` element carries `result`, `total`,
  `passed` and `failed`; each failing `test-case` has a `failure/message`. Report those
  numbers and messages, not "tests pass" from the exit code alone.
- Remove temporary `Debug.Log` probes and throwaway test scenes before you finish, and say in
  the report which checks ran, which could not run, and why.

## When only a person can judge

Feel, timing and visuals need eyes. Ask for something specific and countable: "Enter Play
mode, jump five times, and tell me how many times the landing animation played" beats "check
it looks right". Ask for the Console text if anything is red.
