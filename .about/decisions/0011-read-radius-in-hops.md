---
status: Accepted
date: 2026-09-23
deciders: [k@wetware.works]
history:
  - 2026-09-23: Accepted — makes the read rule in 0003 quantitative and assigns narrowing to the loop and widening to the owner
---

# Decision Record 0011: Read radius in hops, default 1; the loop narrows, the owner widens

## Context

Decision 0003 says a loop reads sideways and down and never up. It does not say how
far down or sideways. A loop that reads everything within its containing directory at
every depth is expensive and reads mostly irrelevant material. A loop that can widen
its own reading can read past a boundary its owner relied on.

## Decision

1. Read scope is measured in **hops**. Hop 0 is the loop's own learnings. Hop 1 is its
   siblings (loops sharing its containing directory) and its children. Each further hop
   is one directory level deeper. The scope never extends above the containing
   directory: a loop lists that directory to find siblings and reads no `ravl.*` or
   learnings file in it or above it.
2. Default radius is 1. The owner sets it in `config/`.
3. Within its radius, the loop **narrows** what it reads by learned relevance: a
   sibling whose learnings never contribute to a passing run is dropped from Reflect.
4. The loop may not widen its radius. It proposes widening as a question to its owner
   when learnings outside the radius would have helped.
5. Learnings from anywhere else are resources the owner names in the specification,
   handled like any other resource.

## Alternatives considered

| Option | Why not |
|---|---|
| Read everything within the containing directory | Cost grows with the tree; most of it is irrelevant to any one loop. |
| Loop sets its own radius | Can read past a trust boundary its owner placed. |
| **Chosen: hops; default 1; loop narrows, owner widens** | Same shape as budgets: granted downward, used upward. A parent that sees a child would benefit from wider reading grants it by editing the child's config, which is the mechanism in 0004. |

## Consequences

- Knowing a containing directory exists is not an upward dependency; depending on its
  contents would be. The rule distinguishes them.
- The read radius is a fourth thing only the owner may change, alongside intent,
  verifier and execution mode.

## Related

- `0003-trust-is-placement`
- `0009-no-run-starts-inside-ravl-no-upward-knowledge`
- `0010-loops-create-and-remove-children-within-budget`
