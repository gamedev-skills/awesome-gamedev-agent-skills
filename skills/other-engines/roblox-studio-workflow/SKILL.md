---
name: roblox-studio-workflow
description: >
  Modify living Roblox Studio projects safely: inspect Explorer and execution locations, preserve
  existing structure, reuse modules/remotes, create meaningful Instances, apply Attributes and
  CollectionService tags, test server/client and multiple devices, inspect Output, and remove
  experiments/debug objects. Use when an agent edits a place or rbxl/rbxlx/Rojo project, operates
  in Studio, adds Scripts/LocalScripts/ModuleScripts, or must verify a Roblox change in context.
---

# Roblox Studio workflow

Work as a collaborator inside an existing place, not as if it were a blank text repository. Targets
current Roblox Studio and rolling platform APIs.

## When to use

- Use before invasive edits to a Roblox place, Studio DataModel, or Rojo-backed project.
- Use to plan execution location, find/reuse systems, create editable Instances, and gather honest
  Studio verification evidence.

**When not to use:** this skill owns project operation, not the domain implementation. Compose it
with `roblox-ui`, `roblox-networking`, `roblox-characters`, `roblox-physics`, `roblox-luau`, or
`roblox-datastores` as appropriate.

## Workflow

1. **Establish source of truth.** Determine whether Studio, Rojo files, a package manager, or a
   generated build owns each subtree. Do not hand-edit generated output or create Studio-only
   changes that the next sync overwrites.
2. **Inventory before proposing structure.** Inspect Explorer, search scripts/modules/remotes/tags,
   read project mapping and naming conventions, and run once to observe existing warnings. Locate
   the feature's current owner and dependencies.
3. **Plan the smallest compatible edit.** Name the Instances and execution locations you will
   change. Reuse existing remotes, component modules, cleanup utilities, tags, Attributes, folders,
   and configuration patterns. State any unresolved ownership boundary.
4. **Create real, meaningful objects.** Normal authored UI, folders, attachments, constraints,
   remotes, and configuration remain inspectable in Explorer. Use scripts for behavior and truly
   dynamic repetition—not to hide the entire feature in runtime construction.
5. **Respect execution and replication.** Put authoritative logic in server containers, persistent
   client logic in `StarterPlayerScripts`, per-character client logic in
   `StarterCharacterScripts`, UI templates in `StarterGui`, shared assets/modules/remotes in
   `ReplicatedStorage`, and secrets/server assets in server-only containers.
6. **Test the actual risk.** Choose Play, Play Here, Run, Server & Clients, Device Emulator,
   Controller Emulator, or scripted Studio testing based on the behavior. Inspect server and client
   Output, not only the viewport.
7. **Clean the experiment.** Remove temporary parts, test remotes, command-bar scripts, debug UI,
   prints, disabled duplicate scripts, placeholder assets, and tags/Attributes created only for
   diagnosis. Stop the session and confirm edit-mode hierarchy is clean.
8. **Report evidence precisely.** List changed Instances/files, modes and client counts, cases
   executed, observed Output, failures and fixes, and anything not run. Never translate “looks
   plausible” or static inspection into “tested in Studio.”

## Execution-location map

| Location | Typical role | Key constraint |
|---|---|---|
| `ServerScriptService` | authoritative server Scripts/modules | not replicated to clients |
| `ServerStorage` | server-only assets/data | clients cannot access it |
| `ReplicatedStorage` | shared modules/assets/remotes | visible to clients; do not store secrets |
| `StarterPlayerScripts` | client systems across respawns | clone into `PlayerScripts` |
| `StarterCharacterScripts` | per-character client behavior | recreated each character |
| `StarterGui` | authored UI templates | clones into `PlayerGui`; lifecycle depends on GUI policy |
| `Workspace` | replicated world and live characters | streaming/ownership may affect client view |

Verify actual Script `RunContext` and project conventions; class/location shorthand does not excuse
inspection of an existing custom setup.

## Reuse before adding

Before creating a RemoteEvent, search by purpose and inspect both endpoints. Before adding a
“manager” or service module, identify the current feature owner. Before introducing folders/tags,
inspect naming and retrieval patterns. Duplicate systems are especially dangerous when both run:
they double-bind input, save twice, create two UI clones, or apply gameplay twice.

Use Attributes for small typed designer-editable metadata that belongs on an Instance. Use
`CollectionService` tags for discovering sets of Instances across hierarchy. Use folders for
ownership/navigation, not as a substitute for semantic tags. Preserve established schemas and
validate missing/malformed Attributes at system boundaries.

```lua
local CollectionService = game:GetService("CollectionService")

local function setupDoor(instance: Instance)
    if not instance:IsA("Model") then return end
    local accessLevel = instance:GetAttribute("AccessLevel")
    if type(accessLevel) ~= "number" then
        warn(`Door {instance:GetFullName()} needs numeric AccessLevel`)
        return
    end
    attachDoorBehavior(instance, accessLevel)
end

for _, door in CollectionService:GetTagged("Door") do setupDoor(door) end
CollectionService:GetInstanceAddedSignal("Door"):Connect(setupDoor)
```

The owning system must also clean behavior when a tagged Instance is removed/destroyed.

## Verification ladder

1. **Static:** project mapping/JSON/XML parses; links resolve; Luau diagnostics/lint if available.
2. **Single session:** correct execution context, hierarchy, no new Output errors/warnings, basic
   happy path and cleanup.
3. **Lifecycle:** respawn, reset, reopen/rejoin, streaming or character replacement as relevant.
4. **Server & Clients:** at least two clients for remotes, replication, ownership, player
   interaction, joins/leaves, and targeted state.
5. **Device/input:** representative device profiles, orientation, touch, controller navigation.
6. **Stress/failure:** malformed input, spam, empty/full content, rapid transitions, simultaneous
   actions, disconnects, and cleanup.

Use the smallest rungs that cover the change, but never substitute a lower rung for a claimed
higher-rung result.

## Common failures

| Symptom | Likely cause | Remedy |
|---|---|---|
| Studio edit disappears after sync | generated/mapped subtree edited | change source-of-truth files and resync |
| feature runs twice | duplicate Script/remote/controller | inspect first; consolidate under existing owner |
| client cannot access module/object | wrong execution/storage location | move shared content deliberately; keep secrets server-only |
| authored screen unreadable in Explorer | everything created by one LocalScript | create named Instance shell and small behavior modules |
| test passes only in Play | replication/lifecycle untested | use Server & Clients and relevant emulators |
| “clean” Output hides client errors | only server Output inspected | inspect each client and server context |
| shipped place has DebugFolder/prints | experiment cleanup skipped | maintain cleanup list and inspect hierarchy after session |
| Attribute/tag behavior silently fails | schema/class not validated | validate at setup boundary; warn with full Instance path |

## Resources

- Read `references/studio-verification.md` before reporting Studio validation or when choosing test
  modes, constructing a temporary harness, or documenting an automation gap.

## Related skills

- `roblox-luau` — services, Instances, events, and basic execution model.
- `roblox-ui`, `roblox-networking`, `roblox-characters`, `roblox-physics` — focused production
  workflows that use this inspection and verification discipline.

## Primary references

- `https://create.roblox.com/docs/studio/testing-modes`
- `https://create.roblox.com/docs/projects/data-model`
- `https://create.roblox.com/docs/scripting/services`
