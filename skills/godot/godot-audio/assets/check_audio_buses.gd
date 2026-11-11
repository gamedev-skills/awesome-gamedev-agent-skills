# Headless check that every audio bus name used in a Godot 4.7 project exists in the
# bus layout the engine actually loads (audio/buses/default_bus_layout).
# A player whose bus name is missing plays on Master without any error, and
# AudioServer.get_bus_index() returns -1, so typos go unnoticed until someone listens.
#
# Run from the project folder:
#   godot --headless --path . --script /abs/path/to/check_audio_buses.gd
# Exit code 0 means every name was found and 1 means at least one is unknown (stderr).
# It scans .tscn/.tres/.gd text for `bus = "Name"`, `bus = &"Name"` and
# `get_bus_index("Name")`; names built at runtime are not seen.
extends SceneTree

const PATTERN := "(?:\\bbus\\s*=\\s*&?|get_bus_index\\(\\s*&?)\"([^\"]+)\""


func _initialize() -> void:
	var known := {}
	for i in AudioServer.get_bus_count():
		known[AudioServer.get_bus_name(i)] = true
	var regex := RegEx.create_from_string(PATTERN)
	var unknown := 0
	for path in project_files("res://"):
		var lines := FileAccess.get_file_as_string(path).split("\n")
		for n in lines.size():
			for found in regex.search_all(lines[n]):
				var bus := found.get_string(1)
				if not known.has(bus):
					unknown += 1
					push_error("%s:%d: unknown audio bus \"%s\"" % [path, n + 1, bus])
	print("buses in layout: %s; unknown bus references: %d" % [", ".join(known.keys()), unknown])
	quit(1 if unknown > 0 else 0)


func project_files(dir: String) -> PackedStringArray:
	var out := PackedStringArray()
	if FileAccess.file_exists(dir.path_join(".gdignore")):
		return out
	for file in DirAccess.get_files_at(dir):
		if file.get_extension() in ["tscn", "tres", "gd"]:
			out.append(dir.path_join(file))
	for sub in DirAccess.get_directories_at(dir):
		if not sub.begins_with("."):  # skips .godot/ and other hidden folders
			out.append_array(project_files(dir.path_join(sub)))
	return out
