---
name: godot-2d-movement
description: >
  Implement 2D kinematic character movement in Godot 4.7 with CharacterBody2D and
  move_and_slide(): platformer run/jump with gravity, top-down 8-direction motion,
  slope handling, and reading collisions. Use when coding a 2D player or enemy
  controller, a platformer or top-down character, or fixing move_and_slide()/
  is_on_floor() behavior in a .tscn with a CharacterBody2D.
---

# Godot 2D Movement (4.x)

Build responsive 2D character controllers with `CharacterBody2D` and the argument-less
`move_and_slide()`. Targets **Godot 4.7**.

## When to use

- Use when scripting a 2D player/enemy that moves and collides: platformer (gravity +
  jump) or top-down (free 8-direction), slope walking, or wall/floor detection.
- Use when `move_and_slide()` "does nothing", the character sinks through floors, or
  `is_on_floor()` is always false.

**When *not* to use:** dynamic rigid bodies, areas, raycasts, collision layers →
`godot-physics`; tile-based levels → `godot-tilemap`; full platformer game template →
the `platformer` genre skill; engine-agnostic feel tuning → `physics-tuning`.

## Core workflow

1. **Use `CharacterBody2D`** with a `CollisionShape2D` child. It is script-driven: it
   does not fall or react to forces on its own.
2. **Set the `velocity` property, then call `move_and_slide()`** (no arguments in 4.x).
   The method reads `velocity`, moves the body, slides along surfaces, and updates
   `velocity` to reflect what actually happened.
3. **Do it in `_physics_process(delta)`** — `move_and_slide()` uses the physics step's
   delta internally, so do not multiply `velocity` by `delta` yourself.
4. **Platformer:** add gravity to `velocity.y` each tick, jump by setting `velocity.y`
   negative when `is_on_floor()`; for air jumps, refill a separate counter on landing and
   spend it only when the ground jump is unavailable (Pattern 5).
5. **Top-down:** build a direction from input and scale by speed; set
   `motion_mode = MOTION_MODE_FLOATING` so there is no "floor/wall" distinction.
6. **Read results** with `is_on_floor()`, `is_on_wall()`, `get_wall_normal()`, and
   `get_slide_collision(i)` after the call.

## Patterns

### 1. Platformer controller (gravity, jump, slopes)

```gdscript
extends CharacterBody2D

@export var speed := 200.0
@export var jump_velocity := -400.0
@export var gravity := 1200.0          # pixels/sec^2 (tune to taste)

func _physics_process(delta: float) -> void:
    # Apply gravity while airborne.
    if not is_on_floor():
        velocity.y += gravity * delta

    # Jump only when grounded (Input action set in Project Settings > Input Map).
    if Input.is_action_just_pressed("jump") and is_on_floor():
        velocity.y = jump_velocity

    # Horizontal input: -1, 0, or 1.
    var dir := Input.get_axis("move_left", "move_right")
    if dir != 0.0:
        velocity.x = dir * speed
    else:
        velocity.x = move_toward(velocity.x, 0.0, speed)   # decelerate to a stop

    move_and_slide()   # 4.x: no arguments; uses and updates `velocity`
```

A fixed `gravity` export keeps tuning simple. To follow the project setting
(*Physics > 2D > Default Gravity*) and any `Area2D` gravity overrides instead, use
`velocity += get_gravity() * delta`, as the built-in CharacterBody2D script template does.

### 2. Top-down 8-direction movement

```gdscript
extends CharacterBody2D

@export var speed := 220.0

func _ready() -> void:
    motion_mode = CharacterBody2D.MOTION_MODE_FLOATING  # no floor/ceiling concept

func _physics_process(_delta: float) -> void:
    # get_vector returns a normalized-ish Vector2 from four input actions.
    var input := Input.get_vector("move_left", "move_right", "move_up", "move_down")
    velocity = input * speed
    move_and_slide()
```

### 3. Reading slide collisions after moving

```gdscript
func _physics_process(delta: float) -> void:
    # ... set velocity ...
    move_and_slide()
    for i in get_slide_collision_count():
        var c := get_slide_collision(i)
        var other := c.get_collider()
        if other and other.is_in_group("enemies"):
            take_damage(1)        # touched an enemy while moving
```

### 4. Coyote time (forgiving jump just after leaving a ledge)

```gdscript
@export var coyote_time := 0.1
var _coyote := 0.0

func _physics_process(delta: float) -> void:
    if not is_on_floor():
        velocity.y += gravity * delta
        _coyote -= delta
    else:
        _coyote = coyote_time

    if Input.is_action_just_pressed("jump") and _coyote > 0.0:
        velocity.y = jump_velocity
        _coyote = 0.0
    # ... horizontal input + move_and_slide() ...
```

### 5. Double jump (air jumps)

Keep **air jumps** in a separate counter from the ground jump. Refill the counter on the
floor and spend one only when the player is airborne and coyote time has expired. A separate
counter means walking off a ledge still leaves exactly the air jumps you configured — the
ground jump is handled by `is_on_floor()` and coyote time.

```gdscript
extends CharacterBody2D

@export var speed := 220.0
@export var jump_velocity := -420.0
@export var air_jump_velocity := -380.0
@export var max_air_jumps := 1          # 1 = double jump, 2 = triple jump
@export var coyote_time := 0.1
@export var jump_buffer_time := 0.12
@export var jump_cut := 0.45

var _air_jumps_left := 0
var _coyote := 0.0
var _buffer := 0.0

func _physics_process(delta: float) -> void:
    var on_floor := is_on_floor()

    if on_floor:
        _air_jumps_left = max_air_jumps
        _coyote = coyote_time
    else:
        _coyote = maxf(_coyote - delta, 0.0)

    if Input.is_action_just_pressed("jump"):
        _buffer = jump_buffer_time
    else:
        _buffer = maxf(_buffer - delta, 0.0)

    if _buffer > 0.0:
        if on_floor or _coyote > 0.0:
            _jump(false)                # ground/coyote jump: free
        elif _air_jumps_left > 0:
            _air_jumps_left -= 1
            _jump(true)                 # air jump: spend one

    if Input.is_action_just_released("jump") and velocity.y < 0.0:
        velocity.y *= jump_cut

    if not on_floor:
        velocity += get_gravity() * delta

    var dir := Input.get_axis("move_left", "move_right")
    velocity.x = move_toward(velocity.x, dir * speed, 1500.0 * delta)
    move_and_slide()

func _jump(is_air_jump: bool) -> void:
    velocity.y = air_jump_velocity if is_air_jump else jump_velocity
    _buffer = 0.0                       # consume the press exactly once
    _coyote = 0.0                       # no second jump from the same coyote window
```

Emit a signal with the `is_air_jump` flag if the second jump needs a different animation or
sound. The full runnable version (with feedback and a headless test) is in the starter
project below.

## Pitfalls

- **3.x signature is gone.** `move_and_slide(velocity)` (returning the new velocity) was
  removed. In 4.x set the `velocity` property and call `move_and_slide()` with no args.
  `move_and_slide(velocity, Vector2.UP)` will not parse.
- **Multiplying velocity by delta.** `move_and_slide()` already accounts for the physics
  delta. Setting `velocity = dir * speed * delta` makes the body crawl.
- **Movement in `_process`** instead of `_physics_process` causes frame-rate-dependent,
  jittery motion. Always move in `_physics_process`.
- **`is_on_floor()` always false** when `up_direction` is wrong (default `Vector2.UP`),
  there is no `CollisionShape2D`, or you never called `move_and_slide()` this frame.
- **Sinking through floors** usually means the collision shape is missing/zero-sized, the
  floor body is on a layer this body's mask doesn't include, or you moved the body via
  `position +=` instead of velocity + `move_and_slide()`.
- **Slope slipping while idle:** keep `floor_stop_on_slope = true` (default) and raise
  `floor_snap_length` (default 1 px) so the body sticks to downward slopes.
- **Air jump fires on the ground or twice from one press** → resolve ground/coyote jumps
  before air jumps, and clear the jump buffer when a jump fires. Otherwise one press can
  spend both the ground jump and an air jump.
- **Walking off a ledge gives a free extra jump** → if the ground jump and air jumps share one
  `_jumps_left` pool and you reset the pool on the floor, falling off leaves the full count.
  Keep air jumps separate (Pattern 5), or decrement the pool when leaving the floor without
  jumping.
- **Coyote time eats the air jump** → check `on_floor or _coyote > 0.0` first and clear the
  coyote timer inside the jump action. If the air branch runs first, a jump just after leaving
  a ledge spends the air jump and the player loses the coyote jump.
- **The second jump feels invisible** → emit a signal with `is_air_jump` and play a distinct
  SFX/animation. Players cannot tell whether the mid-air press registered otherwise.

## Starter project

A runnable Godot 4.6+ project with the double-jump controller, a small test level, and a
headless test lives in [`assets/double-jump-demo/`](assets/double-jump-demo/). Open the folder
in Godot and press F5, or run the test from inside it:

```bash
godot --headless --path . --script res://tests/test_player.gd
```

## References

- For one-way platforms, moving platforms, jump buffering, variable jump height, double
  jumps, and `move_and_collide()` (manual collision response), read `references/controller-recipes.md`.

## Related skills

- `godot-physics` — collision layers/masks, areas, raycasts, rigid bodies.
- `godot-tilemap` — building the levels this character walks on.
- `godot-animation` — driving sprite/skeletal animation from movement state.
- `camera-systems` — follow camera, deadzone, and look-ahead that track this character.
- `platformer` / `input-systems` — full genre template and rebindable input.
