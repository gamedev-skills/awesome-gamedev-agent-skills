---
name: tower-defense
description: >
  Designs tower defense games in any engine: lane and maze pathing, wave pacing, targeting
  priorities, armoured and flying counters, and the gold economy, with a wave-curve checker. Use
  for a Bloons- or Kingdom Rush-like, or late waves that are impossible or trivial or a dominant
  tower. Not for pathfinding (`game-ai`) or survival base building (`survival-crafting`).
---

# Tower defense

Owns the TD loop: paths, waves, towers, targeting and the economy that links them. The core
balance question is whether the DPS the player can afford keeps pace with the HP each wave
sends, so design both curves together and check them with the script before playtesting.

## When to use

- Towers attack waves on their own, the player spends earned currency to build, upgrade and
  sell, and leaks cost lives. Includes lane defense, mazing TD and TD-action hybrids.
- Balancing waves and economy, choosing targeting modes, adding enemy types, fixing pathing.

**When not to use:** the player shoots directly (`fps-shooter`); free-form base building with
needs (`survival-crafting`); the A* or flow-field code itself (`game-ai`).

## Workflow

1. **Pick the map model:** fixed lanes (most TDs; full control of pacing), maze (towers shape
   the path; needs placement validation) or open field with flow fields (large crowds).
2. **Write towers, enemies and waves as data.** Each tower has a role (single-target DPS,
   splash, slow, anti-air, armour pierce, support) and each enemy type exists to counter one
   lazy build: fast (beats slow single-target), armoured (beats rapid low-damage), flying
   (skips ground-only), swarm (beats single-target), boss (HP spike), regenerating or shielded
   (punish slow DPS).
3. **Set the curves:** enemy HP per wave grows geometrically (start near 1.12-1.18x per wave)
   and income grows from bounty growth plus enemy count. The two compound against each other,
   so small changes matter: in the script's example, HP growth 1.15 holds for 30 waves while
   1.25 walls by wave 2.
4. **Run the curve check** (path relative to this skill folder):
   `python3 scripts/td_curve_check.py waves.json`. It buys a reference tower with all gold
   before each wave and prints each wave's pressure (needed DPS / owned DPS x efficiency).
   Errors are walls (pressure above 1.0); warnings are runs of trivial waves. Aim for 0.6-0.95
   with breathers between spikes. `--help` shows the spec format; `--json` for tooling.
5. **Pace the session:** a short build phase between waves, a next-wave preview, an early-call
   bonus for confident players and a 2-3x fast-forward toggle.
6. **Check it.** Run the curve check and these tests, then report the numbers:
   - a fast enemy (speed x 10) on a path with sharp corners keeps its total travel time within
     one tick of `path_length / speed` (refs §1);
   - maze maps: every placement that would cut the spawn or any walking enemy off from the goal
     is refused (refs §1);
   - targeting "first" picks the enemy with the most path progress even when another is
     closer to the tower.

## Economy rules

| Lever | Start here | Why |
|-------|-----------|-----|
| Wave 1 | beatable with starting gold at pressure about 0.5-0.7 | the first wave teaches, it does not test |
| Kill bounty | most income early; wave-clear bonus grows later | late income should reward survival, not farming |
| Leaks | cost lives and the bounty | otherwise leaking can be optimal |
| Sell refund | 50-80% of money spent | repositioning possible, never free |
| Interest | optional, capped | rewards saving but snowballs |
| Upgrades | competitive gold-per-DPS with new towers, with diminishing tiers | "tall" and "wide" both viable |
| Early call | gold bonus scaled by time skipped | speeds the game for experts |
| Targeting | per tower: first (default), last, strongest, weakest, closest | changes play more than raw stats |

## Pattern 1: wave data

```python
# A wave is data: groups spawn in order, each with its own spacing.
WAVES = [
    {"groups": [{"type": "grunt", "count": 10, "spacing": 0.6},
                {"type": "runner", "count": 6, "spacing": 0.3}], "clear_bonus": 30},
    {"groups": [{"type": "armored", "count": 4, "spacing": 1.2}], "clear_bonus": 35,
     "preview": "armored"},                     # shown one wave ahead in the UI
]
```

Telegraph every new enemy type a wave ahead, and introduce it alone before mixing it with
others, so the counter feels learnable rather than random.

## Gotchas

- **Late game impossible or trivial** → HP growth and income growth set separately. Tune them
  together with the curve check; geometric HP needs geometric income or upgrade efficiency.
- **One tower wins everything** → no enemy counters it. Add the counter type (step 2) and
  diminishing upgrade returns.
- **Enemies stuck, or the goal unreachable** → a maze placement severed the path. Validate with
  one search from the goal before committing (refs §1).
- **Fast enemies slow down at corners or overshoot** → movement stops at each waypoint. Carry
  the leftover distance (refs §1).
- **Towers ignore the enemy about to leak** → "closest" used as the default. Default to
  "first" by path progress.
- **Wave timers drift on slow machines** → spawn spacing counted in frames. Use the game clock;
  fast-forward multiplies the clock, not the frame rate.
- **Specials feel unfair** → no preview. Show the next wave's composition.
- **Monotonic ramp exhausts players** → every wave harder than the last. Spike, breather,
  spike.

## References

- `references/balancing.md`: read when choosing path representations and writing waypoint or
  maze validation code, targeting mode code, DPS and "can this lane hold" math, HP scaling,
  economy details, lives and wave pacing.
- `scripts/td_curve_check.py --help`: spec format and the pressure model's limits.

Related: `game-ai` (A*, flow fields), `level-design` (map layouts), `godot-tilemap` or
`unity-tilemap-2d` (grid maps), `godot-resources` or `unity-scriptableobjects` (tower and
wave data), `game-ui-ux` (build menu, wave preview, HUD), `game-feel` and `audio-design`.

## Version notes

Last verified: 2026-11-11.

- Godot 4.7 `Path2D` and `PathFollow2D` (`progress`, `progress_ratio`, `loop`) and
  `AStarGrid2D.set_point_solid()` (no `update()` needed afterwards) used in the reference were
  checked against the 4.7.2 class reference (doc/classes/*.xml); `PathFollow2D.loop` defaults
  to true, so set it to false for leak detection.
- Curve figures (1.15 holds, 1.25 walls) come from running the bundled checker on its test
  spec, not from a shipped game.
