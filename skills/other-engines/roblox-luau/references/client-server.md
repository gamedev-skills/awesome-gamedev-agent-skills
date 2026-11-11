# Roblox client/server model for Luau scripts

Read this when code behaves differently on server and client, an object is missing on the
client, or you need Bindables, Attributes, tags, or the right Studio test mode. Remote contract
design and validation are in the `roblox-networking` skill.

## The split

The server simulates the authoritative world; each client renders its own view and sends input.
Client-to-server replication is always filtered, so a client cannot change server-owned state
directly; it can only ask through a remote. The `player` argument the engine passes to
`OnServerEvent` is trustworthy; every argument after it is not.

Server-only containers (`ServerScriptService`, `ServerStorage`) never reach clients.
`ReplicatedStorage` and `Workspace` replicate to every client, so anything placed there is
readable by an exploiter, including module source.

## Replication timing and WaitForChild

When a client starts, the DataModel streams in over time, and with instance streaming parts of
`Workspace` may never arrive. On the client:

```lua
local remote = ReplicatedStorage:WaitForChild("Remotes"):WaitForChild("BuyItem")
local hud = player:WaitForChild("PlayerGui"):WaitForChild("HUD")
local optional = workspace:WaitForChild("Lobby", 5)  -- returns nil after 5 s instead of hanging
```

Without a timeout, `WaitForChild` warns about a possible infinite yield after a few seconds and
keeps waiting. On the server, Instances you created exist immediately, so direct indexing is fine.

## BindableEvent and BindableFunction

Use them for messages inside one machine (server script to server script, or client to client).
They do not cross the network and carry no security boundary. Many projects use a small signal
module instead; follow whichever the project already has.

## Connections and cleanup

```lua
local conn = part.Touched:Connect(onTouch)
conn:Disconnect()                       -- when the owner goes away

part.Touched:Once(onFirstTouch)         -- disconnects itself after one fire

Players.PlayerRemoving:Connect(function(player)
    cleanupFor(player)                  -- clear every table keyed by this player
end)
```

`Destroy()` disconnects connections on the destroyed Instance, but tables that still reference it
keep it in memory. Clear player-keyed and Instance-keyed tables yourself.

## Attributes and CollectionService tags

- **Attributes** store small typed values on an Instance and replicate to clients:
  `part:SetAttribute("Damage", 25)`, `part:GetAttribute("Damage")`,
  `part:GetAttributeChangedSignal("Damage"):Connect(...)`. Validate the type you read; a designer
  can type anything in the Properties panel.
- **Tags** group Instances for data-driven systems. Handle both existing and future members:

```lua
local CollectionService = game:GetService("CollectionService")
for _, door in CollectionService:GetTagged("Door") do setupDoor(door) end
CollectionService:GetInstanceAddedSignal("Door"):Connect(setupDoor)
CollectionService:GetInstanceRemovedSignal("Door"):Connect(teardownDoor)
```

With streaming, a tagged Instance can be removed and added again on a client as the player moves,
so `setupDoor` must be safe to run more than once.

## Studio test modes

- **Test / Test Here**: one player; toggle the Client/Server view while it runs.
- **Run**: simulation without a player.
- **Server & Clients**: a server plus up to eight client windows; the only interactive way to see
  replication and remotes between players. Check Output in each window.
- **Studio MCP server**: when connected, `start_stop_play` starts a solo session, `execute_luau`
  runs code in the `Edit`, `Server` or `Client` datamodel, and `get_console_output` returns Output.

## Primary references

- `https://create.roblox.com/docs/projects/client-server`
- `https://create.roblox.com/docs/scripting/events/bindable`
- `https://create.roblox.com/docs/studio/testing-modes`
- `https://create.roblox.com/docs/studio/mcp`
