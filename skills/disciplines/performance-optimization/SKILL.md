---
name: performance-optimization
description: >
  Finds and fixes game frame-rate problems by measurement in Godot, Unity, Unreal or Roblox: CPU-
  vs GPU-bound, then the biggest fix (draw calls, pooling, GC spikes). Use for low FPS, stutter, a
  first-use hitch, or requests to optimize or profile. Not for build size (`unity-build-size`),
  physics jitter (`physics-tuning`) or network lag (`roblox-networking`, `godot-multiplayer`).
---

# Performance optimization

The loop: **set a budget, measure, find the one bottleneck, fix it, measure again, report the
numbers.** Guesses usually target the wrong system, so nothing changes until a profiler or a
frame-time capture says where the time goes. This skill is the cross-engine method and the
fixes that recur; each engine's profiler is listed below and in the reference.

## When to use

- The frame rate is low or uneven, or a target (60 FPS desktop, 30 or 60 on mobile) is missed.
- Hitches: first-time effects, loading mid-game, periodic GC pauses, big fights.
- Choosing what to optimize, setting budgets, or adding a performance check to CI.

**Not this skill:** physics stability (`physics-tuning`), install or download size
(`unity-build-size`), network latency (`roblox-networking`, `godot-multiplayer`), shader maths
(`shader-programming`).

## Core workflow

1. **Turn the complaint into a number.** Target FPS gives the budget: 60 FPS is 16.67 ms, 30 is
   33.3 ms, 120 is 8.33 ms. Find a repeatable worst-case scene and save it (a test level, a
   recorded input, a fixed seed).
2. **Uncap before measuring.** VSync and frame caps hide headroom: a 4 ms frame and a 15 ms
   frame both show 60 FPS. Godot `--disable-vsync` (and `--max-fps 0`); Unity
   `QualitySettings.vSyncCount = 0` with `Application.targetFrameRate = -1` on desktop; Unreal
   `r.VSync 0` and `t.MaxFPS 0`. Then read frame time in ms, not FPS.
3. **Profile a release-like build on target hardware.** Editor and debug builds add overhead
   and skip compiler optimization; use a Godot release export, a Unity Development build with
   the profiler attached, or an Unreal Development or Test build.
4. **Split CPU from GPU.** Compare main-thread, render-thread and GPU time. The side closest to
   the frame time is the bottleneck; fixing the other side changes nothing.
5. **Fix the single biggest cost**, preferring doing less work (cache, partition space, run less
   often) over polishing a hot line. Then apply the matching fix below.
6. **Re-measure the same scene on the same machine**, three runs each, and keep or revert on
   the numbers.
7. **Set budgets** per subsystem and per asset so the fix stays fixed, and add the frame-time
   check to CI where the engine allows it.
8. **Report** the scene, hardware, build type, before and after (average and p95 or p99 frame
   time), the bottleneck and the fix. Say what was measured headless or in the editor and what
   still needs the user's device.

## Patterns

### 1. Frame budget split

```text
@60 FPS = 16.67 ms. The slower of CPU frame and GPU frame sets the frame rate.
Example sub-budgets: gameplay/scripts ~5 ms · physics ~3 ms · render submit ~4 ms · UI ~2 ms · slack.
Mobile: keep 20-30% headroom so the game survives thermal throttling.
```

### 2. Where each engine reports the split

```text
Godot 4.7     : Debugger > Profiler (script and physics), Visual Profiler (CPU vs GPU render time
                per pass), Monitors (FPS, draw calls, memory, pipeline compilations).
                Performance.get_monitor(TIME_PROCESS) is the worst frame of the last second in
                SECONDS, refreshed once a second; time frames yourself for per-frame spikes.
Unity 6.3 LTS : Profiler window + Frame Debugger. ProfilerRecorder on "CPU Main Thread Frame Time"
                and "GPU Frame Time" (release players need Frame Timing Stats in Player Settings).
Unreal 5.8    : stat unit (Frame / Game / Draw / RHIT / GPU), stat scenerendering (draw calls),
                Unreal Insights; `csvprofile frames=600` writes a CSV capture you can read.
Roblox        : MicroProfiler (Ctrl+F6 in Studio and the desktop client; mobile via its web UI).
# Game and Draw are CPU threads; GPU is the graphics card. Whichever is nearest Frame wins.
```

**Roblox:** profile on a mid-range phone, because a capped desktop hides the problem. With
Studio Assistant, Roblox's built-in `rbx-perf-profiling` (reads MicroProfiler captures) and
`rbx-scene-analysis` (rendering cost, memory, leaked instances) give real data; use
`roblox-studio-workflow` to run checks in Studio, `roblox-physics` for assembly and simulation
cost, and `roblox-networking` when "lag" means network delay rather than frame time.

### 3. Headless CPU frame-time check (Godot)

```gdscript
# tools/frame_stats.gd: CPU frame time of one scene, headless (no GPU work is measured).
# godot --headless --path . --script res://tools/frame_stats.gd -- res://levels/worst.tscn 600 16.6
extends SceneTree

func _initialize() -> void:
    var args := OS.get_cmdline_user_args()
    var scene_path := args[0] if args.size() > 0 else "res://main.tscn"
    var frames := int(args[1]) if args.size() > 1 else 600
    var budget_ms := float(args[2]) if args.size() > 2 else 16.6
    OS.low_processor_usage_mode_sleep_usec = 0          # headless otherwise sleeps ~6.9 ms a frame
    root.add_child(load(scene_path).instantiate())
    for i in 60:                                       # skip loading and first-use spikes
        await process_frame
    var ms := PackedFloat64Array()
    var last := Time.get_ticks_usec()
    for i in frames:
        await process_frame
        var now := Time.get_ticks_usec()
        ms.append((now - last) / 1000.0)               # whole frame: scripts, physics, engine
        last = now
    ms.sort()
    var avg := 0.0
    for v in ms:
        avg += v / ms.size()
    var p95 := ms[int(ms.size() * 0.95)]
    var p99 := ms[int(ms.size() * 0.99)]
    var over := ms.size() - ms.bsearch(budget_ms, false)
    print("FRAME avg=%.2fms p95=%.2fms p99=%.2fms max=%.2fms over_budget=%d/%d"
            % [avg, p95, p99, ms[-1], over, ms.size()])
    quit(1 if p95 > budget_ms else 0)
```

It exits 1 when p95 exceeds the budget, so it can gate CI for script and physics cost. Headless
mode has no renderer, so it says nothing about GPU time or draw calls; for those, ask the user to
run the game with `--disable-vsync --print-fps` or open the Visual Profiler and report the CPU and
GPU ms for the same scene. A shared or busy machine adds noise, so compare runs on one machine.

### 4. Object pooling (stop allocating and freeing in hot loops)

```gdscript
var _pool: Array[Node2D] = []                     # Node3D for 3D; both have `visible`
func acquire() -> Node2D:
    var n: Node2D = _pool.pop_back() if not _pool.is_empty() else bullet_scene.instantiate()
    n.set_process(true); n.visible = true
    return n
func release(n: Node2D) -> void:
    n.set_process(false); n.visible = false       # disable + hide; don't free
    _pool.append(n)
# Pre-warm at load. Also reset velocity, timers and signal connections on release.
```

### 5. Cut draw calls and state changes

```text
- Atlas textures and share materials so sprites and meshes batch.
- Identical meshes: GPU instancing (Unity; under URP/HDRP the SRP Batcher or GPU Resident Drawer
  takes over), MultiMesh/MultiMeshInstance (Godot), Instanced Static Mesh (Unreal).
- Static geometry: static batching or baking. Bake lighting that does not move.
- Overdraw: fewer large overlapping transparent and particle layers.
- Fill-rate bound: lower render resolution or scale (2x pixel ratio is 4x the pixels).
Measure draw calls and GPU ms before and after; both should drop.
```

### 6. Kill per-frame allocations (GC spikes are periodic hitches)

```csharp
// Unity 6.3 LTS. Steady state should be 0 B "GC Allocated In Frame".
void Update() {
    _hits = Physics.RaycastNonAlloc(ray, _hitBuffer);   // reuse a preallocated array
    for (int i = 0; i < _hits; i++) { /* ... */ }
}   // hit order is undefined and a full buffer may miss the nearest hit: size it, sort if needed
// No LINQ, string building or FindObjectsByType in Update. Cache references once.
// GDScript: reuse Arrays/Dictionaries instead of building new ones each _process.
```

## Gotchas

- **Measuring with VSync on.** The frame rate sits at the refresh rate until the frame is
  already over budget, so fixes look like they did nothing. Uncap, then read ms.
- **Reading `TIME_PROCESS` every frame in Godot.** It is the worst frame of the last second,
  updated once a second, so per-frame samples repeat one value. Time frames directly.
- **Shader and pipeline compile hitches** the first time an effect, enemy or material appears,
  often gone on the second run because the driver cached it. Godot 4.4+: watch the pipeline
  compilation monitors, load features early and keep hidden instances of spawned effects in the
  scene. Unity 6: trace and warm PSOs with `GraphicsStateCollection` (experimental) or warm
  shader variants on older APIs. Unreal: PSO precaching and a bundled PSO cache.
- **Thermal throttling on phones**: 60 FPS for two minutes, then a drop. Ask the user to run a
  15-minute session on the device and report frame time at the start and end; cap the frame rate
  and keep headroom.
- **Unity Android and iOS run at 30 FPS by default** (`targetFrameRate = -1`). Set
  `Application.targetFrameRate` deliberately before calling it a performance problem.
- **Fixing the wrong side.** CPU micro-optimizations do nothing for a GPU-bound frame, and the
  reverse.
- **Instantiate and free in hot loops** cause fragmentation and GC spikes. Pool them.
- **Unity "Enable GPU Instancing" with no effect** under URP/HDRP: the SRP Batcher takes
  precedence for compatible shaders. Check the Frame Debugger; for many identical meshes use the
  GPU Resident Drawer (Forward+, compute-capable APIs, not OpenGL ES).
- **Deep Profile or editor numbers reported as results.** Both distort timings; quote a build.
- **No budgets.** Without per-subsystem ms and asset ceilings, performance regresses quietly.
- **Optimizing a prototype** before it is fun or measured adds complexity that may be thrown away.

## References

- `references/profiling-and-budgets.md`: read when you need a per-engine profiler walkthrough,
  the CPU-vs-GPU triage steps, a generic pool with prewarm and overflow policy, batching and
  instancing rules per engine, allocation rules for C# and GDScript, do-less techniques (LOD,
  culling, time-slicing) or starting asset budgets.

## Related skills

- `physics-tuning`: fixed-step cost, sleeping bodies, broadphase layers.
- `shader-programming`: per-pixel cost of an effect; `godot-shaders` for Godot shader compiles.
- `godot-export`, `unity-build-pipeline`, `unreal-packaging`: building the release build you
  should profile.
- `procedural-gen`, `game-ai`: common CPU hotspots (generation, pathfinding) to defer or slice.

## Version notes

Last verified: 2026-11-11.

- Godot 4.7: `TIME_PROCESS` and `TIME_PHYSICS_PROCESS` are per-second maxima set in
  `main/main.cpp`; headless sleeps `low_processor_usage_mode_sleep_usec` per frame
  (`core/os/os.cpp`); CLI `--disable-vsync`, `--max-fps`, `--print-fps`. Pipeline
  precompilation and its monitors arrived in 4.4, the shader baker in 4.5
  (https://docs.godotengine.org/en/stable/tutorials/performance/pipeline_compilations.html).
  The frame-time script was run on 4.7.2 headless.
- Unity 6.3: `targetFrameRate` defaults and the 30 FPS mobile default
  (https://docs.unity.com/en-us/engine/6000.3/script-reference/unityengine/application/targetframerate);
  `GraphicsStateCollection` is experimental
  (https://docs.unity.com/en-us/engine/6000.3/manual/materials-and-shaders/shaders/shader-troubleshooting/shader-reduce-stalling/shader-prevent-stutter/shader-pso-trace-warming/shader-pso-introduction).
- Unreal: PSO precaching (https://dev.epicgames.com/documentation/unreal-engine/pso-precaching-for-unreal-engine);
  `csvprofile` (https://docs.unrealengine.com/4.27/en-US/TestingAndOptimization/PerformanceAndProfiling/CSVProfiler).
- Roblox: MicroProfiler shortcuts and mobile web UI
  (https://create.roblox.com/docs/performance-optimization/microprofiler.md); built-in
  Assistant skills `rbx-perf-profiling` and `rbx-scene-analysis`
  (https://create.roblox.com/docs/assistant/skills.md).
- RenderDoc 1.47 (2026-10-31), Tracy 0.15.0 (2026-11-05), Unity Project Auditor package 3.2.0
  (2026-11-03): GitHub releases and the Unity package registry.
