"""Run published GDScript examples in Godot."""
import os
import re
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENGINE = os.environ.get("GODOT_BIN") or shutil.which("godot") or shutil.which("godot4")
if not ENGINE and Path("/Applications/Godot.app/Contents/MacOS/Godot").is_file():
    ENGINE = "/Applications/Godot.app/Contents/MacOS/Godot"


def snippet(path, heading, language="gdscript"):
    section = (ROOT / path).read_text(encoding="utf-8").split(heading, 1)[1]
    match = re.search(r"```" + language + r"\n(.*?)```", section, re.S)
    if not match:
        raise AssertionError(f"Missing {language} example after {heading} in {path}")
    return match.group(1)


class GodotDiagnosticError(AssertionError):
    """A completed, successful process still emitted engine/script errors."""


@unittest.skipUnless(ENGINE, "Godot required; set GODOT_BIN to run GDScript examples")
class GodotExamplesTests(unittest.TestCase):
    def run_godot(self, files, body, timeout=20, complete=True):
        """Use an isolated project; Godot can exit zero after a script/runtime error."""
        runner = "extends SceneTree\n\nfunc _initialize():\n    call_deferred(\"_run\")\n\nfunc _run():\n"
        runner += textwrap.indent(textwrap.dedent(body).strip() + "\n", "    ")
        if complete:
            runner += '    print("GODOT_EXAMPLES_COMPLETE")\n    quit(0)\n'
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            (project / "project.godot").write_text(
                'config_version=5\n[application]\nconfig/name="Example tests"\n'
                '[rendering]\nrenderer/rendering_method="gl_compatibility"\n',
                encoding="utf-8",
            )
            for name, source in {**files, "runner.gd": runner}.items():
                target = project / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(source, encoding="utf-8")
            try:
                result = subprocess.run(
                    [ENGINE, "--headless", "--path", directory, "--log-file",
                     str(project / "godot.log"), "--script", "runner.gd"],
                    capture_output=True, text=True, timeout=timeout,
                )
            except subprocess.TimeoutExpired as error:
                self.fail(f"Godot timed out after {timeout}s: {error.stdout!r} {error.stderr!r}")
        output = result.stdout + result.stderr
        self.assertEqual(result.returncode, 0, output)
        self.assertIn("GODOT_EXAMPLES_COMPLETE", result.stdout, output)
        if re.search(r"(?im)^\s*(?:SCRIPT ERROR:|ERROR:|Parse Error:)", output):
            raise GodotDiagnosticError(output)

    def test_root_and_named_child_animation_parameters(self):
        source = snippet("skills/godot/godot-animation/SKILL.md", "### 3. Blend space")
        self.run_godot({"example.gd": "extends Node\nvar tree: AnimationTree\n" + source}, """
            var example = load("res://example.gd").new()
            root.add_child(example)
            var tree = AnimationTree.new()
            example.tree = tree
            example.add_child(tree)
            tree.tree_root = AnimationNodeBlendSpace2D.new()
            example.update_locomotion(Vector2(0.25, -0.5))
            assert(tree.get("parameters/blend_position") == Vector2(0.25, -0.5))
            var nested = AnimationNodeBlendTree.new()
            nested.add_node("Move", AnimationNodeBlendSpace2D.new())
            tree.tree_root = nested
            tree.set("parameters/Move/blend_position", Vector2(-0.75, 0.5))
            assert(tree.get("parameters/Move/blend_position") == Vector2(-0.75, 0.5))
            example.free()
        """)

    def test_spawn_preserves_world_position_and_ready_initial_state(self):
        source = snippet("skills/godot/godot-nodes-scenes/SKILL.md", "### 1. Instance a scene")
        self.run_godot({
            "spawner.gd": source,
            "bullet.gd": textwrap.dedent("""\
                extends Node2D
                var direction: Vector2
                var ready_position: Vector2
                var ready_direction: Vector2
                func _ready():
                    ready_position = global_position
                    ready_direction = direction
            """),
            "bullet.tscn": '[gd_scene load_steps=2 format=3]\n'
                           '[ext_resource type="Script" path="res://bullet.gd" id="1"]\n'
                           '[node name="Bullet" type="Node2D"]\nscript = ExtResource("1")\n',
        }, """
            for transform in [Transform2D.IDENTITY,
                    Transform2D(0.0, Vector2.ONE, 0.0, Vector2(100, -30)),
                    Transform2D(0.7, Vector2(2, 0.5), 0.0, Vector2(100, -30))]:
                var spawner = load("res://spawner.gd").new()
                root.add_child(spawner)
                spawner.transform = transform
                var target = Vector2(10, 20)
                spawner.shoot(target, Vector2.LEFT)
                var bullet = spawner.get_child(0)
                assert(bullet.global_position.is_equal_approx(target))
                assert(bullet.ready_position.is_equal_approx(target))
                assert(bullet.ready_direction == Vector2.LEFT)
                spawner.free()
        """)

    def test_hud_initial_sync_signal_updates_and_empty_health_range(self):
        source = snippet("skills/disciplines/game-ui-ux/SKILL.md", "### 5. Event-driven HUD")
        self.run_godot({
            "hud.gd": "extends Node\nvar player\n" + source,
            "player.gd": "extends Node\nsignal health_changed(current, max_health)\n"
                         "var hp = 100\nvar max_hp = 100\n",
        }, """
            var player = load("res://player.gd").new()
            root.add_child(player)
            var hud = load("res://hud.gd").new()
            var bar = ProgressBar.new()
            bar.name = "HealthBar"
            hud.add_child(bar)
            hud.player = player
            root.add_child(hud)
            assert(is_equal_approx(bar.value, 100.0))
            for sample in [[50, 100, 0.5], [0, 100, 0.0], [100, 100, 1.0],
                    [5, 0, 0.0], [5, -10, 0.0], [200, 100, 1.0], [-5, 100, 0.0]]:
                player.health_changed.emit(sample[0], sample[1])
                assert(is_equal_approx(bar.ratio, sample[2]))
            hud.free()
            player.free()
        """)

    def test_level_reachability_tracks_keys_on_one_directed_path(self):
        source = snippet("skills/disciplines/level-design/SKILL.md", "### 3. Gating")
        self.run_godot({"level.gd": "extends Node\n" + source}, """
            var level = load("res://level.gd").new()
            assert(not level.goal_reachable(level.ROOMS, "entry", "boss"))
            var rooms = {
                "entry": {"exits": [{"to": "key"}, {"to": "goal", "needs": "red"}]},
                "key": {"grants": "red", "exits": []},
                "goal": {"exits": []},
            }
            assert(not level.goal_reachable(rooms, "entry", "goal"))
            rooms["key"]["exits"] = [{"to": "entry"}]
            assert(level.goal_reachable(rooms, "entry", "goal"))
            rooms["goal"] = {"exits": [{"to": "end", "needs": "blue"}]}
            assert(not level.goal_reachable(rooms, "entry", "end"))
            rooms["goal"]["grants"] = "blue"
            assert(level.goal_reachable(rooms, "entry", "end"))
            assert(level.goal_reachable(rooms, "entry", "entry"))
            assert(not level.goal_reachable(rooms, "entry", "missing"))
            level.free()
        """)

    def test_deadzone_zero_and_radial_response(self):
        source = snippet("skills/disciplines/input-systems/SKILL.md", "### 2. Analog deadzone")
        self.run_godot({"input.gd": "extends Node\n" + source}, """
            var input = load("res://input.gd").new()
            assert(input.apply_deadzone(Vector2.ZERO, 0.0) == Vector2.ZERO)
            assert(input.apply_deadzone(Vector2(0.2, 0), 0.2).is_zero_approx())
            assert(input.apply_deadzone(Vector2(0.1, 0), 0.2) == Vector2.ZERO)
            assert(input.apply_deadzone(Vector2(0.6, 0), 0.2).is_equal_approx(Vector2(0.5, 0)))
            assert(input.apply_deadzone(Vector2(0.6, 0), 0.2, 2.0).is_equal_approx(Vector2(0.25, 0)))
            var diagonal = input.apply_deadzone(Vector2.ONE)
            assert(diagonal.is_equal_approx(Vector2.ONE.normalized()))
            input.free()
        """)

    def test_deadzone_invalid_settings_report_errors_and_stop_movement(self):
        source = snippet("skills/disciplines/input-systems/SKILL.md", "### 2. Analog deadzone")
        # The harness still rejects ERROR output after every result and the completion marker.
        with self.assertRaisesRegex(GodotDiagnosticError, "apply_deadzone requires"):
            self.run_godot({"input.gd": "extends Node\n" + source}, """
                var input = load("res://input.gd").new()
                for settings in [[1.0, 1.0], [-0.1, 1.0], [1.1, 1.0], [0.2, 0.0], [0.2, -1.0]]:
                    var value = input.apply_deadzone(Vector2.RIGHT, settings[0], settings[1])
                    assert(value.is_finite() and value == Vector2.ZERO)
                input.free()
            """)

    def test_audio_preroll_first_beat_and_strict_next_boundary(self):
        source = snippet("skills/disciplines/audio-design/SKILL.md", "### 4. Beat-synced events")
        self.run_godot({
            "audio.gd": "extends Node\n" + source,
            # Override the clock, not the published quantization functions.
            "clock.gd": 'extends "res://audio.gd"\nvar time = 0.0\n'
                        'func song_time() -> float:\n    return time\n',
        }, """
            var audio = load("res://clock.gd").new()
            for sample in [[-0.1, 0.1, -1], [-0.6, 0.6, -2], [0.0, 0.5, 0],
                    [0.1, 0.4, 0], [0.5, 0.5, 1], [0.75, 0.25, 1]]:
                audio.time = sample[0]
                assert(is_equal_approx(audio.time_until_next_beat(), sample[1]))
                assert(audio.current_beat() == sample[2])
            audio.free()
        """)

    def test_harness_requires_completion_marker(self):
        with self.assertRaisesRegex(AssertionError, "GODOT_EXAMPLES_COMPLETE"):
            self.run_godot({}, "quit(0)", complete=False)

    def test_harness_bounds_a_stalled_script(self):
        with self.assertRaisesRegex(AssertionError, "timed out"):
            self.run_godot({}, "while true:\n    pass", timeout=0.5)


if __name__ == "__main__":
    unittest.main()
