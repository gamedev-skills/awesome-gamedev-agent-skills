---
name: bevy-ecs
description: >
  Builds and debugs Bevy 0.20 games in Rust: components, Query and Commands systems, schedules,
  States, observers and headless tests. Use when Cargo.toml depends on bevy, on a B0001
  query-conflict panic, or pre-0.20 code (EventReader, SpriteBundle). Not for engine-neutral AI,
  generation, physics or shaders (`game-ai`, `procedural-gen`, `physics-tuning`,
  `shader-programming`).
---

# Bevy ECS

Structure and debug a Bevy game around its ECS. New code targets **Bevy 0.20** (`bevy =
"0.20"`, which resolves to the latest 0.20.x patch). Bevy breaks APIs in every minor
release, so the version the project pins decides which syntax is right.

## When to use

- Wiring an `App`, defining components and resources, writing systems, ordering them,
  gating them on state or timers, or passing data with messages and observers.
- Fixing query-conflict panics, entities that seem missing, order bugs, or code copied from
  an older Bevy release.

**When not to use:** rendering pipelines, custom shaders, UI layout and audio are outside
this skill; AI and generation algorithms go to `game-ai` / `procedural-gen`.

## Workflow

1. **Read the pinned version first.** `Cargo.toml` gives the requirement and `Cargo.lock`
   the resolved `bevy` version. Keep it; a minor-release migration is a separate task that
   follows that release's migration guide. Never mix snippets from two minors.
2. **Model the data.** Per-entity data is a `#[derive(Component)]`; one-of-a-kind data
   (score, settings) is a `#[derive(Resource)]`. Spawn entities as tuples of components;
   required components fill in the rest (`commands.spawn(Camera2d)` adds `Transform`,
   `Camera` and friends).
3. **Write systems as plain functions** whose parameters declare access: `Query<D, F>`,
   `Res`/`ResMut`, `Commands`, `MessageReader`/`MessageWriter`, `Single`. Systems with
   non-conflicting access run in parallel, in no guaranteed order.
4. **Order only what must be ordered** (`.chain()`, `.before`/`.after`, `SystemSet`s) and
   gate with `run_if`. Group features into `Plugin`s. Scale motion by `time.delta_secs()`
   or put it in `FixedUpdate`.
5. **Verify.** Run `cargo check`, then `cargo test` with a headless `App` test (pattern
   below) for each rule you changed, then `cargo run` and read the first panic: Bevy
   reports conflicting system parameters when a schedule first runs, with an error code
   and a link. Report which of these you ran; a clean `cargo check` proves only that it
   compiles. When the change is visual, ask the user to run the game and report what they
   see.

## Patterns

### Spawning and filtering

```rust
#[derive(Component)]
struct Player;
#[derive(Component)]
struct Velocity(Vec2);

fn setup(mut commands: Commands) {
    commands.spawn(Camera2d);
    commands.spawn((Player, Velocity(Vec2::new(150.0, 0.0)), Transform::default()));
}

fn move_players(time: Res<Time>, mut q: Query<(&Velocity, &mut Transform)>) {
    for (v, mut t) in &mut q {
        t.translation += v.0.extend(0.0) * time.delta_secs();
    }
}

// Two &mut Transform queries in one system must be provably disjoint.
fn separate(
    mut players: Query<&mut Transform, With<Player>>,
    mut others: Query<&mut Transform, Without<Player>>,
) { /* ... */ }
```

### Ordering, run conditions, plugins

```rust
struct GameplayPlugin;
impl Plugin for GameplayPlugin {
    fn build(&self, app: &mut App) {
        app.insert_resource(Score(0))
            .add_systems(Startup, setup)
            // damage must resolve before deaths are checked
            .add_systems(Update, (apply_damage, check_deaths).chain())
            .add_systems(Update, spawn_wave.run_if(in_state(AppState::Playing)));
    }
}
```

### Headless test (the check to run)

`MinimalPlugins` gives time and a schedule runner with no window or GPU, so this runs under
plain `cargo test`. Drive time by hand to make movement deterministic.

```rust
#[cfg(test)]
mod tests {
    use super::*;
    use bevy::time::TimeUpdateStrategy;
    use std::time::Duration;

    #[test]
    fn player_moves_at_its_velocity() {
        let mut app = App::new();
        app.add_plugins(MinimalPlugins)
            .insert_resource(TimeUpdateStrategy::ManualDuration(Duration::from_millis(100)))
            .add_systems(Update, move_players);
        let id = app.world_mut().spawn((Velocity(Vec2::X * 10.0), Transform::default())).id();
        for _ in 0..5 {
            app.update();
        }
        // The first update has a zero delta, so 5 updates advance 4 x 0.1 s.
        let x = app.world().get::<Transform>(id).unwrap().translation.x;
        assert!((x - 4.0).abs() < 1e-4, "x = {x}");
    }
}
```

For whole-world assertions use `app.world_mut().query_filtered::<&Health, With<Player>>()`
and `.single(world)`. States need `bevy::state::app::StatesPlugin` next to `MinimalPlugins`.

## Gotchas

- **Panic `error[B0001]: Query<…> in system … accesses component(s) Transform in a way
  that conflicts with a previous system parameter`** → two queries in one system can both
  reach the same component mutably. Make them disjoint with `With`/`Without`, or use
  `ParamSet`.
- **`Query<EntityMut>` (or a broad `Query<Entity>` despawn loop) next to a `Res<T>`
  panics** → since 0.19 every resource lives on an entity tagged `IsResource`, so broad
  queries match resources too. The error is `B0002` when the `Res` comes after the query
  and `B0001` when it comes first. Query your own marker, or add `Without<IsResource>`
  (`use bevy::ecs::resource::IsResource`).
- **"conflicting implementations of trait `Component`"** after deriving `Resource` and
  `Component` on one type → since 0.19 `Resource` implies `Component`; derive `Resource`
  alone.
- **A spawned entity is missing from a query in the same system** → `Commands` are
  deferred to the next sync point. Read it in a later system, or order the reader after
  the spawner.
- **Something works only by luck of system order** → unordered systems run in an
  arbitrary but stable order, which an unrelated change can reshuffle. Add a real
  constraint, and shake out hidden ones in tests with `ScheduleBuildSettings::shuffle_seed`
  (0.20, `debug` feature; see the reference).
- **Headless test sees no movement on the first update** → the first `app.update()` has a
  zero delta. Run one extra update or assert on N−1 steps, as in the test above.
- **`delta_seconds()` not found** → renamed to `delta_secs()` / `elapsed_secs()` in 0.15;
  the old names are gone.
- **`Camera2dBundle` / `SpriteBundle` not found** → bundles were removed in 0.16. Spawn
  the components (`Camera2d`, `Sprite`, `Transform`) and let required components fill in.
- **`EventReader` / `EventWriter` / `add_event` not found** → buffered events became
  messages: `#[derive(Message)]`, `MessageReader`, `MessageWriter::write`,
  `app.add_message::<T>()`. Push-style events use `#[derive(Event)]` with observers.
- **`On<Add, Player>`: "struct takes 1 generic argument but 2 generic arguments were
  supplied"** → 0.20 moved the component into the lifecycle event: `On<Add<Player>>`
  (also `Insert<T>`, `Discard<T>`, `Remove<T>`, `Despawn<T>`).
- **`Pointer<Click>` not found in a picking observer** → 0.20 flattened pointer events:
  observe `On<PointerClick>` / `On<PointerPress>` and read `click.pointer.position`
  (a `Vec2`).
- **`OnExit`/`OnEnter` run when "switching" to the current state** → `NextState::set`
  always transitions. Use `set_if_different` (0.20 name). The old `set_if_neq` now
  resolves to an unrelated change-detection method and fails with "can't compare
  `NextState<S>`".
- **"`text` does not live long enough" from `Name::new(text.as_str())`** → since 0.20
  `Name` takes a `&'static str` or an owned `String`: `Name::new(format!("Enemy {id}"))`.
- **Overlapping sprites swap draw order after moving to 0.20** → sprites render through the
  `Mesh2d` path and equal-`z` order was never guaranteed. Give overlapping sprites distinct
  `z` values.

## References

- Read `references/queries-and-scheduling.md` when the task needs more than the patterns
  above: query filters and `single()`, `iter_many` results, `ParamSet`, schedules and
  `SystemSet`s, 0.20 weak ordering and schedule shuffling, `States` with `DespawnOnExit`,
  change detection and summary ticks, the `Commands` lifecycle and `despawn_all`, exclusive
  `&mut World` systems, and message/observer syntax.

## Related skills

- `game-ai`, `procedural-gen` — portable algorithms to implement as systems.
- `physics-tuning` — fixed-step and collision feel; `shader-programming` — shader technique.
- `pygame-core`, `love2d-core` — lighter engines for small projects.

## Version notes

Last verified: 2026-11-11.

- Bevy 0.20.0 shipped on 2026-10-08 and 0.20.1 on 2026-10-28. 0.20.1 is a maintenance
  release (bug fixes, no API changes this skill relies on); 0.19.0 shipped 2026-06-19.
- Every 0.20 API in this skill and its reference, the panic texts in Gotchas and the
  headless test were compiled and run against `bevy = "=0.20.1"` (default features off,
  `bevy_state`, `bevy_log`, `debug`) with Rust 1.99. `Camera2d`, `Sprite` and pointer
  events were checked against the release notes and migration guide only.
- Sources: [crates.io bevy](https://crates.io/crates/bevy),
  [v0.20.1 release](https://github.com/bevyengine/bevy/releases/tag/v0.20.1),
  [Bevy 0.20 release notes](https://bevy.org/news/bevy-0-20/),
  [0.19 to 0.20 migration guide](https://bevy.org/learn/migration-guides/0-19-to-0-20/).
