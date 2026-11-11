---
name: roblox-physics
description: >
  Roblox physics and spatial queries: assemblies, constraints, collision groups, Raycast and
  Shapecast, and network ownership. Use when parts fall through or jitter, Touched is unreliable,
  a ray hits the shooter, or BodyMovers need replacing. Not for hit legitimacy
  (`roblox-networking`), Humanoid movement (`roblox-characters`) or engine-neutral tuning
  (`physics-tuning`).
---

# Roblox physics

Simulation, character control, hit detection and visual-only motion are different jobs. Pick the
mechanism first, then the API. Whether a hit counts is a server validation decision owned by
`roblox-networking`; this skill supplies the queries it uses.

## Decide the mechanism

| Goal | Mechanism |
|---|---|
| sustained physical interaction | unanchored assembly plus modern constraints or forces |
| one-off physical change | `ApplyImpulse` / `ApplyAngularImpulse` |
| kinematic platform or path | scripted pivot or CFrame with an explicit passenger policy |
| character locomotion | Humanoid or Character Controller Library (`roblox-characters`) |
| hit test | server raycast, shapecast, or overlap with explicit filters |
| cosmetic trail or recoil | local visual motion; no gameplay authority |

## Workflow

1. **Inspect the mechanism.** In Studio, turn on the assembly, constraint and network-owner
   visualizations; or read `part.AssemblyRootPart`, `part.AssemblyMass`, `part.Anchored` and
   `part:GetNetworkOwner()` from code. Identify the assembly root and who should own it.
2. **Write the interaction policy.** A collision-group matrix, then `CanCollide`, `CanTouch` and
   `CanQuery` decided separately per role. Register groups once with
   `Workspace:RegisterCollisionGroup()` and `CollisionGroupSetCollidable()` (or the Collision
   Groups editor), from a single script so assignment never races registration.
3. **Choose simulation or query.** A ray for a line, a shapecast for a moving volume, an overlap for
   a static volume, and simulation contacts only when a physical response is wanted. `.Touched` is
   neither reliable nor secure as a hit detector.
4. **Apply motion at assembly level.** Forces on any part act on the whole assembly. Use
   `LinearVelocity`, `AngularVelocity`, `VectorForce`, `AlignPosition` and `AlignOrientation`;
   migrate BodyMovers when you touch that system.
5. **Set ownership deliberately.** Server-own gameplay-critical loose assemblies when needed;
   client ownership improves response but never authorizes results.
6. **Bound cost and lifetime.** Reuse query params, cap query frequency and result counts, and
   destroy temporary constraints, attachments and connections together.
7. **Check from code.** With the Studio MCP server connected, start play and use `execute_luau` on
   the `Server` datamodel to print the facts the change depends on: `AssemblyRootPart`,
   `AssemblyMass`, `GetNetworkOwner()`, `workspace:CollisionGroupsAreCollidable(a, b)`, and the
   result of one test query; then read `get_console_output`. Without MCP, ask the user to run the
   same snippet from the Command Bar during play and paste the Output. Fast movers, ownership
   hand-off and two-client interaction need a Server & Clients run.

## Pattern: filtered server raycast

```lua
local Workspace = game:GetService("Workspace")

local params = RaycastParams.new()
params.FilterType = Enum.RaycastFilterType.Exclude
params.FilterDescendantsInstances = {shooterCharacter}
params.IgnoreWater = true
params.CollisionGroup = "WeaponQuery"

local direction = aimDirection.Unit * MAX_RANGE   -- direction length is the range
local result = Workspace:Raycast(muzzlePosition, direction, params)
if result then
    local model = result.Instance:FindFirstAncestorOfClass("Model")
    local humanoid = model and model:FindFirstChildOfClass("Humanoid")
    if humanoid and serverCanDamage(shooter, model, result.Position) then
        humanoid:TakeDamage(serverWeaponDamage(shooter))
    end
end
```

`muzzlePosition` and `aimDirection` must come from server-known character and weapon state. A
raycast from a client-supplied origin is not validation (see `roblox-networking`).

## Pattern: overlap volume with explicit policy

```lua
local params = OverlapParams.new()
params.FilterType = Enum.RaycastFilterType.Exclude
params.FilterDescendantsInstances = {sourceCharacter}
params.CollisionGroup = "DamageQuery"
params.MaxParts = 64

local seen: {[Model]: boolean} = {}
for _, part in Workspace:GetPartBoundsInBox(hitboxCFrame, hitboxSize, params) do
    local model = part:FindFirstAncestorOfClass("Model")
    if model and not seen[model] then
        seen[model] = true
        validateAndApplyHit(model)
    end
end
```

Bounds queries test bounding boxes and return several parts per target, so deduplicate by model.
`WorldRoot:GetPartsInPart()` is exact but costs more. `OverlapParams.RespectCanCollide` switches
the query from `CanQuery` to `CanCollide`; set it on purpose or it silently overrides the flag
policy.

## Assemblies, force, and ownership

- Welded parts form one rigid assembly; force, impulse, velocity, mass and ownership act on the
  assembly. One anchored part anchors the whole assembly.
- Tune forces and impulses from intended acceleration times `AssemblyMass`, not by trial values.
- Automatic ownership moves nearby unanchored assemblies to clients. Call `SetNetworkOwner(nil)`
  for critical objects, then measure the server cost and responsiveness. Re-check ownership after
  anchoring changes; it is not always kept.
- A client owner can fake physical results and `.Touched` events. The server validates
  consequential hits, positions, timing and permissions independently.
- If `Workspace.AuthorityMode` is `Server`, the server owns simulation and clients predict nearby
  assemblies with rollback. Drive predicted forces and constraints from
  `RunService:BindToSimulation()` on both sides, not from `Heartbeat` or client-only scripts, and
  expect custom physics scripts to need changes when a place switches modes.

## Gotchas

| Symptom | Likely cause | Remedy |
|---|---|---|
| welded mechanism will not move | one part anchored | inspect the whole assembly; anchor only world roots |
| force too strong or too weak | assembly mass ignored | read `AssemblyMass`; size force for the intended acceleration |
| fast projectile misses | discrete contact sampling | swept query (`Blockcast`, `Spherecast`, `Shapecast`) per step; see `physics-tuning` |
| ray hits the shooter or effects | no filter or query group | reuse explicit params and a query collision group |
| one target damaged many times | overlap returned several body parts | deduplicate by model; attack ID or cooldown |
| exploit fires impossible touches | client owns the relevant part | server query plus context validation; deliberate ownership |
| invisible trigger blocks players or queries miss it | the three Can* flags conflated | set `CanCollide`, `CanTouch`, `CanQuery` independently |
| attachments pile up | temporary constraint lifecycle missing | create and destroy constraint, attachments and connections together |
| collision group "does not exist" at startup | groups registered from several scripts | register in one script before assigning |

## Resources

- Read `references/queries-and-ownership.md` when designing collision groups, query filters, a
  vehicle or other ownership-sensitive object, or a BodyMover migration; it has the flag roles,
  query choice, ownership debugging, and the physics test matrix.

## Related skills

- `physics-tuning`: timestep, jitter, tunnelling, mass ratios, and feel.
- `roblox-characters`: Humanoid and custom movement across respawns.
- `roblox-networking`: authoritative validation of client-requested physical actions.
- `roblox-studio-workflow`: visualization, Output, and multi-client verification.

## Version notes

Last verified: 2026-11-11.

- Collision groups are registered on `Workspace` or a `WorldModel` (`WorldRoot` methods); the
  `PhysicsService` collision-group methods are deprecated. A `WorldModel` keeps its own matrix
  unless `UseWorkspaceCollisionGroups` is on.
- BodyMovers (`BodyPosition`, `BodyVelocity`, `BodyGyro` and others) are deprecated in favour of
  the constraint-based movers.
- Server Authority reached full release in July 2026; see `roblox-networking` for its rules.
- To re-check an API: append `.md` to its Creator Hub URL, or start from
  `https://create.roblox.com/docs/llms.txt`.

Sources: `https://create.roblox.com/docs/physics/assemblies`,
`https://create.roblox.com/docs/physics/network-ownership`,
`https://create.roblox.com/docs/workspace/raycasting`,
`https://create.roblox.com/docs/workspace/collisions`,
`https://create.roblox.com/docs/projects/server-authority`.
