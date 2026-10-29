extends Node2D

@onready var _player = $Player
@onready var _status: Label = $UI/Status
@onready var _air_jumps: Label = $UI/AirJumps


func _ready() -> void:
	_player.jumped.connect(_on_player_jumped)


func _process(_delta: float) -> void:
	_air_jumps.text = "Air jumps left: %d" % _player.get_air_jumps_left()


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo and event.keycode == KEY_R:
		_player.reset()
		_status.text = "Reset"
		_status.modulate = Color.WHITE


func _on_player_jumped(is_air_jump: bool) -> void:
	if is_air_jump:
		_status.text = "DOUBLE JUMP!"
		_status.modulate = Color(0.35, 0.9, 1.0)
	else:
		_status.text = "Jump"
		_status.modulate = Color.WHITE
