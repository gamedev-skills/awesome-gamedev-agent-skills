---
name: bevy-ecs
description: >
  Structure a Bevy app around its Entity Component System: build the App with
  plugins, define Component/Resource types, write systems with Query/Res/Commands,
  filter and order systems, and use the Time resource for frame-rate-independent
  motion. Use when building or debugging a Bevy game in Rust — when the user
  mentions Bevy, ECS, App::new, add_systems, Query, Commands, components/systems,
  or a Cargo.toml depending on bevy.
---

# Bevy ECS

Structure a Bevy game in Rust around the Entity Component System: the `App` and
plugins, components and resources, systems with queries, scheduling, and
frame-rate-independent updates. New examples target **Bevy 0.20**. If the project
already pins another release, keep that release and use its matching migration guide.

## When to use

- Use when wiring a Bevy `App`, defining `Component`/`Resource` types, writing
  systems that query entities, ordering/filtering systems, or fixing
  borrow-conflict panics and frame-dependent movement.
- Use when `Cargo.toml` depends on `bevy` and code calls `App::new()`,
  `add_systems`, `Query`, or `Commands`.

**When *not* to use:** this is the ECS core. Deep rendering, custom shaders/
pipelines, UI layout, and audio are separate concerns. For engine-agnostic AI or
procedural algorithms, pair with `game-ai` / `procedural-gen`.

## Core workflow

1. **Detect and pin the version.** Read `Cargo.toml` and `Cargo.lock` first. For a
   new project use `bevy = "0.20"`; never silently migrate an existing project
   across a Bevy minor release. Treat the matching docs and migration guides as truth.
2. **Build the `App`.** `App::new().add_plugins(DefaultPlugins)` gives windowing,
   input, rendering, time, etc. Register systems into schedules: `Startup` (once)
   and `Update` (every frame).
3. **Model data as components, globals as resources.** `#[derive(Component)]` for
   per-entity data; `#[derive(Resource)]` for one-of-a-kind data (score, settings,
   the `Time` clock). Since 0.19 `Resource` extends `Component` and each resource is
   stored on its own entity, so do not derive both.
4. **Write systems as plain functions.** Parameters declare data access: `Query<...>`
   for entities, `Res<T>`/`ResMut<T>` for resources, `Commands` for deferred
   spawn/despawn. Systems run in parallel when their accesses don't conflict.
5. **Drive motion by `time.delta_secs()`** so speed is frame-rate independent.
6. **Order only what must be ordered** with `.chain()` or explicit constraints;
   gate systems with `run_if`. Group related setup into `Plugin`s. Build with
   `cargo run` and read the panics — Bevy reports conflicting queries at startup.

## Patterns

### 1. Cargo.toml + minimal App

```toml
# Cargo.toml — pin the version; the API differs across minor releases.
[dependencies]
bevy = "0.20"
```

```rust
// main.rs
use bevy::prelude::*;

fn main() {
    App::new()
        .add_plugins(DefaultPlugins)            // window, input, render, time, ...
        .add_systems(Startup, setup)            // runs once at startup
        .add_systems(Update, move_players)      // runs every frame
        .run();
}
```

### 2. Components, resources, and spawning

```rust
#[derive(Component)]
struct Player;

#[derive(Component)]
struct Velocity(Vec2);

#[derive(Resource)]
struct Score(u32);

fn setup(mut commands: Commands) {
    commands.insert_resource(Score(0));

    // Camera2d is a component with required components (bundles removed in 0.16);
    // spawning it pulls in Transform, Camera, etc. automatically.
    commands.spawn(Camera2d);

    // Spawn an entity as a tuple of components.
    commands.spawn((
        Player,
        Velocity(Vec2::new(150.0, 0.0)),
        Transform::from_xyz(0.0, 0.0, 0.0),
    ));
}
```

### 3. A system with a query + the Time resource

```rust
// Iterate every entity that has BOTH Velocity and Transform; mutate Transform.
fn move_players(time: Res<Time>, mut query: Query<(&Velocity, &mut Transform)>) {
    for (velocity, mut transform) in &mut query {
        // delta_secs() is f32 seconds (renamed from delta_seconds() in 0.16).
        transform.translation += velocity.0.extend(0.0) * time.delta_secs();
    }
}
```

### 4. Query filters (With / Without / Changed)

```rust
// Only entities tagged Player (the Player component itself isn't read).
fn aim_player(mut q: Query<&mut Transform, With<Player>>) { /* ... */ }

// Disjoint two mutable Transform queries so they don't conflict at runtime.
fn separate(
    mut players: Query<&mut Transform, With<Player>>,
    mut enemies: Query<&mut Transform, Without<Player>>,
) { /* ... */ }

// React only when Health changed since last run (change detection).
fn on_health_change(q: Query<&Health, Changed<Health>>) {
    for health in &q { /* update the HUD, etc. */ }
}
```

### 5. Resources: read and write

```rust
fn add_points(mut score: ResMut<Score>) {
    score.0 += 10;                 // ResMut = write access
}

fn show_score(score: Res<Score>) {
    info!("score: {}", score.0);   // Res = read access
}
```

### 6. Ordering, run conditions, and plugins

```rust
fn main() {
    App::new()
        .add_plugins((DefaultPlugins, GameplayPlugin))
        // .chain() forces order: damage resolves before death is checked.
        .add_systems(Update, (apply_damage, check_deaths).chain())
        // run_if gates a system on a condition each frame.
        .add_systems(Update, spawn_wave.run_if(wave_timer_finished))
        .run();
}

struct GameplayPlugin;
impl Plugin for GameplayPlugin {
    fn build(&self, app: &mut App) {
        app.insert_resource(Score(0))
           .add_systems(Startup, setup)
           .add_systems(Update, (move_players, add_points));
    }
}
```

## Pitfalls

- **`delta_seconds()` not found** → it was renamed to `time.delta_secs()` (and
  `elapsed_secs()`) in 0.16. Using the old name fails to compile.
- **Movement speed scales with frame rate** → multiply per-frame changes by
  `time.delta_secs()`. Never assume a fixed frame time.
- **Panic `error[B0001]`: "... accesses component(s) Transform in a way that conflicts
  with a previous system parameter"** → two `Query`s in one system both write the same
  component, or one reads while another writes overlapping entities. Make them disjoint
  with `With`/`Without`, or use `ParamSet`.
- **`Camera2dBundle`/`SpriteBundle` not found** → bundles were deprecated in 0.15 and
  removed in 0.16.
  Spawn the components directly (`Camera2d`, `Sprite`, `Transform`); required
  components fill in the rest.
- **"trait `Component` is not implemented"** → you forgot `#[derive(Component)]`
  (or `#[derive(Resource)]` for a resource).
- **Spawned entity not visible to a later query in the same frame** → `Commands` are
  deferred and applied at the next sync point. Read the entity in a subsequent system,
  not the one that spawned it.
- **System order assumed but not enforced** → systems run in parallel by default.
  If `B` must follow `A`, add `(A, B).chain()` or an explicit ordering constraint.
  To find order dependencies that only work by accident, shuffle the schedule in tests
  with `ScheduleBuildSettings::shuffle_seed` (0.20, `debug` feature; see the reference).
- **"conflicting implementations of trait `Component`" after deriving both `Resource`
  and `Component`** → since 0.19 `Resource` extends `Component`; derive `Resource` alone.
- **"Despawn everything" panics, or `Query<EntityMut>` next to a `Res<T>` panics with
  `error[B0002]`** → since 0.19 every resource lives on an entity tagged `IsResource`,
  so `Query<Entity>`/`EntityRef`/`EntityMut` match those entities too. Query your own
  marker component, or add `Without<IsResource>` (`use bevy::ecs::resource::IsResource`).
- **`On<Add, Player>` fails with "struct takes 1 generic argument but 2 generic
  arguments were supplied"** → 0.20 moved the component into the lifecycle event:
  write `On<Add<Player>>` (likewise `Insert<T>`, `Discard<T>`, `Remove<T>`, `Despawn<T>`).
- **`OnExit`/`OnEnter` run again when "switching" to the current state** →
  `NextState::set` always runs the transition schedules. Use `set_if_different` to skip
  same-state transitions (renamed from `set_if_neq` in 0.20; calling `set_if_neq` on a
  `ResMut<NextState<_>>` picks up the unrelated change-detection method and fails with
  "can't compare `NextState`").
- **"`text` does not live long enough" from `Name::new(text.as_str())`** → since 0.20
  `Name` takes a `&'static str` literal or an owned `String`, not a borrowed `&str`;
  pass `Name::new(text.clone())` or `Name::new(format!("Enemy {id}"))`.
- **Overlapping sprites swap draw order after upgrading to 0.20** → sprites now render
  through the `Mesh2d` backend, and draw order at equal `z` was never guaranteed. Give
  sprites that can overlap distinct `Transform` z values.
- **Copy-pasting older Bevy snippets** → APIs shift between minor versions. The
  buffered event system became the message system: `EventReader`/`EventWriter`/
  `add_event` no longer exist, so use `#[derive(Message)]`, `MessageReader`/
  `MessageWriter`, and `app.add_message::<T>()`. Verify against the docs and migration
  guide for *your* pinned version; don't mix versions.

## References

- For schedules and `SystemSet` ordering (including 0.20 weak ordering and schedule
  shuffling), `States`/`OnEnter`/`OnExit` and state-scoped despawning, change
  detection, `Commands` lifecycle and sync points, `ParamSet` and resource-entity
  conflicts, `iter_many` results, and messages/observers in 0.20 syntax, read
  `references/queries-and-scheduling.md`.

## Related skills

- `game-ai` — FSMs/behavior trees/steering as portable concepts to implement in ECS.
- `procedural-gen` — noise/RNG/generation algorithms to drive from systems.
- `pygame-core` / `love2d-core` — lighter-weight engines for smaller projects.
