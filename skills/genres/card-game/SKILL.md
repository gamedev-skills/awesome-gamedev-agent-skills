---
name: card-game
description: >
  Designs card games and deckbuilders in any engine: cards as data with one effect interpreter,
  deck zones, a trigger stack and seeded shuffles. Use for a Slay the Spire- or Balatro-like or a
  TCG, or cards that duplicate or streaky shuffles. Pair with the engine skill for card data and
  hand UI (`godot-resources`, `godot-ui-control`, `unity-scriptableobjects`). Not for grid
  crawlers (`roguelike`).
---

# Card game

Owns the rules engine of a card game: zones, draw, costs, effect resolution, rewards and
balance math, including the run structure of a roguelike deckbuilder. Engine skills supply the
data assets and UI.

## When to use

- The core objects are cards moving between zones: deckbuilder, roguelike deckbuilder,
  TCG/CCG, solitaire, poker-hand scorer, card battler.
- Designing costs, draw, rewards, triggers, enemy intents or a scoring formula, or fixing
  cards that duplicate, vanish or resolve in the wrong order.

**When not to use:** grid dungeon runs (`roguelike`); board games with matching or pushing
rules (`puzzle`); an RPG with a small card minigame (start in `rpg`).

## Workflow

1. **Name the reference game and fix the frame.** Write the numbers down before any card:
   deck size, hand size, draw per turn, resource per turn, what happens to the hand at end of
   turn, copy limits. Reference frames are in the table below.
2. **Model zones and cards as data.** Every card instance has a unique id and lives in exactly
   one zone. Card text maps to a list of ops for one interpreter (Pattern 1).
3. **Pick the resolution model:** a stack (last in resolves first, for response-heavy TCGs) or
   a queue (first in first, simpler for PvE deckbuilders). Write the order for simultaneous
   triggers (active player first, then by timestamp).
4. **Write a power budget** for one resource and price every card against it (below).
5. **Build the reward loop** (deckbuilders): after each fight offer 3 cards, pick 1 or skip,
   with rarity weighted by act; give removal at shops or events.
6. **Check it.** Write and run these as tests and report the results:
   - 10,000 random legal turns with a bot: after every action each card id appears in exactly
     one zone and the total count never changes;
   - shuffle uniformity: shuffle a 4-card deck 24,000 times; each of the 24 orders should
     land near 1,000 (a chi-square statistic above about 41 at 23 degrees of freedom means
     bias, p < 0.01);
   - same seed and same inputs replay to the same final state hash;
   - a trigger loop (A draws when B is drawn, B when A) stops at the depth cap with a log line;
   - a greedy bot plays the starter deck for 1,000 turns; print damage and block per turn and
     size the first enemies from it (about 3-4 turns of starter damage is a common start).

## Reference frames

| Game | Deck | Hand and draw | Resource | End of turn |
|------|------|---------------|----------|-------------|
| Slay the Spire | 10-card starter (Ironclad: 5 Strike, 4 Defend, Bash) | draw 5 | 3 energy | discard hand |
| Balatro | 52 playing cards | hand size 8, play up to 5 | 4 hands, 3 discards per blind | redraw to 8 |
| Hearthstone | 30 cards | hand cap 10, extra draws are destroyed | mana 1 to 10, +1 per turn | keep hand |
| Magic: the Gathering | 60+ constructed, 40+ limited, max 4 copies | 7-card opening hand, draw 1 | lands | discard to 7 |

Balatro's run is 8 antes of three blinds (small 1x, big 1.5x, boss mostly 2x the ante's base
score). Slay the Spire's enemies show their next action (intent), which is what makes a PvE
card game a planning puzzle rather than a guess. Copy the idea, never the cards.

## Power budget and deck math

- **Budget per resource.** Pick a baseline and price everything against it. Slay the Spire's
  starters set 1 energy = 6 damage (Strike) or 5 block (Defend), and an upgrade adds about
  half again (Strike+ deals 9). Rares may exceed the budget; zero-cost cards need a drawback
  or a small effect.
- **Every added card dilutes the deck.** The chance a specific single card is in a 5-card
  hand is 5/deck size: 50% in a 10-card deck, 33% at 15, 25% at 20. That is why skipping a
  reward or removing a Strike is often the strongest pick, and why removal belongs in the
  reward economy.
- **Copies in constructed.** A 4-of in a 60-card deck is in the opening 7 about 40% of the
  time and in the first 10 cards about 53% (hypergeometric). Use the same formula to tune
  any draw consistency.
- **Cycle time** is deck size / draw per turn: a 10-card deck drawing 5 sees every card every
  2 turns. Draw and deck thinning shorten it; that is where infinite combos come from.
- **Scoring pipelines** (Balatro-style): fix the order and write it down, for example base
  chips, then added chips, then added mult, then multiplying mult, applied left to right in
  slot order. Additive and multiplicative stages in the wrong order change scores by orders
  of magnitude.

## Pattern 1: zones, draw and play

```python
# Pseudocode. One zone per card instance; moving = remove from one list, append to another.
def draw(player, n):
    for _ in range(n):
        if not player.draw_pile:
            if not player.discard:
                return on_empty_draw(player)    # deck-out loss, fatigue, or simply stop
            player.draw_pile = player.discard; player.discard = []
            shuffle(player.draw_pile, player.rng)            # seeded Fisher-Yates (refs §6)
        card = player.draw_pile.pop()
        if len(player.hand) >= HAND_CAP:
            move(card, to=player.discard); log("burned", card)   # define overdraw explicitly
        else:
            player.hand.append(card)

def play(card, player, targets):
    if player.energy < cost(card) or not legal(card, targets):
        return False                                         # nothing changed yet
    player.energy -= cost(card)
    move(card, frm=player.hand, to=player.limbo)             # in play while resolving
    for op in card.ops:
        push_effect(op, Ctx(player, card, targets))
    resolve_stack()                                          # refs §2
    move(card, frm=player.limbo, to=destination(card))       # discard, exhaust, board
    return True
```

Holding the card in a "limbo" zone while it resolves keeps a draw effect from reshuffling the
card that is being played back into the draw pile.

## Gotchas

- **A card in two zones, or gone** → move done as add-then-remove, or removing by value when two
  copies exist. Give every instance an id and assert the invariant after each action.
- **Draw effect shuffles the played card back in** → the card went to discard before its
  effects resolved. Resolve from a limbo zone (Pattern 1).
- **Triggers loop forever** → A triggers B triggers A. Cap resolution depth (for example 100
  pushes per action), stop with a log line, and add a test for the known loop.
- **Order changes between runs** → triggers collected from a hash map or unordered set. Sort
  by a fixed key (controller, then timestamp) before pushing.
- **Biased shuffle** → sort with a random comparator, or swap with any index instead of
  `0..i`. Use Fisher-Yates with an inclusive upper bound and check the engine's range
  convention (refs §6).
- **Replays and undo drift** → shuffle uses the engine's global RNG, which particles and AI
  also consume. Give the deck its own seeded generator and save its state.
- **"The shuffle is streaky"** → players misread true randomness. A shuffled deck is already a
  bag randomiser; resist hidden pity rules in deck draws, and add visible tools instead
  (scry, mulligan, retain).
- **Cancelled targeting leaves the board half-changed** → paid before validating. Validate
  cost and targets first, then commit (Pattern 1).
- **Starter deck dies to the first fight or trivialises act 1** → enemy HP set by feel. Size it
  from the bot's measured damage per turn (Workflow step 6).

## References

- `references/effect-resolution.md`: read when writing the op interpreter, the stack or queue,
  triggers and keywords, targeting and fizzle rules, deckbuilder versus constructed structure,
  shuffle code and per-engine RNG calls, or cost curves.

Related: `godot-resources` or `unity-scriptableobjects` (card data assets), `game-ui-ux` with
`godot-ui-control` (hand layout, drag and targeting UI), `save-systems` (run and collection
saves), `game-ai` (opponent choice), `game-feel` (card hover, play and hit feedback).

## Version notes

Last verified: 2026-11-11.

- Slay the Spire Ironclad starter deck and 2-turn cycle time:
  https://slaythespire.wiki.gg/wiki/Slay_the_Spire_2:Ironclad and
  https://sts2.untapped.gg/en/articles/core-deckbuilding-concepts-in-slay-the-spire
  (the same 10-card starter in the first game and in Slay the Spire 2).
- Balatro blinds and antes: https://balatrowiki.org/w/Blinds_and_Antes.
- Hearthstone hand cap and overdraw: https://hearthstone.wiki.gg/wiki/Hand.
- Magic deck limits: Comprehensive Rules section 100.2 (https://magic.wizards.com/en/rules).
- Hypergeometric figures computed with `math.comb` (60 cards, 4 copies: 39.9% in 7, 52.8% in 10).
- Per-engine RNG calls in the reference were checked for Godot 4.7, Unity 6.3 and Phaser 4.
