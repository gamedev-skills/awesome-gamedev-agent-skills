extends CharacterBody2D

## Emitted on every jump. `is_air_jump` is true for the mid-air jump.
signal jumped(is_air_jump: bool)

@export_group("Run")
@export var speed := 220.0
@export var ground_acceleration := 1800.0
@export var ground_friction := 2200.0
@export var air_acceleration := 1100.0

@export_group("Jump")
@export var jump_velocity := -420.0
@export var air_jump_velocity := -380.0
@export var max_air_jumps := 1
@export var coyote_time := 0.1
@export var jump_buffer_time := 0.12
@export var jump_cut_multiplier := 0.45
@export var fall_gravity_multiplier := 1.7

var _air_jumps_left := 0
var _coyote_timer := 0.0
var _jump_buffer_timer := 0.0
var _was_on_floor := false
var _spawn_position := Vector2.ZERO
var _squash_tween: Tween

@onready var _visual: Node2D = $Visual


func _ready() -> void:
	_spawn_position = global_position
	_air_jumps_left = max_air_jumps


func _physics_process(delta: float) -> void:
	var on_floor := is_on_floor()

	# Landing refills the air jumps; the ground jump itself is always free.
	if on_floor:
		_air_jumps_left = max_air_jumps
		_coyote_timer = coyote_time
		if not _was_on_floor:
			_play_squash(Vector2(1.25, 0.8))
	else:
		_coyote_timer = maxf(_coyote_timer - delta, 0.0)

	# Buffer a press so it can fire on the frame we land.
	if Input.is_action_just_pressed("ui_accept"):
		_jump_buffer_timer = jump_buffer_time
	else:
		_jump_buffer_timer = maxf(_jump_buffer_timer - delta, 0.0)

	# Jump priority: ground/coyote first, then spend an air jump.
	if _jump_buffer_timer > 0.0:
		if on_floor or _coyote_timer > 0.0:
			_perform_jump(false)
		elif _air_jumps_left > 0:
			_air_jumps_left -= 1
			_perform_jump(true)

	# Tap to hop, hold for the full arc.
	if Input.is_action_just_released("ui_accept") and velocity.y < 0.0:
		velocity.y *= jump_cut_multiplier

	if not on_floor:
		var gravity := get_gravity()
		if velocity.y > 0.0:
			gravity *= fall_gravity_multiplier
		velocity += gravity * delta

	var direction := Input.get_axis("ui_left", "ui_right")
	var acceleration := air_acceleration if not on_floor else ground_acceleration
	if direction != 0.0:
		velocity.x = move_toward(velocity.x, direction * speed, acceleration * delta)
	else:
		velocity.x = move_toward(velocity.x, 0.0, ground_friction * delta)

	_was_on_floor = on_floor
	move_and_slide()


func _perform_jump(is_air_jump: bool) -> void:
	velocity.y = air_jump_velocity if is_air_jump else jump_velocity
	_jump_buffer_timer = 0.0
	_coyote_timer = 0.0
	_play_squash(Vector2(0.8, 1.25))
	jumped.emit(is_air_jump)


func _play_squash(target: Vector2) -> void:
	if _squash_tween and _squash_tween.is_valid():
		_squash_tween.kill()
	_visual.scale = target
	_squash_tween = create_tween()
	_squash_tween.tween_property(_visual, "scale", Vector2.ONE, 0.18).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)


func reset() -> void:
	if _squash_tween and _squash_tween.is_valid():
		_squash_tween.kill()
	global_position = _spawn_position
	velocity = Vector2.ZERO
	_air_jumps_left = max_air_jumps
	_coyote_timer = 0.0
	_jump_buffer_timer = 0.0
	_was_on_floor = false
	_visual.scale = Vector2.ONE


func get_air_jumps_left() -> int:
	return _air_jumps_left
