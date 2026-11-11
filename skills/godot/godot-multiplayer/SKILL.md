---
name: godot-multiplayer
description: >
  Godot 4.7 high-level multiplayer: ENet host and join, @rpc with rpc_id(), MultiplayerSpawner and
  MultiplayerSynchronizer, with a two-instance headless test. Use for online or LAN co-op in
  Godot, or a rejected RPC, spawned nodes missing on clients, or state that does not sync. Not for
  Roblox (`roblox-networking`), server exports (`godot-export`) or local split-screen
  (`camera-systems`).
---

# Godot Multiplayer (4.x high-level)

Connect peers, call functions remotely with `@rpc`, assign authority, and replicate state
with `MultiplayerSpawner`/`MultiplayerSynchronizer`. Targets **Godot 4.7** with ENet (see
Version notes). Treat all client input as untrusted; keep the server authoritative.

## When to use

- Hosting/joining over ENet, writing RPCs, assigning per-node authority, or
  auto-spawning/syncing nodes across peers.

**When *not* to use:** local split-screen (no networking); raw TCP/UDP/WebSocket protocol
work (`PacketPeer`); HTTP requests; Roblox → `roblox-networking`; persistence →
`save-systems`.

## Core workflow

1. **Create a peer** (`ENetMultiplayerPeer`), call `create_server(port, max_clients)` or
   `create_client(address, port)`, check the returned `Error`, and assign it to
   `multiplayer.multiplayer_peer`. The server's id is always `1`; clients get random
   positive ids.
2. **Handle connection signals** on `multiplayer`: `peer_connected(id)`,
   `peer_disconnected(id)`, `connected_to_server`, `connection_failed`,
   `server_disconnected`. Print each one; the smoke test (step 8) reads those lines.
3. **Define RPCs** with `@rpc(...)` and call them on the method's `Callable` with `rpc()`
   (all peers) or `rpc_id(peer_id)` (one peer). Inside, `multiplayer.get_remote_sender_id()`
   says who sent it.
4. **Keep the RPC set identical** on every build that runs the script: Godot checksums all
   `@rpc` methods of a script, and a mismatch prints errors that can name an unrelated RPC.
5. **Assign authority** per node with `set_multiplayer_authority(id)`; gate input and
   movement on `is_multiplayer_authority()`.
6. **Replicate state** with `MultiplayerSpawner` (instances scenes on clients) and
   `MultiplayerSynchronizer` (syncs chosen properties). Both can be configured in code
   (Pattern 4), so no Replication-dock clicks are needed.
7. **Validate on the server.** Clients send intent; the server checks it and broadcasts
   results.
8. **Check with two headless instances before you finish.** Make the game host or join
   from command-line user args (Pattern 5), then:

   ```bash
   timeout 20 godot --headless --path . -- --host > server.log 2>&1 &
   sleep 2
   timeout 15 godot --headless --path . -- --join 127.0.0.1 > client.log 2>&1
   wait
   grep -nE "^ *(SCRIPT ERROR|ERROR):" server.log client.log   # no output = pass
   grep -n "connected" server.log client.log                   # your step-2 prints
   ```

   Pass means both logs show the handshake prints and no error lines (RPC "not allowed",
   checksum and "Node not found" errors all print as `ERROR:`). With no Godot binary
   (`godot`, `godot4` or `$GODOT_BIN`), ask the user to run these lines and paste both
   logs. Gameplay feel still needs a human: ask the user to start two or more windows
   (editor menu Debug > Customize Run Instances...) and report what desyncs.

## Patterns

### 1. Host or join (ENet)

```gdscript
const PORT := 7000
const MAX_PLAYERS := 8

func host() -> void:
    var peer := ENetMultiplayerPeer.new()
    var err := peer.create_server(PORT, MAX_PLAYERS)
    if err != OK:
        push_error("Cannot host: %s" % error_string(err)); return
    multiplayer.multiplayer_peer = peer
    multiplayer.peer_connected.connect(func(id: int): print("peer_connected ", id))

func join(address := "127.0.0.1") -> void:
    var peer := ENetMultiplayerPeer.new()
    var err := peer.create_client(address, PORT)
    if err != OK:
        push_error("Cannot join: %s" % error_string(err)); return
    multiplayer.multiplayer_peer = peer
    multiplayer.connected_to_server.connect(func(): print("connected_to_server"))

func leave() -> void:
    multiplayer.multiplayer_peer = OfflineMultiplayerPeer.new()
```

### 2. RPCs: client sends input to the server (any_peer, call_local)

This script sits on a player avatar whose authority is the owning client (Pattern 3), so
the server is *not* the node's authority. A server→clients RPC on such a node must be
`"any_peer"` and check that the sender is the server.

```gdscript
func _unhandled_input(event: InputEvent) -> void:
    if event.is_action_pressed("fire") and is_multiplayer_authority():
        request_fire.rpc_id(1)          # send only to the server (id 1)

# Clients may call this; it runs on the server (and locally if server is a player).
@rpc("any_peer", "call_local", "reliable")
func request_fire() -> void:
    if not multiplayer.is_server():     # ignore copies relayed to other clients
        return
    var sender := multiplayer.get_remote_sender_id()
    if not _can_fire(sender):           # server-side validation
        return
    spawn_projectile.rpc(sender)        # tell everyone to spawn it

# "authority" here would make clients reject the server's call (the client is the
# authority), so accept any peer and keep only calls that come from the server.
@rpc("any_peer", "call_local", "reliable")
func spawn_projectile(owner_id: int) -> void:
    if multiplayer.get_remote_sender_id() != 1:
        return
    _do_spawn(owner_id)
```

### 3. Per-node authority (each player controls their own avatar)

```gdscript
extends CharacterBody2D

func _ready() -> void:
    # The node name is the owning peer's id; that peer is the authority.
    set_multiplayer_authority(name.to_int())

func _physics_process(delta: float) -> void:
    if not is_multiplayer_authority():
        return                          # only the owner reads input & moves
    velocity = Input.get_vector("left", "right", "up", "down") * 200.0
    move_and_slide()
```

### 4. MultiplayerSynchronizer configured from code

```gdscript
@onready var sync: MultiplayerSynchronizer = $MultiplayerSynchronizer

func _ready() -> void:
    # Paths are relative to sync.root_path (default "..", the synchronizer's parent).
    var config := SceneReplicationConfig.new()
    config.add_property(^".:position")
    config.property_set_replication_mode(^".:position",
        SceneReplicationConfig.REPLICATION_MODE_ALWAYS)    # unreliable, every interval
    config.add_property(^".:health")
    config.property_set_replication_mode(^".:health",
        SceneReplicationConfig.REPLICATION_MODE_ON_CHANGE) # reliable, only when changed
    sync.replication_config = config
```

Per-peer visibility (`public_visibility`, `set_visibility_for`) is in the reference.

### 5. Host or join from the command line (for the smoke test)

```gdscript
func _ready() -> void:
    var args := OS.get_cmdline_user_args()   # only the arguments after `--`
    if "--host" in args:
        host()
    elif "--join" in args:
        var i := args.find("--join")
        join(args[i + 1] if i + 1 < args.size() else "127.0.0.1")
```

## Gotchas

- **RPC checksum.** Every `@rpc` method in a script must exist with the same annotation on
  client and server builds, *even unused ones*. Argument names and counts are not part of
  the check; the set of RPCs and their annotations are.
- **Default `@rpc` is `"authority"`.** Calls from other peers are dropped unless the mode
  is `"any_peer"`. Add `"call_local"` when the host is also a player.
- **`RPC 'x' is not allowed on node ... from: 1. Mode is "authority"`** → the server called
  an `"authority"` RPC on a node a client owns. "Authority" means the node's authority, not
  the server. Use `"any_peer"` plus a `get_remote_sender_id() == 1` check, or move
  server-driven RPCs to a server-owned node (e.g. a game manager).
- **NodePaths must match across peers.** RPC routing uses the node path; spawn with
  identical names everywhere (`MultiplayerSpawner`, or `add_child(node, true)` after
  setting `name`).
- **Trusting the client.** Never let clients set authoritative state (health, position,
  hits) directly. Send intent, validate on the server, then broadcast.
- **RPCs live on Nodes and carry plain data.** `@rpc` works only on `Node`-derived
  classes, not `Resource`/`RefCounted`, and Objects and Callables do not serialize. Send
  ints, strings, arrays, dictionaries and packed arrays.
- **Disconnect by resetting the peer**: `multiplayer.multiplayer_peer =
  OfflineMultiplayerPeer.new()`.
- **Port already in use** in the smoke test → a previous server is still running; the
  `timeout` wrapper ends it, or pick another port.
- **Android exports need the INTERNET permission** in the export preset, or all
  networking is blocked.

## References

- Read `references/replication-and-rpc.md` when you need the full `@rpc` argument rules,
  `MultiplayerSpawner` with a custom `spawn_function`, synchronizer visibility filters,
  `SceneMultiplayer` authentication, transfer-mode choices, or a lobby skeleton.

## Related skills

- `godot-nodes-scenes` for instancing the scenes that get spawned and synced.
- `godot-signals-groups` for connection signals and event flow.
- `godot-export` for a headless dedicated-server build.
- `godot-gdscript-headless-testing` to keep server-logic tests in CI.

## Version notes

Last verified: 2026-11-11 against Godot 4.7.2-stable (released 2026-08-18).

- `SceneReplicationConfig.property_set_sync`/`property_set_watch` are deprecated; use
  `property_set_replication_mode()`.
- `MultiplayerSynchronizer.public_visibility` defaults to `true`; `MultiplayerSpawner.spawn()`
  errors without a `spawn_function`.

Sources: [SceneReplicationConfig @ 4.7.2-stable](https://github.com/godotengine/godot/blob/4.7.2-stable/modules/multiplayer/doc_classes/SceneReplicationConfig.xml),
[ENetMultiplayerPeer @ 4.7.2-stable](https://github.com/godotengine/godot/blob/4.7.2-stable/modules/enet/doc_classes/ENetMultiplayerPeer.xml),
[OS.get_cmdline_user_args @ 4.7.2-stable](https://github.com/godotengine/godot/blob/4.7.2-stable/doc/classes/OS.xml),
[High-level multiplayer](https://docs.godotengine.org/en/stable/tutorials/networking/high_level_multiplayer.html).
