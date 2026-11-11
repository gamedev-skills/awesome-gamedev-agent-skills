---
name: level-design
description: >
  Engine-neutral level design with Godot checks: player metrics from the real controller, key and
  ability gating with a soft-lock check, and pacing. Use when laying out a level or metroidvania
  gates, or players get lost or a key sits behind its own door. Not for generation
  (`procedural-gen`), painting tiles (`godot-tilemap`, `unity-tilemap-2d`) or jump tuning
  (`platformer`).
---

# Level design

A level is a sequence of intended experiences delivered through space. The order that works:
measure the character, block out with primitives, check reachability and pacing, get playtest
reports, then dress. This skill is engine-neutral with Godot 4.7 checks. Painting the grid is
`godot-tilemap` or `unity-tilemap-2d`; generating layouts is `procedural-gen`.

## When to use

- Planning a level's structure: critical path, optional branches, gating order, encounters, and
  where a mechanic is taught versus tested.
- Building a blockout and checking that every required jump and gate is possible.
- Reviewing a level that confuses, bores or soft-locks players.

**Not this skill:** layout generators and dungeon algorithms (`procedural-gen`), jump and
movement tuning (`platformer`, the engine movement skill), enemy behaviour in the space
(`game-ai`), camera framing (`camera-systems`).

## Core workflow

1. **Measure the metrics from the game, not from memory.** Read the movement constants from the
   player script, then run the jump measurement (Pattern 1) to get the real apex, reach and
   airtime. Size every gap, ledge and corridor in those units.
2. **Block out the whole level** with untextured primitives at true scale: Godot `CSGBox3D` and
   friends with `use_collision` on, Unity ProBuilder (`com.unity.probuilder`), Unreal Modeling
   Mode, or a plain grey tileset in 2D. CSG is for prototyping only; bake it with
   `bake_static_mesh()` and `bake_collision_shape()` before shipping.
3. **Write the room graph** (rooms, exits, what each exit needs, what each room grants) and the
   beat list next to the level. Both are small data files the checks below read.
4. **Lay the critical path, then the golden path** (the route most players will take), then
   optional branches that rejoin it.
5. **Pace and teach.** Intensity rises in a sawtooth with a rest before each spike. Each
   mechanic appears first where failure is cheap, then under pressure.
6. **Gate with intent** using keys, abilities and one-way drops. Guide with light, leading
   lines and landmarks rather than walls.
7. **Run the checks** (see "Check it"), fix the blockout, and only then ask the user for a
   playtest with specific questions.
8. **Dress last**, and re-run the checks after any geometry change.

## Patterns

### 1. Measure the real jump (headless)

```gdscript
# tools/measure_jump.gd: godot --headless --path . --script res://tools/measure_jump.gd
# Runs the real player scene on flat ground with run + jump held and prints the reach.
extends SceneTree

const PLAYER := "res://player.tscn"            # the game's player scene
const RUN := &"move_right"
const JUMP := &"jump"

func _initialize() -> void:
    var ground := StaticBody2D.new()
    var shape := CollisionShape2D.new()
    shape.shape = WorldBoundaryShape2D.new()     # infinite floor at y = 0, normal up
    ground.add_child(shape)
    root.add_child(ground)
    var player: CharacterBody2D = load(PLAYER).instantiate()
    player.position = Vector2(0, -64)
    root.add_child(player)
    for i in 30:                                 # let the player land and settle
        await physics_frame
    Input.action_press(RUN)
    for i in 30:                                 # reach full run speed
        await physics_frame
    var start := player.position
    Input.action_press(JUMP)
    var apex := 0.0
    var ticks := 0
    var airborne := false
    while ticks < 600:
        await physics_frame
        ticks += 1
        apex = maxf(apex, start.y - player.position.y)
        if not player.is_on_floor():
            airborne = true
        elif airborne:
            break                                # landed back on the same height
    Input.action_release(JUMP)
    Input.action_release(RUN)
    var dt := 1.0 / Engine.physics_ticks_per_second
    print("JUMP apex=%.1f distance=%.1f airtime=%.3fs" % [apex, player.position.x - start.x, ticks * dt])
    quit(0 if airborne else 1)
```

Holding jump measures the full jump; release it after one tick to measure the short hop if the
controller has variable height. The formulas `h = v² / 2g` and `d = run_speed * 2v / g` are
only the ideal arc: a controller with `RUN_SPEED` 240, `JUMP_VELOCITY` 420 and gravity 980 gives
90 px and 206 px on paper and measured 93.6 px apex and 212 px reach here, because the fixed
step integrates in whole ticks. Fall gravity, air acceleration, collider width and landing
higher all change the number again. Size required gaps at about 0.7 of the measured reach and
keep gaps near 0.95 for optional challenges. For 3D, swap in `StaticBody3D`,
`WorldBoundaryShape3D` and `CharacterBody3D`.

### 2. Pacing as data, with a check

```gdscript
# Author the level as beats with an intended intensity (0..1), then check the curve.
const BEATS := [
    { "room": "entry",      "type": "teach",   "intensity": 0.1 },
    { "room": "hall_1",     "type": "combat",  "intensity": 0.5 },
    { "room": "vista",      "type": "rest",    "intensity": 0.1 },  # breather + reward
    { "room": "gauntlet",   "type": "combat",  "intensity": 0.8 },
    { "room": "save_room",  "type": "rest",    "intensity": 0.2 },  # before the boss
    { "room": "boss",       "type": "climax",  "intensity": 1.0 },
]

# Returns the pacing problems in a beat list; empty means it passes.
func pacing_problems(beats: Array, high := 0.7, max_high_run := 2) -> PackedStringArray:
    var problems := PackedStringArray()
    var run := 0
    for i in beats.size():
        var beat: Dictionary = beats[i]
        run = run + 1 if beat["intensity"] >= high else 0
        if run > max_high_run:
            problems.append("%s: %d high-intensity beats in a row" % [beat["room"], run])
        if beat["type"] == "climax" and (i == 0 or beats[i - 1]["type"] != "rest"):
            problems.append("%s: no rest beat right before the climax" % beat["room"])
    if not beats.is_empty() and beats[0]["type"] != "teach":
        problems.append("%s: the level does not open with a teach beat" % beats[0]["room"])
    return problems
```

The thresholds are a starting point for the user's game. Drive spawn density and music
intensity from the same table so the built level matches the plan.

### 3. Gating and the critical path (a small graph)

```gdscript
# Model the level as rooms + gated connections. Validate that the goal is
# reachable with the keys/abilities the player can actually obtain in order.
const ROOMS := {
    "entry":   { "exits": [ { "to": "hall_1" } ] },
    "hall_1":  { "exits": [ { "to": "vista", "needs": "double_jump" },
                            { "to": "side_room" } ] },           # optional branch
    "side_room": { "exits": [ { "to": "hall_1" } ], "grants": "double_jump" },
    "vista":   { "exits": [ { "to": "boss", "needs": "red_key" } ] },
}

# Search (room, held keys) states: keys from mutually exclusive one-way branches
# must not be combined. Keys are never consumed and doors never re-lock; model
# consumable keys as counts and persistent door changes as additional state.
# States grow exponentially with distinct keys; fine for hand-built room graphs.
func goal_reachable(rooms: Dictionary, start: String, goal: String) -> bool:
    var pending: Array[Dictionary] = [{"room": start, "keys": {}}]
    var visited := {}                             # "room|sorted keys" -> true
    while not pending.is_empty():
        var state: Dictionary = pending.pop_back()
        var room: String = state["room"]
        var have: Dictionary = state["keys"].duplicate()
        var info: Dictionary = rooms.get(room, {})
        var grant = info.get("grants")
        if grant != null:
            have[grant] = true
        var names := PackedStringArray(have.keys())
        names.sort()
        var id := room + "|" + ",".join(names)
        if visited.has(id):
            continue                              # cycles stop only at an equivalent state
        visited[id] = true
        if room == goal:
            return true
        for exit in info.get("exits", []):
            var open: bool = not exit.has("needs") or have.has(exit["needs"])
            if open:
                pending.append({"room": exit["to"], "keys": have})
    return false
# goal_reachable(ROOMS, "entry", "boss") is FALSE for the table above: no room
# grants "red_key". That is exactly the soft-lock this check exists to catch.
```

Exits are one-way: write both directions for a normal door and one direction for a drop. Also
call `goal_reachable` from every room the player can reach back to the start or a save point if
the level must never trap them; a one-way drop into a dead end fails that call.

## Check it

1. **Reachability:** run `goal_reachable` for start to goal in a headless test (follow
   `godot-gdscript-headless-testing`), plus from each one-way drop's landing room back to a save
   or exit. Any `false` is a soft-lock to fix before anything else.
2. **Metrics:** run Pattern 1 after every movement change. List each required gap and ledge in
   the blockout and compare it to the measured reach; anything above about 0.7 of the reach on
   the critical path needs a reason.
3. **Pacing:** `pacing_problems(BEATS)` returns empty, or each remaining line is a deliberate
   choice you can explain to the user.
4. **Playtest by proxy.** You cannot watch players, so ask the user for specific reports, for
   example: "Play from the start to the boss once without help. Tell me where you were unsure
   where to go, any jump you failed more than three times, any room that felt like a chore, and
   how long the run took." Map each report to the room graph and fix the blockout, not the art.

## Gotchas

- **Dressing before it plays.** Art on an unvalidated blockout is the most expensive work on the
  layout most likely to change.
- **Metrics from formulas only.** The ideal arc overstates or understates the real reach
  depending on the step, fall gravity and collider. Measure the real controller.
- **Validating connectivity but not order.** A flood fill says every room is connected while
  the key still sits behind its own door. Track held keys, as Pattern 3 does.
- **Two-way edges written as one-way** (or the reverse) make the check pass on a level that
  traps players, or fail on one that does not. Write each exit as the player can use it.
- **Flat pacing.** Wall-to-wall combat or wall-to-wall calm numbs players. Alternate, and put a
  rest and a save before the climax.
- **Testing a mechanic before teaching it.** The first meeting with a hazard should be safe.
- **Guidance by wall.** Lost players usually need a sightline, light or landmark, not a barrier.
- **One-way drops with no signposting** strand or surprise players. Telegraph irreversible moves.
- **Authored pacing expected from a generator.** Generation gives variety, not intent; use
  `procedural-gen` for variety and author the beats that need intent.

## References

- `references/pacing-and-flow.md`: read when shaping the tension curve, designing the
  introduce-develop-twist-test loop for a new mechanic, choosing gating tools, guiding players
  through 2D or 3D space, or running a blockout review.

## Related skills

- `platformer`: jump tuning that produces the metrics; re-measure after it changes.
- `procedural-gen`: generated layouts that complement authored structure.
- `godot-tilemap`, `unity-tilemap-2d`: painting the 2D grid.
- `game-ai`: enemies that navigate the space; `camera-systems`: what the player can see.

## Version notes

Last verified: 2026-11-11.

- Godot 4.7: `CSGShape3D` docs say CSG has a significant CPU cost and is meant for prototyping;
  `bake_static_mesh()` and `bake_collision_shape()` turn it into static resources
  (https://github.com/godotengine/godot/blob/4.7-stable/modules/csg/doc_classes/CSGShape3D.xml).
- The jump measurement, pacing check and reachability check were run on Godot 4.7.2 headless.
