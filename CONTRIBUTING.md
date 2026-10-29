# Contributing

Thanks for your interest in improving **awesome-gamedev-agent-skills**. This collection
values correct, lean, original skills over volume. Please read this guide and the
authoring standard in [`docs/SKILL-FORMAT.md`](docs/SKILL-FORMAT.md) before opening a PR.

## What a skill is

A skill is a directory containing a `SKILL.md` file, with optional resources that
support the workflow. It lives under the matching category in `skills/`:

```
skills/<category>/<skill-name>/
├── SKILL.md
├── agents/openai.yaml # optional Codex UI metadata
├── references/        # optional deeper material
├── scripts/           # optional deterministic helpers
└── assets/            # optional templates and starter files
```

The directory name **must equal** the skill's `name` frontmatter field.

Start from [`templates/SKILL.template.md`](templates/SKILL.template.md).

## Originality (non-negotiable)

Write everything from scratch from **primary documentation** (engine/framework docs,
language references, platform specs). You may study other skills or articles for general
patterns, but never copy their text or code. State the engine/runtime version your
examples target, and verify code is correct and idiomatic — do not invent APIs.

## PR checklist (the rubric)

A skill is ready to merge when all of the following are true:

- [ ] **Frontmatter valid.** `name` is ≤64 chars, lowercase letters/digits/hyphens only,
      no leading/trailing hyphen, and equals the folder name; `name` and `description`
      are the only committed frontmatter fields.
- [ ] **Description is a trigger.** `description` is non-empty, ≤1024 chars, and states
      both *what the skill does* and *when to use it*.
- [ ] **Lean body.** `SKILL.md` is under ~500 lines; deeper material is pushed into
      `references/`.
- [ ] **Progressive disclosure.** Name + description are enough to decide relevance; the
      body is loaded on demand.
- [ ] **Correct, version-pinned code.** Examples are tested/idiomatic and name the
      engine/runtime version. No invented APIs.
- [ ] **Original.** No copied text or code; written from primary docs.
- [ ] **Links resolve.** Any `references/` links in the skill point at real files.
- [ ] **Resources verified.** Scripts have `--help`, fail safely, and were exercised;
      templates/JSON parse; any `agents/openai.yaml` names the skill in its default prompt.
- [ ] **Validator passes** (see below).
- [ ] **No growth/marketing language** anywhere in committed files.

## Validator

Run the validator before pushing. It checks every `skills/**/SKILL.md` and
`router/SKILL.md` for the authoring contract. It also checks bundled resource links,
OpenAI UI metadata, JSON assets, router coverage, catalog counts, and plugin manifests:

```bash
python scripts/validate-skills.py
```

It exits non-zero and prints a report if anything fails.

If you have Claude Code installed, `claude plugin validate .` additionally checks
`.claude-plugin/marketplace.json` against Claude Code's own marketplace schema (JSON syntax,
required fields, entry names and relative paths).

If you change the validator itself, run its regression tests too:

```bash
python -m unittest discover -s tests -v
```

The documentation site is generated from the same frontmatter, so a skill's page
appears as soon as its `SKILL.md` is committed. To preview it locally:

```bash
python scripts/generate-site.py     # writes _site/ (git-ignored)
python scripts/check-site.py        # per-page title/description/canonical checks
```

For a later rebuild, use `python scripts/generate-site.py --clean`. Non-empty output
is refused without this flag, and `--clean` only replaces directories carrying the
generator's `.gamedev-skills-site` marker. Use a new or empty directory for `--out`;
the repository, its ancestors, filesystem roots, and symlink outputs are rejected.
Everything inside a marked output directory is disposable when you use `--clean`.

CI runs the validator, the tests and both site steps on every pull request.

## Updating the router when you add a skill

The [master router](router/SKILL.md) only routes to skills it knows about, so a new skill is
not "done" until the router can reach it. When you add a skill, update the router in the same
PR:

1. **Routing table.** Add the skill to the matching section of
   [`router/SKILL.md`](router/SKILL.md) §3 — under its engine in §3a, or as a discipline (§3b),
   genre (§3c), or workflow (§3d) — and to the exhaustive
   [`router/references/routing-table.md`](router/references/routing-table.md) with its trigger
   words and any engine bindings.
2. **Detection (engines only).** If the skill introduces a new engine or a new project-file
   signal, add it to the fingerprint table in §1 and to
   [`router/references/engine-detection.md`](router/references/engine-detection.md).
3. **Composition (genres).** If it's a genre, list the skills it `composes:` so it links out
   instead of re-teaching primitives.
4. **Re-validate.** Run the validator (it checks `router/SKILL.md` too) and confirm a sample
   prompt routes to the new skill.
5. **Wire distribution.** Add the skill to the complete and category bundles in
   [`.claude-plugin/marketplace.json`](.claude-plugin/marketplace.json), then update the README
   catalog/count. The validator checks these connections.

Keep the router lean: it dispatches by `name` + `description`, so a precise description (see
[Required frontmatter](docs/SKILL-FORMAT.md#required-frontmatter)) does most of the routing work.

## Commits & PRs

- Use **conventional commits**: `feat(<category>): …`, `docs: …`, `chore: …`,
  `fix: …`, `refactor: …`. Example: `feat(godot): add godot-tilemap skill`.
- Keep PRs focused — ideally one skill (or one coherent change) per PR.
- Describe what you added/changed and how you verified the example code.

## Code of conduct

Be respectful and constructive. Assume good faith and keep reviews focused on the work.
