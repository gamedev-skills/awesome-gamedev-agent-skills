# butler: CI/CD, full flag reference, and the update-check API

Depth for `itch-publish`. Read this for automated uploads, the complete `butler push` flag
set, and notifying players of updates. Verify against the primary docs:
[the butler manual](https://itch.io/docs/butler) (installing, login, pushing).

## 1. Authentication for CI (`BUTLER_API_KEY`)

Interactive `butler login` opens a browser — useless in CI. Instead, set the
**`BUTLER_API_KEY`** environment variable and butler uses it automatically.

Where to get the key:
- Run `butler login` once locally, then read it from the creds file:
  - Linux: `~/.config/itch/butler_creds`
  - macOS: `~/Library/Application Support/itch/butler_creds`
  - Windows: `%USERPROFILE%\.config\itch\butler_creds`
- Or generate one on your itch.io **API keys** page (`itch.io/user/settings/api-keys`) — the
  relevant key has its source set to `wharf`.

Store it as a CI secret. **Never** print it; a key leaked into a public build log is
compromised — revoke it immediately on the API keys page.

## 2. Installing a reviewed butler release in CI

Pin the official release and its expected SHA-256 together. This Linux amd64 example
uses the asset from [butler v15.32.0](https://github.com/itchio/butler/releases/tag/v15.32.0).
Review both constants when updating it; do not fetch a replacement checksum from a
mutable endpoint in the same install step and treat that as independent verification.

```bash
set -euo pipefail
BUTLER_VERSION=15.32.0
BUTLER_SHA256=5db7b053fc9b578b86ffaf3520a12b952eb95c9225171cc5720dfbc9fe4574b3
curl -fL -o butler.zip "https://github.com/itchio/butler/releases/download/v${BUTLER_VERSION}/butler-linux-amd64.zip"
printf '%s  %s\n' "$BUTLER_SHA256" butler.zip | sha256sum -c -
unzip -q butler.zip
chmod +x butler
./butler -V        # prints version; confirms it runs
```

For another OS/architecture, select its asset and digest from the same official release.
Broth's permanent channel URLs are useful for discovery, but `LATEST` changes over time
and is not a reproducible CI pin. Keep installation and build steps free of publishing
credentials; the uploader itself still needs to be trusted even when the key is step-scoped.

## 3. GitHub Actions example

```yaml
name: Publish to itch.io
on:
  push:
    tags: ["v*"]            # publish when you tag a release
jobs:
  butler:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      # ... your build steps produce ./build/windows, ./build/linux, etc. ...
      - name: Install butler
        run: |
          set -euo pipefail
          BUTLER_VERSION=15.32.0
          BUTLER_SHA256=5db7b053fc9b578b86ffaf3520a12b952eb95c9225171cc5720dfbc9fe4574b3
          curl -fL -o butler.zip "https://github.com/itchio/butler/releases/download/v${BUTLER_VERSION}/butler-linux-amd64.zip"
          printf '%s  %s\n' "$BUTLER_SHA256" butler.zip | sha256sum -c -
          unzip -q butler.zip
          chmod +x butler
      - name: Push builds
        env:
          BUTLER_API_KEY: ${{ secrets.BUTLER_API_KEY }}   # available only to the uploader
        run: |
          VERSION="${GITHUB_REF_NAME#v}"     # tag v1.2.0 -> 1.2.0
          ./butler push ./build/windows leafy/my-game:windows --userversion "$VERSION"
          ./butler push ./build/linux   leafy/my-game:linux   --userversion "$VERSION"
```

For GitLab CI, scope a protected, masked `BUTLER_API_KEY` to the publishing job and keep
ordinary build jobs without it. Use the same pinned install and verification sequence.

## 4. `butler push` flag reference (checked against butler v15.32.0)

| Flag | Purpose |
|---|---|
| `--userversion <v>` | Set an explicit version string instead of itch's auto-incrementing integer. |
| `--userversion-file <f>` | Read the version string from a file (single line, UTF-8, no BOM). |
| `--if-changed` | Skip the push if it would be an empty patch (contents identical to the latest build). |
| `--hidden` | Mark the upload hidden — **only** when the push creates a *new* channel; errors on an existing one. |
| `--ignore '<glob>'` | Exclude matching files; repeatable (`--ignore '*.pdb' --ignore '*.dSYM'`). Two dashes. |
| `--dry-run` | List every file that would be pushed (+ a summary); uploads nothing and needs no login. |
| `--no-auto-unzip` | Push a folder holding a single `.zip` as that one opaque file. By default (`--auto-unzip`) butler pushes the zip's contents instead. |
| `--dereference` | Follow symlinks and upload copies of their targets (larger builds; use with care). |
| `--fix-permissions` | On by default: detects Mac and Linux executables and sets their executable bit. `--no-fix-permissions` turns it off. |
| `--auto-wrap` | On by default: when the source path is a macOS `.app` bundle, keeps the bundle as the top-level folder of the build. |
| `-i, --identity <file>` | Read/save credentials from another file, to use several itch.io accounts on one machine. |

The target may also be given as a numeric game ID or a game page URL
(`butler push ./build https://leafy.itch.io/my-game:windows`).

Related commands:

| Command | Purpose |
|---|---|
| `butler login` / `butler logout` | Authorize / clear local credentials (browser flow). |
| `butler version` | Print butler's version (confirms install + PATH). |
| `butler which` | Print the full path to the running butler binary. |
| `butler status <user>/<game>` | List channels and their latest builds/versions. |
| `butler push-preview <dir> <user>/<game>:<ch>` | Show `NEW/MODIFIED/DELETED/SAME` vs the last build; add `--changes-only` to hide unchanged. Uploads nothing. |
| `butler upgrade` | Update butler itself to the latest version. |

Notes:
- Processing: after a push the build is immediately live via a fast "default" patch; itch.io
  then regenerates an optimized (smaller) patch in the background — around 30 minutes for a
  large game, with its status in the channel's build list. Players are never blocked on it.
- Working from a remote/SSH host: `butler login` prints a URL; open it locally, copy the
  redirected (non-loading) page's address, and paste it back into the terminal.

## 5. Notify players of updates (no auth required)

Players who download directly (not via the itch app) don't auto-update. Query the latest
user-version for a channel and prompt them in-game:

```text
GET https://api.itch.io/wharf/latest?target=<user>/<game>&channel_name=<channel>
# or by numeric game_id (from the Edit game page URL):
GET https://api.itch.io/wharf/latest?game_id=<id>&channel_name=<channel>

Response: { "latest": "1.2.0" }   // omitted if the latest build has no user-version
```

Compare `latest` to your build's version (push with `--userversion`) and surface an
"update available" message. Private games return an "invalid game" error to avoid leaking
unreleased titles.
