# Audio

Ebitengine v2.10, package `github.com/hajimehoshi/ebiten/v2/audio` with the
`wav`, `vorbis` and `mp3` decoders. API baseline: v2.10.6. Snippets require the
project's imports and error handling around their callers.

## Contents

- [Rules](#rules)
- [Effects and music](#effects-and-music)
- [Browsers and mobile](#browsers-and-mobile)
- [Machines without a sound device](#machines-without-a-sound-device)
- [Designing the sounds](#designing-the-sounds)

## Rules

- **One context per process.** `audio.NewContext(rate)` panics with
  `audio: context is already created` on a second call. Create it at start-up
  and pass it around; `audio.CurrentContext()` returns it.
- **One sample rate.** 48000 is a safe default (44100 also works). All players
  run at the context's rate.
- **Decoders and resampling.**

| Decoder | Output | Resamples? | Play with |
| --- | --- | --- | --- |
| `wav/vorbis/mp3.DecodeF32(r)` | 32-bit float stereo | **no**: `Stream.SampleRate()` is the file's rate | `ctx.NewPlayerF32`, `NewPlayerF32FromBytes`, `NewInfiniteLoopF32` |
| `DecodeWithSampleRate(rate, r)` | 16-bit stereo | yes, to `rate` | `ctx.NewPlayer`, `NewPlayerFromBytes`, `NewInfiniteLoop` |
| `Decode(ctx, r)` | — | — | deprecated since v2.1 |

  Mixing F32 streams with `NewPlayer` (or 16-bit streams with `NewPlayerF32`)
  plays noise. A 44.1 kHz file through `DecodeF32` into a 48 kHz context plays
  about 9% too fast and high. Convert assets to the context rate, or use
  `DecodeWithSampleRate`.
- **Start sounds from `Update`**, where game events happen. `Draw` can run zero
  or several times per tick.

## Effects and music

```go
const sampleRate = 48000

type Audio struct {
	ctx *audio.Context
	sfx map[string][]byte
	bgm *audio.Player
}

func NewAudio() *Audio {
	return &Audio{ctx: audio.NewContext(sampleRate), sfx: map[string][]byte{}}
}

// LoadSFX decodes a WAV once into memory. DecodeF32 does not resample, so the
// file must already be at the context's rate.
func (a *Audio) LoadSFX(name string, wavData []byte) error {
	s, err := wav.DecodeF32(bytes.NewReader(wavData))
	if err != nil {
		return err
	}
	if s.SampleRate() != a.ctx.SampleRate() {
		return fmt.Errorf("%s: %d Hz, want %d Hz (convert the file or use DecodeWithSampleRate)",
			name, s.SampleRate(), a.ctx.SampleRate())
	}
	b, err := io.ReadAll(s)
	if err != nil {
		return err
	}
	a.sfx[name] = b
	return nil
}

// PlaySFX makes a new short-lived player per call; overlapping plays are fine.
func (a *Audio) PlaySFX(name string, volume float64) {
	b, ok := a.sfx[name]
	if !ok {
		return // alternatively report an asset-ID error during development
	}
	p := a.ctx.NewPlayerF32FromBytes(b)
	p.SetVolume(volume)
	p.Play()
}

// PlayBGM streams an Ogg file and loops it forever. Keep and reuse the player.
func (a *Audio) PlayBGM(oggData []byte) error {
	s, err := vorbis.DecodeF32(bytes.NewReader(oggData))
	if err != nil {
		return err
	}
	if s.SampleRate() != a.ctx.SampleRate() {
		return fmt.Errorf("bgm: %d Hz, want %d Hz", s.SampleRate(), a.ctx.SampleRate())
	}
	if s.Length() <= 0 {
		return fmt.Errorf("bgm: loop needs a known positive PCM length")
	}
	loop := audio.NewInfiniteLoopF32(s, s.Length())
	p, err := a.ctx.NewPlayerF32(loop)
	if err != nil {
		return err
	}
	if a.bgm != nil {
		a.bgm.PauseAndStopReading()
	}
	a.bgm = p
	a.bgm.SetVolume(0.5)
	a.bgm.Play()
	return nil
}
```

A file at another rate, decoded with resampling:

```go
func playResampled(ctx *audio.Context, wavData []byte) (*audio.Player, error) {
	s, err := wav.DecodeWithSampleRate(ctx.SampleRate(), bytes.NewReader(wavData))
	if err != nil {
		return nil, err
	}
	return ctx.NewPlayer(s) // 16-bit stream: NewPlayer, not NewPlayerF32
}
```

- Short effects: decode bounded assets to bytes at load, new
  player per play. Do not reuse one player for rapid repeats: `Rewind` on a playing
  player cuts the previous sound. Limit simultaneous voices to fit the game's
  mix and performance budget.
- Music: stream (do not `io.ReadAll` long tracks), one player, reused.
  `NewInfiniteLoopWithIntroF32(src, introBytes, loopBytes)` plays an intro once
  and loops the rest. Byte lengths for F32 stereo are `seconds × rate × 8`.
  Looping an entire lossy file is not a guarantee of a seamless musical loop:
  audition its join. The loop API can blend across the seam when source audio
  extends beyond the loop end; provide intentional loop boundaries and a tail.
- Volume is linear 0–1 (`SetVolume`); a mute toggle sets it to 0. Fades: change
  the volume a little each tick in `Update`.
- Use `PauseAndStopReading` before releasing or closing the source (v2.10
  deprecates `Close`). This pauses and stops background reads; it does not
  destroy the player, and `Play` can resume it.
  `SetPosition`/`Position` replace the deprecated `Seek`/`Current`.
- Pitch variation for repeated effects: prepare 2–4 decoded variants (slightly
  different pitches or recordings) and pick one at random; Ebitengine has no
  per-player pitch control.
- Stereo panning: wrap the stream in your own `io.Reader` that scales left and
  right samples; see `examples/audiopanning` for the pinned version.

## Browsers and mobile

- Browsers allow audio only after a user gesture. The context reports
  `ctx.IsReady()` once audio can start; start music from a title-screen action
  rather than at load. When embedding in a page, give the iframe
  `allow="autoplay"`.
- On mobile, audio pauses with the app when the host calls `suspendGame()`; see
  the project-and-builds reference.

## Machines without a sound device

If no audio device can be opened and the app creates an audio context, the audio
context reports an error and `RunGame` returns
`audio: audio error: ... initialization failed ...`. For headless runs either
start a PulseAudio/PipeWire server or point ALSA at its null device:

```sh
null_audio_dir=$(mktemp -d)
printf 'pcm.!default { type null }\n' > "$null_audio_dir/asound.conf"
ALSA_CONFIG_PATH="$null_audio_dir/asound.conf" xvfb-run -a ./game
rm -r "$null_audio_dir"
```

This applies to Linux ALSA configuration; it does not produce audible output or
verify playback quality. Use an explicit project save path for automated runs
so tests do not overwrite player saves. Other audio backends need their own
virtual-device setup.

## Designing the sounds

This reference covers playback. For what the sounds should be (layering,
variation, mixing against music), use the game's brief and
quality criteria (design-and-quality reference). Procedurally generated
PCM can be played directly: build little-endian float32 stereo bytes and pass
them to `NewPlayerF32FromBytes`, as the starter's `sound.go` does. Match attack,
material, pitch, duration and space to the event; a broadband transient helps
many contacts, but sustained ambience and soft UI feedback need different
envelopes. Check clipping, repeated playback, music masking and the loop join
by ear when playback is available; mark unlistened audio explicitly.

Source contracts: [players and lifecycle](https://github.com/hajimehoshi/ebiten/blob/v2.10.6/audio/audio.go)
and [loop lengths and seam blending](https://github.com/hajimehoshi/ebiten/blob/v2.10.6/audio/loop.go).
