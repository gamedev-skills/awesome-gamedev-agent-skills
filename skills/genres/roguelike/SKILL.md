---
name: roguelike
description: >
  Designs run-based roguelikes and roguelites in any engine: run structure, permadeath,
  meta-progression, seeded and daily runs, turn order and symmetric field of view. Use for
  NetHack- or Hades-style games, or runs that feel cheap. Pair with `procedural-gen` for dungeon
  generation and `save-systems` for run vs meta saves. Not for roguelike deckbuilders
  (`card-game`).
---

# Roguelike

Owns the run: what a run contains, what survives death, how turns and seeds work, and what a
generated floor must guarantee. The generators come from `procedural-gen`; this skill decides
what they must produce and checks it.

## When to use

- A game where each run starts fresh, death ends it, and content is regenerated: a
  traditional turn-based grid roguelike or a real-time roguelite.
- Deciding permadeath versus meta-progression, run length and act structure, seeds and daily
  runs, turn scheduling, or FOV.

**When not to use:** the algorithm that carves rooms or caves, noise, WFC or loot-table rolling
(`procedural-gen`); deckbuilders such as Slay the Spire or Balatro, even roguelike ones
(`card-game`); persistent-character RPGs (`rpg`). For a real-time roguelite also load the
action genre skill (`platformer`, `fps-shooter`) for moment-to-moment control.

## Workflow

1. **Settle the type with the user.** Traditional (turn-based, grid, strict permadeath, runs
   of hours, knowledge is the progression) or roguelite (real-time or turn-based, runs of
   20-60 minutes, some power or options persist). The Berlin Interpretation (RogueBasin, 2008)
   lists the traditional traits; use it as a vocabulary, not a checklist.
2. **Lay out the run.** 3-4 acts or biomes, each ending in a boss or gate, with a choice
   between paths or rewards at least every few minutes. Plan a first death around 5-15
   minutes in for a new player, and make the death screen show the seed, depth, cause and
   what was unlocked.
3. **Split state** into run state (wiped on death) and profile state (kept). Decide strict
   permadeath (delete the run save on load) or checkpointed runs, and write the rule down.
4. **Seed everything** from one run seed with per-floor, per-purpose sub-seeds (refs §2).
5. **Turn order** (turn-based games): energy scheduler (Pattern 1) with a few discrete speeds.
6. **Generate floors with `procedural-gen`,** then gate each floor with the acceptance checks
   (refs §1) and the spawn budget (refs §4).
7. **Check it.** Write and run these as tests in the project's runner and report the numbers:
   - same seed twice gives the same hash for floors 1 to N, even after playing floor 1
     differently between the two runs;
   - 500+ seeds per depth pass the acceptance checks, with the reject rate printed;
   - FOV symmetry on random maps (refs §3);
   - speeds 50/100/200 over 1,000 time units give turns in a 1:2:4 ratio;
   - dying deletes or invalidates the run save and leaves the profile file unchanged.

## Design rules and numbers

| Decision | Start here | Why |
|----------|-----------|-----|
| Speeds | 50, 100, 200 (slow, normal, fast) | odd ratios such as 110 give an unexplained extra enemy move every tenth turn |
| Action cost | 100 energy for move, attack and item use | change cost per action (heavy attack 150) rather than adding speeds |
| FOV radius | 6-9 tiles; lit rooms fully visible | small radius adds tension and cuts tactics |
| Out-of-depth spawn | about 5% of spawns, up to 3 levels deeper | rare spikes stay memorable |
| Safe start | no monster within 6-8 tiles of the arrival point | the first turn must not decide the run |
| Meta-progression | new options (characters, items in the pool, starting choices) before flat stat boosts | flat boosts make early acts trivial and turn runs into a grind |
| After the first win | a stacking difficulty ladder (Slay the Spire's Ascension, Hades' Heat) | gives experts a reason to keep playing |
| Daily run | one seed per UTC day, one attempt, shared leaderboard | comparable runs need identical seeds |

## Pattern 1: energy scheduler

```python
# Pseudocode. Actors gain energy each time unit and act when they have enough.
TURN_COST = 100
def next_actor(actors):
    while True:
        for a in actors:                 # 1) serve anyone already ready, in a stable order
            if a.energy >= TURN_COST:
                a.energy -= TURN_COST    #    or the chosen action's cost
                return a
        for a in actors:                 # 2) nobody ready: advance time for everyone at once
            a.energy += a.speed          #    100 = normal, 200 = hasted, 50 = slowed
```

Grant energy in its own pass. Adding it inside the loop that returns the first ready actor
starves everyone after it: with two speed-100 actors the first acts every time.

## Gotchas

- **Same seed, different floor 3** → one RNG shared by generation and combat, so the number of
  attacks on floor 1 shifts later floors. Derive a sub-seed per floor and per purpose (refs §2).
- **Seeds differ between runs of the same build** → seeding from a language `hash()` of a
  string (Python randomises it per process) or iterating an unordered set while generating.
  Hash with a fixed algorithm and iterate in sorted order.
- **One monster never acts** → energy granted inside the "find who is ready" loop (Pattern 1).
- **Double moves or input races** → a real-time loop pretending to be turn-based. Resolve one
  discrete player action, then let the scheduler run until the player is ready again.
- **You see the monster, it does not see you** → classic or ray-cast FOV. Use symmetric
  shadowcasting (python-tcod: `compute_fov(..., algorithm=tcod.constants.FOV_SYMMETRIC_SHADOWCAST)`).
- **Stairs behind an unreachable wall, or the key locked behind its own door** → generator
  output accepted without checks (refs §1).
- **Deaths feel unfair** → damage the player could not see coming. Show enemy intent or
  telegraph big hits, and log every damage source in the message log.
- **Permadeath wipes unlocks** → run and profile in one save. Separate them (refs §6).
- **Save-scumming** → the run save survives a load. Delete or invalidate it on load if strict
  permadeath is the design; copying save files cannot be prevented, so do not try.
- **Identification knowledge carries between runs** → fixed appearance names. Shuffle them per
  run (refs §5).

## References

- `references/run-seeds-fov.md`: read when writing floor acceptance checks, sub-seed and
  daily-seed code, symmetric shadowcasting, spawn budgets, per-run identification, or the
  run and profile save split.

Related: `procedural-gen` (generators, noise, loot tables), `save-systems` (atomic writes,
versioning), `game-ai` (monster behaviour), `godot-tilemap` or `unity-tilemap-2d` (grid
rendering), `game-feel` (impact feedback).

## Version notes

Last verified: 2026-11-11.

- python-tcod 21.2.3 (PyPI): `tcod.constants.FOV_SYMMETRIC_SHADOWCAST = 13`, accepted by
  `tcod.map.compute_fov(..., algorithm=...)` (https://python-tcod.readthedocs.io/en/latest/tcod/map.html).
- Berlin Interpretation: https://www.roguebasin.com/index.php/Berlin_Interpretation (2008).
- Symmetric shadowcasting: Albert Ford, 2021, https://www.albertford.com/shadowcasting/.
