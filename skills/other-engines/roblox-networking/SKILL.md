---
name: roblox-networking
description: >
  Roblox client-server networking and anti-exploit: RemoteEvent and RemoteFunction contracts,
  server authority, rate limits, hit validation and replication. Use when a remote trusts the
  client, exploiters spam remotes or gain items, or hits register wrongly. Not for Luau basics
  (`roblox-luau`), saving (`roblox-datastores`) or force and raycast APIs (`roblox-physics`).
---

# Roblox networking

The server decides authoritative state; clients send input or intent. This skill owns the request
contract across that boundary: what is sent, who validates it, who receives the result, and how it
is tested with more than one client.

## Workflow

1. **Inventory the existing protocol.** Find every remote and both endpoints before adding one:
   `rg -n "OnServerEvent|OnServerInvoke|OnClientEvent|InvokeClient|FireAllClients" src`
   (or the Studio MCP `script_grep` tool). For each, note direction, sender, payload, frequency,
   validation, and consumers. Reuse the canonical remote folder; a duplicate remote created because
   discovery was skipped usually means two handlers apply the same action.
2. **Classify each message.** Client request, server fact, or ephemeral cosmetic sample. Pick
   reliable event, unreliable event, or request/response from that, not from convenience.
3. **Minimize the payload.** Send stable IDs and intent. Never send a price, damage, ownership
   result, arbitrary path, or any outcome the server can derive.
4. **Validate in layers, cheapest first.** Rate budget, type/shape/finiteness, allowlisted value,
   Instance class and ancestry, player permission and state, distance or line of sight, cooldown.
   Only then do expensive work.
5. **Apply on the server.** The server resolves targets and mutates health, inventory, currency,
   cooldowns, and progression. Client checks are UX only.
6. **Replicate narrowly.** `FireClient` for private or local facts; broadcast only shared facts.
   Replicated properties are already a state channel, so do not mirror them through remotes.
7. **Handle time and lifecycle.** Requests arrive after death, respawn, streaming changes, or
   disconnect. Resolve the current character during handling and clear per-player tables on
   `PlayerRemoving`.
8. **Run the abuse matrix and capture Output from every side.** With the Studio MCP server
   connected (`list_roblox_studios` returns a place), start play with `start_stop_play`, drive the
   pure validator from `execute_luau` on the `Server` datamodel with valid, malformed, NaN, wrong
   Instance and burst inputs, then read `get_console_output`. `start_stop_play` is one solo client,
   so for targeted versus broadcast delivery and two-player cases ask the user to run Server &
   Clients with two clients and paste the server and both client Output panes. Report each case as
   executed, prepared but not run, or unverified.

## Choose the transport

| Primitive | Use | Do not use |
|---|---|---|
| `RemoteEvent` | ordered, reliable one-way requests and facts | continuous samples where newer replaces older |
| `UnreliableRemoteEvent` | ephemeral cosmetic or continuous state that tolerates loss and reordering | purchases, damage, inventory, one-shot transitions |
| `RemoteFunction` | bounded client-to-server query that truly needs a reply | server-to-client invocation, long work, ordinary commands |

Never `InvokeClient` from the server: a client that errors makes the server error, a client that
leaves makes it throw, and a client that never returns makes it yield forever. Use `FireClient`
plus a separate response event.

Delivery rules that change handler design (per connection, per direction):

- `RemoteEvent` messages arrive in send order, even across different `RemoteEvent`s, but order
  covers when each handler *starts*. A handler that yields (`task.wait`, `WaitForChild`, a
  DataStore call) lets the next message from the same player start before it resumes, so
  check-then-yield-then-apply code can approve two requests. Claim the cooldown or mark the
  request in progress before the first yield.
- A client firing a `RemoteEvent` faster than the throttle is delayed, not dropped; the backlog
  still arrives. `UnreliableRemoteEvent` traffic over the throttle or size cap, or with no handler
  connected, is discarded.
- Messages sent before a handler connects are queued (bounded) for `RemoteEvent`s and
  `RemoteFunction`s. There is no ordering guarantee between a `RemoteFunction` and a
  `RemoteEvent`; use one remote type or your own sequence number when order matters.
- The client-to-server throttle is shared by every remote of the same type in the experience, so a
  legitimate player sending per-frame reliable events hits it before any attacker does.

## Pattern: validate before resolving gameplay

```lua
-- ServerScriptService/CombatRequests.server.luau
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Workspace = game:GetService("Workspace")

local attack = ReplicatedStorage.Remotes.Attack
local lastRequest: {[Player]: number} = {}
local RANGE = 12
local COOLDOWN = 0.25

attack.OnServerEvent:Connect(function(player: Player, target: unknown)
    local now = Workspace:GetServerTimeNow()
    if now - (lastRequest[player] or -math.huge) < COOLDOWN then return end
    lastRequest[player] = now

    if typeof(target) ~= "Instance" or not target:IsA("Model") then return end
    if not target:IsDescendantOf(Workspace.Characters) then return end
    local targetHumanoid = target:FindFirstChildOfClass("Humanoid")
    local targetRoot = target:FindFirstChild("HumanoidRootPart")
    local character = player.Character
    local root = character and character:FindFirstChild("HumanoidRootPart")
    local humanoid = character and character:FindFirstChildOfClass("Humanoid")
    if not targetHumanoid or not targetRoot or not root or not humanoid then return end
    if humanoid.Health <= 0 or targetHumanoid.Health <= 0 then return end
    if (root.Position - targetRoot.Position).Magnitude > RANGE then return end
    if not serverCombatStateAllowsAttack(player, now) then return end

    targetHumanoid:TakeDamage(serverDamageFor(player))
end)

Players.PlayerRemoving:Connect(function(player)
    lastRequest[player] = nil
end)
```

One distance check is not security. A real melee system also needs server-known attack windows,
shape or line-of-sight checks, team rules, and a lag policy.

**Hit validation for ranged weapons.** The client may report "I fired at time T toward D". The
server rebuilds the shot from server-known state: muzzle origin near the server's character
position, fire rate from the weapon's cooldown, ammo, and a direction within a tolerance of the
claim. Then the server runs its own raycast (query API in `roblox-physics`). Decide the lag policy
explicitly: either accept hits within a bounded rewind window using recorded target positions, or
accept only what the server sees now. Never accept the client's hit `Instance` or hit position as
the result.

## Pattern: token bucket at the boundary

```lua
type Bucket = {tokens: number, updatedAt: number}
local buckets: {[Player]: Bucket} = {}
local CAPACITY, REFILL_PER_SECOND = 6, 3

local function consume(player: Player, cost: number): boolean
    local now = os.clock()
    local bucket = buckets[player] or {tokens = CAPACITY, updatedAt = now}
    bucket.tokens = math.min(CAPACITY,
        bucket.tokens + (now - bucket.updatedAt) * REFILL_PER_SECOND)
    bucket.updatedAt = now
    if bucket.tokens < cost then buckets[player] = bucket; return false end
    bucket.tokens -= cost
    buckets[player] = bucket
    return true
end
```

Assign cost by server impact. Reject cheaply before DataStore calls, cloning, raycasts, or broad
replication. Log aggregate abuse signals, not one warning per rejected packet. Clear the bucket on
`PlayerRemoving`.

## Replication, streaming, and prediction

- With instance streaming, a valid server Instance may not exist on a client. Send a stable ID and
  tolerate absence; do not wait forever for optional streamed content.
- Make each unreliable sample self-contained and add a sequence number or timestamp so receivers
  drop older arrivals. Never split one required transition across several unreliable messages.
- Without Server Authority, predict only latency-sensitive, reversible presentation. Tag client
  commands with a sequence ID; the server returns authoritative state plus an acknowledgement and
  the client corrects smoothly. Prediction never awards damage, currency, inventory, or progression.
- Network ownership makes a client responsive but lets it influence physics. Ownership is not
  authorization: validate consequences on the server.

## Places that use Server Authority

Read `Workspace.AuthorityMode` first (Properties panel, the place file, or `execute_luau`). When it
is `Server`, the engine supplies client prediction, rollback, and resimulation, and gameplay
objects can stay server-owned without input lag. Work with it instead of building a parallel
scheme:

- Put core gameplay in a ModuleScript required by both a server `Script` and a client
  `LocalScript`, with logic in `RunService:BindToSimulation()` callbacks. Only members labelled
  *Simulation Access* work there. Use `time()` (synchronized and rewound during resimulation), not
  `os.clock()`, `tick()`, or `os.time()`.
- Send simulation-affecting input through `InputAction`s (their `InputContext` must sit under the
  owning `Player`), not `UserInputService` events. Keep synchronized custom state in Attributes on
  predicted instances and write them only inside bound functions.
- `Destroy()` and reparenting are not allowed inside bound functions. Record the intent in an
  Attribute and remove the instance in a server `PostSimulation` connection. `Humanoid:EquipTool()`
  is not simulation-safe either, so equippable items are welded Models tracked by an Attribute.
- Remotes still carry discrete facts and requests, but they are not ordered with property and
  attribute replication. Play effects and sounds from `RenderStepped` reading simulation results,
  so a mispredicted frame does not trigger them twice, and make them undoable.
- `RunService:SetPredictionMode()` (client-only) forces prediction per instance, and
  `RunService:GetPredictionStatus()` shows what is predicted. Test with Studio's Network Simulator
  (latency, jitter, loss).

Server Authority is a project-wide migration. Do not switch `AuthorityMode` on an existing place as
a side effect of another task; report it as an option instead.

## Gotchas

| Symptom | Likely cause | Remedy |
|---|---|---|
| exploiter chooses damage or price | outcome accepted from client | send intent or ID; derive and apply on server |
| arbitrary object can be deleted | only `typeof(x) == "Instance"` checked | validate class, ancestry, ownership, state, and an allowlisted operation |
| server stalls on one player | server calls `InvokeClient` | replace with events |
| honest player is throttled | per-frame reliable messages | lower rate, rely on replication, batch, or use unreliable cosmetics |
| old packet reverses a newer effect | unreliable samples treated as commands | version samples; use a reliable event for transitions |
| remote breaks after respawn | cached character or root | resolve the current character in the handler; reject stale state |
| private data leaks | `FireAllClients` by default | `FireClient` with a minimal payload |
| distance check bypassed | client-owned part moved near target | server-own critical parts; validate with server-observed state |
| one cooldown lets two requests through | handler yields between check and apply | claim cooldown or in-progress state before the first yield |
| effect plays twice under Server Authority | effect triggered inside resimulated code | trigger from `RenderStepped` reading simulation state |
| "lag" report | could be frame time, not network | check the MicroProfiler (or Studio's `rbx-perf-profiling` skill) before redesigning remotes |

## Resources

- Read `references/validation-and-testing.md` when writing or changing a remote contract, or
  investigating an exploit or desync: payload rules, validation order, and the full multi-client
  abuse matrix.

## Related skills

- `roblox-luau`: execution locations and basic remote mechanics.
- `roblox-characters`: respawn-safe character resolution.
- `roblox-physics`: raycast and overlap APIs, network ownership mechanics.
- `roblox-studio-workflow`: Server & Clients testing, Studio MCP, and honest evidence.

## Version notes

Last verified: 2026-11-11.

- `UnreliableRemoteEvent` payloads over 1,000 bytes are dropped; Studio Output reports the overage.
- Client-to-server throttle: about 500 requests per second per client, shared by all remotes of the
  same type (`RemoteEvent` and `UnreliableRemoteEvent` each have their own pool).
- Server Authority reached full release in July 2026 (opt-in). Setting `AuthorityMode = Server`
  also requires next-generation replication, `PlayerScriptsUseInputActionSystem`, deferred
  `SignalBehavior`, `UseFixedSimulation`, and `StreamingEnabled`. The release stopped synchronizing
  the Camera `InputAction`; use `Player:GetCameraState()`. Replicated attributes on predicted
  instances: the first 64 per instance, names and string values up to 50 characters. Tools are not
  fully supported yet.
- Studio's Network Simulator was a Studio beta (File → Beta Features → New Device Simulator).
- To re-check: append `.md` to any Creator Hub docs URL, or start from
  `https://create.roblox.com/docs/llms.txt`. With Studio MCP connected, `http_get` and the
  built-in `rbx-docs-search` skill fetch the same pages.

Sources: `https://create.roblox.com/docs/scripting/events/remote`,
`https://create.roblox.com/docs/reference/engine/classes/UnreliableRemoteEvent`,
`https://create.roblox.com/docs/projects/server-authority`,
`https://create.roblox.com/docs/scripting/security/client-server-boundary`,
`https://create.roblox.com/docs/physics/network-ownership`,
`https://create.roblox.com/docs/studio/testing-modes`,
`https://devforum.roblox.com/t/full-release-ship-fair-and-competitive-games-with-server-authority/4727993`.
