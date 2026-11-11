"""End-to-end unity-build-size Build Report summarizer."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "unity" / "unity-build-size" / "scripts" / "build_report.py"


def build_report(textures: str, complete: str, assets: list[tuple[str, str, str]]) -> str:
    """A Build Report block in the layout Unity 6 writes to the Editor log."""
    lines = [
        "Build Report",
        "Uncompressed usage by category (Percentages based on user generated assets only):",
        f"Textures               {textures}\t 60.0% ",
        "Meshes                 85.4 mb\t 34.7% ",
        "Sounds                 547.4 kb\t 0.2% ",
        "Total User Assets      246.3 mb\t 100.0% ",
        f"Complete build size    {complete}",
        "Used Assets and files from the Resources folder, sorted by uncompressed size:",
        *(f" {size}\t {percent}% {path}" for size, percent, path in assets),
        "-------------------------------------------------------------------------------",
        "Unloading 1 Unused Serialized files (Serialized files now loaded: 0)",
    ]
    return "\n".join(lines) + "\n"


class BuildReportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.log = Path(self.temp_dir.name) / "Editor.log"
        first = build_report("1.7 gb", "1.9 gb", [("1.6 gb", "84.0", "Assets/Models/room.glb")])
        second = build_report(
            "137.5 mb",
            "340.1 mb",
            [
                ("68.1 mb", "20.0", "Assets/Models/plant.glb"),
                ("22.1 mb", "6.5", "Assets/Models/shelf.glb"),
                ("361.7 kb", "0.1", "Assets/Audio/ring tone.wav"),
            ],
        )
        self.log.write_text("Starting build\n" + first + "Rebuild\n" + second + "Build Finished\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def run_script(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, check=False)

    def test_uses_the_last_report(self) -> None:
        result = self.run_script(str(self.log), "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["complete_bytes"], round(340.1 * 1024**2))
        self.assertEqual(data["asset_count"], 3)
        expected = {"path": "Assets/Models/plant.glb", "bytes": round(68.1 * 1024**2), "percent": 20.0}
        self.assertEqual(data["assets"][0], expected)
        self.assertEqual(data["assets"][2]["path"], "Assets/Audio/ring tone.wav")
        names = [category["name"] for category in data["categories"]]
        self.assertEqual(names, ["Textures", "Meshes", "Sounds"])  # the total is not a category
        self.assertEqual(data["user_assets_bytes"], round(246.3 * 1024**2))
        self.assertFalse(data["over_budget"])
        self.assertFalse(data["budget_checked"])

    def test_text_output_and_top(self) -> None:
        result = self.run_script(str(self.log), "--top", "1")
        self.assertEqual(result.returncode, 0)
        self.assertIn("Complete build size (uncompressed): 340.1 MB", result.stdout)
        self.assertIn("Largest 1 of 3 used assets:", result.stdout)
        self.assertIn("Assets/Models/plant.glb", result.stdout)
        self.assertNotIn("shelf.glb", result.stdout)

    def test_budget(self) -> None:
        over = self.run_script(str(self.log), "--budget-mb", "200")
        self.assertEqual(over.returncode, 1)
        self.assertIn("OVER BUDGET", over.stdout)
        self.assertEqual(self.run_script(str(self.log), "--budget-mb", "400").returncode, 0)

    def test_budget_fails_when_complete_size_is_missing(self) -> None:
        text = self.log.read_text(encoding="utf-8").splitlines(keepends=True)
        self.log.write_text("".join(line for line in text if not line.startswith("Complete build size")), "utf-8")
        result = self.run_script(str(self.log), "--budget-mb", "400", "--json")
        self.assertEqual(result.returncode, 1)
        self.assertIn("budget was not checked", result.stderr)
        data = json.loads(result.stdout)
        self.assertFalse(data["budget_checked"])
        self.assertIsNone(data["complete_bytes"])
        self.assertEqual(self.run_script(str(self.log)).returncode, 0)

    def test_a_later_bare_build_report_line_is_skipped(self) -> None:
        with self.log.open("a", encoding="utf-8") as handle:
            handle.write("Build Report\nRefresh completed\n")
        data = json.loads(self.run_script(str(self.log), "--json").stdout)
        self.assertEqual(data["complete_bytes"], round(340.1 * 1024**2))
        self.assertEqual(data["asset_count"], 3)

    def test_old_complete_size_layout_is_read(self) -> None:
        self.log.write_text(
            "Build Report\nTextures   137.5 mb\t 60.0% \nComplete size   220.6 mb\t 100.0% \n"
            "Used Assets and files from the Resources folder, sorted by uncompressed size:\n"
            " 68.1 mb\t 20.0% Assets/Models/plant.glb\n" + "-" * 40 + "\n",
            encoding="utf-8",
        )
        result = self.run_script(str(self.log), "--budget-mb", "200", "--json")
        self.assertEqual(result.returncode, 1, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["complete_bytes"], round(220.6 * 1024**2))
        self.assertTrue(data["over_budget"])
        self.assertEqual([category["name"] for category in data["categories"]], ["Textures"])

    def test_other_log_lines_inside_the_asset_list_are_skipped(self) -> None:
        text = self.log.read_text(encoding="utf-8").replace(
            " 22.1 mb\t 6.5% Assets/Models/shelf.glb\n",
            "[Licensing::Client] Successfully resolved entitlements\n 22.1 mb\t 6.5% Assets/Models/shelf.glb\n",
        )
        self.log.write_text(text, encoding="utf-8")
        data = json.loads(self.run_script(str(self.log), "--json").stdout)
        self.assertEqual(data["asset_count"], 3)

    def test_log_without_report(self) -> None:
        empty = Path(self.temp_dir.name) / "empty.log"
        empty.write_text("Refresh completed\n", encoding="utf-8")
        result = self.run_script(str(empty))
        self.assertEqual(result.returncode, 1)
        self.assertIn("no 'Build Report' block", result.stderr)

    def test_missing_log_and_bad_arguments(self) -> None:
        self.assertEqual(self.run_script(str(Path(self.temp_dir.name) / "nope.log")).returncode, 2)
        self.assertEqual(self.run_script(str(self.log), "--top", "-1").returncode, 2)
        self.assertEqual(self.run_script(str(self.log), "--budget-mb", "0").returncode, 2)

    def test_help(self) -> None:
        result = self.run_script("--help")
        self.assertEqual(result.returncode, 0)
        self.assertIn("--budget-mb", result.stdout)


if __name__ == "__main__":
    unittest.main()
