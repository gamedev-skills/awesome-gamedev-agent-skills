---
name: godot-animation
description: >
  Godot 4.7 animation APIs: AnimationPlayer, AnimationTree state machines, AnimatedSprite2D and
  create_tween() Tweens, with a headless state test. Use when travel() does nothing, an animation
  will not play, a tween snaps back or the log says "Animation not found". Not for easing choices
  (`game-feel`), sprite art (`create-game-assets`) or Unity (`unity-animation`).
---

# Godot Animation (4.x)

Drive clips, blends and tweens the way Godot expects, then prove the names and states with a
headless test. Targets **Godot 4.7**; check `config/features` in `project.godot` first.

## Workflow

1. **Pick one owner per property.** `AnimationPlayer` stores keyframed clips. An active
   `AnimationTree` plays those clips and owns their tracks, so code talks to the tree.
   `Tween` is for short code-driven moves (UI pops, fades, one-off motion).
2. **Characters:** clips in an `AnimationPlayer`, then an `AnimationTree` with `anim_player`
   pointing at it, `active = true`, and an `AnimationNodeStateMachine` or blend space as
   `tree_root`. Sprite sheets: `AnimatedSprite2D` + `SpriteFrames`, or key `frame` in a clip.
3. **Drive from gameplay state**, not input: pick the state from velocity and floor checks
   each physics tick and call `travel()`; set blend positions through `parameters/` paths.
4. **Events:** `animation_finished` for non-looping clips, Call Method tracks for frame-exact
   hits and footsteps.
5. **Verify before you finish** (paths are relative to this skill's folder):
   - If `godot-nodes-scenes` is installed, run `python3 ../godot-nodes-scenes/scripts/check_godot_project.py <project>`
     after editing `.tscn` files; it catches broken resource paths and `parent=` node paths.
     The headless test below covers `anim_player`.
   - Run the scene headless and read the log, because Godot exits 0 after these errors:
     `godot --headless --path <project> --quit-after 300 res://player.tscn > run.log 2>&1`, then
     `grep -nE "SCRIPT ERROR|^ERROR:" run.log`. "Animation not found", "No such node" (bad
     `travel()` target) and "started with no Tweeners" all land there.
   - Copy `assets/test_animation_states.gd` to `res://tests/`, list the clip and state names
     the code uses, and run it with `godot --headless --path <project> --script res://tests/test_animation_states.gd`.
     Exit 0 means every clip exists, the tree is active and wired, and each state is
     reachable. CI wiring: `godot-gdscript-headless-testing`.
   - Timing and look need eyes: ask the user to play the scene and report anything that
     pops, slides or plays at the wrong moment.

## Patterns

### 1. Play a clip and continue when it ends

```gdscript
@onready var anim: AnimationPlayer = $AnimationPlayer

func attack() -> void:
    anim.play("attack")                 # must not loop, or the signal never comes
    await anim.animation_finished
    anim.play("idle")
```

### 2. State machine: travel between states

```gdscript
@onready var tree: AnimationTree = $AnimationTree
@onready var playback: AnimationNodeStateMachinePlayback = tree.get("parameters/playback")

func _physics_process(_delta: float) -> void:
    var moving := velocity.length() > 5.0
    playback.travel(&"run" if moving else &"idle")   # follows the graph's transitions
```

`travel()` walks the shortest path of enabled transitions; `start(&"state")` jumps there at
once. Calling `travel()` every tick with the state it is already in does not restart it.

### 3. Blend space: blend run direction by a 2D parameter

```gdscript
# tree.tree_root is an AnimationNodeBlendSpace2D with idle/run points placed in it.
func update_locomotion(input_dir: Vector2) -> void:
    tree.set("parameters/blend_position", input_dir)
# If the blend space is instead a child named "Move" in a blend tree/state machine,
# its parameter is "parameters/Move/blend_position".
```

### 4. Tween: pop a UI element in

```gdscript
func pop_in(node: Control) -> void:
    node.pivot_offset = node.size / 2                 # scale from the centre
    node.scale = Vector2.ZERO
    node.modulate.a = 0.0
    var tw := create_tween().set_parallel(true)
    tw.tween_property(node, "scale", Vector2.ONE, 0.2) \
        .set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
    tw.tween_property(node, "modulate:a", 1.0, 0.2)   # sub-property via ":"
```

## Gotchas

- **Nothing animates and `travel()` does nothing** → `AnimationTree.active` is false or
  `anim_player` is empty or points at the wrong node.
- **`await anim.animation_finished` never returns** → the clip loops; looping clips do not
  emit it. Await a non-looping clip, or use a Call Method key at the end of the loop.
- **`play("run")` does not restart the clip** → playing the clip that is already playing
  continues from the current position. Call `stop()` first or `seek(0.0, true)` to restart.
- **The tree and code fight** → while an `AnimationTree` is active, `AnimationPlayer.play()`
  on the same clips is overridden. Change states through the tree.
- **Wrong parameter path** → root parameters start at `parameters/`
  (`parameters/playback`, `parameters/blend_position`); a named child adds its name
  (`parameters/Move/blend_position`). The tree's Inspector lists them under Parameters.
- **`Tween (bound to ...): started with no Tweeners`** → `create_tween()` was called and
  nothing was added that frame, often in a branch that returns early. Create the tween right
  before adding steps.
- **`Infinite loop detected` and the tween dies** → `set_loops()` (0 = forever) on a tween
  whose steps take no time, such as only `tween_callback()`. Add a `tween_interval()`.
- **A tween stalls** → `node.create_tween()` pauses while that node is outside the tree and
  dies when it is freed; `get_tree().create_tween()` is unbound. Tweens are one-shot: create
  a new one for each animation and `kill()` the old one so two do not fight.
- **Scale or rotation tween on a `Container` child snaps back** → containers reset child
  transforms. In 4.7+ set `offset_transform_enabled = true` and tween
  `offset_transform_scale`/`_rotation`/`_position`, which are visual only.
- **Tweening `modulate` overwrites the other channels** → tween `"modulate:a"` instead.
- **3.x code** → there is no `Tween` node and no `yield`; use `create_tween()` and
  `await anim.animation_finished`.

## References

- Read `references/animation-tree-and-tween.md` for transitions and advance conditions, root
  motion, one-shot and blend-tree nodes, Call Method tracks, `SpriteFrames`, and the full
  Tween API including the 4.7 `tween_await()`.
- `assets/test_animation_states.gd` is the headless test used in step 5.

## Related skills

- `godot-2d-movement`: the velocity and floor state that choose animations.
- `game-feel`: which easing, squash and timing to use.
- `godot-ui-control`: the UI that tweens animate.
- `godot-3d-essentials`: 3D character scenes driven by AnimationTree.
- `godot-gdscript-headless-testing`: running the animation test in CI.

## Version notes

Last verified: 2026-11-11 against the Godot 4.7.2 class reference and a 4.7.2 headless run.

- Godot 4.7.2 (August 2026) is the current stable release; 4.8 is in beta.
- New in 4.7: `Tween.tween_await()` with `AwaitTweener.set_timeout()`, and the Control
  `offset_transform_*` properties.
- Sources: [Godot releases](https://github.com/godotengine/godot/releases),
  [Godot 4.7 release page](https://godotengine.org/releases/4.7),
  [AnimationTree](https://docs.godotengine.org/en/stable/classes/class_animationtree.html),
  [Tween](https://docs.godotengine.org/en/stable/classes/class_tween.html).
