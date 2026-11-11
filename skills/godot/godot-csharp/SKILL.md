---
name: godot-csharp
description: >
  C# and .NET in Godot 4.7: partial node classes, the PascalCase lifecycle, [Export] and [Signal],
  signals as C# events, the .csproj and calling GDScript. Use for .cs scripts in Godot, porting
  GDScript to C#, a failed build, or a failed web or Android export. Not for GDScript
  (`godot-gdscript`), Unity C# (`unity-csharp-scripting`) or export presets (`godot-export`).
---

# Godot C# / .NET (4.x)

Write Godot game code in C# that the source generators accept, build it from the command
line, and check it runs. Targets **Godot 4.7 .NET** with the **.NET 8** SDK (9 for
Android). Read the `.csproj` first: its `Sdk="Godot.NET.Sdk/x.y.z"` is the engine version.

## Workflow

1. **Confirm the toolchain.** The project needs the Godot **.NET** editor build (the
   standard build cannot load C#) and a .NET SDK: `dotnet --list-sdks` should show 8.0 or
   later, and 9.0 or later if the project exports to Android.
2. **Every script is a `public partial class`** whose name matches its `.cs` file name and
   that extends a Godot type. The generators that wire `[Export]`, `[Signal]` and method
   bindings only work on `partial` classes.
3. **Override lifecycle methods in PascalCase** with `double` delta: `_Ready()`,
   `_Process(double delta)`, `_PhysicsProcess(double delta)`.
4. **Signals:** a `[Signal]` delegate named `XxxEventHandler` becomes the `Xxx` signal, an
   `Xxx` C# event and `SignalName.Xxx`. Emit with `EmitSignal(SignalName.Xxx, ...)`.
5. **Verify before you finish:**
   - Build: `dotnet build <project>.csproj` from the project folder must exit 0 with no
     errors. Godot's runtime does not compile C#, so a headless run uses whatever was built
     last. (`godot --headless --build-solutions --quit` also builds, through the editor.)
   - Smoke run with the .NET editor binary: `godot --headless --path <project> --quit-after 300 > run.log 2>&1`,
     then `grep -nE "SCRIPT ERROR|^ERROR:" run.log`. An unhandled exception in a callback is
     logged as an `ERROR:` with its stack trace and the game keeps running, so the exit code
     stays 0.
   - If `godot-nodes-scenes` is installed, `python3 ../godot-nodes-scenes/scripts/check_godot_project.py <project>`
     catches broken script and scene paths in `.tscn` files.
   - For behaviour tests in CI, follow `godot-gdscript-headless-testing`; build before the
     test step.

## Patterns

### 1. A node script: lifecycle, [Export], GetNode<T>

```csharp
using Godot;

public partial class Player : CharacterBody2D
{
    [Export] public float Speed { get; set; } = 200.0f;
    [Export] public float JumpVelocity { get; set; } = -400.0f;

    private AnimatedSprite2D _sprite;

    public override void _Ready()
    {
        _sprite = GetNode<AnimatedSprite2D>("AnimatedSprite2D");
    }

    public override void _PhysicsProcess(double delta)
    {
        Vector2 v = Velocity;                       // struct copy: edit, then assign back
        if (!IsOnFloor())
            v += GetGravity() * (float)delta;
        if (Input.IsActionJustPressed("jump") && IsOnFloor())
            v.Y = JumpVelocity;

        float dir = Input.GetAxis("move_left", "move_right");
        v.X = dir != 0 ? dir * Speed : Mathf.MoveToward(v.X, 0, Speed);

        Velocity = v;
        MoveAndSlide();
    }
}
```

### 2. Signals as C# events

```csharp
using Godot;

public partial class Health : Node
{
    [Signal] public delegate void HealthChangedEventHandler(int current, int max);

    private int _hp = 100;

    public override void _Ready() => HealthChanged += OnHealthChanged;

    public override void _ExitTree() => HealthChanged -= OnHealthChanged;

    public void TakeDamage(int amount)
    {
        _hp = Mathf.Max(_hp - amount, 0);
        EmitSignal(SignalName.HealthChanged, _hp, 100);
    }

    private void OnHealthChanged(int current, int max) => GD.Print($"HP {current}/{max}");
}
```

### 3. Instancing a scene

```csharp
public partial class Spawner : Node2D
{
    private static readonly PackedScene Bullet = GD.Load<PackedScene>("res://bullet.tscn");

    public void Shoot(Vector2 at)
    {
        var b = Bullet.Instantiate<Node2D>();
        b.Position = ToLocal(at);   // world -> this parent's space, before _Ready runs
        AddChild(b);
    }
}
```

### 4. Calling GDScript from C#

```csharp
Node gd = GetNode("Enemy");                       // a node with a .gd script
gd.Call("take_damage", 10);                       // snake_case names, checked at runtime
int score = gd.Get("score").AsInt32();
gd.Connect("died", Callable.From(OnDied));
```

## Gotchas

- **`Cannot find class X for script res://X.cs`** → the class name differs from the file name.
- **Build errors from generated code, or `[Export]` missing in the Inspector** → the class is
  not `partial`, or the project was not rebuilt. The Inspector only shows members from the
  last successful build.
- **`CallDeferred("AddChild", node)` does not work** → string-based engine calls (`Call`,
  `CallDeferred`, `Get`, `Set`, `Connect`) use the engine's snake_case names. Pass
  `MethodName.AddChild` (or `"add_child"`) instead.
- **An override never runs** → wrong case or signature (`_process`, or `float delta`).
  C# uses PascalCase and `double`.
- **`[Signal]` not found** → the delegate name must end in `EventHandler`; the signal is the
  name without it.
- **`ObjectDisposedException` inside a signal handler** → the receiver was freed while the
  emitter lived on, and Godot could not disconnect it because the signal is a custom
  `[Signal]` or the handler is a lambda that captures variables. Unsubscribe with `-=` in
  `_ExitTree()` (Pattern 2), and check `GodotObject.IsInstanceValid(node)` before using
  nodes that may be gone.
- **Editing `Velocity.X` will not compile** → `Vector2`, `Color` and `Transform2D` are
  structs. Copy, change, assign back.
- **A cross-language call does nothing** → names are not translated: GDScript calls a C#
  node by its C# names (`node.TakeDamage(10)`), C# calls GDScript by its snake_case names
  (`Call("take_damage", 10)`). A `Call()` with the wrong number of arguments fails without
  an error, so assert on the effect in a test.
- **`Console.WriteLine` output is missing** → use `GD.Print`/`GD.PrintErr`/`GD.PushError` so
  it reaches the Output panel and log file.
- **Web export fails** → C# projects cannot export to the web in Godot 4. Android and iOS
  work but are experimental, and iOS exports need macOS.
- **Android export fails but desktop works** → the generated `.csproj` switches to
  `net9.0` for Android, so the .NET 9 SDK is required. Keep that condition when editing the
  file.

## References

- Read `references/csharp-setup-and-interop.md` for `.csproj` details and NuGet, export
  attribute variants, `Godot.Collections` vs `System.Collections`, `await ToSignal(...)`,
  `[GlobalClass]` resources, a GDScript-to-C# API table, and per-platform export notes.

## Related skills

- `godot-gdscript`: the GDScript equivalents of these patterns.
- `godot-signals-groups`: signal architecture, language-neutral.
- `godot-resources`: data resources; `[GlobalClass]` is C#'s `class_name`.
- `godot-export`: presets and command-line exports.
- `unity-csharp-scripting`: C# in Unity, for developers coming from there.

## Version notes

Last verified: 2026-11-11 against the Godot 4.7.2 docs and engine source (C# was not built or
run for this check).

- Godot 4.7.2 (August 2026) is the current stable release; 4.8 is in beta.
- SDK minimums: .NET 8 or later, .NET 9 or later for Android exports. The generated
  `.csproj` targets `net8.0` and `net9.0` when `GodotTargetPlatform` is `android`.
- Web export: not supported for C# in Godot 4. Android and iOS: experimental since 4.2.
- Sources: [C# basics](https://docs.godotengine.org/en/stable/tutorials/scripting/c_sharp/c_sharp_basics.html),
  [C# signals](https://docs.godotengine.org/en/stable/tutorials/scripting/c_sharp/c_sharp_signals.html),
  [Cross-language scripting](https://docs.godotengine.org/en/stable/tutorials/scripting/cross_language_scripting.html),
  [ProjectGenerator.cs @ 4.7.2](https://github.com/godotengine/godot/blob/4.7.2-stable/modules/mono/editor/GodotTools/GodotTools.ProjectEditor/ProjectGenerator.cs),
  [ExceptionUtils.cs @ 4.7.2](https://github.com/godotengine/godot/blob/4.7.2-stable/modules/mono/glue/GodotSharp/GodotSharp/Core/NativeInterop/ExceptionUtils.cs),
  [Godot releases](https://github.com/godotengine/godot/releases).
