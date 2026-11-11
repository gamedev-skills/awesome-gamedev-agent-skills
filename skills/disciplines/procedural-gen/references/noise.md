# Noise for terrain, biomes, and scatter

Contents: libraries and ranges; frequency and wavelength; octaves (fBm);
redistribution; biome lookup from two fields; island shaping; object scatter;
wraparound maps; determinism checklist.

Gradient noise (Perlin, Simplex, OpenSimplex) is the workhorse of procedural
terrain. A noise function maps a continuous 2D/3D coordinate to a smooth value;
sampling it across a grid gives a coherent heightfield. **Use a library** —
implementing correct gradient noise is fiddly and rarely worth it.

Libraries by ecosystem: `FastNoiseLite` (C/C++/C#/Rust/JS/GLSL/HLSL and many
more; built into Godot 4 as the `FastNoiseLite` resource, whose
`get_noise_2d()` returns about `-1..1`), `opensimplex` (Python), `simplex-noise`
(JS/TS), `Unity.Mathematics.noise` (`snoise`/`cnoise`, `-1..1`) or
`Mathf.PerlinNoise` (Unity, about `0..1` and may slightly overshoot). Rescale to a
known range before combining. `Mathf.PerlinNoise` takes no seed: derive a large
per-seed offset added to the coordinates instead.

## Frequency and wavelength

Sampling `noise(freq * x, freq * y)` zooms the pattern. Higher frequency = more,
smaller features; `wavelength = map_size / frequency`. Always normalize the input
coordinate (e.g. `nx = x / width`) so the same frequency means the same thing
across map sizes.

## Octaves (fractal Brownian motion)

Real terrain mixes large landforms with small detail. Sum octaves: each octave
multiplies frequency by **lacunarity** (commonly 2.0) and amplitude by **gain**
(a.k.a. persistence, commonly 0.5).

```python
def fbm(noise, x, y, octaves=5, lacunarity=2.0, gain=0.5):
    total, amp, freq, norm = 0.0, 1.0, 1.0, 0.0
    for _ in range(octaves):
        total += amp * noise(x * freq, y * freq)
        norm  += amp
        amp   *= gain
        freq  *= lacunarity
    return total / norm        # divide by summed amplitude -> stays in 0..1
```

To keep octaves independent (avoid correlation artifacts near the origin), give
each octave its own seed, or add a per-octave offset like
`noise(2*x + 5.3, 2*y + 9.1)`.

## Redistribution: shaping the elevation curve

Raw fBm is "all hills". Reshape it with a function `e = f(e)`:

- **Valleys/plateaus**: `e = pow(e, exponent)` with `exponent > 1` pushes mid
  elevations down into flats; `< 1` pulls them up toward peaks.
- **Ridges (mountain spines)**: `r = 1 - abs(2*noise - 1)` (a "ridged" transform)
  before summing octaves.
- **Terraces**: `e = round(e * levels) / levels` snaps to discrete bands.

These are the same image-filter ideas as a photo "curves" tool; experiment and
keep a fudge factor near 1.0 (`pow(e * 1.2, exponent)`).

## Biome lookup from two fields

One noise value bands the map; two decorrelated values give variety. Sample
**elevation** and **moisture** from different seeds, then table-lookup:

```python
def biome(e, m):
    if e < 0.10: return "OCEAN"
    if e < 0.12: return "BEACH"
    if e > 0.80:
        return "SNOW" if m > 0.5 else "TUNDRA"
    if e > 0.60:
        return "TAIGA" if m > 0.66 else "SHRUBLAND"
    if m < 0.16: return "DESERT"
    if m < 0.50: return "GRASSLAND"
    return "FOREST"
# These thresholds are starting points — every generator needs its own tuning.
```

## Island shaping

To force water at the map borders, blend the elevation toward a distance-based
shape. With `nx, ny` in `-1..+1` from center:

```python
# Square-bump distance: 0 at center, ~1 at edges.
d = 1 - (1 - nx*nx) * (1 - ny*ny)
e = lerp(e, 1 - d, mix)        # mix=0 -> original; mix~0.5 -> island
```

Round islands: `d = min(1, (nx*nx + ny*ny) / sqrt(2))`. Apply island shaping only
to low-frequency octaves to keep coastline detail.

## Object scatter (trees, rocks)

For natural spacing, do **not** threshold high-frequency noise. Prefer **Poisson
disc sampling** or a **jittered grid**, which guarantee a minimum spacing and
avoid clumping. Vary the minimum radius per biome for variable density (dense
forest vs sparse desert).

## Wraparound (seamless) maps

For a map whose east edge tiles with its west edge, sample noise on a cylinder:
map `x` to an angle and feed `cos/sin` into 3D noise. Tiling both axes uses 4D
noise on a torus. The value distribution changes with the dimension, so measure
the min/max you actually get over the map and rescale afterward.

## Determinism checklist

- One seeded noise generator per field, stored in the save.
- No time-, frame-, or hash-randomized input feeding generation.
- Same engine + same library version = same output (note: switching noise
  libraries changes results even with the same seed).
