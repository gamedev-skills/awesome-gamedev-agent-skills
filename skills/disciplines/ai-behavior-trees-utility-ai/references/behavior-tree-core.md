# Behavior Tree core — Blackboard, nodes, leaves, composites, decorators

Depth for `ai-behavior-trees-utility-ai`. A complete, allocation-conscious C# behavior-tree
runtime. The code targets plain C# (no engine types) so it drops into Unity 6 or Godot 4 C#
unchanged — bind the leaves to your engine's transform/navigation in the concrete actions.

Contract in one line: every node's `Tick` returns `Success`, `Failure`, or `Running`, and a
parent decides what that means. Build the tree once at spawn; keep per-tick work allocation-free.

## Blackboard — the shared state system

The **Blackboard** is the agent's working memory. Leaves read and write it; no node holds a
reference to another. That indirection is what lets the same `MoveTo` action serve chase, patrol,
and flee subtrees, and what makes subtrees reusable across enemy types.

```csharp
using System.Collections.Generic;

// A typed key/value store. Keys are strings (or use enum/int keys to avoid hashing cost).
public sealed class Blackboard
{
    private readonly Dictionary<string, object> _values = new();

    public void Set<T>(string key, T value) => _values[key] = value!;

    public T Get<T>(string key, T fallback = default!)
        => _values.TryGetValue(key, out var v) && v is T t ? t : fallback;

    public bool TryGet<T>(string key, out T value)
    {
        if (_values.TryGetValue(key, out var v) && v is T t) { value = t; return true; }
        value = default!;
        return false;
    }

    public bool Has(string key) => _values.ContainsKey(key);
    public void Remove(string key) => _values.Remove(key);
}
```

For hot agents, prefer a **struct-of-fields blackboard** (public fields on a class) over a string
dictionary — it removes hashing and boxing entirely. Use the dictionary form when designers add
keys at runtime or you serialize the board.

```csharp
// Zero-allocation alternative: a plain data object shared by every node on this agent.
public sealed class AgentContext
{
    public Vector2 Position;
    public Transform Target;      // null when no target
    public Vector2 Home;
    public float LastSeenTime;
    public readonly List<Vector2> Path = new();
}
```

## The node base and status

```csharp
public enum Status { Success, Failure, Running }

// Every node in the tree derives from Node. dt is the decision-step delta (may differ from frame dt).
public abstract class Node
{
    public abstract Status Tick(Blackboard bb, float dt);

    // Called when a parent stops running this node before it finished (aborted branch).
    // Override to release timers, animations, or reservations.
    public virtual void Reset() { }
}
```

`Reset()` is the half of the contract people forget. When a `Selector` switches from a running
low-priority branch to a higher-priority one, it must `Reset()` the abandoned branch so a
half-finished action (a playing attack animation, a reserved cover point) is cleaned up.

## Base classes: leaf, composite, decorator

Three structural node kinds cover every tree:

```csharp
// A leaf does the actual work; it has no children.
public abstract class Leaf : Node { }

// A composite has many children and defines how their statuses combine (see Composites below).
public abstract class Composite : Node
{
    protected readonly List<Node> Children = new();
    protected int Current;                       // resume index for Running composites

    public Composite Add(Node child) { Children.Add(child); return this; }

    public override void Reset()
    {
        Current = 0;
        foreach (var c in Children) c.Reset();
    }
}

// A decorator wraps exactly one child and transforms its status or gates it (see Decorators below).
public abstract class Decorator : Node
{
    protected Node Child = default!;
    public Decorator Wrap(Node child) { Child = child; return this; }
    public override void Reset() => Child.Reset();
}
```

## Condition leaves — instantaneous predicates

A **condition** reads the blackboard and returns `Success` or `Failure` in the same tick. It never
returns `Running` and never mutates game state. Express reusable predicates as one small class with
an injected test, or subclass for named conditions.

```csharp
// Generic condition: succeed when a predicate over the blackboard holds.
public sealed class Condition : Leaf
{
    private readonly System.Func<Blackboard, bool> _predicate;
    public Condition(System.Func<Blackboard, bool> predicate) => _predicate = predicate;

    public override Status Tick(Blackboard bb, float dt)
        => _predicate(bb) ? Status.Success : Status.Failure;
}

// Named condition when the check is non-trivial or reused across trees.
public sealed class CanSeeTarget : Leaf
{
    private readonly float _sightRange;
    public CanSeeTarget(float sightRange) => _sightRange = sightRange;

    public override Status Tick(Blackboard bb, float dt)
    {
        if (!bb.TryGet<Vector2>("targetPos", out var target)) return Status.Failure;
        var self = bb.Get<Vector2>("position");
        // Real games also raycast for line of sight; keep the check cheap and cache the result.
        return (target - self).sqrMagnitude <= _sightRange * _sightRange
            ? Status.Success : Status.Failure;
    }
}
```

Note the pre-allocated `System.Func` delegate: create conditions **once** when the tree is built,
not per tick, so no closure is allocated during evaluation.

## Action leaves — multi-frame work that returns Running

An **action** performs work and returns `Running` until it completes, then `Success` (or `Failure`
if it can't). Returning `Running` is what lets a walk, an animation, or a timed wait span many
ticks without the parent restarting it.

```csharp
// Move toward a blackboard target; Running until within arrive radius, then Success.
public sealed class MoveToTarget : Leaf
{
    private readonly float _speed, _arriveRadius;
    public MoveToTarget(float speed, float arriveRadius)
    { _speed = speed; _arriveRadius = arriveRadius; }

    public override Status Tick(Blackboard bb, float dt)
    {
        if (!bb.TryGet<Vector2>("targetPos", out var target)) return Status.Failure;
        var pos = bb.Get<Vector2>("position");
        var offset = target - pos;
        if (offset.magnitude <= _arriveRadius) return Status.Success;   // arrived

        pos += offset.normalized * _speed * dt;
        bb.Set("position", pos);          // in an engine, drive the NavMeshAgent / CharacterBody here
        return Status.Running;            // keep going next tick
    }
}

// A timed wait — the canonical Running action, useful for patrol pauses and cooldown holds.
public sealed class Wait : Leaf
{
    private readonly float _duration;
    private float _elapsed;
    public Wait(float duration) => _duration = duration;

    public override Status Tick(Blackboard bb, float dt)
    {
        _elapsed += dt;
        if (_elapsed < _duration) return Status.Running;
        return Status.Success;
    }

    public override void Reset() => _elapsed = 0f;   // restart cleanly if the branch is re-entered
}
```

`Wait` shows why `Reset()` matters: its `_elapsed` accumulator must be cleared when the branch is
abandoned and later re-entered, or the second wait finishes instantly.

The `Sequence`/`Selector`/`Parallel` execution logic and the decorator library build directly on
these base classes — see the composites and decorators sections below.

## Composites — how child statuses combine

Composites are the control flow of a tree. The two you use constantly are `Sequence` (AND) and
`Selector` (OR/fallback); `Parallel` covers concurrent branches.

```csharp
// Sequence = AND: tick children in order; stop at the first that is not Success.
// Resumes at the Running child next tick ("memory" variant).
public sealed class Sequence : Composite
{
    public override Status Tick(Blackboard bb, float dt)
    {
        for (; Current < Children.Count; Current++)
        {
            var s = Children[Current].Tick(bb, dt);
            if (s == Status.Running) return Status.Running;   // resume here next tick
            if (s == Status.Failure) { Current = 0; return Status.Failure; }
        }
        Current = 0;
        return Status.Success;                                // every child succeeded
    }
}

// Selector = OR / fallback: return the first child that is not Failure.
public sealed class Selector : Composite
{
    public override Status Tick(Blackboard bb, float dt)
    {
        for (; Current < Children.Count; Current++)
        {
            var s = Children[Current].Tick(bb, dt);
            if (s == Status.Running) return Status.Running;   // resume here next tick
            if (s == Status.Success) { Current = 0; return Status.Success; }
        }
        Current = 0;
        return Status.Failure;                                // every child failed
    }
}
```

**Memory vs reactive.** The versions above *remember* the `Running` child and resume there. That is
efficient but does not let a higher-priority sibling interrupt. For a **reactive** selector — the
common case for combat AI — re-check children from index 0 every tick and abort the running branch
when an earlier child changes its mind:

```csharp
// Reactive selector: earlier (higher-priority) children can preempt a lower running branch.
public sealed class ReactiveSelector : Composite
{
    private int _running = -1;
    public override Status Tick(Blackboard bb, float dt)
    {
        for (int i = 0; i < Children.Count; i++)
        {
            var s = Children[i].Tick(bb, dt);
            if (s == Status.Failure) continue;
            if (_running != -1 && _running != i) Children[_running].Reset();  // abort old branch
            _running = s == Status.Running ? i : -1;
            return s;                                       // Success or Running
        }
        _running = -1;
        return Status.Failure;
    }

    public override void Reset() { base.Reset(); _running = -1; }
}
```

`Parallel` ticks every child each step and resolves with a policy — succeed when *any* (or *all*)
succeed, fail when *any* (or *all*) fail. Use it for "attack while strafing" or "play VFX while
moving".

```csharp
public enum ParallelPolicy { RequireOne, RequireAll }

public sealed class Parallel : Composite
{
    private readonly ParallelPolicy _success, _failure;
    public Parallel(ParallelPolicy success, ParallelPolicy failure)
    { _success = success; _failure = failure; }

    public override Status Tick(Blackboard bb, float dt)
    {
        int successes = 0, failures = 0;
        foreach (var child in Children)
        {
            var s = child.Tick(bb, dt);
            if (s == Status.Success) successes++;
            else if (s == Status.Failure) failures++;
        }
        if (_failure == ParallelPolicy.RequireOne && failures > 0) return Status.Failure;
        if (_failure == ParallelPolicy.RequireAll && failures == Children.Count) return Status.Failure;
        if (_success == ParallelPolicy.RequireOne && successes > 0) return Status.Success;
        if (_success == ParallelPolicy.RequireAll && successes == Children.Count) return Status.Success;
        return Status.Running;
    }
}
```

## Decorators — wrap one child to change its meaning

Decorators add policy without new leaves: invert a result, force a status, gate on a cooldown, or
repeat. Each wraps exactly one child.

```csharp
// Inverter: Success <-> Failure (Running passes through). "NOT".
public sealed class Inverter : Decorator
{
    public override Status Tick(Blackboard bb, float dt) => Child.Tick(bb, dt) switch
    {
        Status.Success => Status.Failure,
        Status.Failure => Status.Success,
        _              => Status.Running,
    };
}

// ForceSuccess: swallow a child's failure so a Sequence keeps going (optional steps).
public sealed class ForceSuccess : Decorator
{
    public override Status Tick(Blackboard bb, float dt)
        => Child.Tick(bb, dt) == Status.Running ? Status.Running : Status.Success;
}

// Repeat: run the child up to n times (n <= 0 = forever), restarting on each Success.
public sealed class Repeat : Decorator
{
    private readonly int _count;
    private int _done;
    public Repeat(int count) => _count = count;

    public override Status Tick(Blackboard bb, float dt)
    {
        var s = Child.Tick(bb, dt);
        if (s == Status.Running) return Status.Running;
        if (s == Status.Failure) { _done = 0; return Status.Failure; }
        _done++;
        if (_count > 0 && _done >= _count) { _done = 0; return Status.Success; }
        Child.Reset();                        // loop again
        return Status.Running;
    }

    public override void Reset() { base.Reset(); _done = 0; }
}

// Cooldown: gate the child so it can only run once per interval (attack/ability rate-limiting).
public sealed class Cooldown : Decorator
{
    private readonly float _seconds;
    private float _readyAt;
    public Cooldown(float seconds) => _seconds = seconds;

    public override Status Tick(Blackboard bb, float dt)
    {
        float now = bb.Get<float>("time");
        if (now < _readyAt) return Status.Failure;     // still cooling down
        var s = Child.Tick(bb, dt);
        if (s == Status.Success) _readyAt = now + _seconds;
        return s;
    }

    public override void Reset() { base.Reset(); _readyAt = 0f; }
}
```

## Running the tree

Wrap the root and tick it on your decision cadence. A behavior tree does **not** need to tick every
render frame — 5–15 Hz is plenty for most NPCs and slashes CPU cost.

```csharp
public sealed class BehaviorTree
{
    private readonly Node _root;
    private readonly Blackboard _bb;
    public BehaviorTree(Node root, Blackboard bb) { _root = root; _bb = bb; }

    public Status Tick(float dt)
    {
        _bb.Set("time", _bb.Get<float>("time") + dt);   // keep a clock for Cooldown/Wait
        return _root.Tick(_bb, dt);
    }
}

// Fluent assembly — build once at spawn, then tick.
var tree = new BehaviorTree(
    new ReactiveSelector()
        .Add(new Sequence()                              // combat branch (highest priority)
            .Add(new CanSeeTarget(sightRange: 12f))
            .Add(new MoveToTarget(speed: 6f, arriveRadius: 1.5f))
            .Add(new Cooldown(0.8f).Wrap(new AttackTarget())))
        .Add(new Patrol(waypoints)),                     // fallback
    blackboard);
```

The `Patrol` and `AttackTarget` leaves, and full agents that assemble these pieces, are in
`references/practical-examples.md`.
