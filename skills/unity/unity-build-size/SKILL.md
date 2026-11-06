---
name: unity-build-size
description: >
  Find and fix what makes a Unity 6 player build large: read the Editor log Build Report, find
  uncompressed or oversized textures, glTF/GLB models whose embedded images glTFast ships
  uncompressed, PCM audio, heavy meshes, and Resources or StreamingAssets bloat, then rebuild and
  package under a size limit. Use when a Unity build, zip or download is too big, a submission
  has a size cap (for example under 200 MB), sharedassets*.resS is huge, or the user asks why
  the build is large or how to shrink it.
---

# Unity build size

Bring a Unity player build under a size budget by measuring what ships, fixing the few assets
that dominate it, and proving the smaller build still runs. Targets **Unity 6.3 LTS (6000.3)**;
the workflow and scripts were exercised on 6000.5.10f1 with glTFast 6.20.0. Keep an existing
project's version from `ProjectSettings/ProjectVersion.txt`.

## When to use

- A build folder, archive or store upload is over a limit, or much bigger than expected.
- `*_Data/sharedassets*.assets.resS` or `resources.assets.resS` holds most of the bytes.
- The project imports `.glb`/`.gltf` models (glTFast) or large textures and audio from asset
  stores or Sketchfab-style downloads.

**When not to use:** scripting backend, managed code stripping, `link.xml`, Build Profiles and CI
build scripts belong to `unity-build-pipeline`. Frame time, draw calls and runtime memory belong
to `performance-optimization`. Store upload steps belong to `steam-publish` / `itch-publish`.

## Workflow

1. **Pin the budget.** Ask what is limited: the archive someone downloads, the installed folder,
   or a store's package. Measure that same thing at the end.
2. **Measure the current build.** Build once (or reuse the last build in this Editor session) and
   summarize the Build Report from the Editor log:

   ```bash
   python scripts/build_report.py ~/Library/Logs/Unity/Editor.log --top 20
   ```

   Windows: `%LOCALAPPDATA%\Unity\Editor\Editor.log`; Linux: `~/.config/unity3d/Editor.log`;
   batch mode: the `-logFile` path. The categories say *what kind* of data dominates; the asset
   list says *which files*. Sizes are uncompressed and include every scene in the build. Unity
   also saves the last report to `Library/LastBuild.buildreport`, which the Build Report
   Inspector package can open.
3. **Find the causes statically.** Run the checker from the skill directory (paths are relative
   to it) against the project:

   ```bash
   python scripts/check_unity_build_size.py path/to/Project --max-texture-size 2048
   ```

   Each `WARNING` names a file, the setting, an estimated build cost, and a `fix:` line. Cross
   it with the Build Report: an asset that no shipped scene references costs nothing.
4. **Fix the biggest category first**, smallest change first:
   - **glTF/GLB with embedded images** (`gltf-embedded-texture`): glTFast ships them
     uncompressed. Shrink them or move them out; read `references/gltf-textures.md`. The
     `fix:` line holds a `gltf-transform` command to run from the project folder.
   - **Textures** (`uncompressed-texture`, `texture-max-size`): set Compression to Normal
     Quality and lower Max Size, per platform if needed (Pattern 1).
   - **Audio** (`pcm-audio`): Vorbis for music and ambience, ADPCM for short effects, Force To
     Mono where stereo adds nothing.
   - **Meshes**: for FBX/OBJ use the Model Importer's Mesh Compression; for glTF reduce the source
     (`gltf-heavy-geometry`).
   - **Resources / StreamingAssets**: everything in a `Resources` folder ships; StreamingAssets is
     copied byte for byte. Move out what nothing loads.
   - **Scenes**: remove test scenes from the Scene List of the profile you build.
5. **Rebuild and compare.** Rerun `build_report.py` and check that the categories you touched
   dropped. Use `--budget-mb` to fail a CI job over the limit.
6. **Package only what runs** (Pattern 2): leave out `*_BurstDebugInformation_DoNotShip`, then
   archive and measure the archive.
7. **Prove it runs.** Launch the packaged player, reach gameplay, and look at the assets you
   shrank. When you cannot run the target platform, build the same project for your own platform
   and launch that instead, and say which one you tested.

## Patterns

### 1. Apply texture limits in bulk (Editor script)

Place under any `Editor` folder. It changes import settings, so commit first and review the diff.

```csharp
using UnityEditor;
using UnityEngine;

public static class TextureBudget
{
    const int MaxSize = 2048;

    [MenuItem("Tools/Build Size/Compress Large Textures")]
    static void CompressLargeTextures()
    {
        foreach (string guid in AssetDatabase.FindAssets("t:Texture2D", new[] { "Assets" }))
        {
            string path = AssetDatabase.GUIDToAssetPath(guid);
            if (AssetImporter.GetAtPath(path) is not TextureImporter importer)
                continue;   // sub-assets of models (glTFast) have no TextureImporter

            bool changed = false;
            if (importer.maxTextureSize > MaxSize) { importer.maxTextureSize = MaxSize; changed = true; }
            if (importer.textureCompression == TextureImporterCompression.Uncompressed)
            {
                importer.textureCompression = TextureImporterCompression.Compressed;
                changed = true;
            }
            if (changed)
            {
                importer.SaveAndReimport();
                Debug.Log($"Compressed {path}");
            }
        }
    }
}
```

The default setting applies to every platform without an override. To limit one platform only,
use `importer.GetPlatformTextureSettings("Android")`, set `overridden = true`, `maxTextureSize`
and `textureCompression`, then `importer.SetPlatformTextureSettings(settings)`.

### 2. Package the player without debug files

```bash
# From the folder that holds the build folder (Windows example names)
rm -rf "MyGame/MyGame_BurstDebugInformation_DoNotShip"
zip -qr -9 MyGame.zip MyGame
ls -l MyGame.zip
```

Burst writes its debug information (`lib_burst_generated.txt`, PDBs, dSYMs) into that folder
"to ensure it is easy to remove the files that you should not ship" (Burst changelog). Keep a
copy if you need to symbolicate crash reports.

### 3. Fail CI over a budget

```bash
Unity -batchmode -quit -projectPath . -buildTarget win64 \
  -executeMethod BuildScript.BuildWindows -logFile build.log
python scripts/build_report.py build.log --budget-mb 400 --json > build-size.json
```

`--budget-mb` compares the uncompressed complete build size from the report. Check the archive
size separately when the limit is on the archive.

## Pitfalls

- **Texture settings look fine but the build is still huge** → the textures are embedded in a
  `.glb`/`.gltf`; glTFast ships them uncompressed and they have no Texture Importer. Run the
  checker and follow `references/gltf-textures.md`.
- **Normal maps look wrong after moving glTF images out** → the extracted textures came in with
  sRGB on. Turn sRGB (Color Texture) off for every map except base color, emissive and the
  specular-glossiness pair.
- **A compressed archive is still over the limit** → archivers usually gain little on data Unity
  has already block-compressed; reduce resolution or remove assets before trying stronger
  archive settings.
- **Size dropped in the Editor log but not on disk** → you measured an old build folder, or a
  stale `*_BurstDebugInformation_DoNotShip` folder sits beside the data folder. Delete the output
  folder and build clean.
- **An asset you never use still ships** → it sits in a `Resources` folder, or a scene in the
  build list references it. The Build Report lists every used asset; search the scenes for it.
- **Textures look soft after lowering Max Size** → that texture fills more screen pixels than the
  new limit; give it a higher Max Size and lower something less visible instead.
- **The checker shows `Git LFS pointer`** → the clone has pointer files instead of models; run
  `git lfs pull` before building, or Unity imports nothing.

## Resources

- `scripts/check_unity_build_size.py --help` — read-only project check (glTFast embedded images,
  texture compression and Max Size, PCM audio, Resources/StreamingAssets). Python 3.10+, no
  dependencies; `--json` for tools, `--strict` to fail on warnings.
- `scripts/build_report.py --help` — summarizes the last Build Report in an Editor log; `--top`,
  `--json`, `--budget-mb`.
- `references/gltf-textures.md` — why glTFast ships embedded images uncompressed, size table, and
  the two fixes (resize in place, or extract with the right color space).
- Primary docs (Unity 6000.3 Manual): "Reducing the file size of a build", "Texture Import
  Settings window reference", "Audio Clip Import Settings reference", "Log files reference",
  "Reserved folder name reference", and "Include additional files in a build"; the glTFast
  package source.

## Related skills

- `unity-build-pipeline` — scripted and CI builds, stripping, scripting backend.
- `performance-optimization` — runtime budgets for memory and frame time.
- `create-game-assets` — producing textures at the right size before import.
- `steam-publish` / `itch-publish` — uploading the packaged build.
