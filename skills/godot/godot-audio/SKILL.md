---
name: godot-audio
description: >
  Godot 4.7 audio APIs: AudioStreamPlayer 2D and 3D, the bus layout, AudioServer volume and mute,
  polyphony, looping imports and playback position for beat sync. Use when wiring SFX, music or
  volume sliders in Godot, or a sound is silent, cut off, does not loop or ignores its bus. Not
  for engine-neutral mixing, ducking or adaptive music (`audio-design`).
---

# Godot Audio (4.x)

Play, route and control sound through Godot's player nodes and `AudioServer`, then prove
the bus wiring with a headless check. Targets **Godot 4.7**; check `config/features` in
`project.godot` first.

## Workflow

1. **Read the bus layout first.** It lives in the file named by
   `audio/buses/default_bus_layout` (default `res://default_bus_layout.tres`); each
   `bus/N/name` is a bus. Bus names in scenes and code must match it exactly.
2. **Pick the node:** `AudioStreamPlayer` for music, UI and global SFX;
   `AudioStreamPlayer2D`/`3D` when distance and panning matter.
3. **Route every player** by setting `bus` (for example `&"SFX"`). Add a bus by editing the
   layout file, the Audio dock, or `AudioServer.add_bus()` at runtime.
4. **Volume is in decibels.** For 0..1 sliders use `volume_linear` on players and
   `AudioServer.set_bus_volume_linear()`, which convert for you.
5. **Loops are an import setting.** Set loop on the `.ogg`/`.mp3`/`.wav` import (or
   `AudioStreamWAV.loop_mode`), not on the player.
6. **Verify before you finish** (paths are relative to this skill's folder):
   - Run `godot --headless --path <project> --script <this skill>/assets/check_audio_buses.gd`.
     It loads the real bus layout and fails on every `bus = "..."` or `get_bus_index("...")`
     name it does not define, with file and line.
   - If `godot-nodes-scenes` is installed, run `python3 ../godot-nodes-scenes/scripts/check_godot_project.py <project>`
     to catch missing stream files.
   - Playback logic can be tested headless: the Dummy driver plays in real time, so
     `playing`, `get_playback_position()` and `finished` behave (see
     `godot-gdscript-headless-testing` for the runner). Loudness and mix cannot: ask the user
     to listen and report levels, clipping and anything inaudible.

## Patterns

### 1. One-shot SFX that can overlap

```gdscript
@onready var sfx: AudioStreamPlayer = $Sfx   # stream assigned in the scene

func _ready() -> void:
    sfx.max_polyphony = 4                      # default 1: a retrigger cuts the last play

func play_hit() -> void:
    sfx.pitch_scale = randf_range(0.95, 1.05)
    sfx.play()
```

For many variants use an `AudioStreamRandomizer` as the stream instead of code.

### 2. Volume slider and mute for a bus

```gdscript
func set_bus_volume(bus_name: StringName, value_0_to_1: float) -> void:
    var bus := AudioServer.get_bus_index(bus_name)
    if bus == -1:
        push_error("No audio bus named %s" % bus_name)
        return
    AudioServer.set_bus_mute(bus, value_0_to_1 <= 0.0)   # mute at 0 instead of -inf dB
    if value_0_to_1 > 0.0:
        AudioServer.set_bus_volume_linear(bus, value_0_to_1)
```

### 3. Crossfade between two music players

```gdscript
@onready var a: AudioStreamPlayer = $MusicA
@onready var b: AudioStreamPlayer = $MusicB

func crossfade_to(stream: AudioStream, secs := 1.5) -> void:
    b.stream = stream
    b.volume_db = -40.0
    b.play()
    var tw := create_tween().set_parallel(true)
    tw.tween_property(a, "volume_db", -40.0, secs)
    tw.tween_property(b, "volume_db", 0.0, secs)
    tw.chain().tween_callback(a.stop)   # bound to the old player now
    var old := a
    a = b
    b = old
```

### 4. Song time for beat sync

```gdscript
@onready var music: AudioStreamPlayer = $Music

func song_time() -> float:
    # playback position only updates once per mix; add the time since then, minus latency.
    return music.get_playback_position() + AudioServer.get_time_since_last_mix() \
        - AudioServer.get_output_latency()
```

Compare `song_time()` against beat times; `audio-design` covers quantizing and pre-roll.

## Gotchas

- **A sound plays on Master and ignores its bus volume** → its `bus` name does not exist.
  Godot falls back to Master without an error, reading `player.bus` back returns `Master`,
  and `get_bus_index()` returns -1 (later `AudioServer` calls on -1 print an out-of-bounds
  error). Run the bus check.
- **Half volume is still loud** → `volume_db = 0.5` is +0.5 dB. Use the linear helpers or
  `linear_to_db()`.
- **NaN or stuck volume after a fade to silence** → `linear_to_db(0.0)` is `-inf`, and
  `set_bus_volume_linear(bus, 0.0)` stores `-inf` too. Mute at zero, as in Pattern 2.
- **Rapid SFX cut each other off** → `max_polyphony` defaults to 1.
- **Music does not loop** → loop is off in the import settings or `loop_mode`.
- **3D sound is silent** → no current `Camera3D` or `AudioListener3D`, `max_distance` too
  small, or `unit_size` too low for the scene's scale.
- **An Area2D/Area3D reverb bus override does nothing (4.7+)** → positional players'
  `area_mask` now defaults to 0. Tick the area's layer in the player's `area_mask`.
- **Beat-synced visuals drift or jitter** → `get_playback_position()` alone steps once per mix
  chunk. Use Pattern 4. Headless runs report an output latency of 0, so tune latency on the
  real device.
- **Bus effects, reverb, doppler or AudioStreamGenerator silent only in the web build** →
  since 4.3 the web export plays through the browser's Web Audio API ("Sample" playback),
  which skips them. Set the player's `playback_type` to Stream, or
  `audio/general/default_playback_type.web` for the project, at the cost of more latency.

## References

- Read `references/buses-and-effects.md` for the layout file format, the full `AudioServer`
  API, the effect list, side-chain compression, `AudioStreamPolyphonic`,
  `AudioStreamInteractive` and friends, positional audio settings, and
  `AudioStreamGenerator`.
- `assets/check_audio_buses.gd` is the headless bus check used in step 6.

## Related skills

- `audio-design`: mixing levels, ducking, adaptive music and beat-sync technique.
- `godot-ui-control`: the sliders and toggles that call Pattern 2.
- `godot-animation`: tweens for fades.
- `godot-gdscript-headless-testing`: running playback tests in CI.

## Version notes

Last verified: 2026-11-11 against the Godot 4.7.2 class reference and a 4.7.2 headless run.

- Godot 4.7.2 (August 2026) is the current stable release; 4.8 is in beta.
- `volume_linear` on players and `AudioServer.set_bus_volume_linear()` exist since 4.4.
- Web exports use Sample playback (Web Audio API) by default since 4.3.
- 4.7 changed `area_mask` on `AudioStreamPlayer2D`/`3D` to default 0 (GH-107679).
- Sources: [Godot releases](https://github.com/godotengine/godot/releases),
  [Upgrading to Godot 4.7](https://docs.godotengine.org/en/stable/tutorials/migrating/upgrading_to_godot_4.7.html),
  [Audio buses](https://docs.godotengine.org/en/stable/tutorials/audio/audio_buses.html),
  [Exporting for the Web: audio playback](https://docs.godotengine.org/en/stable/tutorials/export/exporting_for_web.html),
  [AudioServer](https://docs.godotengine.org/en/stable/classes/class_audioserver.html).
