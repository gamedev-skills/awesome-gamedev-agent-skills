---
name: survival-crafting
description: >
  Designs survival-crafting loops in any engine: gathering, recipes and tech trees, carry weight,
  spoilage, hunger and temperature, and base building. Use for a Minecraft-, Valheim- or Don't
  Starve-like, or crafting that eats materials or needs that feel like chores. Not for RPG
  equipment stats (`rpg`), terrain generation (`procedural-gen`) or save files (`save-systems`).
---

# Survival crafting

Owns the gather, craft, build and survive loop and the pressure systems around it: needs,
scarcity, logistics and escalating threats. Each tier of tools must open the next tier of
resources; when that ladder breaks, the game turns into chores.

## When to use

- The player gathers resources, crafts tools and structures, manages needs and builds a base
  against rising threats: survival sandbox, crafting game, colony or base builder.
- Tuning needs, recipes, carry limits, spoilage, building rules or raid pacing.

**When not to use:** weapon and armour stat systems, rarity and affixes (`rpg`); world and
biome generation (`procedural-gen`); save file format and migration (`save-systems`).

## Workflow

1. **Choose the needs model with the user** (it sets the tone):
   - *Attrition:* an empty bar causes damage. Minecraft: 20 hunger points; at 0 the player loses
     1 HP every 4 s, stopping at 10 HP on Easy and 1 HP on Normal, and it can kill on Hard.
   - *Buff:* food raises maximums instead. Valheim: up to 3 different foods at once, each
     adding max health and stamina for about 10-50 minutes; nobody starves. Better for
     co-op and building-focused games.
2. **Set the clock.** Pick day length (Minecraft: 20 minutes, 10 of them full day) and size
   needs to it: a full hunger bar lasts about 1-2 days of normal activity, thirst drains about
   1.5-2x faster than hunger, warnings appear at 25-30%, and activity (sprint, cold, carrying
   weight) speeds the drain.
3. **Draw the progression ladder** as a graph: resource tier → tool → new node type → station
   → next resource tier. Each step needs one new trip outward from the base.
4. **Define recipes as data** with a station and tech requirement (Pattern 1), and choose how
   they are discovered: show a recipe once the player has picked up one of its ingredients, so
   the menu teaches the next goal without a wiki.
5. **Set logistics limits:** slots with stack sizes (Minecraft stacks most items to 64), or
   weight (Valheim starts at 300). Storage and crafting from nearby chests relieve them at base.
6. **Pace threats by progress** (bosses killed, tech tier, base size), not by wall-clock time
   alone, and telegraph big raids at least a day ahead.
7. **Check it.** Write and run these as tests and report the results:
   - every craftable item is reachable from the starting resources through the recipe and tech
     graph, and no recipe needs its own output (or a later tier) to be made;
   - crafting with a full inventory either fits the output or changes nothing;
   - simulated needs: minutes from full to warning and to empty at idle and at sprint, printed
     against the day length;
   - spoilage moves food through each freshness tier at the expected time;
   - save, change one chunk and a container, reload: the change and the contents survive.

## Spoilage

Track freshness per stack (`0..1`, merged as a count-weighted average) and apply tiers.
Don't Starve's tiers are a tested reference: fresh (50-100%) gives full value; stale
(20-50%) gives 2/3 of the hunger, 1/3 of the health and no sanity; spoiled (under 20%) gives
1/2 the hunger, no health and costs 10 sanity, then the item rots. Cooking halves the spoilage
so far. Cold storage slows the clock. Show the tier on the icon.

## Pattern 1: atomic crafting

```python
# Pseudocode. Validate everything, then consume and add as one step.
recipe = {"id": "stone_axe", "inputs": {"wood": 3, "stone": 2}, "output": ("stone_axe", 1),
          "station": "workbench", "tech": "basic_tools"}

def craft(recipe, inv, tech, station):
    if recipe["tech"] and recipe["tech"] not in tech: return "locked"
    if recipe["station"] and recipe["station"] != station: return "needs " + recipe["station"]
    if any(inv.count(i) < n for i, n in recipe["inputs"].items()): return "missing materials"
    if not inv.fits_after_removing(recipe["inputs"], *recipe["output"]):
        return "no room"                             # count slots the inputs free up
    for item, n in recipe["inputs"].items():
        inv.remove(item, n)
    inv.add(*recipe["output"])
    return "ok"
```

## Gotchas

- **Inputs consumed, nothing crafted** → output added after removal into a full bag, or an
  exception between the two steps. Check space including freed slots first (Pattern 1); if
  "drop on the ground" is the rule, do it inside the same step.
- **Needs feel like chores** → bars that drain fast with small refills. Fewer, larger meals,
  meal variety that rewards effort, or the buff model.
- **Instant deaths from needs** → binary failure. Warn, then attrition with time to recover.
- **Map stripped, players quit** → no regrowth. Respawn nodes on a timer or when the player is
  far away, and keep rare nodes scarce near base so exploration stays the answer.
- **Inventory always full** → weight or slots with no base-side relief. Add storage, crafting
  from nearby containers and a deposit-all action.
- **Mid-game stalls** → a tier needs a resource with no hint where to find it. Every tier's key
  resource must be visible or hinted before the player needs it.
- **Spoilage doubles or resets when stacks merge** → freshness kept per item but merged by
  taking the newest. Merge by count-weighted average.
- **Needs drain differently on fast machines** → per-frame decay without `dt`, or decay tied to
  render frames. Tick needs on the game clock.
- **Huge, slow saves or lost bases** → saving the whole world each time. Save changed chunks
  and structures incrementally, autosave on sleep or day rollover, never mid-combat
  (`save-systems`).

## References

- `references/needs-and-crafting.md`: read when writing the needs model and thresholds, the
  tech tree as a graph, multi-step recipe chains, gather and respawn rules, build placement
  and stability, threat escalation or incremental world saves.

Related: `rpg` (gear stats and loot rarity), `procedural-gen` (biomes, resource placement),
`save-systems`, `game-ai` (creatures and raiders), `game-ui-ux` with the engine UI skill
(inventory, crafting menu, needs HUD), `godot-tilemap` or `unity-tilemap-2d` (2D build grids).

## Version notes

Last verified: 2026-11-11.

- Minecraft hunger (20 points, starvation 1 HP per 4 s, difficulty floors 10/1/0 HP):
  https://minecraft.wiki/w/Food and https://minecraft.wiki/w/Damage. Day length 24,000
  ticks = 20 minutes: https://minecraft.wiki/w/Daylight_cycle.
- Don't Starve freshness tiers and cooking halving spoilage: https://dontstarve.wiki.gg/wiki/Food.
- Valheim: 3 food slots adding max health and stamina, base carry weight 300 (community
  guides, for example https://eip.gg/valheim/guides/carry-weight).
- Pacing ratios (bar length in days, thirst versus hunger, warning thresholds) are design
  starting points.
