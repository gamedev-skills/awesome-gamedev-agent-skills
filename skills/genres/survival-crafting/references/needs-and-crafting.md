# Survival needs, crafting trees, and building (depth)

Detail behind `SKILL.md`. Engine-neutral pseudocode. Numbers are starting points to tune.

Contents:
1. Needs model
2. Crafting tech tree
3. Recipe data and multi-step chains
4. Gathering and respawn
5. Base building
6. Threat escalation
7. Saving a large world

## 1. Needs model

Each need is a value in `[0, max]` that decays over time and triggers consequences at
thresholds. Keep consequences **graded** (warn → attrition) so players have time to react.

| Need | Decays from | Failure consequence | Restored by |
|------|-------------|---------------------|-------------|
| Hunger | time, activity | HP attrition at 0 | eating food |
| Thirst | time (faster than hunger) | HP attrition at 0 | drinking |
| Temperature | ambient, wetness, time of day | HP attrition when too cold/hot | fire, shelter, clothing |
| Stamina | sprint/work | can't sprint/attack at 0 | rest |
| Health | need failure, damage | death at 0 | safe + fed regen, healing items |

```python
# Rates as fraction of max per real second (tune so a day cycle has meaningful pressure).
HUNGER_RATE = 0.6 / 60     # ~empty in ~100 s of neglect at this scale (illustrative)
THIRST_RATE = 1.0 / 60     # thirst should bite before hunger
```

Design notes:
- Thirst usually drains faster than hunger; both should be manageable during normal play and
  only dangerous when neglected.
- Tie decay to activity (sprinting/cold raises hunger) for emergent pressure.
- Always show needs on the HUD with a warning state before they hit zero.

## 2. Crafting tech tree

Model progression as a directed acyclic graph of **tech nodes**; recipes unlock when their
prerequisite tech is researched/built. This turns crafting into long-term goals, not a flat list.

```python
tech = {
    "basic_tools":   {"requires": [],               "unlocks": ["stone_axe", "stone_pick"]},
    "workbench":     {"requires": ["basic_tools"],  "unlocks": ["workbench_recipes"]},
    "metalworking":  {"requires": ["workbench"],     "unlocks": ["furnace", "iron_tools"]},
}
def can_unlock(node, owned): return all(r in owned for r in tech[node]["requires"])
```

Gate stations behind tech (workbench → furnace → forge) and recipes behind stations, so the
player physically builds their way up the tree. Each tier should grant access to a new
resource tier (stone → iron → advanced), closing the gather→craft→reach loop.

## 3. Recipe data and multi-step chains

```python
# Intermediate products make crafting feel like progression, not a vending machine.
recipes = {
    "plank":     {"inputs": {"log": 1},                 "output": ("plank", 2), "station": None},
    "nails":     {"inputs": {"iron_ingot": 1},          "output": ("nails", 4), "station": "forge"},
    "wall":      {"inputs": {"plank": 4, "nails": 2},   "output": ("wall", 1),  "station": "workbench"},
}
# Refining (log -> plank, ore -> ingot) before assembly (plank+nails -> wall) adds depth
# without more raw resource types.
```

## 4. Gathering and respawn

- Nodes have an HP/tool-tier requirement and a **drop table** (weighted; table mechanics in
  `procedural-gen`). Wrong/weak tool = no yield or slow yield.
- Respawn so the world isn't permanently stripped: timer-based regrowth, or zone-based
  repopulation when the player is away. Scarcity near the base pushes exploration outward.
- Tool tiers gate node types (fists → wood; stone pick → stone/ore; metal pick → hard ore),
  which is the main lever turning "explore farther" into "unlock better gathering".

## 5. Base building

- **Grid/snap placement:** snap structures to a grid or to existing pieces' sockets; validate
  placement (not overlapping, on valid ground, within reach) before committing.
- **Structural sanity (optional):** support/stability rules add depth but cost complexity — add
  only if it serves the fantasy.
- **Function:** bases provide storage (extra inventory), crafting stations (tech gates), and
  defense (walls/traps) against the threat cycle. Storage relieves the inventory cap so the
  player gathers in bulk, then returns — a deliberate logistics loop.

```python
def place(structure, pos, world, inv):
    if not world.is_valid_placement(structure, pos): return notify("Can't build here")
    if not inv.has(structure.cost): return notify("Missing materials")
    inv.consume(structure.cost)
    world.add_structure(structure, pos)     # now functions as storage/station/defense
```

## 6. Threat escalation

- **Day/night:** day for gathering, night for defense — a natural rhythm. Threats spawn or
  strengthen at night.
- **Tiered escalation:** ramp threat by elapsed days, tech tier reached, or distance from
  spawn, so the world keeps pace with the player's power. Telegraph big events (a "blood moon"
  style raid) so players can prepare a base.
- Balance escalation against the progression ladder: new threats should arrive roughly as the
  player unlocks the tools/defenses to answer them.

## 7. Saving a large world

Survival saves are big and frequent. Persist incrementally (changed chunks/structures), keep a
`version` for migration, and autosave on safe events (sleeping, day rollover) rather than
mid-combat. Defer slot/versioning mechanics to `save-systems`.
