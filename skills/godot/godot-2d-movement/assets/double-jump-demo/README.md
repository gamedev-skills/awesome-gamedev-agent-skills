# Double-jump starter (Godot 4.6+)

A tiny 2D platformer that demonstrates the double-jump controller from the
[`godot-2d-movement`](../../SKILL.md) skill. Open this folder in Godot 4.6 or newer and press
F5, or run it headless with the test below.

## Controls

- **Move:** Left/Right arrows
- **Jump:** Space or Enter
- **Double jump:** press jump again while airborne (one extra jump)
- **Reset:** R

## What to try

1. Jump from the ground onto the low platform (single jump).
2. From the low platform, double jump onto the middle platform.
3. From the middle platform, double jump onto the goal platform.
4. Watch **Air jumps left**: it is 1 on the ground, stays 1 after the ground jump, becomes 0
   after the air jump, and refills on landing.

## Tuning

Select the `Player` node and edit the exported values:

- `max_air_jumps`: `1` = double jump, `2` = triple jump.
- `jump_velocity` / `air_jump_velocity`: ground vs. air jump strength.
- `coyote_time`, `jump_buffer_time`, `jump_cut_multiplier`, `fall_gravity_multiplier`.

## Headless test

```bash
godot --headless --path . --import
godot --headless --path . --script res://tests/test_player.gd
```

The test lands, jumps, waits past coyote time, air-jumps, confirms a third press does nothing,
then lands and checks that the air jump refills.

## Files

`project.godot`, `main.tscn` + `main.gd` (level, UI, reset), `player.tscn` + `player.gd`
(controller), `tests/test_player.gd`.

The `*.gd.uid` files are committed on purpose: Godot 4.4+ uses them to keep script references
stable, and regenerating them on every clone would dirty the working tree as soon as the
project is opened. `.godot/` (the import cache) is ignored.
