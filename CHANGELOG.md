# Changelog

Notable changes to this project. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and releases use [semantic versioning](https://semver.org/).

## [Unreleased]

## [2.0.0] - 2026-11-11

### v2 quality release

- **Every skill rewritten to Anthropic's skill-authoring guidance:** a description that says what
  the skill is for and which neighbour handles the rest, one `## Gotchas` section, a final check the
  agent runs itself, editor clicks with a file, code or CLI alternative, contents lists on long
  references, and dated `## Version notes`.
- **Clear ownership for requests two skills both claimed** (behavior trees, coyote time, Unity 2D
  physics, procedural generation vs roguelike vs card games, RPG vs survival inventory, Roblox
  replication), followed by the router and every description.
- **Shorter descriptions:** the full pack lists 29,866 characters, so it fits agents' skill
  listing budgets.
- **Router:** reads the project's pinned engine version first, warns when the project is newer
  than our baseline, and hands live-editor work to official vendor tools (Unity, Roblox, Epic,
  OpenAI game-studio) when they are already installed.
- **Engine baselines refreshed and verified 2026-11-11:** Godot 4.7.2, Unity 6.3 LTS, UE 5.8,
  Phaser 4.2.1, PixiJS 8.22.0, three.js r187, Bevy 0.20.1, Defold 1.14.1, Ebitengine 2.10.6,
  LÖVE 11.5, pygame-ce 2.5.8.
- **New check tools:** five headless GDScript check runners in the Godot skills, a jump tuner for
  `platformer`, a wave-curve checker for `tower-defense`.
- **Measured:** trigger evals and outcome A/B tests, with results in `evals/RESULTS.md`.
- New skills: `unity-build-size` ([#41](https://github.com/gamedev-skills/awesome-gamedev-agent-skills/pull/41))
  and `game-docs` ([#35](https://github.com/gamedev-skills/awesome-gamedev-agent-skills/pull/35)),
  both upgraded and A/B tested before merging. 79 skills in total.
- Validator fix for link-like code inside fences ([#48](https://github.com/gamedev-skills/awesome-gamedev-agent-skills/pull/48)).

### Added

- Trigger evals: `evals/triggers.json` (366 prompts), `evals/README.md` and `evals/RESULTS.md`; `scripts/run-trigger-evals.py`
  checks it offline and scores skill descriptions with any judge command (`claude -p`,
  `codex exec -`). CI runs the offline check.
- Validator warnings for the new writing rules: no `Not for` clause in the description, no
  `## Gotchas` heading, a long reference without a contents list, a reference that links to
  another reference. `--strict` makes them errors.
- `CHANGELOG.md`.
- `ai-behavior-trees-utility-ai`: engine-neutral behavior trees and utility AI
  ([#12](https://github.com/gamedev-skills/awesome-gamedev-agent-skills/pull/12)).
- Five Roblox skills for UI, networking, characters, physics and Studio workflows
  ([#10](https://github.com/gamedev-skills/awesome-gamedev-agent-skills/pull/10)).
- `godot-gdscript-headless-testing`: GDScript tests that run headless and in CI
  ([#16](https://github.com/gamedev-skills/awesome-gamedev-agent-skills/pull/16)).
- Project check scripts for Godot, Unity and Steam builds that catch broken references
  before the project is opened ([#21](https://github.com/gamedev-skills/awesome-gamedev-agent-skills/pull/21)).
- Ebitengine: the `ebitengine-game` skill and an Ebitengine bundle
  ([#22](https://github.com/gamedev-skills/awesome-gamedev-agent-skills/pull/22)), with
  follow-up fixes ([#24](https://github.com/gamedev-skills/awesome-gamedev-agent-skills/pull/24)).
- `defold-core` and Defold routing ([#25](https://github.com/gamedev-skills/awesome-gamedev-agent-skills/pull/25)).
- `roblox-simulator-economy` ([#32](https://github.com/gamedev-skills/awesome-gamedev-agent-skills/pull/32)).
- `create-game-assets` with asset reports and preview sheets, a version support page and
  agent UI metadata ([#9](https://github.com/gamedev-skills/awesome-gamedev-agent-skills/pull/9),
  bringing in [#8](https://github.com/gamedev-skills/awesome-gamedev-agent-skills/pull/8)).
- A documentation site generated from skill frontmatter, built in CI
  ([#7](https://github.com/gamedev-skills/awesome-gamedev-agent-skills/pull/7)).
- Install docs for the Oh My Pi agent ([#13](https://github.com/gamedev-skills/awesome-gamedev-agent-skills/pull/13)).
- A README link to a fan-maintained Meccha Chameleon hide-spots reference
  ([#3](https://github.com/gamedev-skills/awesome-gamedev-agent-skills/pull/3)).
- Router guidance for custom and proprietary engines, wall slide and wall jump in
  `platformer`, and new Phaser and three.js gotchas
  ([#34](https://github.com/gamedev-skills/awesome-gamedev-agent-skills/pull/34)).
- A sponsors section in the README ([#50](https://github.com/gamedev-skills/awesome-gamedev-agent-skills/pull/50),
  [#51](https://github.com/gamedev-skills/awesome-gamedev-agent-skills/pull/51)).

### Changed

- Every skill now uses only `name` and `description` in its frontmatter, and engine baselines
  moved to current releases ([#9](https://github.com/gamedev-skills/awesome-gamedev-agent-skills/pull/9)).
- Content refresh against official engine docs and vendor skills
  ([#17](https://github.com/gamedev-skills/awesome-gamedev-agent-skills/pull/17)).
- `bevy-ecs` updated to Bevy 0.20 ([#18](https://github.com/gamedev-skills/awesome-gamedev-agent-skills/pull/18)).
- All skills, the router and the docs checked again against the latest stable engines on
  2026-10-24 ([#26](https://github.com/gamedev-skills/awesome-gamedev-agent-skills/pull/26)).
- Outdated skill content updated for Godot 4.7, Unity and Unreal 5.8
  ([#47](https://github.com/gamedev-skills/awesome-gamedev-agent-skills/pull/47)).
- The README states the skill count the same way everywhere
  ([#14](https://github.com/gamedev-skills/awesome-gamedev-agent-skills/pull/14)).
- Contributor docs (`docs/SKILL-FORMAT.md`, `CONTRIBUTING.md`, the skill template) describe the
  new writing rules: `Not for` clause, `## Gotchas`, a runnable final check, when to read each
  reference, contents lists, dated `## Version notes`, and trigger evals for new skills.

### Fixed

- `tower-defense` now implements the targeting modes it advertised, plus version gotchas for
  Godot scene changes, Unity Domain Reload and tilemap refreshes
  ([#4](https://github.com/gamedev-skills/awesome-gamedev-agent-skills/pull/4)).
- The validator enforces the frontmatter portability rules it documents
  ([#6](https://github.com/gamedev-skills/awesome-gamedev-agent-skills/pull/6)).
- Runtime examples that kept stale state or broke when combined; the site generator no longer
  deletes output it does not own ([#39](https://github.com/gamedev-skills/awesome-gamedev-agent-skills/pull/39)).
- Issues 27 to 31: Phaser keys stuck down, three.js timer and pixel-ratio problems, and a false
  GPU readback warning in the Ebitengine checker
  ([#34](https://github.com/gamedev-skills/awesome-gamedev-agent-skills/pull/34)).
- The validator no longer treats link-like code inside fences as a link
  ([#48](https://github.com/gamedev-skills/awesome-gamedev-agent-skills/pull/48)).

## [1.1.0] - 2026-06-26

66 skills and the router.

### Added

- Four cross-engine disciplines: `game-feel`, `game-ui-ux`, `camera-systems` and
  `performance-optimization`.
- One-command install as a Claude Code plugin, with skills grouped by category in
  `.claude-plugin/marketplace.json`, and the `npx skills` installer.
- A project banner in the README.

### Changed

- Agent compatibility docs cover more agents, including Antigravity.

## [1.0.0] - 2026-06-25

First stable release: 62 skills and a master router.

### Added

- Engine skills for Godot (15), Unity (8), Unreal (6), the web (6: Phaser, PixiJS, three.js)
  and other engines (5: Bevy, pygame, LÖVE, Roblox).
- Nine disciplines, nine genres and four workflows (game jam, fast prototypes, Steam and itch.io
  publishing).
- `router/SKILL.md`, which detects the engine and task and loads only the skills needed.
- The authoring standard, the skill template and `scripts/validate-skills.py`.

[Unreleased]: https://github.com/gamedev-skills/awesome-gamedev-agent-skills/compare/v2.0.0...HEAD
[2.0.0]: https://github.com/gamedev-skills/awesome-gamedev-agent-skills/compare/v1.1.0...v2.0.0
[1.1.0]: https://github.com/gamedev-skills/awesome-gamedev-agent-skills/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/gamedev-skills/awesome-gamedev-agent-skills/releases/tag/v1.0.0
