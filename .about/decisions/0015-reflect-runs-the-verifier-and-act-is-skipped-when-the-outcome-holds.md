---
status: Proposed
date: 2026-11-26
deciders: [k@wetware.works]
history:
  - "2026-11-26: Proposed — written by the implementing agent while building the runner (first-loop steps 1 to 8), under the owner's instruction to build; implemented in 0.1.0; not yet reviewed by the decider"
---

# Decision Record 0015: Reflect runs the verifier; Act does nothing when the outcome already holds

## Context

The scope includes outcomes that must be maintained: a service that must stay up, a feed
that must stay current ([`0008-ravl-is-for-outcomes-that-recur`](0008-ravl-is-for-outcomes-that-recur.md)).
On most runs of such a loop the outcome already holds. The model said Reflect "reads the
current state of the world" without saying how, and
[`0009-no-run-starts-inside-ravl-no-upward-knowledge`](0009-no-run-starts-inside-ravl-no-upward-knowledge.md)
requires that a run in which nothing changed needs no LLM call.

## Decision

1. Reflect runs the verifier's checks against the world as it is before Act. The result
   is part of the context for Act.
2. When every criterion has a check and all pass at Reflect, Act performs no work and
   records the reason. No LLM is called and no generated code is run. Verify reuses the
   Reflect result, and Learn records a pass.
3. When a check fails at Reflect, Act is performed in the loop's execution mode, and is
   given the failing criteria with their check output.
4. A loop that produces something new on every run states that in its verifier (for
   example, "the report was written during this run"). That criterion fails at Reflect
   on every run, so Act runs every time. The library has no separate setting for the two
   kinds of loop.
5. After Act has done work, Verify runs the checks again. Reflect's result is reused
   only when Act did nothing.

## Alternatives considered

| Option | Why not |
|---|---|
| Act always runs and decides for itself whether work is needed | An LLM call per run to conclude that nothing is wrong; a loop over a healthy system would spend its budget confirming health. |
| A loop type or flag for "maintain" versus "produce" | A setting that the verifier already expresses. |
| **Chosen: the verifier is read at Reflect; Act is skipped when it passes** | A healthy run costs the checks only. The same mechanism serves both kinds of loop. |

## Consequences

- The execution-mode scale applies to the repair, not to the health check: a maintenance
  loop that becomes code-driven runs its generated repair only when a check fails.
- Consecutive passes with no Act do not count toward generating code; only passes in
  which an LLM performed Act do, because only those show a procedure.
- Checks run twice in a run where Act did work. Checks must be safe to repeat and should
  be cheap.

## Related

- `0014-verifier-criteria-carry-checks`
- `0002-execution-mode-learned-and-owner-settable`
- `0009-no-run-starts-inside-ravl-no-upward-knowledge`
