---
name: phaser-arcade-physics
description: >
  Phaser 4 Arcade Physics movement and collision: bodies, velocity, gravity, colliders vs
  overlaps, groups and bullet pools. Use for a Phaser platformer or top-down controller, or a
  sprite that ignores physics, onFloor() always false or bodies passing through walls. Not for
  scenes and the loader (`phaser-core`), coyote time (`platformer`) or tunnelling theory
  (`physics-tuning`).
---

# Phaser 4 Arcade Physics

Moves and collides sprites with Phaser's Arcade engine: axis-aligned rectangles and circles,
no rotation in collision, no joints. That is enough for most platformers, shooters and
top-down games, and it is fast. New projects target **Phaser 4.2**; check the installed major
before editing an existing project. If the game needs hinges, springs, slopes or rotated
polygons, Matter physics is the separate engine for that, and its bodies never collide with
Arcade bodies.

## When to use

- Platformer or top-down movement, gravity, bouncing, world bounds, and collision or overlap
  between sprites, groups and tilemap layers.
- The config has `physics: { default: 'arcade' }`, or code calls `this.physics.add.*`,
  `body.setVelocity` or `this.physics.add.collider`.
- Not for scene structure and loading (`phaser-core`), jump-feel rules such as coyote time
  (`platformer`), or fixed timestep and tunnelling in general (`physics-tuning`).

## Workflow

1. **Enable the world with debug drawing on**: `physics: { default: 'arcade', arcade: {
   gravity: { x: 0, y: 600 }, debug: true } }`. Body outlines and velocity lines answer most
   "why didn't it collide" questions at a glance. Turn debug off before release.
2. **Create bodies through the physics factory**: `this.physics.add.sprite` (dynamic),
   `this.physics.add.staticImage` or `staticGroup` (walls and ground), or
   `this.physics.add.existing(obj)` for an object you already made.
3. **Move dynamic bodies through the body** with velocity, acceleration and gravity. Writing
   `x`/`y` directly teleports the body past colliders.
4. **Register each `collider` and `overlap` once in `create`.** A collider separates bodies;
   an overlap only reports contact (pickups, triggers, hurtboxes).
5. **Use groups** so one collider covers many objects, and pool projectiles with `maxSize`.
6. **Verify** with the probe in [Verify](#verify).

## Patterns

### 1. Enable Arcade Physics

```js
const config = {
  type: Phaser.AUTO,
  width: 800,
  height: 600,
  physics: {
    default: 'arcade',
    arcade: {
      gravity: { x: 0, y: 600 }, // top-down games use { x: 0, y: 0 }
      debug: true,               // body outlines and velocity while building
    },
  },
  scene: [PlayScene],
};
```

### 2. Top-down movement

```js
update() {
  const speed = 220;
  const body = this.player.body;
  body.setVelocity(0);
  if (this.cursors.left.isDown) body.setVelocityX(-speed);
  if (this.cursors.right.isDown) body.setVelocityX(speed);
  if (this.cursors.up.isDown) body.setVelocityY(-speed);
  if (this.cursors.down.isDown) body.setVelocityY(speed);
  body.velocity.normalize().scale(speed); // diagonals at the same speed (zero stays zero)
}
```

### 3. Platformer with a ground check

```js
create() {
  this.platforms = this.physics.add.staticGroup();
  this.platforms.create(400, 568, 'ground');

  this.player = this.physics.add.sprite(100, 450, 'player');
  this.player.setCollideWorldBounds(true);
  this.player.body.setSize(20, 36, true); // hitbox tighter than the art, centred

  this.physics.add.collider(this.player, this.platforms); // once, here
  this.cursors = this.input.keyboard.createCursorKeys();
}

update() {
  const onGround = this.player.body.blocked.down; // same as body.onFloor()
  const dir = (this.cursors.right.isDown ? 1 : 0) - (this.cursors.left.isDown ? 1 : 0);
  this.player.setVelocityX(dir * 160);
  if (this.cursors.up.isDown && onGround) this.player.setVelocityY(-450);
}
```

### 4. Collider vs overlap

```js
// Push apart, then react.
this.physics.add.collider(this.player, this.enemies, (player, enemy) => this.hurt(player, enemy));

// Detect only. The optional 4th argument returns false to skip a pair before the callback.
this.physics.add.overlap(this.player, this.coins, (player, coin) => {
  coin.disableBody(true, true); // deactivate and hide; the group can reuse it
  this.registry.inc('score', 10);
});
```

### 5. Pooled projectiles

```js
create() {
  this.bullets = this.physics.add.group({ defaultKey: 'bullet', maxSize: 30 });
}

fire(x, y) {
  const bullet = this.bullets.get(x, y); // an inactive member, or a new one under maxSize
  if (!bullet) return;                   // every bullet is in flight
  bullet.enableBody(true, x, y, true, true);
  bullet.body.setAllowGravity(false);
  bullet.setVelocityY(-500);
}

update() {
  // Return off-screen bullets to the pool, or firing stops after 30 shots.
  for (const bullet of this.bullets.getChildren()) {
    if (bullet.active && bullet.y < -32) bullet.disableBody(true, true);
  }
}
```

## Verify

1. `npm run build` (or `npx tsc --noEmit`) passes.
2. Probe the running game. If `phaser-core`'s headless smoke script is in use, put this body
   in its `page.evaluate(() => { ... })` after a two-second wait, adjusting the scene key and
   object names:

```js
const s = window.game.scene.getScene('play');
return {
  bodies: s.physics.world.bodies.size,          // dynamic bodies alive
  staticBodies: s.physics.world.staticBodies.size,
  playerOnFloor: s.player.body.blocked.down,    // true once the player has landed
  playerY: Math.round(s.player.y),
};
```

   Expect `playerOnFloor: true` and a `playerY` resting on the ground for a platformer, and a
   body count that stays flat while firing (the pool is recycling).
3. With `debug: true`, take a screenshot and check that hitboxes sit on the art. Without
   browser automation, ask the user to run with `debug: true` and report whether the outlines
   match the sprites and where the player stops.

## Gotchas

- **Sprite ignores physics** → it was made with `this.add.sprite`, so it has no body. Use
  `this.physics.add.sprite` or `this.physics.add.existing(obj)`.
- **`onFloor()` is always false** → nothing to land on: add the `collider` with the ground,
  and check gravity is on. Landing on an ordinary dynamic body does not set `blocked`; make
  platforms static, immovable (`setImmovable(true)`) or non-pushable (`setPushable(false)`).
- **The player shoves platforms around** → they are dynamic bodies; use a `staticGroup`, or
  `setImmovable(true)` for moving platforms.
- **A static body moved but collides at the old spot** → static bodies do not follow their
  game object. Call `body.updateFromGameObject()` (or `refreshBody()` on the object).
- **Fast bullets pass through thin walls** → Arcade has no swept collision, so a body that
  moves farther than a wall's thickness in one step skips it. Thicken the wall's body, cap
  speed with `setMaxVelocity`, or raise `arcade.fps` above its default 60 at CPU cost.
- **Bodies stop colliding after you add a collision category** → a pair collides only when
  each side's mask contains the other's category, and untouched bodies keep mask `1`. Widen
  the other side's mask too, and set a group and its members separately (see the reference).
- **Drag does nothing while a key is held** → Arcade applies drag only on an axis with zero
  acceleration; set acceleration to 0 when input stops.
- **Colliders multiply and the game slows down** → `collider`/`overlap` was called in
  `update`, adding a new one every frame. Register once in `create`; disable with
  `collider.active = false`.
- **The pool stops handing out bullets** → members were hidden but never disabled, so they
  still count as active. Recycle with `disableBody(true, true)`.

## References

- Read [`references/bodies-and-collision.md`](references/bodies-and-collision.md) when tuning
  drag, bounce or max velocity, shaping hitboxes with `setSize`/`setCircle`/`setOffset`,
  filtering pairs with collision categories or a process callback, reading `touching` vs
  `blocked`, or listening for `worldbounds` events.

## Related skills

- `phaser-core`: game config, scenes, loader and cameras.
- `platformer`: coyote time, jump buffering, variable jump height and level structure.
- `physics-tuning`: engine-neutral feel, timestep, tunnelling and jitter.
- `level-design`: the tile and platform layouts these bodies collide with.

## Version notes

Last verified: 2026-11-11 against Phaser 4.2.1 (npm `latest`, published 2026-07-09).

- Checked in the v4.2.1 source: `arcade.fps` defaults to 60 and `fixedStep` to true; bodies,
  static bodies and static groups start in category 1 with mask 1; a dynamic group's mask is
  all bits; `nextCategory()` allows 32 categories; drag applies only at zero acceleration.
- Sources: [Arcade World.js](https://github.com/phaserjs/phaser/blob/v4.2.1/src/physics/arcade/World.js),
  [Arcade Body.js](https://github.com/phaserjs/phaser/blob/v4.2.1/src/physics/arcade/Body.js),
  `npm view phaser dist-tags`.
