# Utility AI system — curves, considerations, evaluator

Depth for `ai-behavior-trees-utility-ai`. Utility AI turns *"which action do I want most right
now?"* into arithmetic: describe each candidate action with a few **considerations**, map each raw
fact through a **normalized response curve** to 0..1, combine them into a score, and select. Same
C#-only style as the BT core, so it composes with it (see the hybrid section in
`references/practical-examples.md`).

Golden rule: **every consideration outputs 0..1.** Mixing ranges (one 0..1, one 0..100) lets the
big one dominate and makes weights meaningless.

## Response-curve library

Curves shape *how* a fact translates to desire. `t` is a normalized 0..1 input (use
`InverseLerp01` to normalize a raw fact first). All outputs are clamped to 0..1.

```csharp
public static class Curves
{
    public static float Clamp01(float x) => x < 0f ? 0f : x > 1f ? 1f : x;

    // Normalize a raw fact into 0..1 (a==0 output, b==1 output). Handles inverted ranges (a>b).
    public static float InverseLerp01(float x, float a, float b)
        => a == b ? (x >= b ? 1f : 0f) : Clamp01((x - a) / (b - a));

    // Linear: desire tracks the fact directly.
    public static float Linear(float t, float slope = 1f, float yIntercept = 0f)
        => Clamp01(slope * t + yIntercept);

    // Polynomial: exponent>1 = ease-in (low until high t); exponent<1 = ease-out (rises fast early).
    public static float Polynomial(float t, float exponent)
        => Clamp01((float)System.Math.Pow(Clamp01(t), exponent));

    public static float Quadratic(float t) => Polynomial(t, 2f);      // slow start, sharp finish
    public static float InverseQuadratic(float t)                     // fast start, gentle finish
        => Clamp01(1f - (1f - Clamp01(t)) * (1f - Clamp01(t)));

    // Exponential: k>0 grows steeply near 1; useful for "only care when nearly full/empty".
    public static float Exponential(float t, float k = 4f)
        => Clamp01(((float)System.Math.Exp(k * Clamp01(t)) - 1f) / (System.MathF.Exp(k) - 1f));

    // Logistic / sigmoid: a smooth S-curve with an adjustable threshold. k = steepness, mid = 0.5 crossing.
    public static float Sigmoid(float t, float k = 8f, float mid = 0.5f)
        => Clamp01(1f / (1f + System.MathF.Exp(-k * (Clamp01(t) - mid))));

    // Smoothstep: eased 0..1 with zero slope at both ends; good default for "soft threshold".
    public static float Smoothstep(float t) { t = Clamp01(t); return t * t * (3f - 2f * t); }
}
```

Pick by intent: **Linear** for proportional wants; **Quadratic/Exponential** for "only matters at
the extreme"; **Sigmoid/Smoothstep** for a soft threshold (flee when health crosses ~40%); invert
any curve with `1 - curve(t)` (e.g. desire-to-heal rises as health falls).

## Considerations — one fact, one curve

A **consideration** binds a fact reader to a curve and yields a 0..1 factor. Build them once and
reuse; they hold no per-tick state.

```csharp
public sealed class Consideration
{
    public readonly string Name;
    private readonly System.Func<Blackboard, float> _fact;   // raw or pre-normalized fact
    private readonly System.Func<float, float> _curve;       // maps the fact to 0..1

    public Consideration(string name, System.Func<Blackboard, float> fact,
                         System.Func<float, float> curve)
    { Name = name; _fact = fact; _curve = curve; }

    public float Evaluate(Blackboard bb) => Curves.Clamp01(_curve(_fact(bb)));
}
```

```csharp
// Example considerations for a "attack the player" action.
var proximity = new Consideration("proximity",
    bb => Curves.InverseLerp01(bb.Get<float>("distToPlayer"), 20f, 2f),  // near -> 1
    Curves.Smoothstep);

var myHealth = new Consideration("myHealth",
    bb => bb.Get<float>("health01"),
    t => Curves.Sigmoid(t, k: 8f, mid: 0.35f));                          // low health -> low desire
```

## Scored actions and the compensation factor

A `UtilityAction` scores as its `weight` times the **combined** considerations. Multiplying factors
is standard (a single near-zero consideration should veto the action), but naive multiplication
over-punishes as you add considerations. Apply Dave Mark's **compensation factor** so more
considerations don't unfairly drag the score down.

```csharp
public sealed class UtilityAction
{
    public readonly string Name;
    public float Weight = 1f;
    public readonly List<Consideration> Considerations = new();
    public Node Behavior;                         // optional BT subtree to run when chosen (hybrid)

    public UtilityAction(string name) => Name = name;
    public UtilityAction With(Consideration c) { Considerations.Add(c); return this; }

    public float Score(Blackboard bb)
    {
        int n = Considerations.Count;
        if (n == 0) return Weight;

        float product = 1f;
        for (int i = 0; i < n; i++) product *= Considerations[i].Evaluate(bb);

        // Compensation: add back some of what extra factors removed. modFactor -> 0 as n grows.
        float modFactor = 1f - 1f / n;
        float makeUp = (1f - product) * modFactor;
        float compensated = product + makeUp * product;

        return Weight * Curves.Clamp01(compensated);
    }
}
```

## The evaluator — scoring and selection

The evaluator scores every action and selects one. Offer three strategies: **argmax** (best),
**softmax** (probabilistic, weighted by score — variety without dumb choices), and
**weighted-random** over raw scores. Add **hysteresis** (an inertia bonus for the current action)
so agents commit instead of flip-flopping on near-ties.

```csharp
public sealed class UtilityEvaluator
{
    private readonly List<UtilityAction> _actions = new();
    private UtilityAction _current;

    public UtilityEvaluator Add(UtilityAction a) { _actions.Add(a); return this; }

    // Argmax with hysteresis: the currently-committed action gets a small bonus.
    public UtilityAction SelectBest(Blackboard bb, float inertiaBonus = 0.05f)
    {
        UtilityAction best = null; float bestScore = float.NegativeInfinity;
        foreach (var a in _actions)
        {
            float s = a.Score(bb);
            if (a == _current) s += inertiaBonus;      // stickiness to avoid jitter
            if (s > bestScore) { bestScore = s; best = a; }
        }
        _current = best;
        return best;
    }

    // Softmax: choose proportionally to exp(score/temperature). Higher temp = more random.
    public UtilityAction SelectSoftmax(Blackboard bb, System.Random rng, float temperature = 0.2f)
    {
        float sum = 0f;
        var weights = new float[_actions.Count];
        for (int i = 0; i < _actions.Count; i++)
        {
            weights[i] = System.MathF.Exp(_actions[i].Score(bb) / System.MathF.Max(temperature, 1e-4f));
            sum += weights[i];
        }
        float roll = (float)rng.NextDouble() * sum;
        for (int i = 0; i < weights.Length; i++)
            if ((roll -= weights[i]) <= 0f) { _current = _actions[i]; return _actions[i]; }
        _current = _actions[^1];
        return _current;
    }
}
```

Usage: score every decision step, then run the winner's `Behavior` (hybrid) or call its handler
directly. Verify by drawing each action's live score as a debug bar while tuning — utility bugs are
almost always a mis-shaped curve or an un-normalized fact, and both are obvious on screen. The
worked villager-needs evaluator and the BT+Utility hybrid are in
`references/practical-examples.md`.
