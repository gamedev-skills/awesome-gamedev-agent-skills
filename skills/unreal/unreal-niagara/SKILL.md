---
name: unreal-niagara
description: >
  Unreal Engine 5 (UE 5.8) Niagara VFX: systems, emitters, User parameters, spawning from C++ or
  Blueprints, bounds and GPU vs CPU sim. Use for any Unreal particle effect, NS_ assets, muzzle
  flashes or impacts, or effects that do not show, vanish at the screen edge or never stop. Not
  for Unity VFX Graph, shader authoring (`shader-programming`) or hit-stop (`game-feel`).
---

# Unreal Niagara VFX

Build UE5 effects that gameplay can spawn, drive and clean up, and that keep rendering where
the camera actually looks. Targets **UE 5.8**. Niagara replaced Cascade, which is deprecated.

## When to use

- Creating or editing Niagara Systems (`NS_`) and Emitters (`NE_`), module order, User
  parameters, renderers, bounds and scalability.
- Spawning, attaching, parameterizing, pooling or stopping effects from C++ or Blueprints.
- Debugging effects that don't appear, cull wrongly, leak or cost too much.

**When *not* to use:** Unity VFX Graph or particles in other engines are not covered here.
Material and shader logic → `shader-programming`. Juice such as screen shake and hit-stop →
`game-feel`. Audio for the effect → `audio-design`.

## Workflow

1. **Read the project.** Check `EngineAssociation`, list existing `NS_*`/`NE_*` assets and
   emitter templates, and grep `Source` for `UNiagaraComponent` to find the spawn path already
   in use. C++ access needs `"Niagara"` in the module's `*.Build.cs`; without it the includes
   compile and the link fails.
2. **Expose what gameplay changes as User parameters.** Only the `User` namespace can be set
   from Blueprint or C++; `System`, `Emitter` and `Particle` values are internal to the sim.
3. **Order modules deliberately.** Modules run top to bottom in each stage, so a force placed
   before the module that initializes velocity acts on zero.
4. **Pick the sim target.** Default to CPU for small counts and anything gameplay reacts to
   (events, collision callbacks); use GPU for large counts of purely visual particles, and give
   GPU emitters fixed bounds.
5. **Spawn from gameplay, never from the Construction Script.**
   `UNiagaraFunctionLibrary::SpawnSystemAtLocation` for world-space one-shots,
   `SpawnSystemAttached` for effects that follow a component or socket. For frequent one-shots
   (impacts, footsteps) pass a pooling method instead of creating a component each time.
6. **Own the lifetime.** One-shots use a non-looping system with auto-destroy or auto-release;
   looping effects keep the returned component and call `Deactivate()` when done.
7. **Check it (see Verify).**

## Patterns

### One-shot impact (pooled) and a driven looping effect

```cpp
#include "NiagaraFunctionLibrary.h"
#include "NiagaraComponent.h"

void AProjectile::SpawnImpact(const FVector& Location, const FRotator& Rotation)
{
    // ImpactSystem: UPROPERTY(EditAnywhere) TObjectPtr<UNiagaraSystem>, non-looping.
    UNiagaraFunctionLibrary::SpawnSystemAtLocation(
        GetWorld(), ImpactSystem, Location, Rotation, FVector(1.f),
        /*bAutoDestroy*/ true, /*bAutoActivate*/ true, ENCPoolMethod::AutoRelease);
    // With AutoRelease the component goes back to the pool when it finishes:
    // don't keep the returned pointer.
}

void ATorch::BeginPlay()
{
    Super::BeginPlay();
    Fire = UNiagaraFunctionLibrary::SpawnSystemAttached(   // Fire: UPROPERTY TObjectPtr<UNiagaraComponent>
        FireSystem, RootComponent, NAME_None, FVector::ZeroVector, FRotator::ZeroRotator,
        EAttachLocation::KeepRelativeOffset, /*bAutoDestroy*/ false);
    if (Fire)                                              // null on servers or when pre-culled
    {
        Fire->SetVariableFloat(TEXT("SpawnRate"), 250.f);  // the User.SpawnRate parameter
        Fire->SetVariableLinearColor(TEXT("FireColor"), FLinearColor::Red);
    }
}
```

Blueprint uses the same nodes: Spawn System at Location or Spawn System Attached, then Set
Niagara Variable (Float, LinearColor and so on) on the returned component.

## Verify

Say which of these you ran.

1. **Compile** the module (`Build.bat`/`Build.sh` as in `unreal-cpp-gameplay`).
2. **Validate assets:** `UnrealEditor-Cmd <Project>.uproject -run=DataValidation -unattended`
   and fix errors in the systems you touched.
3. **Functional test for gameplay-spawned effects:** spawn the system in a test map, assert the
   returned component is valid and active, then (for a one-shot) that it has finished after its
   lifetime. Niagara needs a renderer, so run it with `-RenderOffscreen` rather than `-nullrhi`:
   `UnrealEditor-Cmd <Project>.uproject -ExecCmds="Automation RunTest Project.Functional Tests;Quit" -unattended -RenderOffscreen -ReportExportPath="<dir>"`.
4. **Ask the user** to run PIE and use the Niagara Debugger (Tools > Debug > Niagara Debugger)
   or the console: `fx.Niagara.Debug.Hud Enabled=1` for the debug HUD, `fx.Niagara.DumpComponents`
   to list live components in the log, `stat Niagara` for cost. Ask them to report whether the
   effect appears, whether it disappears when its origin leaves the screen (bounds), and the
   active component count after a minute of play (leaks).
5. **Optional:** Epic's `unreal-mcp` skill can author and inspect Niagara systems in a running
   editor when it is installed; the checks above do not need it.

## Gotchas

- **Setting a parameter does nothing:** it isn't in the `User` namespace, or the name passed to
  `SetVariable*` doesn't match it exactly.
- **Crash on the returned component:** spawn functions return `nullptr` when there is no system
  asset, on a dedicated server, or when scalability pre-culls the effect. Null-check before use.
- **Effect vanishes when its origin leaves the screen:** bounds are too small or dynamic bounds
  were never computed. GPU emitters need fixed bounds set on the emitter or system.
- **Looping effect never stops or components pile up:** spawned with auto-destroy off and never
  deactivated, or the system loops when it should be one-shot.
- **Pooled component changes under you:** with `AutoRelease` the pool reuses it after it
  finishes. Use `ManualRelease` (and release it yourself) if you must keep driving it.
- **Gameplay can't read the particles:** GPU sim data isn't read back to the CPU. Use a CPU
  emitter for anything gameplay reacts to.
- **Following a Cascade tutorial:** different system. Port old assets with the Cascade To
  Niagara Converter plugin as a starting point.
- **Spawning from the Construction Script:** the spawn functions are marked unsafe during actor
  construction. Spawn from BeginPlay or later.
- **Wrong argument lands in the wrong slot:** `SpawnSystemAttached` takes `PoolingMethod`
  before `bAutoActivate`, unlike `SpawnSystemAtLocation`. Check the order in
  `NiagaraFunctionLibrary.h` before passing optional arguments.

## References

- Epic docs: [Overview of Niagara Effects](https://dev.epicgames.com/documentation/unreal-engine/overview-of-niagara-effects-for-unreal-engine),
  [Niagara Debugger](https://dev.epicgames.com/documentation/unreal-engine/niagara-debugger-for-unreal-engine),
  [Console commands reference](https://dev.epicgames.com/documentation/unreal-engine/unreal-engine-console-commands-reference).

## Related skills

- `shader-programming`: particle material and shader concepts.
- `game-feel`: shake, hit-stop and timing around the effect.
- `unreal-cpp-gameplay`: module setup and the actors that spawn effects.
- `unreal-blueprints`: triggering effects from graphs.

## Version notes

Last verified: 2026-11-11.

- Current release: UE 5.8 (5.8.4 hotfix, October 2026); UE 5.9 is in Preview.
- 5.8: new Spawn By Trigger module, Random Jitter and Ramp In/Out dynamic inputs, GPU bitonic
  sort for small particle counts, and a `FiltersEnabled=` option for the debug HUD command.
- 5.9 Preview: the Unreal Animation Framework gains a Play Niagara Effect notify handler, and
  AVBOIT order-independent transparency changes how overlapping translucent particles blend.
- Sources: [UE 5.8 release notes](https://dev.epicgames.com/documentation/unreal-engine/unreal-engine-5-8-release-notes),
  [UE 5.9 Preview release notes](https://dev.epicgames.com/documentation/unreal-engine/unreal-engine-5-9-release-notes),
  [Niagara Debugger](https://dev.epicgames.com/documentation/unreal-engine/niagara-debugger-for-unreal-engine).
