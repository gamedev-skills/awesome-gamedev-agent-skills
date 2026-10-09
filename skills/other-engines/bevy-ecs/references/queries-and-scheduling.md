# Bevy queries & scheduling detail (0.20)

Depth behind the ECS skill: query filters and access, schedules and ordering,
states, change detection, and the `Commands` lifecycle. Verify any borderline API
against the docs for your pinned Bevy version — minor releases move things.

## Query anatomy

A `Query<D, F>` has a **data** part `D` (what you read/write) and an optional
**filter** part `F` (which entities, without fetching their data).

```rust
// Data: read Name, write Transform. Filter: must have Player, must NOT have Frozen.
Query<(&Name, &mut Transform), (With<Player>, Without<Frozen>)>
```

Common filters:

- `With<T>` / `Without<T>` — entity has / lacks a component (no data fetched).
- `Added<T>` — `T` was added since this system last ran.
- `Changed<T>` — `T` was added or mutably accessed since last run (change detection).
- `Or<(...)>` — combine filters disjunctively.

Optional and entity access in the data part:

```rust
Query<(Entity, &Transform, Option<&Velocity>)>  // Entity id; Velocity may be absent
```

### Single-entity access

For a query you expect to match exactly one entity (e.g. the player), `single()`
and `single_mut()` return a `Result` in 0.16+ (they replaced the older
`get_single`/panicking `single`):

```rust
fn read_player(q: Query<&Transform, With<Player>>) {
    if let Ok(transform) = q.single() {
        // exactly one Player matched
    }
}
```

Iterating with `for x in &query` is always valid and the safest default.

### Many-entity access (0.20)

`iter_many`, `iter_many_mut`, and their `unique`/`par_` variants take a list of
entities and, since 0.20, yield `Result<Item, QueryEntityError>`: an entity that was
despawned or doesn't match the query is an `Err`, not silently skipped.

```rust
#[derive(Component)]
struct Health(f32);

#[derive(Resource)]
struct Targets(Vec<Entity>);

fn check_targets(targets: Res<Targets>, q: Query<&Health>) {
    for result in q.iter_many(targets.0.iter()) {
        match result {
            Ok(health) => { /* ... */ }
            Err(err) => warn!("stale target: {err}"),
        }
    }
}

// .matched() keeps the pre-0.20 behaviour of skipping missing entities.
fn heal_targets(targets: Res<Targets>, mut q: Query<&mut Health>) {
    let mut iter = q.iter_many_mut(targets.0.iter()).matched();
    while let Some(mut health) = iter.fetch_next() {
        health.0 += 1.0;
    }
}
```

## Avoiding conflicting access

Two systems can run in parallel only if their data accesses don't conflict. Two
queries **within one system** that both mutably touch the same component will panic
at startup. Fixes:

1. **Disjoint with filters** — `With<Player>` vs `Without<Player>` guarantees the
   sets never overlap, so both can be `&mut`.
2. **`ParamSet`** — when sets *can* overlap, access them one at a time:

```rust
fn swap(mut set: ParamSet<(
    Query<&mut Transform, With<A>>,
    Query<&mut Transform, With<B>>,
)>) {
    for mut t in &mut set.p0() { /* ... */ }
    for mut t in &mut set.p1() { /* ... */ }
}
```

3. **Resource entities** — since 0.19 each resource is stored on an entity tagged
   `IsResource`, so broad queries (`Query<Entity>`, `Query<EntityRef>`,
   `Query<EntityMut>`) match those entities too. `Query<EntityMut>` next to any
   `Res<T>` panics with `error[B0002]`, and despawning every entity a `Query<Entity>`
   returns panics. Query a marker component instead, or exclude resources:

```rust
use bevy::ecs::resource::IsResource; // not in the prelude

fn inspect(entities: Query<EntityMut, Without<IsResource>>, score: Res<Score>) { /* ... */ }
```

## Schedules and ordering

Built-in schedules you'll use most:

- `Startup` — once, before the first `Update`.
- `Update` — every frame.
- `FixedUpdate` — fixed timestep; use it for physics/gameplay that needs
  determinism (read `time.delta_secs()` here too; it's the fixed step).
- `PreUpdate` / `PostUpdate` — around `Update` for setup/teardown ordering.

Ordering within a schedule:

```rust
// Explicit pairwise order.
app.add_systems(Update, (input, movement, collision).chain());

// Named constraints.
app.add_systems(Update, movement.before(collision));
app.add_systems(Update, camera_follow.after(movement));
```

### Weak ordering (0.20)

`.chain_weak()`, `.before_weak()`, and `.after_weak()` keep an ordering only between
systems whose data access actually conflicts; systems that touch disjoint data may run
in either order or in parallel. An earlier system that queues `Commands`, and any
exclusive system, always keeps its place.

```rust
app.add_systems(Update, (tick_ai, tick_audio, tick_particles).chain_weak());
```

The scheduler can't see dependencies carried by interior mutability, channels, atomics,
or global/`NonSend` state, so keep `.chain()` for those. 0.20 also orders several
built-in sets weakly (`RenderSystems`, the `Core2d`/`Core3d` passes, and the UI
`UiSystems` in `PostUpdate`): a custom system in one of those sets that relied on an
earlier set finishing first, without a data dependency, needs an explicit `.after(...)`.

### System sets

Group systems into a `SystemSet` to order whole phases and attach shared run
conditions:

```rust
#[derive(SystemSet, Debug, Clone, PartialEq, Eq, Hash)]
enum GameSet { Input, Logic, Render }

app.configure_sets(Update, (GameSet::Input, GameSet::Logic, GameSet::Render).chain());
app.add_systems(Update, read_input.in_set(GameSet::Input));
app.add_systems(Update, (move_units, resolve).in_set(GameSet::Logic));
```

### Run conditions

```rust
use bevy::time::common_conditions::on_timer; // not in the prelude
use std::time::Duration;

app.add_systems(Update, pause_menu.run_if(in_state(AppState::Paused)));
app.add_systems(Update, autosave.run_if(on_timer(Duration::from_secs(30))));
```

### Testing for hidden order dependencies (0.20)

Systems with no ordering constraint run in an order the scheduler picks
deterministically but arbitrarily, so code can work only by accident until an unrelated
change reshuffles it. With Bevy's `debug` feature, shuffle that order in tests and try
several seeds; explicit `.before`/`.after`/`.chain` constraints are kept.

```rust
// Cargo.toml: bevy = { version = "0.20", features = ["debug"] }
use bevy::ecs::schedule::ScheduleBuildSettings;

app.edit_schedule(Update, |schedule| {
    schedule.set_build_settings(ScheduleBuildSettings {
        shuffle_seed: Some(seed), // log the seed so a failing order can be replayed
        ..default()
    });
});
```

## States

`States` model app-wide modes (menu, playing, paused). Use `OnEnter`/`OnExit`
schedules for transition logic and `in_state` to gate `Update` systems.

```rust
#[derive(States, Default, Debug, Clone, PartialEq, Eq, Hash)]
enum AppState { #[default] Menu, Playing, Paused }

app.init_state::<AppState>()
   .add_systems(OnEnter(AppState::Playing), spawn_level)
   .add_systems(OnExit(AppState::Playing), cleanup_level)
   .add_systems(Update, gameplay.run_if(in_state(AppState::Playing)));

// Transition from a system:
fn start(mut next: ResMut<NextState<AppState>>) { next.set(AppState::Playing); }

// set() always runs OnExit/OnEnter, even when the target is the current state.
// set_if_different() skips same-state transitions (0.20 name; was set_if_neq).
fn resume(mut next: ResMut<NextState<AppState>>) { next.set_if_different(AppState::Playing); }

// Despawned automatically when Playing exits; no cleanup system needed.
fn spawn_enemy(mut commands: Commands) {
    commands.spawn((Enemy, DespawnOnExit(AppState::Playing)));
}
```

## Change detection

`Changed<T>` / `Added<T>` filters and the `Ref<T>`/`Mut<T>` wrappers let systems
react only to modified data — cheaper than recomputing every frame. Note: writing
through a `&mut T` marks it changed even if the value is identical; guard with a
value check if that matters.

For a component that is checked with `Changed<T>` often but written rarely, 0.20 can
keep a per-column summary tick so unchanged columns are skipped wholesale. Every write
gets slightly more expensive, so opt in only where the queries dominate:

```rust
#[derive(Component)]
#[component(summary_tick)]
struct Inventory(Vec<u32>);
```

## Commands lifecycle

`Commands` queue structural changes (spawn, despawn, insert/remove components,
insert resources). They are **deferred** and applied at the next sync point
(end of the schedule stage), so:

- An entity spawned this frame is not in queries until a later system/stage.
- `commands.entity(e).despawn()` removes the entity; in 0.16+ this also removes its
  children (the old explicit `despawn_recursive` was folded in).
- `commands.despawn_all::<With<Enemy>>()` (0.20) despawns every matching entity in one
  batched command, faster than despawning them one at a time.

```rust
fn spawn_bullet(mut commands: Commands) {
    let id = commands.spawn((Bullet, Transform::default())).id();
    commands.entity(id).insert(Velocity(Vec2::Y * 500.0));
}
```

For immediate, exclusive access to the whole `World` (one-off setup, complex
queries), use an exclusive system `fn(&mut World)` — it can't run in parallel, so
use sparingly. Since 0.20 `&mut World` is an ordinary system parameter and no longer has
to come first: `fn snapshot(mut runs: Local<u32>, world: &mut World)` is valid.
Parameters that need their own world access still conflict with it.

## Messages and observers (0.20)

Two ways for systems to communicate:

- **Messages** are buffered and pulled: writers queue them, and each reader drains the
  new ones on its next run. Use them for per-frame streams (damage numbers, input
  actions).
- **Events + observers** are pushed: triggering an event runs every matching observer
  right away (`commands.trigger` when the commands are applied, `world.trigger`
  immediately). Use them for one-off reactions.

```rust
#[derive(Message)]
struct ScoreChanged(u32);

app.add_message::<ScoreChanged>();

fn send(mut writer: MessageWriter<ScoreChanged>) { writer.write(ScoreChanged(10)); }
fn show(mut reader: MessageReader<ScoreChanged>) {
    for msg in reader.read() { info!("+{}", msg.0); }
}
```

```rust
#[derive(Event)]
struct LevelCleared { level: u32 }

app.add_observer(|cleared: On<LevelCleared>| info!("level {} cleared", cleared.level));
fn finish(mut commands: Commands) { commands.trigger(LevelCleared { level: 3 }); }

// Entity-targeted event, observed on one entity.
#[derive(EntityEvent)]
struct Hit { entity: Entity, damage: f32 }

fn spawn_player(mut commands: Commands) {
    commands.spawn((Player, Health(10.0))).observe(|hit: On<Hit>, mut q: Query<&mut Health>| {
        if let Ok(mut health) = q.get_mut(hit.entity) { health.0 -= hit.damage; }
    });
}
fn hit(mut commands: Commands, player: Single<Entity, With<Player>>) {
    commands.trigger(Hit { entity: *player, damage: 4.0 });
}

// Component lifecycle: in 0.20 the component is the event's type parameter.
app.add_observer(|add: On<Add<Player>>| info!("player {} spawned", add.entity));
// Also Insert<T>, Discard<T>, Remove<T>, Despawn<T>.
// 0.17-0.19 wrote On<Add, Player>; 0.16 wrote Trigger<OnAdd, Player>.
```

`EventReader`, `EventWriter`, and `add_event` no longer exist. These APIs have moved in
almost every recent release, so look up the exact message/observer API for the pinned
version rather than copying an example from another one.
