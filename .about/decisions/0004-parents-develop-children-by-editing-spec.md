---
status: Accepted
date: 2026-09-23
deciders: [k@wetware.works]
history:
  - 2026-09-23: Accepted — chosen over "children may read up" and "parent writes into child" to keep never-up and self-write intact
---

# Decision Record 0004: Parents develop children by editing their specification

## Context

`0003-trust-is-placement` forbids reading up. A parent that reads all its children may
learn something they should all know — "child_a and child_b keep discovering the same
rate limit" — yet no steer can reach them. Three routes were considered.

## Decision

1. A parent **does not pass steer to its children**. A parent influences its children only as their
   **owner**: on its next Act it edits a child's specification — its intent or its
   verifier — exactly as a human developing a loop would.
2. This is the same red–green–refactor mechanism the mental model describes (A1),
   performed by an agent. The parent–child relationship is **developmental**, not
   supervisory at run time.
3. This behaviour is **on by default** and may be **switched off** per deployment or
   per parent in configuration, for cases where a parent must only observe.

## Alternatives considered

| Option | Why not |
|---|---|
| Children may read the parent's steer | Makes reading up/down/sideways universal within a subtree; nested trees leak root to leaf. |
| Parent writes steer into children's directories | Violates self-write; makes provenance of a child's learnings ambiguous. |
| **Chosen: parent edits child spec, default on / config off** | Keeps `0003` intact; uses the owner mechanism defined in `0005` with no additional mechanism; the change reaches the child one run-cycle later, which is acceptable. |

## Consequences

- A parent's Learn may conclude "spec change needed for child X"; the change lands on
  the parent's *next* Act, not immediately.
- Children see the change as an owner edit — a new intent — and re-enter the growing
  cycle from there.
- With the switch off, a parent is purely an observer and aggregator.

## Related

- `0003-trust-is-placement`
- `0005-structural-change-is-proposed-by-loop-decided-by-owner`
