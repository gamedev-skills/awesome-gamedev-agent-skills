# FSM, perception and steering patterns

Contents:
1. State machine with queued transitions and shared exits
2. Sight and hearing sensor
3. Priority-truncated steering

Snippets are Godot 4.7 GDScript; the structure ports directly to C# or any engine.

## 1. State machine with queued transitions and shared exits

The machine owns `change_state()`, so the first state's `enter()` runs like every other. A
transition requested during `enter()`/`exit()`/`update()` is queued and applied once, after the
current call returns. Shared exits (death, stun) live in one place instead of in every state.

```gdscript
# state_machine.gd
class_name StateMachine extends RefCounted

var agent
var current: AIState
var _queued: AIState
var _time_in_state := 0.0

func _init(owner_agent, first: AIState) -> void:
    agent = owner_agent
    request(first)
    _apply_queued()

func request(next: AIState) -> void:
    _queued = next                      # last request in one tick wins

func tick(dt: float) -> void:
    _time_in_state += dt
    var shared := _shared_exit()        # checked before the state, so no state can forget it
    if shared != null and (current == null or shared.get_script() != current.get_script()):
        request(shared)
    elif current != null:
        current.update(self, dt)
    _apply_queued()

func time_in_state() -> float:
    return _time_in_state

func _shared_exit() -> AIState:
    if agent.health <= 0:
        return DeadState.new()
    return null

func _apply_queued() -> void:
    while _queued != null:              # enter() may queue again; apply in order, never recurse
        var next := _queued
        _queued = null
        if current != null:
            current.exit(self)
        current = next
        _time_in_state = 0.0
        current.enter(self)
```

```gdscript
# ai_state.gd: base class. States call machine.request(), never assign machine.current.
class_name AIState extends RefCounted
func enter(_machine: StateMachine) -> void: pass
func update(_machine: StateMachine, _dt: float) -> void: pass
func exit(_machine: StateMachine) -> void: pass
```

```gdscript
# chase_state.gd: hysteresis on distance plus a minimum time in state.
class_name ChaseState extends AIState
const GIVE_UP_DISTANCE := 14.0          # chase starts at 10 (see PatrolState); leave at 14
const MIN_TIME := 0.4

func update(machine: StateMachine, _dt: float) -> void:
    var bb: Dictionary = machine.agent.blackboard
    if machine.time_in_state() < MIN_TIME:
        return
    if not bb.can_see and machine.agent.global_position.distance_to(bb.last_known_pos) < 1.0:
        machine.request(SearchState.new())
    elif machine.agent.global_position.distance_to(bb.last_known_pos) > GIVE_UP_DISTANCE:
        machine.request(PatrolState.new())
```

`PatrolState`, `SearchState` and `DeadState` follow the same shape. Each script holds one
`class_name`, so put each in its own file.

## 2. Sight and hearing sensor

One sensor per agent, ticked on a timer, writes facts the decision layer reads. The order is
cheap to expensive, and only targets that pass the cone test pay for raycasts.

```gdscript
# sensor_3d.gd: attach under the agent; set eye, target and blackboard from the agent.
extends Node3D

@export var sight_range := 20.0
@export var half_angle_deg := 55.0
@export var tick_interval := 0.15           # about 7 Hz; stagger start times across agents
@export_flags_3d_physics var sight_mask := 1
var eye: Node3D
var target: Node3D
var blackboard: Dictionary
var _timer := randf() * 0.15                # random phase so agents don't all raycast together
var _exclude: Array[RID] = []

func _ready() -> void:
    if get_parent() is CollisionObject3D:
        _exclude.append(get_parent().get_rid())  # don't let the ray hit our own body

func _physics_process(dt: float) -> void:
    _timer -= dt
    if _timer > 0.0:
        return
    _timer = tick_interval
    var seen := _can_see(target)
    blackboard.can_see = seen
    if seen:
        blackboard.last_known_pos = target.global_position

func _can_see(t: Node3D) -> bool:
    if t == null:
        return false
    var to := t.global_position - eye.global_position
    if to.length_squared() > sight_range * sight_range:
        return false                         # 1. distance, no sqrt
    var fwd := -eye.global_basis.z
    if fwd.dot(to.normalized()) < cos(deg_to_rad(half_angle_deg)):
        return false                         # 2. view cone
    var space := get_world_3d().direct_space_state
    for offset in [Vector3(0, 1.6, 0), Vector3(0, 1.0, 0)]:   # 3. head, then chest
        var q := PhysicsRayQueryParameters3D.create(
            eye.global_position, t.global_position + offset, sight_mask, _exclude)
        var hit := space.intersect_ray(q)
        if hit.is_empty() or hit.collider == t:
            return true
    return false

# Hearing: gameplay posts sounds; agents never poll for them.
func hear(at: Vector3, loudness_radius: float) -> void:
    if eye.global_position.distance_squared_to(at) <= loudness_radius * loudness_radius:
        blackboard.heard_at = at
```

Post noises through a group call, for example
`get_tree().call_group(&"ai_sensors", &"hear", pos, 12.0)` for a gunshot and a smaller radius for
footsteps. Add an awareness value that rises while `can_see` holds (faster when close) and acts
only past a threshold, so the first sighting is not an instant hit.

## 3. Priority-truncated steering

Blending all behaviors with weights lets opposing forces cancel. Priority truncation spends a
fixed force budget in order: avoidance first, then separation, then path following.

```gdscript
# steering.gd: returns a force; the caller integrates vel += force * dt, pos += vel * dt.
func steer(pos: Vector2, vel: Vector2, wants: Array[Vector2], max_force: float) -> Vector2:
    var total := Vector2.ZERO
    var budget := max_force
    for want in wants:                      # ordered by priority, highest first
        if budget <= 0.0:
            break
        var f := want.limit_length(budget)
        total += f
        budget -= f.length()
    return total

func arrive(pos: Vector2, vel: Vector2, target: Vector2, max_speed: float, slow_radius: float) -> Vector2:
    var offset := target - pos
    var dist := offset.length()
    if dist < 0.001:
        return -vel
    var speed := max_speed * minf(dist / slow_radius, 1.0)
    return offset / dist * speed - vel
```

Call it as `steer(pos, vel, [avoid, separate, arrive_to_waypoint], max_force)`. Separation reads
only neighbors from a spatial hash (cells about the neighbor radius, often 2× the agent radius).
