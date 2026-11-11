# Feedback recipes

Contents:
1. The trauma model and tuning ranges
2. Easing cheat sheet, plus an eased pop for Unity without a tween package
3. The rest of the feedback menu (flash, knockback, number pop, particles, freeze)
4. Accessibility toggles
5. Per-engine binding summary

Snippets target Godot 4.7 and Unity 6.3 LTS.

## 1. The trauma model (why shake feels good)

Track a single `trauma` value in `[0, 1]`. Events **add** trauma; it **decays** linearly each
frame. The actual shake amount is `trauma^2` (or `trauma^3`) so:

- small/frequent events barely nudge the screen (low trauma, squared → tiny),
- big events punch hard (high trauma, squared → near full),
- shake **always ends** on its own because trauma decays to 0.

Offset and rotation are `max_* * shake * noise(t)`. Sample a noise function or summed sines
across time — never a fresh `rand()` per frame, which produces a harsh buzz instead of a shake.

```gdscript
# 1D value-noise-ish sampler without an addon: layered sines at incommensurate rates.
func _shake_axis(seed: float, t: float) -> float:
    return 0.6 * sin(t * 11.0 + seed) + 0.4 * sin(t * 23.0 + seed * 2.0)
```

Tunable starting points: `max_offset = (8..16, 6..10) px`, `max_roll = 0.05..0.12 rad`,
`decay = 1.0..1.5` trauma/sec, per-hit trauma `0.15` (light) → `0.8` (heavy).

## 2. Easing cheat sheet — which curve for which job

| Goal | Ease | Godot `Tween` | Notes |
|------|------|---------------|-------|
| UI/element "pop" in | overshoot | `TRANS_BACK`, `EASE_OUT` | shoots past target, settles back |
| Bouncy, lively land | bounce/elastic | `TRANS_ELASTIC`/`TRANS_BOUNCE`, `EASE_OUT` | use sparingly; reads as cartoonish |
| Settle / decelerate | ease-out | `TRANS_CUBIC`/`TRANS_QUAD`, `EASE_OUT` | the default for "comes to rest" |
| Anticipation / wind-up | ease-in | `TRANS_CUBIC`, `EASE_IN` | slow start before a fast action |
| Smooth A→B both ends | ease-in-out | `TRANS_SINE`, `EASE_IN_OUT` | camera moves, menu slides |

Unity 6.3 LTS has no built-in tween library; options in order of preference: `Vector3.SmoothDamp`
for spring-like follow, `Mathf.SmoothStep`/hand-rolled ease in a coroutine, Animator curves,
or a third-party tween package if the project already uses one. Keep the *curve choice* the
same regardless of tool.

```csharp
// Unity 6.3 LTS: an eased scale "pop" in a coroutine (no external deps).
static float EaseOutBack(float k) {                     // 0 -> 1, peaks ~10% past 1
    const float c1 = 1.70158f, c3 = c1 + 1f;
    float m = k - 1f;
    return 1f + c3 * m * m * m + c1 * m * m;
}

IEnumerator Pop(Transform t, float dur = 0.18f) {
    var squash = new Vector3(1.3f, 0.7f, 1f);            // squash on the event
    for (float e = 0f; e < dur; e += Time.deltaTime) {
        // Unclamped, so the overshoot past Vector3.one survives the lerp.
        t.localScale = Vector3.LerpUnclamped(squash, Vector3.one, EaseOutBack(e / dur));
        yield return null;
    }
    t.localScale = Vector3.one;
}
```

## 3. The rest of the feedback menu

- **Flash:** tint the sprite/material white for 1–3 frames on hit (`modulate`/material color),
  then tween back. Cheap, hugely legible.
- **Knockback:** apply an impulse away from the hit normal, clamped and short; let
  `physics-tuning` own stability. Pair with brief control lockout, not a long one.
- **Number/text pop:** spawn a damage number that rises, fades, and eases out; randomize the
  horizontal drift so stacked hits fan out.
- **Particles:** a short burst at the contact point (sparks, dust, debris). Pool them
  (`performance-optimization`) — do not instance-and-free per hit.
- **Freeze frame:** the hit-stop in the body; scale duration to importance (0.04 s light →
  0.15 s heavy). Optionally freeze only the attacker+target, not the whole world.
- **Anticipation & follow-through:** a tiny wind-up before a big action and a settle after read
  as weight; this is animation, not code (engine animation skill).
- **Chromatic/vignette/zoom punch:** post-process nudges for big moments; keep brief.

## 4. Accessibility (ship these toggles)

- **Reduce screen shake** (scale trauma output by a 0–100% setting, default ~60–80%).
- **Reduce/disable flashing** (photosensitivity) — replace white flashes with a static tint.
  Even with flashing on, keep any large-area flash at or under three flashes in any one-second
  window ([WCAG 2.3.1](https://www.w3.org/WAI/WCAG22/Understanding/three-flashes-or-below-threshold.html)
  general flash threshold; [Xbox Accessibility Guideline 118](https://learn.microsoft.com/en-us/xbox/accessibility/xbox-accessibility-guidelines/118),
  Photosensitivity).
- **Reduce camera motion** — cut shake roll and zoom punches.

These pair with `game-ui-ux` (settings menu) and `input-systems` (accessibility section).

## 5. Per-engine binding summary

- **Godot 4.7:** `create_tween()` + `tween_property().set_trans().set_ease()`; `GPUParticles2D/3D`
  one-shot; `Engine.time_scale` + `ignore_time_scale` timer; shake on `Camera2D.offset`.
- **Unity 6.3 LTS:** coroutines + `SmoothDamp`/curves (or a tween package); `ParticleSystem.Play()`;
  `Time.timeScale` + `WaitForSecondsRealtime`; shake via `CinemachineBasicMultiChannelPerlin`
  amplitude/frequency driven by `trauma^2`, or `CinemachineImpulseSource.GenerateImpulse()` for
  one-off hits (see `camera-systems`).
- **Web (Phaser/Pixi/three):** tween via the engine/library tween; `this.cameras.main.shake()`
  in Phaser; `requestAnimationFrame`-driven eases elsewhere.
