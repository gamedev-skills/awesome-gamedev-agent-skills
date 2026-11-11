# Headless check that every GDScript file in a Godot 4.7 project parses and compiles.
# Unlike `--check-only`, it runs with the project's autoloads and global classes
# registered, so scripts that use an autoload by name are not reported as broken.
#
# Run from the project folder (import first on a fresh checkout):
#   godot --headless --path . --import
#   godot --headless --path . --script /abs/path/to/check_scripts_compile.gd
# Exit code 0 means every script compiled and 1 means at least one did not; the
# engine prints the parse error and line above each "BROKEN" line on stderr.
# Loading a script runs no _ready()/_init(), but static variable initialisers do run.
extends SceneTree


func _initialize() -> void:
	var own_path: String = get_script().resource_path
	var broken := 0
	var total := 0
	for path in gd_files("res://"):
		if path == own_path:
			continue  # this runner, if it was copied into the project
		total += 1
		var script := load(path) as Script
		if script == null or not script.can_instantiate():
			broken += 1
			printerr("BROKEN ", path)
	print("scripts checked: %d, broken: %d" % [total, broken])
	quit(1 if broken > 0 else 0)


func gd_files(dir: String) -> PackedStringArray:
	var out := PackedStringArray()
	if FileAccess.file_exists(dir.path_join(".gdignore")):
		return out
	for file in DirAccess.get_files_at(dir):
		if file.get_extension() == "gd":
			out.append(dir.path_join(file))
	for sub in DirAccess.get_directories_at(dir):
		if not sub.begins_with("."):  # skips .godot/ and other hidden folders
			out.append_array(gd_files(dir.path_join(sub)))
	return out
