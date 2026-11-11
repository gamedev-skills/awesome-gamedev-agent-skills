# iOS (App Store, TestFlight)

Read this when the target is iPhone or iPad. Pass `--platform iPhone` to the checker (that is the
`.meta` name for iOS). Checked against the Unity 6000.3 manual and Apple's docs (2026-11).

## What is limited

- **App Store**: 4 GB uncompressed app, and 500 MB for the `__TEXT` sections of the executable
  (deployment target iOS 9 or later)
  ([Maximum build file sizes](https://developer.apple.com/help/app-store-connect/reference/app-uploads/maximum-build-file-sizes)).
- **Cellular download**: Unity's manual still names a 200 MB over-the-air limit, which users can
  override since iOS 13; leave a margin under it if the user cares
  ([Optimize the size of the iOS Player](https://docs.unity3d.com/6000.3/Documentation/Manual/iphone-playerSizeOptimization.html)).
- The App Store encrypts the binary before it compresses it, so the store size comes out larger
  than a local zip of the same app (same page).

The Xcode project Unity writes, and the `.app` inside a local build, are not what users download.
Measure the thinned variants instead
([Reducing your app's size](https://developer.apple.com/documentation/xcode/reducing-your-app-s-size)):

1. In Xcode, Product → Archive.
2. Export the archive as Ad Hoc or Development, and set App Thinning to "All compatible device
   variants".
3. Read `App Thinning Size Report.txt` in the export folder: compressed and uncompressed size per
   device variant.

After an upload, App Store Connect shows the build's file sizes on its build metadata page.

## First moves, in order

1. **Archive a release build in Xcode.** Debug builds keep symbols and are not representative.
2. **Textures and audio**: the main workflow with `--platform iPhone`. ASTC is the preferred format;
   only the oldest Metal devices (A7) lack it and unpack it at runtime
   ([Choose a GPU texture format by platform](https://docs.unity3d.com/6000.3/Documentation/Manual/texture-choose-format-by-platform.html)).
3. **Code size**: Strip Engine Code, Managed Stripping Level, API Compatibility Level .NET
   Standard. Stripping and its breakage belong to `unity-build-pipeline`.
4. **Compression Method**: iOS has no compression by default. LZ4HC shrinks the installed data;
   the IPA is a zip already, so check the thinning report before you claim a smaller download.
5. **Large optional content**: On-Demand Resources (Player Settings → Use on-demand resources,
   AssetBundles tagged for download) keep it out of the initial install
   ([On-demand resources](https://docs.unity.com/engine/6000.3/manual/platform-specific/iphone/ios-building-and-delivering/app-thinning/ios-ondemand-resources)).
6. **Ignore bitcode advice.** Xcode 14 deprecated bitcode and the App Store no longer accepts
   bitcode submissions, so old guides about bitcode inflating the upload do not apply
   ([Xcode 14 release notes](https://developer.apple.com/documentation/xcode-release-notes/xcode-14-release-notes)).

## Prove it

Install the exported build on a device (Xcode → Window → Devices and Simulators, or TestFlight),
play to gameplay, and look at the assets you changed.
