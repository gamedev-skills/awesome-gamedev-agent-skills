---
name: tower-defense
description: >
  Build a tower defense: enemies pathing along lanes, wave spawning, towers that auto-target and fire,
  an economy, and lives. Use for a tower-defense/wave-defense game, or balancing waves and economy.
license: Apache-2.0
compatibility: Engine-agnostic design patterns; snippets are pseudocode (port to your engine)
metadata:
  engine: none
  category: genres
  difficulty: intermediate
---

# Tower Defense

A playbook for tower defense — enemy pathing, wave spawning, tower targeting, and the
economy that ties them together. This is a **compositional** skill: it orchestrates pathing,
AI, and UI into a TD loop. It does not re-teach pathfinding; it defines the systems and the
balance levers (DPS vs. HP vs. income) that decide whether a TD is tense or trivial.

## When to use

- Use when building a game where the player **places towers** that automatically attack
  **waves of enemies** following a path, spends earned currency to expand/upgrade, and loses
  if too many enemies leak through.
- Use when designing wave composition/pacing, tower targeting priorities, or the gold economy.

**When _not_ to use:** the player directly controls a shooter → `fps-shooter`. Free-form base
building with needs → `survival-crafting`. For the pathfinding algorithm itself, use `game-ai`.

## Core loop

**Prepare (place/upgrade towers with current gold) → start the wave → enemies path toward the
goal while towers auto-fire → earn gold from kills → survive the wave → repeat against a
harder one.** The tension is a planning puzzle: is my current DPS enough for what's coming,
and can I afford the answer?

## Must-have systems

1. **Enemy path** — waypoint lanes, or grid + pathfinding for maze TD (refs).
2. **Wave spawner** — timed, scripted sequences of enemy types with per-wave scaling.
3. **Towers** — range, fire rate, damage, projectile/hitscan, splash; placement validity.
4. **Targeting** — per-tower priority (first/last/closest/strongest/weakest) (refs).
5. **Economy** — gold from kills + wave bonuses; tower/upgrade costs; sell refund.
6. **Lives / leak** — enemies reaching the goal cost lives; 0 = game over.
7. **Wave/prep UI** — lives, gold, next-wave preview, start-next-wave control.

## Design knobs

| Knob                      | Effect                  | Notes                                    |
| ------------------------- | ----------------------- | ---------------------------------------- |
| Enemy HP growth/wave      | upgrade pressure        | Geometric ~1.1–1.2× (refs).              |
| Income vs. HP curves      | difficulty              | Player should _almost_ afford each wave. |
| Tower DPS / range / cost  | tower identity          | Cheap+wide vs. expensive+tall.           |
| Targeting priority        | optimal placement       | Changes play more than raw stats.        |
| Enemy variety             | counters one-build wins | Fast / armored / flying / swarm / boss.  |
| Leak penalty              | stakes                  | Cost lives _and_ lost bounty.            |
| Upgrade vs. build economy | strategy depth          | Diminishing upgrade returns.             |
| Wave pacing               | tension curve           | Spike → breather → spike, not monotonic. |

## Patterns

### 1. Wave spawner (timed, data-driven)

```python
# Pseudocode. A wave is data: a list of (enemy_type, count, spacing). Spawn over time.
wave = [ ("grunt", 10, 0.5), ("runner", 5, 0.3), ("tank", 2, 1.0) ]

def run_wave(wave):
    for enemy_type, count, spacing in wave:
        for _ in range(count):
            spawn_enemy(enemy_type, at=path[0])   # enter at the path start
            wait(spacing)                          # seconds between spawns (use a timer/coroutine)
    # wave clears when all spawned enemies are dead or have leaked
```

### 2. Tower targeting (filter to range, then pick by priority)

```python
# Pseudocode. "First" (furthest along path) is the standard default for stopping leaks.
def acquire_target(tower, enemies, mode="first"):
    in_range = [e for e in enemies if distance(tower.pos, e.pos) <= tower.range]
    if not in_range: return None
    if mode == "first":    return max(in_range, key=lambda e: e.progress)   # furthest along path (stop leaks)
    if mode == "last":     return min(in_range, key=lambda e: e.progress)   # least progress (guard the entrance)
    if mode == "closest":  return min(in_range, key=lambda e: distance(tower.pos, e.pos))
    if mode == "strongest":return max(in_range, key=lambda e: e.hp)         # burn down tanks first
    if mode == "weakest":  return min(in_range, key=lambda e: e.hp)         # secure kills / last-hit bounty
    return in_range[0]
```

### 3. "Can this lane hold?" sanity check (DPS vs. HP)

```python
# Pseudocode. One tower's damage to one enemy crossing its range.
tower_dps     = tower.damage * tower.fire_rate
time_in_range = tower.range_coverage_length / enemy.speed
damage_dealt  = tower_dps * time_in_range
# Lane holds if summed damage_dealt from covering towers >= enemy.hp (per enemy). See refs.
```

## Pitfalls / failure modes

- **Enemy HP scales slower than player income/DPS** → game trivializes after a few waves.
  Tune the HP curve against the income curve (refs).
- **One dominant tower/strategy** → no decisions. Add enemy types that hard-counter builds
  (armored vs. rapid-fire, flying vs. ground-only) and diminishing upgrade returns.
- **Maze TD that can fully block the goal** → enemies get stuck/softlock. Forbid placements
  that sever the path; recompute paths when towers change (refs).
- **No next-wave telegraph** → specials feel random and unfair. Preview upcoming composition.
- **Per-frame movement unscaled by `dt`** → speed varies with frame rate. Scale steering by `dt`.
- **Leaks only cost lives, not gold** → leaking is sometimes optimal. Make leaks lose bounty too.
- **Monotonic difficulty ramp** → exhausting. Pace spikes and breathers.

## Composition (build it from these skills)

- **Pathing:** `game-ai` for A\*/flow-field/steering; for fixed lanes, simple waypoint following.
- **Enemy movement:** `godot-2d-movement` (or engine equivalent) to move along the path; `unity-navmesh` for nav-based pathing.
- **Map:** `godot-tilemap` / `unity-tilemap-2d` for the grid/lanes; `level-design` for map layouts.
- **Data:** `godot-resources` / `unity-scriptableobjects` to define towers, enemies, and waves as assets.
- **UI:** `game-ui-ux` for HUD layout, scaling, and the build menu; `godot-ui-control` for the concrete widgets (lives, gold, wave preview).
- **Polish:** `audio-design` for fire/hit/leak sound cues.

## References

- For path representations (waypoints / A\* / flow fields), targeting modes, DPS and economy
  math, enemy scaling, and wave pacing, read `references/balancing.md`.
