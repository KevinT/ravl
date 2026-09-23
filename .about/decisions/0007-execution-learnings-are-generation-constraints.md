---
status: Accepted
date: 2026-09-23
deciders: [k@wetware.works]
history:
  - 2026-09-23: Accepted — direct response to RavlGPT's diagnosed central failure
---

# Decision Record 0007: Execution learnings are constraints on generation

## Context

RavlGPT's last self-diagnosis (January 2026) found that a known execution fact — a
package's correct published name — had been recorded in its learnings and was still
ignored by code generation across seven consecutive attempts. Learning was captured but
not closed. The knowledge was *offered* to a prompt as context; nothing *required* the
derivation to honour it.

## Decision

1. Execution learnings (solution-space knowledge, mental model A4) are **constraints
   injected into the generation contract** for the next Act — not hints appended to a
   prompt.
2. A derivation that violates a recorded execution constraint is rejected before it
   runs, and the violation is recorded in the trace as a library failure, not a model
   failure.
3. Domain learnings remain *context* for Reflect to synthesise; they shape judgement and
   are not enforced mechanically.

## Alternatives considered

| Option | Why not |
|---|---|
| Keep execution learnings as prompt context (RavlGPT) | Demonstrated not to close the loop. |
| Enforce domain learnings mechanically too | Domain learnings are judgements about the subject matter. Enforcing them removes the ability of an LLM-driven run to adapt, which is the reason that mode exists. |
| **Chosen: execution = constraint, domain = context** | Matches the problem/solution split; makes the one class of learning that is mechanically checkable actually checked. |

## Consequences

- The generation contract must have a place for constraints and a check against them.
- "Known answer not enforced" is a bug class the test suite must cover from the start.

## Related

- `0002-execution-mode-learned-and-owner-settable`
