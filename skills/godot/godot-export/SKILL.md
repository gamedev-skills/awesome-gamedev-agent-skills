---
name: godot-export
description: >
  Exports Godot 4.7 projects: templates, export_presets.cfg for desktop, Web and Android,
  command-line exports and web COOP/COEP headers. Use on "No export template found", a blank web
  build, a SharedArrayBuffer error or files missing after export. Not for tests in CI
  (`godot-gdscript-headless-testing`), store uploads (`steam-publish`, `itch-publish`) or netcode
  (`godot-multiplayer`).
---

# Godot Export & Builds (4.x)

Turn a project into builds from export presets on the command line, then prove the build
runs. Targets **Godot 4.7**; export templates must match the editor version exactly, so
read `config/features` in `project.godot` and the CI's Godot version first.

## Workflow

1. **Read `export_presets.cfg`.** Each `[preset.N]` has a `name` (what the CLI wants), a
   `platform` and an `export_path`. If the file is missing, create presets in
   *Project > Export* or ask the user to; avoid hand-writing a full preset from nothing.
2. **Install matching templates** (*Editor > Manage Export Templates*, or unpack the
   `.tpz` so its files land in the folder the error message names, for example
   `~/.local/share/godot/export_templates/4.7.2.stable/` on Linux). `--export-pack` needs
   none.
3. **Export from the CLI**, from the project folder, into a folder that already exists:
   `godot --headless --export-release "<preset name>" build/<platform>/<file>`.
4. **Per platform:** Web needs COOP/COEP headers only when the preset's *Thread Support* is
   on (off by default); Android needs SDK paths and a keystore; macOS needs signing and
   notarization to pass Gatekeeper.
5. **Verify before you finish:**
   - The export command exits 0 and the output file exists. A non-zero exit always means
     failure (missing template, unknown preset, unwritable path); the reason is in the log.
   - Smoke-run the exported data without templates: `godot --headless --path <project> --export-pack "<preset>" build/game.pck`,
     then `godot --headless --main-pack build/game.pck --quit-after 300 > run.log 2>&1` and
     `grep -nE "SCRIPT ERROR|^ERROR:" run.log`. This catches files the preset's filters left
     out and `res://` writes, because it loads only what was packed.
   - For a Linux or server build, run the binary itself the same way:
     `./build/linux/game.x86_64 --headless --quit-after 300`.
   - Platforms you cannot run here (consoles, iOS, a signed macOS app, phones): ask the user
     to launch the build on the device and report whether it starts, saves and loads.

## Patterns

### 1. Command-line exports

```bash
mkdir -p build/windows build/linux build/web          # Godot will not create the folder
godot --headless --export-release "Windows Desktop" build/windows/game.exe
godot --headless --export-release "Linux"           build/linux/game.x86_64
godot --headless --export-release "Web"             build/web/index.html
godot --headless --export-debug   "Windows Desktop" build/windows/game_debug.exe
godot --headless --export-pack    "Linux"           build/game.pck   # .zip for a ZIP pack
godot --headless --export-patch   "Linux"           build/patch1.pck --patches build/game.pck
```

### 2. Detect the build at runtime

```gdscript
func _ready() -> void:
    if OS.has_feature("dedicated_server") or DisplayServer.get_name() == "headless":
        start_server_only()           # skip rendering and UI
    if OS.has_feature("web"):
        apply_web_settings()
    if OS.has_feature("demo"):        # a custom tag set in one preset's Features
        limit_content()
```

### 3. Write paths that survive export

```gdscript
const SAVE_PATH := "user://savegame.tres"   # res:// is read-only inside a .pck

func _ready() -> void:
    print(OS.get_user_data_dir())           # where user:// lives on this platform
```

## Gotchas

- **`No export template found at the expected path`** → templates are missing or for another
  version (including beta/rc). Install the exact version; 4.7 can download one platform's
  templates instead of the full set.
- **`Invalid export preset name: ...`** → names are case- and space-sensitive; the output
  then lists the presets it found. Quote the name.
- **`Can't open file for writing`** → the output folder does not exist. `mkdir -p` first.
- **A file is missing only in the build** → non-resource files (`.json`, `.txt`, `.csv`) are
  not exported unless listed in the preset's *Filters to export non-resource files*
  (`include_filter="*.json"`). Resources excluded by `exclude_filter` vanish too.
- **Saving works in the editor, fails in the build** → the game writes under `res://`. Use
  `user://`.
- **Web build: blank page or `SharedArrayBuffer` error** → *Thread Support* is on and the host
  does not send `Cross-Origin-Opener-Policy: same-origin` and
  `Cross-Origin-Embedder-Policy: require-corp`. Turn threads off, enable the host's option
  (itch.io has one), or use the PWA option that adds the headers. `file://` never works.
- **Web build looks different** → web always uses the Compatibility renderer.
- **C# project will not export to web** → not supported in Godot 4; see `godot-csharp`.
- **Secrets end up in Git** → keystore passwords and encryption keys live in
  `.godot/export_credentials.cfg`, not `export_presets.cfg`. Keep `.godot/` ignored and
  supply secrets in CI through environment variables or a restored file.
- **Shipping a debug build** → `--export-debug` keeps the remote debugger and debug checks;
  ship `--export-release`.

## References

- Read `references/presets-and-cli.md` for the `export_presets.cfg` layout, every useful CLI
  flag, feature tags, web, Android and Apple setup, PCK patches and DLC, and why PCK
  encryption needs custom templates.

## Related skills

- `godot-gdscript-headless-testing`: tests before the export step in CI.
- `godot-multiplayer`: the dedicated-server code you export.
- `godot-csharp`: .NET export limits.
- `steam-publish` / `itch-publish`: getting the build to players.

## Version notes

Last verified: 2026-11-11 against the Godot 4.7.2 CLI help and a 4.7.2 headless export of a
test project (pack export and `--main-pack` run; template exports were checked only for
their failure messages, since no templates were installed).

- Godot 4.7.2 (August 2026) is the current stable release; 4.8 is in beta.
- Web *Thread Support* is off by default since 4.3; web exports always use Compatibility.
- 4.7 adds per-platform template downloads. Confidential export options have lived in
  `.godot/export_credentials.cfg` since at least 4.2.
- Sources: [Godot releases](https://github.com/godotengine/godot/releases),
  [Exporting projects](https://docs.godotengine.org/en/stable/tutorials/export/exporting_projects.html),
  [Exporting for the Web](https://docs.godotengine.org/en/stable/tutorials/export/exporting_for_web.html),
  [Command line tutorial](https://docs.godotengine.org/en/stable/tutorials/editor/command_line_tutorial.html),
  [main.cpp @ 4.7.2](https://github.com/godotengine/godot/blob/4.7.2-stable/main/main.cpp).
