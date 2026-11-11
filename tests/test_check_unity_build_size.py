"""End-to-end unity-build-size project checker."""

from __future__ import annotations

import base64
import json
import os
import shlex
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "skills" / "unity" / "unity-build-size" / "scripts" / "check_unity_build_size.py"

MIB = 1024 * 1024
GLTFAST_MANIFEST = {"dependencies": {"com.unity.cloud.gltfast": "6.20.0"}}


def png(width: int, height: int) -> bytes:
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    chunk = b"IHDR" + ihdr
    return (
        b"\x89PNG\r\n\x1a\n"
        + struct.pack(">I", len(ihdr))
        + chunk
        + struct.pack(">I", zlib.crc32(chunk))
        + b"\x00\x00\x00\x00IEND\xaeB`\x82"
    )


def jpeg(width: int, height: int) -> bytes:
    app0 = b"\xff\xe0" + struct.pack(">H", 16) + b"JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    sof0 = b"\xff\xc0" + struct.pack(">HBHHB", 17, 8, height, width, 3) + b"\x01\x11\x00\x02\x11\x01\x03\x11\x01"
    return b"\xff\xd8" + app0 + sof0 + b"\xff\xd9"


def glb(images: list[bytes], geometry_bytes: int = 0) -> bytes:
    """A GLB whose BIN chunk holds the images; geometry is only declared in buffer.byteLength."""
    blob = b""
    views = []
    for image in images:
        views.append({"buffer": 0, "byteOffset": len(blob), "byteLength": len(image)})
        blob += image + b"\x00" * (-len(image) % 4)
    gltf = {
        "asset": {"version": "2.0"},
        "buffers": [{"byteLength": len(blob) + geometry_bytes}],
        "bufferViews": views,
        "images": [{"bufferView": index, "mimeType": "image/png"} for index in range(len(images))],
    }
    text = json.dumps(gltf).encode()
    text += b" " * (-len(text) % 4)
    body = struct.pack("<II", len(text), 0x4E4F534A) + text + struct.pack("<II", len(blob), 0x004E4942) + blob
    return struct.pack("<III", 0x46546C67, 2, 12 + len(body)) + body


def texture_meta(default_compression: int = 1, default_max: int = 2048, override: dict | None = None) -> str:
    def entry(target: str, max_size: int, compression: int, overridden: int, texture_format: int = -1) -> str:
        return (
            "  - serializedVersion: 4\n"
            f"    buildTarget: {target}\n"
            f"    maxTextureSize: {max_size}\n"
            "    resizeAlgorithm: 0\n"
            f"    textureFormat: {texture_format}\n"
            f"    textureCompression: {compression}\n"
            "    compressionQuality: 50\n"
            f"    overridden: {overridden}\n"
        )

    standalone = override or {"max": default_max, "compression": default_compression, "overridden": 0}
    return (
        "fileFormatVersion: 2\nguid: 79ac4b6a10a8f0f4cb6af61beea5cc9e\nTextureImporter:\n"
        "  serializedVersion: 13\n  isReadable: 0\n"
        f"  maxTextureSize: {default_max}\n"
        "  platformSettings:\n"
        + entry("DefaultTexturePlatform", default_max, default_compression, 0)
        + entry(
            "Standalone",
            standalone["max"],
            standalone["compression"],
            standalone["overridden"],
            standalone.get("format", -1),
        )
        + "  spriteSheet:\n    serializedVersion: 2\n"
    )


def audio_meta(compression_format: int, overrides: str = "{}") -> str:
    return (
        "fileFormatVersion: 2\nguid: 596a81770d97f9547a6c13888467a77a\nAudioImporter:\n"
        "  serializedVersion: 8\n  defaultSettings:\n    serializedVersion: 2\n    loadType: 0\n"
        f"    compressionFormat: {compression_format}\n    quality: 1\n"
        f"  platformSettingOverrides: {overrides}\n  forceToMono: 0\n"
    )


class CheckUnityBuildSizeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name) / "MyGame"
        (self.root / "Assets").mkdir(parents=True)
        (self.root / "ProjectSettings").mkdir()
        self.write("Packages/manifest.json", json.dumps(GLTFAST_MANIFEST))

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    # helpers

    def write(self, rel: str, data: str | bytes) -> Path:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(data, bytes):
            path.write_bytes(data)
        else:
            path.write_text(data, encoding="utf-8")
        return path

    def sized(self, rel: str, size: int, head: bytes = b"") -> Path:
        path = self.write(rel, head)
        with path.open("r+b") as handle:
            handle.truncate(size)  # sparse on most file systems
        return path

    def run_checker(self, *args: str, target: Path | None = None) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(CHECKER), str(target or self.root), *args],
            capture_output=True,
            text=True,
            check=False,
        )

    def report(self, *args: str) -> dict:
        result = self.run_checker("--json", "--max-issues", "0", *args)
        self.assertIn(result.returncode, (0, 1), result.stderr)
        return json.loads(result.stdout)

    def codes(self, data: dict, level: str) -> list[tuple[str, str]]:
        return sorted((item["code"], item["file"]) for item in data[level])

    # tests

    def test_clean_project_passes_strict(self) -> None:
        self.write("Assets/Textures/ui.png", png(256, 256))
        self.write("Assets/Textures/ui.png.meta", texture_meta())
        result = self.run_checker("--strict")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("Summary: 0 errors, 0 warnings, 0 notes", result.stdout)

    def test_glb_with_oversized_embedded_image_warns_with_estimate(self) -> None:
        self.write("Assets/Models/room.glb", glb([png(8192, 8192), png(512, 512)]))
        data = self.report()
        self.assertEqual(self.codes(data, "warnings"), [("gltf-embedded-texture", "Assets/Models/room.glb")])
        message = data["warnings"][0]["message"]
        self.assertIn("1 of 2 embedded images exceed 2048 px", message)
        self.assertIn("8192x8192 png", message)
        # 8192² RGBA32 with mips (341.3 MiB) plus 512² RGBA32 with mips (1.3 MiB)
        self.assertIn("about 342.7 MB", message)
        self.assertIn(
            "npx @gltf-transform/cli@4 resize Assets/Models/room.glb Assets/Models/room.glb --width 2048",
            data["warnings"][0]["fix"],
        )

    def test_jpeg_images_count_three_bytes_per_pixel(self) -> None:
        self.write("Assets/Models/crate.glb", glb([jpeg(4096, 2048)]))
        data = self.report()
        self.assertIn("4096x2048 jpeg", data["warnings"][0]["message"])
        self.assertIn("about 32.0 MB", data["warnings"][0]["message"])

    def test_small_embedded_images_are_a_note(self) -> None:
        self.write("Assets/Models/prop.glb", glb([png(1024, 1024)]))
        data = self.report("--strict")
        self.assertEqual(data["warning_count"], 0)
        self.assertEqual(self.codes(data, "notes"), [("gltf-embedded-images", "Assets/Models/prop.glb")])
        self.assertIn("about 5.3 MB", data["notes"][0]["message"])

    def test_max_texture_size_option_changes_the_limit(self) -> None:
        self.write("Assets/Models/prop.glb", glb([png(1024, 1024)]))
        data = self.report("--max-texture-size", "512")
        self.assertEqual(self.codes(data, "warnings"), [("gltf-embedded-texture", "Assets/Models/prop.glb")])

    def test_heavy_geometry_is_a_note(self) -> None:
        self.write("Assets/Models/plant.glb", glb([], geometry_bytes=40 * MIB))
        data = self.report()
        self.assertEqual(self.codes(data, "notes"), [("gltf-heavy-geometry", "Assets/Models/plant.glb")])
        self.assertIn("simplify Assets/Models/plant.glb Assets/Models/plant.glb", data["notes"][0]["fix"])

    def test_gltf_external_images_are_left_to_the_texture_importer(self) -> None:
        gltf = {
            "asset": {"version": "2.0"},
            "images": [
                {"uri": "wood.png"},
                {"uri": "data:image/png;base64," + base64.b64encode(png(4096, 4096)).decode()},
            ],
        }
        self.write("Assets/Models/table.gltf", json.dumps(gltf))
        self.write("Assets/Models/wood.png", png(4096, 4096))
        data = self.report()
        self.assertEqual(self.codes(data, "warnings"), [("gltf-embedded-texture", "Assets/Models/table.gltf")])
        self.assertIn("1 of 1 embedded images", data["warnings"][0]["message"])

    def test_fix_commands_quote_shell_metacharacters(self) -> None:
        rel = "Assets/Models/$(touch pwned) `id`.glb"
        self.write(rel, glb([png(4096, 4096)]))
        fix = self.report()["warnings"][0]["fix"]
        command = fix.split("run ", 1)[1].split(",", 1)[0]
        self.assertEqual(shlex.split(command)[3:5], [rel, rel])
        self.assertIn(shlex.quote(rel), fix)

    def test_gltf_data_uri_fix_warns_about_srgb(self) -> None:
        image = {"uri": "data:image/png;base64," + base64.b64encode(png(4096, 4096)).decode()}
        self.write("Assets/Models/table.gltf", json.dumps({"asset": {"version": "2.0"}, "images": [image]}))
        self.write("Assets/Models/room.glb", glb([png(4096, 4096)]))
        fixes = {item["file"]: item["fix"] for item in self.report()["warnings"]}
        self.assertIn("separate files", fixes["Assets/Models/table.gltf"])
        self.assertIn("sRGB (Color Texture) off", fixes["Assets/Models/table.gltf"])
        self.assertIn("Fix B", fixes["Assets/Models/table.gltf"])
        self.assertNotIn("sRGB", fixes["Assets/Models/room.glb"])

    def test_gltf_fix_moves_the_model_when_other_gltf_files_share_its_folder(self) -> None:
        image = {"uri": "data:image/png;base64," + base64.b64encode(png(4096, 4096)).decode()}
        text = json.dumps({"asset": {"version": "2.0"}, "images": [image]})
        self.write("Assets/Shared/a.gltf", text)
        self.write("Assets/Shared/b.gltf", text)
        self.write("Assets/Alone/c.gltf", text)
        fixes = {item["file"]: item["fix"] for item in self.report()["warnings"]}
        shared = fixes["Assets/Shared/a.gltf"]
        self.assertIn("first move this file and its .meta into Assets/Shared/a/", shared)
        self.assertIn("resize Assets/Shared/a/a.gltf Assets/Shared/a/a.gltf", shared)
        self.assertIn("overwrites files with those names", shared)
        alone = fixes["Assets/Alone/c.gltf"]
        self.assertNotIn("first move", alone)
        self.assertIn("resize Assets/Alone/c.gltf Assets/Alone/c.gltf --width 2048", alone)
        self.assertIn("baseColor_1.png", alone)
        self.assertNotIn(";", alone)

    def test_broken_package_manifest_does_not_crash(self) -> None:
        self.write("Assets/Models/room.glb", glb([png(4096, 4096)]))
        for manifest in ("[]", '{"dependencies": 5}', "{not json"):
            self.write("Packages/manifest.json", manifest)
            result = self.run_checker("--json")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn("Traceback", result.stderr)
            self.assertEqual(self.codes(json.loads(result.stdout), "notes"), [("gltf-not-checked", "Assets/Models/room.glb")])

    def test_buffer_uri_outside_the_project_is_not_read(self) -> None:
        outside = Path(self.temp_dir.name) / "secret.bin"
        outside.write_bytes(png(4096, 4096))
        gltf = {
            "asset": {"version": "2.0"},
            "buffers": [{"uri": "../../../secret.bin", "byteLength": len(outside.read_bytes())}],
            "bufferViews": [{"buffer": 0, "byteLength": len(outside.read_bytes())}],
            "images": [{"bufferView": 0, "mimeType": "image/png"}],
        }
        self.write("Assets/Models/escape.gltf", json.dumps(gltf))
        self.assertEqual(self.report()["warning_count"], 0)
        # The same layout inside the project, with a percent-encoded name, is read.
        self.write("Assets/Models/my buffer.bin", png(4096, 4096))
        gltf["buffers"][0]["uri"] = "my%20buffer.bin"
        self.write("Assets/Models/inside.gltf", json.dumps(gltf))
        self.assertEqual(
            self.codes(self.report(), "warnings"), [("gltf-embedded-texture", "Assets/Models/inside.gltf")]
        )

    def test_implausible_image_sizes_are_ignored(self) -> None:
        self.write("Assets/Models/zero.glb", glb([png(0, 0)]))
        self.write("Assets/Models/huge.glb", glb([png(4294967295, 4294967295)]))
        self.write("Assets/Textures/huge.png", png(4294967295, 4294967295))
        self.write("Assets/Textures/huge.png.meta", texture_meta(default_compression=0, default_max=8192))
        data = self.report()
        self.assertEqual(data["warning_count"], 0)
        self.assertEqual(data["note_count"], 0)

    def test_named_pipes_are_skipped(self) -> None:
        if not hasattr(os, "mkfifo"):
            self.skipTest("no named pipes on this platform")
        os.mkfifo(self.root / "Assets" / "pipe.glb")
        os.mkfifo(self.root / "Assets" / "pipe.png")
        self.write("Assets/pipe.png.meta", texture_meta())
        result = subprocess.run(
            [sys.executable, str(CHECKER), str(self.root), "--json"],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_malformed_gltf_warns_without_a_traceback(self) -> None:
        nested = "[" * 100_000 + "]" * 100_000
        cases = {
            "list_root.gltf": "[1, 2]",
            "wrong_types.gltf": json.dumps({"buffers": [{"byteLength": "big"}], "images": [1]}),
            "image_list.gltf": json.dumps({"images": [["bufferView"]], "bufferViews": {}}),
            "nested.gltf": '{"images": ' + nested + "}",
        }
        for name, text in cases.items():
            self.write(f"Assets/Models/{name}", text)
        huge_chunk = struct.pack("<III", 0x46546C67, 2, 28) + struct.pack("<II", 0xFFFFFFF0, 0x4E4F534A) + b"{}  "
        self.write("Assets/Models/huge_chunk.glb", huge_chunk)
        result = self.run_checker("--json", "--max-issues", "0")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        data = json.loads(result.stdout)
        expected = sorted(("gltf-unreadable", f"Assets/Models/{name}") for name in [*cases, "huge_chunk.glb"])
        self.assertEqual(self.codes(data, "warnings"), expected)

    def test_unreadable_glb_warns(self) -> None:
        self.write("Assets/Models/broken.glb", b"not a glb at all")
        data = self.report()
        self.assertEqual(self.codes(data, "warnings"), [("gltf-unreadable", "Assets/Models/broken.glb")])

    def test_git_lfs_pointer_is_named(self) -> None:
        pointer = b"version https://git-lfs.github.com/spec/v1\noid sha256:" + b"0" * 64 + b"\nsize 4096\n"
        self.write("Assets/Models/room.glb", pointer)
        data = self.report()
        self.assertEqual(self.codes(data, "warnings"), [("gltf-unreadable", "Assets/Models/room.glb")])
        self.assertIn("Git LFS pointer", data["warnings"][0]["message"])
        self.assertIn("git lfs pull", data["warnings"][0]["fix"])

    def test_models_without_gltfast_are_not_checked(self) -> None:
        self.write("Packages/manifest.json", json.dumps({"dependencies": {}}))
        self.write("Assets/Models/room.glb", glb([png(8192, 8192)]))
        data = self.report("--strict")
        self.assertEqual(data["warning_count"], 0)
        self.assertEqual(self.codes(data, "notes"), [("gltf-not-checked", "Assets/Models/room.glb")])

    def test_uncompressed_large_texture_warns_on_the_setting_line(self) -> None:
        self.write("Assets/Textures/wall.png", png(2048, 2048))
        meta = self.write("Assets/Textures/wall.png.meta", texture_meta(default_compression=0))
        data = self.report()
        self.assertEqual(self.codes(data, "warnings"), [("uncompressed-texture", "Assets/Textures/wall.png.meta")])
        line = data["warnings"][0]["line"]
        self.assertEqual(meta.read_text().splitlines()[line - 1].strip(), "textureCompression: 0")
        self.assertIn("about 21.3 MB", data["warnings"][0]["message"])

    def test_platform_override_wins_over_the_default(self) -> None:
        self.write("Assets/Textures/wall.png", png(2048, 2048))
        self.write(
            "Assets/Textures/wall.png.meta",
            texture_meta(default_compression=0, override={"max": 2048, "compression": 1, "overridden": 1}),
        )
        self.assertEqual(self.report()["warning_count"], 0)
        android = self.report("--platform", "Android")
        self.assertEqual(self.codes(android, "warnings"), [("uncompressed-texture", "Assets/Textures/wall.png.meta")])

    def test_explicit_format_decides_over_compression(self) -> None:
        self.write("Assets/Textures/wall.png", png(2048, 2048))
        etc2 = {"max": 2048, "compression": 0, "overridden": 1, "format": 47}  # ETC2_RGBA8
        self.write("Assets/Textures/wall.png.meta", texture_meta(override=etc2))
        self.assertEqual(self.report()["warning_count"], 0)

        rgba32 = {"max": 2048, "compression": 1, "overridden": 1, "format": 4}
        meta = self.write("Assets/Textures/wall.png.meta", texture_meta(override=rgba32))
        data = self.report()
        self.assertEqual(self.codes(data, "warnings"), [("uncompressed-texture", "Assets/Textures/wall.png.meta")])
        warning = data["warnings"][0]
        self.assertEqual(meta.read_text().splitlines()[warning["line"] - 1].strip(), "textureFormat: 4")
        self.assertIn("Format is RGBA32 in the Standalone override", warning["message"])
        self.assertIn("about 21.3 MB", warning["message"])
        self.assertIn("Format to Automatic", warning["fix"])

    def test_signed_uncompressed_formats_warn_and_obsolete_automatic_formats_use_compression(self) -> None:
        self.write("Assets/Textures/wall.png", png(2048, 2048))
        signed = {"max": 2048, "compression": 1, "overridden": 1, "format": 78}  # RGBA32_SIGNED
        self.write("Assets/Textures/wall.png.meta", texture_meta(override=signed))
        data = self.report()
        self.assertIn("Format is RGBA32_SIGNED", data["warnings"][0]["message"])

        # -3 is the obsolete AutomaticTruecolor: Unity reads it as automatic, so Compression decides.
        for compression, expected in ((1, 0), (0, 1)):
            old = {"max": 2048, "compression": compression, "overridden": 1, "format": -3}
            self.write("Assets/Textures/wall.png.meta", texture_meta(override=old))
            self.assertEqual(self.report()["warning_count"], expected)

    def test_estimate_has_no_mip_chain_when_mipmaps_are_off(self) -> None:
        self.write("Assets/UI/panel.png", png(2048, 2048))
        meta = texture_meta(default_compression=0).replace(
            "  isReadable: 0\n", "  mipmaps:\n    mipMapMode: 0\n    enableMipMap: 0\n  isReadable: 0\n"
        )
        self.write("Assets/UI/panel.png.meta", meta)
        self.assertIn("about 16.0 MB", self.report()["warnings"][0]["message"])

    def test_streaming_assets_is_special_only_at_the_root(self) -> None:
        self.sized("Assets/StreamingAssets/.hidden/video.bin", 9 * MIB)
        self.write("Assets/StreamingAssets/scene.glb", glb([png(8192, 8192)]))
        self.sized("Assets/Sub/StreamingAssets/data.bin", 9 * MIB)
        data = self.report()
        self.assertEqual(data["warning_count"], 0)  # the raw .glb ships as is; glTFast settings do not apply
        self.assertEqual(
            self.codes(data, "notes"), [("large-streaming-asset", "Assets/StreamingAssets/.hidden/video.bin")]
        )

    def test_small_uncompressed_texture_is_ignored(self) -> None:
        self.write("Assets/UI/icon.png", png(512, 512))
        self.write("Assets/UI/icon.png.meta", texture_meta(default_compression=0))
        self.assertEqual(self.report()["warning_count"], 0)

    def test_oversized_max_size_warns(self) -> None:
        self.write("Assets/Textures/sky.jpg", jpeg(8192, 4096))
        self.write("Assets/Textures/sky.jpg.meta", texture_meta(default_max=8192))
        data = self.report()
        self.assertEqual(self.codes(data, "warnings"), [("texture-max-size", "Assets/Textures/sky.jpg.meta")])
        self.assertIn("Max Size is 8192", data["warnings"][0]["message"])

    def test_large_pcm_audio_warns(self) -> None:
        self.sized("Assets/Audio/music.wav", 3 * MIB, b"RIFF")
        self.write("Assets/Audio/music.wav.meta", audio_meta(0))
        self.sized("Assets/Audio/theme.wav", 3 * MIB, b"RIFF")
        self.write("Assets/Audio/theme.wav.meta", audio_meta(1))
        data = self.report()
        self.assertEqual(self.codes(data, "warnings"), [("pcm-audio", "Assets/Audio/music.wav.meta")])
        self.assertEqual(data["warnings"][0]["line"], 8)

    def test_pcm_audio_with_platform_overrides_is_a_note(self) -> None:
        self.sized("Assets/Audio/music.wav", 3 * MIB, b"RIFF")
        overrides = "\n    4:\n      loadType: 1\n      compressionFormat: 1"
        self.write("Assets/Audio/music.wav.meta", audio_meta(0, overrides))
        data = self.report()
        self.assertEqual(data["warning_count"], 0)
        self.assertEqual(self.codes(data, "notes"), [("audio-platform-override", "Assets/Audio/music.wav.meta")])

    def test_resources_and_streaming_assets(self) -> None:
        self.sized("Assets/Resources/Video/intro.mp4", 9 * MIB)
        self.sized("Assets/StreamingAssets/data.bin", 9 * MIB)
        self.sized("Assets/Resources/small.bytes", 1024)
        data = self.report()
        self.assertEqual(
            self.codes(data, "warnings"), [("large-resources-asset", "Assets/Resources/Video/intro.mp4")]
        )
        self.assertEqual(self.codes(data, "notes"), [("large-streaming-asset", "Assets/StreamingAssets/data.bin")])

    def test_hidden_and_tilde_folders_are_skipped(self) -> None:
        self.write("Assets/Docs~/room.glb", glb([png(8192, 8192)]))
        self.write("Assets/.cache/room.glb", glb([png(8192, 8192)]))
        self.assertEqual(self.report()["warning_count"], 0)

    def test_strict_fails_on_warnings_and_json_shape(self) -> None:
        self.write("Assets/Models/room.glb", glb([png(4096, 4096)]))
        result = self.run_checker("--strict")
        self.assertEqual(result.returncode, 1)
        self.assertIn("WARNING Assets/Models/room.glb:", result.stdout)
        self.assertIn("  fix: ", result.stdout)
        self.assertEqual(self.run_checker().returncode, 0)
        data = self.report()
        for key in (
            "tool",
            "schema",
            "root",
            "files_checked",
            "error_count",
            "warning_count",
            "note_count",
            "errors",
            "warnings",
            "notes",
            "truncated",
        ):
            self.assertIn(key, data)
        self.assertEqual(data["tool"], "check_unity_build_size")

    def test_max_issues_truncates_but_keeps_totals(self) -> None:
        for name in ("a", "b", "c"):
            self.write(f"Assets/Models/{name}.glb", glb([png(4096, 4096)]))
        data = json.loads(self.run_checker("--json", "--max-issues", "1").stdout)
        self.assertEqual(data["warning_count"], 3)
        self.assertEqual(len(data["warnings"]), 1)
        self.assertTrue(data["truncated"])
        text = self.run_checker("--max-issues", "2").stdout
        self.assertIn("... and 1 more", text)

    def test_runs_from_a_folder_inside_the_project(self) -> None:
        self.write("Assets/Models/room.glb", glb([png(4096, 4096)]))
        result = self.run_checker(target=self.root / "Assets" / "Models")
        self.assertIn("WARNING Assets/Models/room.glb", result.stdout)

    def test_not_a_unity_project_exits_2(self) -> None:
        other = Path(self.temp_dir.name) / "NotUnity"
        other.mkdir()
        result = self.run_checker(target=other)
        self.assertEqual(result.returncode, 2)
        self.assertIn("not inside a Unity project", result.stderr)
        missing = self.run_checker(target=Path(self.temp_dir.name) / "missing")
        self.assertEqual(missing.returncode, 2)

    def test_help(self) -> None:
        result = subprocess.run([sys.executable, str(CHECKER), "--help"], capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0)
        self.assertIn("--max-texture-size", result.stdout)


if __name__ == "__main__":
    unittest.main()
