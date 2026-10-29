# Platformer feel tuning (depth)

Deeper detail behind the controller in `SKILL.md`. All snippets are engine-neutral
pseudocode; the math is standard kinematics and ports to any engine. Tune by *outcome*
(tiles of height, seconds to apex), then read off the physics values.

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

## 2. Full feel knob reference

| Knob | What it changes | Typical range | Notes |
|------|-----------------|---------------|-------|
| Jump height | vertical reach | 2–5 tiles | Keep below the player's *commit* comfort. |
| Time to apex | weight/snappiness | 0.25–0.45 s | Lower = snappier, "tighter". |
| Fall multiplier | floatiness on descent | 1.3–2.2× | The single biggest "feel" lever. |
| Coyote time | post-ledge grace | 0.05–0.15 s | ~3–9 frames at 60 Hz. |
| Jump buffer | pre-land grace | 0.08–0.18 s | Forgive early presses. |
| Variable-jump cut | tap vs hold height | ×0.3–0.6 of vy | Cut only while rising. |
| Apex hang | air control at top | ×0.4–0.6 g near apex | Define apex as `|vy| < hang_threshold`. |
| Max fall speed | terminal velocity | clamp | Prevents tunneling and runaway speed. |
| Ground accel | time to top speed | 0.03–0.12 s | Instant = arcadey; longer = momentum. |
| Air control | steering mid-jump | 0.5–1.0× ground | <1 gives committed arcs. |
| Air jumps | extra jumps before landing | 0–2 | 1 = double jump; refill on landing. |
| Air jump height | reach of the second jump | 0.7–1.0× ground | Tune separately from the ground jump. |
| Coyote-after-jump lockout | one press firing twice | consume timers | Zero both timers on jump. |

## 2b. Double jump / air jumps

- Keep air jumps in a **separate counter** from the ground jump. Reset it on landing; spend
  one only when the ground/coyote jump is unavailable. This avoids the "walk off a ledge and
  get two air jumps" bug and the "coyote jump spends the air jump" bug.
- Resolve jump priority explicitly: **ground/coyote → wall (if any) → air**. Consume the jump
  buffer once.
- Tune the second jump by height, not by copying the first jump's velocity. A second jump at
  0.7–1.0× the ground jump's height is a common range; at 1.0× the total reach is roughly
  double, which may trivialize gaps.
- Decide whether wall contact refreshes air jumps. If it does, wall-jump chains become much
  stronger and levels must be designed around that.
- Teach the double jump with a ledge that is clearly above the single-jump reach (about
  1.2–1.5× the single-jump height) and a safe landing. Do not combine it with a new hazard.

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

## 7. Camera follow

- **Deadzone:** a rectangle the player can move within before the camera reacts; stops jitter.
- **Look-ahead:** offset the camera target in the direction of motion / facing so the player
  sees what's coming. Lerp the offset; don't snap it.
- **Smoothing:** move the camera toward its target with an exponential `lerp(cam, target,
  1 - exp(-k*dt))` rather than a fixed fraction, so it is frame-rate independent.
- **Clamp:** keep the camera rect inside the level bounds so you never show out-of-level space.
- **Vertical care:** lock or slow vertical follow during normal jumps; only follow Y on large
  height changes (falling into a pit, climbing) to avoid bobbing on every hop.

## 8. Teaching and pacing (hand-off to `level-design`)

- Introduce one mechanic in isolation, let the player practice it safely, *then* combine it
  with a known one. Never introduce two new things in the same hazard.
- Place the first instance of any lethal hazard where failure is cheap (near a checkpoint,
  no long re-traversal).
- Keep checkpoint-to-checkpoint segments short early, longer later; respawn must be instant.
