# 2D controller recipes (Godot 4.7)

Depth companion to `godot-2d-movement`. Coyote time, jump buffering and variable jump height
live in the `platformer` skill.

## One-way platforms

Tick **One Way Collision** on the platform's `CollisionShape2D` / `CollisionPolygon2D` (or set
`one_way_collision = true`). With the default `one_way_collision_direction` of `Vector2(0, 1)`
a body lands on top and passes through from below. The direction property is new in 4.7;
earlier versions always use the shape's local down, so you had to rotate the node to get
one-way walls. Raise `one_way_collision_margin` (default 1) if fast bodies drop through.

To drop through on purpose, clear the platform's layer from the body's mask for a few physics
frames with `set_collision_mask_value(layer, false)`, then restore it.

## Moving platforms

Make the platform an `AnimatableBody2D` and move it with an `AnimationPlayer`, a `Tween` or
code. Keep `sync_to_physics` on (default) so it moves in step with physics. A
`CharacterBody2D` standing on it is carried by `move_and_slide()`:

- `platform_floor_layers` (default: all layers) picks which floors can carry the body.
- `platform_on_leave` decides what happens to the platform's velocity when the body leaves:
  `PLATFORM_ON_LEAVE_ADD_VELOCITY` (default, the body keeps the momentum),
  `ADD_UPWARD_VELOCITY` or `DO_NOTHING`.

## move_and_collide(): manual collision response

Use it when you want your own response, such as a bounce, instead of sliding:

```gdscript
func _physics_process(delta: float) -> void:
    var collision := move_and_collide(velocity * delta)   # this one takes per-frame motion
    if collision:
        velocity = velocity.bounce(collision.get_normal())
```

`KinematicCollision2D` exposes `get_normal()`, `get_collider()`, `get_position()`,
`get_remainder()` and `get_travel()`. `move_and_collide(motion, true)` only tests the move.

## Acceleration and friction

```gdscript
@export var accel := 1500.0
@export var friction := 1800.0

func _physics_process(delta: float) -> void:
    var dir := Input.get_axis("move_left", "move_right")
    var target := dir * speed
    var rate := accel if dir != 0.0 else friction
    velocity.x = move_toward(velocity.x, target, rate * delta)
    move_and_slide()
```

With low friction the bundled test's "stops within 1 s" check can fail on purpose; raise its
frame count rather than the friction if the slide is intended.

## CharacterBody2D properties worth knowing (4.7 defaults)

| Property | Default | Why it matters |
|---|---|---|
| `up_direction` | `Vector2.UP` | Defines floor, wall and ceiling. |
| `floor_max_angle` | 45° (0.785 rad) | Steeper slopes count as walls. |
| `floor_snap_length` | 1 px | Raise to stay glued when walking downhill. |
| `floor_stop_on_slope` | true | Stops idle sliding on slopes. |
| `floor_constant_speed` | false | True keeps speed equal uphill and downhill. |
| `max_slides` | 4 | Collision iterations per `move_and_slide()`. |
| `safe_margin` | 0.08 | Higher detects floors and walls more reliably, with less precision. |
| `slide_on_ceiling` | true | False stops upward motion on ceiling hits. |
