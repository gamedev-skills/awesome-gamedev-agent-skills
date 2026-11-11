"""End-to-end tests for the godot-nodes-scenes project checker."""

from __future__ import annotations

import json
import os
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "skills" / "godot" / "godot-nodes-scenes" / "scripts" / "check_godot_project.py"

PROJECT = """\
config_version=5

[application]

config/name="Test"
run/main_scene="uid://main0000001"
config/icon="res://icon.svg"

[autoload]

GameState="*res://game_state.gd"
"""

MAIN_SCENE = """\
[gd_scene format=3 uid="uid://main0000001"]

[ext_resource type="Script" uid="uid://script000001" path="res://main.gd" id="1_main"]
[ext_resource type="PackedScene" uid="uid://player000001" path="res://player/player.tscn" id="2_player"]
[ext_resource type="Texture2D" uid="uid://icon00000001" path="res://icon.svg" id="3_icon"]
[ext_resource type="PackedScene" uid="uid://model0000001" path="res://model.glb" id="4_model"]

[sub_resource type="RectangleShape2D" id="RectangleShape2D_a"]
size = Vector2(4, 4)

[node name="Main" type="Node2D" unique_id=1]
script = ExtResource("1_main")

[node name="Player" parent="." unique_id=2 instance=ExtResource("2_player")]

[node name="Extra" type="Sprite2D" parent="Player/Body" unique_id=3]
texture = ExtResource("3_icon")

[node name="Shape" type="CollisionShape2D" parent="Player/Body" unique_id=4]
shape = SubResource("RectangleShape2D_a")

[node name="Model" parent="." unique_id=5 instance=ExtResource("4_model")]

[node name="Light" type="Node3D" parent="Model/Armature/Skeleton3D" unique_id=6]

[connection signal="hit" from="Player/Body" to="." method="_on_hit"]
"""

PLAYER_SCENE = """\
[gd_scene format=3 uid="uid://player000001"]

[node name="Player" type="Node2D" unique_id=10]

[node name="Body" type="Node2D" parent="." unique_id=11]
"""

MAIN_GD = """\
extends Node2D

const PLAYER := preload("res://player/player.tscn")
# load("res://commented_out.tscn") is ignored
var level_path := "res://not_a_load.tscn"

func _ready() -> void:
    var scene = load("res://levels/level_%d.tscn" % 1)
"""

IMPORT_TEMPLATE = """\
[remap]

importer="{importer}"
type="{type}"
uid="{uid}"
path="res://.godot/imported/{name}-0.ctex"
"""

UID_CHARS = "abcdefghijklmnopqrstuvwxy012345678"


def binary_resource(uid: str | None, compressed: bool = False) -> bytes:
    """Bytes of a minimal Godot binary resource header (RSRC), or a compressed one (RSCC)."""
    if compressed:
        return b"RSCC" + bytes(64)
    value = 0
    for ch in (uid or "uid://a")[len("uid://"):]:
        value = value * len(UID_CHARS) + UID_CHARS.index(ch)
    type_name = b"ArrayMesh\0"
    flags = 3 if uid else 1
    return (b"RSRC" + struct.pack("<IIIII", 0, 0, 4, 5, 6) + struct.pack("<I", len(type_name)) + type_name
            + struct.pack("<QIQ", 0, flags, value) + bytes(32))


class GodotProjectCheckerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name) / "game"
        self.make_clean_project()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    # -- helpers

    def write(self, rel: str, text: str, newline: str = "\n") -> Path:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8", newline=newline) as handle:
            handle.write(text)
        return path

    def edit(self, rel: str, old: str, new: str) -> None:
        path = self.root / rel
        text = path.read_text(encoding="utf-8")
        self.assertIn(old, text, f"fixture text not found in {rel}")
        path.write_text(text.replace(old, new, 1), encoding="utf-8")

    def make_clean_project(self) -> None:
        self.write("project.godot", PROJECT)
        self.write("main.tscn", MAIN_SCENE)
        self.write("main.gd", MAIN_GD)
        self.write("main.gd.uid", "uid://script000001\n")
        self.write("game_state.gd", "extends Node\n")
        self.write("game_state.gd.uid", "uid://state0000001\n")
        self.write("player/player.tscn", PLAYER_SCENE)
        self.write("icon.svg", "<svg xmlns='http://www.w3.org/2000/svg'/>")
        self.write(
            "icon.svg.import",
            IMPORT_TEMPLATE.format(importer="texture", type="CompressedTexture2D", uid="uid://icon00000001", name="icon"),
        )
        self.write("model.glb", "glTF")
        self.write(
            "model.glb.import",
            IMPORT_TEMPLATE.format(importer="scene", type="PackedScene", uid="uid://model0000001", name="model"),
        )

    def run_checker(self, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(CHECKER), *args],
            check=False,
            capture_output=True,
            text=True,
            cwd=cwd,
        )

    def report(self, *args: str) -> tuple[int, dict]:
        result = self.run_checker(str(self.root), "--json", "--max-issues", "500", *args)
        self.assertIn(result.returncode, (0, 1), result.stderr)
        return result.returncode, json.loads(result.stdout)

    def codes(self, payload: dict, kind: str) -> list[str]:
        return [issue["code"] for issue in payload[kind]]

    def assert_only(self, payload: dict, kind: str, code: str) -> dict:
        self.assertEqual(self.codes(payload, kind), [code], payload)
        return payload[kind][0]

    # -- clean project and CLI contract

    def test_clean_project_passes(self) -> None:
        result = self.run_checker(str(self.root))
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("Summary: 0 errors, 0 warnings", result.stdout)

    def test_defaults_to_current_directory(self) -> None:
        result = self.run_checker(cwd=self.root)
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_json_schema(self) -> None:
        self.edit("main.tscn", 'path="res://icon.svg"', 'path="res://gone.svg"')
        self.edit("main.tscn", 'uid="uid://icon00000001" ', "")
        code, payload = self.report()
        self.assertEqual(code, 1)
        self.assertEqual(
            set(payload), {"tool", "schema", "root", "files_checked", "error_count", "warning_count", "errors", "warnings", "truncated"}
        )
        self.assertEqual(payload["tool"], "check_godot_project")
        self.assertEqual(payload["schema"], 1)
        self.assertGreater(payload["files_checked"], 0)
        self.assertFalse(payload["truncated"])
        issue = payload["errors"][0]
        self.assertEqual(set(issue), {"code", "file", "line", "message", "fix"})
        self.assertEqual(issue["file"], "main.tscn")
        self.assertIsInstance(issue["line"], int)

    def test_text_output_format_and_cap(self) -> None:
        for name in ("a", "b", "c"):
            self.write(f"{name}.gd", f'extends Node\nvar s = load("res://missing_{name}.tscn")\n')
        self.edit("main.tscn", 'path="res://main.gd"', 'path="res://nope.gd"')
        self.edit("main.tscn", 'uid="uid://script000001" ', "")
        result = self.run_checker(str(self.root), "--max-issues", "2")
        self.assertEqual(result.returncode, 1)
        lines = result.stdout.splitlines()
        self.assertTrue(lines[0].startswith("ERROR main.tscn:3: "), lines)
        self.assertTrue(lines[1].startswith("  fix: "), lines)
        self.assertTrue(lines[2].startswith("WARNING a.gd:2: "), lines)
        self.assertIn("... and 2 more", result.stdout)
        self.assertIn("Summary: 1 errors, 3 warnings", result.stdout)

        unlimited = self.run_checker(str(self.root), "--max-issues", "0")
        self.assertNotIn("more", unlimited.stdout)
        self.assertEqual(unlimited.stdout.count("  fix: "), 4)
        code, payload = self.report("--max-issues", "1")
        self.assertTrue(payload["truncated"])
        self.assertEqual((payload["error_count"], payload["warning_count"]), (1, 3))

    def test_strict_fails_on_warnings(self) -> None:
        self.write("extra.gd", 'extends Node\nvar s = load("res://nothing_here.tscn")\n')
        self.assertEqual(self.run_checker(str(self.root)).returncode, 0)
        self.assertEqual(self.run_checker(str(self.root), "--strict").returncode, 1)

    def test_source_controls_are_escaped_in_text_but_preserved_in_json(self) -> None:
        for source, value, escaped in (
            (r"\n", "\n", r"\n"), (r"\r", "\r", r"\r"), (r"\t", "\t", r"\t"),
            ("\x1b", "\x1b", r"\x1b"), ("\x01", "\x01", r"\x01"), ("\x9b", "\x9b", r"\x9b"),
        ):
            with self.subTest(control=escaped):
                scene = MAIN_SCENE.replace(
                    'uid="uid://icon00000001" path="res://icon.svg"',
                    f'path="res://missing{source}AUDIT_MARKER.svg"',
                )
                self.write("main.tscn", scene)
                result = self.run_checker(str(self.root))
                code, payload = self.report()
                self.assertEqual((result.returncode, code), (1, 1))
                self.assertEqual((payload["error_count"], payload["warning_count"]), (1, 0))
                self.assertIn(f"missing{value}AUDIT_MARKER.svg", payload["errors"][0]["message"])
                self.assertIn(f"missing{escaped}AUDIT_MARKER.svg", result.stdout)
                self.assertEqual(len(result.stdout.splitlines()), 3, result.stdout)
                self.assertTrue(result.stdout.startswith("ERROR main.tscn:5: "), result.stdout)

    @unittest.skipIf(os.name == "nt", "Windows filenames cannot contain these control characters")
    def test_filename_and_fix_controls_stay_inside_diagnostic_lines(self) -> None:
        controls = "\n\r\t\x1b\x9b\u2028\u2029"
        escaped = r"\n\r\t\x1b\x9b\u2028\u2029"
        self.write(f"art/{controls}icon.svg", "<svg/>")
        self.write(f"{controls}\x85check.gd", 'extends Node\nvar s = load("res://nothing.tscn")\n')
        # A missing scene resource with the same basename makes its fix name the real file.
        self.edit("main.tscn", 'uid="uid://icon00000001" path="res://icon.svg"',
                  f'path="res://missing/\\n\\r\\t\x1b\x9b\u2028\u2029icon.svg"')
        result = self.run_checker(str(self.root))
        code, payload = self.report()
        self.assertEqual((result.returncode, code), (1, 1))
        self.assertIn(f"art/{controls}icon.svg", payload["errors"][0]["fix"])
        self.assertIn(f"art/{escaped}icon.svg", result.stdout)
        self.assertEqual(payload["warnings"][0]["file"], f"{controls}\x85check.gd")
        self.assertIn(f"WARNING {escaped}\\x85check.gd:2:", result.stdout)
        self.assertTrue(all(line.startswith(("ERROR ", "WARNING ", "  fix: ", "Summary: "))
                            for line in result.stdout.splitlines()), result.stdout)

    def test_invalid_cli_target_controls_are_escaped(self) -> None:
        target = str(self.root / "missing\n\r\t\x1b\x85target")
        result = self.run_checker(target)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(len(result.stderr.splitlines()), 1, result.stderr)
        self.assertIn(r"missing\n\r\t\x1b\x85target", result.stderr)

    def test_not_a_project_exits_2(self) -> None:
        empty = Path(self.temp_dir.name) / "empty"
        empty.mkdir()
        result = self.run_checker(str(empty))
        self.assertEqual(result.returncode, 2)
        self.assertIn("not a Godot project", result.stderr)
        self.assertEqual(self.run_checker(str(empty / "missing")).returncode, 2)

    def test_help_has_example(self) -> None:
        result = self.run_checker("--help")
        self.assertEqual(result.returncode, 0)
        self.assertIn("example:", result.stdout)

    # -- ext_resource / uid rules

    def test_missing_path_and_unknown_uid_is_error(self) -> None:
        self.edit("main.tscn", 'uid="uid://icon00000001" path="res://icon.svg"',
                  'uid="uid://zzzzzzzzzzzz" path="res://art/icon.svg"')
        _, payload = self.report()
        issue = self.assert_only(payload, "errors", "ext-resource-missing")
        self.assertIn("res://icon.svg", issue["fix"])  # suggests the file with the same name

    def test_stale_path_with_resolving_uid_is_only_warning(self) -> None:
        self.write("art/hero.svg", "<svg/>")
        (self.root / "icon.svg").unlink()
        (self.root / "icon.svg.import").rename(self.root / "art" / "hero.svg.import")
        self.edit("project.godot", 'config/icon="res://icon.svg"', 'config/icon="res://art/hero.svg"')
        code, payload = self.report()
        self.assertEqual(code, 0)
        self.assertEqual(payload["errors"], [])
        warning = self.assert_only(payload, "warnings", "ext-resource-path-stale")
        self.assertIn("res://art/hero.svg", warning["fix"])

    def test_existing_path_with_unknown_uid_is_warning(self) -> None:
        self.edit("main.tscn", 'uid="uid://icon00000001"', 'uid="uid://unknown00001"')
        code, payload = self.report()
        self.assertEqual(code, 0)
        self.assert_only(payload, "warnings", "ext-resource-uid-unknown")

    def test_moved_script_without_its_uid_file(self) -> None:
        (self.root / "scripts").mkdir()
        (self.root / "main.gd").rename(self.root / "scripts" / "main.gd")
        self.edit("main.tscn", 'path="res://main.gd"', 'path="res://scripts/main.gd"')
        code, payload = self.report()
        self.assertEqual(code, 0)
        self.assertEqual(sorted(self.codes(payload, "warnings")), ["ext-resource-uid-unknown", "uid-file-orphaned"])

    def test_uid_pointing_at_another_file_is_warning(self) -> None:
        self.edit("main.tscn", 'path="res://icon.svg"', 'path="res://model.glb"')
        _, payload = self.report()
        self.assert_only(payload, "warnings", "uid-path-mismatch")

    def test_case_mismatch_is_error(self) -> None:
        self.edit("main.tscn", 'uid="uid://player000001" path="res://player/player.tscn"',
                  'path="res://Player/Player.tscn"')
        _, payload = self.report()
        issue = self.assert_only(payload, "errors", "path-case-mismatch")
        self.assertIn("res://player/player.tscn", issue["fix"])

    def test_relative_ext_resource_path(self) -> None:
        self.edit("main.tscn", 'uid="uid://player000001" path="res://player/player.tscn"',
                  'path="player/player.tscn"')
        code, payload = self.report()
        self.assertEqual(code, 0, payload)

    def test_undeclared_ids(self) -> None:
        self.edit("main.tscn", 'texture = ExtResource("3_icon")', 'texture = ExtResource("9_nope")')
        self.edit("main.tscn", 'shape = SubResource("RectangleShape2D_a")', 'shape = SubResource("Missing_b")')
        _, payload = self.report()
        self.assertEqual(sorted(self.codes(payload, "errors")),
                         ["ext-resource-id-undeclared", "sub-resource-id-undeclared"])

    def test_sub_resource_used_before_declared(self) -> None:
        self.write("mat.tres", """\
[gd_resource type="ShaderMaterial" format=3 uid="uid://mat000000001"]

[sub_resource type="Shader" id="Shader_x"]
code = "shader_type canvas_item;"

[resource]
shader = SubResource("Shader_x")
next_pass = SubResource("Late_y")

[sub_resource type="ShaderMaterial" id="Late_y"]
""")
        _, payload = self.report()
        self.assert_only(payload, "errors", "sub-resource-used-before-declared")

    def test_references_inside_strings_are_ignored(self) -> None:
        self.write("builtin.tscn", """\
[gd_scene format=3 uid="uid://builtin00001"]

[sub_resource type="GDScript" id="GDScript_1"]
script/source = "extends Node
# ExtResource(\\"nope\\") and
[node name=\\"Fake\\" parent=\\"Nowhere\\"]
"

[node name="Root" type="Node" unique_id=1]
script = SubResource("GDScript_1")
""")
        code, payload = self.report()
        self.assertEqual(code, 0, payload)

    def test_malformed_ext_resource_and_duplicate_ids(self) -> None:
        self.edit("main.tscn", '[ext_resource type="Script" uid="uid://script000001" path="res://main.gd" id="1_main"]',
                  '[ext_resource type="Script" path="res://main.gd" id="2_player"]\n'
                  '[ext_resource path="res://main.gd" id="1_main"]')
        _, payload = self.report()
        self.assertEqual(sorted(self.codes(payload, "errors")), ["ext-resource-malformed", "resource-id-duplicate"])

    def test_duplicate_uid(self) -> None:
        self.write("player/player_copy.tscn", PLAYER_SCENE)
        _, payload = self.report()
        issue = self.assert_only(payload, "errors", "uid-duplicate")
        self.assertEqual(issue["file"], "player/player_copy.tscn")

    def test_placeholder_malformed_sub_resource_and_orphaned_import(self) -> None:
        self.write("holder.tscn", """\
[gd_scene format=3 uid="uid://holder000001"]

[sub_resource type="CircleShape2D"]

[node name="Root" type="Node" unique_id=1]

[node name="Later" parent="." unique_id=2 instance_placeholder="res://levels/later.tscn"]
""")
        self.write("old_art.png.import", IMPORT_TEMPLATE.format(
            importer="texture", type="CompressedTexture2D", uid="uid://oldart000001", name="old_art"))
        _, payload = self.report()
        self.assertEqual(sorted(self.codes(payload, "errors")), ["placeholder-path-missing", "sub-resource-malformed"])
        self.assert_only(payload, "warnings", "import-file-orphaned")

    def test_missing_header(self) -> None:
        self.write("broken.tres", "[resource]\nvalue = 1\n")
        _, payload = self.report()
        self.assert_only(payload, "errors", "header-missing")

    # -- scene trees

    def test_bad_parent_path(self) -> None:
        self.edit("main.tscn", 'parent="Player/Body" unique_id=3', 'parent="Player/Torso" unique_id=3')
        _, payload = self.report()
        issue = self.assert_only(payload, "errors", "node-parent-missing")
        self.assertEqual(issue["line"], 16)

    def test_parent_inside_unreadable_model_is_not_reported(self) -> None:
        # Model/Armature/Skeleton3D lives inside model.glb, which cannot be read; no error expected.
        code, payload = self.report()
        self.assertEqual(code, 0, payload)

    def test_root_node_rules(self) -> None:
        self.write("two_roots.tscn", """\
[gd_scene format=3]

[node name="A" type="Node" unique_id=1]

[node name="B" type="Node" unique_id=2]
""")
        self.write("no_root.tscn", """\
[gd_scene format=3]

[node name="A" type="Node" parent="." unique_id=1]
""")
        _, payload = self.report()
        self.assertEqual(sorted(self.codes(payload, "errors")), ["scene-multiple-roots", "scene-root-missing"])

    def test_inherited_scene_uses_base_nodes(self) -> None:
        self.write("player/blue_player.tscn", """\
[gd_scene format=3 uid="uid://blue00000001"]

[ext_resource type="PackedScene" uid="uid://player000001" path="res://player/player.tscn" id="1_base"]

[node name="BluePlayer" instance=ExtResource("1_base")]

[node name="Hat" type="Sprite2D" parent="Body" unique_id=20]

[node name="Feather" type="Sprite2D" parent="Body/Wing" unique_id=21]
""")
        _, payload = self.report()
        issue = self.assert_only(payload, "errors", "node-parent-missing")
        self.assertIn("Body/Wing", issue["message"])

    def test_connection_to_missing_node(self) -> None:
        self.edit("main.tscn", 'from="Player/Body"', 'from="Player/Legs"')
        _, payload = self.report()
        self.assert_only(payload, "errors", "connection-node-missing")

    # -- project.godot

    def test_main_scene_and_autoload_missing(self) -> None:
        self.edit("project.godot", 'run/main_scene="uid://main0000001"', 'run/main_scene="res://scenes/main.tscn"')
        self.edit("project.godot", '"*res://game_state.gd"', '"*res://autoload/game_state.gd"')
        _, payload = self.report()
        self.assertEqual(sorted(self.codes(payload, "errors")), ["autoload-missing", "main-scene-missing"])

    def test_main_scene_unknown_uid(self) -> None:
        self.edit("project.godot", "uid://main0000001", "uid://nosuchscene1")
        _, payload = self.report()
        self.assert_only(payload, "errors", "main-scene-missing")

    def test_main_scene_not_set_is_warning(self) -> None:
        self.edit("project.godot", 'run/main_scene="uid://main0000001"\n', "")
        code, payload = self.report()
        self.assertEqual(code, 0)
        self.assert_only(payload, "warnings", "main-scene-not-set")

    def test_other_project_setting_path(self) -> None:
        self.edit("project.godot", 'config/icon="res://icon.svg"', 'config/icon="res://icon.png"')
        code, payload = self.report()
        self.assertEqual(code, 0)
        self.assert_only(payload, "warnings", "project-path-missing")

    # -- scripts

    def test_script_literal_paths(self) -> None:
        self.edit("main.gd", 'preload("res://player/player.tscn")', 'preload("res://player/hero.tscn")')
        code, payload = self.report()
        self.assertEqual(code, 0)
        issue = self.assert_only(payload, "warnings", "script-path-missing")
        self.assertEqual((issue["file"], issue["line"]), ("main.gd", 3))

    # -- folders Godot skips, encodings

    def test_gdignore_folder_is_skipped(self) -> None:
        self.write("tools/.gdignore", "")
        self.write("tools/broken.tscn", "[node name=\"x\" parent=\"nowhere\"]\n")
        self.write("tools/broken.gd", 'extends Node\nvar s = load("res://nothing.tscn")\n')
        self.write(".hidden/broken.tscn", "garbage\n")
        code, payload = self.report()
        self.assertEqual(code, 0, payload)

    def test_reference_into_gdignore_folder_is_warning(self) -> None:
        self.write("tools/.gdignore", "")
        self.write("tools/thing.tscn", PLAYER_SCENE.replace("uid://player000001", "uid://thing0000001"))
        self.edit("main.tscn", 'uid="uid://player000001" path="res://player/player.tscn"', 'path="res://tools/thing.tscn"')
        code, payload = self.report()
        self.assertEqual(code, 0)
        self.assert_only(payload, "warnings", "path-in-ignored-dir")

    def test_crlf_and_bom_files(self) -> None:
        self.write("project.godot", "\ufeff" + PROJECT, newline="\r\n")
        self.write("main.tscn", "\ufeff" + MAIN_SCENE, newline="\r\n")
        self.write("main.gd", "\ufeff" + MAIN_GD, newline="\r\n")
        code, payload = self.report()
        self.assertEqual(code, 0, payload)
        self.edit("main.tscn", 'parent="Player/Body" unique_id=3', 'parent="Player/Torso" unique_id=3')
        _, payload = self.report()
        issue = self.assert_only(payload, "errors", "node-parent-missing")
        self.assertEqual(issue["line"], 16)

    # -- review fixes

    def test_backslashes_and_double_slashes_in_paths(self) -> None:
        # Godot's simplify_path() turns "\\" into "/" and collapses "//", so these load fine.
        self.edit("main.tscn", 'uid="uid://player000001" path="res://player/player.tscn"',
                  'path="res://player\\\\player.tscn"')
        self.edit("main.tscn", 'uid="uid://icon00000001" path="res://icon.svg"', 'path="res:///icon.svg"')
        self.edit("project.godot", '"*res://game_state.gd"', '"*res://.//game_state.gd"')
        code, payload = self.report()
        self.assertEqual(code, 0, payload)
        self.assertEqual(payload["warnings"], [])

    def test_stale_parent_with_id_path_is_warning(self) -> None:
        # Godot 4.6+ writes parent_id_path / from_uid_path and recovers a renamed node through them.
        self.edit("main.tscn", 'parent="Player/Body" unique_id=3',
                  'parent="Player/Torso" parent_id_path=PackedInt32Array(2, 11) unique_id=3')
        self.edit("main.tscn", 'from="Player/Body"', 'from="Player/Legs" from_uid_path=PackedInt32Array(2, 11)')
        code, payload = self.report()
        self.assertEqual(code, 0, payload)
        self.assertEqual(sorted(self.codes(payload, "warnings")), ["connection-node-missing", "node-parent-missing"])

    def test_uid_inside_binary_resource(self) -> None:
        (self.root / "meshes").mkdir()
        (self.root / "meshes" / "rock.res").write_bytes(binary_resource("uid://btydvpp0agbfj"))
        self.edit("main.tscn", '[sub_resource',
                  '[ext_resource type="ArrayMesh" uid="uid://btydvpp0agbfj" path="res://rock.res" id="5_rock"]\n\n'
                  '[sub_resource')
        code, payload = self.report()
        self.assertEqual(code, 0, payload)
        warning = self.assert_only(payload, "warnings", "ext-resource-path-stale")
        self.assertIn("res://meshes/rock.res", warning["fix"])

    def test_unknown_uid_may_be_in_compressed_binary_resource(self) -> None:
        (self.root / "level.scn").write_bytes(binary_resource(None, compressed=True))
        self.edit("project.godot", "uid://main0000001", "uid://inlevelscn01")
        self.edit("main.tscn", '[sub_resource',
                  '[ext_resource type="PackedScene" uid="uid://movedscene1" path="res://old/level.scn" id="5_lv"]\n'
                  '[ext_resource type="Texture2D" uid="uid://movedimage1" path="res://old/pic.png" id="6_pic"]\n\n'
                  '[sub_resource')
        _, payload = self.report()
        self.assertEqual(sorted(self.codes(payload, "warnings")), ["ext-resource-missing", "main-scene-missing"])
        self.assertEqual(self.codes(payload, "errors"), ["ext-resource-missing"])  # pic.png: not a binary resource
        self.assertIn("old/pic.png", payload["errors"][0]["message"])

    def test_uppercase_scene_extension_keeps_its_uid(self) -> None:
        self.write("levels/Cave.TSCN", PLAYER_SCENE.replace("uid://player000001", "uid://cave00000001"))
        self.edit("main.tscn", '[sub_resource',
                  '[ext_resource type="PackedScene" uid="uid://cave00000001" path="res://Cave.TSCN" id="5_cave"]\n\n'
                  '[sub_resource')
        code, payload = self.report()
        self.assertEqual(code, 0, payload)
        self.assert_only(payload, "warnings", "ext-resource-path-stale")

    def test_sub_resource_without_type(self) -> None:
        self.edit("main.tscn", '[sub_resource type="RectangleShape2D" id="RectangleShape2D_a"]',
                  '[sub_resource id="RectangleShape2D_a"]')
        _, payload = self.report()
        issue = self.assert_only(payload, "errors", "sub-resource-malformed")
        self.assertIn("type", issue["message"])

    def test_escaped_backslash_before_closing_quote(self) -> None:
        self.write("tool.tres", """\
[gd_resource type="Resource" format=3]

[resource]
path_text = "C:\\\\games\\\\"
other = ExtResource("9_nope")
""")
        _, payload = self.report()
        self.assert_only(payload, "errors", "ext-resource-id-undeclared")

    @unittest.skipUnless(hasattr(os, "symlink"), "needs symlinks")
    def test_symlink_loop_and_broken_symlink(self) -> None:
        try:
            os.symlink(self.root, self.root / "player" / "loop", target_is_directory=True)
            os.symlink(self.root / "nowhere.tscn", self.root / "gone.tscn")
        except OSError:
            self.skipTest("cannot create symlinks here")
        self.edit("main.tscn", 'uid="uid://player000001" path="res://player/player.tscn"', 'path="res://gone.tscn"')
        _, payload = self.report()
        self.assert_only(payload, "errors", "ext-resource-missing")

    @unittest.skipIf(os.name == "nt" or os.geteuid() == 0, "needs POSIX permissions as a normal user")
    def test_unreadable_folder_and_file_are_warnings(self) -> None:
        self.write("locked/thing.tscn", PLAYER_SCENE.replace("uid://player000001", "uid://thing0000001"))
        self.write("secret.tres", '[gd_resource type="Resource" format=3]\n')
        self.edit("main.tscn", 'uid="uid://player000001" path="res://player/player.tscn"', 'path="res://locked/thing.tscn"')
        os.chmod(self.root / "locked", 0)
        os.chmod(self.root / "secret.tres", 0)
        try:
            code, payload = self.report()
        finally:
            os.chmod(self.root / "locked", 0o755)
            os.chmod(self.root / "secret.tres", 0o644)
        self.assertEqual(code, 0, payload)
        self.assertEqual(sorted(self.codes(payload, "warnings")), ["dir-unreadable", "file-unreadable"])

    def test_file_names_the_console_cannot_encode(self) -> None:
        self.write("caf\u00e9.gd", 'extends Node\nvar s = load("res://missing.tscn")\n')
        result = subprocess.run(
            [sys.executable, str(CHECKER), str(self.root)],
            check=False, capture_output=True, text=True, encoding="ascii", errors="replace",
            env={**os.environ, "PYTHONIOENCODING": "ascii"},
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("WARNING caf\\xe9.gd:2:", result.stdout)


if __name__ == "__main__":
    unittest.main()
