---
name: roblox-luau
description: >
  Roblox Luau scripting and code structure: services, Instances, Script vs LocalScript vs
  ModuleScript, the task library and typed Luau, with selene and luau-lsp checks. Use when a
  LocalScript does not run, a client gets nil after joining or wait() needs replacing. Not for
  remotes (`roblox-networking`), saving (`roblox-datastores`) or live-place edits
  (`roblox-studio-workflow`).
---

# Roblox Luau scripting

Write Luau that runs in the right place, cleans up after itself, and passes static checks before
anyone presses Play. Remote events appear here only as basic mechanics; contract design and
validation belong to `roblox-networking`.

## Workflow

1. **Read the project setup first.** Rojo `*.project.json`, `selene.toml`, `.luaurc`, Wally or
   pesde manifests, and the place's `Workspace.SignalBehavior` and `LuauTypeCheckMode`. Follow the
   existing module layout and naming instead of inventing a new one.
2. **Decide where the code runs** (table below). Check `RunContext` on any `Script` before
   assuming it is server code.
3. **Get services with `game:GetService("Name")`** at the top of the file, not by indexing `game`.
4. **Create Instances deliberately.** Set properties, then `Parent` last, so the Instance
   replicates once in its final state and change handlers do not fire for every property.
5. **Own every connection.** Store what `:Connect` returns and disconnect it with the object or
   screen that created it; use `:Once` for one-shot handlers.
6. **Share code through ModuleScripts.** A module runs once per context (server, and each client
   separately) and `require` returns the cached result, so module-level state is per context, never
   shared between server and client.
7. **Check before reporting.** Run the project's static tools (below). With the Studio MCP server
   connected, `start_stop_play`, exercise the change with `execute_luau` on the matching datamodel,
   then read `get_console_output` and report any new error or warning. Without it, ask the user to
   press Play and paste the Output, from both the server and client views when both sides changed.

### Static checks the agent can run

```bash
selene .                                      # root selene.toml needs std = "roblox"
rojo sourcemap default.project.json --output sourcemap.json
luau-lsp analyze --sourcemap=sourcemap.json src   # add Roblox type definitions; see --help
```

Run only the tools the project already uses. Studio Script Sync projects may not have a sourcemap.

## Where code runs

| Container | Runs | Use for |
|---|---|---|
| `ServerScriptService` | server `Script`s | authoritative logic; never replicated |
| `ServerStorage` | not run; server-only storage | assets and data clients must not see |
| `ReplicatedStorage` | `Script` with `RunContext = Client` runs here on clients | remotes, shared modules and assets |
| `StarterPlayerScripts` | `LocalScript`, once per player | persistent client systems |
| `StarterCharacterScripts` | `LocalScript`, once per character | per-character client logic |
| `StarterGui` | `LocalScript` in UI, cloned to `PlayerGui` | UI behavior |

A `LocalScript` in `Workspace` (outside the player's character) or `ServerScriptService` never runs.
A `Script` with `RunContext = Client` inside a `Starter*` container runs twice (the original and the
clone), so keep those in `ReplicatedStorage`.

## Patterns

### Server Script: per-player setup that also covers early joiners

```lua
-- ServerScriptService/Leaderboard.server.luau
local Players = game:GetService("Players")

local function onPlayerAdded(player: Player)
    local stats = Instance.new("Folder")
    stats.Name = "leaderstats"          -- this exact name shows on the default leaderboard
    local coins = Instance.new("IntValue")
    coins.Name = "Coins"
    coins.Parent = stats
    stats.Parent = player               -- parent last
end

Players.PlayerAdded:Connect(onPlayerAdded)
for _, player in Players:GetPlayers() do  -- players who joined before this script connected
    task.spawn(onPlayerAdded, player)
end
```

### Connection owned by its object

```lua
local touchedOnce: {[Humanoid]: boolean} = {}
local connection = part.Touched:Connect(function(hit: BasePart)
    local humanoid = hit.Parent and hit.Parent:FindFirstChildOfClass("Humanoid")
    if not humanoid or touchedOnce[humanoid] then return end
    touchedOnce[humanoid] = true
    humanoid:TakeDamage(10)
    task.delay(1, function() touchedOnce[humanoid] = nil end)
end)
part.Destroying:Once(function() connection:Disconnect() end)
```

A single shared `debounce` boolean blocks every other player while one is touching; key it by the
thing being debounced.

### Basic remote mechanics

```lua
-- LocalScript: request only. The client can send anything.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local buyItem = ReplicatedStorage:WaitForChild("Remotes"):WaitForChild("BuyItem")
buyButton.Activated:Connect(function() buyItem:FireServer("sword") end)
```

```lua
-- Script: the server looks up the price and decides.
local PRICES = { sword = 100, shield = 75 }
buyItem.OnServerEvent:Connect(function(player: Player, itemId: unknown)
    if type(itemId) ~= "string" then return end
    local price = PRICES[itemId]
    local coins = player:FindFirstChild("leaderstats") and player.leaderstats:FindFirstChild("Coins")
    if not price or not coins or coins.Value < price then return end
    coins.Value -= price
    grantItem(player, itemId)
end)
```

Rate limits, Instance arguments, yields inside handlers, and multi-client testing: `roblox-networking`.

### Frame loop and shared module

```lua
local RunService = game:GetService("RunService")
RunService.Heartbeat:Connect(function(dt: number)   -- after physics, every frame
    spinner.CFrame *= CFrame.Angles(0, math.rad(90) * dt, 0)
end)
```

```lua
-- ReplicatedStorage/Shared/GameConfig (ModuleScript)
local GameConfig = table.freeze({
    MaxHealth = 100,
    WeaponDamage = table.freeze({ sword = 25, bow = 15 }),
})
return GameConfig
```

Freezing shared config turns an accidental write into an immediate error instead of a silent
per-context divergence.

## Gotchas

- **Deferred events change ordering.** When `Workspace.SignalBehavior` is `Deferred` (forced by
  Server Authority, and the planned future default), handlers run at the next resumption point,
  not inside the call that fired them. Code that sets a property and expects its `Changed` handler
  to have run on the next line breaks, and a handler may see an Instance that was already
  destroyed. Read state inside the handler and check `instance.Parent` before using it.
- **`nil` on the client right after join.** Replication and streaming deliver objects over time.
  Use `WaitForChild` (with a timeout for optional content) on the client; on the server, objects
  you created exist immediately.
- **Legacy globals.** `wait()`, `spawn()` and `delay()` are throttled legacy scheduling; use
  `task.wait`, `task.spawn`, `task.defer`, `task.delay`.
- **`type` vs `typeof`.** `type(v)` cannot tell Roblox types apart (an Instance and a CFrame both
  report `"userdata"`); use `typeof(v)` to get `"Instance"`, `"CFrame"` and so on.
- **Superseded `Async` methods.** Many engine methods now have `...Async` replacements (for example
  `Player:LoadCharacterAsync()`, `Humanoid:ApplyDescriptionAsync()`). Check the API page before
  using an older name in new code.
- **`BindableEvent` is not a security boundary.** It only works inside one machine (server to
  server, or client to client) and never replaces a remote.
- **Type warnings depend on the solver.** Triage them against the solver and mode the place
  actually uses (`Workspace.UseNewLuauTypeSolver`, `Workspace.LuauTypeCheckMode`, or a
  `--!strict` / `--!nonstrict` comment), not against older behavior.

## Resources

- Read `references/client-server.md` when you need the replication timing details,
  `WaitForChild` behavior, Bindables, Attributes and CollectionService tags, or Studio test modes.

## Related skills

- `roblox-networking`: remote contracts, validation, rate limits, replication, Server Authority.
- `roblox-datastores`: persistence (server only).
- `roblox-studio-workflow`: editing an existing place, Studio MCP, and test evidence.
- `save-systems`, `input-systems`, `game-ai`: engine-neutral patterns to implement in Luau.

## Version notes

Last verified: 2026-11-11.

- Luau's New Type Solver reached general release in November 2025 for nocheck and non-strict
  scripts. Strict-mode places opt in with `Workspace.UseNewLuauTypeSolver = Enabled`;
  `Workspace.LuauTypeCheckMode` sets the default mode. The checker runs at edit time only.
- `SignalBehavior.Default` currently behaves as `Immediate`; Roblox states it will become
  `Deferred`.
- `Player:LoadCharacter()` is deprecated in favour of `LoadCharacterAsync()`.
- Tool versions checked: Rojo 7.7.1, selene 0.32.0, luau-lsp 1.70.1, Luau 0.746.
- To re-check an API: append `.md` to its Creator Hub URL, or start from
  `https://create.roblox.com/docs/llms.txt`.

Sources: `https://create.roblox.com/docs/reference/engine/classes/Workspace`,
`https://create.roblox.com/docs/reference/engine/enums/SignalBehavior`,
`https://create.roblox.com/docs/scripting/events/deferred`,
`https://create.roblox.com/docs/reference/engine/classes/Player`,
`https://devforum.roblox.com/t/general-release-luau%E2%80%99s-new-type-solver/4084991`,
GitHub releases for rojo-rbx/rojo, Kampfkarren/selene, JohnnyMorganz/luau-lsp, luau-lang/luau.
