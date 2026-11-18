"""End-to-end tests for the bevy-video-capture frame checker."""

from __future__ import annotations

import json
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "skills" / "other-engines" / "bevy-video-capture" / "scripts" / "check_frames.py"


def _paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    return b if pb <= pc else c


def _filter_row(kind: int, row: bytes, above: bytes, bpp: int) -> bytes:
    out = bytearray()
    for i, x in enumerate(row):
        a = row[i - bpp] if i >= bpp else 0
        b = above[i]
        c = above[i - bpp] if i >= bpp else 0
        pred = (0, a, b, (a + b) >> 1, _paeth(a, b, c))[kind]
        out.append((x - pred) & 0xFF)
    return bytes(out)


def write_png(path: Path, pixels: list[list[tuple[int, ...]]], filter_kind: int = 0) -> None:
    """Write an 8-bit RGB or RGBA PNG, encoding every row with one PNG filter type."""
    channels = len(pixels[0][0])
    colour = {3: 2, 4: 6}[channels]
    height, width = len(pixels), len(pixels[0])
    above = bytes(width * channels)
    raw = bytearray()
    for row in pixels:
        data = bytes(v for px in row for v in px)
        raw.append(filter_kind)
        raw += _filter_row(filter_kind, data, above, channels)
        above = data

    def chunk(kind: bytes, body: bytes) -> bytes:
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body))

    ihdr = struct.pack(">IIBBBBB", width, height, 8, colour, 0, 0, 0)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
                     + chunk(b"IDAT", zlib.compress(bytes(raw))) + chunk(b"IEND", b""))


def solid(width: int, height: int, colour: tuple[int, ...]) -> list[list[tuple[int, ...]]]:
    return [[colour] * width for _ in range(height)]


def scene(width: int, height: int, step: int) -> list[list[tuple[int, ...]]]:
    """A grey background with a small orange square that moves one pixel per step."""
    rows = solid(width, height, (43, 44, 47))
    for y in range(2, 5):
        for x in range(step, step + 3):
            rows[y][x % width] = (255, 127, 51)
    return rows


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(CHECKER), *args], capture_output=True, text=True)


class CheckFramesTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def frames(self, count: int, size: tuple[int, int] = (16, 8)) -> None:
        for i in range(count):
            write_png(self.dir / f"frame-{i:04d}.png", scene(*size, i), filter_kind=i % 5)

    def test_clean_sequence_passes(self) -> None:
        self.frames(6)
        result = run(str(self.dir), "--expect", "6", "--strict")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Summary: 0 errors, 0 warnings in 6 files checked", result.stdout)

    def test_solid_frames_are_blank_with_every_filter(self) -> None:
        for kind in range(5):
            for colour in ((0, 0, 0), (43, 44, 47), (10, 20, 30, 255)):
                with self.subTest(filter=kind, colour=colour):
                    for old in self.dir.glob("*.png"):
                        old.unlink()
                    write_png(self.dir / "frame-0000.png", scene(16, 8, 0))
                    write_png(self.dir / "frame-0001.png", solid(16, 8, colour), filter_kind=kind)
                    result = run(str(self.dir))
                    self.assertEqual(result.returncode, 1, result.stdout)
                    self.assertIn("1 blank (solid-colour) frames, first at frame 1", result.stdout)

    def test_small_object_on_flat_background_is_not_blank(self) -> None:
        for kind in range(5):
            with self.subTest(filter=kind):
                write_png(self.dir / "frame-0000.png", scene(64, 32, 5), filter_kind=kind)
                result = run(str(self.dir), "--strict")
                self.assertEqual(result.returncode, 0, result.stdout)

    def test_gap_in_numbering_is_an_error(self) -> None:
        self.frames(5)
        (self.dir / "frame-0002.png").unlink()
        result = run(str(self.dir))
        self.assertEqual(result.returncode, 1)
        self.assertIn("frame 2 is missing before this one", result.stdout)

    def test_missing_first_frames_are_an_error(self) -> None:
        self.frames(4)
        (self.dir / "frame-0000.png").unlink()
        result = run(str(self.dir))
        self.assertEqual(result.returncode, 1)
        self.assertIn("numbering starts at 1", result.stdout)

    def test_expect_count_mismatch_is_an_error(self) -> None:
        self.frames(3)
        result = run(str(self.dir), "--expect", "4")
        self.assertEqual(result.returncode, 1)
        self.assertIn("found 3 frames, expected 4", result.stdout)

    def test_size_change_is_an_error(self) -> None:
        self.frames(2)
        write_png(self.dir / "frame-0002.png", scene(32, 8, 2))
        result = run(str(self.dir))
        self.assertEqual(result.returncode, 1)
        self.assertIn("32x8 differs from frame-0000.png (16x8)", result.stdout)

    def test_unreadable_frame_is_an_error(self) -> None:
        self.frames(2)
        (self.dir / "frame-0002.png").write_bytes(b"not a png")
        result = run(str(self.dir))
        self.assertEqual(result.returncode, 1)
        self.assertIn("frame-0002.png: not a PNG file", result.stdout)

    def test_repeated_frame_warns_and_fails_strict(self) -> None:
        self.frames(3)
        # Same pixels and same filter choice, as one encoder writes an unchanged frame.
        write_png(self.dir / "frame-0003.png", scene(16, 8, 2), filter_kind=2)
        result = run(str(self.dir))
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("identical to frame-0002.png; the animation did not advance", result.stdout)
        self.assertEqual(run(str(self.dir), "--strict").returncode, 1)

    def test_last_frame_equal_to_first_warns_about_loop_seam(self) -> None:
        self.frames(4)
        write_png(self.dir / "frame-0004.png", scene(16, 8, 0))
        result = run(str(self.dir))
        self.assertIn("a looping clip will show this pose twice", result.stdout)

    def test_odd_size_warns(self) -> None:
        self.frames(2, size=(15, 8))
        result = run(str(self.dir))
        self.assertEqual(result.returncode, 0)
        self.assertIn("H.264 yuv420p needs even sizes", result.stdout)

    def test_json_report_shape(self) -> None:
        self.frames(3)
        write_png(self.dir / "frame-0003.png", solid(16, 8, (0, 0, 0)))
        result = run(str(self.dir), "--json")
        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout)
        for key in ("tool", "schema", "root", "files_checked", "error_count", "warning_count",
                    "errors", "warnings", "truncated"):
            self.assertIn(key, payload)
        self.assertEqual(payload["tool"], "check_frames")
        self.assertEqual(payload["files_checked"], 4)
        self.assertEqual(payload["errors"][0]["code"], "blank-frames")

    def test_max_issues_truncates_without_changing_totals(self) -> None:
        self.frames(6)
        for i in (1, 3, 5):
            (self.dir / f"frame-{i:04d}.png").unlink()
        result = run(str(self.dir), "--max-issues", "1")  # gaps before frames 2 and 4
        self.assertIn("... and 1 more", result.stdout)
        self.assertIn("Summary: 2 errors", result.stdout)

    def test_usage_errors_exit_2(self) -> None:
        self.assertEqual(run(str(self.dir / "nope")).returncode, 2)
        self.assertEqual(run(str(self.dir)).returncode, 2)  # empty folder
        self.frames(1)
        self.assertEqual(run(str(self.dir), "--pattern", "shot_*.png").returncode, 2)

    def test_help_runs(self) -> None:
        result = run("--help")
        self.assertEqual(result.returncode, 0)
        self.assertIn("FRAMES_DIR", result.stdout)


if __name__ == "__main__":
    unittest.main()
