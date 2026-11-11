---
name: unreal-cpp-gameplay
description: >
  Unreal Engine 5 (UE 5.8) C++ gameplay code: UCLASS and UPROPERTY reflection, the Gameplay
  Framework, GC-safe pointers, Build.cs and command-line builds. Use for GENERATED_BODY, Live
  Coding, "unresolved external symbol" or UHT errors. Not for Blueprints (`unreal-blueprints`),
  Enhanced Input (`unreal-enhanced-input`) or packaging (`unreal-packaging`); engine source builds
  are out of scope.
---

# Unreal C++ Gameplay

Write UE5 gameplay C++ that compiles the first time, survives garbage collection and is
testable from a terminal. Targets **UE 5.8**.

## When to use

- Creating or fixing C++ gameplay classes (`AActor`, `APawn`, `ACharacter`, `AGameModeBase`,
  `UActorComponent`), reflection macros, or a module's `*.Build.cs`.
- Diagnosing compile, UHT, linker or Live Coding problems, and crashes from freed `UObject`s.
- Writing C++ automation tests and running them headless.

**When *not* to use:** designer-facing visual logic → `unreal-blueprints`. Input assets and
bindings → `unreal-enhanced-input`. Behavior Trees and EQS → `unreal-behavior-trees`. Cooking
and packaging → `unreal-packaging`. Building Unreal Engine itself from source is not covered;
follow Epic's source-build instructions for the engine's GitHub repository.

## Workflow

1. **Read the project.** `EngineAssociation` in the `.uproject` gives the engine version; the
   `Modules` list and `Source/<Module>/<Module>.Build.cs` give module names and dependencies;
   existing base classes in `Source/` tell you what to extend. Match the existing API macro
   (`MYGAME_API`) and folder layout (`Public/`, `Private/`).
2. **Declare reflected types correctly.** The prefix matches the base (`A` actors, `U` other
   `UObject`s and components, `F` structs, `E` enums, `I` interfaces). `GENERATED_BODY()` is
   the first line in the body and `#include "Name.generated.h"` is the last include.
3. **Make every `UObject` pointer GC-visible.** Members that hold a `UObject` are
   `UPROPERTY()` with `TObjectPtr<T>`; non-owning references are `TWeakObjectPtr<T>`. This is
   the most common source of random crashes.
4. **Create default components in the constructor** with `CreateDefaultSubobject`, attach with
   `SetupAttachment`, and set `RootComponent`. Runtime components use `NewObject` plus
   `RegisterComponent`.
5. **Put logic where the framework expects it.** Rules and default classes in the GameMode
   (server only), per-player state in PlayerState, input and UI ownership in the
   PlayerController, the body in the Pawn or Character, reusable behavior in components.
6. **Add module dependencies** to `PublicDependencyModuleNames` (or `Private...` when only the
   `.cpp` files use them) whenever you include another module's headers, for example
   `EnhancedInput`, `AIModule`, `Niagara`, `UMG`.
7. **Build and test from the command line (see Verify).** Use Live Coding (Ctrl+Alt+F11) only
   for function-body edits while the editor is open.

## Patterns

### Reflected actor with a GC-safe component

```cpp
// Pickup.h
#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Pickup.generated.h"            // last include

UCLASS()
class MYGAME_API APickup : public AActor
{
    GENERATED_BODY()
public:
    APickup();

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Pickup")
    int32 ScoreValue = 10;

    UFUNCTION(BlueprintCallable, Category = "Pickup")
    void Collect();

protected:
    UPROPERTY(VisibleAnywhere)
    TObjectPtr<UStaticMeshComponent> Mesh;  // UPROPERTY keeps it alive and visible to the editor
};
```

### A C++ automation test

```cpp
// Source/MyGame/Private/Tests/ScoreTests.cpp
#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FScoreAddsTest, "MyGame.Score.Adds",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)

bool FScoreAddsTest::RunTest(const FString& Parameters)
{
    FScoreBoard Board;                       // plain logic: no world needed
    Board.Add(10);
    TestEqual(TEXT("score after one add"), Board.Total(), 10);
    return true;                             // failed Test* calls still mark the test failed
}
#endif
```

Keep testable rules in plain structs or functions so most tests need no world; use functional
tests in a test map for behavior that needs actors.

## Verify

Say which of these you ran and paste the relevant result lines; "it should compile" is not a
check.

1. **Compile the editor target with the editor closed:**
   `Engine/Build/BatchFiles/Build.bat <Project>Editor Win64 Development -Project="<abs path>.uproject" -WaitMutex`
   (Linux: `Engine/Build/BatchFiles/Linux/Build.sh <Project>Editor Linux Development ...`;
   macOS: `Engine/Build/BatchFiles/Mac/Build.sh <Project>Editor Mac Development ...`). Fix
   every error and every warning in files you touched.
2. **Run the tests headless:**
   `UnrealEditor-Cmd <Project>.uproject -ExecCmds="Automation RunTest MyGame;Quit" -unattended -nullrhi -nosplash -ReportExportPath="<dir>"`.
   `RunTest` takes a full name, a dotted prefix, `Test1+Test2`, or `Group:<name>`. Read the
   JSON report or the `Test Completed` lines in the log, and confirm the expected tests ran: a
   wrong filter runs nothing and still looks clean.
3. **When behavior needs a person,** ask the user to open the editor, check that the new class
   and its properties appear, run PIE, and report the Output Log lines for your category.
4. **Optional:** with Epic's `unreal-mcp` skill connected to a running editor, its testing
   toolset can discover and run automation tests and return detailed results.

## Gotchas

- **"Cannot open include file ...generated.h" or UHT errors:** the generated include isn't
  last, `GENERATED_BODY()` is missing, or the file was added while the editor ran and project
  files weren't regenerated.
- **Unresolved external symbol:** the module that defines the symbol isn't in `Build.cs`.
  Find the header's path under `Engine/Source/` or `Engine/Plugins/` to get the module name.
- **Random crash on a pointer that "was valid":** a raw `UObject*` member without `UPROPERTY`,
  or a container of them, so GC freed the object. `IsValid()` on a dangling raw pointer does
  not save you.
- **Live Coding after header changes:** new `UPROPERTY`s or functions rely on Object
  Reinstancing, which is on by default but less reliable; pointers cached to reinstanced
  objects go stale. If the editor or Blueprints misbehave afterwards, close the editor and do a
  full build.
- **Building from the IDE or command line while the editor runs:** with Live Coding active the
  build is refused or fights the editor's loaded modules. Close the editor first, or compile
  through Live Coding.
- **`CreateDefaultSubobject` outside the constructor:** asserts. At runtime use `NewObject` and
  `RegisterComponent`, otherwise the component never ticks or renders.
- **Overrides that skip `Super::`** (`BeginPlay`, `Tick`, `EndPlay`,
  `GetLifetimeReplicatedProps`) silently skip engine setup.
- **GameMode logic on a client:** the GameMode exists only on the server. Use GameState or
  PlayerState for data clients must see.

## References

- Read `references/components-and-gc.md` when creating or attaching components at runtime,
  choosing between `TObjectPtr`, `TWeakObjectPtr`, `TStrongObjectPtr` and `FGCObject`, adding
  `USTRUCT`/`UENUM` data, or replicating a property with `OnRep_`.
- Epic docs: [Gameplay Framework](https://dev.epicgames.com/documentation/unreal-engine/gameplay-framework-in-unreal-engine),
  [Write C++ Tests](https://dev.epicgames.com/documentation/unreal-engine/write-cplusplus-tests-in-unreal-engine),
  [Run Automation Tests](https://dev.epicgames.com/documentation/unreal-engine/run-automation-tests-in-unreal-engine).

## Related skills

- `unreal-blueprints`: exposing C++ to designers.
- `unreal-enhanced-input`: binding input in a C++ Pawn or Character.
- `unreal-behavior-trees`: AIControllers and custom BT nodes.
- `unreal-packaging`: cooking and shipping the build.

## Version notes

Last verified: 2026-11-11.

- Current release: UE 5.8 (5.8.4 hotfix, October 2026); UE 5.9 is in Preview.
- 5.8 Windows toolchain: Visual Studio 2022 17.14 or newer (2026 recommended), MSVC 14.38
  minimum (14.50 recommended), Windows SDK 10.0.22621.0 minimum. 5.8.4 added Visual Studio
  2026 `.slnx` solution support.
- 5.8 macOS: Xcode 15.2 minimum (15.4 or newer recommended). Linux: clang 20.1.8.
- 5.9 Preview adds the Modular Test Framework for scoped plugin tests.
- Sources: [UE 5.8 release notes, Platform SDK Upgrades](https://dev.epicgames.com/documentation/unreal-engine/unreal-engine-5-8-release-notes),
  [5.8.4 hotfix announcement](https://forums.unrealengine.com/t/5-8-4-hotfix-released/2842775)
  and [5.8.4 summary](https://www.digitaldeveloper.io/releases/unreal-engine/5-8-4),
  [UE 5.9 Preview release notes](https://dev.epicgames.com/documentation/unreal-engine/unreal-engine-5-9-release-notes),
  [Write C++ Tests](https://dev.epicgames.com/documentation/unreal-engine/write-cplusplus-tests-in-unreal-engine).
