"""End-to-end tests for the genre helper scripts (platformer jump_tuner, tower-defense td_curve_check)."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JUMP = ROOT / "skills/genres/platformer/scripts/jump_tuner.py"
TD = ROOT / "skills/genres/tower-defense/scripts/td_curve_check.py"


def run(script, *args):
    return subprocess.run([sys.executable, str(script), *map(str, args)],
                          capture_output=True, text=True, timeout=60)


def write_log(path, height, apex_time, tick=60, fall_mult=1.8, y_start=100.0):
    """Record a jump the way a y-down engine would: velocity += g*dt, then move."""
    gravity = 2 * height / apex_time ** 2
    vy, y, t, dt = -2 * height / apex_time, y_start, 0.0, 1 / tick
    lines = ["t,y", f"{t:.5f},{y:.5f}"]
    while True:
        vy += (gravity if vy < 0 else gravity * fall_mult) * dt
        y += vy * dt
        t += dt
        lines.append(f"{t:.5f},{y:.5f}")
        if y >= y_start:
            break
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


class JumpTunerTests(unittest.TestCase):
    def test_derives_gravity_and_speed_from_height_and_time(self):
        result = run(JUMP, "--height", 3.5, "--apex-time", 0.35, "--tile", 16, "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["tool"], "jump_tuner")
        self.assertAlmostEqual(data["derived"]["rise_gravity"], 2 * 56 / 0.35 ** 2, places=6)
        self.assertAlmostEqual(data["derived"]["jump_speed"], 320.0, places=6)
        # Semi-implicit Euler at 60 Hz peaks short by about v0*dt/2 (2.67 of 56 units).
        self.assertAlmostEqual(data["simulated"]["apex"], 56 - 320 / 120, delta=0.05)

    def test_half_step_hits_the_designed_apex(self):
        data = json.loads(run(JUMP, "--integrator", "half", "--json").stdout)
        self.assertLess(abs(data["simulated"]["apex_error"]), 1e-6)
        self.assertEqual(data["warnings"], [])

    def test_float_countdown_loses_a_tick_at_50_hz(self):
        data = json.loads(run(JUMP, "--tick", 50, "--coyote", 0.1, "--json").stdout)
        self.assertEqual(data["simulated"]["coyote_ticks"], 4)
        self.assertEqual(data["simulated"]["coyote_ticks_rounded"], 5)
        self.assertTrue(any("whole ticks" in w for w in data["warnings"]))

    def test_strict_fails_on_out_of_range_grace(self):
        result = run(JUMP, "--integrator", "half", "--coyote", 0.3, "--strict")
        self.assertEqual(result.returncode, 1)
        self.assertIn("coyote time", result.stdout)

    def test_log_matching_the_design_passes_and_a_wrong_one_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "jump.csv"
            write_log(log, height=56, apex_time=0.35)
            ok = run(JUMP, "--log", log)
            self.assertEqual(ok.returncode, 0, ok.stdout + ok.stderr)
            self.assertIn("-> OK", ok.stdout)
            wrong = run(JUMP, "--log", log, "--height", 4.5)
            self.assertEqual(wrong.returncode, 1)
            self.assertIn("ERROR: apex height", wrong.stdout)

    def test_bad_input_exits_2(self):
        self.assertEqual(run(JUMP, "--height", -1).returncode, 2)
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(run(JUMP, "--log", Path(tmp) / "missing.csv").returncode, 2)
            bad = Path(tmp) / "bad.csv"
            bad.write_text("time,height\n0,1\n", encoding="utf-8")
            self.assertEqual(run(JUMP, "--log", bad).returncode, 2)


def td_spec(hp_growth, bounty_growth=1.1, hp=40, start_gold=300):
    return {"start_gold": start_gold, "tower": {"cost": 100, "dps": 20}, "kill_zone": 12,
            "wave_gen": {"waves": 30, "hp": hp, "hp_growth": hp_growth, "count": 8,
                         "count_step": 1, "speed": 2.0, "spacing": 0.8, "bounty": 6,
                         "bounty_growth": bounty_growth, "clear_bonus": 30,
                         "clear_bonus_step": 5}}


class TdCurveCheckTests(unittest.TestCase):
    def check(self, spec, *args):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "spec.json"
            path.write_text(json.dumps(spec), encoding="utf-8")
            return run(TD, path, *args)

    def test_matched_curves_pass(self):
        result = self.check(td_spec(1.15), "--json", "--strict")
        self.assertEqual(result.returncode, 0, result.stdout)
        data = json.loads(result.stdout)
        self.assertEqual(data["error_count"], 0)
        self.assertEqual(len(data["waves"]), 30)
        self.assertTrue(all(w["pressure"] <= 1.0 for w in data["waves"]))

    def test_hp_outrunning_income_is_a_wall(self):
        result = self.check(td_spec(1.25))
        self.assertEqual(result.returncode, 1)
        self.assertIn("WALL", result.stdout)
        self.assertIn("ERROR: wave", result.stdout)

    def test_income_outrunning_hp_warns(self):
        spec = td_spec(1.12, bounty_growth=1.12, hp=30)
        loose = self.check(spec)
        self.assertEqual(loose.returncode, 0)
        self.assertIn("WARNING", loose.stdout)
        self.assertEqual(self.check(spec, "--strict").returncode, 1)

    def test_explicit_waves_with_groups_and_armor(self):
        spec = {"start_gold": 200, "tower": {"cost": 100, "dps": 20}, "kill_zone": 10,
                "waves": [{"groups": [{"hp": 20, "count": 5, "speed": 2, "spacing": 1,
                                       "bounty": 5},
                                      {"hp": 30, "count": 2, "speed": 1, "spacing": 2,
                                       "bounty": 10, "armor": 0.5}],
                           "clear_bonus": 20}]}
        data = json.loads(self.check(spec, "--json").stdout)
        wave = data["waves"][0]
        # Armored group: 60 effective HP over a 10 s crossing sets the burst need of 6 DPS.
        self.assertAlmostEqual(wave["burst_dps"], 6.0, places=6)
        self.assertAlmostEqual(wave["sustained_dps"], (100 + 120) / (5 + 4 - 2 + 10), places=6)

    def test_invalid_specs_exit_2(self):
        self.assertEqual(self.check({"tower": {"cost": 100}}).returncode, 2)
        self.assertEqual(self.check(td_spec(1.1) | {"efficiency": 2}).returncode, 2)
        self.assertEqual(run(TD, ROOT / "no-such-spec.json").returncode, 2)


if __name__ == "__main__":
    unittest.main()
