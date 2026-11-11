# Input

API baseline: Ebitengine v2.10.6. Snippets are patterns to adapt, with the
project's imports, initialization and validation.

## Contents

- [Rules](#rules)
- [Actions instead of keys](#actions-instead-of-keys)
- [Menus: key repeat](#menus-key-repeat)
- [Gamepads](#gamepads)
- [Mouse and simple buttons](#mouse-and-simple-buttons)
- [Touch](#touch)
- [Text entry](#text-entry)
- [Device prompts and cancellation](#device-prompts-and-cancellation)
- [Browsers](#browsers)

## Rules

- Read input in `Update`, once per tick. `inpututil` tracks press and release
  edges per tick and must not be called from `Draw`.
- Held state: `ebiten.IsKeyPressed`, `IsMouseButtonPressed`,
  `IsStandardGamepadButtonPressed`. Edges: `inpututil.IsKeyJustPressed`,
  `IsKeyJustReleased`, `IsMouseButtonJustPressed`,
  `IsStandardGamepadButtonJustPressed`, `AppendJustPressedTouchIDs`.
- Multi-key constants such as `ebiten.KeyShift` work with `IsKeyPressed` but never
  report "just pressed"; use `KeyShiftLeft`/`KeyShiftRight` for edges.
- Collect IDs with the `Append*` functions into a reused slice:
  `pads = ebiten.AppendGamepadIDs(pads[:0])`. The slice-returning forms
  (`GamepadIDs`, `TouchIDs`, `inpututil.PressedKeys`) are deprecated.
- Positions from `ebiten.CursorPosition`, `CursorPositionF` and `TouchPosition`
  use the engine's default mapping to `Layout` coordinates. A custom
  `DrawFinalScreen` transform also needs matching input conversion
  (rendering reference).

## Actions instead of keys

Translate devices into an `Actions` value at the top of `Update` and let game code
read only actions. This keeps keyboard, gamepad and touch equivalent and makes
scripted input (tests, demos, replays) trivial: replace the device reader. The
starter's `input.go` is a complete example.

### Rebindable bindings

```go
type Action int

const (
	ActLeft Action = iota
	ActRight
	ActJump
	actCount
)

type Bindings struct {
	Keys    [actCount][]ebiten.Key
	Buttons [actCount][]ebiten.StandardGamepadButton
}

func DefaultBindings() Bindings {
	var b Bindings
	b.Keys[ActLeft] = []ebiten.Key{ebiten.KeyArrowLeft, ebiten.KeyA}
	b.Keys[ActRight] = []ebiten.Key{ebiten.KeyArrowRight, ebiten.KeyD}
	b.Keys[ActJump] = []ebiten.Key{ebiten.KeySpace, ebiten.KeyZ}
	b.Buttons[ActLeft] = []ebiten.StandardGamepadButton{ebiten.StandardGamepadButtonLeftLeft}
	b.Buttons[ActRight] = []ebiten.StandardGamepadButton{ebiten.StandardGamepadButtonLeftRight}
	b.Buttons[ActJump] = []ebiten.StandardGamepadButton{ebiten.StandardGamepadButtonRightBottom}
	return b
}

// Held aggregates all bindings before deriving the action's press edge.
func (b *Bindings) Held(a Action, pads []ebiten.GamepadID) bool {
	for _, k := range b.Keys[a] {
		if ebiten.IsKeyPressed(k) {
			return true
		}
	}
	for _, id := range pads {
		if !ebiten.IsStandardGamepadLayoutAvailable(id) {
			continue
		}
		for _, btn := range b.Buttons[a] {
			if ebiten.IsStandardGamepadButtonPressed(id, btn) {
				return true
			}
		}
	}
	return false
}

type ActionState struct {
	Held, Pressed [actCount]bool
}

// Sample runs once at the top of each Update, including while menus are open.
func (s *ActionState) Sample(b *Bindings, pads []ebiten.GamepadID) {
	for a := Action(0); a < actCount; a++ {
		held := b.Held(a, pads)
		s.Pressed[a] = held && !s.Held[a]
		s.Held[a] = held
	}
}

// Rebind waits for the next key press and assigns it to the action.
// Call it from Update while a "press a key" prompt is shown.
func (b *Bindings) Rebind(a Action, buf []ebiten.Key) (done bool) {
	buf = inpututil.AppendJustPressedKeys(buf[:0])
	if len(buf) == 0 {
		return false
	}
	b.Keys[a] = []ebiten.Key{buf[0]}
	return true
}
```

This defines an action edge as up → down across all bindings: pressing a second
jump key while the first is held does not retrigger jump. If a game wants each
physical press to trigger, aggregate binding edges instead and document that
choice. Axis bindings need a dead zone and, for digital actions, a threshold.

Persist bindings with the save data (see the architecture-and-testing reference). Ignore
the input that opened the rebind prompt, provide cancel/reset and conflict
handling, and re-sample held state when a binding changes. Show key names with
`ebiten.KeyName(key)`; it reflects the layout for named printable keys but may
return an empty string. Supply labels for arrows, modifiers and unsupported
platforms (for example a table, with `key.String()` as a final fallback).
For engine-neutral rebinding and remapping UX, see `input-systems`.

## Menus: key repeat

Holding a direction in a menu should move once, pause, then repeat.
`inpututil.KeyPressDuration` returns how many ticks the key has been held:

```go
func repeating(key ebiten.Key) bool {
	d := inpututil.KeyPressDuration(key) // ticks held, 0 if up
	return d == 1 || (d >= 20 && (d-20)%4 == 0)
}
```

`StandardGamepadButtonPressDuration` does the same for pads.

## Gamepads

- Prefer the standard layout (W3C "standard gamepad"): check
  `ebiten.IsStandardGamepadLayoutAvailable(id)`, then use
  `StandardGamepadButton*` (`RightBottom` is the bottom face button: A on Xbox,
  Cross on PlayStation; `CenterRight` is Start/Options) and
  `StandardGamepadAxisValue` (−1…1; −1 is left/up).
- Pads without a standard mapping expose raw `GamepadButton`/`GamepadAxisValue`
  indices that differ per device; offer rebinding rather than guessing.
- Apply a dead zone to sticks:

```go
func stickX(id ebiten.GamepadID) float64 {
	v := ebiten.StandardGamepadAxisValue(id, ebiten.StandardGamepadAxisLeftStickHorizontal)
	const dead = 0.2
	switch {
	case v > dead:
		return (v - dead) / (1 - dead)
	case v < -dead:
		return (v + dead) / (1 - dead)
	}
	return 0
}
```

- Hot-plugging: `inpututil.AppendJustConnectedGamepadIDs` and
  `inpututil.IsGamepadJustDisconnected(id)`; pause the game when the active
  player's pad disconnects. No IDs are reported before the game starts.

## Mouse and simple buttons

```go
type Button struct {
	X, Y, W, H int
	armed      bool
}

func (b Button) Hover() bool {
	x, y := ebiten.CursorPosition() // already in Layout's coordinates
	return x >= b.X && x < b.X+b.W && y >= b.Y && y < b.Y+b.H
}

// Update activates only when the press began here and the release is inside.
func (b *Button) Update() bool {
	if inpututil.IsMouseButtonJustPressed(ebiten.MouseButtonLeft) {
		b.armed = b.Hover()
	}
	if inpututil.IsMouseButtonJustReleased(ebiten.MouseButtonLeft) {
		clicked := b.armed && b.Hover()
		b.armed = false
		return clicked
	}
	return false
}
```

Reset `armed` when the UI loses focus or closes. Overlapping widgets need one
input owner; touch needs the same press-origin rule tied to a specific TouchID.
Keyboard/gamepad confirmation should activate the focused widget.

With a camera, convert the cursor with the inverse camera transform
(rendering reference). `ebiten.Wheel()` returns scroll offsets for this tick.
`ebiten.SetCursorMode(ebiten.CursorModeCaptured)` locks the cursor for mouse-look.

## Touch

`ebiten.AppendTouchIDs` lists current touches and `TouchPosition(id)` gives their
positions; `inpututil.AppendJustPressedTouchIDs` and `IsTouchJustReleased` give
edges; `TouchPressDuration` distinguishes taps from holds. Desktop builds report
no touches, and `CursorPosition` is always (0, 0) in mobile apps, so support both
paths if the game runs on both. Make touch targets at least about 44
device-independent pixels at the expected scale; 44 game pixels in a small
logical viewport can be much larger. Check targets on the target device.

## Text entry

- Short Latin input (names, codes): append `ebiten.AppendInputChars(buf[:0])`
  each tick, handle Backspace with `repeating(ebiten.KeyBackspace)`.
- Japanese and other IME input: `github.com/hajimehoshi/ebiten/v2/exp/textinput`
  supports composition, but it is experimental and its API is changing (v2.10
  deprecates `Field` in favour of `Composer`). Follow `examples/textinput` for the
  pinned version.

## Device prompts and cancellation

For games supporting several devices, derive prompts from the current binding
and meaningful recent input, not hardcoded default key names. Use dead zones
and a stability policy so stick drift or incidental mouse motion does not
continually swap the prompt set. Cancel held actions on the appropriate focus,
disconnect or scene boundary; never leave a touch/capture armed after its input
owner disappears. This cleans up transient held/armed/capture state, not semantic
selection: an intentionally selected card or inventory item may remain selected
across a settings modal. Reconcile held controls on return so the closing press
does not leak into gameplay. This adapts the prompt/state lessons in
[game-ui-design](https://github.com/omer-metin/skills-for-antigravity/blob/e8dcf4e8737921a10088bd5c9eb65e81f74c051f/skills/game-ui-design/references/patterns.md)
and [Three.js touch UI](https://github.com/majidmanzarpour/threejs-game-skills/blob/8286774b22a2566bf894dbc825825c16921866af/skills/threejs-game-ui-designer/references/ui-patterns.md).
Browser pointer-event names do not translate directly into Ebitengine APIs.

## Browsers

Keyboard events reach the game only while its canvas or iframe has focus. Ask the
player to click or tap the game first (a title screen does this naturally), and
avoid browser shortcuts (Ctrl+W, F5) as game controls.

Source contracts: [input APIs](https://github.com/hajimehoshi/ebiten/blob/v2.10.6/input.go)
and [tick-based edge helpers](https://github.com/hajimehoshi/ebiten/blob/v2.10.6/inpututil/inpututil.go).
