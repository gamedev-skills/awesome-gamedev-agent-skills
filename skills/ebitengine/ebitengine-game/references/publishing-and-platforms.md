# Publishing and platforms

Read for requested packaging/distribution work. These recipes target the
v2.10.6 starter. Ebitengine's pure-Go desktop backend does not make every game's
SDKs/dependencies portable or establish runtime/store compatibility.
Build commands are in the project-and-builds reference and automation in the
ci-and-release reference.

## Contents

- [Target selection](#target-selection)
- [Windows](#windows)
- [macOS](#macos)
- [Linux](#linux)
- [Steamworks boundary](#steamworks-boundary)
- [Browser, mobile and port readiness](#browser-mobile-and-port-readiness)

## Target selection

| Target | Engine path | Additional verification |
| --- | --- | --- |
| Windows/macOS/Linux | `go build` for supported GOOS/GOARCH | runtime libraries, game dependencies, actual launch/input/audio |
| Browser | `GOOS=js GOARCH=wasm` | HTTP host, matching `wasm_exec.js`, browser console/focus/audio |
| Android/iOS | `ebitenmobile bind` plus native host | cgo, SDK/NDK or Xcode, native lifecycle, real devices |
| Steam | desktop build, optional Steamworks SDK | platform packaging, client services and Valve review |
| Consoles | licensed platform-specific port/toolchain | developer access, SDK, development kit and certification |

Only promise targets actually requested and checked. Public build tags are not
proof of available or complete console support. Consult the pinned engine's
[README](https://github.com/hajimehoshi/ebiten) and platform holder for current
access; keep SDK-specific material within its permitted environment.

## Windows

```sh
GOOS=windows GOARCH=amd64 go build -buildvcs=false -trimpath \
  -ldflags="-s -w -H=windowsgui" -o build/mygame.exe .
```

`-H=windowsgui` avoids a startup console. Provide useful diagnostics through a
log file/error UI when release console output is unavailable. Embed an icon
with a resource tool (its `.syso` is linked by Go) or call `SetWindowIcon`;
v2.10 also uses executable icons as window icons. Code signing and SmartScreen
behavior require testing with the actual distributed binary.

For **Windows Steam builds**, the current
[Ebitengine Steam guide](https://ebitengine.org/en/documents/steam.html)
recommends `-X=runtime.godebugDefault=asyncpreemptoff=1` for reported freezes.
This disables asynchronous preemption; keep it a documented target-specific
workaround, not an unconditionally harmless flag on every build. Recheck the
engine/Go guidance when upgrading.

## macOS

The packager can assemble a universal unsigned `.app`:

```sh
CGO_ENABLED=0 GOOS=darwin GOARCH=amd64 go build -buildvcs=false -trimpath -o build/mygame_amd64 .
CGO_ENABLED=0 GOOS=darwin GOARCH=arm64 go build -buildvcs=false -trimpath -o build/mygame_arm64 .
python3 "$skill_dir/scripts/package_macos_app.py" --name "My Game" \
  --bundle-id com.example.mygame --version 1.2.0 \
  --amd64 build/mygame_amd64 --arm64 build/mygame_arm64 --out build
```

Inspect `--help` for icons and version options. Select the minimum OS consistent
with the actual Go/dependency toolchain. The packager reads Mach-O deployment
targets and rejects a lower explicit minimum. Packaging
on Linux does not verify launch, signing or notarization.

For distribution, follow [Apple's notarization workflow](https://developer.apple.com/documentation/Security/customizing-the-notarization-workflow)
and the chosen store's requirements. Sign the final bundle on macOS with the
appropriate identity, hardened runtime and required entitlements. Steam has
specific signing/entitlement requirements in
[Valve's platform documentation](https://partner.steamgames.com/doc/store/application/platforms).
Submit, staple and validate before archiving; for example use `ditto -c -k
--keepParent` to create the final zip. Extract the distributed archive on a clean
Mac and check launch and Gatekeeper, not just the original local bundle.
The supplied packager and CI do not perform these steps.

## Linux

```sh
CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -buildvcs=false -trimpath -o build/mygame .
```

Pure-Go builds still load graphics/window/audio libraries at runtime. See the
[official installation guide](https://ebitengine.org/en/documents/install.html)
for the pinned engine version. Test with the target distribution/runtime;
building under a development desktop does not prove a clean-machine launch.
For Steam/Deck, test the selected native runtime or Proton path and supported
controllers, text scale and overlay behavior.

## Steamworks boundary

[`go-steamworks`](https://github.com/hajimehoshi/go-steamworks) binds some of the
Steamworks flat API with purego. Pin a concrete version and inspect its exposed
functions and platform support; it does not automatically provide all Steam
features. The binding can load its shared library during package initialization,
so isolate the import behind a store/platform build tag. A runtime flag after
`init` cannot rescue a build whose SDK library failed to load.
For depots, SteamPipe uploads and store release, see `steam-publish`.

Keep game-used services behind a small interface and provide a non-Steam
implementation for other targets/tests. Initialize the SDK deliberately, call
`RunCallbacks` while the game is running, and shut it down according to its
lifecycle. Handle offline/unavailable services without claiming a save or an
achievement was synchronized. Retry/reconcile according to API results.

Use the real App ID, registered achievement names and depots for release. The
official Ebitengine guide describes the required Windows Steam DLL. Development
`steam_appid.txt` and test credentials must not leak into release packaging.
Test through the Steam client, including offline/restart/cloud conflicts where
those features are promised. A binding compile test does not validate these.
Steam Auto-Cloud may avoid a custom cloud-save implementation; choose based on
the game's needs and Valve's current documentation.

## Browser, mobile and port readiness

Browser packaging needs `index.html` at the archive root, the matching Go
`wasm_exec.js` and correct WASM HTTP serving. Test actual hosting, loading errors,
focus, aspect ratios and audio after a gesture. Portal SDK requirements differ;
implement only the selected portal's integration (see the monetization reference).

Mobile needs a native host around the `.aar`/`.xcframework`. Forward lifecycle,
save before background termination and test touch/safe areas/resume on devices.
Store submission, signing and purchases live in that host/store workflow.

For a later port, separate storage and platform services; keep fonts/assets
available and rules independent of direct OS access. Support the port's intended
controls through menus and text entry. Use logical layouts suited to the game
and destination, rather than imposing one fixed resolution on every game.
Release acceptance comes from the destination's current requirements and actual
execution, not from this portability checklist.
