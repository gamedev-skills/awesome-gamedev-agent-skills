# Custom BTTask in C++ (UE 5.8)

Depth for `unreal-behavior-trees`: writing a custom Behavior Tree task node in C++. Verified
against the Behavior Trees documentation and the `UBTTaskNode` API. Requires the `AIModule`
dependency in `*.Build.cs`.

Contents:
- Instant task (returns immediately)
- Latent task (finishes over time, per-AI node memory, `AbortTask`)
- Reading and writing typed Blackboard values
- Notes: node names, owner access, key selectors, custom services and decorators

## Instant task (returns immediately)

```cpp
// BTTask_ClearTarget.h
#pragma once
#include "CoreMinimal.h"
#include "BehaviorTree/BTTaskNode.h"
#include "BTTask_ClearTarget.generated.h"

UCLASS()
class MYGAME_API UBTTask_ClearTarget : public UBTTaskNode
{
    GENERATED_BODY()
public:
    UBTTask_ClearTarget();
    virtual EBTNodeResult::Type ExecuteTask(UBehaviorTreeComponent& OwnerComp,
                                            uint8* NodeMemory) override;

    // Exposes a Blackboard key picker in the BT editor.
    UPROPERTY(EditAnywhere, Category = "Blackboard")
    FBlackboardKeySelector TargetKey;
};
```

```cpp
// BTTask_ClearTarget.cpp
#include "BTTask_ClearTarget.h"
#include "BehaviorTree/BlackboardComponent.h"

UBTTask_ClearTarget::UBTTask_ClearTarget()
{
    NodeName = "Clear Target";
}

EBTNodeResult::Type UBTTask_ClearTarget::ExecuteTask(UBehaviorTreeComponent& OwnerComp,
                                                     uint8* NodeMemory)
{
    if (UBlackboardComponent* BB = OwnerComp.GetBlackboardComponent())
    {
        BB->ClearValue(TargetKey.SelectedKeyName);
        return EBTNodeResult::Succeeded;     // done now
    }
    return EBTNodeResult::Failed;
}
```

`EBTNodeResult::Type` values: `Succeeded`, `Failed`, `Aborted`, `InProgress`.

## Latent task (finishes over time)

Return `InProgress`, then call `FinishLatentTask` when the work completes (e.g. a timer, an
async query, or a delegate callback). Tasks are **not instanced** by default: one node object is
shared by every AI running the tree, so per-run state (here the timer handle) goes in the
node's instance memory, never in member variables.

```cpp
// BTTask_WaitRandom.h
#pragma once
#include "CoreMinimal.h"
#include "BehaviorTree/BTTaskNode.h"
#include "BTTask_WaitRandom.generated.h"

struct FBTWaitRandomMemory
{
    FTimerHandle TimerHandle;
};

UCLASS()
class MYGAME_API UBTTask_WaitRandom : public UBTTaskNode
{
    GENERATED_BODY()
public:
    virtual EBTNodeResult::Type ExecuteTask(UBehaviorTreeComponent& OwnerComp,
                                            uint8* NodeMemory) override;
    virtual EBTNodeResult::Type AbortTask(UBehaviorTreeComponent& OwnerComp,
                                          uint8* NodeMemory) override;

    virtual uint16 GetInstanceMemorySize() const override { return sizeof(FBTWaitRandomMemory); }
    virtual void InitializeMemory(UBehaviorTreeComponent& OwnerComp, uint8* NodeMemory,
                                  EBTMemoryInit::Type InitType) const override
    {
        InitializeNodeMemory<FBTWaitRandomMemory>(NodeMemory, InitType);
    }
    virtual void CleanupMemory(UBehaviorTreeComponent& OwnerComp, uint8* NodeMemory,
                               EBTMemoryClear::Type CleanupType) const override
    {
        CleanupNodeMemory<FBTWaitRandomMemory>(NodeMemory, CleanupType);
    }

    UPROPERTY(EditAnywhere, Category = "Wait") float MinTime = 1.f;
    UPROPERTY(EditAnywhere, Category = "Wait") float MaxTime = 3.f;
};
```

```cpp
// BTTask_WaitRandom.cpp
#include "BTTask_WaitRandom.h"
#include "BehaviorTree/BehaviorTreeComponent.h"
#include "TimerManager.h"

EBTNodeResult::Type UBTTask_WaitRandom::ExecuteTask(UBehaviorTreeComponent& OwnerComp,
                                                    uint8* NodeMemory)
{
    UWorld* World = OwnerComp.GetWorld();
    if (!World) return EBTNodeResult::Failed;

    FBTWaitRandomMemory* Memory = CastInstanceNodeMemory<FBTWaitRandomMemory>(NodeMemory);
    const float Delay = FMath::FRandRange(MinTime, MaxTime);

    // Weak pointer: the component can be destroyed before the timer fires.
    TWeakObjectPtr<UBehaviorTreeComponent> WeakComp(&OwnerComp);
    World->GetTimerManager().SetTimer(Memory->TimerHandle,
        FTimerDelegate::CreateWeakLambda(this, [this, WeakComp]()
        {
            if (UBehaviorTreeComponent* Comp = WeakComp.Get())
            {
                FinishLatentTask(*Comp, EBTNodeResult::Succeeded);   // resumes the tree
            }
        }), Delay, /*bLoop*/ false);

    return EBTNodeResult::InProgress;        // tree waits on this node until FinishLatentTask
}

EBTNodeResult::Type UBTTask_WaitRandom::AbortTask(UBehaviorTreeComponent& OwnerComp,
                                                  uint8* NodeMemory)
{
    // A higher-priority branch took over: cancel the pending timer so it can't finish later.
    if (UWorld* World = OwnerComp.GetWorld())
    {
        World->GetTimerManager().ClearTimer(
            CastInstanceNodeMemory<FBTWaitRandomMemory>(NodeMemory)->TimerHandle);
    }
    return EBTNodeResult::Aborted;
}
```

`AbortTask` returns `Aborted` when it can stop immediately; return `InProgress` instead and call
`FinishLatentAbort(OwnerComp)` later if cancelling is itself asynchronous.

## Reading and writing typed Blackboard values

```cpp
UBlackboardComponent* BB = OwnerComp.GetBlackboardComponent();
AActor* Target  = Cast<AActor>(BB->GetValueAsObject(TargetKey.SelectedKeyName));
FVector Loc     = BB->GetValueAsVector(TEXT("LastKnownLocation"));
BB->SetValueAsBool(TEXT("bIsInvestigating"), true);
```

## Notes

- Set `NodeName` in the constructor so the node reads clearly in the BT graph.
- `OwnerComp.GetAIOwner()` gives the `AAIController`; `GetAIOwner()->GetPawn()` the controlled
  pawn — use these instead of caching world pointers.
- For nodes that need per-instance memory (counters, handles), override
  `GetInstanceMemorySize`, construct and destroy the block with `InitializeNodeMemory<T>` /
  `CleanupNodeMemory<T>`, and read it with `CastInstanceNodeMemory<T>` (as in the latent task
  above). Member UPROPERTYs on a non-instanced node are shared across all uses; treat them as
  read-only settings.
- A bare `FBlackboardKeySelector` offers every key in the editor and only `SelectedKeyName` is
  usable until resolved. Deriving from `UBTTask_BlackboardBase` gives you a `BlackboardKey`
  that is resolved in `InitializeFromAsset`; with your own selector, add a type filter in the
  constructor (e.g. `AddObjectFilter`) and call `ResolveSelectedKey` in `InitializeFromAsset`.
- A custom **Service** subclasses `UBTService` and overrides `TickNode`; a custom **Decorator**
  subclasses `UBTDecorator` and overrides `CalculateRawConditionValue`.
