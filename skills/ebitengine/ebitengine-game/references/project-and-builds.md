# Project setup and builds

The bundled starter pins Ebitengine v2.10.6 / Go 1.25+. Keep an existing
project's pinned versions. Commands are POSIX-shell examples; adapt to the
selected targets and record actual build/runtime verification separately.

## Contents

- [Requirements](#requirements)
- [New project](#new-project)
- [Assets](#assets)
- [Window and screen](#window-and-screen)
- [Desktop builds](#desktop-builds)
- [Browser (WebAssembly)](#browser-webassembly)
- [Mobile](#mobile)
- [Release checklist](#release-checklist)

## Requirements

- **Go 1.25 or later** for Ebitengine v2.10 (`go.mod` of v2.10 says `go 1.25.0`).
  Older Ebitengine releases support older Go versions; keep a project's pinned
  pair unless upgrading on purpose.
- **Ebitengine desktop builds are pure Go in v2.10**: the engine needs no C
  compiler or development headers on Windows, macOS or Linux. Other dependencies
  (including native SDKs) may add requirements.
- **Linux at run time** needs an X server (or XWayland), OpenGL and, for sound,
  PulseAudio/PipeWire or ALSA. Debian/Ubuntu:
  `sudo apt install libx11-6 libgl1 libglx-mesa0`, optionally
  `libxcursor1 libxi6 libxinerama1 libxrandr2 libxrender1 libxext6`, and
  `libasound2t64` (Debian 13, Ubuntu 24.04+) or `libasound2` (older).
  Fedora: `sudo dnf install libX11 libglvnd-glx mesa-libGL mesa-dri-drivers`.
- **WSL**: run the Windows build, `GOOS=windows go run .`.
- **Mobile** builds still use cgo and the platform SDKs (below).
- Smoke test of a machine: `go run github.com/hajimehoshi/ebiten/v2/examples/rotate@v2.10.6`.

## New project

```sh
mkdir mygame && cd mygame
go mod init example.com/mygame
go get github.com/hajimehoshi/ebiten/v2@v2.10.6
```

or `python3 "$skill_dir/scripts/new_game.py" --out mygame --module example.com/mygame`, then
`go mod tidy`. Commit `go.sum`. Upgrade deliberately (`go get
github.com/hajimehoshi/ebiten/v2@vX.Y.Z`), then run
the checker from this skill's absolute path and the tests.

## Assets

Embed bundled assets for consistent loading across targets (user saves and
downloadable content need separate storage). For example:

```go
//go:embed assets
var assets embed.FS
```

Read with `assets.ReadFile("assets/player.png")`. Embedding adds to binary and
`.wasm` size; compress music as Ogg Vorbis, keep effects short.

## Window and screen

Call before `RunGame` (most are also safe at run time):

| Call | Purpose |
| --- | --- |
| `ebiten.SetWindowTitle("…")` | title bar text |
| `ebiten.SetWindowSize(w, h)` | initial size in device-independent pixels, usually a multiple of the logical size |
| `ebiten.SetWindowResizingMode(ebiten.WindowResizingModeEnabled)` | let the player resize; `Layout` chooses logical dimensions |
| `ebiten.SetWindowIcon([]image.Image{...})` | window icon (several sizes) |
| `ebiten.SetFullscreen(b)` / `IsFullscreen()` | toggle, e.g. on F11 or Alt+Enter |
| `ebiten.SetVsyncEnabled(b)` | on by default; choose a deliberate release pacing policy |
| `ebiten.SetTPS(n)` | logic rate, 60 by default |
| `ebiten.RunGameWithOptions(g, &ebiten.RunGameOptions{...})` | transparent window, start unfocused, graphics library, single-thread mode |

On Windows, Ebitengine hides the console window of a game started from Explorer
once it is running. Release builds still add `-H=windowsgui` so no console
appears at all (see the Windows section of the publishing-and-platforms reference).

## Desktop builds

```sh
go build -buildvcs=false -trimpath -ldflags="-s -w" -o build/mygame .            # this OS
GOOS=windows GOARCH=amd64 go build -buildvcs=false -trimpath -ldflags="-s -w -H=windowsgui" -o build/mygame.exe .
GOOS=darwin  GOARCH=arm64 go build -buildvcs=false -trimpath -ldflags="-s -w" -o build/mygame-macos-arm64 .
GOOS=darwin  GOARCH=amd64 go build -buildvcs=false -trimpath -ldflags="-s -w" -o build/mygame-macos-amd64 .
GOOS=linux   GOARCH=amd64 go build -buildvcs=false -trimpath -ldflags="-s -w" -o build/mygame-linux .
```

Steam builds for Windows add `-X=runtime.godebugDefault=asyncpreemptoff=1` to
`-ldflags` (publishing-and-platforms reference).

For universal macOS distribution, an `.app` bundle is useful: `scripts/package_macos_app.py`
assembles one from the amd64 and arm64 binaries. Unsigned apps need the user to
allow them in System Settings; signing and notarisation need Apple tooling on a
Mac (publishing-and-platforms reference).

## Browser (WebAssembly)

Quick test (serves and rebuilds on reload):

```sh
go run github.com/hajimehoshi/wasmserve@latest .
# open http://localhost:8080/
```

Publishing:

```sh
GOOS=js GOARCH=wasm go build -buildvcs=false -trimpath -ldflags="-s -w" -o dist/game.wasm .
cp "$(go env GOROOT)/lib/wasm/wasm_exec.js" dist/   # same Go version as the build
```

`dist/index.html`:

```html
<!DOCTYPE html>
<script src="wasm_exec.js"></script>
<script>
const go = new Go();
WebAssembly.instantiateStreaming(fetch("game.wasm"), go.importObject).then(r => go.run(r.instance));
</script>
```

- Serve over HTTP (a `file://` page cannot fetch the `.wasm`). The server must
  send `application/wasm` for `instantiateStreaming`.
- Embed the game page in another page with
  `<iframe src="index.html" width="1280" height="720" allow="autoplay"></iframe>`.
- Audio starts only after a user gesture; keyboard input needs focus (click first).
- `wasm_exec.js` must match the Go version used to build; it lives in
  `$(go env GOROOT)/lib/wasm/` for current Go releases.
- No ordinary persistent OS file system: small saves can use `localStorage` via
  `syscall/js`; handle quota/unavailable storage. Larger data may need IndexedDB.
- For itch.io upload, zip `dist/` with `index.html` at the top level and test the actual hosted page.
  For page setup and butler uploads, see `itch-publish`.

## Mobile

Install the binder and create a mobile package that registers the game with
`mobile.SetGame` (not `RunGame`) and exports at least one function:

```sh
go install github.com/hajimehoshi/ebiten/v2/cmd/ebitenmobile@v2.10.6
```

```go
package mygamemobile

import (
	"github.com/hajimehoshi/ebiten/v2/mobile"

	"example.com/mygame/game"
)

func init() { mobile.SetGame(game.New()) }

// Dummy is exported because gomobile skips packages without exported functions.
func Dummy() {}
```

```sh
ebitenmobile bind -target android -javapkg com.example.mygame -o mygame.aar ./mobile
ebitenmobile bind -target ios -o MyGame.xcframework ./mobile
```

The Android `.aar` provides an `EbitenView`; call its `suspendGame()`/`resumeGame()`
from `onPause`/`onResume`. The iOS framework provides a view controller to
subclass. Requirements: Android SDK/NDK via Android Studio (ebitenmobile defaults
to minimum API 21; `-androidapi` sets it), Xcode
for iOS 13+. For this layout, move the game type out of `package main` into a
package (here `game`) that both `main` and the mobile package import.

## Release checklist

- [ ] Run relevant rules/static checks; inspect advisory checker findings.
      Linux tests that initialize graphics run under `xvfb-run -a`.
- [ ] Headless frame capture looks right; one manual play-through per platform.
- [ ] Promised resize/fullscreen/pause/quit behavior and persistent saves work.
- [ ] Every advertised input method supports its intended play/menu flow; browser
      build tested for focus and sound after the first input.
- [ ] Licence files for fonts, music and art ship with the build.
- [ ] Version stamped (`-ldflags "-X main.version=…"`, shown on the title or
      options screen) so bug reports name a build.
- [ ] Distribution: the publishing-and-platforms reference. Automated builds:
      the ci-and-release reference. Test the final archive after extraction.

Sources: [v2.10 installation/runtime requirements](https://ebitengine.org/en/documents/install.html),
[WebAssembly](https://ebitengine.org/en/documents/webassembly.html),
[mobile setup](https://ebitengine.org/en/documents/mobile.html).
