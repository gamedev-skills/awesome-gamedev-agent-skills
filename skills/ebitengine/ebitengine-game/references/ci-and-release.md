# CI and release automation

The bundled workflow tests and cross-builds the starter on Linux. Ebitengine
v2.10's desktop backend needs no C compiler; dependencies, SDKs and build tags
can add requirements. Adapt the matrix to the game's promised targets. Native
runtime, signing and store checks remain separate from cross-compilation.

## Workflow asset and its limits

`new_game.py --ci` copies `assets/ci/github-actions.yml` to
`.github/workflows/ci.yml` and the checker/packager to `tools/`. It does not push,
publish or enable a repository. Inspect the generated workflow before use:
its `v*` tag job creates a GitHub release with archives.

On branch pushes and pull requests, on `ubuntu-24.04`:

1. Check formatting and run `go vet ./...`.
2. Run `go test ./...` under Xvfb with `ALSA_CONFIG_PATH` pointing to a temporary
   null ALSA configuration. This accommodates packages initializing graphics.
3. Run the heuristic checker; review warnings in context.
4. Build and smoke-run with `-demo -shot shot.png -shot-tick 240`, with a timeout,
   virtual display and null audio. Require a nonempty PNG and upload it for
   inspection. Existence alone is not visual acceptance.
5. Cross-build Windows amd64, macOS amd64/arm64, Linux amd64 and js/wasm.

On version tags such as `v1.2.3` or `v1.2.3-beta.1`, after tests pass: stamp the
binary version, build desktop/WASM artifacts, assemble an unsigned universal
macOS `.app`, archive and attach to a GitHub release. The binary retains the
full version; Apple metadata uses the numeric version and CI run number.
The general Windows build sets `-H=windowsgui`; Steam-specific workarounds are
not applied automatically. Only the release job has `contents: write`.

Local helper/build checks and workflow linting do not constitute a successful
GitHub Actions run. Check the first actual run, its permissions and logs. The
workflow does not sign/notarize, validate store services, or run Windows/macOS
artifacts. Add native jobs where the delivery needs runtime evidence.

Adapting it:

- Replace scripted inputs and capture points when the game changes. Add more
  meaningful scenarios; retain smoke coverage rather than relying only on builds.
- If rules/tests require cgo or native SDKs, change `CGO_ENABLED`, install the
  toolchain and split targets accordingly.
- The workflow copies `licenses/` into release archives, including the bundled
  Go Regular font notice. Add the required notices for the game's assets and
  linked libraries; the supplied font notice is not an exhaustive dependency
  licence inventory.
- For macOS, sign/notarize the final bundle on a Mac, use the correct store
  entitlements, staple and verify the extracted archive. See
  the publishing-and-platforms reference.
- Store uploads need the actual store tooling and credentials, within the
  user's requested publication scope; do not add upload jobs by default.

## Version stamping and traceability

```go
var version = "dev" // stamped by -ldflags "-X main.version=1.2.0"
```

The starter prints this with `-version` and shows it on its title screen. Verify
the output from the stamped binary: a wrong symbol can leave `dev` unchanged.
Keep dependency versions in `go.mod`/`go.sum`; `go version -m` inspects embedded
module information. `-trimpath` reduces local path exposure. The template uses
`-buildvcs=false`; use your repository's policy for recording commit provenance.

## Visual regression

Store reference renders for scripted states when accidental visual changes matter.
Compare with a tolerance suited to the renderer/driver and inspect differences.
Xvfb is a virtual display, not a software renderer: Ebitengine still uses its
graphics backend, with a hardware or Mesa software implementation depending on
the environment. Pin the CI image/driver where repeatability matters. A repeated
PNG in one environment does not guarantee identical pixels across platforms.

Before a release, inspect the meaningful states, run the packaged build on each
promised platform, check browser hosting/focus/audio where applicable and verify
version/licence files in the final archives. CI green is evidence for the checks
it ran, not a complete playtest.
