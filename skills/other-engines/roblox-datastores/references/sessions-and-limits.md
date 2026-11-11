# Roblox DataStores: sessions, limits and metadata

Read this before shipping save code, or when debugging rollbacks, duplicated items, or throttling.

Contents:
- Session locking (with a lease sketch)
- Versioning and metadata
- Ordered stores: full pagination
- Request budgets and throttling
- Right to be forgotten (RTBF)
- Open Cloud (out-of-game access)

## Session locking

A player can briefly be in two servers (teleports, rejoin races). Two servers that load and later
save the same key lose writes. A session lock makes one server the owner of a key at a time:

1. On load, `UpdateAsync` the key to stamp it with this server's session ID and a timestamp, but
   only if it is unlocked or its lease has expired. Make the lease longer than the periodic save
   interval plus shutdown time.
2. If a live server holds it, retry a few times with backoff, then kick the player with a clear
   message or load read-only.
3. On every save, check inside the callback that this server still owns the key, refresh the
   lease together with the data, and cancel the write if ownership was lost. Release the lock in
   the same write as the final save on leave.

```lua
local HttpService = game:GetService("HttpService")
local SESSION_ID = HttpService:GenerateGUID(false)  -- game.JobId is "" in Studio, so not unique
local LEASE_SECONDS = 600

local function claim(store, key): (boolean, any)
    local claimed, loaded = false, nil
    local ok, err = pcall(function()
        store:UpdateAsync(key, function(record)
            record = record or {}
            local lock = record.lock
            local now = os.time()
            claimed = false                       -- the callback can run more than once
            if lock and lock.owner ~= SESSION_ID and now - lock.at < LEASE_SECONDS then
                return nil                        -- someone else owns it: cancel the write
            end
            record.lock = { owner = SESSION_ID, at = now }
            claimed, loaded = true, record.data
            return record
        end)
    end)
    if not ok then warn("claim failed", key, err) end
    return ok and claimed, loaded
end

local function save(store, key, data, release: boolean)
    return pcall(function()
        store:UpdateAsync(key, function(record)
            if not record or not record.lock or record.lock.owner ~= SESSION_ID then
                return nil                        -- lost ownership: never write a stale snapshot
            end
            record.data = data
            record.lock = if release then nil else { owner = SESSION_ID, at = os.time() }
            return record
        end)
    end)
end
```

The sketch stores `{ data = ..., lock = ... }` at the key. Keys saved earlier as plain data need a
one-time migration on first claim; decide that rule explicitly instead of guessing the shape.

`UpdateAsync` is the right primitive because its callback sees the current value, so the
check-and-set is atomic per request. A vetted open-source profile library implements the same
idea with more edge cases covered; if you write your own, test the teleport and rapid-rejoin
cases with two servers.

## Versioning and metadata

Regular `DataStore` keys support versioning and metadata; `OrderedDataStore` does
not (`DataStoreKeyInfo` is always `nil` there).

```lua
local DataStoreService = game:GetService("DataStoreService")
local store = DataStoreService:GetDataStore("PlayerData")

-- Attach UserIds (for content tracking) and custom metadata on write.
local options = Instance.new("DataStoreSetOptions")
options:SetMetadata({ schema = 2, region = "eu" })
pcall(function()
    store:SetAsync(key, data, { player.UserId }, options)
end)

-- Read returns a second value, the DataStoreKeyInfo.
local ok, value, keyInfo = pcall(function() return store:GetAsync(key) end)
if ok and keyInfo then
    print(keyInfo.Version, keyInfo.CreatedTime, keyInfo.UpdatedTime)
    print(keyInfo:GetUserIds(), keyInfo:GetMetadata())
end
```

Important: when you set metadata or UserIds, you must re-supply them on every write
or they're cleared. In `UpdateAsync`, the callback receives `(currentValue, keyInfo)` and
returns up to `(newValue, userIds, metadata)`; return `keyInfo:GetUserIds()` and
`keyInfo:GetMetadata()` when you are not changing them. List past versions with
`ListVersionsAsync` and fetch one with `GetVersionAsync` to recover from a bad write.

A `schema`/version number stored alongside the data lets you **migrate** old saves:
on load, if `data.schema < CURRENT`, transform the table forward before use.

## Ordered stores: full pagination

```lua
local boards = DataStoreService:GetOrderedDataStore("Coins")
local ok, pages = pcall(function()
    return boards:GetSortedAsync(false, 50)   -- descending, page size 50
end)
if ok then
    while true do
        for rank, entry in ipairs(pages:GetCurrentPage()) do
            -- entry.key (the data key), entry.value (the number)
        end
        if pages.IsFinished then break end
        pages:AdvanceToNextPageAsync()        -- yields; wrap loops in pcall in production
    end
end
```

`GetSortedAsync(ascending, pageSize, minValue?, maxValue?)` — page size (1–100) caps how
many entries `AdvanceToNextPageAsync` fetches per request; `minValue`/`maxValue` must be
integers.

To show specific players' scores (friends, a party) without paging the whole board, read
up to 100 keys in one request with `boards:BatchGetAsync(keys)`. It is supported only on
ordered stores, returns a dictionary of `key → { value = n }`, omits missing keys, and
each requested key counts against the ordered read budget.

## Request budgets and throttling

Current numbers are in the SKILL.md Version notes; the design rules below do not change with them.

- Requests draw on two budgets refreshed every minute: one for the whole experience (scales with
  total concurrent users and is shared with Open Cloud traffic) and one per server (scales with the
  players in that server). `UpdateAsync` spends from both the read and the write budget.
- Over budget, requests queue (each queue holds 30) and then fail with a 301-306 error.
  `DataStoreService:GetRequestBudgetForRequestType()` shows the current server's headroom, and
  `SetRateLimitForRequestType()` changes a server's share.
- A hot shared key throttles on its own per-key throughput limit (`KeyThrottled`) even when the
  experience budget has room. Shard read-heavy shared records across several keys only after
  removing unnecessary requests.
- Error-message names tell you which budget ran out: `...ExperienceThrottled` is the shared
  experience budget, `...GameServerThrottled` is this server's limit or a full queue.
- Storage is an experience-wide limit measured on the compressed latest version of each key.
  Superseded versions and deleted keys do not count. Store plain data; pre-compressing only adds
  CPU cost.
- Save on leave, in `BindToClose`, and on a periodic timer. Coalesce small changes into one write.
- A failed write call does not prove the write was not applied; verify with an uncached read
  (`DataStoreGetOptions.UseCache = false`, which costs a real request) before retrying a
  non-idempotent operation.

## Right to be forgotten (RTBF)

You're responsible for deleting a user's data on request. Implement a removal path
(e.g. `RemoveAsync` on every store keyed by that `UserId`, plus any ordered-store
entries) and the Open Cloud DataStore API can perform deletions from outside the
game. Keep the list of stores/keys a player touches so deletion is complete.

## Open Cloud (out-of-game access)

The Open Cloud DataStore API lets trusted external tools read/write the same stores
with scoped API keys — useful for admin dashboards, moderation, and bulk migration.
Treat the API key as a secret; never embed it in client or game code.
