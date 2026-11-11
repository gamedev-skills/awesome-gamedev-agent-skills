# Networking and multiplayer

Read only for requested multiplayer work. Ebitengine supplies the game loop,
not a network protocol, matchmaking or authoritative server. Go libraries can
provide transport; browser builds have different transport constraints. Keep rules
independent of rendering so clients, tests and a server can share them.

This reference is design guidance, not a ready-to-ship netcode implementation.
A toy relay or same-process determinism test is insufficient evidence for an
online game. Add executable protocol tests in the actual project.

## Contents

- [Choose the model from latency and trust requirements](#choose-the-model-from-latency-and-trust-requirements)
- [Fixed simulation and determinism](#fixed-simulation-and-determinism)
- [Lockstep protocol invariants](#lockstep-protocol-invariants)
- [Transport and lifecycle](#transport-and-lifecycle)
- [Private views and session lifecycle](#private-views-and-session-lifecycle)
- [Verification before claiming online support](#verification-before-claiming-online-support)

## Choose the model from latency and trust requirements

| Need | Candidate | Main cost |
| --- | --- | --- |
| Local play | several devices/actions in one simulation | device ownership and join/leave flow |
| Turn-based or asynchronous moves | server validates moves over HTTP/WebSocket | reconnect, persistence, turn ownership |
| Synchronized deterministic simulation | lockstep, exchanging inputs | peers wait for missing input; determinism and latency budget |
| Responsive deterministic action | rollback with prediction and state restore | full state capture, re-simulation, cosmetic event reconciliation |
| Many players or authoritative competition | server authority with prediction/interpolation | server operations, correction and interpolation |

These are choices, not genre rules. Online play need not start as a local
multiplayer product. A local two-peer harness is useful for testing the chosen
protocol. Establish player count, acceptable delay, join/reconnect behavior and
hosting before expanding content that depends on them.

## Fixed simulation and determinism

- Keep the simulation tick distinct from Ebitengine's presentation/update clock.
  When lockstep stalls, continue sampling input, polling messages and drawing;
  do not block `Update` waiting for a peer.
- For cross-architecture bit identity, integers/fixed point simplify positions
  and velocities. Go permits fused floating-point operations and architecture
  implementations can differ; do not infer cross-platform determinism from two
  copies in one process. See the [Go spec](https://go.dev/ref/spec#Floating_point_operators).
- Stable iteration order matters: sort map keys or use ordered storage for
  simulation. Separate gameplay and cosmetic RNGs; serialize all gameplay RNG
  state for rollback. Fixed seeds alone do not control input order or threading.
- Version the rules, content and protocol. Exchange hashes at agreed simulation
  ticks, compare states at the same tick, and retain inputs/seed/version to
  reproduce a desync. Test across the supported architectures.

## Lockstep protocol invariants

Use a fixed session roster and input delay selected from measured latency/jitter.
Three to six ticks is only 50–100 ms at 60 TPS; it does not cover every internet
connection. Seed initial delayed ticks consistently.

For each simulation tick:

1. Sample local actions and schedule them for the appropriate future tick.
   Send each tick's immutable input once. Waiting for remote input must not
   repeatedly overwrite or resend a different value for the same local tick.
2. Drain received messages from a bounded inbox. Validate session, authenticated
   sender/player mapping, tick window, input bits and duplicate consistency.
3. Advance only when the roster's inputs for the current tick are complete.
   Release consumed history according to the replay/rollback policy.
4. If a peer stalls/disconnects, apply an explicit timeout/reconnect/end policy
   while menus and status remain responsive.

Reject invalid player indices before indexing, bound future/history windows and
queue sizes, and reject conflicting duplicates. A peer-supplied `Player` field
alone is not identity. A reliable ordered transport does not supply a session
handshake, late join, state synchronization or authority.

## Transport and lifecycle

`github.com/coder/websocket` supports Go desktop and `js/wasm`; browsers cannot
use Go's raw TCP/UDP APIs. Pin and inspect the transport version and its
[documentation](https://pkg.go.dev/github.com/coder/websocket). HTTPS pages need
secure WebSocket endpoints. Use only transports supported by the chosen targets.

- Dial, read and write outside `Update`/`Draw`. Queue immutable commands and
  results. Blocking writes with `context.Background()` can freeze a game even
  for two players; use deadlines, bounded queues and explicit overflow/error
  policy. Surface send failures to the game.
- Have one owner for connection lifecycle and a defined writer order. Cancel
  workers on scene/session exit. In browser `js.Func` callbacks, return promptly;
  do not wait synchronously for promises/events that need the JS event loop.
- A relay needs a roster/ready barrier before play. Enforce message size/rate,
  room capacity and origin policy, and isolate slow peers with bounded output
  queues. Define disconnect/empty-room cleanup.
- Validate moves on the authoritative server where the game requires trust.
  Relaying input does not prevent cheating. SDK bindings such as Steamworks do
  not imply that matchmaking/transport APIs needed by the game are exposed.

## Private views and session lifecycle

Construct each player's authorized view on the server **before serialization**.
Hiding cards, fog-of-war entities or private resources in the client's renderer
does not hide them from that client. Send a full authorized view on join/resync;
if using diffs, define the base/version and recovery after a missed update.
Replication relevance can reduce traffic, but is also an information boundary.

For matchmaking, a connected-player count is not enough: concurrent joins can
consume the same free slot. Serialize allocation and count pending reservations;
give reservations an expiry and bind one-use join credentials to the assigned
session/player. Recheck on connect, release failed/expired reservations and reject
stale assignments after cancellation/requeue. Apply a completed match result
idempotently so retries cannot award a second score/rating update.

These are transferable view/lifecycle lessons from
[multiplayer-game](https://github.com/rivet-dev/skills/blob/ba5d3db3d7489cfc6190fd0de45b96e3787e1ea3/multiplayer-game/SKILL.md)
and [Higgsfield's game flow](https://github.com/higgsfield-ai/skills/blob/f83af0bc1d937c8119099a11f8ebbf5e6fb99819/higgsfield-websites/references/game-flow.md).
They apply when those online features are promised; they do not require Rivet,
sharding or a backend for a local game. Turn-based servers can apply discrete
actions without a continuous realtime loop; Ebitengine can still animate the UI
at its normal update cadence.

## Verification before claiming online support

Test two real peers, then scripted latency, jitter, stalls, disconnects, duplicate,
invalid and out-of-window messages. Check UI responsiveness and bounded memory,
not just state equality. Exercise handshake, version mismatch, reconnect and
shutdown. For rollback, verify restored RNG/timers and that speculative sounds,
particles and rewards are reconciled rather than duplicated. For an authoritative
server, test input validation, prediction correction and snapshot loss/reordering.

Build browser clients, then run them over HTTP with the actual relay. A successful
WASM build is not a connection test. Record the tested platforms, protocol/library
versions and scenarios; leave untested deployment/scale claims explicit.
