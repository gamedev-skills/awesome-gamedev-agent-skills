# Components, garbage collection & replication primer (UE 5.8 C++)

Depth for `unreal-cpp-gameplay`. Verified against the Gameplay Framework docs and the UE5
C++ programming references. Covers component creation/attachment, the UPROPERTY/GC ownership
rules that trip up newcomers, and a minimal replication example.

Contents:
- Creating and attaching components (constructor vs runtime)
- Garbage collection ownership (`UPROPERTY`, `TObjectPtr`, `TWeakObjectPtr`, `TStrongObjectPtr`, `FGCObject`)
- USTRUCT and UENUM for reflected data
- Minimal replication (`ReplicatedUsing`, `DOREPLIFETIME`)
- Gotchas

## Creating and attaching components

Default subobjects are created in the constructor; runtime components use `NewObject` +
`RegisterComponent`.

```cpp
// In the constructor — built into the Class Default Object, editable in the Blueprint subclass.
ACharacterBase::ACharacterBase()
{
    SpringArm = CreateDefaultSubobject<USpringArmComponent>(TEXT("SpringArm"));
    SpringArm->SetupAttachment(RootComponent);          // attach to an existing component
    SpringArm->TargetArmLength = 300.f;

    Camera = CreateDefaultSubobject<UCameraComponent>(TEXT("Camera"));
    Camera->SetupAttachment(SpringArm);                 // socket chain: root -> arm -> camera
}
```

```cpp
// At runtime (e.g. add a component after spawn):
UAudioComponent* Audio = NewObject<UAudioComponent>(this);
Audio->RegisterComponent();                              // required, or it won't tick/render
Audio->AttachToComponent(RootComponent, FAttachmentTransformRules::KeepRelativeTransform);
```

- `CreateDefaultSubobject` is **only** valid in a constructor; using it later asserts.
- `SetupAttachment` is for constructor-time hierarchy; `AttachToComponent` is the runtime call.

## Garbage collection ownership (the #1 newcomer crash)

The UE garbage collector only keeps `UObject`s alive if it can reach them through a reflected
reference. A raw `UObject*` member that isn't a `UPROPERTY` is invisible to the GC and can be
collected, leaving a dangling pointer.

```cpp
UPROPERTY()                                  // GC sees it -> stays alive while this owner lives
TObjectPtr<UMyDataObject> Data;

UPROPERTY()
TArray<TObjectPtr<AActor>> Tracked;          // containers of UObjects also need UPROPERTY

UMyDataObject* Raw;                           // BUG: not tracked; may be GC'd -> crash
```

Rules:
- Every `UObject`/Actor pointer that must persist gets a `UPROPERTY` (use `TObjectPtr<T>` in
  UE5; raw pointers still compile but `TObjectPtr` adds access tracking in the editor).
- Plain C++ data (ints, FStrings, FVectors, USTRUCTs of POD) doesn't need this — it's owned by
  value.
- For a UObject you create that has no UPROPERTY owner (rare), `AddToRoot()` pins it and
  `RemoveFromRoot()` releases it — but prefer proper ownership.
- A plain C++ class (not a UObject) can't use `UPROPERTY`. Hold UObjects there with
  `TStrongObjectPtr<T>`, or derive from `FGCObject` and report them in `AddReferencedObjects`
  (it also requires `GetReferencerName`).
- For references that must *not* keep the target alive (a cached target actor, a listener),
  use `TWeakObjectPtr<T>` and check `IsValid()`/`Get()` before each use.

## USTRUCT and UENUM for reflected data

```cpp
UENUM(BlueprintType)
enum class EWeaponType : uint8 { Pistol, Rifle, Shotgun };

USTRUCT(BlueprintType)
struct FWeaponStats
{
    GENERATED_BODY()
    UPROPERTY(EditAnywhere, BlueprintReadWrite) int32 Damage = 10;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float FireRate = 0.25f;
};
```

`BlueprintType` makes the enum/struct usable as Blueprint variables.

## Minimal replication (multiplayer)

```cpp
// Header
UPROPERTY(ReplicatedUsing = OnRep_Health)
float Health = 100.f;

UFUNCTION()
void OnRep_Health();                          // client callback when Health replicates

// Source
#include "Net/UnrealNetwork.h"
void AMyActor::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Out) const
{
    Super::GetLifetimeReplicatedProps(Out);
    DOREPLIFETIME(AMyActor, Health);          // register the property for replication
}
```

- Set `bReplicates = true;` in the constructor for the actor to replicate at all.
- Server authority: gameplay changes happen on the server; clients receive replicated state and
  react in `OnRep_` callbacks.

## Gotchas

- `NewObject` without `RegisterComponent` gives a component that exists but never ticks or
  renders.
- Forgetting `#include "Net/UnrealNetwork.h"` breaks `DOREPLIFETIME`.
- `TObjectPtr` implicitly converts to the raw pointer for calls, so existing `->`/`.` usage is
  unchanged; the difference is GC visibility and editor tooling, not syntax at call sites.
