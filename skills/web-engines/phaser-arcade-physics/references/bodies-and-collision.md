# Arcade body anatomy & collision detail (Phaser 4.2)

Depth on the Arcade `Body` and the collision system. The `SKILL.md` covers the
common path; reach for this when tuning feel, shaping hitboxes, or filtering
collisions.

Contents:

- Dynamic vs static bodies
- Movement properties (table)
- Custom hitboxes
- Colliders, overlaps, and callbacks
- Contact state (`touching`, `blocked`, `wasTouching`)
- World bounds
- Collision categories & masks
- Debugging

## Dynamic vs static bodies

- **Dynamic** (`this.physics.add.sprite`, `image`, `group`): moved by velocity,
  acceleration, drag, and gravity; pushed by collisions.
- **Static** (`staticImage`, `staticSprite`, `staticGroup`): never moves, never
  pushed. Cheaper. Use for ground, walls, platforms. After moving its parent game
  object, call `body.updateFromGameObject()` (or `gameObject.refreshBody()`) so the
  body re-syncs — static bodies do **not** track their parent automatically.

Make a dynamic body behave like a wall with `body.setImmovable(true)`; it still
exists in the simulation but won't be displaced by collisions.

## Movement properties

| Property | Setter | Notes |
|----------|--------|-------|
| velocity | `setVelocity(x, y)` / `setVelocityX/Y` | pixels per second |
| acceleration | `setAcceleration(x, y)` | pixels/sec²; accumulates into velocity |
| gravity | `setGravity(x, y)` | added on top of world gravity |
| drag | `setDrag(x, y)` | px/sec² of slowdown, applied only while that axis has no acceleration; with `setDamping(true)` it is the share of velocity kept per second (e.g. `0.05`) |
| max velocity | `setMaxVelocity(x, y)` | clamp speed |
| bounce | `setBounce(x, y)` | 0 = stop on hit, 1 = full rebound |
| friction | `setFriction(x, y)` | share of motion passed to a riding body |

`body.stop()` zeroes velocity, acceleration, and speed in one call.
`body.reset(x, y)` teleports the body and clears motion.

Total gravity on a body = `world.gravity + body.gravity`. Disable world gravity
for a single body with `body.setAllowGravity(false)` (useful for flying enemies).

## Custom hitboxes

The body defaults to the sprite's frame size. Tighten it to the art:

```js
sprite.body.setSize(20, 36, true);   // width, height, center on the frame
sprite.body.setOffset(6, 4);         // nudge the box within the frame
sprite.body.setCircle(16);           // circular body of radius 16
```

`setSize`'s third argument re-centers the body; pass `false` to keep the offset at
`(0, 0)` and position it yourself with `setOffset`.

## Colliders, overlaps, and callbacks

```js
const collider = this.physics.add.collider(
  objectsA, objectsB,
  collideCallback,   // (objA, objB) => {}   runs after separation
  processCallback,   // (objA, objB) => boolean  return false to skip this pair
  this               // callback context
);

collider.active = false;                 // temporarily disable
this.physics.world.removeCollider(collider); // remove entirely
```

`overlap(...)` has the same signature but never separates the bodies — use it for
pickups, hurt-boxes, and triggers. A `processCallback` that returns `false`
discards the pair before the main callback (e.g. ignore collisions with allied
units).

`objectsA`/`objectsB` may each be a single game object, an array, or a physics
group, so one call can wire up "all bullets vs all enemies".

## Contact state

After the physics step, each body exposes which sides are touching:

```js
body.blocked.down   // can't move down: bounds, tile, or a blocking body below
body.touching.left  // touching another body on the left this step
body.onFloor()      // shorthand for blocked.down
body.onWall()       // blocked.left || blocked.right
body.wasTouching    // touching state from the previous step (edge detection)
```

`touching` is set for any body contact. `blocked` means the body cannot move further
that way: the world bounds, a colliding tile, an immovable, static or non-pushable
(`sprite.setPushable(false)`) body, or a body that is itself blocked (a crate resting
on the floor). That is why `blocked.down`/`onFloor()` works as a ground check on a
`staticGroup` platform but stays `false` when landing on an ordinary dynamic body in
mid-air. Compare `touching` against `wasTouching` to detect the first frame of a hit
(e.g. play a sound once on landing).

## World bounds

```js
this.physics.world.setBounds(0, 0, 1600, 1200);        // simulation bounds
body.setCollideWorldBounds(true);                       // clamp this body
body.onWorldBounds = true;                              // emit events at edges
this.physics.world.on('worldbounds', (b, up, down, left, right) => { /* ... */ });
```

## Collision categories & masks

Every body starts in category `1` with a mask of `1`, so everything collides with
everything. A pair is tested only when **each** side's mask contains the other side's
category. Moving a body into a new category therefore also cuts it off from every
body you have not touched, because their mask is still `1`:

```js
const WORLD  = 1;                                  // the default category
const PLAYER = this.physics.nextCategory();        // 2, 4, 8, ... (max 32 categories)
const ENEMY  = this.physics.nextCategory();

player.setCollisionCategory(PLAYER);
player.setCollidesWith([WORLD, ENEMY]);            // keep the untouched ground

// The ground still has mask 1, so it would now ignore PLAYER: widen it too.
ground.setCollidesWith([WORLD, PLAYER, ENEMY]);    // or ground.resetCollisionCategory()
```

When one side of a collider is a group, the group's own category and mask are checked
**and** each member's. The group's values are not copied to its members, so set both:

```js
enemies.setCollisionCategory(ENEMY).setCollidesWith([WORLD, PLAYER]);
const enemy = enemies.create(600, 400, 'enemy');   // and every other member
enemy.setCollisionCategory(ENEMY).setCollidesWith([WORLD, PLAYER]);
```

A dynamic physics group starts with a mask of all bits; a static group and every
body start with mask `1`. `resetCollisionCategory()` sets category `1` and a mask of
all bits ("collides with everything"), which is wider than a new body's default.
If you only need to skip a few pairs, a `processCallback` that returns `false` is
simpler than categories.

## Debugging

While building, enable `arcade.debug: true` to render body rectangles, static-body
outlines, and velocity vectors. Per-body overrides:

```js
this.physics.world.defaults.debugShowVelocity = true;
gameObject.setDebug(true, true, 0x00ff00);   // showBody, showVelocity, color
```

Turn debug off for release builds; the overlay has a real per-frame cost.
