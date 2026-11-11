---
name: roblox-characters
description: >
  Roblox player characters: CharacterAdded lifecycle, Humanoid and HumanoidRootPart, R6, R15 and
  custom rigs, respawn and Tools. Use when a character script breaks after respawn, animations do
  not play or replicate, or sprint code fights the Humanoid. Not for hit validation
  (`roblox-networking`), forces and raycasts (`roblox-physics`) or cameras (`camera-systems`).
---

# Roblox characters

A `Player` is the durable identity; each `Character` is a replaceable session with its own
references, connections, animation tracks, and cleanup. Most character bugs are one character's
state leaking into the next.

## Workflow

1. **Read the character contract.** Avatar Settings (rig type, movement system), `StarterCharacter`,
   `StarterCharacterScripts`, `Players.CharacterAutoLoads`, `Workspace.PlayerCharacterDestroyBehavior`,
   the existing Animate or controller scripts, tools, tags, and collision groups. Extend what is
   there; do not add a second controller.
2. **Separate scopes.** Player-scope state survives respawn; character-scope state does not. Put
   each character's connections, tracks, and temporary instances in one cleanup scope.
3. **Bind existing and future characters.** Connect `CharacterAdded`, then bind `player.Character`
   if it already exists. On the server, do this for players already in `Players:GetPlayers()`.
4. **Resolve parts defensively.** `WaitForChild` with a timeout for `Humanoid`, the root part, and
   `Animator`; after every yield, check the character is still the current one before acting.
5. **Choose one movement owner per state.** Standard avatars use Humanoid movement or the
   Character Controller Library. Physical mechanics (dash, knockback, grapple) use an impulse or a
   constraint for their duration and hand control back cleanly.
6. **Own animation lifecycle.** Load through the rig's `Animator`, keep tracks and marker
   connections in the character scope, and stop them on cleanup. Markers drive presentation; any
   gameplay effect they trigger is validated on the server.
7. **Run the lifecycle check.** With the Studio MCP server connected, start play, respawn the
   player several times from `execute_luau` on the `Server` datamodel
   (`for _ = 1, 5 do player:LoadCharacterAsync() task.wait(1) end`), then read
   `get_console_output`: expect no errors and exactly one setup log per spawn. Without MCP, ask the
   user to reset five times in Test and once with two players in Server & Clients, and to report
   duplicated logs, stuck animations, or errors.

## Pattern: replaceable character scope

```lua
local Players = game:GetService("Players")
local player = Players.LocalPlayer
local generation = 0
local connections: {RBXScriptConnection} = {}
local currentCharacter: Model? = nil

local function clearCharacter()
    generation += 1
    for _, connection in connections do connection:Disconnect() end
    table.clear(connections)
    currentCharacter = nil
end

local function bindCharacter(character: Model)
    -- Guard before teardown: a stale call must not clear a binding that is already current.
    if player.Character ~= character or currentCharacter == character then return end
    clearCharacter()
    currentCharacter = character
    local thisGeneration = generation
    local humanoid = character:WaitForChild("Humanoid", 10)
    local root = character:WaitForChild("HumanoidRootPart", 10)
    -- A respawn during WaitForChild bumps generation and makes this call stale.
    if not humanoid or not root or generation ~= thisGeneration then return end

    table.insert(connections, humanoid.Died:Connect(function()
        if generation ~= thisGeneration then return end
        setCharacterUiEnabled(false)
    end))
    attachCurrentCharacterSystems(character, humanoid, root)
end

player.CharacterRemoving:Connect(function(character)
    if currentCharacter == character then clearCharacter() end
end)
player.CharacterAdded:Connect(bindCharacter)
if player.Character then task.defer(bindCharacter, player.Character) end
```

Use the project's cleanup utility when one exists rather than introducing a framework for three
connections. Server systems repeat this binding per `Player` and clear player-scope tables on
`PlayerRemoving`.

## Pattern: animation through Animator and markers

```lua
local animation = Instance.new("Animation")
animation.AnimationId = "rbxassetid://1234567890"
local track = animator:LoadAnimation(animation)
local markerConnection = track:GetMarkerReachedSignal("Commit"):Connect(function(parameter)
    playLocalSwingEffect(parameter) -- presentation only; the server validates any hit
end)

track:Play(0.1)
-- On character teardown:
markerConnection:Disconnect()
track:Stop(0.1)
animation:Destroy()
```

Rigs without a `Humanoid` need an `AnimationController` with an `Animator`. `Humanoid:LoadAnimation()`
is deprecated; always load through the `Animator`.

## Movement and rig rules

- If R6 is supported, do not hardcode R15 limb names. Prefer attachments, tags, or a small rig
  adapter; branch on `Humanoid.RigType` only where topology really differs.
- `HumanoidRootPart` is the usual assembly root, not a guarantee for custom models. Write down the
  custom rig contract and validate it at spawn.
- Setting `AssemblyLinearVelocity` is an instant change; use `ApplyImpulse` for one-off pushes and
  a `LinearVelocity` constraint for sustained control (details in `roblox-physics`).
- For new actions such as sprint or rebinding jump, use the Input Action System (`InputContext`,
  `InputAction`, `InputBinding`) instead of raw `UserInputService` hooks. Give your context a higher
  `Priority` (and `Sink`) than the default player contexts so it wins.
- If the place uses the Character Controller Library (Avatar Settings → Movement → Abilities) or a
  `ControllerManager`, extend its abilities and controllers. Layering `HumanoidStateType` changes
  on top of it fights the library.
- Tools move between `Backpack` and the character on equip. Listen to ancestry and the tool's
  `Equipped`/`Unequipped` events instead of assuming one parent.
- Change appearance with `Humanoid:ApplyDescriptionAsync()` and keep the applied
  `HumanoidDescription` up to date.
- Under Server Authority (`Workspace.AuthorityMode = Server`), gameplay animation runs inside
  bound simulation functions and the client may replace tracks during rollback, so look tracks up
  each frame with `Animator:GetTrackByAnimationId()` instead of caching them. Tools are not fully
  supported there yet; see `roblox-networking`.

## Gotchas

| Symptom | Likely cause | Remedy |
|---|---|---|
| works once, breaks after reset | cached character, Humanoid or root | rebuild per `CharacterAdded`; clear on removal |
| callbacks fire twice after deaths | old character connections survived | character-scoped cleanup plus generation checks |
| memory grows with every respawn | old characters are only unparented, and tables still reference them | clear Instance-keyed tables; check `PlayerCharacterDestroyBehavior` |
| delayed setup edits the wrong rig | async work outlived its spawn | compare current character or generation after every yield |
| animation plays only locally or not at all | wrong Animator, side, or asset permission | inspect the rig's Animator, who loads it, and the asset owner |
| hit marker awards impossible hits | marker trusted as authority | marker for timing; server validates combat state |
| R6 or custom rig errors | R15 names assumed | rig contract and adapter; test every supported rig |
| tool disappears from a system | fixed Backpack or Character parent assumed | handle equip, unequip, and character replacement |
| custom force fights the Humanoid | two controllers own motion | one movement owner per state; restore on exit |

## Resources

- Read `references/lifecycle-and-animation.md` when a system spans respawns, supports several
  rigs, or owns animation and tool resources: server binding, death vs removal, custom-character
  checklist, and the lifecycle stress matrix.

## Related skills

- `roblox-physics`: forces, constraints, assemblies, and network ownership.
- `roblox-networking`: validating character actions and rejecting stale requests.
- `input-systems`: action mapping and responsive movement intent.
- `camera-systems`: cameras that follow a replaceable character.

## Version notes

Last verified: 2026-11-11.

- `Player:LoadCharacter()`, `Humanoid:ApplyDescription()` and `Humanoid:PlayEmote()` are deprecated
  in favour of `LoadCharacterAsync()`, `ApplyDescriptionAsync()` and `PlayEmoteAsync()`.
- The Character Controller Library was announced as released for live experiences in April 2026;
  its docs page still carried a beta note on the verification date. Avatar Settings needs a saved
  or published place.
- `Workspace.PlayerCharacterDestroyBehavior`, when enabled, destroys the old character on respawn
  and the `Player` object on leave.
- To re-check an API: append `.md` to its Creator Hub URL, or start from
  `https://create.roblox.com/docs/llms.txt`.

Sources: `https://create.roblox.com/docs/characters`,
`https://create.roblox.com/docs/animation/using`,
`https://create.roblox.com/docs/characters/character-controller-library`,
`https://create.roblox.com/docs/reference/engine/classes/Player`,
`https://create.roblox.com/docs/reference/engine/classes/Humanoid`,
`https://create.roblox.com/docs/reference/engine/classes/Workspace`,
`https://create.roblox.com/docs/projects/server-authority`,
`https://devforum.roblox.com/t/full-release-the-future-of-character-movement-character-controller-library/4565267`.
