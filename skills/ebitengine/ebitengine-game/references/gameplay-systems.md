# Gameplay systems: tweens, animation, particles, juice, Tiled maps, physics

API baseline: Ebitengine v2.10.6. Advance state in `Update` and render it in
`Draw`. These snippets illustrate individual systems; validate their inputs and
test their integration in the actual game. Choose systems based on the
game design and quality criteria (design-and-quality reference).

Contents: [Tweens and easing](#tweens-and-easing) · [Animation state](#animation-state) · [Particles](#particles) · [Screen shake and hit-stop](#screen-shake-and-hit-stop) · [Tiled maps](#tiled-maps) · [Rigid-body physics (Chipmunk2D)](#rigid-body-physics-chipmunk2d)

## Tweens and easing

Count ticks, not seconds: a tween then plays identically at any frame rate and
in headless runs.

```go
type Ease func(t float64) float64

func Linear(t float64) float64   { return t }
func OutCubic(t float64) float64 { u := 1 - t; return 1 - u*u*u }
func InOutCubic(t float64) float64 {
	if t < 0.5 {
		return 4 * t * t * t
	}
	u := -2*t + 2
	return 1 - u*u*u/2
}
func OutBack(t float64) float64 {
	const c1 = 1.70158
	const c3 = c1 + 1
	u := t - 1
	return 1 + c3*u*u*u + c1*u*u
}

// Tween moves one value from From to To over Ticks updates.
type Tween struct {
	From, To float64
	Ticks    int
	Ease     Ease
	tick     int
}

// Step advances one tick and reports whether the tween has finished.
func (tw *Tween) Step() bool {
	if tw.tick < tw.Ticks {
		tw.tick++
	}
	return tw.tick >= tw.Ticks
}

func (tw *Tween) Value() float64 {
	if tw.Ticks <= 0 {
		return tw.To
	}
	t := float64(tw.tick) / float64(tw.Ticks)
	if tw.Ease != nil {
		t = tw.Ease(t)
	}
	return tw.From + (tw.To-tw.From)*t
}
```

Use `OutCubic` for things arriving (menus sliding in), `InOutCubic` for camera
moves between points, `OutBack` for a small overshoot on pop-ups and score
counters. Keep UI tweens short (8–20 ticks at 60 TPS). For several properties,
use one tween for a 0→1 progress and derive the properties from it.

## Animation state

The rendering reference shows cutting frames from a sheet. A per-entity animator switches
clips without restarting the running one and holds the last frame of one-shot
clips:

Validate clips when loading: at least one frame and `Hold > 0`; call `Play`
before querying the animator. Keep the clip configuration immutable while used.

```go
type Clip struct {
	Frames []*ebiten.Image
	Hold   int  // ticks per frame
	Loop   bool // otherwise stays on the last frame
}

type Animator struct {
	clip *Clip
	tick int
}

// Play switches clips; replaying the current clip does not restart it.
func (a *Animator) Play(c *Clip) {
	if a.clip != c {
		a.clip, a.tick = c, 0
	}
}

func (a *Animator) Update() { a.tick++ }

func (a *Animator) Done() bool {
	return !a.clip.Loop && a.tick >= len(a.clip.Frames)*a.clip.Hold
}

func (a *Animator) Frame() *ebiten.Image {
	i := a.tick / a.clip.Hold
	if a.clip.Loop {
		i %= len(a.clip.Frames)
	} else if i >= len(a.clip.Frames) {
		i = len(a.clip.Frames) - 1
	}
	return a.clip.Frames[i]
}
```

Choose the clip in `Update` from the rules state (`onGround`, `vx`, `hurtTicks`),
call `Play` every tick, and draw `Frame()` in `Draw`. Mirror for facing with
`GeoM.Scale(-1, 1)` around the actor's chosen registration pivot: translate that
pivot to the origin, apply the facing scale, then place the actor in the world.
Use the sprite centre only when it is the chosen pivot. The assets-and-animation
reference covers frame registration.

## Particles

A fixed-capacity pool, its own random generator (so effects never change the
gameplay sequence), no allocation per tick:

```go
type Particle struct {
	X, Y, VX, VY float64
	Life, Max    int
	Size         float32
	Color        color.RGBA
}

type Particles struct {
	ps  []Particle
	rng *rand.Rand // cosmetic generator, separate from gameplay
}

func NewParticles(capacity int, seed uint64) *Particles {
	return &Particles{ps: make([]Particle, 0, capacity), rng: rand.New(rand.NewPCG(seed, 1))}
}

// Burst emits n particles; extra particles are dropped when the pool is full.
func (p *Particles) Burst(x, y float64, n int, speed float64, c color.RGBA) {
	for i := 0; i < n && len(p.ps) < cap(p.ps); i++ {
		a := p.rng.Float64() * 2 * math.Pi
		s := speed * (0.3 + 0.7*p.rng.Float64())
		life := 20 + p.rng.IntN(20)
		p.ps = append(p.ps, Particle{X: x, Y: y, VX: math.Cos(a) * s, VY: math.Sin(a) * s,
			Life: life, Max: life, Size: 2 + 2*p.rng.Float32(), Color: c})
	}
}

func (p *Particles) Update() {
	for i := 0; i < len(p.ps); {
		q := &p.ps[i]
		q.X += q.VX
		q.Y += q.VY
		q.VY += 0.15 // gravity
		q.VX *= 0.96 // drag
		q.Life--
		if q.Life <= 0 {
			p.ps[i] = p.ps[len(p.ps)-1]
			p.ps = p.ps[:len(p.ps)-1]
			continue
		}
		i++
	}
}

func (p *Particles) Draw(dst *ebiten.Image, camX, camY float64) {
	for _, q := range p.ps {
		k := float32(q.Life) / float32(q.Max)
		c := q.Color
		c.A = uint8(float32(c.A) * k)
		c.R, c.G, c.B = uint8(float32(c.R)*k), uint8(float32(c.G)*k), uint8(float32(c.B)*k) // premultiplied
		vector.FillRect(dst, float32(q.X-camX)-q.Size/2, float32(q.Y-camY)-q.Size/2, q.Size, q.Size, c, true)
	}
}

func (p *Particles) Len() int { return len(p.ps) }
```

Spawn bursts from the rules' events (`Landed`, `Coin`, `Hit`), not from inside
the rules. Colours are premultiplied, so fading scales R, G, B and A together.
Profile the expected particle count on the target devices. If individual shape
draws are a bottleneck, draw a pre-rendered small image per particle with
`DrawImage` or batch geometry with `DrawTriangles32` (its `uint32` indices are not
capped at 65,536 vertices like the `uint16` indices of `DrawTriangles`). The sample antialiases smooth
geometry; intentional pixel art needs a consistent snapped grid instead.

## Screen shake and hit-stop

Choose feedback by the event's meaning and frequency. A routine action should
leave headroom for a rare decisive one; a quiet puzzle may need no shake at all.
Treat each response as a bounded envelope that returns to rest. Repeated triggers
should extend/replace/accumulate according to one explicit policy, rather than
start competing tweens that each restore an old scale or pause value.

Emit feedback once from an accepted rules event, not every tick an attack is
held or every `Draw` while two bodies overlap. Keep visual squash, flashes and
camera offsets separate from collision state; gameplay knockback is a rules
effect and belongs in the simulation. Keep UI/input advancing during hit-stop,
and preserve intended buffered actions. The assets-and-animation reference
covers aligning contact markers, hitboxes and sound.

This applies the importance/decay principle from
`game-feel`.
There is no required number of channels. Easing is useful for settling UI or
poses; constant-speed projectiles, precise meters and some art directions should
stay linear. A large feedback bundle cannot compensate for unclear rules.

```go
// Juice holds presentation-only timers. Gameplay reads Frozen() to skip
// simulation ticks during hit-stop; Draw reads Offset() for the camera.
type Juice struct {
	trauma float64 // 0..1, decays every tick
	freeze int
	tick   int
}

func (j *Juice) Shake(amount float64) { j.trauma = math.Min(1, j.trauma+amount) }
func (j *Juice) HitStop(ticks int)    { j.freeze = max(j.freeze, ticks) }
func (j *Juice) Frozen() bool         { return j.freeze > 0 }

func (j *Juice) Update() {
	j.tick++
	if j.freeze > 0 {
		j.freeze--
	}
	j.trauma = math.Max(0, j.trauma-1.0/30) // gone after half a second
}

// Offset is smooth noise scaled by trauma², so small hits barely move the
// screen and big ones shake hard. maxPx of 6-8 suits a 320-640 px screen.
func (j *Juice) Offset(maxPx float64) (float64, float64) {
	s := j.trauma * j.trauma * maxPx
	t := float64(j.tick)
	return s * (math.Sin(t*1.7) + math.Sin(t*3.1)) / 2, s * (math.Sin(t*2.3+1) + math.Sin(t*4.3)) / 2
}
```

- In `Update`, sample `frozen := juice.Frozen()` **before** `juice.Update()`.
  Then skip simulation if `frozen`; otherwise step rules and apply their new
  hit-stop requests. This freezes exactly N subsequent simulation ticks for
  `HitStop(N)`, including N=1. Continue sampling input and updating presentation;
  buffer actions the game should preserve across the freeze.
- In `Draw`: add `juice.Offset(8)` to the camera position.
- Example starting values at 60 TPS: a heavy hit might use `HitStop(3–6)` and
  `Shake(0.4–0.6)`. Tune by the game's pace and feedback hierarchy; many genres
  need neither hit-stop nor shake.
- Offer a "reduce screen shake" option that scales `maxPx` to 0
  (text-and-ui reference, accessibility).

## Tiled maps

For Tiled-based levels, read the tilemaps reference (map-loader subset
and integration notes).
This is optional; grids, authored Go data and other level formats are valid.
Keep collision/spawn data in the rules layer instead of querying rendered pixels.

## Rigid-body physics (Chipmunk2D)

For simple axis-aligned tile movement, the starter's `world` solver is a small,
testable starting point. Slopes, moving platforms, one-way surfaces and
continuous collisions need additional rules. Consider a physics engine for
stacks, ragdolls, ropes, vehicles and physics puzzles.
`github.com/jakecoffman/cp/v2` is a pure-Go port of Chipmunk2D:

```go
package game

import (
	"github.com/hajimehoshi/ebiten/v2"
	"github.com/jakecoffman/cp/v2"
)

// Rigid-body physics with Chipmunk2D's Go port. Units are your world
// units (pixels here); y grows downward like the screen, so gravity is +y.

type Physics struct {
	Space       *cp.Space
	StepSeconds float64 // fixed positive simulation step; default assumes 60 TPS
}

func NewPhysics() *Physics {
	s := cp.NewSpace()
	s.SetGravity(cp.Vector{X: 0, Y: 600})
	s.Iterations = 10
	return &Physics{Space: s, StepSeconds: 1.0 / 60}
}

// AddGround adds a static segment (floors, walls, slopes).
func (p *Physics) AddGround(x0, y0, x1, y1 float64) {
	seg := cp.NewSegment(p.Space.StaticBody, cp.Vector{X: x0, Y: y0}, cp.Vector{X: x1, Y: y1}, 2)
	seg.SetFriction(0.8)
	seg.SetElasticity(0.3)
	p.Space.AddShape(seg)
}

func (p *Physics) AddBall(x, y, r, mass float64) *cp.Body {
	b := p.Space.AddBody(cp.NewBody(mass, cp.MomentForCircle(mass, 0, r, cp.Vector{})))
	b.SetPosition(cp.Vector{X: x, Y: y})
	sh := p.Space.AddShape(cp.NewCircle(b, r, cp.Vector{}))
	sh.SetFriction(0.6)
	sh.SetElasticity(0.5)
	return b
}

func (p *Physics) AddBox(x, y, w, h, mass float64) *cp.Body {
	b := p.Space.AddBody(cp.NewBody(mass, cp.MomentForBox(mass, w, h)))
	b.SetPosition(cp.Vector{X: x, Y: y})
	sh := p.Space.AddShape(cp.NewBox(b, w, h, 0))
	sh.SetFriction(0.7)
	return b
}

// Update steps with the fixed tick length. Never pass a measured frame time.
func (p *Physics) Update() {
	p.Space.Step(p.StepSeconds)
}

// DrawBody draws img centred on a body, rotated with it.
func DrawBody(dst, img *ebiten.Image, b *cp.Body, camX, camY float64) {
	w, h := img.Bounds().Dx(), img.Bounds().Dy()
	op := &ebiten.DrawImageOptions{}
	op.GeoM.Translate(-float64(w)/2, -float64(h)/2)
	op.GeoM.Rotate(b.Angle())
	pos := b.Position()
	op.GeoM.Translate(pos.X-camX, pos.Y-camY)
	op.Filter = ebiten.FilterLinear // rotated sprites look better filtered
	dst.DrawImage(img, op)
}
```

- Initialize a positive fixed `StepSeconds` for the chosen simulation rate and
  step once per simulation tick. Do not feed measured render-frame time into
  this fixed-tick integration. Keep input/UI ticking if simulation is paused or
  slowed. `SyncWithFPS` is not a positive fixed TPS.
- Choose consistent units and tune tolerances, gravity, timestep and solver
  settings together. Numeric scale and extreme mass ratios affect stability;
  a particular pixel size or mass is not a universal requirement.
- Collision callbacks (`space.NewCollisionHandler`) run inside `Step`; record
  events there and react after the step, the same way as the tile rules.
- Choose rotated-sprite filtering to fit the art direction. Infinite moment
  (`cp.NewBody` with `math.Inf(1)`) prevents angular acceleration from torque;
  it is a gameplay constraint, not a required pixel-art technique.
- `github.com/solarlune/resolv` is a lighter alternative for collision
  detection without dynamics (shapes, rays, intersection tests).

Source contract: [Chipmunk2D Go port](https://github.com/jakecoffman/cp).
