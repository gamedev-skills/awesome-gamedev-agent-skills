#!/usr/bin/env python3
"""Create a new Ebitengine game project from the bundled starter.

Copies ../assets/starter into a new directory, sets the Go module path and window
title, and writes go.mod pinned to an Ebitengine version. It does not run `go`
or touch the network; run `go mod tidy` afterwards to fetch dependencies.

The output directory must not exist, or must be empty.

With --ci it also writes .github/workflows/ci.yml (tests, headless smoke run,
cross-compiles, tagged releases) and copies check_ebitengine.py and
package_macos_app.py into tools/, which that workflow calls.

Examples:
  python3 new_game.py --out ./mygame --module example.com/mygame --title "My Game"
  python3 new_game.py --out ./mygame --module github.com/you/mygame --ci --bundle-id com.you.mygame
  cd mygame && go mod tidy && go run .
"""
import argparse
import html
import json
import shlex
import unicodedata
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STARTER = os.path.join(HERE, "..", "assets", "starter")
WORKFLOW = os.path.join(HERE, "..", "assets", "ci", "github-actions.yml")
MODULE_RE = re.compile(r"^[a-z0-9][a-z0-9._~\-]*(/[A-Za-z0-9._~\-]+)*$")
VERSION_RE = re.compile(r"^v2\.\d+\.\d+(-[0-9A-Za-z.\-]+)?$")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True, help="new project directory (must not exist or be empty)")
    ap.add_argument("--module", required=True, help="Go module path, e.g. example.com/mygame or github.com/you/game")
    ap.add_argument("--title", default="My Game", help="window and title-screen text")
    ap.add_argument("--ebiten", default="v2.10.6", help="Ebitengine version for go.mod (default v2.10.6)")
    ap.add_argument("--go", default="1.25.0", help="go directive (Ebitengine v2.10 needs 1.25 or later)")
    ap.add_argument("--ci", action="store_true", help="add a GitHub Actions workflow and the tools/ scripts it uses")
    ap.add_argument("--bundle-id", help="macOS bundle ID for --ci release builds (default com.example.<name>)")
    args = ap.parse_args()

    if not MODULE_RE.fullmatch(args.module) or any(
        part in (".", "..") or part.startswith(".") or part.endswith(".")
        for part in args.module.split("/")
    ):
        print(f"error: invalid module path {args.module!r}", file=sys.stderr)
        return 2
    if not VERSION_RE.fullmatch(args.ebiten):
        print(f"error: --ebiten must look like v2.10.6, got {args.ebiten!r}", file=sys.stderr)
        return 2
    if int(args.ebiten.split(".")[1]) < 10:
        print("error: this starter uses Ebitengine v2.10+ APIs", file=sys.stderr)
        return 2
    if not re.fullmatch(r"1\.\d+(\.\d+)?", args.go):
        print(f"error: --go must look like 1.25.0, got {args.go!r}", file=sys.stderr)
        return 2
    if int(args.go.split(".")[1]) < 25:
        print("error: Ebitengine v2.10 needs Go 1.25 or later", file=sys.stderr)
        return 2
    if not args.title.strip() or any(unicodedata.category(c).startswith("C") for c in args.title):
        print("error: --title must be nonempty and contain no control characters", file=sys.stderr)
        return 2
    parts = args.module.split("/")
    if len(parts) > 1 and re.fullmatch(r"v\d+", parts[-1]):
        parts.pop()  # major-version suffix: github.com/you/game/v2 -> game
    name = re.sub(r"[^a-z0-9_-]", "", parts[-1].lower()) or "game"
    bundle_name = name.replace("_", "-").strip("-") or "game"
    bundle_id = args.bundle_id or f"com.example.{bundle_name}"
    if not re.match(r"^[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+$", bundle_id):
        print(f"error: --bundle-id {bundle_id!r} is not reverse-DNS", file=sys.stderr)
        return 2
    if not os.path.isdir(STARTER):
        print(f"error: starter not found at {STARTER}", file=sys.stderr)
        return 1
    if args.ci and not os.path.isfile(WORKFLOW):
        print(f"error: workflow not found at {WORKFLOW}", file=sys.stderr)
        return 1
    out = os.path.abspath(args.out)
    if os.path.exists(out) and (not os.path.isdir(out) or os.listdir(out)):
        print(f"error: {out} exists and is not an empty directory", file=sys.stderr)
        return 1

    title_literal = json.dumps(args.title, ensure_ascii=False)
    shutil.copytree(STARTER, out, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    for root, _, names in os.walk(out):
        for n in names:
            if not n.endswith(".go"):
                continue
            p = os.path.join(root, n)
            with open(p, encoding="utf-8") as f:
                s = f.read()
            s = s.replace('"starter/world"', f'"{args.module}/world"')
            s = s.replace('ebiten.SetWindowTitle("Starter")', f'ebiten.SetWindowTitle({title_literal})')
            s = s.replace('"STARTER"', title_literal)
            with open(p, "w", encoding="utf-8") as f:
                f.write(s)
    page = os.path.join(out, "web", "index.html")
    if os.path.exists(page):
        with open(page, encoding="utf-8") as f:
            s = f.read().replace("<title>Starter</title>", f"<title>{html.escape(args.title)}</title>")
        with open(page, "w", encoding="utf-8") as f:
            f.write(s)
    with open(os.path.join(out, "go.mod"), "w", encoding="utf-8") as f:
        f.write(f"module {args.module}\n\ngo {args.go}\n\nrequire github.com/hajimehoshi/ebiten/v2 {args.ebiten}\n")

    if args.ci:
        os.makedirs(os.path.join(out, ".github", "workflows"))
        with open(WORKFLOW, encoding="utf-8") as f:
            wf = f.read()
        wf = wf.replace("GAME: mygame", f"GAME: {name}").replace("com.example.$GAME", bundle_id)
        with open(os.path.join(out, ".github", "workflows", "ci.yml"), "w", encoding="utf-8") as f:
            f.write(wf)
        os.makedirs(os.path.join(out, "tools"))
        for tool in ("check_ebitengine.py", "package_macos_app.py"):
            shutil.copy2(os.path.join(HERE, tool), os.path.join(out, "tools", tool))

    print(f"created {out}")
    print("next:")
    print(f"  cd {shlex.quote(out)}")
    print("  go mod tidy        # fetches Ebitengine and writes go.sum")
    print("  go test ./world/... # game rules, no graphics initialization")
    print("  go run .           # play")
    print("  go run . -demo -shot shot.png   # scripted run, saves a frame, exits")
    if args.ci:
        print("  git init && git add . && git commit   # then push; tag v1.0.0 for a release")
    return 0


if __name__ == "__main__":
    sys.exit(main())
