# Screen state stack (LÖVE 11.5)

A small, complete screen manager: menu → game → pause, with the active screen on a stack so
overlays (pause on top of game) are trivial. Each *screen* is a plain Lua table with any of
the optional methods `enter`, `leave`, `update(dt)`, `draw`, `keypressed(key)`.

Drop `state_stack.lua` in your project root and the screens under `screens/`. The module,
wiring and example screens below were run together on LÖVE 11.5 (menu → game → pause →
resume).

## Contents

- [`state_stack.lua`](#state_stacklua): push, pop, switch, current
- [Wiring it in `main.lua`](#wiring-it-in-mainlua), including
  [drawing overlays](#drawing-overlays-pause-on-top-of-the-paused-game)
- [Example screens](#example-screens): menu, game, pause
- [Notes](#notes): module caching, loading, transitions

## `state_stack.lua`

```lua
-- state_stack.lua — minimal screen/state manager for LÖVE 11.x.
-- A screen is a table that may define: enter, leave, update(dt), draw, keypressed(key).
local Stack = { screens = {} }

-- Add a screen on top (e.g. open a pause overlay above the game).
function Stack.push(screen)
    table.insert(Stack.screens, screen)
    if screen.enter then screen:enter() end
end

-- Remove and return the top screen (e.g. close the pause overlay).
function Stack.pop()
    local screen = table.remove(Stack.screens)
    if screen and screen.leave then screen:leave() end
    return screen
end

-- Replace the top screen entirely (e.g. menu -> game).
function Stack.switch(screen)
    if #Stack.screens > 0 then Stack.pop() end
    Stack.push(screen)
end

function Stack.current()
    return Stack.screens[#Stack.screens]
end

return Stack
```

## Wiring it in `main.lua`

Delegate each LÖVE callback to the top screen. The helper tolerates screens that omit a
method, so a screen only implements what it needs.

```lua
local Stack = require("state_stack")

-- Call method `name` on the top screen if it exists.
local function forward(name, ...)
    local screen = Stack.current()
    if screen and screen[name] then screen[name](screen, ...) end
end

function love.load()        Stack.push(require("screens.menu")) end
function love.update(dt)    forward("update", dt) end
function love.draw()        forward("draw") end
function love.keypressed(k) forward("keypressed", k) end
```

### Drawing overlays (pause on top of the paused game)

To keep the game visible behind a pause screen, draw every screen bottom-to-top but only
update the top one:

```lua
function love.update(dt)
    forward("update", dt)                 -- only the top screen updates
end

function love.draw()
    for _, screen in ipairs(Stack.screens) do   -- draw all, bottom to top
        if screen.draw then screen:draw() end
    end
end
```

## Example screens

```lua
-- screens/menu.lua
local menu = {}

function menu:draw()
    love.graphics.setColor(1, 1, 1)
    love.graphics.print("MENU — press Enter to play, Esc to quit", 20, 20)
end

function menu:keypressed(key)
    if key == "return" then
        require("state_stack").switch(require("screens.game"))
    elseif key == "escape" then
        love.event.quit()
    end
end

return menu
```

```lua
-- screens/game.lua
local Stack = require("state_stack")
local game = {}

function game:enter()
    self.player = { x = 100, y = 100, speed = 220 }
end

function game:update(dt)
    if love.keyboard.isDown("right") then
        self.player.x = self.player.x + self.player.speed * dt   -- dt-scaled motion
    end
end

function game:draw()
    love.graphics.setColor(0.2, 0.8, 1.0)
    love.graphics.rectangle("fill", self.player.x, self.player.y, 40, 40)
    love.graphics.setColor(1, 1, 1)
    love.graphics.print("P = pause, hold Right to move", 20, 20)
end

function game:keypressed(key)
    if key == "p" then Stack.push(require("screens.pause")) end  -- overlay, game stays beneath
end

return game
```

```lua
-- screens/pause.lua
local Stack = require("state_stack")
local pause = {}

function pause:draw()
    -- Dim the game beneath, then label the overlay.
    love.graphics.setColor(0, 0, 0, 0.5)
    love.graphics.rectangle("fill", 0, 0, love.graphics.getWidth(), love.graphics.getHeight())
    love.graphics.setColor(1, 1, 1)
    love.graphics.print("PAUSED — press P to resume", 20, 60)
end

function pause:keypressed(key)
    if key == "p" then Stack.pop() end   -- return to the game underneath
end

return pause
```

## Notes

- `require("screens.menu")` returns the **same table** each call (Lua caches modules), so a
  screen here is effectively a singleton. If you need fresh per-instance state, make the
  module a factory: `return function() return setmetatable({}, Screen) end` and call it.
- Keep screen logic in `update`/`draw`; do not block in `enter`. Long loads belong in a
  loading screen that yields across frames.
- This manager has no transitions/animation by design. Add a `fade` screen pushed on top that
  draws a shrinking alpha rectangle if you want crossfades — the stack already supports it.
