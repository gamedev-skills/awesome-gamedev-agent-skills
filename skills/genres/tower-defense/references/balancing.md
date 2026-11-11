# Tower defense balancing and pathing (depth)

Math and structures behind `SKILL.md`. Engine-neutral pseudocode. The numbers are starting
points; tune against playtests. For pathfinding internals defer to `game-ai`.

Contents:
1. Representing the path (waypoints, maze placement check)
2. Tower targeting modes
3. DPS and "can this lane hold?"
4. Enemy scaling across waves
5. Economy
6. Leak and lives model
7. Wave pacing

## 1. Representing the path

Three common approaches:

- **Fixed waypoints (lanes):** an ordered list of points; enemies steer toward the next one.
  Simplest, fully authored, ideal for lane defense. Most TD games use this.
- **Grid + pathfinding (A\*):** enemies path from spawn to goal over a walkable grid. Enables
  **maze TD**, where placing towers reshapes the path. Recompute paths when towers change and
  forbid placements that fully block the goal.
- **Flow field:** precompute one direction per tile pointing toward the goal; every enemy reads
  it. Scales to huge crowds (one computation for all enemies) — see `game-ai`.

```python
# Waypoint following (pseudocode). Spend this step's whole move distance, carrying any
# leftover past a waypoint, so fast enemies don't lose time at corners or overshoot them.
def update_enemy(e, dt):
    remaining = e.speed * dt
    while remaining > 0:
        target = path[e.wp_index]
        to_go  = distance(e.pos, target)
        if to_go > remaining:
            e.pos = move_toward(e.pos, target, remaining)
            e.progress += remaining
            return
        e.pos = target                     # reached this waypoint exactly
        e.progress += to_go
        remaining -= to_go
        e.wp_index += 1
        if e.wp_index >= len(path):
            leak(e)                        # reached the goal: cost the player a life
            return
```

`e.progress` is distance travelled along the path; "first"/"last" targeting reads it (§2).
In Godot 4.7, a `Path2D` with one `PathFollow2D` per enemy does this for you: add
`speed * delta` to `PathFollow2D.progress` (set `loop = false`) and treat
`progress_ratio >= 1.0` as a leak.

**Maze TD placement check.** Before committing a tower, mark its cell blocked and run one
breadth-first search (or flow-field build) from the goal. Reject the placement if the spawn
**or any enemy currently on the field** can no longer reach the goal; otherwise keep it and
re-path the enemies. In Godot, `AStarGrid2D.set_point_solid()` takes effect without another
`update()` call.

## 2. Tower targeting modes

Expose a per-tower targeting priority; it changes optimal play more than raw stats:

| Mode | Picks | Good for |
|------|-------|----------|
| First | enemy furthest along the path | default; stops leaks |
| Last | enemy least far along | feeding another tower / slows |
| Closest | nearest to the tower | short-range/splash towers |
| Strongest | highest current/max HP | focus tanks |
| Weakest | lowest HP | last-hit / efficiency |

```python
# Pseudocode. Filter to in-range, then pick by mode.
def acquire_target(tower, enemies, mode):
    in_range = [e for e in enemies if distance(tower.pos, e.pos) <= tower.range]
    if not in_range: return None
    if mode == "first":    return max(in_range, key=lambda e: e.progress)
    if mode == "last":     return min(in_range, key=lambda e: e.progress)
    if mode == "closest":  return min(in_range, key=lambda e: distance(tower.pos, e.pos))
    if mode == "strongest":return max(in_range, key=lambda e: e.hp)
    if mode == "weakest":  return min(in_range, key=lambda e: e.hp)
```

## 3. DPS and "can this lane hold?"

```
tower_dps        = damage * fire_rate            # shots/sec
effective_dps    = tower_dps * (1 - target.armor_reduction)
time_in_range    = path_length_in_range / enemy_speed
damage_dealt     = effective_dps * time_in_range  # what one tower does to one passing enemy
```

A lane holds a wave if the **sum of damage_dealt across all covering towers** ≥ enemy HP for
each enemy, accounting for how many enemies overlap in range at once (a single tower can only
shoot one target at a time unless it has splash/multi-shot).

## 4. Enemy scaling across waves

```python
# Pseudocode. Scale HP (and sometimes count/speed) so towers must be upgraded, not just spammed.
def wave_enemy_hp(base_hp, wave, growth=1.15):
    return int(base_hp * (growth ** wave))     # geometric HP growth

# Mix enemy types so one tower build can't answer everything:
#   fast/low-HP (rush slows), armored (counters low-damage rapid fire),
#   flying (needs anti-air), swarm (needs splash), boss (huge HP spike).
```

Geometric HP growth (~1.1–1.2× per wave) paired with a linear-ish income curve forces
upgrades. If HP grows slower than the player's income/DPS, the game trivializes; faster, and
it walls. Tune the two curves against each other.

## 5. Economy

Income sources and sinks must be balanced so the player is *almost* able to cover each wave:

```
income_per_wave = kill_bounty * enemies_killed + wave_clear_bonus (+ interest, optional)
spend           = tower_costs + upgrade_costs
```

- **Kill bounty:** gold per enemy. Leaks should cost income *and* lives so leaking hurts twice.
- **Upgrade vs. build curve:** make upgrades cost-efficient enough that "tall" (few upgraded
  towers) competes with "wide" (many cheap towers). Diminishing upgrade returns prevent one
  god-tower.
- **Interest/banking (optional):** rewards saving but can snowball; cap it.
- **Sell refund:** partial (e.g. 70%) so repositioning is possible but not free.

## 6. Leak / lives model

- Each enemy reaching the goal removes lives (often 1, bosses more). Game over at 0.
- Show a clear "lives" counter and telegraph the next wave's composition so players can prepare.
- A short build/prep phase between waves (or a "start next wave early" bonus) gives agency and
  pacing control.

## 7. Wave pacing

- Alternate pressure: a hard wave, then a breather, then a spike. Pure monotonic ramps exhaust.
- Telegraph specials (flying/boss) one wave ahead via UI so the counter feels fair, not random.
- Let players trigger the next wave early for an economy bonus — rewards confidence and speeds
  pacing for experts without punishing newcomers.
