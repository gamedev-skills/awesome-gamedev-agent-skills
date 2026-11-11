---
name: steam-publish
description: >
  Publish or update a game on Steam with Steamworks and SteamPipe: configure depots and
  packages, upload builds with steamcmd, set a build live on a branch, and run the release
  checklists. Use for Steam publishing, app_build.vdf/steamcmd uploads, depots, beta branches,
  or a store page release.
---

# Steam Publish (Steamworks + SteamPipe)

Take a finished build to a live Steam store page. Two tracks run in parallel and both must be
approved before release: the **store page** (presence) and the **build** (SteamPipe upload +
the release checklists). This skill is the operational checklist; deep build-script,
CI/CD, and troubleshooting detail lives in `references/steampipe-build-scripts.md`.

## When to use

- Use when setting up a Steam app, building/editing the store page, configuring depots and
  packages, uploading a build via SteamPipe/steamcmd, managing beta branches, or releasing
  and updating a Steam title.
- Triggers: `steam_appid.txt`, the Steamworks SDK `tools/ContentBuilder`, `app_build_*.vdf`,
  `steamcmd`, "publish on Steam", "depot", "set build live".

**When *not* to use:** publishing on itch.io (use `itch-publish`); writing the
Steamworks **API** in-game (achievements/cloud/overlay live in engine SDK integrations, not
here); store/financial *advice* (pricing strategy, tax) — direct the user to Steamworks docs
and their own counsel.

## Prerequisites (do these once, in order)

1. **Partner account + Steam Direct fee.** Onboarding asks for legal identity, bank and tax
   details (tax verification can take up to 30 days). Each new app needs the Steam Direct fee
   (USD $100 or equivalent per app at time of writing): not refundable, recouped once the
   product reaches $1,000 Adjusted Gross Revenue, and not payable with Steam Wallet funds.
   You receive an **App ID** — find it on your Steamworks homepage. Treat the App ID as the
   key to everything below. For your first few titles, Valve also enforces a **21-day wait**
   between paying the app fee and releasing that game, so pay it well before the planned
   launch date.
2. **A dedicated build account with least privilege.** Builds require a Steam account in your
   partner group with **Edit App Metadata** and **Publish App Changes To Steam**. Create a
   *separate* build account with only those permissions (not your admin login). Posting the
   Coming Soon page and releasing additionally need **Manage pricing and discounts**. Once the
   app is released, setting a build live on `default` needs an extra confirmation sent to the
   Steam Mobile Authenticator or, failing that, by SMS — so the account that sets builds live
   needs one of them attached.
3. **Download the Steamworks SDK** on the upload machine. The SteamPipe tools are under
   `tools/ContentBuilder/`.

> Security note: never commit account passwords or the `config.vdf` login token to the repo.
> See the CI/CD section in the reference for the supported token workflow.

## Core workflow

1. **Configure the app (App Admin).**
   - Set **launch options** (executable path + args per OS) under *Installation*. For a
     sub-folder exe, put the sub-folder in the Executable field — no leading slashes/dots. For
     macOS prefer the app bundle (`Game.app`) over the binary inside it: on Apple Silicon a
     bundle launch picks the best architecture in the app, while a direct binary launch runs
     with the Steam client's architecture (currently x86_64).
   - Add **depots** on the *Depots* page (a depot is a bucket of files). Name each depot
     ("Base Content", "Windows Content"). Leave *[All languages]* / *[All OSes]* unless the
     depot is genuinely OS- or language-specific.
   - **Grant yourself the depots:** add them to your **Developer Comp** package on the
     *Associated Packages & DLC* page, or you won't own the content you upload.
   - **Publish** the configuration. Unpublished config is the most common cause of upload
     failures.
2. **Build the store page (presence track).** Fill graphical assets, description, tags,
   trailers, system requirements. Complete the **Content Survey** (general content, which
   generates regional age ratings; mature content; and generative AI — see Pitfalls) before
   you submit anything for review. When complete, click **Mark as ready for review**. Store
   review takes ~3-5 business days; submit at least **7 business days** before you want it
   live. Approval does not publish the page: click **Post as Coming Soon** to make it public.
   A new product must be in **Coming Soon** for at least **2 weeks** before release.
3. **Create your build scripts.** Start with the simple app-build `.vdf` in Patterns below;
   for multi-depot/multi-platform apps use depot scripts (see the reference). The script maps
   local files into depots and names where build output/logs go.
4. **Check the scripts, then bootstrap steamcmd and upload.** Run
   `python scripts/check_steam_build.py <app_build.vdf>` before you upload (Pattern 3) and fix
   every ERROR; then run `steamcmd` once to self-update and run the build (Patterns).
   steamcmd chunks files (~1 MB), uploads only changed chunks, and registers a global **BuildID**.
5. **Set the build live on a branch.** Go to `https://partner.steamgames.com/apps/builds/<AppID>`,
   pick the build, **Preview Change**, then **Set Build Live Now** for a branch. Test on a
   beta branch first (see `references/steampipe-build-scripts.md` for branch setup).
6. **Run the Game Build checklist** and **Mark as ready for review** (store presence must be
   submitted *before* the build review). Valve reviews the build live on `default`: it should
   be near-final, launch on every OS the store page lists, and contain every feature the store
   page claims. Build review also takes ~3-5 business days; plan for at least 7 business
   days. Both tracks must be approved. Approval is once: later updates are not re-reviewed.
7. **Release manually.** When approved and Coming Soon has run its time, use the green
   **Release App** button → **Publish Now** → **Release Now**. Approved titles do **not**
   release themselves.
8. **Update later** by uploading a new build and setting it live on `default` (manually) or
   shipping to a beta branch first. See `references/steampipe-build-scripts.md`.

## Patterns

### 1. SteamPipe ContentBuilder layout (Steamworks SDK)

```text
tools/ContentBuilder/
  builder/         steamcmd.exe (Windows)   <- run once to bootstrap
  builder_linux/   steamcmd (Linux)
  builder_osx/     steamcmd (macOS)
  content/         <- your final, runnable build goes here (the files players get)
  output/          build logs + chunk cache (safe to delete; speeds up re-uploads)
  scripts/         <- your *.vdf build scripts live here
```

### 2. Minimal app build script — `app_build_1000.vdf`

```text
// AppID 1000 with one depot (1001): upload everything under ../content recursively.
// VDF is Valve KeyValues: "key" "value", braces for nesting. Adjust IDs to your app.
"AppBuild"
{
    "AppID"       "1000"                 // your App ID
    "Desc"        "1.0.0 launch build"   // internal only; visible in Your Builds

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

### 3. Check the build scripts before uploading (read-only, no login)

```bash
# Run before you upload. Parses the app script and every depot script, resolves
# ContentRoot/LocalPath exactly as SteamPipe documents, and counts what each depot would upload.
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
AppBuild script. Errors cover: unparseable VDF, missing/non-numeric AppID or DepotID, no
depots, duplicate depots, missing depot script, ContentRoot or InstallScript, a LocalPath
that matches nothing or names a bare folder, and a depot that would upload zero files.
Warnings cover `SetLive` without `Preview` (goes live on that branch at once; `default`
gets a louder warning), missing `Desc`, `Local` builds, BuildOutput inside ContentRoot,
and misspelled keys. Read the per-depot file count and size before you upload.
Run the script path relative to this skill directory, or resolve the installed skill path
first. It needs Python 3.10+ and nothing else, and never logs in or uploads.

### 4. Upload the build (Windows; substitute the platform builder elsewhere)

```bat
REM Run from the SDK. Bootstrap once, then build. Use a build account, not your admin login.
tools\ContentBuilder\builder\steamcmd.exe ^
  +login <build_account> ^
  +run_app_build ..\scripts\app_build_1000.vdf ^
  +quit
```

For the first login, enter the password and Steam Guard code at SteamCMD's interactive
prompts. Later runs can reuse the protected login token; see
`references/steampipe-build-scripts.md` for CI setup. Do not put passwords in command-line
arguments, where shell history, process listings or logs may expose them.

```text
What happens: steamcmd self-updates -> logs in -> for each depot, hashes files into ~1 MB
chunks -> uploads only NEW chunks -> writes a depot manifest -> finishes with a global
BuildID. The build is NOT live yet; set it live per the workflow above.
```

### 5. Iterate safely with a preview build (uploads nothing)

```text
// Add to the AppBuild block to validate file mappings without uploading:
"Preview" "1"     // outputs logs + a file manifest into BuildOutput only
// And to auto-set live on a BETA branch after a successful build (never 'default'):
"SetLive" "beta-qa"
```

## Pitfalls

- **The `default` branch cannot be set live automatically.** `SetLive` only works for a
  *beta* branch; you must set the default (customer) build live by hand in App Admin. Plan
  releases around this.
- **Store page must be approved before the build.** You cannot submit the build for review
  until store presence is submitted; both must pass, and Coming Soon must run ~2 weeks.
- **Coming Soon clock never started.** An approved store page stays hidden until someone
  clicks **Post as Coming Soon**; the two-week minimum only runs while the page is public.
- **Titles never auto-release.** Even after approval, a human must click **Release App** at
  the chosen moment.
- **Generative AI content left out of the Content Survey.** Disclose AI-made content that
  ships to players (art, audio, text, localization) as *pre-generated*; content made while
  the game runs is *live-generated* and also needs a description of the guardrails that
  stop it producing illegal content. AI tools used only to work faster do not need to be
  listed. Some answers cannot be edited after approval without contacting Steam Support.
- **Build rejected for missing features.** Every feature selected in the store's Basic Info
  tab and every OS the page lists must work in the reviewed build; remove a feature there
  until it is implemented.
- **Mac/Linux install nothing.** Almost always: the OS-specific depots aren't in the package.
  Add every depot to the package on *Associated Packages & DLC*.
- **Unpublished app config.** "Failed to get application info" / build errors usually mean
  depots, launch options, or the App ID config were never **Published**.
- **`status = 6` on build.** The build account lacks permission for the App ID, or
  `ContentRoot`/`LocalPath` points at the wrong (empty) path.
- **Committing the login token.** The `config.vdf` Steam Guard token and account password are
  secrets. Keep them out of the repo; use the CI workflow in the reference.
- **Released-app safety delay.** Any security change on the build account (email, phone
  number, …) forces a **3-day** wait before it can set a build live for a *released* app —
  don't reconfigure the account right before launch.
- **Private beta leaked.** Set the branch password *before* you set a build live on that
  branch; a branch without a password is visible to every owner in *Game Versions & Betas*.
- **"Unknown" on Steam Deck / Steam Machine.** Hardware compatibility is a separate review
  from the release review and does not block release. It requires a completed build review;
  results publish automatically after about a week unless you ship a fix first. See the
  reference for the checklist (controller input and glyphs, on-screen keyboard, default
  framerate, Deck text size).

## References

- For advanced multi-depot/multi-platform build scripts, `FileExclusion`/`FileProperties`,
  beta-branch setup, the CI/CD login-token workflow, the Steam Deck / Steam Machine
  compatibility checklist, and the SteamPipe troubleshooting table, read
  `references/steampipe-build-scripts.md`.
- `scripts/check_steam_build.py` — read-only check of an app build script, its depot scripts
  and content folders; `--help` lists every check and the exit codes.
- Primary docs: Steamworks "Uploading to Steam" (`partner.steamgames.com/doc/sdk/uploading`),
  "Release Process" (`/doc/store/releasing`), "Branches (Betas)" (`/doc/store/application/branches`),
  "Builds" (`/doc/store/application/builds`), "Depots" (`/doc/store/application/depots`),
  "Onboarding" (`/doc/gettingstarted/onboarding`, first-title waiting periods), "Steam Direct
  Fee" (`/doc/gettingstarted/appfee`), "Coming Soon" (`/doc/store/coming_soon`), "Content
  Survey" (`/doc/gettingstarted/contentsurvey`), "Review Process" (`/doc/store/review_process`),
  "Steam Deck and Steam Machine Compatibility Review" (`/doc/steamhardware/compat`).

## Related skills

- `itch-publish` — the same game shipped on itch.io with `butler` (often done alongside Steam).
- `game-jam` / `prototype-fast` — earlier stages of the same project's lifecycle.
