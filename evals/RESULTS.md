# Eval results (2026-11-11)

How the v2 skills were tested before release, and what came out. These are model-judged
results, not user studies; read the method notes before quoting a number.

## 1. Trigger accuracy

**Set:** `evals/triggers.json`, 366 prompts written the way people type in a coding agent:
237 should-trigger (3 per skill), 79 near-misses (1 per skill, shares keywords with the skill
but needs another one or none), 30 prompts that need 2 or 3 skills, and 20 that need none.

**Method:** a separate agent saw only the skill names and descriptions plus the prompts, never
the expected answers, and picked 0 to 3 skills per prompt. Three judges split the prompts. We
ran it with Claude Opus 5.5 and Claude Haiku 5.5, on the descriptions before this release and
on the final ones. `router` is ignored when scoring.

| Judge | Descriptions | Precision | Recall | Should | Near-miss | Combo | None |
|---|---|--:|--:|--:|--:|--:|--:|
| Opus 5.5 | before (31,355 chars total) | 0.984 | 0.979 | 99.6% | 97.5% | 80.0% | 100% |
| Opus 5.5 | v2 (29,866 chars total) | 0.973 | 0.963 | 98.7% | 97.5% | 80.0% | 100% |
| Haiku 5.5 | before | 0.958 | 0.979 | 99.2% | 91.1% | 90.0% | 100% |
| Haiku 5.5 | v2 | 0.945 | 0.966 | 97.9% | 96.2% | 90.0% | 100% |

**What it means:** triggering stayed about where it was while the descriptions got shorter and
now name their neighbours. The small model got much better at near-misses (91.1% to 96.2%).
Most of the remaining "errors" are an engine skill loaded together with its matching discipline
skill (for example `godot-ui-control` with `game-ui-ux`), which the router allows.

**Why the descriptions are short:** Claude Code lists skill descriptions within a budget of 1% of
the model's context window and drops the descriptions of the least-used skills when the list is
too long ([Claude Code docs](https://code.claude.com/docs/en/skills)). The first rewrite of the
descriptions reached 56,142 characters for the full pack; the v2 set is 29,866.

## 2. Outcome A/B for the two new skills

**Method:** the same three tasks were given to an agent with the skill and to one without it.
A third agent, told only "assistant A" and "assistant B", fact-checked both on the web and
scored them. One run per side, so treat small gaps as ties.

| Skill | Round 1 (with vs without) | Changes made | Round 2 (with vs without) |
|---|---|---|---|
| `unity-build-size` | 22.5 vs 23 (tie) | Web audio, exceptions and Minify caveats, Steam patch diagnosis, Android video and symbols | **8.2 vs 7.5** (won 2 of 3) |
| `game-docs` | 112 vs 122 (lost all 3) | Draft real core mechanics instead of a template; smallest edits in the user's style; no to-dos in user docs | **8.4 vs 8.0** (won all 3) |

## 3. Repo checks

- `python scripts/validate-skills.py`: 80 skill files, 0 errors, 0 warnings.
- `python -m unittest discover -s tests`: all pass; Godot tests run with Godot 4.7.2 headless.
- Every changed GDScript block parse-checked with Godot 4.7.2; web snippets run in headless
  Chromium against Phaser 4.2.1, PixiJS 8.22.0 and three r187; Luau blocks compiled with
  luau-compile 0.746; pygame-ce, LÖVE 11.5, Bevy 0.20.1, Defold 1.14.1 and Ebitengine 2.10.6
  snippets built or run where the toolchain was available.
- Not run: the Unity Editor, Unreal Editor, Roblox Studio and .NET builds of Godot C#.

## Method limits

- Judges are models, not users, and each cell is one run.
- The prompt set was written by one agent before the ownership rules changed, so a few expected
  answers reflect the old split between skills.
- Run it yourself with `scripts/run-trigger-evals.py --judge-cmd ...` (see `evals/README.md`).
