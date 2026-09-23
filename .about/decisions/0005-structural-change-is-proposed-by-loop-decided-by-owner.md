---
status: Accepted
date: 2026-09-23
deciders: [k@wetware.works]
history:
  - 2026-09-23: Accepted — settles "infer-then-confirm vs infer-then-act" by introducing the owner and giving structural decisions to it
---

# Decision Record 0005: Structural change is proposed by the loop, decided by the owner

## Context

Learn can usually infer that a loop should never lock, or that it is really two loops.
The question was whether the loop should act on that inference alone, act and inform
afterwards, or propose and wait. The answer required naming who decides.

## Decision

1. **Every loop has exactly one owner**: whoever holds its intent and verifier. Owner is
   inferred from placement — a loop under a parent directory is owned by that parent
   loop; a root loop is owned by whoever runs it, human or agent. There is no owner
   field or registry.
2. Only the owner may: change intent or verifier; pin the gradient (`lock`,
   `never-lock`); decompose or merge; retire the loop.
3. For each of these the loop's role is to **propose**, as a question addressed to its
   owner in its steer. It never performs the change on itself.
4. Latency of the decision follows the owner: a parent loop, being an agent, may decide
   on its next Act (`0004`); a human decides on their own cadence. One mechanism, two
   speeds — no separate "confirm" and "act" modes.

## Alternatives considered

| Option | Why not |
|---|---|
| Loop acts on its own inference (infer-then-act) | Structural change to *what a loop is* made without its owner's judgement; groups could restructure from the bottom. |
| Two modes: confirm for humans, act for agents | Two mechanisms for one concept; the owner notion already gives the latency difference for free. |
| **Chosen: propose to owner; owner decides** | Authority flows down, evidence flows up; leaves propose, parents decide, the root's human decides for the root. |

## Consequences

- Known-unknowns (questions for the owner) are a first-class output of Learn, and
  structural proposals are one kind of them.
- The library must make proposals easy for an owner to see and act on — through
  whatever surface the owner uses.

## Related

- `0002-determinism-gradient-learned-and-declarable`
- `0004-parents-develop-children-by-editing-spec`
