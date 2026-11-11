# RPG stats, combat, and quests (depth)

Formulas and data shapes behind `SKILL.md`. Engine-neutral pseudocode. Treat every number
as a starting point to tune against playtests, not a law.

Contents:
1. Stat block: base, derived and modifiers
2. Damage formulas
3. Levelling curves
4. Turn-based versus action combat timelines
5. Inventory and equipment data
6. Quest state model

## 1. Stat block: base, derived, and modifiers

Separate **base** attributes from **derived** combat stats so a single attribute change
ripples predictably, and keep **modifiers** in their own layer so buffs/equipment are
reversible without corrupting base values.

```python
# Base attributes (what leveling/allocation changes)
base = { "STR": 10, "AGI": 10, "INT": 10, "VIT": 10 }

# Derived stats are pure functions of base (+ modifiers). Recompute; never store as truth.
def derive(base, mods):
    s = sum_layers(base, mods)                  # base + flat + percent modifiers
    return {
        "max_hp":  20 + s["VIT"] * 8,
        "attack":  s["STR"] * 2,
        "defense": s["VIT"] * 1 + s["AGI"] * 0.5,
        "crit":    min(0.05 + s["AGI"] * 0.005, 0.50),   # cap it
        "speed":   s["AGI"],
    }
```

Modifier layers (apply in this order): **base → flat adds → percent multipliers → clamp**.
Equipping an item pushes a modifier; unequipping pops the same one. This avoids the classic
"buff wore off and left me at the wrong HP" bug. Decide how percents stack and write it down:
summing them (`+20%` and `+30%` → `×1.5`) keeps growth linear; multiplying them (`×1.2 × 1.3`
→ `×1.56`) compounds and runs away when many buffs stack. Sum within a layer by default and
reserve multiplicative stacking for a few rare effects. Store a modifier's source (item or
effect id) so removing it removes exactly that one.

## 2. Damage formulas

Two common families — pick one and stay consistent:

```python
# (a) Subtractive: defense flatly reduces damage. Simple; high defense can trivialize hits.
dmg = max(1, attacker.attack - defender.defense)        # floor at 1 so nothing is immune

# (b) Ratio/mitigation: defense gives diminishing % reduction. Scales smoothly to high numbers.
mitigation = defender.defense / (defender.defense + K)  # K ~ 100: defense == K halves damage
dmg = attacker.attack * (1 - mitigation)                # same as attack * K / (defense + K)

# Layer on: random variance (±10%), crit multiplier, and type effectiveness.
dmg *= rng.range(0.9, 1.1)
if is_crit: dmg *= 1.5
dmg *= type_multiplier(attacker.element, defender.element)   # 0.5 / 1.0 / 2.0
dmg = max(1, round(dmg))                                # round once, at the very end
```

Subtractive feels "tactical" at low numbers; ratio scales better for big late-game values.
Round only the final number: rounding after every step adds error at each step and makes the
result depend on the order the multipliers are applied.

## 3. Leveling curves

XP-to-next-level shapes the whole pace. Three common curves:

```python
# Linear-ish (gentle):     next = base * level
# Quadratic (classic JRPG):next = base * level^2
# Exponential (steep):     next = base * growth^level     # growth ~1.2–1.5

def xp_to_next(level, base=100, kind="quadratic", growth=1.3):
    if kind == "linear":      return base * level
    if kind == "quadratic":   return base * level * level
    if kind == "exponential": return int(base * (growth ** level))
```

Guidance: keep early levels fast (reward in minutes) and stretch later ones. Grant stat gains
and/or skill points on level-up; telegraph the next unlock to pull players forward.

## 4. Turn-based vs. action combat timelines

| | Turn-based | Action |
|---|---|---|
| Time | Discrete; pause to choose | Real-time; reflexes matter |
| Initiative | Speed stat / ATB gauge orders turns | Cooldowns / attack timing |
| Strength | Deep tactics, accessible | Visceral, skill-expressive |
| Build with | A turn scheduler (the energy scheduler in `roguelike`) | The engine movement/physics skill |

ATB ("active time battle") is a hybrid: a gauge fills by `speed`; when full, the actor may act.

## 5. Inventory and equipment data

```python
# Items are data, not code. Define them as resources/assets (see godot-resources /
# unity-scriptableobjects) and reference by id.
item = {
    "id": "iron_sword", "name": "Iron Sword", "slot": "weapon",
    "stackable": False, "max_stack": 1,
    "modifiers": [ {"stat": "STR", "type": "flat", "value": 3} ],
    "value": 50,
}
# Inventory = list of (item_id, count). Equipment = slot -> item_id.
# Equipping applies the item's modifiers (push); unequipping removes them (pop).
```

## 6. Quest state model

```python
# A quest is a small state machine with objectives. Persist its state in the save.
quest = {
    "id": "missing_cat", "state": "available",   # available -> active -> complete -> turned_in
    "objectives": [ {"id": "find_cat", "done": False, "count": 0, "needed": 1} ],
    "rewards": { "xp": 150, "gold": 30, "items": ["iron_sword"] },
}
# Game events (kill, pickup, talk) update matching objectives; when all done, state=complete.
# Dialogue conditions read quest state; turning in grants rewards and advances dependent quests.
```

Keep quest *definitions* as data and quest *progress* in the save. Gate dialogue lines and
NPC behavior on quest state via `dialogue-systems` conditions/variables.
