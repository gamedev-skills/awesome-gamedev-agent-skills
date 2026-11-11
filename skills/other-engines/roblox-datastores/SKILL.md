---
name: roblox-datastores
description: >
  Roblox DataStoreService persistence: load on join, save on leave and BindToClose, UpdateAsync vs
  SetAsync, session locking and OrderedDataStore leaderboards. Use for lost player data, items
  duplicating after teleport, or "too many requests" errors. Not for engine-neutral saves
  (`save-systems`), Luau basics (`roblox-luau`) or economy numbers (`roblox-simulator-economy`).
---

# Roblox DataStores

Persist data across sessions without losing or duplicating it. All DataStore calls are network
requests from server `Script`s; they can fail, be throttled, and race with another server writing
the same key.

## Workflow

1. **Find the existing persistence layer.** Search for `DataStoreService`, `GetDataStore`, and any
   profile or session library before writing new code. If the project already uses one, extend it;
   two systems writing the same key is the most common cause of rollbacks.
2. **Use a test place for Studio work.** Studio reads and writes the same live data as players.
   In a separate published test place, turn on File → Experience Settings → Security → *Enable
   Studio Access to API Services*; without it, requests fail with `StudioAccessToApisNotAllowed`.
3. **Key by `UserId`**, never by name: `"Player_" .. player.UserId`.
4. **Guard every call with `pcall`.** On a failed *load*, mark the session as not loaded and refuse
   to save, so defaults never overwrite real data.
5. **Load on `PlayerAdded`, save on `PlayerRemoving` and in `game:BindToClose`**, plus a periodic
   save (every 60-120 s), never on every value change.
6. **Write with `UpdateAsync` and session ownership.** `UpdateAsync` reads the latest value before
   writing; session ownership (in `references/sessions-and-limits.md`) stops a stale server from
   writing an old snapshot over newer progress.
7. **Use `OrderedDataStore` only for numeric rankings** (leaderboards).
8. **Check before reporting.** Run the static check below and fix every hit. Then, with the Studio
   MCP server connected and API access on in a test place, play, change a value, stop, play again,
   and read it back with an uncached read from `execute_luau` on the `Server` datamodel. Without
   MCP, ask the user to do join, change, leave, rejoin in the test place and report the value seen
   after rejoining and any Output warnings. Rate-limit behavior needs Team Create, not Run mode.

```bash
# Every DataStore call should sit inside pcall; this lists the lines to inspect by hand.
rg -n ":(GetAsync|SetAsync|UpdateAsync|IncrementAsync|RemoveAsync|GetSortedAsync)\(" src
rg -n "BindToClose" src        # expect at least one save-everyone handler
rg -n ":SetAsync\(" src        # each one on a player profile key needs a reason
```

## Patterns

### Load on join

```lua
local DataStoreService = game:GetService("DataStoreService")
local Players = game:GetService("Players")
local store = DataStoreService:GetDataStore("PlayerData")

local DEFAULT = { Coins = 0, Level = 1 }

Players.PlayerAdded:Connect(function(player)
    local key = "Player_" .. player.UserId
    local ok, data = pcall(function()
        return store:GetAsync(key)
    end)
    if not ok then
        warn("Load failed for", player.UserId, data)  -- network failure, not a new player
        player:SetAttribute("DataLoaded", false)
        return
    end
    player:SetAttribute("DataLoaded", true)
    applyToLeaderstats(player, data or table.clone(DEFAULT))  -- nil means a genuinely new player
end)
```

### Save with UpdateAsync (session ownership still required)

This callback ignores `old`, so on its own it can overwrite newer progress from another server.
Before shipping, add the session check from `references/sessions-and-limits.md` inside the
callback, or use a vetted profile library.

```lua
local function savePlayer(player)
    -- `~= true` also covers a player who left while GetAsync was still in flight.
    if player:GetAttribute("DataLoaded") ~= true then return end
    local key = "Player_" .. player.UserId
    local newData = gatherDataFor(player)    -- plain, JSON-serializable table

    local ok, err = pcall(function()
        store:UpdateAsync(key, function(old)
            -- Must not yield and may run more than once. Return nil to cancel the write
            -- when this session no longer owns the key.
            return newData
        end)
    end)
    if not ok then warn("Save failed for", player.UserId, err) end
end
```

### Save on leave and on shutdown

```lua
Players.PlayerRemoving:Connect(savePlayer)

game:BindToClose(function()
    local players = Players:GetPlayers()
    local remaining = #players
    for _, player in players do
        task.spawn(function()
            savePlayer(player)
            remaining -= 1
        end)
    end
    while remaining > 0 do task.wait() end  -- the server waits at most 30 s in total
end)
```

### Retry only what is safe to repeat

```lua
local function withRetry(fn, attempts)
    attempts = attempts or 3
    for i = 1, attempts do
        local ok, result = pcall(fn)
        if ok then return true, result end
        if i < attempts then task.wait(2 ^ i) end
    end
    return false
end
```

A failed write does not prove the write did not happen; the server may only have missed the
response. Re-running an `UpdateAsync` that writes the full state is harmless; re-running
`IncrementAsync` can add twice. When the outcome matters, confirm with an uncached read
(`DataStoreGetOptions` with `UseCache = false`) before retrying.

### Leaderboard with OrderedDataStore

```lua
local board = DataStoreService:GetOrderedDataStore("Coins")
pcall(function() board:SetAsync("Player_" .. player.UserId, coins) end)  -- on change, throttled

local ok, pages = pcall(function()
    return board:GetSortedAsync(false, 10)   -- false = descending, highest first
end)
if ok then
    for rank, entry in pages:GetCurrentPage() do
        print(rank, entry.key, entry.value)
    end
end
```

Values must be integers. For a few specific players (friends, a party), `BatchGetAsync(keys)`
reads up to 100 keys in one request instead of paging the whole board.

## Gotchas

- **Defaults saved over real data.** A failed load treated as "new player" wipes progress on the
  next save. Gate saves on "load succeeded", not on "load did not fail".
- **`SetAsync` races between servers.** During a teleport or fast rejoin two servers can hold the
  same player; the last blind write wins. Use `UpdateAsync` with session ownership.
- **Yields or side effects inside the `UpdateAsync` callback.** The callback cannot yield, and
  Roblox re-runs it when another server changed the key first, so granting items, firing remotes
  or incrementing counters inside it can happen twice. Act after the call returns.
- **No `BindToClose` save.** Players in the server at shutdown lose everything since the last
  periodic save.
- **Saving on every change.** Throttling queues requests and then drops them with 301-306 errors.
  Coalesce changes and save on a timer and on leave.
- **Stale reads.** `GetAsync` caches a key for about four seconds after the first read, so an
  immediate re-read after a write may return the old value.
- **Non-serializable values.** Only JSON-like data persists: numbers, strings, booleans, and tables
  with string or sequential number keys. Convert `Vector3`, `CFrame`, `Color3` and Instances to
  plain tables first.
- **Metadata and UserIds cleared on write.** Once a key has metadata or UserIds, every write must
  supply them again or they are removed.
- **`DataStoreKeyInfo` is nil for ordered stores.** They have no versioning or metadata; use a
  regular `DataStore` when you need those.
- **Temporary cross-server state.** Matchmaking queues and per-round data belong in
  `MemoryStoreService`, not DataStores.

## Resources

- Read `references/sessions-and-limits.md` before shipping save code or when debugging rollbacks,
  duplication, or throttling: session locking, versioning and metadata, pagination, request
  budgets, storage limits, Right to be Forgotten, and Open Cloud.

## Related skills

- `roblox-luau`: services, events, and the server/client model.
- `roblox-simulator-economy`: repairing loaded values and offline earnings.
- `save-systems`: engine-neutral serialization, slots, and migration.

## Version notes

Last verified: 2026-11-11.

- Since 2026-07-29, in-game and Open Cloud requests share one per-experience budget per request
  type: 300 per minute plus a per-CCU multiplier (reads 40, writes 20, lists 2 for standard and
  ordered stores). `UpdateAsync` spends from both read and write. Per-server limits still apply.
- Storage limit per experience: 500 MB + 1 MB per lifetime user, measured on the compressed latest
  version of each key.
- Per key: about 25 MB per minute of reads and 4 MB per minute of writes. Value size: 4,194,304
  characters. Key, store and scope names: 50 characters.
- `BindToClose` handlers get 30 seconds in total. Studio Run mode uses its own lower static
  limits; test rate limits in Team Create.
- Automated Right to be Forgotten processing for data stores was in beta during 2026; check its
  status before relying on it.

Sources: `https://create.roblox.com/docs/cloud-services/data-stores`,
`https://create.roblox.com/docs/cloud-services/data-stores/error-codes-and-limits`,
`https://create.roblox.com/docs/reference/engine/classes/GlobalDataStore`,
`https://create.roblox.com/docs/reference/engine/classes/DataModel` (BindToClose),
`https://devforum.roblox.com/t/unifying-data-stores-open-cloud-and-game-apis-and-increasing-storage-limits/4739240`.
