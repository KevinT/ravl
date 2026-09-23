# Decision Records — `ravl`

Decisions that govern the whole repository. A record in `<dir>/.about/decisions/`
governs `<dir>` and everything beneath it; walk up the tree to collect every record in
force, nearest scope first.

## Conventions

- Files are `NNNN-short-noun-phrase.md`, numbered from `0000` within this scope.
  Reference records by full slug, never bare number.
- Frontmatter: `status` (Proposed / Accepted / Superseded / Rejected), `date`,
  `deciders`, `history` (one dated line per status change).
- Body: `## Context`, `## Decision`, `## Alternatives considered` (table),
  `## Consequences`, `## Related` (records in this scope or an ancestor only).
- A record is written *before* the thing it decides is built. Proposed records are
  design context only; do not cite them as current behaviour.
- Scope test: if the decision would survive renaming or removing any one component,
  it belongs here at the root. Otherwise it belongs in that component's `.about/decisions/`.

## Index

| Record | Status | One line |
|---|---|---|
| [`0000-rebuild-from-concepts-not-from-code`](0000-rebuild-from-concepts-not-from-code.md) | Accepted | `ravl` re-derives RavlGPT's concepts in a new repository; no code is ported |
| [`0001-one-attempt-per-run`](0001-one-attempt-per-run.md) | Accepted | A run never retries; failures are the next run's context |
| [`0002-determinism-gradient-learned-and-declarable`](0002-determinism-gradient-learned-and-declarable.md) | Accepted | Loops crystallise toward code and pull back on solution-attributed failure; owners may pin either end |
| [`0003-trust-is-placement`](0003-trust-is-placement.md) | Accepted | Read sideways and down, write self only; trust inferred from filesystem orientation |
| [`0004-parents-develop-children-by-editing-spec`](0004-parents-develop-children-by-editing-spec.md) | Accepted | Steer never flows down; a parent changes a child's specification instead (default on, config off) |
| [`0005-structural-change-is-proposed-by-loop-decided-by-owner`](0005-structural-change-is-proposed-by-loop-decided-by-owner.md) | Accepted | Lock, never-lock, split, merge, retire belong to the owner; the loop proposes |
| [`0006-core-is-environment-blind`](0006-core-is-environment-blind.md) | Accepted | No knowledge store, organisation, host or runtime is named in the core; surfaces and resources are handed in |
| [`0007-execution-learnings-are-generation-constraints`](0007-execution-learnings-are-generation-constraints.md) | Accepted | Execution knowledge is enforced on derivation, not offered as a hint |
