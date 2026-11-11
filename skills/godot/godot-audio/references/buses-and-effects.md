# Audio buses & effects reference (Godot 4.7)

Depth companion to `godot-audio`.

## The bus layout

Buses are configured in the editor's **Audio** panel (bottom dock) and saved as a bus
layout resource (`default_bus_layout.tres` by default; set in Project Settings > Audio).

- **Master** always exists and is the final output. Every other bus routes to Master (or
  to another bus via **Send**).
- Add buses like `Music`, `SFX`, `UI`, `Ambience`. Set each player node's `bus` to route.
- Per bus: **volume (dB)**, **mute**, **solo**, **bypass effects**, and a chain of effects.

## AudioServer API

```gdscript
var i := AudioServer.get_bus_index("Music")
AudioServer.set_bus_volume_db(i, linear_to_db(0.8))
AudioServer.set_bus_volume_linear(i, 0.8)    # same thing, converts for you
AudioServer.set_bus_mute(i, true)
AudioServer.set_bus_solo(i, true)
AudioServer.get_bus_count()
AudioServer.add_bus(at_position)              # runtime bus creation
AudioServer.set_bus_send(i, "Master")
AudioServer.add_bus_effect(i, AudioEffectReverb.new())
AudioServer.get_bus_effect(i, effect_idx)
AudioServer.set_bus_effect_enabled(i, effect_idx, false)
AudioServer.get_output_latency()
AudioServer.get_time_since_last_mix()
```

Volume helpers: `linear_to_db(linear)` and `db_to_linear(db)`.

## Effects

Add `AudioEffect*` resources to a bus (editor or `add_bus_effect`):

- `AudioEffectReverb`, `AudioEffectDelay`, `AudioEffectChorus`, `AudioEffectDistortion`.
- `AudioEffectEQ6/EQ10/EQ21`, `AudioEffectLowPassFilter`, `AudioEffectHighPassFilter`.
- `AudioEffectCompressor`, `AudioEffectHardLimiter` (mastering; the older
  `AudioEffectLimiter` is deprecated).
- `AudioEffectPitchShift`, `AudioEffectSpectrumAnalyzer` (for visualizers/beat detection).
- `AudioEffectCapture` / `AudioEffectRecord` (read/record bus output).

## Side-chain ducking (music dips under dialogue/SFX)

1. Put music on a `Music` bus and add an `AudioEffectCompressor` to it.
2. Set the compressor's **Sidechain** to the bus whose loudness should trigger ducking
   (e.g. `Voice`). When `Voice` is loud, the compressor lowers `Music`.
3. Tune threshold/ratio/attack/release for a natural dip and recovery.

## Polyphony and interactive music

- `AudioStreamPolyphonic` — one player that can play many overlapping streams; grab a
  `AudioStreamPlaybackPolyphonic` from `get_stream_playback()` and call `play_stream(...)`.
- `AudioStreamInteractive` — define clips and transitions for adaptive music that switches
  between sections on cue (4.3+). `AudioStreamSynchronized` plays layered stems together, and
  `AudioStreamPlaylist` plays a list of streams in order or shuffled.
- `AudioStreamRandomizer` — pick a random stream/pitch per play (great for footsteps).

## Positional audio (2D/3D)

- `AudioStreamPlayer2D`: `max_distance`, `attenuation`, `panning_strength`, `area_mask`.
  Since 4.7 `area_mask` defaults to `0` on both positional players, so an `Area2D`/`Area3D`
  audio bus override is ignored until you tick the area's layer in the player's mask.
  Without a current `AudioListener2D` the hearing point is the centre of the screen; add one
  and call `make_current()` to hear from somewhere else.
- `AudioStreamPlayer3D`: `unit_size`, `max_distance`, `attenuation_model`
  (inverse/inverse-square/log/disabled), `panning_strength`, doppler via the player or
  camera. A `Camera3D` acts as the default listener; add an `AudioListener3D` to override.

## Procedural / generated audio

`AudioStreamGenerator` + `AudioStreamGeneratorPlayback.push_frame(Vector2)` lets you push
raw stereo samples for synthesis. Set `mix_rate` and `buffer_length`; keep the buffer
filled in `_process` to avoid underruns.

## Sync-to-beat recipe

```gdscript
const BPM := 120.0
var sec_per_beat := 60.0 / BPM
var last_beat := -1

func _process(_d: float) -> void:
    var t := music.get_playback_position() + AudioServer.get_time_since_last_mix() \
             - AudioServer.get_output_latency()
    var beat := int(t / sec_per_beat)
    if beat != last_beat:
        last_beat = beat
        _on_beat(beat)        # spawn, flash, or step a rhythm here
```
