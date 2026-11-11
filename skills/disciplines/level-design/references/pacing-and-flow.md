# Pacing, teaching, gating and guidance

Contents: the tension curve; the teaching loop; critical path, golden path and branches; gating
tools; guidance without walls; 2D vs 3D; blockout review.

## The tension curve

Plot intended intensity against progress.

- **Overall rise with local dips.** Intensity trends up toward a climax in a sawtooth: spikes
  (combat, platforming gauntlets, bosses) separated by rests (exploration, story, safe rooms).
  A flat high numbs the player; a flat low bores them.
- **Rest before the climax.** A save point, vista or resource cache right before the hardest
  beat makes the spike land harder.
- A useful rhythm is introduce, build, peak, release, then repeat higher. Each peak exceeds the
  last and each release sits a little above the previous baseline.

## The teaching loop

1. **Introduce** the mechanic alone, where failure is harmless.
2. **Develop** it with movement or a second element so the player practises on purpose.
3. **Twist** the context so the player applies the idea rather than a memorised motion.
4. **Test** it under time or health pressure.

The level is a lesson plan: a new mechanic meets the player before a lethal test, never during
one. In the beat list, a `teach` beat for each mechanic should come before its first `combat`
or `climax` beat.

## Critical path, golden path and branches

- **Critical path:** the minimal route from start to goal, solvable with keys and abilities
  obtained in order. Check it with the reachability graph.
- **Golden path:** the route most players actually take. Pace along this one.
- **Branches:** optional loops for exploration and reward. Keep them short enough to rejoin the
  golden path without losing momentum, and make the reward worth the detour.
- **Shortcuts** that unlock back to an earlier hub cut backtracking and make the space feel
  coherent. Add them to the room graph as exits that need the unlock.

## Gating tools

- **Locks and keys:** explicit, readable order control.
- **Ability gates:** a chasm that needs the double jump found later (the metroidvania
  pattern). Check the acquisition order, not just connectivity.
- **One-way drops and collapsing paths:** enforce direction. Telegraph them, and check that the
  landing room can still reach a save or exit.
- **Soft gates:** enemies, hazards or difficulty that say "not yet" without a hard wall.

## Guidance without walls

- **Light and contrast:** a bright doorway reads as "go here"; shadow reads as optional or
  dangerous.
- **Leading lines:** architecture, rails and paths that point at the objective.
- **Landmarks:** a tall, unique silhouette visible from afar orients the player.
- **Colour and material:** one consistent colour for interactive things or exits teaches players
  to scan for it.
- **Framing:** show the next goal from a high point before the player descends to it.

When playtest reports say "I got lost here", the fix is usually a sightline or a light.

## 2D vs 3D

- **2D:** think in the tile grid and the camera window. The player sees a fixed slice, so
  telegraph off-screen threats with sound or approach time. Platform spacing and sightlines
  dominate.
- **3D:** think in sightlines, verticality and navigation. Players lose their bearings in three
  dimensions, so landmarks and framed vistas matter more. Tight interiors and the view cone
  change what feels reachable.

## Blockout review

Run the agent checks first, then use this list to write the playtest questions for the user.

- Critical path solvable with keys and abilities in order; no one-way drop into a dead end.
- Every required traversal within the measured metrics.
- Pacing is a rising sawtooth with a rest before each major spike.
- Each mechanic is taught before it is tested.
- The eye is led toward the path. Ask the user where they were unsure where to go.
- Optional content rewards the detour and rejoins smoothly.
- It plays well as untextured geometry. Ask the user whether any room felt like a chore or
  unfair, and how many attempts the hardest required jump took.
