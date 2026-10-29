---
name: audio-design
description: >
  Implement game audio practice — bus/mixer architecture and gain in decibels,
  ducking (sidechain), adaptive/dynamic music via layering and re-sequencing,
  SFX variation, and beat synchronization. Engine-neutral. Use when the user
  mentions audio mixing, audio buses, adaptive/dynamic music, ducking, SFX
  variation, music layers, or syncing gameplay to the beat.
---

# Audio design

Game audio is a **mixing graph plus a music system**. Route every sound through a
small set of buses so you can balance and process groups; make music *react* to
play through layering and re-sequencing rather than looping one track. This skill
teaches the portable practice; bind it to `godot-audio`, Unity's AudioMixer, or
middleware (FMOD/Wwise) for concrete APIs.

## When to use

- Use to design a bus/mixer layout, set group volumes, and apply effects (reverb,
  compression, EQ) to groups of sounds.
- Use to duck music/ambience under dialogue or impacts (sidechain).
- Use to build adaptive music that responds to combat/exploration intensity.
- Use to add SFX variation (pitch/sample randomization) and sync events to a beat.

**When *not* to use:** for the engine's concrete audio nodes/streams, use
`godot-audio` or the engine's audio skill. Loading/streaming and asset import are
engine concerns. For UI sliders that drive bus volume, see the engine UI skill.

## Core workflow

1. **Lay out buses, not per-sound volume.** A typical tree: `Master ← {Music,
   SFX, Ambience, UI, Voice}`. Everything plays into a bus; the player's settings
   sliders map to bus volumes. Never set hundreds of clip volumes by hand.
2. **Work in decibels, not linear.** Perceived loudness is logarithmic. Volume
   controls and automation should operate in dB; convert only at the edges.
3. **Leave headroom and hit a loudness target.** Keep true peaks at or below -1 dBTP and
   measure integrated loudness over a representative play session with an ITU-R BS.1770 meter.
   Sony's ASWG-R001 recommendation, the usual reference, is -24 LUFS (±2) for console/PC
   played on TVs and speakers and -18 LUFS (±2) for handheld/mobile. Music-streaming targets
   such as -14 LUFS are not game targets.
4. **Duck competing sources** with a sidechain compressor (or volume automation):
   when voice/important SFX plays, the music bus dips, then recovers.
5. **Make music adaptive** via *vertical* layering (stems faded in/out) and/or
   *horizontal* re-sequencing (swap segments at musical boundaries). See the
   reference.
6. **Vary repeated SFX** with small random pitch/volume offsets and sample pools
   so footsteps and hits don't sound robotic.
7. **Verify on real output.** Listen on headphones and speakers; check that the
   mix balances, ducking is audible but not pumping, and music transitions land
   on the beat — never assume from the editor meters alone.

## Patterns

Snippets are Godot 4.7 GDScript; the Unity 6.3 LTS and middleware equivalents are noted
under each one.

### 1. Bus routing and slider-to-gain mapping

```gdscript
# Route sounds to named buses; control GROUPS, not individual clips.
sfx_player.bus = &"SFX"
music_player.bus = &"Music"

# Map a 0..1 settings slider to bus gain. Squaring the slider first spreads the
# audible change over the whole travel; a raw linear-amplitude slider puts most of
# the change in the bottom fifth.
func set_bus_volume(bus_name: StringName, slider01: float) -> void:
    var idx := AudioServer.get_bus_index(bus_name)
    var gain := clampf(slider01, 0.0, 1.0)
    AudioServer.set_bus_mute(idx, gain <= 0.0)             # true silence at 0
    AudioServer.set_bus_volume_linear(idx, gain * gain)    # = set_bus_volume_db(idx, linear_to_db(gain * gain))
# WRONG: AudioServer.set_bus_volume_db(idx, slider01): "0.5" is +0.5 dB (no audible
# change) and 0 is 0 dB (full volume).
```

Unity 6.3 LTS: expose the group's Volume as a mixer parameter, then
`mixer.SetFloat("MusicVolume", 20f * Mathf.Log10(Mathf.Max(gain * gain, 0.0001f)))` (the mixer
floor is -80 dB). An `AudioSource` whose Output group is empty plays outside your mixer groups,
so no category slider or snapshot affects it: route every source.

### 2. Ducking via sidechain (music dips under voice)

A compressor on the music bus, keyed by the voice bus, lowers the music while dialogue plays and
releases afterwards. Starting values: threshold about -30 dB on the voice signal, ratio 4:1 to
8:1, attack as fast as the effect allows (up to ~10 ms), release 300-500 ms.

```gdscript
# Godot 4.7: AudioEffectCompressor reads its sidechain bus for threshold detection.
func _ready() -> void:
    var duck := AudioEffectCompressor.new()
    duck.sidechain = &"Voice"      # the bus that triggers the dip
    duck.threshold = -30.0         # dB, range -60..0
    duck.ratio = 8.0               # range 1..48
    duck.attack_us = 2000.0        # MICROseconds, range 20..2000 (2 ms is the maximum)
    duck.release_ms = 400.0        # milliseconds, range 20..2000
    AudioServer.add_bus_effect(AudioServer.get_bus_index(&"Music"), duck)

# No-compressor alternative: tween a dedicated "MusicDuck" bus that sits between
# Music and Master, so ducking never overwrites the player's Music slider.
func duck_music(active: bool) -> void:
    var idx := AudioServer.get_bus_index(&"MusicDuck")
    var from := AudioServer.get_bus_volume_db(idx)
    var to := -12.0 if active else 0.0
    create_tween().tween_method(
        func(db: float) -> void: AudioServer.set_bus_volume_db(idx, db), from, to, 0.25)
```

Unity 6.3 LTS: add a **Duck Volume** effect to the Music group and a **Send** effect on the Voice
group targeting it. FMOD Studio and Wwise have sidechain/auto-ducking on buses; prefer those over
script tweens when the project already uses middleware.

### 3. SFX variation (kill the "machine gun" repeat)

```gdscript
# Godot 4.7: AudioStreamRandomizer picks a take (no immediate repeats by default)
# and randomizes pitch and volume on every play. No per-shot node allocation.
func make_footsteps(samples: Array[AudioStream]) -> void:
    var rnd := AudioStreamRandomizer.new()
    for s in samples:
        rnd.add_stream(-1, s)                 # -1 appends; optional third arg = weight
    rnd.random_pitch_semitones = 1.0          # up to +/-1 semitone (about 6%)
    rnd.random_volume_offset_db = 2.0         # up to +/-2 dB
    $Footsteps.stream = rnd
    $Footsteps.max_polyphony = 4              # overlapping steps without new players
```

Unity 6.3 LTS has no built-in randomizer: keep an array of clips, pick one that differs from the
last, set `pitch` in a small range, and call `PlayOneShot` on a pooled `AudioSource`.

### 4. Beat-synced events (quantize to the music grid)

```gdscript
# Schedule gameplay/visuals on musical time, not frame time, so they land on beat.
const BPM := 120.0
const SECONDS_PER_BEAT := 60.0 / BPM

# What the player HEARS now: playback position, plus time since the last mix
# (the position only updates once per mixed chunk), minus output latency.
func song_time() -> float:
    return ($Music.get_playback_position() + AudioServer.get_time_since_last_mix()
            - AudioServer.get_output_latency())

func current_beat() -> int:
    return floori(song_time() / SECONDS_PER_BEAT)  # negative means beat 0 is not audible yet

# Quantize an action to the NEXT beat boundary instead of firing immediately.
func time_until_next_beat() -> float:
    var time := song_time()
    if time < 0.0:
        return -time                             # pre-roll: wait for the first audible beat
    return SECONDS_PER_BEAT - fposmod(time, SECONDS_PER_BEAT)
# At an exact non-negative beat boundary, NEXT means one full beat later.
```

Unity 6.3 LTS: read `AudioSettings.dspTime` and schedule with `AudioSource.PlayScheduled(dspTime)`
for sample-accurate starts.

## Pitfalls

- **Treating slider values as dB.** Map `0..1` to gain (`linear_to_db`, or
  `set_bus_volume_linear`) and back with `db_to_linear`. A raw linear-amplitude
  slider sounds almost unchanged over most of its travel and drops off at the
  bottom; squaring (or cubing) the slider before conversion evens it out.
- **Per-clip volume instead of buses** makes a global balance pass impossible and
  bloats save/settings. Mix on buses.
- **Sources that bypass the mix.** A Unity `AudioSource` with no Output group, or a
  Godot player left on `Master`, ignores the category sliders. Route everything.
- **Clipping the master.** Summed sounds exceed 0 dBFS and distort. Leave
  headroom; put a limiter on Master as a safety net, not as the mixer.
- **Pumping ducking**: too-fast release or too-high ratio makes music audibly
  breathe. Lengthen release; lower ratio.
- **Ducking that fights the volume slider.** Tweening the Music bus back to 0 dB
  overwrites the player's setting. Duck a separate bus, or use the compressor.
- **Looping a single music track** for the whole game feels flat. Use layers or
  segments that respond to state (see the reference).
- **Beat sync off frame time.** `delta` drifts; read the **audio playback
  position**, add the time since the last mix, and subtract output latency.
- **Unbounded one-shot players**: spawning AudioStreamPlayers without freeing
  them leaks. Use `max_polyphony`/`AudioStreamRandomizer`, free on `finished`, or
  pool them.

## References

- `references/adaptive-music.md` — vertical layering vs horizontal re-sequencing,
  transition timing (bars/quantize), stingers, intensity mapping, and crossfades.

## Related skills

- `godot-audio` — buses, `AudioStreamPlayer`, effects, and sync-to-beat in Godot.
- `input-systems` — trigger audio from input actions.
- `physics-tuning` — collision events that drive impact SFX.
- `platformer`, `roguelike` — genres whose feel leans on audio feedback.
