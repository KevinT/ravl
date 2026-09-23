---
status: Accepted
date: 2026-09-23
deciders: [k@wetware.works]
history:
  - 2026-09-23: Accepted — rejects child-to-parent signalling in favour of parents deciding how to observe their children
---

# Decision Record 0009: Nothing inside `ravl` starts a run; a loop has no knowledge of its ancestors

## Context

For a tree of loops to adapt to a change in the world at the point the change is
detected, something has to run the parent when a child's state changes. The first
proposal was that the runtime runs a loop's owner when the loop's Verify changes state.
This gives a loop knowledge that a parent exists, which is an upward dependency. A loop
with an upward dependency cannot be copied from one tree to another, or from a library
into a tree, and work unchanged.

## Decision

1. A run starts only when something outside the library invokes `ravl run` on a
   directory. The library has no scheduler, no event system and no trigger.
2. A loop does not read, signal or depend on the existence of any ancestor. Everything
   an ancestor wants a loop to know is written into the loop's specification, `config/`
   or budget.
3. How a parent observes its children, and how any loop observes the world, is part of
   that loop's own design. Its owner specifies it, or the loop learns it. The library
   guarantees only that a loop's state is on disk in a known place and format when its
   run ends.

## Alternatives considered

| Option | Why not |
|---|---|
| Runtime runs the owner when a child's Verify changes state | Upward dependency; loops not reusable across trees. |
| A "watch" loop type that emits events | An event system inside the library; the same coupling with extra machinery. |
| **Chosen: external invocation only; parent decides how to observe** | No upward edges. A parent that needs fast response runs often with a cheap Reflect. The pattern matches existing practice: a health check failing is what starts a repair session, and the health check does not know who is watching. |

## Consequences

- Propagation of a change up a tree takes one run per level, at whatever frequency each
  owner has chosen.
- "Cheap when nothing changed" is a design requirement for Reflect: reading steer files
  and comparing state must not require an LLM call.
- A loop from a library works in any tree without modification.

## Related

- `0003-trust-is-placement`
- `0004-parents-develop-children-by-editing-spec`
