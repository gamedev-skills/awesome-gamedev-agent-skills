---
name: camera-systems
description: >
  Builds and tunes game cameras, engine-neutral with Godot and Cinemachine 3 mappings: 2D follow
  with deadzone and look-ahead, third-person orbit, first-person look and split-screen. Use when
  the camera lags, jitters while following, shows past the level edge, clips through walls or
  changes with frame rate. Not for shake (`game-feel`) or physics timestep jitter
  (`physics-tuning`).
---

# Camera systems

A good camera follows smoothly at any frame rate, leads the action, never shows outside the
level and never clips through walls. This skill owns those techniques and maps them onto each
engine's camera node or rig; prefer the engine's built-in rig before hand-rolling one.

## When to use

- A 2D camera should follow smoothly, ignore small movements, lead motion and stay in bounds.
- A 3D third-person orbit or first-person look controller, or framing several targets.
- Fixing jitter, snapping, motion sickness or a camera that peeks past the level.

**Not this skill:** shake magnitude and triggers (`game-feel`; this skill only exposes the
offset), physics jitter of the body itself (`physics-tuning`), `Camera3D` and environment setup
(`godot-3d-essentials`), player movement (`godot-2d-movement` or the engine movement skill),
look-sensitivity input curves (`input-systems`).

## Core workflow

1. **Decide what the camera serves.** Platformer (lead the jump, see hazards), top-down (centre
   with deadzone), third-person (orbit plus collision), first-person (look only).
2. **Use the built-in rig first**: Godot `Camera2D` smoothing, limits and drag margins, or
   `SpringArm3D`; Unity Cinemachine 3 (`CinemachineCamera` plus Position Composer, Orbital
   Follow, Deoccluder, Confiner). Hand-roll only what the rig cannot do.
3. **Smooth with `1 - exp(-rate * dt)`** or a critically damped spring (`SmoothDamp`), never a
   fixed `lerp(a, b, 0.1)` per frame.
4. **Add a deadzone, then look-ahead** eased toward its goal so direction flips don't whip.
5. **Clamp the view, not the centre**, to the level rectangle, accounting for zoom.
6. **For 3D, separate look from collision**: yaw and pitch on a pivot, a spring arm or ray pulls
   the camera in, pitch clamped.
7. **Update after the target moves** (late update, or after physics) and follow the target's
   interpolated transform when physics interpolation is on.
8. **Verify with a runnable check, then by eye.** Step the follow code headless with a target
   moving at 300 px/s for 2 s at `dt = 1/30` and at `dt = 1/144`, and compare how far the camera
   trails the target. With `rate = 8` exponential smoothing the lag is about 33 px and 37 px; a
   fixed `lerp(..., 0.1)` gives about 90 px and 19 px, a sign the follow is frame-rate
   dependent. Then ask the user to run into corners, walls and level edges at low and high frame
   rates and report any jitter, peeking or snapping.

## Patterns

### 1. Godot 2D built-in follow: smoothing + bounds (don't hand-roll first)

```gdscript
# Godot 4.7 Camera2D. Engine-provided smoothing + hard limits + drag margins.
@onready var cam := $Camera2D
func _ready() -> void:
    cam.make_current()
    cam.position_smoothing_enabled = true
    cam.position_smoothing_speed = 6.0           # higher = snappier; lower = floatier
    cam.limit_left = 0; cam.limit_top = 0        # clamp to the level rect (pixels)
    cam.limit_right = level_width; cam.limit_bottom = level_height
    cam.drag_horizontal_enabled = true           # built-in deadzone via drag margins
```

### 2. Frame-rate-independent smooth follow (when you hand-roll it)

```gdscript
# RIGHT: exponential smoothing — same feel at any FPS. `rate` ~ 5..12.
func _follow(dt: float) -> void:
    var t := 1.0 - exp(-rate * dt)               # converges correctly regardless of dt
    global_position = global_position.lerp(target.global_position, t)
# WRONG: global_position = global_position.lerp(target.global_position, 0.1)
#        → faster smoothing at higher FPS; different feel on every machine.
# Unity 6.3 LTS: Vector3.SmoothDamp(transform.position, target.position, ref vel, smoothTime) in
# LateUpdate gives the same spring behavior with built-in frame-rate correction.
```

### 3. Deadzone + look-ahead (lead the player, ignore jitter)

```gdscript
# Camera only chases once the target leaves the deadzone box, then aims AHEAD of motion.
func _camera_target(dt: float) -> Vector2:
    var to := target.global_position - _focus
    var dz := deadzone_half_extents                  # e.g. Vector2(48, 32)
    # Only move the focus by the overflow beyond the deadzone (per axis).
    _focus.x += clampf(absf(to.x) - dz.x, 0, INF) * signf(to.x)
    _focus.y += clampf(absf(to.y) - dz.y, 0, INF) * signf(to.y)
    var lead := target.velocity.normalized() * look_ahead_dist    # aim ahead of travel
    return _focus + lead
```

### 4. 3D third-person orbit with collision push-in

```gdscript
# Godot 4.7. Yaw/pitch a pivot; a SpringArm3D auto-pulls the camera in when blocked.
func _unhandled_input(e):
    if e is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
        # screen_relative is unscaled; `relative` is scaled by the stretch settings, so
        # sensitivity would change with window size. The docs recommend screen_relative
        # for captured-mouse aiming.
        _yaw -= e.screen_relative.x * sensitivity
        _pitch = clampf(_pitch - e.screen_relative.y * sensitivity,
                        deg_to_rad(-80.0), deg_to_rad(45.0))       # clamp pitch!
func _process(_dt):
    pivot.rotation = Vector3(_pitch, _yaw, 0)
    # $SpringArm3D handles wall collision: set spring_length + collision_mask; the child
    # Camera3D slides in automatically. RIGHT: spring arm. WRONG: camera clips through walls.
# Unity 6.3 LTS: a Cinemachine 3 CinemachineCamera (namespace Unity.Cinemachine) with an Orbital
# Follow + Cinemachine Deoccluder; the CinemachineBrain on the Camera blends automatically.
```

### 5. Screen shake hook (owned trigger lives in `game-feel`)

```gdscript
# Expose an additive offset the game-feel trauma model writes to; follow + shake compose.
var shake_offset := Vector2.ZERO                 # set each frame by game-feel (trauma^2 * noise)
func _apply(final_focus: Vector2) -> void:
    global_position = final_focus + shake_offset  # shake rides ON TOP of smooth follow
# Unity Cinemachine 3: CinemachineBasicMultiChannelPerlin (AmplitudeGain/FrequencyGain) for
# continuous noise driven by trauma; for one-off impacts, a CinemachineImpulseSource on the
# hitter plus a CinemachineImpulseListener on the camera.
```

## Gotchas

- **`lerp(pos, target, const)` per frame** is frame-rate dependent: floatier at 30 FPS,
  snappier at 144. Use `1 - exp(-rate * dt)` or `SmoothDamp`.
- **Jitter while following a physics body**: the body moves at the physics tick (60 Hz) and the
  camera at the display rate. Turn on physics interpolation (Godot
  `physics/common/physics_interpolation`) and follow the body's interpolated transform in
  `_process` (`get_global_transform_interpolated()` in 3D), or follow in the physics step with
  `Camera2D.process_callback = CAMERA2D_PROCESS_PHYSICS`. Mixing the two is what jitters.
- **One-frame lag** when following in the normal update before the target has moved. Follow in
  `LateUpdate` (Unity) or after movement and physics resolve.
- **Camera parented to the moving player** inherits every bump and fights interpolation. Keep
  the camera on its own branch (or `top_level = true`) and follow in code or with a rig.
- **Clamping the centre instead of the view** shows black past the edge. Clamp to
  `[min + half_view, max - half_view]`, and centre on any axis where the level is smaller than
  the view.
- **No deadzone in twitchy games** makes the camera twitch with every micro-movement; a box
  deadzone and a circular one feel different, so pick deliberately.
- **Unclamped pitch** flips the camera over the top. About -80° to +45° for an orbit, ±80° for
  first-person.
- **Mouse-look sensitivity changes with window size** in Godot: `InputEventMouseMotion.relative`
  is scaled by the stretch settings; read `screen_relative` for captured-mouse aiming.
- **Clipping through walls** in 3D: use a spring arm or occlusion ray, with a probe radius a
  little larger than the camera's near-plane half-size.
- **Slingshot after teleport or respawn**: a smoothed camera whips across the level. Hard-cut and
  reset the smoothing state (Godot `Camera2D.reset_smoothing()`), or fast-ease deliberately.
- **Shake written into the follow target** makes follow fight shake. Smooth follow first, add the
  shake offset last.

## References

- `references/follow-and-framing.md`: read for the smoothing derivation, a full deadzone plus
  look-ahead plus bounds 2D rig, orbit and first-person details, group framing and
  split-screen, cutscene blends, and the Godot/Cinemachine 3 component mapping table.

## Related skills

- `game-feel`: shake trauma and triggers; writes this skill's offset.
- `godot-2d-movement`, `godot-3d-essentials`: the player and world the camera frames.
- `physics-tuning`: timestep and interpolation for the bodies being followed.
- `input-systems`: look sensitivity, invert and stick response curves.

## Version notes

Last verified: 2026-11-11.

- Godot 4.7: `Camera2D.position_smoothing_*`, `limit_*`, `drag_*`, `process_callback`,
  `reset_smoothing()`; `InputEventMouseMotion.screen_relative`; physics interpolation and manual
  camera interpolation per
  https://docs.godotengine.org/en/4.7/tutorials/physics/interpolation/advanced_physics_interpolation.html.
- Unity 6.3 LTS with Cinemachine 3.1 (3.1.7 is the latest release, 9 June 2026; namespace
  `Unity.Cinemachine`). The 2.x names `CinemachineVirtualCamera`, `CinemachineCollider` and
  `CinemachineFramingTransposer` are deprecated in 3.x
  (https://packages.unity.com/com.unity.cinemachine).
- PhantomCamera (Godot addon) latest release v0.11.0.4, October 2026
  (https://github.com/ramokz/phantom-camera/releases).
