# Headless behaviour check for a CharacterBody2D controller (Godot 4.7).
#
# Run from the project folder; the scene path after "--" overrides PLAYER_SCENE:
#   godot --headless --path . --script res://tests/test_character_controller.gd -- res://player.tscn
# It also runs from outside the project if you pass this file's absolute path to --script.
#
# Exit code 0 means every check passed and 1 means one failed (details on stderr).
# A grounded (platformer) body must land, jump and run; a floating (top-down) body must
# move in both axes and stay put without input. Edit the action names to match the
# project's Input Map.
extends SceneTree

const PLAYER_SCENE := "res://player.tscn"
const JUMP := "jump"
const LEFT := "move_left"
const RIGHT := "move_right"
const UP := "move_up"
const DOWN := "move_down"
const MAX_FRAMES := 120  # physics frames to wait for a landing (2 s at 60 Hz)

var failed := 0


func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	var scene_path: String = args[0] if args.size() > 0 else PLAYER_SCENE
	for action: String in [JUMP, LEFT, RIGHT, UP, DOWN]:
		if not InputMap.has_action(action):
			print("note: Input Map has no '%s' action; added a blank one for this run" % action)
			InputMap.add_action(action)
	await process_frame  # root is not inside the tree until the first frame

	var packed := load(scene_path) as PackedScene
	var player := packed.instantiate() as CharacterBody2D if packed else null
	check(player != null, "%s loads and its root is a CharacterBody2D" % scene_path)
	if player == null:
		finish()
		return
	var shapes := player.find_children("*", "CollisionShape2D", true, false)
	shapes.append_array(player.find_children("*", "CollisionPolygon2D", true, false))
	check(not shapes.is_empty(), "the body has a CollisionShape2D or CollisionPolygon2D")

	var floor := StaticBody2D.new()
	floor.collision_layer = player.collision_mask  # sit on whatever layers the body collides with
	var floor_shape := CollisionShape2D.new()
	floor_shape.shape = WorldBoundaryShape2D.new()  # endless floor, normal pointing up
	floor.add_child(floor_shape)
	floor.position = Vector2(0, 64)
	root.add_child(floor)
	player.position = Vector2.ZERO
	root.add_child(player)

	if player.motion_mode == CharacterBody2D.MOTION_MODE_GROUNDED:
		await check_platformer(player)
	else:
		await check_top_down(player)
	finish()


func check_platformer(player: CharacterBody2D) -> void:
	check(await wait_for_floor(player), "falls and lands on a floor within %d physics frames" % MAX_FRAMES)
	var ground_y := player.position.y
	await press(JUMP, 2)
	check(player.velocity.y < 0.0, "pressing '%s' on the floor gives upward velocity" % JUMP)
	await frames(10)
	check(player.position.y < ground_y - 4.0, "the jump leaves the floor")
	check(await wait_for_floor(player), "lands again after the jump")
	var start_x := player.position.x
	await press(RIGHT, 15)
	check(player.position.x > start_x + 4.0, "'%s' moves the body right" % RIGHT)
	await frames(60)
	check(absf(player.velocity.x) < 1.0, "stops within 1 s of releasing '%s'" % RIGHT)
	start_x = player.position.x
	await press(LEFT, 15)
	check(player.position.x < start_x - 4.0, "'%s' moves the body left" % LEFT)


func check_top_down(player: CharacterBody2D) -> void:
	await frames(30)
	var rest := player.position
	check(rest.distance_to(Vector2.ZERO) < 1.0, "a floating body does not drift without input")
	await press(RIGHT, 15)
	check(player.position.x > rest.x + 4.0, "'%s' moves the body right" % RIGHT)
	var before := player.position
	await press(UP, 15)
	check(player.position.y < before.y - 4.0, "'%s' moves the body up" % UP)
	before = player.position
	await press(DOWN, 15)
	check(player.position.y > before.y + 4.0, "'%s' moves the body down" % DOWN)


func wait_for_floor(player: CharacterBody2D) -> bool:
	for i in MAX_FRAMES:
		await physics_frame
		if player.is_on_floor():
			return true
	return false


func press(action: String, count: int) -> void:
	Input.action_press(action)
	await frames(count)
	Input.action_release(action)


func frames(count: int) -> void:
	for i in count:
		await physics_frame


func check(ok: bool, label: String) -> void:
	if ok:
		print("ok   ", label)
	else:
		failed += 1
		push_error("FAIL " + label)


func finish() -> void:
	print("controller checks failed: %d" % failed)
	quit(1 if failed > 0 else 0)
