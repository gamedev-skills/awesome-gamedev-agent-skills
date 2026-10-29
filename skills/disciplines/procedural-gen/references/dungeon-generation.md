# Dungeon and level generation

Four families cover most 2D level generation. All write into a plain grid
(`0 = wall`, `1 = floor`, or tile ids for WFC) that a tile pass renders later.
All take a seeded RNG.

## A. Rooms and corridors

Simple, readable, gives recognizable rooms. Place rectangles, then connect.

```python
def generate(W, H, rng, attempts=200, rmin=4, rmax=9):
    grid = [[0]*W for _ in range(H)]          # 0 = wall
    rooms = []
    for _ in range(attempts):
        w = rng.randint(rmin, rmax); h = rng.randint(rmin, rmax)
        x = rng.randint(1, W - w - 1); y = rng.randint(1, H - h - 1)
        new = (x, y, w, h)
        if any(_overlap(new, o, pad=1) for o in rooms):
            continue                          # keep at least one tile between rooms
        _carve_room(grid, new)
        if rooms:                             # connect to the previously placed room
            (cx, cy), (px, py) = _center(new), _center(rooms[-1])
            _carve_h(grid, px, cx, py)        # horizontal leg
            _carve_v(grid, py, cy, cx)        # vertical leg -> L-shaped corridor
        rooms.append(new)
    return grid, rooms
```

For more interesting connectivity than "chain the rooms", connect rooms via a
minimum spanning tree of their centers, then add a few extra edges for loops.

## B. BSP (binary space partitioning)

Splits space recursively, guaranteeing rooms never overlap and tile the map. Good
for structured, building-like dungeons.

```python
def bsp(node, rng, depth, min_size=8):
    if depth == 0 or (node.w < min_size*2 and node.h < min_size*2):
        node.room = _random_room_inside(node, rng)   # leaf: place one room
        return
    if node.w > node.h:                               # split the longer axis
        cut = rng.randint(min_size, node.w - min_size)
        left, right = node.split_vertical(cut)
    else:
        cut = rng.randint(min_size, node.h - min_size)
        left, right = node.split_horizontal(cut)
    bsp(left, rng, depth-1, min_size); bsp(right, rng, depth-1, min_size)
    node.children = (left, right)
    _connect(left.room_or_subroom(), right.room_or_subroom(), rng)  # join siblings
```

Connect siblings as the recursion unwinds, so every region links to its sibling
and the whole tree stays connected.

## C. Random-walk / cellular caves

Organic caverns. Either carve with a drunkard's walk, or seed noise then smooth
with cellular automata.

```python
# Drunkard's walk: a digger wanders, carving floor, until enough is open.
def drunkard(W, H, rng, target_ratio=0.45, max_steps=None):
    if W < 3 or H < 3 or not 0 <= target_ratio <= 1:
        raise ValueError("need W,H >= 3 and target_ratio in [0,1]")
    goal = int(W*H*target_ratio)             # fraction of the whole map, including its border
    capacity = (W-2)*(H-2)
    if goal > capacity:
        raise ValueError("target exceeds the carveable interior")
    if max_steps is None:
        max_steps = capacity * 100
    if max_steps < 0:
        raise ValueError("max_steps must be non-negative")
    grid = [[0]*W for _ in range(H)]
    x, y = W//2, H//2; carved = 0
    for _ in range(max_steps):
        if carved == goal: return grid
        if grid[y][x] == 0: grid[y][x] = 1; carved += 1
        dx, dy = rng.choice([(1,0), (-1,0), (0,1), (0,-1)])
        x = min(max(x + dx, 1), W-2)        # cardinal steps keep carved floor 4-connected
        y = min(max(y + dy, 1), H-2)
    if carved < goal:
        raise RuntimeError("target not reached within max_steps")
    return grid

# Cellular automata smoothing: a cell becomes wall if most neighbors are walls.
def smooth(grid, W, H, steps=4):
    for _ in range(steps):
        new = [row[:] for row in grid]
        for y in range(1, H-1):
            for x in range(1, W-1):
                walls = sum(1 for dy in (-1,0,1) for dx in (-1,0,1)
                            if grid[y+dy][x+dx] == 0)
                new[y][x] = 0 if walls >= 5 else 1   # 5/9 majority rule
        grid = new
    return grid
```

`target_ratio` counts the whole map; the solid border cannot be carved. Impossible
targets fail immediately. A feasible target can still exhaust the random walk's
step budget: report that failure or retry with an explicit new seed/budget rather
than treating a partial cave as a finished map. Smoothing can split regions, so
validate connectivity again after applying it.

## D. Wave function collapse (tile adjacency rules)

WFC fills a grid so every pair of neighbours obeys adjacency rules you give it
(simple-tiled model). Each cell starts with every tile possible; repeat:
**observe** the undecided cell with the fewest options, **collapse** it to one
tile by weight, then **propagate** — shrink neighbours to tiles still compatible,
spreading until nothing changes. An empty cell is a contradiction: restart (or
backtrack).

```python
DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1)]          # +x, -x, +y, -y

def wfc(W, H, weights, allowed, rng, max_restarts=20):
    """weights: {tile: weight}; allowed[(tile, d)]: tiles that may sit in DIRS[d] of tile."""
    for _ in range(max_restarts):
        cells = [[set(weights) for _ in range(W)] for _ in range(H)]
        failed = False
        # Validate the initial domains too: singleton grids still have adjacency constraints.
        stack = [(x, y) for y in range(H) for x in range(W)]
        while not failed:
            # Propagate: shrink neighbours to tiles some remaining option still allows.
            while stack and not failed:
                cx, cy = stack.pop()
                for d, (dx, dy) in enumerate(DIRS):
                    nx, ny = cx + dx, cy + dy
                    if not (0 <= nx < W and 0 <= ny < H):
                        continue
                    support = set().union(*(allowed[(t, d)] for t in cells[cy][cx]))
                    narrowed = cells[ny][nx] & support
                    if narrowed != cells[ny][nx]:
                        if not narrowed:
                            failed = True                # contradiction: restart
                            break
                        cells[ny][nx] = narrowed
                        stack.append((nx, ny))
            if failed: break
            # Observe only after propagation, including on the first iteration.
            open_cells = [(len(cells[y][x]), x, y) for y in range(H) for x in range(W)
                          if len(cells[y][x]) > 1]
            if not open_cells:
                return [[next(iter(c)) for c in row] for row in cells]
            fewest = min(n for n, _, _ in open_cells)
            _, x, y = rng.choice([c for c in open_cells if c[0] == fewest])
            opts = sorted(cells[y][x])                   # sorted: set order is not stable
            cells[y][x] = {rng.choices(opts, [weights[t] for t in opts])[0]}
            stack = [(x, y)]
    raise RuntimeError("no solution within max_restarts")
```

- Author symmetric rules: if B may sit east of A, A must be allowed west of B.
  Both directed constraints are propagated; conflicting rules can make the grid unsatisfiable.
- Option count is the simplest "entropy"; the weighted Shannon entropy of the
  remaining options is the usual refinement. Either way the grid grows outward
  from the first collapse, so tile **weights** decide the overall mix.
- Pre-collapse fixed cells (border = wall, an entrance tile) and propagate from
  them before the loop to steer layouts.
- WFC guarantees local rules only. Run the connectivity check below on the
  result like any other generator.

## Connectivity validation (do this every time)

Generation can isolate regions. Flood-fill from the spawn; if floor tiles remain
unreached, either discard the map, dig a tunnel to the nearest reached tile, or
keep only the largest region.

```python
def reachable_floor(grid, start):    # assumes a solid wall border (no bounds checks)
    seen, stack = set(), [start]
    while stack:
        x, y = stack.pop()
        if (x, y) in seen or grid[y][x] == 0: continue
        seen.add((x, y))
        stack += [(x+1,y),(x-1,y),(x,y+1),(x,y-1)]
    return seen        # compare len(seen) to total floor count; reconnect the rest
```

Also validate: a path from spawn to exit exists (reuse `game-ai` A*), the spawn
tile is safe, and key items aren't behind locks they themselves gate.

## Distribution control for loot/spawns

Pure weighted rolls produce streaks (ten commons in a row). Two fixes:

- **Bag / deck**: fill a bag with items in proportion to weights, shuffle, draw
  without replacement, refill when empty. Guarantees the rate over a window.
- **Pity timer**: track rolls since the last rare; once a threshold is passed,
  force or boost the rare's chance. Common in gacha/loot systems.

Keep these in the seeded RNG too, so drop sequences stay reproducible.
