---
name: save-systems
description: >
  Engine-neutral save and load with Godot and Python code: what to serialize, slots and autosave,
  atomic writes and versioned migration. Use for save/load or a continue button, or saves that
  corrupt after a crash or break after a patch. Not for Roblox DataStores (`roblox-datastores`),
  data assets (`godot-resources`, `unity-scriptableobjects`) or genre save screens (`rpg`,
  `visual-novel`).
---

# Save systems

A save file is a serialized snapshot of game state that must survive crashes, restarts and
patches. The hard parts are choosing what to save, writing it so a crash mid-save cannot
destroy it, and reading old saves after an update. This skill owns the file: format, writes,
versioning, slots and location. Genre skills decide what goes in it.

## When to use

- Persisting progress: stats, inventory ids, world flags, settings, positions, seeds.
- Save slots, quicksave, autosave, crash-safe writes, backups.
- Old saves failing after a code or content change.

**Not this skill:** Roblox cloud persistence (`roblox-datastores`), the data model itself
(`godot-resources`, `unity-scriptableobjects`), rebinding data shape (`input-systems`), save
screens and rollback in a visual novel (`visual-novel`).

## Core workflow

1. **Find what exists.** Grep for the current save code (`FileAccess`, `ConfigFile`,
   `ResourceSaver`, `PlayerPrefs`, `SaveGameToSlot`, `persistentDataPath`) and any shipped
   saves. If players already have saves, every change below needs a migration.
2. **Save data, not objects.** Ids, numbers, flags and the RNG seed; rebuild nodes and objects
   from that data on load. Live references and node paths do not survive a refactor.
3. **Stamp an integer `version`** in every save from the first release.
4. **Start with JSON** (readable, diffable, easy to migrate); move to binary only for size or
   speed you have measured.
5. **Write atomically**: temp file, keep the previous save as `.bak`, rename into place.
6. **Load defensively**: parse, read version, refuse newer saves, migrate older ones step by
   step, validate, then apply. Fall back to the backup on failure and tell the player.
7. **Autosave at safe boundaries** (checkpoint, level change), throttled, into its own slot.
8. **Run the checks** below, then ask the user for the quit-and-relaunch test.

## Patterns

### 1. State as plain data

```gdscript
func capture_state() -> Dictionary:
    return {
        "version": SAVE_VERSION,
        "player": { "hp": player.hp, "pos": [player.position.x, player.position.y] },
        "inventory": player.inventory.to_array(),  # ids + counts, not Item nodes
        "flags": world.flags,
        "seed": world.seed,                        # regenerate procedural content
    }

func apply_state(data: Dictionary) -> void:        # rebuild from data; no live references
    player.hp = int(data["player"]["hp"])
    player.position = Vector2(data["player"]["pos"][0], data["player"]["pos"][1])
    player.inventory.from_array(data["inventory"])
    world.flags = data["flags"]
```

### 2. Atomic, crash-safe write (temp + rename)

```gdscript
# Godot 4.7. Write a temp file, keep the previous save as .bak, then rename.
func save_atomic(path: String, data: Dictionary) -> Error:
    var tmp := path + ".tmp"
    var f := FileAccess.open(tmp, FileAccess.WRITE)
    if f == null:
        return FileAccess.get_open_error()       # disk full, read-only, no permission...
    if not f.store_string(JSON.stringify(data)):
        return ERR_FILE_CANT_WRITE
    f.close()                                    # flushes Godot's buffer to the OS
    if FileAccess.file_exists(path):
        DirAccess.rename_absolute(path, path + ".bak")   # keep the last good save
    return DirAccess.rename_absolute(tmp, path)

func load_save(path: String) -> Dictionary:      # empty = nothing loadable
    for p in [path, path + ".bak"]:              # .bak covers a crash between renames
        if FileAccess.file_exists(p):
            var data = JSON.parse_string(FileAccess.get_file_as_string(p))
            if data is Dictionary and data.has("version"):
                data["version"] = int(data["version"])   # JSON numbers load as float
                return data
    return {}
# WRONG: opening `path` directly and writing in place — a crash mid-write leaves a
# truncated, unloadable save and destroys the player's progress.
```

A crash leaves the old save, the new one, or (between the two renames) only the `.bak`, which
the loader tries next. `rename()` replaces the target atomically on POSIX within one volume, but
Godot's Windows `rename_absolute` deletes the target and then moves, so Windows relies on the
`.bak` as well. Neither `flush()` nor `close()` calls `fsync`, so a power cut right after a save
can still lose the newest file. Check every returned `Error` and tell the player when a save
fails.

### 3. Versioned load with migration

```python
SAVE_VERSION = 3

def load_save(raw_bytes):
    data = parse(raw_bytes)                  # JSON/binary -> dict
    v = int(data.get("version", 1))          # no field = the first shipped schema
    if v > SAVE_VERSION:
        raise NewerSaveError(v)              # save is from a newer build; refuse
    while v < SAVE_VERSION:                   # apply migrations in order, v -> v+1
        data = MIGRATIONS[v](data)
        v += 1
        data["version"] = v
    validate(data)                            # check required keys / ranges
    return data

# Each migration is a pure function from one version's shape to the next.
def migrate_1_to_2(d):
    d["flags"] = {k: True for k in d.pop("completed_quests", [])}  # list -> set-map
    return d
def migrate_2_to_3(d):
    d.setdefault("difficulty", "normal")      # new field: old saves get the default
    return d
MIGRATIONS = {1: migrate_1_to_2, 2: migrate_2_to_3}
```

Keep every migration forever; deleting one strands every save of that version.

### 4. Slots and throttled autosave

```gdscript
const SLOT_PATH := "user://save_%d.json"      # manual slots 0..N
const AUTOSAVE_PATH := "user://autosave.json"  # separate file: never clobbers a slot
var _autosave_cooldown := 0.0

func autosave_if_due(dt: float) -> void:
    _autosave_cooldown -= dt
    if _autosave_cooldown <= 0.0:
        save_atomic(AUTOSAVE_PATH, capture_state())
        _autosave_cooldown = 60.0             # at most once a minute; also save on checkpoints
```

### 5. Round-trip and corruption test (headless)

```gdscript
# tools/save_roundtrip_test.gd: godot --headless --path . --script res://tools/save_roundtrip_test.gd
extends SceneTree

const PATH := "user://test_save.json"

func _initialize() -> void:
    var saver = load("res://save.gd").new()      # the game's save_atomic / load_save
    var ok := true
    var first := {"version": 3, "player": {"hp": 7, "pos": [1.5, -2.0]}, "flags": {"met_guard": true}}
    var second := first.duplicate(true)
    second["player"]["hp"] = 4
    ok = ok and saver.save_atomic(PATH, first) == OK
    ok = ok and saver.save_atomic(PATH, second) == OK  # first is now the .bak
    var loaded: Dictionary = saver.load_save(PATH)
    # Compare fields, not whole Dictionaries: JSON turned hp 4 into 4.0, and 4 != 4.0 there.
    ok = ok and loaded.get("version") is int and loaded["player"]["hp"] == 4
    ok = ok and loaded["player"]["pos"] == [1.5, -2.0] and loaded["flags"] == second["flags"]
    var f := FileAccess.open(PATH, FileAccess.WRITE)   # simulate a truncated primary
    f.store_string("{\"version\": 3, \"pla")
    f.close()
    ok = ok and saver.load_save(PATH)["player"]["hp"] == 7          # fell back to .bak
    for p in [PATH, PATH + ".bak", PATH + ".tmp"]:
        DirAccess.remove_absolute(ProjectSettings.globalize_path(p))
    print("SAVE_ROUNDTRIP ", "ok" if ok else "FAIL")
    quit(0 if ok else 1)
```

Point `res://save.gd` at the game's own save script. The truncated file makes Godot print
`Parse JSON failed`; that line is expected here, and the test passes only if the `.bak` loads.

## Check it

1. Run the round-trip test: it must print `SAVE_ROUNDTRIP ok`.
2. Keep one real save per shipped version in a fixtures folder and load each through the
   migration chain in a test after every schema change.
3. Load a save stamped with a newer version and confirm it is refused with a message, not
   half-loaded.
4. Grep the save path for engine objects (`Node`, `Resource`, `var_to_str`, `store_var` with
   objects allowed); there should be none.
5. Ask the user to save mid-level, quit the game fully, relaunch, load, and report anything that
   differs (position, inventory, flags, quest state). For Steam Cloud, ask them to repeat it on a
   second machine and report whether the save arrived.

## Gotchas

- **No version field.** The first patch turns every existing save into guesswork.
- **Serializing engine objects or node paths** ties saves to scene structure; a rename breaks
  every old save.
- **In-place writes** corrupt saves on a crash or power loss. Write a temp file, keep a `.bak`.
- **Godot JSON turns every number into a float**: `version` 3 loads as `3.0`, so
  `MIGRATIONS.has(data["version"])` is false, whole-Dictionary `==` against the original fails,
  and integers above 2^53 (64-bit ids, big seeds) lose digits. Convert with `int()`, store big ids
  as strings, or wrap the state with `JSON.from_native()` / `JSON.to_native()`.
- **`JSON.parse_string` on a corrupt file** logs an engine error and returns `null`. Use a
  `JSON` instance and `parse()` when you need the error line and message for the player or log.
- **Loading objects from save files.** Godot `str_to_var` or `get_var` with objects allowed, a
  `ConfigFile` holding objects, or `ResourceLoader` on a `.tres` the player can swap will create
  an object whose script runs during the load. Saves get shared online; keep them plain data.
- **Floats and locale.** Hand-built text formats can write comma decimals in some locales. Use
  the engine's JSON or another locale-invariant serializer.
- **Autosave clobbering a manual save**, or firing mid-combat and saving an inconsistent state.
  Use a dedicated slot and safe boundaries.
- **Saving next to the executable**: often read-only, and replaced by updates. Use the engine's
  per-user folder (see the reference).
- **Trusting client saves online.** A local save is player-controlled; never use it as the
  authority for multiplayer or economy state.

## References

- `references/versioning-and-migration.md`: read when evolving a schema (additive, rename and
  removal migrations), keeping a save corpus, rotating backups, choosing JSON vs binary,
  writing load-time validation, finding where saves live per engine, or setting up Steam Cloud.

## Related skills

- `roblox-datastores`: cloud persistence, request limits, session locking.
- `godot-resources`, `unity-scriptableobjects`: the data model you serialize.
- `procedural-gen`: saving the seed and generator version instead of the world.
- `rpg`, `survival-crafting`, `visual-novel`: what each genre puts in the save.
- `steam-publish`: the Steamworks app admin pages where Steam Cloud is configured.

## Version notes

Last verified: 2026-11-11.

- Godot 4.7: `FileAccess.store_string` returns `bool`; `JSON.from_native`/`to_native` exist;
  Windows `DirAccess.rename` deletes the target before moving
  (`drivers/windows/dir_access_windows.cpp`). The round-trip test above ran on 4.7.2 headless.
- Steam Cloud: files sync after the game exits and before the next launch; byte and file quotas
  must be set before it works; Cross-Platform is the recommended OS setting for Auto-Cloud roots;
  Dynamic Cloud Sync can change files mid-session
  (https://partner.steamgames.com/doc/features/cloud).
