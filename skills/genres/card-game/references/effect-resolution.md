# Card effect resolution and structure (depth)

Detail behind `SKILL.md`. Engine-neutral pseudocode. Models how card effects resolve, how
triggers stack, and how deck construction shapes the game.

Contents:
1. Effects as data and an interpreter
2. The resolution queue or stack
3. Triggers and keywords
4. Targeting
5. Deckbuilder versus constructed
6. Shuffle fairness and per-engine RNG calls
7. Mana and resource curves

## 1. Effects as data + an interpreter

Define a small vocabulary of **operations**; every card is a list of them. Adding a card means
adding data, not code. This keeps cards testable and prevents per-card spaghetti.

```python
# A handful of ops cover most card games. Extend deliberately.
OPS = {
    "damage":     lambda fx, ctx: deal_damage(ctx.target(fx), fx["amount"]),
    "heal":       lambda fx, ctx: heal(ctx.target(fx), fx["amount"]),
    "draw":       lambda fx, ctx: ctx.owner.draw(fx["amount"]),
    "gain_res":   lambda fx, ctx: add_resource(ctx.owner, fx["amount"]),
    "summon":     lambda fx, ctx: summon(ctx.owner, fx["unit_id"]),
    "buff":       lambda fx, ctx: add_modifier(ctx.target(fx), fx["mod"]),
    "destroy":    lambda fx, ctx: move_to_discard(ctx.target(fx)),
}
def resolve_effect(fx, ctx):
    OPS[fx["op"]](fx, ctx)
```

## 2. The resolution queue / stack

When effects can trigger other effects (e.g. "when a creature dies, draw a card"), resolve
through an explicit structure so order is deterministic:

- **Queue (FIFO):** effects resolve in the order they were added. Intuitive for simple games.
- **Stack (LIFO):** the most recently added effect resolves first — this is how trading card
  games model "responses" (the last thing said happens first). Choose one and document it.

```python
# Stack model (pseudocode): pushing during resolution lets responses resolve first.
stack = []
def push_effect(fx, ctx): stack.append((fx, ctx))
MAX_PUSHES = 100                       # per player action; stops A-triggers-B-triggers-A loops
def resolve_stack():
    pushes = 0
    while stack:
        fx, ctx = stack.pop()          # LIFO: last in resolves first
        resolve_effect(fx, ctx)        # may push more (triggers) -> they resolve next
        pushes += 1
        if pushes > MAX_PUSHES:
            stack.clear(); log("trigger loop stopped", fx); break
```

Decide simultaneity rules up front: when several triggers fire at once, order them by a fixed
rule (active player first, then by timestamp) so outcomes are reproducible.

## 3. Triggers and keywords

- **Triggers:** "when X happens, do Y" (on-play, on-death, on-draw, start/end of turn). Register
  listeners by event; when the event fires, push the triggered effects onto the queue/stack.
- **Keywords:** named, reusable abilities (e.g. taunt/guard, lifesteal, poison/DoT, shield).
  Implement each once as a modifier or trigger and tag cards with it — never re-implement per card.

```python
# Event bus (pseudocode): triggers subscribe; effects fire when the event is published.
on("creature_died", lambda ev: [push_effect(t, ctx_for(t)) for t in triggers_for("on_death", ev)])
```

## 4. Targeting

- Resolve targets at the moment of resolution (or at play, per your rules) and **validate** them
  — a target may have left the zone or died before the effect resolves; define "fizzle" behavior.
- Make playing a card **atomic**: validate cost + legal targets first, then pay and commit. A
  cancelled or illegal play must leave zones exactly as they were.

## 5. Deckbuilder vs. constructed

| | Constructed (TCG/CCG) | Deckbuilder (in-run) |
|---|---|---|
| Deck built | Before the game, from a collection | During play (draft/buy cards) |
| Variance | Mulligans, draw order | Reshuffle of a growing deck each "shuffle" |
| Power growth | Fixed deck | Deck thins/grows; combos emerge mid-run |
| Persistence | Collection + decklists | Run state plus a profile of unlocks |

In a roguelike deckbuilder, the deck *is* the build: adding/removing cards mid-run is the core
progression. Keep run state separate from any meta-collection (see `save-systems`); the run
map (paths of fights, elites, shops, rests, events) and post-win difficulty ladders work as in
any roguelite, but the deck itself is the character sheet.

## 6. Shuffle fairness and consistency

- Use a correct **Fisher–Yates** shuffle. Two common hand-rolled versions are biased: sorting
  with a random *comparator* (`sort(cmp=random)`), and swapping each index with any index
  `0..n-1` instead of `0..i`. Both make some deck orders more likely than others.
- Watch the range convention of the RNG call you use (table below). Picking `j` from `0..i-1`
  instead of `0..i` gives Sattolo's algorithm, which never leaves a card in place: also biased.
- Seed the RNG if you want reproducible runs, replays, or deterministic undo, and save the
  generator's **state** (not just the seed) with the run so a reload continues the same sequence.
- A small-state PRNG cannot reach every order of a large deck (52 cards have about 2^226
  orderings; a 64-bit state reaches at most 2^64). That is fine for games; it only matters if you
  promise "every shuffle equally likely" for money or tournaments.
- For digital games, players perceive true-random as "streaky". Some games use a *pity* /
  smoothing system (e.g. bound how long before a needed resource appears). Decide intentionally;
  document it so balance math accounts for it.

```python
def shuffle(cards, rng):                 # Fisher–Yates
    for i in range(len(cards) - 1, 0, -1):
        j = rng.int_inclusive(0, i)      # j in 0..i, both ends included
        cards[i], cards[j] = cards[j], cards[i]
```

| Engine | Seedable generator | Integer in `0..i` inclusive | Built-in shuffle |
|--------|--------------------|-----------------------------|------------------|
| Godot 4.7 | `RandomNumberGenerator` (`seed`, `state`) | `rng.randi_range(0, i)` | `Array.shuffle()` uses the **global** seed, not your instance |
| Unity 6.3 | `System.Random` or `Unity.Mathematics.Random` per run | `rnd.Next(0, i + 1)` / `UnityEngine.Random.Range(0, i + 1)` (max exclusive) | none |
| Phaser 4 | `new Phaser.Math.RandomDataGenerator([seed])` (`state()`) | `rnd.between(0, i)` | `rnd.shuffle(array)` (uses that generator) |

`UnityEngine.Random` is one global generator; anything else that calls it (particles, AI)
consumes values and breaks replay. Give the deck its own generator instance.

## 7. Mana / resource curves

- The **resource curve** (how much you can spend by turn N) paces power. Cheap cards early,
  expensive payoffs later.
- A deck's **cost distribution** (its "curve") determines consistency: too top-heavy and you
  can't act early; too cheap and you run out of gas. Balance card power against cost so a
  higher cost reliably buys more impact, with rarer cards bending the rule.
