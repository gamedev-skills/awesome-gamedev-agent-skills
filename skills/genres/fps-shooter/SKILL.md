---
name: fps-shooter
description: >
  Designs first-person shooter combat in any engine: hitscan vs projectiles, time-to-kill, damage
  falloff, recoil patterns, ADS sensitivity and lag-compensated hits. Use for a Doom- or
  Counter-Strike-like, or guns that feel weak or shots that do not register. Not for the camera
  rig (`camera-systems`), shake and hit-stop (`game-feel`) or raycast APIs (`godot-physics`,
  `unity-physics`).
---

# FPS shooter

Owns how shooting works and feels: the shot model, the damage and TTK numbers, recoil and
spread, fire timing, aim scaling and how enemies fight back. The engine skills supply the
controller body, raycasts and networking.

## When to use

- First-person games whose core verb is aim and shoot; also third-person shooters for the
  shot model and numbers.
- Tuning TTK, recoil, spread, falloff, fire rate or aim feel, or fixing shots that miss.

**When not to use:** camera follow, orbit and look smoothing (`camera-systems`); juice
(`game-feel`); the raycast API (`godot-physics`, `unity-physics`, `unreal-cpp-gameplay`);
replication and prediction (engine multiplayer skill, `roblox-networking` on Roblox).

## Workflow

1. **Name the reference shooter** and its TTK band: fast (tactical; body kills in about
   0.3 s, one-shot headshots on rifles), mid (military; about 0.2-0.5 s), slow (arena and hero
   shooters; about 0.8 s and up, so tracking and movement matter).
2. **Write every weapon as data** (damage by range band, head and limb multipliers, fire
   rate, magazine, reload, spread, recoil pattern) and generate a TTK table per weapon against
   each target HP (Pattern 2). Tune the table, not individual numbers.
3. **Shot model:** hitscan from the camera for bullets; projectiles for rockets, grenades and
   anything the target should dodge. Third person: ray from the camera to find the aim point,
   then from the muzzle to that point so cover in front of the gun still blocks.
4. **Fire timing on a scheduled clock** (Pattern 1), not "if enough time passed".
5. **Aim scaling:** expose FOV and sensitivity; scale sensitivity when zoomed (below).
6. **Enemies (PvE):** a reaction delay before the first shot, telegraphed attacks and
   deliberate early misses (refs §7).
7. **Check it.** Write and run tests and report the numbers:
   - the TTK table for every weapon and HP value, flagging weapons outside the chosen band;
   - fire 10 s of full-auto at a simulated 30, 60 and 144 FPS; the round counts must match
     `fire_rate * 10` within 1;
   - a shot fired from inside the player's own collider at a wall 1 m away hits the wall;
   - a shot through a trigger volume (pickup, zone) still hits the target behind it;
   - ADS sensitivity: a mouse movement that turns X degrees at hip turns X * ratio when zoomed.

## Numbers that matter

| Knob | Start here | Notes |
|------|-----------|-------|
| Headshot multiplier | 2-4x | Valorant's Vandal: 160 head, 40 body, 34 legs, no falloff, 9.75 rounds/s |
| Falloff | full to 20-30 m, floor 50-70% by 50-60 m (rifles) | shotguns and SMGs fall off much earlier |
| First-shot spread | near zero | taps must feel exact; spread grows per shot and with movement |
| Recoil | fixed pattern, mostly up then sideways, resets after ~0.3-0.5 s of no fire | learnable beats random |
| Pitch clamp | ±89° | stops the view flipping |
| FOV | 90° horizontal on PC, 70-80° on TV | Godot `Camera3D.fov` (default 75) and Unity `Camera.fieldOfView` are vertical by default |
| Enemy reaction | 0.3-0.6 s before the first shot after spotting the player | human reaction is about 0.2-0.25 s |
| Lag compensation window | cap the rewind | Source's `sv_maxunlag` defaults to 1 s |

Worked TTK: the Vandal against 150 HP kills in 4 body shots, so `(4 - 1) / 9.75 = 0.31 s`,
or one headshot at any range.

**Vertical and horizontal FOV:** `h = 2 * atan(tan(v / 2) * aspect)`. Godot's default
vertical 75° is about 107.5° horizontal at 16:9. Store the player's FOV setting as horizontal
at a reference aspect and convert, or ultrawide players get a zoomed-in view.

**ADS sensitivity:** multiply look speed by `tan(ads_fov / 2) / tan(hip_fov / 2)` (both the
same axis). The crosshair then moves across targets at the same rate on screen near the centre.

## Pattern 1: fire rate that survives low FPS

```python
# Pseudocode, per frame. Schedule shots on a clock; never reset the timer to "now".
interval = 1.0 / FIRE_RATE                     # 9.75 rounds/s -> 0.1026 s
if trigger_held and ammo > 0:
    if next_shot_time < now - interval:        # idle gap: do not bank shots
        next_shot_time = now
    while next_shot_time <= now and ammo > 0:  # several shots in one long frame
        fire(spread_for(shot_index)); ammo -= 1; shot_index += 1
        next_shot_time += interval
```

Resetting with `last_shot = now` throws away the remainder each frame, so a 600 rpm gun fires
at about 450-600 rpm depending on frame rate.

## Pattern 2: TTK table

```python
def ttk(hp, dmg_per_shot, rate):               # first shot at t = 0
    shots = ceil(hp / dmg_per_shot)
    return shots, (shots - 1) / rate

for w in weapons:
    for hp in TARGET_HPS:                      # e.g. 100, 150 (armour), boss values
        for zone, mult in (("head", w.head), ("body", 1.0), ("legs", w.legs)):
            print(w.id, hp, zone, *ttk(hp, w.damage(range_band) * mult, w.rate))
```

## Gotchas

- **Fire rate lower at low FPS** → timer reset to "now" each shot (Pattern 1).
- **Shots do nothing** → the ray hits the shooter, ignores hitboxes built from trigger or area
  volumes, or stops on an invisible trigger zone. Exclude the shooter and set the trigger rule
  per engine (refs §2 table).
- **Sensitivity changes with frame rate** → mouse delta multiplied by `dt`. Mouse delta is
  already a distance; only stick input is a rate that needs `dt`.
- **Recoil recovery fights the player** → recoil written into the look angle. Keep it as an
  offset that decays to zero (refs §4).
- **Square spread pattern** → yaw and pitch randomised independently. Sample a disc (refs §4).
- **Zoomed aim feels too fast** → sensitivity not scaled with FOV (formula above).
- **Ultrawide players see less** → vertical FOV setting treated as horizontal, or the reverse.
- **"I shot first"** → client-side hit authority. The server rewinds targets to the shooter's
  view time, capped (refs §6), and decides.
- **Enemies feel like aimbots** → instant reaction and perfect first shots. Add reaction delay,
  telegraphs and early misses.

## References

- `references/shooting-and-feel.md`: read when comparing hitscan and projectiles, writing the
  ray query per engine (shooter exclusion, triggers, start-inside rules), falloff, disc spread
  and recoil offset code, TTK trade-offs, lag compensation, or the PvE enemy state machine.

Related: `camera-systems`, `game-feel`, `input-systems` (rebinding, aim assist input),
`game-ai` (enemy decisions), `audio-design` (weapon and hit sounds), `godot-3d-essentials`,
`unreal-cpp-gameplay`, `unity-physics`.

## Version notes

Last verified: 2026-11-11.

- Valorant Vandal damage (160/40/34, no falloff) and 9.75 rounds/s:
  https://playvalorant.com/en-us/news/dev/valorant-data-drop-phantom-vs-vandal and
  https://valohub.co/weapons/compare. Weapon numbers change with patches.
- Source `sv_maxunlag` default and maximum 1 s:
  https://developer.valvesoftware.com/wiki/Lag_Compensation.
- Godot 4.7.2 `Camera3D.fov` default 75, vertical under the default `keep_aspect`
  (doc/classes/Camera3D.xml).
- TTK bands, falloff and reaction ranges are design starting points.
