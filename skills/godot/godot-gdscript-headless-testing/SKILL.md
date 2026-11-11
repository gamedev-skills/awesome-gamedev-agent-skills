---
name: godot-gdscript-headless-testing
description: >
  Runs Godot 4.7 GDScript tests with godot --headless and a SceneTree runner that exits non-zero
  on failure, so CI can gate merges. Owns Godot tests in CI. Use for GitHub Actions jobs or a
  headless run that hangs or exits 0 despite SCRIPT ERROR lines. Not for export in CI
  (`godot-export`), GDScript language (`godot-gdscript`) or Unity tests
  (`unity-csharp-scripting`).
---

# Godot GDScript headless testing (4.x)

Run GDScript tests from a terminal or CI and get a process exit code that means something.
Targets the **Godot 4.7** CLI; `--headless` is built into every 4.x editor binary.

The one rule behind most of this skill: **Godot's exit code only reflects what your runner
passes to `quit()`.** Script errors, `push_error()` and failed `assert()` calls do not make
it non-zero, so the runner counts failures itself.

## Workflow

1. **Check the binary:** `godot --headless --version` prints a version and opens no window.
2. **Import on every fresh checkout:** `godot --headless --path <project> --import`.
   `.godot/` is normally not committed, so without it `class_name` types do not resolve
   (`Identifier "X" not declared in the current scope`) and imported assets fail to load.
3. **Write the runner as a `SceneTree` script** (Pattern 1). `_initialize()` runs before the
   first frame and needs no `.tscn`.
4. **Count failures with a helper and end with `quit(1 if failed > 0 else 0)`.** Do not fail
   tests with bare `assert()`: in a debug build a failed assert stops `_initialize()` before
   `quit()`, and the process never exits.
5. **Run it:** `godot --headless --path <project> --script res://tests/test_runner.gd`
   (an absolute path to a runner outside the project also works) and read the exit code.
6. **In CI**, add the import step, a step timeout, and capture stdout and stderr to files
   (Pattern 3).
7. **Verify the runner itself before trusting a green run:** break one assertion on purpose
   and confirm the exit code becomes 1, then put it back. A runner that always exits 0
   passes CI forever.

For quick smoke checks without a test file, run a scene for a few hundred frames and scan
the log, since the exit code stays 0 after runtime errors:
`godot --headless --path <project> --quit-after 300 res://main.tscn > run.log 2>&1`, then
`grep -nE "SCRIPT ERROR|^ERROR:" run.log` (no match means clean).

## Patterns

### 1. Minimal SceneTree test runner with a real exit code

```gdscript
# res://tests/test_runner.gd
# godot --headless --path . --script res://tests/test_runner.gd
extends SceneTree

var passed := 0
var failed := 0

func _initialize() -> void:
    for t: String in ["test_add", "test_load"]:
        if call(t) != true:                       # a runtime error returns null, not true
            failed += 1
            push_error("FAIL %s: did not finish (runtime error?)" % t)
    print("Results: %d passed, %d failed" % [passed, failed])
    quit(1 if failed > 0 else 0)

func assert_eq(actual, expected, label: String) -> void:
    if actual == expected:
        passed += 1
    else:
        failed += 1
        push_error("FAIL %s: expected %s, got %s" % [label, expected, actual])

func test_add() -> bool:
    assert_eq(2 + 2, 4, "add")
    return true

func test_load() -> bool:
    assert_eq(load("res://icon.svg") != null, true, "icon loads")
    return true
```

Tests return `true` on their last line so a test that dies halfway is still counted:
a runtime error such as calling a method on `null` aborts only that function, which hands
its caller `null`. For tests that `await`, use `await call(t)` in the loop.

### 2. Tests that need a frame, a timer or a signal

```gdscript
extends SceneTree

var failed := 0

func _initialize() -> void:
    await run_tests()
    print("Results: %d failed" % failed)
    quit(1 if failed > 0 else 0)

func run_tests() -> void:
    await process_frame                 # root joins the tree on the first frame
    var timer := Timer.new()
    timer.one_shot = true
    root.add_child(timer)
    timer.start(0.1)
    await timer.timeout
    if not timer.is_stopped():
        failed += 1
        push_error("FAIL timer_fires_once")
    timer.queue_free()
```

`_initialize()` may `await`. Before the first `process_frame`, `root` is not inside the tree,
so a `Timer` started there errors ("not inside the tree") and its `timeout` never fires.

### 3. CI step (GitHub Actions)

```yaml
- name: Import project (fresh checkout has no .godot/)
  run: godot --headless --path . --import
- name: Run GDScript tests
  timeout-minutes: 5
  run: godot --headless --path . --script res://tests/test_runner.gd > test.log 2> test.err
- name: Show test output
  if: always()
  run: cat test.log test.err
```

The `run:` step fails on a non-zero exit code by itself; the discipline lives in the runner's
`quit()`. `timeout-minutes` is a backstop for a hung `await`.

## Gotchas

- **The job hangs until the CI timeout** → a failed bare `assert()` stopped `_initialize()`
  before `quit()` (prints `SCRIPT ERROR: Assertion failed`); or an `await` waits on a signal
  that never fires. Use the counter helper, and race long awaits against a timer.
- **An `await` never returns and nothing errors** → the object that emits the signal, or the
  node running the coroutine, was freed while waiting; Godot drops the coroutine silently.
  Await `SceneTreeTimer`s (`create_timer()`), which the tree owns, for delays.
- **Exit code 0 although checks failed** → the runner never calls `quit(1)`, or a test died
  on a runtime error and was never counted (see Pattern 1's `call(t) != true` loop).
- **Exit code 0 although the log shows `SCRIPT ERROR`** → expected: errors never change the
  exit code. Scan logs of smoke runs with `grep`, as in the workflow.
- **`--check-only` fails with `Identifier not found: SomeAutoload`** → `--check-only` parses a
  single script without registering autoloads. Load scripts from a runner instead
  (`godot-gdscript` ships a compile check that does).
- **The log grep flags `... still in use at exit` or `... leaked at exit`** → shutdown leak
  reports for objects the test created and never freed. Free them (or `queue_free()` and
  wait a frame before `quit()`); they are not test failures, so filter them if you must.
- **`Identifier "X" not declared` or "No loader found" only in CI** → the import step is
  missing.
- **Nothing happens or the editor opens** → `--headless` is missing or the `--script` path is
  wrong; `res://` paths resolve against `--path`.
- **`The InputMap action "x" doesn't exist` in a test** → the action is not in
  `project.godot`; tests that press inputs can add missing actions with
  `InputMap.add_action()`, but the game needs the real Input Map entry.
- **Output missing or out of order in PowerShell or some CI shells** → redirect stdout and
  stderr to files and read them after the process exits, as in Pattern 3.

## Related skills

- `godot-gdscript`: language rules, plus a compile check for every script in the project.
- `godot-2d-movement`, `godot-animation`: ready-made headless tests for controllers and
  animation states that plug into this runner.
- `godot-export`: exporting builds in CI, a different `--headless` use.

## Version notes

Last verified: 2026-11-11 with a Godot 4.7.2 headless binary (every behaviour above was
reproduced) and the 4.7.2 CLI help.

- Godot 4.7.2 (August 2026) is the current stable release; 4.8 is in beta.
- Sources: [Godot releases](https://github.com/godotengine/godot/releases),
  [Command line tutorial](https://docs.godotengine.org/en/stable/tutorials/editor/command_line_tutorial.html),
  [main.cpp @ 4.7.2](https://github.com/godotengine/godot/blob/4.7.2-stable/main/main.cpp).
