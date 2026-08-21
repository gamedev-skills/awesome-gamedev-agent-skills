---
name: roblox-networking
description: >
  Design and harden Roblox client/server networking with RemoteEvent, RemoteFunction, and
  UnreliableRemoteEvent; server authority, argument and Instance validation, rate limits,
  proximity/ownership checks, targeted replication, streaming, lifecycle, prediction, and
  reconciliation. Use for Roblox remotes, exploits, request spam, multiplayer replication,
  network ownership, high-frequency cosmetic updates, or server/client desynchronization.
---

# Roblox networking

Build explicit request and replication contracts in which the server decides authoritative game
state and clients provide input or intent. Targets Roblox's rolling platform APIs. This skill goes
deeper than the networking primer in `roblox-luau`.

## When to use

- Use to design, implement, debug, or secure cross-boundary Roblox communication.
- Use when a remote trusts client values, an exploiter can target arbitrary Instances, messages
  spam services, streamed objects are missing, or clients disagree with the server.

**When not to use:** basic Luau/services belong to `roblox-luau`; persistent state belongs to
`roblox-datastores`; physical ownership mechanics also compose with `roblox-physics`.

## Workflow

1. **Inspect the existing protocol.** Find every remote and both endpoints; document direction,
   sender, payload, frequency, authority, validation, and consumers. Reuse the canonical remote
   folder—do not create a duplicate because discovery was skipped.
2. **Classify each message.** Client request, server fact, or ephemeral cosmetic sample. Choose
   reliable event, unreliable event, or request/response from semantics—not convenience.
3. **Minimize the payload.** Send stable identifiers and intent. Do not send a price, damage,
   ownership result, arbitrary path, or computed outcome the server can derive.
4. **Validate in layers.** Check type/shape/finiteness, allowlisted value, Instance class and
   ancestry, player permissions/state, distance/line of sight where relevant, server cooldown,
   and rate budget before doing expensive work.
5. **Apply on the server.** The server resolves targets and mutates health, inventory, currency,
   cooldowns, and progression. Client-side checks improve UX but grant no trust.
6. **Replicate narrowly.** Use `FireClient` for private or local facts; broadcast only shared facts.
   Avoid sending replicated properties again unless the client needs a distinct presentation event.
7. **Handle time and lifecycle.** Requests may arrive after death, respawn, streaming changes, or
   disconnect. Resolve the current character/state during handling and clean per-player limiter data.
8. **Verify with Server & Clients.** Exercise normal, malformed, spam, out-of-range, stale
   character, rapid respawn, leaving, simultaneous players, targeted, and broadcast cases. Inspect
   server and each client Output separately.

## Choose the transport

| Primitive | Use | Do not use |
|---|---|---|
| `RemoteEvent` | ordered, reliable one-way requests/facts | continuous samples where newer replaces older |
| `UnreliableRemoteEvent` | ephemeral cosmetic/continuous state tolerant of loss and reordering | purchases, damage decisions, inventory, one-shot state transitions |
| `RemoteFunction` | bounded client-to-server query that truly needs an immediate reply | server-to-client invocation; long/uncertain work; ordinary commands |

Never invoke a client synchronously from the server. A client may disconnect, error, or never
return. Prefer server `RemoteEvent:FireClient()` and a separate response event when needed.

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

This is still only a compact example: a real melee system may require server-known attack windows,
line-of-sight/shape checks, team rules, and lag policy. Do not treat one distance check as security.

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

Assign cost by server impact. Reject cheaply before datastore calls, cloning, raycasts, or broad
replication. Log aggregate abuse signals, not one warning per rejected packet.

## Replication, streaming, and prediction

- Replicated Instances/properties are already a state channel. Use remotes for intent, private
  state, or presentation cues, not an unconditional parallel copy of the DataModel.
- With instance streaming, a valid server Instance may not exist on a client. Send a stable ID and
  tolerate absence; do not wait forever for optional streamed content.
- High-rate cosmetic data may use `UnreliableRemoteEvent`; make each sample self-contained because
  delivery and order are not guaranteed. Keep payloads well below its documented size limit.
- Predict only latency-sensitive reversible presentation. Include a client sequence/command ID;
  the server returns authoritative state and acknowledgement; the client corrects smoothly. Never
  let prediction award damage, currency, inventory, or progression.
- Network ownership improves responsiveness but lets that client influence physical simulation.
  Validate gameplay consequences on the server; ownership is not authorization.

## Common failures

| Symptom | Likely cause | Remedy |
|---|---|---|
| exploiter chooses damage/price | outcome accepted from client | send intent/ID; derive and apply on server |
| arbitrary object can be deleted | only `typeof(Instance)` checked | validate class, ancestry, ownership, state, and allowlisted operation |
| server stalls on a player | server invokes client `RemoteFunction` | replace with asynchronous events |
| valid player triggers throttling | per-frame reliable messages | lower frequency, state replication, batching, or unreliable cosmetics |
| old packet reverses new effect | unordered unreliable samples treated as commands | make samples replaceable/versioned; use reliable event for transitions |
| remote breaks after respawn | cached character/root | resolve current character during handling and reject stale state |
| private data leaks | `FireAllClients` used by default | use `FireClient` and minimal payloads |
| distance check is bypassed | client-owned object moved near target | anchor/server-own critical object and validate full server context |

## Resources

- Read `references/validation-and-testing.md` for payload rules, Instance/finiteness checks,
  replication design, and the required multi-client abuse matrix.

## Related skills

- `roblox-luau` — execution locations and basic RemoteEvent mechanics.
- `roblox-characters` — respawn-safe character resolution.
- `roblox-physics` — network ownership, ray/overlap validation, and physical consequences.
- `roblox-studio-workflow` — Server & Clients testing and Output inspection.

## Primary references

- `https://create.roblox.com/docs/scripting/events/remote`
- `https://create.roblox.com/docs/scripting/security/client-server-boundary`
- `https://create.roblox.com/docs/physics/network-ownership`
- `https://create.roblox.com/docs/studio/testing-modes`
