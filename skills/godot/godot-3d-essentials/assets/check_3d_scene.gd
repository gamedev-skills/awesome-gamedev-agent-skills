# Headless check for the usual reasons a Godot 4.7 3D scene shows black or nothing.
# Needs no GPU, so it cannot judge colours: it checks the camera, lights, ambient light
# and mesh placement that decide whether anything can be seen at all.
#
# Run from the project folder (the scene after "--" defaults to the main scene):
#   godot --headless --path . --script /abs/path/to/check_3d_scene.gd -- res://level.tscn
# Exit code 0 means no problems and 1 means problems were found (listed on stderr).
extends SceneTree

const DEFAULT_ENV_SETTING := "rendering/environment/defaults/default_environment"


func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	var path: String = args[0] if args.size() > 0 else ProjectSettings.get_setting(
			"application/run/main_scene", "")
	var packed := load(path) as PackedScene if path != "" else null
	if packed == null:
		push_error("cannot load scene '%s'; pass one after --" % path)
		quit(1)
		return
	await process_frame  # root is not inside the tree until the first frame
	var scene := packed.instantiate()
	root.add_child(scene)
	await process_frame  # let a Camera3D with current = false claim the viewport

	var problems := PackedStringArray()
	var cam := root.get_camera_3d()
	if cam == null:
		problems.append("no current Camera3D: add one, or set current = true on the one you want")

	var lights := scene.find_children("*", "Light3D", true, false).filter(
			func(l: Light3D) -> bool: return l.is_visible_in_tree() and l.light_energy > 0.0)
	var env: Environment = null
	var envs := scene.find_children("*", "WorldEnvironment", true, false)
	if not envs.is_empty():
		env = (envs[0] as WorldEnvironment).environment
	if env == null and cam != null:
		env = cam.environment
	var default_env: String = ProjectSettings.get_setting(DEFAULT_ENV_SETTING, "")
	if env == null and default_env != "":
		env = load(default_env) as Environment
	var has_ambient := ambient_present(env)
	if lights.is_empty() and not has_ambient:
		problems.append("nothing lights the meshes (no visible light, no ambient), so they render"
				+ " black; the editor's preview sun and sky do not exist in the running game")
	elif lights.is_empty():
		print("note: no visible light; meshes get only flat ambient light")
	if env != null and env.background_mode == Environment.BG_SKY and env.sky == null:
		problems.append("Environment background is Sky but no Sky resource is set")

	if cam != null:
		for node in scene.find_children("*", "MeshInstance3D", true, false):
			var mesh := node as MeshInstance3D
			if not mesh.is_visible_in_tree():
				continue
			if mesh.mesh == null:
				problems.append("%s has no mesh" % scene.get_path_to(mesh))
				continue
			var centre := mesh.global_transform * mesh.get_aabb().get_center()
			if mesh.layers & cam.cull_mask == 0:
				problems.append("%s is on visual layers the camera's cull_mask hides"
						% scene.get_path_to(mesh))
			elif cam.is_position_behind(centre):
				problems.append("%s is behind the camera" % scene.get_path_to(mesh))
			elif cam.global_position.distance_to(centre) > cam.far:
				problems.append("%s is beyond the camera's far plane" % scene.get_path_to(mesh))

	for problem in problems:
		push_error(problem)
	print("3D scene problems: %d (current camera: %s, visible lights: %d, ambient: %s)" % [
			problems.size(), scene.get_path_to(cam) if cam else "none", lights.size(), has_ambient])
	quit(1 if problems.size() > 0 else 0)


# Mirrors the 4.7 renderers: with no Environment, Forward+ and Mobile use the default clear
# colour as ambient light, and the Compatibility renderer adds none.
func ambient_present(env: Environment) -> bool:
	var clear: Color = ProjectSettings.get_setting(
			"rendering/environment/defaults/default_clear_color", Color(0.3, 0.3, 0.3))
	if env == null:
		var method: String = ProjectSettings.get_setting("rendering/renderer/rendering_method", "")
		return method != "gl_compatibility" and clear.get_luminance() > 0.0
	if env.ambient_light_source == Environment.AMBIENT_SOURCE_DISABLED:
		return false
	if env.ambient_light_source == Environment.AMBIENT_SOURCE_COLOR:
		return env.ambient_light_color.get_luminance() * env.ambient_light_energy > 0.0
	if env.ambient_light_source == Environment.AMBIENT_SOURCE_SKY:
		return env.sky != null
	match env.background_mode:  # AMBIENT_SOURCE_BG: ambient follows the background
		Environment.BG_CLEAR_COLOR:
			return clear.get_luminance() > 0.0
		Environment.BG_COLOR:
			return env.background_color.get_luminance() > 0.0
		Environment.BG_SKY:
			return env.sky != null
	return true  # canvas, keep or camera-feed backgrounds: not judged here
