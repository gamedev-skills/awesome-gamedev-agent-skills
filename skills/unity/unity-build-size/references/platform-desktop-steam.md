# Desktop builds: zips, jam uploads, installed size and Steam

Read this for Windows, macOS and Linux players: a zip with a size cap (game jams, itch.io
downloads, email), the installed folder, or a Steam depot. The checker's default
`--platform Standalone` is the right one. Checked against the Unity 6000.3 manual and the
Steamworks docs (2026-11).

## What is limited

| Limit on | Measure |
|----------|---------|
| A zip or other archive | the archive file, after Pattern 1 below |
| Installed size | the build folder, without the debug folders |
| Steam download | the size SteamPipe reports for the build; Steam compresses every chunk itself |
| Steam update size | the download of the second build, which SteamPipe diffs in 1 MB chunks |

Limits written in MB are often decimal (1 MB = 1,000,000 bytes); `ls -l` prints bytes.

## Player compression (Compression Method)

On Windows, macOS and Linux the default is no compression. LZ4HC compresses the player data at
build time and shrinks the installed folder; LZ4 builds faster for iteration
([Windows build settings](https://docs.unity.com/en-us/engine/6000.3/manual/platform-specific/windows/standalone-binaries)).
Scripted builds pass `BuildOptions.CompressWithLz4HC`.

- **Zip or installed-size limit**: use LZ4HC, then measure the archive again. A zip of LZ4HC data
  shrinks less, so the archive can drop by less than the folder did.
- **Steam: leave it on Default.** Steam already compresses everything it uploads and downloads,
  and Valve advises against compression that crosses asset boundaries, because one change then
  spreads across many 1 MB chunks
  ([Uploading to Steam](https://partner.steamgames.com/doc/sdk/uploading)). With LZ4 or LZ4HC,
  Unity packs the player data into one `data.unity3d` file in 128 KB compressed chunks
  ([BuildOptions.CompressWithLz4](https://docs.unity.com/en-us/engine/6000.3/script-reference/unityeditor/buildoptions/compresswithlz4)),
  so a small change shifts everything after it and most of that file looks new to SteamPipe.
  Use LZ4HC on Steam only when installed size matters more than patch size, and say so.
- **Prove what changed before blaming compression.** Build twice with one small change and hash
  every file in both folders (`sha256sum` or PowerShell `Get-FileHash`). Files that differ when
  nothing in them changed (a `data.unity3d`, one large `resources.assets`, or AssetBundles
  rebuilt with new hashes in their names) are what make the patch big.

## Leave the debug folders out

Burst writes `<Product>_BurstDebugInformation_DoNotShip` and IL2CPP writes
`<Product>_BackUpThisFolder_ButDontShipItWithYourGame` next to the data folder. They hold symbols
and generated C++, often hundreds of MB, and should not ship
([Burst changelog](https://docs.unity3d.com/Packages/com.unity.burst@1.8/changelog/CHANGELOG.html),
[IL2CPP build files](https://docs.unity3d.com/2021.2/Documentation/Manual/WindowsPlayerIL2CPPBuildProducedFiles.html)).
Keep them, or archive them separately, so you can symbolicate crash reports from this build.
On Windows, Build Profiles → Copy PDB files adds PDBs to the player; leave it off for a release.

### Pattern 1: zip without the debug folders

```bash
# From the folder that holds the build folder (Windows example names)
zip -qr -9 MyGame.zip MyGame \
  -x '*_BurstDebugInformation_DoNotShip/*' '*_BackUpThisFolder_ButDontShipItWithYourGame/*'
unzip -l MyGame.zip | grep -E 'DoNotShip|DontShip' || echo "debug folders excluded"
ls -l MyGame.zip
```

On Windows without `zip`, `Compress-Archive` cannot exclude folders: copy the build without the
two folders first (`robocopy MyGame MyGame-ship /E /XD *_DoNotShip *_ButDontShipItWithYourGame`),
then compress the copy.

### Pattern 2: exclude them from a Steam depot

In the depot build script, next to the `FileMapping`:

```text
"FileExclusion" "*_BurstDebugInformation_DoNotShip*"
"FileExclusion" "*_BackUpThisFolder_ButDontShipItWithYourGame*"
```

Steamworks documents wildcard `FileExclusion` lines such as `"*.pdb"`. Upload steps belong to
`steam-publish`.

## Keep Steam patches small

SteamPipe sends only changed 1 MB chunks, so small patches come from data that changes in place.
Content split by level or feature (Addressables groups or AssetBundles, each compressed on its
own) keeps a level fix inside that level's files; new content goes into new files. To check, make
a test build with one small change and compare its download with the previous build.

## Prove it

Unzip the archive (or install the Steam build) into an empty folder on a clean machine or account,
launch it, reach gameplay and look at the assets you shrank. A stale build folder or a leftover
debug folder makes the size you measured wrong, so always build into an empty output folder.
