# Puzzle board models and resolution (depth)

Detail behind `SKILL.md`. Engine-neutral pseudocode. Board coordinates are `(y, x)` with
`(0,0)` top-left and `y` growing downward (matches most tilemaps).

Contents:
1. Match-3 full resolution
2. Deadlock detection and reshuffle
3. Cascade scoring
4. Sokoban and push puzzles
5. Rule-based and logic puzzles
6. Undo strategies
7. Solvable generation and sliding-tile parity
8. Input locking and presentation

## 1. Match-3 full resolution

The resolution loop is: detect matches → score → clear → gravity → refill → repeat until stable.

```python
def apply_gravity(board):
    for x in range(W):
        # Compact non-empty cells downward within each column.
        column = [board[y][x] for y in range(H) if board[y][x] is not EMPTY]
        pad = [EMPTY] * (H - len(column))
        for y in range(H):
            board[y][x] = (pad + column)[y]      # empties on top, pieces settle to the bottom

def refill(board, rng):
    for y in range(H):
        for x in range(W):
            if board[y][x] is EMPTY:
                board[y][x] = random_piece(rng)  # seeded RNG for reproducibility
```

**Avoid spawning matches on refill** if you don't want free cascades: when filling, reject a
color that would immediately complete a line, or resolve those cascades intentionally as part
of scoring.

**Initial board:** generate so there are **no pre-existing matches** but **at least one valid
move** (see deadlocks). A common method: fill randomly, clear any starting matches, then verify
a move exists.

## 2. Deadlock detection and reshuffle (match-3)

A board with no possible matching move is a soft-lock. Detect it and react:

```python
def has_valid_move(board):
    # Try every adjacent swap; if any creates a match, a move exists.
    for y in range(H):
        for x in range(W):
            for dy, dx in ((0, 1), (1, 0)):
                if in_bounds(y+dy, x+dx):
                    swap(board, (y, x), (y+dy, x+dx))
                    ok = bool(find_matches(board))
                    swap(board, (y, x), (y+dy, x+dx))   # swap back
                    if ok: return True
    return False
# If not has_valid_move(board): reshuffle existing pieces (keep counts) until a move exists
# AND find_matches(board) is empty (a reshuffle must not hand out free matches), or end the
# level, depending on your rules. Cap the attempts and fall back to a fresh board.
```

## 3. Cascade scoring

Reward chains so deep setups feel great:

```python
def score_for(matches, chain):
    base = len(matches) * 10
    return base * chain            # linear in chain; or base * 2**(chain-1) for exponential
# Bonus for larger single matches (4 = line-clear piece, 5 = color bomb, etc.) is a common
# layer on top — special pieces created by 4+/5+ matches add strategy.
```

## 4. Sokoban / push puzzles

A different rule family: the player pushes blocks; the goal is to place blocks on targets.
Resolution is a legality check, not a cascade.

```python
def try_push(board, player, dir):
    ahead  = player + dir
    beyond = player + dir * 2
    if is_wall(board, ahead): return False
    if is_block(board, ahead):
        if is_wall(board, beyond) or is_block(board, beyond):
            return False                       # can't push two blocks or into a wall
        move_block(board, ahead, beyond)
    move_player(board, player, ahead)
    return True
# Win when every target cell holds a block. Undo is essential — sokoban is unforgiving.
# Detect dead states (a block pushed into a corner that isn't a target) to hint a restart.
```

## 5. Rule-based / logic puzzles

For logic grids (nonograms, sliding tiles, circuit/flow puzzles), the "resolution" is usually
just **validity + win check** after each move — no cascade. Keep the rule check pure and total:
given a board, return solved / unsolved / invalid. Undo and a clear "current constraints"
display matter more than animation here.

## 6. Undo strategies

| Strategy | Stores | Pros | Cons |
|----------|--------|------|------|
| Snapshot | full board + counters per move | trivial, exact | memory on big boards |
| Command | the move + inverse data | compact | must implement invert per rule |
| Redo stack | future snapshots/commands | redo support | extra bookkeeping |

Whatever you choose, undo must restore **everything** that affects play: board, score, moves
left, RNG state, and any special-piece state. Test undo by hashing full state before a move and
after undo — they must match.

## 7. Solvable generation

Generated levels must be solvable, or players hit unfair dead ends:

- **Generate-and-verify:** make a candidate, run a solver (BFS/DFS/A\* over board states for
  push/slide puzzles; move-existence for match-3); keep it only if solvable within the move/time
  budget. Use a seed so a level is reproducible.
- **Reverse generation:** start from a solved board and apply random *legal inverse* moves; the
  scrambled result is guaranteed solvable by reversing them. Great for sliding/sokoban puzzles
  (for sokoban the inverse move is a *pull*: the player steps back and drags the block).
- **Sliding-tile parity:** placing the tiles of an N×M sliding puzzle in a random order gives an
  unsolvable board exactly half the time. With the blank's goal in the bottom-right corner, count
  *inversions* (pairs of numbered tiles in the wrong order, reading row by row, ignoring the
  blank). Odd width: solvable iff inversions are even. Even width: solvable iff inversions plus
  the blank's row counted from the bottom (1 = bottom row) is odd. If a shuffle fails, swap any
  two numbered tiles to flip the parity.
- Tag each level with its seed and intended difficulty so progression curves are tunable and a
  bad level can be reproduced and fixed.

## 8. Input locking and presentation

The board model resolves instantly; animation plays the resolution out over time. **Lock input
until the board is stable** so the player can't act on a mid-cascade board. Drive visuals from
the sequence of state changes resolution produced (a list of clears/falls/spawns), not by
re-reading a half-updated board.
