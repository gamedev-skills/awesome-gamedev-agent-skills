# Roblox remote validation and multi-client testing

Read this for a new/changed remote contract or an exploit/desynchronization investigation.

## Contract worksheet

For each message record: remote path; client-to-server/server-to-client; sender; payload schema;
maximum expected frequency/size; authoritative owner; rejection rules; recipient scope; behavior if
the player, character, or referenced Instance disappears.

## Validation order

Reject in the cheapest useful order:

1. limiter budget;
2. argument count and `type`/`typeof`;
3. numeric finiteness (`value == value` rejects NaN; compare against `math.huge`) and range;
4. string length and allowlist; table depth/entry count and exact expected keys;
5. Instance class, ancestry, tag/attribute, current membership, and player ownership;
6. authoritative player state, cooldown, alive/current character, permission/team;
7. geometry such as distance, overlap, or line of sight using server-observed state;
8. only then expensive work and authoritative mutation.

Avoid accepting arbitrary callback names, module/asset IDs, DataModel paths, or Instances for broad
mutation. A client-visible secret is not a security boundary; renaming/remapping remotes does not
replace validation.

## Replication choices

Use targeted messages for private inventory, quest details, personal prediction acknowledgements,
and UI cues visible to one player. Broadcast only world facts all relevant clients need. For nearby
effects, select recipients on the server rather than broadcasting and asking every client to filter.

An unreliable sample should carry enough state to stand alone and may include a monotonically
increasing sequence/time so clients can ignore older arrivals. Never split one required logical
transition across several unreliable messages.

## Required Server & Clients matrix

Run at least two clients where possible and capture server/client Output:

| Case | Expected evidence |
|---|---|
| valid request | exactly one server mutation and correct recipient update |
| wrong type/shape, NaN/huge value | rejected without error or expensive work |
| unknown or wrong-ancestry Instance | rejected; unrelated Instance unchanged |
| burst and sustained spam | limiter rejects; server remains responsive; logs bounded |
| out of range / no permission / cooldown | authoritative state unchanged |
| character dies or respawns mid-request | stale request rejected; new character works |
| player leaves during pending work | no stale table entries or callback errors |
| two simultaneous players | budgets/state remain per player; no cross-target leak |
| targeted server message | only intended client observes it |
| broadcast | all connected clients observe once |
| unreliable cosmetic load | losses/reordering do not corrupt gameplay state |

Do not weaken production validation just to inject malformed calls. Use a Studio-only test harness
or Command Bar fixture that calls the same pure validator/handler boundary, and remove it after the
test. Record unexecuted cases explicitly.

## Primary references

- `https://create.roblox.com/docs/scripting/security/client-server-boundary`
- `https://create.roblox.com/docs/reference/engine/classes/UnreliableRemoteEvent`
- `https://create.roblox.com/docs/studio/testing-modes`
