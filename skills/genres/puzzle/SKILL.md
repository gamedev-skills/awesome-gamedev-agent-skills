---
name: puzzle
description: >
  Designs grid and logic puzzle games in any engine: match-3 cascades, Sokoban pushing,
  unique-solution grids (nonogram, Sudoku), exact undo and solver-checked levels. Use for a Candy
  Crush-like, Sokoban or Picross, or broken cascades, drifting undo or unsolvable levels. Not for
  physics puzzlers (`platformer`, `physics-tuning`) or card games (`card-game`).
---

# Puzzle

Owns discrete board puzzles: the rules engine, resolution order, undo, solvability and level
difficulty. The board model is the only truth; the view replays the list of changes each move
produced.

## When to use

- The player changes a discrete board with moves and the board resolves by rules: matching,
  pushing, sliding, merging, or pure logic deduction.
- Writing a solver or generator, ordering levels by difficulty, fixing undo or soft-locks.

**When not to use:** physics-driven puzzles and puzzle platformers (`platformer`,
`physics-tuning`); turn-based dungeon runs (`roguelike`); card zones (`card-game`).

## Workflow

1. **Model the board as plain data** (grid of cell values plus counters and RNG state) with a
   pure `apply(state, move) -> (state, events)` function. The view animates `events`.
2. **Write the rule resolver** for the family (below) and loop until stable where rules cascade.
3. **Undo from day one:** push a snapshot (or invertible command) before every move, including
   score, move counters and RNG state. Add restart, which thinky puzzles need as much as undo.
4. **Write a solver early** (BFS or A* over states for push and slide puzzles, a line or
   constraint solver for logic grids, move-existence for match-3). It validates every level,
   measures difficulty and powers hints.
5. **Order levels by measured difficulty,** introducing one mechanic at a time: a level that
   teaches it alone, a level that tests it, then one that combines it with a known mechanic.
6. **Check it.** Run these in the project's test runner and report the numbers:
   - the solver solves every shipped level; print minimum moves and states explored per level
     and flag levels whose order disagrees with difficulty;
   - logic grids: the solver finds exactly one solution without guessing;
   - undo: hash the full state, make a random move, undo, and compare hashes (1,000 times);
   - match-3: 10,000 random boards after generation have no ready-made match and at least one
     valid move;
   - input during a resolving cascade is ignored or queued, never applied mid-resolution.

## Rule families and numbers

| Family | Rules that matter | Starting numbers |
|--------|------------------|------------------|
| Match-3 | 4 in a line makes a line-clear piece, an L or T of 5 makes an area bomb, 5 in a line makes a colour bomb (Candy Crush naming) | 8x8 or 9x9 board, 5-6 colours (fewer colours, more cascades), hint after about 5 s idle |
| Push (Sokoban) | push one box, never pull; dead squares (non-goal corners, wall edges with no goal) | difficulty from minimum pushes and states explored, not board size |
| Slide (15-puzzle) | half of random arrangements are unsolvable | check inversion parity (refs §7) |
| Merge (2048) | slide, merge equal neighbours once per move, then spawn | the original spawns a 2 with 90% chance and a 4 with 10% |
| Logic grids | exactly one solution, reachable by deduction alone | grade difficulty by the hardest deduction rule the solver needed |
| Rule-changing (Baba Is You style) | rules are board objects; re-derive the rule set after every move, before win checks | test every rule word against every object type |

No-guess generation is standard for logic puzzles: Simon Tatham's Mines, for example,
ensures by default that the whole grid can be deduced from the first opening.

## Pattern 1: resolve to stability (match-3)

```python
def resolve(board, rng):
    events, chain = [], 0
    while True:
        matches = find_matches(board)              # runs of 3+, rows and columns
        if not matches:
            break
        chain += 1
        specials = specials_from(matches)          # decide BEFORE clearing (shape and swap cell)
        events.append(("clear", matches, chain))
        clear(board, matches); place(board, specials)
        events.append(("fall", apply_gravity(board)))
        events.append(("spawn", refill(board, rng)))   # seeded RNG, saved in undo snapshots
    if not has_valid_move(board):
        events.append(("shuffle", reshuffle_until_playable(board, rng)))
    return events
```

## Gotchas

- **Cascades miss matches** → resolution ran once. Loop until no matches (Pattern 1).
- **Special piece appears in the wrong cell** → specials decided after clearing. Decide from
  the match shape and the swapped cell first.
- **Undo rerolls the refill** → RNG state not in the snapshot; players learn to undo for better
  pieces. Snapshot board, score, counters and RNG state together.
- **Visuals desync from the board** → animation code reads a half-updated board. Animate the
  event list; lock or queue input until it finishes.
- **Soft-lock with no moves** → no deadlock check. Detect and reshuffle (keep piece counts, no
  free matches) or end the level.
- **Unsolvable generated level** → random scramble with no check. Generate backwards from the
  solved state with inverse moves (pull for Sokoban), or generate and solve, with the seed kept.
- **Two valid answers in a logic grid** → generator never checked uniqueness. Run the solver
  for a second solution and reject or add a clue.
- **Difficulty jumps** → levels ordered by designer guess. Order by solver effort and teach one
  mechanic at a time.
- **Box pushed into a dead corner with no hint** → no dead-square detection. Precompute dead
  squares and offer restart or flag them.

## References

- `references/board-and-resolution.md`: read when writing match-3 gravity, refill and
  deadlock code, cascade scoring, Sokoban pushing, logic-grid validity checks, undo strategies,
  solvable generation and sliding-tile parity, or input locking during animation.

Related: `level-design` (teaching order), `procedural-gen` (seeded generators), `save-systems`
(progress, daily seeds), `game-feel` (match pops, chain feedback), `godot-tilemap` or
`unity-tilemap-2d` (board rendering).

## Version notes

Last verified: 2026-11-11.

- 2048 spawn odds: `Math.random() < 0.9 ? 2 : 4` in
  https://github.com/gabrielecirulli/2048/blob/master/js/game_manager.js.
- Simon Tatham's Mines "Ensure solubility" option, on by default:
  https://www.chiark.greenend.org.uk/~sgtatham/puzzles/doc/mines.html.
- Match-3 board size, colour count and hint delay are common practice, not measured.
