---
name: studio-architecture-decision
description: Create or update a concise architecture decision record comparing real options, constraints, consequences, validation and rollback.
---

# Studio Architecture Decision Record (ADR)

Use for decisions that affect multiple systems, content contracts, team workflows, or long-term cost. Not every local refactor needs an ADR.

## Procedure

1. Inspect the current engine, ADR log, implementation and constraints. State the decision question and whether it is reversible.
2. List 2–4 viable options, including keep-current, with risks, costs and affected data/assets.
3. Evaluate implementation complexity, quality/iteration speed, compatibility, licensing, runtime performance, testing and migration impact.
4. State the chosen option only when evidence supports it or the user delegates the call; distinguish tradeoffs from certainties.
5. Record consequences and what must change; include rollout stages, test evidence, observation windows and a rollback trigger.
6. Write a dated ADR under `docs/architecture/decisions/` or the existing ADR location. Cross-link superseded decisions rather than deleting history.

## ADR template

```text
Status: proposed | accepted | superseded
Context / decision question:
Constraints / evidence:
Options and tradeoffs:
Decision and rationale:
Consequences:
Migration / compatibility:
Verification plan and actual results:
Rollback condition:
Open questions / owner:
```

Do not silently change engine choice, project tools or asset format while drafting an ADR. Route actual code through the detected engine skills.
