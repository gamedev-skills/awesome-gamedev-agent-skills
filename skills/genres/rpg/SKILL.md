---
name: rpg
description: >
  Designs RPG progression and combat numbers in any engine: stats with a modifier stack, XP
  curves, damage formulas, items and equipment (slots, rarity, affixes) and quests. Use for a JRPG
  or Diablo-style looter, or stats wrong after unequipping. Pair with `save-systems` to save
  characters and inventory. Not for crafting and carry weight (`survival-crafting`) or dialogue
  (`dialogue-systems`).
---

# RPG

Owns the numbers that make a character grow: stats, levels, damage, items and quests. Design by
target outcomes (minutes per level, hits to kill), then derive formulas and tables from them,
and check the tables with a script before anyone plays.

Works with any engine, including custom ones: bind the data shapes below to the project's
content format and save interface after reading its existing items and stats.

## When to use

- Character progression, combat math, item and equipment systems, loot rarity, quest tracking.
- Symptoms: buff or gear removal leaves the wrong stats, defense stacking makes enemies
  immune, damage numbers explode late, players out-level content, loot is all "+1%".

**When not to use:** gathering, crafting recipes, stack limits, weight and spoilage
(`survival-crafting`); conversation trees and barks (`dialogue-systems`); save file format and
migration (`save-systems`); permadeath runs (`roguelike`).

## Workflow

1. **Read what exists:** stat names, item data, enemy tables, the content format (resources,
   ScriptableObjects, JSON). Keep the project's names.
2. **Set pacing targets** and get the user to confirm them: level cap, total hours to cap,
   and minutes per level at a few points. Starting point: about 3-5 minutes per level for the
   first five levels, rising to 30-60 minutes near the cap.
3. **Derive the XP table** from those minutes: `xp_to_next(L) = expected_xp_per_minute(L) *
   minutes_for_level(L)`, where XP per minute comes from the enemies and quests at that
   level. A bare formula such as `100 * L^2` is a fine first fill, but tune against minutes.
4. **Pick one damage family** (below) and set hit targets at equal level: a normal enemy dies
   in 2-4 player hits, the player survives 5-8 normal hits, a boss takes 25-60 hits.
5. **Build stats as base plus a modifier stack** (Pattern 1); items push modifiers.
6. **Define item rarity and affixes** with item level tied to the source's level.
7. **Check it.** Write a balance script or test that prints one row per level (player HP,
   damage, hits to kill a same-level enemy, hits to survive, minutes to next level) and fails
   when a row leaves the targets. Add a test that equips and unequips every item and asserts
   derived stats return exactly to their old values. Run both and report the table's outliers.

## Formulas that hold up

| Choice | Default | Why |
|--------|---------|-----|
| Damage vs defense | ratio: `dmg * K / (K + def)`, K = the defense that should halve damage | each defense point adds the same effective HP (1/K of HP), so defense never makes anyone immune; League of Legends uses K = 100 |
| Subtractive alternative | `max(1, atk - def)` | crisp at small numbers, but stacking defense quickly zeroes damage |
| Resist caps | percentage resists capped (Path of Exile: 75% by default) | stacked percentages reach 100% otherwise |
| Variance | ±10% | wider makes hits-to-kill unpredictable |
| Crit | 5% base chance, 1.5-2x damage | crit builds need room to grow |
| Type multipliers | 0.5 / 1 / 2 | clear tells; stack dual types multiplicatively (0.25-4) |
| XP curve | cubic total XP (Pokemon "Medium Fast": total XP to reach level n is n^3) or a minutes-based table | early levels fast, late ones long |
| Rarity weights | common 60, uncommon 25, rare 10, epic 4, legendary 1 | with a pity counter for the top tier if drops gate progress |
| Item level | the level of the monster or chest that dropped it | keeps loot useful while levelling |

Round once at the end of the damage formula. Sum percentage modifiers of the same kind
(+20% and +30% = +50%); multiply only across deliberately separate layers.

## Pattern 1: base stats plus a modifier stack

```python
# Pseudocode. Base attributes are the only stored truth; derived stats are recomputed.
def stat(actor, name):
    flat = sum(m.value for m in actor.mods if m.stat == name and m.kind == "flat")
    pct  = sum(m.value for m in actor.mods if m.stat == name and m.kind == "pct")
    more = product(1 + m.value for m in actor.mods if m.stat == name and m.kind == "more")
    return clamp((actor.base[name] + flat) * (1 + pct) * more, *LIMITS[name])

def equip(actor, item):
    for m in item.mods:
        actor.mods.append(Mod(m.stat, m.kind, m.value, source=item.instance_id))

def unequip(actor, item):
    actor.mods = [m for m in actor.mods if m.source != item.instance_id]   # exactly that item
```

When max HP changes, decide whether current HP keeps its value or its ratio, and apply the
same rule everywhere; otherwise swapping gear becomes a free heal.

## Gotchas

- **Stats wrong after a buff ends or gear comes off** → the buff edited base stats, or the
  modifier was removed by value instead of by source. Remove by source id (Pattern 1).
- **Unequip and re-equip heals to full** → current HP reset to the new max. Keep absolute HP
  (clamped) or the ratio, one rule for all cases.
- **Enemies become immune** → subtractive formula or uncapped percentage resists. Use the
  ratio formula or cap resists.
- **Late-game numbers explode** → exponential XP or damage growth with multiplicative
  modifiers stacking. Sum modifiers within a layer; check the per-level table.
- **Players out-level everything, or grind** → XP only from kills. Give quest XP sized to the
  minutes target so the critical path keeps the player near the content's level.
- **Progression feels pointless** → enemies scaled fully to the player's level. Scale within
  regional bands, or scale only part of the stats, so growth is visible.
- **Loot feels flat** → affix rolls with tiny ranges or too many affix types per item. Fewer,
  larger affixes per rarity tier read better.
- **Quest breaks on reload** → only "completed" is saved. Save quest state and objective
  counters (`save-systems`).
- **Displayed numbers disagree with combat** → UI rounds differently from the formula. Format
  from the same rounded value the combat code uses.

## References

- `references/stats-combat-quests.md`: read when writing the stat block and modifier layers,
  the two damage families in code, XP curve variants, turn-based versus ATB timelines, item and
  equipment data shapes, or the quest state model.

Related: `dialogue-systems` (conversations gated on quest state), `save-systems`,
`godot-resources` or `unity-scriptableobjects` (content as data), `game-ai` (enemy behaviour),
`roguelike` Pattern 1 (energy scheduler, the base of CTB and ATB turn order), `game-ui-ux`
(inventory and character screens).

## Version notes

Last verified: 2026-11-11.

- League of Legends armor multiplier 100 / (100 + armor) and linear effective HP:
  https://wiki.leagueoflegends.com/en-us/Armor.
- Pokemon experience groups (Medium Fast = n^3, 1,000,000 XP at level 100):
  https://bulbapedia.bulbagarden.net/wiki/Experience.
- Path of Exile default maximum resistance 75%: https://www.poewiki.net/wiki/Resistance.
- Pacing minutes, hits-to-kill bands and rarity weights are design starting points, not
  measured from a specific game.
