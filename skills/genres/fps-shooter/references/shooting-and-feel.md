# FPS shooting model and feel (depth)

Detail behind `SKILL.md`. Engine-neutral pseudocode. For the camera/character body and the
raycast/physics APIs, defer to your engine 3D + physics skill; this file is the shooter glue.

Contents:
1. Hitscan versus projectile
2. Hitscan shot and per-engine ray query rules
3. Damage falloff
4. Spread and recoil
5. Time-to-kill
6. Hit registration and lag compensation
7. Enemy AI states (single-player)

## 1. Hitscan vs. projectile

| | Hitscan | Projectile |
|---|---|---|
| Travel | Instant ray to target | Object flies over time |
| Player skill | Pure aim/flick | Leading, prediction, arcs |
| Feel | Crisp, precise (rifles, pistols) | Dodgeable, readable (rockets, plasma) |
| Cost | One raycast per shot | Spawn + per-frame move + collision |
| Range design | Add damage falloff to limit reach | Speed/lifetime limit reach naturally |
| Counterplay | Cover, peeking | Dodging, sidestepping |

Many shooters mix both: hitscan for hip-fire/automatics, projectiles for heavies and lobs.
Slow projectiles enable big readable fights; hitscan rewards precision but can feel "unfair"
at long range without falloff.

## 2. Hitscan shot

```python
# Pseudocode. Cast from the camera along its forward vector; the first hit takes damage.
origin    = camera.world_position
direction = camera.forward
direction = apply_spread(direction, current_spread)     # see §4
hit = raycast(origin, direction, max_dist=RANGE, mask=SHOOTABLE, exclude=[shooter])
if hit:
    dmg = base_damage * falloff(hit.distance)           # see §3
    if hit.is_head: dmg *= HEADSHOT_MULT                # e.g. 2.0
    hit.actor.take_damage(dmg)
    spawn_impact_fx(hit.point, hit.normal)              # decal + particles = feedback
```

Engine query details that silently drop hits (check these before tuning anything):

| | Godot 4.7 (`PhysicsRayQueryParameters3D`) | Unity 6.3 (`Physics.Raycast`) |
|---|---|---|
| Skip the shooter | `exclude = [shooter.get_rid()]` or a `collision_mask` without the player layer | a `layerMask` without the player layer |
| Trigger / area volumes | `Area3D` is ignored unless `collide_with_areas = true` (hitboxes built from areas need it) | triggers **are** hit while the project's *Queries Hit Triggers* setting is on (the default), so pickup and zone triggers stop bullets; pass `QueryTriggerInteraction.Ignore` per shot, or `Collide` if your hitboxes are triggers |
| Ray starting inside a collider | not reported unless `hit_from_inside = true` | that collider is not hit |

Third-person or muzzle-blocked shots: cast from the camera to find the aim point, then from the
muzzle to that point, so cover directly in front of the gun still blocks the bullet.

## 3. Damage falloff (range limiting for hitscan)

```python
# Full damage up to a near distance, then lerp down to a floor by a far distance.
def falloff(d, near=20.0, far=60.0, min_mult=0.4):
    if d <= near: return 1.0
    if d >= far:  return min_mult
    t = (d - near) / (far - near)
    return lerp(1.0, min_mult, t)
```

## 4. Spread and recoil

- **Spread** is randomized inaccuracy (a cone). It grows while firing/moving and shrinks while
  still/aiming. Good for automatics; keep the first shot accurate so single taps feel precise.
- **Recoil** is a (often patterned) camera kick. A *fixed* pattern is learnable and skill-based;
  pure random recoil feels bad. Recover toward the original aim over time.

```python
# Spread: a random direction inside a cone whose half-angle = spread_rad.
# Picking yaw and pitch independently fills a square, not a cone (corners reach 1.41x spread).
def apply_spread(dir, spread_rad):
    r     = spread_rad * sqrt(rng.float01())   # sqrt -> hits uniform over the disc
    theta = rng.float01() * TAU                # drop the sqrt for a centre-weighted pattern
    return rotate(dir, yaw=r * cos(theta), pitch=r * sin(theta))

# Keep recoil as an offset on top of the player's look, so recovery never fights the mouse.
def on_fire():
    recoil_offset += recoil_pattern[min(shot_index, len(recoil_pattern) - 1)]  # learnable kick
    shot_index += 1
    current_spread = min(current_spread + SPREAD_PER_SHOT, MAX_SPREAD)
def tick(dt):
    current_spread = max(BASE_SPREAD, current_spread - SPREAD_RECOVER * dt)
    recoil_offset  = move_toward(recoil_offset, 0.0, RECOIL_RECOVER * dt)
    if time_since_last_shot > PATTERN_RESET: shot_index = 0     # pattern restarts per burst
    # look_pitch comes only from mouse/stick input; positive = up here, check your engine's sign.
    camera.pitch = clamp(look_pitch + recoil_offset, -MAX_PITCH, MAX_PITCH)   # e.g. ±89°
```

## 5. Time-to-kill (TTK) — the master balance lever

```
shots_to_kill = ceil(target_hp / damage_per_shot)
TTK_seconds   = (shots_to_kill - 1) / fire_rate_per_second   # first shot at t=0
```

- **Low TTK** (fast kills): positioning/first-shot advantage dominate; twitchy, less forgiving.
- **High TTK**: tracking/sustained aim and team play matter; more time to react and reposition.
- Tune `damage_per_shot`, `fire_rate`, and `target_hp` together — they are one system. Headshot
  multipliers create a skill-based *faster* TTK without lowering the body TTK.

## 6. Hit registration and (multiplayer) lag

- **Single-player:** raycast on the same frame as input; no networking concerns.
- **Multiplayer:** the shooter and the target see slightly different worlds. Common server-side
  approach is **lag compensation** — the server rewinds other actors to where the shooter saw
  them (using the shooter's timestamp/ping) before testing the hit. This is hard; for networking
  plumbing defer to the engine multiplayer skill and keep authority on the server.

## 7. Enemy AI states (single-player)

A small state machine covers most PvE shooters:

```
IDLE/PATROL --(sees player)--> ALERT --(in range)--> ATTACK
ATTACK --(lost line of sight)--> SEARCH(last known pos) --(timeout)--> PATROL
any --(took damage from unseen)--> ALERT (turn toward source)
```

Use cover queries, burst-fire with reload pauses, and a reaction delay so enemies feel fair.
Make the first one or two shots of an engagement miss on purpose (offset the aim point by a
shrinking amount), and telegraph heavy attacks with a wind-up sound or flash, so the player
learns where damage comes from instead of dying to a sudden perfect burst.
Implement the tree/FSM with `game-ai` and the engine's navigation (`unity-navmesh`,
`unreal-behavior-trees`, Godot navigation).
