---
name: steam-publish
description: >
  Publishes or updates a game on Steam with Steamworks and SteamPipe: depots, app_build .vdf
  scripts, steamcmd uploads, beta branches, SetLive, store review and Coming Soon. Use for
  steamcmd, ContentBuilder, "Failed to get application info", Steam Deck Verified or "ship it on
  Steam". Not for itch.io (`itch-publish`) or Steamworks SDK calls in game code.
---

# Steam Publish (Steamworks + SteamPipe)

Take a finished build to a live Steam store page. Two tracks run in parallel and both must be
approved before release: the **store page** (presence) and the **build** (SteamPipe upload plus
the Game Build checklist). The agent writes and checks the build scripts and drives steamcmd;
the partner-site steps are the user's, so ask for them and for the IDs they produce. Deep
build-script, CI and troubleshooting detail lives in `references/steampipe-build-scripts.md`.
Fees, waiting periods and review times are in Version notes at the end.

## When to use

- Setting up a Steam app, configuring depots and packages, writing `app_build_*.vdf` /
  `depot_build_*.vdf`, uploading with steamcmd, managing beta branches, getting through store
  and build review, and releasing or updating a Steam title.
- Project signals: `steam_appid.txt`, a Steamworks SDK `tools/ContentBuilder/` folder,
  `*.vdf` build scripts, steamcmd in CI.

**Not for:** itch.io (use `itch-publish`); pricing strategy, tax or legal advice (point the
user at the Steamworks docs and their own advisers).

**Steamworks SDK integration is out of scope.** For `SteamAPI_Init`, achievements, stats,
Steam Input, overlay, Cloud, lobbies or networking in game code, read Valve's
[Steamworks API overview](https://partner.steamgames.com/doc/sdk/api) and use the engine's
binding: [GodotSteam](https://godotsteam.com/) for Godot,
[Steamworks.NET](https://steamworks.github.io/) or Facepunch.Steamworks for Unity and C#, or
Unreal's Online Subsystem Steam plugin. This skill only uses the SDK's `tools/ContentBuilder`.

## One-time setup (the user does these)

1. **Partner account and Steam Direct fee.** Ask the user to finish onboarding (legal identity,
   bank, tax) and pay the per-app fee, then report the **App ID**. Tax verification and, for a
   first few titles, a waiting period between paying and releasing both run in calendar time,
   so the fee should be paid well before the launch date (numbers in Version notes).
2. **A dedicated build account.** Ask the user to create a separate Steam account in the
   partner group with only **Edit App Metadata** and **Publish App Changes To Steam**. Posting
   Coming Soon and releasing also need **Manage pricing and discounts**, which the build account
   can do without. After release, setting a build live on `default` sends a confirmation to the
   account's Steam Mobile Authenticator or phone, so the account that does it needs one.
3. **Steamworks SDK** on the upload machine. Only `tools/ContentBuilder/` is used: `builder*/`
   holds steamcmd per OS, `content/` the files players get, `scripts/` the `.vdf` files,
   `output/` logs and the chunk cache.

Never commit the account password or steamcmd's `config.vdf` login token. The reference has
the supported CI token workflow.

## Workflow

1. **Configure the app in App Admin.** Ask the user to do this and report the depot IDs:
   - *Installation*: one launch option per OS. A sub-folder exe goes in the Executable field
     with no leading slash or dot. On macOS point at `Game.app`, not the binary inside it
     (see Gotchas).
   - *Depots*: one depot per bucket of files ("Base Content", "Windows Content"). Leave *[All
     languages]* / *[All OSes]* unless the depot really is OS- or language-specific.
   - *Associated Packages & DLC*: add every depot to the **Developer Comp** package and to the
     store package, or nobody (including the developer) owns the content.
   - **Publish** the configuration. Unpublished config is the most common upload failure.
2. **Store page track.** Ask the user to fill assets, description, tags, trailer and system
   requirements, then complete the **Content Survey** (general content, mature content,
   generative AI) before submitting. Then **Mark as ready for review**. Approval does not
   publish the page: someone must click **Post as Coming Soon**, and the minimum Coming Soon
   period only runs while the page is public.
3. **Write the build scripts.** One depot: the minimal `app_build` below. Several depots or
   platforms: one `depot_build_<DepotID>.vdf` per depot (reference, section 1).
4. **Check the scripts** with `scripts/check_steam_build.py` and fix every ERROR. Then do a
   first run with `"Preview" "1"`, which writes logs and a manifest and uploads nothing.
5. **Upload.** Remove `Preview`, run steamcmd with the build account (Pattern 3). It chunks
   files at about 1 MB, uploads only new chunks and registers a global **BuildID**.
6. **Set the build live on a beta branch first.** Either `"SetLive" "<beta>"` in the script or,
   on `https://partner.steamgames.com/apps/builds/<AppID>`, **Preview Change** then **Set Build
   Live Now**. Ask the user to install that branch and report that it launches on every OS the
   store page lists. Then promote it to `default` by hand: `default` cannot be set from a script.
7. **Build review.** Store presence must be submitted first. Valve reviews the build that is
   live on `default`: near-final, launching on every listed OS, with every feature the store
   page claims. Ask the user to complete the Game Build checklist and **Mark as ready for
   review**. Review happens once; later updates are not re-reviewed.
8. **Release.** Titles never release themselves. When both tracks are approved and Coming Soon
   has run its time, the user clicks **Release App**, **Publish Now**, then **Release Now**.
9. **Updates later:** upload, set live on a beta, test, promote to `default`.

## Patterns

### 1. Minimal app build script: `app_build_1000.vdf` in ContentBuilder's scripts folder

```text
// AppID 1000 with one depot (1001): upload everything under ../content recursively.
// VDF is Valve KeyValues: "key" "value", braces for nesting. Adjust IDs to your app.
"AppBuild"
{
    "AppID"       "1000"                 // your App ID
    "Desc"        "1.0.0 launch build"   // internal only; shown in Your Builds

    "ContentRoot" "..\content\"          // root of files to upload (relative to this file)
    "BuildOutput" "..\output\"           // logs + chunk cache

    "Depots"
    {
        "1001"                           // your Depot ID
        {
            "FileMapping"
            {
                "LocalPath"  "*"         // all files from ContentRoot
                "DepotPath"  "."         // mapped to the depot root
                "recursive"  "1"         // include subfolders
            }
        }
    }
}
```

Two optional top-level keys: `"Preview" "1"` (dry run: logs and manifest only) and
`"SetLive" "beta-qa"` (set live on that beta branch after a successful build; never `default`).

### 2. Check the build scripts (read-only, no login)

```bash
# Paths are relative to this skill directory. Python 3.10+, standard library only.
python scripts/check_steam_build.py tools/ContentBuilder/scripts/app_build_1000.vdf
python scripts/check_steam_build.py app_build_1000.vdf --json --strict   # CI gate
```

```text
ERROR depot_build_1002.vdf:7: LocalPath "bin\*" matches no files under ../content
  fix: LocalPath is relative to the content root; check the folder names, ...
Depots:
  1001 [depot_build_1001.vdf]: 412 files, 1.8 GiB, 3 excluded, from ../content
Summary: 1 errors, 0 warnings in 3 files checked
```

Exit 0 = no errors, 1 = errors (or warnings with `--strict`), 2 = file missing or not an
AppBuild script. It resolves `ContentRoot` and `LocalPath` the way SteamPipe documents and
reports, per depot, the files and bytes that would upload. Errors: unparseable VDF, bad or
missing AppID/DepotID, no or duplicate depots, missing depot script, ContentRoot or
InstallScript, a LocalPath that matches nothing or names a bare folder, a depot with zero
files. Warnings: `SetLive` without `Preview` (louder for `default`), missing `Desc`, `Local`
builds, BuildOutput inside ContentRoot, misspelled keys. Read the per-depot count and size: a
depot far smaller than the build folder usually means a wrong mapping. It never logs in or
uploads; `--help` lists every check.

### 3. Upload the build

```bat
REM Windows, from the SDK root. Use the build account, not an admin login.
tools\ContentBuilder\builder\steamcmd.exe ^
  +login <build_account> ^
  +run_app_build ..\scripts\app_build_1000.vdf ^
  +quit
```

On Linux and macOS use `builder_linux/steamcmd.sh` or `builder_osx/steamcmd.sh` (reference,
section 2). The first login is interactive: the user types the password and Steam Guard code
at steamcmd's prompts. Keep passwords out of command-line arguments, where shell history,
process lists and CI logs expose them. Later and CI runs reuse the saved login token
(reference, section 4).

## Verify

Run these yourself and report the result:

1. `python scripts/check_steam_build.py <app_build.vdf> --strict` exits 0, and each depot's file
   count and size match the build folder.
2. The `Preview` run's console ends with `Successfully finished AppID <id> build preview`, and
   the manifest in `BuildOutput` lists the expected files. On the real upload, the same line
   must report a BuildID instead of `preview`; if it still says `preview`, `Preview` is still
   `1` and nothing was uploaded.
3. On failure, read the `*.log` files in `BuildOutput`, not just the console, and match the
   error to the troubleshooting table in the reference.
4. Ask the user to confirm the BuildID appears on the Builds page, is live on the intended
   branch, and launches from that branch on every listed OS.

## Gotchas

- **`default` cannot be set live from a script.** `SetLive` works only for beta branches; the
  customer build is promoted by hand on the Builds page.
- **Store page before build.** The build cannot be submitted for review until store presence
  is submitted, and both must pass.
- **Coming Soon clock never started.** An approved page stays hidden until someone clicks
  **Post as Coming Soon**; the minimum period counts only public days.
- **Approved titles never auto-release.** A person clicks **Release App** at the chosen time.
- **Generative AI left out of the Content Survey.** Content made with AI that ships to players
  (art, audio, text, localization) is *pre-generated*; content made while the game runs is
  *live-generated* and also needs a description of the guardrails against illegal output. AI
  tools used only to work faster need no entry. Some answers cannot be edited after approval
  without Steam Support.
- **Build rejected for missing features.** Every feature ticked on the store's Basic Info tab
  and every listed OS must work in the reviewed build; untick features that are not done.
- **Mac or Linux installs no files.** The OS depots are not in the package. Add every depot on
  *Associated Packages & DLC*.
- **"Failed to get application info".** Wrong App ID, the account does not own the app, or the
  App Admin config was never **Published**.
- **`status = 6` on build.** The build account lacks permission for the App ID, or
  `ContentRoot`/`LocalPath` points at an empty or wrong folder.
- **macOS game launches as Intel on Apple Silicon.** A launch option pointing at
  `Game.app/Contents/MacOS/Game` runs with the Steam client's architecture; pointing at
  `Game.app` lets macOS pick the best architecture in the bundle.
- **Security change right before launch.** Changing the build account's email or phone blocks
  it from setting builds live on a released app for a few days (Version notes).
- **Private beta leaked.** Set the branch password before setting a build live on it; a branch
  without one is visible to every owner under *Game Versions & Betas*.
- **"Unknown" on Steam Deck or Steam Machine.** Hardware compatibility is a separate review that
  needs a finished build review and never blocks release. Checklist in the reference.
- **Committed login token.** `config.vdf` and the account password are secrets. A leaked token
  means re-securing the account.

## References

- Read `references/steampipe-build-scripts.md` when the app has several depots or platforms,
  needs `FileExclusion`/`FileProperties`, uses beta branches, uploads from CI, targets Steam
  Deck Verified, or a build fails.
- `scripts/check_steam_build.py`: run before every upload (Pattern 2); `--help` for all checks.

## Related skills

- `itch-publish`: the same game on itch.io with butler, often shipped alongside Steam.
- `game-jam` / `prototype-fast`: earlier stages of the same project.

## Version notes

Last verified: 2026-11-11. Steam changes these; recheck the linked pages before quoting them.

- **Steam Direct fee:** USD 100 (or local equivalent) per app, not refundable, recouped after
  the product reaches USD 1,000 Adjusted Gross Revenue, payable by any Steam payment method
  except Steam Wallet funds.
- **Tax verification:** 10 to 15 business days, and tax details are locked while it runs.
- **First few titles:** 21 days between paying the app fee and releasing that game.
- **Coming Soon:** a new product must be public as Coming Soon for at least 2 weeks before
  release.
- **Reviews:** store presence and build each typically take 3 to 5 business days; Valve asks
  for at least 7 business days before the date you need.
- **Build account security change:** 3-day wait before it can set a build live on a released
  app. Setting live on a released app is confirmed by Steam Mobile Authenticator or SMS.
- **Steam Deck / Steam Machine review:** results publish automatically after about a week
  unless a fixing build is uploaded first.
- **macOS launch:** the Steam client process is x86_64, so direct binary launches run as
  x86_64 on Apple Silicon.
- Sources: [Steam Direct Fee](https://partner.steamgames.com/doc/gettingstarted/appfee),
  [Onboarding](https://partner.steamgames.com/doc/gettingstarted/onboarding),
  [Coming Soon](https://partner.steamgames.com/doc/store/coming_soon),
  [Review Process](https://partner.steamgames.com/doc/store/review_process),
  [Release Process](https://partner.steamgames.com/doc/store/releasing),
  [Content Survey](https://partner.steamgames.com/doc/gettingstarted/contentsurvey),
  [Uploading to Steam](https://partner.steamgames.com/doc/sdk/uploading),
  [Branches](https://partner.steamgames.com/doc/store/application/branches),
  [Steam Deck and Steam Machine Compatibility Review](https://partner.steamgames.com/doc/steamhardware/compat).
