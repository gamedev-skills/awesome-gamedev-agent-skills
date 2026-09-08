---
name: roblox-physics
description: >
  Implement Roblox physical simulation and queries with assemblies, anchoring, constraints,
  collision groups, CanCollide/CanTouch/CanQuery, raycasts and overlap queries, mass, impulses,
  forces, velocity, moving assemblies, cleanup, and network ownership. Use for Roblox collisions,
  hit detection, RaycastParams, PhysicsService, projectiles, vehicles, knockback, constraints,
  deprecated BodyMovers, unstable motion, or client-owned physics exploits.
---

# Roblox physics

Choose deliberately between simulation, character control, hit detection, and visual-only motion;
they are different jobs. Targets Roblox's rolling platform APIs. Pair with `physics-tuning` for
engine-neutral stability and feel.

## When to use

- Use for BasePart assemblies, constraints, collision/query policy, ray/overlap queries, forces,
  impulses, moving physical objects, network ownership, or physics cleanup.
- Use when `Touched` is unreliable/security-sensitive, parts tunnel or jitter, a mechanism breaks
  when anchored, or old BodyMover patterns appear.

**When not to use:** ordinary Humanoid lifecycle/control belongs to `roblox-characters`; remote
validation belongs to `roblox-networking`; decorative UI/world motion may only need a tween.

## Decide the system first

| Goal | Mechanism |
|---|---|
| sustained physical interaction | unanchored assembly + modern constraints/forces |
| instantaneous physical change | `ApplyImpulse` / `ApplyAngularImpulse` |
| kinematic platform/path | controlled pivot/transform with an explicit passenger policy |
| character locomotion | Humanoid/custom character controller (`roblox-characters`) |
| authoritative hit test | server raycast/overlap with filters and gameplay validation |
| cosmetic trail/recoil | local visual motion; no gameplay authority |

## Workflow

1. **Inspect the mechanism.** In Studio, visualize assemblies, anchors, constraints, collision
   groups, massless parts, and network owners. Identify the assembly root and intended authority.
2. **Define interaction policy.** Write the collision-group matrix and separately decide
   `CanCollide`, `CanTouch`, and `CanQuery`. These flags are not interchangeable.
3. **Choose simulation or query.** Do not use `.Touched` as a universal hit detector. Use a ray for
   a path/line, an overlap query for a volume, and simulation contacts when physical response is
   actually required.
4. **Apply motion at assembly level.** Forces on a part affect its assembly. Use modern
   `LinearVelocity`, `AngularVelocity`, `VectorForce`, `AlignPosition`, and `AlignOrientation`
   constraints as appropriate; migrate deprecated BodyMovers when changing that system.
5. **Set ownership deliberately.** Server-own gameplay-critical loose assemblies when required;
   client ownership can improve responsiveness but never authorizes gameplay results.
6. **Bound cost and lifetime.** Reuse query parameters, cap query frequency/result count, remove
   temporary constraints/attachments, and disconnect event listeners.
7. **Verify under load and multiplayer.** Test anchored/unanchored transitions, mass extremes,
   collision matrix, fast motion, multiple clients, ownership changes, streaming, and cleanup.

## Pattern: filtered server raycast

```lua
local Workspace = game:GetService("Workspace")

local params = RaycastParams.new()
params.FilterType = Enum.RaycastFilterType.Exclude
params.FilterDescendantsInstances = {shooterCharacter}
params.IgnoreWater = true
params.CollisionGroup = "WeaponQuery"

local direction = aimDirection.Unit * MAX_RANGE
local result = Workspace:Raycast(muzzlePosition, direction, params)
if result then
    local model = result.Instance:FindFirstAncestorOfClass("Model")
    local humanoid = model and model:FindFirstChildOfClass("Humanoid")
    if humanoid and serverCanDamage(shooter, model, result.Position) then
        humanoid:TakeDamage(serverWeaponDamage(shooter))
    end
end
```

The server must validate the origin/direction against server-known character/weapon state; do not
accept an arbitrary client origin and treat the raycast itself as validation.

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

Bounds queries use bounding boxes and can include multiple parts from one target; deduplicate and
perform exact/gameplay checks as needed. For exact geometry use `WorldRoot:GetPartsInPart(part, overlapParams)`
only when its additional cost is justified. Note `OverlapParams.RespectCanCollide` decides whether a
query honours `CanCollide` or `CanQuery` — set it deliberately, or it silently overrides the flag
policy below. `OverlapParams.Tolerance` controls contact slop.

## Assemblies, force, and ownership

- Welded parts form one rigid assembly; force, impulse, velocity, mass, and ownership operate on
  that assembly. Anchoring a part changes simulation/ownership and can make an assembly effectively
  infinite mass.
- Apply an impulse for a one-time change; use a force or velocity constraint for sustained control.
  Setting `AssemblyLinearVelocity` is an immediate state change, not a continuous force model.
- Prefer attachments plus modern constraints over `BodyPosition`, `BodyVelocity`, `BodyGyro`, and
  other deprecated BodyMovers when authoring or revising a mechanism.
- Automatic ownership may move nearby unanchored assemblies to clients. Use
  `SetNetworkOwner(nil)` conservatively for critical objects, then measure responsiveness/server
  cost. Visualize network owners in Studio.
- A client owner can manipulate physical results and `.Touched` observations. The server validates
  consequential hits, positions, timing, and permissions independently.

## Common failures

| Symptom | Likely cause | Remedy |
|---|---|---|
| welded mechanism will not move | one part anchored | inspect full assembly; anchor only intentional world roots |
| force behaves too strongly/weakly | assembly mass ignored | inspect `AssemblyMass`; tune force/impulse by intended acceleration |
| hit misses fast projectile | discrete touch sampling/tunneling | swept query — `WorldRoot:Blockcast()`, `Spherecast()`, or `Shapecast()` — plus `physics-tuning`; do not rely only on `.Touched` |
| ray hits shooter/effects | filters/collision group absent | reuse explicit params and query group |
| same target damaged many times | overlap returned multiple body parts | deduplicate by target model and enforce attack ID/cooldown |
| exploit fires impossible touch | client owns relevant physics | server query/context validation; deliberate ownership |
| invisible trigger blocks or cannot query | three flags conflated | set `CanCollide`, `CanTouch`, `CanQuery` independently |
| mechanism leaks attachments | temporary constraint lifecycle missing | own and destroy constraints, attachments, and connections together |

## Resources

- Read `references/queries-and-ownership.md` for collision/query matrices, assembly debugging,
  ownership security, migration choices, and the physics verification matrix.

## Related skills

- `physics-tuning` — timestep, jitter, tunneling, mass ratios, and stability methodology.
- `roblox-characters` — Humanoid/custom movement and respawn lifecycle.
- `roblox-networking` — authoritative validation of client-requested physical actions.
- `roblox-studio-workflow` — visualization, Output, and multi-client verification.

## Primary references

- `https://create.roblox.com/docs/physics/assemblies`
- `https://create.roblox.com/docs/physics/network-ownership`
- `https://create.roblox.com/docs/workspace/raycasting`
