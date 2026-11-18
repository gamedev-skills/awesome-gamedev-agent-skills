#!/usr/bin/env python3
"""Check a folder of recorded PNG frames before encoding them. Read-only.

Run it after a frame-by-frame capture (for example a Bevy recorder that saves
``frame-0000.png``, ``frame-0001.png`` ...) and before turning the frames into
a GIF, WebP or MP4. It catches the failures that are easy to miss by looking
at one or two frames: missing frames, blank frames, size changes and a clock
that did not advance. It needs only the Python standard library.

What it checks:

* Numbering: frames are found by ``--pattern`` (default ``frame-*.png``); the
  number in each name must run 0, 1, 2 ... with no gaps. With ``--expect N``
  the folder must hold exactly N frames.
* Readable PNG: each file must be a PNG with an IHDR chunk and image data that
  decompresses.
* One size: every frame must match the first frame's width and height.
* Blank frames: a frame where every pixel has the same colour (often all
  black). Screen captures return these when the window stopped presenting or
  the GPU readback failed. Checked exactly for non-interlaced 8- and 16-bit
  PNGs. Error.
* Stalled clock: two neighbouring frames with byte-identical image data mean
  the animation did not advance between captures. The comparison uses the PNG's
  stored (filtered) data, which one encoder writes identically for identical
  frames. Warning.
* Loop seam: when the last frame equals the first, a looping clip shows that
  pose twice. Warning.
* Odd width or height: H.264 with yuv420p needs even dimensions. Warning.

Exit codes: 0 no errors, 1 errors (or warnings with --strict),
2 usage problem, missing folder or no matching frames.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import sys
import zlib
from dataclasses import dataclass
from pathlib import Path

TOOL = "check_frames"
SCHEMA = 1
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
# Bytes per pixel for 8-bit PNG colour types: grey, RGB, palette, grey+alpha, RGBA.
CHANNELS = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}
NUMBER_RE = re.compile(r"(\d+)(?=\.[^.]+$)")


@dataclass
class Issue:
    severity: str  # "error" or "warning"
    code: str
    file: str
    line: int | None
    message: str
    fix: str

    def as_dict(self) -> dict:
        return {"code": self.code, "file": self.file, "line": self.line, "message": self.message, "fix": self.fix}


@dataclass
class Frame:
    path: Path
    number: int
    width: int = 0
    height: int = 0
    bpp: int = 0
    interlaced: bool = False
    digest: str = ""
    blank: bool = False
    error: str = ""


def read_png(frame: Frame) -> None:
    """Fill size, digest and blank flag from the PNG's IHDR and IDAT chunks."""
    try:
        data = frame.path.read_bytes()
    except OSError as exc:
        frame.error = f"cannot read file ({exc.strerror})"
        return
    if not data.startswith(PNG_SIGNATURE):
        frame.error = "not a PNG file"
        return
    pos = len(PNG_SIGNATURE)
    idat = bytearray()
    while pos + 8 <= len(data):
        length, kind = struct.unpack(">I4s", data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + length]
        if kind == b"IHDR" and length >= 13:
            frame.width, frame.height, depth, colour = struct.unpack(">IIBB", body[:10])
            frame.interlaced = body[12] != 0
            if colour in CHANNELS and depth in (8, 16):
                frame.bpp = CHANNELS[colour] * depth // 8
        elif kind == b"IDAT":
            idat += body
        elif kind == b"IEND":
            break
        pos += 12 + length
    if not frame.width or not idat:
        frame.error = "PNG has no IHDR or no image data"
        return
    try:
        raw = zlib.decompress(bytes(idat))
    except zlib.error:
        frame.error = "PNG image data is truncated or corrupt"
        return
    frame.digest = hashlib.sha1(raw).hexdigest()
    if frame.bpp and not frame.interlaced:
        frame.blank = is_solid_colour(raw, frame.width, frame.height, frame.bpp)


def is_solid_colour(raw: bytes, width: int, height: int, bpp: int) -> bool:
    """True when every pixel has the same value.

    Instead of undoing the PNG filters byte by byte, assume the image is one
    colour, work out the pixel from each row's first bytes, predict what the
    rest of that filtered row must be, and compare. The first row that differs
    proves the frame is not solid, so real frames are rejected quickly.
    """
    row_len = width * bpp
    if len(raw) < height * (row_len + 1) or width < 1:
        return False
    above = [0] * bpp  # previous row's pixel; the row above the image is zeros
    colour = None
    for y in range(height):
        start = y * (row_len + 1)
        kind = raw[start]
        first = raw[start + 1:start + 1 + bpp]
        rest = raw[start + 1 + bpp:start + 1 + row_len]
        if kind in (0, 1):  # None, Sub: first pixel is stored as is
            pixel = list(first)
        elif kind == 2:  # Up
            pixel = [(f + a) & 0xFF for f, a in zip(first, above)]
        elif kind == 3:  # Average with left = 0
            pixel = [(f + (a >> 1)) & 0xFF for f, a in zip(first, above)]
        elif kind == 4:  # Paeth with left = 0 picks the pixel above
            pixel = [(f + a) & 0xFF for f, a in zip(first, above)]
        else:
            return False
        if kind == 0:
            expected = bytes(pixel)
        elif kind == 2:
            expected = bytes((p - a) & 0xFF for p, a in zip(pixel, above))
        elif kind == 3:
            expected = bytes((p - ((p + a) >> 1)) & 0xFF for p, a in zip(pixel, above))
        else:  # Sub and Paeth predict the identical left pixel exactly
            expected = bytes(bpp)
        if rest != expected * (width - 1):
            return False
        if colour is None:
            colour = pixel
        elif pixel != colour:
            return False
        above = pixel
    return True


def check(folder: Path, pattern: str, expect: int | None) -> tuple[list[Issue], int]:
    issues: list[Issue] = []
    frames: list[Frame] = []
    for path in folder.glob(pattern):
        if not path.is_file():
            continue
        match = NUMBER_RE.search(path.name)
        if not match:
            issues.append(Issue("warning", "unnumbered", path.name, None,
                                "file matches the pattern but has no frame number before the extension",
                                "name frames like frame-0000.png or narrow --pattern"))
            continue
        frames.append(Frame(path, int(match.group(1))))
    frames.sort(key=lambda f: f.number)

    numbers = [f.number for f in frames]
    if numbers and numbers[0] != 0:
        issues.append(Issue("error", "missing-frames", frames[0].path.name, None,
                            f"numbering starts at {numbers[0]}, frames 0-{numbers[0] - 1} are missing",
                            "re-record from frame 0, or resume the recorder at the first missing frame"))
    for prev, cur in zip(frames, frames[1:]):
        if cur.number == prev.number:
            issues.append(Issue("error", "duplicate-number", cur.path.name, None,
                                f"frame number {cur.number} appears twice (also {prev.path.name})",
                                "keep one file per frame number"))
        elif cur.number > prev.number + 1:
            gap = (f"frame {prev.number + 1} is" if cur.number == prev.number + 2
                   else f"frames {prev.number + 1}-{cur.number - 1} are")
            issues.append(Issue("error", "missing-frames", cur.path.name, None,
                                f"{gap} missing before this one",
                                "resume the recorder at the first missing frame and re-check"))
    if expect is not None and len(frames) != expect:
        issues.append(Issue("error", "frame-count", folder.name, None,
                            f"found {len(frames)} frames, expected {expect}",
                            "record loop_seconds x fps frames (the frame at exactly loop_seconds equals frame 0)"))

    for frame in frames:
        read_png(frame)
        if frame.error:
            issues.append(Issue("error", "unreadable", frame.path.name, None, frame.error,
                                "delete it and record that frame again; the capture may have been cut off"))

    good = [f for f in frames if not f.error]
    if good:
        first = good[0]
        for frame in good[1:]:
            if (frame.width, frame.height) != (first.width, first.height):
                issues.append(Issue("error", "size-mismatch", frame.path.name, None,
                                    f"{frame.width}x{frame.height} differs from {first.path.name} "
                                    f"({first.width}x{first.height})",
                                    "keep the window size and scale factor fixed for the whole recording"))
        if first.width % 2 or first.height % 2:
            issues.append(Issue("warning", "odd-size", first.path.name, None,
                                f"{first.width}x{first.height} has an odd side; H.264 yuv420p needs even sizes",
                                "record at an even size, or scale/crop to even dimensions when encoding"))

    blank = [f for f in good if f.blank]
    if blank:
        names = ", ".join(f.path.name for f in blank[:5]) + (" ..." if len(blank) > 5 else "")
        issues.append(Issue("error", "blank-frames", blank[0].path.name, None,
                            f"{len(blank)} blank (solid-colour) frames, first at frame {blank[0].number}: {names}",
                            "keep the capture window visible and on top, then re-record from the first blank frame"))

    for prev, cur in zip(good, good[1:]):
        if cur.number == prev.number + 1 and cur.digest == prev.digest and not cur.blank:
            issues.append(Issue("warning", "stalled-clock", cur.path.name, None,
                                f"identical to {prev.path.name}; the animation did not advance",
                                "advance the animation clock by exactly one frame per capture, not by wall time"))
    if len(good) > 2 and good[-1].digest == good[0].digest and not good[0].blank:
        issues.append(Issue("warning", "loop-seam", good[-1].path.name, None,
                            f"identical to {good[0].path.name}; a looping clip will show this pose twice",
                            "drop the last frame: a loop of L seconds at F fps is L*F frames, 0 to L*F-1"))
    return issues, len(frames)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="check_frames.py",
        description=__doc__.split("\n\n")[0],
        epilog=(
            "examples:\n"
            "  check_frames.py frames\n"
            "  check_frames.py frames --expect 120 --strict\n"
            "  check_frames.py renders --pattern 'shot_*.png' --json\n\n"
            "exit codes: 0 no errors, 1 errors (or warnings with --strict),\n"
            "2 usage problem, missing folder or no matching frames"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("frames_dir", metavar="FRAMES_DIR", help="folder that holds the recorded PNG frames")
    parser.add_argument("--pattern", default="frame-*.png", help="glob for frame files (default: frame-*.png)")
    parser.add_argument("--expect", type=int, metavar="N", help="fail unless exactly N frames are present")
    parser.add_argument("--json", action="store_true", help="print one JSON object instead of text")
    parser.add_argument("--strict", action="store_true", help="exit 1 when there are warnings too")
    parser.add_argument("--max-issues", type=int, default=50, metavar="N",
                        help="print at most N issues, errors first (default: 50; 0 = no limit)")
    return parser


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="backslashreplace")
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.max_issues < 0:
        parser.error("--max-issues must be 0 or more")
    if args.expect is not None and args.expect < 1:
        parser.error("--expect must be 1 or more")
    root = Path(args.frames_dir).expanduser()
    if not root.is_dir():
        print(f"error: {args.frames_dir} is not a folder", file=sys.stderr)
        return 2
    if not any(p.is_file() for p in root.glob(args.pattern)):
        print(f"error: no files matching {args.pattern} in {args.frames_dir}", file=sys.stderr)
        return 2
    root = root.resolve()
    issues, frame_count = check(root, args.pattern, args.expect)

    def sort_key(issue: Issue) -> tuple:
        return (issue.file, issue.code, issue.message)

    errors = sorted((i for i in issues if i.severity == "error"), key=sort_key)
    warnings = sorted((i for i in issues if i.severity == "warning"), key=sort_key)
    ordered = errors + warnings
    shown = ordered[: args.max_issues] if args.max_issues else ordered
    truncated = len(ordered) > len(shown)

    if args.json:
        payload = {
            "tool": TOOL,
            "schema": SCHEMA,
            "root": root.as_posix(),
            "files_checked": frame_count,
            "error_count": len(errors),
            "warning_count": len(warnings),
            "errors": [i.as_dict() for i in shown if i.severity == "error"],
            "warnings": [i.as_dict() for i in shown if i.severity == "warning"],
            "truncated": truncated,
        }
        print(json.dumps(payload, indent=2))
    else:
        for issue in shown:
            print(f"{issue.severity.upper()} {issue.file}: {issue.message}")
            print(f"  fix: {issue.fix}")
        if truncated:
            print(f"... and {len(ordered) - len(shown)} more")
        print(f"Summary: {len(errors)} errors, {len(warnings)} warnings in {frame_count} files checked")

    if errors or (args.strict and warnings):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
