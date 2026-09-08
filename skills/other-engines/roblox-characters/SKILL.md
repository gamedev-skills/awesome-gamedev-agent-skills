---
name: roblox-characters
description: >
  Build respawn-safe Roblox character systems around Players, CharacterAdded/CharacterRemoving,
  Humanoid, HumanoidRootPart, Animator, R6/R15 rigs, movement, animations and markers, death,
  tools, accessories, ownership, and custom characters. Use when character scripts break after
  respawn, cache stale Humanoids, control movement or velocity, load AnimationTracks, handle death,
  equip Tools, modify avatars, or support custom player rigs.
---

# Roblox characters

Treat a `Player` as the durable identity and each `Character` as a replaceable session with its own
references, connections, animation tracks, and cleanup. Targets Roblox's rolling platform APIs.

## When to use

- Use for player-character lifecycle, Humanoid state/movement, rigs, animations, tools,
  accessories, custom characters, death, or respawn defects.
- Use whenever code stores a Character/Humanoid/root reference longer than one spawn.

**When not to use:** general physics queries and constraints belong to `roblox-physics`; remote
trust belongs to `roblox-networking`; camera logic belongs to `camera-systems`.

## Workflow

1. **Inspect the character contract.** Check avatar settings, `StarterCharacter`,
   `StarterCharacterScripts`, `CharacterAutoLoads`, R6/R15 support, existing Animate/controller
   scripts, tools, tags, collision groups, and server/client ownership.
2. **Separate scopes.** Player-scope state survives respawn; character-scope state does not. Put
   character connections/tracks/resources in one cleanup scope and destroy it on removal.
3. **Bind existing and future characters.** Connect `CharacterAdded`, then bind `player.Character`
   if present. Do not assume event subscription alone sees a character that already spawned.
4. **Resolve required components defensively.** Wait with a timeout where replication warrants it;
   validate `Humanoid`, root, `Animator`, and rig assumptions. Abort if that character is no longer
   current before applying delayed work.
5. **Choose movement ownership.** Use Humanoid movement for standard avatars; use
   `AssemblyLinearVelocity`, `BasePart:ApplyImpulse()`, or a `LinearVelocity`/`AlignPosition`
   constraint only for mechanics that need physical control. Keep gameplay
   authority and network ownership implications explicit.
6. **Own animation lifecycle.** Load via the rig's `Animator`; store tracks/connections; use named
   markers for gameplay timing only with server validation; stop/disconnect on character cleanup.
7. **Verify lifecycle stress.** Spawn, die, reset, rapid-respawn, swap rig if supported, equip/drop
   tools, leave during setup, and run with at least two players when character interactions matter.

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
    -- Guard BEFORE teardown. A stale invocation (see the CharacterAdded/defer race below) must not
    -- clear a binding that is already current, or nothing ends up bound at all.
    if player.Character ~= character then return end
    clearCharacter()
    currentCharacter = character
    local thisGeneration = generation
    local humanoid = character:WaitForChild("Humanoid", 10)
    local root = character:WaitForChild("HumanoidRootPart", 10)
    -- Re-check after the yields: a respawn during WaitForChild bumps generation and makes this call stale.
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

Use the project's cleanup utility when one exists; do not introduce a new framework for three
connections. Server systems repeat this binding per `Player` and clear player-scope tables on
`PlayerRemoving`.

## Pattern: animation through Animator and markers

```lua
local animation = Instance.new("Animation")
animation.AnimationId = "rbxassetid://1234567890"
local track = animator:LoadAnimation(animation)
local markerConnection = track:GetMarkerReachedSignal("Commit"):Connect(function(parameter)
    playLocalSwingEffect(parameter) -- presentation; server still validates any hit
end)

track:Play(0.1)
-- On character teardown:
markerConnection:Disconnect()
track:Stop(0.1)
animation:Destroy()
```

For rigs without a `Humanoid`, use an `AnimationController` with an `Animator`. Do not use the
deprecated convenience path as a substitute for owning the actual Animator and track lifecycle.

## Movement and rig rules

- Do not hardcode R15 limb names if R6 is supported. Prefer attachments, tags, or a rig-type
  adapter; branch on `Humanoid.RigType` only where topology materially differs.
- `HumanoidRootPart` is the usual character assembly root, not a universal guarantee for every
  custom model. Define the custom rig contract and validate it at spawn.
- Prefer `Humanoid:Move()`/standard controls for ordinary avatar locomotion. Directly changing
  `AssemblyLinearVelocity` is an instantaneous physical action; use forces/constraints or impulses
  when continuous or instantaneous physics is the real intent.
- Never grant damage or movement authority because a client owns its character physics. Validate
  cross-player consequences on the server.
- Tools move between Backpack and Character during equip; listen to lifecycle/state rather than
  assuming one fixed parent. Modify accessories/appearance through current character APIs and
  preserve an up-to-date applied `HumanoidDescription` when editing avatar appearance.

## Common failures

| Symptom | Likely cause | Remedy |
|---|---|---|
| works once, breaks after reset | cached character/Humanoid/root | rebuild per `CharacterAdded`; clear on removal |
| callbacks fire twice after deaths | old character connections survived | character-scoped cleanup and generation/current checks |
| delayed load edits wrong rig | async work outlived spawn | compare current Character/generation after every yield |
| animation visible only locally or not at all | wrong Animator/context/asset ownership | inspect rig Animator, execution side, permissions, and replication |
| hit marker awards impossible hit | animation marker trusted as authority | use marker for timing/presentation; server validates combat state |
| R6/custom rig errors | R15 names assumed | define rig contract; attachments/adapter; test each supported rig |
| tool disappears from system | fixed Backpack/Character parent assumed | handle equip/unequip ancestry and character replacement |
| custom force fights Humanoid | two controllers own motion | choose one movement authority per state and restore cleanly |

## Resources

- Read `references/lifecycle-and-animation.md` for server binding, death vs removal, rig and
  animation verification, custom characters, and the lifecycle stress matrix.

## Related skills

- `roblox-physics` — forces, constraints, assemblies, collision, and network ownership.
- `roblox-networking` — server validation of character actions and stale requests.
- `input-systems` — action mapping and responsive movement intent.
- `camera-systems` — camera behavior following replaceable characters.

## Primary references

- `https://create.roblox.com/docs/characters`
- `https://create.roblox.com/docs/animation/using`
- `https://create.roblox.com/docs/characters/appearance`
