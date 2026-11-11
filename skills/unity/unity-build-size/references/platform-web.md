# Web (WebGL / WebGPU) builds

Read this when the target is a browser: itch.io, a game portal, your own site. Pass
`--platform WebGL` to the checker. Checked against the Unity 6000.3 manual (2026-11).

## What is limited

- **The host's per-file and total limits.** itch.io HTML5 uploads: at most 1,000 files, 500 MB
  extracted, **200 MB per file**, 240 characters per path
  ([itch.io HTML5 docs](https://itch.io/docs/creators/html5)). The `Build/*.data` file is the one
  that usually hits the per-file limit, so check each file, not only the total.
- **What the player downloads**: the compressed files (`*.data.br`, `*.wasm.br`, or `.gz`). These
  are also the files a host's per-file limit applies to, so compression counts against it.

The Build Report sizes are before Web compression, so they overstate the download. Measure the
`Build/` folder itself:

```bash
ls -l path/to/WebBuild/Build/
```

## First moves, in order

1. **Build a release build.** Compression Format applies only to release builds; development builds
   are not compressed at all
   ([Deploy a Web application](https://docs.unity.com/en-us/engine/6000.3/manual/platform-specific/webgl/building-distribution/deploying)).
   A development build measured against a limit looks several times too big.
2. **Compression Format = Brotli** (Player Settings → Publishing Settings). The default is gzip.
   Brotli files are smaller, but Chrome and Firefox decode Brotli only over HTTPS, and the server
   must send `Content-Encoding: br` for `.br` files. itch.io does that for files ending in `.br`.
   Turn on Decompression Fallback only for a host that cannot set the header: it makes startup
   slower.
3. **Code Optimization = Disk Size with LTO** (Build Profiles → Web). Unity recommends it for
   shipping builds; it builds slower
   ([Web build settings](https://docs.unity.com/en-us/engine/6000.3/manual/platform-specific/webgl/building-distribution/web-build-settings)).
   In a script it is `UnityEditor.WebGL.UserBuildSettings.codeOptimization =
   UnityEditor.WebGL.WasmCodeOptimization.DiskSizeLTO`
   ([Optimize Web for mobile](https://docs.unity.com/engine/6000.5/manual/platform-specific/webgl/building-distribution/web-optimization-mobile)).
   It is a user build setting kept under `Library/`, not in `ProjectSettings/` (Unity's own
   `optimize-web` skill notes the same), so a CI machine does not inherit it from your Editor: set
   it in the build script that makes the release.
4. **Code size**: Strip Engine Code on and API Compatibility Level = .NET Standard. Enable
   Exceptions = None saves the most, but then any thrown exception aborts the player, so use it
   only when the game and its plugins never rely on catching exceptions; otherwise keep
   Explicitly Thrown Exceptions Only (or Target WebAssembly 2023 for exceptions without the
   overhead)
   ([Recommended Player settings](https://docs.unity.com/en-us/engine/6000.3/manual/platform-specific/webgl/building-distribution/web-optimization/player)).
   Managed Stripping Level and `link.xml` breakage belong to `unity-build-pipeline`.
5. **Assets**: the main workflow (checker, glTF, textures, audio) applies, with one audio
   difference: Web encodes every clip to AAC whatever format you pick, and supports only the
   Compressed In Memory and Decompress On Load load types, not Streaming
   ([Audio in Web](https://docs.unity.com/en-us/engine/6000.3/manual/platform-specific/webgl/develop/audio)).
   Lower the Quality slider for music to shrink it. Texture
   compression on Web has a per-build subtarget (DXT for desktop browsers, ASTC or ETC2 for mobile;
   Build Profiles → Texture Compression). A build for mobile browsers with DXT textures ships them
   decompressed at runtime, so pick the subtarget for your audience
   ([Texture compression in Web](https://docs.unity3d.com/6000.3/Documentation/Manual/webgl-texture-compression.html)).
6. **One file over the per-file limit after all that**: move content out of the `.data` file into
   Addressables groups (each bundle is its own file, local or remote), and load levels on demand.
   Addressables setup itself belongs to `unity-build-pipeline`.

## Prove it

Open the build through a web server, never from `index.html` on disk. A plain static server that
does not send `Content-Encoding` fails to start a Brotli build unless Decompression Fallback is on.
Use one of:

- the Editor's **Build And Run**;
- `unity build run` when the Unity CLI is installed (it serves a recorded Web build from a
  loopback-only local server);
- an itch.io draft page (the real host).

In the browser's developer tools, Network tab, confirm the `.br` files come back with
`content-encoding: br`, and note the transferred size. Then play to gameplay and look at the
assets you shrank.
