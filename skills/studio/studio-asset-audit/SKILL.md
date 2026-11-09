---
name: studio-asset-audit
description: Audit the completeness, consistency, provenance, technical validity, and import readiness of a game asset library against an approved art bible and manifest.
---

# Studio Asset Audit

This is a **read-first** QA and inventory workflow, not a license to regenerate or delete assets.

## Workflow

1. Read the art bible, manifests, asset specs, generation history, and engine importer conventions. If missing, record the gap before inventing a schema.
2. Inventory files by family, path, hash, dimensions, frames, direction, state, format, license, provenance and game use. Distinguish placeholder, proposed, accepted, rejected, deprecated and shipped.
3. Check duplicate/near-duplicate naming, ambiguous variants, frame count, alpha, malformed sprite sheets, inconsistent baselines, pivots, palette, compression and scaling.
4. Verify modular gear compatibility: shared poses, facing order, coverage masks, attachment offsets, collision silhouette and animation duration.
5. Check license/provenance evidence: source, author, generation workflow, restrictions, third-party rights and attribution. Unknown rights are an explicit shipping block.
6. Validate a representative contact sheet and actual engine import. Report only tests that were actually run.
7. Produce a prioritized finding register with precise file paths, reproducible evidence, severity and owner. Propose bounded fixes and rerun affected checks after approval.

## Output schema

| ID | Asset/path | Finding | Severity | Evidence | Recommended action | Status |
|----|------------|---------|----------|----------|--------------------|--------|

Classify severity as blocker (unusable/rights), major (visible or functional), minor (polish). Give totals for expected/present/approved assets only when a trustworthy manifest exists.

## Handoff

Summarize readiness, critical missing assets, license blockers, import risks, corrective actions, tests performed, and unknowns. Pair with `create-game-assets` only for authorized repairs.
