---
name: unity-build-size
description: >
  Finds and shrinks what makes a Unity 6.3 LTS build too big: Build Report reading, uncompressed
  textures, glTFast models, PCM audio and per-platform levers. Use when an APK, AAB, WebGL build
  or Steam depot is over a size limit or the download is too big. Not for frame rate
  (`performance-optimization`), build scripts or stripping (`unity-build-pipeline`) or store
  uploads (`steam-publish`).
---

# Unity build size

Bring a Unity player build under a size limit: measure the thing that is limited, fix the few
assets and settings that dominate it, rebuild, and prove the result runs. Targets **Unity 6.3 LTS
(6000.3)**; the scripts were exercised against glTFast 6.20.0 projects. Keep an existing project's
version from `ProjectSettings/ProjectVersion.txt`.

Script paths below are relative to this skill's folder. Both scripts are read-only, standard-library
Python 3.10+.

## 1. Pin what is limited

A build has several sizes, and fixing the wrong one wastes the user's time. Find out which file is
limited and by how much, then read **only** the matching reference:

| Target | What is usually limited | Read |
|--------|-------------------------|------|
| Browser (itch.io, portals, own site) | each file in `Build/` (itch.io: 200 MB per file) and the compressed download | [references/platform-web.md](references/platform-web.md) |
| Android (APK, AAB, Google Play) | the download Play computes from the AAB | [references/platform-android.md](references/platform-android.md) |
| iOS (App Store, TestFlight) | the thinned download per device | [references/platform-ios.md](references/platform-ios.md) |
| Windows, macOS, Linux (zip, jam, Steam) | the archive, the installed folder, or Steam patch size | [references/platform-desktop-steam.md](references/platform-desktop-steam.md) |

If the user names a number but not the file it applies to, ask that one question. With no hard
limit, pick what the user pays for (download, installed size, patch size) and say which one you
measured. Write down the current size of that file before you change anything: it is the
baseline you compare against.

## 2. Measure what ships

Build once (or use the last build of this Editor session) and summarize the Build Report:

```bash
python scripts/build_report.py ~/Library/Logs/Unity/Editor.log --top 20
```

Log paths: Windows `%LOCALAPPDATA%\Unity\Editor\Editor.log`, Linux
`~/.config/unity3d/Editor.log`, batch mode the `-logFile` path. Categories say *what kind* of data
dominates; the asset list says *which files*. The sizes are uncompressed and in MiB, so they are
not the download size: always compare against the file you measured in step 1.

When the Unity CLI is installed (`unity --version`), it can make the build and keep its log:
`unity build . --profile "<Build Profile name>" --output-path <output path> --log-file build.log`, then run
`build_report.py build.log`. Without it, use the Editor's Build Profiles window or the project's
build script.

## 3. Find the causes in the project

```bash
# --platform: the one you ship, as Standalone, Android, iPhone or WebGL
python scripts/check_unity_build_size.py path/to/Project --platform WebGL --max-texture-size 2048
```

Without the right `--platform`, that platform's texture overrides are not checked. Each
`WARNING` names a file, the setting, an estimated build cost and a `fix:` line; `NOTE`s are
context. The checker cannot know which assets a build references, so cross it with the Build
Report: an asset no shipped scene uses costs nothing.

## 4. Fix the biggest category first

Smallest change first, one category at a time, so the next measurement shows what each fix bought.

- **glTF/GLB with embedded images** (`gltf-embedded-texture`): glTFast ships them uncompressed,
  and they have no Texture Importer to fix. Run the checker's `fix:` command, or move the images
  out; read [references/gltf-textures.md](references/gltf-textures.md) before the first one.
- **Textures** (`uncompressed-texture`, `texture-max-size`): Compression Normal Quality and a lower
  Max Size, per platform if needed (Pattern below). An override with an explicit Format ignores
  Compression, so set that Format to Automatic or a compressed one. For download size on
  DXT/ETC formats, Use Crunch Compression shrinks the files further at some quality cost.
- **Audio** (`pcm-audio`): Vorbis for music and ambience, ADPCM for short effects, Force To Mono
  where stereo adds nothing.
- **Resources and StreamingAssets**: everything in a `Resources` folder ships whether or not it is
  loaded; `Assets/StreamingAssets` is copied byte for byte. Move out what nothing uses.
- **Meshes, animation, lightmaps**: Model Importer Mesh Compression for FBX/OBJ (glTF: reduce the
  source, `gltf-heavy-geometry`), animation compression on clips, and in the Lighting window a
  lower Max Lightmap Size and Lightmap Compression when lightmaps top the Textures category.
- **Scenes**: remove test scenes from the Scene List of the profile you build.
- **Code and engine size**: when native libraries, `.wasm` or managed DLLs top the list, apply the
  platform reference's settings; stripping levels and `link.xml` belong to `unity-build-pipeline`.
- **Packaging**: the platform reference covers player compression, store packaging and the debug
  folders that must not ship.

## 5. Rebuild, compare, prove

1. Build into an **empty** output folder (a stale folder or a leftover debug folder skews the size).
2. Rerun `build_report.py` and the checker; the categories you touched must have dropped. Measure
   the limited file from step 1 again and report before and after as numbers.
3. Launch the build the way players get it, reach gameplay, and look at the assets you shrank. The
   platform reference says how (a Web build needs a server). When you cannot run the target, build
   for your own platform and launch that, and say which one you tested.
4. For CI, `build_report.py build.log --budget-mb 400` exits 1 over budget, and also when the log
   has no complete size to compare. It checks the uncompressed total, so check the shipped file
   separately when the limit is on that file.

## Gotchas

- **Texture settings look fine but the build is still huge** → the textures sit inside `.glb`/`.gltf`
  models. Run the checker; `references/gltf-textures.md` has the fixes.
- **Textures in the Build Report are far larger than their `.meta` settings allow** → the Build
  Profiles window's Asset Import Overrides set Texture Compression to Force Uncompressed (or Force
  No Crunch). They are a local iteration shortcut the checker cannot see; clear them before a
  release build
  ([Build Profiles reference](https://docs.unity3d.com/6000.3/Documentation/Manual/build-profiles-reference.html)).
- **Running a `.gltf` fix for several models in one folder** → `gltf-transform` names the images it
  writes after the texture slot (`baseColor_1.png`) and overwrites existing ones, so every model
  ends up with the last one's textures. The checker's `fix:` line says when to move a model into
  its own folder first; follow it.
- **Normal maps look wrong after moving glTF images out** → they came in with sRGB on. Turn sRGB
  (Color Texture) off for every map except base color, emissive and the specular-glossiness pair.
- **LZ4HC made the zip smaller and the Steam patch huge** → Steam compresses downloads itself, and
  Unity's compressed player data spreads small changes across many chunks. On Steam and Android,
  leave Compression Method on Default; see the platform reference.
- **The Web build is several times the expected size** → it is a development build, which Unity
  never compresses.
- **Addressables content is missing from the Build Report's asset list** → local groups are built
  as bundles and copied into the player's `StreamingAssets/aa`; the player Build Report does not
  list the assets inside them. Use the Addressables Build Report window. Current Addressables
  versions build into `Library/`, so a leftover `Assets/StreamingAssets/aa` is stale and ships
  anyway; the Addressables changelog recommends deleting it
  ([changelog](https://docs.unity3d.com/Packages/com.unity.addressables@2.9/changelog/CHANGELOG.html)).
- **An `uncompressed-texture` warning on a sprite you packed** → a sprite in a Sprite Atlas ships
  with the atlas's settings; check the atlas instead.
- **Textures look soft after lowering Max Size** → that texture fills more screen pixels than the
  limit; give it a higher Max Size and lower something less visible.
- **The checker reports a `Git LFS pointer` model** → the clone has pointer files; run
  `git lfs pull` before measuring anything.

## Pattern: texture limits in bulk (Editor script)

Commit first: this changes import settings, and the diff is the review. Place under any `Editor`
folder. It skips small textures, as the checker does, so pixel art and UI icons keep their settings.

```csharp
using UnityEditor;
using UnityEngine;

public static class TextureBudget
{
    const int MaxSize = 2048;
    const int MinEdgeToCompress = 1024;

    [MenuItem("Tools/Build Size/Compress Large Textures")]
    static void CompressLargeTextures()
    {
        AssetDatabase.StartAssetEditing();   // one reimport pass instead of one per texture
        try
        {
            foreach (string guid in AssetDatabase.FindAssets("t:Texture2D", new[] { "Assets" }))
            {
                string path = AssetDatabase.GUIDToAssetPath(guid);
                if (AssetImporter.GetAtPath(path) is not TextureImporter importer)
                    continue;   // sub-assets of models (glTFast) have no TextureImporter
                importer.GetSourceTextureWidthAndHeight(out int width, out int height);
                if (Mathf.Max(width, height) < MinEdgeToCompress)
                    continue;

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
        finally
        {
            AssetDatabase.StopAssetEditing();
        }
    }
}
```

This changes the default settings, which apply to every platform without an override. For one
platform, use `importer.GetPlatformTextureSettings("Android")`, set `overridden = true`,
`maxTextureSize` and `textureCompression`, then `importer.SetPlatformTextureSettings(settings)`.

## Optional helpers

This skill works with files and the Editor log alone. When they are installed, these save steps:

- **Unity CLI** (`unity`, experimental): builds with a kept log (step 2) and `unity build run` to
  launch the last build, including a Web build on a local server
  ([Unity CLI docs](https://docs.unity.com/en-us/unity-cli)).
- **Unity's official agent skills** ([Unity-Technologies/skills](https://github.com/Unity-Technologies/skills)):
  `optimize-web` and `optimize-audio` apply Player and audio settings through a live Editor,
  `project-auditor-fixes` runs Project Auditor. Use them for the Editor-side changes, and keep
  this skill's measure-and-compare loop around them.

## Resources

- `scripts/check_unity_build_size.py --help`: the project check. `--json` for tools, `--strict` to
  fail on warnings.
- `scripts/build_report.py --help`: Build Report summary; `--top`, `--json`, `--budget-mb`.
- [references/gltf-textures.md](references/gltf-textures.md): glTFast embedded images, size table,
  the two fixes, heavy geometry.
- Unity manual: [Reducing the file size of a build](https://docs.unity.com/en-us/engine/6000.3/manual/building-and-publishing/reducing-filesize),
  [Reserved folder names](https://docs.unity3d.com/6000.3/Documentation/Manual/SpecialFolders.html),
  [Include additional files in a build](https://docs.unity3d.com/6000.3/Documentation/Manual/StreamingAssets.html).

## Related skills

- `unity-build-pipeline`: build scripts, CI, scripting backend, managed stripping, Addressables setup.
- `performance-optimization`: runtime memory and frame time.
- `create-game-assets`: making textures at the right size before import.
- `steam-publish` / `itch-publish`: uploading the packaged build.
