# Roblox physics queries, collision policy, and ownership

Read this when designing collision groups, query filters, a physical gameplay object, or a
multiplayer ownership/security test.

## Separate the three flags

`CanCollide` controls physical response, `CanTouch` controls touch event participation, and
`CanQuery` controls spatial-query eligibility (subject to query parameters). Define each by role.
Typical sensor parts do not collide but may touch/query; visual-only geometry may do neither. Use
named collision groups through `PhysicsService` and verify the actual matrix in Studio.

## Query selection

- `Workspace:Raycast(origin, direction, params)` for the first surface along a segment. Direction
  magnitude is range.
- sphere/block radius/bounds overlap methods for broad volume candidates. Deduplicate assemblies or
  target models and refine if bounding-box false positives matter.
- configure `RaycastParams`/`OverlapParams` with include/exclude instances, collision group, water,
  and result bounds. Reuse params where the filter is stable; update it when character generations
  or streamed containers change.

Query results are evidence, not a whole gameplay authorization. Also validate actor state, team,
cooldown, origin, target membership, and permissions on the server.

## Assembly and ownership debugging

In Studio, inspect `AssemblyRootPart`, `AssemblyMass`, center of mass, anchors, constraints, and the
Network Owners visualization. Test automatic ownership before forcing it. Server ownership protects
simulation authority but can increase server work and latency; client ownership improves response
but requires server validation of consequences.

When a mechanism changes anchor state, re-check ownership because prior ownership state may not be
retained. For vehicles, explicitly decide which occupant should own the assembly and what happens
on seat changes, death, or disconnect.

## Modern motion migration

Map sustained linear control to `LinearVelocity` or `VectorForce`, rotational control to
`AngularVelocity`/`Torque`, and pose following to `AlignPosition`/`AlignOrientation`. Preserve the
old system's coordinate space, force/torque limits, attachment geometry, reaction force, and
ownership behavior; do not replace class names without measuring behavior.

## Verification matrix

Test one part and a welded multi-part assembly; anchored/unanchored transitions; intended collision
group pairs; each Can* flag; fast and slow movers; low/high mass; ray miss/hit/filter edge; overlap
deduplication and max-result behavior; client approaching/leaving automatic ownership; explicit
owner disconnect/death; two clients interacting simultaneously; streaming absence; and complete
temporary-object cleanup. Use server-observed results for gameplay assertions.

## Primary references

- `https://create.roblox.com/docs/physics/assemblies`
- `https://create.roblox.com/docs/physics/network-ownership`
- `https://create.roblox.com/docs/workspace/raycasting`
- `https://create.roblox.com/docs/reference/engine/datatypes/RaycastParams`
