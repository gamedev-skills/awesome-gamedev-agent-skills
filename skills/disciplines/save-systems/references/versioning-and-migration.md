# Save versioning, migration, and robustness

Contents: the version field; the migration chain; backups and rollback; format
trade-offs; load-time validation checklist; where saves live and cloud sync
(Godot, Unity, Unreal, Steam Cloud, consoles); what to store vs recompute.

Saves outlive the code that wrote them. A player who saved in v1.0 expects to
load in v1.4 after an update. Plan for schema evolution from the first release.

## The version field is non-negotiable

Stamp every save with an integer `version` (or a structured `{major, minor}` if
you need it). On load:

1. Read `version`.
2. If it is **newer** than the running build → refuse with a clear message
   ("This save is from a newer version"). Do not guess at fields you don't know.
3. If it is **older** → run migrations in sequence until it matches the current
   version.
4. Validate, then instantiate.

Prefer a single monotonic integer. Semantic two-part versions are only worth it
if you genuinely branch save compatibility across release lines.

## The migration chain

Write each migration as a **pure function** `vN -> vN+1` and apply them in order.
This keeps any version reachable to current with small, testable steps — never a
giant "convert anything to latest" function.

```python
SAVE_VERSION = 4

MIGRATIONS = {
    1: migrate_1_to_2,   # added "flags" map
    2: migrate_2_to_3,   # split "name" into first/last
    3: migrate_3_to_4,   # inventory items gained a "durability" field
}

def upgrade(data):
    v = data.get("version", 1)
    while v < SAVE_VERSION:
        data = MIGRATIONS[v](data)
        v += 1
        data["version"] = v
    return data
```

Guidelines:

- **Additive changes are easy**: new field with a default. The migration just
  inserts the default for old saves.
- **Renames/restructures**: move/transform in the migration; never read both old
  and new names in game code.
- **Removed fields**: drop them in the migration so later steps see a clean shape.
- **Keep old migrations forever.** Deleting `migrate_1_to_2` strands every v1
  save. They are cheap to keep and must remain a faithful record.
- **Test the chain**: keep a corpus of real saves from each shipped version and
  assert they load after every change (this is your regression net).

## Backups and rollback

- Before overwriting, copy the current save to `*.bak`. On a failed load of the
  primary, try the backup automatically.
- For autosaves, rotate a small ring (autosave_0..2) so a bad autosave doesn't
  destroy the only recent state.
- Consider a checksum/hash of the payload to detect truncation or corruption
  (distinct from anti-tamper, which a determined local player can always defeat).

## Format trade-offs

| Format | Pros | Cons | Use when |
|---|---|---|---|
| JSON / text | Human-readable, debuggable, diff-able, easy migration | Larger, slower, trivially editable | Default; most games |
| Binary (engine) | Compact, fast, mildly opaque | Hard to debug/migrate, version-fragile | Large state, perf-critical |
| Key/value store | Simple, robust per-key | No structure, manual schema | Settings, small flag sets |
| Cloud KV (e.g. DataStore) | Cross-device | Quotas, latency, conflicts | Online/cross-device saves |

Whatever the on-disk format, keep an **in-memory dictionary/struct** as the
canonical shape and (de)serialize at the boundary. Migrations then operate on
that neutral shape, not on format-specific bytes.

## Load-time validation checklist

- Required keys present; types correct (string vs number vs bool).
- Numbers within sane ranges (no NaN/Infinity; hp ≥ 0; indices in bounds).
- Enum/id values still exist in current content (an item id removed in a patch
  must be handled — drop it or substitute, don't crash).
- References resolve (a quest id points to a known quest).
- On any failure: log, fall back to backup, and if all else fails, fail *loudly*
  to the player rather than silently loading a broken state.

## Where saves live, and cloud sync

Write saves to the per-user data folder the engine gives you, never next to the
executable (often read-only, and replaced by updates):

- **Godot 4.7** `user://` — Windows `%APPDATA%\Godot\app_userdata\[project]`,
  macOS `~/Library/Application Support/Godot/app_userdata/[project]`, Linux
  `~/.local/share/godot/app_userdata/[project]`. Turn on
  `application/config/use_custom_user_dir` (optionally with
  `custom_user_dir_name`) to drop the `Godot/app_userdata` part before you ship,
  because changing it later moves every player's saves. Web exports store
  `user://` in the browser's IndexedDB.
- **Unity 6.3** `Application.persistentDataPath` — Windows
  `%userprofile%\AppData\LocalLow\<company>\<product>`, Linux
  `~/.config/unity3d/<company>/<product>`, macOS player
  `~/Library/Application Support/unity.<company>.<product>`; Web uses IndexedDB;
  tvOS returns an empty string (no persistent folder). Changing the company or
  product name changes the folder.
- **Unreal 5.8** `UGameplayStatics::SaveGameToSlot` / `AsyncSaveGameToSlot`
  with a `USaveGame` subclass; the platform layer picks the folder and, on
  consoles, the platform save API.

**Steam Cloud.** Auto-Cloud syncs files under the root paths you configure in
Steamworks (for example `WinAppDataRoaming`, `WinAppDataLocalLow`,
`MacAppSupport`, `LinuxXdgDataHome`); the ISteamRemoteStorage API is the
alternative when you need control. Files upload after the game exits and
download before the next launch, so a save written while the game runs is not
in the cloud yet. Choose the Cross-Platform OS setting for each root (with root
overrides where the folder differs per OS) even for a single-platform game: a
root locked to one OS will not sync to other platforms if you add them later.
Set the per-user byte and file quotas in the app admin panel first; Steam Cloud
is not active without them. Keep the `.tmp` file out of the synced pattern.
Games that opt into Dynamic Cloud Sync (Steam Deck suspend) can receive changed
files mid-session and must reload them. To test Auto-Cloud before release, ask the
user to open the Steam console (`steam://open/console`), run
`testappcloudpaths <AppId>` and `set_spew_level 4 4`, launch the game, save, quit,
and report the upload lines; Steam also logs to `logs/cloud_log.txt` in its
install folder.

**Consoles and mobile** have platform save APIs, storage limits and
certification rules; follow the platform's documentation rather than raw file
paths there.

## What to store vs recompute

- **Store** authoritative, non-derivable state: choices, unlocked flags, RNG
  seed, inventory, positions.
- **Recompute** derived data on load (full stat tables from base + modifiers,
  procedural maps from the seed). Saving derived data invites desync when the
  formula changes in a patch — and bloats the file.
