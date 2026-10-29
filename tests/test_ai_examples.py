"""Compile published BT/Utility C# fragments and exercise their lifecycle contracts."""
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills/disciplines/ai-behavior-trees-utility-ai"
DOTNET = shutil.which("dotnet")


def csharp_block(path, marker):
    blocks = re.findall(r"```csharp\n(.*?)```", path.read_text(encoding="utf-8"), re.S)
    matches = [block for block in blocks if marker in block]
    if len(matches) != 1:
        raise AssertionError(f"Expected one C# block containing {marker!r} in {path}")
    return matches[0]


def published_source():
    core = SKILL / "references/behavior-tree-core.md"
    utility = SKILL / "references/utility-ai-system.md"
    practical = SKILL / "references/practical-examples.md"
    fragments = [csharp_block(core, "public sealed class Blackboard")]
    for marker in ("public enum Status", "public abstract class Leaf",
                   "public sealed class Sequence", "public sealed class ReactiveSelector",
                   "public sealed class ReactiveSequence", "public enum ParallelPolicy",
                   "public sealed class Inverter"):
        fragments.append(csharp_block(core, marker))
    # Keep the engine-neutral definitions verbatim, leaving the movement bindings to the engine.
    fragments.append(csharp_block(core, "public sealed class Condition").split("// Named condition")[0])
    fragments.append("public sealed class Wait" + csharp_block(core, "public sealed class Wait")
                     .split("public sealed class Wait", 1)[1])
    fragments.append(csharp_block(core, "public sealed class BehaviorTree")
                     .split("// Fluent assembly")[0])
    for marker in ("public static class Curves", "public sealed class Consideration",
                   "public sealed class UtilityAction", "public sealed class UtilityEvaluator"):
        fragments.append(csharp_block(utility, marker))
    fragments.append(csharp_block(practical, "public sealed class UtilitySelectorNode"))
    fragments.append("namespace EntryExample {\n" +
                     csharp_block(SKILL / "SKILL.md", "public sealed class Selector") + "\n}")
    fragments.append("public sealed class VillagerExample {\n" +
                     csharp_block(practical, "UtilityEvaluator BuildVillagerBrain()") + r'''
    public readonly List<string> Dispatched = new();
    void Dispatch(string action) => Dispatched.Add(action);
    public UtilityEvaluator Build() => BuildVillagerBrain();
    public void Run(UtilityEvaluator brain, Blackboard bb) => UpdateVillager(brain, bb);
}
''')
    return "\n".join(fragments) + HARNESS


HARNESS = r'''
public sealed class Probe : Leaf
{
    public int Ticks, TotalTicks;
    public int TerminalAfter;
    public Status TerminalStatus;
    public Probe(int after, Status status = Status.Success)
    { TerminalAfter = after; TerminalStatus = status; }
    public override Status Tick(Blackboard bb, float dt)
    {
        Ticks++; TotalTicks++;
        return Ticks >= TerminalAfter ? TerminalStatus : Status.Running;
    }
    public override void Reset() => Ticks = 0;
}

public sealed class FixedRandom : System.Random
{
    private readonly double _value;
    public FixedRandom(double value) => _value = value;
    public override double NextDouble() => _value;
}

public static class Program
{
    static void Check(bool condition, string message)
    {
        if (!condition) throw new System.Exception(message);
    }
    static void Expect(BehaviorTree tree, params Status[] expected)
    {
        foreach (var status in expected)
            Check(tree.Tick(0.25f) == status, $"Expected {status}");
    }
    static UtilityAction Scored(string name, string key, Node behavior = null)
        => new UtilityAction(name) { Behavior = behavior }
            .With(new Consideration(key, bb => bb.Get<float>(key), Curves.Linear));

    public static void RootAndSequenceWaitRepeat()
    {
        var round = new[] { Status.Running, Status.Running, Status.Running, Status.Success };
        foreach (Node root in new Node[] { new Wait(1f), new Sequence().Add(new Wait(1f)) })
        {
            var tree = new BehaviorTree(root, new Blackboard());
            Expect(tree, round);
            Expect(tree, round);
        }
    }

    public static void CompletedChildrenResetWhileParentRuns()
    {
        var bb = new Blackboard();
        var done = new Probe(1);
        var later = new Probe(3);
        var sequence = new Sequence().Add(done).Add(later);
        Check(sequence.Tick(bb, 0.25f) == Status.Running, "sequence should wait for later child");
        Check(done.Ticks == 0 && later.Ticks == 1, "completed child reset must be immediate");
        Check(sequence.Tick(bb, 0.25f) == Status.Running && done.TotalTicks == 1,
              "memory sequence must not re-tick a completed child");
        sequence.Reset();
        Check(later.Ticks == 0, "aborted sequence must reset running child");

        foreach (Composite selector in new Composite[] { new Selector(), new EntryExample.Selector() })
        {
            var failed = new Probe(1, Status.Failure);
            var running = new Probe(3);
            selector.Add(failed).Add(running);
            Check(selector.Tick(bb, 0.25f) == Status.Running, "selector should use fallback");
            Check(failed.Ticks == 0 && running.Ticks == 1, "failed child must reset immediately");
        }
    }

    public static void ReactiveBranchesAbortAndReenter()
    {
        var bb = new Blackboard();
        var low = new Probe(3);
        var selector = new ReactiveSelector().Add(new Condition(b => b.Get<bool>("urgent"))).Add(low);
        Check(selector.Tick(bb, 0.25f) == Status.Running && low.Ticks == 1, "fallback should start");
        bb.Set("urgent", true);
        Check(selector.Tick(bb, 0.25f) == Status.Success && low.Ticks == 0, "preemption must abort fallback");
        bb.Set("urgent", false);
        Check(selector.Tick(bb, 0.25f) == Status.Running && low.Ticks == 1, "fallback must restart cleanly");

        var action = new Probe(3);
        var sequence = new ReactiveSequence().Add(new Condition(b => b.Get<bool>("visible"))).Add(action);
        bb.Set("visible", true);
        Check(sequence.Tick(bb, 0.25f) == Status.Running, "guard should allow action");
        bb.Set("visible", false);
        Check(sequence.Tick(bb, 0.25f) == Status.Failure && action.Ticks == 0, "lost guard must abort action");
        bb.Set("visible", true);
        Check(sequence.Tick(bb, 0.25f) == Status.Running && action.Ticks == 1, "action must restart");

        var failure = new Probe(1, Status.Failure);
        var fallback = new Probe(3);
        var failover = new ReactiveSelector().Add(failure).Add(fallback);
        Check(failover.Tick(bb, 0.25f) == Status.Running && failure.Ticks == 0,
              "reactive selector must reset terminal failed child");
        var success = new Probe(1);
        var guarded = new ReactiveSequence().Add(success).Add(new Probe(3));
        Check(guarded.Tick(bb, 0.25f) == Status.Running && success.Ticks == 0,
              "reactive sequence must reset terminal successful child");
    }

    public static void DecoratorsResetTerminalChildren()
    {
        var bb = new Blackboard();
        foreach (Decorator decorator in new Decorator[] { new Inverter(), new ForceSuccess(), new Cooldown(1f) })
        {
            var leaf = new Probe(1, Status.Failure);
            decorator.Wrap(leaf);
            decorator.Tick(bb, 0.25f);
            Check(leaf.Ticks == 0, "decorator must reset terminal failure immediately");
        }
        foreach (Node root in new Node[] {
            new Inverter().Wrap(new Wait(0.5f)), new ForceSuccess().Wrap(new Wait(0.5f)) })
        {
            var tree = new BehaviorTree(root, new Blackboard());
            var terminal = root is Inverter ? Status.Failure : Status.Success;
            Expect(tree, Status.Running, terminal, Status.Running, terminal);
        }
        var failed = new Probe(1, Status.Failure);
        var repeat = new Repeat(2).Wrap(failed);
        Check(repeat.Tick(bb, 0.25f) == Status.Failure && failed.Ticks == 0,
              "repeat must reset a failed child");
        var final = new Probe(1);
        Check(new Repeat(1).Wrap(final).Tick(bb, 0.25f) == Status.Success && final.Ticks == 0,
              "repeat must reset its final successful child");
    }

    public static void RepeatAndParallelReuse()
    {
        var repeated = new BehaviorTree(new Repeat(2).Wrap(new Wait(0.5f)), new Blackboard());
        Expect(repeated, Status.Running, Status.Running, Status.Running, Status.Success);
        Expect(repeated, Status.Running, Status.Running, Status.Running, Status.Success);
        var bb = new Blackboard();
        var fast = new Probe(1);
        var slow = new Probe(3);
        var parallel = new Parallel(ParallelPolicy.RequireAll, ParallelPolicy.RequireOne).Add(fast).Add(slow);
        Check(parallel.Tick(bb, 0.25f) == Status.Running && fast.Ticks == 0,
              "parallel must reset a completed child while retaining its result");
        Check(parallel.Tick(bb, 0.25f) == Status.Running && fast.TotalTicks == 1,
              "parallel must not re-tick its completed child");
        Check(parallel.Tick(bb, 0.25f) == Status.Success && slow.Ticks == 0, "parallel should finish");
        Check(parallel.Tick(bb, 0.25f) == Status.Running && fast.TotalTicks == 2 && slow.Ticks == 1,
              "parallel must start a fresh execution");
        parallel.Reset();
        Check(slow.Ticks == 0 && parallel.Tick(bb, 0.25f) == Status.Running && fast.TotalTicks == 3,
              "explicit abort must clear cached terminal results");
        foreach (Status result in new[] { Status.Success, Status.Failure })
        {
            var pending = new Probe(10);
            var early = new Parallel(ParallelPolicy.RequireOne, ParallelPolicy.RequireOne)
                .Add(new Probe(1, result)).Add(pending);
            Check(early.Tick(bb, 0.25f) == result && pending.Ticks == 0,
                  "parallel terminal policy must abort unfinished siblings");
        }
    }

    public static void CooldownDeadlineSurvivesResets()
    {
        var bb = new Blackboard();
        var leaf = new Probe(1);
        var cooldown = new Cooldown(1f).Wrap(leaf);
        var tree = new BehaviorTree(cooldown, bb);
        Expect(tree, Status.Success);
        Check(leaf.Ticks == 0, "successful cooldown child should reset");
        cooldown.Reset();
        Expect(tree, Status.Failure, Status.Failure, Status.Failure, Status.Success);
        Check(leaf.TotalTicks == 2, "ancestor cleanup must not bypass cooldown deadline");
    }

    public static void UtilityBestHonorsVeto()
    {
        var bb = new Blackboard();
        var a = Scored("A", "a"); var b = Scored("B", "b");
        var evaluator = new UtilityEvaluator().Add(a).Add(b).Add(new UtilityAction("negative") { Weight = -1f });
        bb.Set("a", 1f); bb.Set("b", 0.01f);
        Check(evaluator.SelectBest(bb) == a, "A should be selected initially");
        bb.Set("a", 0f);
        Check(evaluator.SelectBest(bb) == b, "inertia must not revive a zero raw score");
        bb.Set("b", 0f);
        Check(evaluator.SelectBest(bb) == null, "all vetoed must return null");
        bb.Set("a", 0.02f); bb.Set("b", 0.01f);
        Check(evaluator.SelectBest(bb) == a, "no-action selection must clear previous inertia");
        Check(new UtilityEvaluator().SelectBest(bb) == null, "empty evaluator must return null");
        bb.Set("a", 0.00001f);
        Check(new UtilityEvaluator().Add(a).SelectBest(bb) == a, "positive near-zero is not a hard veto");
    }

    public static void UtilitySoftmaxHonorsVeto()
    {
        var bb = new Blackboard();
        var a = Scored("A", "a");
        var evaluator = new UtilityEvaluator().Add(new UtilityAction("zero-first") { Weight = 0f })
            .Add(a).Add(new UtilityAction("zero-last") { Weight = 0f })
            .Add(new UtilityAction("negative") { Weight = -1f });
        bb.Set("a", 1f);
        foreach (double roll in new[] { 0.0, 0.5, 0.999999999 })
            Check(evaluator.SelectSoftmax(bb, new FixedRandom(roll)) == a,
                  "softmax must never choose vetoed actions, including boundary rolls");
        var high = new UtilityAction("high") { Weight = 1f };
        var low = new UtilityAction("low") { Weight = 0.01f };
        var underflow = new UtilityEvaluator().Add(high).Add(low);
        Check(underflow.SelectSoftmax(bb, new FixedRandom(0.999999999), 0.0001f) == high,
              "near-one random rolls must not choose a trailing underflowed zero weight");
        bb.Set("a", 0f);
        Check(evaluator.SelectSoftmax(bb, new FixedRandom(0)) == null, "all vetoed softmax must return null");
        Check(new UtilityEvaluator().SelectSoftmax(bb, new FixedRandom(0)) == null,
              "empty softmax must return null");
        bb.Set("a", 0.00001f);
        Check(evaluator.SelectSoftmax(bb, new FixedRandom(0)) == a, "positive near-zero must remain eligible");
        bb.Set("b", 0.02f); bb.Set("a", 0.01f);
        var b = Scored("B", "b");
        var clearInertia = new UtilityEvaluator().Add(a).Add(b);
        Check(clearInertia.SelectBest(bb) == b, "B should initially win");
        bb.Set("a", 0f); bb.Set("b", 0f);
        Check(clearInertia.SelectSoftmax(bb, new FixedRandom(0)) == null, "softmax must clear commitment");
        bb.Set("a", 0.02f); bb.Set("b", 0.01f);
        Check(clearInertia.SelectBest(bb) == a, "softmax no-action must clear inertia for later argmax");
    }

    public static void UtilityCallersHandleNoActionAndSubtreeLifecycle()
    {
        var bb = new Blackboard();
        var villager = new VillagerExample();
        var brain = villager.Build();
        villager.Run(brain, bb);
        Check(villager.Dispatched.Count == 0, "villager must tolerate no available action");
        bb.Set("food01", 1f); bb.Set("hunger01", 1f);
        villager.Run(brain, bb);
        Check(villager.Dispatched.Count == 1 && villager.Dispatched[0] == "Eat", "villager should dispatch winner");

        var action = new Probe(2);
        var hybrid = new UtilitySelectorNode(new UtilityEvaluator().Add(Scored("A", "a", action)));
        bb.Set("a", 1f);
        Check(hybrid.Tick(bb, 0.25f) == Status.Running, "hybrid action should begin");
        Check(hybrid.Tick(bb, 0.25f) == Status.Success && action.Ticks == 0, "hybrid must reset terminal subtree");
        Check(hybrid.Tick(bb, 0.25f) == Status.Running && action.Ticks == 1, "hybrid must re-enter cleanly");
        bb.Set("a", 0f);
        Check(hybrid.Tick(bb, 0.25f) == Status.Failure && action.Ticks == 0,
              "no eligible utility action must abort the running subtree");
    }

    public static void Main(string[] args)
    {
        typeof(Program).GetMethod(args[0]).Invoke(null, null);
        System.Console.WriteLine(args[0] + " passed");
    }
}
'''


@unittest.skipUnless(DOTNET, ".NET 10 SDK required to execute C# examples")
class AIExamplesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sdks = subprocess.run([DOTNET, "--list-sdks"], capture_output=True, text=True, timeout=15)
        versions = re.findall(r"^(10\.\S+)\s", sdks.stdout, re.M)
        if not versions:
            raise unittest.SkipTest(".NET 10 SDK required to execute C# examples")
        cls.temp = tempfile.TemporaryDirectory(prefix="ai-examples-")
        cls.addClassCleanup(cls.temp.cleanup)
        project = Path(cls.temp.name)
        cls.env = dict(os.environ, DOTNET_CLI_HOME=str(project / ".dotnet"),
                       DOTNET_CLI_TELEMETRY_OPTOUT="1", DOTNET_NOLOGO="1",
                       DOTNET_SKIP_FIRST_TIME_EXPERIENCE="1")
        (project / "global.json").write_text(
            '{"sdk":{"version":"' + versions[-1] + '"}}', encoding="utf-8")
        (project / "NuGet.Config").write_text(
            '<configuration><packageSources><clear /></packageSources></configuration>', encoding="utf-8")
        (project / "AIExamples.csproj").write_text('''<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net10.0</TargetFramework>
    <Nullable>disable</Nullable>
  </PropertyGroup>
</Project>
''', encoding="utf-8")
        (project / "Program.cs").write_text(published_source(), encoding="utf-8")
        result = subprocess.run([DOTNET, "build", "--nologo", "--verbosity", "quiet",
                                 "-p:UseSharedCompilation=false"], cwd=project, env=cls.env,
                                capture_output=True, text=True, timeout=90)
        if result.returncode:
            raise AssertionError(result.stdout + result.stderr)
        cls.program = project / "bin/Debug/net10.0/AIExamples.dll"

    def run_scenario(self, name):
        result = subprocess.run([DOTNET, str(self.program), name], env=self.env,
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_wait_repeats_at_root_and_in_sequence(self):
        self.run_scenario("RootAndSequenceWaitRepeat")

    def test_completed_children_reset_before_parent_finishes(self):
        self.run_scenario("CompletedChildrenResetWhileParentRuns")

    def test_reactive_branches_abort_and_reenter(self):
        self.run_scenario("ReactiveBranchesAbortAndReenter")

    def test_decorators_reset_terminal_children(self):
        self.run_scenario("DecoratorsResetTerminalChildren")

    def test_repeat_and_parallel_reuse(self):
        self.run_scenario("RepeatAndParallelReuse")

    def test_cooldown_deadline_survives_resets(self):
        self.run_scenario("CooldownDeadlineSurvivesResets")

    def test_utility_argmax_does_not_revive_zero_scores(self):
        self.run_scenario("UtilityBestHonorsVeto")

    def test_utility_softmax_excludes_zero_even_at_roll_zero(self):
        self.run_scenario("UtilitySoftmaxHonorsVeto")

    def test_utility_callers_handle_no_action_and_subtree_lifecycle(self):
        self.run_scenario("UtilityCallersHandleNoActionAndSubtreeLifecycle")


if __name__ == "__main__":
    unittest.main()
