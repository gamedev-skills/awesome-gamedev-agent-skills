# Architecture and testing

API baseline: Ebitengine v2.10.6. Snippets illustrate patterns to adapt; a
production project must supply imports, initialization and validation.

## Contents

- [Package layout](#package-layout)
- [Scenes](#scenes)
- [Resource and callback lifetime](#resource-and-callback-lifetime)
- [Entities](#entities)
- [Randomness](#randomness)
- [Saving](#saving)
- [Testing](#testing)
- [Debugging](#debugging)

## Package layout

```text
mygame/
├── go.mod
├── main.go          # flags, window setup, ebiten.RunGame
├── game.go          # type Game: Update/Draw/Layout, scene switching
├── input.go         # devices -> actions
├── assets.go        # //go:embed + decoding, done once
├── sound.go         # audio context and players
├── scenes.go        # title, play, results...
├── world/           # rules: no Ebitengine import, unit-tested
└── assets/          # png, ogg, wav, ttf + licence files
```

Keep `main` thin. Rules deciding *what happens* (movement, collision, scoring,
turn order, card effects, AI) are easier to test in a package without Ebitengine,
using explicit inputs and simulation steps where appropriate. It can then be tested
with `go test` on any machine, replayed, and reused on a server. The starter's
`world` package is this split.

## Scenes

A scene owns its state and implements `Update` and `Draw`. Switch scenes between
ticks, and keep a stack when a scene overlays another (pause, dialogue, inventory).

```go
type Scene interface {
	Update(m *Manager) error
	Draw(screen *ebiten.Image)
}

type Manager struct {
	stack   []Scene // top is active; lower scenes stay drawn (pause overlays)
	next    Scene
	fade    int // ticks left in the current fade
	fadeLen int
}

func (m *Manager) Push(s Scene) { m.stack = append(m.stack, s) }
func (m *Manager) Pop()         { m.stack = m.stack[:len(m.stack)-1] }

// Replace fades out, swaps the whole stack for s, and fades in.
func (m *Manager) Replace(s Scene, ticks int) {
	ticks = max(0, ticks)
	m.next, m.fade, m.fadeLen = s, ticks*2, ticks
}

func (m *Manager) Update() error {
	if m.fade == 0 && m.next != nil { // zero-length transition: next tick
		m.stack, m.next = []Scene{m.next}, nil
	}
	if m.fade > 0 {
		m.fade--
		if m.fade == m.fadeLen && m.next != nil { // midpoint: screen is black
			m.stack, m.next = []Scene{m.next}, nil
		}
		return nil // ignore input while fading
	}
	return m.stack[len(m.stack)-1].Update(m)
}

func (m *Manager) Draw(screen *ebiten.Image) {
	for _, s := range m.stack {
		s.Draw(screen)
	}
	if m.fade > 0 {
		t := float32(m.fade-m.fadeLen) / float32(m.fadeLen) // 1 -> 0 while fading out
		if t < 0 {
			t = -t // 0 -> 1 while fading in
		}
		alpha := uint8(255 * (1 - t))
		w, h := screen.Bounds().Dx(), screen.Bounds().Dy()
		vector.FillRect(screen, 0, 0, float32(w), float32(h), color.RGBA{0, 0, 0, alpha}, false)
	}
}
```

Load a level's heavy assets when its scene is created, not during the fade.
Initialize the manager with a non-empty stack; prevent popping the last scene
and reject nil replacements at the call boundary. For loading that would stall
play, use a loading scene and a deliberate CPU decoding/GPU upload policy.

## Resource and callback lifetime

Make ownership explicit for a scene's load jobs, cached resources, subscriptions,
timers and audio streams. Deduplicate concurrent loads of the same asset when
needed, but clear failed in-flight entries so a retry can actually run. A shared
resource must not be released just because one scene stopped using it.

For asynchronous work, tag results with a scene/request generation. Apply them
at an update boundary only if that owner is still current; cancel or discard a
late completion after leaving/restarting. Unsubscribe scene listeners and stop
owned workers on exit so revisiting a screen does not double-trigger events.
Load and validate the next scene before replacing a working one when failure
needs to be recoverable. This adapts resource and scene lifecycle principles from
[game-engine](https://github.com/github/awesome-copilot/blob/2d4b998d2df28917074ee33db45c9601484c72ad/skills/game-engine/references/game-engine-core-principles.md).
It does not require a reference-counted asset manager, ECS or custom allocator
in every Go game.

## Entities

Plain structs in slices are a useful starting point. Reuse capacity in hot paths;
structs alone do not guarantee allocation-free updates. Remove by swapping with
the last element only when entity order is unimportant:

```go
type Bullet struct {
	X, Y, VX, VY float64
	Life         int
}

func stepBullets(bs []Bullet) []Bullet {
	for i := 0; i < len(bs); {
		b := &bs[i]
		b.X += b.VX
		b.Y += b.VY
		b.Life--
		if b.Life <= 0 {
			bs[i] = bs[len(bs)-1]
			bs = bs[:len(bs)-1]
			continue
		}
		i++
	}
	return bs
}
```

- Collision for platformers and top-down games: move one axis at a time and
  resolve against the tile grid (starter `world.moveX`/`moveY`). Choose a broad phase
  (for example a uniform grid) when collision profiling warrants it.
- Fast objects can pass through thin walls in one tick; use swept collision or
  substeps chosen for the collider geometry. Test high speeds and corners;
  the starter's axis-separated grid solver is not a general physics engine.
- Collect what happened in a tick as events (jumped, landed, hit) and let the
  presentation layer play sounds and spawn particles from them.

## Randomness

Use a seeded generator owned by the game state so runs can be reproduced with
the same input sequence, content, rules version and update order:

```go
func newRNG(seed uint64) *rand.Rand {
	return rand.New(rand.NewPCG(seed, seed^0x9e3779b97f4a7c15))
}
```

(`math/rand/v2`.) Keep separate generators for gameplay and cosmetic effects so
particles do not change the gameplay sequence.
The seed alone is insufficient: avoid gameplay decisions based on map iteration
order or wall-clock time, and record inputs and the game version for replays.

## Saving

```go
type SaveData struct {
	Version  int  `json:"version"`
	BestTime int  `json:"best_time_ticks"`
	Muted    bool `json:"muted"`
}

func savePath(game string) (string, error) {
	dir, err := os.UserConfigDir()
	if err != nil {
		return "", err
	}
	return filepath.Join(dir, game, "save.json"), nil
}

func Save(game string, d SaveData) error {
	p, err := savePath(game)
	if err != nil {
		return err
	}
	if err := os.MkdirAll(filepath.Dir(p), 0o755); err != nil {
		return err
	}
	b, err := json.MarshalIndent(d, "", "  ")
	if err != nil {
		return err
	}
	f, err := os.CreateTemp(filepath.Dir(p), ".save-*.tmp")
	if err != nil {
		return err
	}
	tmp := f.Name()
	defer os.Remove(tmp)
	if _, err := f.Write(b); err != nil {
		f.Close()
		return err
	}
	if err := f.Sync(); err != nil {
		f.Close()
		return err
	}
	if err := f.Close(); err != nil {
		return err
	}
	return os.Rename(tmp, p)
}

func Load(game string) (SaveData, error) {
	d := SaveData{Version: 1}
	p, err := savePath(game)
	if err != nil {
		return d, err
	}
	b, err := os.ReadFile(p)
	if errors.Is(err, fs.ErrNotExist) {
		return d, nil // first run
	}
	if err != nil {
		return d, err
	}
	if err := json.Unmarshal(b, &d); err != nil {
		return d, err
	}
	return d, nil
}
```

- This writes a separate temporary file before replacing the old save. It is
  not a universal crash-safety guarantee: Go does not promise atomic rename on
  non-Unix platforms, and power-loss durability can require directory syncing
  and platform-specific replacement. Keep a validated backup where save loss
  matters. Serialize saves and validate/migrate decoded versions before use.
- Save before quitting: `ebiten.SetWindowClosingHandled(true)`, then in `Update`
  check `ebiten.IsWindowBeingClosed()`, save, and return `ebiten.Termination`.
  This handles a desktop close request, not a process kill, browser unload or
  mobile termination; save progress at appropriate checkpoints too.
- Browsers have no user config directory; store small saves in `localStorage`
  through `syscall/js` behind a `//go:build js` file.
- Include a format version, migrate supported old formats and report unsupported
  versions without overwriting them. Recover malformed data from a validated
  backup or show a recoverable error. For engine-neutral save design and
  migration, see `save-systems`.

## Testing

For controlled action sequences and matching state/image diagnostics, read
the playtest-diagnostics reference. The capture helper below only
writes pixels; it does not establish that a complete interaction succeeded.

1. **Rules:** `go test ./world/...` with table tests and fixed seeds. Step the
   world N ticks with scripted inputs and assert positions, scores and events.
   Add a determinism test (same inputs twice, same state).
2. **Static checks:** `go vet ./...` and the skill's
   `scripts/check_ebitengine.py .`. The checker is a heuristic, not a proof of
   correct code or API support.
3. **Rendering smoke test:** run the game with scripted input and capture a frame
   (the starter's `-demo -shot FILE -shot-tick N`), on Linux under `xvfb-run -a`
   with a null audio device if there is no sound card (see the audio reference). Look at
   the PNG; for regression checks compare against a stored image with a small
   per-channel tolerance, since GPU drivers differ slightly.
4. **Opt-in VM testing:** Ebitengine's
   `run-ebitengine-app-headless` skill, when present for the project's pinned
   version, drives a game through the experimental
   `exp/vmhost` package: injected keyboard/mouse/touch/gamepad input, ticks
   faster than real time, frame readback, observed audio. Rebuild the app with
   `ebitenginevmguest` and configure `EBITENGINE_VM_ENDPOINT`, or use
   `RunGameOptions.VMGuestEndpoint`. It requires matching engine versions and
   a graphics environment for the host; it is not a software renderer.
5. **Builds:** compile the advertised targets (see the project-and-builds reference), then
   run the resulting artifacts in their target environments. Compilation alone
   does not validate packaging, SDKs, input, storage or audio.
6. **People:** feel, difficulty and audio quality still need someone playing.
   Report what was not checked.

On Linux, any tests importing graphics-backed Ebitengine packages may require
initializing a display even without a test calling `RunGame`; run those under
`xvfb-run -a`. Keep pure rules tests independent of the engine.

Capturing a frame from inside the game (call from `Draw`; pixels are
premultiplied RGBA, which equals straight RGBA when the screen is opaque):

```go
func savePNG(screen *ebiten.Image, path string) error {
	img := image.NewRGBA(screen.Bounds())
	screen.ReadPixels(img.Pix)
	f, err := os.Create(path)
	if err != nil {
		return err
	}
	if err := png.Encode(f, img); err != nil {
		f.Close()
		return err
	}
	return f.Close()
}
```

## Debugging

- `ebitenutil.DebugPrint(screen, fmt.Sprintf("TPS %.1f FPS %.1f", ebiten.ActualTPS(), ebiten.ActualFPS()))`.
- `go run -tags=ebitenginedebug .` logs the draw commands issued each frame.
- Desktop games keep running when unfocused (the default of
  `ebiten.SetRunnableOnUnfocused`); call it with `false` to pause in the
  background. Browsers throttle background tabs regardless.
- Errors returned from `Update` stop the game and come back from `RunGame`; return
  wrapped errors instead of `log.Fatal` deep inside scenes.

Source contracts: [game loop and focus policy](https://github.com/hajimehoshi/ebiten/blob/v2.10.6/run.go)
and [Go file replacement guarantees](https://pkg.go.dev/os#Rename).
