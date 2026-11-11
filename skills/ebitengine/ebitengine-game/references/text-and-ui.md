# Text and UI

API baseline: Ebitengine v2.10.6, package
`github.com/hajimehoshi/ebiten/v2/text/v2`. Snippets illustrate patterns to adapt;
they are not a complete text-layout or localization library.
The font examples use outline fonts. Keep a suitable existing bitmap font or
glyph-atlas renderer when it fits the art and shipped scripts; these examples
do not require replacing it.

Contents: [Fonts](#fonts) · [Drawing and alignment](#drawing-and-alignment) · [Wrapping](#wrapping) · [Readability](#readability) · [Simple UI](#simple-ui) · [UI states](#ui-states-attention-and-ownership) · [Localization](#localization) · [Accessibility](#accessibility)

## Contents

- [Fonts](#fonts)
- [Drawing and alignment](#drawing-and-alignment)
- [Wrapping](#wrapping)
- [Readability](#readability)
- [Simple UI](#simple-ui)
- [UI states, attention and ownership](#ui-states-attention-and-ownership)
- [Localization](#localization)
- [Accessibility](#accessibility)

## Fonts

- Parse each font file once with `text.NewGoTextFaceSource` and keep the source.
  It owns the glyph cache. Create `&text.GoTextFace{Source: src, Size: px}` values
  freely; they are cheap.
- Embed the font file (`//go:embed fonts/MyFont.ttf`) and keep its licence file
  next to it. `golang.org/x/image/font/gofont/goregular` (BSD licence) is a
  convenient font for prototypes; check glyph coverage for the shipped strings.
- Japanese, Chinese and Korean need a font that contains those glyphs. For
  prototypes, `github.com/hajimehoshi/ebiten/v2/examples/resources/fonts`
  exposes `MPlus1pRegular_ttf` (M+ licence, free use); for a shipped game, embed
  your own CJK font such as one licensed under the SIL OFL, and include the licence.
- Glyph images are made per size. Animating `Size` every frame regenerates glyphs;
  to zoom text, draw it once at the largest size into an image and scale the image.
- `text.CacheGlyphs(str, face)` pre-renders glyphs (for example all digits for a
  score) to avoid a hitch the first time they appear.

```go
type Fonts struct {
	Latin *text.GoTextFaceSource
}

func LoadFonts() (*Fonts, error) {
	src, err := text.NewGoTextFaceSource(bytes.NewReader(goregular.TTF))
	if err != nil {
		return nil, err
	}
	return &Fonts{Latin: src}, nil
}

func (f *Fonts) Face(size float64) *text.GoTextFace {
	return &text.GoTextFace{Source: f.Latin, Size: size}
}
```

### Mixed scripts

`text.NewMultiFace` tries faces in order per glyph, so a Latin face with a CJK
fallback renders both in one string:

```go
func mixedFace(latin, cjk *text.GoTextFaceSource, size float64) (text.Face, error) {
	return text.NewMultiFace(
		&text.GoTextFace{Source: latin, Size: size},
		&text.GoTextFace{Source: cjk, Size: size},
	)
}
```

Set `GoTextFace.Language` (for example `language.Japanese` from
`golang.org/x/text/language`) when glyph forms differ by language. `Script` is
deprecated since v2.9.

## Drawing and alignment

`text.Draw(dst, str, face, op)` places the text's layout box at the origin of
`op.GeoM`. `op.PrimaryAlign` aligns along the line (start, centre, end) and
`op.SecondaryAlign` across lines, both relative to that origin. `op.LineSpacing`
is the distance between baselines and is required for multi-line strings. Colour
the text with `op.ColorScale.ScaleWithColor(c)`.

- `text.Measure(str, face, lineSpacing)` returns the width and height of a block.
- `text.AdvanceAt(str, len(str), face)` is the width of one line (v2.10
  deprecates `text.Advance`).
- `face.Metrics()` gives `HAscent`, `HDescent` and `HLineGap`; their sum is a
  natural line spacing.

## Wrapping

`text.Draw` respects explicit newlines; it does not automatically wrap to a
width. Compute lines when text, font, locale or available width changes, then
draw the cached result:

```go
// lines have already been wrapped by the project's text-layout code.
func drawParagraph(dst *ebiten.Image, lines []string, face text.Face, x, y float64, clr color.Color) {
	m := face.Metrics()
	lineH := m.HAscent + m.HDescent + m.HLineGap
	op := &text.DrawOptions{}
	op.GeoM.Translate(x, y)
	op.LineSpacing = lineH
	op.ColorScale.ScaleWithColor(clr)
	text.Draw(dst, strings.Join(lines, "\n"), face, op)
}
```

A wrapper should choose legal line-break opportunities for the shipped
languages, measure each complete candidate with the actual face, and specify an
overflow policy for a word or glyph wider than the box. Space splitting alone
does not handle CJK; splitting every rune breaks combining marks and emoji
sequences. Use Unicode line-break and grapheme segmentation, including Japanese
kinsoku rules when shipping Japanese. Test long words, explicit blank lines,
mixed scripts, combining accents and narrow boxes. Use a proven layout library
for broad script support rather than inventing a code-point threshold.

## Readability

- Size text for the logical screen and the expected window scale: in a 320×180
  pixel-art game, 8–12 px bitmap-style fonts read well; outline fonts under about
  12 logical px blur after scaling. Use a larger logical screen or a separate
  high-resolution UI layer for long text.
- Put a dark band or outline behind text over busy backgrounds; draw an outline by
  drawing the text 4–8 times offset by 1 px in the outline colour, then once on top.
- Typewriter dialogue: advance revealed grapheme clusters in `Update`, not UTF-8
  bytes. A rune alone can be half of a visible character. Keep wrapping stable
  using the complete line, and check shaping for joined scripts; reshaping a
  prefix can change its appearance.

## Simple UI

- Buttons and menus: rectangles hit-tested with the logical cursor (see
  the input reference), a focus index moved by keys/pad for non-mouse play, and the
  same "confirm" action for click, Enter and the pad's bottom face button.
- Lay UI out in logical coordinates relative to the screen edges you get from
  `Layout`, so it survives window resizes when `Layout` returns a fixed size.
- `ebitenutil.DebugPrint`/`DebugPrintAt` draws a fixed debug font; use it for
  development overlays, not shipped UI.
- `github.com/ebitengine/debugui` (a separate module) provides immediate-mode
  debug panels (sliders, checkboxes) for tuning during development.

## UI states, attention and ownership

For each element, name the decision it supports and when it is needed. Keep
urgent information visible when the threat exists; delay/coalesce less urgent
messages instead of letting a loot notification obscure the next action.
Optional details may appear contextually, but provide a way to recover an
important instruction. Distinguish unavailable, temporarily cooling down,
selected and active states, including why an attempted action was refused.
These are useful attention-management patterns from
[game-ui-design](https://github.com/omer-metin/skills-for-antigravity/blob/e8dcf4e8737921a10088bd5c9eb65e81f74c051f/skills/game-ui-design/references/patterns.md),
not reasons to impose a combat HUD on every game.

For advertised keyboard/gamepad paths, define initial focus, neighbors and back
behavior. A modal owns input; closing it restores a still-valid previous control
or a deliberate fallback. Skip hidden/disabled items, and prevent the same press
that opens/closes an overlay from also activating a control or gameplay behind
it. Mouse hover and persistent focus need not be the same state. This develops
the focus lifecycle in `game-ui-ux` (its layout-and-flow reference).

Reserve stable space for changing numbers (score, time, ammunition); measure the
largest supported representation or use suitable tabular digits. Test transitions
such as 9→10 and 99→100, long localized labels, disabled actions and simultaneous
alerts. This prevents layout movement at the moment attention is most occupied,
as emphasized by [Three.js game UI patterns](https://github.com/majidmanzarpour/threejs-game-skills/blob/8286774b22a2566bf894dbc825825c16921866af/skills/threejs-game-ui-designer/references/ui-patterns.md).
Its CSS choices and aesthetic dislikes are not engine or genre requirements.

The UI reads an authoritative model and dispatches intents rather than duplicating
legality/scoring rules. In Ebitengine, reading a small value in `Draw` is often
appropriate; cache costly formatting/wrapping or use change events when useful.
If using subscriptions, manage their lifetime on scene exit. Do not introduce a
global event bus simply to forbid harmless polling.

## Localization

For games that will ship in multiple languages, establish the catalog and text
layout before UI content grows. A small single-language prototype need not build
a localization system before testing its core mechanic.

- Every player-visible string goes through a catalog keyed by a stable ID; no
  literals in `Draw`. Keep the source language as the fallback so a missing
  translation shows English (or the key) instead of crashing.
- Embed a font for every shipped script (`text.NewMultiFace` above) and set
  `GoTextFace.Language` per locale; Japanese and Chinese share code points but
  not glyph shapes.
- Measure translated content instead of relying on a fixed expansion percentage;
  allow flexible button widths and test the longest shipped strings.
- Use whole sentences with placeholders (`"%d coins"`), never concatenate
  fragments; word order differs between languages. Plurals differ too: use
  `golang.org/x/text/message` or separate keys when counts matter.
- Pick the initial locale from the store or system, then let the player change
  it in options and save the choice.

```go
// i18n.go
package game

import (
	"encoding/json"
	"fmt"
	"io/fs"
	"os"
	"strings"

	"golang.org/x/text/language"
)

// Strings live in one JSON file per locale (assets/i18n/en.json, ja.json),
// keyed by stable IDs, never by the English text:
//
//	{"menu.start": "Start", "hud.coins": "Coins: %d"}
type Catalog struct {
	lang     string
	msgs     map[string]string
	fallback map[string]string // the source language, for missing keys
}

func LoadCatalog(fsys fs.FS, dir, lang, fallback string) (*Catalog, error) {
	read := func(l string) (map[string]string, error) {
		b, err := fs.ReadFile(fsys, dir+"/"+l+".json")
		if err != nil {
			return nil, err
		}
		m := map[string]string{}
		if err := json.Unmarshal(b, &m); err != nil {
			return nil, err
		}
		return m, nil
	}
	fb, err := read(fallback)
	if err != nil {
		return nil, err
	}
	c := &Catalog{lang: lang, msgs: fb, fallback: fb}
	if lang != fallback {
		if m, err := read(lang); err == nil {
			c.msgs = m
		} else {
			c.lang = fallback
		}
	}
	return c, nil
}

func (c *Catalog) Lang() string { return c.lang }

// T formats a message. Missing keys fall back to the source language, then
// to the key itself, so a missing string is visible but never crashes.
func (c *Catalog) T(key string, args ...any) string {
	s, ok := c.msgs[key]
	if !ok {
		if s, ok = c.fallback[key]; !ok {
			s = key
		}
	}
	if len(args) == 0 {
		return s
	}
	return fmt.Sprintf(s, args...)
}

// PickLocale matches what the platform reports (Steam language name, the
// browser's navigator.language, $LANG) against the locales the game ships.
func PickLocale(reported string, supported []language.Tag) language.Tag {
	if len(supported) == 0 {
		return language.Und // callers should validate shipped locales at startup
	}
	steam := map[string]string{"english": "en", "japanese": "ja", "schinese": "zh-Hans",
		"tchinese": "zh-Hant", "koreana": "ko", "french": "fr", "german": "de",
		"spanish": "es", "latam": "es-419", "brazilian": "pt-BR", "russian": "ru"}
	if t, ok := steam[reported]; ok {
		reported = t
	}
	reported = strings.SplitN(reported, ".", 2)[0] // ja_JP.UTF-8 -> ja_JP
	reported = strings.ReplaceAll(reported, "_", "-")
	tag, _ := language.Parse(reported) // errors leave language.Und
	m := language.NewMatcher(supported)
	_, i, _ := m.Match(tag)
	return supported[i]
}

// DesktopLocale reads the usual environment variables (Linux, macOS
// terminals). Windows and macOS apps should prefer the store's language or a
// setting in the options menu.
func DesktopLocale() string {
	for _, k := range []string{"LC_ALL", "LC_MESSAGES", "LANG"} {
		if v := os.Getenv(k); v != "" && v != "C" && v != "POSIX" {
			return v
		}
	}
	return ""
}
```

Browser builds read the language from JavaScript
(`js.Global().Get("navigator").Get("language").String()`) in a `//go:build js`
file; Steam builds can obtain the reported language through their store adapter
(publishing-and-platforms reference).

## Accessibility

Options that cost little in Ebitengine and widen the audience:

- **Remapping** required actions for the supported devices (input reference), including
  one-handed layouts where practical. Provide alternatives for required rapid
  tapping or simultaneous presses ("hold to repeat", toggle instead of hold).
- **Text size**: a UI scale option (draw UI into a layer scaled by 1–2×), and a
  minimum readable size for the target screen (`Readability` above).
- **Colour**: never encode meaning by colour alone; add shapes, icons or
  patterns. Check palettes with a colour-blindness simulator.
- **Motion and flashes**: options to reduce screen shake (scale the offset to 0,
  gameplay-systems reference) and disable flashing effects. A frequency rule alone
  does not establish flash safety; brightness, contrast and affected screen area
  also matter. Avoid unnecessary high-contrast flashes.
- **Audio**: separate music, effects and voice volumes; captions or on-screen
  cues for sounds that carry information.
- **Difficulty and timing**: consider assist modes, adjustable time limits and
  pausing where the genre permits. Keep UI and input responsive during slow
  motion: use an explicit simulation-time scale rather than lowering `SetTPS`.
  Lower TPS changes input/UI cadence, does not slow audio, and does not slow a
  physics step that computes `1/TPS`. Online games require an agreed pause policy.
- **Input devices**: verify a complete playthrough with each advertised device.
  A keyboard-only puzzle and a touch-only rhythm game need different support;
  avoid making mouse controls mandatory in an advertised gamepad path.

Collect these in an options scene and save them with the save data.
Choose the relevant options from the game's supported inputs and intended audience;
see the design-and-quality reference.

Source contracts: [text layout and measurement](https://github.com/hajimehoshi/ebiten/blob/v2.10.6/text/v2/text.go)
and [font source and size behavior](https://github.com/hajimehoshi/ebiten/blob/v2.10.6/text/v2/gotext.go).
