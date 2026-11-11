"""Regression tests for documentation output ownership and safe rebuilding."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "generate-site.py"
SPEC = importlib.util.spec_from_file_location("generate_site", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
generate_site = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(generate_site)


class GenerateSiteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name).resolve()
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.out = self.root / "site"
        self.root_patch = patch.object(generate_site, "REPO_ROOT", self.repo)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)
        self.write_skill()

    def write_skill(self, category: str = "disciplines") -> None:
        skill = self.repo / "skills" / category / "test-skill" / "SKILL.md"
        skill.parent.mkdir(parents=True, exist_ok=True)
        skill.write_text(
            "---\nname: test-skill\ndescription: A test skill.\n---\n\n# Test skill\n",
            encoding="utf-8",
        )

    def run_generator(self, *args: str) -> tuple[int, str]:
        output = io.StringIO()
        with patch("sys.argv", [str(SCRIPT), "--out", str(self.out), *args]), \
                contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            code = generate_site.main()
        return code, output.getvalue()

    def marker(self) -> Path:
        return self.out / generate_site.OUTPUT_MARKER

    def test_new_and_empty_output_generate_site(self) -> None:
        for name, create in (("new", False), ("empty", True)):
            with self.subTest(name=name):
                self.out = self.root / name
                if create:
                    self.out.mkdir()
                code, output = self.run_generator()
                self.assertEqual(code, 0, output)
                self.assertEqual(self.marker().read_text(), generate_site.OUTPUT_MARKER_CONTENT)
                self.assertTrue((self.out / "disciplines/test-skill/index.html").is_file())
                self.assertTrue((self.out / "sitemap.xml").is_file())

    def test_non_empty_unmarked_output_is_never_cleaned(self) -> None:
        self.out.mkdir()
        sentinel = self.out / "keep.txt"
        sentinel.write_text("user data", encoding="utf-8")
        for args in ((), ("--clean",)):
            with self.subTest(args=args):
                code, _ = self.run_generator(*args)
                self.assertEqual(code, 1)
                self.assertEqual(sentinel.read_text(), "user data")
                self.assertFalse(self.marker().exists())

    def test_marker_requires_explicit_clean_and_correct_content(self) -> None:
        self.assertEqual(self.run_generator()[0], 0)
        sentinel = self.out / "stale.html"
        sentinel.write_text("old generated page", encoding="utf-8")
        self.assertEqual(self.run_generator()[0], 1)
        self.assertTrue(sentinel.exists())
        self.marker().write_text("wrong generator", encoding="utf-8")
        self.assertEqual(self.run_generator("--clean")[0], 1)
        self.assertTrue(sentinel.exists())
        self.marker().write_text(generate_site.OUTPUT_MARKER_CONTENT, encoding="utf-8")
        code, output = self.run_generator("--clean")
        self.assertEqual(code, 0, output)
        self.assertFalse(sentinel.exists())
        self.assertTrue((self.out / "index.html").is_file())

    def test_invalid_sources_leave_existing_output_untouched(self) -> None:
        self.assertEqual(self.run_generator()[0], 0)
        sentinel = self.out / "keep.txt"
        sentinel.write_text("keep", encoding="utf-8")
        with patch.object(generate_site, "collect_skills", return_value=[]):
            self.assertEqual(self.run_generator("--clean")[0], 1)
        self.assertEqual(sentinel.read_text(), "keep")
        self.write_skill("unsupported-category")
        self.assertEqual(self.run_generator("--clean")[0], 1)
        self.assertEqual(sentinel.read_text(), "keep")

    def test_protected_output_paths_are_rejected_before_writing(self) -> None:
        for out in (self.repo, self.root, Path(self.repo.anchor)):
            with self.subTest(out=out):
                with self.assertRaises(ValueError):
                    generate_site.prepare_output(out, clean=True)
        self.assertTrue((self.repo / "skills").is_dir())

    def test_file_output_is_preserved(self) -> None:
        self.out.write_text("keep", encoding="utf-8")
        self.assertEqual(self.run_generator("--clean")[0], 1)
        self.assertEqual(self.out.read_text(), "keep")

    def test_symlink_output_and_marker_are_rejected(self) -> None:
        target = self.root / "target"
        target.mkdir()
        sentinel = target / "keep.txt"
        sentinel.write_text("keep", encoding="utf-8")
        try:
            self.out.symlink_to(target, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlink creation unavailable")
        self.assertEqual(self.run_generator("--clean")[0], 1)
        self.assertEqual(sentinel.read_text(), "keep")
        self.out.unlink()
        self.out.mkdir()
        outside_marker = self.root / "outside-marker"
        outside_marker.write_text(generate_site.OUTPUT_MARKER_CONTENT, encoding="utf-8")
        self.marker().symlink_to(outside_marker)
        self.assertEqual(self.run_generator("--clean")[0], 1)
        self.assertTrue(self.marker().is_symlink())

    def test_failed_generation_can_be_retried_with_clean(self) -> None:
        with patch.object(generate_site, "build_index", side_effect=RuntimeError("render failed")):
            with self.assertRaisesRegex(RuntimeError, "render failed"):
                self.run_generator()
        self.assertEqual(self.marker().read_text(), generate_site.OUTPUT_MARKER_CONTENT)
        self.assertEqual(self.run_generator("--clean")[0], 0)


if __name__ == "__main__":
    unittest.main()
