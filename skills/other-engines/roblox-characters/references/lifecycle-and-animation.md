# Character lifecycle and animation verification

Read this when a character system crosses respawns, supports multiple rigs, or owns animation and
tool resources.

## Durable player, replaceable character

Keep account/session data keyed by `Player`. Keep Humanoid/root/Animator references, tracks,
character-only state, touch listeners, and character UI bindings inside a spawn scope. The scope
ends at `CharacterRemoving` or when a newer generation replaces it. `Humanoid.Died` is gameplay
death; it is not a guaranteed substitute for removal/cleanup.

On the server, bind players already present as well as future players when a Script can start after
players exist. On the client, subscribe before handling `LocalPlayer.Character` to reduce races.
After every yield, confirm the player still owns that same character.

## Custom character checklist

- Model/root contract is documented; `PrimaryPart` is set if systems use it.
- Humanoid rig has required body/root/head/joints; non-Humanoid rig has an
  `AnimationController`/`Animator` if animated.
- collision groups, mass, ownership, camera subject, controls, spawn placement, death/reset, tools,
  attachments, and accessories are deliberately handled.
- `StarterCharacter` and `CharacterAutoLoads` behavior is tested, including manual loading if used.
- R6/R15/custom branches are limited to topology differences rather than duplicated systems.

## Animation checks

Verify the animation is owned/usable by the experience, loads on the intended Animator, uses the
expected priority/looping, blends in/out cleanly, and stops on state exit. Marker names and optional
parameters must match the authored animation. Store every marker/stopped connection in the same
scope as the track.

Client-played character animation can provide responsive presentation, but gameplay effects remain
server-authoritative. For NPC/server-controlled rigs, load/play in the authoritative context chosen
by the project and verify what all clients observe.

## Lifecycle stress matrix

Test initial spawn, ordinary death, Reset Character, rapid repeated respawn, respawn during delayed
setup, character replacement without death, tool equipped during death, leave during setup, two
players dying simultaneously, and every supported rig. Inspect for duplicate callbacks, lingering
tracks, errors/warnings, stale UI/camera subjects, leftover tagged objects, and player-scope state
that was incorrectly cleared.

## Primary references

- `https://create.roblox.com/docs/characters`
- `https://create.roblox.com/docs/animation/using`
- `https://create.roblox.com/docs/characters/appearance`
