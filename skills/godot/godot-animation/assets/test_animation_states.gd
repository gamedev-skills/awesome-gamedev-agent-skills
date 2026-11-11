# Headless check that a scene's animation clips and state-machine states exist and that
# the AnimationTree can reach each state (Godot 4.7).
#
# Copy to res://tests/, set SCENE, CLIPS and STATES to the names the game code uses, then:
#   godot --headless --path . --script res://tests/test_animation_states.gd
# Exit code 0 means every check passed and 1 means one failed (details on stderr).
extends SceneTree

const SCENE := "res://player.tscn"
const PLAYER_PATH := "AnimationPlayer"  # node paths inside SCENE
const TREE_PATH := "AnimationTree"      # leave the node out of the scene to skip tree checks
const CLIPS := ["idle", "run", "attack"]  # every name the code passes to play()
const STATES := [&"idle", &"run"]         # every name the code passes to travel()

var failed := 0


func _initialize() -> void:
	await process_frame  # root is not inside the tree until the first frame
	var scene := (load(SCENE) as PackedScene).instantiate()
	scene.set_process(false)  # keep the root script from choosing states during the test
	scene.set_physics_process(false)
	root.add_child(scene)

	var anim := scene.get_node_or_null(PLAYER_PATH) as AnimationPlayer
	check(anim != null, "%s has an AnimationPlayer at '%s'" % [SCENE, PLAYER_PATH])
	if anim:
		for clip: String in CLIPS:
			check(anim.has_animation(clip), "clip '%s' exists" % clip)

	var tree := scene.get_node_or_null(TREE_PATH) as AnimationTree
	if tree:
		check(tree.active, "AnimationTree.active is true")
		check(tree.get_node_or_null(tree.anim_player) is AnimationPlayer,
				"AnimationTree.anim_player points at an AnimationPlayer")
		var playback := tree.get("parameters/playback") as AnimationNodeStateMachinePlayback
		check(playback != null, "the tree root is a state machine")
		if playback:
			# Step time by hand: headless frames have uneven, often near-zero deltas.
			tree.callback_mode_process = AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
			for state: StringName in STATES:
				playback.travel(state)
				for i in 10:
					tree.advance(0.05)
				check(playback.get_current_node() == state, "state machine reaches '%s'" % state)

	print("animation checks failed: %d" % failed)
	quit(1 if failed > 0 else 0)


func check(ok: bool, label: String) -> void:
	if ok:
		print("ok   ", label)
	else:
		failed += 1
		push_error("FAIL " + label)
