---
name: platformer
description: >
  Designs 2D platformers in any engine: jump feel (coyote time, jump buffering, variable height,
  fall gravity, corner correction), wall jumps, hazards, checkpoints and one-way platforms. Use
  for a Mario- or Celeste-like, or a jump that feels floaty or laggy. Pair with the engine skill
  (`godot-2d-movement`, `phaser-arcade-physics`). Not for generic input buffering
  (`input-systems`) or juice (`game-feel`).
---

# Platformer

Owns how the jump feels and how levels are built around it. Numbers are engine-neutral, in
tiles and seconds, so they survive a change of tile size or engine. The engine's movement skill
supplies the body API (`godot-2d-movement`, `unity-physics`, `phaser-arcade-physics`).

## When to use

- Building a side-view game whose core verb is jumping between surfaces.
- Fixing feel: "floaty", "heavy", "the jump didn't register", "I fell off and couldn't jump",
  "I bonk on corners", short hops that are too tall or too short.

**When not to use:** top-down movement without gravity (engine movement skill), 3D traversal
(`fps-shooter` or the engine 3D skill), grid or turn-based movement (`roguelike`, `puzzle`).

## Workflow

1. **Read the controller first.** Find where velocity is integrated and at what rate: Godot
   `_physics_process` (60 Hz default), Unity `FixedUpdate` (0.02 s = 50 Hz default), Phaser
   Arcade (`fixedStep` on by default). Note the tile size, the y direction and the current
   constants. Ask which game the feel should resemble if the user has not said; "Mario-like"
   (momentum, heavy fall) and "Celeste-like" (instant, precise) need different targets.
2. **Pick targets** from the table below, in tiles and seconds.
3. **Derive the constants** with the calculator (path relative to this skill folder):
   `python3 scripts/jump_tuner.py --height 3.5 --apex-time 0.35 --tile 16 --tick 60
   --run-speed 8`. It prints rise and fall gravity and launch velocity, simulates the jump at
   the project's tick, and warns about apex error from the integrator, grace windows that lose
   a tick, tap-hop ratio and tunnelling. Add `--json` for machine-readable output.
4. **Implement the feel core** (Pattern 1) in this order: buffer, coyote, variable height,
   apex hang, fall cap, then corner correction. Run it on the fixed tick.
5. **Size the level to the measured reach.** Critical-path platforms sit at least half a
   tile below the reached apex and gaps at least one tile shorter than the gap reach the tool
   prints. Optional routes may use the full reach.
6. **Check it.** Add a debug switch that writes `t,y` for every physics tick of one jump
   (start on the tick the jump fires) to a CSV, run the scene (headless where the engine
   allows: `godot --headless`), then run `python3 scripts/jump_tuner.py <same targets> --log
   jump.csv`. Exit 1 means the measured apex height or time to apex is off by more than 5%.
   Then script these edge cases as tests and report what each one did: press 1 tick before
   landing, press N ticks after walking off a ledge (N = coyote ticks, then N + 1), tap versus
   hold, and jump into a ceiling corner 2 px off the edge.

## Feel targets

Starting points. The Celeste column comes from its published `Player.cs` (8 px tiles, 60 Hz);
use it as a "precise and snappy" reference, not as the only right answer.

| Knob | Start here | Range | Celeste |
|------|-----------|-------|---------|
| Full jump height | 3.5 tiles | 2-5 | about 3.5 tiles (28 px) |
| Time to apex | 0.35 s | 0.25-0.45 | about 0.37 s |
| Full airtime on flat ground | 0.6-0.7 s | 0.5-0.9 | about 0.68 s |
| Tap hop | 30% of full | 15-60% | about 20% |
| Fall gravity | 1.8 x rise | 1.3-2.5 | same as rise, but terminal speed capped low |
| Terminal fall speed | 18-25 tiles/s | keep under half a tile per tick | 20 tiles/s, 30 with fast-fall |
| Apex hang | half gravity while held and vertical speed under ~40% of launch speed | 0.4-0.6 x | half gravity under 40 of 105 px/s |
| Coyote time | 0.1 s | 0.06-0.15 | 0.1 s |
| Jump buffer | 0.1-0.15 s | 0.05-0.2 | not in the published file |
| Ground acceleration | top speed in 0.05-0.1 s | instant to 0.2 s | 0.09 s |
| Air control | 0.65 x ground accel | 0.5-1.0 | 0.65 x |
| Ceiling corner correction | up to half a tile sideways | 1/4-1/2 tile | 4 px |
| Wall-jump steering lock | 0.15 s | 0.1-0.2 | 0.16 s |

Floatiness usually comes from a long apex hang, a low terminal speed or a long time to apex,
not only from symmetric gravity. Change one knob at a time and re-run the calculator.

## Pattern 1: the feel core

Count grace windows in whole ticks at the fixed rate. A float countdown such as
`timer -= dt; if timer > 0` silently loses a tick at some rates (0.1 s at 50 Hz gives 4 ticks,
not 5), so the same build feels different in Unity and Godot. Tick stamps avoid that and also
let Unity's `Update` record a press for `FixedUpdate` to consume.

```python
# Pseudocode at the fixed tick. y points DOWN. Constants come from jump_tuner.py.
COYOTE_TICKS = round(COYOTE_TIME * TICK_RATE)     # 0.1 s at 60 Hz -> 6
BUFFER_TICKS = round(JUMP_BUFFER * TICK_RATE)     # 0.12 s at 60 Hz -> 7
NEVER = -10**9                                     # initial value of both stamps

tick += 1
if on_floor and velocity.y >= 0:
    last_ground_tick = tick                        # refresh only while standing, not rising
if jump_pressed_this_tick:
    last_press_tick = tick

if tick - last_press_tick <= BUFFER_TICKS and tick - last_ground_tick <= COYOTE_TICKS:
    velocity.y = JUMP_VELOCITY                     # negative = up
    last_press_tick = last_ground_tick = NEVER     # consume both: no second jump from coyote
    if not jump_held:                              # buffered press already released: short hop
        velocity.y *= JUMP_CUT

if jump_released_this_tick and velocity.y < 0:
    velocity.y *= JUMP_CUT                         # 0.4-0.6; only while rising

g = FALL_GRAVITY if velocity.y > 0 else RISE_GRAVITY
if jump_held and abs(velocity.y) < APEX_THRESHOLD:
    g *= APEX_HANG                                 # 0.5
velocity.y = min(velocity.y + g * dt, MAX_FALL_SPEED)
# then move and collide once; on a ceiling hit try corner correction (refs §4), else zero vy
```

Variable height has three common models. Use the release cut above by default: it is one line
and gives a fixed minimum hop. For precision platformers use the Celeste model instead: hold
the launch speed for up to ~0.2 s while the button is held, then let gravity act; release ends
the hold. The third model raises gravity (2-3 x) while rising with the button up; it gives the
smoothest arc but is the hardest to reason about. Pick one; mixing two doubles the effect.

## Engine pointers

- **Godot 4:** run the controller in `_physics_process`; `Input.is_action_just_pressed()`
  reports presses per physics tick, so it is safe there. `is_on_floor()` is valid after
  `move_and_slide()`. Body API, slopes and moving platforms: `godot-2d-movement`.
- **Unity 6:** `Rigidbody2D.linearVelocity` (`velocity` is obsolete). Record the press in
  `Update` (set a flag or the tick number) and consume it in `FixedUpdate`; polling a "pressed
  this frame" call inside `FixedUpdate` can miss or repeat presses. y points up, so flip the
  signs above. One-way platforms: `PlatformEffector2D`.
- **Phaser 4 Arcade:** `body.blocked.down` or `body.onFloor()`, `Phaser.Input.Keyboard.JustDown`
  in `update`; y points down. See `phaser-arcade-physics`.

## Gotchas

- **Jump height changes with frame rate** → integration runs on a variable `dt`. The usual
  "add gravity, then move" step peaks short by about `v0 * dt / 2` (about 5% of a 3.5-tile jump
  at 60 Hz, more at 30 Hz). Run on the fixed tick and design to the simulated apex, or use the
  half-step update (refs §1, `--integrator half`).
- **Double jump inside the coyote window** → coyote was not zeroed when the jump fired, or it
  refreshes while still rising off the floor on the first tick. Consume both timers on jump and
  refresh coyote only when `velocity.y >= 0`.
- **Buffered jump is always full height** → the release happened before landing, so the
  release edge never reaches the rising jump. Check the held state when the buffered jump fires.
- **Head-bonk keeps the jump sustained** → a ceiling hit must zero upward speed and end the
  variable-height hold (Celeste allows 0.05 s of grace before ending it).
- **Player is flung off or doubles speed leaving a moving platform** → platform velocity added
  twice. Godot's `CharacterBody2D` already adds it on leave (`platform_on_leave`); Unity's
  `CharacterController` does not carry riders at all (refs §6).
- **Wall jump eats the ground jump or the double jump** → resolve one buffered press in
  ground/coyote, then wall, then air order, with an explicit air-jump refresh rule (refs §9).
- **Snagging on tile seams** → per-tile box colliders. Merge level collision into larger shapes
  and use one capsule or rounded box for the player.
- **Falling through thin floors** → terminal speed moves more than half a tile per tick. The
  calculator warns; cap fall speed or enable continuous collision (`physics-tuning`).
- **Presses lost in Unity** → input polled in `FixedUpdate`. Latch it in `Update`.

## References

- `references/feel-tuning.md`: read when you need the jump math derivation and half-step
  integrator, apex hang and fast-fall code, ceiling corner correction, one-way drop-through,
  moving-platform behaviour per engine, or the full wall slide and wall jump resolver.
- `scripts/jump_tuner.py --help`: every option of the calculator and the log check.

Related: `level-design` (teaching order, pacing), `camera-systems` (platformer camera
deadzone and look-ahead), `game-feel` (landing dust, squash, hit-stop), `input-systems`
(rebinding, gamepad, generic input buffers).

## Version notes

Last verified: 2026-11-11.

- Celeste numbers: `Source/Player/Player.cs` in https://github.com/NoelFB/Celeste (MIT, file
  released 2018): `JumpGraceTime` 0.1, `JumpSpeed` -105, `VarJumpTime` 0.2, `Gravity` 900,
  `HalfGravThreshold` 40, `MaxFall` 160, `FastMaxFall` 240, `MaxRun` 90, `RunAccel` 1000,
  `AirMult` 0.65, `UpwardCornerCorrection` 4, `WallJumpForceTime` 0.16,
  `CeilingVarJumpGrace` 0.05. Height, apex time and tap hop were computed from these at 60 Hz.
- Godot 4.7.2: `Input.is_action_just_pressed` documents per-physics-tick behaviour
  (doc/classes/Input.xml).
- Unity 6.3 LTS: `Rigidbody2D.linearVelocity`; default fixed timestep 0.02 s
  (https://docs.unity.com/en-us/engine/6000.6/manual/physics-section/physics-overview/physics-optimization/cpu/frequency).
- Phaser 4.2.1: Arcade `fixedStep` defaults to true; `Keyboard.JustDown` and `body.onFloor()`
  exist in the shipped typings.
- Jump-from-height-and-time method: Kyle Pittman, "Math for Game Programmers: Building a Better
  Jump", GDC 2016.
