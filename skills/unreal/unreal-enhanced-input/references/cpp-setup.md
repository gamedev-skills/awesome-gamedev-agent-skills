# Enhanced Input — complete C++ Character (UE 5.8)

Depth for `unreal-enhanced-input`: a self-contained third-person Character that adds a mapping
context and binds move/look/jump. Verified against the Enhanced Input documentation.

Contents:
- Header
- Source (context added in `PawnClientRestart`, bindings, move and look handlers)
- Build.cs
- Asset setup checklist (editor)
- Runtime rebinding note (Enhanced Input User Settings)

## Header

```cpp
// MyCharacter.h
#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "MyCharacter.generated.h"

class UInputMappingContext;
class UInputAction;
struct FInputActionValue;

UCLASS()
class MYGAME_API AMyCharacter : public ACharacter
{
    GENERATED_BODY()
public:
    AMyCharacter();

protected:
    virtual void PawnClientRestart() override;   // owning client, after possession
    virtual void SetupPlayerInputComponent(UInputComponent* PlayerInputComponent) override;

    // Assign these in the Blueprint subclass (IMC_/IA_ assets).
    UPROPERTY(EditAnywhere, Category = "Input")
    TObjectPtr<UInputMappingContext> DefaultMappingContext;

    UPROPERTY(EditAnywhere, Category = "Input")
    TObjectPtr<UInputAction> MoveAction;

    UPROPERTY(EditAnywhere, Category = "Input")
    TObjectPtr<UInputAction> LookAction;

    UPROPERTY(EditAnywhere, Category = "Input")
    TObjectPtr<UInputAction> JumpAction;

    void Move(const FInputActionValue& Value);
    void Look(const FInputActionValue& Value);
};
```

## Source

```cpp
// MyCharacter.cpp
#include "MyCharacter.h"
#include "EnhancedInputComponent.h"
#include "EnhancedInputSubsystems.h"
#include "InputActionValue.h"

AMyCharacter::AMyCharacter()
{
    // (camera/spring-arm setup omitted; see the unreal-cpp-gameplay skill)
}

void AMyCharacter::PawnClientRestart()
{
    Super::PawnClientRestart();
    if (APlayerController* PC = Cast<APlayerController>(GetController()))
        if (ULocalPlayer* LP = PC->GetLocalPlayer())
            if (UEnhancedInputLocalPlayerSubsystem* Subsystem =
                    LP->GetSubsystem<UEnhancedInputLocalPlayerSubsystem>())
                Subsystem->AddMappingContext(DefaultMappingContext, 0);
}

void AMyCharacter::SetupPlayerInputComponent(UInputComponent* PlayerInputComponent)
{
    Super::SetupPlayerInputComponent(PlayerInputComponent);
    if (UEnhancedInputComponent* EIC = Cast<UEnhancedInputComponent>(PlayerInputComponent))
    {
        EIC->BindAction(MoveAction, ETriggerEvent::Triggered, this, &AMyCharacter::Move);
        EIC->BindAction(LookAction, ETriggerEvent::Triggered, this, &AMyCharacter::Look);
        EIC->BindAction(JumpAction, ETriggerEvent::Started,   this, &ACharacter::Jump);
        EIC->BindAction(JumpAction, ETriggerEvent::Completed, this, &ACharacter::StopJumping);
    }
}

void AMyCharacter::Move(const FInputActionValue& Value)
{
    const FVector2D Axis = Value.Get<FVector2D>();
    if (Controller)
    {
        // Move relative to where the controller is facing (yaw only).
        const FRotator Yaw(0, Controller->GetControlRotation().Yaw, 0);
        AddMovementInput(FRotationMatrix(Yaw).GetUnitAxis(EAxis::X), Axis.Y);
        AddMovementInput(FRotationMatrix(Yaw).GetUnitAxis(EAxis::Y), Axis.X);
    }
}

void AMyCharacter::Look(const FInputActionValue& Value)
{
    const FVector2D Axis = Value.Get<FVector2D>();
    AddControllerYawInput(Axis.X);
    AddControllerPitchInput(Axis.Y);
}
```

## Build.cs

```csharp
PublicDependencyModuleNames.AddRange(new string[]
{
    "Core", "CoreUObject", "Engine", "InputCore", "EnhancedInput"
});
```

## Asset setup checklist (editor)

1. `IA_Move` — Value Type **Axis2D**; `IA_Look` — Axis2D; `IA_Jump` — **Digital (bool)**.
2. `IMC_Default` mappings:
   - `IA_Move`: W (no modifier), S (**Negate**), and a **Swizzle Input Axis Values** on the
     up/down keys so vertical maps to Y; A (**Negate**), D for X.
   - `IA_Look`: Mouse XY (add **Negate** on Y if inverted); gamepad right stick.
   - `IA_Jump`: Space Bar / gamepad face button.
3. In the Blueprint subclass of `AMyCharacter`, assign `DefaultMappingContext` and the three
   `IA_` assets.

## Runtime rebinding note

The supported path for a "rebind controls" menu is Enhanced Input's **User Settings**, not
editing the `IMC_` asset:

1. Project Settings → Engine → Enhanced Input → User Settings → **Enable User Settings**.
2. On each remappable Input Action (or on individual mappings in the `IMC_`), set **Player
   Mappable Key Settings** with a unique **Name**; that name is the save key.
3. Register the context with the settings object: `Subsystem->GetUserSettings()->
   RegisterInputMappingContext(IMC)`, or pass `FModifyContextOptions` with
   `bNotifyUserSettings = true` to `AddMappingContext`.
4. Remap with `UEnhancedInputUserSettings::MapPlayerKey` (an `FMapPlayerKeyArgs` naming the
   mapping, slot and new key), reset with `UnMapPlayerKey` (capital M), and persist with
   `SaveSettings`.

The settings object belongs to the `UEnhancedInputLocalPlayerSubsystem` (one per local player),
so it exists only while that local player does.
