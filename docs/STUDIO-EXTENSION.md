# Studio Extensions

This fork retains the original game-development router and adds ten production/design skills. All ten are portable, engine-neutral and located under `skills/studio/`.

## Ownership rules

- Engine skills own code and APIs; disciplines own portable algorithms; genre skills own composition.
- `create-game-assets` owns generation, normalization and import. Studio skills own durable decisions, specifications and validation evidence.
- Route minimally: one or two studio skills for each relevant task, not the entire catalog.
- Read approved art bibles, ADRs, game design documents, manifests and source before proposing changes.
- Preserve the project's actual engine. MonoGame and other unsupported engines use the existing custom-engine fallback, not invented Godot or Unity integrations.

## Examples

| Task | Skills |
|------|--------|
| Define an Alongsia visual style | `studio-art-bible` |
| Specify modular equipment for a boss | `studio-asset-spec`, `create-game-assets` |
| Audit PixelLab sprites | `studio-asset-audit` |
| Design an ARPG loot system | `studio-system-design`, `rpg`, `save-systems` |
| Choose animation architecture | `studio-architecture-decision`, `create-game-assets` |
| Deliver a polished combat slice | `studio-vertical-slice`, `rpg`, `game-feel`, engine skills |
| Check design/code contradictions | `studio-consistency-check` |
| Test equipment-swap regressions | `studio-qa-plan` and engine test skills |

## Provenance and license notices

Base project: https://github.com/gamedev-skills/awesome-gamedev-agent-skills (Apache-2.0).
Curated from Codex Game Studio: https://github.com/merlinhu1/codex-game-studio (MIT, copyright 2026 MerlinH). Full source MIT notice is in `docs/third-party/codex-game-studio-LICENSE`. Retain the original Apache-2.0 LICENSE and NOTICE.

These rewritten skill playbooks do not import Codex Game Studio's CLI, 50 agent profiles, project-state assumptions or model-routing metadata. All modified catalog files are marked where appropriate.

## Maintenance

After synchronizing the upstream fork, review the marked unified-studio-extension blocks and run:

```bash
python scripts/validate-skills.py
git diff --check
```

Install this fork rather than simultaneously installing it and the unmodified base router.