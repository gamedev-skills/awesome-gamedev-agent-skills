# Platformer feel tuning (depth)

Depth behind `SKILL.md`. Engine-neutral pseudocode; the math is standard kinematics. Tune by
outcome (tiles of height, seconds to apex), then read off the physics values with
`scripts/jump_tuner.py`.

Contents:
1. Deriving jump physics and the half-step integrator
2. Variable jump height: the hold (sustain) model
3. Apex hang and fast-fall
4. Corner correction
5. One-way platforms and drop-through
6. Moving platforms per engine
7. Camera follow (pointer)
8. Teaching and pacing
9. Wall slide and wall jump

## 1. Deriving jump physics

A jump is just projectile motion. Choose the two values a designer can actually feel —
**peak height** `h` and **time to reach the peak** `t` — and solve for the rest. With the
y-axis pointing down (most 2D engines):

```
gravity        g  = 2h / t²
jump_velocity  v0 = -2h / t          # negative = upward
peak reached after t seconds; total airtime ≈ 2t (symmetric gravity)
```

Asymmetric gravity makes the fall snappier than the rise without changing peak height:

```
rise_gravity = g
fall_gravity = g * fall_multiplier   # 1.5–2.0 feels good
# airtime shortens; the arc looks like a fast, weighty drop after a quick pop up.
```

If you instead know the jump velocity and want the height: `h = v0² / (2g)`.

These formulas describe continuous motion. A game integrates in steps, and the usual
"add gravity to velocity, then add velocity to position" update peaks short by about
`v0 · dt / 2`: with a 56 px jump and a 0.35 s apex that is ~2.7 px at 60 Hz and ~5 px at 30 Hz.
Fixed-tick physics keeps the error the same on every machine (tune by eye and accept it). To hit
the designed height exactly, apply half the gravity before the move and half after:

```python
velocity.y += 0.5 * g * dt
position.y += velocity.y * dt       # or move_and_slide() / CharacterController.Move here
velocity.y += 0.5 * g * dt
```

## 2. Variable jump height: the hold (sustain) model

The release cut in `SKILL.md` is the default. Precision platformers (Celeste is the usual
reference) instead hold the launch speed while the button is held, for a capped time, and end
the hold on release or on a ceiling hit. Tap height then comes from gravity alone, so it stays
small (about 20% of a full jump with Celeste's numbers) and the full height depends on the hold
time as much as on gravity.

```python
# On jump: start the hold.
velocity.y = -LAUNCH_SPEED
hold_ticks = round(HOLD_TIME * TICK_RATE)        # Celeste: 0.2 s

# Every tick, after applying gravity:
if hold_ticks > 0:
    if jump_held and not hit_ceiling:
        velocity.y = min(velocity.y, -LAUNCH_SPEED)  # keep rising at launch speed
        hold_ticks -= 1
    else:
        hold_ticks = 0                           # release or bonk ends the hold for good
```

With this model, full height = `LAUNCH_SPEED * HOLD_TIME` plus the free rise
`LAUNCH_SPEED^2 / (2g)` (less with apex hang), so `jump_tuner.py`'s height-and-time solution
does not apply directly. Tune hold time for full height and gravity for tap height.

## 3. Apex hang and fast-fall

```python
# Reduced gravity near the apex gives a moment of extra air control ("hang time").
if abs(velocity.y) < APEX_THRESHOLD and not on_floor:
    g = g * 0.5

# Optional fast-fall: holding Down past the apex increases downward gravity.
if holding_down and velocity.y > 0:
    g = g * 1.5
```

## 4. Corner correction (ceiling and ledge nudging)

When a rising jump clips a corner by a pixel or two, players read it as the game being
"sticky". Nudge them past it instead of stopping the jump dead:

```python
# On hitting a ceiling while rising, if only the outer 1–4 px are blocked, shift the body
# sideways into the free space and keep the upward velocity. Test both directions, at the
# position the body is trying to move to this step.
if blocked_overhead and velocity.y < 0:
    target = position + Vector2(0, velocity.y * dt)
    for offset in (1, 2, 3, 4):                        # smallest nudge first
        for side in (-1, +1):
            if free_at(target + Vector2(side * offset, 0)):
                position.x += side * offset
                break                                  # keep rising; don't zero velocity.y
        else:
            continue
        break
```

Only nudge when the blocked part is a corner, never when the player is under a solid ceiling
more than a few pixels wide; the 4 px cap is what enforces that.

The same idea on landing edges (a few px of "ledge grab"/snap) makes platforms feel generous.

## 5. One-way platforms and drop-through

- Mark the platform's collision as one-directional (solid only when the player is above and
  moving down). Engines expose this directly — do not hand-roll it (Godot
  `CollisionShape2D.one_way_collision`, Unity `PlatformEffector2D` **Use One Way**, Phaser Arcade
  `body.checkCollision.down = false` on the platform).
- **Drop-through:** when the player holds Down + Jump on a one-way platform, disable that
  collision for ~0.1–0.2 s (or until the player's top passes below the platform), then re-enable.
  In Godot, clear the platform's layer from the player's `collision_mask` for that window rather
  than disabling the shape, so other bodies still land on it.

## 6. Moving platforms

- Carry the player: add the platform's per-frame delta to the player's position while standing
  on it, so they ride it instead of sliding off.
- Apply the platform's velocity to the player on jump-off so leaps from a moving platform feel
  physical. Cap the inherited horizontal velocity so it can't fling the player uncontrollably.
- **Check what the engine already does before adding either.** Godot 4.7 `CharacterBody2D`
  follows floor bodies on `platform_floor_layers` during `move_and_slide()` and, by default,
  adds the platform's velocity when you leave it (`platform_on_leave =
  PLATFORM_ON_LEAVE_ADD_VELOCITY`; `ADD_UPWARD_VELOCITY` drops the downward part, `DO_NOTHING`
  turns it off). Move the platform as an `AnimatableBody2D` so it reports a velocity. Phaser
  Arcade carries a rider horizontally when the platform is an immovable *dynamic* body that is
  moving (`body.friction`, default `(1, 0)`); a static body does not. Unity's
  `CharacterController` does not carry riders; add the delta yourself.

## 7. Camera follow (pointer)

Platformer cameras need a deadzone, look-ahead in the facing direction, frame-rate
independent smoothing and level-bounds clamping, with vertical follow locked or slowed during
ordinary hops. The `camera-systems` skill owns that code; load it rather than rebuilding it
here.

## 8. Teaching and pacing (hand-off to `level-design`)

- Introduce one mechanic in isolation, let the player practice it safely, *then* combine it
  with a known one. Never introduce two new things in the same hazard.
- Place the first instance of any lethal hazard where failure is cheap (near a checkpoint,
  no long re-traversal).
- Keep checkpoint-to-checkpoint segments short early, longer later; respawn must be instant.

## 9. Wall slide and wall jump

Treat wall traversal as part of the existing jump resolver, not a second independent jump
script. Use fixed physics ticks and latched input edges. The following is engine-neutral
pseudocode for static, vertical walls with positive Y downward; names are controller state,
not engine APIs. Bind contact detection to the project's collision system. Distinguish walls
from floors/ceilings using contact normals, and use contacts from the latest completed physics
step or an explicit probe. Collision flags may disappear when the player stops pushing.

Remember the last valid wall side (`-1` left, `+1` right) for a short **wall-coyote** window.
Do not use the remembered contact to apply slide friction after the player has left the wall.
For a narrow passage with both sides touching, pick one side deterministically, such as the
side the player presses toward. Clear wall state on respawn, teleport, and scene changes.

| Knob | Starting experiment, not a universal default |
|------|---------------------------------------------|
| Wall-coyote window | 0.08–0.12 s |
| Wall jump height | about 0.8 × ground jump height |
| Horizontal kick speed | about 1.25 × run speed |
| Steering lock after kick | 0.10–0.15 s |
| Slide max fall speed | about 0.2 × normal terminal speed |
| Refresh air jumps on wall contact | explicit boolean; false preserves limited midair jumps |

Derive upward kick speed from height: `-sqrt(2 * rise_gravity * WALL_JUMP_HEIGHT)`.
Tune these values in the level's world units. Refreshing air jumps on each wall contact
enables longer climbing routes; not refreshing them makes the existing air-jump budget matter.
In this example a wall jump itself does **not** spend an air jump.

```python
# At each fixed tick, before moving. side is current contact; 0 means no wall.
# All timers and air_jumps_left persist between ticks; initialize them on spawn.
coyote_timer = max(0, coyote_timer - dt)
wall_timer = max(0, wall_timer - dt)
buffer_timer = max(0, buffer_timer - dt)
steer_lock = max(0, steer_lock - dt)
if jump_pressed_this_tick:
    buffer_timer = JUMP_BUFFER
if on_floor:
    coyote_timer = COYOTE_TIME
    air_jumps_left = MAX_AIR_JUMPS
    wall_timer = 0
elif side != 0 and steer_lock == 0:
    wall_side = side
    wall_timer = WALL_COYOTE
    if REFRESH_AIR_JUMPS_ON_WALL:
        air_jumps_left = MAX_AIR_JUMPS

# Run normal horizontal steering only when steer_lock == 0.
# After steering, remove only velocity INTO a current wall; retain velocity away.
if side != 0 and velocity.x * side > 0:
    velocity.x = 0

jumped = False
if buffer_timer > 0:
    if on_floor or coyote_timer > 0:           # ground/coyote wins
        velocity.y = jump_velocity
        jumped = True
    elif wall_timer > 0 and steer_lock == 0:  # then wall, using remembered side
        velocity.x = -wall_side * WALL_KICK_SPEED
        velocity.y = -sqrt(2 * rise_gravity * WALL_JUMP_HEIGHT)
        steer_lock = WALL_STEER_LOCK
        jumped = True
    elif air_jumps_left > 0:                  # finally air jump
        velocity.y = air_jump_velocity
        air_jumps_left -= 1
        jumped = True
if jumped:
    buffer_timer = 0                          # consume the press exactly once
    coyote_timer = 0
    wall_timer = 0

# Apply the existing variable-height/gravity rules once, then cap wall descent.
# Keep the cap after gravity so gravity does not immediately exceed it.
if not on_floor and side != 0 and velocity.y > 0 and input_x * side > 0:
    velocity.y = min(velocity.y, WALL_SLIDE_MAX_FALL)
# Move/collide once; refresh contacts for the next tick.
```

The lock prevents normal steering from cancelling the kick on its first frames. It also
prevents the previous contact from immediately refreshing wall grace. Collision response still
applies while locked. Landing restores the normal ground/air-jump state; clear stale grounded
flags through the normal physics update after a jump. If a game forbids repeated jumps from
the same wall until landing or reaching another wall, track wall identity separately.

Test both left and right walls: ground jump beside a wall; jump one tick after losing wall
contact; hold toward the wall through a kick; release direction while falling; double jump
before/after wall contact under both refresh policies; one press with every jump eligible.
Only one branch may fire per press. A weak kick usually means steering overwrote its X
velocity; an unexplained launch after leaving a wall often means stored into-wall velocity
was never removed. A slide while rising or away from a wall means the cap predicate is too broad.

For an example of contact-query semantics, the primary
[Godot CharacterBody2D reference](https://docs.godotengine.org/en/stable/classes/class_characterbody2d.html)
documents wall normals and contact flags from the last movement call. Verify equivalent
semantics against the actual engine/version before translating this pseudocode.
