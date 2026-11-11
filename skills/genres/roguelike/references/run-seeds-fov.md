# Roguelike floors, seeds, FOV and run state (depth)

Depth behind `SKILL.md`. Engine-neutral pseudocode. The generation algorithms themselves
(rooms and corridors, BSP, cellular caves, drunkard's walk, WFC, noise) and loot-table
mechanics belong to `procedural-gen`; this file covers what a roguelike demands of their
output.

Contents:
1. Floor acceptance checks
2. Seeds and RNG streams
3. Field of view: symmetric shadowcasting
4. Spawn budgets and out-of-depth threats
5. Per-run item identification
6. Run state and profile state

## 1. Floor acceptance checks

Run these on every generated floor and regenerate (with the next sub-seed) on failure. Log the
failure rate in a batch run: above a few percent, fix the generator instead.

```python
def accept(floor):
    reached = flood_fill(floor, floor.start)              # 4- or 8-way, as movement allows
    if floor.stairs_down not in reached: return False
    if any(cell not in reached for cell in floor.floor_cells): return False   # or carve/fill
    if any(dist(floor.start, m.pos) < SAFE_START for m in floor.monsters): return False
    for key, door in floor.locks:                         # every key reachable without its door
        if key.pos not in flood_fill(floor, floor.start, blocked=door): return False
    return True
```

A `SAFE_START` of 6-8 tiles keeps the first turn from being a death. On caves, keeping only
the largest connected region is the cheap way to satisfy the "every floor cell reachable" rule.

## 2. Seeds and RNG streams

```python
def sub_seed(run_seed, *parts):                           # stable across processes and platforms
    data = repr((run_seed,) + parts).encode()
    return int.from_bytes(hashlib.blake2b(data, digest_size=8).digest(), "little")

map_rng    = Rng(sub_seed(run_seed, "map", depth))       # floor layout
spawn_rng  = Rng(sub_seed(run_seed, "spawn", depth))     # monsters and items placed at gen time
combat_rng = Rng(sub_seed(run_seed, "combat"))           # hits and damage; consumed by play
loot_rng   = Rng(sub_seed(run_seed, "loot"))             # drops; consumed by play
```

Floor N then depends only on the seed and N, not on how many attacks happened on floors 1 to
N-1, so two players on the same seed see the same floors. Do not use a language's built-in
`hash()` for this: Python randomises string hashing per process. Daily runs use
`sub_seed("daily", utc_date)` so every player gets the same seed for the same UTC day.

## 3. Field of view: symmetric shadowcasting

Properties you want: **symmetric** (if floor tile A sees floor tile B, B sees A), no blind
corners, and walls that light up as you walk along them. Classic recursive shadowcasting (eight
octants, tiles shown if they touch the visible slope range) is fast but breaks symmetry.
*Symmetric shadowcasting* (Albert Ford, 2021) fixes it with one rule: a **floor** tile is
visible only if its **centre** lies inside the visible slope range; a **wall** tile is visible
if any part of it does.

```python
# Pseudocode. Scan each of the 4 quadrants (N, E, S, W) row by row, moving away from the origin.
# Slopes are col/depth; keep them as exact fractions (rationals), not floats, so the edge
# tests do not wobble. (depth, col) is mapped to (x, y) per quadrant by a small transform.
def scan(quadrant, depth, start, end):           # first call: depth=1, start=-1, end=+1
    prev_wall = None
    for col in range(round_half_up(depth * start), round_half_down(depth * end) + 1):
        wall = is_wall(quadrant, depth, col)
        centre_inside = depth * start <= col <= depth * end
        if wall or centre_inside:
            mark_visible(quadrant, depth, col)
        if prev_wall is True and not wall:        # leaving a wall: narrow the start
            start = Fraction(2 * col - 1, 2 * depth)
        if prev_wall is False and wall:           # hitting a wall: scan the gap before it
            scan(quadrant, depth + 1, start, Fraction(2 * col - 1, 2 * depth))
        prev_wall = wall
    if prev_wall is False:                        # row ended on floor: continue outward
        scan(quadrant, depth + 1, start, end)
```

`round_half_up(x)` is `floor(x + 1/2)` and `round_half_down(x)` is `ceil(x - 1/2)`. The origin
tile is always visible and treated as not blocking. Stop recursing at the map edge or at your
light radius, and use a circular check (`dx*dx + dy*dy <= R*R`) for a round light rather than a
square one.

Test it: on random maps, compute FOV from every floor tile and assert that whenever A sees B,
B sees A. This version passes that test; classic recursive shadowcasting does not.

- Keep `explored` separately; render explored-but-not-visible cells dimmed.
- Recompute only when the viewer moves or a door or wall changes, not every frame.

## 4. Spawn budgets and out-of-depth threats

Give each floor a threat budget that grows with depth and spend it from the depth-filtered
monster list, instead of rolling a fixed monster count:

```python
budget = BASE_THREAT + THREAT_PER_DEPTH * depth
while budget > 0:
    choices = [m for m in MONSTERS if m.min_depth <= depth and m.threat <= budget]
    if not choices: break
    if spawn_rng.random() < OUT_OF_DEPTH_CHANCE:          # rare spike, e.g. 0.05
        choices = [m for m in MONSTERS if m.min_depth <= depth + 3] or choices
    m = weighted_pick(choices, spawn_rng)                 # table mechanics: procedural-gen
    place(m); budget -= m.threat
```

The budget keeps density readable at every depth, and the out-of-depth roll creates the
memorable "a dragon on floor 2" moments without making them common. Give items their own
budget so loot does not shrink when a floor rolls tough monsters.

## 5. Per-run item identification

Shuffle unidentified appearances per run so knowledge from the last run does not carry over:

```python
looks = ["murky", "fizzing", "violet", "smoky", "golden", "oily"]
id_rng = Rng(sub_seed(run_seed, "id"))
id_rng.shuffle(looks)
appearance = dict(zip(POTION_KINDS, looks))               # e.g. healing -> "violet" this run
known = set()                                             # kinds identified so far this run
```

Using an item, a scroll of identify or a shop price can reveal its kind. Give at least one
cheap, low-risk way to identify, or players stop using unknown items at all.

## 6. Run state and profile state

- **Run state** (floor, HP, inventory, seed, RNG states, identification table): exists only
  during the run. For strict permadeath, delete or invalidate the run save as soon as it is
  loaded, and write it again on save-and-quit. Write it atomically (see `save-systems`).
- **Profile state** (unlocks, best scores, run history, meta currency, difficulty-ladder
  level): persists across deaths. This is what a roguelite spends on meta-progression.
- Keep them in separate files so a wiped run never touches the profile.
