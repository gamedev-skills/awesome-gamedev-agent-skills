---
name: godot-animation
description: >
  Animate in Godot 4.7 three ways: AnimationPlayer for keyframed clips (incl. Call
  Method tracks), AnimationTree with state machines and blend spaces for
  character animation, and Tween for short procedural/UI tweens via create_tween().
  Use when working with AnimationPlayer/AnimationTree nodes in a .tscn, blending
  character states, sprite-sheet animation, or code-driven Tweens.
---

# Godot Animation (4.x)

Choose and drive the right animation tool: `AnimationPlayer` (clips), `AnimationTree`
(blending/state machines), or `Tween` (short procedural moves). Targets **Godot 4.7**.

## When to use

- Use when playing keyframed animations, blending walk/run/idle states, animating a
  sprite sheet, or tweening UI/objects in code.

**When *not* to use:** the movement *logic* that decides which state to play →
`godot-2d-movement`; UI layout (vs. UI tweening) → `godot-ui-control`; shader-driven
effects → `godot-shaders`.

## Core workflow

1. **Pick the tool:**
   - `AnimationPlayer` — author keyframed clips (transforms, properties, method calls,
     audio, even other animations). The source of truth for clip data.
   - `AnimationTree` — blend and transition between those clips at runtime with a state
     machine and/or blend spaces. Needs an `AnimationPlayer` to pull clips from.
   - `Tween` — fire-and-forget procedural interpolation in code (`create_tween()`); ideal
     for UI pops, fades, and one-off moves.
2. **For 2D sprite sheets:** use `AnimatedSprite2D` + `SpriteFrames`, or keyframe the
   `frame` property in an `AnimationPlayer`.
3. **For characters:** build clips in `AnimationPlayer`, then add an `AnimationTree`
   (`active = true`), set its `anim_player`, and design an `AnimationNodeStateMachine` or
   `AnimationNodeBlendSpace2D` as the tree root.
4. **Drive transitions from code** via the playback object (`travel`) or by setting blend
   parameters.
5. **React to clip events** with the `animation_finished` signal and Call Method tracks.

## Patterns

### 1. AnimationPlayer: play a clip and await it

```gdscript
@onready var anim: AnimationPlayer = $AnimationPlayer

func attack() -> void:
    anim.play("attack")
    await anim.animation_finished     # resume after the clip ends
    anim.play("idle")
```

### 2. AnimationTree state machine: travel between states

```gdscript
@onready var tree: AnimationTree = $AnimationTree

func _ready() -> void:
    tree.active = true                # the tree drives animation; AnimationPlayer is the source

func set_state(state: StringName) -> void:
    # The playback object controls an AnimationNodeStateMachine root.
    var sm: AnimationNodeStateMachinePlayback = tree.get("parameters/playback")
    sm.travel(state)                  # transitions using the graph's connections

func _physics_process(_d: float) -> void:
    set_state(&"run" if velocity.length() > 5.0 else &"idle")
```

### 3. Blend space: blend run direction by a 2D parameter

```gdscript
# tree.tree_root is an AnimationNodeBlendSpace2D with idle/run points placed in it.
func update_locomotion(input_dir: Vector2) -> void:
    tree.set("parameters/blend_position", input_dir)
# If the blend space is instead a child named "Move" in a blend tree/state machine,
# its parameter is "parameters/Move/blend_position".
```

### 4. Tween: fade and scale a UI element (code-driven)

```gdscript
func pop_in(node: Control) -> void:
    node.scale = Vector2.ZERO
    node.modulate.a = 0.0
    var tw := create_tween()                          # bound to this node's tree
    tw.set_parallel(true)                             # run the two tweens together
    tw.tween_property(node, "scale", Vector2.ONE, 0.2) \
      .set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
    tw.tween_property(node, "modulate:a", 1.0, 0.2)   # sub-property via ":"
```

## Pitfalls

- **`AnimationTree.active` left false** → nothing animates and `travel()` appears to do
  nothing. Set `active = true` and assign the `anim_player` path.
- **Wrong parameter path.** Root parameters start at `"parameters/"` (e.g.
  `"parameters/blend_position"` or `"parameters/playback"`). Nested nodes add their names,
  e.g. `"parameters/Move/blend_position"`; match the actual tree hierarchy.
- **AnimationPlayer and AnimationTree fighting.** When an `AnimationTree` is active, don't
  also call `AnimationPlayer.play()` for the same tracks — let the tree own playback.
- **3.x Tween node is gone.** There is no `Tween` node to add in 4.x; create tweens in
  code with `create_tween()` (which returns a `Tween`). They auto-start and free themselves.
- **Tween stalls when its node leaves the tree.** `node.create_tween()` pauses while that
  node is outside the tree and dies when it is freed. Use `get_tree().create_tween()` for a
  tween that must keep running while the node is out of the tree.
- **Scale/rotation tween on a child of a `Container` snaps back** → the container resets
  child transforms whenever it re-sorts. In 4.7+ set `offset_transform_enabled = true` and
  tween `offset_transform_scale` / `offset_transform_rotation` / `offset_transform_position`
  instead (visual only by default).
- **Reusing a finished tween.** A tween is one-shot; call `create_tween()` again for a new
  animation. Use `set_loops()` for repetition.
- **`yield`/`yield(anim, "...")` is gone.** Use `await anim.animation_finished`.
- **Sub-property tweens** use a colon: `"modulate:a"`, `"position:x"`. Tweening the whole
  property instead overwrites siblings.

## References

- For state machine transitions/conditions, root motion, one-shot/blend nodes, method &
  call tracks, `SpriteFrames`/`AnimatedSprite2D`, and Tween easing/chaining/callbacks,
  read `references/animation-tree-and-tween.md`.

## Related skills

- `godot-2d-movement` — supplies the velocity/state that selects animations.
- `godot-ui-control` — UI that Tweens animate.
- `godot-3d-essentials` — 3D character scenes driven by AnimationTree.
- `game-ai` — state machines that mirror animation states.
