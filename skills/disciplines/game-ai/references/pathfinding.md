# Pathfinding: A* in full

Contents:
1. Complete A* (engine-neutral Python) and its correctness points
2. Heuristics by movement type
3. Grid graph adapter (no corner cutting)
4. Admissibility self-test
5. When to use Godot `AStarGrid2D` or an engine navmesh instead
6. Performance notes

A* finds the shortest path on a **graph** (nodes + weighted edges). A grid is
just one kind of graph. The algorithm is the same whether nodes are tiles, rooms,
or navmesh polygons — only `neighbors()` and `cost()` change.

A* keeps a priority queue (the *frontier*) ordered by `f = g + h`, where `g` is
the known cost from the start and `h` is a heuristic estimate to the goal. It is
optimal **if** `h` never overestimates the true remaining cost (it is
*admissible*). With `h = 0`, A* degenerates to Dijkstra's algorithm.

## Complete A* (engine-neutral Python)

```python
import heapq, math

def heuristic(a, b):               # nodes are (x, y) tuples; see the table below
    dx, dy = abs(a[0] - b[0]), abs(a[1] - b[1])
    return (dx + dy) + (math.sqrt(2) - 2) * min(dx, dy)   # octile (8-way grid)

def a_star(graph, start, goal, h=heuristic):   # h=lambda a, b: 0 turns this into Dijkstra
    # Priority queue of (f_score, tie, node). heapq pops the SMALLEST first.
    frontier = [(0, 0, start)]
    came_from = {start: None}      # node -> node we reached it from
    cost_so_far = {start: 0.0}     # node -> best known g cost from start
    counter = 0                    # stable tie-breaker so heapq never compares nodes

    while frontier:
        _, _, current = heapq.heappop(frontier)
        if current == goal:
            break                  # early exit: we popped the goal, path is optimal

        for nxt in graph.neighbors(current):
            new_cost = cost_so_far[current] + graph.cost(current, nxt)
            # Relax: accept this edge only if it improves the best known cost.
            if nxt not in cost_so_far or new_cost < cost_so_far[nxt]:
                cost_so_far[nxt] = new_cost
                priority = new_cost + h(nxt, goal)           # f = g + h
                counter += 1
                heapq.heappush(frontier, (priority, counter, nxt))
                came_from[nxt] = current

    return came_from, cost_so_far

def reconstruct_path(came_from, start, goal):
    if goal not in came_from:
        return None                # unreachable
    path = []
    node = goal
    while node != start:
        path.append(node)
        node = came_from[node]
    path.append(start)
    path.reverse()                 # came_from points backward; flip to start->goal
    return path
```

Key correctness points:

- **Check the goal when *popping*, not when pushing.** Testing on push breaks as
  soon as edges have varying cost; testing on pop is always correct.
- **Relaxation** (`new_cost < cost_so_far[nxt]`) lets a node be improved if a
  cheaper route is found later — essential with non-uniform movement costs.
- **Tie-breaker**: push a monotonic counter alongside the node so the heap never
  has to order two equal-`f` nodes by the node object itself.

## Heuristics by movement type

| Allowed moves | Heuristic | Formula (`dx=|ax-bx|`, `dy=|ay-by|`) |
|---|---|---|
| 4-directional grid | Manhattan | `dx + dy` |
| 8-directional grid | Octile | `(dx + dy) + (sqrt(2) - 2) * min(dx, dy)` |
| Any-angle / Euclidean space | Euclidean | `sqrt(dx*dx + dy*dy)` |

Scale the heuristic by the minimum step cost so it stays in the same units as
`g`. If `h` can exceed the true cost, A* is faster but returns non-optimal paths
(this is the "weighted A*" trade-off — use it deliberately, not by accident).

## Grid graph adapter

```python
class GridGraph:
    def __init__(self, walls, width, height, diagonal=True):
        self.walls, self.w, self.h, self.diagonal = walls, width, height, diagonal
    def in_bounds(self, p): return 0 <= p[0] < self.w and 0 <= p[1] < self.h
    def passable(self, p):  return p not in self.walls
    def open(self, p):      return self.in_bounds(p) and self.passable(p)
    def neighbors(self, p):
        x, y = p
        result = [c for c in [(x+1,y),(x-1,y),(x,y+1),(x,y-1)] if self.open(c)]
        if self.diagonal:
            for dx, dy in [(1,1),(1,-1),(-1,1),(-1,-1)]:
                # No corner cutting: both orthogonal neighbours must be open too.
                if self.open((x+dx, y+dy)) and self.open((x+dx, y)) and self.open((x, y+dy)):
                    result.append((x+dx, y+dy))
        return result
    def cost(self, a, b):
        diagonal = a[0] != b[0] and a[1] != b[1]
        return math.sqrt(2) if diagonal else 1.0   # multiply by a terrain weight >= 1
```

The step costs must match the heuristic: octile assumes diagonal steps cost `sqrt(2)`.
If diagonals cost 1 the true distance is Chebyshev (`max(dx, dy)`) and octile
overestimates; on a 4-way grid (`diagonal=False`) switch the heuristic to Manhattan.
Terrain weights below 1 make any of these heuristics inadmissible.

## Admissibility self-test

Run this whenever the heuristic, step costs or terrain weights change. Dijkstra (`h = 0`) is
always optimal, so any grid where A* returns a higher cost means the heuristic overestimates.

```python
import random

def check_admissible(trials=50, size=20, wall_ratio=0.25, seed=1):
    rng = random.Random(seed)
    for _ in range(trials):
        walls = {(rng.randrange(size), rng.randrange(size))
                 for _ in range(int(size * size * wall_ratio))}
        start, goal = (0, 0), (size - 1, size - 1)
        walls -= {start, goal}
        graph = GridGraph(walls, size, size, diagonal=True)
        _, a_cost = a_star(graph, start, goal)
        _, d_cost = a_star(graph, start, goal, h=lambda a, b: 0.0)
        if goal in d_cost:
            assert abs(a_cost[goal] - d_cost[goal]) < 1e-9, (a_cost[goal], d_cost[goal])
    return True
```

## When to use an engine navmesh instead

Hand-rolled grid A* is ideal for 2D tile games and for understanding the
algorithm. For 3D worlds, arbitrary geometry, dynamic obstacle avoidance, and
agent radius/height, prefer the engine's baked navigation:

- **Unity** — bake a `NavMeshSurface` (AI Navigation package) and drive a
  `NavMeshAgent` (see `unity-navmesh`).
- **Unreal** — Nav Mesh Bounds + `AIController` MoveTo (see `unreal-behavior-trees`).
- **Godot** — `NavigationRegion2D/3D` + `NavigationAgent2D/3D`, querying
  `NavigationServer2D/3D` for paths. For a tile grid, the built-in `AStarGrid2D`
  already implements this file: set `region` and `cell_size`, set `diagonal_mode`
  (the default `DIAGONAL_MODE_ALWAYS` cuts wall corners) and the heuristics, call
  `update()`, and only then mark walls with `set_point_solid()` or
  `fill_solid_region()`, because `update()` clears every solid flag and weight. Read
  paths with `get_id_path(from, to)` or `get_point_path`; pass
  `allow_partial_path = true` to get the closest reachable cell instead of an empty
  array. `jumping_enabled` speeds searches up but ignores weight scales.

These handle path smoothing, off-mesh links, and crowd avoidance you would
otherwise reimplement. Use A* directly when the world is a discrete grid/graph or
when you need full control over the cost function.

## Performance notes

- Shrink the graph before optimizing the search: merge open areas, use waypoint
  graphs instead of dense grids, or precompute connected regions.
- Cap pathfinding work per frame (a budget of N searches), and queue the rest.
- For many agents heading to the same goal, compute one **flow field** (a
  Dijkstra pass from the goal outward) and have every agent follow the gradient,
  instead of running A* per agent.
