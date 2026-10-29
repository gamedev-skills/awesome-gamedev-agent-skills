# Roblox DataStores: sessions, limits & metadata (current engine)

Depth behind the DataStores skill: session locking, versioning/metadata, ordered-
store pagination, request limits, and compliance.

## Session locking (preventing duplicate / clobbered data)

Players can occasionally be in two servers briefly (teleports, rejoin races). Two
servers loading and later saving the same key can lose writes. A *session lock*
makes a key owned by one server at a time:

1. On load, `UpdateAsync` the key to stamp it with this server's `JobId` and a
   timestamp, but only if it's unlocked or its lease has expired. Set the lease duration
   to accommodate the save/refresh interval and expected shutdown delays.
2. If it's locked by a live server, retry a few times, then either kick the player
   or load read-only.
3. On every save, verify the stored owner inside the callback and refresh its lease
   together with the data. Cancel the write if ownership was lost; a stale server must
   not resume saving. Keep ownership across periodic saves, then release it atomically
   with the final save when the player leaves.

`UpdateAsync` is the right primitive because its callback sees the current value, so
the check-and-set is atomic per request. (Production code often uses a vetted
open-source profile/session library that implements this correctly; if you roll your
own, test the teleport and rapid-rejoin cases.)

## Versioning & metadata

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

## Request limits & throttling

- Requests draw on two tiers of per-minute budget, both refreshed continuously: an
  EXPERIENCE-level (game-wide) budget that scales with total concurrent users across the
  whole experience, and a per-SERVER budget that scales with the players in that one
  server. Since 2026-07-29 the in-game (game server) and Open Cloud APIs SHARE the
  experience-level budget, so heavy external Open Cloud traffic can throttle in-game
  requests and vice versa. Experience limits start at a 300/min baseline plus a per-CCU
  multiplier per request type (reads scale fastest, lists slowest); `UpdateAsync` spends
  from BOTH the read and write budgets on every call. Exceeding a budget queues requests
  (each queue holds ~30) and then drops them with a 301-306 error. Per-server defaults are
  configurable via `DataStoreService:SetRateLimitForRequestType`; check current headroom
  with `GetRequestBudgetForRequestType`.
- Storage is a GAME-level limit, not per-key: total = 500 MB + 1 MB x lifetime user count
  (any user who has ever joined), measured on the compressed latest version of each key.
  Superseded versions and deleted keys do not count toward it. Store plain data; Roblox
  compresses it, so pre-compressing only adds CPU cost.
- Per entry: store, key, and scope names are at most 50 characters; a value is at most
  4,194,304 characters of serialized JSON (measure with `HttpService:JSONEncode`).
  Per key across all servers: about 25 MB/minute of reads and 4 MB/minute of writes,
  rounded up to the next KB per request. A hot shared key throttles as `KeyThrottled`
  even when the experience budget has room.
- A failed write call does not prove the write was not applied; verify with an uncached
  read before retrying a non-idempotent operation.
- `GetAsync` results are cached for about four seconds — an immediate re-read returns the
  cached value, not necessarily the freshest. For a verification read after a write, pass
  a `DataStoreGetOptions` with `UseCache = false` (it costs a real request).
- Practical rules: save on leave / `BindToClose` and on a periodic timer (e.g. every
  60–120s), **not** on every value change. Coalesce many small changes into one
  write. Use `UpdateAsync` with a merge policy or verified session ownership; returning
  a stale snapshot unchanged can still overwrite another writer's progress.
- Treat every Async call as fallible: `pcall` + bounded retry with backoff. See
  `https://create.roblox.com/docs/cloud-services/data-stores/error-codes-and-limits`
  for the exact current numeric limits, which change over time.

## Right to be forgotten (RTBF)

You're responsible for deleting a user's data on request. Implement a removal path
(e.g. `RemoveAsync` on every store keyed by that `UserId`, plus any ordered-store
entries) and the Open Cloud DataStore API can perform deletions from outside the
game. Keep the list of stores/keys a player touches so deletion is complete.

## Open Cloud (out-of-game access)

The Open Cloud DataStore API lets trusted external tools read/write the same stores
with scoped API keys — useful for admin dashboards, moderation, and bulk migration.
Treat the API key as a secret; never embed it in client or game code.
