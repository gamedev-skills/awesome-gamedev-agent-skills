# Rendering

API baseline: Ebitengine v2.10.6. Snippets illustrate individual patterns; add the
imports, initialization and validation required by the project.

## Contents

- [Images are GPU resources](#images-are-gpu-resources)
- [Transforms](#transforms)
- [Sprite sheets and animation](#sprite-sheets-and-animation)
- [Colour and blending](#colour-and-blending)
- [Shapes](#shapes)
- [Camera](#camera)
- [Tilemaps](#tilemaps)
- [Layers and offscreens](#layers-and-offscreens)
- [Screen size, scaling and HiDPI](#screen-size-scaling-and-hidpi)
- [Performance checklist](#performance-checklist)

## Images are GPU resources

- Create reusable images at load or when a level starts. Repeated `NewImage`,
  `NewImageFromImage` and decoding in hot paths can cause allocation and upload
  costs; profile before attributing a slowdown to them.
- Ebitengine packs small images into shared atlases automatically. Do not build
  your own atlas just for batching; do keep each sprite sheet as one image and cut
  frames with `SubImage`.
- Reading pixels back (`At`, `ReadPixels`) waits for the GPU. Use it for
  screenshots and tests only. `ReadPixels` cannot run before `RunGame` starts.
- Do not draw the screen into another image, do not draw A into B and B into A,
  and do not change an image's pixels after using it as a source in the same
  frame: each forces extra work.

### Decode embedded PNGs once

```go
//go:embed assets/*.png
var assetsFS embed.FS

func loadImage(path string) (*ebiten.Image, error) {
	b, err := assetsFS.ReadFile(path)
	if err != nil {
		return nil, err
	}
	img, _, err := image.Decode(bytes.NewReader(b)) // import _ "image/png"
	if err != nil {
		return nil, err
	}
	return ebiten.NewImageFromImage(img), nil
}
```

## Transforms

`GeoM` operations apply in the order you call them. To rotate or scale around a
sprite's centre: move the centre to the origin, scale, rotate, then place.

```go
func drawSprite(dst, img *ebiten.Image, x, y, angle, scale float64) {
	w, h := img.Bounds().Dx(), img.Bounds().Dy()
	op := &ebiten.DrawImageOptions{}
	op.GeoM.Translate(-float64(w)/2, -float64(h)/2) // 1. pivot to origin
	op.GeoM.Scale(scale, scale)                     // 2. scale
	op.GeoM.Rotate(angle)                           // 3. rotate (radians)
	op.GeoM.Translate(x, y)                         // 4. place in the world
	dst.DrawImage(img, op)
}
```

Options can be reused in a loop; reset every field that varies per sprite,
including `GeoM` and `ColorScale`. A local options value often stays on the
stack, so creating one per draw does not itself prove a heap allocation.

## Sprite sheets and animation

```go
type Anim struct {
	frames        []*ebiten.Image
	ticksPerFrame int
}

func NewAnim(sheet *ebiten.Image, frameW, frameH, count, ticksPerFrame int) *Anim {
	a := &Anim{ticksPerFrame: ticksPerFrame}
	for i := 0; i < count; i++ {
		x := i * frameW
		// SubImage shares the sheet's pixels; frames batch together when drawn.
		a.frames = append(a.frames, sheet.SubImage(image.Rect(x, 0, x+frameW, frameH)).(*ebiten.Image))
	}
	return a
}

// Frame picks the frame for a tick counted in Update; Draw only reads it.
func (a *Anim) Frame(tick int) *ebiten.Image {
	return a.frames[(tick/a.ticksPerFrame)%len(a.frames)]
}
```

Leave at least one transparent pixel between frames in the sheet if you ever
draw with `FilterLinear` or non-integer scales; neighbouring frames otherwise
bleed in at the edges.
Validate frame dimensions, count and ticks per frame at load time;
`Anim.Frame` assumes non-empty frames and a positive tick duration.

## Colour and blending

`ColorScale` multiplies premultiplied colour: `ScaleAlpha(a)` fades the whole
sprite. `Blend` chooses compositing (`ebiten.BlendLighter` for additive light).
`DrawImageOptions.ColorM` and `CompositeMode` are deprecated since v2.5; use
`ColorScale`, `Blend`, or the `colorm` package for full colour matrices.

```go
func drawGlow(dst, img *ebiten.Image, x, y float64, alpha float32) {
	op := &ebiten.DrawImageOptions{}
	op.GeoM.Translate(x, y)
	op.ColorScale.Scale(1, 0.8, 0.4, 1) // warm tint
	op.ColorScale.ScaleAlpha(alpha)     // fade (premultiplied: scales RGB too)
	op.Blend = ebiten.BlendLighter      // additive
	dst.DrawImage(img, op)
}
```

## Shapes

`vector.FillRect`, `StrokeRect`, `StrokeLine`, `FillCircle`, `StrokeCircle` take
`float32` coordinates, a colour and an `antialias` flag; the `Stroke*` functions
also take a `float32` `strokeWidth` before the colour. Use `true` for smooth geometry; intentional
pixel-art edges may use `false`. (v2.9 renamed
`DrawFilledRect`/`DrawFilledCircle` to `FillRect`/`FillCircle`). For other
shapes, build a `vector.Path`:

```go
func drawStar(dst *ebiten.Image, cx, cy, r float32) {
	var p vector.Path
	for i := 0; i < 10; i++ {
		rad := r
		if i%2 == 1 {
			rad = r * 0.45
		}
		a := float64(i)*math.Pi/5 - math.Pi/2
		x, y := cx+rad*float32(math.Cos(a)), cy+rad*float32(math.Sin(a))
		if i == 0 {
			p.MoveTo(x, y)
		} else {
			p.LineTo(x, y)
		}
	}
	p.Close()
	op := &vector.DrawPathOptions{AntiAlias: true}
	op.ColorScale.Scale(1, 0.85, 0.2, 1)
	vector.FillPath(dst, &p, nil, op)
}
```

Shapes that never change are cheaper drawn once into an image at load and then
drawn as a sprite.

## Camera

Keep game objects in world coordinates and convert in `Draw`.

```go
type Camera struct {
	X, Y float64 // world point at the screen centre
	Zoom float64 // initialize to 1; must stay positive for inverse mapping
}

func (c Camera) Apply(geo *ebiten.GeoM, screenW, screenH float64) {
	geo.Translate(-c.X, -c.Y)
	geo.Scale(c.Zoom, c.Zoom)
	geo.Translate(math.Round(screenW/2), math.Round(screenH/2))
}

// ScreenToWorld converts a cursor position (already in logical pixels).
func (c Camera) ScreenToWorld(sx, sy, screenW, screenH float64) (float64, float64) {
	var g ebiten.GeoM
	c.Apply(&g, screenW, screenH)
	g.Invert()
	return g.Apply(sx, sy)
}
```

Per sprite: `op.GeoM.Reset()`, translate to the sprite's world position, then
`op.GeoM.Concat(cameraGeoM)`. For pixel art without zoom, round the camera
position once per frame and add it to integer sprite positions, so everything
moves by whole pixels together; rounding each sprite separately makes them
jitter against each other.

Smooth following belongs in `Update` (move a fixed fraction of the distance per
tick and clamp to the level bounds), as in the starter's `playScene`.

## Tilemaps

Compute the visible cell range from the camera and draw only those cells; skip
empty cells. Draw all tiles from one tileset image in one loop so they batch.
For static layers, consider caching visible-sized chunks. A whole-map image
uses width × height × 4 bytes before additional GPU costs and can exceed device
texture limits; use it only when its measured size and load cost are acceptable.

## Layers and offscreens

An offscreen is an `ebiten.NewImage(w, h)` you `Clear()` and draw into each
frame, then draw onto the screen (for lighting, a minimap, a pixelated layer
under smooth UI). Create it once; recreate it only when its size must change.

## Screen size, scaling and HiDPI

`Layout` decides the logical screen. Three common choices:

| Goal | `Layout` returns | Notes |
| --- | --- | --- |
| Pixel art | a fixed small size, e.g. 320×180 | choose a viewport/sampling policy below |
| Fixed-size design that scales smoothly | a fixed size, e.g. 1280×720 | letterboxed; `FilterLinear` for art |
| UI that uses all the space | the outside size | layout code must handle any size |

Start with the default final-screen renderer. In v2.10.6 it uses nearest
sampling at integer scales, `FilterPixelated` for fractional enlargement, and
linear filtering for shrinking. This preserves the engine's matching input
transform. Test the actual window sizes and device scale factors you support.

Strict integer enlargement requires a deliberate viewport policy. If using
`FinalScreenDrawer`, retain its supplied default matrix **D** and your custom
presentation matrix **P**. Cursor and touch positions returned by Ebitengine
still use D; convert them with `P⁻¹(D(position))` before hit testing, and reject
points in the letterbox bars. Test clicks after resizing and on HiDPI displays.
Define the behavior when the physical window is smaller than the logical
screen: forcing a minimum scale of 1 crops the game instead of fitting it.
Do not paste a custom draw-only scaling function into an input-driven game.

For sharp text and vectors on HiDPI displays, implement `LayoutF` and multiply by
the device scale factor (then draw with coordinates scaled by the same factor):

```go
func (g *Game) LayoutF(outsideW, outsideH float64) (float64, float64) {
	s := ebiten.Monitor().DeviceScaleFactor()
	return outsideW * s, outsideH * s
}
```

`ebiten.DeviceScaleFactor()` is deprecated since v2.6; use
`ebiten.Monitor().DeviceScaleFactor()`.

## Performance checklist

1. Count draw commands: build with `-tags=ebitenginedebug` and read the log.
   Many commands per frame usually means interleaved source images, blends or
   filters or texture-atlas boundaries. Group compatible draws only when the
   resulting order preserves overlap and transparency.
2. Show `ebiten.ActualFPS()` and `ebiten.ActualTPS()` with
   `ebitenutil.DebugPrint` during development.
3. Reuse hot-path slices (`buf[:0]`), images and measured allocation-heavy
   resources. Choose a frame-time/allocation budget from profiling rather than
   enforcing zero allocations everywhere.
4. Profile CPU with `runtime/pprof` around a scripted run before guessing.
5. `ebiten.SetVsyncEnabled(false)` can help measure uncapped rendering cost;
   retain an intentional frame-pacing policy for the release.

For the chosen target, set a frame-time budget and exercise representative dense
content, transitions and first-use asset/glyph loads. Track slow frames and load
spikes as well as average FPS. A 60 Hz presentation interval is about 16.67 ms;
that is a chosen target, not a universal requirement. CPU duration of `Draw` is
not GPU completion time, and uncapped hidden capture is not a pacing test.

If profiling identifies expensive noncritical AI/path queries, consider spreading
them over fixed simulation ticks with a stable entity-based phase. Do not skip
collision-critical movement, tie rules updates to `Draw`, or let offscreen render
culling silently stop gameplay. These are conditional applications of
[game-developer's performance guidance](https://github.com/Jeffallan/claude-skills/blob/02b05028ba6c93f7aed45314b15c0dd5abead9d6/skills/game-developer/references/performance-optimization.md),
rather than requirements to add pooling, LOD or an ECS before measuring.
For engine-neutral profiling and budgeting, pair this with `performance-optimization`.

For art-set/sprite registration checks, see the assets-and-animation reference.
For Kage, consult the pinned engine's shader documentation or its
`writing-kage-shaders` skill when available.

Source contracts: [default final-screen renderer](https://github.com/hajimehoshi/ebiten/blob/v2.10.6/gameforui.go),
[input coordinate conversion](https://github.com/hajimehoshi/ebiten/blob/v2.10.6/internal/ui/context.go),
and [performance guidance](https://ebitengine.org/en/documents/performancetips.html).
