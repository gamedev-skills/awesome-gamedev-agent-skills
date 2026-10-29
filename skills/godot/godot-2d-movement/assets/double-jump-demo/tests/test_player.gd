extends SceneTree

var passed := 0
var failed := 0


func _initialize() -> void:
	await run_tests()
	print("Results: %d passed, %d failed" % [passed, failed])
	quit(1 if failed > 0 else 0)


func assert_true(condition: bool, label: String) -> void:
	if condition:
		passed += 1
	else:
		failed += 1
		push_error("FAIL %s" % label)


func assert_eq(actual, expected, label: String) -> void:
	if actual == expected:
		passed += 1
	else:
		failed += 1
		push_error("FAIL %s: expected %s, got %s" % [label, expected, actual])


func run_tests() -> void:
	await process_frame

	var world := Node2D.new()
	root.add_child(world)

	var floor_body := StaticBody2D.new()
	floor_body.position = Vector2(0, 100)
	var floor_shape := CollisionShape2D.new()
	var floor_rect := RectangleShape2D.new()
	floor_rect.size = Vector2(2000, 40)
	floor_shape.shape = floor_rect
	floor_body.add_child(floor_shape)
	world.add_child(floor_body)

	var player_scene: PackedScene = load("res://player.tscn")
	var player = player_scene.instantiate()
	player.position = Vector2(0, 50)
	world.add_child(player)

	# Let the player settle on the floor.
	for _i in 10:
		await physics_frame

	assert_eq(player.is_on_floor(), true, "player_lands")
	assert_eq(player.get_air_jumps_left(), 1, "air_jump_available_on_floor")

	# Ground jump: the air jump must stay available.
	Input.action_press("ui_accept")
	await physics_frame
	await physics_frame
	assert_true(player.velocity.y < 0.0, "ground_jump_rises")
	assert_eq(player.get_air_jumps_left(), 1, "ground_jump_keeps_air_jump")

	# Wait out coyote time, then use the air jump.
	for _i in 8:
		await physics_frame
	Input.action_release("ui_accept")
	await physics_frame
	Input.action_press("ui_accept")
	await physics_frame
	await physics_frame
	assert_true(player.velocity.y < 0.0, "air_jump_rises")
	assert_eq(player.get_air_jumps_left(), 0, "air_jump_consumed")

	# A third press while airborne must not jump again.
	Input.action_release("ui_accept")
	await physics_frame
	var velocity_before: float = player.velocity.y
	Input.action_press("ui_accept")
	await physics_frame
	await physics_frame
	assert_eq(player.get_air_jumps_left(), 0, "no_third_jump")
	assert_true(player.velocity.y > velocity_before, "third_press_does_not_reset_velocity")

	Input.action_release("ui_accept")

	# Land and confirm the air jump refills.
	for _i in 240:
		await physics_frame
		if player.is_on_floor():
			# The landing frame has not run _physics_process yet; wait one more
			# frame so the controller refills its air-jump counter.
			await physics_frame
			break
	assert_eq(player.is_on_floor(), true, "player_lands_again")
	assert_eq(player.get_air_jumps_left(), 1, "air_jump_refilled_on_landing")
