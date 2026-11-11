---
name: godot-2d-movement
description: >
  Godot 4.7 CharacterBody2D movement in GDScript: platformer run and jump, top-down 8-direction
  motion, slopes and one-way platforms, with a headless landing test. Use when a 2D controller
  will not move, falls through the floor or is_on_floor() is always false. Not for coyote time and
  jump feel (`platformer`), RigidBody2D, raycasts or 3D (`godot-physics`) or tile levels
  (`godot-tilemap`).
---

# Godot 2D Movement (4.x)

Write `CharacterBody2D` controllers that land, run, jump and slide the way the engine expects,
then prove it with a headless test. Targets **Godot 4.7**; check `config/features` in
`project.godot` and keep an older project on its own version.

## Workflow

1. **Read the scene first.** Open the player `.tscn`: the root should be a `CharacterBody2D`
   with a `CollisionShape2D`/`CollisionPolygon2D` child, and the action names the script uses
   must exist under `[input]` in `project.godot`.
2. **Pick the motion mode.** Platformers keep the default `MOTION_MODE_GROUNDED`; top-down
   games set `MOTION_MODE_FLOATING`, which has no floor, wall or ceiling.
3. **Set `velocity`, then call `move_and_slide()` once per `_physics_process()`.** It takes no
   arguments, applies the physics delta itself, and writes back the velocity after collisions.
4. **Read results after the call:** `is_on_floor()`, `is_on_wall()`, `get_wall_normal()`,
   `get_slide_collision(i)`. They describe the last `move_and_slide()`, not the current frame.
5. **Hand off feel.** Coyote time, jump buffering, variable jump height and apex tuning belong
   to `platformer`; this skill supplies the Godot hooks they read (`is_on_floor()`, `velocity`).
6. **Verify before you finish** (paths are relative to this skill's folder):
   - If `godot-nodes-scenes` is installed, run `python3 ../godot-nodes-scenes/scripts/check_godot_project.py <project>`
     after adding or moving scenes and scripts; fix every `ERROR`.
   - Copy `assets/test_character_controller.gd` to `res://tests/`, set the action names at
     the top to the project's, and run
     `godot --headless --path <project> --script res://tests/test_character_controller.gd -- res://player.tscn`.
     Exit 0 means the body landed, jumped and ran (or, floating, moved on both axes without
     drifting); each `FAIL` line names the behaviour that broke. On a fresh checkout run
     `godot --headless --path <project> --import` first. To keep it in CI, use
     `godot-gdscript-headless-testing`.
   - If the user wants feel signed off, ask them to play and report jump height and how fast
     the character stops; the test only proves the mechanics.

## Patterns

### 1. Platformer controller

```gdscript
extends CharacterBody2D

@export var speed := 200.0
@export var jump_velocity := -400.0

func _physics_process(delta: float) -> void:
    if not is_on_floor():
        velocity += get_gravity() * delta   # project gravity plus any Area2D override

    if Input.is_action_just_pressed("jump") and is_on_floor():
        velocity.y = jump_velocity

    var dir := Input.get_axis("move_left", "move_right")
    if dir != 0.0:
        velocity.x = dir * speed
    else:
        velocity.x = move_toward(velocity.x, 0.0, speed)   # stops within one tick

    move_and_slide()
```

For a tunable fall speed that ignores the project setting, replace `get_gravity()` with an
exported `Vector2(0, gravity)`. For weight, ramp with `move_toward(velocity.x, dir * speed,
accel * delta)`; the reference has the full version.

### 2. Top-down 8-direction movement

```gdscript
extends CharacterBody2D

@export var speed := 220.0

func _ready() -> void:
    motion_mode = CharacterBody2D.MOTION_MODE_FLOATING

func _physics_process(_delta: float) -> void:
    # get_vector applies the action deadzones and caps the length at 1.
    velocity = Input.get_vector("move_left", "move_right", "move_up", "move_down") * speed
    move_and_slide()
```

### 3. React to what the body touched

```gdscript
func _physics_process(delta: float) -> void:
    # ... set velocity ...
    move_and_slide()
    for i in get_slide_collision_count():
        var other := get_slide_collision(i).get_collider()
        if other and other.is_in_group("enemies"):
            take_damage(1)
```

## Gotchas

- **The character crawls** → `velocity` was multiplied by `delta`. `move_and_slide()` already
  scales by the physics step; only `move_and_collide()` takes a per-frame motion.
- **`is_on_floor()` is always false** → the body is in `MOTION_MODE_FLOATING`, `up_direction`
  is not `Vector2.UP`, there is no collision shape, the floor's layer is not in this body's
  mask, or `move_and_slide()` has not run yet this tick (it reports the last call).
- **It falls through the floor or teleports** → code moves it with `position +=` or
  `global_position =`, which skips collision. Move through `velocity` only; teleport only for
  respawns.
- **Motion jitters or depends on frame rate** → movement runs in `_process()`. Use
  `_physics_process()`; for smooth visuals at high refresh rates turn on
  `physics/common/physics_interpolation` rather than moving the body in `_process()`.
- **Sliding down slopes while idle** → keep `floor_stop_on_slope` on (default) and raise
  `floor_snap_length` (default 1 px) so the body sticks when walking downhill. Slopes steeper
  than `floor_max_angle` (default 45°) count as walls.
- **3.x code will not parse** → `move_and_slide(velocity, Vector2.UP)` is gone; set
  `velocity` and `up_direction` as properties and call `move_and_slide()` with no arguments.
- **`The InputMap action "jump" doesn't exist` in the log, and the character ignores input** →
  the action is missing from `project.godot`. The bundled test adds blank actions it cannot
  find and prints a `note:` line, so it can pass while the game fails; read the notes and fix
  the Input Map.

## References

- Read `references/controller-recipes.md` for one-way platforms (including the 4.7
  `one_way_collision_direction`), moving platforms, `move_and_collide()` bounces, acceleration
  ramps and the main `CharacterBody2D` properties.
- `assets/test_character_controller.gd` is the headless behaviour test used in step 6.

## Related skills

- `platformer`: coyote time, jump buffering, variable jump and jump feel on top of Pattern 1.
- `godot-physics`: collision layers and masks, areas, raycasts, rigid bodies, 3D characters.
- `physics-tuning`: engine-neutral tunnelling and jitter diagnosis.
- `godot-animation`: driving sprites and state machines from `velocity` and floor state.
- `camera-systems`: a follow camera for this character.
- `godot-gdscript-headless-testing`: running the controller test in CI.

## Version notes

Last verified: 2026-11-11 against the Godot 4.7.2 class reference and a 4.7.2 headless run.

- Godot 4.7.2 (August 2026) is the current stable release; 4.8 is in beta.
- `CollisionShape2D`/`CollisionPolygon2D.one_way_collision_direction` is new in 4.7 (default
  `Vector2(0, 1)`); earlier versions always block from the shape's local up side.
- `get_gravity()` on physics bodies exists since 4.3.
- Sources: [Godot releases](https://github.com/godotengine/godot/releases),
  [CharacterBody2D](https://docs.godotengine.org/en/stable/classes/class_characterbody2d.html),
  [Using CharacterBody2D](https://docs.godotengine.org/en/stable/tutorials/physics/using_character_body_2d.html).
