"""Run the published Python generators and dialogue graph against their contracts."""
import json
import random
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DISCIPLINES = ROOT / "skills/disciplines"


def python_blocks(path):
    return re.findall(r"```python\n(.*?)```", path.read_text(encoding="utf-8"), re.S)


class DungeonExamplesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = DISCIPLINES / "procedural-gen/references/dungeon-generation.md"
        # The other recipes intentionally leave rendering/room helpers to the engine.
        cls.code = {}
        for block in python_blocks(path):
            if any(marker in block for marker in ("def drunkard(", "def wfc(", "def reachable_floor(")):
                exec(compile(block, str(path), "exec"), cls.code)

    def test_impossible_and_invalid_walks_fail_immediately(self):
        for width, height, ratio in [(4, 4, .45), (3, 3, 1), (2, 8, .2),
                                     (8, 2, .2), (8, 8, -.1), (8, 8, 1.1)]:
            with self.subTest(width=width, height=height, ratio=ratio):
                with self.assertRaises(ValueError):
                    self.code["drunkard"](width, height, random.Random(6), ratio)

    def test_walk_density_seed_border_and_cardinal_connectivity(self):
        walk = self.code["drunkard"]
        for seed in range(12):
            with self.subTest(seed=seed):
                grid = walk(10, 10, random.Random(seed))
                self.assertEqual(sum(map(sum, grid)), 45)
                self.assertEqual(len(self.code["reachable_floor"](grid, (5, 5))), 45)
                self.assertEqual(grid, walk(10, 10, random.Random(seed)))
                self.assertFalse(any(grid[0]) or any(grid[-1]))
                self.assertTrue(all(row[0] == row[-1] == 0 for row in grid))

    def test_walk_budget_and_small_valid_targets(self):
        walk = self.code["drunkard"]
        self.assertEqual(sum(map(sum, walk(3, 3, random.Random(1), 0))), 0)
        self.assertEqual(sum(map(sum, walk(3, 3, random.Random(1), 1/9))), 1)
        self.assertEqual(sum(map(sum, walk(4, 4, random.Random(1), .25))), 4)
        with self.assertRaises(RuntimeError):
            walk(10, 10, random.Random(1), max_steps=1)
        with self.assertRaises(ValueError):
            walk(10, 10, random.Random(1), max_steps=-1)

    def test_wfc_rejects_an_impossible_singleton_domain(self):
        allowed = {("A", d): set() for d in range(4)}
        with self.assertRaises(RuntimeError):
            self.code["wfc"](2, 1, {"A": 1}, allowed, random.Random(2), max_restarts=2)
        # With no neighbour there is no forbidden edge to violate.
        self.assertEqual(self.code["wfc"](1, 1, {"A": 1}, allowed, random.Random(2)), [["A"]])

    def test_wfc_accepts_legal_singletons_and_enforces_every_edge(self):
        wfc = self.code["wfc"]
        allowed = {("A", d): {"A"} for d in range(4)}
        self.assertEqual(wfc(2, 1, {"A": 1}, allowed, random.Random(2)), [["A", "A"]])
        allowed = {(tile, d): ({"B"} if tile == "A" else {"A"})
                   for tile in ("A", "B") for d in range(4)}
        for seed in range(5):
            grid = wfc(6, 4, {"A": 1, "B": 2}, allowed, random.Random(seed))
            for y, row in enumerate(grid):
                for x, tile in enumerate(row):
                    for d, (dx, dy) in enumerate(self.code["DIRS"]):
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < 6 and 0 <= ny < 4:
                            self.assertIn(grid[ny][nx], allowed[(tile, d)])


class DialogueExamplesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = DISCIPLINES / "dialogue-systems/SKILL.md"
        cls.graph = json.loads(re.search(r"```json\n(.*?)```", path.read_text(encoding="utf-8"), re.S)[1])
        cls.code = {}
        for block in python_blocks(DISCIPLINES / "dialogue-systems/references/runner.md"):
            exec(compile(block, "runner.md", "exec"), cls.code)

    def runner(self, gold=None):
        class UI:
            closed = False

            def show_line(self, speaker, text):
                self.line = (speaker, text)

            def show_choices(self, choices):
                self.choices = choices

            def show_continue(self, callback):
                self.advance = callback

            def close(self):
                self.closed = True

        ui = UI()
        runner = self.code["DialogueRunner"](self.graph, ui, lambda key: key)
        if gold is not None:
            runner.vars["gold"] = gold
        runner.start()
        return runner, ui

    def test_published_graph_starts_with_declared_variables(self):
        runner, ui = self.runner()
        self.assertEqual(runner.vars, {"gold": 0, "gate_open": False})
        self.assertEqual([choice["text"] for choice in ui.choices], ["DLG_OPT_LEAVE"])
        runner.choose(ui.choices[0])
        self.assertTrue(ui.closed)

    def test_bribe_gate_cost_and_completion(self):
        for gold in (0, 49, 50, 100):
            with self.subTest(gold=gold):
                runner, ui = self.runner(gold)
                bribes = [choice for choice in ui.choices if choice["to"] == "bribe"]
                self.assertEqual(bool(bribes), gold >= 50)
                if bribes:
                    runner.choose(bribes[0])
                    self.assertEqual(runner.vars["gold"], gold - 50)
                    self.assertTrue(runner.vars["gate_open"])
                    ui.advance()
                    self.assertTrue(ui.closed)

if __name__ == "__main__":
    unittest.main()
