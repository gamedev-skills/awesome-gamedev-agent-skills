---
name: studio-consistency-check
description: Find contradictions between a game art bible, system design, architecture, content, implementation, and player-facing behavior, then recommend bounded fixes.
---

# Studio Consistency Check

Use for cross-document and cross-implementation conflicts, particularly when AI agents have made independent decisions in different sessions.

## Workflow

1. Locate canonical sources: user-approved art bible, ADRs, design docs, engine configuration, manifest, schemas, tests, implementation and captures.
2. Build a consistency matrix mapping each invariant to its source, affected files and verification method (e.g., camera orientation, sprite dimensions, animation directions, inventory slot semantics, hit-frame timing).
3. Compare claims and implementations. Separate true contradictions from optional variants, superseded decisions and gaps in evidence.
4. Rank by player-visible harm, migration cost and risk of repeat divergence.
5. For each conflict propose a canonical source, affected files, precise correction, migration test and owner. Do not silently overwrite contested decisions.
6. Apply only small, authorized corrections and rerun affected tests. Update references and caches that the project actually uses.

## Finding table

| Invariant | Canonical source | Conflicting source/path | Evidence | Impact | Resolution |
|-----------|------------------|-------------------------|----------|--------|------------|

## Gates

No invented architectural decisions; no blanket rewrites; when evidence is missing, report 'unverified' and propose an inspection step. Include changed files, tests performed and unresolved decisions.
