# Practical examples — guard AI, villager needs, hybrid agent

Depth for `ai-behavior-trees-utility-ai`. Three drop-in templates that assemble the BT core
(`references/behavior-tree-core.md`) and the Utility system (`references/utility-ai-system.md`) into
real agents. Same plain-C# style — bind the movement/attack leaves to your engine's transform,
navigation, and combat.

## 1. Enemy guard — Patrol → Combat behavior tree

The classic guard: patrol waypoints until it sees the player, then close in and attack on a
cooldown, and fall back to patrol when the player escapes. Two extra leaves complete the set the
core promised:

```csharp
// Patrol: walk a waypoint ring, pausing at each. Always Running (a patrol never "finishes").
public sealed class Patrol : Leaf
{
    private readonly Vector2[] _points;
    private readonly float _speed, _pause;
    private int _i;
    private float _waited;

    public Patrol(Vector2[] points, float speed = 3f, float pause = 1f)
    { _points = points; _speed = speed; _pause = pause; }

    public override Status Tick(Blackboard bb, float dt)
    {
        var pos = bb.Get<Vector2>("position");
        var goal = _points[_i];
        if ((goal - pos).magnitude > 0.2f)
        {
            bb.Set("position", pos + (goal - pos).normalized * _speed * dt);
            return Status.Running;
        }
        _waited += dt;                                  // reached a waypoint: pause, then advance
        if (_waited >= _pause) { _waited = 0f; _i = (_i + 1) % _points.Length; }
        return Status.Running;
    }

    public override void Reset() => _waited = 0f;
}

// AttackTarget: one swing. Wrap in a Cooldown decorator to rate-limit (see the assembly below).
public sealed class AttackTarget : Leaf
{
    public override Status Tick(Blackboard bb, float dt)
    {
        if (!bb.TryGet<IDamageable>("target", out var target)) return Status.Failure;
        target.ApplyDamage(10f);
        return Status.Success;
    }
}
```

Assemble and drive it. Perception writes `targetPos`/`target` onto the blackboard; the tree only
*decides*:

```csharp
public sealed class GuardAgent
{
    private readonly BehaviorTree _tree;
    private readonly Blackboard _bb = new();
    private float _decisionTimer;
    private const float TickRate = 1f / 10f;             // decide at 10 Hz, not every frame

    public GuardAgent(Vector2[] patrolRoute)
    {
        _tree = new BehaviorTree(
            new ReactiveSelector()                       // reactive: seeing the player preempts patrol
                .Add(new Sequence()                      // --- combat branch (higher priority) ---
                    .Add(new CanSeeTarget(sightRange: 12f))
                    .Add(new MoveToTarget(speed: 6f, arriveRadius: 1.5f))
                    .Add(new Cooldown(0.8f).Wrap(new AttackTarget())))
                .Add(new Patrol(patrolRoute)),           // --- fallback ---
            _bb);
    }

    // Call every frame; the tree itself only ticks on the decision cadence.
    public void Update(float dt, PerceptionResult perception)
    {
        _bb.Set("position", perception.SelfPos);
        if (perception.SeesPlayer) { _bb.Set("targetPos", perception.PlayerPos); _bb.Set("target", perception.Player); }
        else _bb.Remove("targetPos");

        _decisionTimer += dt;
        if (_decisionTimer < TickRate) return;
        _tree.Tick(_decisionTimer);
        _decisionTimer = 0f;
    }
}
```

## 2. Villager needs — Utility AI

When behavior is driven by competing *needs* rather than a fixed priority order, Utility AI is the
better fit. A villager weighs hunger, fatigue, and social need against opportunity, and does the
most-wanted thing:

```csharp
UtilityEvaluator BuildVillagerBrain()
{
    // Each action: weight * combined considerations (all 0..1). Curves shape the "want".
    var eat = new UtilityAction("Eat") { Weight = 1.2f }
        .With(new Consideration("hunger", bb => bb.Get<float>("hunger01"),
                                 t => Curves.Sigmoid(t, k: 10f, mid: 0.5f)))     // want food as hunger rises
        .With(new Consideration("hasFood", bb => bb.Get<float>("food01"), Curves.Linear));

    var sleep = new UtilityAction("Sleep") { Weight = 1f }
        .With(new Consideration("fatigue", bb => bb.Get<float>("fatigue01"),
                                 t => Curves.Quadratic(t)))                       // only strong when very tired
        .With(new Consideration("isNight", bb => bb.Get<float>("night01"), Curves.Smoothstep));

    var socialize = new UtilityAction("Socialize") { Weight = 0.8f }
        .With(new Consideration("lonely", bb => bb.Get<float>("loneliness01"), Curves.Linear))
        .With(new Consideration("friendsNear", bb => bb.Get<float>("friendsNear01"), Curves.Smoothstep));

    var work = new UtilityAction("Work") { Weight = 0.7f }
        .With(new Consideration("daytime", bb => bb.Get<float>("day01"), Curves.Smoothstep))
        .With(new Consideration("notTooTired",
              bb => 1f - bb.Get<float>("fatigue01"), Curves.Linear));            // inverted fact

    return new UtilityEvaluator().Add(eat).Add(sleep).Add(socialize).Add(work);
}

// Per decision step: pick and dispatch. Hysteresis stops the villager thrashing between near-ties.
void UpdateVillager(UtilityEvaluator brain, Blackboard bb)
{
    var choice = brain.SelectBest(bb, inertiaBonus: 0.05f);
    Dispatch(choice.Name);      // route "Eat"/"Sleep"/... to your gameplay handlers
}
```

## 3. Hybrid — a BT that delegates a choice to Utility AI

The best of both: a behavior tree gives the top-level *structure and priorities*; a utility node
makes a *graded sub-choice* (which target, which attack) inside a branch. Bridge them with a leaf
that owns a `UtilityEvaluator` and runs the winner's `Behavior` subtree.

```csharp
// A BT leaf that scores utility actions and ticks the chosen action's Behavior subtree.
public sealed class UtilitySelectorNode : Leaf
{
    private readonly UtilityEvaluator _evaluator;
    private readonly float _inertia;
    private UtilityAction _running;

    public UtilitySelectorNode(UtilityEvaluator evaluator, float inertia = 0.05f)
    { _evaluator = evaluator; _inertia = inertia; }

    public override Status Tick(Blackboard bb, float dt)
    {
        var choice = _evaluator.SelectBest(bb, _inertia);
        if (choice != _running) { _running?.Behavior?.Reset(); _running = choice; }  // switched: clean up
        return _running?.Behavior?.Tick(bb, dt) ?? Status.Failure;
    }

    public override void Reset() { _running?.Behavior?.Reset(); _running = null; }
}
```

```csharp
// Combat structured by a BT; "which attack" chosen by utility each tick.
var attackChoice = new UtilityEvaluator()
    .Add(new UtilityAction("Melee")  { Weight = 1f, Behavior = new MeleeCombo() }
        .With(new Consideration("close", bb => Curves.InverseLerp01(bb.Get<float>("distToPlayer"), 6f, 1f), Curves.Smoothstep)))
    .Add(new UtilityAction("Ranged") { Weight = 1f, Behavior = new FireVolley() }
        .With(new Consideration("far",  bb => Curves.InverseLerp01(bb.Get<float>("distToPlayer"), 2f, 14f), Curves.Smoothstep))
        .With(new Consideration("ammo", bb => bb.Get<float>("ammo01"), Curves.Linear)));

var hybrid = new BehaviorTree(
    new ReactiveSelector()
        .Add(new Sequence()
            .Add(new CanSeeTarget(12f))
            .Add(new UtilitySelectorNode(attackChoice)))   // BT picks "engage"; utility picks how
        .Add(new Patrol(route)),
    blackboard);
```

This layering is the recommended default for combat AI: keep the readable, debuggable BT for
"engage vs disengage vs patrol", and let utility handle the continuous trade-offs. The performance
and architecture trade-offs of the hybrid are in `references/best-practices-and-pitfalls.md`.
