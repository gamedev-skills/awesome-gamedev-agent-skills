---
name: godot-physics
description: >
  Godot 4.7 physics API in 2D and 3D: body and Area types, collision_layer and mask bits, Area
  signals for hurtboxes, RayCast and space queries, and Jolt (3D default since 4.6). Use when
  objects pass through each other, body_entered never fires or a raycast hits itself. Not for
  engine-neutral jitter and tunnelling (`physics-tuning`) or CharacterBody movement
  (`godot-2d-movement`).
---

# Godot Physics (4.x, 2D + 3D)

Pick the body type, wire collision layers and masks, detect overlaps, cast rays, and know
where Jolt differs. Swap the `2D`/`3D` suffix as needed. Targets **Godot 4.7** (see Version
notes). 2D always uses Godot's own 2D engine.

## When to use

- Choosing a body type, setting layers/masks so the right things collide, overlap
  detection (triggers, hurtboxes) with `Area`, forces/impulses on a `RigidBody`, or rays
  for line-of-sight and ground checks.

**When *not* to use:** `move_and_slide` controllers → `godot-2d-movement`; tile collision
setup → `godot-tilemap`; engine-neutral feel (timestep, mass, jitter, CCD strategy) →
`physics-tuning`.

## Core workflow

1. **For 3D, read which engine runs** before debugging behavior. In `project.godot`,
   `[physics]` `3d/physics_engine="Jolt Physics"` means Jolt; no line (`DEFAULT`) means
   GodotPhysics3D. New 4.6+ projects write the Jolt line. The API is the same, but joints,
   ray face indices, kinematic contacts and margins differ (see Gotchas).
2. **Choose the body type:** `StaticBody` never moves; `AnimatableBody` is moved by code or
   animation and pushes others (platforms, doors); `RigidBody` is simulated (move it with
   forces, impulses or `linear_velocity`, never `position`); `CharacterBody` is
   script-driven; `Area` only detects and can override gravity/damping. Every body needs a
   non-empty `CollisionShape`/`CollisionPolygon` child.
3. **Configure layers and masks.** Layers are what a body *is*; masks are what it *scans*.
   A detects B only if B's layer bit is in A's mask. Name the bits in `project.godot` so
   the `.tscn` values are readable:

   ```ini
   [layer_names]
   2d_physics/layer_1="player"
   2d_physics/layer_2="walls"
   2d_physics/layer_3="enemies"
   ```

   In a `.tscn`, `collision_layer = 1` and `collision_mask = 6` (bits 2 and 3) are plain
   integers; bit *n* is `1 << (n - 1)`. In code, `set_collision_mask_value(3, true)` uses
   the same 1-based numbers as the editor checkboxes.
4. **Detect overlaps** with `Area` signals (`body_entered`, `area_entered`); `monitoring`
   on the detecting Area, `monitorable` on the detected one.
5. **Cast rays** with a `RayCast2D/3D` node (polled each physics frame) or a one-shot
   `direct_space_state` query (Pattern 2).
6. **Check before you finish.** Physics runs normally under `--headless`, so prove the
   behavior with a test runner instead of describing it (Pattern 3). Run
   `godot --headless --path . --script res://tests/test_physics.gd` and read the exit code
   and any `SCRIPT ERROR`/`ERROR:` lines. With no Godot binary (`godot`, `godot4` or
   `$GODOT_BIN`), ask the user to run it and paste the output. For a visual check, ask the
   user to run `godot --path . --debug-collisions` and report what overlaps. If you edited
   `.tscn` files by hand, also run the `godot-nodes-scenes` skill's
   `scripts/check_godot_project.py <project-dir>`.

## Patterns

### 1. RigidBody: impulse, force, and a safe teleport

```gdscript
extends RigidBody3D

var _teleport_to: Variant = null

func push(direction: Vector3) -> void:
    apply_central_impulse(direction * 8.0)      # one-off velocity change

func teleport(to: Transform3D) -> void:
    _teleport_to = to                           # applied inside the solver step

func _integrate_forces(state: PhysicsDirectBodyState3D) -> void:
    if _teleport_to != null:
        state.transform = _teleport_to
        state.linear_velocity = Vector3.ZERO
        state.angular_velocity = Vector3.ZERO
        _teleport_to = null
```

### 2. One-shot ray that skips the caster

```gdscript
func ground_under(from: Vector2) -> Dictionary:
    var space := get_world_2d().direct_space_state
    var query := PhysicsRayQueryParameters2D.create(from, from + Vector2(0, 64))
    query.collision_mask = 0b10                  # layer 2 only ("walls")
    query.exclude = [get_rid()]                  # Array[RID], not nodes
    return space.intersect_ray(query)            # {} on miss, else collider/position/normal
```

Call it from `_physics_process`; space-state data is only valid during the physics step.

### 3. Headless test that an Area sees a body

```gdscript
# res://tests/test_physics.gd
extends SceneTree

func _initialize() -> void:
    var level: Node = load("res://levels/test_arena.tscn").instantiate()
    root.add_child(level)
    for _i in 3:
        await physics_frame                      # overlap lists update once per step
    var hurtbox: Area2D = level.get_node("Hurtbox")
    var player: Node2D = level.get_node("Player")
    var ok := hurtbox.overlaps_body(player)
    print("hurtbox sees player: ", ok)
    quit(0 if ok else 1)
```

Place the two nodes so they overlap in the test scene. The same shape works for "the crate
lands on the floor" (compare `global_position.y` after N frames) or "the ray hits the
wall". Add counters as in `godot-gdscript-headless-testing` once there is more than one
assertion.

## Gotchas

- **Layer vs mask confusion** is the most common bug. Detection can be one-directional:
  A sees B if B's layer is in A's mask, whatever B's mask says.
- **Moving a RigidBody by `position`** fights the solver and causes tunnelling or jitter.
  Use impulses, forces, `linear_velocity`, `freeze`, or set `state.transform` in
  `_integrate_forces` (Pattern 1).
- **A RigidBody's own `body_entered` never fires** unless `contact_monitor = true` and
  `max_contacts_reported > 0`.
- **`Area` doesn't fire** when `monitoring` is off on it, `monitorable` is off on the other
  Area, or the bits don't overlap. Toggling `monitoring` from inside an enter/exit signal
  handler is blocked ("Function blocked during in/out signal"); use
  `set_deferred("monitoring", false)`.
- **`get_overlapping_bodies()` is empty right after spawning** → the list updates once per
  physics step. Await a `physics_frame` or use the signals.
- **RayCast2D/3D read stale or no data** if `enabled` is false or you read before physics
  ran. Read in `_physics_process`; call `force_raycast_update()` after moving it in the
  same tick.
- **Fast objects tunnel** through thin walls → enable `continuous_cd` on the RigidBody or
  sweep with a ray/shape cast. Tuning strategy belongs to `physics-tuning`.
- **"Can't change this state while flushing queries"** → you added/removed bodies or
  shapes inside a physics callback. Use `call_deferred` / `set_deferred`.

### Jolt Physics (3D) differences

- **`face_index` is always `-1`** in `intersect_ray()` / `RayCast3D` results. Set
  `physics/jolt_physics_3d/queries/enable_ray_cast_face_index=true` in `project.godot` if
  you need it (roughly 25% more memory for `ConcavePolygonShape3D`).
- **A joint with only one body gets inverted limits after switching engines.** Jolt treats
  the lone body as `node_b` with `node_a` as the world; GodotPhysics3D treats it as
  `node_a`. Move the body to the slot Jolt expects, or set
  `physics/jolt_physics_3d/joints/world_node` for compatibility with an older project.
- **Joint soft-limit properties do nothing** under Jolt: `bias`/`damping`/`impulse_clamp` on
  `PinJoint3D`; `bias`/`softness`/`relaxation` on `HingeJoint3D` and `ConeTwistJoint3D`;
  `angular_*` and limit softness/restitution/damping on `SliderJoint3D`; limit
  softness/restitution/damping/erp on `Generic6DOFJoint3D`. Godot warns when they are set
  to non-default values.
- **A frozen kinematic `RigidBody3D` reports no contacts** with static or kinematic bodies,
  even with `max_contacts_reported > 0`. Enable
  `physics/jolt_physics_3d/simulation/generate_all_kinematic_contacts` if gameplay needs them.
- **Shape `margin` shrinks the shape instead of padding it**, so sizes stay true but shape
  queries can return odd normals on small shapes; the effective margin comes from
  `physics/jolt_physics_3d/collisions/collision_margin_fraction`.
- **`Area3D` fires `body_entered` for `SoftBody3D`** under Jolt. Filter soft bodies with
  layers/masks if the old behavior is expected.
- **A `WorldBoundaryShape3D` floor sits at the wrong height after upgrading to 4.7** →
  under Jolt, 4.7 reads `plane.d` with Godot's sign convention, the opposite of 4.6; flip
  the sign of `d` in projects tuned on 4.6. Jolt also caps the plane's effective size
  (`physics/jolt_physics_3d/limits/world_boundary_shape_size`), so bodies far from the
  origin can fall off an "infinite" floor.

## References

- Read `references/bodies-and-queries.md` when you need the body-type table, the full
  RigidBody control API, shape queries (`intersect_shape`, `cast_motion`), RayCast node
  options, joints, one-way collision, or Area gravity/damping overrides.
- Read the Godot docs page [Using Jolt Physics](https://docs.godotengine.org/en/stable/tutorials/physics/using_jolt_physics.html)
  when a Jolt difference is not in the list above.

## Related skills

- `godot-2d-movement` for `CharacterBody2D` controllers.
- `godot-tilemap` for tile collision shapes and their layers.
- `physics-tuning` for engine-neutral feel: timestep, mass, drag, CCD, jitter.
- `godot-3d-essentials` for the 3D scene these bodies live in.
- `godot-gdscript-headless-testing` to keep Pattern 3 tests in CI.

## Version notes

Last verified: 2026-11-11 against Godot 4.7.2-stable (released 2026-08-18).

- Jolt Physics is the default 3D engine for projects created in 4.6 or later; older
  projects keep GodotPhysics3D until someone switches them.
- 4.7 flipped how Jolt reads `WorldBoundaryShape3D` `plane.d` and added
  `one_way_collision_direction` on 2D collision shapes.
- The `physics/jolt_physics_3d/*` settings named above exist in 4.7.2.

Sources: [Godot 4.6 release](https://godotengine.org/releases/4.6),
[Upgrading from 4.6 to 4.7](https://docs.godotengine.org/en/stable/tutorials/migrating/upgrading_to_godot_4.7.html),
[ProjectSettings @ 4.7.2-stable](https://github.com/godotengine/godot/blob/4.7.2-stable/doc/classes/ProjectSettings.xml),
[Area2D @ 4.7.2-stable](https://github.com/godotengine/godot/blob/4.7.2-stable/doc/classes/Area2D.xml).
