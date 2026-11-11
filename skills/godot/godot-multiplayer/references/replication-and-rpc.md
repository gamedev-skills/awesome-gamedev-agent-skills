# Replication & RPC reference (Godot 4.7)

Depth companion to `godot-multiplayer`.

Contents: the @rpc annotation in full · MultiplayerSpawner · MultiplayerSynchronizer
(replication modes, visibility) · SceneMultiplayer authentication · transfer mode
guidance · dedicated server export · minimal lobby flow

## The @rpc annotation in full

```gdscript
@rpc(mode, sync, transfer_mode, transfer_channel)
```

Defaults — `@rpc` is equivalent to `@rpc("authority", "call_remote", "reliable", 0)`:

- **mode**: `"authority"` (only the node's multiplayer authority may call remotely) or
  `"any_peer"` (any client may call — needed for player input).
- **sync**: `"call_remote"` (does not run on the local/sending peer) or `"call_local"`
  (also runs locally — use when the host is a player).
- **transfer_mode**: `"reliable"` (acknowledged, ordered, slower), `"unreliable"`
  (fire-and-forget, may drop/reorder — good for frequent position updates), or
  `"unreliable_ordered"` (drops late packets to preserve order).
- **transfer_channel**: integer channel index; the first three args can be in any order,
  but the channel must be the 4th argument, so all three must be given before it. Use
  separate channels to keep unrelated streams from
  blocking each other.

Call forms (on a `Callable` for the method):

```gdscript
my_method.rpc(args...)            # call on all peers (per mode/sync rules)
my_method.rpc_id(peer_id, args)   # call on one peer (1 = server)
multiplayer.get_remote_sender_id()  # inside the method: who invoked it
```

## MultiplayerSpawner

Auto-instantiates scenes on remote peers when the authority spawns them.

1. Add a `MultiplayerSpawner` node; set its **Spawn Path** to the parent that will hold
   spawned instances.
2. Add the scenes it may spawn to its **Auto Spawn List** (`add_spawnable_scene()` in code).
3. On the authority, `add_child()` one of those scenes under the spawn path — the spawner
   replicates it to clients with a matching name. For custom setup, assign a
   `spawn_function` (it receives your `data` and returns the node) and call
   `spawner.spawn(data)`; `spawn()` errors without a `spawn_function`.

```gdscript
@onready var spawner: MultiplayerSpawner = $MultiplayerSpawner

func server_spawn_player(id: int) -> void:
    var p := preload("res://player.tscn").instantiate()
    p.name = str(id)                 # deterministic name = authority id
    $Players.add_child(p, true)      # true = readable, replicated name
```

## MultiplayerSynchronizer

Replicates chosen properties from the authority to other peers each network tick.

- Add it as a child of the node to sync. Add property paths (e.g. `.:position`,
  `.:velocity`, `Sprite2D:modulate`, relative to `root_path`) in the editor's
  **Replication** panel, or in code with `SceneReplicationConfig.add_property()` and
  assign the config to `replication_config`.
- Per property: **Spawn** (sent once when the node is spawned) and a **Replicate** mode:
  *Always* (unreliable, every `replication_interval`), *On Change* (reliable, checked every
  `delta_interval` and sent only when the value changed) or *Never*. In code use
  `SceneReplicationConfig.property_set_replication_mode()`; `property_set_sync` and
  `property_set_watch` are deprecated.
- `replication_interval` / `delta_interval` (on the synchronizer) tune bandwidth.
- Visibility filtering for per-peer data. A peer receives the node only if every filter
  returns `true` **and** it is visible to that peer — `public_visibility` (default `true`) or
  `set_visibility_for(peer, true)`. So `set_visibility_for` alone does nothing until
  `public_visibility` is off:
  ```gdscript
  sync.public_visibility = false                 # otherwise every peer still receives it
  sync.set_visibility_for(peer_id, true)
  sync.add_visibility_filter(func(peer): return _can_see(peer))
  sync.update_visibility()
  ```

Only the authority's values are sent; remote peers receive read-only updates. Combine with
per-node authority so each player's synchronizer pushes that player's state.

## SceneMultiplayer authentication

Protect RPCs from unauthenticated peers using the built-in handshake:

```gdscript
# Both sides set auth_callback BEFORE assigning multiplayer_peer.
@onready var sm := multiplayer as SceneMultiplayer   # auth API lives on SceneMultiplayer

func setup_server_auth() -> void:
    sm.auth_timeout = 3.0
    sm.auth_callback = func(peer_id: int, data: PackedByteArray) -> void:
        var info: Variant = JSON.parse_string(data.get_string_from_utf8())
        if info is Dictionary and _valid(info):
            sm.complete_auth(peer_id)

func setup_client_auth() -> void:
    # The client needs an auth_callback too, or it skips the handshake entirely.
    sm.auth_callback = func(_peer_id: int, _data: PackedByteArray) -> void:
        pass                                 # read the server's reply here, if any
    sm.peer_authenticating.connect(func(peer_id: int) -> void:
        var payload := JSON.stringify({"token": _token}).to_utf8_buffer()
        sm.send_auth(peer_id, payload)
        sm.complete_auth(peer_id)            # the client must complete its side too
    )
```

`connected_to_server` / `peer_connected` only fire once both sides call `complete_auth()`.
If the client never calls it, the handshake times out and `peer_authentication_failed`
fires; if the client has no `auth_callback`, the server waits for data that never comes.

## Transfer mode guidance

- **Player input / commands** → reliable (must not be lost).
- **Position/rotation updates** → unreliable or unreliable_ordered via a
  `MultiplayerSynchronizer` (frequent, latest-wins).
- **Chat / state changes** → reliable, possibly on a dedicated channel.

## Dedicated server export

Export a **headless** build (no GPU) for servers; see `godot-export`. Modify the lobby so
the server is not counted as a player and the first joining client can start the match. Run
with the server feature tag and `--headless`.

## Minimal lobby flow

1. Host: `create_server`; add self to `players` keyed by id 1.
2. On `peer_connected(id)`: send your player info to that id via `rpc_id`.
3. Each peer registers others (`@rpc("any_peer")` register function using
   `get_remote_sender_id()`).
4. On `peer_disconnected(id)`: erase from `players`, emit a UI signal.
5. Server starts the game by RPC'ing a `load_game(path)` (`@rpc("call_local","reliable")`)
   so all peers `change_scene_to_file` together.
