---
name: godot-export
description: >
  Export and build a Godot 4.7 project for distribution: install export templates,
  define export presets (Windows/macOS/Linux/Web/Android), run headless command-line
  exports for CI, and handle web (HTML5) COOP/COEP and dedicated-server/headless
  builds. Use when exporting a Godot game, configuring export_presets.cfg, building
  for web/desktop/mobile, or automating builds from the command line.
---

# Godot Export & Builds (4.x)

Turn a project into runnable platform builds via export presets and the command line, and
handle the web/dedicated-server gotchas. Targets **Godot 4.7**.

## When to use

- Use when producing a shippable build: installing export templates, creating/editing
  export presets, exporting from the editor or headless CLI (CI), or troubleshooting web
  (HTML5) and dedicated-server exports.

**When *not* to use:** storefront publishing flows → `steam-publish`/`itch-publish`; the
networking code of a server → `godot-multiplayer` (this skill covers building it headless).

## Core workflow

1. **Install export templates** matching your engine version: Editor menu >
   *Manage Export Templates* (download), or install the `.tpz` offline. Versions must
   match the editor exactly. Since 4.7 the downloader can fetch templates for a single
   platform or architecture instead of the full set.
2. **Add export presets** in *Project > Export*: pick a platform (Windows Desktop, macOS,
   Linux, Web, Android, iOS), set the export path, icons, features, and resource
   include/exclude filters. Presets are saved to `export_presets.cfg`.
3. **Export from the editor** with *Export Project* (release) or *Export PCK/ZIP*.
4. **Or export headless from the CLI** for automation/CI using
   `--export-release "<preset name>" <output path>`.
5. **Per platform:** Web needs cross-origin isolation (COOP/COEP) only if the preset's
   *Thread Support* is on (off by default); Android needs the SDK/keystore; macOS/iOS need
   signing for distribution.
6. **Smoke-test the build** on the target before shipping — exported builds use `res://`
   read-only; write to `user://`.

## Patterns

### 1. Headless CLI export (CI-friendly)

```bash
# Preset name must match exactly what's in Project > Export (quote it).
# Run from the project directory (where project.godot lives).
# The output folder must already exist; Godot does not create it.
mkdir -p build/windows build/linux build/web
godot --headless --export-release "Windows Desktop" build/windows/game.exe
godot --headless --export-release "Linux"           build/linux/game.x86_64
godot --headless --export-release "Web"             build/web/index.html

# Debug build (includes debug symbols / remote debug):
godot --headless --export-debug "Windows Desktop" build/windows/game_debug.exe

# Export only the data pack (no executable):
godot --headless --export-pack "Linux" build/game.pck

# Export only files changed since the given base pack(s):
godot --headless --export-patch "Linux" build/patch1.pck --patches build/game.pck
```

### 2. Run a project headless (dedicated server / tests)

```bash
# No window/GPU — for a server build or automated runs.
godot --headless --path . res://server_main.tscn
# Quit after N main-loop iterations (frames, NOT seconds) — handy for a headless smoke test:
godot --headless --path . --quit-after 600
```

### 3. Detect the build context at runtime

```gdscript
func _ready() -> void:
    if OS.has_feature("dedicated_server") or DisplayServer.get_name() == "headless":
        _start_server_only()          # skip rendering/UI on a headless server
    if OS.has_feature("web"):
        _apply_web_tweaks()
    # Custom feature tags (added per preset) are also queryable:
    # if OS.has_feature("demo"): limit_content()
```

### 4. Choose write paths that survive export

```gdscript
# res:// is READ-ONLY in exported games. Always write to user://.
func save_path() -> String:
    return "user://savegame.tres"     # resolves to the OS app-data dir

func _ready() -> void:
    print(OS.get_user_data_dir())     # where user:// actually lives
```

## Pitfalls

- **"No export template found".** Templates must match the exact editor version (incl.
  beta/rc). Re-download via *Manage Export Templates* after upgrading Godot.
- **Preset name mismatch in CLI.** `--export-release "Windows"` fails if the preset is
  named `"Windows Desktop"`. Names are case- and space-sensitive; quote them.
- **Web build shows a blank page / threads error.** Builds with the preset's *Thread
  Support* option enabled require the server to send
  `Cross-Origin-Opener-Policy: same-origin` and `Cross-Origin-Embedder-Policy: require-corp` (cross-origin isolation for
  `SharedArrayBuffer`). Must be served over HTTP(S), not opened as a `file://`. itch.io has
  a "SharedArrayBuffer support" toggle for this. If the host cannot set headers (GitHub
  Pages), leave *Thread Support* off — the default since 4.3.
- **Writing to `res://` at runtime fails** in exports (read-only, packed). Use `user://`.
- **Missing resources in the build.** Non-resource files (e.g. external `.json`, `.txt`)
  are not auto-included — add them via the preset's *Resources > Filters to export
  non-resource files* (e.g. `*.json`).
- **Android export needs setup**: Android SDK/JDK paths in Editor Settings, a debug or
  release **keystore**, and the `INTERNET` permission for networked games.
- **macOS/iOS distribution requires signing/notarization**; unsigned macOS apps are
  blocked by Gatekeeper.
- **Debug vs release.** `--export-debug` enables remote debugging and debug checks; ship
  `--export-release`.

## References

- For the `export_presets.cfg` structure, all useful CLI flags, custom feature tags,
  PCK/expansion patching, encryption, and per-platform setup (Android keystore, macOS
  signing, web headers), read `references/presets-and-cli.md`.

## Related skills

- `godot-multiplayer` — the dedicated-server code you export headless.
- `steam-publish` / `itch-publish` — getting the build to players.
- `prototype-fast` / `game-jam` — quick web/desktop builds for sharing.
