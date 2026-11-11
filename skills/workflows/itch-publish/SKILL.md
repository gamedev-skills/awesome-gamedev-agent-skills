---
name: itch-publish
description: >
  Publishes and updates games on itch.io with the butler CLI: butler push to user/game:channel,
  channel platform tags, HTML5 builds, --userversion and CI uploads. Use for "upload to itch", an
  HTML5 game that downloads instead of playing, a blank or 403 web build, or "invalid target". Not
  for Steam (`steam-publish`) or jam scope (`game-jam`).
---

# itch.io Publish (butler)

Get a build onto an itch.io page and keep it updated. The page is created in the browser by
the user; every upload goes through **butler**, itch.io's CLI, with one command: `butler push`.
butler diffs against the channel's previous build and uploads only what changed. CI and the
full flag list live in `references/butler-ci.md`; limits and dated rules are in Version notes.

## When to use

- Creating or updating an itch.io page, installing or logging in to butler, pushing a build,
  choosing channel names, versioning uploads, shipping a jam, demo or release build.
- Project signals: `butler` in scripts or CI, `BUTLER_API_KEY`, a `.itch.toml` manifest.

**Not for:** Steam (use `steam-publish`); jam scope and schedule (use `game-jam`; this skill is
only the upload); building or exporting the game (engine skills).

## Workflow

1. **The page must exist first.** butler pushes only to an existing page. Ask the user to
   create it at `itch.io/game/new` and report the page URL. Settings to ask for: *Kind of
   project* stays **Downloadable** for native builds or becomes **HTML** for a browser game;
   visibility stays **Draft** (or Restricted, with a password, for testers) until the page is
   finished, because the first public publish puts it on Most Recent once and never again.
2. **Work out the target.** `<user>/<game>` is the lowercase page address:
   `finji.itch.io/overland` is `finji/overland`. Pick channel names now (Pattern 2) and reuse
   them forever.
3. **Install butler.** Locally from `itchio.itch.io/butler` or the itch app; in CI use the
   pinned, checksum-verified install in the reference. Check with `butler version`.
4. **Prepare a portable build folder:** exactly the files a player runs. Push a folder (or one
   `.zip` of that folder), never an installer or a pre-compressed pack (Gotchas).
5. **Dry-run the push** and read the file list (Verify, step 1). This needs no login.
6. **Log in.** `butler login` opens a browser, so ask the user to run it and approve. In CI,
   set `BUTLER_API_KEY` from a secret instead.
7. **Push:** `butler push <dir> <user>/<game>:<channel> --userversion <version>`. The first
   push uploads everything; later pushes to the same channel upload the diff.
8. **Finish the page.** Ask the user, on *Edit game*, to fix platform tags (tick only platforms
   the build was run on), tick *This file will be played in the browser* for an HTML channel,
   answer the **AI generation disclosure**, set adult content under *Metadata →
   Classification*, and Save.
9. **Update later** by pushing to the same channel. `butler push-preview` shows what will
   change first.

## Patterns

### 1. Push one channel per platform

```bash
# butler push <directory-or-zip> <user>/<game>:<channel>
butler push ./build/windows leafy/my-game:windows --userversion 1.2.0
butler push ./build/mac     leafy/my-game:osx     --userversion 1.2.0
butler push ./build/linux   leafy/my-game:linux   --userversion 1.2.0
butler push ./web           leafy/my-game:html    --userversion 1.2.0  # page Kind = HTML
```

`--userversion-file build.txt` reads the version from a file instead. Without either flag,
itch numbers builds with an auto-incrementing integer, and the update API (reference) has no
version to report.

### 2. Channel names set the initial platform tag

```text
Substring in channel name -> tag:  win / windows -> Windows   mac / osx -> macOS
                                   linux -> Linux             android -> Android
Several platforms in one channel:  butler push ./jar leafy/my-game:win-linux-mac
Convention: lowercase, dash-separated (windows-beta, osx-demo, soundtrack).
No CPU-architecture tag: name the channel (windows-arm64) if you ship several.
Tags are only the first guess; fix them on Edit game.
```

### 3. Filtered, hidden and conditional pushes

```bash
butler push ./build leafy/my-game:windows --ignore '*.pdb' --ignore '*.dSYM'   # repeatable
butler push ./build leafy/my-game:windows-beta --hidden    # only when CREATING a channel
butler push ./build leafy/my-game:windows --if-changed     # skip an empty patch (CI reruns)
butler status leafy/my-game                                # channels, builds, versions
```

## Verify

Run these yourself and report the result:

1. `butler push <dir> <user>/<game>:<channel> --dry-run` (plus the same `--ignore` flags) lists
   every file and ends with `Would push <size> (<n> files, ...)`. It needs no credentials.
   Check that the executable (or `index.html` at the root for HTML) is there and that
   symbols, editor files and installers are not. For HTML, also check the file count and sizes
   against the limits in Version notes.
2. `butler validate <dir>` (offline) exits 0. Without a `.itch.toml` it lists the file the itch
   app would launch; with one, it fails on a parse error or an action whose path is missing.
3. After a real push, `butler status <user>/<game>` shows the channel with the new build and
   user-version. Processing finishes in the background; the build is already downloadable.
4. Ask the user to open the page logged out (or in a private window), download or play the
   build, and report that it starts.

## Gotchas

- **Pushing an installer.** itch patches portable builds; an `.exe`/`.msi` installer defeats
  patching and the itch app's auto-update, and may need admin rights players lack.
- **Pre-compressed builds.** A compressed archive, or an archive of archives, makes every patch
  huge because a tiny change rewrites the whole blob. Push plain files; butler compresses.
- **A folder holding only one `.zip`.** butler unzips it and pushes the contents to avoid a zip
  in a zip. `--no-auto-unzip` uploads the zip as one opaque file.
- **HTML5 game shows as a download.** Two settings, neither set by the channel name: page
  **Kind** = HTML, and the channel ticked as played in the browser on *Edit game*.
- **HTML5 blank page or 403.** `index.html` must be at the upload root. The CDN is
  case-sensitive, serves the game from a subfolder (root-absolute `/` paths break; use
  relative paths), returns 403 for folder URLs, and allows only HTTPS requests to other
  domains. Keep the build inside the HTML5 limits in Version notes.
- **Selling a web game.** HTML pages take payment only as donations; make the page
  Downloadable to sell it.
- **`invalid target (bad user)` / `(bad game)`.** The target must match the page address
  exactly, lowercase, and the page must already exist.
- **macOS `.app` loses its structure.** Push the `.app` folder itself (or its parent); butler
  keeps the bundle as the top-level folder and sets the executable bit on Mac and Linux
  binaries by default.
- **`--hidden` on an existing channel errors.** It applies only when the push creates the
  channel. Unhide on *Edit game*.
- **Channel typos create duplicate downloads.** `windows` and `win-final` are separate files on
  the page.
- **Paid page delisted or payouts frozen.** Payment processors refuse some themes, and adult
  content must be classified. Ask the user to check itch.io's creator FAQ before pricing.
- **API key in a CI log.** A printed `BUTLER_API_KEY` is compromised; revoke it on the API keys
  page at once.

## References

- Read `references/butler-ci.md` when uploading from CI (GitHub Actions or GitLab), installing
  a pinned butler, needing a flag not shown above, or adding an in-game update check.
- Primary docs: [butler manual](https://itch.io/docs/butler/),
  [HTML5 uploads](https://itch.io/docs/creators/html5),
  [quality guidelines](https://itch.io/docs/creators/quality-guidelines) (tagging, AI
  disclosure, delisting).

## Related skills

- `steam-publish`: the same game on Steam via SteamPipe.
- `game-jam`: most jams run on itch.io; this skill handles the upload.
- `prototype-fast`: share an early prototype on a Draft or Restricted page.

## Version notes

Last verified: 2026-11-11.

- **butler:** latest release v15.32.0 (2026-10-06). Every flag on this page was checked against
  its `--help`; `push --dry-run` was run without credentials.
- **HTML5 upload limits:** at most 1,000 files, 500 MB extracted in total, 200 MB per file,
  240 characters per path; file names are case-sensitive UTF-8. itch.io may raise limits on
  request.
- **Build size:** the backend rejects builds over 30 GB uncompressed.
- **AI disclosure:** projects with generative-AI content must say so in the AI Disclosure
  section; asset pages without it may be delisted. Traditional game AI (pathfinding,
  procedural generation, dynamic difficulty) needs no tag.
- **Most Recent:** a page enters Most Recent only on its first public publish; Draft and
  Restricted pages are not listed.
- Sources: [butler releases](https://github.com/itchio/butler/releases/tag/v15.32.0),
  [Pushing builds](https://itch.io/docs/butler/pushing.html),
  [HTML5 uploads](https://itch.io/docs/creators/html5),
  [quality guidelines](https://itch.io/docs/creators/quality-guidelines),
  [access control](https://itch.io/docs/creators/access-control).
