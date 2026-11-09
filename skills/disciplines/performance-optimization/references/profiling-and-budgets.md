# Profiling & budgets — depth for `performance-optimization`

Detail the body defers here: per-engine profiler walkthroughs, the CPU-vs-GPU triage flow, a
pooling manager, batching/instancing rules, allocation/GC guidance, LOD/culling, and asset
budgets. Targets **Godot 4.7**, **Unity 6.3 LTS**, **Unreal 5.8**.

## 1. CPU-vs-GPU triage (decide before you fix)

```text
1. Read total frame time vs your budget (16.67 ms @60).
2. Compare CPU-frame time and GPU-frame time:
     GPU >> CPU  → GPU-bound  → overdraw, shader cost, resolution, lights/shadows.
     CPU >> GPU  → CPU-bound  → inspect main AND render threads: scripts, physics, pathfinding,
                                allocations/GC, draw submission and render-state changes.
     Both high / alternating → find the per-frame spike in the timeline (one function/system).
3. Within the bound side, sort costs descending and attack the top one only.
4. Re-measure. If it didn't move the frame time, you fixed the wrong thing — revert and re-triage.
```

Optimize the measured bottleneck. Reducing draw calls or state changes can lower CPU rendering
cost when submission is limiting the frame, even if the GPU has spare capacity. Batching and
instancing also have costs, so compare main-thread, render-thread and GPU time before and after
the change. Faster scripts alone usually won't help a frame limited by GPU work.

## 2. Per-engine profiler quick start

**Godot 4.7**
- Editor: **Debugger ▸ Profiler** (per-function script + physics time, frame time), **Debugger ▸
  Visual Profiler** (CPU and GPU time spent on rendering — the Profiler tab does not show GPU cost),
  and the **Monitors** tab (FPS, draw calls, video/static memory, object/node counts).
- Code: `Performance.get_monitor(Performance.TIME_PROCESS)` (frame process time in **seconds**;
  multiply by 1000 for ms), `Performance.TIME_PHYSICS_PROCESS`,
  `Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME`, `Performance.RENDER_TOTAL_PRIMITIVES_IN_FRAME`,
  `Performance.MEMORY_STATIC`.
- Visual debugging: 3D viewport **View Information / View Frame Time** overlays.
- Native-code traces: an engine built from source with `scons profiler=tracy` (or `perfetto`,
  `instruments`) streams engine zones to that profiler.

**Unity 6.3 LTS**
- **Profiler** window: CPU Usage, GPU Usage, Rendering, Memory modules. Use **Deep Profile**
  sparingly (high overhead, skews numbers).
- **Frame Debugger** to step draw calls and see what breaks batching (SetPass calls, batches).
- Code: `ProfilerRecorder` on the built-in counters `"CPU Main Thread Frame Time"`,
  `"GPU Frame Time"` (release players need **Frame Timing Stats** enabled) and
  `"GC Allocated In Frame"` (development players only) for an in-build HUD/CSV;
  `FrameTimingManager` for CPU/GPU frame times.
- **Profile a Development build on device** (`Autoconnect Profiler`), not just the editor.
- **Project Auditor** (`com.unity.project-auditor` package) statically flags costly code and
  settings before you profile.

**Unreal 5.8**
- Console: `stat unit` (Frame / Game / Draw / RHIT / GPU ms — Game is the game thread, Draw the
  render thread, both CPU), `stat fps`, `stat scenerendering` (draw calls, primitives),
  `stat game`, `stat gpu`, `stat hitches` (logs frames over `t.HitchFrameTimeThreshold`).
- **Unreal Insights** for full timeline traces; `ProfileGPU` (Ctrl+Shift+,) for a GPU breakdown.

**External tools (engine-agnostic)**
- **RenderDoc** (1.46 at last check): GPU frame capture for Vulkan, D3D11/12 and OpenGL/ES on
  Windows, Linux and Android; no Metal. On Apple platforms use the Xcode Metal debugger and
  Instruments; on Windows D3D12, PIX.
- **Tracy** (0.14.1 at last check): instrumented CPU/GPU timeline for native code; keep the
  client library and the viewer on the same release, because the network protocol can change.

## 3. Pooling manager (generic)

```text
class Pool<T>:
    free: list
    create_fn, reset_fn
    prewarm(n):  for n → free.push(create_fn())          # allocate up front, off the hot path
    acquire():   t = free.pop() or create_fn(); activate(t); return t
    release(t):  reset_fn(t); deactivate(t); free.push(t)  # never destroy; recycle
```

Pool anything spawned frequently and briefly: bullets, shells, particles, damage numbers,
enemies in waves, audio one-shots. Pre-warm at load to avoid first-use hitches. Cap the pool and
decide an overflow policy (grow, or recycle the oldest).

## 4. Batching & instancing rules

- **What breaks a batch:** a different material, texture, or render state between objects. Share
  materials and **atlas** textures so runs of objects submit as one draw call.
- **Identical meshes, many instances** → GPU instancing: Unity (enable *GPU Instancing* on the
  material — but under URP/HDRP an SRP Batcher-compatible shader is drawn by the SRP Batcher
  instead; for large counts enable the **GPU Resident Drawer**, which needs the Forward+ path and
  a compute-capable graphics API other than OpenGL ES) / Godot `MultiMesh` +
  `MultiMeshInstance2D/3D` / Unreal Instanced Static Mesh or Hierarchical ISM.
- **Static geometry** → static batching (Unity), mark static; bake where possible. Unity's
  dynamic batching is no longer recommended outside low-end devices: its CPU cost can exceed the
  draw calls it saves.
- **2D** → texture atlases + a shared material batch sprites; avoid per-sprite materials.
- **UI** → minimize canvas rebuilds (Unity: split static/dynamic canvases); a changing element
  shouldn't dirty the whole canvas.
- **Lights/shadows** → bake static lighting; cap real-time shadow casters; cull small shadows.

## 5. Allocation / GC guidance

- **C# (Unity):** no per-frame `new`, no LINQ in `Update`, avoid boxing (e.g. `enum` as dictionary
  key), use `NonAlloc` physics queries, reuse `List`/arrays (`Clear()` not realloc), prefer
  structs for small hot data, cache `GetComponent`/`Find` results. The goal is **0 B GC.Alloc per
  frame** in steady state.
- **GDScript (Godot):** don't build new `Array`/`Dictionary` each `_process`; reuse; prefer typed
  arrays; avoid heavy work in `_process` that belongs on a timer/signal.
- **General:** strings are a classic hidden allocator (concatenation, formatting) — build them
  rarely, cache results.

## 6. Do-less techniques (algorithmic wins)

- **Run less often:** update AI/HUD/expensive checks on a timer or every N frames, not every
  frame; stagger across frames (time-slicing).
- **Spatial partition:** grid/quadtree/octree so queries touch nearby objects only, not all N.
- **LOD & culling:** lower detail at distance; frustum/occlusion culling; despawn off-screen
  far entities.
- **Cache results:** memoize pathfinding, line-of-sight, and derived data; invalidate on change.
- **Defer/Amortize:** spread procedural generation and loading across frames to avoid spikes.

## 7. Asset budgets (prevent regressions at the source)

| Asset | Typical desktop budget | Mobile budget | Notes |
|-------|------------------------|---------------|-------|
| Texture max size | 2048–4096 | 1024–2048 | use mipmaps; compress (BCn / ASTC) |
| Character triangles | 30k–80k | 5k–20k | LODs for distance |
| Draw calls / frame | low thousands | a few hundred | the count that matters most on mobile |
| Real-time lights | a few | 1–2 + baked | bake the rest |
| Audio | streamed music, short SFX in memory | same | don't decompress everything at load |

Mobile adds **thermal throttling**: a game that hits 60 FPS for 2 minutes then drops is
overheating — target headroom, cap frame rate, and reduce sustained GPU load.
