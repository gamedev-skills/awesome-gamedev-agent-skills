---
name: roblox-studio-workflow
description: >
  Safely edits an existing Roblox place or Rojo project: finds the source of truth and proves
  changes with the right test mode or Studio MCP (execute_luau). Use when an agent edits a .rbxl
  or Rojo project, works through Studio MCP tools, or must report what was tested. Not for
  installing Studio MCP (`roblox-get-started`) or the feature code (`roblox-luau`, `roblox-ui`).
---

# Roblox Studio workflow

Work as a collaborator inside an existing place, not as if it were a blank text repository. This
skill owns how changes are made and proven; the domain skills own what the code does.

## Workflow

1. **Establish the source of truth.** Decide whether Studio, Rojo files, Script Sync, a package,
   or a generated build owns each subtree (`*.project.json` mappings, `PackageLink` objects). Edit
   only the owner; a Studio edit to a Rojo-mapped script is overwritten by the next sync.
2. **Inventory before proposing structure.** Search scripts, modules, remotes, tags and
   Attributes for the feature's current owner (`rg` over the Rojo tree, or `script_grep` and
   `search_game_tree` over Studio MCP). Run once and record existing warnings, so new ones are
   yours.
3. **Plan the smallest compatible edit.** Name the Instances and execution locations you will
   change. Reuse existing remotes, components, cleanup utilities, tags, folders, and config
   patterns. State any ownership question you could not resolve.
4. **Create real, meaningful objects.** Authored UI, folders, attachments, constraints, remotes and
   configuration stay inspectable in Explorer. Scripts add behavior and genuinely dynamic
   repetition; they do not hide the whole feature in runtime construction.
5. **Respect execution and replication.** Authoritative logic in server containers, persistent
   client logic in `StarterPlayerScripts`, per-character logic in `StarterCharacterScripts`, UI
   templates in `StarterGui`, shared modules and remotes in `ReplicatedStorage`, secrets and
   server assets in server-only containers. Check each `Script`'s `RunContext`.
6. **Test the actual risk** with the smallest rung of the verification ladder that covers it.
7. **Clean the experiment.** Remove temporary parts, test remotes, Command Bar fixtures, debug UI,
   prints, disabled duplicate scripts, placeholder assets, and diagnostic tags or Attributes. Stop
   the session and confirm the edit-mode hierarchy is clean (`search_game_tree` or Explorer).
8. **Report evidence precisely.** Changed Instances and files; modes and client counts; cases run;
   observed Output; failures and fixes; and what was not run. Label each claim executed,
   statically checked, prepared but not run, or unverified. "Looks right" and static inspection are
   never "tested in Studio".

## When Studio MCP is connected

If tools such as `list_roblox_studios` and `execute_luau` are available, drive the same ladder
through them instead of asking the user to click: pick the place with `list_roblox_studios`,
inventory, edit with `multi_edit`, run with `start_stop_play` and `execute_luau`, and collect
evidence with `get_console_output` and `screen_capture` from both server and client. For live
debugging, unit tests, device capture and profiling, call Studio's built-in skills (`rbx-debug`,
`rbx-unit-test`, `rbx-device-simulator-lua`, `rbx-perf-profiling`) through the `skill` tool.
Read `references/studio-mcp.md` for the tool map, limits, and safety rules.

When the tools are absent, the manual Studio and Rojo path is the full default; nothing here
requires MCP. If the user wants it connected, Roblox's official `roblox-get-started` skill handles
installation and connection.

## Execution-location map

| Location | Typical role | Key constraint |
|---|---|---|
| `ServerScriptService` | authoritative Scripts and modules | not replicated to clients |
| `ServerStorage` | server-only assets and data | clients cannot access it |
| `ReplicatedStorage` | shared modules, assets, remotes | visible to clients; no secrets |
| `StarterPlayerScripts` | client systems across respawns | cloned into `PlayerScripts` |
| `StarterCharacterScripts` | per-character client behavior | recreated each character |
| `StarterGui` | authored UI templates | cloned into `PlayerGui`; lifecycle follows `ResetOnSpawn` |
| `Workspace` | replicated world and live characters | streaming and ownership change what clients see |

## Reuse before adding

Before creating a RemoteEvent, search by purpose and read both endpoints. Before adding a
"manager" module, find the current feature owner. Before adding folders or tags, read the existing
naming and lookup patterns. Duplicate systems that both run double-bind input, save twice, create
two UI clones, or apply gameplay twice.

Attributes hold small typed designer-editable values on an Instance; `CollectionService` tags find
sets of Instances across the hierarchy; folders express ownership and navigation. Validate
Attributes at the system boundary:

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

The owning system also tears behavior down when a tagged Instance is removed.

## Verification ladder

1. **Static:** project JSON and models build (`rojo build default.project.json -o check.rbxlx`),
   links resolve, selene and luau-lsp pass where the project uses them.
2. **Single session:** right execution context and hierarchy, no new Output errors or warnings,
   happy path and cleanup.
3. **Lifecycle:** respawn, reset, rejoin, streaming, or character replacement as relevant.
4. **Server & Clients:** at least two clients for remotes, replication, ownership, player
   interaction, joins and leaves, and targeted state.
5. **Device and input:** representative device profiles, orientation, touch, controller.
6. **Stress and failure:** malformed input, spam, empty and full content, rapid transitions,
   simultaneous actions, disconnects.

Use the smallest rungs that cover the change, and never report a lower rung as a higher one.
Rungs 4-5 usually need the user: ask them to run the named mode and paste the server and client
Output, or script it with `StudioTestService` from a plugin.

## Gotchas

| Symptom | Likely cause | Remedy |
|---|---|---|
| Studio edit disappears after sync | generated or Rojo-mapped subtree edited | change the source files and resync |
| feature runs twice | duplicate Script, remote or controller | inspect first; consolidate under the existing owner |
| client cannot reach a module or object | wrong storage location | move shared content deliberately; keep secrets server-only |
| authored screen unreadable in Explorer | everything created by one LocalScript | named Instance shell plus small behavior modules |
| test passes only in solo Test | replication or lifecycle untested | Server & Clients and the relevant simulators |
| "clean" Output hides client errors | only server Output read | read each client and the server |
| shipped place has DebugFolder or prints | cleanup skipped | keep a cleanup list; inspect the hierarchy after the session |
| `list_roblox_studios` is empty | Studio closed, no place open, or MCP setting off | ask the user to open a place and enable the server |
| MCP edit landed in the wrong place | several Studio windows open | pass the `studio_id` from `list_roblox_studios` |
| Attribute or tag behavior silently fails | schema or class not validated | validate at setup; warn with the full Instance path |

## Resources

- Read `references/studio-verification.md` before reporting Studio validation, or when choosing
  test modes, building a temporary harness, or documenting an automation gap.
- Read `references/studio-mcp.md` when Studio MCP tools are available or you plan to use them.

## Related skills

- `roblox-luau`: services, Instances, events, and the execution model.
- `roblox-ui`, `roblox-networking`, `roblox-characters`, `roblox-physics`, `roblox-datastores`:
  feature work that uses this inspection and verification discipline.

## Version notes

Last verified: 2026-11-11.

- Studio MCP tool names and the built-in `rbx-` skills change with Studio releases; the dated list
  is in `references/studio-mcp.md`.
- Server & Clients and `StudioTestService:ExecuteMultiplayerTestAsync()` both allow up to eight
  clients.
- The toolbar Device Simulator and the Network Simulator were a Studio beta (File → Beta Features
  → New Device Simulator).
- Rojo 7.7.1 is the current release.
- Roblox docs for agents: append `.md` to any Creator Hub URL; the index is
  `https://create.roblox.com/docs/llms.txt`.

Sources: `https://create.roblox.com/docs/studio/testing-modes`,
`https://create.roblox.com/docs/studio/mcp`,
`https://create.roblox.com/docs/assistant/skills`,
`https://create.roblox.com/docs/reference/engine/classes/StudioTestService`,
`https://github.com/Roblox/roblox-studio-agent-plugin`.
