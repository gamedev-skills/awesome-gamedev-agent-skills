#!/usr/bin/env python3
"""Find the assets that make a Unity 6 player build large, before you build.

Reads the project's import settings and source files and reports what will be
stored uncompressed or at full resolution in the player:

WARNINGS (probably wasting space; each one might still be intentional)
  gltf-embedded-texture  A .glb/.gltf imported by glTFast embeds a PNG/JPEG image
                         larger than --max-texture-size. glTFast decodes embedded
                         images with Texture2D.LoadImage, so they ship as
                         uncompressed RGBA32/RGB24 (with mipmaps by default).
  uncompressed-texture   A texture whose effective platform setting has
                         Compression = None (or an explicit uncompressed Format)
                         and whose source is at least 1024 px. A sprite packed
                         into a Sprite Atlas ships with the atlas settings, so
                         this can be a false positive for packed sprites.
  texture-max-size       A texture whose effective Max Size is above
                         --max-texture-size and whose source is that large too.
  pcm-audio              An AudioClip of 1 MB or more whose default settings use
                         PCM (no compression).
  large-resources-asset  A file of 8 MB or more inside a Resources folder. Every
                         asset in a Resources folder ships, used or not.
  gltf-unreadable        A .glb/.gltf that could not be parsed or has an
                         unexpected structure.

NOTES (informational, never affect the exit status)
  gltf-embedded-images   A glTFast model whose embedded images are all within the
                         limit, with the estimated bytes they add to the build.
  audio-platform-override  A PCM AudioClip with platform overrides this tool does
                         not read; check the override in the Inspector.
  large-streaming-asset  A file of 8 MB or more in Assets/StreamingAssets, which
                         is copied into the build byte for byte. Models and
                         textures there are not checked as imported assets,
                         because the raw file is what ships.
  gltf-heavy-geometry    A glTFast model holding 32 MB or more of non-image buffer
                         data. glTFast turns it into Unity meshes of about the
                         same size, and the Model Importer's Mesh Compression
                         does not apply to them.
  gltf-not-checked       .glb/.gltf files exist but glTFast is not in
                         Packages/manifest.json, so their import is unknown.

This tool does not know which assets a build references. Confirm the real cost
with the Build Report in the Editor log (see build_report.py).

Standard library only. Read-only: nothing is ever written.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import shlex
import struct
import sys
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import unquote

TOOL = "check_unity_build_size"
SCHEMA = 1

GLTFAST_PACKAGES = ("com.unity.cloud.gltfast", "com.atteneder.gltfast")
TEXTURE_EXTENSIONS = frozenset(
    {".png", ".jpg", ".jpeg", ".tga", ".psd", ".tif", ".tiff", ".exr", ".hdr", ".bmp", ".gif", ".iff", ".pict"}
)
AUDIO_EXTENSIONS = frozenset({".wav", ".aif", ".aiff", ".mp3", ".ogg", ".flac", ".mod", ".it", ".s3m", ".xm"})

# TextureImporterCompression.Uncompressed and AudioCompressionFormat.PCM as stored in .meta files.
UNCOMPRESSED = 0
PCM = 0

# TextureImporterFormat.Automatic. Any value of 0 or more is an explicit format, and Unity then
# ignores textureCompression for that platform. The other negative values are obsolete automatic
# modes from old .meta files; they are treated like Automatic.
AUTOMATIC_FORMAT = -1

# Explicit TextureImporterFormat values that store pixels uncompressed: value -> (name, bytes per pixel).
# Every other explicit format is block-compressed (DXT, BC, ETC, EAC, ASTC, PVRTC, crunched).
# Values from UnityCsReference Editor/Mono/AssetPipeline/TextureImporterEnums.cs.
UNCOMPRESSED_FORMATS = {
    1: ("Alpha8", 1),
    2: ("ARGB16", 2),
    3: ("RGB24", 3),
    4: ("RGBA32", 4),
    5: ("ARGB32", 4),
    7: ("RGB16", 2),
    9: ("R16", 2),
    13: ("RGBA16", 2),
    15: ("RHalf", 2),
    16: ("RGHalf", 4),
    17: ("RGBAHalf", 8),
    18: ("RFloat", 4),
    19: ("RGFloat", 8),
    20: ("RGBAFloat", 16),
    22: ("RGB9E5", 4),
    62: ("RG16", 2),
    63: ("R8", 1),
    72: ("RG32", 4),
    73: ("RGB48", 6),
    74: ("RGBA64", 8),
    75: ("R8_SIGNED", 1),
    76: ("RG16_SIGNED", 2),
    77: ("RGB24_SIGNED", 3),
    78: ("RGBA32_SIGNED", 4),
    79: ("R16_SIGNED", 2),
    80: ("RG32_SIGNED", 4),
    81: ("RGB48_SIGNED", 6),
    82: ("RGBA64_SIGNED", 8),
}
UNCOMPRESSED_AUTOMATIC_BPP = 4

# Largest texture edge Unity imports; a header claiming more (or 0) is treated as unreadable.
MAX_TEXTURE_EDGE = 16384

UNCOMPRESSED_MIN_PX = 1024
PCM_MIN_BYTES = 1024 * 1024
LARGE_FILE_BYTES = 8 * 1024 * 1024
NOTE_MIN_BYTES = 1024 * 1024
GEOMETRY_NOTE_BYTES = 32 * 1024 * 1024
DEFAULT_MAX_TEXTURE_SIZE = 2048
DEFAULT_PLATFORM = "Standalone"

# Bytes per pixel Texture2D.LoadImage produces: PNG -> 32-bit RGBA/ARGB, JPEG -> RGB24.
LOADIMAGE_BPP = {"png": 4, "jpeg": 3}

# Enough of a file to reach a JPEG frame header behind a large EXIF/XMP block.
HEADER_READ_BYTES = 512 * 1024

GLTF_TRANSFORM = "npx @gltf-transform/cli@4"

LFS_POINTER = b"version https://git-lfs.github.com/spec/"

GLB_MAGIC = 0x46546C67
GLB_JSON = 0x4E4F534A
GLB_BIN = 0x004E4942

JPEG_SOF = frozenset({0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF})
JPEG_NO_LENGTH = frozenset({0x01, *range(0xD0, 0xDA)})

PLATFORM_ENTRY_RE = re.compile(r"^  - serializedVersion:")
PLATFORM_KEY_RE = re.compile(
    r"^    (buildTarget|maxTextureSize|textureFormat|textureCompression|overridden):\s*(\S+)\s*$"
)
IMPORTER_RE = re.compile(r"^[A-Za-z]+Importer:$")
MIPMAP_RE = re.compile(r"^    enableMipMap:\s*([01])\s*$")
AUDIO_FORMAT_RE = re.compile(r"^    compressionFormat:\s*(-?\d+)\s*$")
AUDIO_OVERRIDES_RE = re.compile(r"^  platformSettingOverrides:\s*(\{\})?\s*$")


@dataclass
class Issue:
    level: str  # "error", "warning" or "note"
    code: str
    file: str
    line: int | None
    message: str
    fix: str

    def as_json(self) -> dict:
        return {"code": self.code, "file": self.file, "line": self.line, "message": self.message, "fix": self.fix}


@dataclass
class Scan:
    root: Path
    platform: str
    max_texture_size: int
    files_checked: int = 0
    issues: list[Issue] = field(default_factory=list)

    def rel(self, path: Path) -> str:
        return path.relative_to(self.root).as_posix()

    def add(self, level: str, code: str, path: Path, line: int | None, message: str, fix: str) -> None:
        self.issues.append(Issue(level, code, self.rel(path), line, message, fix))


def quoted(path: str) -> str:
    """Quote a path for a POSIX shell, so names with $(...) or backticks paste safely."""
    return shlex.quote(path)


def mb(size: int) -> str:
    return f"{size / (1024 * 1024):.1f} MB"


# ---------------------------------------------------------------------------
# image headers


def image_kind(head: bytes) -> str | None:
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if head.startswith(b"\xff\xd8"):
        return "jpeg"
    return None


def png_size(head: bytes) -> tuple[int, int] | None:
    if len(head) < 24 or head[12:16] != b"IHDR":
        return None
    return struct.unpack(">II", head[16:24])


def jpeg_size(head: bytes) -> tuple[int, int] | None:
    pos = 2
    while pos + 4 <= len(head):
        if head[pos] != 0xFF:
            return None
        marker = head[pos + 1]
        if marker == 0xFF:  # fill byte
            pos += 1
            continue
        if marker in JPEG_NO_LENGTH:
            pos += 2
            continue
        (length,) = struct.unpack(">H", head[pos + 2 : pos + 4])
        if marker in JPEG_SOF:
            if pos + 9 > len(head):
                return None
            height, width = struct.unpack(">HH", head[pos + 5 : pos + 9])
            return width, height
        pos += 2 + length
    return None


def header_size(head: bytes, suffix: str) -> tuple[int, int] | None:
    kind = image_kind(head)
    if kind == "png":
        return png_size(head)
    if kind == "jpeg":
        return jpeg_size(head)
    if head.startswith(b"8BPS") and len(head) >= 22:
        height, width = struct.unpack(">II", head[14:22])
        return width, height
    if suffix == ".tga" and len(head) >= 18:
        return struct.unpack("<HH", head[12:16])
    return None


def image_size(head: bytes, suffix: str = "") -> tuple[int, int] | None:
    """Width and height from the first bytes of a PNG, JPEG, TGA or PSD file.

    None when the header is unknown or claims a size Unity cannot import (0, or above 16384).
    """
    size = header_size(head, suffix)
    if size is None or min(size) < 1 or max(size) > MAX_TEXTURE_EDGE:
        return None
    return size


def mip_chain_bytes(width: int, height: int, bpp: int, mips: bool = True) -> int:
    """Bytes of an uncompressed texture as Unity stores it: one level, or a full mip chain."""
    total = 0
    while True:
        total += width * height * bpp
        if not mips or (width == 1 and height == 1):
            return total
        width, height = max(1, width // 2), max(1, height // 2)


def read_head(path: Path, limit: int = HEADER_READ_BYTES) -> bytes:
    with path.open("rb") as handle:
        return handle.read(limit)


# ---------------------------------------------------------------------------
# glTF / GLB


@dataclass
class EmbeddedImage:
    index: int
    kind: str
    width: int
    height: int

    @property
    def build_bytes(self) -> int:
        return mip_chain_bytes(self.width, self.height, LOADIMAGE_BPP[self.kind])


def decode_data_uri(uri: str) -> bytes | None:
    if not uri.startswith("data:") or ";base64," not in uri:
        return None
    return base64.b64decode(uri.split(";base64,", 1)[1], validate=False)


def read_glb_chunks(path: Path) -> tuple[dict, int | None, int]:
    """Return (glTF JSON, offset of the BIN chunk data or None, BIN length)."""
    with path.open("rb") as handle:
        file_size = os.fstat(handle.fileno()).st_size
        header = handle.read(12)
        if len(header) < 12:
            raise ValueError("file is shorter than a GLB header")
        magic, version, _ = struct.unpack("<III", header)
        if magic != GLB_MAGIC:
            raise ValueError("missing 'glTF' magic")
        if version != 2:
            raise ValueError(f"GLB version {version} (only 2 is supported)")
        gltf: dict | None = None
        bin_offset: int | None = None
        bin_length = 0
        while True:
            chunk_header = handle.read(8)
            if len(chunk_header) < 8:
                break
            length, kind = struct.unpack("<II", chunk_header)
            if length > file_size - handle.tell():
                raise ValueError("a chunk length runs past the end of the file")
            if kind == GLB_JSON and gltf is None:
                gltf = json.loads(handle.read(length).decode("utf-8"))
                continue
            if kind == GLB_BIN and bin_offset is None:
                bin_offset, bin_length = handle.tell(), length
            handle.seek(length, os.SEEK_CUR)
        if gltf is None:
            raise ValueError("no JSON chunk")
        return gltf, bin_offset, bin_length


def external_file(path: Path, uri: str, root: Path) -> Path | None:
    """The file a relative glTF URI names, or None when it is missing or outside the project."""
    if "://" in uri or uri.startswith("/"):
        return None
    target = Path(os.path.realpath(path.parent / unquote(uri)))
    if not target.is_relative_to(Path(os.path.realpath(root))) or not target.is_file():
        return None
    return target


def buffer_view_head(
    path: Path, gltf: dict, view_index: int, bin_offset: int | None, root: Path
) -> bytes | None:
    views = gltf.get("bufferViews") or []
    buffers = gltf.get("buffers") or []
    if not 0 <= view_index < len(views):
        return None
    view = views[view_index]
    buffer_index = view.get("buffer", 0)
    if not 0 <= buffer_index < len(buffers):
        return None
    start = view.get("byteOffset", 0)
    size = min(view.get("byteLength", 0), HEADER_READ_BYTES)
    uri = buffers[buffer_index].get("uri")
    if uri is None:
        if bin_offset is None:
            return None
        with path.open("rb") as handle:
            handle.seek(bin_offset + start)
            return handle.read(size)
    data = decode_data_uri(uri)
    if data is not None:
        return data[start : start + size]
    external = external_file(path, uri, root)
    if external is None:
        return None
    with external.open("rb") as handle:
        handle.seek(start)
        return handle.read(size)


@dataclass
class Model:
    images: list[EmbeddedImage]
    geometry_bytes: int  # buffer bytes not used by images


def read_model(path: Path, root: Path) -> Model:
    """Images stored inside the model (bufferView or data: URI) and the remaining buffer bytes."""
    if path.suffix.lower() == ".glb":
        gltf, bin_offset, _ = read_glb_chunks(path)
    else:
        gltf, bin_offset = json.loads(path.read_text(encoding="utf-8")), None
    if not isinstance(gltf, dict):
        raise ValueError("the glTF JSON root is not an object")
    views = gltf.get("bufferViews") or []
    buffer_bytes = sum(buffer.get("byteLength", 0) for buffer in gltf.get("buffers") or [])
    image_bytes = 0
    found = []
    for index, image in enumerate(gltf.get("images") or []):
        if "bufferView" in image:
            view = image["bufferView"]
            if isinstance(view, int) and 0 <= view < len(views):
                image_bytes += views[view].get("byteLength", 0)
            head = buffer_view_head(path, gltf, view, bin_offset, root)
        else:
            head = decode_data_uri(image.get("uri", ""))  # None for an external file
        if not head:
            continue
        kind = image_kind(head)
        size = image_size(head)
        if kind and size:
            found.append(EmbeddedImage(index, kind, *size))
    return Model(found, max(0, buffer_bytes - image_bytes))


def unreadable(scan: Scan, path: Path, message: str) -> None:
    scan.add(
        "warning",
        "gltf-unreadable",
        path,
        None,
        message,
        "open it in a glTF viewer or re-export it; glTFast will fail to import it too",
    )


def resize_command(scan: Scan, rel: str) -> str:
    return (
        f"from the project folder run {GLTF_TRANSFORM} resize {quoted(rel)} {quoted(rel)} "
        f"--width {scan.max_texture_size} --height {scan.max_texture_size}"
    )


def resize_fix(scan: Scan, path: Path) -> str:
    rel = scan.rel(path)
    if path.suffix.lower() != ".gltf":
        return (
            f"{resize_command(scan, rel)}, or move the images out of the model so the Texture Importer "
            "compresses them (references/gltf-textures.md)"
        )
    # gltf-transform 4.x writes a .gltf's images as separate files named after the texture slot
    # (baseColor_1.png, normal_1.png, ...) and overwrites files of that name, so this is Fix B, and two
    # .gltf files in one folder end up sharing (and overwriting) each other's images.
    after = (
        ". It writes the images out as separate files named after their texture slot "
        "(baseColor_1.png, normal_1.png, ...) and overwrites files with those names. The Texture Importer "
        "compresses them. Turn sRGB (Color Texture) off on every data map such as normal, "
        "metallic-roughness and occlusion (references/gltf-textures.md, Fix B)"
    )
    siblings = [
        other for other in path.parent.iterdir() if other != path and other.suffix.lower() == ".gltf"
    ]
    if not siblings:
        return resize_command(scan, rel) + after
    folder = path.parent / path.stem
    moved = scan.rel(folder / path.name)
    return (
        f"other .gltf files share this folder and would overwrite each other's images, so first move "
        f"this file and its .meta into {scan.rel(folder)}/ (in the Editor, or with git mv, which keeps "
        f"the GUID). Then {resize_command(scan, moved)}" + after
    )


def check_gltf(scan: Scan, path: Path) -> None:
    scan.files_checked += 1
    try:
        if read_head(path, len(LFS_POINTER)) == LFS_POINTER:
            scan.add(
                "warning",
                "gltf-unreadable",
                path,
                None,
                "this is a Git LFS pointer file, not the model",
                "run git lfs pull so Unity and this check see the real file",
            )
            return
        model = read_model(path, scan.root)
    except (OSError, ValueError, UnicodeDecodeError, struct.error) as exc:
        unreadable(scan, path, f"could not read the model: {exc}")
        return
    except (TypeError, AttributeError, KeyError, IndexError, RecursionError, MemoryError, OverflowError):
        unreadable(scan, path, "the glTF JSON does not have the structure the glTF 2.0 spec requires")
        return
    if model.geometry_bytes >= GEOMETRY_NOTE_BYTES:
        scan.add(
            "note",
            "gltf-heavy-geometry",
            path,
            None,
            f"about {mb(model.geometry_bytes)} of mesh and animation data, which ships at a similar size",
            f"{GLTF_TRANSFORM} weld {quoted(scan.rel(path))} {quoted(scan.rel(path))}, then "
            f"{GLTF_TRANSFORM} simplify {quoted(scan.rel(path))} {quoted(scan.rel(path))} --ratio 0.5 "
            "--error 0.001, then check the silhouette in the scene",
        )
    images = model.images
    if not images:
        return
    total = sum(image.build_bytes for image in images)
    largest = max(images, key=lambda image: max(image.width, image.height))
    too_big = [image for image in images if max(image.width, image.height) > scan.max_texture_size]
    if too_big:
        scan.add(
            "warning",
            "gltf-embedded-texture",
            path,
            None,
            f"{len(too_big)} of {len(images)} embedded images exceed {scan.max_texture_size} px "
            f"(largest image {largest.index}: {largest.width}x{largest.height} {largest.kind}); "
            f"glTFast ships them uncompressed, about {mb(total)} in the build",
            resize_fix(scan, path),
        )
    elif total >= NOTE_MIN_BYTES:
        scan.add(
            "note",
            "gltf-embedded-images",
            path,
            None,
            f"{len(images)} embedded images ship uncompressed, about {mb(total)} in the build",
            "fine if the total build is within budget; otherwise see references/gltf-textures.md",
        )


# ---------------------------------------------------------------------------
# texture and audio importers


@dataclass
class PlatformSetting:
    build_target: str = ""
    max_size: int | None = None
    compression: int | None = None
    compression_line: int | None = None
    format: int = AUTOMATIC_FORMAT
    format_line: int | None = None
    max_size_line: int | None = None
    overridden: bool = False


def texture_platforms(lines: list[str]) -> list[PlatformSetting]:
    platforms: list[PlatformSetting] = []
    inside = False
    for number, line in enumerate(lines, start=1):
        if line.startswith("  platformSettings:"):
            inside = True
            continue
        if not inside:
            continue
        if line.startswith("  ") and not line.startswith("  -") and not line.startswith("    "):
            break  # next top-level importer key
        if PLATFORM_ENTRY_RE.match(line):
            platforms.append(PlatformSetting())
            continue
        match = PLATFORM_KEY_RE.match(line)
        if not match or not platforms:
            continue
        key, value = match.groups()
        current = platforms[-1]
        if key == "buildTarget":
            current.build_target = value
        elif key == "maxTextureSize" and value.lstrip("-").isdigit():
            current.max_size, current.max_size_line = int(value), number
        elif key == "textureFormat" and value.lstrip("-").isdigit():
            current.format, current.format_line = int(value), number
        elif key == "textureCompression" and value.lstrip("-").isdigit():
            current.compression, current.compression_line = int(value), number
        elif key == "overridden":
            current.overridden = value == "1"
    return platforms


def effective_platform(platforms: list[PlatformSetting], platform: str) -> PlatformSetting | None:
    for setting in platforms:
        if setting.build_target == platform and setting.overridden:
            return setting
    for setting in platforms:
        if setting.build_target == "DefaultTexturePlatform":
            return setting
    return None


def explicit_format(setting: PlatformSetting) -> bool:
    return setting.format >= 0


def uncompressed_storage(setting: PlatformSetting) -> tuple[str, int, int | None] | None:
    """(what the setting says, bytes per pixel, .meta line) when the texture ships uncompressed."""
    if explicit_format(setting):
        if setting.format not in UNCOMPRESSED_FORMATS:
            return None
        name, bpp = UNCOMPRESSED_FORMATS[setting.format]
        return f"Format is {name}", bpp, setting.format_line
    if setting.compression == UNCOMPRESSED:
        return "Compression is None", UNCOMPRESSED_AUTOMATIC_BPP, setting.compression_line
    return None


def texture_mipmaps(lines: list[str]) -> bool:
    """Generate Mipmaps from the importer's mipmaps block (on unless the .meta says 0)."""
    for line in lines:
        match = MIPMAP_RE.match(line)
        if match:
            return match.group(1) == "1"
    return True


def check_texture(scan: Scan, asset: Path, meta: Path, lines: list[str]) -> None:
    setting = effective_platform(texture_platforms(lines), scan.platform)
    if setting is None:
        return
    try:
        size = image_size(read_head(asset), asset.suffix.lower())
    except OSError:
        return
    if size is None:
        return
    longest = max(size)
    max_size = setting.max_size or longest
    shipped = min(longest, max_size)
    where = f"{setting.build_target} override" if setting.overridden else "default platform setting"
    storage = uncompressed_storage(setting)
    if storage and shipped >= UNCOMPRESSED_MIN_PX:
        said, bpp, line = storage
        scale = shipped / longest
        width, height = max(1, round(size[0] * scale)), max(1, round(size[1] * scale))
        fix = (
            "set Format to Automatic (or a compressed format) unless this texture must stay lossless"
            if explicit_format(setting)
            else "set Compression to Normal Quality (or High Quality) unless this texture must stay lossless"
        )
        scan.add(
            "warning",
            "uncompressed-texture",
            meta,
            line,
            f"{said} in the {where} for a {size[0]}x{size[1]} source; "
            f"about {mb(mip_chain_bytes(width, height, bpp, texture_mipmaps(lines)))} in the build",
            fix,
        )
    if max_size > scan.max_texture_size and longest > scan.max_texture_size:
        scan.add(
            "warning",
            "texture-max-size",
            meta,
            setting.max_size_line,
            f"Max Size is {max_size} in the {where} for a {size[0]}x{size[1]} source",
            f"lower Max Size to {scan.max_texture_size} or less if the texture never fills that many pixels on screen",
        )


def check_audio(scan: Scan, asset: Path, meta: Path, lines: list[str]) -> None:
    format_line = next((n for n, line in enumerate(lines, start=1) if AUDIO_FORMAT_RE.match(line)), None)
    if format_line is None:
        return
    if int(AUDIO_FORMAT_RE.match(lines[format_line - 1]).group(1)) != PCM:
        return
    size = asset.stat().st_size
    if size < PCM_MIN_BYTES:
        return
    has_overrides = any(
        (match := AUDIO_OVERRIDES_RE.match(line)) and match.group(1) is None for line in lines
    )
    if has_overrides:
        scan.add(
            "note",
            "audio-platform-override",
            meta,
            format_line,
            f"default Compression Format is PCM for a {mb(size)} clip, and platform overrides exist",
            "check the override for your build target in the Inspector",
        )
        return
    scan.add(
        "warning",
        "pcm-audio",
        meta,
        format_line,
        f"Compression Format is PCM for a {mb(size)} clip",
        "use Vorbis (music, ambience) or ADPCM (short effects) unless the clip must stay lossless",
    )


def check_meta(scan: Scan, asset: Path, meta: Path) -> None:
    if not meta.is_file():
        return
    try:
        lines = meta.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return
    scan.files_checked += 1
    importer = next((line for line in lines if IMPORTER_RE.match(line)), "")
    suffix = asset.suffix.lower()
    if importer == "TextureImporter:" and suffix in TEXTURE_EXTENSIONS:
        check_texture(scan, asset, meta, lines)
    elif importer == "AudioImporter:" and suffix in AUDIO_EXTENSIONS:
        check_audio(scan, asset, meta, lines)


def in_streaming_assets(parts: tuple[str, ...]) -> bool:
    """Only Assets/StreamingAssets is special; a StreamingAssets folder deeper down is ordinary."""
    return parts[:2] == ("Assets", "StreamingAssets")


def check_special_folder(scan: Scan, asset: Path, parts: tuple[str, ...]) -> None:
    try:
        size = asset.stat().st_size
    except OSError:
        return
    if size < LARGE_FILE_BYTES:
        return
    if in_streaming_assets(parts):
        scan.add(
            "note",
            "large-streaming-asset",
            asset,
            None,
            f"{mb(size)} file in StreamingAssets is copied into the build as is",
            "keep it only if the game reads it at runtime",
        )
    elif "Resources" in parts:
        scan.add(
            "warning",
            "large-resources-asset",
            asset,
            None,
            f"{mb(size)} file in a Resources folder ships whether or not anything loads it",
            "move it out of Resources if no Resources.Load call needs it, or load it through Addressables",
        )


# ---------------------------------------------------------------------------
# project walk


def gltfast_installed(root: Path) -> bool:
    for name in ("manifest.json", "packages-lock.json"):
        path = root / "Packages" / name
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, RecursionError):
            continue
        dependencies = data.get("dependencies") if isinstance(data, dict) else None
        if not isinstance(dependencies, dict):
            continue
        if any(package in dependencies for package in GLTFAST_PACKAGES):
            return True
    return False


def is_ignored(name: str, streaming: bool = False) -> bool:
    """Names the Unity asset database skips. Under Assets/StreamingAssets, dot-names are kept."""
    if name.startswith(".") and not streaming:
        return True
    return name.endswith("~") or name.lower() == "cvs" or name.endswith(".tmp")


def run(root: Path, platform: str, max_texture_size: int) -> Scan:
    scan = Scan(root=root, platform=platform, max_texture_size=max_texture_size)
    with_gltfast = gltfast_installed(root)
    skipped_models: list[Path] = []
    for folder, dirs, files in os.walk(root / "Assets"):
        folder_path = Path(folder)
        parts = folder_path.relative_to(root).parts
        streaming = in_streaming_assets(parts)
        dirs[:] = sorted(d for d in dirs if not is_ignored(d, in_streaming_assets((*parts, d))))
        names = set(files)
        for name in sorted(files):
            if is_ignored(name, streaming) or name.endswith(".meta"):
                continue
            asset = folder_path / name
            if not asset.is_file():
                continue  # named pipes, sockets and broken links would block or fail a read
            suffix = asset.suffix.lower()
            if streaming:
                pass  # shipped byte for byte; the importers' settings do not apply
            elif suffix in (".glb", ".gltf"):
                if with_gltfast:
                    check_gltf(scan, asset)
                else:
                    skipped_models.append(asset)
            elif f"{name}.meta" in names:
                check_meta(scan, asset, folder_path / f"{name}.meta")
            check_special_folder(scan, asset, parts)
    if skipped_models:
        scan.add(
            "note",
            "gltf-not-checked",
            skipped_models[0],
            None,
            f"{len(skipped_models)} glTF model(s) found, but glTFast is not in Packages/manifest.json",
            "check how your glTF importer stores textures; this tool only knows glTFast",
        )
    return scan


def find_project_root(start: Path) -> Path | None:
    for folder in (start, *start.parents):
        if (folder / "Assets").is_dir() and (folder / "ProjectSettings").is_dir():
            return folder
    return None


LEVEL_ORDER = {"error": 0, "warning": 1, "note": 2}


def sort_key(issue: Issue) -> tuple:
    return (LEVEL_ORDER[issue.level], issue.file, issue.line or 0, issue.code)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="check_unity_build_size.py",
        description=(
            "Read-only check of a Unity 6 project for assets that bloat the player build:\n"
            "glTFast models with large embedded images, uncompressed or oversized textures,\n"
            "PCM audio, and large files in Resources or StreamingAssets."
        ),
        epilog=(
            "example:\n"
            "  python scripts/check_unity_build_size.py path/to/MyGame\n"
            "  python scripts/check_unity_build_size.py . --max-texture-size 1024 --json\n\n"
            "exit codes: 0 no errors (warnings allowed), 1 errors found (or warnings with --strict),\n"
            "            2 usage problem or not a Unity project"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "project_dir",
        nargs="?",
        default=".",
        metavar="PROJECT_DIR",
        help="Unity project folder (the one holding Assets/ and ProjectSettings/), or any folder inside it. "
        "Default: current folder.",
    )
    parser.add_argument("--json", action="store_true", help="print one JSON object instead of text")
    parser.add_argument("--strict", action="store_true", help="exit 1 when there are warnings too")
    parser.add_argument(
        "--max-issues",
        type=int,
        default=50,
        metavar="N",
        help="print at most N issues, warnings before notes (default: 50; 0 = no limit)",
    )
    parser.add_argument(
        "--max-texture-size",
        type=int,
        default=DEFAULT_MAX_TEXTURE_SIZE,
        metavar="PX",
        help=f"largest texture edge you accept in the build (default: {DEFAULT_MAX_TEXTURE_SIZE})",
    )
    parser.add_argument(
        "--platform",
        default=DEFAULT_PLATFORM,
        metavar="NAME",
        help="texture platform override to honour, as written in .meta buildTarget: Standalone "
        f"(Windows, macOS, Linux), Android, iPhone (iOS) or WebGL (Web). Default: {DEFAULT_PLATFORM}. "
        "Pass the platform you ship, or that platform's overrides are not checked.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")  # non-ASCII paths on a legacy Windows console
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.max_issues < 0:
        parser.error("--max-issues must be 0 or more")
    if args.max_texture_size < 1:
        parser.error("--max-texture-size must be 1 or more")

    start = Path(args.project_dir).expanduser()
    if not start.is_dir():
        print(f"error: '{args.project_dir}' is not a folder", file=sys.stderr)
        return 2
    root = find_project_root(start.resolve())
    if root is None:
        print(
            f"error: '{args.project_dir}' is not inside a Unity project "
            "(no folder with both Assets/ and ProjectSettings/ found)",
            file=sys.stderr,
        )
        return 2

    scan = run(root, args.platform, args.max_texture_size)
    issues = sorted(scan.issues, key=sort_key)
    errors = [i for i in issues if i.level == "error"]
    warnings = [i for i in issues if i.level == "warning"]
    notes = [i for i in issues if i.level == "note"]
    limit = args.max_issues or len(issues)
    shown = issues[:limit]
    truncated = len(shown) < len(issues)

    if args.json:
        payload = {
            "tool": TOOL,
            "schema": SCHEMA,
            "root": root.as_posix(),
            "files_checked": scan.files_checked,
            "error_count": len(errors),
            "warning_count": len(warnings),
            "note_count": len(notes),
            "errors": [i.as_json() for i in shown if i.level == "error"],
            "warnings": [i.as_json() for i in shown if i.level == "warning"],
            "notes": [i.as_json() for i in shown if i.level == "note"],
            "truncated": truncated,
        }
        print(json.dumps(payload, indent=2))
    else:
        for issue in shown:
            location = f"{issue.file}:{issue.line}" if issue.line else issue.file
            print(f"{issue.level.upper()} {location}: {issue.message}")
            print(f"  fix: {issue.fix}")
        if truncated:
            print(f"... and {len(issues) - len(shown)} more")
        print(
            f"Summary: {len(errors)} errors, {len(warnings)} warnings, {len(notes)} notes "
            f"in {scan.files_checked} files checked"
        )

    if errors or (args.strict and warnings):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
