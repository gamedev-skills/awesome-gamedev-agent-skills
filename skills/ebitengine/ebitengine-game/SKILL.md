---
name: ebitengine-game
description: >
  Creates, debugs and packages 2D games in Go with Ebitengine v2: a play-and-retry loop, input,
  pixel-art scaling, text, audio and desktop, WASM or mobile builds. Use when go.mod requires
  ebiten/v2 or the user wants a game in Go, or on blurry pixel art, missed key presses or stutter.
  Not for engine patches; pair with `game-feel`, `game-ui-ux` or a genre skill for design.
---

# Ebitengine game

Deliver a game that is understandable, responsive and complete at the requested scope. A
scaffold, a clean build or a good screenshot alone is not a finished game. For a focused
fix, keep the project's design and touch only the affected behaviour.

The bundled starter targets **Ebitengine v2.10.6 / Go 1.25+**. Keep an existing project's
versions unless an upgrade is needed and authorized, and check the pinned version's API
before using newer or experimental APIs. Only the bundled scripts and starter are tested
deliverables; reference snippets are patterns to adapt.

## Delivery workflow

1. **Inspect and decide.** Read repository instructions, `go.mod`, the `RunGame` entry
   point and existing tests and assets. For a new game, read
   [Design and quality](references/design-and-quality.md). Settle the player's goal,
   repeated decision, consequence, end/retry path, look, platform and inputs; infer
   defaults and ask only about choices that change the product. Write a short brief with
   observable acceptance criteria into the project.
2. **Build a representative playable slice.** Make the central interaction and its
   feedback work with the intended controls and look before adding content. Calibrate
   content against what the player can actually do. For an art set, fix perspective,
   scale, anchors and palette first ([Assets and animation](references/assets-and-animation.md)).
3. **Complete and refine.** Implement the promised start → play → outcome →
   retry/continue loop (or the right persistent/sandbox loop). Refine hierarchy,
   animation, sound, difficulty and transitions in context, reading only the references
   for the systems you use. Fix the defects you find within this delivery.
4. **Verify the product** with the commands under Verification: rules and transitions in
   tests, real input paths, rendered states at important moments, and every promised
   target built. Include failure/retry and boundary cases. For multi-step scripted
   interactions, pair each image with the game state at the same tick
   ([Playtest diagnostics](references/playtest-diagnostics.md)).
5. **Hand off.** Give launch/build instructions, actual artifact paths and asset licences.
   State what was run and observed and what was not. A scripted demo cannot judge control
   feel and a null audio sink cannot judge sound, so ask the user to play a session and
   report on feel, audio and difficulty. Publishing, purchases and uploads are separate
   actions that need the user's go-ahead.

## Starting a project

Run the scripts from this skill's directory (set `skill_dir` to where it is installed):

```sh
python3 "$skill_dir/scripts/new_game.py" --out mygame \
  --module example.com/mygame --title "My Game"
cd mygame
go mod tidy
go test ./world/...
```

The starter is a small **platformer** that demonstrates scenes, action input, text, sound,
a camera, pause and scripted capture. It is an integration example, not a template for
every genre: a puzzle or card game should drop gravity, jumping, camera scrolling and the
platformer HUD. Existing projects rarely need it. `--ci` adds a GitHub Actions workflow
and its tools; read its triggers, targets and release steps before enabling it. For a
macOS release, `scripts/package_macos_app.py` assembles a (universal) `.app` from built
binaries; run it with `--help` first, and sign and notarize separately on a Mac.

## Loop and resource contracts

| Method | Responsibility | Important distinction |
| --- | --- | --- |
| `Update() error` | Sample actions, advance simulation, apply scene changes, trigger event audio | 60 fixed ticks/s by default. Catch-up updates, focus pauses and slow machines change the real schedule. |
| `Draw(screen *ebiten.Image)` | Render the state the updates produced | Not one call per tick. Never advance gameplay, consume input edges or start sounds here. |
| `Layout(outsideW, outsideH int) (int, int)` | Choose the logical size for rendering and input | Fixed and responsive designs are both valid; check small windows, aspect ratio and readability. |

- Express durations in ticks or an explicit fixed `dt` (30 ticks = 0.5 s at 60 TPS).
- Return `ebiten.Termination` from `Update` for a clean stop; propagate other errors out of
  `RunGame`.
- Decode images and parse font sources once; reuse offscreens and hot-path slices.
- Keep rules apart from device and GPU code so they are testable. A small game does not
  need an ECS, scene stack or service layer.

## Essential Ebitengine choices

- **Input:** map devices to actions in `Update`; separate held, pressed and released;
  check gamepad availability and apply stick dead zones. [Input](references/input.md).
- **Rendering:** `GeoM` operations apply in call order. Choose sampling deliberately for
  pixel art versus smooth art. A custom final-screen transform needs matching pointer
  conversion. [Rendering](references/rendering.md).
- **Text/UI:** keep a suitable existing bitmap or atlas renderer; new outline-font code uses
  `text/v2` with fonts that cover the shipped scripts (and their licences). Measure real
  strings and check focus and long text. [Text/UI](references/text-and-ui.md).
- **Audio:** one `audio.Context` per process; match sample rate and PCM format; give
  overlapping effects their own players. [Audio](references/audio.md).
- **Systems:** tweens, particles, shake, physics and map loaders are optional helpers for
  the central interaction. [Gameplay systems](references/gameplay-systems.md).
- **State:** queue external callbacks into `Update`, make reset/retry complete, split
  gameplay and cosmetic randomness, and test saves when persistence is promised.
  [Architecture/testing](references/architecture-and-testing.md).

## Verification

Run from the game directory and keep `go.mod` and `go.sum`. `-buildvcs=false` avoids
depending on surrounding Git metadata.

```sh
go vet ./...
go test ./world/...   # the starter's GPU-independent rules; run your other packages too
python3 "$skill_dir/scripts/check_ebitengine.py" .
go build -buildvcs=false -o game .
```

Run the checker after changing loop, input or audio code or when reviewing old APIs. It is
a read-only text scan: warnings (deprecated APIs, `ReadPixels`, work in `Draw`) need a look
in context, and notes (ambiguous `.At()` calls the scanner cannot type) never fail
`--strict`. `--json` prints the shared checker schema with `note_count` and `notes`;
`--max-issues N` caps the report without changing totals. A clean result proves neither
correctness nor quality.

Capture the starter with `-demo -shot frame.png -shot-tick 240`. On Linux, use a virtual
display and, if there is no sound card, a null ALSA device without touching `HOME`:

```sh
audio_config=$(mktemp)
printf 'pcm.!default { type null }\n' > "$audio_config"
ALSA_CONFIG_PATH="$audio_config" xvfb-run -a ./game \
  -demo -shot frame.png -shot-tick 240
rm "$audio_config"
```

Open the PNG, then capture other states that matter: first play, a busy moment, failure and
the outcome screen. Once the game differs from the template, update the scripted actions and
capture points; the template demo proves nothing about another loop. Tests that initialize
graphics need `xvfb-run -a` on Linux. For injected input and replay tests, v2.10's opt-in
`exp/vmhost` is covered in [Architecture/testing](references/architecture-and-testing.md).

Build only the promised targets, for example:

```sh
GOOS=windows GOARCH=amd64 go build -buildvcs=false -o game.exe .
GOOS=js GOARCH=wasm go build -buildvcs=false -o game.wasm .
```

Cross-compiling proves buildability, not runtime support. Serve browser builds over HTTP
and check the console, input and audio. Native SDKs, store bindings and cgo dependencies add
requirements beyond Ebitengine's pure-Go desktop backend.

## Gotchas

- **A key press is sometimes missed, or fires twice** → input edges (`inpututil.IsKeyJustPressed`
  and friends) are tick-based. Read them once per tick in `Update`, never in `Draw`, and
  combine bindings before computing an action's edge.
- **Animation or gameplay speed changes with the monitor's refresh rate** → state advances
  in `Draw`, or code uses `ActualTPS`/`ActualFPS` as a delta. Advance in `Update` by ticks.
  `SetTPS` changes the whole clock, so it is not a slow-motion switch.
- **Sprite rotates around the wrong point or drifts** → `GeoM` applies in call order:
  translate the pivot to the origin, scale and rotate, then translate to the position.
- **Pixel art is blurry or uneven** → sampling and scale policy were not chosen. Read the
  scaling section of the rendering reference; strict integer scaling with a custom final
  screen also needs matching cursor conversion.
- **A sound plays about 9% fast and high, or as noise** → `DecodeF32` does not resample, and
  F32 streams need the `…F32` players. Convert assets to the context rate or use
  `DecodeWithSampleRate` with `NewPlayer`.
- **`audio: context is already created` panic** → `audio.NewContext` ran twice. Create one
  context at start-up and pass it around (`audio.CurrentContext()` returns it).
- **A rapid sound effect cuts itself off** → one `audio.Player` is rewound for every hit.
  Use a small voice pool and cap concurrent voices.
- **No sound in the browser** → browsers allow audio only after a user gesture. Start
  music from a title-screen action and check `ctx.IsReady()`; an embedding iframe needs
  `allow="autoplay"`.
- **Frame rate drops when text is on screen** → a font file is parsed with
  `text.NewGoTextFaceSource` every frame, or `Size` is animated (glyphs are rebuilt per
  size). Parse each font once and keep the source; to zoom text, scale a pre-drawn image.
- **The HUD shows an old value** → text was cached (an image or a wrapped layout) and not
  rebuilt when the value changed. Rebuild the cache on change, or draw the text directly.
- **The game hangs or slows at a `ReadPixels`/`At` call** → GPU readback waits for the GPU,
  and `ReadPixels` cannot run before `RunGame`. Keep it to tests and screenshots.
- **Deprecation warnings from the checker** → `ebiten.DeviceScaleFactor` →
  `ebiten.Monitor().DeviceScaleFactor()`; `inpututil.PressedKeys` →
  `AppendPressedKeys`; `ebiten.GamepadIDs`/`TouchIDs` → `AppendGamepadIDs`/`AppendTouchIDs`;
  `text.Advance` → `text.AdvanceAt`. Deprecated code still builds; change it when touched.
- **Visible stutter when the frame rate is near the TPS (or a multiple of it), at startup or
  after a long frame** → fixed in v2.10.6 (issue 4015). Upgrade an older v2.10 pin before
  tuning the game's own timing.
- **`go: go.mod requires go >= 1.25.0 (running go 1.22…; GOTOOLCHAIN=local)`** → the local
  Go is older than v2.10 needs. Install
  Go 1.25+, or allow the toolchain download (`GOTOOLCHAIN=auto`, the default).

## Compose within this catalog

This skill owns Ebitengine and Go APIs. For portable design, pair it with the relevant
discipline (`game-ui-ux`, `game-feel`, `audio-design`, `create-game-assets`,
`input-systems`, `performance-optimization`, `save-systems`), a genre skill or a shipping
workflow, and bind their engine slots to this skill's references rather than another
engine's code. The folder also works on its own.

## Read as needed

- [Design and quality](references/design-and-quality.md): for a new game or redesign; brief,
  genre structure, complete loop, presentation and playtest acceptance.
- [Project and builds](references/project-and-builds.md): when setting up, building desktop,
  WASM or mobile targets, or writing the release checklist.
- [Rendering](references/rendering.md), [input](references/input.md),
  [text/UI](references/text-and-ui.md), [audio](references/audio.md): when changing that
  system.
- [Assets and animation](references/assets-and-animation.md): when making or importing an
  art set; shared visual rules, pivots and sprite-sheet checks.
- [Playtest diagnostics](references/playtest-diagnostics.md): when scripting interactions or
  reproducing a failure; controlled ticks with paired state and image evidence.
- [Architecture/testing](references/architecture-and-testing.md): when structuring scenes,
  entities, saves, randomness or tests, or using `exp/vmhost`.
- [Gameplay systems](references/gameplay-systems.md): when adding tweens, animation state,
  particles, shake and hit-stop, or rigid bodies. [Tiled maps](references/tilemaps.md):
  only when levels come from Tiled.
- [Networking](references/networking.md): only for requested online play.
- [Publishing/platforms](references/publishing-and-platforms.md),
  [monetization](references/monetization.md), [CI/release](references/ci-and-release.md):
  only for requested distribution, store or automation work.

Ebitengine's own repository has agent skills under `skills/` on its main branch
(`run-ebitengine-app-headless`, `writing-kage-shaders`, `avoiding-blurry-ebitengine-rendering`,
`efficient-ebitengine-rendering`). Use them when installed for headless input injection,
Kage shaders and rendering performance, and check that what they describe exists in the
project's pinned version: they track the next release.

## Version notes

Last verified: 2026-11-11.

- Ebitengine v2.10.6 (2026-11-07) is the latest stable release; v2.11.0-alpha exists. v2.10.6
  changes only the internal tick clock (the stutter fix, issue 4015) and the PureGo
  dependency, so the v2.10.5 API notes in the references carry over unchanged.
- Ebitengine v2.10 needs Go 1.25 or later (`go 1.25.0` in its `go.mod`).
- The starter was generated with `new_game.py` (default `--ebiten v2.10.6`), then
  `go mod tidy`, `go vet`, `go test ./world/...`, the checker, native, Windows and WASM
  builds and the Xvfb capture above were run with Go 1.25.0.
- Sources: [Go module proxy](https://proxy.golang.org/github.com/hajimehoshi/ebiten/v2/@latest),
  [v2.10 release notes](https://ebitengine.org/en/documents/2.10.html),
  [v2.10.5...v2.10.6 diff](https://github.com/hajimehoshi/ebiten/compare/v2.10.5...v2.10.6),
  [issue 4015](https://github.com/hajimehoshi/ebiten/issues/4015),
  [repository skills](https://github.com/hajimehoshi/ebiten/tree/main/skills).
