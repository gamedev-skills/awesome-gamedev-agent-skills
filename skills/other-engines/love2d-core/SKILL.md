---
name: love2d-core
description: >
  Builds and debugs LÖVE (Love2D) 11.x games in Lua: main.lua callbacks, conf.lua, fixed steps,
  crisp pixel-art scaling, love.filesystem saves and a scripted run. Use when main.lua calls
  love.*, or on blurry pixel art, the blue error screen or speed tied to frame rate. Not for
  Defold (`defold-core`) or engine-neutral saves and input (`save-systems`, `input-systems`).
---

# LÖVE (Love2D) Core

Build and debug a LÖVE game. New code targets **LÖVE 11.5**, the current stable release;
12.0 is unreleased and changes APIs, so do not copy 12.0 examples into an 11.x game.

## When to use

- Starting a LÖVE game, or fixing its loop, timing, input, drawing, scaling, saving or
  screen flow.
- Any folder with `main.lua` calling `love.*`, a `conf.lua`, or a `.love` archive.

**When not to use:** Defold (also Lua, but `game.project` and `.script` files); physics
joints, shaders and networking beyond pointers; portable design owned by related skills.

## Workflow

1. **Read `conf.lua` first.** `t.version` names the target LÖVE version and `t.identity`
   the save folder. Keep the project's version; ask before porting between 0.10, 11 and 12.
2. **Load once, draw often.** Create images, fonts, canvases and sounds in `love.load` (or
   a loader), never inside `love.draw` or `love.update`.
3. **Simulate in steps.** Scale motion by `dt`; for physics, collisions or replays use the
   fixed-step accumulator below.
4. **Wrap world drawing in `push`/`pop`** and draw the HUD after `pop`, in screen space.
5. **Verify.** Add the `--frames` check below and run it under a timeout; read the output
   and open the screenshot in the save directory. Report what you ran. Input feel and sound
   need a person: ask the user to play briefly and report speed, controls and audio.

## Pattern: conf.lua with an error-exit hook

```lua
function love.conf(t)
    t.version = "11.5"               -- warns when run on another LÖVE version
    t.identity = "my-game"           -- save folder name; set it before the first release
    t.window.width, t.window.height = 960, 540
end

-- Under --frames, print errors and exit 1 instead of showing the blue error screen.
-- conf.lua runs before main.lua, so this also catches syntax errors in main.lua.
if arg and table.concat(arg, " "):find("--frames", 1, true) then
    function love.errorhandler(msg)
        print("ERROR: " .. tostring(msg) .. debug.traceback("", 2))
        return function() return 1 end
    end
end
```

## Pattern: fixed step and a scripted run

```lua
local STEP = 1 / 60
local acc = 0
local check = { frames = nil, shot = nil, count = 0 }
local player

function love.load(args)             -- args: command-line arguments after the game folder
    for i, a in ipairs(args) do
        if a == "--frames" then check.frames = tonumber(args[i + 1]) end
        if a == "--shot" then check.shot = args[i + 1] end
    end
    love.graphics.setDefaultFilter("nearest", "nearest")  -- before any newImage/newCanvas
    player = { x = 100, y = 100, speed = 120 }            -- pixels per second
end

local function step(dt)
    local dx = (love.keyboard.isDown("right") and 1 or 0)
             - (love.keyboard.isDown("left") and 1 or 0)
    player.x = player.x + dx * player.speed * dt
end

function love.update(dt)
    acc = acc + math.min(dt, 0.25)   -- clamp stalls so the loop cannot spiral
    while acc >= STEP do
        step(STEP)
        acc = acc - STEP
    end
    check.count = check.count + 1
    if check.frames and check.count == check.frames and check.shot then
        love.graphics.captureScreenshot(check.shot)       -- saved in the save directory
    elseif check.frames and check.count > check.frames then
        print("RUN OK frames=" .. check.frames .. " save=" .. love.filesystem.getSaveDirectory())
        love.event.quit(0)
    end
end
```

Use `love.keypressed(key, scancode, isrepeat)` for one-off actions and
`love.keyboard.isDown` inside `step` for held movement.

## Pattern: pixel-art canvas and camera

```lua
local W, H = 320, 180
local canvas                         -- create in love.load, after setDefaultFilter

function love.draw()
    love.graphics.setCanvas(canvas)
    love.graphics.clear(0.1, 0.1, 0.12)
    love.graphics.push()
    love.graphics.translate(-math.floor(cam.x), -math.floor(cam.y))  -- whole pixels
    drawWorld()
    love.graphics.pop()              -- every push needs a pop, even on an early return
    drawHud()                        -- screen space, after pop
    love.graphics.setCanvas()

    local w, h = love.graphics.getDimensions()
    local s = math.max(1, math.floor(math.min(w / W, h / H)))  -- integer scale only
    love.graphics.draw(canvas, math.floor((w - W * s) / 2), math.floor((h - H * s) / 2), 0, s, s)
end
```

Save with `love.filesystem.write("save.lua", text)` and read back with
`love.filesystem.read` or `love.filesystem.load`; files land in the save directory.

## The check to run

```sh
love --version
timeout 30 love . --frames 120 --shot frame.png; echo "exit=$?"
```

Expect `RUN OK` and exit 0; exit 1 prints the Lua error and traceback; exit 124 means the
game hung or the error hook is missing. The PNG is in the printed save directory, not the
project folder. On a Linux machine without a display, run `xvfb-run -a love . …`; if OpenAL
cannot open a sound device there, point `ALSA_CONFIG_PATH` at a file containing
`pcm.!default { type null }`.

## Gotchas

- **Pixel art looks blurry** → images default to linear filtering. Call
  `love.graphics.setDefaultFilter("nearest", "nearest")` before creating images, fonts or
  canvases (earlier objects keep `linear`), draw to a low-resolution canvas, scale it by a
  whole number, and round camera offsets.
- **`Maximum stack depth reached (more pushes than pops?)`** → a `push` without a matching
  `pop`, often skipped by an early `return` in `love.draw`. The stack survives across frames,
  so the error appears a few frames later. `Minimum stack depth reached` is the reverse.
- **Save file missing from the project folder** → `love.filesystem.write` only writes to the
  save directory (`love.filesystem.getSaveDirectory()`, named by `t.identity`; on Linux
  `~/.local/share/love/<identity>`). The game folder is read-only. Changing `t.identity`
  after release orphans players' saves.
- **A module's state resets or is duplicated** → it was required with two spellings.
  `require("screens.menu")` and `require("screens/menu")` load two separate copies. Always
  use dotted paths from the game root.
- **Same "random" level every run** → LuaJIT's `math.random` is not seeded at startup, while
  `love.math.random` is. Use `love.math.random` (or `love.math.newRandomGenerator(seed)` for
  replayable runs).
- **Speed changes with frame rate, or objects tunnel after a stall** → scale by `dt`, clamp
  `dt`, and step physics and collisions at a fixed rate.
- **The game freezes on the blue error screen in a scripted run** → the default error
  handler waits for the user. Use the `conf.lua` hook above so errors print and exit 1.
- **Colours come out white or fully opaque** → 11.x colours are 0–1. `setColor(128, 234,
  255)` draws white; use `love.math.colorFromBytes(128, 234, 255)` for byte values.
- **Everything is tinted after one `setColor`** → colour is global state. Reset with
  `love.graphics.setColor(1, 1, 1)` before drawing images and text.
- **`love.conf` has no effect** → it must be in `conf.lua`, which runs before `main.lua`.
- **Holding a key fires `love.keypressed` once** → key repeat is off by default.
  `love.keyboard.setKeyRepeat(true)` enables it; repeats arrive with `isrepeat == true`.
- **Memory climbs and frames slow down** → `newFont`, `newImage` or `newCanvas` is called
  every frame. Create them once and reuse them.

## References

- Read `references/state-stack.md` when the game needs menus, pause overlays or several
  screens: a complete push/pop screen manager with delegated callbacks and example screens.

## Related skills

- `save-systems` — save formats, slots and migration; `input-systems` — rebinding and
  gamepads.
- `defold-core` — the other Lua engine in this catalog; `pygame-core` — the same loop in
  Python.

## Version notes

Last verified: 2026-11-11.

- LÖVE 11.5 (2023-12-03) is the latest stable release; 12.0 has no stable release yet.
- The patterns, the check commands and the behaviour in Gotchas (filters, `require`
  spellings, seeding, push/pop errors across frames, save directory, error hook,
  `colorFromBytes`, key repeat) were run with the official LÖVE 11.5 x86_64 AppImage under
  Xvfb. Taken from the wiki only: `t.window.vsync` is a number since 11.0 and
  `love.math.colorFromBytes` arrived in 11.3.
- Sources: [LÖVE releases](https://github.com/love2d/love/releases),
  [love2d.org](https://love2d.org/), [11.5 `love.run`
  source](https://github.com/love2d/love/blob/11.5/src/modules/love/callbacks.lua),
  [love.filesystem](https://love2d.org/wiki/love.filesystem),
  [love.graphics.setDefaultFilter](https://love2d.org/wiki/love.graphics.setDefaultFilter),
  [Config Files](https://love2d.org/wiki/Config_Files).
