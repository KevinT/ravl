---
status: Accepted
date: 2026-09-23
deciders: [k@wetware.works]
history:
  - 2026-09-23: Accepted — generalises RavlGPT's "read-anywhere, write-own" into a placement-inferred topology with a never-up rule
---

# Decision Record 0003: Trust is placement

## Context

Loops learn more when they can read one another's learnings. But groups of loops run
on behalf of different people and organisations must never inform each other, and the
core must enforce that without knowing who those parties are
(`0006-core-is-environment-blind`).

## Decision

1. **Write:** a loop writes learnings only for itself. Ever.
2. **Read:** a loop reads learnings **sideways** (siblings — loops sharing its parent
   directory) and **down** (its descendants). It never reads **up**.
3. Reading siblings is *expected*: their steer is an input to Reflect.
4. Trust relationships are **inferred from filesystem orientation** and from nothing
   else. There is no trust configuration, registry or allow-list in the core.
5. Two groups that must never inform each other are simply never placed under a common
   parent.

## Alternatives considered

| Option | Why not |
|---|---|
| Configured trust scopes / allow-lists | Configuration drifts from placement; the core would need vocabulary for parties it must not know. |
| Read anywhere (RavlGPT) | When two parties share a machine, a shared store lets one party's loops read the other's learnings. |
| Read up as well as sideways/down | Everything in a subtree becomes visible to everything else; nested trees leak from root to leaf. |
| **Chosen: sideways and down, self-write, placement-inferred** | Provable by inspection of a directory tree; supports emergent group behaviour without a global view. |

## Consequences

- A group of loops can coordinate without any loop having a view of the whole group:
  each reacts only to the steer of its siblings and descendants.
- A parent cannot push steer down; see
  `0004-parents-develop-children-by-editing-spec` for how it influences children.
- A deployment separates groups of loops by directory layout, and can verify the
  separation by listing the directories.

## Related

- `0004-parents-develop-children-by-editing-spec`
- `0006-core-is-environment-blind`
