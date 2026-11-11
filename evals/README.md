# Trigger evals

A skill only helps when the agent picks it. These evals measure that: for each realistic
request, does the agent choose the right skills from their `name` and `description` alone,
and leave the wrong ones alone?

`evals/triggers.json` holds the prompts. [`scripts/run-trigger-evals.py`](../scripts/run-trigger-evals.py)
checks the file offline and scores the current descriptions with any judge command you have.

## File format

The file is one JSON list. Each entry looks like this:

```json
{
  "id": "audio-design.s1",
  "prompt": "my game music cuts hard between explore and combat, how do i crossfade layers",
  "expected": ["audio-design"],
  "kind": "should",
  "notes": "adaptive music, no engine named"
}
```

| Field | Meaning |
|---|---|
| `id` | Unique. Should and near-miss ids start with the skill they test and a dot (`audio-design.s1`, `audio-design.nm`). Other kinds use `combo.01` or `none.01`. |
| `prompt` | The request as a user would type it: casual, short, typos welcome. |
| `expected` | Skills that should be picked. Never `router`; the runner ignores it on both sides. |
| `kind` | `should`, `near-miss`, `combo` or `none` (below). |
| `notes` | Optional. Why the prompt exists, or `AMBIGUOUS: ...` when two skills could fairly win. |

Kinds:

- **should**: the skill in the id must fire. `expected` includes it, and may add a second
  skill the request clearly needs (an engine skill next to a genre skill).
- **near-miss**: shares words with the skill in the id but belongs elsewhere. `expected` is
  the skill that should win, or `[]`, and never the skill in the id.
- **combo**: needs two or three skills together.
- **none**: not game-development work. `expected` is `[]`.

Every skill needs at least 3 should prompts and 1 near-miss prompt. Vary the phrasing: one
direct, one casual or implicit, one that only describes a symptom. A good near-miss uses the
skill's own keywords for a job its neighbour owns (see the "Not for" clause in its description).

## Check the file

```bash
python scripts/run-trigger-evals.py --check
```

This needs no network. It fails on bad JSON or fields, duplicate ids, unknown skill names, a
near-miss that expects its own skill, and any skill with fewer than 3 should or 1 near-miss
prompts. CI runs it with `--allow-missing`, which passes while the file does not exist yet.

## Score descriptions with a judge

The runner builds one selector prompt per entry (every skill name and description, then the
request) and sends it on stdin to the command you give. The command must print a JSON list of
skill names. The runner itself calls no API and needs no keys.

```bash
# Run from an empty folder so the judge does not load this repo's skills itself.
cd "$(mktemp -d)"
python /path/to/repo/scripts/run-trigger-evals.py --root /path/to/repo --judge-cmd "claude -p --model haiku"
python /path/to/repo/scripts/run-trigger-evals.py --root /path/to/repo --judge-cmd "codex exec --skip-git-repo-check -" --json > after.json
```

Scoring, with `router` ignored:

- **should** and **combo** pass when every expected skill is picked. Extra picks do not fail
  the prompt but lower precision.
- **near-miss** passes when the skill in the id is not picked and every expected skill is.
- **none** passes when nothing is picked.
- Precision and recall count each (prompt, skill) pair. The report also lists the worst skills
  by F1 with the ids they missed or wrongly took.

Useful options: `--kind near-miss` and `--limit 20` for a quick run, `--jobs 4` for parallel
calls, `--print-prompt ID` to see exactly what the judge gets, `--without-router` to leave the
router out of the list, and `--root OTHER_CHECKOUT` to score older descriptions against the same
file (unknown skills then only warn and count as misses). The exit code is 1 if any judge call
failed, so re-run or raise `--retries`.

To compare two versions, run the same file and judge against both checkouts and compare the
`summary` blocks. Judges vary between runs and models, so use the same model for both sides and
treat differences of a few points as noise.

## When you add or change a skill

Add 3 should prompts and 1 near-miss prompt for a new skill, and a near-miss for the neighbour
it is most likely to steal from. When you change a description, run at least that skill's
prompts and its neighbours' before and after.
