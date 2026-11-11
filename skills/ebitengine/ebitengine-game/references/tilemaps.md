# Tiled maps

API baseline: Ebitengine v2.10.6. Read only when the game uses Tiled.
The illustrative loader below handles a constrained subset; prefer an existing
maintained loader when the map requires more of Tiled's format.

## Contents

- [Finite orthogonal JSON subset](#finite-orthogonal-json-subset)
- [Loader](#loader)
- [Using the loader](#using-the-loader)
- [Integration notes](#integration-notes)

## Finite orthogonal JSON subset

[Tiled](https://www.mapeditor.org/) is the usual level editor. Save maps as JSON
(`.tmj`, tilesets as `.tsj` or embedded), layer format CSV or Base64 with zlib or
gzip. The loader below handles finite orthogonal maps, tile and object layers,
external tilesets, margins/spacing and the flip flags in the top bits of each
global tile ID (horizontal `0x80000000`, vertical `0x40000000`, diagonal
`0x20000000`, hexagonal rotation `0x10000000`). Clear the flags with `&^`, then
the tileset is the one with the largest `firstgid` not above the ID.

Its supported subset is deliberately small: non-grouped tile/object layers with
no layer offsets, parallax or tint; a single atlas image per tileset; square
tiles matching the map grid; and point or axis-aligned rectangle objects.
It does not implement tile animation, tile properties, image-collection
tilesets, rotated/tile/polygon objects, or nested groups. The checks below
reject those cases instead of silently displaying a different level. Use an
established loader or explicitly extend this subset when the project needs more.

## Loader

```go
package game

import (
	"bytes"
	"compress/gzip"
	"compress/zlib"
	"encoding/base64"
	"encoding/binary"
	"encoding/json"
	"fmt"
	"image"
	"io"
	"io/fs"
	"path"

	"github.com/hajimehoshi/ebiten/v2"
)

// Minimal loader for Tiled JSON maps (.tmj): orthogonal, finite, tile and
// object layers, embedded or external (.tsj) tilesets, CSV or base64 data
// (uncompressed, zlib or gzip). Field names follow the Tiled JSON format.

const (
	flipH    = 0x80000000
	flipV    = 0x40000000
	flipD    = 0x20000000
	rotHex   = 0x10000000
	gidFlags = flipH | flipV | flipD | rotHex
)

type TiledMap struct {
	Width, Height         int
	TileWidth, TileHeight int `json:"-"`
	Orientation           string
	Infinite              bool
	Layers                []TiledLayer
	Tilesets              []TiledTileset
}

type TiledLayer struct {
	Name, Type            string
	Visible               bool
	Opacity               float64
	Width, Height         int
	Data                  json.RawMessage
	Encoding, Compression string
	Objects               []TiledObject
	X, Y                  float64
	OffsetX, OffsetY      float64
	ParallaxX, ParallaxY  *float64
	TintColor, Mode       string
	gids                  []uint32
}

type TiledObject struct {
	Name, Type, Class   string // Tiled 1.9 used class; 1.10+ uses type again
	X, Y, Width, Height float64
	Point               bool
	GID                 uint32
	Rotation            float64
	Ellipse, Capsule    bool
	Polygon, Polyline   []json.RawMessage
	Text                json.RawMessage
	Template            string
}

type TiledTileset struct {
	FirstGID              int `json:"firstgid"`
	Source                string
	Image                 string
	ImageWidth            int `json:"imagewidth"`
	Columns, TileCount    int
	Margin, Spacing       int
	TileWidth, TileHeight int `json:"-"`
	Tiles                 []json.RawMessage
	TileOffset            struct{ X, Y int }
	TransparentColor      string
	img                   *ebiten.Image
}

// UnmarshalJSON handles the lowercase keys Tiled writes for tile sizes.
func (m *TiledMap) UnmarshalJSON(b []byte) error {
	type plain TiledMap
	var aux struct {
		plain
		TW int `json:"tilewidth"`
		TH int `json:"tileheight"`
	}
	if err := json.Unmarshal(b, &aux); err != nil {
		return err
	}
	*m = TiledMap(aux.plain)
	m.TileWidth, m.TileHeight = aux.TW, aux.TH
	return nil
}

func (t *TiledTileset) UnmarshalJSON(b []byte) error {
	type plain TiledTileset
	var aux struct {
		plain
		TW int `json:"tilewidth"`
		TH int `json:"tileheight"`
	}
	if err := json.Unmarshal(b, &aux); err != nil {
		return err
	}
	*t = TiledTileset(aux.plain)
	t.TileWidth, t.TileHeight = aux.TW, aux.TH
	return nil
}

// Tiled's opacity defaults to 1 when omitted.
func (l *TiledLayer) UnmarshalJSON(b []byte) error {
	type plain TiledLayer
	aux := plain{Visible: true, Opacity: 1}
	if err := json.Unmarshal(b, &aux); err != nil {
		return err
	}
	*l = TiledLayer(aux)
	return nil
}

// LoadTiledMap reads a .tmj from fsys (for example an embed.FS) and decodes
// its tileset images with decode (for example via image.Decode).
func LoadTiledMap(fsys fs.FS, name string, decode func(io.Reader) (image.Image, error)) (*TiledMap, error) {
	b, err := fs.ReadFile(fsys, name)
	if err != nil {
		return nil, err
	}
	var m TiledMap
	if err := json.Unmarshal(b, &m); err != nil {
		return nil, fmt.Errorf("%s: %w", name, err)
	}
	if m.Orientation != "orthogonal" || m.Infinite {
		return nil, fmt.Errorf("%s: only finite orthogonal maps are supported", name)
	}
	if m.Width <= 0 || m.Height <= 0 || m.TileWidth <= 0 || m.TileWidth != m.TileHeight {
		return nil, fmt.Errorf("%s: need positive map dimensions and square grid tiles", name)
	}
	dir := path.Dir(name)
	for i := range m.Tilesets {
		ts := &m.Tilesets[i]
		base := dir
		if ts.Source != "" { // external tileset: keep firstgid from the map
			first := ts.FirstGID
			src := path.Join(dir, ts.Source)
			tb, err := fs.ReadFile(fsys, src)
			if err != nil {
				return nil, err
			}
			if err := json.Unmarshal(tb, ts); err != nil {
				return nil, fmt.Errorf("%s: %w", src, err)
			}
			ts.FirstGID, base = first, path.Dir(src)
		}
		if ts.Image == "" || ts.FirstGID <= 0 || ts.Columns <= 0 || ts.TileCount <= 0 ||
			ts.Margin < 0 || ts.Spacing < 0 || ts.TileWidth != m.TileWidth || ts.TileHeight != m.TileHeight ||
			len(ts.Tiles) != 0 || ts.TileOffset.X != 0 || ts.TileOffset.Y != 0 || ts.TransparentColor != "" {
			return nil, fmt.Errorf("tileset %d: need a matching atlas without per-tile metadata or offset", i)
		}
		f, err := fsys.Open(path.Join(base, ts.Image))
		if err != nil {
			return nil, err
		}
		img, err := decode(f)
		f.Close()
		if err != nil {
			return nil, fmt.Errorf("%s: %w", ts.Image, err)
		}
		rows := (ts.TileCount + ts.Columns - 1) / ts.Columns
		needW := 2*ts.Margin + ts.Columns*ts.TileWidth + (ts.Columns-1)*ts.Spacing
		needH := 2*ts.Margin + rows*ts.TileHeight + (rows-1)*ts.Spacing
		if img.Bounds().Dx() < needW || img.Bounds().Dy() < needH {
			return nil, fmt.Errorf("%s: atlas is too small for its declared tiles", ts.Image)
		}
		ts.img = ebiten.NewImageFromImage(img)
	}
	for i := range m.Layers {
		l := &m.Layers[i]
		if (l.Type != "tilelayer" && l.Type != "objectgroup") ||
			l.X != 0 || l.Y != 0 || l.OffsetX != 0 || l.OffsetY != 0 ||
			(l.ParallaxX != nil && *l.ParallaxX != 1) || (l.ParallaxY != nil && *l.ParallaxY != 1) ||
			l.TintColor != "" || (l.Mode != "" && l.Mode != "normal") {
			return nil, fmt.Errorf("layer %q: unsupported type or presentation properties", l.Name)
		}
		for _, o := range l.Objects {
			if o.GID != 0 || o.Rotation != 0 || o.Ellipse || o.Capsule || len(o.Polygon) != 0 || len(o.Polyline) != 0 ||
				len(o.Text) != 0 || o.Template != "" {
				return nil, fmt.Errorf("object %q: only points and axis-aligned rectangles are supported", o.Name)
			}
		}
		if l.Type == "tilelayer" {
			if err := l.decode(); err != nil {
				return nil, fmt.Errorf("layer %q: %w", l.Name, err)
			}
			for _, gid := range l.gids {
				id := int(gid &^ gidFlags)
				if id == 0 {
					continue
				}
				ts := m.tileset(id)
				if ts == nil || id-ts.FirstGID >= ts.TileCount {
					return nil, fmt.Errorf("layer %q: invalid GID %d", l.Name, id)
				}
			}
		}
	}
	return &m, nil
}

func (l *TiledLayer) decode() error {
	if l.Width <= 0 || l.Height <= 0 {
		return fmt.Errorf("tile layer dimensions must be positive")
	}
	count := l.Width * l.Height
	if l.Encoding == "" || l.Encoding == "csv" {
		if err := json.Unmarshal(l.Data, &l.gids); err != nil {
			return err
		}
		if len(l.gids) != count {
			return fmt.Errorf("got %d cells, want %d", len(l.gids), count)
		}
		return nil
	}
	if l.Encoding != "base64" {
		return fmt.Errorf("encoding %q not supported", l.Encoding)
	}
	var s string
	if err := json.Unmarshal(l.Data, &s); err != nil {
		return err
	}
	raw, err := base64.StdEncoding.DecodeString(s)
	if err != nil {
		return err
	}
	var r io.Reader = bytes.NewReader(raw)
	var closer io.Closer
	switch l.Compression {
	case "":
	case "zlib":
		if r, err = zlib.NewReader(r); err != nil {
			return err
		}
		closer = r.(io.Closer)
	case "gzip":
		if r, err = gzip.NewReader(r); err != nil {
			return err
		}
		closer = r.(io.Closer)
	default:
		return fmt.Errorf("compression %q not supported (save as CSV, zlib or gzip)", l.Compression)
	}
	if closer != nil {
		defer closer.Close()
	}
	raw, err = io.ReadAll(io.LimitReader(r, int64(count)*4+1))
	if err != nil {
		return err
	}
	if len(raw) != count*4 {
		return fmt.Errorf("got %d tile bytes, want %d", len(raw), count*4)
	}
	l.gids = make([]uint32, count)
	return binary.Read(bytes.NewReader(raw), binary.LittleEndian, l.gids)
}

// GID returns the raw global tile ID (with flip flags) at a cell, 0 if empty.
func (l *TiledLayer) GID(x, y int) uint32 {
	if x < 0 || y < 0 || x >= l.Width || y >= l.Height {
		return 0
	}
	return l.gids[y*l.Width+x]
}

func (m *TiledMap) tileset(id int) *TiledTileset {
	var ts *TiledTileset
	for i := range m.Tilesets { // the tileset with the largest firstgid <= id
		if m.Tilesets[i].FirstGID <= id && (ts == nil || m.Tilesets[i].FirstGID > ts.FirstGID) {
			ts = &m.Tilesets[i]
		}
	}
	return ts
}

// tile finds the image for a validated GID; nil for empty cells.
func (m *TiledMap) tile(gid uint32) *ebiten.Image {
	id := int(gid &^ gidFlags)
	if id == 0 {
		return nil
	}
	ts := m.tileset(id)
	local := id - ts.FirstGID
	x := ts.Margin + (local%ts.Columns)*(ts.TileWidth+ts.Spacing)
	y := ts.Margin + (local/ts.Columns)*(ts.TileHeight+ts.Spacing)
	return ts.img.SubImage(image.Rect(x, y, x+ts.TileWidth, y+ts.TileHeight)).(*ebiten.Image)
}

// DrawLayer draws the visible part of a tile layer with the camera at
// (camX, camY), honouring Tiled's flip flags.
func (m *TiledMap) DrawLayer(dst *ebiten.Image, l *TiledLayer, camX, camY float64) {
	if !l.Visible {
		return
	}
	tw, th := m.TileWidth, m.TileHeight
	sw, sh := dst.Bounds().Dx(), dst.Bounds().Dy()
	x0, y0 := int(camX)/tw, int(camY)/th
	op := &ebiten.DrawImageOptions{}
	op.ColorScale.ScaleAlpha(float32(l.Opacity))
	for y := y0; y <= y0+sh/th+1; y++ {
		for x := x0; x <= x0+sw/tw+1; x++ {
			gid := l.GID(x, y)
			img := m.tile(gid)
			if img == nil {
				continue
			}
			op.GeoM = TileGeoM(gid, float64(tw), float64(th))
			op.GeoM.Translate(float64(x*tw)-camX, float64(y*th)-camY)
			dst.DrawImage(img, op)
		}
	}
}

// TileGeoM maps a w×h tile into its cell at the origin, applying Tiled's
// flags in Tiled's order: diagonal (swap x and y) first, then horizontal,
// then vertical. Diagonal flips assume square tiles.
func TileGeoM(gid uint32, w, h float64) ebiten.GeoM {
	var g ebiten.GeoM
	g.Translate(-w/2, -h/2) // flip around the tile centre
	if gid&flipD != 0 {
		var swap ebiten.GeoM
		swap.SetElement(0, 0, 0)
		swap.SetElement(0, 1, 1)
		swap.SetElement(1, 0, 1)
		swap.SetElement(1, 1, 0)
		g.Concat(swap)
	}
	if gid&flipH != 0 {
		g.Scale(-1, 1)
	}
	if gid&flipV != 0 {
		g.Scale(1, -1)
	}
	g.Translate(w/2, h/2)
	return g
}
```

## Using the loader

Use it with an embedded directory and `image.Decode` (import `_ "image/png"`):

```go
//go:embed maps
var maps embed.FS

m, err := LoadTiledMap(maps, "maps/level1.tmj", func(r io.Reader) (image.Image, error) {
	img, _, err := image.Decode(r)
	return img, err
})
```

## Integration notes

- Collision: read a layer named `collision` into the
  rules package's grid at load time; do not test collisions against images.
- Spawns, triggers, doors: object layers. Points have `point: true`; tile
  objects use `y` at the bottom edge, rectangles at the top edge.
- Infinite maps store chunks instead of `data`; turn "Infinite" off in Tiled or
  extend the loader. zstd compression needs an extra package; pick zlib.
- Large static layers: consider bounded chunk caches instead of a whole-map GPU
  image (rendering reference).
- `github.com/lafriks/go-tiled` is a fuller loader that reads the XML `.tmx`
  format.


Source contracts: [Tiled JSON format](https://doc.mapeditor.org/en/stable/reference/json-map-format/),
[Tiled GID flags](https://doc.mapeditor.org/en/stable/reference/global-tile-ids/).
