# SteamPipe: advanced build scripts, branches, CI/CD, troubleshooting

Depth for `steam-publish`. Read this when one depot and a single `app_build.vdf` aren't
enough — multiple platforms/languages, file filtering, beta branches, automated uploads, or
a build that won't go through. All file formats are Valve **KeyValues (VDF)**. Verify against
the primary doc: Steamworks → SDK → [Uploading to Steam](https://partner.steamgames.com/doc/sdk/uploading).

## 1. App build script with separate depot scripts

For apps with several depots, keep the app script thin and reference one depot script per
depot. Convention: `app_build_<AppID>.vdf` and `depot_build_<DepotID>.vdf`.

```text
// scripts/app_build_1000.vdf  — game 1000 with a Windows depot (1001) and a content depot (1002).
"AppBuild"
{
    "AppID"       "1000"
    "Desc"        "1.2.0"
    "ContentRoot" "..\content\"
    "BuildOutput" "..\output\"

    // Optional top-level switches:
    // "Preview" "1"          // dry run: write manifest/logs, upload nothing
    // "SetLive" "beta-qa"    // auto-set live on this BETA branch (never "default")
    // "Local"   "..\..\ContentServer\htdocs"   // build to a Local Content Server instead

    "Depots"
    {
        "1001" "depot_build_1001.vdf"   // reference external depot scripts
        "1002" "depot_build_1002.vdf"
    }
}
```

```text
// scripts/depot_build_1002.vdf — file mapping, exclusions, and special file flags.
"DepotBuild"
{
    "DepotID" "1002"

    // Map a subtree into a folder inside the depot.
    "FileMapping"
    {
        "LocalPath" "bin\*"          // wildcards '*' and '?' allowed
        "DepotPath" "executables\"
        "Recursive" "1"
    }

    "FileExclusion" "*.pdb"          // drop debug symbols everywhere
    "FileExclusion" "bin\tools\*"    // drop a whole subtree

    // Mark files that the game/user writes at runtime so updates don't clobber them:
    "FileProperties"
    {
        "LocalPath"  "settings.cfg"
        "Attributes" "userconfig"    // user-modified: never overwritten, never flagged on verify
    }
    // "versionedconfig" is like userconfig but IS overwritten when you change it in the depot
    // (use only for genuine format changes/bug fixes).
}
```

Notes:
- `ContentRoot` can be overridden per depot inside a `DepotBuild`.
- `InstallScript "<file.vdf>"` marks and signs an install script the Steam client runs for any
  app mounting the depot (prerequisites, registry, shortcuts). Most games don't need one.
- You can name scripts anything; the `app_build_<AppID>` / `depot_build_<DepotID>` convention
  just keeps multi-app build machines organized.

## 2. Running builds (per platform)

```bash
# Windows
tools\ContentBuilder\builder\steamcmd.exe +login <account> +run_app_build ..\scripts\app_build_1000.vdf +quit

# Linux / macOS (bootstrap once, then build)
./tools/ContentBuilder/builder_linux/steamcmd.sh +login <account> +run_app_build ../scripts/app_build_1000.vdf +quit
```

On first use, enter credentials at the interactive prompts. Keep passwords out of argv,
shell history and logs. For unattended runs, provision and protect the login token as
described in section 4 rather than adding a password to these commands.

macOS first-run bootstrap: `cd tools/ContentBuilder/builder_osx`, `chmod +x steamcmd`,
`bash ./steamcmd.sh`, then `exit` once it reaches the `Steam>` prompt.

## 3. Branches (betas) — test before customers see it

The **default** branch is what customers get. Always validate a build on a beta branch first.

1. Create a branch on the **Builds** page in App Admin. Use a name with **no spaces**; add a
   **password** if it should be private (players type it under *Properties → Game Versions &
   Betas*). Set the password *before* setting any build live on the branch, or its contents
   are not private.
2. Upload your build (steamcmd, as above), or auto-target it with `"SetLive" "<branch>"`.
3. On the Builds page: select the branch in *Set build live for branch…*, **Preview Change**,
   then **Set Build Live Now**.
4. Opt in via the Steam client: right-click the game → *Properties* → *Game Versions &
   Betas* → pick the branch. Steam downloads it, replacing the installed branch.

Reminder: there is **no** way to auto-set the `default` branch live — promote a tested beta
build to default manually when you're confident. For a released game, that step also sends
an authorization prompt to the requesting account's Steam Mobile Authenticator (or SMS to
its phone number), so do it from an account that has one attached.

Games can also switch branches themselves through `ISteamApps` (`GetNumBetas`,
`GetBetaInfo`, `SetActiveBeta`, `GetCurrentBetaName`) — that is in-game API work, outside
this skill.

## 4. CI/CD upload (token-based login, no password in scripts)

steamcmd stores a login token in `config.vdf` after a successful interactive login with Steam
Guard. CI reuses that token instead of a password.

1. On the build machine (or once locally), run `steamcmd +login <username>`, enter the
   password and the Steam Guard code, type `info` to confirm "connected", then `quit`.
2. **Preserve `<Steam>/config/config.vdf` between CI runs** (cache it as a secret artifact).
   This file holds the refreshed login token.
3. Subsequent runs log in with **no password**: `steamcmd +login <username>`.

```yaml
# GitHub Actions sketch — restore the token, then build. Never echo the token.
# Store the base64 of config.vdf as a repo secret (e.g. STEAM_CONFIG_VDF).
# Assumes steamcmd is already installed on the runner and treats ~/Steam as <Steam>.
- name: Restore steam login token
  run: |
    mkdir -p ~/Steam/config
    echo "${{ secrets.STEAM_CONFIG_VDF }}" | base64 -d > ~/Steam/config/config.vdf
- name: Upload build to Steam
  run: |
    steamcmd +login "${{ secrets.STEAM_BUILD_ACCOUNT }}" \
      +run_app_build "$PWD/scripts/app_build_1000.vdf" +quit
```

- `<Steam>` is the folder steamcmd installs itself into, so it depends on how steamcmd was
  installed. After the first interactive login on the same image, look for the
  `config/config.vdf` that login wrote, and restore the token to that path.
- Pass `+run_app_build` an absolute path (as above) so it does not depend on the working
  directory.
- If a build run prints `Account Login Denied`, Steam Guard is blocking it. Run
  `set_steam_guard_code <code>` in steamcmd (code from the account's email), then retry login.
- Logging in with the password again issues a **new** Steam Guard token, which is then
  required to log in — avoid it in CI, or re-export `config.vdf` afterwards.
- Never print or commit `config.vdf`, the account password, or the Steam Guard code. Treat a
  leaked token as compromised and re-secure the account.

## 5. Patch-size hygiene (keep updates small)

SteamPipe diffs at ~1 MB chunk granularity and ships only changed chunks. To avoid bloated
updates:

- Don't compress or encrypt your own pack files in ways that cross asset boundaries — a small
  change then rewrites the whole compressed blob. Let Steam do compression on its side.
- Localize asset changes within pack files; avoid reshuffling asset order; keep pack files to
  ~1-2 GB and grouped by level/feature; add **new** pack files for new content instead of
  rewriting big existing ones.
- **Unreal Engine** pak alignment: build with `-patchpaddingalign=1048576 -blocksize=1048576`
  so re-alignments shift by SteamPipe's block size and patches stay small.

## 6. Steam Deck and Steam Machine compatibility review

A separate review from the release review: it never blocks release, but it sets the badge
players see (Verified, Playable, Unsupported, or Unknown until reviewed), with one rating for
Steam Deck, one for Steam Machine, and one for other SteamOS devices. Verified on Deck
implies Verified on Machine.

- **Getting reviewed:** Valve queues some games itself; partners with access can request one
  from *Steam Hardware Compatibility Review* under Technical Tools on the app landing page,
  choosing the branch to test (default otherwise). A standard build review must be finished
  first. Results arrive by email; they publish automatically after about a week. Uploading a
  fixing build before then delays publication and triggers a retest.
- **Verified checklist (both devices):** the default controller configuration reaches all
  content with no in-game setting changes; on-screen glyphs match the active controller (no
  keyboard/mouse glyphs while using a controller — the Steam Input API handles this); text
  entry opens the on-screen keyboard through the Steamworks API or offers a controller-usable
  entry; the default settings run at a playable framerate (30 fps at 800p on Deck, 1080p on
  Machine); no "unsupported OS/GPU" warnings; any launcher is fully controller-navigable.
- **Deck-only display checks:** a supported resolution (1280x800 preferred, or 1280x720) and
  no text smaller than 9 px tall at 1280x800 (12 px recommended).
- Windows-only games run through Proton; a Proton-specific blocker gives Unsupported until
  Valve fixes it and retests.

## 7. Troubleshooting table

| Symptom | Likely cause | Fix |
|---|---|---|
| `Failed to get application info for app NNNNN` | Wrong App ID, account doesn't own the app, or config never published | Verify App ID in the script; confirm ownership; **Publish** the app config in App Admin |
| `ERROR! Failed 'DepotBuild …' status = 6` | Build account lacks permission, or `ContentRoot`/`LocalPath` is wrong/empty | Grant *Edit App Metadata* + *Publish App Changes*; check paths are relative to the script and contain files |
| `Account Login Denied` in steamcmd | Steam Guard blocking automated login | `set_steam_guard_code <code>` then retry; preserve `config.vdf` for future runs |
| Build uploaded but players don't get it | Build not set live, or set live only on a beta branch | Set live on the correct branch (default = manual) via the Builds page |
| Windows installs, Mac/Linux install no files | OS depots not added to the package | Add every depot to the package on *Associated Packages & DLC* |
| "Invalid content configuration" at launch | No build set live on the selected branch, bad launch options, or your account doesn't own the depots | Set a build live; verify *Installation* launch options; add the depots to the Developer Comp package |
| Your own account downloads no files | The depot is missing from the package your account owns | Run Steam with `-dev`, then `licenses_for_app <AppID>` in the console to see the package and its depots; add the missing depot |
| Forgot a steamcmd command's syntax | — | At the `Steam>` prompt run `find <partial>` (e.g. `find build_installer`) to print matching commands + args |

Check the `*.log` files in `BuildOutput` (not the console) for the authoritative error on a
failed build.
