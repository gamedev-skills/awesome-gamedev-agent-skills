---
name: replace-with-skill-name
description: >
  Engine and job first: state the concrete outcome this skill delivers. Use when the
  request mentions the files, APIs, symptoms or phrases users actually type. Not for
  the nearby job another skill owns (use related-skill).
---

# Replace with skill title

Deliver the outcome in one sentence. State the baseline version for new projects and preserve an
existing project's pinned version unless migration is requested.

## When to use

- Use when …
- Use when …

**When not to use:** hand off nearby work to `$related-skill` or the relevant engine skill.

## Workflow

1. **Inspect.** Read the project manifest, relevant files, existing conventions, and constraints.
2. **Choose.** Select the smallest compatible approach and state any consequential assumption.
3. **Implement.** Make the focused change using the project's current version and patterns.
   Where the usual answer is an editor click, also give the file, code or CLI way.
4. **Check.** Run `python scripts/example.py PROJECT` (or a headless run, test, build log or
   `grep`) and read the real output. Pass means … If a step needs a person, ask the user to …
   and report …
5. **Handoff.** Report changed files, evidence, caveats, and the next useful action.

## Patterns

### Focused pattern

```text
Use a compact, verified example. Do not invent APIs.
```

## Gotchas

- **Visible symptom** → likely cause; concrete fix and how to confirm it.
- **Version mismatch** → inspect the installed version and use its matching docs or migration guide.

## Resources

- Read `references/example.md` when … (one branch of the workflow, not every run).
- Run `scripts/example.py --help` before using the optional helper.
- Copy `assets/example.ext` only when the task needs the starter asset.

## Related skills

- `$related-skill`: the adjacent responsibility it owns.

## Version notes

Last verified YYYY-MM-DD.

- Facts that go stale (versions, prices, SDK minimums, store rules) go here, not in the workflow.
