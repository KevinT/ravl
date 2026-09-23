---
status: Accepted
date: 2026-09-23
deciders: [k@wetware.works]
history:
  - 2026-09-23: Accepted — extends 0004 from editing children to creating and removing them, and adds budgets so the cascade is bounded
---

# Decision Record 0010: A loop may create and remove loops in its own directory, within a budget its owner set

## Context

A human writing one root loop with an abstract intent, which then decomposes its
outcome into child loops it owns, each of which may do the same, gives a tree that
can be re-targeted over time without the human specifying every level. Decision 0004
already lets a parent edit a child's specification. Creating a child is writing a
specification where none existed; removing one is retiring it. Both are owner actions.
A loop that can create children can create too many, and each costs LLM calls until it
becomes code-driven.

## Decision

1. A loop may create, edit and remove loops in its own directory as part of its Act.
   It may not create, edit or remove itself or anything outside its directory. On by
   default; may be disabled in `ravl.toml` or `config/`.
2. Before removing a child, the parent absorbs the child's domain learnings into its
   own. Execution learnings are not absorbed. Removal then deletes the directory.
3. Every loop has a per-run budget and a per-subtree budget over a rolling window,
   measured in the units of the cost ledger. Defaults are set by the library and
   overridden per loop in `config/`.
4. When a parent creates a child it sets the child's budgets, which may not exceed the
   parent's remaining budget. The child never reads the parent's budget.
5. Exceeding the per-run budget stops the run and is a world failure. Exceeding the
   per-subtree budget stops the loop from creating children or running LLM-driven until
   the window moves, and writes a question to the owner.

## Alternatives considered

| Option | Why not |
|---|---|
| Only humans create loops | The tree cannot re-target itself; every decomposition is manual. |
| Creation allowed, no budget | The first defect in a parent's Act is an unbounded spend. |
| Delete children without absorbing learnings | Knowledge is lost if a similar child is later created. |
| **Chosen: create/remove in own directory; absorb on removal; budgets cascade downward** | Bounded, DAG-safe (the child only ever sees a number its parent wrote), and keeps decision 0009 intact. |

## Consequences

- Budget defaults are placeholders until real loops provide figures. The first loops
  record cost ledgers; defaults are set from them.
- The cost ledger must be aggregatable per subtree, which requires that each run's
  ledger is on disk in a fixed format.
- The model's A8 and A9 state these rules.

## Related

- `0004-parents-develop-children-by-editing-spec`
- `0005-structural-change-is-proposed-by-loop-decided-by-owner`
- `0009-no-run-starts-inside-ravl-no-upward-knowledge`
